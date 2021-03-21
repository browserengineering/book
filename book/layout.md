---
title: Laying Out Pages
chapter: 5
cur: layout
prev: html
next: styles
...

So far, layout is a linear process, processing each open tag, text
node, and close tag in order. But web pages are trees, and not just
syntactically: elements with borders or backgrounds visually nest
inside one another. So this chapter switches to *tree-based layout*,
where the tree of elements is transformed into a tree of *layout
objects*, each of which draws a part of the page. In the process,
we'll add support for backgrounds to make our web pages more colorful.

The Layout Tree
===============

The way our browser works now, laying out an element involves separate
modifications to global state at the open tag, for each child, and
then once more for the close tag. While this does put things in the
right place, information about the element as a whole, like its width
and height, isn't computed. That makes it pretty hard to draw a
background, without knowing how wide and tall to draw it.

So web browsers structure layout differently. In a browser, layout
produces a *layout tree* of layout objects associated with the HTML
elements.[^no-box] Each of those layout objects has a size and a
position, and the layout process is thought of as generating the
layout tree and then computing those sizes and positions.

[^no-box]: Some elements like `<script>` don't generate layout
    objects, and some elements like `<li>` generate multiple (one for
    the bullet point!), but for most elements it's one element one
    layout object.

For example, consider a web page with a body that contains a heading
and three paragraphs:

<div>
  <iframe src="layout-example.html"
          style="width: 100%; height: 710px; border: 2px solid gray;"></iframe>
  <span style="font-size: 16px">
    This is a real example. Play with it in
    <a href="layout-example.html" target=_blank>another browser tab</a> to see
    how it behaves!
  </span>
</div>

Its layout tree will have a layout object for the top-level `html`
element, a layout object inside that for the body element, and then
one layout object inside that for each heading and paragraph. Each
layout object will store its size and position, so for example if the
body element has a background the body element's size and position can
be used to draw that background.

The layout tree drives the rest of the layout process. The browser
first traverses the HTML tree to create the layout tree. Then it
computes the size and position for each layout object. Finally, each
layout object generates drawing commands which the browser executes
to render the page.

Layout modes
============

Different layout objects lay out their children differently. Some
*container* elements contain text, like the paragraph above, and lay
that text out horizontally in lines. But other elements contain those
containers themselves. In the example above, the body element contains
a heading and some paragraphs, which are themselves containers for
text. Those containers are stacked vertically, from top to bottom.
Abstracting a bit, there are two *layout modes* here, two ways an
element can be laid out relative to its children.[^or-equivalently]
They're called block layout, for laying out containers, and inline
layout, for laying out text.

In the example above the body element is in block layout mode (because
its children are containers) while the paragraphs and heading are in
inline layout mode (because their children are text). In real browsers
there are a lot of other layout modes too, but in this chapter we'll
keep it simple.

[^or-equivalently]: Or, equivalently, how an element is laid out
relative to its siblings and parent. The oldest CSS properties, like
the `inline` and `block` values for `display`, are set on children,
but newer ones like `inline-block`, `flex`, and `grid` are set on the
parent. This chapter takes its nomenclature from this newer
convention, even though it's actually implement inline and block layout.

Let's have one class for each layout mode. `InlineLayout` should be
familiar: it's what we've been implementing up until this point and
corresponds to how text inside a paragraph are laid out in lines, left
to right.[^in-english] `BlockLayout` is new to this chapter: it
corresponds to the way containers like paragraphs and headings are
laid out one after another vertically from top to bottom.

[^in-english]: In European languages, at least!

Since the existing `Layout` class is more or less inline layout, let's
rename it to `InlineLayout` and rename its constructor to be a new
`layout` method:

``` {.python}
class InlineLayout:
    def layout(self):
        # ...
```

Right now, the code in the `layout` method refers to a `tree`
argument; replace those references with a new `node` field, and add a
new constructor to `InlineLayout` to initialize it. Because layout
objects form a tree, we'll also want references to the parent node and
also the previous sibling:

``` {.python}
class InlineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
```

Besides the references to other related layout objects, each layout object also
needs a size and position, which we'll store in the `w`, `h`, `x`, and
`y` fields. Each layout object will have a `layout` method whose job
is computing the values of those fields.

