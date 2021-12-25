---
title: Scheduling and Threading
chapter: 12
prev: visual-effects
next: skipped
...


Our browser now knows how to load a web page with HTTP and parse it into an
HTML tree & style sheets. It can also *render* the page, by constructing the
layout tree, computing styles on it, laying out its contents, and painting the
result to the screen. These rendering steps make up a basic
[*rendering pipeline*](https://en.wikipedia.org/wiki/Graphics_pipeline) for the
browser.[^rendering-pipeline]

[^rendering-pipeline]: Our browse's current rendering pipeline has 5 steps:
style, layout, paint, raster and draw.

But of course, there is more to web pages than just running the rendering
pipeline. There is keyboard/mouse/touch input, scrolling, interacting with
browser chrome, submitting forms, executing scripts, loading things off the
network, and so on. All of these are *tasks* that the browser executes.

In this chapter we'll see how to decouple the rendering pipeline from events.
This change allows us to best utilize the hardware capabilities of
modern computers---matching the screen refresh rate, and exploiting CPU
parallelism. We'll then be able to add threaded scrolling and 
browser chrome interactions, two key features of all modern browsers.

Task queues
===========

When the browser is free to do work, it finds the next *task* in line from one
of the queues and runs it; when it's done it repeats, and so on. A sequence of
related tasks is a *task queue*, and browsers have multiple tasks queues---which
queue a task goes into depends on which other tasks it depends on.

One or more task queues can be grouped together into a single, sequential
thread of execution.[^thread-process]
This thread has an *event loop* associated with it.[^event-loop] The job
of the event loop is to schedule events to happen according to the priorities
of the browser---to make sure it's responsive to the user, uses hardware
efficiently, 

[^thread-process]: You can think of these threads as mapping 1:1 to CPU threads
within a single process, but this is not required. For example, multiple event
loops could be placed together on a single thread with yet another scheduler on
top of them that round-robins between them. It's really useful to distinguish
between conceptual events, event queues and dependencies between them, and
their implementation in a computer architecture. This way, the browser
implementer (you!) has maximum ability to use more or less hardware parallelism
as appropriate to the situation---some devices have more [CPU cores][cores] than
others, or are more sensitive to battery power usage.

[cores]: https://en.wikipedia.org/wiki/Multi-core_processor


[^event-loop]: Event loops were also briefly touched on in
[chapter 2](graphics.md#eventloop), and we wrote our own event loop in
[chapter 11](visual-effects.md#sdl-creates-the-window) (before that, we used
`tkinter.mainloop`).

Let's implement a `Task` and a `TaskQueue` class. Then we can move all of the
event loop tasks into task queues later in the chapter.

A `Task` encapsulates some code to run in the form of a function, plus arguments
to that function. A `TaskQueue` is simply a first-in-first-out list of
`Task`s.

``` {.python}
class Task:
    def __init__(self, task_code, arg1=None, arg2=None):
        self.task_code = task_code
        self.arg1 = arg1
        self.arg2 = arg2
        self.__name__ = "task"

    def __call__(self):
        if self.arg2:
            self.task_code(self.arg1, self.arg2)
        elif self.arg1:
            self.task_code(self.arg1)
        else:
            self.task_code()
        # Prevent it accidentally running twice.
        self.task_code = None
        self.arg1 = None
        self.arg2 = None
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
```
(Note: in Python, `__call__` is a method that is called when an object is called
as if it's a function; for example via code like `Task()()`---this constructs
a `Task` and then "calls" it.)


Rendering pipeline tasks
========================

The most important task in a browser is the rendering pipeline---but not just
for the obvious reason that it's impossible to see web pages that aren't
rendered. Most of the time spent doing work in a browser is in rendering,
and *interactions* with the browser, such as scrolling, clicking and typing,
have a close relationship with rendering. If you want to make those
interactions faster and smoother, the very first think you have to do is
carefully optimize the rendering pieline.

Right now, the rendering pipeline in our browser is not a task at all---it's
spread across several subroutines of event handlers in the event loop. That's
no good, because it makes rendering much less efficient, and keeps us from
separating rendering from other event queues that don't depend directly on it.
The ideal rendering event loop looks like this:

``` {.python expected=False}
# This is the rendering event loop we want:
while True:
    while there_is_enough_time():
        run_a_task_from_a_task_queue()
    run_rendering_pipeline()
```

Whereas what we have at the moment is effectively this:

``` {.python expected=False}
# This is what our browser currently does:
while True:
    while there_is_enough_time():
        run_a_task_from_a_task_queue()
        run_rendering_pipeline()
```

Except that as I mentioned, it's even worse, due to the multiple subroutines:
`render`, `raster_chrome`, `raster_tab` and `draw`.
Each of these is run when we happen to know that the event handler changed
the inputs to rendering that caused those subroutines to do their work again.

We'll need to fix that, but first let's figure out how long "enough time" in the
above loop should be. This was first discussed in Chapter 2, which introduced
the [animation frame budget](graphics.md#framebudget), The animation frame
budget is the amount of time allocated to re-draw the screen after an something
has changed. The animation frame budget is typically about 16ms, in order to
draw at 60Hz (60 * 16.66ms ~ 1s), and matches the refresh rate of most
displays. This means that each iteration through the `while` loop should
ideally complete in at most 16ms.

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

In order to separate rendering from event handler tasks and make it into a
proper pipeline, we'll need to make it asynchronous. Instead of updating the
subroutines right away, we'll set *dirty bits* indicating that a particular
part of the pipeline needs updating. Then when the pipeline is run, we'll 
run the parts indicated by the dirty bits. We'll also need some way of
*scheduling* the rendering pipeline to be updated at a given time in the
future.

Start with schedule the update. You can do that by starting a new
[Python thread][python-thread] via the `threading.Timer` class, which takes two
parameters: a time delta from now, and a function to call when that time
expires. Put them in a `set_timeout` function:

[python-thread]: https://docs.python.org/3/library/threading.html

``` {.python}
def set_timeout(func, sec):     
    t = None
    def func_wrapper():
        func()
        t.cancel()
    t = threading.Timer(sec, func_wrapper)
    t.start()
```

Next, add a dirty bit `needs_pipeline_update` (plus `display_scheduled` to
avoid double-running `set_timeout` unnecessarily) to `Tab`, which means
"rendering needs to happen, and has been scheduled, but hasn't happened yet".
Combined with `set_timeout`, we can now implement async rendering in a `Tab`.
Also, rename `render` to `run_rendering_pipeline`, and
call the other rendering pipeline stages on `Browser` via a new
`raster_and_draw` method (which we'll implement shortly).

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
            style(self.nodes, sorted(self.rules, key=cascade_priority))
            self.document = DocumentLayout(self.nodes)
            self.document.layout()
            self.display_list = []
            self.document.paint(self.display_list)
            self.needs_pipeline_update = False
```

Now replace all cases where parts of the rendering pipeline were called with
`set_needs_animation_frame`, for example `load`:

Or `load`:

``` {.python}
class Tab:
    def load(self, url, body=None):
        # ...
        self.set_needs_animation_frame()
```

The `raster_and_draw` method will be where we add new dirty bits for whether the
active tab, browser chrome, or draw needs to happen. This will get us back the
same performance we had at the end of chapter 11, where the browser only
ran raster and draw when needed.^[also-tab]

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

Oh, andd we'll need to schedule an animation frame whenever any of those dirty
bits are set. This is easiest to add in `set_needs_draw`:

``` {.python expected=False}
class Browser:
    def set_needs_draw(self):
        # ...
        self.tabs[self.active_tab].set_needs_animation_frame()
```

And in each case where raster or draw were called previously, now set the
dirty bits, such as in `handle_click`, and also schedule an animation frame.
Note that scheduling an animation frame does *not* mean that
`run_rendering_pipeline` does all its expensive work, just that the task is
scheduled 16ms in the future.

``` {.python expected=False}
class Browser:
    def handle_click(self, e):
        if e.y < CHROME_PX:
            # ...
            self.set_needs_chrome_raster()
            self.tabs[self.active_tab].set_needs_animation_frame()
```
or `handle_down`:

``` {.python}
class Browser:
    def handle_down(self):
        # ...
        self.set_needs_draw()
```

Scripts in the event loop
=========================

In addition to event handlers, it's also of course possible for scripts to run
in the rendering event loop. In general, the rendering event loop can run any of
a wide variety of tasks, only some of which respond to input events. As we saw in
[chapter 9](scripts.md), the first way in which scripts can be run is that when
a `<script>` tag is inserted into the DOM, the script subsequently loads and
then runs. We can easily wrap all this in a `Task`, with a zero-second timeout,
like so:

``` {.python expected=False}
    for script in find_scripts(self.nodes, []):
        # ...
        header, body = request(script_url, url)
        set_timeout((0, Task(self.js.run, script, body)
```

Of course, scripts are not just for running straight through in one task, or
responding to input events. They can also schedule more events to be put on the
rendering event loop and run later. There are multiple JavaScript APIs in
browsers to do this, but for now let's focus on the one most related to
rendering: `requestAnimationFrame`. It's used like this:

``` {.javascript expected=False}
/* This is JavaScript */
function callback() {
    console.log("I was called!");
}
requestAnimationFrame(callback);
```

This code will do two things: request an "animation frame" task to be run on the
event loop, and call `callback` at the beginning of that task.  An animation
frame is the same thing as "run the rendering pipeline", and allows JavaScript
to run just before `run_rendering_pipeline`. The implementation of this
JavaScript API is straightforward: add a new dirty bit to `Tab` and code to
call the JavaScript callbacks when it's set, during the next animation frame.

``` {.python replace=browser/commit_func}
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

    def run_animation_frame(self):
        if self.needs_raf_callbacks:
            self.needs_raf_callbacks = False
            self.js.interp.evaljs("__runRAFHandlers()")

        self.run_rendering_pipeline()
        self.commit_func(self.url, self.scroll)
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

1. Reset the variables `needs_animation_frame` and `needs_raf_callbacks` to false.

2. Call the JavaScript callbacks.

3. Run the rendering pipeline.

Look a bit more closely at steps 1 and 2. Would it work to run step 1 *after*
step 2? The answer is no, but the reason is subtle: it's because the JavaScript
callback code could *once again* call `requestAnimationFrame`. If this happens
during such a callback, the spec says that a *second*  animation frame should
be scheduled (and 16ms further in the future, naturally). Likewise, the runtime
JavaScript needs to be careful to copy the `RAF_LISTENERS` array to a temporary
variable and then clear out ``RAF_LISTENERS``, so that it can be re-filled by
any new calls to `requestAnimationFrame`.

This situation may seem like a corner case, but it's actually very important, as
this is how JavaScript can run a 60Hz animation. Let's
try it out with a script that counts from 1 to 100, one frame at a time:

``` {.javascript expected=False}
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
    if (count < 100)
        requestAnimationFrame(callback);
    cur_frame_time = Date.now()
}
requestAnimationFrame(callback);
```

To make the above code work, you'll need this small addition to the runtime 
code:
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

Event loop speedup
==================

TODO: update/rewrte

To meet the desired rendering cadence of 60Hz, each of the 100 animation frames
is ideally separated by about a 16ms gap. Unfortunately, when I ran the script
script in out browser, I found that there were about *140ms* between
each frame. Looks like we have some work to do to get to 16ms!

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

And the long pole in the rendering pipeline in this case is Layout phase 1A,
followed by Paint and Drawing. These costs are due to changes to the element
tree resulting from setting ``innerHTML`` on the `#output` element. The
runRAFHandlers timing shows less than 1ms spent running actual JavaScript.
[^another-scenario]

[^another-scenario]: In other scenarios, it could easily occur that the slowest
part ends up being Style, Paint, or IdleTasks.  For example, Style could be
slow if the style sheet had a huge number of complex rules in it. If we're not
very careful in the implementation (or even if we are!) it could still be slow.
The only way to be sure is to profile the code; the true source of the slowdown
is sometimes not what you thought it was. The case in this chapter was a real
example---I was truly unsure of which part was slow, until I profiled it.

Of course, it could also be that `runRAFHandlers` is the slowest part. For example,
suppose we inserted the following busyloop into the callback, like so:

``` {.javascript expected=False}
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
part of the loop. This demonstrates, of course, that no matter how
cleverly we optimize the browser, it's always possible for JavaScript to
make it slow. Browser engineers can't rewrite
a site's JavaScript to be magically faster!

There are a few general techniques for optimizing the browser when encountering
situations like we've discussed so far:

1. *Do less work*: use a faster algorithm, perform fewer memory allocations
or function calls and branches, or skip work that is not necessary. The
optimization we worked out in [chapter 2](graphics.md#faster-rendering) to skip
painting for off-screen elements is a good example.

2. *Cache*: carefully remember what the browser already knows from the previous
animation frame, and re-compute only what is absolutely necessary for the next
one. An example is the partial layout optimizations in [chapter 10](reflow.md).

3. *Parallelize*: run tasks on more than one CPU thread or process. We haven't
seen an example of this yet, but will see one later in this chapter.

4. *Schedule*: when possible, delay tasks that can be done later in batches, or
break up work into smaller chunks and do them in separate animation frames. The
every-16ms animation frame task is a form of scheduling---it waits that long on
purpose to gather up rendering work queued in the meantime.[^not-much-queueing]

[^not-much-queueing]: There aren't a lot of great examples of scheduling yet in
this book's browser, and this chapter is already long. I've left some examples
to explore in the exercises.

Let's consider each class of optimization in turn.

Do less work & Cache
====================

TODO: update/rewrite

The Compositor thread
=====================

The second thread that runs drawing is often called the *compositor* thread.
It's so named because in a real browser it'll end up doing a lot more than
drawing to a canvas, but let's skip that part for now and focus on drawing.

To get the compositor thread working, we'll have to find a way to run tkinter
on a second thread, and communicate between the threads in a way that allows
them to do things in parallel. The first thing you should know is that tkinter
is *not* thread-safe, so it cannot magically parallelize for free. Instead we'll
have to carefully avoid using tkinter at all on the main thread, and move all
use of it to the compositor thread.

The approach we'll take is to call the thread we already have the compositor
thread, and add a new thread; this thread is usually called the *main* thread.
The main thread will run these kinds of tasks in our browser:

* JavaScript

* Browser-internal tasks like executing a page load

* Animation frames - `rAF` callbacks plus the rendering pipeline

 The compositor thread (the one with tkinter in it) will be in charge of:

* Scheduling an animation frame every 16ms

* Drawing to the screen after the rendering pipeline is done

* Listening to mouse and keyboard events

To do this we'll have to expand greatly on the implementation of an event loop,
because now we'll need to manage this event loop ourselves rather than using
tkinter for most of it.

Let's start the implementation by introducing a class `MainThreadRunner` that
encapsulates the main thread and its rendering event loop. The two threads will
communicate by writing to and reading from some shared data structures, and use
a `threading.Lock` object to prevent race conditions.[^python-gil]

[^python-gil]: Our browser code uses locks, because real multi-threaded programs
will need them. However, Python has a [global interpreter lock][gil], which
means that you can't really run two Python threads in parallel, so technically
these locks don't do anything useful in our browser. And this also means, of
course, that the real performance of our browser will not actually be faster
with two threads, unless work is offloaded to code that is not using Python
bytecodes.

[gil]: https://wiki.python.org/moin/GlobalInterpreterLock

``` {.python}
class MainThreadRunner:
    def __init__(self, tab):
        self.lock = threading.Lock()
        self.tab = tab
        self.needs_animation_frame = False
        self.main_thread = threading.Thread(target=self.run, args=())
        self.script_tasks = TaskQueue(self.lock)
        self.browser_tasks = TaskQueue(self.lock)

    def start(self):
        self.main_thread.start()        
```

It will have some methods to set the variables, such as:

``` {.python}
    def schedule_animation_frame(self):
        self.lock.acquire(blocking=True)
        self.needs_animation_frame = True
        self.lock.release()

    def schedule_script_task(self, script):
        self.script_tasks.add_task(script)
```

With accompanying edits to `TaskQueue` to add a lock:

``` {.python}
class TaskQueue:
    def __init__(self, lock):
        self.tasks = []
        self.lock = lock

    def add_task(self, task_code):
        self.lock.acquire(blocking=True)
        self.tasks.append(task_code)
        self.lock.release()

    def has_tasks(self):
        self.lock.acquire(blocking=True)
        retval = len(self.tasks) > 0
        self.lock.release()
        return retval

    def get_next_task(self):
        self.lock.acquire(blocking=True)
        retval = self.tasks.pop(0)
        self.lock.release()
        return retval
```

Its main functionality is in the `run` method, which implements a simple event
loop strategy that runs the rendering pipeline if needed, and also one browser
method and one script task, if there are any on those queues. It then sleeps for
1ms and checks again.

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

            time.sleep(0.001) # 1ms
```

The `run_animation_frame` method on `Browser` will run on the main thread. Since
`draw` is supposed to happen on the compositor thread, we can't run it as part
of the main thread rendering pipeline. Instead, we need to `commit` (copy) the
display list to the compositor thread, so that it can be drawn
later:[^fast-commit]

``` {.python}
class TabWrapper:
    def commit(self, url, scroll):
        self.browser.compositor_lock.acquire(blocking=True)
        if url != self.url or scroll != self.scroll:
            self.browser.set_needs_chrome_raster()
        self.url = url
        self.scroll = scroll
        self.browser.active_tab_height = math.ceil(self.tab.document.height)
        self.browser.active_tab_display_list = self.tab.display_list.copy()
        self.browser.set_needs_tab_raster()
        self.browser.compositor_lock.release()
```

[^fast-commit]: `commit` is the one time when both threads are both "stopped"
simultaneously---in the sense that neither is running a different task at the
same time. For this reason commit needs to be as fast as possible, so as to
lose the minimum possible amount of parallelism.

Other tasks
===========

Next up we'll move browser tasks such as loading to the main thread. Now that
we have `MainThreadRunner`, this is super easy! Whenever the compositor thread
needs to schedule a task on the main thread event loop, we just call
`schedule_browser_task`:

``` {.python}
class TabWrapper:
    def schedule_load(self, url, body=None):
        self.tab.main_thread_runner.schedule_browser_task(
            Task(self.tab.load, url, body))
        self.browser.set_needs_chrome_raster()
```

We can do the same for input event handlers, but there are a few additional
subtleties. Let's look closely at each of them in turn, starting with
`handle_click`. In most cases, we will need to [hit test]
(chrome.md#hit-testing) for which DOM element receives the click event, and
also fire an event that JavaScript can listen to. Since DOM computations and
JavaScript can only be run on the main thread, it seems we should just send the
click event to the main thread for processing. But if the click was *not*
within the web page window, we can handle it right there in the compositor
thread, and leave the main thread none the wiser:

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
            self.tabs[self.active_tab].schedule_click(e.x, e.y - CHROME_PX)
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

``` {.python}
class Browser:
    def handle_down(self):
        self.compositor_lock.acquire(blocking=True)
        if not self.active_tab_height:
            return
        max_y = self.active_tab_height - (HEIGHT - CHROME_PX)
        active_tab = self.tabs[self.active_tab]
        active_tab.schedule_scroll(min(active_tab.scroll + SCROLL_STEP, max_y))
        self.set_needs_draw()
        self.compositor_lock.release()
```

And we're done! Now we can reap the benefits of two threads working in parallel.
Here are the results:

    Average total compositor thread time (Draw and Draw Chrome): 4.8ms
    Average total main thread time: 4.4ms

This means that we've been able to save about half of the of main thread time.
With that time we can do other work, such as more JavaScript tasks, while in
parallel the draw operations happen. This kind of optimization is called 
*pipeline parallelization*.

Threaded interactions
=====================

All this work to create a compositor thread is not just to offload some of the
rendering pipeline. There is another, even more important, performance
advantage: any operation that does not require the main thread *cannot be slowed
down by it*. Look closely at the code we've written in the previous section to
handle input events---you'll see that in the following cases the main thread is
not involved at all:

* Interactions with browser chrome (if the click or keyboard event is not
targeted at the web page)

* Scrolling

These are *threaded interactions*---ones that don't need to run any code at all
on the main thread. No matter how slow the main thread rendering pipeline is, or
how slow JavaScript is (even if it's stuck in an infinite loop!), we can still
smoothly scroll the parts of it that are already in `draw_display_list`, and
type in the browser URL box.

In real browsers, the two examples listed above are *extremely* important
optimizations. Think how annoying it would be to type in the name of a new
website if the old one was getting in the way of your keystrokes because it was
dslow. Likewise, scrolling a web page with a lot of slow JavaScript is
sometimes painful unless the scrolling is threaded, even for relatively good
sites.

Unfortunately, threaded scrolling is not always possible or feasible. In the
best browsers today, there are two primary reasons why threaded scrolling may
fail to occur:

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
        self.tab.run_rendering_pipeline()
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
