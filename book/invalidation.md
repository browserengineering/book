---
title: Reusing Previous Computations
chapter: 16
prev: embeds
next: skipped
...

So far, we've focused on improving animation performance by improving
our browser's graphics subsystem. But that hasn't helped
layout-inducing animations, since those typically spend most of their
time in layout, not graphics. Yet just like compositing enabled smooth
animations by avoiding redundant raster work, we can avoid redundant
layout work using a technique called invalidation.

Editing Content
===============

In [Chapter 13](animations.md), we used compositing to enable smooth
animation of CSS properties like `transform` or `opacity`. Some CSS
properties, however, can't be smoothly animated in this way, because
as they change they not only modify the _display list_ but also the
_layout tree_. This was a good reason to avoid animating
_layout-inducing_ properties like `width`. However, while _animating_
these properties is a bad practice, many other _interactions_
unavoidably affect the layout tree, and yet we want them to be as
smooth and low-latency as possible.

One good example is editing text. Most people type at a rate of
several characters per second, and even a delay of a few frames is
very distracting. Yet editing text changes the document, and therefore
requires constructing a new layout tree that reflects the new text.
And, in fact, if you open up a large web page (like this one) and type
into an input box on it (like the one below) in our toy browser,
you'll
see that it is quite laggy indeed:

<input style="width:100%"/>

Now, in the case of typing into an `input` element, our browser
rebuilds the layout tree, but in fact the layout tree looks the same
each time---the text inside an `input` element doesn't get its own
layout object. So that situation is easy to optimize. But browsers
support other forms of text editing which do affect the layout tree.
For example, in a real browser you can give any element the
`contenteditable` attribute to make it editable. Once you do so, the
user can click on the element to add or modify rich, formatted text in
it:

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
it. In a real browser, the implementation would be a bit more complex
in order to handle cursor movement, but I'm going to have key presses
append to the last text node in the editable element. First we need to
find that element:

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
a cursor to show the user where the editing will happen and to provide
visual confirmation that they've focused on the right element. Let's
do that in `BlockLayout`:

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
```

Here, `DrawCursor` is just a wrapper around `DrawLine`:

``` {.python}
def DrawCursor(elt, width):
    return DrawLine(elt.x, elt.y, elt.x + width, elt.y + elt.height)
```

We can also use this wrapper to draw the cursor in `InputLayout`:

``` {.python}

class InputLayout(EmbedLayout):
    def paint(self, display_list):
        if self.node.is_focused and self.node.tag == "input":
            cmds.append(DrawCursor(self, self.font.measureText(text)))
```

You should now be able to edit the example above in your own
browser---but if you try it, you'll see that editing is extremely
slow, with each character taking hundreds of milliseconds to type.

Idempotence
===========

At a high level, the reason edits are slow is because each edit
requires recomputing layout---and on a large page like this one, that
takes our browser many, many milliseconds. But recomputing the layout
isn't really necessary: when you type a single character, adding a
single letter to a single word on a single line of the page, almost
everything else on the page stays in the exact same place. So
recomputing layout spends many, many milliseconds recomputing exactly
the same layout coordinates that we already have. Invalidation means
not doing that.

So, why do we need to recompute layout every time we type a new
character? Well, to start with, our `render` method uses a brand new
layout tree, every time we need to recompute layout:

``` {.python file=lab15}
class Frame:
    def render(self):
        if self.needs_layout:
            self.document = DocumentLayout(self.nodes, self)
            self.document.layout(self.frame_width, self.tab.zoom)
            # ...
