---
title: Laying Out Pages
chapter: 5
prev: html
next: styles
...

So far, layout is a linear process, processing each open tag, text
node, and close tag in order. But web pages are trees, and not just
syntactically: elements with borders or backgrounds clearly nest
inside one another. So this chapter switches to *tree-based layout*,
where the tree of elements is transformed into a tree of *layout
objects*, each of which draws a part of the page. In the process,
we'll add support for backgrounds to make our web pages more colorful.

Tree-based layout
=================

The way our browser works now, every element is laid out by modifying
global state for the open tag, for each child, and then once more for
the close tag. Information about the element as a whole, like its
width and height, isn't computed because the element's layout is split
between its open and close tags. While things do get put in the right
place, it's pretty hard to draw a background without knowing how wide
and tall to draw it.

So web browsers structure layout differently. In a browser, layout
produces a *layout tree* of layout object associated with the HTML
elements[^no-box]. Each layout object of those has a size and a
position, and the layout process is thought of as generating the
layout tree and then computing those sizes and positions.

[^no-box]: Some elements like `<script>` don't generate layout
    objects, and some elements like `<li>` generate multiple (one for
    the bullet point!), but for most elements it's one element one
    layout object.
    
Before we jump to code, let's talk through some layout concepts.

First: layout modes. Web pages contain different kinds of things.
We've already talked a lot about [text](text.md), which is laid out
left-to-right in lines[^in-english]. But that text is organized in
paragraphs, which are laid out top-to-bottom with gaps in between.
Indeed, browsers have an "inline" layout mode for things like text and
a "block" layout mode for things like paragraphs. Different layout
modes compute sizes and positions differently.

The inline layout mode is effectively what we implemented in [Chapter
3](text.md), so this chapter will mostly be implementing block layout.

Second: the layout tree. Tree-based layout starts by recursively
traversing the HTML tree to build the layout tree. With two layout
modes, the layout objects will have one of two types: inline and
block.

We'll follow a simple rule, which is that a block layout either
contains any number of blocks, or a single inline, while inline layout
has no children. So for example, a document with a heading and two
paragraphs would correspond to a tree like this:

[^in-english]: In European languages. But not universally!

![A tree of layout objects. The root is a block for the `<html>`
    element; it has one child, a block for the `<body>` element; it
    has three children, each blocks as well (for the `<h1>` and two
    `<p>` elements); and each of those have a single child, an
    inline.](/im/layout-modes.png)

Finally: layout. With the layout tree created, how do we compute the
size and position of each layout object? The general rule is that a
block, like a paragraph, should take up as much horizontal room as it
can, and should be tall enough to contain everything inside it. That
means that a layout objects's width is based on its *parent*'s width,
while its *height* is based on its *children*'s height:

![The flow of information through layout. Width information flows down
    the tree, from parent to child, while height information flows up,
    from child to parent.](/im/layout-order.png)

This suggests a step-by-step approach to layout. First, an element
must compute its width, based on its parent's width. That makes it
possible to lay out the children, which comes next. Finally, the
children's heights are now available, so the element's height can be
calculated.

Let's now turn these concepts into code.

::: {.further}
Formally, computations on a tree like this can be
described by an [attribute grammar](wiki-atgram). Attribute grammar
engines analyze dependencies between different attributes to determine
the right order to calculate each attribute.
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

These layout objects will be the nodes of the layout tree, and in fact
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

The `InlineLayout` constructor also initializes `weight`, `style`, and
`size`, as well as `x` and `y`, and it calls `recurse`. Let's move all
that into a `layout` method.

``` {.python expected=False}
def layout(self):
    self.display_list = []

    self.x = HSTEP
    self.y = VSTEP
    self.weight = "normal"
    self.style = "roman"
    self.size = 16

    self.line = []
    self.recurse(self.node)
    self.flush()
```

Besides a node, a parent, and children, each layout object also needs
a size and position, which we'll store in the `w`, `h`, `x`, and `y`
fields:

``` {.python}
def __init__(self, node, parent):
    # ...
    self.x = -1
    self.y = -1
    self.w = -1
    self.h = -1
```

Unfortunately, `InlineLayout` already uses the `x` and `y` fields for
the location of the next word. To avoid a *very* annoying conflict,
let's rename those fields to `cx` and `cy`. Instead of initializing
them to `HSTEP` and `VSTEP`, let's initialize them to `self.x` and
`self.y`, the position of the overall inline layout object:

``` {.python}
def layout(self):
    # ...
    self.cx = self.x
    self.cy = self.y
    # ...
```

**Make sure** to replace `x` and `y` with `cx` and `cy` throughout the
class, lest you run into some difficult-to-diagnose bugs.

::: {.todo}
In retrospect, those should have been named something else from the
beginning.
:::

The `InlineLayout` class can now serve as a model for our second type
of layout object:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent):
        self.node = node
        self.parent = parent
        self.children = []

        self.x = -1
        self.y = -1
        self.w = -1
        self.h = -1

    def layout(self):
        # ...
```

With the two classes drafted, the next step is to build a whole tree
of these layout objects.

Creating the layout tree
========================

The first job of the `layout` method is to create child layout
objects. Let's focus on `BlockLayout`, since `InlineLayout` won't have
children for now.[^but-later]

[^but-later]: Later, in [Chapter 7](chrome.md), we'll make inline
    layouts contain lines, which themselves contain words.

Usually, a block layout has one block child per child in the element
tree. But when you get to something like a paragraph, the children are
like text, so the child layout object is a single inline layout. We
can tell the difference by examining the children of the node we are
laying out: some elements are only used inside running text, other
elements are only used as blocks:

``` {.python}
INLINE_ELEMENTS = [
    "a", "em", "strong", "small", "s", "cite", "q", "dfn", "abbr",
    "ruby", "rt", "rp", "data", "time", "code", "var", "samp",
    "kbd", "sub", "sup", "i", "b", "u", "mark", "bdi", "bdo",
    "span", "br", "wbr", "big"
]
```

A block layout object looks at its children's tags to determine
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

Then `layout` can call `has_block_children` to figure out how to
create child layout objects:

``` {.python indent=4}
def layout(self):
    if self.has_block_children():
        for child in self.node.children:
            if isinstance(child, TextNode): continue
            self.children.append(BlockLayout(child, self))
    else:
        self.children.append(InlineLayout(self.node, self))
```

Note that when each child is created, `self` is passed as the parent.
With the children created, their own `layout` method can be called
recursively to build the tree:

``` {.python}
def layout(self):
    # ...
    for child in self.children:
        child.layout()
```

What sits at the root of the layout tree? Inconveniently, both
`BlockLayout` and `InlineLayout` require a parent node, we need
another kind of layout object at the root. I think of that root as the
document itself, let's call it `DocumentLayout`:

``` {.python}
class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.children = []

    def layout(self):
        child = BlockLayout(self.node, self)
        self.children.append(child)
        child.layout()
```

To summarize the rules of layout tree creation:

1. The root of the layout tree is always a `DocumentLayout`.
2. Its only child is always a `BlockLayout`.
3. Each `BlockLayout` either has multiple `BlockLayout` children, or a
   single `InlineLayout` child.
4. An `InlineLayout` doesn't have children.

Size and position
=================

The layout tree is now made, but the size and position of each layout
object is still left unset. Let's fix that. The general strategy is
clear: each layout object computes its width, then lays out its
children, and then computes its height.

Besides width and height, we also need to position each element. This
is trickier, because if you have several paragraphs, the position of
the second depends on the height of the first. I'll use the rule that
each element it positioned by its parent before its own `layout`
method is called.

Let's start in `BlockLayout`. For the width, the idea is that a
paragraph or header or something like that should take up all the
horizontal space it can. So it should use the parent's width:

``` {.python}
self.w = self.parent.w
```

Then, each of the children need to be laid out. That means each child
has to be positioned, and its `layout` method must be called:

``` {.python indent=8}
y = self.y
for child in self.children:
    child.x = self.x
    child.y = y
    child.layout()
    y += child.h
