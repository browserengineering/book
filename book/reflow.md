---
title: Saving Partial Layouts
chapter: 10
prev: scripts
next: security
...

Our little browser now renders pages that *change*. That means it's
now laying out the page multiple times. That translates to a lot of
wasted work: a page doesn't usually change *much*, and layout is
expensive. So in this chapter we'll modify our browser to reuse as
much as it can between layouts.

Profiling our browser
=====================

Before we start speeding up our browser, let's confirm that layout is
taking up a lot of time. And before that, let's list out everything
our browser does. First, on initial load:

-   It downloads a web page (including parsing the URL, opening a
    connection, sending a request, and getting a response);
-   Then it parses the HTML (including lexing and parsing)
-   Then it parses the CSS (including finding linked CSS files,
    downloading them, parsing them, and sorting them)
-   Then it runs the JavaScript (including finding linked JS files,
    downloading them, and running them)

And then every time it does layout:

-   It styles the page
-   It lays out the page
-   It computes the display list

Finally, every time it renders the page, the browser:

-   Applies all of the drawing commands
-   Draws the browser chrome

I'd like to measure how long each of these phases takes. You could use
a profiler, but that would provide a breakdown by function. We're more
interested in a breakdown per phase. So let's make a `Timer` class to
report how long each phase took.

``` {.python}
import time

class Timer:
    def __init__(self):
        self.phase = None
        self.time = None

    def start(self, name):
        if self.phase: self.stop()
        self.phase = name
        self.time = time.time()

    def stop(self):
        dt = time.time() - self.time
        print("[{:>10.6f}] {}".format(dt, self.phase))
        self.phase = None
```

That wacky string in the `print` statement is a Python "format
string" so that the time is right-aligned, ten characters wide, and
has six digits after the decimal point. Using `Timer` is pretty easy.
First we define a `timer` field in our browser:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.timer = Timer()
```

Then we call `start` every time we start one of the phases above. For
example, in `load`, I start the `Downloading` phase:

``` {.python}
self.timer.start("Downloading")
```

Then, at the end of `render`, I stop the timer:

``` {.python}
self.timer.stop()
```

Your results may not match mine,[^1] but here's what I saw on my
console on a full page load for this web page.

[^1]: These results were recorded on a 2019 13-inch MacBook Pro with a
    2.4GHz i5, 8 GB of LPDDR3 memory, and an Intel Iris Plus graphics
    655 with 1.5 GB of video memory, running macOS 10.14.6 and Python
    3.8.5 and Tk 8.5.

    [  0.333341] Downloading
    [  0.023406] Parsing HTML
    [  0.406265] Parsing CSS
    [  0.131022] Running JS
    [  0.023172] Style
    [  0.722214] Layout
    [  0.113295] Display list
    [  0.005794] Rendering
    [  0.003216] Chrome
    
The overall process takes about 1.76 seconds (105 frames), with layout
consuming the largest portion. Moreover, consider that the first four
phases (totalling 0.89 seconds) only happen on initial load, so they
only run once per page. And the final two steps, which run every time
you scroll, take less than a frame, so scrolling is smooth. But style,
layout, and display list generation together---the steps that run when
the page changes, whether due to JavaScript or just from typing in an
input area---take 0.86 seconds or over 50 frames!

You can get a good feel for this latency by typing into an input box
on a large web page. Compare it to typing into the address bar; typing
the address bar doesn't run layout, and it feels fluid and fast,
whereas for the input box you need to type fairly slowly to avoid the
browser freezing up and drawing multiple letters at a time.

Layout needs to be faster. And the same problem exists in real web
browsers too.[^3] In fact, networking and parsing in a real web
browser are similar enough to our toy version,[^2] while layout is
*much more* complex, so the need to speed up layout is correspondingly
even greater.[^4]

[^2]: Granted with caching, keep-alive, parallel connections, and
    incremental parsing to hide the delay...

[^3]: Of course they're also not written in Python...

[^4]: Now is a good time to mention that benchmarking a real browser is
    a lot harder than benchmarking ours. A real browser will run most of
    these phases simultaneously, and may also split the work over
    multiple CPU and GPU processes. Counting how much time everything
    takes is a chore. Real browsers are also memory hogs, so optimizing
    their memory usage is also important!

By the way, this might be the point in the book where you realize you
accidentally implemented something inefficiently. If something other
than the network, parsing, or layout is taking a long time, look into
it.[^inexact] If layout isn't the bottleneck, this chapter won't help!

[^inexact]: The exact speeds of each of these phases can vary, and
    depend on the exercises you implemented and the operating system
    you're using, so don't sweat the details as long as layout is the
    slowest phase.

Relative positions
==================

How can we make layout faster? Well, consider typing into an `<input>`
field. Yes, the web page itself changes, but it does not exactly
change *much*, and that's the key here. Most changes to a web page are
*local*, whether that means local to a single input field or local to
a single HTML element whose children were changed via `innerHTML`.
When the page is *reflowed*---laid out after the initial layout---the
sizes of *most* elements on the page stay the same. We will leverage
this fact to avoid recomputing the layout of most elements.

To do that, we must split layout into two phases. The first phase will
compute widths and heights for each element; when an element changes,
only it, its children, and its ancestors need to run this phase. The
second phase will then compute the absolute positions of each element.
This second phase will run on every element (since one element
changing size might move other elements around), but it'll be fast
enough that that won't take much time.

The `layout` function will thus become two. The width and height
computation will be in a function called `size`; the position
computation will be in a function called `position`. The `size`
function will also compute auxiliary fields like the margin, border,
and padding fields.

I'll start with block layout to understand this split better. Look at
how a block's `x` and `y` positions are computed. Recall that in
general, a layout object's parent sets its `x` and `y`, and then that
layout object adjusts them to account for margins and sets `x` and `y`
values for its own children before calling their `layout` function.

Now, we'll want to move that code into its `position` method:

``` {.python}
class BlockLayout:
    def position(self):
        self.y += self.mt
        self.x += self.ml

        y = self.y
        for child in self.children:
            child.x = self.x + self.pl + self.bl
            child.y = y
            child.position()
            y += child.mt + child.h + child.mb
