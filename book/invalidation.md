---
title: Reusing Previous Computations
chapter: 16
prev: embeds
next: skipped
...

We [used compositing](animations.md) to make animations smoother, but
that doesn't help with interactions that affect layout, like text
editing or DOM modifications. Luckily, we can avoid redundant layout
work by treating the layout tree as a kind of cache, and only
recomputing the parts that change. This *invalidation* technique is
traditionally complex and bug-prone, but we'll use a principled
approach and simple abstractions to make it managable.

Editing Content
===============

In [Chapter 13](animations.md), we used compositing to smoothly
animate CSS properties like `transform` or `opacity`. But we couldn't
animate _layout-inducing_ properties this way because they change not
only the _display list_ but also the _layout tree_. And while it's
best to avoid animating layout-inducing properties, many user
interactions need to be responsive but change the layout tree.

One good example is editing text. People type pretty quickly, so even
a few frames' delay is distracting. But editing changes the HTML tree
and therefore the layout tree. Rebuilding the layout tree from
scratch, which our browser currently does, can drop multiple frames on
complex pages. Try, for example, loading [this
chapter](invalidation.md) in our toy browser and typing into this
input box:

<input style="width:100%"/>

You'll find that it is *much* too slow.

Typing into `input` elements could be special-cased,[^no-resize] but
there are other text editing APIs that can't be. For example, the
`contenteditable` attribute makes any element editable:[^amazing-ce]

[^no-resize]: The `input` element doesn't change size as you type, and
    the text in the `input` element doesn't get its own layout object,
    so typing into an `input` element doesn't really have to induce
    layout, just paint.

[^amazing-ce]: The `contenteditable` attribute can turn any element on
    any page into a living document. It's how we implemented the "typo"
    feature for this book: type `Ctrl-E` (or `Cmd-E` on a Mac) to turn
    it on. The source code is [here](/feedback.js); see the
    `typo_mode` function for the `contenteditable` attribute.

::: {.demo contenteditable=true}
Click on this <i>formatted</i> <b>text</b> to edit it, including rich text!
:::

Let's implement `contenteditable` in our browser---it's a useful
feature and also a good test of invalidation. To begin with, we need
to make elements with a `contenteditable` property
focusable:[^other-values]

[^other-values]: Actually, in real browsers, `contenteditable` can be
    set to `true` or `false`, and `false` is useful in case you want
    to have a non-editable element inside an editable one. But I'm
    not going to implement that in our toy browser.

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
node in the editable element. First we need to find that text node:

``` {.python}
class Frame:
    def keypress(self, char):
        # ...
        elif self.tab.focus and \
            "contenteditable" in self.tab.focus.attributes:
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
        elif self.tab.focus and \
            "contenteditable" in self.tab.focus.attributes:
            # ...
            last_text.text += char
            self.set_needs_render()
```

This is enough to make editing work, but it's convenient to also draw
a cursor to confirm that the element is focused and show where edits
will go. Let's do that in `BlockLayout`:

``` {.python replace=.width/.width.get()}
class BlockLayout:
    def paint(self, display_list):
        # ...
        if self.node.is_focused \
            and "contenteditable" in self.node.attributes:
            text_nodes = [
                t for t in tree_to_list(self, [])
                if isinstance(t, TextLayout)
            ]
            if text_nodes:
                cmds.append(DrawCursor(text_nodes[-1],
                    text_nodes[-1].width))
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
each key stroke will take hundreds of milliseconds, making for a
frustrating editing experience. So let's work on speeding that up.

::: {.further}
Actually, text editing is [exceptionally hard][editing-hates-you],
including tricky concepts like caret affinity (which line the cursor
is on, if a long line is wrapped in the middle of a word), unicode
handling, [bidirectional text](http://unicode.org/faq/bidi.html), and
mixing text formatting with editing. So it's a good thing browsers
implement all this complexity and hide it behind `contenteditable`!
:::

[editing-hates-you]: https://lord.io/text-editing-hates-you-too/


Why Invalidation?
=================

Fundamentally, the reason editing this page is slow in our browser is
that it's pretty big.[^other-reasons] After all, it's not handling the
keypress that's slow: appending a character to a `Text` node takes
almost no time. What takes time is rerendering the whole page
afterwards. On a big page, even tiny changes can take a long time.

[^other-reasons]: I'm sure there are all sorts of performance
    improvements possible without implementing the invalidation
    techniques from this chapter, but invalidation is still essential
    for incremental performance, which is a kind of asymptotic
    guarantee that simple optimizations won't achieve.

We want interactions to be fast, even on large, complex pages, so we
want re-rendering the page to take time proportional to the *size of
the change*, and not proportional to the *size of the page*. I call
this the *principle of incremental performance*, and it's crucial for
handling large and complex web applications. Not only does it mean
fast text editing, it also means that developers can think about
performance one change at a time, without considering the contents of
the whole page. Incremental performance is therefore necessary for
complex applications. But the principle of incremental performance
also really constrains our browser. For example, even *traversing* the
whole layout tree would take time proportional to the whole page, not
the change being made, so we can't even affort to do that.

To achieve incremental performance, we're going to need to think of
the initial render and later re-renders differently.[^big-change] When
the page is first loaded, rendering will take time proportional to the
size of the page. But we'll treat that initial render as a cache.
Later renders will *invalidate* and recompute parts of that cache,
taking time proportional to the size of the change, but won't touch
most of the page.

[^big-change]: While initial and later renders are conceptually
    different, they'll use the same code path. Basically, the initial
    render will be one big change from no page to the initial page,
    while later re-renders will handle smaller changes. And anyway,
    a page could use `innerHTML` to replace the whole page; that would
    be a big change, and rendering it would take time proportional to
    the whole page, because the change is the size of the whole page!
    The point is: all of these will ultimately use the same code path.

The key to this cache-and-invalidate approach will be tracking the
effects of changes. When one part of the page, like a `style`
attribute, changes, other things that depends on it, like that
element's size, change as well. So we'll need to construct a detailed
*dependency graph*, down to the level of each layout field, and use
that graph to determine what to recompute. It will be similar to our
`needs_style` and `needs_layout` flags, but with many more fields.

In a real browser, every step of the rendering pipeline needs to be
incremental, but this chapter focuses on layout.[^why-layout] Most of
this chapter is about tracking dependencies in the dependency graph,
and building abstractions to help us do that. To use those
abstractions, we'll need to refactor our layout engine significantly.
But ultimately, incrementalizing layout will allow us to skip the two
most expensive parts of layout: building the layout tree and
traversing it to compute layout fields. When we're done, re-layout
will take under a millisecond for small changes like text editing.

[^why-layout]: Why layout? Because layout is both important and 
    complex enough to demonstrate most of the core challenges and
    techniques.

::: {.further}
The principle of incremental performance is part of what makes
browsers a good platform. Remember that the web is *declarative*:
web pages only concern themselves with *describing* how the page
looks, and it's up to the browser to implement that description. To us
browser engineers, that creates a whole bunch of complexity. But think
about the web as a whole---it involves not just browser engineers, but
web developers and users as well. Implementing complex invalidation
algorithms in the browser lets web developers focus on making more
interesting applications and gives users a better, more responsive
web. The declarative web makes it possible for the invalidation
algorithms to be written once and then automatically benefit everyone
else who uses the web.
:::



Idempotence
===========

If we want to implement this caching-and-invalidation idea, the first
road block is that our browser rebuilds the layout tree from scratch
every time the layout phase runs:

``` {.python file=lab15}
class Frame:
    def render(self):
        if self.needs_layout:
            self.document = DocumentLayout(self.nodes, self)
            self.document.layout(self.frame_width, self.tab.zoom)
            # ...
