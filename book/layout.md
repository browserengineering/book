---
title: Laying Out Pages
chapter: 5
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

Let's start by looking how the existing `Layout` class is used:

``` {.python expected=False}
class Browser:
    def load(self, url):
        # ...
        self.display_list = Layout(self.nodes).display_list
        #...
```

Here, a `Layout` object is created briefly and then thrown away.
Let's instead make it the beginning of our layout tree by storing it
in a `Browser` field:

``` {.python expected=False}
class Browser:
    def load(self, url):
        # ...
        self.document = Layout(self.nodes)
        self.document.layout()
        self.display_list = self.document.display_list
        #...
```

Note that I've renamed the `Layout` constructor to a `layout` method,
so that constructing a layout object and actually laying it out can be
different steps. The constructor now just stores the node it was
passed:

``` {.python replace=Layout/BlockLayout}
class Layout:
    def __init__(self, node):
        self.node = node
```

So far, we still don't have a tree---we just have a single `Layout`
object. To make it into a tree, we'll need add child and parent
pointers. I'm also going to add a pointer to the previous sibling,
because that'll be useful for computing sizes and positions later:

``` {.python replace=Layout/BlockLayout}
class Layout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
```

That said, requiring a `parent` and `previous` element now makes it
tricky to construct a `Layout` object in `Browser`, since the root of
the layout tree obviously can't have a parent. To rectify that, let me
add a second kind of layout object to serve as the root of the layout
tree.[^or-none] I think of that root as the document itself, so let's
call it `DocumentLayout`:

[^or-none]: I don't want to just pass `None` for the parent, because
the root layout object also computes its size and position
differently, as we'll see later this chapter.

``` {.python replace=%20Layout/%20BlockLayout dropline=display_list}
class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.children = []

    def layout(self):
        child = Layout(self.node, self, None)
        self.children.append(child)
        child.layout()
        self.display_list = child.display_list
```

Note an interesting thing about this new `layout` method: its role is
to _create_ the child layout objects, and then _recursively_ call its
children's `layout` methods. This is a common pattern for constructing
trees, and we'll be seeing it a lot throughout this book.

Now when we construct a `DocumentLayout` object inside `load`, we'll
be building a tree! A very short tree, more of a stump for now, but
it's something!

By the way, since we now have `DocumentLayout`, let's rename `Layout`
so it's less ambiguous. I like `BlockLayout` as a name, because we
ultimately want `Layout` to represent a block of text, like a
paragraph or a heading:

``` {.python}
class BlockLayout:
    # ...
```

Make sure to rename the `Layout` constructor call in `DocumentLayout`
as well. Test your browser and make sure that after all of these
refactors, everything still works.

::: {.further}
The layout tree isn't accessible to web developers, so it hasn't been
standardized, and its structure differs between browsers. Even the
names don't match! Chrome calls it a [layout tree][blink-tree],
Safari a [render tree][webkit-tree], and Firefox a [frame tree][gecko-tree].
:::

[blink-tree]: https://developers.google.com/web/updates/2018/09/inside-browser-part3
[webkit-tree]: https://webkit.org/blog/114/webcore-rendering-i-the-basics/
[gecko-tree]: https://wiki.mozilla.org/Gecko:Key_Gecko_Structures_And_Invariants


Block layout
============

So far, we've focused on text layout---and text is laid out
horizontally in lines.[^in-english] But web pages are really
constructed out of larger blocks, like headings, paragraphs, and
menus, that are stacked vertically one after another. We need to add
support for this kind of layout to our browser, and the way we're
going to do that involves expanding on the layout tree we've already
built.

[^in-english]: In European languages, at least!

The core idea is that we'll have a whole tree of `BlockLayout` objects
(with a `DocumentLayout` at the root). Some will represent leaf blocks
that contain text, and they'll lay out their contents the way we've
already implemented. But there will also be new, intermediate
`BlockLayout`s with `BlockLayout` children, and they will stack their
children vertically.

To create these intermediate `BlockLayout` children, we can use a loop
like this:

``` {.python replace=layout_intermediate/layout}
class BlockLayout:
    def layout_intermediate(self):
        previous = None
        for child in self.node.children:
            next = BlockLayout(child, self, previous)
            self.children.append(next)
            previous = next
```

I've called this method `layout_intermediate`, but only so you can add
it to the code right away and then compare it with the existing
`recurse` method.