```

Every time layout runs, the whole layout tree is discarded and a new
one is created, starting with the root `DocumentLayout`. Because we're
creating a new tree, we're throwing away all of the old layout
information, even the information that was already correct. But this
is wasteful: when layout _does_ need to run, it's typically due to a
small change, like `innerHTML` or `style` being set on some element.
Recreating the layout tree is wasteful, and we'd like to avoid it.

But before jumping right to coding, let's read over the existing code
to understand where layout objects are created: search the code for
`Layout`, which all layout class names end with. You should see that
layout objects are created only in a few places:

- `DocumentLayout` objects are created by the `Tab` in `render`
- `BlockLayout` objects are created by either:
  - A `DocumentLayout`, in `layout`
  - A `BlockLayout`, in `layout`
- `LineLayout` objects are created by `BlockLayout` in `new_line`
- All others are created by `BlockLayout` in `add_inline_child`

In each of these locations, we want to reuse an existing layout
object, instead of creating a new one, whenever possible. That'll save
a bit of time and memory, but more importantly it'll later let us
reuse already-computed layout information.

Let's start with the first location. The `DocumentLayout` is created
the same way each time, and its argument, `nodes`, is never assigned
to once the page finishes loading. And the `DocumentLayout`
constructor just copies its arguments into the `DocumentLayout`'s
fields. This means every execution of this line of code creates an
identical object.

Because the `DocumentLayout` is constructed the same way each time, we
only need to do it once. Let's move that one line of code from
`render` to `load`:

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

Let's move on to the next case, where `BlockLayout` objects are
created by `DocumentLayout`. Here's what that code looks like:

``` {.python file=lab15}
class DocumentLayout:
    def layout(self, width, zoom):
        child = BlockLayout(self.node, self, None, self.frame)
        # ...
```

As you can see, the arguments to `BlockLayout` here also cannot
change: the `node` and `frame` fields, and `self`, are never assigned
to, while `None` is just a constant. This means `BlockLayout`
construction also has no arguments, which means we don't need to redo
this step every time we do layout.

We might therefore be tempted to skip the redundant work, with
something like this:

``` {.python replace=.append(child)/%20%3d%20[child]}
class DocumentLayout:
    def layout(self, width, zoom):
        if not self.children:
            child = BlockLayout(self.node, self, None, self.frame)
        else:
            child = self.children[0]
        # ...
```

This reuses an existing `BlockLayout` object if possible. But note
that right after `child` is created, it is *appended to* the the
`children` array:

``` {.python}
class DocumentLayout:
    def layout(self, width, zoom):
        # ...
        self.children.append(child)
        # ...
```

If we run this line of code twice, the `BlockLayout` will end up in
the `children` array twice, which would cause all sorts of strange
problems. The layout tree wouldn't even be a tree any more!

The core issue here is what's called *idempotence*: if we're keeping
the layout tree around instead of rebuilding it from scratch each
time, we're going to be calling `layout` multiple times, and we need
repeated calls not to make any extra changes. More formally, a
function is idempotent if calling it twice in a row with the same
inputs and dependencies yields the same result. Assignments to fields
are idempotent---if you assign a field the same value twice, it's gets
the same value as assigning it once---but methods like `append`
aren't.

Here, the issue is easy to fix by replacing the `children` array
instead of just modifying it:

``` {.python}
class DocumentLayout:
    def layout(self, width, zoom):
        if not self.children:
            child = BlockLayout(self.node, self, None, self.frame)
        else:
            child = self.children[0]
        self.children = [child]
        # ...
```

But we have similar issues in `BlockLayout`, which creates all the
other types of layout objects and `append`s them to its `children`
array. Here, the easy fix is to reset the `children` array at the top
of `layout`:

``` {.python}
class BlockLayout:
    def layout(self):
        self.children = []
        # ...
```

Now the `BlockLayout`'s `layout` function is idempotent again, because
each call will recreate the `children` array the same way each time.

Take a moment to read all of our other `layout` methods and look for
any method calls to make sure they're idempotent. I found:

- In `new_line`, `BlockLayout` will append to its `children` array;
- In `text` and `input`, `BlockLayout` will append to the `children`
  array of some `LineLayout` child
- In `text` and `input`, `BlockLayout` will call `get_font`, as will
  the `TextLayout` and `InputLayout` methods
- Basically every layout method calls `display_px`

Luckily, none of these break idempotence. The `new_line` method is
only called through `layout`, which resets the `children` array, so
the `children` array ends up the same each time it is called.
Similarly, `text` and `input` are also only called through `layout`,
which means all of the `LineLayout` children are reset. Meanwhile,
`get_font` acts as a cache, so multiple calls return the same font
object, while `display_px` just does some math so always returns the
same result given the same inputs.

So every layout method is now idempotent, which means the browser
should again work correctly, even though some layout objects are
reused between layouts. Idempotency is important because it means it
doesn't matter _how many_ times a function was called: one call, two
calls, ten calls, no matter what the result is the same. And this
means that avoiding redundant work is safe: if we find that we're
calling the function twice with the same inputs and dependencies, we
can just skip the second call without breaking anything else. So let's
turn to that.

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

So far these changes have lead to some small readability improvements,
but `ProtectedField`s can track dependencies for us. For example,
consider the code in `keypress` that handles edits:

``` {.python}
class Frame:
    def keypress(self, char):
        elif self.tab.focus and "contenteditable" in self.tab.focus.attributes:
            # ...
            self.tab.focus.layout_object.children.mark()
