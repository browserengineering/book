---
title: Constructing a Document Tree
chapter: 4
prev: text
next: layout
...

::: {.todo}
- HTML attributes are unmotivated
- I've dropped `<meta>` and `<link>` self-closing tags, probably should put them back somehow
:::

So far, your web browser sees web pages as a stream of open tags,
close tags, and text. But HTML is actually a tree, and though the tree
structure hasn't been important yet, you'll need it to draw
backgrounds, add margins, and let alone implement CSS. So this chapter
adds a proper HTML parser and converts the layout engine to use it.


A tree of nodes
===============

Right now, the browser sees web pages as a flat sequence of tags and
text, which is why the `Layout` object's `token` method includes code
for both open and close tags. But HTML is a tree, and each open and
close tag pair are one node in the tree, as is each text token. We
need to convert from tokens to nodes.

Let's start by defining the two types of nodes:[^1]

[^1]: In reality there are other types of nodes too, like comments,
    doctypes, and `CDATA` sections, and processing instructions. There
    are even some deprecated types!

``` {.python}
class ElementNode:
    def __init__(self, tag):
        self.tag = tag
        self.children = []

class TextNode:
    def __init__(self, text):
        self.text = text
```

Element nodes start empty, and our parser fills them in. The idea is
simple: keep track of the currently open elements, and any time we
finish a node (at a text or end tag token) we add it to the
bottom-most currently-open element. Let's store the currently open
elements in a list, from top to bottom:

``` {.python}
def parse(tokens):
    currently_open = []
    for tok in tokens:
        # ...
```

Inside the loop, we need to figure out if the token is text, an open
tag, or a close tag, and do the appropriate thing. `Text` tokens are
the easiest: create a new `TextNode` and add it to the bottom-most
open element.

``` {.python indent=8}
if isinstance(tok, Text):
    node = TextNode(tok.text)
    currently_open[-1].children.append(node)
```

End tags are similar, but instead of making a new node they take the
bottom-most open element:

``` {.python indent=8 expected=True}
elif tok.tag.startswith("/"):
    node = currently_open.pop()
    currently_open[-1].children.append(node)
```

Finally, for open tags, we need to create a new `ElementNode` and add
it to the list of currently open elements:

``` {.python indent=8}
else:
    node = ElementNode(tok.tag)
    currently_open.append(node)
```

The core of this logic is about right, but what and when does the
parser return? Try parsing

``` {.html}
<html><body><h1>Hi!</h1></body></html>
```

and the parser will read the `</html>` element, pop the last open
element off the list of open elements, and then crash since there's no
open element to append it to. So in this case we actually want to
return that root element:

``` {.python indent=8}
elif tok.tag.startswith("/"):
    node = currently_open.pop()
    if not currently_open: return node
    currently_open[-1].children.append(node)
```

Time to test this parser out!

::: {.further}
The real [HTML parsing algorithm][html5-after-body] doesn't stop when
it sees the `</html>` tag; it just moves to a state called `after
after body`, and any additional nodes are added to the end of the
`<body>` element. It also doesn't require you to write the `<html>`
tag to begin with.
:::

[html5-after-body]: https://html.spec.whatwg.org/multipage/parsing.html#parsing-main-afterbody

Parsing subtleties
==================

Try running this parser on this page, and you'll find that `parse`
doesn't return anything; let's find out why:

``` {.python expected=False}
def parse(tokens):
    # ...
    print(currently_open)
    raise Exception("Reached end of token before end of document"))
```

Python prints a list of `ElementNode` objects, meaning that there were
open HTML elements still around when it reached the last token. Why?
Unfortunately, Python does not help us resolve the mystery, because it
prints `ElementNode`s like this:

```
[<__main__.ElementNode object at 0x101399c70>,  ...]
```

Python needs a method called `__repr__` to be defined to print things
a little more reasonably:

``` {.python}
class ElementNode:
    # ...
    def __repr__(self):
        return "<" + self.tag + ">"
```

This produces a more reasonable result:

