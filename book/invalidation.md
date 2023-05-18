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
        if not self.dirty:
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

Now our layout objects are not recreated needlessly, and we're even
not recomputing the width of an object unless we need to. But we're
still recomputing the `x`, `y`, and `height` parameters repeatedly,
which takes a lot of time. Let's speed up layout further by avoiding
redundant recomputations of these three fields.

Here we again need to think about dependencies. The computations for
these three fields look like this:

``` {.python file=lab15}
class BlockLayout:
    def layout(self):
        # ...
        self.x = self.parent.x
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y
        # ...
        self.height = sum([child.height for child in self.children])
```

Thus, the dependencies of each field are:

- A node's `x` field depends on its parent's `x` field;
- A node's `height` field depends on its childrens' `height`s.
- A node's `y` field depends on its parent's `y` and its previous
  node's `y` and `height`;

Therefore we can introduce new `dirty_x`, `dirty_height`, and
`dirty_y` fields. For each of these new dirty flags, we need to set
them when a dependency changes, check them before computing the field
they protect, and reset them afterwards.

For `dirty_x`, we must:

- Check the parent's `dirty_x` when `x` is recomputed
- Reset `dirty_x` by computing `x`.
- Set all children's `dirty_x` fields when `x` changes

Putting that into code, we get the following code:

``` {.python}
class BlockLayout:
    def layout(self):
        # ...
        if self.dirty_x:
            assert not self.parent.dirty_x
            self.x = self.parent.x
            for child in self.children:
                child.dirty_x = True
            self.dirty_x = False
        # ...
```

Here we need to be a little careful, because we are modifying the
`BlockLayout` class, but the parent of a `BlockLayout` can be a
`DocumentLayout`, and its children can be `LineLayout`s. We therefore
need those layout objects to also support dirty flags. For now, we're
not doing any kind of invalidation on those elements, so just reset
their dirty flags at the end of their `layout` method:

``` {.python}
class LineLayout:
    def __init__(self, node, parent, previous):
        # ...
        self.dirty_width = True
        self.dirty_height = True
        self.dirty_x = True
        self.dirty_y = True

    def layout(self):
        # ...
        self.dirty_width = False
        self.dirty_height = False
        self.dirty_x = False
        self.dirty_y = False
```

Of course, we could add invalidation to these additional layout
objects. But invalidation code like this is _very_ bug-prone, and
what's worse, the bugs are often difficult to find, because often they
rely on a precise sequence of modifications that cause a stale value
to affect a user-visible computation. Playing it safe and working on
one thing at a time pays dividends.

The `dirty_height` flag is kind of similar; for that we must:

- Check all children's `dirty_height` when computing `height`;
- Reset `dirty_height` by computing `height`;
- Set the parent's `dirty_height` when `height` is recomputed.

That code looks like this:

``` {.python replace=self.height/new_height}
class BlockLayout:
    def layout(self):
        # ...
        if self.dirty_height:
            assert not self.dirty_children
            for child in self.children:
                assert not child.dirty_height
            self.height = sum([child.height for child in self.children])
            self.parent.dirty_height = True
            self.dirty_height = False
```

The code is very similar to the `dirty_x` code, and that's good,
because for tricky code like this, having a rigid style with clear
roles for each line of code helps avoid bugs. But do note a key
difference: since `x` position is computed top-down, that code checked
the parent's `dirty_x` flag, and set its children's `dirty_x`. Height,
on the other hand, is computed bottom-up, so it checks its children's
`dirty_height` flag and sets its parent's `dirty_height`.

::: {.further}

:::

Dirty flags for *y* positions
=============================

Finally, let's tackle the `dirty_y` flag. This one is trickier than
the others, because the `y` position depends not only on the _parent_
element's `y` position, but also the _previous_ element's `y` and
`height`. To handle `dirty_y` properly, we'll need to:

- Check the previous sibling's `dirty_y` and `dirty_height`, or the
  parent's `dirty_y`, when `y` is recomputed;
- And reset `dirty_y` by computing `y`.
- Set the children's and next sibling's `dirty_y` when `y` is
  recomputed;
- Also, set the next sibling's `dirty_y` when `height` is recomputed;

The corresponding code looks like this; note that we need to add code
to the `dirty_height` block which sets `dirty_y`:

``` {.python}
class BlockLayout:
    def layout(self):
        if self.dirty_y:
            assert not self.previous or not self.previous.dirty_y
            assert not self.previous or not self.previous.dirty_height
            assert not self.parent.dirty_y
            if self.previous:
                self.y = self.previous.y + self.previous.height
            else:
                self.y = self.parent.y
            for child in self.children:
                child.dirty_y = True
            if self.next:
                self.next.dirty_y = True
            self.dirty_y = False
        # ...
        if self.dirty_height:
            # ...
            if self.next:
                self.next.dirty_y = True
```

Since we need to access the next sibling, we will also need to save
that:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        if previous: previous.next = self
        self.next = None
