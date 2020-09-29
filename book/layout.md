---
title: Laying Out Pages
chapter: 5
prev: html
next: styles
...

So far, layout is a linear process, processing each open tag, text
node, and close tag in order. But web pages are trees not just
syntactically but also visually: borders and backgrounds draw one
element inside another in a way that requires tracking the layout of
parent elements. So this chapter switches to *tree-based layout*,
where the tree of elements is transformed into a tree of *boxes*, each
of which draws a part of the page. In the process, we'll add support
for backgrounds and make our web pages more colorful.

Tree-based layout
=================

The way layout works now, every element is laid out by modifying
global state three times: for the open tag, for each child, and then
for the close tag. While things do get put in the right place, there's
data for the element as a whole (like its height and width) isn't
present, because the element itself is split into independent open and
close tags. That might work for simple layouts, but it's pretty hard
to draw a background without knowing how wide and tall to draw it.

Web browsers actually structure layout differently. In a browser, the
job of layout is to produce a tree, called the *box tree*. Each
element has an associated box[^no-box] and each box has a size and a
position. The layout process is thought of as generating the box tree
from the element tree.

[^no-box]: Well, some elements like `<script>` don't generate boxes,
    and some elements like `<li>` generate multiple, but for most
    elements it's one element one box.
    
Before we jump to code, let's talk through some layout concepts.

First: layout modes. Web pages contain different kinds of things.
We've already talked a lot about [text](text.md), which is laid out
left-to-right in lines[^in-english]. But that text is organized in
paragraphs, which are laid out top-to-bottom, usually with gaps in
between. To account for the difference, browsers have an "inline"
layout mode for things like text and a "block" layout mode for things
like paragraphs. Different layout modes correspond to different types
of boxes. So for example, a document with a heading and two paragraphs
would correspond to a tree like this:

[^in-english]: In European languages. But not universally!

![A tree of boxes. The root is a block for the `<html>` element; it
    has one child, a block for the `<body>` element; it has three
    children, each blocks as well (for the `<h1>` and two `<p>`
    elements); and each of those have a single child, an
    inline.](im/layout-modes.png)

The inline layout mode is effectively what we implemented in [Chapter
3](text.md), so this chapter will be about implementing block layout.

Second: creating this box tree. The current layout algorithm is a
recursive function which (eventually) adds things to a linear
`display_list`. Tree-based layout means the recursive function must
traverse the HTML tree and builds a box tree instead.

Since we have two types of of layout modes, the elements of the box
tree will have one of two types: inline and block boxes. We'll follow
a simple rule, which is that a block box either contains any number of
block boxes, or a single inline box, while inline boxes have no
children. This invariant will make it easier when we're doing layout.

Finally: layout. With the box tree created, how do we compute the size
and position of each box? The general rule is that a block, like a
paragraph, should take up as much horizontal room as it can, and
should be tall enough to contain everything inside it. That means that
a box's width is based on its *parent*'s width, while its *height* is
based on its *children*'s height:

![The flow of information through layout. Width information flows down
    the tree, from parent to child, while height information flows up,
    from child to parent.](im/layout-order.png)

This suggests a step-by-step approach to layout. First, an element
must compute its width, based on its parent's width. That makes it
possible to lay out the children, which comes next. Finally, the
children's heights are now available, so the element's height can be
calculated.

[^and-inlines]: On the web, all boxes have margin, padding, and
    borders, though they work in complicated ways for non-block boxes.
    For simplicity this book only gives block boxes the full box
    model.

Let's now turn these concepts into code.

::: {.further}
Formally, computations on a tree like this can be described by an
[attribute grammar](wiki-atgram). Attribute grammar engines use the
same logic we used above to determine the right order to calculate
each attribute.
:::

[wiki-atgram]: https://en.wikipedia.org/wiki/Attribute_grammar

Layout modes
============

Let's start with the scaffolding for layout modes. We'll have two,
block and inline layout, and since what we've written now is basically
inline layout let's rename `Layout` to `InlineLayout` and add a new
`BlockLayout` class:

``` {.python}
class InlineLayout:
    # ...

class BlockLayout:
    # ...
```