``` 
[<!DOCTYPE html>,
 <html lang="en-US" xml:lang="en-US">,
 <head>,
 <meta charset="utf-8" />,
 <meta name="generator" content="pandoc" />,
 <meta name="viewport" content=... />,
 <link rel="prev" href="text" />,
 <link rel="next" href="layout" />,
 <link rel="stylesheet" href="../book.css" />]
```

Why aren't these open elements closed? Well, most of them (like
`<meta>` and `<link>`) are what are called self-closing: they don't
need a close tag because they never surround content. Let's add a case
for that to our parser:

``` {.python indent=8}
# ...
elif tok.is_self_closing():
    node = ElementNode(tok.tag)
    currently_open[-1].children.append(node)
```

This relies on an `is_self_closing` method on `Tag`s:[^void-elements]

[^void-elements]: The list below comes from the HTML standard's list of
    [void elements][html5-void-elements]; a lot of them are obscure or
    obsolete, but why not get the whole list in?

[html5-void-elements]: https://html.spec.whatwg.org/multipage/syntax.html#void-elements

``` {.python}
SELF_CLOSING_ELTS = [
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
]

class Tag:
    # ...
    def is_self_closing(self):
        return self.tag.split()[0].lower() in SELF_CLOSING_ELTS
```

Note that I'm doing a case-insensitive comparison[^case-insensitive]
of the tag name, and furthermore that I'm ignoring an attributes like
in the `meta` and `link` tags above. Now the list of open elements is
shorter:

[^case-insensitive]: This is [not the right way][case-hard] to do case
    insensitive comparisons; the Unicode case folding algorithm should
    be used if you want to handle languages other than English. But in
    HTML specifically, tag names only use the ASCII characters where
    this test is sufficient.
    
[case-hard]: https://www.b-list.org/weblog/2018/nov/26/case/


```
[<!DOCTYPE html>]
```

[html5-doctype]: https://html.spec.whatwg.org/multipage/syntax.html#the-doctype

This is a special element called a [doctype][html5-doctype], and it's
not supposed to have a close tag either. But we can't mark it a
self-closing tag—it's always the very first thing in the document, so
there wouldn't be an open element to append it to. And it isn't an
element anyway; it's a bit of syntax that tells you that you're
parsing an HTML document. Best to throw it away:

``` {.python indent=8}
elif tok.tag.split()[0].lower() == "!doctype":
    continue
```

Now we have a new problem: a crash when a text node appears without
any currently open elements; this text node is the newline between
`<!DOCTYPE html>` and `<html>` in the HTML source:

``` {.html}
<!DOCTYPE html>
<html>
...
```

This is kind of a silly issue. It's white space, and it doesn't
matter, after all. Let's hand it by simply skipping text nodes when
there aren't any currently-open elements:

``` {.python indent=8}
if isinstance(tok, Text):
    node = TextNode(tok.text)
    if not currently_open: continue
    currently_open[-1].children.append(node)
```

Now a tree is successfully generated and returned from our parser for
this (and many other) web pages!

::: {.further}

:::


Layout from a tree
==================

Now that we can turn a token list into an element tree, `Layout` ought
to operate on element trees too. Let's add a `layout` method to
replace the current `for` loop inside the constructor. To start, we
can just call `token` twice per element node, emulating the old
token-based layout:

``` {.python indent=4}
def layout(self, tree):
    if isinstance(tree, TextNode):
        self.text(tree.text)
    else:
        self.token(Tag(tree.tag))
        for child in tree.children:
            self.layout(child)
        self.token(Tag("/" + tree.tag))
```

This works

One complication is `layout`'s local variables: the current `x` and `y`
position, the current `bold` and `italic` state, and even that tricky
`terminal_space` variable that took up so much time in the last chapter.
Plus, there's the `display_list` variable for render commands. To turn
`layout` into a recursive function, we'll need those local variables to
become global state that multiple invocations of `layout` can share:[^6]

``` {.python}
class State:
    def __init__(self):
        self.x = 13
        self.y = 13
        self.bold = False
        self.italic = False
        self.terminal_space = True
        self.dl = []

state = State()
```

The local variable `x` is now replaced by the field `state.x`.

The the pieces of the old `layout` function must now migrate to
`layout_open`, `layout_close`, and `layout_text`. For example,
`layout_open` needs to set the bold and italics flags.

