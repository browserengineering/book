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

To determine whether the `zoom` argument changed, we can store the old
value and compare:

``` {.python}
class BlockLayout:
    def __init__(self):
        # ...
        self.dirty_zoom = True
        self.zoom = None

    def layout(self, zoom):
        self.dirty_zoom = (zoom != self.zoom)
        if self.dirty_zoom:
            self.zoom = zoom
        # ...
```

Before we reset the `dirty_zoom` field, we need to set any dirty flags
that depend on `zoom`, like `dirty_children`:

``` {.python}
class BlockLayout:
    def layout(self, zoom):
        if self.dirty_zoom:
            # ...
            self.dirty_children = True
            self.dirty_zoom = False
```

Similarly, every time we use `zoom` we should check the `dirty_zoom`
flag:

``` {.python}
class BlockLayout:
    def layout(self, zoom):
        # ...
        assert not self.dirty_zoom
        self.width = display_px(self.parent.width, self.zoom)
        # ...

    def recurse(self):
        assert not self.dirty_zoom
        # ...
```

Now let's look at `dirty_style`:

``` {.python}
class BlockLayout:
    def __init__(self):
        # ...
        self.dirty_style = True
```

We already have an `old_style` in the `style` function, which we can
use to set the `dirty_style` flag:

``` {.python}
class BlockLayout:
    def __init__(self):
        # ...
        self.dirty_style = True

def style(node, rules, tab):
    # ...
    if node.style != old_style:
        node.layout_object.dirty_style = True
```

Just like with `dirty_zoom`, we need to check this flag, set any flags
that depend on it, and then reset it:

``` {.python}
class BlockLayout:
    def layout(self, zoom):
        if self.dirty_style:
            self.dirty_children = True
            self.dirty_style = False
```

Since `dirty_style` flag protects the `node.style` field, which is
used in `recurse`, let's check it before we use it:

``` {.python}
class BlockLayout:
    def recurse(self):
        assert not self.dirty_style
        # ...
```

We now have protected fields for `dirty_zoom` and `dirty_style`; to
skip redundant re-allocations of layout objects, we just need to add
`dirty_width`:

``` {.python}
class BlockLayout:
    def __init__(self):
        # ...
        self.dirty_width = True
```

The width of a block is computed by a call to `display_px`. Since
`display_px` is idempotent, its output changes when its inputs or
dependencies do. The zoom argument changes when `dirty_zoom` is set,
so before we reset `dirty_zoom` we need to set `dirty_width`

``` {.python}
class BlockLayout:
    def layout(self, zoom):
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
    def layout(self, zoom):
        # ...
        if self.dirty_width:
            assert not self.parent.dirty_width
            self.width = display_px(self.parent.width, self.zoom)
            self.dirty_children = True
            for child in self.children:
                self.dirty_width = True
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
no: a `DocumentLayout`'s width is a constant,[^unless-resize] so it
never changes and so its child's `dirty_width` flag doesn't need to be
set.

::: {.todo}
Not true, the padding increases when you zoom.
:::

[^unless-resize]: Of course, if you've implemented browser window
    resizing, then you _do_ need to think about the `DocumentLayout`'s
    `width` changing.

So now we have `dirty_zoom`, `dirty_style`, and `dirty_width` flags,
which protect the `zoom`, `style`, and `width` fields. And this means
that if any of those fields change, `dirty_children` will get set.
So if that flag isn't set, it's safe to skip the call to `new_line`
and `recurse`:

``` {.python}
class BlockLayout:
    def layout(self, zoom):
        # ...
        if self.needs_children:
            mode = layout_mode(self.node)
            if mode == "block":
                # ...
            else:
                # ...
        # ...
```

Try this out. Add a `print` statement to each layout object
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

``` {.python}
class BlockLayout:
    def layout(self):
        # ...
        self.x = self.parent.x
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y
        # ...
        self.height = sum([
            child.height for child in self.children])
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

The `assert` here should never fire, because we always compute the `x`
position in a top-down traversal of the layout tree, which means we
would always recompute the parent's `x`, and reset its `dirty_x`,
before recursing to its children. But invalidation code like this can
be _very_ bug-prone, and what's worse, the bugs are often difficult to
find, because often they rely on a precise sequence of modifications
that cause a stale value to affect a user-visible computation. Being
vigilant and defensive in code like this pays for itself.

The `dirty_height` flag is kind of similar; for that we must:

- Check all children's `dirty_height` when computing `height`;
- Reset `dirty_height` by computing `height`.
- Set the parent's `dirty_height` when `height` is recomputed;

That code looks like this:

``` {.python}
class BlockLayout:
    def layout(self):
        # ...
        if self.dirty_height:
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
            if self.next: self.next.dirty_y = True
            self.dirty_y = False
        # ...
        if self.dirty_height:
            # ...
            self.next.dirty_y = True
```

Since we need to access the next sibling, we will also need to save
that:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous):
        # ...
        self.next = None
        previous.next = self
```

Note a couple of interesting things about this `dirty_y` code. First
off, both when checking dirty flags and when setting them, we need to
make sure the relevant element exists. This wasn't an issue before
because `BlockLayout` elements always have parents.

Second, note that the `y` computation uses _either_ the previous
node's `y` position and `height`, _or_ the parent node's `y` position.
Yet the code checks that _both_ of those nodes have their dirty bits
cleared. This makes the assertions a little stricter than they need to
be; we're acting as if every node depends on its parent's `dirty_y`
flag, but in fact only the some nodes will. Similarly, when the `y`
position of a node is recomputed, we set all its children's `dirty_y`
flags, even though only the first child will actually read the new `y`
position.

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


Avoid redundant recursion
=========================

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


Skipping no-op updates
======================
