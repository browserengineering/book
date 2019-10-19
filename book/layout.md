---
title: Laying Out Pages
chapter: 5
prev: html
next: styles
...

Our browser now does layout from the element tree. However, until now,
layout has been a pretty unstructured process, with each tag just
directly modifying state like the current *x* and *y* position or
whether text is bold and italic. That\'s an appropriate way to lay out
text, but isn't enough to handle borders.

Inline layout
=============

Web pages can lay out different kinds of content: text, paragraph and
headings, tables, figures that text wraps around, and so on. Each
element on the page is identified with one of these different *layout
modes*; each layout mode has its own logic for placing parts of the
page. It\'s best to think of a layout mode as a function: each layout
mode takes as input some description of *where* it should lay out
content; then it does the layout in a mode-specific way; and finally it
returns some information describing *how much* space it took up.

Now, our `layout` function from last time doesn\'t do this. It takes no
input (and implicitly uses the page boundaries to determine where to
place text). And it produces no output (though it does write to the
display list). Let\'s change this.

First, we\'ll need a data structure to store the area of the page where
text is allowed to be laid out. I\'m going to call this a `Block`:

``` {.python}
class Block:
    def __init__(self, x, y, w):
        self.x = x
        self.y = y
        self.w = w
```

Now I\'m going to rearrange the `layout` function into a class called
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

Next, `layout` will become a method on this class:

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
references to the parts of `state` with references to `self`.[^1]

However, there are a few key changes to line breaking. Where we used to
have...

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
mode = InlineLayout(page)
mode.layout(nodes)
display_list = mode.dl
```

Now, once we do an inline layout, we should also return how much space
that layout took out. That means we want to return the total height of
the resulting text:

``` {.python}
def height(self):
    font = self.font()
    return (self.y + font.metrics('linespace') * 1.2) - self.parent.y
```

Here the height is computed by taking the bottom of the laid out text
(using `self.y` for its top and adding its height) and subtracting the
place where we started laying out text. Note that I\'m calling the
helper function `self.font` to compute the current font, setting the
weight and slant properly.

We can make use of this height in `show`. First, store the height in the
`maxh` variable:

``` {.python}
maxh = mode.height()
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

`InlineLayout` is good for laying text out into lines, but most things
aren\'t laid out into lines. For example, we generally think of each
paragraph as separate, with succeeding paragraphs stacked vertically
atop each other. But the current code treats paragraphs as just part of
the general left-to-right line-oriented layout method. Let\'s change how
paragraphs work to instead treat paragraphs as separate `InlineLayout`
contexts that later get vertically stacked.

To do that, I\'m going to rename `Block` to `BlockLayout`. Block layouts
will have multiple children, so we\'ll add fields for children and
parents. We\'ll now be able to retrieve the `x`, `y`, and `w` values in
the constructor from the parent:

``` {.python}
class BlockLayout:
    def __init__(self, parent):
        self.parent = parent
        self.children = []
        self.parent.children.append(self)
        self.x = parent.x
        self.y = parent.y
        self.w = parent.w
```

Let\'s also add a class to represent the overall page and to be the
parent of the top-level block:

``` {.python}
class Page:
    def __init__(self):
        self.x = 13
        self.y = 13
        self.w = 774
        self.children = []
```

Now, we\'d like to lay out the page using `BlockLayout` instead of
`InlineLayout`. To do that, we\'ll need a `layout` function for
`BlockLayout`. Since we want blocks to be laid out one after another, we
might write something like this:

``` {.python}
class BlockLayout
    # ...
    def layout(self, y):
        y = self.y
        for child in node.children:
            layout = BlockLayout(self, child)
            layout.layout(y)
            y += layout.height()
```

This isn\'t too far off conceptually, but there are a bunch of flaws:

-   We haven\'t implemented `BlockLayout.height`, so calling it seems
    fishy
-   We\'re passing the child *y* position to the `layout` function,
    which doesn\'t expect that input
-   Now we\'re only ever using `BlockLayout` and never calling
    `InlineLayout`