These layout objects will be the nodes of the box tree, and in fact
some browsers call it a layout tree. To make it a tree, we'll want
both types of layout objects to know their children, their parent, and
the HTML element they correspond to:

``` {.python}
def __init__(self, node, parent):
    self.node = node
    self.parent = parent
    self.children = []
    # ...
```

The `InlineLayout` constructor also sets up the `weight`, `style`,
`size`, `x`, and `y`; plus, the constructor calls the `recurse` method
to do the actual layout. It'll be convenient to trigger layout
separately from constructing the box tree itself, so let's move all of
that—setting the field values, calling `recurse`—to a new method:

``` {.python}
def layout(self):
    self.display_list = []

    self.x = HSTEP
    self.y = VSTEP
    self.weight = "normal"
    self.style = "roman"
    self.size = 16

    self.line = []
    self.recurse(node)
    self.flush()
```

The `BlockLayout` class will need the same structure:

``` {.python}
def BlockLayout:
    def __init__(self, node, parent):
        self.node = node
        self.parent = parent
        self.children = []

    def layout(self):
        pass
```

With the two layout modes now drafted, the next step is to construct a
whole tree of these things.

Creating the box tree
=====================

The first job of the `layout` method is to create the child layout
objects. For `InlineLayout` that's already done, so let's focus on
`BlockLayout`.

Usually, a block box has one block child per child in the element
tree. But not always! When you get to something like a paragraph, the
children are like text, so the child layout object is a single inline
layout box. We can tell the difference by examining the children of
the node we are laying out: some elements are only used inside running
text, other elements are only used as blocks:

``` {.python}
INLINE_ELEMENTS = [
    "a", "em", "strong", "small", "s", "cite", "q", "dfn", "abbr",
    "ruby", "rt", "rp", "data", "time", "code", "var", "samp", "kbd",
    "sub", "sup", "i", "b", "u", "mark", "bdi", "bdo", "span", "br",
    "wbr", "big"
]
```

A block box has can look at its children's types and tags to determine
whether it should have block or inline contents:

```
def has_block_children(self):
    for child in self.node.children:
        if isinstance(child, TextNode):
            if not child.text.isspace():
                return False
        elif child.tag in INLINE_ELEMENTS:
            return False
    return True
```

The `layout` method can use this to create child layout objects:

``` {.python}
def layout(self):
    if self.has_block_children():
        for child in self.node.children:
            if isinstance(child, TextNode): continue
            self.children.append(BlockLayout(child, self))
    else:
        self.children.append(InlineLayout(self.node, self))
```

One final nit: what forms the root of this box tree? Since both
`BlockLayout` and `InlineLayout` require a parent in their
constructor, we need another layout object at the root. Since I think
of that root as the page itself, let's call it `PageLayout`:

``` {.python}
class PageLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.children = []

    def layout(self):
        child = BlockLayout(self.node, self)
        self.children.append(child)
```

To summarize the rules of box tree creation:

1. The root of the box tree is always a `PageLayout`.
2. Its first child is always a `BlockLayout`.
3. Each `BlockLayout` either contains all `BlockLayout` children, or a
   single `InlineLayout`.
4. An `InlineLayout` doesn't have children.

With the box tree set up, let's move on to laying out each box in the
tree.

Computing size and position
===========================

The general structure of layout is clear: each box computes its width,
then lays out its children, and then computes its height. Besides
width and height, we also need to position each element. This is
tricky, because if you have several paragraphs, the position of the
second depends on the height of the first. I'll use the rule that each
element it positioned by its parent before its own `layout` method is
called.

For the width, the idea is that a paragraph or header or something
like that should take up all the horizontal space it can. So it should
use the parent's width:

``` {.python}
self.w = self.parent.w
```

Then, each of the children need to be laid out. That means each child
has to be positioned, and then its `layout` method must be called:

``` {.python expected=True}
y = self.y
for child in self.children:
    child.pos = (self.x, y)
    child.layout()
    y += child.h
```

Finally, the height of an element has to encompass all its children.
We conveniently already added all the children's heights into `y`, so
we can just subtract its starting value:

``` {.python}
self.h = y - self.y
```

