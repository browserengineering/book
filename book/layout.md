---
title: Laying Out Pages
chapter: 5
prev: html
next: styles
...

So far, layout has been an unstructured process, with each tag just
directly modifying state like the current *x* and *y* position.
That\'s an appropriate way to lay out text, but gets cumbersome as
we add more and more layout features. Plus, it's patently unsuited for
handling things like borders and margins. This chapter describes a
better way to do layout.

Inline layout
=============

The way layout works now, every time we lay out an element, we first
modify the state (in `layout_open`), then lay out each child, and then
modify the state again (in `layout_close`). The actual measurements of
each element (like their height and width) don't exist as data; you
can only glimpse them by watching the pattern of state modifications.

Well, that works for simple layouts, but it's pretty hard to draw a
border without knowing how wide and tall to draw the border.

So web browsers actually structure layout differently. In a browser,
the job of layout is to produce a tree, called the *box tree*, so that
each element has an associated box and each box is annotated with a
size and a position. When you lay out text, you do so relative to the
box the element is contained in.

Our `layout` function doesn\'t do this yet, so let's fix it.

Let's start by defining a data structure to store an area where text
can be laid out. I\'m going to call this a `Block`:

``` {.python}
class Block:
    def __init__(self, x, y, w):
        self.x = x
        self.y = y
        self.w = w
```

Now I\'m going to rearrange the `layout` functions into a class called
`InlineLayout`, which will sort of combine the three `layout`
functions and the `State` class together:

``` {.python}
class InlineLayout:
    def __init__(self, block):
        self.parent = block
        self.x = block.x
        self.y = block.y
        self.bold = False
        self.italic = False
        self.terminal_space = True
        self.dl = []
```

Here, the `parent` field will point to a `block` data structure from
above, which will define the area where text will be placed.

The `layout` function will become a method in this class:

``` {.python}
class InlineLayout:
    # ...
    def layout(self, node):
        if isinstance(node, ElementNode):
            self.open(node)
            for child in node.children:
                self.layout(child)
            self.close(node)
        else:
            self.text(node)
```

The `open`, `close`, and `text` methods will be the similarly-named
functions from the previous lab. Just make sure to replace all
references to the parts of `state` with references to `self`.^[Be
careful with this. Python in particular will not warn you if you
assign to an undeclared variable, because it has no notion of variable
declaration as separate from assignment!]

As we're doing this, we need to update the hard-coded constants that
used to define the page boundaries with references to `parent`. So
instead of...

``` {.python}
if self.x + w > 787:
    self.x = 13
    self.y += font.metrics('linespace') * 1.2
```

... we now now want to reset `self.x` not to 13 but to the left edge of
the block that we are doing layout inside of; and likewise the right
hand edge is no longer 787 but instead `self.parent.x + self.parent.w`:

``` {.python}
if self.x + w > self.parent.x + self.parent.w:
    self.x = self.parent.x
    self.y += font.metrics('linespace') * 1.2
```

You should be able to use `InlineLayout` in `show` by creating a `Block`
representing the page and then laying out to it:

``` {.python}
page = Block(13, 13, 774)
layout = InlineLayout(page)
layout.layout(nodes)
display_list = layout.dl
```

Layout uses its block parent as an input, to define where text should
go, but that block is also an output, since we only discover how tall
a block of text is during inline layout. So at the end of `layout`,
let's set the `h` field on the `InlineLayout` to define its height:

``` {.python}
font = self.font()
last_line = font.metrics('linespace') * 1.2
self.h = (self.y + last_line) - self.parent.y
```

Here the height is computed by taking the bottom of the laid out text
(using `self.y` for its top and adding its height) and subtracting the
place where we started laying out text. Note that I\'m calling a new
helper function `self.font` to compute the current font, setting the
weight and slant properly.

We can make use of this height in `show` to stop users from scrolling
past the bottom of the page. First, store the height in the `maxh`
variable:

``` {.python}
maxh = layout.h
```

Then, when the user scrolls down, we won\'t let them scroll past the
bottom of the page:

``` {.python}
def scrolldown(e):
    nonlocal scrolly
    scrolly = min(scrolly + SCROLL_STEP, 13 + maxh - 600)
    render()
```

Here, the `13` accounts for the 13 pixels of padding we have at the
beginning of the page and the `600` is the height of the screen.

Block layout
============

`InlineLayout` is good for laying out lines of text, but what about
paragraphs of text, with succeeding paragraphs stacked vertically atop
each other? The current code treats paragraphs as just part of the
general left-to-right line-oriented layout method, which does't make
much sense. Instead it makes sense to treat paragraphs as separate
`InlineLayout` contexts that later get vertically stacked.

To do that, I\'m going to rename `Block` to `BlockLayout`, and it'll
be a separate *layout mode*, which is intended for things like
paragraphs and headings. Block layouts will have multiple children, so
we\'ll add fields for children and parents.

``` {.python}
class BlockLayout:
    def __init__(self, parent, node):
        self.parent = parent
        self.children = []
        self.node = node
        self.x = 13
        self.y = 13
        self.w = 774
```

