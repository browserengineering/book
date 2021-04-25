---
title: Laying Out Pages
chapter: 5
cur: layout
prev: html
next: styles
...

So far, layout has been a linear process that handles open tags and
close tags independently. But web pages are trees, and look like them:
borders and backgrounds visually nest inside one another. To support
that, this chapter switches to *tree-based layout*, where the tree of
elements is transformed into a tree of *layout objects* for the visual
elements of the page. In the process, we'll make our web pages more
colorful with backgrounds.

The layout tree
===============

Right now, our browser lays out an element's open and close tags
separately. Both tags modify global state, like the `cursor_x` and
`cursor_y` variables, but they aren't otherwise connected, and
information about the element as a whole, like its width and height,
is never computed. That makes it pretty hard to draw a background color
behind text. So web browsers structure layout differently.

In a browser, layout is about producing a *layout tree*, whose nodes
are *layout objects*, each associated with an HTML element,[^no-box]
and each with a size and a position. The browser walks the HTML tree
to produce the layout tree, then computes the size and position for
each layout object, and finally draws each layout object to the
screen.

[^no-box]: Elements like `<script>` don't generate layout objects, and
    some elements generate multiple (`<li>` elements have a layout
    object for the bullet point!), but mostly it's one layout object
    each.

Let's start a new class called `BlockLayout`, which will represent a
node in the layout tree. Like our `Element` class, layout objects form
a tree, so they have a list of `children` and a `parent`. We'll also
have a `node` field for the HTML element the layout object corresponds
to.

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
```

I've also added a field for the layout object's previous sibling.
We'll need it to compute sizes and positions.

Each layout object also needs a size and position, which we'll store
in the `width`, `height`, `x`, and `y` fields. But let's leave that
for later. The first job for `BlockLayout` is creating the layout tree
itself.

We'll do that in a new `layout` method, looping over each child _node_
and creating a new child _layout object_ for it.

``` {.python}
class BlockLayout:
    def layout(self):
        previous = None
        for child in self.node.children:
            next = BlockLayout(child, self, previous)
            self.children.append(next)
            previous = next
```

This code is tricky because it involves two trees. The `node` and
`child` are part of the HTML tree; but `self`, `previous`, and `next`
are part of the layout tree. The two trees have similar structure, so
it's easy to get confused. But remember that this code constructs the
layout tree from the HTML tree, so it reads from `node.children` (in
the HTML tree) and writes to `self.children` (in the layout tree).

Anyway, this code creates layout objects for the direct children of
the node in question. Now those children's own `layout` methods can be
called to build the whole tree recursively:

``` {.python}
def layout(self):
    # ...
    for child in self.children:
        child.layout()
```

We'll discuss the base case of the recursion in just a moment, but
first let's ask how it starts. Inconveniently, the `BlockLayout`
constructor requires a parent node, so we need another kind of layout
object at the root.[^or-none] I think of that root as the document
itself, so let's call it `DocumentLayout`:

[^or-none]: You couldn't just use `None` for the parent, because the
root layout object also computes its size and position differently, as
we'll see later this chapter.

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

So we're building a layout tree with one layout object per HTML node,
plus an extra layout object at the root, by recursively calling
`layout`. It looks like this:

<iframe class="widget"
    src="widgets/layout-block-container-example.html?embed=true"
    data-big-height=490 data-small-height=860></iframe>

In this example there are four `BlockLayout` objects, in green, one
per element. There's also a `DocumentLayout` at the root.

The browser must now move on to computing sizes and
positions for each layout object. But before we write that code, we
have to face an important truth: different HTML elements are laid out
differently. They need different kinds of layout objects!

::: {.further}
The layout tree isn't accessible to web developers, so it hasn't been
standardized, and its structure differs between browsers. Even the
names don't match! Chrome calls it a [layout tree][blink-tree],
Safari a [render tree][webkit-tree], and Firefox a [frame tree][gecko-tree].
:::

[blink-tree]: https://developers.google.com/web/updates/2018/09/inside-browser-part3
[webkit-tree]: https://webkit.org/blog/114/webcore-rendering-i-the-basics/
[gecko-tree]: https://wiki.mozilla.org/Gecko:Key_Gecko_Structures_And_Invariants

Layout modes
============

Elements like `<body>` and `<header>` contain blocks stacked
vertically. But elements like `<p>` and `<h1>` contain text and lay
that text out horizontally in lines.[^in-english] Abstracting a bit,
there are two *layout modes*, two ways an element can be laid out
relative to its children: block layout and inline layout.

[^in-english]: In European languages, at least!

We've already got `BlockLayout` for block layout. And actually, we've
already got inline layout too: it's just the text layout we've been
implementing since [Chapter 2](graphics.md). So let's rename the
existing `Layout` class to `InlineLayout` and refactor to match
methods with `BlockLayout`.

Rename `Layout` to `InlineLayout` and rename its constructor to
`layout`. Add a new constructor similar to `BlockLayout`'s:

``` {.python}
class InlineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
```

In the new `layout` method, replace the `tree` argument with the
`node` field:

``` {.python}
class InlineLayout:
    def layout(self):
        # ...
        self.line = []
        self.recurse(self.node)
        self.flush()