``` {.python}
def layout_open(node):
    if node.tag == "b":
        state.bold = True
    elif node.tag == "i":
        state.italic = True
```

The new `layout_close` will be pretty similar (unsetting the flags),
while `layout_text` will do the line wrapping and terminal space
computations from the last chapter.

Finally, don't forget to update `show` to get its display list from
inside `state`.

``` {.python}
layout(nodes)
display_list = state.display_list
```


Handling author errors
======================

So far, the HTML parser does confusing, sort-of arbitrary things when
tags are left unclosed, or when the wrong tag is closed in the wrong
order. Real HTML documents usually have all sorts of mistakes like that,
so real HTML parsers try to guess what the author meant and somehow
return a tree anyway.[^3]

For example, some HTML tags serve as both an open and a close tag (they
are called self-closing tags). The `<br>` tag, which inserts a line
break, is one such tag. However, right now, our parser doesn't know
that, and will just keep looking for a `</br>` tag that never
arrives.[^4]

To support self-closing tags, we just need to modify the part of the
parser that creates a new node, which reads:

``` {.python}
new = ElementNode(current, tok.tag)
if current is not None: current.children.append(new)
current = new
```

Here, the first line creates the element and the second makes it a child
of its parent. Then, the third one "enters" the new node, in effect
opening it. For a self-closing tag, we just need to avoid doing that:

``` {.python}
if new.tag != "br":
    current = new
```

Now is a good time, by the way, to implement `<br>` in `layout`; it
works pretty much the same way that `<p>` does, ending the current line
by resetting `x` and incrementing `y`.

Self-closing tags aren't supposed to have close tags; but sometimes
people forget close tags for elements that really should have them. For
example, you might have a `<p>` inside a `<section>` and then close the
`</section>` without closing the `</p>`. Because these errors are so
common, browsers try to automatically fix them so they do the "right
thing". The full algorithm is pretty complicated (there are multiple
types of tags and so on) but let's implement a simple version of it:
when a close tag is encountered, we will walk up the tree until we find
a tag that it closes.

``` {.python}
tagname = tok.tag[1:]
node = current
while node is not None and node.tag != tagname:
    node = node.parent
```

Here, we start by taking `tok.tag` and stripping off the initial slash.
Then, we walk up the tree of nodes until we find a node with a matching
tag. Once we're done with the loop, there are two cases: either we
found a matching node (in which case we set `current` to its parent) or
we didn't (in which case we assume it's a typo and you meant to close
the current tag).

``` {.python}
if node:
    current = node

if current.parent is not None:
    current = current.parent
```

There's also a chance that the page author forgot to close the tags
they opened. In that case we want to implicitly close the remaining open
tags. That takes a loop just before the return statement.

``` {.python}
while current.parent:
    current = current.parent
```

