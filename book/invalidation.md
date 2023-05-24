---
title: Reusing Previous Computations
chapter: 16
prev: embeds
next: skipped
...

So far, we've worked on animation performance by improving our
browser's graphics subsystem. But that hasn't helped animations and
interactions that affect layout, like user- or JavaScript-driven
edits. Luckily, Yet like compositing enabled smooth animations by
avoiding redundant raster work, we can avoid redundant layout work
using a technique called invalidation.

Editing Content
===============

In [Chapter 13](animations.md), we used compositing smoothly animate
CSS properties like `transform` or `opacity`. However, other CSS
properties like `width` can't be animated in this way. That's because
these _layout-inducing_ animations change not only the _display list_
but also the _layout tree_. Layout-inducing animations are a bad
practice for this reason. Unfortunately, plenty of other interactions
affect the layout tree and yet need to be as smooth as possible.

One good example is editing text. People type pretty quickly, so even
a few frames' delay is very distracting. But editing changes the HTML
tree and therefore requires a new layout tree that reflects the new
text. But on large pages (like this one) constructing the layout tree
can take quite a while. Try, for example, typing into this input box
from our toy browser:

<input style="width:100%"/>

Typing into an `input` element could be special-cased,[^no-resize] but
there are other text editing APIs. For example, the `contenteditable`
attribute makes any element editable:

[^no-resize]: For example, the `input` element doesn't change size as
    you type, and the text in the `input` element doesn't get its own
    layout object.

::: {.example contenteditable=true}
Click on this <i>formatted</i> <b>text</b> to edit it.
:::

Let's implement `contenteditable` in our browser---it will make a good
test of invalidation. To begin with, we need to make elements with a
`contenteditable` property focusable:

``` {.python}
def is_focusable(node):
    # ...
    elif "contenteditable" in node.attributes:
        return True
    # ...
```

Once we're focused on an editable node, key presses should add text to
it. A real browser would need to handle cursor movement and all kinds
of complications, but I'm just going to add characters to the last
text node in the editable element. First we need to find that element:

``` {.python}
class Frame:
    def keypress(self, char):
        # ...
        elif self.tab.focus and "contenteditable" in self.tab.focus.attributes:
            text_nodes = [
               t for t in tree_to_list(self.tab.focus, [])
               if isinstance(t, Text)
            ]
            if text_nodes:
                last_text = text_nodes[-1]
            else:
                last_text = Text("", self.tab.focus)
                self.tab.focus.children.append(last_text)
```

Note that if the editable element has no text children I append a new
one. Now we need to add the typed character to this element:

``` {.python}
class Frame:
    def keypress(self, char):
        elif self.tab.focus and "contenteditable" in self.tab.focus.attributes:
            # ...
            last_text.text += char
            self.set_needs_render()
```

This is enough to make editing work, but it's convenient to also draw
a cursor confirm that the element is focused and show where edits will
go. Let's do that in `BlockLayout`:

``` {.python}
class BlockLayout:
    def paint(self, display_list):
        # ...
        if self.node.is_focused and "contenteditable" in self.node.attributes:
            text_nodes = [
                t for t in tree_to_list(self, [])
                if isinstance(t, TextLayout)
            ]
            if text_nodes:
                cmds.append(DrawCursor(text_nodes[-1], text_nodes[-1].width))
            else:
                cmds.append(DrawCursor(self, 0))
        # ...
```

Here, `DrawCursor` is just a wrapper around `DrawLine`:

``` {.python}
def DrawCursor(elt, width):
    return DrawLine(elt.x + width, elt.y, elt.x + width, elt.y + elt.height)
```

We might as well also use this wrapper in `InputLayout`:

``` {.python}
class InputLayout(EmbedLayout):
    def paint(self, display_list):
        if self.node.is_focused and self.node.tag == "input":
            cmds.append(DrawCursor(self, self.font.measureText(text)))
```

You should now be able to edit the examples on this page in your toy
browser---but if you try it, you'll see that editing is extremely
slow, with each character taking hundreds of milliseconds to type.

Idempotence
===========

At a high level, edits are slow is because each edit recomputes
layout---and on a large page like this one, that takes our browser
many, many milliseconds. But is recomputing layout necessary? Adding a
single letter to a single word on a single line of the page doesn't
exactly change the page dramatically: almost everything stays in the
exact same place. Recomputing layout on every edit wastes a lot of
time recomputing the exact the same layout we already had.

So why do we recompute layout? Basically, `render` creates a brand new
layout tree, every time we need to recompute layout:

``` {.python file=lab15}
class Frame:
    def render(self):
        if self.needs_layout:
            self.document = DocumentLayout(self.nodes, self)
            self.document.layout(self.frame_width, self.tab.zoom)
            # ...
```

By creating a new tree, we're throwing away all of the old layout
information, even those bits that were already correct. Invalidation
begins with not doing that.

But before jumping right to coding, let's review how layout objects
are created. Search your browser code for `Layout`, which all layout
class names end with. You should see that layout objects are created
only in a few places:

- `DocumentLayout` objects are created by the `Tab` in `render`
- `BlockLayout` objects are created by either:
  - A `DocumentLayout`, in `layout`
  - A `BlockLayout`, in `layout`
- `LineLayout` objects are created by `BlockLayout` in `new_line`
- All others are created by `BlockLayout` in `add_inline_child`

We want to _avoid_ creating layout objects, instead reusing them
whenever possible.

Let's start with `DocumentLayout`. It's created in `render`, and its
two parameters, `nodes` and `self`, are the same every time. This
means every execution of this line of code creates effectively
identical objects.[^side-effects] That seems wasteful, so let's create
the `DocumentLayout` just once, in `load`:

[^side-effects]: This wouldn't be true if the `DocumentLayout`
    constructor had side-effects or read global state, but it doesn't
    do that.

``` {.python}
class Frame:
    def load(self, url, body=None):
        # ...
        self.document = DocumentLayout(self.nodes, self)
        self.set_needs_render()

    def render(self):
        if self.needs_layout:
            self.document.layout(self.frame_width, self.tab.zoom)
            # ...
```

The `DocumentLayout` then constructs a `BlockLayout`:

``` {.python file=lab15}
class DocumentLayout:
    def layout(self, width, zoom):
        child = BlockLayout(self.node, self, None, self.frame)
        # ...
```

Again, the constructor parameters cannot change, so again we can skip
re-constructing this layout object, with code like this:

``` {.python replace=.append(child)/%20%3d%20[child]}
class DocumentLayout:
    def layout(self, width, zoom):
        if not self.children:
            child = BlockLayout(self.node, self, None, self.frame)
        else:
            child = self.children[0]
        # ...
```

