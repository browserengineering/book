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
                print("Script", script, "crashed", e)
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
            "requestAnimationFrame", self.js_requestAnimationFrame)

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

Optimizing the event loop
=========================

Analyzing timings shows that, in this case, the slowdown is almost entirely in
the rendering pipeline:

    [  0.000810] runRAFHandlers
    [  0.000057] Style
    [  0.094592] Layout (phase 1A)
    [  0.000010] Layout (phase 1B)
    [  0.000050] Layout (phase 2)
    [  0.019368] Display list
    [  0.029137] Drawing
    [  0.002585] Chrome
    [  0.004198] IdleTasks
    Total: 0.150807s (~150ms)

And the long pole in the rendering pipeline in this case is layout, paint and
drawing, which in turn is caused by setting the innerHTML of the `#output`
element. The new runRAFHandlers timing shows less than 1ms spent running
JavaScript; commenting out that line of JavaScript cases the frames to be at
exactly the right 16ms cadence.

TODO: rest of chapter.
