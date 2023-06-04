---
title: Reusing Previous Computations
chapter: 16
prev: embeds
next: skipped
...

We [previously](animations.md) improved animation performance by
improving our browser's graphics subsystem. But that doesn't help
interactions that affect layout, like text editing or JavaScript DOM
modifications. Luckily, we can avoid redundant layout work using a
technique called invalidation. While invalidation is traditionally
complex and bug-prone, a principled approach and simple abstractions
can make it managable, and the complexity is necessary to make key
user interactions like text input much faster.

Editing Content
===============

In [Chapter 13](animations.md), we used compositing to smoothly
animate CSS properties like `transform` or `opacity`. However, other
CSS properties are _layout-inducing_ and can't be animated this way,
because they change not only the _display list_ but also the _layout
tree_. And while layout-inducing animations are best avoided, lots of
other interactions require changing the layout tree yet need to be as
smooth as possible.

One good example is editing text. People type pretty quickly, so even
a few frames' delay is distracting. But editing changes the HTML tree
and therefore requires changing the layout tree to reflect new text.
Currently, that forces our browser to rebuild the layout tree from
scratch, which can drop multiple frames on complex pages like this
one. Try, for example, typing into this input box in our toy browser:

<input style="width:100%"/>

Typing into an `input` element could be special-cased,[^no-resize] but
there are other text editing APIs that can't be. For example, the
`contenteditable` attribute makes any element editable:

[^no-resize]: The `input` element doesn't change size as you type, and
    the text in the `input` element doesn't get its own layout object,
    so the layout tree is actually the same after each edit.

::: {.demo contenteditable=true}
Click on this <i>formatted</i> <b>text</b> to edit it.
:::

Let's implement `contenteditable` in our browser---it's a useful
feature and also a good test of invalidation. To begin with, we need
to make elements with a `contenteditable` property
focusable:[^other-values]

[^other-values]: Actually, in real browsers, `contenteditable` can be
    set to `true` or `false`, and `false` is useful in case you want
    to have a non-editable element inside an editable one. But I'm
    going to skip supporting that.

``` {.python}
def is_focusable(node):
    # ...
    elif "contenteditable" in node.attributes:
        return True
    # ...
```

Once we're focused on an editable node, typing should edit it. A real
browser would handle cursor movement and all kinds of complications,
but I'll keep it simple and just add each character to the last text
node in the editable element. First we need to find that element:

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

Note that if the editable element has no text children, we create a
new one. Then we add the typed character to this element:

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

``` {.python replace=.width/.width.get()}
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

``` {.python replace=.x/.x.get(),.y/.y.get(),.height/.height.get()}
def DrawCursor(elt, offset):
    x = elt.x + offset
    return DrawLine(x, elt.y, x, elt.y + elt.height)
```

We might as well also use this wrapper in `InputLayout`:

``` {.python replace=self.font/self.font.get()}
class InputLayout(EmbedLayout):
    def paint(self, display_list):
        if self.node.is_focused and self.node.tag == "input":
            cmds.append(DrawCursor(self, self.font.measureText(text)))
```

You can now edit the examples on this page in your toy browser---but
each key stroke will take hundreds of milliseconds to type, making for
a slow and frustrating editing experience. Let's now work toward
making that faster.

::: {.further}
Actually, text editing is [exceptionally hard][editing-hates-you],
including tricky concepts like caret affinity (which line the cursor
is on, if a long line is wrapped in the middle of a word), unicode
handling, [bidirectional text](http://unicode.org/faq/bidi.html), and
mixing text formatting with editing. So it's a good thing browsers
implement all this complexity and hide it behind the `contenteditable`
API!
:::

[editing-hates-you]: https://lord.io/text-editing-hates-you-too/

Idempotence
===========

At a high level, the reason editing is slow is that each edit
recomputes the page's layout tree---and on a large page like this one,
that takes a long time. But is recomputing layout necessary? Adding a
single letter to a single word on a single line of the page doesn't
exactly change the page dramatically: almost everything stays in the
exact same place. If we could reuse the old layout, instead of
throwing it away, editing could conceivably be pretty snappy.

The layout recomputation happens in `render` every time the layout
changes:

``` {.python file=lab15}
class Frame:
    def render(self):
        if self.needs_layout:
            self.document = DocumentLayout(self.nodes, self)
            self.document.layout(self.frame_width, self.tab.zoom)
            # ...
```

When we create a new `DocumentLayout`, we throw away all of the old
layout information and start from scratch. Invalidation begins with
not doing that.

But before jumping right to coding, let's review how layout objects
are created. Search your browser code for `Layout`, which all layout
class names end with. You should see that layout objects are created
in just a few places:

- `DocumentLayout` objects are created by the `Tab` in `render`
- `BlockLayout` objects are created by either:
  - A `DocumentLayout`, in `layout`
  - A `BlockLayout`, in `layout`
- `LineLayout` objects are created by `BlockLayout` in `new_line`
- All others are created by `BlockLayout` in `add_inline_child`

We want to _avoid_ creating layout objects, instead reusing them
whenever possible. That both saves time immediately (allocating new
objects takes time) and sets us up for more speedups by keeping around
the old layout information.

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

But don't run your browser with these changes just yet! By reusing
layout objects, we end up running `layout` multiple times on the same
object. That's not what the `layout` method expects, so it causes all
sorts of weird behavior.

For example, after the `DocumentLayout` creates its child
`BlockLayout`, it *appends* it to the `children` array:

``` {.python file=lab15}
class DocumentLayout:
    def layout(self, width, zoom):
        # ...
        self.children.append(child)
        # ...
```

But we don't want to `append` the same child more than once! The issue
here is called *idempotence*: repeated calls to `layout` need to not
repeatedly change state. More formally, a function is idempotent if
calling it twice in a row with the same inputs and dependencies yields
the same result. Idempotent functions are like assignments: assigning
a field the same value for a second time doesn't change its state.
Methods like `append`, however, aren't idempotent.

We'll need to fix any non-idempotent method calls. In
`DocumentLayout`, we can switch from `append` to assignment:

``` {.python}
class DocumentLayout:
    def layout(self, width, zoom):
        # ...
        self.children = [child]
        # ...
```

However, `BlockLayout` also calls `append` on its `children` array.
That's going to be harder to fix, so for now, reset the `children`
array at the top of `layout`:

``` {.python}
class BlockLayout:
    def layout(self):
        self.children = []
        # ...