However, if you try them, these changes don't actually work, because
reusing a layout object also means we are running `layout` multiple
times on the same object. That's not what we were doing before, and it
doesn't work. For example, after the `DocumentLayout` creates its
child `BlockLayout`, it *appends* it to the `children` array:

``` {.python}
class DocumentLayout:
    def layout(self, width, zoom):
        # ...
        self.children.append(child)
        # ...
```

If we do layout more than once, the same `BlockLayout` will end up in
the `children` array more than once, causing all sorts of strange
problems. The layout tree wouldn't even be a tree any more!

The core issue here is what's called *idempotence*: we need repeated
calls to `layout` to work. More formally, a function is idempotent if
calling it twice in a row with the same inputs and dependencies yields
the same result. Assignments to fields are idempotent---you can assign
a field the same value twice without changing it---but methods like
`append` aren't.

So before we move on, we need to replace any non-idempotent methods
like `append` with idempotent ones like assignment:

``` {.python}
class DocumentLayout:
    def layout(self, width, zoom):
        # ...
        self.children = [child]
        # ...
```

Likewise in `BlockLayout`, which creates other layout objects and
`append`s them to its `children` array. Here, the easy fix is to reset
the `children` array at the top of `layout`:

``` {.python}
class BlockLayout:
    def layout(self):
        self.children = []
        # ...
```

This makes the `BlockLayout`'s `layout` function idempotent because
each call will recreate the `children` array the same way each time.

Let's check all other `layout` methods for idempotency by reading them
and noting any non-idempotent method calls. I found:

- In `new_line`, `BlockLayout` will append to its `children` array;
- In `text` and `input`, `BlockLayout` will append to the `children`
  array of some `LineLayout` child
- In `text` and `input`, `BlockLayout` will call `get_font`, as will
  the `TextLayout` and `InputLayout` methods
- Basically every layout method calls `display_px`

Luckily, the `new_line` and `add_inline_child` methods are only called
through `layout`, which resets the `children` array. Meanwhile,
`get_font` acts as a cache, so multiple calls return the same font
object, and `display_px` just does math, so always returns the same
result given the same inputs. So all of our `layout` methods are now
idempotent, and the browser should work correctly again.

Idempotency means it doesn't matter _how many_ times a function is
called, and that gives us the freedom to skip redundant work. That
makes it the foundation for the rest of this chapter, which is all
about knowing what work is truly redundant.

::: {.further}

:::


Dependencies
============

So far, we've only looked at one place where layout objects are
created. Let's look at another: `BlockLayout`s created by
`BlockLayout`s in their `layout` method. Here's the relevant code;
it only runs in block layout mode:

``` {.python file=lab15 dropline=self.children%20%3d}
class BlockLayout:
    def layout(self):
        self.children = []
        # ...
        if mode == "block":
            previous = None
            for child in self.node.children:
                next = BlockLayout(child, self, previous, self.frame)
                self.children.append(next)
                previous = next
        # ...
```

Here, the arguments to `BlockLayout` are a little more complicated
than the ones passed in `DocumentLayout`. The second argument, `self`,
is never assigned to, but `child` and `previous` both contain elements
read from `node.children`, and that `children` array can change---as a
result of `contenteditable` edits or, potentially, `innerHTML` calls.
Moreover, in order to even run this code, the node's `layout_mode` has
to be `"block"`, and `layout_mode` itself also reads the node's
`children`.[^and-tags]

[^and-tags]: It also looks at the node's `tag` and the node's
    childrens' `tag`s, but a node's `tag` can't change, so we don't
    need to have a dirty flag for them.
    
We want to avoid redundant `BlockLayout` creation, but recall that
idempotency means that calling a function again _with the same inputs
and dependencies_ yields the same result. Here, the inputs can change,
so we can only avoid redundant re-execution _if the node's `children`
field hasn't changed_.

To do that, we're going to use a dirty flag:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.dirty_children = True
```

We've seen dirty flags before---like `needs_layout` and
`needs_draw`---but layout is more complex and we're going to need to
think about dirty flags a bit more rigorously.

Every dirty flag protects a certain field; this one protects the
`children` field for a `BlockLayout`. A dirty flag has a certain life
cycle. First, it is set to `True` when a change occurs, marking the
protected field as unusable. Then, before using the protected field,
the dirty flag must be checked. Finally, once the field is up to date,
the flag is reset to `False`.

Let's implement this for the `dirty_children` flag, starting with
setting the flag. Dirty flags start out set, just like in the code
above, but they also have to be set if any _dependencies_ of the
fields they protect change. In this case, the dirty flag protects the
`children` field of a `BlockLayout`, which in turn depends on the
`children` field of the associated `Element`. That means that any time
an `Element`'s `children` field is modified, we need to set the flag:

``` {.python}
class JSContext:
    def innerHTML_set(self, handle, s, window_id):
        # ...
        elt.layout_object.dirty_children = True
```

Likewise, we need to set the dirty flag any time we modify the `text`
of a `Text` object, since that can also affect the `children` of a
`BlockLayout`:

``` {.python}
class Frame:
    def keypress(self, char):
        elif self.tab.focus and "contenteditable" in self.tab.focus.attributes:
            # ...
            self.tab.focus.layout_object.dirty_children = True
```

It's important to make sure we set the dirty flag for _all_
dependencies of the protected fields. Otherwise, we'll fail to
recompute the protected fields, causing unpredictable layout glitches.

Next, we need to check the dirty flag before using any field that it
protects. `BlockLayout` uses its `children` field in three places: to
recursively call `layout` on all its children; to compute its
`height`; and to `paint` itself. Let's add a check in each place:

``` {.python replace=self.height/new_height}
class BlockLayout:
    def layout(self):
        # ...
        
        assert not self.dirty_children
        for child in self.children:
            child.layout()
            
        assert not self.dirty_children
        self.height = sum([child.height for child in self.children])

    def paint(self, display_list):
        assert not self.dirty_children
        # ...
```

Adding these checks before using any protected field helps avoid bugs
caused by computing fields in the wrong order. It's very easy to
compute some field before computing its dependencies---a problem we
talked about in [Chapter 5](layout.md)---which causes the
characteristic invalidation problem of some change needing multiple
layouts to "take".

Finally, we can reset the flag when we're done recomputing the
protected field. In this case, we want to reset the dirty flag when
we've recomputed the `children` array, meaning right after that `if`
statement:

``` {.python}
class BlockLayout:
    def layout(self):
        if mode == "block":
            # ...
        else:
            # ...
        self.dirty_children = False
