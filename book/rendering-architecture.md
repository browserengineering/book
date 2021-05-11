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

``` {.python expected=False}
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Button-1>", self.handle_click)
        self.window.bind("<Key>", self.keypress)
        self.window.bind("<Return>", self.press_enter)
```

What we want to do next is to run the rendering pipeline in a separte event.
We can do that by *scheduling a render to occur* instead of synchronously
computing it, via a call to a new method called `set_needs_display`:

``` {.python expected=False}
REFRESH_RATE = 16 # 16ms

class Browser:
    def __init__(self):
        self.display_scheduled = False

    def set_needs_display(self):
        if not self.display_scheduled:
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
    def load(self, url, body):
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
        # ....
        self.setup_js()

        scripts=[]
        thread = threading.Thread(target=self.load_scripts, args=(scripts,))
        thread.start()
        thread.join()
        # ...
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
            # ...
            self.js.evaljs("__runRAFHandlers()")

        self.run_rendering_pipeline()
        # ...
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

Optimize & Cache
================

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

The output looks like this for me (only listing the top methods by cumulative
time spent:

```
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
     65/1    0.000    0.000    6.633    6.633 {built-in method builtins.exec}
        1    0.000    0.000    6.633    6.633 lab13.py:1(<module>)
        1    0.000    0.000    6.512    6.512 __init__.py:601(mainloop)
        1    0.028    0.028    6.512    6.512 {method 'mainloop' of '_tkinter.tkapp' objects}
       51    0.000    0.000    6.484    0.127 __init__.py:1887(__call__)
       51    0.000    0.000    6.484    0.127 __init__.py:812(callit)
       51    0.001    0.000    6.482    0.127 lab13.py:1016(begin_main_frame)
     6290    6.344    0.001    6.344    0.001 {method 'call' of '_tkinter.tkapp' objects}
      102    0.000    0.000    6.311    0.062 lab13.py:1041(run_rendering_pipeline)
       52    0.001    0.000    6.311    0.121 lab13.py:1051(reflow)
   159/52    0.002    0.000    4.221    0.081 lab13.py:577(size)
       53    0.001    0.000    4.216    0.080 lab13.py:487(size)
     2472    0.006    0.000    3.307    0.001 font.py:152(measure)
   208/53    0.001    0.000    2.856    0.054 lab13.py:507(recurse)
      104    0.003    0.000    2.583    0.025 lab13.py:520(text)
      618    0.004    0.000    1.759    0.003 lab13.py:425(size)
     1236    0.008    0.000    1.678    0.001 font.py:159(metrics)
      104    0.001    0.000    1.632    0.016 lab13.py:535(flush)
      104    0.000    0.000    1.631    0.016 lab13.py:373(size)
      104    0.002    0.000    1.631    0.016 lab13.py:377(compute_height)
       52    0.004    0.000    1.271    0.024 lab13.py:1074(draw)