```

Note that `position` only invokes the children's `position` method. We
need to make `size` call their `size` method. Rename the old `layout`
method to `size`, remove the loop at the end, and replace it with
this:

``` {.python}
class BlockLayout:
    def size(self):
        self.children = []
        # ...
        self.h = 0
        for child in self.children:
            child.size()
            self.h += child.mt + child.h + child.mb
```

Examine these `size` and `position` methods carefully. Check that the
`size` method neither reads nor writes to any layout object's `x` and
`y` fields, and that it only invokes `size` on other layout objects.
Check also that the `position` method writes to the `x` and `y` fields
of the layout object's children and then calls their `position` method.
The upshot of this split is you can lay out a tree of layout objects
by first calling `size` and then calling `position`.

One final subtlety: since the plan is to keep layout objects around
between reflows, you can now longer rely on the constructor being run
right before `size` is. So you'll need to initialize the `children`
field to the empty list at the top of `size`, instead of in the
constructor. Make this change for `InlineLayout` as well!

Let's review the layout object methods before moving on to other
layout modes:

The constructor

:   This method should just set `self.node` and `self.parent`, and
    avoid doing anything else.

`size`

:   This method creates the child layout objects and computes `w` and
    `h` fields. Plus, it calls `ize` on its children. It may not read
    any layout object's `x` or `y` fields, or call any layout object's
    `position` method.

`position`

:   This method must set the `x` and `y` fields any children, then
    call their `position` method.

Let's move on to text, input, and line layout. I'll save inline layout
to the very end.

`TextLayout` and `InputLayout` have no children, so `position` has
nothing to do. Rename the `layout` function to `size` and create an
empty `position` function.

In `LineLayout` the `layout` function computes `w` and `h` in terms of
`max_ascent` and `max_descent`, and then its children's `x` and `y`
values in terms of `baseline`. Let's leave `max_ascent` and
`max_descent` in the `size` method but move `baseline` and the loop
over children to the `position` method.

``` {.python}
class LineLayout:
    def size(self):
        self.w = self.parent.w
        if not self.children:
            self.h = 0
            return
        self.metrics = [child.font.metrics() for child in self.children]
        self.max_ascent = max([metric["ascent"] for metric in self.metrics])
        self.max_descent = max([metric["descent"] for metric in self.metrics])
        self.h = 1.2 * (self.max_descent + self.max_ascent)

    def position(self):
        baseline = self.y + 1.2 * self.max_ascent
        cx = 0
        for child, metrics in zip(self.children, self.metrics):
            child.x = self.x + cx
            child.y = baseline - metrics["ascent"]
            cx += child.w + child.font.measure(" ")