```

By creating a new `DocumentLayout`, we ignore all of the old layout
information and start from scratch; we are essentially *invalidating*
the whole tree. So our first optimization has to avoid doing that,
reusing as many layout objects as possible. That both saves time
allocating memory and makes the caching-and-invalidation approach
possible by keeping around the old layout information.

But before jumping right to coding, let's review how layout objects
are created. Search your browser code for `Layout`, which all layout
class names end with. You should see that layout objects are created
in just a few places:

- `DocumentLayout` objects are created by the `Tab` in `render`
- `BlockLayout` objects are created by either:
  - a `DocumentLayout`, in `layout`, or
  - a `BlockLayout`, in `layout`
- `LineLayout` objects are created by `BlockLayout` in `new_line`
- All others are created by `BlockLayout` in `add_inline_child`

Let's start with `DocumentLayout`. It's created in `render`, and its
two parameters, `nodes` and `self`, are the same every time. This
means that identical `DocumentLayout`s are created each
time.[^side-effects] That's wasteful; let's create the
`DocumentLayout` just once, in `load`:

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

Moving on, let's look at where `DocumentLayout` constructs a
`BlockLayout`:

``` {.python file=lab15}
class DocumentLayout:
    def layout(self, width, zoom):
        child = BlockLayout(self.node, self, None, self.frame)
        # ...
```

Once again, the constructor parameters cannot change, so again we can
skip re-constructing this layout object, like so:

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
object. That's not how `layout` is intended to work, and it causes all
sorts of weird behavior. For example, after the `DocumentLayout`
creates its child `BlockLayout`, it *appends* it to the `children`
array:

``` {.python file=lab15}
class DocumentLayout:
    def layout(self, width, zoom):
        # ...
        self.children.append(child)
        # ...
```

But we don't want to `append` the same child more than once!

The issue here is called *idempotence*: repeated calls to `layout`
shouldn't repeatedly change state. More formally, a function is
idempotent if calling it twice in a row with the same inputs and
dependencies yields the same result. Assigning a field is idempotent:
assigning the same value for a second time is a no-op. But methods
like `append` aren't idempotent.

We'll need to fix any non-idempotent method calls. In
`DocumentLayout`, we can switch from `append` to assignment:

``` {.python}
class DocumentLayout:
    def layout(self, width, zoom):
        # ...
        self.children = [child]
        # ...
```

`BlockLayout` also calls `append` on its `children` array. We can fix
that by resetting the `children` array in `layout`. I'll put separate
reset code in the block and inline cases:

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

This makes the `BlockLayout`'s `layout` function idempotent because
each call will assign a new `children` array.

Before we try running our browser, let's read through all of the other
`layout` methods, noting any subroutine calls that might not be
idempotent. I found:[^exercises]

[^exercises]: If you've being doing exercises throughout this book,
    there might be more, in which case there might be more calls. In
    any case, the core idea is replacing non-idempotent calls with
    idempotent ones.

- In `new_line`, `BlockLayout` will append to its `children` array.
- In `text` and `input`, `BlockLayout` will append to the `children`
  array of some `LineLayout` child.
- In `text` and `input`, `BlockLayout` will call `get_font`, as will
  the `TextLayout` and `InputLayout` methods.
- Basically every layout method calls `device_px`.

The `new_line` and `add_inline_child` methods are only called through
`layout`, which resets the `children` array, so they don't break
idempotency. The `get_font` function acts as a cache, so multiple
calls return the same font object. And `display_px` just does math, so
it always returns the same result given the same inputs. In other
words all of our `layout` methods are now idempotent.

Because all of the `layout` methods are now idempotent, it's safe to
call `layout` multiple times on the same object---which is exactly
what we're now doing. More generally, since it doesn't matter _how
many_ times an idempotent function is called, we can *skip redundant
calls*! That makes idempotency the foundation for the rest of this
chapter, which is all about skipping redundant work.

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

So far, we're only reusing two layout objects: the `DocumentLayout`,
and the root `BlockLayout`. Let's look at the other `BlockLayout`s,
created when laying out a `BlockLayout`:

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

This code is a little more complicated than the code that creates the
root `BlockLayout`: the `child` and `previous` arguments come from
`node.children`, and that `children` array can change---as a result of
`contenteditable` edits or calls to `innerHTML`.[^or-others] Moreover,
in order to even run this code, the node's `layout_mode` has to be
`block`, and `layout_mode` itself also reads the node's
`children`.[^and-tags] This makes it harder to know when we need to
recreate the `BlockLayout`s.

[^or-others]: Or any other exercises and extensions that you've implemented.

[^and-tags]: It also looks at the node's `tag` and the node's
    childrens' `tag`s, but `tag`s can't change, so we don't need to
    think about them as dependencies. In invalidation we care only
    about dependencies that can change.

Recall that idempotency means that calling a function again _with the
same inputs and dependencies_ yields the same result. Here, the inputs
can change, so we can only avoid redundant re-execution _if the node's
`children` field hasn't changed_. So we need a way of knowing whether
that `children` field has changed. We're going to use a dirty flag:

``` {.python expected=False}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.children_dirty = True
```

We've seen dirty flags before---like `needs_layout` and
`needs_draw`---but layout is more complex and we're going to need to
think about dirty flags a bit more rigorously.

Every dirty flag *protects* a certain field; this one protects a
`BlockLayout`'s `children` field. A dirty flag has a certain life
cycle: it can be set, checked, and reset. The dirty flag starts out
`True`, and is set to `True` when an input or dependency of the field
changes, marking the *protected field* as unusable. Then, before using
the protected field, the dirty flag must be checked. The flag is reset
to `False` only when the protected field is recomputed.

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
        elif self.tab.focus and \
            "contenteditable" in self.tab.focus.attributes:
            # ...
            obj = self.tab.focus.layout_object
            while not isinstance(obj, BlockLayout):
                obj = obj.parent
            obj.children_dirty = True
```