```

This makes the `BlockLayout`'s `layout` function idempotent because
each call will assign a new `children` array.

Let's check all other `layout` methods for idempotency by reading them
and noting any non-idempotent method calls. I found:[^exercises]

[^exercises]: If you've being doing exercises throughout this book,
    there might be more, in which case it might be harder to follow
    along, depending on how you've implemented them. But the core idea
    is replacing non-idempotent calls with idempotent ones.

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
HTTP also features a [notion of idempotence][idempotence-mdn], but
that notion is subtly different from the one we're discussing here
because HTTP involves both a client and a server. In HTTP, idempotence
only covers the effects of a request on the server state, not the
response. So, for example, requesting the same page twice with `GET`
might result in different responses (if the page has changed) but the
request is still idempotent because it didn't make any change to the
server. And HTTP idempotence also only covers client-visible state, so
for example it's possible that the first `GET` request goes to cache
while the second doesn't, or it's possible that each one adds a
separate log entry.
:::

[idempotence-mdn]: https://developer.mozilla.org/en-US/docs/Glossary/Idempotent


Dependencies
============

So far, we've only looked at one place where layout objects are
created. Let's look at another: `BlockLayout`s created when laying out
another `BlockLayout`. Here's the relevant code; it only runs in block
layout mode:

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
result of `contenteditable` edits or `innerHTML` calls.[^or-others]
Moreover, in order to even run this code, the node's `layout_mode` has
to be `"block"`, and `layout_mode` itself also reads the node's
`children`.[^and-tags]

[^or-others]: Or any other exercises and extensions that you've implemented.

[^and-tags]: It also looks at the node's `tag` and the node's
    childrens' `tag`s, but a node's `tag` can't change, so I don't
    think of those as dependencies. In invalidation we care only about
    dependencies that can change.

To avoid redundant `BlockLayout` creation, recall that idempotency
means that calling a function again _with the same inputs and
dependencies_ yields the same result. Here, the inputs can change, so
we can only avoid redundant re-execution _if the node's `children`
field hasn't changed_.

To know whether that's the case, we're going to use a dirty flag:

``` {.python expected=False}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.children_dirty = True
```

We've seen dirty flags before---like `needs_layout` and
`needs_draw`---but layout is more complex and we're going to need to
think about dirty flags a bit more rigorously.

Every dirty flag protects a certain field; this one protects a
`BlockLayout`'s `children` field. A dirty flag has a certain life
cycle: it can be set, checked, and reset. The dirty flag is set to
`True` when an input or dependency of the field changes, marking the
protected field as unusable. Then, before using the protected field,
the dirty flag must be checked. Finally, once the field is recomputed,
the flag is reset to `False` to indicate that the value is up to date.

So let's analyze the `children_dirty` flag in this way. Dirty flags
have to be set if any _dependencies_ of the fields they protect
change. In this case, the dirty flag protects the `children` field of
a `BlockLayout`, which in turn depends on the `children` field of the
associated `Element`. That means that any time an `Element`'s
`children` field is modified, we need to set the dirty flag for the
associated `BlockLayout`:

``` {.python replace=children_dirty%20%3d%20True/children.mark()}
class JSContext:
    def innerHTML_set(self, handle, s, window_id):
        # ...
        obj = elt.layout_object
        while not isinstance(obj, BlockLayout):
            obj = obj.parent
        obj.children_dirty = True
```

Likewise, we need to set the dirty flag any time we edit a
`contenteditable` element, since that can also affect the `children`
of a node:

``` {.python replace=children_dirty%20%3d%20True/children.mark()}
class Frame:
    def keypress(self, char):
        elif self.tab.focus and "contenteditable" in self.tab.focus.attributes:
            # ...
            obj = self.tab.focus.layout_object
            while not isinstance(obj, BlockLayout):
                obj = obj.parent
            obj.children_dirty = True
```

It's important that _all_ dependencies of the protected field set the
dirty bit. Otherwise, we'll fail to recompute the protected fields,
causing unpredictable layout glitches. And this can be challenging,
since it requires being vigilent about which fields depend on which
others.

Anyway, the next step is, check the dirty flag before using the
protected field. `BlockLayout` uses its `children` field in three
places: to recursively call `layout` on all its children; to compute
its `height`; and to `paint` itself. Let's add a check in each place:

``` {.python replace=self.height/new_height expected=False}
class BlockLayout:
    def layout(self):
        # ...
        
        assert not self.children_dirty
        for child in self.children:
            child.layout()
            
        assert not self.children_dirty
        self.height = sum([child.height for child in self.children])

    def paint(self, display_list):
        assert not self.children_dirty
        # ...
```

It's tempting to skip these assertions, since the children will always
be up to date when this code is called, but adding these checks helps
avoid bugs down the line as you add more invalidation. It's very easy
to compute some field but skip computing its dependencies, or compute
fields in the wrong order, and that will cause hard-to-diagnose bugs.

Finally, when the field is recomputed we need to reset the dirty flag.
Here, we reset the flag when we've recomputed the `children` array,
meaning right after that `if mode` statement:

``` {.python expected=False}
class BlockLayout:
    def layout(self):
        if mode == "block":
            # ...
        else:
            # ...
        self.children_dirty = False
```

Run your browser again and test it on this page. When editing, the
browser should run like normal without triggering any assertions. It's
important to work incrementally and test often---because if you make a
mistake, it can be pretty difficult to figure out what it was.

With the `children_dirty` flag properly set and reset, we can finally
use it to avoid redundant work. Right now `layout` recreates the
`BlockLayout`s every time it's called, but it doesn't need to if
`children` isn't dirty. Let's skip the `BlockLayout` creation in that
case.

First, find the line at the top of `layout` that resets the `children`
array, and move it into the two branches of the `if` statement:

``` {.python expected=False}
class BlockLayout:
    def layout(self):
        if mode == "block":
            self.children = []
            # ...
        else:
            self.children = []
            # ...
```

Now, in the block case, we can skip recreating the `children` array if
it's not dirty:

``` {.python expected=False}
class BlockLayout:
    def layout(self):
        if mode == "block":
            if self.children_dirty:
                self.children = []
                previous = None
                for child in self.node.children:
                    next = BlockLayout(child, self, previous, self.frame)
                    self.children.append(next)
                    previous = next