```

Next, `DocumentLayout`. You can rename `layout` to `size` and move the
lines that compute `x` and `y` to a new `position` function:

``` {.python}
class DocumentLayout:
    def position(self):
        child = self.children[0]
        child.x = self.x = 0
        child.y = self.y = 0
        child.position()
```

Finally, inline layout. This is the most complex layout mode, and it
computes positions and sizes in a couple of places:

- Its `w` and `h` fields are computed in `layout`;
- It reads its `y` position in `layout` to initialize the `cy` field;
- It calls `layout` on its children's children in `text` and `input`;
- It computes its children's `x` and `y`, and calls their `layout`
  method, in `flush`.

We're going to have to make some changes.

First, since `w` and `h` are computed in `layout`, let's rename that
method to `size`.

Now, you can't read your `y` position in the `size` phase, since it's
only computed later on, in the `position` phase. So instead of
initializing `cy` to `self.y`, let's initialize it to `0` instead.
Then to compute `h`, we won't need to subtract off `self.y`.

``` {.python}
class InlineLayout:
    def size(self):
        # ...
        self.cy = 0
        self.recurse(self.node)
        self.flush()
        self.children.pop()
        self.h = self.cy
```

Wait a minute... If `h` is just set to `cy`, why not just drop the
`cy` field, and use `h`? Yeah, let's do that:


``` {.python}
class InlineLayout:
    def size(self):
        # ...
        self.h = 0
        self.recurse(self.node)
        self.flush()
        self.children.pop()
```

Next, inside the `text` and `input` methods, we create layout objects
and call their `layout` method. Let's change that to `size`. There's
no point calling their `position` method since it doesn't do anything
anyway.

Finally, the `flush` method creates new children, sets their `x` and
`y` fields, and calls their `layout` method. We'll need to split that.
The `flush` method should just create children and call their `size`
method:

``` {.python}
class InlineLayout:
    def flush(self):
        child = self.children[-1]
        child.size()
        self.h += child.h
        self.children.append(LineLayout(self.node, self))
```

Then we'll make a new `position` method that sets the children's `x`
and `y` fields and calls their `position` methods:

``` {.python}
class InlineLayout:
    def position(self):
        cy = self.y
        for child in self.children:
            child.x = self.x
            child.y = cy
            child.position()
            cy += child.h
```

Now that all the layout objects have been updated, we should have one
final `layout` method in the whole browser: the one on the `Browser`
object itself. It now needs to call both `size` and `position`:

``` {.python}
class Browser:
    def layout(self, tree):
        # ...
        self.timer.start("Layout (phase 1)")
        self.document = DocumentLayout(tree)
        self.document.size()
        self.timer.start("Layout (phase 2)")
        self.document.position()