This code is tricky, so read it carefully. It involves two trees: the
HTML tree, which `node` and `child` point to; and the layout tree,
which `self`, `previous`, and `next` point to. The two trees have
similar structure, so it's easy to get confused. But remember that
this code constructs the layout tree from the HTML tree, so it reads
from `node.children` (in the HTML tree) and writes to `self.children`
(in the layout tree).

So we have two ways to lay out an element: either calling `recurse`
and `flush`, or this `layout_intermediate` function. To determine
which one a layout object should use, we'll need to know what kind
of content its HTML node contains: text and text-related tags like
`<b>`, or blocks like `<p>` and `<h1>`. That function looks something
like this:

``` {.python}
def layout_mode(node):
    if isinstance(node, Text):
        return "inline"
    elif node.children:
        if any([isinstance(child, Element) and \
                child.tag in BLOCK_ELEMENTS
                for child in node.children]):
            return "block"
        else:
            return "inline"
    else:
        return "block"
```

Here the list of `BLOCK_ELEMENTS` is basically what you expect, a list
of all the tags that describe parts of a page instead of
formatting:[^from-the-spec]

[^from-the-spec]: Taken from the [HTML living standard][html5-elts].

[html5-elts]: https://html.spec.whatwg.org/multipage/#toc-semantics

``` {.python}
BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "pre", "blockquote",
    "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
    "figcaption", "main", "div", "table", "form", "fieldset",
    "legend", "details", "summary"
]
```

Our `layout_mode` function has to handle one tricky case, where a node
contains both block children like a `<p>` element but also text
children like a text node or a `<b>` element. I've chosen to use block
mode in this case, but it's probably best to think of this as a kind
of error on the part of the web developer. And just like with implicit
tags in [Chapter 4](html.md), we use a repair mechanism to make sense
of the situation.[^anon-block]

[^anon-block]: In real browsers, that repair mechanism is called
"[anonymous block boxes][anon-block]" and is more complex than what's
described here.

[anon-block]: https://developer.mozilla.org/en-US/docs/Web/CSS/Visual_formatting_model#anonymous_boxes

So now `BlockLayout` can determine what kind of layout to do based on
the `layout_mode` of its HTML node:

``` {.python}
class BlockLayout:
    def layout(self):
        mode = layout_mode(self.node)
        if mode == "block":
            previous = None
            for child in self.node.children:
                next = BlockLayout(child, self, previous)
                self.children.append(next)
                previous = next
        else:
            self.display_list = []

            self.cursor_x = 0
            self.cursor_y = 0
            self.weight = "normal"
            self.style = "roman"
            self.size = 16

            self.line = []
            self.recurse(self.node)
            self.flush()
```

Finally, since `BlockLayout`s can now have children, the `layout`
method next needs to recursively call `layout` so those children can
construct their children, and so on recursively:

``` {.python}
class BlockLayout:
    def layout(self):
        # ...
        for child in self.children:
            child.layout()
```

We also need to gather their `display_list` fields into a single
array:

``` {.python expected=False}
class BlockLayout:
    def layout(self):
        # ...
        for child in self.children:
            self.display_list.extend(child.display_list)
```

Our browser is now constructing a whole tree of `BlockLayout` objects;
in fact, if you add a `print_tree` call to `Browser`'s `load` method,
you'll see that large web pages like this chapter produce large and
complex layout trees!

::: {.widget big-height=490px small-height=860px}
    layout-container-example.html?embed=true
:::

Oh, you might also notice that the text on these web pages is now
totally unreadable, because it's all overlapping at the top of the
page. Let's fix that next.

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

In the [previous chapter](html.md), the `Layout` object was
responsible for the whole web page, so it just laid out its content
starting at the top of the page. Now that we have multiple
`BlockLayout` objects each containing a different paragraph of text,
we're going to need to do things a little differently, computing a
size and position for each layout object independently.

Let's start with `cursor_x` and `cursor_y`. Instead of having them
denote absolute positions on the page, let's make them relative to the
`BlockLayout` itself; they now need to start from `0` instead of
`HSTEP` and `VSTEP`, both in `layout` and `flush`:

``` {.python}
class BlockLayout:
    def layout(self):
        else:
            self.cursor_x = 0
            self.cursor_y = 0

    def flush(self):
        # ...
        self.cursor_x = 0
        # ...
```

Since these fields are now relative, we'll need to add the block's `x`
and `y` position in `flush` when computing the display list:

``` {.python}
class BlockLayout:
    def flush(self):
        # ...
        for rel_x, word, font in self.line:
            x = self.x + rel_x
            y = self.y + baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))
        # ...
```

Similarly, to wrap lines, we can't compare `cursor_x` to `WIDTH`,
because `cursor_x` is a relative measure while `WIDTH` is an absolute
measure; instead, we'll wrap lines when `cursor_x` reaches the block's
`width`:

``` {.python}
class BlockLayout:
    def text(self, node):
        for word in node.text.split():
            # ...
            if self.cursor_x + w > self.width:
                # ...
            # ...
```

So now that leaves us with the problem of computing these `x`, `y`,
and `width` fields. Let's recall that `BlockLayout`s represent blocks
of text like paragraphs or headings, and are stacked vertically one
atop another. That means each one starts at its parent's left edge:

``` {.python}
class BlockLayout:
    def layout(self):
        self.x = self.parent.x
        # ...
```

Its vertical position depends on the position and height of their
previous sibling. If there is no previous sibling, they start at the
parent's top edge:

``` {.python}
class BlockLayout:
    def layout(self):
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y
        # ...
```

Note that in each of these cases, to compute one block's `x` and `y`,
the `x` and `y` of its parent block must _already_ have been computed.
That means these computations have to go *before* the recursive
`layout` call, so those children can compute their `x` and `y` based
on this block's `x` and `y`. Similarly, since the `y` position of a
block depends on its previous sibling's `y` position, the recursive
`layout` calls have to start at the first sibling and iterate through
the list forward---which is how we've already done it, but which will
be an important constraint in [later chapters](invalidation.md).

Now we'll need compute widths and heights. Width is easy: blocks are
as wide as their parents:[^until-css]

[^until-css]: In the [next chapter](styles.md), we'll add support for
author-defined styles, which in real browsers modify these layout
rules by setting custom widths or changing how *x* and *y* position
are computed.

``` {.python}
class BlockLayout:
    def layout(self):
        self.width = self.parent.width
        # ...
```

Height, meanwhile, is a little tricky. A `BlockLayout` that contains
other blocks should be tall enough to contain all of its children, so
its height should be the sum of its children's heights:

``` {.python}
class BlockLayout:
    def layout(self):
        # ...
        if mode == "block":
            self.height = sum([
                child.height for child in self.children])
```

However, a `BlockLayout` that contains text doesn't have children;
instead, it needs to be tall enough to contain all its text, which we
can conveniently read off of `cursor_y`:[^why-two-fields]

[^why-two-fields]: Since the height is just equal to `cursor_y`, why
    not rename `cursor_y` to `height` instead? You could, it would
    work fine, but I would rather not. As you can see from, say, the
    `y` computation, the `height` field is a public field, read by
    other layout objects to compute their positions. As such I'd
    rather make sure it _always_ has the right value, whereas
    `cursor_y` changes as we lay out a paragraph of text and therefore
    sometimes has the "wrong" value. Keeping these two fields separate
    avoids a whole class of nasty bugs where the `height` field is
    read "too soon" and therefore gets the wrong value.

``` {.python}
class BlockLayout:
    def layout(self):
        # ...
        else:
            self.height = self.cursor_y
```

Let's think again about dependencies. Height has the opposite
dependencies compared to `x`, `y`, and `width`: the `height` of a
block depends on its children's heights. While `x`, `y`, and `width`
must be computed _before_ the recursive call, `height` has to be
computed _after_, at the very end of `layout`.

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

+ When `layout` is called, it first computes the `width`, `x`, and `y`
  fields, reading from the `parent` and `previous` layout objects.
+ Next, it creates a child layout object for each child element.
+ Then, the child layout nodes are recursively laid out by calling
  their `layout` methods.
+ Finally, `layout` computes the `height` field, reading from the
  child layout objects.

You can see these steps in action in this widget:

::: {.widget height=204}
    lab5-propagate.html
:::

This kind of dependency reasoning is crucial to layout and more
broadly to any kind of computation on trees. If you get the order of
operations wrong, some layout object will try to read a value that
hasn't been computed yet, and the browser will have a bug. We'll come
back to this issue of dependencies [later](invalidation.md), where it
will become even more important.

Anyway, with all of the sizes and positions now computed correctly,
you should see the browser now correctly display all of the text on
the page.