```

Try this out again. If you add a `print` statement inside that
inner-most `if`, you'll see every time we recreate the `BlockLayout`
children; when editing text, it shouldn't happen at all, and that will
make editing somewhat smoother.

::: {.further}
If you've heard [Phil Karlton's saying][quote-originates] that "the
two hardest problems in computer science are cache invalidation and
naming things", you know that managing more and more dirty flags explodes
complexity. Phil worked at Netscape at one point (officially as "[Principal
Curmudgeon][curmudgeon]") so I like to imagine him saying that quote
while talking about layout invalidation.
:::

[quote-originates]: https://www.karlton.org/2017/12/naming-things-hard/
[curmudgeon]: https://www.karlton.org/karlton/


Protected fields
================

Dirty flags like `children_dirty` are the traditional approach to
layout invalidation, but they have some downsides. As you've seen,
using them correctly means paying careful attention to the
dependencies between various fields and tracking when fields are used.
In our simple browser, you could do it by hand, but a real browser's
layout system is much more complex, and mistakes become impossible to
avoid.

We need a better approach. As a first step, let's try to combine a
dirty flag and the field it protects into a single object:

``` {.python replace=(self)/(self%2c%20node%2c%20name)}
class ProtectedField:
    def __init__(self):
        self.value = None
        self.dirty = True
```

That clarifies which dirty flag protects which field. We can replace
our existing dirty flag with this simple abstraction:

``` {.python ignore=ProtectedField}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.children = ProtectedField()
        # ...
```

Next, let's add methods for each step of the dirty flag life cycle.
I'll say that we `mark` a protected field to set its dirty flag:

``` {.python}
class ProtectedField:
    def mark(self):
        if self.dirty: return
        self.dirty = True
```

Note that I added an "early exit": marking an already-dirty field
doesn't do anything. That'll become relevant later. Call `mark` in
`innerHTML_set` and `keypress`:

``` {.python}
class JSContext:
    def innerHTML_set(self, handle, s, window_id):
        # ...
        obj.children.mark()

class Frame:
    def keypress(self, char):
        elif self.tab.focus and "contenteditable" in self.tab.focus.attributes:
            # ...
            obj.children.mark()
```

Before getting a `ProtectedField`'s value, let's check the dirty flag:

``` {.python}
class ProtectedField:
    def get(self):
        assert not self.dirty
        return self.value
```

Now we can use `get` to read the `children` field in `layout` and in
lots of other places besides:

``` {.python expected=False}
class BlockLayout:
    def layout(self):
        # ...
        for child in self.children.get():
            child.layout()

        self.height = sum([child.height for child in self.children.get()])
```

The nice thing about `get` is it makes the dirty flag operations
automatic, and therefore impossible to forget. It also make the code a
little nicer.

Finally, to reset the dirty flag, let's make the caller pass in a new
value for the field. This guarantees that the dirty flag and the value
are updated together:

``` {.python}
class ProtectedField:
    def set(self, value):
        self.value = value
        self.dirty = False
```

To use `set` in `BlockLayout`, I'll build the children array in a
local variable and then `set` the `children` field:

``` {.python}
class BlockLayout:
    def layout(self):
        if mode == "block":
            if self.children.dirty:
                children = []
                previous = None
                for child in self.node.children:
                    next = BlockLayout(child, self, previous, self.frame)
                    children.append(next)
                    previous = next
                self.children.set(children)
```

As with `get`, the `set` method automates the dirty flag operations,
making them hard to mess up. `ProtectedField` frees us from
remembering that two fields (`children` and `children_dirty`) go
together and makes sure we always check and reset dirty flag when
we're supposed to.

::: {.further}
[Under-invalidation][under-invalidation] is the technical name for the
bug where you forget to set the dirty flag on a field when you change
a dependency. These bugs are [hard to find][hard-to-find], because
they typically only show up if you make a very specific sequence of
changes. The characteristic symptom of this bug is that a particular
change needs to happen multiple times to "take". In other words, this
kind of bug creates accidental non-idempotency!
:::

[under-invalidation]: https://developer.chrome.com/articles/layoutng/#under-invalidation
[hard-to-find]: https://developer.chrome.com/articles/layoutng/#correctness


Recursive invaliation
=====================

Armed with the `ProtectedField` class, let's take a look at how a
`BlockLayout` element creates `LineLayout`s and their children. It all
happens inside this `if` statement:

``` {.python file=lab15 ignore=self.children}
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

``` {.python ignore=ProtectedField}
class DocumentLayout:
    def __init__(self, node, frame):
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

``` {.python ignore=ProtectedField}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.zoom = ProtectedField()
        # ...
```

However, in the `BlockLayout`, the `zoom` field comes from its
parent's `zoom` field. We might be tempted to write something like
this:

``` {.python dropline=self.parent.zoom.get() replace=set(parent_zoom)/copy(self.parent.zoom)}
class BlockLayout:
    def layout(self):
        if self.zoom.dirty:
            parent_zoom = self.parent.zoom.get()
            self.zoom.set(parent_zoom)
        # ...
```

However, recall that with dirty flags we must always think about
setting them, checking them, and resetting them. The `get` method
automatically checks the dirty flags, and the `set` method
automatically resets them, but who *sets* the `zoom` dirty flags?

Generally, we need to set a dirty flags when something it depends on
changes. That's why we call `mark` in the `innerHTML_set` and
`keypress` handlers: those change the DOM tree, which the layout
tree's `children` field depends on. So since a child's `zoom` field
depends on its parents' `zoom` field, we need to mark all the children
when the `zoom` field changes:

``` {.python .example}
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

``` {.python replace=(self)/(self%2c%20node%2c%20name),depended_on/depended_lazy}
class ProtectedField:
    def __init__(self):
        # ...
        self.depended_on = set()
```

We can mark all of the dependencies with `notify`:

``` {.python replace=depended_on/depended_lazy}
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

``` {.python .example}
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

``` {.python replace=depended_on/depended_lazy}
class ProtectedField:
    def read(self, field):
        field.depended_on.add(self)
        return field.get()
```

Now the `zoom` computation just needs to use `read`, and all of the
marking and dependency logic will be handled automatically:

``` {.python dropline=self.parent.zoom replace=set(parent_zoom)/copy(self.parent.zoom)}
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
    def copy(self, field):
        self.set(self.read(field))
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
The `ProtectedField` class defined here is a type of [monad][monad],
a programming pattern used in programming languages like
[Haskell][haskell]. In brief, a monad describes a way to connect
computations, but the specifics are [famously
confusing][monad-tutorials]. Luckily, in this chapter we don't really
need to think about monads in general, just `ProtectedField`.
:::

[monad]: https://en.wikipedia.org/wiki/Monad_(functional_programming)
[haskell]: https://www.haskell.org/
[monad-tutorials]: https://wiki.haskell.org/Monad_tutorials_timeline





Protecting widths
=================

Protecting `zoom` was relatively simple, but it points the way toward
protecting complex layout fields. Working toward our goal of
invalidating line breaking, let's next work on protecting the `width`
field.

Like `zoom`, `width` is initially set in `DocumentLayout`:

``` {.python ignore=ProtectedField}
class DocumentLayout:
    def __init__(self, node, frame):
        # ...
        self.width = ProtectedField()
        # ...

    def layout(self, width, zoom):
        # ...
        self.width.set(width - 2 * device_px(HSTEP, zoom))
        # ...