```

Take the time now to stop and debug. We've done a big refactoring, but
we're still calling both `size` and `position` any time anything
changes, so now is a good time to flush out minor bugs and to read
over every layout object's `size` and `position` methods to check them
over before we we make things more complicated by sometimes avoiding
calls to `size`.

Moving between phases
=====================

Time your browser again, now that layout is split into two phases:

    [  0.026640] Style
    [  0.585366] Layout (phase 1)
    [  0.204182] Layout (phase 2)
    [  0.113936] Display list

If you total these phases up, you get 0.93 seconds. Before this
refactor, the style, layout, and display list phases took 0.86
seconds, which means the refactor made our browser a little slower.

That's not too surprising: two phases mean we have to traverse the
tree twice, and in a couple of places we now have to loop over all
children in each phase. But this refactor wasn't supposed to make our
code faster. Our goal here is to make phase 1 layout much faster by
running it on only some nodes, not all of them.

Let's suppose that works, and phase 1 layout becomes much faster.
For example, suppose it gets 100 times faster:

    [  0.026640] Style
    [  0.005853] Layout (phase 1)
    [  0.204182] Layout (phase 2)
    [  0.113936] Display list

Then the total amount of time our browser needs to reflow the
page---that is, lay it out after a small change---will go from 0.93
seconds to 0.35 seconds. That's quite a bit better! But it's also a
bit disappointing: we made the slowest thing 100 times faster, and
reflow itself didn't even get 3 times faster. This general phenomenon
is called [Amdahl's law][amdahl]: as you speed up some component of a
program, it becomes a smaller and smaller part of the program's run
time, and that means speed-ups in that component translate to smaller
and smaller speed-ups to the program.

[amdahl]: https://en.wikipedia.org/wiki/Amdahl's_law

We want reflow to be as fast as possible. We can't run phase 2 layout
on fewer elements---since changes to one element can change the
position of every other element---but we can try moving things from
phase 2 to phase 1. Look through your layout objects' `position`
methods: are any doing unnecessary computation?

Well, looking them over, `BlockLayout` and `InlineLayout` just have a
loop over their children to compute their `y` position---a bit of
math, nothing else. `DocumentLayout` does even less. And `TextLayout`
and `InputLayout` do nothing at all. But `LineLayout`'s `position`
method is a bit different: it computes font measures and metrics in
order to update the `cx` variable, and those font metrics take time to
compute.

Luckily, the `cx` variable isn't involved with any `x` and `y`
positions at all. That means it could be computed in `size` instead.
So let's change `LineLayout` so that the `cx` variable is computed in
phase 1, and just passed along to phase 2:

``` {.python}
class LineLayout:
    def size(self):
        # ...
        cx = 0
        self.cxs = []
        for child in self.children:
            self.cxs.append(cx)
            cx += child.w + child.font.measure(" ")
```

Then we can use `self.cxs` in `position`:

``` {.python}
class LineLayout:
    def position(self):
        baseline = self.y + 1.2 * self.max_ascent
        for cx, child, metrics in \
          zip(self.cxs, self.children, self.metrics):
            child.x = self.x + cx
            child.y = baseline - metrics["ascent"]
```

Now the timings look a bit like this:

    [  0.024881] Style
    [  0.737944] Layout (phase 1)
    [  0.002762] Layout (phase 2)
    [  0.120213] Display list

Phase 1 layout is longer, but phase 2 is near-instantaneous,[^8] and
now if we manage to run phase 1 on fewer elements, reflow will be a
lot faster. So let's work on avoiding the first phase whenever we can.

[^8]: "Near-instantaneous‽ 2.454 milliseconds is almost 14% of our
    one-frame time budget! And then there's the display list!" Yeah,
    uh, this is a toy web browser written in Python. Cut me some
    slack.

Incrementalizing layout
=======================

The idea is simple, but the implementation will be tricky, because
sometimes you *do* need to lay an element out again; for example, the
element you hover over gains a border, and that changes its width and
therefore potentially its line breaking behavior. So you may need to
run `size` on *that* element. But you won't need to do so on its
siblings. The responsibilities of `size` and `position`, outlined
above, will be our guide to what must run when.

Let's plan. Look over your browser and list all of the places where
`layout` is called. For me, these are:

-   In `load`, on initial page load.
-   In `handle_click`, when the user clicks on an input element.
-   In `keypress`, when the user adds text to an input element.
-   In `js_innerHTML`, when new elements are added to the page (and old
    ones removed).

Each of these needs a different approach:

-   In `load`, we are doing the initial page load so we don't even
    have an existing layout. We need to create one, and that involves
    calling both layout phases for everything.
-   In `js_innerHTML`, the new elements and their parent are the only
    elements that have had their nodes or style changed, so only they
    need the first layout phase.
-   In `handle_click` and `keypress`, only the input element itself
    has had a change to node or style, so only it needs the first
    layout phase.

We'll need to split `layout` into pieces to satisfy the above. Let's
have a `layout` function, which is called on initial layout, and a
`reflow` function that is called when the page changes, to fix up the
layout. The `layout` function will create the `document` object, and
ask to fix up that new object:

```
class Browser:
    def layout(self, tree):
        self.document = DocumentLayout(tree)
        self.reflow(self.document)