For now, I'm hard-coding the `x`, `y`, and `w` values in the
constructor from the parent, but that'll eventually change.

We\'ll have a `layout` function for `BlockLayout`to lay out blocks
vertically one after another. You might write it like this:

``` {.python}
class BlockLayout
    def layout(self):
        y = self.y
        for child in node.children:
            layout = BlockLayout(self, child)
            self.children.append(layout)
            layout.layout(y)
            y += layout.h
```

This isn\'t too far off conceptually, but there are a bunch of flaws:

-   We don't set the `h` field, so we can't use it yet;
-   We\'re passing the child *y* position to the `layout` function,
    which doesn\'t expect that input;
-   Now we\'re only ever using `BlockLayout` and never calling
    `InlineLayout`;
-   `TextNode` has no `children` field, but this `layout` method will
    eventually reach a `TextNode` and crash.

Let\'s fix these one by one. First, the height. At the end of
`BlockLayout.layout` we know the current `y` position, and it is after
every child node\'s layout, so we just use that to change the value of
`self.h`:

``` {.python}
def layout(self, y):
    # ...
    self.h = y - self.y
```

Second, the `y` argument. Let\'s add a `y` parameter to `layout`
function and use that to set `self.y`:

``` {.python}
def layout(self, y):
    self.y = y
    # ...
```

That also lets us remove the hard-coded assignment to `self.y` in
`__init__`, and while we're at it, let's change `self.x` and `self.w`
to not be hard-coded:

``` {.python}
def __init__(self, parent):
    # ...
    self.x = self.parent.x
    self.y = self.parent.y
```

Since we're now looking for data in the parent, let's add a new type
of node to be the root node:

``` {.python}
class Page:
    def __init__(self):
        self.x = 13
        self.y = 13
        self.w = 774
        self.children = []
```

Third and fourth, we need to call `InlineLayout` to handle
`TextNode`s, plus the `ElementNode`s that are supposed to be inline,
like `<b>` and `<i>`. The idea is that instead using `BlockLayout` to
lay out each child node, we\'ll look to see what that node contains.
If it contains a `TextNode`, or if contains a `<b>` or `<i>` element,
it will be laid out with `InlineLayout` instead:

``` {.python}
def is_inline(node):
    if isinstance(node, TextNode):
        return true
    else:
        return node.tag in ["b", "i"]

def layout(self, y):
    self.y = y
    if any(is_inline(child) for child in node.children):
        layout = InlineLayout(self)
        self.children.append(layout)
        layout.layout(node)
        y += layout.height()
    else:
        # ...
```

Let\'s try it out. We\'ll need to tweak `show`:

``` {.python}
page = Page()
layout = BlockLayout(page)
layout.layout(nodes)
maxh = layout.h
display_list = layout.display_list()
```

Here I\'m calling `layout.display_list()` instead of directly
accessing `layout.dl`, because display lists will be computed
differently for `InlineLayout` and `BlockLayout`. On an `InlineLayout`
that function should just return the `dl` field, and on a
`BlockLayout` it should concatenate all its childrens\' display
lists:^[I\'m trying to avoid fancy Python features where possible, but
if your language supports iterators it makes a lot of sense to return
an iterator from `display_list` instead of a list. That will also
avoid a lot of copying.]

``` {.python}
def display_list(self):
    dl = []
    for child in self.children:
        dl.extend(child.display_list())
    return dl
```

If you run this, you\'ll find that everything is laid out in one giant
paragraph, despite all our work putting each paragraph in its own
`ElementNode`. That\'s because most elements have an all-whitespace
`TextNode`; that causes those elements to be laid out with
`InlineLayout`. A small tweak to `is_inline` will mostly fix it:

``` {.python}
if isinstance(node, TextNode):
    return not node.text.isspace()
# ...
```

We\'ll also need to skip these empty `TextNode` objects when we create
layouts for each child of a block:

``` {.python}
for child in node.children:
    if isinstance(child, TextNode): continue
    # ...
```

You should see now see paragraphs vertically stacked, and headings
should now automatically take up their own lines, as should list
items, code snippets, and every other element of that sort.

One thing we lost with this big layout refactor, though, is the blank
line between paragraphs. Let\'s add it back.

The box model
=============

Let\'s add support for *margins*, *borders*, and *padding*, which are
the main ways you change the position of block layout elements.
Here\'s how those work. In effect, every block element has four
rectangles associated with it: the *margin rectangle*, the *border
rectangle*, the *padding rectangle*, and the *content rectangle*:

![](https://www.w3.org/TR/CSS2/images/boxdim.png)

The margin, border, and padding, gives the width of the gap between
each of these rectangles. Margin, border, and padding can be different
on each side of the block). That makes for a lot of variables:

``` {.python}
class BlockLayout:
    def __init__(self, parent, node):
        # ....
        self.mt = self.mr = self.mb = self.ml = 0
        self.bt = self.br = self.bb = self.bl = 0
        self.pt = self.pr = self.pb = self.pl = 0
```

