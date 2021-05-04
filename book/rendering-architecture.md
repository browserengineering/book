---
title: Browser Rendering Architecture Concepts
chapter: 13
cur: rendering-architecture
prev: visual-effects
next: skipped
...

The Rendering Event Loop and Pipeline
=====================================

In previous chapters, you learned about how to load a web page with HTTP, parse
HTML into an HTML tree, compute styles on that tree, construct the layout tree,
layout its contents, and paint the result to the screen. These steps are the
basics of the [*rendering
pipeline*](https://en.wikipedia.org/wiki/Graphics_pipeline) of the browser. 

Chapter 2 also introduced the notion of an [event loop](graphics.md#eventloop),
which is a how a browser iteratively finds out about inputs---or other changes
of state---that affect
rendering, then re-runs the rendering pipeline, leading to an update on the
screen. In terms of our new terminology, the code is:

``` {.python expected=False}
while True:
    for evt in pending_events():
        handle_event(evt)
    run_rendering_pipeline()
```

Let's make the same changes to your browser, beginning with renaming
the `render` method to `draw`, since it is only doing the part about drawing
the display list to the screen:

``` {.python}
def draw(self):
    # ...
````

Likewise, let's rename `layout` to `run_rendering_pipeline`:


``` {.python}
def run_rendering_pipeline(self):
    # ...
    self.reflow(reflow_root)
    # ...
```

As a reminder, if you're using `tkinter`, the call to `tkinter.mainloop()`
is what your browser uses to implement the above while loop.

The cadence of rendering
========================

Now that same chapter *also* says that there is a [frame
budget](graphics.md#framebudget), which is the amount of time allocated to
re-draw the screen after an input update. The frame budget is typically about
16ms, in order to draw at 60Hz (`60 * 16.66ms ~= 1s`). This means that each
iteration through the `while` loop should ideally complete in at most 16ms.

It also means that the browser should not run the while loop faster than that
speed, even if the CPU is up to it, because there is no point---the screen can't
keep up anyway. For this reason, `16ms` is not just a frame budget but also a
desired rendering *cadence*.

Our next goal is to make the browser match this cadence.

(TODO: rename the pipeline stages in earlier chapters to match the nomenclature below.)

Currently, your browser runs the rendering pipeline (style, layout, paint, and
draw) immediately after each possible event that might cause a change to what is
shown on the screen. These events are currently `handle_click`, `keypress`, `load`,
`js_innerHTML` and `scrolldown`. `tkinter` puts a task on the event loop each
time one of the above events happen; that is effect of binding *event handler*
methods to those events, via this code:

``` {.python}
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Button-1>", self.handle_click)
        self.window.bind("<Key>", self.keypress)
        self.window.bind("<Return>", self.pressenter)
```

What we want to do next is to run the rendering pipeline in a separte event.
We can do that by *scheduling a render to occur* instead of synchronously
computing it, via a call to a new method called `set_needs_display`:

``` {.python}
REFRESH_RATE = 16 # 16ms

class Browser:
    def __init__(self):
        self.needs_display = False

    def set_needs_display(self):
        if not self.needs_display:
            self.needs_display = True
            self.canvas.after(REFRESH_RATE,
                              self.begin_main_frame)
```

For `handle_click`, this means replacing a call to `self.reflow(self.focus)`
with `self.set_needs_display()`. But that's not all---if we just called
`set_needs_display()`, the fact that it was `self.focus` that needed reflow would
be lost. To solve that we'll record the need for a reflow in a new variable
`reflow_roots`, which records which layout objects need reflow, and insert
into it when needed:

``` {.python expected=False}
class Browser:
    # ...
    self.reflow_roots = []

    def set_needs_reflow(self, layout_object):
        self.reflow_roots.append(layout_object)
        self.set_needs_display()

    def handle_click(self, e):
        # ...
        self.set_needs_reflow(self.focus)
```

Scripts in the event loop
=========================

In addition to event handlers, it's also of course possible for script to run in
the event loop, or schedule itself to be run. In general, the event loop can any
of a wide variety of *tasks*, only some of which respond to input events. As we
saw in [chapter 9](scripts.md), the first way in which scripts can be run is
that when a `<script>` tag is inserted into the DOM, and the script load. The
browser currently synchronously fetches the script and then evaluates it, like
so:

``` {.python expected=False}
    for script in find_scripts(self.nodes, []):
        header, body = request(relative_url(
            script, self.history[-1]), headers=req_headers)
        self.js.evaljs(body)
```

Real browsers of course don't synchronously fetch the script, because otherwise
the whole browser would lock up in the meantime---and who knows how long it will
take to fetch it!

One simple way to fix this is to perform the fetches on another CPU thread
(and this is how real browsers typically do it---network fetches happen in a
different set of threads or processes):

``` {.python}
    def load(self, url, body=None):
        # ...

        self.run_scripts()
        self.set_needs_layout_tree_rebuild()

    def load_scripts(self, scripts):
        req_headers = { "Cookie": self.cookie_string() }
        for script in find_scripts(self.nodes, []):
            header, body = request(
                relative_url(script, self.history[-1]), headers=req_headers)
            scripts.append([header, body])

    def run_scripts(self):
        self.timer.start("Running JS")
        self.setup_js()

        scripts=[]
        thread = threading.Thread(target=self.load_scripts, args=(scripts,))
        thread.start()
        thread.join()
        for [header, body] in scripts:
            try:
                print("Script returned: ", self.js.evaljs(body))
            except dukpy.JSRuntimeError as e:
                print("Script", body, "crashed", e)
```

Note that the *loading* happens on a background thread, but not the *evaluation*
of the script. That's because JavaScript is not multi-threaded, and all scripts
have to be evaluated on the main thread. (I'll get into the implications of this
later in the chapter.)

But that's not all! In addition to runing straight through, scripts can also
schedule more events to be put on the event loop and run later. There are
multiple JavaScript APIs in browsers to do this, but for now let's focus on the
one most related to rendering: `requestAnimationFrame`. This API is used like
this:

``` {.javascript}
/* This is JavaScript! */
function callback() {
    console.log("I was called!");
}
requestAnimationFrame(callback);
```

This code will do two things: request an "animation frame", and call `callback`
just before that happens. An animation frame is the same thing as "run the
rendering pipeline". The implenmentation of this JavaScript API, then is as
follows:

``` {.python}
    def js_requestAnimationFrame(self):
        self.needs_raf_callbacks = True
        self.set_needs_display()
```

We'll also need to modify `run_rendering_pipeline` to first execute the
JavaScript callbacks. The full definition is:

``` {.python}
    def setup_js(self):
        # ...
        self.js.export_function(
            "requestAnimationFrame",
            self.js_requestAnimationFrame)

    def js_requestAnimationFrame(self):
        self.needs_raf_callbacks = True
        self.set_needs_display()

    def begin_main_frame(self):
        self.needs_display = False

        if (self.needs_raf_callbacks):
            self.needs_raf_callbacks = False
            self.timer.start("runRAFHandlers")
            self.js.evaljs("__runRAFHandlers()")

        self.run_rendering_pipeline()
        self.timer.start("IdleTasks")
        self.canvas.update_idletasks()

    def run_rendering_pipeline(self):
        if self.needs_layout_tree_rebuild:
            self.document = DocumentLayout(self.nodes)
            self.reflow_roots = [self.document]
        self.needs_layout_tree_rebuild = False

        for reflow_root in self.reflow_roots:
            self.reflow(reflow_root)
        self.reflow_roots = []
```

And in the JavaScript runtime we'll need:

``` {.javascript}
function Date() {}
Date.now = function() {
    return call_python("now");
}

RAF_LISTENERS = [];

function requestAnimationFrame(fn) {
    RAF_LISTENERS.push(fn);
    call_python("requestAnimationFrame");
}

function __runRAFHandlers() {
    var handlers_copy = [];
    for (var i = 0; i < RAF_LISTENERS.length; i++) {
        handlers_copy.push(RAF_LISTENERS[i]);
    }
    RAF_LISTENERS = [];
    for (var i = 0; i < handlers_copy.length; i++) {
        handlers_copy[i]();
    }
}

```

Let's walk through what it does:

1. Reset the `needs_display` and `needs_raf_callbacks` variables to false.

2. Call the JavaScript callbacks.

3. Run the rendering pipeline (style, layout, paint, draw)

Let's look a bit more closely at steps 1 and 2. Would it work to run step 1
*after* step 2?[^copy-raf] The answer is no, but the reason is subtle: it's because
the JavaScript callback code could *once again* call `requestAnimationFrame`.
If this happens during such a callback, the spec says that a *second* frame
should be scheduled (and 16ms further in the future, naturally).

[^copy-raf]: Likewise the runtime JavaScript needs to be careful to copy the
`RAF_LISTENERS` array to a temporary variable and clear out RAF_LISTENERS, so
that it can be re-filled by new calls to `requestAnimationFrame` later.

This may seem like a corner case, but it's actually very important, as it's the
way that JavaScript can cause a 60Hz animation loop to happen. Let's try it out
with a script that counts from 1 to 100, one frame at a time:

```
var count = 0;
var start_time = Date.now();
var cur_frame_time = start_time

function callback() {
    var output = document.querySelectorAll("#output")[0];
    var since_last_frame = Date.now() - cur_frame_time;
    var total_elapsed = Date.now() - start_time;
    output.innerHTML = "count: " + (count++) + "<br>" +
        " time elapsed since last frame: " + 
        since_last_frame + "ms" +
        " total time elapsed: " + total_elapsed + "ms";
    if (count <= 100)
        requestAnimationFrame(callback);
    cur_frame_time = Date.now()
}
requestAnimationFrame(callback);
```
This script will cause 101 JavaScript tasks to be put on event loop. First,
there is a task that executes immediately after loading the script from the
network. Then there is a sequence of frames generated (100 of them), each
ideally separated by about a 16ms gap.

When I ran the script script in this book's browser, I found that there were
about *140ms* between each frame. Looks like we have some work to do to get
to 16ms!

Speeding up the event loop
==========================

Analyzing timings shows that, in this case, the slowdown is almost entirely in
the rendering pipeline:

    [  0.000810] runRAFHandlers
    [  0.000057] Style
    [  0.094592] Layout (phase 1A)
    [  0.000010] Layout (phase 1B)
    [  0.000050] Layout (phase 2)
    [  0.019368] Paint
    [  0.029137] Draw
    [  0.002585] Draw Chrome
    [  0.004198] IdleTasks
    Total: 0.150807s (~150ms)

And the long pole in the rendering pipeline in this case is layout phase 1A,
followed by Paint and Drawing, which in turn is caused by setting the innerHTML
of the `#output` element. The new runRAFHandlers timing shows less than 1ms
spent running JavaScript; commenting out that line of JavaScript cases the
frames to be at exactly the right 16ms cadence.

However, in another scenario it could also easily occur that the slowest part
ends up being Style, or Paint, or IdleTasks. As one example of how Style
could end up being the slow part, the style sheet could have a huge number of
complex rules in it, many of which may not actually affect the newly-changed
elements. If we're not very careful in the implementation (or even if we are!)
it could still be slow.

In addition, it could be that runRAFHandlers is the slowest part. For example,
suppose we inserted the following busyloop into the callback, like so:

``` {.javascript}
function callback() {
    var now = Date.now();
    while (Date.now() - date < 100) {}
    # ...
}
```

The performance timings now look like this:

    [  0.100409] runRAFHandlers
    [  0.000095] Style
    [  0.157739] Layout (phase 1A)
    [  0.000012] Layout (phase 1B)
    [  0.000052] Layout (phase 2)
    [  0.024089] Paint
    [  0.033669] Draw
    [  0.002961] Draw Chrome
    [  0.010219] IdleTasks

As you can see, runRAFHandlers now takes 100ms to finish, so it's the slowest
part of the loop. This demonstrates, of course, that no matter how fast or
cleverly we optimize the browser, it's always possible for JavaScript to
make it slow.

There are a few general techniques to optimize the browser when encountering
these situations:

1. Optimize: find ways to do less work to achieve the same goal. For example, a
faster algorithm, fewer memory allocations, fewer function calls and branches,
or skipping work that is not necessary. An example is the optimizations to
[skip painting](graphics.md#faster-rendering) for off-screen elements.

2. Cache: carefully remember what the browser already knows from the previous
frame, and re-compute only what is absolutely necessary for the next one.
An example is the partial layout optimizations in [chapter 10](reflow.md)

3. Parallelize: run tasks on an different thread or process. An example
is the change we made earlier in this chapter to run network loading
asynchronously in a background thread.

4. Schedule: when possible, delay tasks that can be done later, or break up
work into smaller chunks and do them in separate frames. We haven't encountered
an optimization of this kind yet.

Let's consider each class of optimization in turn

Optimize
========

What could we do to make Paint, for example, faster? There are a few
micro-optimizations we could try, such as pre-allocationg `self.display_list`
rather than appending to it each time. when I tried this, on my machine it
showed no benefit. That may or may not be due to the interpred nature of Python
vs compiled languages such as C++.

Ok that didn't work.  Micro-optimization can be hard to guess solutions for,
especially for interpreted languages which have speed characteristics that
are hard to predict without a lot of experience. Instead, let's take the next
step beyond using per-rendering pipeline stage timing, and do a CPU profile of
the program. We can do that by using the cPython profiler that comes with
python, via a command like like:

`python -m cPython <my-program.py>`

If you do this, you'll likely find that most of the time is spent in library
code such as tkinter, and not in my-program.py. To actually "zero in" on
potential optimizations, you'll need to edit the JavaaScript to create much
larger HTML that exercises the style and layout machiner harder. I did this,
but was unable to find anything to significantly unoptimized. How about you?

Cache
=====

Within Paint, there is an opportunity to cache in the same way that we did for
Layout in chapter 10. Right now, regardless of how much re-layout there was,
we re-paint the entire display list. This could be optmiized in a few ways,
such as:

* Caching the previous display list and only updating the parts that
changed, by walking only part of the layout tree

* Caching each entry in the display list within the corresponding layout object.
For example, via code like this:

``` {.python expected=False}
class TextLayout:
    def __init__(self, node, word):
        # ...
        self.display_item = None

    def size(self):
        # Sizing changed, so we need to re-creae the display item
        self.display_item = None
            # ...

    def paint(self, to):
        if not self.display_item:
            color = self.node.style["color"]
            self.display_item = DrawText(self.x, self.y, self.word, self.font, color)
        to.append(self.display_item)
```

I tried this, and was able to observe perhaps a 5% increase in speed. One
reason it was not higher may be that each frame of animation in this testcase
includes about 12 *new* TextLayout objects (the ones that are part of the
`innerHTML` contents), as compared with 5 other ones. This optimization of
course can only apply to a TextLayout object that is preserved across frames.

Let's now consider Layout. One thing that jumped out at me is that there are
a number of TextLayout objects created in each frame of the animation, and
all of them have the same font. Unless cached well, fonts are actually very
expensive to create and load. The reason for this is usually that font files are
sometimes very large, and as a result are not loaded into memory unless
necessary. Any unnecessary duplication of loading fonts from disk will be
a big source of slowdowns. On a guess that tkinter fonts don't have good
internal caching, I tried the following optimization:

``` {.python}
FONT_CACHE = {}

def GetFont(size, weight, style):
    key = (size, weight, style)
    value = FONT_CACHE.get(key)
    if value: return value
    value = tkinter.font.Font(size=size, weight=weight, slant=style)
    FONT_CACHE[key] = value
    return value

class TextLayout:
    # ...

    def size(self):
        # ...
        self.font = GetFont(size, weight, style) 
```

This will create only one font object for each tuple of `(size, weight, style)`.
The timing results after this optimization are:

    [  0.000753] runRAFHandlers
    [  0.000091] Style
    [  0.000925] Layout (phase 1A)
    [  0.000012] Layout (phase 1B)
    [  0.000055] Layout (phase 2)
    [  0.000194] Paint
    [  0.004903] Draw
    [  0.003691] Draw Chrome
    [  0.001578] IdleTasks
    Total: 0.012s = 12ms

Success! This optimization made a huge difference, and the rendering pipeline
now fits within our 16ms frame budget. Note that not only was it a lot cheaper
to only create one font object, but this made Paint an order of magnitude faster
as well. This is because DrawText calls `font.measure("linespace")`, and
that is expensive to compute from scratch, but is (presumably) cached within
a tkinter Font object. So we saved the time of re-compuoting this measurement
for each DrawText.