```

Meanwhile `reflow` will contain the steps of the old `layout` method:
applying styles, calling `size` on the changed elements, and then
calling `position` and `draw` on all elements:

```
class Browser:
    def reflow(self, obj):
        style(obj.node, None, self.rules)
        obj.size()
        self.document.position()
        self.display_list = []
        self.document.draw(self.display_list)
        self.render()
        self.max_y = self.document.h
```

Note that `style` and `size` are called just on the layout object
passed into `reflow`, while `position` and `draw` are called on the
whole document. When the page it loaded, it'll create the `document`
object and call `reflow` to reflow the whole document. But later
changes to the page can just invoke `reflow` with a particular layout
object, and only that object will be styled and go through phase 1
layout.

Let's go make those changes.

The `load` function doesn't need any changes, because it calls
`layout`, which does initial layout for the whole document.

In `handle_click`, we're interested in the case where the user clicks
on an input element, and we only need to reflow that input element:

``` {.python}
def handle_click:
    # ...
    elif elt.tag == "input":
        elt.attributes["value"] = ""
        self.focus = obj
        return self.reflow(self.focus)
    # ...
```

Likewise in `keypress`:

``` {.python}
def keypress(self, e):
    # ...
    else:
        self.focus.node.attributes["value"] += e.char
        self.dispatch_event("change", self.focus.node)
        self.reflow(self.focus)
```

In `js_innerHTML` we don't have a reference to the layout object lying
around, but we can find it by traversing the tree:[^10]

[^10]: There is a subtlety in the code below. It's important to check
    the current node before recursing, because some nodes have two
    layout objects, in particular block layout elements that contain
    text and thus have both a `BlockLayout` and an `InlineLayout`. We
    want the parent, and doing the check before recursing guarantees us
    that.

``` {.python}
def layout_for_node(tree, node):
    if tree.node == node:
        return tree
    for child in tree.children:
        out = layout_for_node(child, node)
        if out: return out

def js_innerHTML(self, handle, s):
    # ...
    self.reflow(layout_for_node(self.document, elt))
```

With these changes, phase 1 layout is usually run on very few
elements---if you're typing into an input box, just one! The timings
for typing into an input field now look something like this:

    [  0.000042] Style
    [  0.000023] Layout (phase 1)
    [  0.002l37] Layout (phase 2)
    [  0.118164] Display list

You can see that phase 1 layout takes a truly miniscule amount of time
now, and if you try typing into a input box you'll find that input is
smooth and you can see each letter as you type it.

Tracking dependencies
=====================

Recall the general structure of our layout algorithm:

![Width information flows from parent to child, while height
    information flows from child to parent.](/im/layout-order.png)

We're now only running width and height computations for some of our
elements. Why is this OK? Let's think it through to make sure we got
it right.

Think about the subtree that changed, whether due to keypress or
`innerHTML` or something else. It got its width from its parent---and
that parent is unchanged. Every element in that tree computed its
width based on that correct, unchanged parent width, so all the widths
are correct. Then those widths impact heights all through the changed
subtree, and those heights flow up until they reach node being
reflowed.

But if that node's height ended up changing---for example, because
`innerHTML` gave it more or less content---we actually need that
height to keep flowing up, to its unchanged parent and then that
parent's parent and so on. We're not doing that, so we should have a
bug if a node changes height.

Let's try to reproduce the bug. We'll need an HTML page like this:

``` {.html}
<!doctype html>
<script src="test10.js"></script>
<div><button id="button">Click me</button></div>
<div><p id="test">Test</p></div>
<p>Example text which should go below the previous paragraph</p>
```

The idea is that clicking the button should change the page that
makes the `test` paragraph much longer:

``` {.javascript}
var button = document.querySelectorAll("#button")[0]
var test = document.querySelectorAll("#test")[0]
button.addEventListener("click", function() {
    test.innerHTML = "This is a lot of text that is going" +
        " to break over multiple lines, causing this test" +
        " paragraph to change height, which should be a" +
        " problem for our reflow algorithm."
})
```

Try it out. When you click the button, you expect the example text to
move down, but it doesn't. That's because even though the `test`
paragraph had its `size` method invoked, so that its height changed,
the `div` that contains it didn't change, so its `size` method was
never invoked, which means its height was never recomputed, which
means the example text was never moved down.

How do we fix this?

Well, we need to rerun the height computation not just for the
modified elements, but also their parent, and their parent's parent,
and so on. Ok, let's start by moving the code that computes a layout
object's height to a new `compute_height` function. That code should
include the line that sets the `h` field and also any other code that
reads properties of child elements. Call `compute_height` at the end
of `size`. So for `DocumentLayout` the new `compute_height` method
looks like this:

```
class DocumentLayout:
    def compute_height(self):
        self.h = self.children[0].h