```

Then, `BlockLayout` copies it from the parent:

``` {.python ignore=ProtectedField}
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

``` {.python replace=node.style/self.children%2c%20node.style}
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

``` {.python ignore=ProtectedField}
class Element:
    def __init__(self, tag, attributes, parent):
        # ...
        self.style = ProtectedField()
        # ...

class Text:
    def __init__(self, text, parent):
        # ...
        self.style = ProtectedField()
        # ...
```

This style field is computed in the `style` method, which builds the
map of style properties through multiple phases. Let's build that new
dictionary in a local variable, and `set` it once complete:

``` {.python expected=False}
def style(node, rules, frame):
    old_style = node.style.value
    new_style = {}
    # ...
    node.style.set(new_style)
```

Inside `style`, a couple of lines read from the parent node's style.
We need to mark dependencies in these cases:

``` {.python expected=False}
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

``` {.python dropline=read(node.style) replace=style/self.children%2c%20node.style}
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

``` {.python replace=list)/l),ProtectedField/list,if/if%20not}
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

::: {.further}
In real browsers, the layout phase is sometimes split in two, first
constructing a layout tree and then a separate [fragment
tree][fragment-tree].[^our-book-simple] In Chrome, the fragment tree
is immutable, and invalidation is done by comparing the previous
and new fragment trees instead of by using dirty flags, though the
overall algorithm ends up pretty similar to what this book describes.
:::

[fragment-tree]: https://developer.chrome.com/articles/renderingng-data-structures/#the-immutable-fragment-tree

[^our-book-simple]: This book doesn't separate out the fragment tree
    because our layout algorithm is simple enough not to need it.


Widths for inline elements
==========================

For uniformity, let's make all of the other layout object types also
protect their `width`; that means `LineLayout`, `TextLayout`, and then
`EmbedLayout` and its variants. `LineLayout` is pretty easy:

``` {.python ignore=ProtectedField}
class LineLayout:
    def __init__(self, node, parent, previous):
        # ...
        self.width = ProtectedField()
        # ...

    def layout(self):
        # ...
        if self.width.dirty:
            self.width.copy(self.parent.width)
        # ...
```

In `TextLayout`, we again need to handle `font`:

``` {.python expected=False}
class TextLayout:
    def __init__(self, node, parent, previous, word):
        # ...
        self.width = ProtectedField()
        # ...

    def layout(self):
        # ...
        if self.width.dirty:
            style = self.width.read(self.node.style)
            zoom = self.width.read(self.zoom)
            self.font = font(style, zoom)
            self.width.set(self.font.measureText(self.word))
        # ...
```

In `EmbedLayout`, we just need to protect the `width` field:

``` {.python ignore=ProtectedField}
class EmbedLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.width = ProtectedField()
        # ...
```

There's also a reference to `width` in the `layout` method for
computing `x` positions. For now you can just use `get` here.

Now all that's left are the various types of replaced content. In
`InputLayout`, the width only depends on the zoom level:

``` {.python}
class InputLayout(EmbedLayout):
    def layout(self):
        # ...
        if self.width.dirty:
            zoom = self.width.read(self.zoom)
            self.width.set(device_px(INPUT_WIDTH_PX, zoom))
        # ...
```

`IframeLayout` and `ImageLayout` are very similar, with the width
depending on the zoom level and also the element's `width` and
`height` attributes. Luckily, our browser doesn't provide any way to
change those attributes, so we don't need to track them as
dependencies.^[That said, a real browser *would* need to make those
attributes `ProtectedField`s as well.] So they're handled just like
`InputLayout`.


Once again, make sure you go through the associated `paint` methods
and make sure you're always calling `get` when you use `width`. Check
that your browser works, including with interactions like
`contenteditabel`. If anything's wrong, you just need to make sure
that you're always refering to `width` via methods like `get` and
`read` that check dirty flags.

::: {.further}

:::



Invalidating layout fields
==========================

Protecting every `width` field is good. And every time we protect
another field, we save some layout work and potentially also some
memory (if we can avoid re-allocating something). So let's expand our
invalidation efforts to every other layout field, such as `x`, `y`,
and `height`. As with `width`, let's start with `DocumentLayout` and
`BlockLayout`, which tend to be simpler.

Let's start with `x` positions. On `DocumentLayout`, we can just `set`
the `x` position:

``` {.python ignore=ProtectedField}
class DocumentLayout:
    def __init__(self, node, frame):
        # ...
        self.x = ProtectedField()
        # ...

    def layout(self, width, zoom):
        # ...
        if self.x.dirty:
            self.x.set(device_px(HSTEP, zoom))
        # ...
```

A `BlockLayout`'s `x` position is just its parent's `x` position, so
we can just `copy` it over:

``` {.python ignore=ProtectedField}
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

Easy. Next let's do `height`s. For `DocumentLayout`, we just read the
child's height:

``` {.python ignore=ProtectedField}
class DocumentLayout:
    def __init__(self, node, frame):
        # ...
        self.height = ProtectedField()
        # ...

    def layout(self, width, zoom):
        # ...
        if self.height.dirty:
            child_height = self.height.read(child.height)
            self.height.set(child_height + 2 * device_px(VSTEP, zoom))
```

`BlockLayout` is similar, except it loops over multiple children:

``` {.python ignore=ProtectedField}
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
                for child in children
            ])
            self.height.set(new_height)
```

Note that we have to `read` the `children` field before using it.
That's because `height`, unlike the previous layout fields, depends on
the childrens' fields, not the parent's. Luckily, just using the
`ProtectedField` methods handles this correctly.

Finally, with `height` done, let's do the last layout field, `y`
position. Just like `x`, `y` is just `set` in `DocumentLayout`:

``` {.python ignore=ProtectedField}
class DocumentLayout:
    def __init__(self, node, frame):
        # ...
        self.y = ProtectedField()

    def layout(self, width, zoom):
        # ...
        if self.y.dirty:
            self.y.set(device_px(VSTEP, zoom))
        # ...
```

In `BlockLayout`, we need to sometimes refer to fields of the
`previous` sibling:

``` {.python ignore=ProtectedField}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.y = ProtectedField()

    def layout(self):
        # ...
        if self.y.dirty:
            if self.previous:
                prev_y = self.y.read(self.previous.y)
                prev_height = self.y.read(self.previous.height)
                self.y.set(prev_y + prev_height)
            else:
                self.y.copy(self.parent.y)
        # ...
