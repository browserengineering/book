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
the infrastructure, and then try it out on some examples.

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

Implement the `Task` class. A `Task` encapsulates some code to
run in the form of a function, plus arguments to that function.[^task-notes]

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

Also define a new `TaskRunner` class to manage the task queues and run them. It
will have a list of `Task`s, a method to add a `Task`, and a method to run once
through the event loop. Implement a simple scheduling heuristic in
`run` that executes one task each time through, if there is one to run.

``` {.python expected=False}
class TaskRunner:
    def __init__(self):
        self.tasks = []

    def schedule_task(self, callback):
        self.tasks.append(callback)

    def run(self):
        if len(self.tasks) > 0):
            task = self.tasks.pop(0)
            task()
```

Finally we just need to modify the main event loop to run the task runner each
time, in case there is a script task to execute:

``` {.python expected=False}
if __name__ == "__main__":
    # ...
    while True:
        while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            # ...
            browser.tabs[browser.active_tab].task_runner.run()
```

Of course, this is all pointless at the moment, since there aren't any tasks
yet. Let's try out this infrastructure on a simple example: evaluating scripts
after load. Currently the browser just evaluates them right away, but instead
let's make script evaluationt a task.

It's as simple as calling `schedule_task` with a `Task` that runs the script,
and then continuing on with the rest of the loading logic as if nothing
was changed:

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

That's it! Now our browser will not run scripts until after `load` has completed
and the event loop comes around again. But before continuing, let's consider
why this change is interesting---is it anything other than just some
refactoring?

It used to be that we had no choice but to eval scripts right away just as they
were loaded. But now it's pretty clear that we have a lot more control over
when to run scripts. For example, it's easy to make a change to `TaskRunner` to
only run one script per second, or to not run them at all during page load, or
when a tab is not the active tab. This flexibility is quite powerful, and we
can use it without having to dive into the guts of a `Tab` or how it loads web
pages---all we'd have to do is implement a new `TaskRunner` heuristic.

Timers and setTimeout
====================

It's often the case that when adding a task, it's not to be run right away, but
instead at some point in the future. One example is the
[`setTimeout`][settimeout] JavaScript API, which provides a way to run a
function a given number of milliseconds from now. For example,

``` {.javascript expected=false}
function callback() {
    console.log('Callback')
}
setTimeout(callback, 1000);
```
will print "Callback" to the console log one second from now.

This API *could* be implemented by recording a time associated with each new
`Task`, and comparing that time against the current time in the event
loop.^[This approach is called
*polling*, and is also what the SDL event loop does to look for events and
 tasks.] A better approach is to use Python's [`threading.Timer`][timer] class,
 which does this for you (and probably much more efficiently) with a
 [Python thread][python-thread].

[timer]: https://docs.python.org/3/library/threading.html#timer-objects
[settimeout]: https://developer.mozilla.org/en-US/docs/Web/API/setTimeout
[python-thread]: https://docs.python.org/3/library/threading.html

Start by importing that module:

``` {.python}
import threading
```

The `Timer` class lets you run a callback at a specified time in the future. It
takes two parameters: a time delta in seconds from now, and a function to call
when that time expires. The following code will run `callback` 10 seconds in
the future on a new Python thread:

``` {.python expected=False}
threading.Timer(10, callback).start()
```