```

Remember to also call `compute_height` at the end of the `size`
method.

Next up: the `BlockLayout`. Here `compute_height` looks like this:

``` {.python}
class BlockLayout:
    def compute_height(self):
        self.h = 0
        for child in self.children:
            self.h += child.mt + child.h + child.mb
```

You'll need to call it at the end of `size`, after calling `size` on
all the children.

Next, `InlineLayout`. Here, the height is the sum of the children's
heights, but it's computed incrementally in `flush`. Let's remove the
line that adjusts `h` inside `flush`, and move that into a new
`compute_height` method that just sums the height of the children:

``` {.python}
class InlineLayout:
    def compute_height(self):
        self.h = 0
        for child in self.children:
            self.h += child.h
```

Make sure `flush` no longer adjusts the `h` field.

Next, `LineLayout`. Here, most of the function involves reading
properties on child layout objects, so let's just move all of it,
except the single line that sets the `w` field, to `compute_height`.

``` {.python}
class LineLayout:
    def size(self):
        self.w = self.parent.w
        self.compute_height()
```

Finally, for `InputLayout` and `TextLayout` we just need to move the
single line that sets the element's height into `compute_height`.

Now that we've split `size` into two pieces, we can call the full
`size` method on the changed elements, and just the `compute_height`
method on those elements' parents and ancestors:

``` {.python}
class Browser:
    def reflow(self, obj):
        # ...
        self.timer.start("Layout (phase 1A)")
        obj.size()
        self.timer.start("Layout (phase 1B)")
        while obj.parent:
            obj.parent.compute_height()
            obj = obj.parent
```

Note that I've now got phase 1A layout and phase 1B layout---it's
really a three phase layout algorithm here!

Try the buggy web page we wrote earlier. You should see it correctly
adjust heights after you click the button, making sure that no text
overlaps.

By the way, you might worry that all these extra `compute_height`
calls slowed our browser back down to where we started, but that's not
the case:

    [  0.000046] Style
    [  0.005434] Layout (phase 1A)
    [  0.000025] Layout (phase 1B)
    [  0.003215] Layout (phase 2)
    [  0.110548] Display list

Phase 1B doesn't take a long time because it's only modifying the
ancestors, which there aren't that many of, and also because all of
the `compute_height` methods are very short, just doing a few
additions.

Summary
=======

Over the course of this chapter, we've replaced the simplistic,
single-phase layout algorithm with a complex three-phase algorithm
that allows us to skip most of the work when just one part of the page
changes. That's made typing into input elements much smoother and
means JavaScript interactions go much faster.

Exercises
=========

*Granular timing*: Extend the timer to measure the time to for each
layout phase for each type of layout object. For the initial load of a
large web page (like this one), what percentage of the phase 1A layout
is spent handling inline layouts?

*setAttribute*: Add support for the `setAttribute` method in
JavaScript. Note that this method can be used to change the `id`,
`class`, or `style` attribute, which can change which styles apply to
the affected element; handle that with reflow. Furthermore, you can
use `setAttribute` to update the `href` attribute of a `<link>`
element, which means you must download a new CSS file and recompute
the set of CSS rules. Make sure to handle that edge case as
well.[^not-script]

[^not-script]: If you change the `src` attribute of a `<script>` tag,
oddly enough, the new JavaScript file is not downloaded or executed.