```

Before going further, rerun your browser and test it on a web page
with `contenteditable`. The browser should run like normal without
triggering the assertion.

With the `dirty_children` flag properly set and reset, we can now use
it to avoid redundant work. Right now `layout` recreates the
`children` array every time, but it doesn't need to if the children
array isn't dirty. Let's find the line at the top of `layout` that
resets the `children` array, and move it into the two branches of the
`if` statement:

``` {.python}
class BlockLayout:
    def layout(self):
        if mode == "block":
            self.children = []
            # ...
        else:
            self.children = []
            # ...
```

Now the block layout mode case has all the code to compute the
`children` array. We can skip it if the `children` array is up to
date:

``` {.python}
class BlockLayout:
    def layout(self):
        if mode == "block":
            if self.dirty_children:
                # ...
```

Try this out, perhaps after throw a `print` statement inside that
inner-most `if` conditional. You should see see that only
`BlockLayout`s corresponding to changed nodes are re-created.

::: {.further}

:::


Protected fields
================

Dirty flags, like `dirty_children`, are the traditional way to write a
browser layout engine, but they have some downsides. As you've seen,
using them correctly means paying careful attention to how any given
field is computed and used, and tracking dependencies between various
computations across the browser. In our simple browser, that's pretty
doable by hand, but a real browser's layout system is much more
complex, and mistakes become impossible to avoid.

So let's try to put a more user-friendly face on dirty flags. As a
first step, let's try to combine a dirty flag and the field it
protects into a single object:

``` {.python}
class ProtectedField:
    def __init__(self):
        self.value = None
        self.dirty = True
```

We can pretty easily replace our existing dirty flag with this simple
abstraction:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.children = ProtectedField()
        # ...
```

On key press and `innerHTML`, we need to set the dirty flag. Let's put
that behind a method; I'll say that we `mark` a dependent field to set
its dirty flag:

``` {.python}
class ProtectedField:
    def mark(self):
        if self.dirty: return
        self.dirty = True
```

Then call the method, here and in `innerHTML_set`:

``` {.python}
class Frame:
    def keypress(self, char):
        elif self.tab.focus and "contenteditable" in self.tab.focus.attributes:
            # ...
            self.tab.focus.layout_object.children.mark()
```

To reset the dirty flag, let's make the caller pass in a new value for
the field. This guarantees that the dirty flag and the value are
updated together:

``` {.python}
class ProtectedField:
    def set(self, value):
        self.value = value
        self.dirty = False
```

Using this method in `BlockLayout` will require changing `BlockLayout`
to first add all the children to a local variable, and then `set` that
variable into the `children` field:

``` {.python}
class BlockLayout:
    def layout(self):
        if mode == "block":
            if self.children.dirty:
                children = []
                previous = None
                for child in node_children:
                    next = BlockLayout(child, self, previous, self.frame)
                    children.append(next)
                    previous = next
                self.children.set(children)
```

Finally, when it comes time to use the `children` field, the
`ProtectedField` can check that it isn't dirty:

``` {.python}
class ProtectedField:
    def get(self):
        assert not self.dirty
        return self.value
```

Now we can use `get` to read the `children` field in `layout` and in
lots of other places besides:

``` {.python}
class BlockLayout:
    def layout(self):
        # ...
        for child in self.children.get():
            child.layout()

        self.height = sum([child.height for child in self.children.get()])
```

`ProtectedField` is a nice convenience: it frees us from remembering
that two fields (`children` and `dirty_children`) go together, and it
makes sure we always check and reset dirty bits when we're supposed
to.

::: {.further}

:::


Recursive dirty bits
====================

Armed with the `ProtectedField` class, let's take a look at how a
`BlockLayout` element creates `LineLayout`s and their children. It all
happens inside this `if` statement:

``` {.python}
class BlockLayout:
    def layout(self):
        if mode == "block":
            # ...
        else:
            self.children = []
            self.new_line()
            self.recurse(self.node)
```

Basically, these lines handle line wrapping: they check widths, create
new lines, and so on. We'd like to skip this work if the `children`
field isn't dirty, but to do that, we first need to make sure that
everything `new_line` and `recurse` read can mark the `children`
field. Let's start with `zoom`, which almost every method reads.

Zoom is initially set on the `DocumentLayout`, so let's start there:

``` {.python}
class DocumentLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.zoom = ProtectedField()
        # ...

    def layout(self, width, zoom):
        # ...
        self.zoom.set(zoom)
        # ...
```

That's easy enough, but when we get to `BlockLayout` it gets more
complex. Naturally, each `BlockLayout` has its own `zoom` field, which
we can protect:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.zoom = ProtectedField()
        # ...
```

However, in the `BlockLayout`, the `zoom` field comes from its
parent's `zoom` field. We might be tempted to write something like
this:

``` {.python}
class BlockLayout:
    def layout(self):
        if self.zoom.dirty:
            parent_zoom = self.parent.zoom.get()
            self.zoom.set(parent_zoom)
        # ...
```

However, recall that with dirty bits we must always think about
setting them, checking them, and resetting them. The `get` method
automatically checks the dirty bits, and the `set` method
automatically resets them, but who *sets* the `zoom` dirty bit?

Generally, we need to set a dirty bit when something it depends on
changes. That's why we call `mark` in the `innerHTML_set` and
`keypress` handlers: those change the DOM tree, which the layout
tree's `children` field depends on. So since a child's `zoom` field
depends on its parents' `zoom` field, we need to mark all the children
when the `zoom` field changes:

``` {.python.example}
class BlockLayout:
    def layout(self):
        if self.zoom.dirty:
            # ...
            for child in self.children.get():
                child.zoom.mark()
```

That said, doing this every time we modify any protected field is a
pain, and it's easy to forget a dependency. We want to make this
seamless: we want writing to a field to automatically mark all the
fields that depend on it.

To do that, we're going to need to track dependencies at run time:

``` {.python}
class ProtectedField:
    def __init__(self, eager=False):
        # ...
        self.depended_on = set()
```

We can mark all of the dependencies with `notify`:

``` {.python}
class ProtectedField:
    def notify(self):
        for field in self.depended_on:
            field.mark()
```

However, you typically need to `notify` dependants when you compute a
new value for some other field, and we can make that automatic:

``` {.python}
class ProtectedField:
    def set(self, value):
        self.notify()
        self.value = value
        self.dirty = False