::: {.further}
Formally, computations on a tree like this can be described by an
[attribute grammar][wiki-atgram]. Attribute grammar engines analyze
dependencies between different attributes to determine the right order
to traverse the tree and calculate each attribute.
:::

[wiki-atgram]: https://en.wikipedia.org/wiki/Attribute_grammar

Recursive painting
==================

Our `layout` method is now doing quite a bit of work: computing sizes
and positions; creating child layout objects; recursively laying out
those child layout objects; and aggregating the display lists so the
text can be drawn to the screen. This is a bit messy, so let's take a
moment to extract just one part of this, the display list part. Along
the way, we can stop copying the display list contents over and over
again as we go up the layout tree.

I think it's most convenient to do that by adding a `paint` function
to each layout object, which appends any of its own layout objects to
the display list and then recursively paints the child layouts. A neat
trick here is to pass the list itself as an argument, and have the
recursive function append to that list. For `DocumentLayout`, which
only has one child, the recursion looks like this:

``` {.python}
class DocumentLayout:
    def paint(self, display_list):
        self.children[0].paint(display_list)
```

You can now delete the line that computes a `DocumentLayout`'s
`display_list` field.

For a `BlockLayout` with multiple children, `paint` is called on each
child:

``` {.python}
class BlockLayout:
    def paint(self, display_list):
        for child in self.children:
            child.paint(display_list)
```

Again, delete the line that computes a `BlockLayout`'s `display_list`
field by copying from child layout objects.

Finally for a `BlockLayout` object with text inside, we need to copy
over the `display_list` field that it computes during `recurse` and
`flush`:

``` {.python expected=False}
class BlockLayout:
    def paint(self, display_list):
        display_list.extend(self.display_list)
```

Now the browser can use `paint` to collect its own `display_list`
variable:

``` {.python}
class Browser:
    def load(self, url):
        # ...
        self.display_list = []
        self.document.paint(self.display_list)
        self.draw()
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
[boxes-glue]: https://www.overleaf.com/learn/latex/Articles/Boxes_and_Glue%3A_A_Brief%2C_but_Visual%2C_Introduction_Using_LuaTeX
[auto-layout]: https://developer.apple.com/library/archive/documentation/UserExperience/Conceptual/AutolayoutPG/index.html

Backgrounds
===========

Browsers use the layout tree a lot,[^for-what] and one simple and
visually compelling use case is drawing backgrounds.

[^for-what]: For example, in [Chapter 7](chrome.md), we'll use the
size and position of each link to figure out which one the user
clicked on.

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

Now `BlockLayout` must add `DrawText` objects to the display
list:[^why-not-change]

[^why-not-change]: Why not change the `display_list` field inside an
`BlockLayout` to contain `DrawText` commands directly? I suppose you
could, but I think it's cleaner this way, with all of the draw
commands created in one place.

``` {.python}
class BlockLayout:
    def paint(self, display_list):
        for x, y, word, font in self.display_list:
            display_list.append(DrawText(x, y, word, font))
        # ...
```

Note that we must add the block's `x` and `y`, since the positions in
the display list are relative to the block's position.

But it can also add `DrawRect` commands for backgrounds. Let's add
a gray background to `pre` tags (which are used for code examples):

``` {.python}
class BlockLayout:
    def paint(self, display_list):
        if isinstance(self.node, Element) and self.node.tag == "pre":
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, "gray")
            display_list.append(rect)
        # ...
```

Make sure this code comes *before* the loop that adds `DrawText`
objects and *before* the recursion into child layout objects: the
background has to be drawn *below* and therefore *before* any
contents. This is again a kind of dependency reasoning with tree
traversals!

With the display list filled out, we need the `paint` method to run
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

The browser's `draw` method now just uses `top` and `bottom` to
decide which commands to `execute`:

``` {.python}
class Browser:
    def draw(self):
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
    self.draw()
```

So those are the basics of tree-based layout! In fact, as we'll see in
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

::: {.signup}
:::

Outline
=======

The complete set of functions, classes, and methods in our browser 
should look something like this:

::: {.cmd .python .outline html=True}
    python3 infra/outlines.py --html src/lab5.py
:::

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
Specifically, modify `BlockLayout` so it can be passed a sequence of
sibling nodes, instead of a single node. Then, modify the algorithm
that constructs the layout tree so that any sequence of text-like
elements gets made into a single `BlockLayout`.

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
