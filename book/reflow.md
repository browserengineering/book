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
field to the empty list at the top of `size`, instead of in the constructor.

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

One quirk here is that we want to do as little work as possible in
`position`. So let's compute `cx` variable metrics in `size`:

``` {.python}
class LineLayout:
    def size(self):
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
        for cx, child, metrics in zip(self.cxs, self.children, self.metrics):
            child.x = self.x + cx
            child.y = baseline - metrics["ascent"]
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

Incrementalizing layout
=======================

Time your browser again, and note how much time it spends in the first
and second phase of layout:

    [  0.698471] Layout (phase 1)
    [  0.002454] Layout (phase 2)
    [  0.108819] Display list

So we've succeeded in making the second phase near-instantaneous.[^8]
That motivates the next step: avoiding the first phase whenever we can.

[^8]: "Near-instantaneous‽ 2.454 milliseconds is almost 14% of our
    one-frame time budget! And then there's the display list!" Yeah,
    uh, this is a toy web browser written in Python. Cut me some
    slack.

The idea is simple, but the implementation will be tricky, because
sometimes you *do* need to lay an element out again; for example, the
element you hover over gains a border, and that changes its width and
therefore potentially its line breaking behavior. So you may need to
run `size` on *that* element. But you won't need to do so on its
siblings. The responsibilities of `size` and `position`, outlined
above, will be our guide to what must run when.

Let's plan. Look over your browser and list all of the places where
`layout` is called. For me, these are:

-   In `parse`, on initial page load.
-   In `handle_click`, when the user clicks on an input element.
-   In `keypress`, when the user adds text to an input element.
-   In `js_innerHTML`, when new elements are added to the page (and old
    ones removed).

Each of these needs a different approach:

-   In `parse`, we are doing the initial page load so we don't even
    have an existing layout. We need to create one, and that involves
    calling both layout phases for everything.
-   In `js_innerHTML`, the new elements and their parent are the only
    elements that have had their nodes or style changed, so only they
    need the first layout phase.
-   In `handle_click` and `keypres`, only the input element itself has had a change to
    node or style, so only it needs the first layout phase.

::: {.todo}
Stopped here. It's going pretty well, but I still need:
- Split the `layout` function into two pieces
- Talk them through computing heights for ancestors
- Talk them through debugging
:::

Let's split `relayout` into pieces to reflect the above. First,
let's move the construction of `self.page` and `self.layout` into
`parse`, since they only occur on initial load. Then let's create a
new `reflow` function that calls `style` and `layout1` on an element
of your choice. And finally, `relayout` will just contain the call to
`layout2` and the computation of the display list. Here's `parse` and
`relayout`:

``` {.python}
class Browser:
    def parse(self, body):
        # ...
        self.page = Page()
        self.layout = BlockLayout(self.page, self.nodes)
        self.reflow(self.nodes)
        self.relayout()

    def relayout(self):
        self.start("Layout2")
        self.layout.layout2(0)
        self.max_h = self.layout.h
        self.timer.start("Display List")
        self.display_list = self.layout.display_list()
        self.render()
```

The new `reflow` method is a little more complex. Here's what it looks
like after a simple reorganization:

``` {.python}
class Browser:
    def reflow(self, elt):
        self.timer.start("Style")
        style(self.nodes, self.rules)
        self.timer.start("Layout1")
        self.layout.layout1()
```

Note that while `reflow` takes an element as an argument, it ignores it,
and restyles and re-lays-out the whole page. That's clearly silly, so
let's fix that. First, the `style` call only needs to be passed
`elt`:

``` {.python}
style(elt, self.rules)
```

Second, instead of calling `layout1` on `self.layout`, we only want to
call it on the layout object corresponding to `elt`. The easiest way to
find that is with a big loop:[^10]

``` {.python}
def find_layout(layout, elt):
    if not isinstance(layout, LineLayout) and layout.node == elt:
        return layout
    for child in layout.children:
        out = find_layout(child, elt)
        if out: return out
```

This is definitely inefficient, because we could store the
element-layout correspondence on the node itself, but let's run with it
for the sake of simplicity. We can now change the
`self.layout.layout1()` line to:

``` {.python}
layout = find_layout(self.layout, elt)
if layout: layout.layout1()
```

This mostly works, but `find_layout` won't be happy on initial page
load because at that point some of the layout objects don't have
children yet. Let's add a line for that:[^11]

``` {.python}
def find_layout(layout, elt):
    if not hasattr(layout, "children"):
        return layout
    # ...
