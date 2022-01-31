---
title: Scheduling and Threading
chapter: 12
prev: visual-effects
next: skipped
...

To be a capable application platform, the browser must run
applications efficiently and stay responsive to user actions. To do
so, the browser must explicitly choose which of its many tasks to
prioritize and delay unnecessary tasks until later. Such a task queue
system also allows the browser to split tasks across multiple threads,
which makes the browser even more responsive and a better fit to
modern multi-core hardware.

Tasks
=====

So far, most of the work our browser's been doing has been handling
user actions like scrolling, pressing buttons, and clicking on links.
But as our browser runs more and more sophisticated web applications,
it starts spend more and more time querying remote servers, animating
objects on the page, or prefetching information that the user may
need. This requires a change in perspective: while users are slow and
deliberative, leaving long gaps between actions for the browser to
catch up, applications can be very demanding, with a never-ending queue
of tasks for the browser to do.

Modern browsers adapt to this reality by multitasking, prioritizing,
and deduplicating work. To do so, events from the operating system are
turned into *tasks* and placed onto one of several task queues. Those
task queues are each assigned to different threads, and each thread
chooses the most important task to work on next to keep the browser
fast and responsive. Loading pages, running scripts, and responding to
user actions all become tasks in this framework.

One of the most expensive tasks a browser does is render a web
page---style the HTML elements, construct a layout tree, compute sizes
and positions, paint it to a display list, raster the result into
surfaces, and draw tha surfaces to the screen. These rendering steps
make up the [*rendering pipeline*][graphics-pipeline]
for the browser, and can be expensive and slow. For this reason,
modern browsers split the rendering pipeline across threads and make
sure to run the rendering pipeline only when necessary.

[graphics-pipeline]: https://en.wikipedia.org/wiki/Graphics_pipeline

Refactoring our browser to think in terms of tasks will require
significant changes throughout---concurrent programming is
never easy! But these architectural changes are a key optimization
behind modern browsers, and enable many advanced features discussed in
this and later chapters.

Task queues
===========

At the moment, our browser has a lot of entangled code, and it will take
substantial work to put everything in tasks on queues. Let's start by defining
the infrastructure. This will be a bit of work, so once it's done we'll reward
ourselves for this work by adding a fun new feature built on top of this
tech--the `setTimeout` API.

When the browser is free to do work, it finds the next pending *task* and runs
it, and repeats. A sequence of related tasks is a *task queue*, and browsers
have multiple tasks queues.

One or more task queues can be grouped together into a single, sequential
*thread* of execution. Each thread has an *event loop* associated with
it.[^event-loop] The job of the event loop is to schedule tasks
 according to the priorities of the browser---to make sure it's responsive to
 the user, uses hardware efficiently, loads pages fast, and so on. You've
 already seen many examples of tasks, such as handling clicks, loading, and
 scrolling.

[cores]: https://en.wikipedia.org/wiki/Multi-core_processor