```

So that's all the layout fields on `BlockLayout` and `DocumentLayout`.
Do go through and fix up these layout types' `paint` methods (and also
the `DrawCursor` helper)---but note that the browser won't quite run
right now, because the `BlockLayout` assumes its children's `height`
fields are protected, but if those fields are `LineLayout`s they aren't.

::: {.further}

:::



Protecting inline layout
========================

Layout for `LineLayout`, `TextLayout`, and `EmbedLayout` and its
subtypes works a little differently. Yes, each of these layout objects
has `x`, `y`, and `height` fields. But they also compute `font` fields
and have `get_ascent` and `get_descent` methods that are called by
other layout objects. We'll protect all of these fields.[^dps] Since
we now have quite a bit of `ProtectedField` experience, we'll do all
the fields in one go.

[^dps]: Including rewriting `ascent` and `descent` to be protected
    fields. It's possible to protect methods as well, using something
    called "destination passing style", where the destination of a
    method's return value is passed to it as an argument, somewhat
    like out parameters in C. But converting to fields is usually
    cleaner.

Let's start with `TextLayout`:

``` {.python ignore=ProtectedField}
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

Note the new `ascent` and `descent` fields.

We'll need to compute these fields in `layout`. All of the
font-related ones are fairly straightforward:

``` {.python dropline=self.font.read(self.node.style) replace=font(style/font(self.font%2c%20self.node.style}
class TextLayout:
    def layout(self):
        # ...

        if self.font.dirty:
            zoom = self.font.read(self.zoom)
            style = self.font.read(self.node.style)
            self.font.set(font(style, zoom))
            
        if self.width.dirty:
            f = self.width.read(self.font)
            self.width.set(f.measureText(self.word))

        if self.ascent.dirty:
            f = self.ascent.read(self.font)
            self.ascent.set(f.getMetrics().fAscent * 1.25)

        if self.descent.dirty:
            f = self.descent.read(self.font)
            self.descent.set(f.getMetrics().fDescent * 1.25)

        if self.height.dirty:
            f = self.height.read(self.font)
            self.height.set(linespace(f) * 1.25)
```

Note that I've changed `width` to read the `font` field instead of
directly reading `zoom` and `style`. It *does* looks a bit odd to
compute `font` again inside each `if` statement, but remember that
each of those `read` calls establishes a dependency for one layout
field upon another. I like to think of each `font` as being scoped to
its `if` statement.[^python-scope]

[^python-scope]: Python scoping doesn't actually work like this, but
many languages like C++ and JavaScript do. Python scoping is also why
I named the font object `f`.

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
                self.x.set(prev_x + prev_font.measureText(' ') + prev_width)
            else:
                self.x.copy(self.parent.x)
```

So that's `TextLayout`. `EmbedLayout` is basically identical, except
that its `ascent` and `descent` are simpler. However, there's a bit of
a catch with how `EmbedLayout`'s subclasses work: `EmbedLayout`
handles computing the `zoom`, `x`, `y`, and `font` fields, each
subclass handles computing the `width` and `height` fields, and then
the `ascent` and `descent` should be handled by `EmbedLayout` but
depend on `height`. To avoid this, I'll split the `EmbedLayout`'s
`layout` method into a `layout_before` method, containing `zoom`, `x`,
`y`, and `font`, and a new `layout_after` method that computes
`ascent` and `descent`:

``` {.python}
class EmbedLayout:
    def layout_before(self):
        # ...
    
    def layout_after(self):
        if self.ascent.dirty:
            height = self.ascent.read(self.height)
            self.ascent.set(-height)
        
        if self.descent.dirty:
            self.descent.set(0)
```

Each of the `EmbedLayout` subclasses can call `layout_before` at the
start of `layout` and `layout_after` at the end. Here's `InputLayout`,
but make the same change to each one:

``` {.python}
class InputLayout(EmbedLayout):
    def layout(self):
        self.layout_before()
        # ...
        self.layout_after()
```

Speaking, each `EmbedLayout` subtype has its own way of computing its
height. Here's `InputLayout`:

``` {.python}
class InputLayout(EmbedLayout):
    def layout(self):
        # ...
        if self.height.dirty:
            font = self.height.read(self.font)
            self.height.set(linespace(font))
        # ...
```

Here's `ImageLayout`; it has an `img_height` field, which I'm not
going to protect and instead treat as an intermediate step in
computing `height`:

``` {.python}
class ImageLayout(EmbedLayout):
    def layout(self):
        # ...
        if self.height.dirty:
            font = self.height.read(self.font)
            self.height.set(max(self.img_height, linespace(font)))
```

Finally, here's `IframeLayout`, which is straightforward:

``` {.python}
class IframeLayout(EmbedLayout):
    def layout(self):
        # ...
        if self.height.dirty:
            zoom = self.height.read(self.zoom)
            if height_attr:
                self.height.set(device_px(int(height_attr) + 2, zoom))
            else:
                self.height.set(device_px(IFRAME_HEIGHT_PX + 2, zoom))
        # ...
```

So that covers all of the inline layout objects. All that's left is
`LineLayout`. Here are `x` and `y`:

``` {.python ignore=ProtectedField}
class LineLayout:
    def __init__(self, node, parent, previous):
        # ...
        self.x = ProtectedField()
        self.y = ProtectedField()
        # ...
```

The computations are straightforward:

``` {.python}
class LineLayout:
    def layout(self):
        # ...

        if self.x.dirty:
            self.x.copy(self.parent.x)

        if self.y.dirty:
            if self.previous:
                prev_y = self.y.read(self.previous.y)
                prev_height = self.y.read(self.previous.height)
                self.y.set(prev_y + prev_height)
            else:
                self.y.copy(self.parent.y)

        # ...
```

However, `height` is a bit complicated: it computes the maximum ascent
and descent across all children and uses that to set the `height` and
the children's `y`. I think the simplest way to handle this code is to
add `ascent` and `descent` fields to the `LineLayout` to store the
maximum ascent and descent, and then have the `height` and the
children's `y` field depend on those:

``` {.python ignore=ProtectedField}
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
            if not self.children:
                self.height.set(0)
                return
```

Note that we don't need to `read` the `children` field because in
`LineLayout` it isn't protected---because it's filled in by
`BlockLayout` when the `LineLayout` is created, and then never
modified.

Next, let's recompute the ascent and descent:

``` {.python}
class LineLayout:
    def layout(self):
        # ...
        if self.ascent.dirty:
            self.ascent.set(max([
                -self.ascent.read(child.ascent)
                for child in self.children
            ]))

        if self.descent.dirty:
            self.descent.set(max([
                self.descent.read(child.descent)
                for child in self.children
            ]))