```

::: {.todo}
Relying on `hasattr` is extremely ugly. Perhaps we need dirty bits?
:::

The logic of returning any layout object without a `children` field is
that if some layout object does not have such a field, it definitely
hasn't had `layout1` called on it and therefore we should, which we do
by returning it from `find_layout`.

Finally, let's go back to place where we call `relayout` and add a call
to `reflow`. The only complicated case is `handle_hover`, where you need
to call `reflow` both on the old `hovered_elt` and on the new one. (You
only need to call `layout` once, though.)

With this tweak, you should see `layout1` taking up almost no time,
except on initial page load, and hovering should be much more
responsive. For me the timings now look like this:

``` {.python}
[  0.009246] Layout1
[  0.003590] Layout2
```

::: {.todo}
I should add rendering times.
:::

So now rendering takes up roughly 89% of the runtime when hovering, and
everything else takes up 32 milliseconds total. That's not one frame,
but it's not bad for a Python application!

Faster rendering
================

Let's put a bow on this lab by speeding up `render`. It's actually
super easy: we just need to avoid drawing stuff outside the browser
window; in the graphics world this is called *clipping*. Now,
sometimes stuff is half-inside and half-outside the browser window. We
still want to draw it! For that, we'll need to know where that stuff
starts and ends. I'm going to update the `DrawText` constructor to
compute that:

``` {.python}
self.y1 = y
self.y2 = y + 50
```

::: {.todo}
This misdirection is stupid. It should implement it the right way,
notice the slowdown, and improve it.
:::

Ok, wait, that's not the code you expected. Why 50? Why not use
`font.measure` and `font.metrics`? Because `font.measure` and
`font.metrics` are quite slow: they actually execute text layout, and
that takes a long time! So I'll be using only *y* position for
clipping, and I'll be using an overapproximation to `font.metrics`. The
50 is not a magic value; it just needs to be *bigger* than any actual
line height. If it's too big, we render a few too many `DrawText`
objects, but it won't change the resulting page.

Now both `DrawText` and `DrawRect` objects have top-left and
bottom-right coordinates and we can check those in `render`:

``` {.python}
for cmd in self.display_list:
    if cmd.y2 - self.scrolly < 0: continue
    if cmd.y2 - self.scrolly > 600: continue
    cmd.draw(self.scrolly - 60, self.canvas)
```

That takes rendering down from a quarter-second to a hundredth of a
second for me, and makes the hover animation fairly smooth. A hover
reflow now takes roughly 25 milliseconds, with the display list
computation 44% of that, rendering 39%, and `layout2` 13%. We could
continue optimizing (for example, tracking invalidation rectangles in
rendering), but I'm going to call this a success. We've made
interacting with our browser more than 30 times faster, and in the
process made the `:hover` selector perfectly usable.

Summary
=======

The more complex, two-phase layout algorithm in this chapter sped up
my toy browser by roughly 30×, to the point that it can now run simple
animations like hovering.

Exercises
=========

-   When `TextLayout.display_list` creates a `DrawText`, it already
    knows the width and height of the text to be laid out. Use that to
    compute `y2` and `x2` in `DrawText`. Add horizontal clipping to
    the rendering function.
-   Turns out, the `font.measure` function is quite slow! Change Add a
    cache for the size of each word in a given font. Measure the
    speed-up that results.
-   Extend the timer to measure the time to lay out each type of
    layout object. That is---compute how much time is spent laying out
    `BlockLayout` objects, how much in `InlineLayout`, and so on. What
    percentage of the `layout1` time is spent handling inline layouts?
    If you did the first and second exercises, measure the effect.
-   Add support for the `setAttribute` method in JavaScript. Note that
    this method can be used to change the `id`, `class`, or `style`
    attribute, which can change which styles apply to the affected
    element; make sure to handle that with reflow. Furthermore, you can
    use `setAttribute` to update the `href` attribute of a `<link>`
    element, which means you must download a new CSS file and recompute
    the set of CSS rules. Make sure to handle that edge case as well. If
    you change the `src` attribute of a `<script>` tag, oddly enough,
    the new JavaScript file is not downloaded or executed.
-   Add support for `setTimeout` command in JavaScript;
    `setTimeout(ms, f)` should run the function `f` in `ms`
    milliseconds. In Python, you can use the `Timer` class from the
    `threading` library, but be careful---the callback on the timer is
    called in a separate thread, so you need to make sure no other
    JavaScript is running when calling the timeout handler. Use
    `setTimeout` to implement a simple animation; for example, you might
    implement a "typewriter effect" where a paragraph is typed out
    letter-by-letter. Check that your browser handles the animation
    relatively smoothly.

[^7]: Because it calls `font.measure`, which has to do a slow and
    expensive text rendering to get the right size. Text is crazy.

[^10]: There is a subtlety in the code below. It's important to check
    the current node before recursing, because some nodes have two
    layout objects, in particular block layout elements that contain
    text and thus have both a `BlockLayout` and an `InlineLayout`. We
    want the parent, and doing the check before recursing guarantees us
    that.

[^11]: I recognize that in many languages, unlike in Python, you can't
    just add fields in some method without declaring them earlier on. I
    assume that in all of those cases you've been initializing the
    fields with dummy values, and then you'd check for that dummy value
    instead of using `hasattr`. Just make sure your dummy value for
    `children` isn't the empty list, since that is also a valid value.
    Better to use a null pointer or something like that, whatever your
    language provides.