```

As you can see, there is a bunch of time spent, seemingly about equally spread
between layout and painting. The next thing to do is to examine each method
mentioned above and see if you can find anything that might be optimized out. As
it turns out, there is one that is pretty easy to fix, which is the `font.py`
lines that do font measurement. It's apparently the case that tkinter fonts
don't have a good internal cache, and loading fonts is
expensive[^why-fonts-slow]. But right now we don't take advantage of the fact
that everything on the page has the same font, and repeat that font for every
object! Let's fix that:

[^why-fonts-slow]: fonts are surprisingly large, especially for scripts like
Chinese that have a lot of diffferent, complex characters. For this reason they
are generally stored on disk and only loaded into memory on-demand. Hence it is
slow to load them. Optimizing font loading (and the cost to shape them and lay
them out, since many web pages have a *lot* of text) turns out to be one of the
most important factors in a fast rendering engine.


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

This turns out to make a dramatic difference, not just in text measurement, but
in layout *and* paint!

```
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
     65/1    0.000    0.000    1.143    1.143 {built-in method builtins.exec}
        1    0.000    0.000    1.143    1.143 lab13.py:1(<module>)
        1    0.000    0.000    1.007    1.007 __init__.py:601(mainloop)
        1    0.435    0.435    1.007    1.007 {method 'mainloop' of '_tkinter.tkapp' objects}
       51    0.000    0.000    0.572    0.011 __init__.py:1887(__call__)
       51    0.001    0.000    0.572    0.011 __init__.py:812(callit)
       51    0.002    0.000    0.570    0.011 lab13.py:1016(begin_main_frame)
     5108    0.449    0.000    0.450    0.000 {method 'call' of '_tkinter.tkapp' objects}
      102    0.000    0.000    0.441    0.004 lab13.py:1041(run_rendering_pipeline)
       52    0.001    0.000    0.441    0.008 lab13.py:1051(reflow)
       52    0.003    0.000    0.290    0.006 lab13.py:1074(draw)
     1133    0.005    0.000    0.270    0.000 __init__.py:2768(_create)
      925    0.001    0.000    0.258    0.000 __init__.py:2808(create_text)
      873    0.002    0.000    0.152    0.000 lab13.py:676(draw)
       56    0.001    0.000    0.150    0.003 evaljs.py:39(evaljs)
       56    0.018    0.000    0.145    0.003 {built-in method dukpy._dukpy.eval_string}
   159/52    0.003    0.000    0.127    0.002 lab13.py:577(size)
      308    0.003    0.000    0.127    0.000 evaljs.py:72(_call_python)
       53    0.000    0.000    0.121    0.002 lab13.py:487(size)
       51    0.001    0.000    0.112    0.002 lab13.py:962(js_innerHTML)
   208/53    0.000    0.000    0.091    0.002 lab13.py:507(recurse)
        1    0.000    0.000    0.086    0.086 lab13.py:641(size)
      104    0.002    0.000    0.086    0.001 lab13.py:520(text)
     2472    0.003    0.000    0.085    0.000 font.py:152(measure)
```

As you can see, everything became a lot cheaper. This is because font
measurement overhead was making both layout and paint slower for every single
object. The new timings show that we're easily meeting the 16ms frame budget:


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

Great! Technically speaking though, this font optimization is not a pure
micro-optimization, but a caching strategy, so let's now discuss that.

Various kinds of caches are the single most important class of optimizations for
browsers. Real browsers have caches all over the place---network resource
caches and font caches are two. (Well, we haven't actually implemented a network
cache yet---maybe in a future chapter?) The rendering pipeline is no different:
there are caches of various kinds throughout style, layout, and paint. In fact,
we already saw an example of this in [chapter 10](reflow.md).

Notice that the layout tree itself is a cache, as is the display list. We can
come up with all sorts of ideas to minimize changes to the tree or the list
when things change.

Let's keep optimizing. The top item in the CPU profile below
`run_rendering_pipeline` is `reflow`. However, this is a little unclear, since
reflow currently includes style, layout, paint and draw. Let's at least separate
paint and draw:

``` {.python}
    def run_rendering_pipeline(self):
        for reflow_root in self.reflow_roots:
            self.reflow(reflow_root)
        self.reflow_roots = []
        self.paint()
        # ...
```

With these changes, the profile now shows that `draw` is actually a big
component of the remaining cost, with these pieces. The following data
is aggregated over 50 frames of animation:

```
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
       52    0.005    0.000    0.391    0.008 lab13.py:1075(draw)
      873    0.003    0.000    0.201    0.000 lab13.py:676(draw)