That settles the matter in `BlockLayout`; let's turn our attention to
`InlineLayout`. Its `layout` method needs to set up the same `w`, `h`;
it doesn't need to assign `pos` for any children since inline boxes
don't have any children:

``` {.python}
class InlineLayout:
    def layout(self):
        self.w = self.parent.w
        # ...
        self.h = self.y - self.parent.y
```

Note that in `InlineLayout` the `x` and `y` fields mark the location
of the next word, not the position of the box itself.

Finally even `PageLayout` needs some layout code, though since the
page is always in the same place it's pretty simple:

``` {.python}
class PageLayout:
    def layout(self):
        self.w = WIDTH
        child.pos = self.pos = (0, 0)
        child.layout()
        self.h = child.h
```

To summarize the rules of layout computation:

1. Before a box is laid out, its parent must set its `pos` field.
2. When a box is laid out, it must first compute its `w` field.
3. Next, the box must lay out its children, which requires setting
   their `pos` fields and then calling their `layout` methods.
4. Finally, the box must set its `h` field.

Using tree-based layout
=======================

With tree-based layout implemented, let's use it in the browser
itself, in its `layout` method. First, we need to create the box tree
and lay it out:

``` {.python}
class Browser:
    def layout(self, tree):
        page = PageLayout(tree)
        page.layout()
```

Once the page is laid out, it must be drawn, which means first
collecting a display list of things to draw and then calling
`self.render()` to actually draw those things.

To collect the display list itself, we'll need to recurse down the
tree; I think it's most convenient to do that by adding a `draw`
function to each box type which does the recursion. A neat trick when
accumulating a list like this is to pass the list itself in as an
argument, and have the method just append to that list instead of
returning anything. For `PageLayout`, which only has one child, it
looks like this:

``` {.python}
class PageLayout:
    def draw(self, to):
        self.children[0].draw(to)
```

For `BlockLayout`, which has multiple, `draw` is called on each child::

``` {.python}
class BlockLayout:
    def draw(self, to):
        for child in self.children:
            child.draw(to)
```

Finally, `InlineLayout` is already storing things to draw in its
`display_list` variable, so we can copy them over:

``` {.python}
class InlineLayout:
    def draw(self, to):
        to.extend(self.display_list)
```

Now the browser can use draw to collect its own `display_list`
variable:

``` {.python}
class Browser:
    def layout(self, tree):
        # ...
        self.display_list = []
        page.draw(self.display_list)
        self.render()
```

And since we're already working on `Browser`, let's add one more
feature, made possible by tree-based layout. The overall height of the
page content is now available in `page.h`; let's use that to avoid
scrolling past the bottom of the page. First, we'll need to store it
in `layout`:

``` {.python}
class Browser:
    def layout(self, tree):
        # ...
        self.page_h = page.h
```

Then the `scrolldown` hander should make sure you can't go past it:

``` {.python last=True}
class Browser:
    def scrolldown(self, e):
        self.scroll = min(self.scroll + SCROLL_STEP, self.page_h - HEIGHT)
        self.render()
```

Try it out—your browser should now work, all using the fancy new
tree-based layout algorithm! I recommend taking this moment to debug:
tree-based layout is powerful but complex. Adding more features, as
we're about to do, leverages the power but adds to the complexity, so
it's good to have stable foundations before we move on to that.

Backgrounds
===========

Tree-based layout gives every block box a size and position. We'll end
up using this capability for a lot of different things (dispatching
clicks, for example), but for now let's use it for something simple
and visually compelling: background colors.

To draw backgrounds for the elements on the page, we'll need to draw
rectangles on our canvas, and to draw something on the canvas we first
need to put it in the display list. Right now, the display list only
contains text to draw—that's going to have to change. Conceptually,
the display list contains *commands*, so let's have two types of
commands, for text and for rectangles:

``` {.python}
class DrawText:
    def __init__(self, x1, y1, text, font):
        self.x1 = x1
        self.y1 = y1
        self.text = text
        self.font = font
    
class DrawRect:
    def __init__(self, x1, y1, x2, y2, color):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.color = color
```

Now `InlineLayout` needs to add `DrawText` objects to the display
list:

``` {.python}
class InlineLayout:
    def draw(self, to):
        for x, y, word, font in self.display_list:
            to.append(DrawText(x, y, word, font)
```