It's important that _all_ dependencies of the protected field set the
dirty bit. This can be challenging, since it requires being vigilant
about which fields depend on which others. But if we do forget to set
the dirty bit, we'll sometimes fail to recompute the protected
fields, which means we'll display the page incorrectly. Typically
these bugs look like unpredictable layout glitches, and they can be
very hard to debug---so let's be careful.

Anyway, now that we're setting the dirty flag, the next step is
checking the dirty flag before using the protected field.
`BlockLayout` uses its `children` field in three places: to
recursively call `layout` on all its children, to compute its
`height`, and to `paint` itself. Let's add a check in each place:

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

It's tempting to skip these assertions, since they should never be
triggered, but coding defensively like this catches bugs earlier and
makes them easier to debug. It's very easy to invalidate fields in the
wrong order, or skip a computation when it's actually important, and
you'd rather that trigger a crash rather than a subtly incorrect
rendering---at least when debugging a toy browser![^no-crash]

[^no-crash]: Real browsers prefer not to crash.

Finally, when the field is recomputed we need to reset the dirty flag.
Here, we reset the flag when we've recomputed the `children` array:

``` {.python expected=False}
class BlockLayout:
    def layout(self):
        if mode == "block":
            # ...
            self.children_dirty = False
        else:
            # ...
            self.children_dirty = False
```

Now that we have all three parts of the dirty flag done, you should be
able to run your browser and test it on this page. Even when you edit
text or call `innerHTML`, you shouldn't see any assertion failures.
Work incrementally and test often---it makes debugging easier.

Now that the `children_dirty` flag works correctly, we can rely on it
to avoid redundant work. If `children` isn't dirty, we don't need to
recreate the `BlockLayout` children:

``` {.python expected=False}
class BlockLayout:
    def layout(self):
        if mode == "block":
            if self.children_dirty:
                self.children = []
                previous = None
                for child in self.node.children:
                    next = BlockLayout(child, self, previous,
                        self.frame)
                    self.children.append(next)
                    previous = next
                self.children_dirty = False
```

If you add a `print` statement inside that inner-most `if`, you'll see
console output every time `BlockLayout` children are created. Try that
out while editing text: it shouldn't happen at all, and editing will
be slightly smoother.

::: {.further}
If you've heard [Phil Karlton's saying][quote-originates] that "the
two hardest problems in computer science are cache invalidation and
naming things", you know that managing more and more dirty flags
creates increasing complexity. Phil worked at Netscape at one point
(officially as "[Principal Curmudgeon][curmudgeon]") so I like to
imagine him saying that quote while talking about layout invalidation.
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
layout system is much more complex, and mistakes become almost impossible
to avoid.

We need a better approach. As a first step, let's try to combine a
dirty flag and the field it protects into a single object:

``` {.python replace=(self):/(self%2c%20obj%2c%20name%2c%20parent%3dNone%2c%20dependencies%3dNone%2c}
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
        elif self.tab.focus and \
            "contenteditable" in self.tab.focus.attributes:
            # ...
            obj.children.mark()
```

Before "`get`"-ting a `ProtectedField`'s value, let's check the dirty flag:

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

        self.height = \
            sum([child.height for child in self.children.get()])
```

The nice thing about `get` is it makes the dirty flag operations
automatic, and therefore impossible to forget. It also make the code a
little nicer to read.

Finally, to reset the dirty flag, let's make the caller pass in a new
value when "`set`"-ting the field. This guarantees that the dirty flag
and the value are updated together:

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
                    next = BlockLayout(
                        child, self, previous, self.frame)
                    children.append(next)
                    previous = next
                self.children.set(children)
```

As with `get`, the `set` method automates the dirty flag operations,
making them hard to mess up. `ProtectedField` frees us from
remembering that two fields (`children` and `children_dirty`) go
together and makes sure we always check and reset dirty flags when
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
        parent_zoom = self.parent.zoom.get()
        self.zoom.set(parent_zoom)
        # ...
```

However, recall that with dirty flags we must always think about
setting them, checking them, and resetting them. The `get` method
automatically checks the dirty flags, and the `set` method
automatically resets them, but who *marks* the `zoom` dirty flags?
(Without marking them when they change, we will incorrectly skip too much
layout work.)

Generally, we need to mark a dirty flag when something it depends on
changes. That's why we call `mark` in the `innerHTML_set` and
`keypress` handlers: those change the DOM tree, which the layout
tree's `children` field depends on. So since a child's `zoom` field
depends on its parents' `zoom` field, we need to mark all the children
when the `zoom` field changes:

``` {.python .example}
class BlockLayout:
    def layout(self):
        # ...
        for child in self.children.get():
            child.zoom.mark()
