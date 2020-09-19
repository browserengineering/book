---
title: Constructing a Document Tree
chapter: 4
prev: text
next: layout
...

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

Self-closing tags
=================

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

Why aren't these open elements closed?[^4] Well, most of them (like
`<meta>` and `<link>`) are what are called self-closing: they don't
need a close tag because they never surround content. Let's add a case
for that to our parser:

[^4]: Some people put a slash at the end of a self-closing tag (like
    `<br/>`) but they don't have to: `<br>` is self-closing both with
    and without that slash.

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
        return self.tag.lower() in SELF_CLOSING_ELTS
```

Note that I'm doing a case-insensitive comparison[^case-insensitive]
of the tag name, and furthermore that I'm ignoring an attributes like
in the `meta` and `link` tags above.

::: {.further}
This is [not the right way][case-hard] to do case
insensitive comparisons; the Unicode case folding algorithm should be
used if you want to handle languages other than English. But in HTML
specifically, tag names only use the ASCII characters where this test
is sufficient.
:::
    
[case-hard]: https://www.b-list.org/weblog/2018/nov/26/case/

Attributes
==========

Try the code with self-closing elements again. It didn't help. Why?
Well, because the self closing tags in question look like this:

``` {.html}
<meta charset="utf-8" />
```

But we're comparing them to just `meta`. What gives? Well, HTML tags
have not only names but also *attributes*, which give additional
information about that element. For example, in `meta` the `charset`
attribute tells you what character encoding to use on this web page.

An open tag any number of attributes, and a close tag cannot have any.
The attribute names are case-insensitive, while the attribute values
are an arbitrary string of characters terminated by a space, or an
arbitrary string of characters including spaces if they are surrounded
in quotes. Also, the values are optional; they default to an empty
string.

We need to handle attributes to get this page parsing. Since they
appear in tags, we'll add them to the lexer. First, let's extend `Tag`
to store attributes:

``` {.python}
class Tag:
    def __init__(self, tag):
        # ...
        self.attributes = {}
```

Filling those attributes in, however, will be a challenge. Right now,
`lex` contains two pieces of state: `text`, which is whatever will go
inside the next token it outputs, and `in_tag`, which indicates
whether that token will be a tag or a text token. Now, with
attributes, there are more options: the lexer can be reading some
text, reading a tag name, reading an attribute name, reading an
unquoted attribute value, or reading a quoted attribute value. Plus,
it might have a `Tag` in progress. Let's add new variables to `lex` to
reflect this:

``` {.python}
def lex(body):
    out = []
    text = ""
    state = "text"
    current_tag = None
    current_attribute = ""
    for c in body:
        # ...
```

The new `current_tag` variable stores any in-progress `Tag` element,
and likewise `current_attribute` will be useful when we're handling
attributes. Meanwhile, the new `state` variable tracks what the lexer
is currently doing, replacing the old `in_tag` variable. The behavior
of the lexer will be different in different states. In the `text`
state, it just collects characters until it reaches an open angle
bracket:

``` {.python indent=8}
if state == "text":
    if c == "<":
        if text: out.append(Text(text))
        text = ""
        state = "tagname"
    else:
        text += c
```

Note that the open angle bracket changes the `state` variable to
indicate that it is now planning to read a tag name.[^state-machine]
So how does the lexer handle tag names?


[^state-machine]: This is called a "state machine".

``` {.python indent=8}
elif state == "tagname":
    if c == ">":
        out.append(Tag(text))
        text = ""
        state = "text"
    elif c.isspace():
        current_tag = Tag(text)
        text = ""
        state = "attribute"
    else:
        text += c
```

With a tag name, both right angle brackets (ends the tag) and white
space (ends the tag name but not yet the tag) are special. Ending the
tag puts us back in the `text` state, but if the tag name ends without
ending the tag, the lexer waits for attributes. Attributes have lots
of special characters; while reading an attribute, you might see:

1. An equal sign, in which case the attribute is done and you should
   now read a value;
2. Whitespace, which ends means the attribute you're reading needs to
   be added to the tag with the default value;
3. A right angle bracket, which also means the attribute is done and
   has its default value but also ends the tag;
4. Some other text, which I guess is part of the attribute.

Four cases! This one is a doozy:

``` {.python indent=8}
elif state == "attribute":
    if c == "=":
        current_attribute = text.lower()
        text = ""
        state = "value"
    elif c.isspace():
        if text: current_tag.attributes[text.lower()] = ""
        text = ""
    elif c == ">":
        if text: current_tag.attributes[text.lower()] = ""
        text = ""
        out.append(current_tag)
        current_tag = None
        state = "text"
    else:
        text += c