```

Let's also initialize `cursor_x` and `cursor_y` from `x` and `y`
instead of `HSTEP` and `VSTEP`, both in `layout` and `flush`:

``` {.python}
class InlineLayout:
    def layout(self):
        # ...
        self.cursor_x = self.x
        self.cursor_y = self.y
        # ...

    def flush(self):
        # ...
        self.cursor_x = self.x
        # ...
```

Inline layout objects aren't going to have any children [for
now](chrome.md), so we don't need any code for that in `layout`. So
the new `InlineLayout` now matches `BlockLayout`'s methods. Just as
with block layout, let's leave actually computing `x` and `y` and
`width` and `height` to later.

Our tree-creation code now needs to use the right layout object for
each element. Normally this is easy: things with text in them get
`InlineLayout`, things with block elements like `<div>` inside get
`BlockLayout`. But what happens if an element contains both? In some
sense, this is an error on the part of the web developer. And just
like with implicit tags in [Chapter 4](html.md), browsers use a repair
mechanism to make sense of the situation. In real browsers,
"[anonymous block boxes][anon-block]" are used, but in our toy browser
we'll implement something a little simpler.

[anon-block]: https://developer.mozilla.org/en-US/docs/Web/CSS/Visual_formatting_model#anonymous_boxes

Here's a list of block elements:[^from-the-spec]

[^from-the-spec]: Taken from the [HTML5 living standard][html5-elts].

[html5-elts]: https://html.spec.whatwg.org/multipage/#toc-semantics

``` {.python}
BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "ol", "ul", "menu", "li",
    "dl", "dt", "dd", "figure", "figcaption", "main", "div",
    "table", "form", "fieldset", "legend", "details", "summary",
]
```

We'll use `BlockLayout` for elements with children in that list, and
`InlineLayout` otherwise. Put that logic in a new `layout_mode`
function:

``` {.python}
def layout_mode(node):
    if isinstance(node, Text):
        return "inline"
    elif node.children:
        for child in node.children:
            if isinstance(child, Text): continue
            if child.tag in BLOCK_ELEMENTS:
                return "block"
        return "inline"
    else:
        return "block"
```

This function additionally makes sure text nodes get inline layout
while empty elements get block layout. Now we can call `layout_mode`
to determine which layout mode to use for each element:

``` {.python}
class BlockLayout:
    def layout(self):
        previous = None
        for child in self.node.children:
            if layout_mode(child) == "inline":
                next = InlineLayout(child, self, previous)
            else:
                next = BlockLayout(child, self, previous)
            self.children.append(next)
            previous = next
        # ...
```

Our layout tree now has a `DocumentLayout` at the root, `BlockLayout`s
at interior nodes, and `InlineLayout`s at the leaves:[^or-empty]

[^or-empty]: Or, the leaf nodes could be `BlockLayout`s for empty
elements.

<iframe class="widget" src="widgets/layout-container-example.html?embed=true" data-big-height="490px" data-small-height="860px"></iframe>

With the layout tree built, we can finally move on to computing the
sizes and positions for the layout objects in the tree.

::: {.further}
In CSS, the layout mode is set by the [`display`
property][mdn-display]. The oldest CSS layout modes, like `inline` and
`block`, are set on the children instead of the parent, which leads to
hiccups like [anonymous block boxes][anon-block]. Newer properties
like `inline-block`, `flex`, and `grid` are set on the parent. This
chapter uses the newer, less confusing convention, even though it's
actually implementing inline and block layout.
:::

[mdn-display]: https://developer.mozilla.org/en-US/docs/Web/CSS/display

Size and position
=================

By default, layout objects are greedy and take up all the horizontal
space they can.[^until-css] So their width is their parent's width:

[^until-css]: In the [next chapter](styles.md), we'll add support for
user styles, which modify these rules and allow setting custom widths,
borders, or padding.

``` {.python}
self.width = self.parent.width
```

And each layout object starts at its parent's left edge:

``` {.python}
self.x = self.parent.x
```

The vertical position of a layout object depends on the position and
height of their previous sibling. If there is no previous sibling,
they start at the parent's top edge:

``` {.python}
if self.previous:
    self.y = self.previous.y + self.previous.height
else:
    self.y = self.parent.y