Let's start with `InlineLayout`. Right now its constructor also
initializes `weight`, `style`, and `size`, as well as `display_list`.
Let's move all of those into a new `layout` method:

``` {.python}
def layout(self):
    self.display_list = []
    self.weight = "normal"
    self.style = "roman"
    self.size = 16

    # ...
```

The constructor also initializes `cursor_x`, `cursor_y`, and `line`,
and calls `recurse` and `flush`. Let's move that into `layout` as
well:

``` {.python}
def layout(self):
    # ...

    self.cursor_x = self.x
    self.cursor_y = self.y
    self.line = []
    self.recurse(self.node)
    self.flush()
```

Note that I've changed the code to initialize `cursor_x` and
`cursor_y` from `x` and `y` instead of `HSTEP` and `XSTEP`. Make sure
to make that change inside the `flush` method also.

For now, we're not actually calculating the `x`, `y`, `w`, and `h`
variables anywhere. We'll do that later this chapter. We're also not
creating any children; that'll have to wait for [another
chapter](chrome.md). For now, we need to focus on the other layout
mode, block layout.

Creating the layout tree
========================

Our second type of layout object will be called `BlockLayout`:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
```

Unlike with inline layout, the first job of `BlockLayout` is creating
layout objects for all the containters inside it.

When creating child layout objects, the big question for each child is
whether it should be a `BlockLayout` or an `InlineLayout`. Basically,
elements that just contains text, or maybe formatted text, should have
an `InlineLayout`, but containers like `<div>` or `<header>` should
have a `BlockLayout`.

What happens if an element contains both text and something like a
`<div>`? In some sense, this is an error on the part of the web
developer. And just like with implicit tags in [Chapter 4][html.md],
browsers use a repair mechanism to make sense of the situation. In
real browsers, "[anonymous block boxes][anon-block]" are used, but in
our toy browser we'll implement something a little simpler. 

[anon-block]: https://developer.mozilla.org/en-US/docs/Web/CSS/Visual_formatting_model#anonymous_boxes

To determine whether an element has an `InlineLayout` or a
`BlockLayout` we compare its children against that list. Let's add a
`layout_mode` function that creates a `BlockLayout` for an element
that has containers inside, and also for empty elements:

``` {.python}
def layout_mode(node):
    has_text = False
    has_containers = False
    # ...
    if has_containers or not has_text:
        return "block"
    else:
        return "inline"
```

We'll set `has_text` and `has_containers` by just matching the
element's children against a list of elements used for formatting
text:

``` {.python}
INLINE_ELEMENTS = [
    "a", "em", "strong", "small", "s", "cite", "q", "dfn", "abbr",
    "ruby", "rt", "rp", "data", "time", "code", "var", "samp",
    "kbd", "sub", "sup", "i", "b", "u", "mark", "bdi", "bdo",
    "span", "br", "wbr", "big"
]
```

The loop looks like this:

``` {.python}
def layout_mode(node):
    # ...
    for child in node.children:
        if isinstance(child, Text):
            has_text = True
        elif child.tag in INLINE_ELEMENTS:
            has_text = True
        else:
            has_containers = True
    # ...
```

`BlockLayout` can now call `layout_mode` as it creates child layout
nodes to determine what type of layout object to create:

``` {.python}
class BlockLayout:
    def layout(self):
        previous = None
        for child in self.node.children:
            if layout_mode(child) == "inline":
                previous = InlineLayout(child, self, previous)
            else:
                previous = BlockLayout(child, self, previous)
            self.children.append(previous)
```

Note that when each child is created, `self` is passed as the parent,
and the previously-created child is kept around for the previous
sibling.

With the children created, their own `layout` method can be called
recursively to build the whole tree, with `InlineLayout` objects at
the leaves:

``` {.python}
def layout(self):
    # ...
    for child in self.children:
        child.layout()
```

What sits at the root of the layout tree and kicks off this whole
process? Inconveniently, both `BlockLayout` and `InlineLayout` require
a parent node, so we need another kind of layout object at the root. I
think of that root as the document itself, so let's call it
`DocumentLayout`:

``` {.python}
class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.children = []

    def layout(self):
        child = BlockLayout(self.node, self, None)
        self.children.append(child)
        child.layout()