```

Note that attributes are also case-insensitive, so we always
lower-case them before adding them to the tag. Now there's a `value`
state to handle. Values come in two types: quoted and unquoted. So the
quote character is special in values:

``` {.python indent=8}
elif state == "value":
    if c == "\"":
        state = "quoted"
    elif c.isspace():
        current_tag.attributes[current_attribute] = text
        text = ""
        current_attribute = ""
        state = "attribute"
    else:
        text += c
```

Now there's a quoted value case! These new states are getting tedious,
but luckily this is the very last one:

``` {.python indent=8}
elif state == "quoted":
    if c == "\"":
        state = "value"
    else:
        text += c
```

It's worth thinking about how quotes work. Quotes don't appear in
attribute values (because the lexer doesn't add them to `text`);
instead, they only move the lexer between the `value` and `quoted`
states. And those states are basically the same, except for how they
handle whitespace!

At the end of the big `for` loop in `lex`, we still need to handle
unclosed tags:

``` {.python indent=4}
if state == "text" and text:
    out.append(Text(text))
```

When you're writing this sort of code, it's very easy to misspell a
state name at some point, so it's also helpful to add some error
checking code at the end:

``` {.python indent=8}
else:
    raise Exception("Unknown state " + state)
```

If you've done things correctly, this should never be triggered. If
you have a typo… well, then I recommend printing all of the local
variables and the current character at the top of the `for` loop, and
stepping through the printed output very carefully.

::: {.further}
Something about state machines with auxiliary state?
:::

Doctype declarations
====================

Now that our lexer handles attributes correctly, the tag names of
elements are correctly determined, so self-closing elements are
handled correctly and the list of open elements when parsing this page
is now shorter:

```
[<!DOCTYPE>]
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

This works! Our parser converts this web page to a tree!

Now our browser should *use* this element tree. Let's add a `layout`
method to replace the current `for` loop inside the constructor. To
start, we can just call `token` twice per element node, emulating the
old token-based layout:

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

This works but it's a little ridiculous. We've gone through all this
effort to construct a tree, and now we're just emulating tokens? It's
now a little clearer that the old `token` function had three different
parts to it:

- The part that handled `Text` tokens, which now isn't being used;
- The part that handled start tags; and
- The part that handled end tags.

Let's split `token` into two functions, then, `open` and `close`:

``` {.python indent=4}
def open(self, tag):
    if tag == "i":
        self.style = "italic"
    # ...

def close(self, tag):
    if tag == "i":
        self.style = "roman"
    # ...
```

Make sure to update `layout` to call these two new functions; now it
no longer has to construct `Tag` objects or add slashes to things to
indicate a close tag!

::: {.further}
Document type declarations are a holdover from [SGML][sgml], the
80s-era precursor to XML, and originally included a URL pointing to a
full definition of the SGML variant you were using, which is no
longer necessary. Browsers use the absense of a document type
declaration to identify [older HTML versions][quirks-mode].[^almost-standards-mode]
:::

[sgml]: https://en.wikipedia.org/wiki/Standard_Generalized_Markup_Language
[quirks-mode]: https://developer.mozilla.org/en-US/docs/Web/HTML/Quirks_Mode_and_Standards_Mode
[^almost-standards-mode]: There's also a crazy thing called "[almost
    standards][limited-quirks]" or "limited quirks" mode, due to a
    backwards-incompatible change in table cell vertical layout. Yes.
    I don't need to make these up!
[limited-quirks]: https://hsivonen.fi/doctype/

``` {.python last=True}
```

Handling author errors
======================

The HTML parser does confusing, sort-of arbitrary things when
tags are left unclosed, or when the wrong tag is closed in the wrong
order. Real HTML documents usually have all sorts of mistakes like that,
so real HTML parsers try to guess what the author meant and somehow
return a tree anyway.[^3]

[^3]: Yes, it's a crazy system, and for a few years in the early '00s
    the W3C tried to [do away with it](https://www.w3.org/TR/xhtml1/).
    They failed.

For example, you might have a `<p>` inside a `<section>` and then
close the `</section>` without closing the `</p>`. Because these
errors are so common, browsers try to automatically fix them so they
do the "right thing". The full algorithm is pretty complicated (there
are multiple types of tags and so on) but let's implement a simple
version of it: when a close tag is encountered, we will walk up the
tree until we find a tag that it closes.

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