These rules for malformed HTML may seem arbitrary, and they are. But
they evolved over years of trying to guess what people "meant" when
they wrote that HTML, and are now codified in the [HTML 5 parsing
algorithm](https://www.w3.org/TR/2011/WD-html5-20110113/parsing.html),
which spells out in detail how to handle user errors. The tweaks above
are much more limited, but give you some sense of what the full
algorithm is like.

Debugging your parser
=====================

Parsers are frequently buggy, and annoying to debug. So before we go
further, let's make sure the parser works correctly. Let's start by
making it easy to print the parsed HTML tree:

``` {.python}
def print_tree(node, indent="-"):
    if isinstance(node, ElementNode):
        print(indent, "<{}>".format(node.tag))
        for child in node.children:
            print_tree(child, "  " + indent)
    elif isinstance(node, TextNode):
        print(indent, "\"{}\"".format(node.text))
    else:
        raise ValueError("Unknown node type", node)
```

Now it's easy to see the result of parsing an HTML document:

``` {.python}
print_tree(parse(lex(" ... ")))
```

Make sure to try this for several documents. Try documents without
text, or without tags; documents without close tags; documents with
extra whitespace before or after the root element; and so on. Most
likely, you'll find incorrect results or crashes.

When you do, the best way to get more insight is to print the state of
the parse---the current element and current token---at every parsing
step. Walking through the output by hand will reveal a mistake. It is
a slow but a sure process.


HTML attributes
===============

HTML tags have tag names but also *attributes*, which are added to an
open tag to give additional information about that element. For example,
the `lang` attribute tells you what language the text in that element is
in, while the `href` attribute on `a` tags gives the URL that the link
points to.[^5] Attributes look like this:

``` {.example}
<tagname attrname=attrvalue attrname=attrvalue>
```

You can have any number of attributes in an open tag; the names are
case-insensitive, while the values are an arbitrary string of character
that can even include spaces if you surround them with quotes. Also, the
values are optional; "`<tagname attrname>`" is perfectly valid and
sets that attribute to an empty string.

Let's extend `ElementNode` to store attributes:

``` {.python}
class ElementNode:
    def __init__(self, parent, tagname):
        # ...
        self.attributes = {}
```

The `tagname` passed into the `ElementNode` constructor contains both
the tag name and all the attributes. A quick and dirty way to separate
them is to split on whitespace:

``` {.python}
self.tag, *attrs = tagname.split(" ")
```

This syntax tells Python to split `tagname` on whitespace and to store
the first bit into `self.tag` while the rest are collected into the list
`attrs`. Now, we can go through `attrs` extracting each attribute-value
pair:

``` {.python}
for attr in attrs:
    out = attr.split("=", 1)
    name = out[0]
    val = out[1].strip("\"") if len(out) > 1 else ""
    self.attributes[name.lower()] = val
```

Here the attribute name is split from the attribute value by looking for
the first equal sign, and then if the value has quotes on either side,
those are stripped off. The name is made lowercase before adding it to
`self.attributes` because attribute names are case-insensitive.


Summary
=======

In this chapter, we taught our browser to understand HTML as a
structured tree, not just a flat list of tokens, and we've updated
layout to be a recursive tree traversal instead of a linear pass through
the document. We've also made the browser much more robust to malformed
HTML. While these changes don't have much impact yet, this new,
structured understanding of HTML sets us up to implement a layout
engine in the next chapter.


Exercises
=========

-   HTML documents almost always start with "doctype declarations". These
    look like tags that begin with `!doctype` and don't have close
    tags. Doctype declarations, when they are present, are always the
    first token in a document. Skip doctype declarations in the parser.
-   Update the HTML lexer and parser to support comments. Comments in
    HTML begin with `<!--` and end with `-->`. However, comments aren't
    the same as tags: they can contain any text, including open or close
    tags. Comments should be a new token type, which `parse` should
    ignore.
-   Update the HTML lexer or parser to support *entities*. Entities in
    HTML begin an ampersand `&`, then contain letters and numbers, and
    end with a semicolon "`;`"; they resolve to particular characters.
    Implement support for `&amp;`, `&lt;`, `&gt;`, and `&quot;`, which
    expand to ampersand, less than, greater than, and the quotation
    mark. Should you handle entities in the lexer, the parser, or in an
    earlier pass? Consider that attribute values can contain entities.
-   For some tags, it doesn't make sense to have one inside the other.
    For example, it's not clear what it would mean for one paragraph to
    contain another, so the most common reason for this to happen in a
    web page is that someone forgot a close tag. Change the parser so
    that a document like `<p>hello<p>world</p>` results in two sibling
    nodes instead of one paragraph inside another.
-   The attribute parser doesn't correctly handle attribute values
    that contain spaces, which is valid when the attribute is quoted.
    Fix this case in the attribute parser. You will likely need to
    loop over the attribute character-by-character.

[^3]: Yes, it's a crazy system, and for a few years in the early '00s
    the W3C tried to [do away with it](https://www.w3.org/TR/xhtml1/).
    They failed.

[^4]: Some people put a slash at the end of a self-closing tag (like
    `<br/>`) but they don't have to: `<br>` is self-closing with and
    without that slash.

[^5]: Where `href` stands for "hypertext reference".

[^6]: If you implemented earlier exercises like support for `<a>`,
    `<small>`, and `<big>`, you will likely have more parts to the
    state.