```

Line 676 is `DrawText.draw`. Half the total time drawing is in drawing text
I told you that fonts and text rendering are big time hogs and sources of 
optimization!) Unfortunately, in this case there is nothing further we can do,
without finding out where to optmiize tkinter further. Also note that the total
time spent drawing text is only 0.201s in this case, and therefore 4ms per
frame. If the amount of text was much larger, this would become a big problem,
as we'd start missing the 16ms frame budget again.

Or is there something we can do? Let's go back to the list of ways to make
the event loop faster. We alreedy showed that Optimize and Cache are two ways.
What about Parallelize? Can't we run these draw commands on a different thread?
Well, of course we can.

The Compositor thread
=====================

This second thread that runs drawing is often called the Compositor thread
It's so named because in a real browser it'll end up doing a lot more than
drawing to a canvas, but let's forget that for now and focus on drawing.

To get this compositor thread working, we'll have to find a way to run tkinter
on a second thread, and communicate between the threads in a way that allows
them to do things in parallel. The first thing you should know is that tkinter
is *not* thread-safe, so it cannot magically parallelize for free. Instead we'll
have to carefully avoid using tkinter at all on the main thread, and move all
use of it to the compositor thread.

The approach we'll take is to take the thread we already have and call it the
compositor thread, and add a new thread that is the "main thread". This thread
will have these kinds of tasks:

* JavaScript

* Run a browser-internal tasks like executing a page load

* The rendering pipeline (including `requestAnimationFrame`)

 The compositor thread (the one with tkinter in it) will be in charge of:

* Listening to mouse and keyboard events

* Scheduling a rendering pipeline frame every 16ms

* Drawing to the screen after the rendering pipeline is done

To do this we'll have to expand greatly on the implementation of an event loop,
because now we'lll need to manage this event loop ourselves rather than using
tkinter for most of it.

Let's start the implementation by introducing a class that encapsulates the main
thread and the event loop, called `MainThreadRunner`. The two threads will
communicate by writing to and reading from some shared data structures. This
of course introduces the risk of a race condition between the threads,
so we'll add a `threading.Lock` object for each thread. Any code that touches
the shared data structures for a thread will have to acquire the lock before
doing so.

Let's introduce a new class called `MainThreadRunner` that encapsulates the
maind thread its event loop, and a few queues for different types of event loop
tasks:

```
class MainThreadRunner:
    def __init__(self, browser):
        self.lock = threading.Lock()
        self.browser = browser
        self.needs_begin_main_frame = False
        self.main_thread = threading.Thread(target=self.run, args=())
        self.script_tasks = []
        self.browser_tasks = []

    def start(self):
        self.main_thread.start()        
```

It will have some methods to set the variables, such as:

```
    def schedule_main_frame(self):
        self.lock.acquire(blocking=True)
        self.needs_begin_main_frame = True
        self.lock.release()

    def schedule_script_task(self, script):
        self.lock.acquire(blocking=True)
        self.script_tasks.append(script)
        self.lock.release()
```

Its main functionality is in the `run` method. It implements a simple event
loop strategy that runs the rendering pipeline if needed, and also one browser
method and one script task, if there are any on those queues. It then sleeps
for 1ms and checks again.

```
     def run(self):
        while True:
            self.lock.acquire(blocking=True)
            needs_begin_main_frame = self.needs_begin_main_frame
            self.lock.release()
            if needs_begin_main_frame:
                browser.begin_main_frame()
                self.browser.commit()

            browser_method = None
            self.lock.acquire(blocking=True)
            if len(self.browser_tasks) > 0:
                browser_method = self.browser_tasks.pop(0)
            self.lock.release()
            if browser_method:
                browser_method()

            script = None
            self.lock.acquire(blocking=True)
            if len(self.script_tasks) > 0:
                script = self.script_tasks.pop(0)
            self.lock.release()

            if script:
                try:
                    retval = self.browser.js.evaljs(script)
                except dukpy.JSRuntimeError as e:
                    print("Script", script, "crashed", e)

            time.sleep(0.01)
```

The `begin_main_frame` method on `Browser` will run on the main thread. Since
`draw` is supposed to happen on the compositor thread. This is where the
`commit` method on the `Browser ` class that the code snippet above calls comes
in to play:

``` {.python}
    def commit(self):
        self.compositor_lock.acquire(blocking=True)
        self.needs_draw = True
        self.draw_display_list = self.display_list.copy()
        self.compositor_lock.release()
```


Here are the results:
    Average total compositor thread time (Draw and Draw Chrome): 4.8ms
    Average total main thread time: 4.4ms

This means that we've been able to save about 4.8ms of main-thread time, in
which we can do other work, such as more JavaScript tasks, while in parallel
the draw operations happen.