```

Note that the call to the child's `layout` method not only asks it to
compute its size, but also to build more of the layout tree.

The height of an element must include all its children. Since the
children's heights have already all been summed into `y`, we can just
subtract its starting value to compute the height:

``` {.python}
self.h = y - self.y
```

That settles `BlockLayout`; let's now work on `InlineLayout`. Its `x`
and `y` will be set by its parent, so its `layout` just needs to set
`w` and `h`:

``` {.python}
class InlineLayout:
    def layout(self):
        self.w = self.parent.w
        # ...
        self.h = self.cy - self.y
```

Finally even `DocumentLayout` needs some layout code, though since the
document always starts in the same place it's pretty simple:

``` {.python}
class DocumentLayout:
    def layout(self):
        self.w = WIDTH
        # ...
        child.x = self.x = 0
        child.y = self.y = 0
        child.layout()
        self.h = child.h
```

To summarize the rules of layout computation:

1. Before `layout` is called, the layout object's parent must set its
   `x` and `y` fields.
2. When `layout` is called, it first computes the object's `w` field.
3. Next, the object must lay out its children, which requires setting
   their `x` and `y` fields and calling their `layout` methods.
4. Finally, `layout` must set the object's `h` field.

Using tree-based layout
=======================

With tree-based layout implemented, let's use it in the browser
itself, in its `layout` method. First, we need to create the layout
tree and lay it out:

``` {.python}
class Browser:
    def layout(self, tree):
        document = DocumentLayout(tree)
        document.layout()
```

Once the page is laid out, it must be drawn, which means first
collecting a display list of things to draw and then calling
`self.render()` to actually draw those things. To collect the display
list itself, we'll need to recurse down the tree; I think it's most
convenient to do that by adding a `draw` function to each layout
object which does the recursion.

A neat trick when accumulating a list in a recursive function is to
pass the list itself in as an argument, and have the method just
append to that list instead of returning anything. For
`DocumentLayout`, which only has one child, it looks like this:

``` {.python}
class DocumentLayout:
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

``` {.python expected=False}
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
        document.draw(self.display_list)
        self.render()
```

Check it out: your browser is now using fancy tree-based layout! I
recommend debugging and testing: tree-based layout is powerful but
complex. And we're about to add more features, leveraging the power
but adding complexity. Stable foundations make for comfortable houses.

Backgrounds
===========

Tree-based layout gives every block a size and position. This
capability is essential[^for-what] but this already-complex chapter
demands a simple and visually compelling demonstration: backgrounds.

[^for-what]: For example, in [Chapter 7](chrome.md), we'll figure out
    what link a user clicked on by knowing the size and position of
    each link!

Backgrounds are rectangles, so our first task is to learn to draw
rectangles on the screen. That means first putting rectangles, along
with text, on the display list. Conceptually, the display list
contains *commands*, and we'll have two types of commands:

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

`InlineLayout` adds `DrawText` objects to the display
list:[^why-not-change]

[^why-not-change]: Why not change `display_list` to contain `DrawText`
    commands directly? You could, it would be fine, but this will
    be easier to refactor later.

``` {.python}
class InlineLayout:
    def draw(self, to):
        for x, y, word, font in self.display_list:
            to.append(DrawText(x, y, word, font)
```

Meanwhile `BlockLayout` can draw backgrounds with `DrawRect` commands.
Let's add a gray background to `pre` tags, which contain code:

``` {.python}
class BlockLayout:
    def draw(self, to):
        if self.node.tag == "pre":
            x2, y2 = self.x + self.w, self.y + self.h
            to.append(DrawRect(self.x, self.y, x2, y2, "gray"))
        # ...
```