```

Do you notice that this method *modifies* an `Element`'s `children`
field, but notifies a layout object about it? That makes sense,
because the layout object's `children` field depends on the
`Element`'s `children` field, but tracking this dependency manually is
error-prone. Instead, let's wrap make each `Element` have a protected
`children` field:

``` {.python}
class Element:
    def __init__(self, tag, attributes, parent):
        # ...
        self.children = ProtectedField()
```

In the `keypress` handler, we want to call a method on the `Element`'s
`children` field, because that's what the `keypress` handler actually
modifies. But the dirty field we want *set* is on the layout object's
`children` field. To accomplish that, we'll need some kind of link
between the two `ProtectedField`s. Specifically, we'll need to the
`Element`'s children field to know that the layout object's `children`
field depends on it:

``` {.python}
class ProtectedField:
    def __init__(self, eager=False):
        # ...
        self.depended_on = set()
```

We can now add a new `notify` method that sets all of the dirty flags
that depend on the notified field:

``` {.python}
class ProtectedField:
    def notify(self):
        for field in self.depended_on:
            field.mark()
```

The keypress handler can now call `notify` on the `Element`'s
`children`:

``` {.python}
class Frame:
    def keypress(self, char):
        elif self.tab.focus and "contenteditable" in self.tab.focus.attributes:
            # ...
            self.tab.focus.children.notify()
```

We can also `notify` any time we `set` a value:

``` {.python}
class ProtectedField:
    def set(self, value):
        self.notify()
        self.value = value
        self.dirty = False
```

The only remaining question is how to establish the dependency in the
first place. Just like with our `set` method, we want *depending on a
value* and *establishing a dependency* to be the same operation, so
that we can't accidentally forget one of them. So let's add a method
that *reads* a protected field, but simultaneously establishes a
dependency:

``` {.python}
class ProtectedField:
    def read(self, field):
        assert not field.dirty
        field.depended_on(self)
        return field.value
```

To use this method, you call it on the field you're currently
computing, passing in the field whose value you want as an argument:

``` {.python}
class BlockLayout:
    def layout(self):
        if mode == "block":
            if self.children.dirty:
                node_children = self.children.read(self.node.children)
                # ...
```

Here the `BlockLayout`'s `children` field reads the associated
`Element`'s `children` field, thus establishing that the former
depends upon the latter. And note that the `read` method explicitly
checks that the field being read is not dirty; this guarantees that
the returned value (which should be used in place of `node.children`)
is up to date.

By encapsulating a value and its dirty field into a single object,
`ProtectedField` makes sure that dirty flags are set, checked, and
reset correctly. That will be key to using invalidation in the rest of
our layout engine.

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

Here the `new_line` and `recurse` methods add new layout objects to
the `children` array. We'd like to skip this if the `children` field
isn't dirty, but to do that, we need to make sure that all of the
dependencies that `new_line` and `recurse` read set the `children`
dirty bit.

To do that, let's read through the `new_line` and `recurse` methods,
as well as the methods that they call (like `text`,
`add_inline_child`, and `font`). Focus on the fields of `self` and
`node` being read. You should notice that the `font` function reads
from `node.style`, the `add_inline_child` method reads the `width`
field, and lots of methods read the `zoom` field.

All of these dependencies can change, so we need to wrap all of them
with `ProtectedField`. Let's start with `zoom`. It is initially set on
the `DocumentLayout`, so let's start there:

``` {.python}
class DocumentLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.zoom = ProtectedField()
        # ...

    def layout(self, width, zoom):
        # ...
        self.zoom = self.zoom.set(zoom)
        # ...