```

These three computations have to go *before* the recursive call to
each child's `layout` method. After all, a layout object's width
depends on the parent's width; so the width must be computed before
laying out the children. The position is the same: it depends on both
the parent and previous sibling, so the parent has to compute it
before recursing, and when recursing it has to lay out the children in
order.

Height is the opposite. A `BlockLayout` should be tall enough to
contain all of its children, so its height should be the sum of its
children's heights:

``` {.python}
self.height = sum([child.height for child in self.children])
```

Since a `BlockLayout`'s height depends on the height of its children, its height
must be computed after recursing to compute the heights of its children.
Getting this dependency order right is crucial: get it wrong, and some layout
object will try to read a value that hasn't been computed yet, and the browser
will have a bug.

An `InlineLayout` computes `width`, `x`, and `y` the same way, but
`height` is a little different: an `InlineLayout` has to contain all
of the text inside it, which means its height must be computed from
its *y*-cursor.

``` {.python}
class InlineLayout:
    def layout(self):
        # ...
        self.height = self.cursor_y - self.y
```

Again, `width`, `x`, and `y` have to be computed before text is laid
out, but `height` has to be computed after. It's all about that
dependency order.

Finally, even `DocumentLayout` needs some layout code, though since the
document always starts in the same place it's pretty simple:

``` {.python}
class DocumentLayout:
    def layout(self):
        # ...
        self.width = WIDTH - 2*HSTEP
        self.x = HSTEP
        self.y = VSTEP
        child.layout()
        self.height = child.height + 2*VSTEP
```

Note that there's some padding around the contents---`HSTEP` on the
left and right, and `VSTEP` above and below. That's so the text won't
run into the very edge of the window and get cut off.

For all three types of layout object, the order of the steps in the
`layout` method should be the same:

+ When `layout` is called, it first creates a child layout object for
  each child element.
+ Then, `layout` computes the `width`, `x`, and `y` fields, reading from the
  `parent` and `previous` layout objects.
+ Next, the child layout nodes are recursively laid out by calling
  their `layout` methods.
+ Finally, `layout` computes the `height` field, reading from the
  child layout objects.

Sticking to this order is necessary to satisfy the the dependencies
between size and position fields; [Chapter 10](reflow.md) will explore
this topic in more detail.

::: {.further}
Formally, computations on a tree like this can be described by an
[attribute grammar][wiki-atgram]. Attribute grammar engines analyze
dependencies between different attributes to determine the right order
to traverse the tree and calculate each attribute.
:::

[wiki-atgram]: https://en.wikipedia.org/wiki/Attribute_grammar

Using tree-based layout
=======================

Now that our layout objects have size and position information, our
browser should use that information to render the page itself. First,
we need to run layout in the browser's `load` method:

``` {.python}
class Browser:
    def load(self, url):
        headers, body = request(url)
        nodes = HTMLParser(body).parse()
        self.document = DocumentLayout(nodes)
        self.document.layout()
```

[Recall](graphics.html#scrolling-text) that our browser draws a web page
by first collecting a display list and then calling `render` to draw
the things in the list. With tree-based layout, we collect the display
list by recursing down the layout tree.

I think it's most convenient to do that by adding a `draw` function to
each layout object which does the recursion. A neat trick here is to
pass the list itself as an argument, and have the recursive function
append to that list. For `DocumentLayout`, which only has one child,
the recursion looks like this:

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
        self.document.draw(self.display_list)
        self.render()
```

Check it out: your browser is now using fancy tree-based layout! I
recommend pausing to test and debug. Tree-based layout is powerful but
complex, and we're about to add more features. Stable foundations make
for comfortable houses.

::: {.further}
Layout trees are common [in GUI frameworks][widget-tree], but there
are other ways to structure layout, such as constraint-based layout.
TeX's [boxes and glue][boxes-glue] and iOS [auto-layout][auto-layout]
are two examples of this alternative paradigm.
:::

[widget-tree]: https://book.huihoo.com/debian-gnu-linux-desktop-survival-guide/Widget_Tree.html
[boxes-glue]: https://www.overleaf.com/learn/latex/Articles/Boxes_and_Glue:_A_Brief,_but_Visual,_Introduction_Using_LuaTeX
[auto-layout]: https://developer.apple.com/library/archive/documentation/UserExperience/Conceptual/AutolayoutPG/index.html

Backgrounds
===========

Browsers use the layout tree a lot,[^for-what] and one simple and
visually compelling use case is drawing backgrounds.

[^for-what]: For example, in [Chapter 7](chrome.md), we'll use the
size and position of each link to figure out which one the user
clicked on!

Backgrounds are rectangles, so our first task is putting rectangles in
the display list. Conceptually, the display list contains *commands*,
and we want two types of commands:

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

