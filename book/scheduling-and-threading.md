---
title: Scheduling and Threading
chapter: 12
prev: visual-effects
next: skipped
...

Our browser now knows how to load a web page with HTTP and parse it into an
HTML tree & style sheets. It can also *render* the page, by constructing the
layout tree, computing styles on it, laying out its contents, painting it into
a dispaly list, rastering the result into surfaces, and drawing those surfaces
to the screen. These rendering steps make up a basic
[*rendering pipeline*](https://en.wikipedia.org/wiki/Graphics_pipeline) for the
browser.[^rendering-pipeline]

[^rendering-pipeline]: Our browse's current rendering pipeline has 5 steps:
style, layout, paint, raster and draw.

But of course, there is more to web pages than just running the rendering
pipeline. There is keyboard/mouse/touch input, scrolling, interacting with
browser chrome, submitting forms, executing scripts, loading things off the
network, and so on. All of these *tasks* currently run on the main *event
loop*; since it has only one such loop, the browser is generally
single-threaded.

In this chapter we'll see how to reason more deeply about the main event loop,
generalizing to multiple event loops, types of tasks, and task queues. We'll
refactor the rendering pipeline into its own special kind of task, and use this
to add a second *browser thread*, separate from the thread for web page contents.

The browser thread will process input, scroll, interact with the browser chrome,
raster display lists, and draw---basically, all the things the browser can do
without interacting with the web page. This thread is a central performance
feature of modern browsers.

Task queues
===========

When the browser is free to do work, it finds the next pending *task* and runs
it, and repeats. A sequence of related tasks is a *task queue*, and browsers
have multiple tasks queues.

One or more task queues can be grouped together into a single, sequential
*thread* of execution. Each thread has an *event loop* associated with
it.[^event-loop] The job of the event loop is to schedule tasks
 according to the priorities of the browser---to make sure it's responsive to
 the user, uses hardware efficiently, loads pages fast, and so on. You've
 already seen many examples of tasks---handling clicks, loading, and scrolling.

[cores]: https://en.wikipedia.org/wiki/Multi-core_processor

[^event-loop]: Event loops were also briefly touched on in
[chapter 2](graphics.md#eventloop), and we wrote our own event loop in
[chapter 11](visual-effects.md#sdl-creates-the-window) (before that, we used
`tkinter.mainloop`).

Let's implement a `Task` and a `TaskQueue` class. Then we can move all of the
event loop tasks into task queues later in the chapter.

A `Task` encapsulates some code to run in the form of a function, plus arguments
to that function.[^task-notes] A `TaskQueue` is simply a
first-in-first-out list of `Task`s.

[^task-notes]: In `Task`, we're using the varargs syntax for Python, allowing
any number of arguments to be passed to the task. We're also using Python's
`__call__` builtin method. It is called when an object is called as if it's a
function. The Python code `Task()()` will constructs a `Task` and then "call"
(run) it

``` {.python}
class Task:
    def __init__(self, task_code, *args):
        self.task_code = task_code
        self.args = args
        self.__name__ = "task"

    def __call__(self):
        self.task_code(*self.args)
        # Prevent it accidentally running twice.
        self.task_code = None
        self.args = None
```

``` {.python expected=False}

class TaskQueue:
    def __init__(self):
        self.tasks = []

    def add_task(self, task_code):
        self.tasks.append(task_code)

    def has_tasks(self):
        return len(self.tasks) > 0

    def get_next_task(self):
        return self.tasks.pop(0)

    def clear(self):
        self.tasks = []
```

::: {.further}
Event loops often map 1:1 to CPU threads within a single CPU process, but
this is not required. For example, multiple event loops could be placed together
on a single CPU thread with yet another scheduler on top of them that
round-robins between them. It's useful to distinguish between conceptual
events, event queues and dependencies between them, and their implementation in
a computer architecture. This way, the browser implementer (you!) has maximum
ability to use more or less hardware parallelism as appropriate to the
situation---some devices have more [CPU cores][cores] than others, or are more
sensitive to battery power usage.
:::

Rendering pipeline tasks
========================

The most important task in a browser is the rendering pipeline---but not just
for the obvious reason that it's impossible to see web pages that aren't
rendered. Most of the time spent doing work in a browser is in *rendering
interactions* with the browser, such as loading, scrolling, clicking and typing.
. All of these interactions require rendering. If you want to make those
interactions faster and smoother, the very first think you have to do is
carefully optimize the rendering pieline.

The main event loop of a web page in a browser is called the *rendering event
loop*. An idealized rendering event loop looks like this:


``` {.python expected=False}
# This is the rendering event loop we want.
while True:
    while there_is_enough_time():
        run_a_task_from_a_task_queue()
    run_rendering_pipeline()
```
This is "ideal" because separating rendering into its own task will allow us
to optimize it and spread it across multiple threads.^[Here
`run_rendering_pipeline` is made to look like it's all on the main event loop,
but all the parts of it that are after layout are invisible to web page
authors, so we'll be able to optimize them later on into a second event loop
on another thread.]

This loop implies that the rendering pipeline is its own task. But right now,
the rendering pipeline in our browser is not a task at all---it's hidden in
various subroutines of other tasks in the event loop. 

``` {.python expected=False}
# This is what our browser currently does.
while True:
    run_a_task_from_a_task_queue() # Might do some rendering
```

We'll need to fix that, but first let's figure out how long "enough time" in the
above loop should be. This was discussed in Chapter 2, which introduced the
[animation frame budget](graphics.md#framebudget), The animation frame budget
is the amount of time allocated to re-draw the screen after an something has
changed. It's typically about 16ms, in order to draw at 60Hz (60 * 16.66ms ~
1s), and matches the refresh rate of most displays. This means that each
iteration through the `while` loop should ideally complete in at most 16ms.

It also means that the browser should not run the while loop faster than that
speed, even if the CPU is up to it, because there is no point---the screen
can't keep up anyway. For this reason, `16ms` is not just an animation frame
budget but also a desired rendering *cadence*. If an iteration of the `while`
loop finishes faster than `16ms`, the browser should wait a bit before
the next iteration.

Therefore, let's use 16ms as the definition of "enough time":

``` {.python}
REFRESH_RATE_SEC = 0.016 # 16ms
```

Asynchronous rendering
======================

In order to separate rendering from other tasks and make it into a proper
pipeline, we'll need to make it asynchronous. Instead of updating rendering
right away, we'll set *dirty bits* indicating that a particular part of the
pipeline needs updating. Then when the pipeline is run, we'll run the parts
indicated by the dirty bits. We'll also need some way of
*scheduling* the rendering pipeline to be updated at a given time in the
future.

Let's start with how to schedule the update, via a new `set_timeout` function.
This function will run a callback at a specified time in the future.
You can do that by starting a new [Python thread][python-thread] via the
`threading.Timer` class, which takes two parameters: a time delta from now, and
a function to call when that time expires.

[python-thread]: https://docs.python.org/3/library/threading.html

``` {.python}
def set_timeout(func, sec):     
    t = threading.Timer(sec, func)
    t.start()
```

Next, add a dirty bit `needs_pipeline_update` (plus `display_scheduled` to
avoid double-running `set_timeout` unnecessarily) to `Tab`, which means
"rendering needs to happen, and has been scheduled, but hasn't happened yet".
 
Also, rename `render` to `run_rendering_pipeline`, and add a new
`run_animation_frame` method that runs the pipeline and calls the other
rendering pipeline stages on `Browser` via a new `raster_and_draw` method
(which we'll implement shortly).

``` {.python expected=False}
class Tab:
    def __init__(self, browser):
        self.browser = browser
        self.display_scheduled = False
        self.needs_pipeline_update = False

    def set_needs_pipeline_update(self):
        self.needs_pipeline_update = True
        set_needs_animation_frame()

    def set_needs_animation_frame(self):
        def callback():
            self.display_scheduled = False
            self.run_rendering_pipeline()

        if not self.display_scheduled:
            set_timeout(callback, REFRESH_RATE_SEC)
            self.display_scheduled = True

    def run_animation_frame(self):
        self.run_rendering_pipeline()
        browser.raster_and_draw()

    def run_rendering_pipeline(self):
        if self.needs_pipeline_update:
            style(self.nodes, sorted(self.rules,
                key=cascade_priority))
            self.document = DocumentLayout(self.nodes)
            self.document.layout()
            self.display_list = []
            self.document.paint(self.display_list)
            self.needs_pipeline_update = False
```

Now replace all cases where parts of the rendering pipeline were called with
`set_needs_pipeline_update`, for example `load`:

``` {.python}
class Tab:
    def load(self, url, body=None):
        # ...
        self.set_needs_pipeline_update()
```

Now add dirty bits to `Browser` to control what happens in  `raster_and_draw`.
This will get us back the same performance we had at the end of chapter 11,
where the browser only ran raster and draw when needed.

``` {.python} 
class Browser:
    def __init__(self):
        # ...
        self.needs_tab_raster = False
        self.needs_chrome_raster = True
        self.needs_draw = True

    def set_needs_tab_raster(self):
        self.needs_tab_raster = True
        self.needs_draw = True

    def set_needs_chrome_raster(self):
        self.needs_chrome_raster = True
        self.needs_draw = True

    def set_needs_draw(self):
        self.needs_draw = True

    def raster_and_draw(self):
        if self.needs_chrome_raster:
            self.raster_chrome()
        if self.needs_tab_raster:
            self.raster_tab()
        if self.needs_draw:
            self.draw()
        self.needs_tab_raster = False
        self.needs_chrome_raster = False
        self.needs_draw = False
```

Oh, and we'll need to schedule an animation frame whenever any of those dirty
bits are set. This is easiest to add in `set_needs_draw`. Note that scheduling
an animation frame does *not* mean that `run_rendering_pipeline` does all its
expensive work, just that the animation frame task is scheduled 16ms in the
future. Only `set_needs_pipeline_update` will cause that expensive work.


``` {.python expected=False}
class Browser:
    def set_needs_draw(self):
        # ...
        self.tabs[self.active_tab].set_needs_animation_frame()
```

And in each case where raster or draw was called previously, set the dirty
bits. Here's the change to `handle_click`:

``` {.python expected=False}
class Browser:
    def handle_click(self, e):
        if e.y < CHROME_PX:
            # ...
            self.set_needs_chrome_raster()
            self.tabs[self.active_tab].set_needs_animation_frame()
```

and `handle_down`:

``` {.python}
class Browser:
    def handle_down(self):
        # ...
        self.set_needs_draw()
```

Scripts in the event loop
=========================

In addition to event handlers and rendering, JavaScript also runs on the
rendering event loop. As we saw in [chapter 9](scripts.md), when the parser
encounters a `<script` tag, , the script subsequently loads and then runs. We
can easily wrap all this in a `Task`, with a zero-second timeout, like so:

``` {.python expected=False}
class Tab:
    for script in find_scripts(self.nodes, []):
        # ...
        header, body = request(script_url, url)
        set_timeout(0, Task(self.js.run, script, body))
```

As you probably know, scripts are not just for running straight through in one
task, or responding to input events. They can also schedule more events to be
put on the rendering event loop and run later. There are multiple JavaScript
APIs in browsers to do this, but for now let's focus on the one most related to
rendering: `requestAnimationFrame`.[^set-timeout] It's used like this:

[^set-timeout]: the `setTimeout` JavaScript API is very easy to add also, but
I'll leave that as an exercise.

``` {.javascript expected=False}
/* This is JavaScript */
function callback() {
    console.log("I was called!");
}
requestAnimationFrame(callback);
```

This code will do two things: request an animation frame task to be run on the
event loop,[^animation-frame] and call `callback` at the beginning of that
rendering task. This is super useful to web page authors, as it allows them to
do any setup work related to rendering just before it occurs. The
implementation of this JavaScript API is straightforward: add a new dirty bit
to `Tab` and code to call the JavaScript callbacks during the
next animation frame.

[^animation-frame]: Now you know why I chose the `*_animation_frame` naming
for the methods on `Tab` in the previous section!

``` {.python expected=False}
class JSContext:
    def __init__(self, tab):
        # ...
        self.interp.export_function("requestAnimationFrame",
            self.requestAnimationFrame)

    def requestAnimationFrame(self):
        self.tab.request_animation_frame_callback()

class Tab:
    def __init__(self, browser):
        self.needs_raf_callbacks = False

    def request_animation_frame_callback(self):
        self.needs_raf_callbacks = True
        self.set_needs_animation_frame()

    def run_animation_frame(self):
        if self.needs_raf_callbacks:
            self.needs_raf_callbacks = False
            self.js.interp.evaljs("__runRAFHandlers()")

        self.run_rendering_pipeline()
        browser.raster_and_draw()
```

And in the JavaScript runtime we'll need:

``` {.javascript file=runtime}
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

Let's walk through what `run_animation_frame` does:

1. Reset `needs_animation_frame` and `needs_raf_callbacks` to
`False`
2. Call the JavaScript callbacks
3. Run the rendering pipeline

Look a bit more closely at steps 1 and 2. Would it work to run step 1 *after*
step 2? The answer is no, but the reason is subtle: it's because the JavaScript
callback code could call `requestAnimationFrame`. If this happens
during such a callback, the spec says that a *second*  animation frame should
be scheduled (and 16ms further in the future, naturally). Likewise, the runtime
JavaScript needs to be careful to copy the `RAF_LISTENERS` array to a temporary
variable and then clear out ``RAF_LISTENERS``, so that it can be re-filled by
any new calls to `requestAnimationFrame`.

This situation may seem like a corner case, but it's actually very important, as
this is how JavaScript can run a 60Hz animation. Let's
try it out with a script that counts from 1 to 100, one frame at a time:

``` {.javascript file=eventloop}
var count = 0;
var start_time = Date.now();
var cur_frame_time = start_time;

function callback() {
    var since_last_frame = Date.now() - cur_frame_time;
    var total_elapsed = Date.now() - start_time;
    var output = document.querySelectorAll("div")[1];
    output.innerHTML = "count: " + (count++) + "<br>" +
        " time elapsed since last frame: " + 
        since_last_frame + "ms" +
        " total time elapsed: " + total_elapsed + "ms";
    if (count < 100)
        requestAnimationFrame(callback);
    cur_frame_time = Date.now()
}
requestAnimationFrame(callback);
```

To make the above code work, you'll need this small addition to the runtime 
code to implement a subset of the [Date API][date-api]:

[date-api]: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date

``` {.javascript}
function Date() {}
Date.now = function() {
    return call_python("now");
}
```
and Python bindings:
``` {.python}
class JSContext:
    def __init__(self, tab):
        # ...
        self.interp.export_function("now",
            self.now)

    def now(self):
        return int(time.time() * 1000)
```

This script will cause 100 animation frame tasks to run on the rendering event
loop. During that time, our browser will display an animated count from 0 to
99.

And while we're at it, let's add an web page to our HTTP server that
serves this example:

``` {.python file=server replace=eventloop12/eventloop}
def do_request(session, method, url, headers, body):
    elif method == "GET" and url == "/count":
        return "200 OK", show_count()
# ...
def show_count():
    out = "<!doctype html>"
    out += "<div>";
    out += "  Let's count up to 100!"
    out += "</div>";
    out += "<div>Output</div>"
    out += "<script src=/eventloop.js></script>"
    return out
```

Parallel rendering
==================

What happens if rendering takes much more than 16ms to finish? If
it's a rendering task that's slow, such as font loading (see
[chapter 3][faster-text-loading]), if we're lucky we can make it faster.
But sometimes it's not possible to make the code a lot faster, it just has a
lot to do. In rendering, this could be because the web page is very large or
complex.

[faster-text-loading]: text.md#faster-text-layout

What if we ran raster and draw *in parallel* with the main thread, by using
CPU parallelism? That sounds fun to try, but before adding such complexity,
let's instrument the browser and measure how much time is really being spent
in raster and draw (always measure before optimizing!).

Add a simple class measuring time spent:

``` {.python}
class Timer:
    def __init__(self):
        self.time = None

    def start(self):
        self.time = time.time()

    def stop(self):
        return time.time() - self.time
        self.time = None
```

Now count total time spent in the two categories:

TODO: explain handle_quit. Maybe add to chapter 11?

``` {.python expected=False}
class Tab:
    def __init__(self, browser):
        # ...
        self.time_in_style_layout_and_paint = 0.0

    def run_rendering_pipeline(self):
        if self.needs_pipeline_update:
            timer = Timer()
            timer.start()
            style(self.nodes, sorted(self.rules,
                key=cascade_priority))
            self.document = DocumentLayout(self.nodes)
            self.document.layout()
            self.display_list = []
            self.document.paint(self.display_list)
            self.time_in_style_layout_and_paint += timer.stop()

    def handle_quit(self):
        print("Time in style, layout and paint: {:>.6f}s".format(
            self.tab.time_in_style_layout_and_paint))
```

``` {.python}
class Browser:
    def __init__(self):
        self.time_in_raster_and_draw = 0
        self.time_in_draw = 0

    def raster_and_draw(self):
        timer = None
        if self.needs_draw:
            timer = Timer()
            timer.start()
        if self.needs_chrome_raster:
            self.raster_chrome()
        if self.needs_tab_raster:
            self.raster_tab()
        if self.needs_draw:
            draw_timer = Timer()
            draw_timer.start()
            self.draw()
            self.time_in_draw += draw_timer.stop()
        self.needs_tab_raster = False
        self.needs_chrome_raster = False
        self.needs_draw = False
        if timer:
            self.time_in_raster_and_draw += timer.stop()

    def handle_quit(self):
        print("Time in raster and draw: {:>.6f}s".format(
            self.time_in_raster_and_draw))
        print("Time in draw: {:>.6f}s".format(
            self.time_in_draw))
        # ...
```

Now fire up the server and navigate to `http://localhost:8000/count`. When it's
done counting, click the close button on the window. The browser will print out
the total time spent in each category. When I ran it on my computer, it said:

    Time in raster and draw: 1.855505s
    Time in draw: 1.753160s
    Time in style, layout and paint: 0.097325s

Over a total of 100 frames of animation, the browser spent about 1.9s (or 19ms
per animation frame on average) rastering and drawing[^raster-draw], and most
of the time is in draw, not raster. On the other hand, the browser spent about
100ms (1ms per animation frame) in the other phases.[^timing-overhead]

If I were optimizing the browser, the first thing I'd do would be to optimize
draw.[^profile-draw] I profiled, it, and found that each of the steps of the
surface-drawing-into-surface steps (of which there are three) take a
significant amount of time. (I told you that[optimizing surfaces]
[visual-effects.md#optimizing-surface-use] was important!) 

But even if those surfaces were optimized, raster is still as slow as
style, layout and paint put together. So we should see a win by running
raster and draw on a parallel thread.

[^profile-draw]: I encourage you to do this profiling, to see for yourself.

[^raster-draw]: When I first wrote this section of the chapter, I was surpised
at how high the raster and draw time was, so I went back and added the separate
draw timer that you see in the code above. Profiing your code often yields
interesting insights!

[^timing-overhead]: It's always good to remember that, unless you're careful,
sometimes the overhead to measure timings can bias the timings themselves. In
our case, since the style, layout and paint timer only showed 1ms per frame, it
can't be all that high.

::: {.further}
It's possible to optimize those surfaces further, but the best way to do that
is to put them on the GPU (and modern browsers do it!), so that the draws can
happen in parallel in GPU hardware. But for real web pages, raster and draw
sometimes really do take a lot of time on complex pages, even with the GPU. So
rendering pipeline parallelism is a win regardless.
:::

Slow scripts
============

JavaScript can also be arbitrarily slow to run, of course. This is a problem,
because these scripts can make the browser very janky and annoying to use---so
annoying that you will quickly not want to use that browser. But don't take my
word for it---let's implement an artificial slowdown and you can see for
yourself.

Add the slowdown to our counter page as follows, with a 200ms synchronous delay
running JavaScript:

``` {.javascript file=eventloop}
var count = 0;
var start_time = Date.now();
var cur_frame_time = start_time;

artificial_delay_ms = 200;

function callback() {
    var since_last_frame = Date.now() - cur_frame_time;
    while (since_last_frame < artificial_delay_ms) {
        var since_last_frame = Date.now() - cur_frame_time;
    }
    # ...
}
```

Now load the page and hold down the down arrow button. Observe how inconsistent
and janky the scrolling is. Compare with no artificial delay, which is pleasant
to scroll.

Browsers can and do optimize their JavaScript engines to be as fast as possible,
but ultimately scripts can and are sometimes very slow. So the only way to keep
the browser responsive is to run key interactions in parallel with JavaScript.
Luckily, it's pretty easy to use the raster and draw thread we're planning
to *also* scroll and interact with browser chrome.

The browser thread
==================

This new thread will be called the *browser thread*.[^also-compositor] The
browser thread will be for:

[^also-compositor]: This thread is similar to what modern browsers call the 
*compositor thread*.

* Raster and draw
* Interacting with browser chrome
* Scrolling

The other thread, which we'll call the *main thread,*[^main-thread-name] will
be for:

* Evaluating scripts
* Loading resources
* The front half of the rendering pipeline: animation frame callbacks, style,
  layout, and paint
* Event handlers for clicking on and typing into web pages

[^main-thread-name]: Here I'm going with the name real browsers often use. A
better name might be the "JavaScript" thread (or even bertter, the "DOM"
thread, since JavaScript can sometimes run on [other threads][webworker]).

[webworker]: https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API

Let's implement the browser thread with [Python threads][python-thread]. All
code in `Browser` will run on the browser thread, and all code in `Tab` and
`JSContext` will run on the main thread.

The thread that already exists (the one started by the Python interpreter
by default) will be the browser thread, and we'll make a new one for
the main thread. Let's add a new `MainThreadRunner` class that will
encapsulate the main thread and its event loop. The two threads will
communicate by writing to and reading from some shared data structures, and use
`threading.Lock` objects to prevent race conditions. `MainThreadRunner` will
be the only class allowed to call methods on `Tab` or `JSContext`.

`MainThreadRunner` will have a lock and a thread object. Calling `start` will
begin the thread. This will excute the `run` method on that thread; `run` will
execute forever (until the program quits, which is indicated by the
`needs_quit` dirty bit) and is where we'll put the main thread event loop.
There will also be two task queues (one for browser-generated tasks such as
clicks, and one for tasks to evaluate scripts), and a rendering pipeline dirty
bit.

``` {.python}
class MainThreadRunner:
    def __init__(self, tab):
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.tab = tab
        self.needs_animation_frame = False
        self.main_thread = threading.Thread(target=self.run, args=())
        self.script_tasks = TaskQueue()
        self.browser_tasks = TaskQueue()
        self.needs_quit = False

    def start(self):
        self.main_thread.start()    

    def run(self):
        while True:
            # ...
```
\
Add some methods to set the dirty bit and schedule tasks. These need to 
acquire the lock before setting these thread-safe variables. (Ignore the
`condition` line, we'll get to that in a moment).


``` {.python}
    def schedule_animation_frame(self):
        self.lock.acquire(blocking=True)
        self.needs_animation_frame = True
        self.condition.notify_all()
        self.lock.release()

    def schedule_script_task(self, script):
        self.lock.acquire(blocking=True)
        self.script_tasks.add_task(script)
        self.condition.notify_all()
        self.lock.release()

    def schedule_browser_task(self, callback):
        self.lock.acquire(blocking=True)
        self.browser_tasks.add_task(callback)
        self.condition.notify_all()

    def set_needs_quit(self):
        self.lock.acquire(blocking=True)
        self.needs_quit = True
        self.condition.notify_all()
        self.lock.release()
```

In `run`, implement a simple event loop scheduling strategy that runs the
rendering pipeline if needed, and also one browser method and one script task,
if there are any on those queues.

The part at thet end is the trickiest. First, we check if there are more tasks
to excecute; if so, loop again and run those tasks. If not, sleep until there
is a task to run. The way we "sleep until there is a task" is via a *condition
variable*, which is a way for one thread to block until it has been notified by
another thread that the the desired condition has become true.[^threading-hard]

[^threading-hard]: Threading and locks are hard, and it's easy to get into a
deadlock situation. Read the [documentation][python-thread] for the classes
you're using very carefully, and make sure to release the lock in all the right
places. For example, `condition.wait()` will re-acquire the lock once it has
been notified, so you'll need to release the lock immediately after, or else
the thread will deadlock in the next while loop iteration.

``` {.python}
     def run(self):
        while True:
            self.lock.acquire(blocking=True)
            needs_animation_frame = self.needs_animation_frame
            self.lock.release()
            if needs_animation_frame:
                self.tab.run_animation_frame()

            browser_method = None
            if self.browser_tasks.has_tasks():
                browser_method = self.browser_tasks.get_next_task()
            if browser_method:
                browser_method()

            script = None
            if self.script_tasks.has_tasks():
                script = self.script_tasks.get_next_task()

            if script:
                script()

            self.lock.acquire(blocking=True)
            if not self.script_tasks.has_tasks() and \
                not self.browser_tasks.has_tasks() and not \
                self.needs_animation_frame and not \
                self.needs_quit:
                self.condition.wait()
            self.lock.release()
```

Each `Tab` will own a `MainThreadRunner`, control its runtime, and
schedule script eval tasks and animation frames on it:

``` {.python replace=browser/commit_func,%20body))/}
class Tab:
    def __init__(self, browser):
        self.main_thread_runner = MainThreadRunner(self)
        self.main_thread_runner.start()

    def load(self, url, body=None):
        # ...
        for script in scripts:
            # ...
            self.main_thread_runner.schedule_script_task(
                Task(self.js.run, script_url, body))

    def set_needs_animation_frame(self):
        def callback():
            self.display_scheduled = False
            self.main_thread_runner.schedule_animation_frame()
        if not self.display_scheduled:
            set_timeout(callback, REFRESH_RATE_SEC)
```

The `Browser` will also schedule tasks on the main thread. But now it's not
safe for any methods on `Tab` to be directly called by `Browser`, because
`Tab` runs on a different thread. All request must be queued as tasks on the
`MainThreadRunner`. To make this easier, let's wrap `Tab` in a new `TabWrapper`
class that only exposes what's needed. `TabWrapper` will run on the browser
thread.

Likewise, `Tab` can't have direct acccess to the `Browser`. But the only
method it needs to call on `Browser` is `raster_and_draw`. We'll rename that
to a `commit` method on `TabWrapper`, and pass this method to `Tab`'s
constructor. When `commit` is called, all state of the `Tab` that's relevant
to the `Browser` is sent across.

``` {.python expected=False}
class Tab:
    def __init__(self, commit_func):
        # ...
        self.commit_func = commit_func

    def run_animation_frame(self):
        self.run_rendering_pipeline()
        # ...
        self.commit_func(
            self.url, self.scroll,
            document_height,
            self.display_list)

```

``` {.python}
class TabWrapper:
    def __init__(self, browser):
        self.tab = Tab(self.commit)
        self.browser = browser
        self.url = None
        self.scroll = 0

    def commit(self, url, scroll, tab_height, display_list):
        self.browser.compositor_lock.acquire(blocking=True)
        if url != self.url or scroll != self.scroll:
            self.browser.set_needs_chrome_raster()
        self.url = url
        if scroll != None:
            self.scroll = scroll
        self.browser.active_tab_height = tab_height
        self.browser.active_tab_display_list = display_list.copy()
        self.browser.set_needs_tab_raster()
        self.browser.compositor_lock.release()
```

Note that `commit` will acquire a lock on the browser thread before doing
any of its work, because all of the inputs and outputs to it are cross-thread
data structures.[^fast-commit]

[^fast-commit]: `commit` is the one time when both threads are both "stopped"
simultaneously---in the sense that neither is running a different task at the
same time. For this reason commit needs to be as fast as possible, so as to
lose the minimum possible amount of parallelism and responsiveness.

Finally, let's add some methods on `TabWrapper` to schedule various kinds
of main thread tasks scheduled by the `Browser` (`schedule_scroll` will be
implementd on `MainThreadRunner` in a bit).

``` {.python}
class TabWrapper:
    def schedule_load(self, url, body=None):
        self.tab.main_thread_runner.schedule_browser_task(
            Task(self.tab.load, url, body))
        self.browser.set_needs_chrome_raster()

    def schedule_click(self, x, y):
        self.tab.main_thread_runner.schedule_browser_task(
            Task(self.tab.click, x, y))

    def schedule_keypress(self, char):
        self.tab.main_thread_runner.schedule_browser_task(
            Task(self.tab.keypress, char))

    def schedule_go_back(self):
        self.tab.main_thread_runner.schedule_browser_task(
            Task(self.tab.go_back))

    def schedule_scroll(self, scroll):
        self.scroll = scroll
        self.tab.main_thread_runner.schedule_scroll(scroll)

    def handle_quit(self):
        self.tab.main_thread_runner.set_needs_quit()
```

Next up we'll call all these methods from the browser thread, for example
loading:

``` {.python}
class Browser:
    def load(self, url):
        new_tab = TabWrapper(self)
        new_tab.schedule_load(url)
        self.active_tab = len(self.tabs)
        self.tabs.append(new_tab)
```

We can do the same for input event handlers, but there are a few additional
subtleties. Let's look closely at each of them in turn, starting with
`handle_click`. In most cases, we will need to
[hit test](chrome.md#hit-testing) for which DOM element receives the click
event, and also fire an event that JavaScript can listen to. Since DOM
computations and JavaScript can only be run on the main thread, it seems we
should just send the click event to the main thread for processing. But if the
click was *not* within the web page window, we can handle it right there in the
compositor thread, and leave the main thread none the wiser:

``` {.python}
class Browser:
    def handle_click(self, e):
        self.compositor_lock.acquire(blocking=True)
        if e.y < CHROME_PX:
            self.focus = None
            if 40 <= e.x < 40 + 80 * len(self.tabs) and 0 <= e.y < 40:
                self.active_tab = int((e.x - 40) / 80)
            elif 10 <= e.x < 30 and 10 <= e.y < 30:
                self.load("https://browser.engineering/")
            elif 10 <= e.x < 35 and 40 <= e.y < 90:
                self.tabs[self.active_tab].schedule_go_back()
            elif 50 <= e.x < WIDTH - 10 and 40 <= e.y < 90:
                self.focus = "address bar"
                self.address_bar = ""
            self.set_needs_chrome_raster()
        else:
            self.focus = "content"
            self.tabs[self.active_tab].schedule_click(
                e.x, e.y - CHROME_PX)
        self.compositor_lock.release()

```

The same logic holds for `keypress`:

``` {.python}
class Browser:
    def handle_key(self, char):
        self.compositor_lock.acquire(blocking=True)
        if not (0x20 <= ord(char) < 0x7f): return
        if self.focus == "address bar":
            self.address_bar += char
            self.set_needs_chrome_raster()
        elif self.focus == "content":
            self.tabs[self.active_tab].schedule_keypress(char)
        self.compositor_lock.release()
```

As it turns out, the return key and scrolling have no use at all for the main
thread:

``` {.python expected=False}
class Browser:
    def handle_down(self):
        self.compositor_lock.acquire(blocking=True)
        if not self.active_tab_height:
            return
        max_y = self.active_tab_height - (HEIGHT - CHROME_PX)
        active_tab = self.tabs[self.active_tab]
        active_tab.schedule_scroll(
            min(active_tab.scroll + SCROLL_STEP, max_y))
        self.set_needs_draw()
        self.compositor_lock.release()
```

::: {.further}
Our browser code uses locks, because real multi-threaded programs
will need them. However, Python has a [global interpreter lock][gil], which
means that you can't really run two Python threads in parallel, so technically
these locks don't do anything useful in our browser. (The interpreter lock is
present because the Python bytecode interpreter is not thread-safe.)

This also means that the *throughput* (animation frames delivered per second) of
our browser will not actually be greater with two threads. However, it's
possible to turn off the global interpreter lock while running foreign C/C++
code linked into a Python library. Skia is thread-safe, but SDL may not be.

However, even though the throughput is not higher, the *responsiveness* of the
browser thread is still massively improved, since it isn't running JavaScript
or the front half of the rendering pipeline.
:::

[gil]: https://wiki.python.org/moin/GlobalInterpreterLock

Threaded scrolling
==================

Recall how we've added some scroll-related code, but we didn't really get into
how it works (I also omitted some of the code). Let's now carefully examine
how to implement threaded scrolling. But before getting to that, go and load
the counting demo with artificial delay, and check out how much more responsive
scrolling is now!

The reason that scrolling so responsive is that it happens on the browser
thread, without waiting around to synchronoize with the main thread. But the
main thread can and does affect scroll. For example, when loading a new page,
scroll is set to 0; when running `innerHTML`, the height of the document could
change, leading to a potential change of scroll offset. What should
we do if the two threads disagree about the scroll offset?

The best policy is to respect the scroll offset the user last observed, unless
it's incompatible with the web page. In other words, use the browser thread
scroll, unless a new web page has loaded or the scroll exceeds the current
document height. Let's implement that.

The trickiest part is how to communicate a browser thread scroll offset to the
main thread, and integrate it with the rendering pipeline. It'll work like
this:

* When the browser thread changes scroll offset, notify the `MainThreadRunner`
and store the result in a `pending_scroll` variable.
* When `MainThreadRunner` decides to run an animation frame, first apply
the `pending_scroll` to the `Tab`. Then, after running the rendering pipeline,
*adjust* it if the document height requires it.
* When loading a new page in a `Tab`, override the scroll.
* If an animation frame or load caused a scroll adjustment, note it in a
new `scroll_changed_in_tab` variable on `Tab`
* When calling `commit`, only pass the scroll if it was changed in the `Tab`,
and otherwise pass `None`. Commit will ignore the scroll if it is `None`.

Implement each of these in turn. In `MainThreadRunner`:

``` {.python}
class MainThreadRunner:
    def __init__(self, tab):
        # ...
        self.pending_scroll = None

    def schedule_scroll(self, scroll):
        self.lock.acquire(blocking=True)
        self.pending_scroll = scroll
        self.condition.notify_all()
        self.lock.release()

    def run(self):
        # ...
        self.lock.acquire(blocking=True)
        needs_animation_frame = self.needs_animation_frame
        self.needs_animation_frame = False
        pending_scroll = self.pending_scroll
        self.pending_scroll = None
        self.lock.release()
        if pending_scroll:
            self.tab.apply_scroll(pending_scroll)
        if needs_animation_frame:
            self.tab.run_animation_frame()
        # ...
        self.lock.acquire(blocking=True)
        if not self.script_tasks.has_tasks() and \
            not self.browser_tasks.has_tasks() and not \
            self.needs_animation_frame and not \
            self.pending_scroll and not \
            self.needs_quit:
            self.condition.wait()
        self.lock.release()
```

in `Tab`:

``` {.python expected=False}
def clamp_scroll(scroll, tab_height):
    return min(scroll, tab_height - (HEIGHT - CHROME_PX))

class Tab:
    def __init__(self, commit_func):
        # ...
        self.scroll_changed_in_tab = False
    # ...
    def apply_scroll(self, scroll):
        self.scroll = scroll

    def load(self, url, body=None):
        headers, body = request(url, self.url, payload=body)
        self.scroll = 0
        self.scroll_changed_in_tab = True
        # ...

    def run_animation_frame(self):
        # ....
        self.run_rendering_pipeline()

        document_height = math.ceil(self.document.height)
        clamped_scroll = clamp_scroll(self.scroll, document_height)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_tab = True
        self.scroll = clamped_scroll

        self.commit_func(
            self.url, clamped_scroll if self.scroll_changed_in_tab \
                else None, 
            document_height,
            self.display_list)
        self.scroll_changed_in_tab = False
```

In `TabWrapper`:

``` {.python}
class TabWrapper:
    def commit(self, url, scroll, tab_height, display_list):
        # ...
        if scroll != None:
            self.scroll = scroll
```

In `Browser`:

``` {.python}
class Browser:
    def handle_down(self):
        # ...
        active_tab.schedule_scroll(
            clamp_scroll(
                active_tab.scroll + SCROLL_STEP, self.active_tab_height))
        # ...
```

That's it! Pretty complicated, but we got it done.

Now let's step back from the code for a bit and consider the full scope of
scrolling. Unfortunately, threaded scrolling is not always possible or feasible
in real browsers. In the best browsers today, there are two primary reasons why
threaded scrolling may fail to occur:

* Javascript events listening to a scroll. If the event handler
for the [`scroll`][scroll-event] event calls `preventDefault` on the first such
event (or via [`touchstart`][touchstart-event] on mobile devices), the scroll
will not be threaded in most browsers. Our browser has not implemented these
events, and so can avoid this situation.[^real-browser-threaded-scroll]

[scroll-event]: https://developer.mozilla.org/en-US/docs/Web/API/Document/scroll_event
[touchstart-event]: https://developer.mozilla.org/en-US/docs/Web/API/Element/touchstart_event

[^real-browser-threaded-scroll]: A real browser would also have an optimization
to disable threaded scrolling only if there was such an event listener, and
transition back to threaded as soon as it doens't see `preventDefault` called.
This situation is so important that there is also a special kind of event
listener [designed just for it][designed-for].

* Certain advanced (and thankfully uncommon) rendering features, such as
[`background-attachment:
fixed`](https://developer.mozilla.org/en-US/docs/Web/CSS/background-attachment).
These features are complex and uncommon enough that that browsers disable
threaded scrolling when they are present. Sometimes browsers simply
disallow these features.[^not-supported]

[designed-for]: https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/addEventListener#improving_scrolling_performance_with_passive_listeners

[^not-supported]: Until 2020, Chromium-based browsers on Android did just this,
and did not support `background-attachment: fixed`.

Threaded loading
================

The last piece of code that can be threaded is loading resources from the
network, i.e calls to `request` and `XMLHTTPRequest`.

In the `load` method on `Tab`, currently the first thing it does is
synchronously wait for a network response to loading the main HTML resource.
It then does the same thing for each subsequent *sub-resource request*, to load
style sheets and scripts. Arguably, there isn't a whole lot of point to making
the initial request asynchronous, because there isn't anything else for the
main thread to do in the meantime. But there is a pretty clear performance
problem with the script and style sheet requests: they pile up sequentially,
which means that there is a loading delay equal to the round-trip time to the
server, multiplied by the number of scripts and style sheets.

We should be able to send off all of the requests in parallel. Let's use an
async, threaded version of `request` to do that. For simplicity, let's make new
thread for each resource. When a resource loads, the thread will complete and
we can parse the script or load the style sheet, as appropriate.
[^ignore-order]

Define a new `async_request` function. This will start a thread. The thread will
requests the resource, store the results in `results`, and then return. The
thread refrence will be returned by `async_request`. It's expected that the
caller of this function will call `join` on the thread (`join` means
"block until the thread has completed").

``` {.python}
def async_request(url, top_level_url, results):
    headers = None
    body = None
    def runner():
        headers, body = request(url, top_level_url)
        results[url] = {'headers': headers, 'body': body}
    thread = threading.Thread(target=runner)
    thread.start()
    return thread
```

Then we can use it in `load`. Note how we send off all of the requests first,
and only at the end `join` all of the threaqds created.

``` {.python}
class Tab:
    def load(self, url, body=None):
        # ...
        async_requests = []
        script_results = {}
        for script in scripts:
            script_url = resolve_url(script, url)
            if not self.allowed_request(script_url):
                print("Blocked script", script, "due to CSP")
                continue
            async_requests.append({
                "url": script_url,
                "type": "script",
                "thread": async_request(script_url, url, script_results)
            })
 
        self.rules = self.default_style_sheet.copy()
        links = [node.attributes["href"]
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "link"
                 and "href" in node.attributes
                 and node.attributes.get("rel") == "stylesheet"]

        style_results = {}
        for link in links:
            style_url = resolve_url(link, url)
            if not self.allowed_request(style_url):
                print("Blocked style", link, "due to CSP")
                continue
            async_requests.append({
                "url": style_url,
                "type": "style sheet",
                "thread": async_request(style_url, url, style_results)
            })
            try:
                header, body = request(style_url, url)
            except:
                continue

        for async_req in async_requests:
            async_req["thread"].join()
            if async_req["type"] == "script":
                script_url = async_req["url"]
                self.main_thread_runner.schedule_script_task(
                    Task(self.js.run, script_url,
                        script_results[script_url]['body']))
            else:
                self.rules.extend(CSSParser(results['body']).parse())
```

Now our browser will parallleize loading sub-resources!

Next up is `XHMLHttpRequest`. We introduced this API in chapter 10, and
implemented it only as a synchronous API. But in fact, the synchronous
version of that API is almost useless for real websites,^[and also a huge
performance footgun, for the same reason we've been optiming work to use
threads in this chapter!], because the whole point of using thia API on a
website is to keep it resposive to the user while network requests are going
on.

Let's fix that. We'll make these changes. There are a bunch of them, but they
are mostly about communicating back and forth with JavaScript.
* Allow `is_async` to be `true` in the constructor of `XMLHttpRequest` in the
runtime
* Store a uniquehandle for each `XMLHttpRequest` object, analogous to how we
  used handles for `Node`s
* Store a map from handle to object
* Add a new `__runXHROnload` method that will call the `onload` function
specified on a `XMLHttpRequest`, if any
* Store the response on the `responseText` field, as required by the API
* Augment `XMLHttpRequest_send` to support async requests that use a thread
and a subsequent script task on `main_thread_runner`.

Here's the runtime JavaScript code:

``` {.javascript}
XHR_REQUESTS = {}

function XMLHttpRequest() {
    this.handle = Object.keys(XHR_REQUESTS).length;
    XHR_REQUESTS[this.handle] = this;
}

XMLHttpRequest.prototype.open = function(method, url, is_async) {
    this.is_async = is_async
    this.method = method;
    this.url = url;
}

XMLHttpRequest.prototype.send = function(body) {
    this.responseText = call_python("XMLHttpRequest_send",
        this.method, this.url, this.body, this.is_async, this.handle);
}

function __runXHROnload(body, handle) {
    var obj = XHR_REQUESTS[handle];
    var evt = new Event('load');
    obj.responseText = body;
    if (obj.onload)
        obj.onload(evt);
}
```

On the Python side, here's `XMLHttpRequest_send`:

``` {.python}
class JSContext:
    def XMLHttpRequest_send(self, method, url, body, is_async, handle):
        full_url = resolve_url(url, self.tab.url)
        if not self.tab.allowed_request(full_url):
            raise Exception("Cross-origin XHR blocked by CSP")

        def run_load():
            headers, out = request(full_url, self.tab.url, payload=body)
            handle_local = handle
            if url_origin(full_url) != url_origin(self.tab.url):
                raise Exception("Cross-origin XHR request not allowed")
            self.tab.main_thread_runner.schedule_script_task(
                Task(self.xhr_onload, out, handle_local))
            return out

        if not is_async:
            run_load(is_async)
        else:
            load_thread = threading.Thread(target=run_load, args=())
            load_thread.start()
```

As you can see, the threading and task machinery we've built is quite
general and multi-purpose!

Now let's try out this new async API by augmenting our counter javscript like
this:

``` {.javascript file=eventloop}
function callback() {
    if (count == 0)
        requestXHR();
    # ...
}

var request;
function requestXHR() {
    request = new XMLHttpRequest();
    request.open('GET', '/xhr', true);
    request.onload = function(evt) {
        document.querySelectorAll("div")[2].innerHTML = 
            "XHR result: " + this.responseText;
    };
    request.send();
}
```

And the HTTP server:

``` {.python file=server}
def show_count():
    out = "<!doctype html>"
    out += "<div>";
    out += "  Let's count up to 50!"
    out += "</div>";
    out += "<div>Output</div>"
    out += "<div>XHR</div>"
    # ...

def show_xhr():
    time.sleep(5)
    return "Slow XMLHttpRequest response!"
```

Load the counter page. You should see the counter going up, and then after
5 seconds, "Slow XMLHttpRequest response!" should appear onscreen.

[^ignore-order]: This ignores the parse order of the scripts and style sheets,
which is technically incorrect and a real browser would be much more
careful. But as mentioned in an earlier chapter, our browser is already
incorrect in terms of orders of operations, as scripts and style sheets are
supposed to block the HTML parser as well.

Threaded style and layout
=========================

You may have wondered: does the earlier part of the rendering pipeline---style,
layout and paint---have to run on the main thread? The answer is: in principle,
no. The only thing browsers *have* to do is implement all the web API
specifications correctly, and draw to the screen after scripts and
`requestAnimationFrame` callbacks have completed. The
specification spells this out in detail in what it calls the
[update-the-rendering] steps. Go look at that link and come back. Notice
anything missing? That's right, it doesn't mention style or layout at all! All
it says is "update the rendering or user interface" at the very end.

[update-the-rendering]: https://html.spec.whatwg.org/multipage/webappapis.html#update-the-rendering

How can that be? Aren't style and layout crucial parts of the way HTML and CSS
work? Yes they are---but note the spec doesn't mention paint, draw or raster
either. And just like those parts of the pipeline, style and layout are
considered pure implementation details of a browser. The spec simply says that
if rendering "opportunities" arise, then the update-the-rendering steps are the
sequence of *JavaScript-observable* things that have to happen before drawing
to the screen.



Nevertheless, no current modern browser runs style or layout on another thread
than the main thread.[^servo] The reason is simple: there are many JavaScript
APIs that can query style or layout state. For example, [`getComputedStyle`](https://developer.mozilla.org/en-US/docs/Web/API/Window/getComputedStyle)
can't be implemented without the browser first computing style, and
`getBoundingClientRect` needs layout.[^nothing-later] If a web page calls
one of these APIs, and style or layout is not up-to-date, then is has to be
computed synchronously, then and there. These computations are called
*forced style* or *forced layout*. The world "forced" refers to forcing the
 computation to happen right away, as opposed to possibly 16ms in the future if
 it didn't happen to be already computed. Because there are forced style and
 layout situations, browsers have to be able to do that work on the main thread
 if necessary.[^or-stall]

 [^or-stall]: Or stall the compositor thread and ask it to do it synchronously.



[^servo]: The [Servo] rendering engine is sort of an exception. However, in that
case it's not that style and layout run on a different thread, but that they
attempt to take advantage of parallelism for faster end-to-end performance. It's
more akin to the reason the hardware acceleration we saw in [chapter
12](visual-effects.md#hardware-acceleration) makes things faster; this is not
the same thing as "threaded style and layout".

[Servo]: https://en.wikipedia.org/wiki/Servo_(software)

[^nothing-later]: There is no JavaScript API that allows reading back state
from anything later in the rendering pipeline than layout.

By analogy with web pages that don't `preventDefault` a scroll, is it a good
idea to try to optimistically move style and layout off the main thread for
cases when JavaScript doesn't force it to be done otherwise? Maybe, but even
setting aside this problem there are unfortunately other sources of forced
style and layout. One example is our current implementation of `innerHTML`. Look
closely at the code, can you see the forced layout?

``` {.python}
class JSContext:
    def innerHTML_set(self, handle, s):
        self.tab.run_rendering_pipeline()
        doc = HTMLParser("<html><body>" + s + "</body></html>").parse()
        new_nodes = doc.children[0].children
        elt = self.handle_to_node[handle]
        elt.children = new_nodes
        for child in elt.children:
            child.parent = elt
        self.tab.set_needs_pipeline_update()
```

The call to `run_rendering_pipeline` is a forced layout. It's needed because
`layout_for_node` needs an up-to-date layout tree in order to find the right
node. Luckily, this forced layout can be avoided. One way---employed
by real browsers---is to store a pointer from each DOM element to its layout
object, rather than searching for it by walking the layout tree.

However, even if we fix that there are yet more reasons why forced layouts are
needed. A tricky one is hit testing. When a click event happens, looking at
positions of layout objects is how the browser knows which element was clicked
on. This is implemented in `find_layout`.

However, `handle_click` doesn't call `run_rendering_pipeline` like
`js_innerHTML` does; why not? In a real browser, this would be a bug, but in
our current browser it's really difficult to cause a situation to happen where
a click event happens but the rendering pipeline is not up-to-date. That's
because currently the only way to schedule a script task is via
`requestAnimationFrame`. In a real browser there is also `setTimeout`, for
example. For completeness, let's implement it by adding a call to 
`update_rendering_pipeline` before `find_layout`:

``` {.python}
class Tab:
    def click(self, x, y):
        self.run_rendering_pipeline()
        # ...
```

It's not impossible to move style and layout off the main thread
"optimistically", but these are the reasons it's challenging. for browsers to do
it. I expect that at some point in the future it will be achieved (maybe you'll
be the one to do it?).

Summary
=======

This chapter explained in some detail the two-thread rendering system at the
core of modern browsers. The main points to remember are:

* The browser uses event loops, tasks and task queues to do work.

* The goal is to consistently generate drawings to the screen at a 60Hz
cadence, which means a 16ms budget to draw each animation frame.

* There are multiple ways to achieve the desired animation frame candence:
do less work, cache, parallelize, and schedule.

* The main thread runs an event loop for various tasks, including
JavaScript, style and layout. The rendering task is special, can include
special JavaScript `requestAnimationFrame` callbacks in it, and at the end
commits a display list to a second thread.

* The second thread is the compsitor thread. It draws the display list to the
screen and handles/dispatches input events, scrolls, and interactions with the
browser chrome.

* Forced style and layout makes it hard to fully isolate the rendering pipeline
from JavaScript.

Exercises
=========

* *Networking thread*: Real browsers tend to have a separate thread for
networking (and other I/O). Implement a third thread with an event loop and put
all networking tasks (including HTML and script fetches) on it.

* *setTimeout*: The [`setTimeout`] JavaScript API schedules a function to be
called a fixed number of milliseconds from now. Implement it, and try to
implement a web page that demonstrates the hit testing but we fixed above.

[setTimeout]: https://developer.mozilla.org/en-US/docs/Web/API/WindowOrWorkerGlobalScope/setTimeout

* *setInterval*: [`setInterval`][setInterval] is similar to `setTimeout` but
runs repeatedly at a given cadence until [`clearInterval`][clearInterval] is
called. Implement these, and test them out on a sample page that also uses
`requestAnimationFrame` with various cadences, and with some expensive rendering
pipeline work to do. Use console.log or `innerHTML` to record the actual timings
via `Date.now`. How consistent are the cadences?

[setInterval]: https://developer.mozilla.org/en-US/docs/Web/API/WindowOrWorkerGlobalScope/setInterval
[clearInterval]: https://developer.mozilla.org/en-US/docs/Web/API/WindowOrWorkerGlobalScope/clearInterval

* *Clock-based frame timing*: Right now our browser schedules the next
animation frame to happen exactly 16ms later than the first time
`set_needs_animation_frame` is called. However, this actually leads to a slower
animation frame rate cadence than 16ms, for example if `run_rendering_pipeline`
takes say 10ms to run. Can you see why? Fix this in our browser by aligning
calls to `begin_main_frame` to an absolute clock time cadence.

* *Scheduling*: As more types of complex tasks end up on the event queue, there
comes a greater need to carefully schedule them to ensure the rendering cadence
is as close to 16ms as possible, and also to avoid task starvation. Implement a
sample web page that taxes the system with a lot of `setTimeout`-based tasks,
come up with a simple scheduling algorithm that does a good job at balancing
these two needs.

* *Font caching*: look at the tkinter source code. Can you figure out where its
font cache is?


*HTTP Requests*: The [`XMLHttpRequest` object][xhr-tutorial] allows scripts to
 make HTTP requests and read the responses.  Implement this API, including the
 `addEventListener`, `open`, and `send` methods. Beware that `XMLHttpRequest`
 calls are asynchronous:[^sync-xhr] you need to finish executing the script
 before calling any event listeners on an `XMLHttpRequest`.[^sync-xhr-ok] That
 will require some kind of queue of requests you need to make and the listeners
 to call afterwards. Make sure `XMLHttpRequest`s work even if you create them
 inside event listeners.
    
[^sync-xhr]: Technically, `XMLHttpRequest` supports synchronous requests as an
option in its API, and this is supported in all browsers, though
[strongly discouraged](https://xhr.spec.whatwg.org/#sync-warning) for web
developers to actually use. It's discouraged because it "freezes" the website
completely while waiting for the response, in the same way form submissions do.
However, it's even worse, than that: because of the single-threaded nature of
the web, other browser tabs might also be frozen at the same time if they share
this thread.

[^sync-xhr-ok]: It's ok for you to cut corners and implement this by making the
browser make the request synchronously, using our `request` function. But the
whole script should finish running before calling the callback.

[xhr-tutorial]: https://developer.mozilla.org/en-US/docs/Web/API/XMLHttpRequest/Using_XMLHttpRequest