```

Next, we can recompute the `y` position of each child:

``` {.python}
class LineLayout:
    def layout(self):
        # ...
        for child in self.children:
            if child.y.dirty:
                new_y = child.y.read(self.y)
                new_y += child.y.read(self.ascent)
                new_y += child.y.read(child.ascent)
                child.y.set(new_y)
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
fields use `read` and `get`, and make sure your browser still runs.
Test `contenteditable`, and make sure the browser smoothly updates
with every change. You will likely need to now fix a few uses of
`height` and `y` inside `Frame` and `Tab`, like for clamping scroll
positions.

::: {.further}

:::



Skipping no-op updates
======================

If you try your browser again, you'll probably notice that despite all
of this invalidation work with `ProtectedField`, it's not obvious that
editing is any faster. Let's try to figure out why. Add a `print`
statement inside the `set` method on `ProtectedField`s to see which
fields are getting recomputed:

``` {.python expected=False}
class ProtectedField:
    def set(self, value):
        if self.value != None:
            print("Change", self)
        self.notify()
        self.value = value
        self.dirty = False
```

The `if` statement skips printing during initial page layout. Try
editing some text with `contenteditable` on a large web page (like
this one)---you'll see a *screenful* of output, thousands of lines of
printed nonsense. It's a little hard to understand why, so let's add a
nice printable form for `ProtectedField`s:[^why-print-node]

[^why-print-node]: Note that I print the node, not the layout object,
because layout objects' printable forms print layout field values,
which might be dirty and unreadable.

``` {.python}
class ProtectedField:
    def __init__(self, node, name):
        self.node = node
        self.name = name
        # ...

    def __repr__(self):
        return "ProtectedField({}, {})".format(self.node, self.name)
```

Name all of your `ProtectedField`s, like this:

``` {.python}
class DocumentLayout:
    def __init__(self, node, frame):
        # ...
        self.zoom = ProtectedField(node, "zoom")
        self.width = ProtectedField(node, "width")
        self.height = ProtectedField(node, "height")
        self.x = ProtectedField(node, "x")
        self.y = ProtectedField(node, "y")
```

If you look at your output again, you should now see two phases.
First, there's a lot of `style` recomputation:
    
    Change ProtectedField(<body>, style)
    Change ProtectedField(<header>, style)
    Change ProtectedField(<h1 class="title">, style)
    Change ProtectedField('Reusing Previous Computations', style)
    Change ProtectedField(<a href="https://twitter.com/browserbook">, style)
    Change ProtectedField('Twitter', style)
    Change ProtectedField(' ·\n', style)
    ...

Then, we recompute four layout fields repeatedly:

    Change ProtectedField(<html lang="en-US" xml:lang="en-US">, zoom)
    Change ProtectedField(<html lang="en-US" xml:lang="en-US">, zoom)
    Change ProtectedField(<head>, zoom)
    Change ProtectedField(<head>, children)
    Change ProtectedField(<head>, height)
    Change ProtectedField(<body>, zoom)
    Change ProtectedField(<body>, y)
    Change ProtectedField(<header>, zoom)
    Change ProtectedField(<header>, y)
    ...

Let's fix these. First, let's tackle `style`. The reason `style` is
being recomputed repeatedly is just that we don't skip `style`
recomputation if it isn't dirty. Let's do that:

``` {.python replace=node.style.dirty/needs_style}
def style(node, rules, frame):
    if node.style.dirty:
        # ...

    for child in node.children:
        style(child, rules, frame)
```

There should now be barely any style recomputation at all. But what
about those layout field recomputations? Why are those happening?
Well, the very first field being recomputed here is `zoom`, which
itself traces back to `DocumentLayout`:

``` {.python}
class DocumentLayout:
    def layout(self, width, zoom):
        self.zoom.set(zoom)
        # ...
```

Every time we lay out the page, we `set` the zoom parameter, and we
have to do that because the user might have zoomed in or out. But
every time we `set` a field, that notifies every dependant field. The
combination of these two things means we are recomputing the `zoom`
field, and everything that depends on `zoom`, on every frame.

What makes this all wasteful is that `zoom` usually doesn't change.
So we want to not nodify dependants if the value didn't change:

``` {.python}
class ProtectedField:
    def set(self, value):
        if value != self.value:
            self.notify()
        self.value = value
        self.dirty = False
```

This change is safe, because if the new value is the same as the old
value, any downstream computations don't actually need to change.

This small tweak should reduce the number of field changes down to the
minimum:

    Change ProtectedField(<html lang="en-US" xml:lang="en-US">, zoom)
    Change ProtectedField(<div class="demo" contenteditable="true">, children)
    Change ProtectedField(<div class="demo" contenteditable="true">, height)

The only things happeneing here are recreating the `contenteditable`
element's `children` (which we have to do, to incorporate the new
text) and checking that its `height` didn't change (necessary in case
we wrapped onto more lines). As a bonus, editing should now also feel
*much* snappier.

::: {.further}

:::


Avoiding redundant recursion
============================

All of the layout fields are now wrapped in invalidation logic,
ensuring that we only compute `x`, `y`, `width`, `height`, or other
values when absolutely necessary. That's good: it causes faster layout
updates on complex web pages.

But on the largest web pages it's still not enough. For example, on my
computer, the initial layout for this page takes about 300
milliseconds, while each character typed into a `contenteditable`
takes only 3. That's way faster, but 3 milliseconds is still a
substantial fraction of our 16 millisecond frame budget, and we'd like
to bring it down. Since we know we're not recomputing many layout
fields, all that time must be spent merely traversing the layout tree
looking for work to do. Luckily, there's a way to skip needless
traversals, and it involves pushing invalidation one step further.

So far, we've thought about the *data* dependencies of a particular
layout computation, for example with a node's `height` depending on
its children's `height`s. But computations also have *control*
dependencies: the sequence of steps that lead to that computation
occurring. For example, computing a node's `height` depends on calling
that node's `layout` method, which depends on calling its parent's
`layout` method, and so on. We can apply invalidation to control
dependencies just like we do to data dependencies---though there are
some differences.

Let's start with first principles. In what cases do we need to make
sure we call a particular layout object's `layout` method? Well, the
`layout` method does three things: create layout objects, compute
layout properties, and recurse into more calls to `layout`. Those
steps can be skipped if:

- The layout object's `children` field isn't dirty, meaning we don't
  need to create new layout objects;
- The layout object's layout fields aren't dirty, meaning we don't
  need to compute layout properties; and
- The layout object's children's `layout` methods also don't need to
  be called.

So let's add a new dirty flag, which I call `descendants`,[^ancestors]
to track when these conditions are true:

[^ancestors]: You will also see these called *ancestor* dirty flags
    instead. It's the same thing, just following the flow of dirty
    bits instead of the flow of control.

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.descendants = ProtectedField(node, "descendants")
```

We can add this to every other kind of layout object, too.

This field doesn't store a value, just a dirty flag, but it's
convenient to use the `ProtectedField` machinery. We want this flag
dirty if any descendant has a dirty `children` or layout field.
Something like this is *close* to working:

``` {.python expected=False}
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
this node's layout fields. That's because this element is one of its
parent's (not its own) descendants.

However, this code doesn't quite work, for a couple of reasons.

First of all, `read` asserts that the field being read is not dirty,
and here the fields being read were just created and are therefore
dirty. We need a variant of `read`, which I'll call `control` because
it's for control dependencies:

``` {.python replace=depended_on/depended_eager}
class ProtectedField:
    def control(self, source):
        source.depended_on.add(self)
        self.dirty = True
```

Note that the `control` method doesn't actually read the source field's
value; that's why it's safe to use even when the source field is dirty.
The `descendants` field can use it:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.parent.descendants.control(self.zoom)
        self.parent.descendants.control(self.width)
        self.parent.descendants.control(self.height)
        self.parent.descendants.control(self.x)
        self.parent.descendants.control(self.y)
```

We also need `descendants` to control the `children` field:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.parent.descendants.control(self.children)
```

Finally, we need `descendants` to include not just direct children but
also distant descendants. We can do that with a bit of recursion:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.parent.descendants.control(self.descendants)
```

Replicate this code in every layout object type. In `DocumentLayout`
you won't need to `control` any fields, since `DocumentLayout` has no
parent, and in the other layout objects also `control` the `font`,
`ascent`, and `descent` fields that those layout objects have, and
don't `control` the `children` field, which is unprotected.


Eager and lazy propagation
==========================

Now that we have descendant dirty flags, let's use them to skip
unneeded recursions. We'd like to use the `descendants` dirty flags to
skip recursing in the `layout` method:

``` {.python}
class BlockLayout:
    def layout(self):
        # ...
        if self.descendants.dirty:
            for child in self.children.get():
                child.layout()
            self.descendants.set(None)
        # ...
```

Here the `set` call clears the dirty flags. However, this code doesn't
work. If you run it, your browser will crash when it skips recomputing
a field that was dirty.

This is a consequence of us implementing *lazy* marking. Recall how
the `mark` method works:

``` {.python}
class ProtectedField:
    def mark(self):
        if self.dirty: return
        self.dirty = True
```

When a protected field is marked, *its* dirty field is set, but any
other fields that depend on it aren't set yet.

Lazy marking works for data dependencies but not for control
dependencies. That's because data dependencies are computed before the
dirty flags is checked, meaning the dirty flags gets marked before it's
checked. Lazy marking also allows us to skip no-op updates, so it's
important for data dependencies to be fast.

But for control dependencies we need eager marking. If the `width` of
some layout object is marked, we need its parent's `descendants`
field, which depends on `width`, needs to be marked right away,
_before_ the `width` is recomputed. After all, that `descendats` field
is used to determine _whether_ the `width` is recomputed!

For eager marking, I'll give each protected field a second sets of
fields to mark eagerly:

``` {.python}
class ProtectedField:
    def __init__(self, node, name):
        # ...
        self.depended_lazy = set()
        self.depended_eager = set()
```

The `read` method will be lazy, but `control` will be eager:

``` {.python}
class ProtectedField:
    def read(self, field):
        field.depended_lazy.add(self)
        return field.get()

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
            field.mark()
```

There's one more subtlety here: multi-step dependencies. For example,
imagine changing the `style` of a `<b>` tag from JavaScript. That
might affect the `style` of a `Text` child of that tag, which might
affect the `height` of its `TextLayout`. Because of this chain, we
want the `style` change to mark a bunch of `descendants` flags. But,
because none of the `descendants` flags directly `control` the `style`
field, it doesn't have any eager dependants and no dirty flags are
propagated to the `descendants` field.

To solve this, we need to add one more rule: when one field reads
another, any fields controling the first need to also control the
second:

``` {.python}
class ProtectedField:
    def read(self, field):
        field.depended_lazy.add(self)
        for dependant in self.depended_eager:
            dependant.control(field)
        return field.get()
```

With these changes, the descendant dirty flags should now be set
correctly, and we can now skip recursively calling layout when the
descendants aren't dirty:

``` {.python}
class BlockLayout:
    def layout(self):
        # ...
        if self.descendants.dirty:
            for child in self.children.get():
                child.layout()
            self.descendants.set(None)
        # ...
```

You can replicate this on all the other layout types. Even on larger
web pages, layout should now be under a millisecond, and editing
should be fairly smooth.


Granular style invalidation
===========================

Thanks to all of this invalidation work, we should now have a pretty
fast editing experience,[^other-phases] and many JavaScript-driven
interactions should be fairly fast as well. However, we have
inadvertantly broken smooth animations.

[^other-phases]: It might still be pretty laggy on large pages due to
    the composite-raster-draw cycle being fairly slow, depending on
    which exericses you implemented in [Chapter 13](animations.md).

Here's the basic issue: suppose an element's `opacity` or `transform`
property changes, for example through JavaScript. That property isn't
layout-inducing, so it _should_ be animated entirely through
compositing. However, once we added the protected fields, changing any
style property invalidates the `Element`'s `style` field, and that in
turn invalidates the `children` field, causing the layout tree to be
rebuilt. That's no good.

Ultimately the core problem here is *over*-invalidation caused by
`ProtectedField`s that are too coarse-grained. It doesn't make sense
to depend on the whole `style` dictionary at once; instead, it's
better to depend on each style property individually. To do that, we
need `style` to be a dictionary of `ProtectedField`s, not a
`ProtectedField` of a dictionary:

``` {.python}
class Element:
    def __init__(self, tag, attributes, parent):
        # ...
        self.style = dict([
            (property, ProtectedField(self, property))
            for property in CSS_PROPERTIES
        ])
        # ...
```

Do the same thing for `Text`. The `CSS_PROPERTIES` dictionary contains
each CSS property that we support, and also their default values:

``` {.python}
CSS_PROPERTIES = {
    "font-size": "inherit", "font-weight": "inherit",
    "font-style": "inherit", "color": "inherit",
    "opacity": "1.0", "transition": "",
    "transform": "none", "mix-blend-mode": "normal",
    "border-radius": "0px", "overflow": "visible",
    "outline": "none", "background-color": "transparent",
    "image-rendering": "auto",
}
```

Now, in `style`, we will need to recompute a node's style if *any* of
their style properties are dirty:

``` {.python}
def style(node, rules, frame):
    needs_style = any([field.dirty for field in node.style.values()])
    if needs_style:
        # ...
    for child in node.children:
        style(child, rules, frame)
