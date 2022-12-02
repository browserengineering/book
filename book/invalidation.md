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

``` {.python}
class Tab:
    def render(self):
        if self.needs_layout:
            self.document = DocumentLayout(self.nodes)
            self.document.layout(self.zoom)
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
class Tab:
    def load(self, url, body=None):
        # ...
        self.document = DocumentLayout(self.nodes)
        self.set_needs_render()

    def render(self):
        if self.needs_layout:
            self.document.layout(self.zoom)
            # ...
```

Next, let's look at the next case, where `BlockLayout` objects are
created by `DocumentLayout`. Here's what that code looks like:

``` {.python}
class DocumentLayout:
    def layout(self, zoom):
        child = BlockLayout(self.node, self, None)
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

``` {.python}
class DocumentLayout:
    def layout(self, zoom):
        if not self.children:
            child = BlockLayout(self.node, self, None)
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
    def layout(self, zoom):
        if not self.children:
            child = BlockLayout(self.node, self, None)
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
    def layout(self, zoom):
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

``` {.python}
class BlockLayout:
    def layout(self, zoom):
        self.children = []
        # ...
        if layout_mode(self.node) == "block":
            previous = None
            for child in self.node.children:
                next = BlockLayout(child, self, previous)
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
    def __init__(self, node, parent, previous):
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
    def innerHTML_set(self, handle, s):
        # ...
        elt.layout_object.dirty_children = True
```

It's important to make sure we set the dirty flag for _all_
dependencies of the protected fields. Otherwise, we'll fail to
recompute the protected fields, causing unpredictable layout glitches.

Next, we need to check the dirty flag before using any field that it
protects. `BlockLayout` uses its `children` field in three places: to
recursively call `layout` on all its children; to compute its
`height`; and to `paint` itself. Let's add a check in each place:

``` {.python}
class BlockLayout:
    def layout(self, zoom):
        # ...
        
        assert not self.dirty_children
        for child in self.children:
            child.layout(zoom)
            
        assert self.dirty_children
        self.height = display_px(
            sum([child.height for child in self.children]), zoom)

    def paint(self):
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
    def layout(self, zoom):
        if layout_mode(self.node) == "block":
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
    def layout(self, zoom):
        if layout_mode(self.node) == "block":
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
    def layout(self, zoom):
        if layout_mode(self.node) == "block":
            if self.dirty_children:
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
    def layout(self, zoom):
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

Protecting layout values
========================