```

To summarize the rules of layout tree creation:

+ The root of the layout tree a `DocumentLayout`, and its only child
  is a `BlockLayout`.
+ A `BlockLayout`'s children are either `BlockLayout`s or
  `InlineLayout`s.
+ An `InlineLayout` doesn't have children.

The whole layout tree is now being built. But so far, we haven't
actually done _layout_---we haven't determined the size and position
of each layout object in the tree. Let's turn to that next.

Size and position
=================

Let's start in `BlockLayout`. Block layout objects are greedy and take
take up all the horizontal space they can. So their width is their
parent's width:

``` {.python}
self.w = self.parent.w
```

This also means that a block layout object's horizontal position is
the same as its parent's:

``` {.python}
self.x = self.parent.x
```

The vertical position of a block layout object depends on whether it
is its parent's first child or not. First children start at the top of
the parent, but later children have to start where their previous
sibling ended:

``` {.python}
if self.previous:
    self.y = self.previous.y + self.previous.h
else:
    self.y = self.parent.y
```

These three computations have to go before the loop that calls
`layout` on each child. After all, a block layout object's width
depends on the parent's width; so the width must be computed before
laying out the children. The position is the same: it depends on both
the parent and previous sibling, so the parent has to compute it
before recursing, and when recursing it has to lay out the children in
order. Getting this dependency order right is crucial, because if you
don't some layout object will try to read a value that hasn't been
computed yet, and the browser will crash.

Finally, we need to compute the block layout's height. A block layout
object should be tall enough to contain all of its children, so its
height should be the sum of its children's height:

``` {.python}
self.h = sum([child.h for child in self.children])
```

But note that the height of a block layout depends on the height of
its *children*. So, it must be computed after recursing, after the
heights of its children are computed. In other words, the `layout`
method must be ordered like so:

+ When `layout` is called, it first creates layout objects for each child.
+ It then computes the `w`, `x`, and `y` fields, reading from the
  `parent` and `previous` layout objects.
+ The children are then be recursively laid out by calling their
  `layout` methods.
+ Finally, the object's `h` field can be computed, reading from the
  child layout objects.

This *dependency ordering* plays a really important role in
understanding how layout works, especially as layout gets more
complicated to support more features and faster speed. [Chapter
10](reflow.md) will explore this topic more.

That settles `BlockLayout`; let's now work on `InlineLayout`. Its `x`,
`w`, and `y` are set the same way as for a `BlockLayout`, but its
height is computed based on its *y*-cursor instead of the height of
its children.

``` {.python}
class InlineLayout:
    def layout(self):
        self.x = self.parent.x
        self.w = self.parent.w

        if self.previous:
            self.y = self.previous.y + self.previous.h
        else:
            self.y = self.parent.y

        # ...

        self.h = self.cursor_y - self.y
```

Finally, even `DocumentLayout` needs some layout code, though since the
document always starts in the same place it's pretty simple:

``` {.python}
class DocumentLayout:
    def layout(self):
        # ...
        self.w = WIDTH - 2*HSTEP
        self.x = HSTEP
        self.y = VSTEP
        child.layout()
        self.h = child.h + 2*VSTEP
```

Note that I'm adding a little bit of padding around the main
text---`HSTEP` on the left and right, and `VSTEP` above. That's so the
text won't run into the very edge of the window, where a bit of it
would get cut off.

::: {.further}
Formally, computations on a tree like this can be described by an
[attribute grammar](wiki-atgram). Attribute grammar engines analyze
dependencies between different attributes to determine the right order
to traverse the tree and calculate each attribute.
:::

[wiki-atgram]: https://en.wikipedia.org/wiki/Attribute_grammar

Using tree-based layout
=======================

So we're now creating a layout tree and computing the size and
position of everything in it. Let's now use all this in the browser
itself, in the `load` method. First, we need to create the layout tree
and lay it out:

``` {.python}
class Browser:
    def load(self, url):
        headers, body = request(url)
        tree = HTMLParser(body).parse()
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
    def draw(self, display_list):
        self.children[0].draw(display_list)
```

For `BlockLayout`, which has multiple children, `draw` is called on
each child:

``` {.python}
class BlockLayout:
    def draw(self, display_list):
        for child in self.children:
            child.draw(display_list)