```

That said, doing this every time we modify any protected field is a
pain, and it's easy to forget a dependency. What we need is something
seamless: `set`-ting to a field should automatically mark all the
fields that depend on it.

To do that, we're going to need to keep around a set of fields that
depend on this one, called its `invalidations`:

``` {.python replace=(self):/(self%2c%20obj%2c%20name%2c%20parent%3dNone%2c%20dependencies%3dNone%2c}
class ProtectedField:
    def __init__(self):
        # ...
        self.invalidations = set()
```

We can mark all of the dependencies with `notify`:

``` {.python}
class ProtectedField:
    def notify(self):
        for field in self.invalidations:
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
        self.parent.zoom.invalidations.add(self.zoom)
```

That's definitely less error-prone, but it'd be even better if we
didn't have to think about dependencies at all. Think: why _does_ the
child's `zoom` need to depend on its parent's? It's because we read
from the parent's zoom, with `get`, when computing the child's. We can
make a variant of `get` that captures this pattern. The `notify` parameter
indicates a field to invalidate when this field changes. 

``` {.python}
class ProtectedField:
    def read(self, notify):
        self.invalidations.add(notify)
        return self.get()
```

Now the `zoom` computation just needs to use `read`, and all of the
marking and dependency logic will be handled automatically:

``` {.python dropline=self.parent.zoom replace=set(parent_zoom)/copy(self.parent.zoom)}
class BlockLayout:
    def layout(self):
        parent_zoom = self.parent.zoom.read(notify=self.zoom)
        self.zoom.set(parent_zoom)
```

In fact, this pattern where we just copy our parent's value is pretty
common, so let's add a shortcut for it:

``` {.python}
class ProtectedField:
    def copy(self, field):
        self.set(field.read(notify=self))
```

This makes the code a little shorter:

``` {.python}
class BlockLayout:
    def layout(self):
        self.zoom.copy(self.parent.zoom)
        # ...
```

Make sure to go through every other layout object type (there are now
quite a few!) and protect their `zoom` fields also. Anywhere else that
you see the `zoom` field refered to, you can use `get` to extract the
actual zoom value. You can check that you succeeded by running your
browser and making sure that nothing crashes, even when you increase
or decrease the zoom level.

By the way, note that I didn't bother testing the `dirty` flag before
executing this code. That's because computing `zoom` takes barely any
time at all: it's just a copy. Testing dirty bits takes time and
clutters the code, so it's not worth doing for trivial fields like
this one.

But that doesn't mean protecting `zoom` isn't worth it!
Our goal is not to avoid recomputing it, but to avoid *rebuilding the
layout tree at all*---just like we avoided re-creating the `children` array,
but with more dependent fields.

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

Protecting `zoom` points the way toward protecting complex layout
fields. Let's work towards a goal of invalidating line breaking, starting
with protecting the `width` field.

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
        self.width.copy(self.parent.width)
        # ...
```

Note that I am again not testing the `dirty` flag because the actual
computation occurring here is trivial.

However, `width` is more complex than `zoom` because `width` is also
used in a bunch of other places during line wrapping.

For example, `add_inline_child` reads from the `width` to determine
whether to add a new line. We thus need the `children` field to depend
on the `width`:

``` {.python}
class BlockLayout:
    def add_inline_child(self, node, w, child_class,
        frame, word=None):
        width = self.width.read(notify=self.children)
        if self.cursor_x + w > width:
            self.new_line()
        # ...
```

While we're here, note that the decision for whether or not to add a
new line also depends on `w`, which is an input to `add_inline_child`.
If you look through `add_inline_child`'s callers, you'll see that most
of the time, this argument depends on `zoom`:

``` {.python}
class BlockLayout:
    def input(self, node):
        zoom = self.zoom.read(notify=self.children)
        w = device_px(INPUT_WIDTH_PX, zoom)
        self.add_inline_child(node, w, InputLayout, self.frame)
```

The same kind of dependency needs to be added to `image` and `iframe`.

In `text`, however, we need to be a little more careful. This method
computes the `w` parameter using a font returned by `font`:

``` {.python replace=node.style/self.children%2c%20node.style}
class BlockLayout:
    def text(self, node):
        zoom = self.zoom.read(notify=self.children)
        node_font = font(node.style, zoom)
        for word in node.text.split():
            w = node_font.measureText(word)
            self.add_inline_child(
                node, w, TextLayout, self.frame, word)
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
    protected field, and have the `style` field depend on it, but I'm
    taking a short-cut in the interest of simplicity.

``` {.python expected=False}
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
        # ...
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
            if self.children.dirty:
                # ...
        else:
            if self.children.dirty:
                # ...
```

Here, it *is* important to check the dirty flag, because the
computation we are skipping here---line breaking and rebuilding the
layout tree---is pretty expensive.

We also need to fix up `add_inline_child`'s and `new_line`'s
references to `children`. There are a couple of possible fixes, but in
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
        last_line = self.temp_children[-1] \
            if self.temp_children else None
        new_line = LineLayout(self.node, self, last_line)
        self.temp_children.append(new_line)
```

You'll want to do something similar in `add_inline_child`:

``` {.python}
class BlockLayout:
    def add_inline_child(self, node, w, child_class,
        frame, word=None):
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
tree][fragment-tree].[^our-book-simple] In Chromium, the fragment tree
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
`EmbedLayout` and its subclasses. `LineLayout` is pretty easy:

``` {.python ignore=ProtectedField}
class LineLayout:
    def __init__(self, node, parent, previous):
        # ...
        self.width = ProtectedField()
        # ...

    def layout(self):
        # ...
        self.width.copy(self.parent.width)
        # ...
```

In `TextLayout`, we again need to handle `font` (and hence have `width`
depend on `style`):

``` {.python expected=False}
class TextLayout:
    def __init__(self, node, parent, previous, word):
        # ...
        self.width = ProtectedField()
        # ...

    def layout(self):
        # ...
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
        zoom = self.zoom.read(notify=self.width)
        self.width.set(device_px(INPUT_WIDTH_PX, zoom))
        # ...
```

`IframeLayout` and `ImageLayout` are very similar, with the width
depending on the zoom level and also the element's `width` and
`height` attributes. So, we'll need to invalidate the `width` field
if those attributes are changed from JavaScript:

``` {.python}
class JSContext:
    def setAttribute(self, handle, attr, value, window_id):
        # ...
        obj = elt.layout_object
        if isinstance(obj, IframeLayout) or \
           isinstance(obj, ImageLayout):
            if attr == "width":
                obj.width.mark()
```

Otherwise, `IframeLayout` and `ImageLayout` are handled just like
`InputLayout`.

Once again, make sure you go through the associated `paint` methods
and make sure you're always calling `get` when you use `width`. Check
that your browser works, including with interactions like
`contenteditabel`. If anything's wrong, you just need to make sure
that you're always refering to `width` via methods like `get` and
`read` that check dirty flags.

::: {.further}
TODO
:::


Invalidating layout fields
==========================

By protecting the `width` field, we were able to avoid re-building the
layout tree when it changes. This saves some layout work and
potentially also some memory, but it doesn't take layout time down to
zero, because we still have to *traverse* the whole layout tree. We
can use invalidation to skip this work too, but to do that, we first
have to expand invalidation to every other layout field, such as `x`,
`y`, and `height`. As with `width`, let's start with `DocumentLayout`
and `BlockLayout`, which tend to be simpler.

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
        child_height = child.height.read(notify=self.height)
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
        children = self.children.read(notify=self.height)
        new_height = sum([
            child.height.read(notify=self.height)
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
        if self.previous:
            prev_y = self.previous.y.read(notify=self.y)
            prev_height = self.previous.height.read(notify=self.y)
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
TODO
:::

Protecting inline layout
========================

Layout for `LineLayout`, `TextLayout`, and `EmbedLayout` and its
subclasses works a little differently. Yes, each of these layout objects
has `x`, `y`, and `height` fields. But they also compute `font` fields
and have `get_ascent` and `get_descent` methods that are called by
other layout objects. We'll protect all of these.[^dps] Since
we now have quite a bit of `ProtectedField` experience, we'll do all
the fields in one go.

[^dps]: Including rewriting `ascent` and `descent` to be protected
    fields. It's possible to protect methods as well, using something
    called "destination passing style", where the destination of a
    method's return value is passed to it as an argument, somewhat
    like out parameters in C. But converting to fields is usually
    cleaner.

Let's start with `TextLayout`. Note the new `ascent` and `descent` fields:

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

We'll need to compute these fields in `layout`. All of the
font-related ones are fairly straightforward:

``` {.python dropline=self.node.style.read(notify%3dself.font) replace=font(style/font(self.font%2c%20self.node.style}
class TextLayout:
    def layout(self):
        # ...

        zoom = self.zoom.read(notify=self.font)
        style = self.node.style.read(notify=self.font)

        f = self.font.read(notify=self.width)
        self.width.set(f.measureText(self.word))

        f = self.font.read(notify=self.ascent)
        self.ascent.set(f.getMetrics().fAscent * 1.25)

        f = self.font.read(notify=self.descent)
        self.descent.set(f.getMetrics().fDescent * 1.25)

        f = self.font.read(notify=self.height)
        self.height.set(linespace(f) * 1.25)
```

Note that I've changed `width` to read the `font` field instead of
directly reading `zoom` and `style`. It *does* looks a bit odd to
compute `f` repeatedly, but remember that each of those `read` calls
establishes a dependency for one layout field upon another. I like to
think of each `f` as being scoped to its field's computation.

We also need to compute the `x` position of a `TextLayout`. That can
use the previous sibling's font, *x* position, and width:

``` {.python}
class TextLayout:
    def layout(self):
        # ...
        if self.previous:
            prev_x = self.previous.x.read(notify=self.x)
            prev_font = self.previous.font.read(notify=self.x)
            prev_width = self.previous.width.read(notify=self.x)
            self.x.set(
                prev_x + prev_font.measureText(' ') + prev_width)
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
        height = self.height.read(notify=self.ascent)
        self.ascent.set(-height)
        
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

As for computing height in subclasses, here's `InputLayout`:

``` {.python}
class InputLayout(EmbedLayout):
    def layout(self):
        # ...
        font = self.font.read(notify=self.height)
        self.height.set(linespace(font))
        # ...
```

And here's `ImageLayout`; it has an `img_height` field, which I'm not
going to protect and instead treat as an intermediate step in computing
`height`:

``` {.python}
class ImageLayout(EmbedLayout):
    def layout(self):
        # ...
        font = self.font.read(notify=self.height)
        self.height.set(max(self.img_height, linespace(font)))
```

Finally, here's `IframeLayout`, which is straightforward:

``` {.python}
class IframeLayout(EmbedLayout):
    def layout(self):
        # ...
        zoom = self.zoom.read(notify=self.height)
        if height_attr:
            self.height.set(device_px(int(height_attr) + 2, zoom))
        else:
            self.height.set(device_px(IFRAME_HEIGHT_PX + 2, zoom))
        # ...
```

You'll need to remember to invalidate the `height` if the `height`
attribute changes:

``` {.python}
class JSContext:
    def setAttribute(self, handle, attr, value, window_id):
        if isinstance(obj, IframeLayout) or \
           isinstance(obj, ImageLayout):
            # ...
            if attr == "height":
                obj.height.mark()
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

The computations for these are straightforward:

``` {.python}
class LineLayout:
    def layout(self):
        # ...

        self.x.copy(self.parent.x)

        if self.previous:
            prev_y = self.previous.y.read(notify=self.y)
            prev_height = self.previous.height.read(notify=self.y)
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
children's `y` field depend on those.

Let's do that, starting with declaring the protected fields:

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
        self.ascent.set(max([
            -child.ascent.read(notify=self.ascent)
            for child in self.children
        ]))

        self.descent.set(max([
            child.descent.read(notify=self.descent)
            for child in self.children
        ]))
```

Next, we can recompute the `y` position of each child:

``` {.python}
class LineLayout:
    def layout(self):
        # ...
        for child in self.children:
            new_y = self.y.read(notify=child.y)
            new_y += self.ascent.read(notify=child.y)
            new_y += child.ascent.read(notify=child.y)
            child.y.set(new_y)
```

Finally, we recompute the line's height:

``` {.python}
class LineLayout:
    def layout(self):
        # ...
        max_ascent = self.ascent.read(notify=self.height)
        max_descent = self.descent.read(notify=self.height)
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
TODO
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

The `if` statement skips printing during initial page layout, so it
will only show how well our invalidation optimizations are working. Try
editing some text with `contenteditable` on a large web page (like
this one)---you'll see a *screenful* of output, thousands of lines of
printed nonsense. It's a little hard to understand why, so let's add a
nice printable form for `ProtectedField`s, plus a new `name` parameter
for debugging puposes:[^why-print-node]

[^why-print-node]: Note that I print the node, not the layout object,
because layout objects' printable forms print layout field values,
which might be dirty and unreadable.

``` {.python replace=%2c%20name):/%2c%20name%2c%20parent%3dNone%2c%20dependencies%3dNone%2c}
class ProtectedField:
    def __init__(self, obj, name):
        self.obj = obj
        self.name = name
        # ...

    def __repr__(self):
        return "ProtectedField({}, {})".format(
            self.obj.node if hasattr(self.obj, "node") else self.obj,
            self.name)
```

Name all of your `ProtectedField`s, like this:

``` {.python expected=False}
class DocumentLayout:
    def __init__(self, node, frame):
        # ...
        self.zoom = ProtectedField(self, "zoom")
        self.width = ProtectedField(self, "width")
        self.height = ProtectedField(self, "height")
        self.x = ProtectedField(self, "x")
        self.y = ProtectedField(self, "y")
```

If you look at your output again, you should now see two phases.
First, there's a lot of `style` recomputation:
    
    Change ProtectedField(<body>, style)
    Change ProtectedField(<header>, style)
    Change ProtectedField(<h1 class="title">, style)
    Change ProtectedField('Reusing Previous Computations', style)
    Change ProtectedField(<a href="...">, style)
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
So we should notify dependants only if the value didn't change:

``` {.python}
class ProtectedField:
    def set(self, value):
        if value != self.value:
            self.notify()
        # ...
```

This change is safe, because if the new value is the same as the old
value, any downstream computations don't actually need to change. As a
bonus, editing should now also feel snappier.

This small tweak should reduce the number of field changes down to the
minimum:

    Change ProtectedField(<html lang="en-US" xml:lang="en-US">, zoom)
    Change ProtectedField(<div class="demo" ...>, children)
    Change ProtectedField(<div class="demo" ...>, height)

The only things happening here are recreating the `contenteditable`
element's `children` (which we have to do, to incorporate the new
text) and checking that its `height` didn't change (necessary in case
we wrapped onto more lines).

::: {.further}
TODO
:::

Skipping traversals
===================

All of the layout fields are now wrapped in invalidation logic,
which means that if any layout field needs to be recomputed, a
dirty bit somewhere in the layout tree is set. But we're still
*visiting* every layout object to actually recompute them. Instead, we
should use the dirty bits to guide our traversal of the layout tree
and minimize the number of layout objects we need to visit.

The basic idea revolves around the question: do we even need to call
`layout` on a given node? The `layout` method does three things:
create child layout objects, compute layout properties, and recurse into
more calls to `layout`. Those steps can be skipped if:

- The layout object's `children` field isn't dirty, meaning we don't
  need to create new child layout objects;
- The layout object's layout fields aren't dirty, meaning we don't
  need to compute layout properties; and
- The layout object's children's `layout` methods also don't need to
  be called.

Note that we're now thinking about *control* decisions (does a
particular piece of code even need to be run) instead of *data*
dependencies (what that code returns). For example, computing a node's
`height` depends on calling that node's `layout` method, which depends
on calling its parent's `layout` method, and so on. We can apply
invalidation to control dependencies just like we do to data
dependencies---though there are some differences.