Meanwhile block boxes can add backgrounds by adding `DrawRect`
commands. I'm going to add a gray background to `pre` tags, which
surround code snippets:

``` {.python}
class BlockLayout:
    def draw(self, to):
        if self.node.tag == "pre":
            x1, y1 = self.pos
            x2, y2 = x + self.w, y + self.h
            to.append(DrawRect(x, y, x2, y2, "gray"))
        # ...
```

Note that this code has to come *before* we call `draw` on the child
layout objects, because the background has to be drawn *before* the
text inside the element, lest the background obscure the
text.

Once graphics commands are on the display list, we need to run them on
our actual canvas. Let's do this with a `draw` method. On `DrawText`
it's just a call to `create_text`:

``` {.python}
class DrawText:
    def draw(self, scroll, canvas):
        canvas.create_text(
            self.x1, self.y1 - scroll,
            text=self.text,
            font=self.font,
            anchor='nw',
        )
```

In `DrawRect` it calls `create_rectangle`. Remember to pass `width=0`,
because by default `create_rectangle` draws a one-pixel black border:

``` {.python}

class DrawRect:
    def draw(self, scroll, canvas):
        canvas.create_rectangle(
            self.x1, self.y1 - scroll,
            self.x2, self.y2 - scroll,
            width=0,
            fill="black",
        )
```

We do still want to clip out graphics commands that only occur
offscreen. For a rectangle, that means testing `y1` and `y2`; let's
just add those fields to `DrawText`:

``` {.python}
def __init__(self, x1, y1, text, font):
    # ...
    self.x2 = x1 + font.measure(text)
    self.y2 = y1 + font.metrics("linespace")
```

::: {.quirks}
On some systems, the `measure` and `metrics` commands are awfully
slow. Adding two more calls to those methods, as here, would only make
things slower.

Luckily, these two calls aren't necessary; the `measure` call
duplicates an equivalent call in `InlineLayout.text`, while the
`metrics` call duplicates a call in `InlineLayout.flush`. If you're
careful you can pass the results of those calls all the way into
`DrawText`.
:::

Since all the drawing logic is now in the drawing commands themselves,
the browser's `render` method just needs to determine which commands
to execute, and then call their `draw` method.

``` {.python}
    def render(self):
        self.canvas.delete("all")
        for cmd in self.display_list:
            if cmd.y1 > self.scroll + HEIGHT: continue
            if cmd.y2 < self.scroll: continue
            cmd.draw(self.scroll, self.canvas)
```

Try it on this page, which has lots of code snippets; each should now
have a gray background. By the way, we not only have access to the
height of any element, but also the height of the whole page. We can
use that to stop the user from scrolling past the bottom of the page.
In `layout`, store the height in a `max_y` variable:

``` {.python}
def layout(self, tree):
    # ...
    self.max_y = page.h
```

Then, when the user scrolls down, don't let them scroll past the
bottom of the page:

``` {.python}
def scrolldown(self, e):
    self.scroll = min(self.scroll + SCROLL_STEP, self.max_y)
    self.render()
```

Summary
=======

In this chapter, we did a pretty dramatic rewrite of the layout
portion of our browser. We\'ve split layout into two different *layout
modes* for block and inline content, and we\'ve extended the styling
capabilities of our browser by adding margins, border, and padding.

Exercises
=========

-   Remove the magic numbers from the `Page` object by instead assigning
    padding to the `<body>` element
-   Add bullets to list items, which in HTML are `<li>` tags. You can
    make them little squares, located to the left of the list item
    itself.
-   Add support for background colors and border colors. Code blocks
    (`<pre>` tags) should have light-gray background color, while
    headings (`<h2>` tags) should have light-gray bottom borders, or
    some other colors you like better. Make sure background colors are
    located behind the text, not in front of it!
-   Implement *margin collapsing*. In margin collapsing, when one block
    has a bottom margin and the next block has a top margin, the actual
    gap between them is the *larger* of the two margins, not their sum.
-   Extend margin collapsing to allow the top (bottom) margin of an
    element to overlap with the top (bottom) margin of its first
    (last) child, as long as it has no top (bottom) border or padding.