```

Now we can establish dependencies once and automatically have
dependant fields get marked:

``` {.python.example}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.parent.zoom.depended_on.add(self.children)
```

That's definitely less error-prone, but it'd be even better if we
didn't have to think about dependencies at all. Think: why _does_ the
child's `zoom` need to depend on its parent's? It's because we read
from the parent's zoom, with `get`, when computing the child's. We can
make a variant of `get` that captures this pattern:

``` {.python}
class ProtectedField:
    def read(self, field):
        field.depended_on.add(self)
        return field.get()
```

Now the `zoom` computation just needs to use `read`, and all of the
marking and dependency logic will be handled automatically:

``` {.python}
class BlockLayout:
    def layout(self):
        if self.zoom.dirty:
            parent_zoom = self.zoom.read(self.parent.zoom)
            self.zoom.set(parent_zoom)
```

In fact, this pattern where we just copy our parent's value is pretty
common, so let's add a shortcut for it:

``` {.python}
class ProtectedField:
    def copy(self, other):
        self.set(self.read(other))
```

This makes the code a little shorter:

``` {.python}
class BlockLayout:
    def layout(self):
        if self.zoom.dirty:
            self.zoom.copy(self.parent.zoom)
        # ...
```

Make sure to go through every other layout object type (there are now
quite a few!) and protect their `zoom` fields also. Anywhere else that
you see the `zoom` field refered to, you can use `get` to extract the
actual zoom value. You can check that you succeeded by running your
browser and making sure that nothing crashes, even when you increase
or decrease the zoom level.

Protecting `zoom` doesn't speed up our browser much, since it really
was just copied up and down the tree. That said, the dependency
tracking system in `ProtectedField` makes handling complex
invalidation scenarios much easier, and it will push us toward making
every field protected.

::: {.further}

:::


Protecting widths
=================

Protecting `zoom` was relatively simple, but it points the way toward
protecting complex layout fields. Working toward our goal of
invalidating line breaking, let's next work on protecting the `width`
field.

Like `zoom`, `width` is initially set in `DocumentLayout`:

``` {.python}
class DocumentLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.width = ProtectedField()
        # ...

    def layout(self, width, zoom):
        # ...
        self.width.set(width - 2 * device_px(HSTEP, zoom))
        # ...
```

Then, `BlockLayout` copies it from the parent:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.zoom = ProtectedField()
        # ...

    def layout(self):
        # ...
        if self.width.dirty:
            self.width.copy(self.parent.width)
        # ...
```

However, `width` is more complex than `zoom` because `width` is also
used in a bunch of other places during line wrapping.

For example, `add_inline_child` reads from the `width` to determine
whether to add a new line. We thus need the `children` field to depend
on the `width`:

``` {.python}
class BlockLayout:
    def add_inline_child(self, node, w, child_class, frame, word=None):
        width = self.children.read(self.width)
        if self.cursor_x + w > width:
            self.new_line()
        # ...
```

While we're here, note that the decision over whether or not to add a
new line also depends on `w`, which is an input to `add_inline_child`.
If you look through `add_inline_child`'s callers, you'll see that most
of the time, this argument depends on `zoom`:

``` {.python}
class BlockLayout:
    def input(self, node):
        zoom = self.children.read(self.zoom)
        w = device_px(INPUT_WIDTH_PX, zoom)
        self.add_inline_child(node, w, InputLayout, self.frame)
```

The same kind of dependency needs to be added to `image` and `iframe`.

In `text`, however, we need to be a little more careful. This method
computes the `w` parameter using a font returned by `font`:

``` {.python}
class BlockLayout:
    def text(self, node):
        zoom = self.children.read(self.zoom)
        node_font = font(node.style, zoom)
        for word in node.text.split():
            w = node_font.measureText(word)
            self.add_inline_child(node, w, TextLayout, self.frame, word)
```

Note that the font depends on the node's `style`, which can change,
for example via the `style_set` function. To handle this, we'll need
to protect `style`:

``` {.python}
class Element:
    def __init__(self, tag, attributes, parent):
        # ...
        self.style = ProtectedField()
        # ...

class Text:
    def __init__(self, tag, attributes, parent):
        # ...
        self.style = ProtectedField()
        # ...
```

This style field is computed in the `style` method, which builds the
map of style properties through multiple phases. Let's build that new
dictionary in a local variable, and `set` it once complete:

``` {.python}
def style(node, rules, frame):
    old_style = node.style.value
    new_style = {}
    # ...
    node.style.set(new_style)
```

Inside `style`, a couple of lines read from the parent node's style.
We need to mark dependencies in these cases:

``` {.python}
def style(node, rules, frame):
    for property, default_value in INHERITED_PROPERTIES.items():
        if node.parent:
            parent_style = node.style.read(node.parent.style)
            new_style[property] = parent_style[property]
        else:
            new_style[property] = default_value
```

If `style_set` changes a style, we can mark the `style`
field:[^protect-style-attr]

[^protect-style-attr]: We would ideally make the `style` attribute a
    protected field, and have the `style `field depend on it, but I'm
    taking a short-cut in the interest of simplicity.

``` {.python}
class JSContext:
    def style_set(self, handle, s, window_id):
        # ...
        elt.style.mark()
```

Finally, in `text` (and also in `add_inline_child`) we can depend on
the `style` field:

``` {.python}
class BlockLayout:
    def text(self, node):
        zoom = self.children.read(self.zoom)
        style = self.children.read(node.style)
        node_font = font(style, zoom)
        # ...
```

Make sure all other uses of the `style` field use either `read` or
`get`; it should be pretty clear which is which. We've now protected
the `width` and `style` properties, so we can finally skip line layout
when it's unchanged. To begin with, we only want to do line layout if
the `children` field is dirty:

``` {.python}
class BlockLayout:
    def layout(self):
        # ...
        if mode == "block":
            # ...
        else:
            if self.children.dirty:
                # ...
```

We also need to fix up `add_inline_child`'s and `new_line`'s
references to `children`. There are couple of possible fixes, but in
the interests of expediency,[^perhaps-local] I'm going to use a
second, unprotected field, `temp_children`:

[^perhaps-local]: Perhaps the nicest design would thread a local
    `children` variable through all of the methods involved in line
    layout, similar to how we handle `paint`.

``` {.python}
class BlockLayout:
    def layout(self):
        # ...
        if mode == "block":
            # ...
        else:
            if self.children.dirty:
                self.temp_children = []
                self.new_line()
                self.recurse(self.node)
                self.children.set(self.temp_children)
                self.temp_children = None
```

Note that I reset `temp_children` once we're done with it, to make
sure that no other part of the code accidentally uses it. This way,
`new_line` can modify `temp_children`, which will eventually become
the value of `children`:

``` {.python}
class BlockLayout:
    def new_line(self):
        self.previous_word = None
        self.cursor_x = 0
        last_line = self.temp_children[-1] if self.temp_children else None
        new_line = LineLayout(self.node, self, last_line)
        self.temp_children.append(new_line)
```

You'll want to do something similar in `add_inline_child`:

``` {.python}
class BlockLayout:
    def add_inline_child(self, node, w, child_class, frame, word=None):
        # ...
        line = self.temp_children[-1]
        # ...
```

In total, we ended up protecting the `style` field on DOM nodes and
the `children`, `width`, and `zoom` fields on `DocumentLayout` and
`BlockLayout` elements. If you've been going through and adding the
appropriate `read` and `get` calls, your browser should be close to
working. There's one tricky case: `tree_to_list`, which might deal
with both protected and unprotected `children` fields. I fixed this
with a type test:

``` {.python}
def tree_to_list(tree, list):
    # ...
    children = tree.children
    if isinstance(children, ProtectedField):
        children = children.get()
    for child in children:
        tree_to_list(child, list)
    # ...
```

With all of these changes made, your browser should work again, and it
should now skipping line layout for most elements.


Widths for inline elements
==========================

Now that `BlockLayout` protects its `width`, let's make sure all the
other layout objects do. We've already done `DocumentLayout`.
`LineLayout` is also pretty similar. However, the other layout methods
are a bit more complex.

In `InputLayout` width depends on the zoom level:

``` {.python}
class EmbedLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.width = ProtectedField()
        # ...

class InputLayout(EmbedLayout):
    def layout(self):
        # ...
        if self.width.dirty:
            zoom = self.width.read(self.zoom)
            self.width.set(device_px(INPUT_WIDTH_PX, zoom))
        # ...
```

Finally, when it comes to `width`, let's look at `TextLayout`. Here,
the width is computed based the `font`:

``` {.python file=lab15}
class TextLayout:
    def layout(self):
        # ...
        self.font = font(self.node, zoom)
        self.width = self.font.measureText(self.word)
```

For `iframe` and `img` elements, the width depends on the zoom level
and also the element's `width` and `height` attributes. Luckily, our
browser doesn't provide any way to change those attributes, so we
don't need to track them as dependencies.^[That said, a real browser
*would* need to make those attributes `ProtectedField`s as well.] So
we just need to handle the `zoom` dependency, which looks the same as
above:

``` {.python}
class ImageLayout(EmbedLayout):
    def layout(self):
        if width_attr and height_attr:
            zoom = self.width.read(self.zoom)
            self.width.set(device_px(int(width_attr), zoom))
            # ...
```

You can repeat this pattern to handle the other uses of `width` in
`ImageLayout` and `IframeLayout`.

Finally, `TextLayout`. Here, the width depends on the font:

``` {.python}
class TextLayout:
    def __init__(self, node, parent, previous, frame, word):
        # ...
        self.width = ProtectedField()
        # ...

    def layout(self):
        # ...
        if self.width.dirty:
            self.font = font(self.node, self.zoom.get())
            self.width.set(self.font.measureText(self.word))
        # ...
```

As you can see, the `font` is computed based on `self.zoom`, which we
can handle with `read`. However, it also depends on `node`, or more
precisely, the node's `style` field:

``` {.python file=lab15}
def font(node, zoom):
    weight = node.style['font-weight']
    style = node.style['font-style']
    size = float(node.style['font-size'][:-2])
    font_size = device_px(size, zoom)
    return get_font(font_size, weight, style)
```

A similar issue exists in the `BlockLayout`'s `text` method, where the
`node_font` influences the arguments to `add_inline_child` and
therefore the `children` field:

``` {.python file=lab15}
class BlockLayout
    def text(self, node):
        node_font = font(node, self.zoom.get())
        for word in node.text.split():
            w = node_font.measureText(word)
            self.add_inline_child(node, w, TextLayout, self.frame, word)
```

We know these are dependencies we need to capture; more generally:

- If we're using the `get` method during layout, it's being used to
  compute another layout field, so we need to use `read` instead to
  keep track of the dependency.
- If we're modifying something used during layout, like the style, it
  needs to be behind a `ProtectedField` so it can track dependencies.




Now, we can depend have the `TextLayout` width, and the width used in
the `text` method, depend on the style:

``` {.python}
class BlockLayout:
    def text(self, node):
        # ...
        zoom = self.width.read(self.zoom)
        style = self.children.read(node.style)
        node_font = font(style, zoom)
        # ...

class TextLayout:
    def layout(self):
        # ...
        zoom = self.width.read(self.zoom)
        style = self.width.read(self.node.style)
        self.font = font(style, zoom)
        # ...
```

Here I've changed `font` to take the style, not the node, as its
argument:

``` {.python}
def font(style, zoom):
    weight = style['font-weight']
    style = style['font-style']
    size = float(style['font-size'][:-2])
    font_size = device_px(size, zoom)
    return get_font(font_size, weight, style)

```

Thanks to these changes, all of the dependencies of line wrapping are
now wrapped in `ProtectedField`s, which means that the `children`
dirty flag will correctly tell us whether or not we can skip re-doing
it:

``` {.python}
class BlockLayout:
    def layout(self):
        # ...
        if self.children_field.dirty:
            mode = layout_mode(self.node)
            node_children = self.children_field.read(self.node.children_field)
            if mode == "block":
                # ...
            else:
                # ...
        # ...
```

We've just done quite a number of significant changes to our layout
algorithm, so let's take a moment to clean up. You'll need to go
through every reference to the `children` and `style` fields on nodes,
and the `width`, `zoom`, and `children` fields on layout objects. The
references that happen during style or layout should all use the
protected field method `read` to get the current value. (This will
require, for example, a small refactor of `compute_style`.) References
outside the style and layout phases---for example, those during
paint---should use this simpler `get` method:

``` {.python}
class ProtectedField:
    def get(self):
        assert not self.dirty
        return self.value
```

I'll leave you to make these changes on your own. They are all fairly
straightforward, if a bit tedious. Once they're all made, you should
be able to run your browser again without error. If you further add
`print` statements to each layout object constructor, you should be
able to see far fewer layout objects being created with each change,
which was our goal.

::: {.further}

:::



Invalidating layout fields
==========================

So far, we've made sure we're not recreating layout objects
needlessly, but we are still recomputing each of their sizes and
positions---except for `zoom` and `width`, which we've already had to
handle. Anyway, recomputing these layout fields, typically `x`, `y`,
and `height`, wastes time. Let's wrap all of those to in protected
fields.