-   `TextNode` has no `children` field, but this `layout` method will
    eventually reach a `TextNode` and crash

Let\'s fix these one by one. First, let\'s keep track of our height. At
the end of `BlockLayout.layout` we know the current `y` position, and it
is after every child node\'s layout, so we just use that to change the
value of a `self.h` parameter:

``` {.python}
class BlockLayout
    def __init__(self, parent):
        # ...
        self.h = None

    def layout(self, node):
        # ...
        self.h = y - self.y

    def height(self):
        return self.h
```

Then, for the second, let\'s add a `y` parameter to `layout` function
and use that instead of `parent.y`:

``` {.python}
def __init__(self, parent, node):
    # ...
    self.node = node
    # ...
```

Now, the last two we\'ll solve together. The idea is that instead using
`BlockLayout` to lay out each child node, we\'ll look to see what that
node contains. If it contains a `TextNode`, or if contains a `<b>` or
`<i>` element, it will be laid out with `InlineLayout` instead:

``` {.python}
def is_inline(node):
    if isinstance(node, TextNode):
        return true
    else:
        return node.tag in ["b", "i"]

class BlockLayout:
    # ...
    def layout(self, y):
        self.y = y
        if any(is_inline(child) for child in node.children):
            layout = InlineLayout(self)
            layout.layout(node)
            y += layout.height()
        else:
            # ...
```

This is almost correct. Let\'s get it running. We\'ll need to change
`show` like this:

``` {.python}
page = Page()
mode = BlockLayout(page)
mode.layout(nodes)
maxh = mode.height()
display_list = mode.display_list()
```

Here I\'m calling `mode.display_list()` instead of directly accessing
`mode.dl`, because display lists will be computed differently for
`InlineLayout` and `BlockLayout`. On an `InlineLayout` that function
should just return the `dl` field, and on a `BlockLayout` it should
append all its childrens\' display lists:[^2]

``` {.python}
def display_list(self):
    dl = []
    for child in self.children:
        dl.extend(child.display_list())
    return dl
```

This should be enough to get things running. However, you\'ll find that
everything is laid out in one giant paragraph for almost all web pages.
That\'s because most elements have an all-whitespace `TextNode`; that
causes those elements to be laid out with `InlineLayout`. A small tweak
to `is_inline` will mostly fix it:

``` {.python}
if isinstance(node, TextNode):
    return not node.text.isspace()
# ...
```

We\'ll also need to skip these empty `TextNode` objects when we create
layouts for each child of a block:

``` {.python}
for child in node.children:
    if isinstance(child, TextNode) and child.text.isspace(): continue
    # ...
```

Ok, let\'s get block layout up and running! All we need to do is change
`InlineLayout` in `show` to `BlockLayout` and you should see paragraphs
vertically stacked. As a plus, headings should now also take up their
own lines automatically, as should list items, code snippets, and
similar.

One thing we lost with this big layout refactor, though, is the blank
line between paragraphs. Let\'s add it back.

The box model
=============

Now that we have block layout working, let\'s add some additional
styling features. In particular, let\'s add support for *margins*,
*borders*, and *padding*. Here\'s how those work. In effect, every block
element has four rectangles associated with it: the *margin rectangle*,
the *border rectangle*, the *padding rectangle*, and the *content
rectangle*:

![](https://www.w3.org/TR/CSS2/images/boxdim.png)

Now, each of the margin, border, and padding can appear on any side of
the block (on the top, bottom, left, and right). That\'s a whole lot of
variables:

``` {.python}
class BlockLayout:
    def __init__(self, parent, y):
        # ....
        self.mt = self.mr = self.mb = self.ml = 0
        self.bt = self.br = self.bb = self.bl = 0
        self.pt = self.pr = self.pb = self.pl = 0
```

The naming convention here is that the first letter tells you whether
it\'s a margin, a border, or a padding, while the second letter gives
the direction (top, right, bottom, or left). Now that we have all of
these rectangles, let\'s establish that the `self.x` and `self.y`
coordinates refer to the top-left of the *border rectangle*. That is,
the top margin is *above* `self.y`, and likewise the left margin, but
the top and left borders are *below and to the right* of
`self.x, self.y`. Similarly, `self.w` should give the width and height
of the border rectangle, and `self.height()` should return its height.
We can add some helper functions:

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
margins where appropriate:

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

Let\'s make a final tweak. Right now we leave room for borders, but we
don\'t draw them. That\'s pretty silly! To draw borders, we\'ll need to
draw lines (one per border) or, more precisely, rectangles (since the
borders have width). That\'s going to mean extending the display list to
draw both rectangles and text. Let\'s create some data structures for
that.

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
`create_rectangle` would pass a one-pixel black border, which we don\'t
need, and also `fill` to make the border black.

Now we\'ll need to change `InlineLayout.layout` to create `DrawText`
objects, and also add `DrawRect` objects in
`BlockLayout.display_list()`:

``` {.python}
def display_list(self):
    dl = []
    # ...
    if self.bl > 0: dl.append(DrawRect(self.x, self.y, self.x + self.bl, self.y + self.h))
    if self.br > 0: dl.append(DrawRect(self.x + self.w - self.br, self.y, self.x + self.w, self.y + self.h))
    if self.bt > 0: dl.append(DrawRect(self.x, self.y, self.x + self.w, self.y + self.bt))
    if self.bb > 0: dl.append(DrawRect(self.x, self.y + self.h - self.bb, self.x + self.w, self.y + self.h))
    return dl
```

Finally, when we use the display list, we\'ll now just call `draw` on
each command in the display list:

``` {.python}
def render():
    canvas.delete("all")
    for cmd in display_list:
        cmd.draw(scrolly, canvas)
```

You can now add a few lines to take code blocks (which are in `<pre>`
tags) and indent them 8 pixels from the text, plus surround them with a
one pixel border and then add another 8 pixels between the border and
the code itself:

``` {.python}
elif node.tag == "pre":
    self.mr = self.ml = 8
    self.bt = self.br = self.bb = self.bl = 1
    self.pt = self.pr = self.pb = self.pl = 8
```

Summary
=======

In this chapter, we did a pretty dramatic rewrite of the layout portion of
our browser. We\'ve now split layout into two different *layout modes*,
which handle laying out different types of content. Furthermore, we\'ve
extended the styling capabilities of our browser, adding the CSS box
model.

Assignments
===========

-   Remove the magic numbers from the `Page` object by instead assigning
    padding to the `<body>` element
-   Add bullets to list items, which in HTML are `<li>` tags. You can
    make them little squares, located to the left of the list item
    itself.
-   Add support for background colors and border colors. Code blocks
    (`<pre>` tags) should have light-gray background color, while
    headings (`<h2>` tags) should have light-gray bottom borders. You
    can pick more fun colors if you\'d like. To draw a background color,
    pass the `fill` parameter to `create_rect`.
-   On this web page, there are `<div>` elements with `id` attributes
    with values `preamble` and `content`. Make the `content` element
    roughly 600 pixels wide and located in the top-left of its parent,
    while the `preamble` element roughly 200 pixels wide (leave some
    space between them) and located in the top-right of its parent.[^3]
-   Implement *margin collapsing*. In margin collapsing, when one block
    has a bottom margin and the next block has a top margin, the actual
    gap between them is the *larger* of the two margins, not their sum.
    Likewise, the top (bottom) margin of an element is allowed to
    overlap with the top (bottom) margin of its first (last) child, as
    long as it has no top (bottom) border or padding.

[^1]: Be careful with this. Python in particular will not warn you if
    you assign to an undeclared variable, because it has no notion of
    variable declaration as separate from assignment!

[^2]: I\'m trying to avoid fancy language features where possible, but
    if your language supports iterators it makes a lot of sense to
    return an iterator from `display_list` instead of a list. That will
    also avoid a lot of copying.

[^3]: In CSS, this is implemented using a feature called `float`. Sadly,
    `float` is a little too complex to implement in our toy browser...