[^event-loop]: Event loops were also briefly touched on in
[chapter 2](graphics.md#eventloop), and we wrote our own event loop in
[chapter 11](visual-effects.md#sdl-creates-the-window) (before that, we used
`tkinter.mainloop`).

Implement the `Task` and `TaskQueue` classes. A `Task` encapsulates some code to
run in the form of a function, plus arguments to that function.[^task-notes] A
`TaskQueue` is simply a first-in-first-out list of `Task`s.

[^task-notes]: In `Task`, we're using the varargs syntax for Python, allowing
any number of arguments to be passed to the task. We're also using Python's
`__call__` builtin method. It is called when an object is called as if it's a
function. The Python code `Task()()` will constructs a `Task` and then "call"
(run) it.

``` {.python}
class Task:
    def __init__(self, task_code, *args):
        self.task_code = task_code
        self.args = args
        self.__name__ = "task"

    def __call__(self):
        self.task_code(*self.args)
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

Also define a new `TaskRunner` class to manage the task queues and run them. It
will have a `TaskQueue`, a method to add a `Task`, and a method to run once
through the event loop. Implement a simple scheduling heuristic in
`run_once` that executes one task each time through, if there is one to run.

``` {.python expected=False}
class TaskRunner:
    def __init__(self):
        self.tasks = TaskQueue()

    def schedule_task(self, callback):
        self.tasks.add_task(callback)

    def run_once(self):
        if self.tasks.has_tasks():
            task = self.tasks.get_next_task()
            task()
```

Now we're ready to move script loading for a `Tab` onto a
`TaskRunner`.[^event-handlers-later] Add the `TaskRunner` to `Tab` and, instead
of running a script synchronously, schedule it:

[^event-handlers-later]: We'll move script event handlers to a task later.

``` {.python expected=False}
class Tab:
    def __init__(self):
        self.task_runner = TaskRunner()

    def run_script(self, url, body):
        try:
            print("Script returned: ", self.js.run(body))
        except dukpy.JSRuntimeError as e:
            print("Script", url, "crashed", e)

    def load(self):
        # ...

        for script in scripts:
            # ...
            header, body = request(script_url, url)
            self.task_runner.schedule_task(
                Task(self.run_script, script_url, body))
```

Now we just need to modify the main event loop to run the task runner each time,
in case there is a script task to execute:

``` {.python expected=False}
if __name__ == "__main__":
    # ...
    while True:
        while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            # ...
            browser.tabs[browser.active_tab].task_runner.run_once()
```

That's it! Now our browser will not run scripts until after `load` has completed
and the event loop comes around again.

Before continuing, let's consider why this change is interesting. It used to be
that we had no choice but to eval scripts right away just as they were loaded.
But now it's pretty clear that we have a lot more control over when to run
scripts. For example, it's easy to make a change to `TaskRunner` to only run
one script per second, or to not run them at all during page load, or when a
tab is not the active tab. This flexibility is quite powerful, and we can use it
without having to dive into the guts of a `Tab` or how it loads web pages---all
we'd have to do is implement a new `TaskRunner` heuristic.

Example: setTimeout
===================

Now for the fun part I promised. Let's implement the
[`setTimeout`][settimeout] JavaScript API, which provides a way to run
a function a given number of milliseconds from now. In terms of the JavaScript
and Python communication, it'll use an approach with handles, similar to the
`addEventListener` code we added in [Chapter 9](scripts.md#event-handling).
The *new* part will be our first use of Python threads.

[settimeout]: https://developer.mozilla.org/en-US/docs/Web/API/setTimeout

We'll very soon have a lot more use for threads; for now all you need to know is
that the `threading` module allows you to create threads and run code on them
now or at a time specified in the future. To use them, start by adding an import
for that module:

``` {.python}
import threading
```

The `threading` module has a class  called `Timer`. This class lets you run a
callback at a specified time in the future, on a new
[Python thread][python-thread]. It takes two parameters: a time delta in seconds
from now, and a function to call when that time expires. The following code will
run `func` 10 seconds in the future on a new thread:

[python-thread]: https://docs.python.org/3/library/threading.html

``` {.python expected=False}
threading.Timer(10, func).start()
```

Now implement `setTimeout` on top of this functionality. In the JavaScript
runtime, add a new internal handle for each call to `setTimeout`, and store the
mapping between handles and callback functions in a global object called
`SET_TIMEOUT_REQUESTS`. When the timeout occurs, Python will call
`__runSetTimeout` and pass the handle as an argument.

``` {.javascript file=runtime}
SET_TIMEOUT_REQUESTS = {}

function setTimeout(callback, time_delta) {
    var handle = Object.keys(SET_TIMEOUT_REQUESTS).length;
    SET_TIMEOUT_REQUESTS[handle] = callback;
    call_python("setTimeout", handle, time_delta)
}

function __runSetTimeout(handle) {
    var callback = SET_TIMEOUT_REQUESTS[handle]
    delete SET_TIMEOUT_REQUESTS[handle];
    callback();
}
```

On the Python side, add a binding for `setTimeout` and an implementation that
starts a `threading.Timer`. However, we have to be careful here, since in the
code below, `run_callback` will run *on a different Python thread than the
current one*. So we can't just call `evaljs` directly, or we'll end up with
JavaScript running on two Python threads at the same time, which is not
ok.[^js-thread]

This is easy to fix by using the `TaskRunner` you already implemented: instead
of running the script right away, schedule a task to do it later, when the
other thread is free. Here's the code:

[^js-thread]: JavaScript is not a multi-threaded programming language.
It's possible on the web to create [workers] of various kinds, but they
all run independently and communicate only via special message-passing APIs.

[workers]: https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API

``` {.python}
class JSContext:
    def __init__(self, tab):
        # ...
        self.interp.export_function("setTimeout",
            self.setTimeout)

    def setTimeout(self, handle, time):
        def run_callback():
            self.tab.event_loop.schedule_task(
                Task(self.interp.evaljs,
                    "__runSetTimeout({})".format(handle)))

        threading.Timer(time / 1000.0, run_callback).start()
```

That's it! Your browser now supports running asynchronous JavaScript tasks.

Except there is a bug in this code: it doesn't account for the fact that
the first thread and the timer thread run concurrently, and there is therefore
no guarantee that one callback that adds a task via `schedule_task` will not be
interleaved with code on the other thread trying to read the task queue,
leading to a [race condition](https://en.wikipedia.org/wiki/Race_condition)
bug and nondeterministic results.

This bug is easily fixed by use of a `threading.Lock` object. Before reading
from or writing to a data structure shared across threads, acquire the lock;
after you're done, release it.^[The `blocking` parameter to `acquire` indicates
whether the thread should wait for the lock to be available before continuing;
in this chapter you'll always set it to true. (When the thread is waiting, it's
said to be *blocked*.)] The code changes in `TaskRunner` are pretty easy---just
be careful to not forget to release the lock, and hold it for the minimum time
possible, so as to maximize thread parallelism. That's why the code releases
the lock before calling `task`: after the task has been removed from the queue,
it can't be accessed by another thread.

``` {.python expected=False}
class TaskRunner:
    def __init__(self):
        # ...
        self.lock = threading.Lock()

    def schedule_task(self, callback):
        self.lock.acquire(blocking=True)
        self.tasks.add_task(callback)
        self.lock.release()

    def run_once(self):
        self.lock.acquire(blocking=True)
        task = None
        if self.tasks.has_tasks():
            task = self.tasks.get_next_task()
        self.lock.release()
        if task:
            task()
```

::: {.further}
Event loops often map 1:1 to CPU threads within a single CPU process, but
this is not required. For example, multiple event loops could be placed together
on a single CPU thread with yet another scheduler on top of them that
round-robins between them. It's useful to distinguish between: conceptual
events, event queues and dependencies between them; and their implementation in
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
All of these interactions require rendering. If you want to make those
interactions faster and smoother, the very first think you have to do is
carefully optimize the rendering pipeline.

The main event loop of a web page in a browser is called the *rendering event
loop*. An idealized rendering event loop looks like this:


``` {.python expected=False}
# This is the rendering event loop we want.
while True:
    while there_is_enough_time():
        run_a_task_from_a_task_queue()
    run_rendering_pipeline()
```

The way the loop is written implies that the rendering pipeline is its own task.
And it's "ideal" because separating rendering into its own task will allow us
to optimize it and spread it across multiple threads.^[Here
`run_rendering_pipeline` is made to look like it's all on the main event loop,
but all the parts of it that are after layout are invisible to web page
authors, so we'll be able to optimize them later on into a second event loop
on another thread.]

But right now, the rendering pipeline in our browser is not a task at
all---it's hidden in various subroutines of other tasks in the event loop.

``` {.python expected=False}
# This is what our browser currently does.
while True:
    run_a_task_from_a_task_queue() # Might do some rendering.
```

We'll need to fix that, but first let's figure out how long "enough time" in the
"ideal" loop should be. This was discussed in Chapter 2, which introduced the
[animation frame budget](graphics.md#framebudget), The animation frame budget
is the amount of time allocated to re-draw the screen after an something has
changed. It's typically about 16ms, in order to draw at 60Hz (60 * 16.66ms ~
1s), and matches the refresh rate of most displays. This means that each
iteration through the `while` loop should ideally complete in at most 16ms.

It also means that the browser should not run the `while` loop faster than that,
even if the CPU is up to it, because there is no point---the screen can't keep
up anyway. For this reason, `16ms` is not just an animation frame budget but
also a desired rendering *cadence*. If an iteration of the `while` loop
finishes faster than `16ms`, the browser should wait a bit before the next
iteration.

Therefore, let's use 16ms as the definition of "enough time":

``` {.python}
REFRESH_RATE_SEC = 0.016 # 16ms
```

Asynchronous rendering
======================

In order to separate rendering from other tasks and make it into a proper
pipeline, let's make it asynchronous. Instead of updating rendering right away,
the browser should set *dirty bits* (a fancy name for a boolean state variable)
indicating that a particular part of the pipeline needs updating. Then when the
pipeline is run, it will run the parts indicated by the dirty bits. We'll also
need some way of
*scheduling* the rendering pipeline to be updated at a given time in the
future.

First, add one dirty bit to `Tab`:

* `needs_pipeline_update`, indicating that
the pipeline needs to be re-run.

And two to `TaskRunner`:

* `display_scheduled`, indicating that a rendering task was already scheduled
via a `threading.Timer` (this avoids double-running a timer unnecessarily).
* `needs_animation_frame`, indicating that the event loop should
run the pipeline ASAP.

Add methods to set the dirty bits and use a `threading.Timer`  as
needed to schedule future renders.

``` {.python expected=False}
class Tab:
    def __init__(self, browser):
        # ...
        self.task_runner = TaskRunner(self)
        self.needs_pipeline_update = False

    def set_needs_pipeline_update(self):
        self.needs_pipeline_update = True
        self.task_runner.schedule_animation_frame()


class TaskRunner:
    def __init__(self, tab):
        # ...
        self.tab = tab
        self.display_scheduled = False
        self.needs_animation_frame = False

    def schedule_animation_frame(self):
        def callback():
            self.lock.acquire(blocking=True)
            self.display_scheduled = False
            self.needs_animation_frame = True
            self.lock.release()
        self.lock.acquire(blocking=True)
        if not self.display_scheduled:
            threading.Timer(REFRESH_RATE_SEC, callback).start()
        self.lock.release()
```
 
Also, rename `render` to `run_rendering_pipeline`, and add a new
`run_animation_frame` method that runs the pipeline and calls the other
rendering pipeline stages on `Browser` via a new `raster_and_draw`
method.

``` {.python expected=False}
class Tab:
    def __init__(self, browser):
        self.browser = browser

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

class Browser:
    def raster_and_draw(self):
        self.raster_chrome()
        self.raster_tab()
        self.draw()
```

The last piece is to actually call `run_animation_frame` from somewhere; at the
moment all we're doing is setting `needs_animation frame`. The place to put
it is in `run_once`, of course:

``` {.python expected=False}
class TaskRunner:
    # ...
    def run_once():
        # ...
        lock.acquire(blocking=True)
        needs_animation_frame = self.needs_animation_frame
        lock.release()
        if needs_animation_frame:
            self.tab.run_animation_frame()
```

Rendering is now async and scheduled according to the desired cadence.

Let's now take advantage of this new asynchronous technology by replacing all
cases where the rendering pipeline is computed synchronously with
`set_needs_pipeline_update`. Here is `load`, for example:[^more-examples]

[^more-examples]: There are more of them; you should fix them all.

``` {.python}
class Tab:
    def load(self, url, body=None):
        # ...
        self.set_needs_pipeline_update()
```

Now our browser can run rendering in an asynchronous, scheduled way on the event
loop!

But along the way we lost some performance. We're now always calling
`raster_and_draw` instead of only when needed. A dirty bit called
`needs_raster_and_draw` on `Browser` can fix most of this. Wherever it used to
call `raster_chrome`, `raster_tab` or `draw`  directly, now the browser should
set the dirty bit.^[Note that this will not get back some of the same
performance we had at the end of
[chapter 11](visual-effects.md#browser-compositing), where the browser only ran
raster and draw when needed. I've left this as an exercise.]

``` {.python} 
class Browser:
    def __init__(self):
        # ...
        self.needs_raster_and_draw = False

    def set_needs_raster_and_draw(self):
        self.needs_raster_and_draw = True

    def raster_and_draw(self):
        if not self.needs_raster_and_draw:
            return
        # ...
        self.needs_raster_and_draw = False

```

Here's the change to `handle_click` to set the dirty bit instead of calling
`raster_chrome` or `raster_tab` directly:

``` {.python expected=False}
class Browser:
    def handle_click(self, e):
        if e.y < CHROME_PX:
            # ...
            self.set_needs_raster_and_draw()
        else:
            # ...
            self.set_needs_raster_and_draw()
        self.tabs[self.active_tab].set_needs_animation_frame()
```

and `handle_down`:^[And so on, for all the call sites.]

``` {.python}
class Browser:
    def handle_down(self):
        # ...
        self.set_needs_raster_and_draw()
```

::: {.further}
The `needs_raster_and_draw` dirty bit is not just for making the browser a
bit more efficient. Later in the chapter, we'll move raster and draw to another
thread. If that bit was not there, then that thread would cause very erratic
behavior when animating. Once you've read the whole chapter and implemented
that thread, try removing this dirty bit and see for yourself!
:::

Scripts and rendering
=====================

Scripts are not just just for tasks unrelated to rendering. In fact, many
script tasks are there to update rendering state in the DOM after a state
change of the application (perhaps caused by an input event, or new information
downloaded from the server). To facilitate this, browsers have the
`requestAnimationFrame` JavaScript API. It's used like this:

``` {.javascript expected=False}
/* This is JavaScript */
function callback() {
    console.log("I was called!");
}
requestAnimationFrame(callback);
```

This code will do two things: request an *animation frame* task to be scheduled
on the event loop (i.e. `Tab.run_animation_frame`, the one you already
implemented in the previous section) and call `callback` *at the beginning* of
that rendering task, before any browser rendering code. This is super useful to
web page authors, as it allows them to do any setup work related to rendering
just before it occurs. The implementation of this JavaScript API is
straightforward:

* Add a new dirty bit to `Tab` and code to call the JavaScript
callbacks during the next animation frame:

``` {.python expected=False}
class Tab:
    def __init__(self, browser):
        self.needs_raf_callbacks = False

    def request_animation_frame_callback(self):
        self.needs_raf_callbacks = True
        self.task_runner.schedule_animation_frame()

    def run_animation_frame(self):
        if self.needs_raf_callbacks:
            self.needs_raf_callbacks = False
            self.js.interp.evaljs("__runRAFHandlers()")

        self.run_rendering_pipeline()
        browser.raster_and_draw()
```

* Add the interface to JSContext:

``` {.python}
class JSContext:
    def __init__(self, tab):
        # ...
        self.interp.export_function("requestAnimationFrame",
            self.requestAnimationFrame)

    def requestAnimationFrame(self):
        self.tab.request_animation_frame_callback()
```

* Extend the JavaScript runtime, once again using handles:

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

Now let's take a deeper look at what `run_animation_frame` does:

1. Reset `needs_raf_callbacks` to false.
2. Call the JavaScript callbacks.
3. Run the rendering pipeline.

Look a bit more closely at steps 1 and 2. Would it work to run step 1 *after*
step 2? The answer is no, but the reason is subtle: it's because the JavaScript
callback code could call `requestAnimationFrame`. If this happens
during such a callback, the spec says that a *second*  animation frame should
be scheduled (and 16ms further in the future, naturally). If the order of
operations had been different, it wouldn't correctly schedule another animation
frame.

 Likewise, the runtime JavaScript needs to be careful to copy the
 `RAF_LISTENERS` array to a temporary variable and then clear out
 ``RAF_LISTENERS``, so that it can be re-filled by any new calls to
 `requestAnimationFrame`.

This situation may seem like a corner case, but it's actually very important, as
this is how JavaScript can run an *animation*. Let's
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

``` {.python file=server replace=eventloop/eventloop12}
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

What if we ran raster and draw *in parallel* with the main thread, by using CPU
parallelism? After all, they take as input only the display list and not the
DOM. That sounds fun to try, but before adding such complexity, let's
instrument the browser and measure how much time is really being spent in
raster and draw.^[Pro tip: always measure before optimizing. You'll often
be surprised at where the bottlenecks are.]

Add a simple class measuring time spent:

``` {.python}
class Timer:
    def __init__(self):
        self.time = None

    def start(self):
        self.time = time.time()

    def stop(self):
        result = time.time() - self.time
        self.time = None
        return result
```

Count the total time spent in the two categories. We'll also need a
`handle_quit` hook in `Tab`, called from `Browser`, to print out the `Tab`
rendering time.

``` {.python}
class Tab:
        # ...
        self.time_in_style_layout_and_paint = 0.0
        self.num_pipeline_updates = 0

    def run_rendering_pipeline(self):
        # ...
        if self.needs_pipeline_update:
            timer = Timer()
            timer.start()
            style(self.nodes, sorted(self.rules,
                key=cascade_priority))
            self.document = DocumentLayout(self.nodes)
            self.document.layout()
            self.display_list = []
            self.document.paint(self.display_list)
            # ...
            self.time_in_style_layout_and_paint += timer.stop()
            self.num_pipeline_updates += 1

    def handle_quit(self):
        print("""Time in style, layout and paint: {:>.6f}s
    ({:>.6f}ms per pipeline run on average;
    {} total pipeline updates)""".format(
            self.time_in_style_layout_and_paint,
            self.time_in_style_layout_and_paint / \
                self.num_pipeline_updates * 1000,
            self.num_pipeline_updates))
        # ...
```

``` {.python}
class Browser:
    def __init__(self):
        self.time_in_raster = 0
        self.time_in_draw = 0
        self.num_raster_and_draws = 0

    def raster_and_draw(self):
        if not self.needs_raster_and_draw:
            return
        self.num_raster_and_draws += 1

        raster_timer = Timer()
        raster_timer.start()
        self.raster_chrome()
        self.raster_tab()
        self.time_in_raster += raster_timer.stop()

        draw_timer = Timer()
        draw_timer.start()
        self.draw()
        self.time_in_draw += draw_timer.stop()
        self.needs_raster_and_draw = False

    def handle_quit(self):
        print("""Time in raster: {:>.6f}s
    ({:>.6f}ms per raster run on average;
    {} total rasters)""".format(
            self.time_in_raster,
            self.time_in_raster / \
                self.num_raster_and_draws * 1000,
            self.num_raster_and_draws))
        print("""Time in draw: {:>.6f}s
    ({:>.6f}ms per draw run on average;
    {} total draw updates)""".format(
            self.time_in_draw,
            self.time_in_draw / self.num_raster_and_draws * 1000,
            self.num_raster_and_draws))
```

Now fire up the server and navigate to `/count`.^[The full URL will probably be
`http://localhost:8000/count`] When it's done counting, click the close button
on the window. The browser will print out the total time spent in each
category. When I ran it on my computer, it said:

Time in raster: 1.379575s
    (13.659154ms per raster run on average;
    101 total rasters)
Time in draw: 2.961407s
    (29.320861ms per draw run on average;
    101 total draw updates)
Time in style, layout and paint: 2.192260s
    (21.922598ms per pipeline run on average;
    100 total pipeline updates)

Over a total of 100 frames of animation, the browser spent about 50ms
rastering per frame,[^raster-draw] and 30ms drawing. That's a lot, and certainly
greater than our 16ms time budget.

On the other hand, the browser spent about 20ms per animation frame in the other
phases, which is also a lot. We'll see how to optimize that in
a future chapter.

Based on these timings, the first thing to try is optimizing
draw. I profiled it in more depth, and found that each of the
surface-drawing-into-surface steps (of which there are three) take a
significant amount of time.[^profile-draw] (I told you that
[optimizing surfaces](visual-effects.md#optimizing-surface-use) was important!) 

But even if those surfaces were optimized (not such an easy feat), raster is
still very expensive. So we should see a win by running raster and draw on a
parallel thread.

[^profile-draw]: I encourage you to do this profiling, to see for yourself.

[^raster-draw]: When I first wrote this section of the chapter, I was surprised
at how high the raster and draw time was, so I went back and added the separate
draw timer that you see in the code above. Profiling your code often yields
interesting insights!

::: {.further}
The best way to optimize `draw` is to perform raster and draw on the GPU (and
modern browsers do this), so that the draws can happen in parallel in GPU
hardware. Skia also supports this, so you could try it. But raster and draw
sometimes really do take a lot of time on complex pages, even
with the GPU. So rendering pipeline parallelism is a performance win regardless.
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

Now load the page and hold down the down-arrow button. Observe how inconsistent
and janky the scrolling is. Compare with no artificial delay, which is pleasant
to scroll.

Browsers can and do optimize their JavaScript engines to be as fast as possible,
but this has its limits. So the only way to keep the browser
guaranteed-responsive is to run key interactions in parallel with JavaScript.
Luckily, it's pretty easy to use the raster and draw thread we're planning
to *also* scroll and interact with browser chrome.

The browser thread
==================

This new thread will be called the *browser thread*.[^also-compositor] The
browser thread will be for:

[^also-compositor]: This thread is similar to what modern browsers often call
the *compositor thread*.

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
* `setTimeout` callbacks

[^main-thread-name]: Here I'm going with the name real browsers often use. A
better name might be the "JavaScript" thread (or even better, the "DOM"
thread, since JavaScript can sometimes run on [other threads][webworker]).

[webworker]: https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API

In other words: all code in `Browser` will run on the browser thread, and all
code in `Tab` and `JSContext` will run on the existing thread.

The thread that already exists (the one started by the Python interpreter
by default) will be the browser thread, and we'll make a new one for
the main thread. Let's add more code to the `TaskRunner` class to make it
into a complete event loop, and then rename it to `MainThreadEventLoop`.

The two threads will communicate by reading and writing shared data structures
(and use `threading.Lock` objects to prevent race conditions, just like with
`TaskRunner`). `MainThreadEventLoop` will be the only class allowed to call
methods on `Tab` or `JSContext`.

`MainThreadEventLoop` will add a thread object called `main_thread`, using the
`threading.Thread` class. The constructor for a `Thread` takes a `target`
argument indicating what function to execute on the thread once it's started.
Calling `start` will begin the thread. This will execute the target function
(`run`, in our case; rename `run_once` for this purpose), which will execute
forever, or until the function quits. The need to quit is is indicated by the
`needs_quit` dirty bit.

The main thread event loop is `run`.

``` {.python}
class MainThreadEventLoop:
    def __init__(self, tab):
        # ...
        self.main_thread = threading.Thread(target=self.run, args=())
        self.needs_quit = False

    def set_needs_quit(self):
        self.lock.acquire(blocking=True)
        self.needs_quit = True
        self.lock.release()

    def start(self):
        self.main_thread.start()    

    def run(self):
        while True:
            needs_quit = self.needs_quit
            if needs_quit:
                return
            # ...
```

In `run`, implement a simple event loop scheduling strategy that runs one
task per loop.[^not-ideal]

[^not-ideal]: This is not quite the "ideal" loop described at the beginning
of the chapter, but I hope it's clear that it would be easy to change strategies
to prioritize rendering.

``` {.python}
class MainThreadEventLoop:
    def run(self):
        while True:
            task = None
            self.lock.acquire(blocking=True)
            if self.tasks.has_tasks():
                task = self.tasks.get_next_task()
            self.lock.release()
            if task:
                task()
```

This works, but is wasteful of the CPU. Even if there are no
tasks, the thread will keep looping over and over. Let's add a way for the
thread to go to sleep once all the queues are empty, until they have something
in them again. The way to "sleep until there is a task" is via a *condition
variable*.

Condition variables are a way for one thread to block until it has been notified
by another thread that some condition has become true.[^threading-hard]
Condition variables allow a thread not to run an infinite
loop and use up a lot of CPU when there is nothing to
do.[^browser-thread-burn] Instead, the `while True` loop in `run` should only
continue if there is actually a task to execute.

Add a `condition.wait()` call to the run loop (meaning: wait until there is a task
to run), and `condition.notifyAll()` (meaning: notify the run loop that a task
has been added) to all the places where tasks are added. Notice that
`notify_all` can only be called when the lock is held, and does *not* release
the lock. `wait`, on the other hand, releases the lock when it goes to sleep
and re-acquires it automatically when it awakens.

``` {.python}
class MainThreadEventLoop:
    def __init__(self, tab):
        self.condition = threading.Condition(self.lock)

    def schedule_task(self, callback):
        # ...
        self.condition.notify_all()
        self.lock.release()

    def set_needs_quit(self):
        # ...
        self.condition.notify_all()
        self.lock.release()

    def run(self):
        while True:
            # ...

            self.lock.acquire(blocking=True)
            if not self.tasks.has_tasks() and \
                not self.needs_quit:
                self.condition.wait()
            self.lock.release()
```

[^browser-thread-burn]: At the moment, the browser thread's `while True` loop
does just this, but we need not do it for the main thread. (It appears there
is not a way to avoid this in SDL at present.)

[^threading-hard]: Threading and locks are hard, and it's easy to get into a
deadlock situation. Read the [documentation][python-thread] for the classes
you're using very carefully, and make sure to release the lock in all the right
places. For example, `condition.wait()` will re-acquire the lock once it has
been notified, so you'll need to release the lock immediately after, or else
the thread will deadlock in the next while loop iteration.

Note that each `Tab` owns a `MainThreadEventLoop`.[^one-per-tab]
And since we'll be copying the display list across threads and not a canvas,
the focus painting behavior needs to become a new `DrawLine` canvas command:

[^one-per-tab]: That means there will be one main thread per `Tab`, and even
tabs that are not currently shown will be able to run tasks in the background.

``` {.python}
class Tab:
    def __init__(self, browser):
        self.event_loop = MainThreadEventLoop(self)
        self.event_loop.start()

    def run_rendering_pipeline(self):
        # ...
        if self.needs_pipeline_update:
            # ...
            self.document.paint(self.display_list)
            if self.focus:
                obj = [obj for obj in tree_to_list(self.document, [])
                       if obj.node == self.focus][0]
                text = self.focus.attributes.get("value", "")
                x = obj.x + obj.font.measureText(text)
                y = obj.y
                self.display_list.append(
                    DrawLine(x, y, x, y + obj.height))
        # ...
```

Here's `DrawLine`:

``` {.python}
class DrawLine:
    def __init__(self, x1, y1, x2, y2):
        self.rect = skia.Rect.MakeLTRB(x1, y1, x2, y2)
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def execute(self, canvas):
        draw_line(canvas, self.x1, self.y1, self.x2, self.y2)
```

The `Browser` will also schedule tasks on the main thread. But now it's not
safe for any methods on `Tab` to be directly called by `Browser`, because
`Tab` runs on a different thread. All requests must be queued as tasks on the
`MainThreadEventLoop`.

Likewise, `Tab` can't have direct access to the `Browser`. But the only
method it needs to call on `Browser` is `raster_and_draw`. We'll add a new
`commit` method on `Browser` that will copy state from the main thread to the
browser thread. Then the browser won't have to depend on any main thread
data structures in order to raster, draw and scrolll.

``` {.python expected=False}
class Tab:
    def __init__(self, browser):
        # ...
        self.browser = browser

    def run_animation_frame(self):
        self.run_rendering_pipeline()
        # ...
        self.browser.commit(
            self.url, self.scroll,
            document_height,
            self.display_list)

```

In `Browser`:

``` {.python}
class Browser:
    def __init__(self):
        self.url = None
        self.scroll = 0

    def commit(self, url, scroll, tab_height, display_list):
        self.lock.acquire(blocking=True)
        if url != self.url or scroll != self.scroll:
            self.set_needs_raster_and_draw()
        self.url = url
        if scroll != None:
            self.scroll = scroll
        self.active_tab_height = tab_height
        self.active_tab_display_list = display_list.copy()
        self.set_needs_raster_and_draw()
        self.lock.release()
```

Note that `commit` will acquire a lock on the browser thread before doing
any of its work, because all of the inputs and outputs to it are cross-thread
data structures.[^fast-commit]

But we're not done. We need to have the *browser thread* determine the cadence
of animation frames, *not* the main thread. The reason is simple: there is no
point to running the front half of the rendering pipeline faster than it can be
drawn to the screen on the browser thread.

``` {.python}
class Tab:
    def set_needs_pipeline_update(self):
        self.needs_pipeline_update = True
        self.browser.set_needs_animation_frame()

    def request_animation_frame_callback(self):
        self.needs_raf_callbacks = True
        self.browser.set_needs_animation_frame()
```

``` {.python}
class Browser:
    def set_needs_animation_frame(self):
        self.lock.acquire(blocking=True)
        self.needs_animation_frame = True
        self.lock.release()

```

Let's now finish plumbing the animation frame dirty bit to `Browser`. We'll
store the bit, and check for it each time through the browser's event loop.
This will be the trigger for actually scheduling an animation frame back on the
main thread. This completes the loop: now the main thread will request that the
browser thread schedule a task back on the main thread 16ms in the future).

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.needs_animation_frame = False

    def set_needs_animation_frame(self):
        self.needs_animation_frame = True

    def schedule_animation_frame(self):
        if not self.needs_animation_frame:
            return
        self.needs_animation_frame = False

        def callback():
            self.lock.acquire(blocking=True)
            self.display_scheduled = False
            scroll = self.scroll
            active_tab = self.tabs[self.active_tab]
            self.lock.release()
            active_tab.event_loop.schedule_task(
                Task(active_tab.run_animation_frame, scroll))
        self.lock.acquire(blocking=True)
        if not self.display_scheduled:
            if USE_BROWSER_THREAD:
                threading.Timer(REFRESH_RATE_SEC, callback).start()
            self.display_scheduled = True
        self.lock.release()
```

``` {.python}
# ...

while True:
    if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
        # ...
    browser.raster_and_draw()
    browser.schedule_animation_frame()
```

[^fast-commit]: `commit` is the one time when both threads are both "stopped"
simultaneously---in the sense that neither is running a different task at the
same time. For this reason commit needs to be as fast as possible, so as to
lose the minimum possible amount of parallelism and responsiveness.

Finally, let's modify methods on `Browser` to schedule various kinds
of main thread tasks. Here is `load`:

``` {.python}
class Browser:
    def schedule_load(self, url, body=None):
        active_tab = self.tabs[self.active_tab]
        active_tab.event_loop.schedule_task(
            Task(active_tab.load, url, body))
        self.set_needs_raster_and_draw()

    def load(self, url):
        new_tab = Tab(self)
        self.set_active_tab(len(self.tabs))
        self.tabs.append(new_tab)
        self.schedule_load(url)
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
        self.lock.acquire(blocking=True)
        if e.y < CHROME_PX:
             # ...
        else:
            self.focus = "content"
            active_tab = self.tabs[self.active_tab]
            active_tab.event_loop.schedule_task(
                Task(active_tab.click, e.x, e.y - CHROME_PX))
        self.lock.release()
```

The same logic holds for `keypress`:

``` {.python}
class Browser:
    def handle_key(self, char):
        self.lock.acquire(blocking=True)
        if not (0x20 <= ord(char) < 0x7f): return
        if self.focus == "address bar":
            # ...
        elif self.focus == "content":
            active_tab = self.tabs[self.active_tab]
            active_tab.event_loop.schedule_task(
                Task(active_tab.keypress, char))
        self.lock.release()
```

::: {.further}
Python is unfortunately not fully thread-safe. For this reason, it has a
[global interpreter lock][gil], which means that you can't truly run two Python
threads in parallel.[^why-gil]

This means that the *throughput* (animation frames delivered per second) of our
browser will not actually be greater with two threads. Even though the
throughput is not higher, the *responsiveness* of the browser thread is still
massively improved, since it often isn't blocked on JavaScript or the front
half of the rendering pipeline.

Another point: the global interpreter lock doesn't save us from race conditions
for shared data structures. In particular, the Python interpreter on a thread
may yield between bytecode operations at any time. So the locks we added are
still useful, because race conditions such as reading and writing sequentially
from the same Python variable and getting locally-inconsistent results
(because the other thread modified it in the meantime) are still possible. And
in fact, while debugging the code for this chapter, I encountered this kind of
race condition in cases where I forgot to add a lock; try removing some of the
locks from your browser to see for yourself!
:::

[^why-gil]: It's possible to turn off the global
interpreter lock while running foreign C/C++ code linked into a Python library.
Skia is thread-safe, but SDL may not be.


[gil]: https://wiki.python.org/moin/GlobalInterpreterLock

Threaded scrolling
==================

Two sections back we talked about how important it is to run scrolling on the 
browser thread, to avoid slow scripts. But right now, even though there
is a browser thread, scrolling still happens in a `Task` on the main thread.
Let's now make scrolling truly *threaded*, meaning it runs on the browser
thread in parallel with scripts and other main thread work.

Threaded scrolling is quite tricky to implement. The reason is that both the
browser thread *and* the main thread can affect scroll. For example, when
loading a new page, scroll is set to 0; when running `innerHTML`, the height of
the document could change, leading to a potential change of scroll offset to
clamp it to that height. What should we do if the two threads disagree about
the scroll offset?

The best policy is to respect the scroll offset the user last observed, unless
it's incompatible with the web page. In other words, use the browser thread
scroll, unless a new web page has loaded or the scroll exceeds the current
document height. Let's implement that.

The trickiest part is how to communicate a browser thread scroll offset to the
main thread, and integrate it with the rendering pipeline. It'll work like
this:

* When the browser thread changes scroll offset, store it in a `scroll` variable
  on the `Browser`, set `needs_raster_and_draw`, and schedule an animation
  frame. This will immediately apply the scroll offset to the screen (at the
  next time `raster_and_draw` is called from the browser thread event loop).
  Scheduling an animation frame is necessary only to notify the main thread
  that scroll was changed.

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.scroll = 0

    def handle_down(self):
        # ...
        self.scroll = scroll
        self.set_needs_raster_and_draw()
        self.lock.release()
        self.schedule_animation_frame()
```

The `set_active_tab` method is an interesting case, because it causes
scroll to be set back to 0, but we need the main thread to run in order
to commit a new display list for the other tab. That's why this method doesn't
call `set_needs_raster_and_draw`.

``` {.python}
class Browser:
    def set_active_tab(self, index):
        self.active_tab = index
        self.scroll = 0
        self.url = None
        self.schedule_animation_frame()
```

* When the browser thread decides to run the animation frame,^[Remember, it's
  the browser thread, not the main thread, that decides the cadence of
  animation frames.] pass the scroll as an argument to the `Task` that calls
  `Tab.run_animation_frame`. `Tab.run_animation_frame` will set the scroll
  variable on itself as the first step.

``` {.python}
class Tab:
    def run_animation_frame(self, scroll):
        self.scroll = scroll
        # ...

class Browser:
    def schedule_animation_frame(self):
        # ...
        def callback():
            self.lock.acquire(blocking=True)
            scroll = self.scroll
            active_tab = self.tabs[self.active_tab]
            self.lock.release()
            active_tab.event_loop.schedule_task(
                Task(active_tab.run_animation_frame, scroll))
        # ...
```

* When loading a new page in a `Tab`, override the scroll to 0. Do the same for
  cases when the document height causes scroll clamping. If either of these
  happened, note it in a new `scroll_changed_in_tab` variable on `Tab`.

``` {.python}
class Tab:
    def __init__(self, browser):
        # ...
        self.scroll_changed_in_tab = False

    def load(self, url, body=None):
        self.scroll = 0
        self.scroll_changed_in_tab = True

    def run_animation_frame(self, scroll):
        # ...
        self.run_rendering_pipeline()

        document_height = math.ceil(self.document.height)
        clamped_scroll = clamp_scroll(self.scroll, document_height)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_tab = True
        self.scroll = clamped_scroll
```

* When calling `commit`, only pass the scroll if `scroll_changed_in_tab` was
  set, and otherwise pass `None`. The commit will ignore the scroll if it is
  `None`.

``` {.python}
class Tab:
    def run_animation_frame(self, scroll):
        # ...
        self.browser.commit(
            self.url,
            clamped_scroll if self.scroll_changed_in_tab \
                else None, 
            document_height, self.display_list)
```

That was pretty complicated, but we got it done. Fire up the counting demo and
enjoy the newly smooth scrolling.

Now let's step back from the code for a moment and consider the full scope and
difficulty of scrolling in real browsers. It goes *way* beyond what we've
implemented here. Unfortunately, due to some of this complexity, threaded
scrolling is not always possible or feasible in real browsers. This means
that they need to support both threaded and non-threaded scrolling modes, and
all the complexity that entails.

In the best browsers today, there are two primary reasons why threaded scrolling
may fail to occur:

* Javascript events listening to a scroll. If the event handler
for the [`scroll`][scroll-event] event calls `preventDefault` on the first such
event (or via [`touchstart`][touchstart-event] on mobile devices), the scroll
will not be threaded in most browsers. Our browser has not implemented these
events, and so can avoid this situation.[^real-browser-threaded-scroll]

[scroll-event]: https://developer.mozilla.org/en-US/docs/Web/API/Document/scroll_event
[touchstart-event]: https://developer.mozilla.org/en-US/docs/Web/API/Element/touchstart_event

[^real-browser-threaded-scroll]: A real browser would also have an optimization
to disable threaded scrolling only if there was such an event listener, and
transition back to threaded as soon as it doesn't see `preventDefault` called.
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
synchronously wait for a network response to load the main HTML resource.
It then does the same thing for each subsequent *sub-resource request*, to load
style sheets and scripts. Arguably, there isn't a whole lot of point to making
the initial request asynchronous, because there isn't anything else for the
main thread to do in the meantime. But there is a pretty clear performance
problem with the script and style sheet requests: they pile up sequentially,
which means that there is a loading delay equal to the round-trip time to the
server, multiplied by the number of scripts and style sheets.

We should be able to send off all of the requests in parallel. Let's use an
async, threaded version of `request` to do that. For simplicity, let's use a
new Python thread for each resource. When a resource loads, the thread will
complete and we can parse the script or load the style sheet, as appropriate.
[^ignore-order]

Define a new `async_request` function. This will start a thread. The thread will
request the resource, store the result in `results`, and then return. The
thread object will be returned by `async_request`. It's expected that the
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
and only at the end `join` all of the threads created.

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
                "thread": async_request(
                    script_url, url, script_results)
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

        for async_req in async_requests:
            async_req["thread"].join()
            req_url = async_req["url"]
            if async_req["type"] == "script":
                self.event_loop.schedule_task(
                    Task(self.js.run, req_url,
                        script_results[req_url]['body']))
            else:
                self.rules.extend(
                    CSSParser(
                        style_results[req_url]['body']).parse())
```

Now our browser will parallelize loading sub-resources!

Next up is `XHMLHttpRequest`. We introduced this API in chapter 10, and
implemented it only as a synchronous API. But in fact, the synchronous
version of that API is almost useless for real websites,^[It's also a huge
performance footgun, for the same reason we've been adding async tasks
in this chapter!] because the whole point of using this API on a
website is to keep it responsive to the user while network requests are going
on.

Let's fix that. We'll make the following changes. There are a bunch of them, but they
are mostly about communicating back and forth with JavaScript.

* Allow `is_async` to be `true` in the constructor of `XMLHttpRequest` in the
runtime.
* Store a unique handle for each `XMLHttpRequest` object, analogous to how we
  used handles for `Node`s.
* Store a map from request handle to object.

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
```

* Add a new `__runXHROnload` method that will call the `onload` function
specified on a `XMLHttpRequest`, if any.
* Store the response on the `responseText` field, as required by the API.

``` {.javascript}
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

* Augment `XMLHttpRequest_send` to support async requests that use a thread
and a script task on `event_loop`.

``` {.python}
class JSContext:
    def XMLHttpRequest_send(
        self, method, url, body, is_async, handle):
        full_url = resolve_url(url, self.tab.url)
        if not self.tab.allowed_request(full_url):
            raise Exception("Cross-origin XHR blocked by CSP")

        def run_load():
            headers, out = request(
                full_url, self.tab.url, payload=body)
            handle_local = handle
            if url_origin(full_url) != url_origin(self.tab.url):
                raise Exception(
                    "Cross-origin XHR request not allowed")
            self.tab.event_loop.schedule_task(
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

Now let's try out this new async API by augmenting our counter javascript like
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
    out += "  Let's count up to 100!"
    out += "</div>";
    out += "<div>Output</div>"
    out += "<div>XHR</div>"
    # ...

def show_xhr():
    time.sleep(5)
    return "Slow XMLHttpRequest response!"
```

Load the counter page. You should see the counter going up, and then after
5 seconds, "Slow XMLHttpRequest response!" should appear onscreen. This
would not have been possible without an async request to `/xhr`.

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
APIs that can query style or layout state. For example, [`getComputedStyle`][gcs]
can't be implemented without the browser first computing style, and
[`getBoundingClientRect`][gbcr] needs layout.[^nothing-later] If a web page calls
one of these APIs, and style or layout is not up-to-date, then is has to be
computed synchronously, then and there. These computations are called
*forced style* or *forced layout*. The world "forced" refers to forcing the
 computation to happen right away, as opposed to possibly 16ms in the future if
 it didn't happen to be already computed. Because there are forced style and
 layout situations, browsers have to be able to do that work on the main thread
 if necessary.[^or-stall]

[gcs]: https://developer.mozilla.org/en-US/docs/Web/API/Window/getComputedStyle
[gbcr]: https://developer.mozilla.org/en-US/docs/Web/API/Element/getBoundingClientRect

 [^or-stall]: Or stall the compositor thread and ask it to do it synchronously,
 but that is generally a worse option because it'll jank scrolling.

[^servo]: The [Servo] rendering engine is sort of an exception. However, in that
case it's not that style and layout run on a different thread, but that they
attempt to take advantage of parallelism for faster end-to-end performance.

[Servo]: https://en.wikipedia.org/wiki/Servo_(software)

[^nothing-later]: There is no JavaScript API that allows reading back state
from anything later in the rendering pipeline than layout.

By analogy with web pages that don't `preventDefault` a scroll, is it a good
idea to try to optimistically move style and layout off the main thread for
cases when JavaScript doesn't force it to be done otherwise? Maybe, but even
setting aside this problem there are unfortunately other sources of forced
style and layout. One example is our current implementation of `click`. The
first line of this method forces a layout:

``` {.python}
class Tab:
    def click(self, x, y):
        self.run_rendering_pipeline()
        # ...
```

The call to `run_rendering_pipeline` is a forced layout. It's needed because
clicking needs to run hit testing, which in turn requires layout.

It's not impossible to move style and layout off the main thread
"optimistically", but here I outlined some of the reasons it's challenging. for
 browsers to do it. I expect that at some point in the future it will be
 achieved (maybe you'll be the one to do it?).

Summary
=======

This chapter explained in some detail the two-thread rendering system at the
core of modern browsers. The main points to remember are:

* The browser uses event loops, tasks and task queues to do work.

* The goal is to consistently generate frames to the screen at a 60Hz
cadence, which means a 16ms budget to draw each animation frame.

* The main thread runs an event loop for various tasks, including
JavaScript, style and layout. The rendering task is special, can include
special JavaScript `requestAnimationFrame` callbacks in it, and at the end
commits a display list to a second thread.

* The second thread is the browser thread. It draws the display list to the
screen and handles/dispatches input events, scrolls, and interactions with the
browser chrome.

* Threads are useful for other kinds of tasks, such as network loading.

* Forced style and layout makes it hard to fully isolate the rendering pipeline
from JavaScript.

Outline
=======

The complete set of functions, classes, and methods in our browser 
should now look something like this:

::: {.cmd .python .outline html=True}
    python3 infra/outlines.py --html src/lab12.py
:::

Exercises
=========

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

* *Networking thread*: Real browsers tend to have a separate thread for
   networking (and other I/O) instead of creating a one thread per request.
   Implement a third thread with an event loop and put all networking tasks
   (including HTML and script fetches) on it.

* *Fine-grained dirty bits*: at the moment, the browser always re-runs
the entire rendering pipeline if anything changed. For example, it re-rasters
the browser chrome every time (this is a performance regression as compoared
with the state at the end of chapter 11). Add in additional dirty bits for
raster and draw stages. (You can also try adding dirty bits for whether layout
needs to be run, but be careful to think very carefully about all the ways
this dirty bit might need to end up being set.)

* *Multi-tab scroll offsets*: our browser doesn't currently keep track of the
   scroll offset of each tab separately. That's why `set_active_tab`
   unconditionally sets it to zero. In a real browser, all the tabs would
   remember their scroll offset. Fix this.