The naming convention here is that the first letter stands for margin,
border, or padding, while the second letter stands for top, right,
bottom, or left. Let's stick with the convention that the `x` and `y`
fields on a layout object represent the top right of the *border*
rectangle, so that the top margin goes *above* `self.y`, and likewise
for the left margin, but the top and left borders and padding are
below and to the right of `self.y` and `self.x`. Similarly, `self.w`
and `self.h` should give the width and height of the border rectangle.
We can add helper functions to get some other useful sizes:

``` {.python}
def content_left(self):
    return self.x + self.bl + self.pl
def content_top(self):
    return self.y + self.bt + self.pt
def content_width(self):
    return self.w - self.bl - self.br - self.pl - self.pr
```

We\'ll now need to take a look at every place we use these variables and
add the appropriate padding, margin, or border:

-   In the `BlockLayout` constructor, instead of using `parent.x` for
    `self.x`, we\'ll use `parent.content_left()`.
-   In the `BlockLayout` constructor, instead of using `parent.w` for
    `self.w`, we\'ll use `parent.content_width()`.
-   In `BlockLayout.layout`, we\'ll want to add top and left margins to
    `self.x` and `self.y`, and subtract left and right margins from
    `self.w.`
-   In `BlockLayout.layout`, we\'ll need to add the vertical padding and
    border to the `y` variable after laying out all of the children.
-   In the `InlineLayout` constructor, instead of using `block.x` and
    `block.y`, we\'ll use `block.content_left()` and
    `block.content_top()`.
-   In `InlineLayout.text`, we\'ll use `block.content_left()` and
    `block.content_top()`.

We\'ll also want to modify `BlockLayout.layout` to insert vertical
margins between the children that it lays out:

``` {.python}
y += layout.height() + layout.mt + layout.mb
```

Note that `InlineLayout` does not have margin fields, but that\'s OK
because every `InlineLayout` is safely hidden inside a `BlockLayout`.

Right now, all of these changes are useless since all of the fields are
set to 0. Let\'s add code to the top of `BlockLayout.layout` to set
those fields:

``` {.python}
if node.tag == "p":
    self.mb = 16
elif node.tag == "ul":
    self.mt = self.mb = 16
    self.pl = 20
elif node.tag == "li":
    self.mb = 8
```

You should now see blanks between paragraphs, and list items (like in a
table of contents) should be indented.

One more stop: let's actually draw the borders. That means drawing
lines (one per border) or, more precisely, rectangles (since the
borders have width). That\'s going to mean extending the display list
to draw both rectangles and text. Let\'s create some data structures
for that.

``` {.python}
class DrawText:
    def __init__(self, x, y, text, font):
        self.x = x
        self.y = y
        self.text = text
        self.font = font

    def draw(self, scrolly, canvas):
        canvas.create_text(
            self.x, self.y - scrolly,
            text=self.text,
            font=self.font,
            anchor='nw',
        )

class DrawRect:
    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def draw(self, scrolly, canvas):
        canvas.create_rectangle(
            self.x1, self.y1 - scrolly,
            self.x2, self.y2 - scrolly,
            width=0,
            fill="black",
        )
```

Here I\'ve passed `width=0` to `create_rectangle`, because otherwise
`create_rectangle` would draw a one-pixel black border.

Now `InlineLayout.layout` will create `DrawText` objects, while
`BlockLayout.display_list` will create `DrawRect` objects for the
borders.

``` {.python}
def display_list(self):
    dl = []
    # ...
    _ol, _ot = self.x, self.y
    _or, _ob = _ol + self.w, _ot + self.h
    _il, _it = _ol + self.bl, _ot + self.bt
    _ir, _ib = _or - self.br, _ob - self.bb
    if self.bl: dl.append(DrawRect(_ol, _ot, _il, _ob))
    if self.br: dl.append(DrawRect(_ir, _ot, _or, _ob))
    if self.bt: dl.append(DrawRect(_ol, _ot, _or, _it))
    if self.bb: dl.append(DrawRect(_ol, _ib, _or, _ob))
    return dl
```

Here I define the variables `_ol`, `_il`, `_ot`, `_it`, `_or`, `_ir`,
`_ob`, and `_ib` for the outer and inner left, top, right, and bottom
coordinates. The underscore is because otherwise `or` would conflict
with a keyword.

Finally, when we use the display list, we\'ll now just call `draw` on
each command in the display list:

``` {.python}
def render():
    canvas.delete("all")
    for cmd in display_list:
        cmd.draw(scrolly, canvas)
```

This setup also makes it fairly easy to change the appearance of
elements. For example, a few lines will indent code blocks 8 pixels,
surround them with a one pixel border, and then add another 8 pixels
between the border and the code itself:

``` {.python}
elif node.tag == "pre":
    self.mr = self.ml = 8
    self.bt = self.br = self.bb = self.bl = 1
    self.pt = self.pr = self.pb = self.pl = 8
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
