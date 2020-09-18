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

Right now, our browser understands web pages as a flat sequence of tags
and text. HTML more structure than this: each open tag has a
corresponding close tag, and the stuff between those two is
"contained" within that tag. Every open tag must be closed before
closing its parent.

So, the tags form a tree, and every pair of open and close tags forms a
node of that tree. Of course, the tree also has to contain another kind
of node: text. We call the two types of nodes *element nodes* and *text
nodes*; there isn't additional structure besides those two.[^1] Here's
a data structure for these two types:[^2]

``` {.python}
class ElementNode:
    def __init__(self, parent, tagname):
        self.tag = tagname
        self.children = []
        self.parent = parent

class TextNode:
    def __init__(self, parent, text):
        self.text = text
        self.parent = parent
```

We need to create these `Node` structures from the list of tokens. The
overall idea is pretty simple. Keep track of the node that we're
currently in. When we see an open tag, create a new node and go into it;
when we see a close tag, go back out to its parent. The current node
will start out with a dummy value:

``` {.python}
current = None
for tok in tokens:
    # ...
return current
```

In that look, we need to figure out if the token is text, an open tag,
or a close tag, and do the appropriate thing. `Text` tokens are the
easiest:

``` {.python}
new = TextNode(current, tok.text)
current.children.append(new)
```

For `Tag` tokens, we check whether the tag starts with a slash to
determine whether it's an open or a close tag. For open tags, we create
a new `ElementNode`, make it a child of the current node, and then make
the new node current:

``` {.python}
new = ElementNode(current, tok.tag)
if current is not None: current.children.append(new)
current = new
```

Finally, close tags exit from the current node to its parent:

``` {.python}
if current.parent is not None:
    current = current.parent
```

Here I'm testing `current.parent` because of a subtlety with the root
of the tree. The first thing in an HTML document is always the `<html>`
open tag, so it's safe to start `current` with the dummy value `None`:
it'll immediately be replaced by an `ElementNode`. But then when we
reach the `</html>` close tag, we don't want to walk up to the parent,
which would cause `current` to take on that dummy `None` value again: if
that happened, we wouldn't be able to get back to the nodes we just
created! So instead I do nothing, so that moments later we exit the
`for` loop and return the nodes we've created.


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


Layout from a tree
==================

Now that we can turn a token list into an element tree, `layout` ought
to operate on element trees. Since trees have a recusive structure,
`layout` must become a recursive function, changing its single `for`
loop into recursive invocations of `layout`. The new `layout` will need
to:

1.  Update the state, using the rules for start tags
2.  Recursively call `layout` for each child
3.  Update the state, using the rules for close tags
4.  Handle text nodes separately

That suggests an implementation like this:

``` {.python}
def layout(node):
    if isinstance(node, ElementNode):
        layout_open(node)
        for child in node.children:
            layout(child)
        layout_close(node)
    else:
        layout_text(node)
```

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

[^1]: To be clear: there is additional structure, we're just ignoring
    it for now.

[^2]: Tracking the parent like I'm doing here is going to be useful for
    parsing.

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
