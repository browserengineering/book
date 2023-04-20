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

In [Chapter 13](animations.md), we use compositing to enable smooth
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
into an input box on it (like the one below) in your browser, you'll
see that it is quite laggy indeed:

<input style="width:100%"/>

Now, in the case of typing into an `input` element, our browser
rebuilds the layout tree, but in fact the layout tree looks the same
each time---the text inside an `input` element doesn't get its own
layout object. But browsers support other forms of text editing which
does affect the layout tree. For example, in a real browser you can
give any element the `contenteditable` attribute to make it editable.
Once you do so, the user can click on the element to add or modify
text in it:

::: {.example contenteditable=true}
Click on this text to edit it.
:::

Let's implement this in our browser---it will make a good test of
invalidation. To begin with, we need to make elements with a
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
    def paint(self):
        # ...
        if self.node.is_focused and "contenteditable" in self.node.attributes:
            text_children = [
                t for t in tree_to_list(self, [])
                if isinstance(t, TextLayout)
            ]
            if text_nodes:
                cx = text_nodes[-1].x + text_nodes[-1].width
                cy1 = text_nodes[-1].y
                cy2 = text_nodes[-1].y + text_nodes[-1].height
            else:
                cx = self.x
                cy1 = self.y
                cy2 = self.y + self.height
            cmds.append(DrawLine(cx, cy1, cx, cy2))
        # ...
```

You should now be able to edit the example above in your own
browser---but if you try it, you'll see that editing is extremely
slow, with each character typed adding multiple frames of delay.

Idempotence
===========

Invalidation is a pretty simple idea: don't redo redundant layout
work. It means not recreating layout objects if the existing ones are
already the right ones, and not recomputing layout values (like a
width or a *y* value) if it is already up to date. Yet invalidation
has a well-earned reputation as a rats' nest, with even real browsers
having dozens of known invalidation bugs as of this writing. That's
because of a real risk that an invalidation bug accidentally forgets
to recompute a value that changed, causing layout glitches, or
recomputes way too many values that didn't change, dramatically
slowing down layout.

So in this chapter, the challenge won't just be implementing
invalidation. It'll be making sure that we implement invalidation
_correctly_. That's going to involve thinking carefully about how each
layout value is computed, and what values it depends on.

Let's start by thinking about how layout objects are created. Right
now, layout objects are created by `Tab`s when `render` is called:

``` {.python file=lab15}
class Frame:
    def render(self):
        if self.needs_layout:
            self.document = DocumentLayout(self.nodes, self)
            self.document.layout(self.frame_width, self.tab.zoom)
            # ...
```

Every time layout runs, the whole layout tree is discarded and a new
one is created, starting with the root `DocumentLayout`. But this is
wasteful: when layout _does_ need to run, it's typically due to a
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
- `LineLayout` objects are created by `BlockLayout`s in `new_line`
- `TextLayout` objects are created by `BlockLayout`s in `text`
- `InputLayout` objects are created by `BlockLayout`s in `input`

Let's start with the first location. The `DocumentLayout` is created
the same way each time, and its argument, `nodes`, is never assigned
to once the page finishes loading. And the `DocumentLayout`
constructor just copies its arguments into the `DocumentLayout`'s
fields. This means every execution of this line of code creates an
identical object.

Because `DocumentLayout` construction has no dependencies that can
change, we only need to do it once. Let's move that one line of code
from `render` to `load`:

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

Next, let's look at the next case, where `BlockLayout` objects are
created by `DocumentLayout`. Here's what that code looks like:

``` {.python file=lab15}
class DocumentLayout:
    def layout(self, width, zoom):
        child = BlockLayout(self.node, self, None, self.frame)
        self.children.append(child)
        # ...
```

As you can see, the arguments to `BlockLayout` here also cannot
change: the `node` field and `self` are never assigned to, while
`None` is just a constant. This means `BlockLayout` construction also
has no arguments, which means we don't need to redo this step if it's
already occurred before.

We might therefore be tempted to skip the redundant work, with
something like this:

``` {.python replace=.append(child)/%20%3d%20[child]}
class DocumentLayout:
    def layout(self, width, zoom):
        if not self.children:
            child = BlockLayout(self.node, self, None, self.frame)
        else:
            child = self.children[0]
        self.children.append(child)
        # ...