```

Finally, `InlineLayout` is already storing things to draw in its
`display_list` variable, so we can copy them over:

``` {.python expected=False}
class InlineLayout:
    def draw(self, display_list):
        display_list.extend(self.display_list)
```

Now the browser can use `draw` to collect its own `display_list`
variable:

``` {.python}
class Browser:
    def load(self, url):
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
        self.top = y1
        self.left = x1
        self.text = text
        self.font = font
    
class DrawRect:
    def __init__(self, x1, y1, x2, y2, color):
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color
```

`InlineLayout` adds `DrawText` objects to the display
list:[^why-not-change]

[^why-not-change]: Why not change `display_list` to contain `DrawText`
    commands directly? You could, it would be fine, but this will
    be easier to refactor later.

``` {.python}
class InlineLayout:
    def draw(self, display_list):
        for x, y, word, font in self.display_list:
            display_list.append(DrawText(x, y, word, font))
```

Meanwhile `BlockLayout` can draw backgrounds with `DrawRect` commands.
Let's add a gray background to `pre` tags, which contain code:

``` {.python}
class BlockLayout:
    def draw(self, display_list):
        if self.node.tag == "pre":
            x2, y2 = self.x + self.w, self.y + self.h
            display_list.append(DrawRect(self.x, self.y, x2, y2, "gray"))
        # ...
```

Make sure this code come *before* recursively calling `draw` on child
layout objects: the background has to be drawn *before* and therefore
*below* the text inside the source block.

The `render` method now needs to run graphics commands on our actual
canvas. Let's do this with an `execute` method for each command. On
`DrawText` it calls to `create_text`:

``` {.python}
class DrawText:
    def execute(self, scroll, canvas):
        canvas.create_text(
            self.left, self.top - scroll,
            text=self.text,
            font=self.font,
            anchor='nw',
        )
```

Note that `execute` takes the scroll amount as a parameter; in effect,
we're asking each graphics command to perform coordinate conversion.

`DrawRect` works the same way, except it calls `create_rectangle`. By
default `create_rectangle` draws a one-pixel black border, so make
sure to pass `width = 0`:

``` {.python}

class DrawRect:
    def execute(self, scroll, canvas):
        canvas.create_rectangle(
            self.left, self.top - scroll,
            self.right, self.bottom - scroll,
            width=0,
            fill=self.color,
        )
```

We do still want to skip graphics commands that occur offscreen, and
`DrawRect` already contains a `bottom` field we can use, so let's add
the same to `DrawText`:

``` {.python}
def __init__(self, x1, y1, text, font):
    # ...
    self.bottom = y1 + font.metrics("linespace")
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
to call `execute` for:

``` {.python}
def render(self):
    self.canvas.delete("all")
    for cmd in self.display_list:
        if cmd.y1 > self.scroll + HEIGHT: continue
        if cmd.y2 < self.scroll: continue
        cmd.execute(self.scroll, self.canvas)
```

We not only have access to the height of any element, but also of the
whole page. The browser can use that to stop the user from scrolling
past the bottom of the page. In `load`, store the height in a
`max_y` variable:

``` {.python}
class Browser:
    def load(self, url):
        # ...
        self.max_y = document.h - HEIGHT
```

Then, when the user scrolls down, don't let them scroll past the
bottom of the page:

``` {.python}
def scrolldown(self, e):
    self.scroll = self.scroll + SCROLL_STEP
    self.scroll = min(self.scroll, self.max_y)
    self.scroll = max(0, self.scroll)
    self.render()
```

Make sure those `max` and `min` calls happen in the right order!

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
background, above that list. Don't modify the lexer or parser.

*Anonymous block boxes*: Sometimes, an element has a mix of text-like
and container-like children. For example, in this HTML,

    <div><i>Hello, </i><b>world!</b><p>So it began...</p></div>

the `<div>` element has three children: the `<i>`, `<b>`, and `<p>`
elements. The first two are text-like; the last is container-like.
This is supposed to look like two paragraphs, one for the `<i>` and
`<b>` and the second for the `<p>`. Make your browser do that.
Specifically, modify `InlineLayout` so it can be passed a sequence of
sibling nodes, instead of a single node. Then, modify the algorithm
that constructs the layout tree so that any sequence of text-like
elements gets made into a single `InlineLayout`.