```

Note a couple of interesting things about this `dirty_y` code. First
off, both when checking dirty flags and when setting them, we need to
make sure the relevant next sibling exists. This wasn't an issue
before because `BlockLayout` elements always have parents.

Second, note that the `y` computation uses _either_ the previous
node's `y` position and `height`, _or_ the parent node's `y` position.
Yet the code checks that _both_ of those nodes have their dirty bits
cleared. This makes the assertions a little stricter than they need to
be; we're acting as if every node depends on its parent's `dirty_y`
flag, but in fact only the some nodes will. Similarly, when the `y`
position of a node is recomputed, we set all its children's `dirty_y`
flags, even though only the first child will actually read the new `y`
position.

Skipping no-op updates
======================

Being overly strict is preferable to trying to write overly clever
code that is then incorrect. It is sometimes important to use careful
logic to set fewer dirty bits, so that less invalidation has to happen
and so the browser can therefore be faster, but these kind of
optimizations get complicated quickly: the logic to determine which
dirty flags to set often end up reading data that itself needs to be
invalidated. Getting this kind of code right is very challenging, and
even if it is written correctly, this kind of subtle flag-setting
logic is extremely brittle as the code changes. Typically it's best to
keep "clever" flag setting logic to a minimum, justifying each
departure from setting all the flags with detailed profiling.

But one optimization is pretty straightforward and can lead to big
wins. Right now, when we set a field like `width`, we immediately set
dirty flags for all fields that depend on it. This is the right thing
to do, but it's a big of a waste if we set the `width` to its previous
value. Recomputing a field and getting the same value as before is
quite common, especially for the `height` field, where it's common to
add or remove text from a single line without changing the height of
the line.

We can skip setting dirty flags in this case: merely compute the new
height and compare it to the old value before setting dirty flags:

``` {.python}
class BlockLayout:
    def layout(self):
        if self.dirty_height:
            for child in self.children:
                assert not child.dirty_height
            new_height = sum([child.height for child in self.children])
            if self.height != new_height:
                self.height = new_height
                self.parent.dirty_height = True
                if self.next:
                    self.next.dirty_y = True
            self.dirty_height = False
```

The value of this optimization isn't that it avoids setting one or two
dirty flags---it's that it also avoids setting the dirty flags that
would be set by those dirty flags, and so on. For `height`, which ends
up influencing the `height` of every later layout object, this is
especially important, though it's worth adding this optimization for
every layout field.

Avoiding redundant recursion
============================

All of the layout fields in `BlockLayout` are now wrapped in careful
invalidation logic, ensuring that we only compute `x`, `y`, `width`,
or `height` values when absolutely necessary. That's good: it causes
faster layout updates on complex web pages.

For example, consider the following web page, which contains a `width`
animation from [Chapter 13](animations.md#compositing), followed by
the complete text of Chapter 13 itself:

In this example, the animation changes the `width` of an element, and
therefore forces a layout update to compute the new size of the
animated element. But since Chapter 13 itself is pretty long, and has
a lot of text, recomputing layout takes a lot of time, with almost all
of that time spent updating the layout of the text, not the animating
element.

With our invalidation code, layout updates are somewhat faster, since
usually the actual layout values aren't being recomputed. But they
still take a long time---dozens or hundreds of milliseconds, depending
on your computer---because the browser still needs to traverse the
layout tree, diligently checking that it has no work to do at each
node. There's a solution to this problem, and it involves pushing our
invalidation approach one step further.

So far, we've thought about the *data* dependencies of a particular
layout computation, for example with a node's `height` depending on
the `height` of its children. But computations also have *control*
dependencies, which refers to the sequence of steps needed to actually
run a certain piece of code. For example, computing a node's `height`
depends on calling that node's `layout` method, which depends on
calling its parent's `layout` method, and so on. We can apply
invalidation to control dependencies just like we do to data
dependencies.

So---in what cases do we need to make sure we call a particular
`layout` method? Well, the `layout` method does three things: create
layout objects, modify their layout properties, and recurse into more
calls to `layout`. If a layout object's dirty flags are all unset, the
`layout` call won't create layout objects or modify layout properties,
and if that's true for all its descendants as well, their calls to
`layout` won't do anything either and recursing won't matter. So we
should be able to skip the recursive `layout` calls.

To track this property, let's add a new `dirty_descendants` field to
each `BlockLayout`:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.dirty_descendants = True
```

We'll want this flag to be set if any other dirty flag is set. So, any
time a dirty flag is set, we'll want to set the `dirty_descendants`
flag on all ancestors:

``` {.python}
def mark_dirty(node):
    if isinstance(node.parent, BlockLayout) and \
        not node.parent.dirty_descendants:
        node.parent.dirty_descendants = True
        mark_dirty(node.parent)
```

Now we'll call this any time we set a dirty flag. The best way to make
this change in your code is to search it for `dirty_.* = True`, but
here's the full list of layout objects that need to be marked dirty in
my browser:

 - In the `innerHTML_set` method in `JSContext`, the `elt.layout_object`
 - In the `keypress` method in `Frame`, the `self.tab.focus.layout_object`
 - In the `style` function if `node.style != old_style`, the `node.layout_object`
 - In the `layout` method if `dirty_zoom`, `self`
 - In the `layout` method if `dirty_width`, `child` for each child
 - In the `layout` method if `dirty_x`, `child` for each child
 - In the `layout` method if `dirty_y`, `child` for each child and
   also `self.next` if it exists
 - In the `layout` method if `dirty_height`, `self.parent` and also
   `self.next` if it exists

It's important to call `mark_dirty` any time a dirty flag is set,
because that's the only way to guarantee that if it is _not_ set, all
of the element's descendants are clean and we can skip the recursive
call.

Finally, we can make use of the flag around the recursive `layout`
call:

``` {.python}
class BlockLayout:
    def layout(self):
        # ... 
        if self.dirty_descendants:
            for child in self.children:
                child.layout()
        # ... 
```

With this change, your browser should now be skipping traversals of
most of the tree for most updates, but still doing whatever
recomputations are necessary.

Relative *y* positions
======================

There's still one case, however, where the browser has to traverse the
whole layout tree to update layout computations.


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

*Modifying width*: Add a DOM method that allows JavaScript code to
change an `iframe` element's `width` attribute. This should cause both
the parent and the child frame to be re-laid-out to match the new width.

*Descendant bits for style*: Add descendant dirty bits to the style
phase. This should make the style phase much faster by avoiding
recomputing style for most elements.