```

This reuses an existing `BlockLayout` object if possible. But note the
code that *appends* the `BlockLayout` object to the `children` array.
If we run this line of code twice, the `BlockLayout` will end up in
the `children` array twice, turning our layout tree into a DAG and
causing many strange problems.

If you actually run our browser like this, you'll see odd behavior;
for example, typing into an `<input>` element will trigger layout,
create the duplicate `children` entries, and end up duplicating the
web page on your screen.

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

I examined all of the other `layout` methods to check whether they are
idempotent. I found a few worrying causes:

- In `new_line`, `BlockLayout` will append to its `children` array;
- In `text` and `input`, `BlockLayout` will append to the `children`
  array of some `LineLayout` child
- In `text` and `input`, `BlockLayout` will call `get_font`, as will
  the `TextLayout` and `InputLayout` methods
- Basically every layout method calls `display_px`

Luckily, none of these break idempotence. The `new_line` method is
only called through `layout`, which resets the `children` array.
Similarly, `text` and `input` are also only called through `layout`,
which means all of the `LineLayout` children are reset. And `get_font`
acts as a cache, so multiple calls return the same font object, while
`display_px` just does some math so always returns the same result
given the same inputs. This means the browser should now work
correctly again.

Idempotency is important because it means it doesn't matter _how many_
times a function was called: one call, two calls, ten calls, no matter
what the result is the same. And this means that avoiding redundant
work is safe: if we find that we're calling the function twice with
the same inputs and dependencies, we can just skip the second call
without breaking anything else. So let's turn to that.

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
read from `node.children`, and that `children` array can change as a
result of `innerHTML`. Moreover, in order to even run this code, the
node's `layout_mode` has to be `"block"`, and `layout_mode` itself
also reads the node's `children`.[^and-tags]

[^and-tags]: It also looks at the node's `tag` and the node's
    childrens' `tag`s, but a node's `tag` can't change, so we don't
    need to have a dirty flag for them.
    
We want to avoid redundant `BlockLayout` creation, but recall that
idempotency means that calling a function again _with the same inputs
and dependencies_ yields the same result. Here, because the inputs are
more complicated, we need to know when these inputs, ultimately
meaning the node's `children` array, changes.

To do that, we're going to use a dirty flag:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.dirty_children = True
```

We've seen dirty flags before---like `needs_layout` and
`needs_draw`---but layout is more complex and we're going to need to
think about dirty flags a bit more rigorously. Every dirty flag
protects a certain set of fields; this one protects the `children`
field for a `BlockLayout`. Every dirty flag is involved in three kinds
of activities: it can be _set_ to `True`; _checked_ before use; or
_reset_ to `False`. It's crucially important to understand when each
one happens.

Let's start with setting the flag. Dirty flags start out set, just
like in the code above, but they also have to be set if any
_dependencies_ of the fields they protect change. In this case, the
dirty flag protects the `children` field on a `BlockLayout`, which in
turn depends on the `children` field on an `Element` or `Text` object.
That can be modified by the `innerHTML` API, so we need to set the
dirty flag any time that API is called:

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

Finally, let's talk about resetting the flag. We'll do this when we're
done recomputing the protected field. In this case, we want to reset
the dirty flag when we've recomputed the `children` array, meaning
right after that `if` statement:

``` {.python}
class BlockLayout:
    def layout(self):
        if self.dirty_children:
            if mode == "block":
                # ...
            else:
                # ...
            self.dirty_children = False
```

Before going further, rerun your browser and test it on a web page
that calls `innerHTML`. The browser should run like normal without
triggering the assertion.

Finally, we can now _use_ the `dirty_children` flag to avoid redundant
work. Right now `layout` recreates the `children` array every time,
but it doesn't need to if the children array isn't dirty. Let's find
the line at the top of `layout` that resets the `children` array, and
move it into the two branches of the `if` statement:

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
        if self.dirty_children:
            if mode == "block":
                # ...
```

Try this out on an example web page that runs `innerHTML`. You might
want to throw a `print` statement inside that inner-most `if`
conditional; that way, you'll see that only `BlockLayout`s
corresponding to changed nodes are re-created.

Now let's look at inline layout mode, the other case of this `if`
statement:

``` {.python}
class BlockLayout:
    def layout(self):
        if self.dirty_children:
            else:
                self.children = []
                self.new_line()
                self.recurse(self.node)
```

Here the `new_line` and `recurse` methods add new layout objects to
the `children` array. Can we use `dirty_children` to skip work here as
well? To answer that, read through the `new_line` and `recurse`
methods, as well as the `text` and `inline` methods that they call.
Focus on what kind of data is read to decide whether to create layout
objects and what their arguments should be.

You should notice that the `text` method reads from `node.style`, the
`zoom` argument, and the `self.width` field before creating a
`TextLayout` object. The other methods also read these fields. All of
these dependencies can change, so the `dirty_children` flag is not
enough; we need to check a `dirty_zoom` flag and a `dirty_style` flag
and a `dirty_width` flag before we can skip that code.

::: {.further}

:::

Recursive dirty bits
====================

Let's start with the `zoom` and `style` dependencies; we need to
protect both of these with dirty flags.

::: {.todo}
I think this will be clearer if we go _back_ through Chapter 14 and
change `zoom` to be a recursively computed field, not a flag. This
will give us a chance to introduce recursive computation in the
simplest possible case, and make all our discussions of dirty flags
simpler.
:::

Let's start by adding a dirty flag for the `zoom` field:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.dirty_zoom = True
```