So let's add a new dirty flag, which I call `has_dirty_descendants`,
to track whether any descendants have a dirty
`ProtectedField`.[^ancestors]

[^ancestors]: In some code bases, you will see these
called *ancestor* dirty flags instead. It's the same thing, just
following the flow of dirty bits instead of the flow of control.

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...
        self.has_dirty_descendants = False
```

Add this to every other kind of layout object, too.

This will be easy to do with an additional (and optional) `parent` parameter to
a `ProtectedField`. (It's optional because only `ProtectedField`s on layout
objects need this feature.)

``` {.python replace=parent%3dNone):/parent%3dNone%2c%20dependencies%3dNone%2c}
class ProtectedField:
    def __init__(self, obj, name, parent=None):
        # ...
        self.parent = parent
```

Then, whenever `mark` or `notify` is called, we set the bits:


``` {.python}
class ProtectedField:
    def set_ancestor_dirty_bits(self):
        parent = self.parent
        while parent:
            parent.has_dirty_descendants = True
            parent = parent.parent

    def mark(self):
        # ...
        self.set_ancestor_dirty_bits()

    def notify(self):
        # ...
        self.set_ancestor_dirty_bits()
```

For each layout object type, pass the parameter for each `ProtectedField`.
Here's `BlockLayout`, for example:


``` {.python expected=False}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        # ...    
        self.children = ProtectedField(self, "children", self.parent)
        self.zoom = ProtectedField(self, "zoom", self.parent)
        self.width = ProtectedField(self, "width", self.parent)
        self.height = ProtectedField(self, "height", self.parent)
        self.x = ProtectedField(self, "x", self.parent)
        self.y = ProtectedField(self, "y", self.parent)