```

To keep with the existing code, we'll make `old_style` and `new_style`
just map properties to values:

``` {.python}
def style(node, rules, frame):
    if needs_style:
        old_style = dict([
            (property, field.value)
            for property, field in node.style.items()
        ])
        new_style = CSS_PROPERTIES.copy()
        # ...
```

Then, when we resolve inheritance, we specifically have one field of
our style depend on one field of the parent's style:

``` {.python}
def style(node, rules, frame):
    if needs_style:
        for property, default_value in INHERITED_PROPERTIES.items():
            if node.parent:
                parent_field = node.parent.style[property]
                parent_value = node.style[property].read(parent_field)
                new_style[property] = parent_value
```

Likewise when resolving percentage font sizes:

``` {.python}
def style(node, rules, frame):
    if needs_style:
        if new_style["font-size"].endswith("%"):
            if node.parent:
                parent_field = node.parent.style["font-size"]
                parent_font_size = node.style["font-size"].read(parent_field)
```

Then, once the `new_style` is all computed, we individually set every
field of the node's `style`:

``` {.python}
def style(node, rules, frame):
    if needs_style:
        # ...
        for property, field in node.style.items():
            field.set(new_style[property])
```

We now have `style` mapping property names to `ProtectedField`s, so
all that's left is to update the rest of the browser to match. Mostly,
this means replacing `style.get()[property]` with
`style[property].get()`:

``` {.python}
def paint_visual_effects(node, cmds, rect):
    opacity = float(node.style["opacity"].get())
    blend_mode = parse_blend_mode(node.style["mix-blend-mode"].get())
    translation = parse_transform(node.style["transform"].get())
    border_radius = float(node.style["border-radius"].get()[:-2])
    # ...
```

Make sure to do this for all instances of accessing a specific style
property.

However, the `font` method needs a little bit of work. Until now,
we've read the node's `style` and passed that to `font`:

``` {.python expected=False}
class BlockLayout:
    def text(self, node):
        zoom = self.children.read(self.zoom)
        style = self.children.read(node.style)
        node_font = font(style, zoom)
        # ...
```

That won't work anymore, because now we need to read three different
properties of `style`. To keep things compact, I'm going to rewrite
`font` to pass in `self.children`, or whoever is going to be affected
by the font, as an argument:

``` {.python}
def font(who, css_style, zoom):
    weight = who.read(css_style['font-weight'])
    style = who.read(css_style['font-style'])
    try:
        size = float(who.read(css_style['font-size'])[:-2])
    except ValueError:
        size = 16
    font_size = device_px(size, zoom)
    return get_font(font_size, weight, style)
```

Now we can simply pass `self.children` in for the `who` parameter when
requesting a font during line breaking:

``` {.python}
class BlockLayout:
    def text(self, node):
        zoom = self.children.read(self.zoom)
        node_font = font(self.children, node.style, zoom)
        # ...
```

Meanwhile, when computing a `font` field, we pass it in:

``` {.python}
class TextLayout:
    def layout(self):
        if self.font.dirty:
            zoom = self.font.read(self.zoom)
            self.font.set(font(self.font, self.node.style, zoom))
```

This "destination-passing style" is an easy way to write a helper
function for use in computing various `ProtectedField`s. Make sure to
update all other uses of the `font` method to this new interface.

Finally, now that we've added granular invalidation to `style`, we can
invalidate just the animating property when handling animations:

``` {.python}
class Tab:
    def run_animation_frame(self, scroll):
        for (window_id, frame) in self.window_id_to_frame.items():
            for node in tree_to_list(frame.nodes, []):
                for (property_name, animation) in \
                    node.animations.items():
                    value = animation.animate()
                    if value:
                        node.style[property_name].set(value)
                        # ...
```

When a property like `opacity` or `transform` is changed, it won't
invalidate any layout fields (because none of those fields depend on
these properties) and so animations will once again skip layout
entirely.


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

*Emptying an element*: Implement the [`replaceChildren` DOM
method][replacechildren-mdn] when called with no arguments. This
method should delete all the children of a given element. Make sure to
handle invalidation properly.

*Protecting layout phases*: Replace the `needs_style` and
`needs_layout` dirty flags by protecting the `document` field on
`Tab`s. Make sure animations still work correctly: animations of
`opacity` or `transform` shouldn't trigger layout, while animations of
other properties should.

*Transfering children*: Implement the [`replaceChildren` DOM
method][replacechildren-mdn] when called with multiple arguments. Here
the arguments are elements from elsewhere in the
document,[^unless-createelement] which are then removed from their
current parent and then attached to this one. Make sure to handle
invalidation properly.

[replacechildren-mdn]: https://developer.mozilla.org/en-US/docs/Web/API/Element/replaceChildren

[^unless-createelement]: Unless you've implemented the "createElement"
    or "removeChild" exercises [in Chapter 9](scripts.md#exercises),
    in which case they can also be "detached" elements.

*Descendant bits for style*: Add descendant dirty flags for `style`
information, so that the `style` phase doesn't need to traverse nodes
whose styles are unchanged.

*Modifying widths*: Add the `width` and `height` setters on `iframe`
and `image` elements, which allow JavaScript code to change the
element's `width` or `height` attribute. Make sure invalidation works
correctly when changing these values. For `iframe` elements, make sure
adjusting these attributes causes both the parent and the child frame
to be re-laid-out to match the new size.

*Matching children*: Add support for [the `appendChild`
method][appendchild-mdn] if you [haven't
already](scripts.md#exercises). What's interesting about `appendChild`
is that, while it *does* change a layout object's `children` field, it
only does so by adding new children to the end. In this case, you can
keep all of the existing layout object children. Apply this
optimization, at least in the case of block-mode `BlockLayout`s.

[appendchild-mdn]: https://developer.mozilla.org/en-US/docs/Web/API/Node/appendChild

*Invalidating `previous`*: Add support for [the `insertBefore`
method][insertbefore-mdn] if you [haven't
already](scripts.md#exercises). Like `appendChild`, this method only
modifies the `children` field in minor ways, and we want to skip
rebuilding layout objects if we can. However, this method also changes
the `previous` field of a layout object; protect that field on all
block-mode `BlockLayout`s and then apply this optimization to avoid
rebuilding as much of the layout tree as possible.

[insertbefore-mdn]: https://developer.mozilla.org/en-US/docs/Web/API/Node/insertBefore