It's set in the `DocumentLayout`:

``` {.python}
class DocumentLayout:
    def layout(self, width, zoom):
        # ...
        if zoom != self.zoom:
            self.zoom = zoom
            child.dirty_zoom = True
        # ...
```

When our `zoom` field is dirty, we recompute it:

``` {.python}
class BlockLayout:
    def layout(self):
        if self.dirty_zoom:
            self.zoom = self.parent.zoom
```

Before we reset the `dirty_zoom` field, we need to set any dirty flags
that depend on `zoom`, like `dirty_width`:

``` {.python}
class BlockLayout:
    def layout(self):
        if self.dirty_zoom:
            # ...
            for child in self.children:
                child.dirty_zoom = True
            self.dirty_width = True
            self.dirty_zoom = False
```

Similarly, every time we use `zoom` we should check the `dirty_zoom`
flag:

``` {.python}
class BlockLayout:
    def layout(self):
        if self.dirty_children:
            else:
                # ...
                self.recurse(self.node)           
                # ...
```

Now let's look at `dirty_style`:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.dirty_style = True
```

We already have an `old_style` in the `style` function, which we can
use to set the `dirty_style` flag:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.dirty_style = True

def style(node, rules, frame):
    # ...
    if node.style != old_style and node.layout_object:
        node.layout_object.dirty_style = True
```

Just like with `dirty_zoom`, we need to check this flag, set any flags
that depend on it, and then reset it:

``` {.python}
class BlockLayout:
    def layout(self):
        if self.dirty_style:
            self.dirty_children = True
            self.dirty_style = False
```

Since the `dirty_style` flag protects the `node.style` field, which is
used in `recurse`, let's check it before we use it:

``` {.python}
class BlockLayout:
    def recurse(self, node):
        assert not self.dirty_style
        # ...
```

We now have protected fields for `dirty_zoom` and `dirty_style`; to
skip redundant re-allocations of layout objects, we just need to add
`dirty_width`:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.dirty_width = True
```

The width of a block is computed by a call to `display_px`. Since
`display_px` is idempotent, its output changes when its inputs or
dependencies do. The zoom argument changes when `dirty_zoom` is set,
so before we reset `dirty_zoom` we need to set `dirty_width`

``` {.python}
class BlockLayout:
    def layout(self):
        if self.dirty_zoom:
            # ...
            self.dirty_width = True
            self.dirty_zoom = False
```

Likewise, the `width` field depends on the parent's `width`, so when
the parent's width is computed, it needs to set the child's
`dirty_width` flag:

``` {.python}
class BlockLayout:
    def layout(self):
        # ...
        if self.dirty_width:
            assert not self.parent.dirty_width
            self.width = self.parent.width
            self.dirty_children = True
            for child in self.children:
                child.dirty_width = True
            self.dirty_width = False
```

There's also a very subtle strangeness in this code: when we set all
the children's `dirty_width` flags, we need to read from `children`.
Does that mean we now depend on `dirty_children`? Luckily, no. If the
set of `children` changed, then we will create new layout objects, and
because they are new they will have their `dirty_width` flag already
set.

One other subtlety you might notice: the parent of a `BlockLayout` can
actually _also_ be a `DocumentLayout`. Does it also need to set its
child's `dirty_width` field when it computes its width? Luckily, also
no: a `DocumentLayout`'s width is a constant, so it never changes and
so its child's `dirty_width` flag doesn't need to be set.

::: {.todo}
Not true, the padding increases when you zoom.
:::

::: {.todo}
Also not true because an iframe can resize when its width attribute is changed.
:::

So now we have `dirty_zoom`, `dirty_style`, and `dirty_width` flags,
which protect the `zoom`, `style`, and `width` fields. And this means
that if any of those fields change, `dirty_children` will get set.
So if that flag isn't set, it's safe to skip the call to `new_line`
and `recurse`:

``` {.python}
class BlockLayout:
    def layout(self):
        # ...
        mode = layout_mode(self.node)
        if self.dirty_children:
            if mode == "block":
                # ...
            else:
                # ...
        # ...
```

Try this out: add a `print` statement to each layout object
constructor and run your browser on some web page---maybe our guest
book server, or some of the animation examples from previous
chapters---where JavaScript makes changes to the page. You should see
that after the initial layout during page load, JavaScript changes
will only cause a few layout objects to be constructed at a time. This
speeds up our browser somewhat, and thanks to the careful work we've
done with dirty bits, the browser should otherwise behave identically.

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

``` {.python replace=BlockLayout:/LineLayout:}
class BlockLayout:
    def mark_dirty(self):
        if isinstance(self.parent, BlockLayout) and \
            not self.parent.dirty_descendants:
            self.parent.dirty_descendants = True
            self.parent.mark_dirty()
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