Now implement `setTimeout` on top of this functionality.  In terms of the
JavaScript and Python communication, it'll use an approach with handles,
similar to the `addEventListener` code we added in
[Chapter 9](scripts.md#event-handling). In the
JavaScript runtime, add a new internal handle for each call to `setTimeout`,
and store the mapping between handles and callback functions in a global object
called `SET_TIMEOUT_REQUESTS`. When the timeout occurs, Python will call
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
            self.tab.task_runner.schedule_task(
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

    def run(self):
        self.lock.acquire(blocking=True)
        task = None
        if len(self.tasks) > 0:
            task = self.tasks.pop(0)
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

Long-lived threads
==================

Python not only lets you create timers, but you can create and manipulate
threads themselves, via the `threading.Thread` class. Let's use threads to
implement async `XHMLHttpRequest`, a feature we left out of
[Chapter 10](security.md#cross-site-requests). At the time, we implemented it
as a synchronous API, but in fact, the synchronous version of that API is almost
useless for real websites,^[It's also a huge performance footgun, for the same
reason we've been adding async tasks in this chapter!] because the whole point
of using this API is to keep the website responsive to the user while
network requests are going on.

Our approach will be to start a thread, run some code on it that does the
request and gets a response, then schedule a `Task` to send the response back
to the script. Starting a thread is easy: define a function that is the "main"
function of the thread, then start the thread with the function passed as the
`target` argument. When the main function exits, the thread will automatically
die.

In this example:
``` {.python expected=False}
def run:
    count = 0
    while count < 100:
        print("Thread")
        count += 1

thread = threading.Thread(target=run)
thread.start()
while True:
    print("Browser")
```

a stream of lines with the words "Thread" and "Browser" will be
interspersed---according to the CPU scheduling algorithm of the computer and
the Python runtime---until the thread has printed 100 times, after which
"Browser" will continue printing forever.

Here is the code for `XMLHttpRequest_send` (the new `is_async` parameter
indicates an async request). In this case, `run_load` is the thread main
function, and after the line that says "return out" executes, the thread will
die.^[Note that for async requests, the return statement is meaningless;
it's only there for the sync version.]

``` {.python}
XHR_ONLOAD_CODE = "__runXHROnload(dukpy.out, dukpy.handle)"

class JSContext:
    def xhr_onload(self, out, handle):
        do_default = self.interp.evaljs(
            XHR_ONLOAD_CODE, out=out, handle=handle)

    def XMLHttpRequest_send(
        self, method, url, body, is_async, handle):
        full_url = resolve_url(url, self.tab.url)
        if not self.tab.allowed_request(full_url):
            raise Exception("Cross-origin XHR blocked by CSP")
        if url_origin(full_url) != url_origin(self.tab.url):
            raise Exception(
                "Cross-origin XHR request not allowed")

        def run_load():
            headers, out = request(
                full_url, self.tab.url, payload=body)
            handle_local = handle
            self.tab.task_runner.schedule_task(
                Task(self.xhr_onload, out, handle_local))
            return out

        if not is_async:
            return run_load(is_async)
        else:
            load_thread = threading.Thread(target=run_load)
            load_thread.start()
```

Now for the JavaScript plumbing. We'll make the following changes:

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

And there you have it. With the task machinery and only a few more lines of
non-plumbing code, we can support lots of new features, and `setTimeout` and
async `XMLHttpRequest` are only the start.

Rendering pipeline tasks
========================

Everything in a browser can be considered a task, including rendering. In fact,
the most important task in a browser is the rendering pipeline---but not just
for the obvious reason that it's impossible to see web pages that aren't
rendered. Most of the time spent doing work in a browser is in *rendering
interactions* with the browser, such as loading, scrolling, clicking and
typing. All of these interactions require rendering. If you want to make those
interactions faster and smoother, the very first think you have to do is
schedule the rendering pipeline, and to achieve that it'll need to be a
schedulable task.

On thing that is special about rendering is that it's a "singleton" task. There
is only one rendering task, and either it's been scheduled or not, but it
doesn't make sense to schedule it twice at the same time. On the other hand,
it's totally fine and natural to have many `setTimeout` or `XMLHttpRequest`
callbacks pending at the same time. The singleton nature of the rendering task
has to do with there being only one DOM to render.

Because it's a singleton, we'll need an additional boolean variable on a `Tab`
to avoid having two rendering tasks, called `needs_animation_frame`. This
variable means "a rendering task was already scheduled". Also add a
`schedule_animation_frame`[^animation-frame] method that adds a new task to
render, and a new method `run_animation_frame` as the task callback. Note
how we avoid two scheduled frames with an if statement.

[^animation-frame]: It's called an "animation frame" because sequential
rendering of different pixels is an animation, and each time you render it's
one "frame"---like a drawing in a picture frame.


``` {.python expected=False}
class Tab:
    def __init__(self, browser):
        # ...
        self.needs_animation_frame = False

    def set_needs_render(self):
        self.schedule_animation_frame()

    def schedule_animation_frame(self):
        if self.needs_animation_frame:
            return
        self.needs_animation_frame = True
        self.task_runner.schedule_task(Task(self.run_animation_frame))

    def run_animation_frame(self):
        self.render()
        self.needs_animation_frame = False
```

But `render` only does style, layout and paint. We also need raster and draw,
so add a method to `Browser` and call it from `run_animation_frame`:

``` {.python expected=False}
class Tab:
    def __init__(self, browser):
        self.browser = browser

    def run_animation_frame(self):
        self.render()
        browser.raster_and_draw()

class Browser:
    def raster_and_draw(self):
        self.raster_chrome()
        self.raster_tab()
        self.draw()
```

The last piece is to actually call `set_needs_render` from somewhere.
Replace all cases where the rendering pipeline is computed synchronously with
`set_needs_render`. Here, for example, is `load`:[^more-examples]

[^more-examples]: There are more of them; you should fix them all.

``` {.python}
class Tab:
    def load(self, url, body=None):
        # ...
        self.set_needs_render()
```

All the places that call `raster_chrome`, `raster_tab` or `draw` directly will
also need to call `set_needs_render` instead.[^render-instead] Here's
`handle_down`:

[^render-instead]: Technically, it's not necessary to do so, but thinking of all
of rendering (including raster and draw) as one pipeline that's either run or
not run is a good way to think about what is going on. Later we'll add ways to
get back equivalent performance to rastering directly without resorting to
a short-circuit of the rendering pipeline.

``` {.python expected=False}
class Browser:
    def handle_down(self):
        active_tab = self.tabs[self.active_tab]
        active_tab.scrolldown()
        self.active_tab.set_needs_render()
```

Now our browser can run rendering in an asynchronous, scheduled way on the event
loop!

Unfortunately, we also regressed the overall performance of the browser by
quite a lot in some cases. For example, scrolling down will now cause
the entire rendering pipeline (style, layout, etc.) to run, instead of
just `draw`. Let's see how to fix that.

Animating frames
================

Scrolling is an interesting case, actually. It's a situation that is the closest
to a true animation in the browser right now---if you hold down the down-arrow
key, you'll see what looks like a scrolling animation. Since it's one case of a
more general situation (animations of all kinds), it makes sense to understand
animations more generally, then apply what we learned to scrolling as
a special case. To this end, let's explore yet another JavaScript API,
[`requestAnimationFrame`][raf].

[raf]: https://developer.mozilla.org/en-US/docs/Web/API/window/requestAnimationFrame

This API lets scripts run an animation by integrating with the rendering task.
It works like this:

``` {.javascript expected=False}
/* This is JavaScript */
function callback() {
    console.log("I was called!");
}
requestAnimationFrame(callback);
```

This code will do two things: request an animation frame task to be scheduled
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
        self.schedule_animation_frame()

    def run_animation_frame(self):
        if self.needs_raf_callbacks:
            self.needs_raf_callbacks = False
            self.js.interp.evaljs("__runRAFHandlers()")

        self.render()
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

Ok, now that that's implemented, let's take a deeper look at what
`run_animation_frame` does:

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
function callback() {
    var output = document.querySelectorAll("div")[1];
    output.innerHTML = "count: " + (count++);
    if (count < 100)
        requestAnimationFrame(callback);
}
requestAnimationFrame(callback);
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

Load this up and observe an animation from 0 to 100.

However, there is a pretty big flaw in our implementation that might be apparent
when you try this demo. Depending on your computer's speed, it might run really
fast or really slow. In fact, the animation will take a total amount of time
about equal to the time it takes to run 100 rendering tasks. This is
bad---animations should have a smooth and consistent frame rate, or *cadence*,
regardless of the computer hardware.

The cadence of rendering
========================

So what should this cadence be? Well, clearly it shouldn't go faster
than the display hardware can refresh. On most computers, this is 60 times
per second, or 16ms per frame (`60*16.66ms ~= 1s`).

Ideally, the cadence shouldn't be slower than that either, so that animations
are as smooth as possibile. This was discussed briefly in Chapter 2 as well,
which introduced the [animation frame budget](graphics.md#framebudget). The
animation frame budget is our target for how fast the rendering task should
be.

Therefore, let's use 16ms as the definition of the cadence (otherwise known
as the refresh rate), and see how close we can get to that speed:

``` {.python}
REFRESH_RATE_SEC = 0.016 # 16ms
```

To not go faster than the refresh rate, use a `Timer`:

``` {.python expected=False}
class Tab:
    def schedule_animation_fraggme(self):
        # ...
        def callback():
            self.task_runner.schedule_task( \
                Task(self.run_animation_frame))
        threading.Timer(REFRESH_RATE_SEC, callback).start()
```

Unfortunately, not going slower than the refresh rate is difficult. We can't
just randomly speed up a computer; instead we need to do the painstaking work
of *optimizing* the rendering pipeline.

Here's a start: avoid running `render` or `raster_and_draw` just because
an animation frame was scheduled. As we saw with `requestAnimationFrame`,
sometimes frames are scheduled just to run a script, and style etc. may not
need to run at all. Likewise, just because we're scrolling doesn't mean we
need to style or raster anything.

To achieve this, add two *dirty bits*, boolean variables that indicate
whether something changed that requires re-doing the first or second half of
the rendering pipeline. Naturally, they will be called `needs_render`
and `needs_raster_and_draw`. They will come with methods to set them to true
(we already `have set_needs_render` in `Tab`, actually),
and we'll obey them when considering running `render` or `raster_and_draw`.


``` {.python expected=False}
class Tab:
    def __init__(self, browser):
        # ...
        self.needs_render = False

    def set_needs_render(self):
        self.needs_render = True
        self.schedule_animation_frame()

    def render(self):
        if not self.needs_render:
            return
        # ...
        self.needs_render = False

class Browser:
    def __init__(self):
        # ...
        self.needs_raster_and_draw = False

    def set_needs_raster_and_draw(self):
        self.needs_raster_and_draw = True
        self.tab.schedule_animation_frame()

    def raster_and_draw(self):
        if not self.needs_raster_and_draw:
            return
        # ...
        self.needs_raster_and_draw = False
```

Note how this change also magically made `requestAnimationFrame` avoid calling
`render` by defaut, because that API calls `request_animation_frame_callback`,
not `set_needs_render`.

On the `Browser` side, here are some optimizations we can now add, such as to
`handle_click`:

``` {.python}
class Browser:
    def handle_click(self, e):
        if e.y < CHROME_PX:
            # ...
            self.set_needs_raster_and_draw()
        else:
            # ...
            self.set_needs_raster_and_draw()
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

Parallel rendering
==================

What happens if rendering takes much more than 16ms to finish and we're out of
ideas for how to make it run more efficiently? If it's a rendering task that's
slow, such as font loading (see [chapter 3][faster-text-loading]), if we're
lucky we can make it faster. But sometimes it's not possible to make the code a
lot faster, it just has a lot to do. In rendering, this could be because the
web page is very large or complex.

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
        self.time_in_render = 0.0
        self.num_renders = 0

    def render(self):
        if not self.needs_render:
            return
        timer = Timer()
        timer.start()
        # ...
        self.time_in_render += timer.stop()
        self.num_renders += 1

    def handle_quit(self):
        print("Time in render on average: {:>.0f}ms".format(
            self.time_in_render / \
                self.num_renders * 1000))
```

``` {.python}
class Browser:
    def __init__(self):
        self.time_in_raster_and_draw = 0
        self.num_raster_and_draws = 0

    def raster_and_draw(self):

        if not self.needs_raster_and_draw:
            return
        self.lock.acquire(blocking=True)
        raster_and_draw_timer = Timer()
        raster_and_draw_timer.start()
        # ...
        self.time_in_raster_and_draw += raster_and_draw_timer.stop()
        self.num_raster_and_draws += 1

    def handle_quit(self):
        print("Time in raster-and-draw on average: {:>.0f}ms".format(
            self.time_in_raster_and_draw / \
                self.num_raster_and_draws * 1000))
```

Now fire up the server and navigate to `/count`.^[The full URL will probably be
`http://localhost:8000/count`] When it's done counting, click the close button
on the window. The browser will print out the total time spent in each
category. When I ran it on my computer, it said:

    Time in raster-and-draw on average: 66ms
    Time in render on average: 20ms

Over a total of 100 frames of animation, the browser spent abou 20ms in `render`
and about 66ms in `raster_and_draw` per animation frame. Therefore, moving
`raster_and_draw` to a second thread has the potential to reduce total
rendering time from 88ms to 66ms by running the two operations in parallel. In
addition, there would only be a 20ms delay to any other main-thread task that
wants to run after rendering. That's more than enough of a win to justify
the second thread.

::: {.further}

If you profile just raster and draw, you'll find that there is lots of time
spent doing both. Within draw, each drawing-into-surface step takes a
significant amount of time. I told you that
[optimizing surfaces](visual-effects.md#optimizing-surface-use) was important!
In any case, I encourage you to do this profiling, to see for yourself.

The best way to optimize `draw` is to perform raster and draw on the
GPU---modern browsers do this---so that the draws can happen in parallel in GPU
hardware. Skia supports GPU raster, so you could try it. But raster and draw
sometimes really do take a lot of time on complex pages, even with the GPU. So
rendering pipeline parallelism is a performance win regardless, and if it's
done in a separate process, there are also security advantages.

Further, even with the second thread, the browser thread is somewhat
unresponsive to clicks and scrolls---it's not good to wait around 66ms
before *starting* to handle a click event! For this reason, modern browsers run
raster and draw on [*yet more* threads or processes][renderingng-architecture].
 This change finally the browser thread extremely responsive
to input.[^thread-exercise]

[^thread-exercise]: I've left this task to an exercise.

[renderingng-architecture]: https://developer.chrome.com/blog/renderingng-architecture/#process-and-thread-structure
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

[^also-compositor]: Th browser thread is similar to what modern browsers often
call the [*compositor thread*][cc].

[cc]: https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/how_cc_works.md

* Raster and draw
* Interacting with browser chrome
* Scrolling

The other thread, which we'll call the *main thread,*[^main-thread-name] will
be for:

* Evaluating scripts
* Loading resources
* Animation frame callbacks, style, layout, and paint
* DOM Event handlers
* `setTimeout` callbacks

[^main-thread-name]: Here I'm going with the name real browsers often use. A
better name might be the "JavaScript" thread (or even better, the "DOM"
thread, since JavaScript can sometimes run on [other threads][webworker]).

[webworker]: https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API

In terms of the our browser implementation, all code in `Browser` will run on
the *browser* thread, and all code in `Tab` and `JSContext` will run on the
*main* thread.

Let's plan out the implementation of this two-thread setup:

* The thread that already exists (the one started by the Python interpreter
by default) will be the browser thread, and we'll make a new one for the main
thread.

* The two threads will communicate as follows:

  * *Browser->main*: The browser thread will place tasks on the main thread
    `TaskRunner`.

  * *Main->browser*: The main thread will call two new methods on `Browser`:
     `commit` and `set_needs_animation_frame`. `commit` will copy the
     display list the browser thread.
     `set_needs_animation_frame` will request an animation frame.

The control flow for generating a rendered frame will be:

1. The main thread (or browser thread) code requests an animation frame.
2. The browser thread event loop schedules an animation frame on the main
thread `TaskRunner`.
3. The main thread executes its part of rendering, then calls `browser.commit`.
4. The browser rasters the display list and draws to the screen.

Other tasks started by the browser thread event loop (input event handlers
for mouse and keyboard) will work like this:

1. The browser thread event loop calls the appropriate method on the `browser`.
2. If the event's target is in the web page, the browser will schedule a task
on the main thead `TaskRunner`.
3. The main thread executes the task. If the task affects rendering, it calls
`browser.set_needs_animation_frame`.

Let's implement this design. Begin by adding a `threading.Thread` object
called `main_thread` to `TaskRunner`, with a `target of` `run`. `run` will
no longer just go once through, and will instead start an infinite loop looking
for tasks. This infinite loop will keep the main thread live indefinitely.

``` {.python}
class TaskRunner:
    def __init__(self, tab):
        # ...
        self.main_thread = threading.Thread(target=self.run)

    def start(self):
        self.main_thread.start()    

    def run(self):
        while True:
            # ...
```

In `run`, implement a simple event loop scheduling strategy that runs one
task per loop.

``` {.python}
class TaskRunner:
    def run(self):
        while True:
            # ...
            task = None
            self.lock.acquire(blocking=True)
            if len(self.tasks) > 0:
                task = self.tasks.pop(0)
            self.lock.release()
            if task:
                task()
```

Next, make the `Browser` schedule tasks on the main thread
instead of calling them directly. For example, here is loading:

``` {.python}
class Browser:
    def schedule_load(self, url, body=None):
        active_tab = self.tabs[self.active_tab]
        active_tab.task_runner.schedule_task(
            Task(active_tab.load, url, body))

    def handle_enter(self):
        self.lock.acquire(blocking=True)
        if self.focus == "address bar":
            self.schedule_load(self.address_bar)
            self.url = self.address_bar
            self.focus = None
            self.set_needs_raster_and_draw()
        self.lock.release()

    def load(self, url):
        new_tab = Tab(self)
        self.set_active_tab(len(self.tabs))
        self.tabs.append(new_tab)
        self.schedule_load(url)
```

Do the same for input event handlers, but there is one additional
subtlety: sometimes the event is handled on the browser thread, and
sometimes the main thread.

Consider `handle_click`: typically, we will need to
[hit test](chrome.md#hit-testing) for which DOM element receives the click
event, and also fire an event that scripts can listen to. Since DOM
computations and scripts can only run on the main thread, it seems we
should just send the click event to the main thread for processing. But if the
click was *not* within the web page window (i.e., `e.y < CHROME_PX`), we can
handle it right there in the browser thread, and leave the main thread
none the wiser:

``` {.python}
class Browser:
    def handle_click(self, e):
        self.lock.acquire(blocking=True)
        if e.y < CHROME_PX:
             # ...
        else:
            self.focus = "content"
            active_tab = self.tabs[self.active_tab]
            active_tab.task_runner.schedule_task(
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
            active_tab.task_runner.schedule_task(
                Task(active_tab.keypress, char))
        self.lock.release()
```

Now let's go the other direction, and implement the `commit` method that
copies the display list, url and scroll offset to the browser thread.

``` {.python expected=False}
class Tab:
    def __init__(self, browser):
        # ...
        self.browser = browser

    def run_animation_frame(self):
        self.render()
        # ...
        self.browser.commit(
            self, self.url, self.scroll,
            document_height,
            self.display_list)
```

In `Browser`, commit will copy across the url, scroll offset and display list,
and call `set_needs_raster_and_draw` as needed. Since each `Tab` has its own
thread that is always running, the `tab` parameter is
compared with the active tab to avoid committing display lists for invisible
tabs.

``` {.python}
class Browser:
    def __init__(self):
        self.url = None
        self.scroll = 0

    def commit(self, tab, url, scroll, tab_height, display_list):
        self.lock.acquire(blocking=True)
        if tab != self.tabs[self.active_tab]:
            self.lock.release()
            return
        self.display_scheduled = False
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

[^fast-commit]: Fun fact: `commit` is a critical time when both threads are
both "stopped" simultaneously---in the sense that neither is running a
different task at the same time. For this reason commit needs to be as fast as
possible, to maximize parallelism and responsiveness. In modern browsers,
optimizing commit is quite challenging.

But we're not done. The last piece is to ensure that the *browser thread*
determines the cadence of animation frames, *not* the main thread.
Why the browser thread and not the main thread? The reason
is simple: there is no point to rendering display lists
faster than they can be drawn to the screen.

Implement this by adding a `needs_animation_frame` dirty bit on `Browser`. Tabs
call a special version of this method that uses a lock and disallows setting
the bit for a non-active tab.^[The `Browser` use-cases that set this dirty bit
also need a lock, but all of the calling functions already hold the lock. If
they tried to call the version that locks then a [deadlock] would occur.]

Setting the bit only for active tabs prevents others from setting a
dirty bit they don't need (because there is nothing to display for a non-active
tab), and elegantly prevents any `requestAnimationFrame`
callbacks from running. Try making a second tab while the counter demo is
running, then go back to the demo tab. Notice that it stopped counting up
while the other tab was visible, and resumes when it is made visible again!

[deadlock]: https://en.wikipedia.org/wiki/Deadlock

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.needs_animation_frame = False

    def set_tab_needs_animation_frame(self, tab):
        self.lock.acquire(blocking=True)
        if tab == self.tabs[self.active_tab]:
            self.needs_animation_frame = True
        self.lock.release()

    def set_needs_animation_frame(self):
        self.needs_animation_frame = True
```

Then, *only once the browser thread is done drawing to the screen*
will it schedule an animation frame on the main thread.[^backpressure]

[^backpressure]: The technique of controlling the speed of the front of a
pipeline by means of the speed of its end is called *back pressure*.

``` {.python}
if __name__ == "__main__":
    while True:
        # ...
        browser.raster_and_draw()
        browser.schedule_animation_frame()
```

And `schedule_animation_frame` on `Browser` works just like the version
earlier in the chapter:

``` {.python expected=False}
class Browser:
    def __init__(self):
        # ...
        self.display_scheduled = False

    def schedule_animation_frame(self):
        def callback():
            self.lock.acquire(blocking=True)
            active_tab = self.tabs[self.active_tab]
            active_tab.task_runner.schedule_task(
                Task(active_tab.run_animation_frame))
            self.lock.release()
        self.lock.acquire(blocking=True)
        if not self.display_scheduled and self.needs_animation_frame:
            threading.Timer(REFRESH_RATE_SEC, callback).start()
            self.display_scheduled = True
            self.needs_animation_frame = False
        self.lock.release()
```

To make use of this sytem, call `set_tab_needs_animation_frame` from
`set_needs_render`, and also from `request_animation_frame_callback`:

``` {.python}
class Tab:
    def set_needs_render(self):
        self.needs_render = True
        self.browser.set_tab_needs_animation_frame(self)

    def request_animation_frame_callback(self):
        self.needs_raf_callbacks = True
        self.browser.set_tab_needs_animation_frame(self)
```

And also in `Browser`:

``` {.python}
class Browser:
    def set_needs_raster_and_draw(self):
        self.needs_raster_and_draw = True
        self.set_needs_animation_frame()
```

That's it. Don't forget to remove the old implementation of
`schedule_animation_frame` on `Tab`, and also convert over all of the other
callsites I omitted here for brevity.

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
        self.set_needs_animation_frame()
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
            active_tab.task_runner.schedule_task(
                Task(active_tab.run_animation_frame, scroll))
            self.lock.release()
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
        self.render()

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
            self, self.url,
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
network, i.e calls to `request` and `XMLHTTPRequest`. This will allow us to
load all resources for the page *in parallel*, greatly reducing the time to
load the page. This feature is a key to good performance in modern browsers.

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

To make it work, we'll use a new threading feature: `join`. Join blocks
one thread's execution on another thread completing. For example, this code:

``` {.python expected=False}
def run:
    count = 0
    while count < 100:
        print("Thread")
        count += 1

thread = threading.Thread(target=run)
thread.start()
thread.join()
while True:
    print("Browser")
```

will print "Thread" 100 times, and *only then* start printing "Browser".

Define a new `async_request` function. This will start a thread. The thread will
request the resource, store the result in `results`, and then return. The
thread object will be returned by `async_request`. `async_request` will need a
lock, because `request` will need to access the thread-shared `COOKIE_JAR`
variable.

``` {.python}
def async_request(url, top_level_url, results, lock):
    headers = None
    body = None
    def runner():
        headers, body = request(url, top_level_url, None, lock)
        results[url] = {'headers': headers, 'body': body}
    thread = threading.Thread(target=runner)
    thread.start()
    return thread
```

And we'll need a small edit to `request` to use the lock:

``` {.python}
def request(url, top_level_url, payload=None, lock=None):
    # ...
    if lock:
        lock.acquire(blocking=True)
    has_cookie = host in COOKIE_JAR
    if has_cookie:
        cookie, params = COOKIE_JAR[host]
    if lock:
        lock.release()

    # ...

    if "set-cookie" in headers:
        # ...
        if lock:
            lock.acquire(blocking=True)
        COOKIE_JAR[host] = (cookie, params)
        if lock:
            lock.release()
```

Then we can use it in `load`. Note how we send off all of the requests first:

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
                    script_url, url, script_results,
                    self.task_runner.lock)
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
                "thread": async_request(
                    style_url, url, style_results,
                    self.task_runner.lock)
            })
```

And only at the end `join` all of the threads created:

``` {.python}
        for async_req in async_requests:
            async_req["thread"].join()
            req_url = async_req["url"]
            if async_req["type"] == "script":
                self.task_runner.schedule_task(
                    Task(self.js.run, req_url,
                        script_results[req_url]['body']))
            else:
                self.rules.extend(
                    CSSParser(
                        style_results[req_url]['body']).parse())
```

Now our browser will parallelize loading sub-resources!

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

::: {.further}

The approach in this section ignores the parse order of the scripts and style
sheets, which is technically incorrect and a real browser would be much more
careful. But as mentioned in an earlier chapter, our browser is already
incorrect in terms of orders of operations, as scripts and style sheets are
supposed to block the HTML parser as well. Nevertheless, modern browsers
achieve performance similar to the one here, by use of a *preload scanner*.

While the "observable" side-effects of loading have to be done in a certain
order, that doesn't mean that the browser has to issue network requests in that
order. Modern browsers take advantage of that by adding a second, simpler
HTML parser called a preload scanner (the HTML spec calls it a
[speculative HTML parser][speculative-parser]). The preload scanner does nothing
but look for URLs referred to by DOM elements, and kicks off network requests
to load them.
:::

[speculative-parser]: https://html.spec.whatwg.org/#active-speculative-html-parser

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
        self.render()
        # ...
```

The call to `render` is a forced layout. It's needed because
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
animation frame rate cadence than 16ms, for example if `render`
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

* *Condition variables*: the main thread event loop works, but but is wasteful
   of the CPU. Even if there are no tasks, the thread will keep looping over
   and over. You can fix this by introducing a *condition variable* that
   wakes up the thread and runs it only when there is actually a task to run.
  [^browser-thread-burn]
   The [`threading.Condition`][condition] class implements this pattern in
   Python. Call `wait()` to stop the thread until notified that a task has
   arrived, and call `notify_all` when the task is added.

[condition]: https://docs.python.org/3/library/threading.html#condition-objects
[^browser-thread-burn]: The browser thread's `while True` loop is also
wasteful. Unfortunately, it appears there is not a way to avoid this in SDL at
present.

* *Optimized scheduling*: currently, `schedule_animation_frame` uses a timer to
   run the animation frame task `REFRESH_RATE_SEC` in the future, regardless of
   how long the browser event loop took to run once through. This doesn't make
   a lot of sense, since the whole point of the refresh rate is to generate
   frames at about the desired cadence. Fix this by subtracting from
   `REFRESH_RATE_SEC` according to how much time the *previous* frame took.

   A second problem is that the browser may simply not be able to keep up with
   the desired cadence. Instead of constantly pegging the CPU in a futile
   attempt to keep up, implement a *frame time estimator* that estimates the
   true cadence of the browser based on previous frames, and
   adjust `schedule_animation_frame` to match.

   A third problem is that the main thread `TaskRunner` only has one task queue,
   and both rendering and non-rendering tasks go into it. Therefore a slow
   sequence of script or event handler tasks may interfere with the desired
   rendering cadence. This problem can be lessened by *prioritizing* rendering
   tasks: placing them in a separate queue that can take priority over
   other tasks. Implement this.

* *Raster-and-draw thread*: the browser thread is currently not very responsive
   to input events, because raster and draw are
   [slow](#parallel-rendering). Fix this by adding a raster-and-draw thread
   controlled by the browser thread, so that the browser thread is no longer
   blocked on this work. Be careful to take into account that SDL is not
   thread-safe, so all of the steps that directly use SDL still need to happen
   on the browser thread.