Make sure this code come *before* recursively calling `draw` on child
layout objects: the background has to be drawn *before* and therefore
*below* the text inside the source block.

The `render` method now needs to run graphics commands on our actual
canvas. Let's do this with a `draw` method for each command. On
`DrawText` it calls to `create_text`:

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

Note that the `draw` command accepts the scroll amount as a parameter;
in effect, we're asking each graphics command to perform coordinate
conversion.

`DrawRect` works the same way, except it calls `create_rectangle`. By
default `create_rectangle` draws a one-pixel black border, so make
sure to pass `width = 0`:

``` {.python}

class DrawRect:
    def draw(self, scroll, canvas):
        canvas.create_rectangle(
            self.x1, self.y1 - scroll,
            self.x2, self.y2 - scroll,
            width=0,
            fill=self.color,
        )
```

We do still want to clip out graphics commands that only occur
offscreen. `DrawRect` already contains a `y2` field we can use, so
let's add the same `DrawText`:

``` {.python}
def __init__(self, x1, y1, text, font):
    # ...
    self.y2 = y1 + font.metrics("linespace")
```

::: {.quirks}
On some systems, the `measure` and `metrics` commands are awfully
slow. Adding another call will make things a lot slower.

Luckily, this `metrics` call duplicates a call in `flush`. If you're
careful you can pass the results of that call to `DrawText` as an
argument.
:::

With the drawing logic now inside the drawing commands themselves,
the browser's `render` method just determines which commands
to call `draw` for:

``` {.python}
def render(self):
    self.canvas.delete("all")
    for cmd in self.display_list:
        if cmd.y1 > self.scroll + HEIGHT: continue
        if cmd.y2 < self.scroll: continue
        cmd.draw(self.scroll, self.canvas)
```

Not only have access to the height of any element, but also of the
whole page. We can use that to stop the user from scrolling past the
bottom of the page. In `layout`, store the height in a `max_y`
variable:

``` {.python}
def layout(self, tree):
    # ...
    self.max_y = document.h
```

Then, when the user scrolls down, don't let them scroll past the
bottom of the page:

``` {.python}
def scrolldown(self, e):
    self.scroll = self.scroll + SCROLL_STEP
    self.scroll = min(self.scroll, self.max_y)
    self.scroll = max(0, self.scroll))
    self.render()
```

Make sure those `max` and `min` happen in the right order!

Summary
=======

This chapter was a dramatic rewrite of your browser's layout engine.
That means:

- Layout is now tree-based and produces a *layout tree*
- Each node in the tree has one of two different *layout modes*
- Each layout object has a size and position computed
- The display list now contains generic commands
- Backgrounds for source code blocks are now drawn.

Tree-based layout makes it possible to dramatically expand our
browser's styling capabilities. We'll work on that in the [next
chapter](styles.md).

Exercises
=========

*Links Bar*: At the top and bottom of each chapter of this book is a
gray bar naming the chapter and offering back and forward links. It is
enclosed in a `<nav class="links">` tag. Have your browser give this
links bar the same light gray background that any other browser does.

*Hidden Head*: There's a good chance your browser is still showing
scripts, styles, and page titles at the top of every page you visit.
Make it so that the `<head>` element and its contents are never
displayed.

*Bullets*: Add bullets to list items, which in HTML are `<li>` tags.
You can make them little squares, located to the left of the list item
itself. Also indent `<li>` elements so the bullets are to the left of
the text of the bullet point.

*Scrollbar*: At the right edge of the screen, draw a blue, rectangular
scrollbar. The ratio of its height to the screen height should be the
same as the ratio of the screen height to the document height, and its
location should reflect the position of the screen within the
document. Hide the scrollbar if the whole document fits onscreen.

*Table of Contents*: This book has a table of contents at the top of
each chapter, enclosed in a `<nav id="toc">` tag, which contains a
list of links. Add the text "Table of Contents", with a gray
background, above that list. Don't modifying the lexer or parser.