Now `InlineLayout` must add `DrawText` objects to the display
list:[^why-not-change]

[^why-not-change]: Why not change `display_list` to contain `DrawText`
commands directly? You could, but it would be a bit harder to refactor
later.

``` {.python}
class InlineLayout:
    def draw(self, display_list):
        for x, y, word, font in self.display_list:
            display_list.append(DrawText(x, y, word, font))
```

Meanwhile `BlockLayout` can add `DrawRect` commands for backgrounds.
Let's add a gray background to `pre` tags (which are used for code
examples):

``` {.python}
class BlockLayout:
    def draw(self, display_list):
        if self.node.tag == "pre":
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, "gray")
            display_list.append(rect)
        # ...
```

Make sure this code comes *before* the recursive `draw` call on child
layout objects: the background has to be drawn *below* and therefore
*before* the text inside the source block.

With the display list filled out, we need the `render` method to run
each graphics command. Let's add an `execute` method for this. On
`DrawText` it calls `create_text`:

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

Note that `execute` takes the scroll amount as a parameter; this way,
each graphics command does the relevant coordinate conversion itself.
`DrawRect` does the same with `create_rectangle`:

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

By default, `create_rectangle` draws a one-pixel black border, which
for backgrounds we don't want, so make sure to pass `width = 0`:

We still want to skip offscreen graphics commands, so let's add a
`bottom` field to `DrawText` so we know when to skip those:

``` {.python}
def __init__(self, x1, y1, text, font):
    # ...
    self.bottom = y1 + font.metrics("linespace")
```

The browser's `render` method now just uses `top` and `bottom` to
decide which commands to `execute`:

``` {.python}
def render(self):
    self.canvas.delete("all")
    for cmd in self.display_list:
        if cmd.top > self.scroll + HEIGHT: continue
        if cmd.bottom < self.scroll: continue
        cmd.execute(self.scroll, self.canvas)
```

Try your browser on a page---maybe this one---with code snippets on
it. You should see each code snippet set off with a gray background.

::: {.quirk}
On some systems, the `measure` and `metrics` commands are awfully
slow. Adding another call makes things even slower.

Luckily, this `metrics` call duplicates a call in `flush`. If you're
careful you can pass the results of that call to `DrawText` as an
argument.
:::

Here's one more cute benefit of tree-based layout. Thanks to
tree-based layout we now record the height of the whole page. The
browser can use that to avoid scrolling past the bottom of the page:

``` {.python}
def scrolldown(self, e):
    max_y = self.document.height - HEIGHT
    self.scroll = min(self.scroll + SCROLL_STEP, max_y)
    self.render()
```

So that's the basics of tree-based layout! In fact, as we'll see in
the next two chapters, this is just part of the layout tree's role in
the browser. But before we get to that, we need to add some styling
capabilities to our browser.

::: {.further}
The draft CSS [Painting API][mdn-houdini] allows pages to extend the
display list with new types of commands, implemented in JavaScript.
This makes it possible to use CSS for styling with visually-complex
styling provided by a library.
:::

[mdn-houdini]: https://developer.mozilla.org/en-US/docs/Web/API/CSS_Painting_API/Guide

Summary
=======

This chapter was a dramatic rewrite of your browser's layout engine:

- Layout is now tree-based and produces a *layout tree*
- Each node in the tree has one of two different *layout modes*
- Layout computes a size and position for each layout object
- The display list now contains generic commands
- Plus, source code snippets now have backgrounds

Tree-based layout makes it possible to dramatically expand our
browser's styling capabilities. We'll work on that in the [next
chapter](styles.md).

Exercises
=========

*Links Bar*: At the top and bottom of each chapter of this book is a
gray bar naming the chapter and offering back and forward links. It is
enclosed in a `<nav class="links">` tag. Have your browser give this
links bar the light gray background a real browser would.

*Hidden Head*: There's a good chance your browser is still showing
scripts, styles, and page titles at the top of every page you visit.
Make it so that the `<head>` element and its contents are never
displayed. Those elements should still be in the HTML tree, but not in
the layout tree.

*Bullets*: Add bullets to list items, which in HTML are `<li>` tags.
You can make them little squares, located to the left of the list item
itself. Also indent `<li>` elements so the text inside the element is
to the right of the bullet point.

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

*Run-ins*: A "run-in heading" is a heading that is drawn as part of
the next paragraph's text.[^like-these] Modify your browser to render
`<h6>` elements as run-in headings. You'll need to implement the
previous exercise on anonymous block boxes, and then add a special
case for `<h6>` elements.

[^like-these]: The exercise names in this section could be considered
run-in headings. But since browser support for the `display: run-in`
property [is poor](https://caniuse.com/run-in), this book actually
doesn't use it; the headings are actually embedded in the next
paragraph.