```

And then the bit needs to be cleared after `layout`:

``` {.python}
class BlockLayout:
    def layout(self):
        # ...
        for child in self.children.get():
            child.layout()

        self.has_dirty_descendants = False    
```

Now that we have descendant dirty flags, let's use them to skip
unneeded recursions. We'd like to use the `descendants` dirty flags to
skip recursing in the `layout` method:

``` {.python}
class BlockLayout:
    def layout(self):
        if not self.layout_needed(): return
        # ...
```

Here, the `layout_needed` method can just check all of the dirty bits
in turn:

``` {.python}
class BlockLayout:
    def layout_needed(self):
        if self.zoom.dirty: return True
        if self.width.dirty: return True
        if self.height.dirty: return True
        if self.x.dirty: return True
        if self.y.dirty: return True
        if self.children.dirty: return True
        if self.has_dirty_descendants: return True
        return False
```

With these changes, the descendant dirty bits should now be set
correctly, and the `layout_needed` approach above should work as long
as you include all of the protected fields for each layout type.

In`DocumentLayout`, you do need to be a little careful, since it
receives the frame width and zoom level as an argument. You need to
make sure to `mark` those fields if they changed. The `width` changes
when the `frame_width` changes, here:[^or-protect-them]

[^or-protect-them]: We need to mark the root layout object's `width`
    because the `frame_width` is passed into `DocumentLayout`'s
    `layout` method as the `width` parameter. We could have protected
    the `frame_width` field instead, and then this `mark` would happen
    automatically; I'm skipping that for expediency, but it would have
    been a bit safer.

``` {.python}
class IframeLayout(EmbedLayout):
    def layout(self):
        if self.node.frame:
            # ...
            self.node.frame.document.width.mark()
```

The `zoom` level changes in `Tab`:

``` {.python}
class Tab:
    def zoom_by(self, increment):
        # ...
        for id, frame in self.window_id_to_frame.items():
            frame.document.zoom.mark()

    def reset_zoom(self):
        # ...
        for id, frame in self.window_id_to_frame.items():
            frame.document.zoom.mark()
```

Once you've done this, layout should now take less than a millisecond
even on large pages, and editing text should be fairly smooth.

::: {.further}

The `ProtectedField` class can also be viewed as an instance of an
[observer pattern][observer-pattern], where different pieces of code can
observe state elsewhere by triggering callbacks when the state changes. This
kind of pattern is common in UI frameworks that have a lot of state with
complex dependencies; one early example is the
[key-value observation pattern][kvo] for macOS.

In the case of our browser, the "observation callbacks" (`mark`/`notify`) simply
set a dirty bit to be cleaned up later, but they could also have been
implemented to *eagerly* re-compute layout directly. For this reason, a
rendering pipeline with dirty bits--as implemented in our browser--can be
viewed as a [*lazy* evaluation][lazy-eval] approach to an observer pattern that
batches updates to improve performance.

[lazy-eval]: https://en.wikipedia.org/wiki/Lazy_evaluation

Real browsers use dirty bits and lazy evaluation, but in most cases
don't actually implement an automatic dependency-tracking class like
`ProtectedField`. One reason for that is performance: with something
like `ProtectedField`, it's easy to accidentally make performance worse
by over-using it in too many performance-sensitive places, or cause a lot of cascading work invalidating dependent protected fields. Another reason may
simply be practical: most browser engine code bases have a lot of historical
code, and it takes a lot of time to refactor them to use new approaches.

:::

[observer-pattern]: https://en.wikipedia.org/wiki/Observer_pattern
[kvo]: https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/KeyValueObserving/KeyValueObserving.html

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

``` {.python expected=False}
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