Let's start with `x` positions. A `BlockLayout`'s `x` position is just
its parent's `x` position, so we can just `copy` it over:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.x = ProtectedField()
        # ...

    def layout(self):
        # ...
        if self.x.dirty:
            self.x.copy(self.parent.x)
        # ...
```

On `DocumentLayout`, we can just `set` the `x` position:

``` {.python}
class DocumentLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.x = ProtectedField()
        # ...

    def layout(self, width, zoom):
        # ...
        self.x.set(device_px(HSTEP, zoom))
        # ...
```

Let's skip the other layout objects for now, and instead move on to
`height`s. For `BlockLayout`, these are computed based on the
children's heights:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.height = ProtectedField()
        # ...

    def layout(self):
        # ...
        if self.height.dirty:
            children = self.height.read(self.children)
            new_height = sum([
                self.height.read(child.height)
                for child in self.children
            ])
            self.height.set(new_height)
```

Note that for this field, unlike the previous ones, parents'
properties depend on their children, not the other way around. This
means the `height` field depends on the `children` field as well as
each of their heights. However, `ProtectedField` makes this easy to
ensure, because we know we need to `read` the `children` field to get
the list of children out.

`DocumentLayout` is even simpler:

``` {.python}
class DocumentLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.height = ProtectedField()
        # ...

    def layout(self, width, zoom):
        # ...
        child_height = self.height.read(child.height)
        self.height.set(child_height + 2 * device_px(VSTEP, zoom))
        # ...
```

So that's `BlockLayout` and `DocumentLayout`. Now let's think about
the other layout object types: `LineLayout`, `TextLayout`, and
`EmbedLayout` and its subtypes.

Line and inline layout works a little differently from block layout.
Let's review:

1. The tree structure is always a `BlockLayout` containing one or more
   `LineLayout`s which in turn contain one or more of the others.
2. The `LineLayout` computes its `zoom`, `x`, `y`, and `width`, then
   recurses to its children.
3. Those children compute their `zoom`, `x`, `width`, and `height`,
   but also their `font`
4. Later children use previous children's `font` to add spaces between
   words
5. Once they're done, the `LineLayout` calls `get_ascent` and
   `get_descent` methods to compute its own `height` and the `y` of
   each child

The dependency structure is a little complex. Don't try to get it all
in your head; instead, focus on the fact that besides `zoom`, `x`,
`y`, `width`, and `height`, these layout objects also compute a
`font`, an ascent, and a descent.

We'll make all three of these fields protected. Let's start with
`TextLayout`:

``` {.python}
class TextLayout:
    def __init__(self, node, parent, previous, word):
        # ...
        self.x = ProtectedField()
        self.y = ProtectedField()
        self.height = ProtectedField()
        self.font = ProtectedField()
        self.ascent = ProtectedField()
        self.descent = ProtectedField()
        # ...
```

Note that I've converted `ascent` and `descent` from methods to
protected fields. This will make it easier to manage using
`ProtectedField`.^[An alternative to rewriting this is to use what's
called "destination passing style", where to destination of a method's
return value is passed to it as an argument. But rewriting usually
leads to cleaner code.]

We'll need to compute these fields in `layout`. Let's start with
`font`, `width`, `height`, `ascent`, and `descent`, because these are
all similar and fairly straightforward:

``` {.python}
class TextLayout:
    def layout(self):
        # ...

        if self.font.dirty:
            zoom = self.font.read(self.zoom)
            style = self.font.read(self.node.style)
            self.font.set(font(style, zoom))
            
        if self.width.dirty:
            font = self.width.read(self.font)
            self.width.set(font.measureText(self.word))

        if self.ascent.dirty:
            font = self.ascent.read(self.font)
            self.ascent.set(font.getMetrics().fAscent)

        if self.descent.dirty:
            font = self.descent.read(self.font)
            self.descent.set(font.getMetrics().fDescent)

        if self.height.dirty:
            font = self.height.read(self.font)
            self.height.set(linespace(font))
```

It looks a bit odd to compute `font` again inside each `if` statement,
but remember that each of those `read` calls establishes a dependency
for one layout field upon another. I like to think of each `font` as
being scoped to its `if` statement.^[Python scoping doesn't actually
work like this, but many languages like C++ and JavaScript do.]

We also need to compute the `x` position of a `TextLayout`. That can
use the previous sibling's font, *x* position, and width:

``` {.python}
class TextLayout:
    def layout(self):
        # ...
        if self.x.dirty:
            if self.previous:
                prev_x = self.x.read(self.previous.x)
                prev_font = self.x.read(self.previous.font)
                prev_width = self.x.read(self.previous.width)
                space = self.previous.font.measureText(' ')
                self.x.set(prev_x + prev_font.measureText(" ") + prev_width)
            else:
                self.x.copy(self.parent.x)
```

That's it for `TextLayout`. `EmbedLayout` is basically identical,
except that its `ascent` and `descent` are simpler:

``` {.python}
class EmbedLayout:
    def layout(self):
        # ...
        if self.ascent.dirty:
            height = self.ascent.read(self.height)
            self.ascent.set(-height)
        
        if self.descent.dirty:
            self.descent.set(0)
```

Then, each of the `EmbedLayout` subtypes have their own way of
computing their height. These also need to be converted to use
`ProtectedField`, but that's typically simple. For example, for
`InputLayout`, it looks like this:

``` {.python}
class InputLayout(EmbedLayout):
    def layout(self):
        # ...
        font = self.height.read(self.font)
        self.height = linespace(font)
```

Specifically `ImageLayout` has one extra quirk, which is that it also
computes an `img_height` field, which also needs to be converted to a
`ProtectedField`:

``` {.python}
class ImageLayout(EmbedLayout):
    def __init__(self, node, parent, previous, frame):
        super().__init__(node, parent, previous, frame)
        self.img_height = ProtectedField()

    def layout(self):
        # ...
        img_height = self.height.read(self.img_height)
        font = self.height.read(self.font)
        self.height.set(max(img_height, linespace(font)))
```

So that covers all of the inline layout objects. What about
`LineLayout`? These only have the usual five layout fields: `zoom`,
`x`, `y`, `width`, and `height`:

``` {.python}
class LineLayout:
    def __init__(self, node, parent, previous):
        # ...
        self.zoom = ProtectedField()
        self.x = ProtectedField()
        self.y = ProtectedField()
        self.width = ProtectedField()
        self.height = ProtectedField()
```

Most of them are computed in straightforward ways:

``` {.python}
class LineLayout:
    def layout(self):
        if self.zoom.dirty:
            self.zoom.copy(self.parent.zoom)

        if self.width.dirty:
            self.width.copy(self.parent.width)

        if self.x.dirty:
            self.x.copy(self.x.width)

        if self.y.dirty:
            if self.previous:
                prev_y = self.y.read(self.previous.y)
                prev_height = self.y.read(self.previous.height)
                self.y.set(prev_y + self.prev_height)

        # ...
```

However, `height` is a bit complicated: it computes the maximum ascent
and descent across all children and uses that to set the `height` and
the children's `y`. I think the simplest way to handle this code is to
add `ascent` and `descent` fields to the `LineLayout` to store the
maximum ascent and descent, and then have the `height` and the
children's `y` field depend on those:

``` {.python}
class LineLayout:
    def __init__(self, node, parent, previous):
        # ...
        self.ascent = ProtectedField()
        self.descent = ProtectedField()
```

Now, in `layout`, we'll first handle the case of no children:

``` {.python}
class LineLayout:
    def layout(self):
        # ...
        if self.height.dirty:
            children = self.height.read(self.children)
            if not children:
                self.height.set(0)
                return
```

Next, let's recompute the ascent and descent:

``` {.python}
class LineLayout:
    def layout(self):
        # ...
        if self.ascent.dirty:
            children = self.ascent.read(self.children)
            self.ascent = max([
                -self.ascent.read(child.ascent)
                for child in children
            ])

        if self.descent.dirty:
            children = self.descent.read(self.children)
            self.descent = max([
                self.descent.read(child.descent)
                for child in children
            ])
```

Next, we can recompute the `y` position of each child:

``` {.python}
class LineLayout:
    def layout(self):
        # ...
        for child in self.children:
            if child.y.dirty:
                y = child.y.read(self.y)
                y += child.y.read(self.ascent)
                y += child.y.read(child.ascent)
                child.y.set(y)
```

Finally, we recompute the line's height:

``` {.python}
class LineLayout:
    def layout(self):
        # ...
        if self.height.dirty:
            max_ascent = self.height.read(self.ascent)
            max_descent = self.height.read(self.descent)
            self.height.set(max_ascent + max_descent)
```

As a result of these changes, all of our layout objects' fields should
now be `ProtectedField`s. Take a moment to make sure all uses of these
fields use `read` and `get`, and make sure your browser still runs. I
recommend testing your browser on this page, which has a
`contenteditable` element toward the type. Try typing into it, and
test what happens if you type multiple words or enough text to force
it to wrap over multiple lines. The browser should smoothly update
with every change.

::: {.further}

:::

Skipping no-op updates
======================

Now that our browser runs, let's look at what impact protected fields
have had on recomputation. To do this, we can add a `print` statement
inside the `set` method on `ProtectedField`s:

``` {.python}
class ProtectedField:
    def set(self, value):
        if self.value is not None:
            print("Change", self)
        self.notify()
        self.value = value
        self.dirty = False
```

Here, I check `self.value` so as to not print anything if the
protected field is being set for the first time, like during initial
page layout.

Now try editing some text with `contenteditable` (like on this page),
or running some JavaScript, or otherwise modifying a page. You should
see a screenful of output. To make it a little easier to read, let's
add a nice printable form for `ProtectedField`s:

``` {.python}
class ProtectedField:
    def __init__(self, base, name):
        self.base = base
        self.name = name
        # ...

    def __repr__(self):
        return "ProtectedField({}, {})".format(self.base, self.name)
```

You'll want to pass `self` for the base everywhere a `ProtectedField`
is created, and a name that matches the field name. Now retry editing,
say, this page. If you scroll to the beginning of the output, you'll
see that the first thing that's updated is the `contenteditable`
element's `children`, followed by the associated layout object's
`children` field:

    Change ProtectedField(<div ...>, children)
    Change ProtectedField(BlockLayout(...), children)

This creates a bunch of new layout objects; since they're being laid
out for the first time, they're not printed. Therefore the next thing
that's recomputed is the `contenteditable` element's layout object's
`height`:

    Change ProtectedField(BlockLayout(...), height)

Now, that makes sense: the `height` could have changed, if typing into
the `contenteditable` wrapped over more lines. But what happens next
makes less sense: every other `y` on the page is recomputed:

    Change ProtectedField(BlockLayout(...), y)
    Change ProtectedField(BlockLayout(...), y)
    Change ProtectedField(BlockLayout(...), y)
    Change ProtectedField(BlockLayout(...), y)
    ...

Why does this happen? Well, let's think step by step. When we change
the edited element's `height`, we notify everyone who depended on it.
But since an element's `y` position depends on the previous element's
`height`, that means recomputing its `y` position. Eventually, that
influences the `y` of the _next_ element, and so on.

What makes this all wasteful is that in most cases the `height` didn't
change. For example, if you just type a few characters into the
`contenteditable` on this page, it won't change height, and nothing on
the page needs to move. They key here is to not nodify dependants if
the value didn't change:

``` {.python}
class ProtectedField:
    def set(self, value):
        if self.value is not None:
            print("Change", self)
        if value != self.value:
            self.notify()
        self.value = value
        self.dirty = False
```

This change is safe, because if the new value is the same as the old
value, any downstream computations don't actually need to change.

This small tweak should reduce the number of field changes for most
edits. When you reach the end of a line, however, you'll still see the
cascade of changes to `y` positions, which is correct because those
`y` positions now need to change.


Avoiding redundant recursion
============================

All of the layout fields are now wrapped in invalidation logic,
ensuring that we only compute `x`, `y`, `width`, `height`, or other
values when absolutely necessary. That's good: it causes faster layout
updates on complex web pages.

But on the largest web pages it's not enough. For example, on my
computer, a no-op layout of this page, where no layout field is
actually recomputed, still takes approximately 70 milliseconds---way
too long for smooth animations or a good editing experience. It takes
this long because our browser still needs to traverse the layout tree,
diligently checking that it has no work to do at each node.

There's a solution to this problem, and it involves pushing our
invalidation approach one step further. So far, we've thought about
the *data* dependencies of a particular layout computation, for
example with a node's `height` depending on the `height` of its
children. But computations also have *control* dependencies, which
refers to the sequence of steps needed to actually run a certain piece
of code. For example, computing a node's `height` depends on calling
that node's `layout` method, which depends on calling its parent's
`layout` method, and so on. We can apply invalidation to control
dependencies just like we do to data dependencies.

So---in what cases do we need to make sure we call a particular layout
object's `layout` method? Well, the `layout` method does three things:
create layout objects, compute layout properties, and recurse into
more calls to `layout`. Those steps can be skipped if:

- The layout object's `children` field isn't dirty, meaning we don't
  need to create new layout objects;
- The layout object's layout fields aren't dirty, meaning we don't
  need to compute layout properties; and
- The layout object's children's `layout` methods also don't need to
  be called.

If all of these are tree, we should be able to skip calling the layout
object's `layout` method. In a bit web page, that can save a lot of
time.

At a high level, we can implement all of this with a new dirty flag,
which I call `descendants`.[^ancestors] We'll add it to every kind of
layout object:

[^ancestors]: You will also see these called *ancestor* dirty bits
    instead. It's the same thing, just following the flow of dirty
    bits instead of the flow of control.

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.descendants = ProtectedField(self, "descendants")
```

This field will be dirty if any of the descendants of this layout
object, need their `layout` method called. We'll want this field to be
marked when any descendant's layout field is marked, so we need to
establish dependencies. Something like this is *close* to working:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.parent.descendants.read(self.zoom)
        self.parent.descendants.read(self.width)
        self.parent.descendants.read(self.height)
        self.parent.descendants.read(self.x)
        self.parent.descendants.read(self.y)
```

Note that it is the *parent's* `descendants` field that depends on
this node's layout fields. That's because it's one of the parent's
descendants that needs its `layout` method called.

However, this won't quite work, because `read` asserts that the field
being read is not dirty, and here the fields being read were just
created and are therefore dirty. We need a variant of `read`, which
I'll call `control` because it's for control dependencies:

``` {.python}
class ProtectedField:
    def control(self, source):
        source.depended_on.add(self)
        self.dirty = True

    def read(self, field):
        assert not field.dirty
        field.depended_on.add(self)
        return field.value

class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.parent.descendants.control(self.zoom)
        self.parent.descendants.control(self.width)
        self.parent.descendants.control(self.height)
        self.parent.descendants.control(self.x)
        self.parent.descendants.control(self.y)
```

Note that the `control` method doesn't actually read the source field's
value; that's why it's safe to use even when the source field is dirty.

So far, we've made the `descendants` field depend on child layout
fields. We also need it to depend on the child `children` field, since
again, that is computed by calling `layout`:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.parent.descendants.control(self.children)
```

Moreover, the notion of descendant dirty bits is recursive: if a
child's descendants are dirty, that means this node's descendants are
dirty. We establish this recursion like so:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.parent.descendants.control(self.descendants)
```

Finally, any changes to the style or node tree also means we may need
to redo layout:

``` {python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.parent.descendants.control(self.node.children)
        self.parent.descendants.control(self.node.style)
```

Make sure to replicate this code in every layout object type. In the
`LineLayout`, `TextLayout`, and `EmbedLayout` types, further make sure
that the parent's `descendants` also `depend` on the `font`, `ascent`,
and `descent` fields that those layout objects have. Now that we have
descendant dirty bits, let's use them to skip unneeded recursions


Eager and lazy propagation
==========================

Our ultimate goal is to use the `descendants` dirty bit to avoid
recursing into a layout object's children inside the `layout` method:

``` {.python}
class BlockLayout:
    def layout(self):
        # ...
        if self.descendants.dirty:
            for child in self.children:
                child.layout()
            self.descendants.set(None)
        # ...
```

However, this won't work. More precisely, your browser will likely
crash inside a `get` call somewhere during paint because your browser
will skip recursing even into layout objects that are dirty.

This is a consequence of us implementing *lazy* marking. Consider how
the `mark` method is implemented:

``` {.python}
class ProtectedField:
    def mark(self):
        if self.dirty: return
        self.dirty = True
```

When a protected field is marked, *its* dirty field is set, but any
other fields that depend on it aren't set yet.

Lazy marking works for data dependencies but not for control
dependencies. That's because dirty bits are marked when dependencies
are computed. For data dependencies, those are computed before the
dirty bit is checked, which means every field that needs to be
recomputed is marked before its dirty bit is checked.

But for control dependencies we need something else. For example,
suppose the `width` of some layout object is marked. Then its parent's
`descendants` field, which depends on `width`, needs to be marked
right away, _before_ the `width` is recomputed, because after all it
is used to determine _whether_ the `width` is recomputed.

Let's add an eager marking mode to `ProtectedField`. I'll give each
protected field two sets of fields that depend on it: those that will
be marked lazily, and those that will be marked eagerly:

``` {.python}
class ProtectedField:
    def __init__(self, base, name):
        # ...
        self.depended_lazy = set()
        self.depended_eager = set()
```

The existing `read` method for data dependencies will be lazy:

``` {.python}
class ProtectedField:
    def read(self, field):
        assert not field.dirty
        field.depended_lazy.add(self)
        return field.value
```

However, the `control` method for control dependencies will be eager:

``` {.python}
class ProtectedField:
    def control(self, source):
        source.depended_eager.add(self)
        self.dirty = True
```

In `notify`, we'll mark both lazy and eager dependencies:

``` {.python}
class ProtectedField:
    def notify(self):
        for field in self.depended_lazy:
            field.mark()
        for field in self.depended_eager:
            field.mark()
```

However, in `mark`, we'll only recursively notify the eager fields:

``` {.python}
class ProtectedField:
    def mark(self):
        if self.dirty: return
        self.dirty = True
        for field in self.depended_eager:
            field.notify()
```

With these changes, the descendant dirty bits should now be set
correctly, and we can now skip recursively calling layout when the
descendants aren't dirty. Even on larger web pages, layout should now
be a millisecond or less, and editing should become fairly smooth.


Granular style invalidation
===========================

Thanks to all of this invalidation work, we should now have a pretty
fast editing experience,[^other-phases] and many JavaScript-driven
interactions should be fairly fast as well. However, 

[^other-phases]: It might still be pretty laggy on large pages due to
    the composite-raster-draw cycle being fairly slow, depending on
    which exericses you implemented in [Chapter 13](animations.md).


Summary
=======

::: {.todo}
Not written yet
:::


Outline
=======

The complete set of functions, classes, and methods in our browser 
should now look something like this:

::: {.cmd .python .outline html=True}
    python3 infra/outlines.py --html src/lab16.py
:::


Exercises
=========

*Inserting children*: Implement the `insertBefore` DOM method, as in
[Chapter 9][scripts.md#exercises], and modify your browser to
invalidate it correctly. 

*Modifying width*: Add a DOM method that allows JavaScript code to
change an `iframe` element's `width` attribute. This should cause both
the parent and the child frame to be re-laid-out to match the new width.

*Descendant bits for style*: Add descendant dirty bits to the style
phase. This should make the style phase much faster by avoiding
recomputing style for most elements.