```

Now, each `BlockLayout` has its own `zoom` field:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.zoom = ProtectedField()
        # ...
```

However, in the `BlockLayout`, the `zoom` field comes from its
parent's `zoom` field, so we need to add a dependency using `read` and
`set`:

``` {.python}
class BlockLayout:
    def layout(self):
        if self.zoom.dirty:
            parent_zoom = self.zoom.read(self.parent.zoom)
            self.zoom.set(parent_zoom)
        # ...
```

In fact, this pattern where we just copy our parent's value is pretty
common, so let's add a shortcut for it:

``` {.python}
class ProtectedField:
    def copy(self, other):
        return self.set(self.read(other))
```

This makes the code a little shorter:

``` {.python}
class BlockLayout:
    def layout(self):
        if self.zoom.dirty:
            self.zoom.copy(self.parent.zoom)
        # ...
```

We can also wrap the `zoom` field for all of the other types of layout
objects, each of which have their own `zoom` fields.

Next, let's wrap `width` field. Like `zoom`, it's initially set in
`DocumentLayout`:


``` {.python}
class DocumentLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.width = ProtectedField()
        # ...

    def layout(self, width, zoom):
        # ...
        self.width = self.width.set(width - 2 * device_px(HSTEP, zoom))
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

The `LineLayout` does the same thing. However, in `InputLayout`, the
width depends on the zoom level instead of the parent's width:

``` {.python}
class EmbedLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.width = ProtectedField()
        # ...

class InputLayout(EmbedLayout):
    def layout(self):
        # ...
        zoom = self.width.read(self.zoom)
        self.width.set(device_px(INPUT_WIDTH_PX, zoom))
        # ...
```

For `iframe` and `img` elements, the width depends on the zoom level
and also the element's `width` and `height` attributes. The `zoom`
dependency works like for `InputLayout`, but what about `width` and
`height`? Luckily, our browser doesn't provide any way to change those
values, so we don't need to track them as dependencies.^[That said, a
real browser *would* need to make those attributes `ProtectedField`s
as well.]

Another place the width is used is inside `add_inline_child`. This
whole method is about adding children, so we'll just make the
`children` field depend on the `width`:

``` {.python}
class BlockLayout:
    def add_inline_child(self, node, w, child_class, frame, word=None):
        width = self.children_field.read(self.width_field)
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

A similar issue exists in the `BlockLayout`'s `text` method, where the
`node_font` influences the arguments to `add_inline_child` and
therefore the `children` field:

``` {.python file=lab15}
class BlockLayout
    def text(self, node):
        node_font = font(node, self.zoom)
        for word in node.text.split():
            w = node_font.measureText(word)
            self.add_inline_child(node, w, TextLayout, self.frame, word)
```

Ultimately, the `font` method reads the node's `style`:

``` {.python}
def font(node, zoom):
    weight = node.style['font-weight']
    style = node.style['font-style']
    size = float(node.style['font-size'][:-2])
    font_size = device_px(size, zoom)
    return get_font(font_size, weight, style)
```

So the point is that all of this depends on the style, and the style
itself can change if, for example, new elements are added or the
`style` attribute is assigned to.

To handle this, we'll need to replace `style`, also, by a protected
field:

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

This style field is computed in the `style` method, which build a
dictionary of new style properties in multiple phases. Let's build
that new dictionary in a local variable, and set it at the end:

``` {.python}
def style(node, rules, frame):
    old_style = node.style.value
    new_style = CSS_PROPERTIES.copy()
    # ...
    node.style.set(new_style)
```

It can also be changed in the `style_set` method:

``` {.python}
class JSContext:
    def style_set(self, handle, s, window_id):
        # ...
        elt.style_field.notify()
```

Also, in a couple of places we need to read from the parent node's
style, line when we handle inheritance. We need to mark dependencies
in that case:

``` {.python}
def style(node, rules, frame):
    for property, default_value in INHERITED_PROPERTIES.items():
        if node.parent:
            parent_style = node.style.read(node.parent.style)
            new_style[property] = parent_style[property]
        else:
            new_style[property] = default_value
```

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