Now, we have to invalidate fields one by one. For example, when
setting the `style` property from JavaScript, I'll invalidate all of
the fields:

``` {.python}
class JSContext:
    def style_set(self, handle, s, window_id):
        # ...
        for property, value in elt.style:
            value.mark()
        # ...
```

Similarly, in `style`, we will need to recompute a node's style if
*any* of their style properties are dirty:

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
                parent_value = \
                    parent_field.read(notify=node.style[property])
                new_style[property] = parent_value
```

Likewise when resolving percentage font sizes:

``` {.python}
def style(node, rules, frame):
    if needs_style:
        if new_style["font-size"].endswith("%"):
            if node.parent:
                parent_field = node.parent.style["font-size"]
                parent_font_size = \
                    parent_field.read(notify=node.style["font-size"])
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
    weight = css_style['font-weight'].read(notify=who)
    style = css_style['font-style'].read(notify=who)
    try:
        size = float(css_style['font-size'].read(notify=who)[:-2])
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
        zoom = self.zoom.read(notify=self.children)
        node_font = font(self.children, node.style, zoom)
        # ...
```

Meanwhile, when computing a `font` field, we pass it in:

``` {.python expected=False}
class TextLayout:
    def layout(self):
        if self.font.dirty:
            zoom = self.zoom.read(notify=self.font)
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

::: {.further}
TODO
:::


Analyzing dependencies
======================

We now have dirty bits to skip unnecessarily rebuilding the layout
tree and descendant bits to skip unnecessarily traversing it, which
gives us a pretty fast layout engine. Moreover, our `ProtectedField`
abstraction guarantees that dirty bits are always set when necessary.
However, because `Protectedfield` establishes dependencies implicitly,
when `read` is called, it's not always easy to tell _which_ fields
will ultimately get invalidated from any given operation. That makes
it hard to understand which operations are fast and which are slow,
especially as we add new style and layout features.

This *auditability* concern happens in real browsers, too. After all,
real browsers are millions, not thousands, of lines long, and support
thousands, not just a couple, of CSS properties. Their dependency
graphs are therefore dramatically more complex than in our browser. So
let's make it a little easier to see the dependency graph. And along
the way we can extract *invariants* from the code and assert the shape
of that graph in a central place. That will give us a second benefit
of [hardening] our browser against accidental bugs in the future, and
a third one of making the browser a bit faster because it won't need to
update the graph over and over every time layout is run.

[hardening]: https://en.wikipedia.org/wiki/Hardening_(computing)

One easy first step is to explicitly list the dependencies of each
`ProtectedField`. We can make this an optional parameter to each:

``` {.python replace=dependencies%3dNone):/dependencies%3dNone%2c}
class ProtectedField:
    def __init__(self, obj, name, parent=None, dependencies=None):
        # ...
        if dependencies != None:
            for dependency in dependencies:
                dependency.invalidations.add(self)
```

Moreover, if the dependencies are passed in the constructor, we can
"freeze" the `ProtectedField`, so that `read` no longer adds new
dependencies, just checks that they were declared:

``` {.python replace=dependencies%3dNone):/dependencies%3dNone%2c,frozen_dependencies:/frozen_dependencies%20or%20self.frozen_invalidations:}
class ProtectedField:
    def __init__(self, obj, name, parent=None, dependencies=None):
        # ...
        self.frozen_dependencies = dependencies != None
        if dependencies != None:
            for dependency in dependencies:
                dependency.invalidations.add(self)

    def read(self, notify):
        if notify.frozen_dependencies:
            assert notify in self.invalidations
        else:
            self.invalidations.add(notify)

        return self.get()
```

For example, in `DocumentLayout`, we can now be explicit about the
fact that its fields have no external dependencies (and thus have to
be `mark`ed):^[Before I wrote this, I didn't even notice myself that
they have no dependencies!]

``` {.python}
class DocumentLayout:
    def __init__(self, node, frame):
        # ...
        self.zoom = ProtectedField(self, "zoom", None, [])
        self.width = ProtectedField(self, "width", None, [])
        self.x = ProtectedField(self, "x", None, [])
        self.y = ProtectedField(self, "y", None, [])
        self.height = ProtectedField(self, "height")
```

However, note that `height` is missing the third parameter!
That's because a `DocumentLayout`'s height depends on its child's
height, and that child doesn't exist until `layout` is called.
Because of "downward" dependencies like this, we can't freeze
every `ProtectedField`---but every protected field that we
freeze is one more part of the dependency graph that is easy to
audit.

In `BlockLayout`, we likewise can't freeze the `height` field. In the
`y` field, we need to be a bit careful, because the depenendencies
differ based on whether or not the layout object has a previous
sibling:

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
    # ...
    if self.previous:
        y_dependencies = [self.previous.y, self.previous.height]
    else:
        y_dependencies = [self.parent.y]
    self.y = ProtectedField(self, "y", self.parent, y_dependencies)
    # ...
```

We also can't easily freeze the `children` field, because that reads all
sorts of style properties and other fields.

But while we don't know in the constructor, we do actually know the
dependencies of `height` for both `DocumentLayout` and `BlockLayout`
as soon as the children array is created. Let's add a way to
*dynamically* set them in a central place.^[It's dynamic just like the
calls to `read` we added earlier, but at least not spread all over the place---one more [defense-in-depth] against invalidation bugs.] To do
that, add a `set_dependencies` method:

[defense-in-depth]: https://en.wikipedia.org/wiki/Defense_in_depth_(computing)

``` {.python}
class ProtectedField:
    def set_dependencies(self, dependencies):
        for dependency in dependencies:
            dependency.invalidations.add(self)
        self.frozen_dependencies = True
```

And then freeze `height` as soon as possible in `DocumentLayout`:

``` {.python}
class DocumentLayout:
    def layout(self, width, zoom):
        # ...
        if not self.children:
            child = BlockLayout(self.node, self, None, self.frame)
            self.height.set_dependencies([child.height])
```

and `BlockLayout`:

``` {.python}
class BlockLayout:
    def layout(self):
        # ...
        if mode == "block":
            if self.children.dirty:
                # ...
                self.children.set(children)

                height_dependencies = \
                   [child.height for child in children]
                height_dependencies.append(self.children)
                self.height.set_dependencies(height_dependencies)
        else:
            if self.children.dirty:
                # ...
                self.children.set(self.temp_children)

                height_dependencies = \
                   [child.height for child in self.temp_children]
                height_dependencies.append(self.children)
                self.height.set_dependencies(height_dependencies)
```

As for `LineLayout`, everything can be frozen because a line is always
created all at once in our browser, including the children. However,
due to the somewhat complicated way a line is created and then laid out,
we need to delay freezing `ascent` and `descent` until the first time
`layout` is called:

``` {.python}
class LineLayout:
    def __init__(self, node, parent, previous):
        # ...
        self.zoom = ProtectedField(self, "zoom", self.parent,
            [self.parent.zoom])
        self.x = ProtectedField(self, "x", self.parent,
            [self.parent.x])
        if self.previous:
            y_dependencies = [self.previous.y, self.previous.height]
        else:
            y_dependencies = [self.parent.y]
        self.y = ProtectedField(self, "y", self.parent,
            y_dependencies)
        self.ascent = ProtectedField(self, "ascent", self.parent)
        self.descent = ProtectedField(self, "descent", self.parent)
        self.width = ProtectedField(self, "width", self.parent,
            [self.parent.width])
        self.height = ProtectedField(self, "height", self.parent,
            [self.ascent, self.descent])
        self.initialized_fields = False

    def layout(self):
        if not self.initialized_fields:
            self.ascent.set_dependencies(
               [child.ascent for child in self.children])
            self.descent.set_dependencies(
               [child.descent for child in self.children])
            self.initialized_fields = True
```

And `TextLayout` is actually quite straightforward:

``` {.python}
class TextLayout:
    def __init__(self, node, parent, previous, word):
        self.zoom = ProtectedField(self, "zoom", self.parent,
            [self.parent.zoom])
        self.font = ProtectedField(self, "font", self.parent,
            [self.zoom,
             self.node.style['font-weight'],
             self.node.style['font-style'],
             self.node.style['font-size']])
        self.width = ProtectedField(self, "width", self.parent,
            [self.font])
        self.height = ProtectedField(self, "height", self.parent,
            [self.font])
        self.ascent = ProtectedField(self, "ascent", self.parent,
            [self.font])
        self.descent = ProtectedField(self, "descent", self.parent,
            [self.font])
        if self.previous:
            x_dependencies = [self.previous.x, self.previous.font,
            self.previous.width]
        else:
            x_dependencies = [self.parent.x]
        self.x = ProtectedField(self, "x", self.parent,
            x_dependencies)
        self.y = ProtectedField(self, "y", self.parent,
            [self.ascent, self.parent.y, self.parent.ascent])
```

We can even freeze all of the style protected fields! The only ones that
have any dependencies are inherited. And there is a slight complication
that setting `innerHTML` can cause dependencies to change around, so
let's create the style dict dynamically rather than in the constructor.
First set it to `None`:

``` {.python}
class Element:
    def __init__(self, tag, attributes, parent):
        # ...
        self.style = None
```

``` {.python}
class Text:
    def __init__(self, text, parent):
        # ...
        self.style = None
```

Then set it the first time `style` is called:

``` {.python}
def init_style(node):
    node.style = dict([
            (property, ProtectedField(node, property, None,
                [node.parent.style[property]] \
                    if node.parent and \
                        property in INHERITED_PROPERTIES \
                    else None))
            for property in CSS_PROPERTIES
        ])
```

``` {.python}
def style(node, rules, frame):
    if not node.style:
        init_style(node)
```

We ended up freezing every field of layout and style except
`children`. This means that, any time we want to know what depends on
what, we can typically just see a list in the constructor. That's
pretty nice!

::: {.further}

Correct and performant cache invalidation in a web browser is extremely
difficult to get right. That's why it's justified to spend a whole
chapter of this book on the topic, and go out of our way to make
it pretty robust. (More robust than many parts of real browsers, in fact.)

In real browsers, untold hours are spent finding and fixing
invalidation bugs in the rendering engine. For
example, just before writing this section, I^[This is Chris speaking.]
spent *weeks* finding and weeding out a whole class of
under-invalidation bugs in the accessibility code of Chromium. This
particular batch of bugs were especially insidious and difficult to find,
because at first they only reproduced on certain automated test machines
that happened to be more overloaded than other ones. This led to the
HTML parser for the certain test cases yielding[^parser-yield] more often,
triggering different and incorrect rendering paths.

Real browsers also make very agressive use of assertions like those
I added in this chapter. To avoid slowing down the browser for users,
non-essential assertions are "compiled out" in what's usually called
the *release build*, but left in for the *debug build*. The debug build
is often used by engineers when debugging or developing new features,
and also used to run automated tests.

:::

[^parser-yield]: In a real browser, HTML parsing doesn't happen in one go,
but often is broken up into multiple event loop tasks. This leads to better
web page loading performance, and is the reason you'll often see web pages
render only part of the HTML at first when loading large web pages (including
this book!).

Summary
=======

This chapter intoduces the concept of partial style and layout through the
technique of optimized cache invalidation. The main takeways are:

* Partial rendering dramatically speeds up key browser
interactions, and are therefore an essential feature of real browsers.

* Making rendering idempotent allows us to systematically remove work
 without worrying about side-effects.

* A good browser aims to preserve the principle of incremental
performance---the cost of an update should be proportional to the change made.

* Cache invalidation is difficult and error-prone, and justifies careful
work and good abstractions like `ProtectedField`.

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
element's `width` or `height` attribute.^[The `setAttribute` method
you already added in [Chapter 14](/accessibility.md) is another way
to change width and height.] Make sure invalidation works
correctly when changing these values. For `iframe` elements, make sure
adjusting these attributes causes both the parent and the child frame
to be re-laid-out to match the new size.

*Resizing the browser*: Perhaps, back in [Chapter
2](graphics.md#exercises), you implemented support for resizing the
browser. (And most likely, you dropped support for it when we switched
to SDL.) Reimplement support for resizing your browser; you'll need to
pass the `SDL_WINDOW_RESIZABLE` flag to `SDL_CreateWindow` and listen
for `SDL_WINDOWEVENT_RESIZED` events. Make sure invalidation works:
resizing the window show resize the page. How much does invalidation
help make resizing fast? Test both vertical and horizontal resizing.

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
