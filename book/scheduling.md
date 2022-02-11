---
title: Scheduling and Threading
chapter: 12
prev: visual-effects
next: skipped
...

The browser must run sophisticated applications while staying
responsive to user actions. Doing so means choosing which of its many
tasks to prioritize and which to delay until later---tasks like
JavaScript callbacks, user input, and rendering. Moreover, the browser
must be split across multiple threads, with different threads running
events in parallel to maximize responsiveness.

Tasks and Task Queues
=====================

So far, most of the work our browser's been doing has been handling
user actions like scrolling, pressing buttons, and clicking on links.
But as the web applications our browser runs get more and more
sophisticated, they begin querying remote servers, showing animations,
and prefetching information for later. And while users are slow and
deliberative, leaving long gaps between actions for the browser to
catch up, applications can be very demanding. This requires a change
in perspective: the browser now has a never-ending queue of tasks to
do.

Modern browsers adapt to this reality by multitasking, prioritizing,
and deduplicating work. Every bit of work the browser might
do---loading pages, running scripts, and responding to user
actions---is turned into a *task*, which can be executed later. Here,
a task is just a function (plus its arguments) that can be
executed:[^varargs]

[^varargs]: By writing `*args` as an argument to `Task`, we indicate
that a `Task` can be constructed with any number of arguments, which
are then available as the list `args`.

``` {.python}
class Task:
    def __init__(self, task_code, *args):
        self.task_code = task_code
        self.args = args
        self.__name__ = "task"

    def run(self):
        self.task_code(*self.args)
        self.task_code = None
        self.args = None
```

The point of a task is that it can be created at one point in time,
and then run at some later time by a task runner of some kind,
according to a scheduling algorithm.[^event-loop] In our browser, the
task runner will store tasks in a first-in first-out queue:

[^event-loop]: The event loops we discussed in [Chapter
2](graphics.md#eventloop) and [Chapter
11](visual-effects.md#sdl-creates-the-window) are task runners, where
the tasks to run are provided by the operating system.

``` {.python replace=(self)/(self%2c%20tab)}
class TaskRunner:
    def __init__(self):
        self.tasks = []

    def schedule_task(self, callback):
        self.tasks.append(callback)
```

When the time comes to run a task, our task runner can just remove
the first task from the queue and run it:

``` {.python expected=False}
class TaskRunner:
    def run(self):
        if len(self.tasks) > 0):
            task = self.tasks.pop(0)
            task.run()

class Tab:
    def __init__(self):
        self.task_runner = TaskRunner()
```

First-in-first-out is a simplistic way to choose which task to run
next, and real browsers have sophisticated *schedulers* which consider
[many different factors][chrome-scheduling].

[chrome-scheduling]: https://blog.chromium.org/2015/04/scheduling-tasks-intelligently-for_30.html

To run those tasks, we need to call the `run` method on our
`TaskRunner`, which we can do in the main event loop:

``` {.python expected=False}
if __name__ == "__main__":
    while True:
        # ...
        browser.tabs[browser.active_tab].task_runner.run()
```

Here I've chosen to only run tasks on the active tab. Now our browser
will not run scripts until after `load` has completed and the event
loop comes around again.

This simple task runner now lets us save tasks for later and execute
when there's time. For example, right now, when loading a web page,
our browser will download and run all scripts before doing its
rendering steps. That makes pages slower to load. We can fix this by
creating tasks for running scripts later.

``` {.python expected=False}
class Tab:
    def run_script(self, url, body):
        try:
            print("Script returned: ", self.js.run(body))
        except dukpy.JSRuntimeError as e:
            print("Script", url, "crashed", e)

    def load(self):
        for script in scripts:
            # ...
            header, body = request(script_url, url)
            self.task_runner.schedule_task(
                Task(self.run_script, script_url, body))
```

This change is nice---pages will load a bit faster---but there's more
to it than that. Before this change, we no choice but to run scripts
right away just as they were loaded. But now that running scripts is a
`Task`, the task runner controls when it runs. It could run only one
script per second, or at different rates for active and inactive
pages, or only if there isn't a higher-priority user action to respond
to. A browser could even have multiple task runners, optimized for
different use cases.


::: {.further}
Thinking of the browser as a rendering pipeline is strongly influenced
by the history of graphics and games. High-performance games have a lot in
common with a browser in this sense, especially those that use
[scene graphs](https://en.wikipedia.org/wiki/Scene_graph), which are a lot
like the DOM. Games and browsers are both driven by event loops that
convert a representation of the scene graph into a display list, and the
 display list into pixels.

On the other hand, there are some aspects of browsers that are *very* different
than games. The most important difference is that in games, the programmer
almost always knows *in advance* what scene graphs will be provided. They
can then pre-optimize the pipeline to make it super fast for those graphs.
This is why games often take a while to load, because they are uploading
hyper-optimized code and pre-rendered data to the CPU and GPU memory.

Browsers, on the other hand, need to load arbritrary web pages, and do so
extremely fast. So they can't spend much time optimizing anything, and instead
have to get right to the business of pushing pixels. This important difference
makes for a very different set of tradeoffs, and is why browsers often
feel less fancy and smooth than games.

Native apps also have the equivalent of a known-in-advance scene graph, though
they don't have the advantage of tolerating a slow load time. As a consequence,
they sometimes have a fancier user experience than equivalent websites, but not
nearly so much as games.
:::

Timers and setTimeout
=====================

Tasks are *also* a natural way to support several JavaScript APIs that
ask for a function to be run at some point in the future. For example,
the [`setTimeout`][settimeout] JavaScript API lets you run a function
some number of milliseconds from now. This code prints "Callback" to
the console one minute in the future, for example:

[settimeout]: https://developer.mozilla.org/en-US/docs/Web/API/setTimeout

``` {.javascript expected=false}
function callback() { console.log('Callback'); }
setTimeout(callback, 1000);
```

We can implement `setTimeout` in our browser using the
[`Timer`][timer] class in Python's [`threading`][threading] module.
You use the class like this:[^polling]

[^polling]: An alternative approach would be to record when each
`Task` is supposed to occur, and compare against the current time in
the event loop. This is called *polling*, and is what, for example,
the SDL event loop does to look for events and tasks. However, that
can mean wasting time in a loop waiting for the task to be ready, so I
expect the `Timer` to be more efficient.

[timer]: https://docs.python.org/3/library/threading.html#timer-objects
[threading]: https://docs.python.org/3/library/threading.html

``` {.python expected=False}
import threading
threading.Timer(1, callback).start()
```

This runs `callback` one second from now on a new Python thread. Now,
it's going to be a little tricky to use `Timer` to implement
`setTimeout` due to the fact that multiple threads will be involved,
but it's worth it.

As with `addEventListener` in [Chapter 9](scripts.md#event-handling),
the call to `setTimeout` will save the callback in a JavaScript
variable and create a handle by which the Python-side code can call
it:

``` {.javascript file=runtime}
SET_TIMEOUT_REQUESTS = {}

function setTimeout(callback, time_delta) {
    var handle = Object.keys(SET_TIMEOUT_REQUESTS).length;
    SET_TIMEOUT_REQUESTS[handle] = callback;
    call_python("setTimeout", handle, time_delta)
}
```

The exported `setTimeout` function will create a timer, wait for the
requested time period, and ask the JavaScript runtime to run the
callback. This happens via the `__runSetTimeout` function:

``` {.javascript file=runtime}
function __runSetTimeout(handle) {
    var callback = SET_TIMEOUT_REQUESTS[handle]
    delete SET_TIMEOUT_REQUESTS[handle];
    callback();
}
```

The Python side, however, is quite a bit more complex, because
`threading.Timer` executes its callback *on a new Python thread*. That
thread can't just call `evaljs` directly: we'll end up with JavaScript
running on two Python threads at the same time, which is not
ok.[^js-thread] Instead, the timer will have to merely add a new
`Task`, which our primary thread will execute, to call the callback:

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

Now only the primary thread will call `evaljs`,. But now
we have two threads accessing the `task_runner`: the main thread, to
run tasks, and the timer thread, to add them. This is a [race
condition](https://en.wikipedia.org/wiki/Race_condition) that can
cause all sorts of bad things to happen, so we need to make sure only
one thread accesses the `task_runner` at a time.

To do so we use a `Lock` object, which can only held by one thread at
a time. Each thread will try to acquire the lock before reading or
writing to the `task_runner`, avoiding simultaneous access:^[The
`blocking` parameter to `acquire` indicates whether the thread should
wait for the lock to be available before continuing; in this chapter
you'll always set it to true. (When the thread is waiting, it's said
to be *blocked*.)]

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
            task.run()
```

When using locks, it's super important to remember to release the lock
eventually and to hold it for the shortest time possible. The code
above, for example, why releases the lock before running the `task`.
That's because after the task has been removed from the queue, it
can't be accessed by another thread, so the lock does not need to be
held while the task is running.

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

[cores]: https://en.wikipedia.org/wiki/Multi-core_processor

Long-lived threads
==================

Threads can also be used to add browser multitasking. For example, in
[Chapter 10](security.md#cross-site-requests) we implemented the
`XMLHttpRequest` class, which lets scripts make requests to other
websites. But in our implementation, the whole browser would seize up
while waiting for the request to finish. That's obviously bad.^[For
this reason, the synchronous version of the API that we implemented in
Chapter 10 is basically useless and a huge performance footgun. Some
browsers are now moving to deprecate the synchronous version of this
API.]

Threads let us do better. In Python, the code

    threading.Thread(target=callback).start()
    
creates a new thread that runs the `callback` function. Importantly,
this code returns right away, and `callback` runs in parallel with any
other code. We'll use this to implement asynchronous `XMLHttpRequest`
calls: we'll have the browser start a thread, do the request and parse
the response on that thread, and then schedule a `Task` to send the
response back to the script.

Like with `setTimeout`, we'll store the callback on the
JavaScript side and refer to it with a handle:

``` {.javascript file=runtime}
XHR_REQUESTS = {}

function XMLHttpRequest() {
    this.handle = Object.keys(XHR_REQUESTS).length;
    XHR_REQUESTS[this.handle] = this;
}
```

When a script calls the `open` method on an `XMLHttpRequest` object,
we'll now allow the `is_async` flag to be true:[^async-default]

[^async-default]: In browsers, the default for `is_async` is `true`,
    which the code below does not implement just for expedience.

``` {.javascript file=runtime}
XMLHttpRequest.prototype.open = function(method, url, is_async) {
    this.is_async = is_async
    this.method = method;
    this.url = url;
}
```

The `send` method will need to send over the `is_async` flag and the
handle:

``` {.javascript file=runtime}
XMLHttpRequest.prototype.send = function(body) {
    this.responseText = call_python("XMLHttpRequest_send",
        this.method, this.url, this.body, this.is_async, this.handle);
}
```

On the browser side, we'll need to split the `XMLHttpRequest_send`
function into three parts. The first part will resolve the URL and
do security checks:

``` {.python}
class JSContext:
    def XMLHttpRequest_send(self, method, url, body, is_async,
        handle):
        full_url = resolve_url(url, self.tab.url)
        if not self.tab.allowed_request(full_url):
            raise Exception("Cross-origin XHR blocked by CSP")
        if url_origin(full_url) != url_origin(self.tab.url):
            raise Exception(
                "Cross-origin XHR request not allowed")
```

Then, we'll define a function that makes the request and enqueues a
task for running callbacks:

``` {.python}
class JSContext:
    def XMLHttpRequest_send(self, method, url, body, is_async,
        handle):
        # ...
        def run_load():
            headers, local_body = request(
                full_url, self.tab.url, payload=body)
            task = Task(self.dispatch_xhr_onload, body, handle)
            self.tab.task_runner.schedule_task(task)
            return local_body
```

Finally, depending on the `is_async` flag the browser will either call
this function right away, or in a new thread using the `target`
argument to the `Thread` constructor:

``` {.python}
class JSContext:
    def XMLHttpRequest_send(self, method, url, body, is_async,
        handle):
        # ...
        if not is_async:
            return run_load(is_async)
        else:
            load_thread = threading.Thread(target=run_load)
            load_thread.start()
```

Note that in the async case, the `XMLHttpRequest_send` method starts a
thread and then immediately returns. That thread will run in parallel
to the browser's main work until it adds a new task for running
`dispatch_xhr_onload` on the main thread. This method runs the
JavaScript callback:

``` {.python}
XHR_ONLOAD_CODE = "__runXHROnload(dukpy.out, dukpy.handle)"

class JSContext:
    def dispatch_xhr_onload(self, out, handle):
        do_default = self.interp.evaljs(
            XHR_ONLOAD_CODE, out=out, handle=handle)
```

The `__runXHROnload` method just pulls the relevant object from
`XHR_REQUESTS` and calls its `onload` function:

``` {.javascript}
function __runXHROnload(body, handle) {
    var obj = XHR_REQUESTS[handle];
    var evt = new Event('load');
    obj.responseText = body;
    if (obj.onload)
        obj.onload(evt);
}
```

So tasks not only allow our browser to delay tasks until later, but
also allow applications running in the browser to do the same.
However, there's a whole other category of work done by the browser
not directly related to running JavaScript.

::: {.further}

While it looks simple and maybe even obvious in retrospect, the `XMLHttpRequest`
API played a key role in the evolution from the "90s web" that relied on
loading new pages whenever anyone clicked a link or submitted a form. With the
async version of this API, web pages were able to act a whole lot more like
an *application* than a page of information. This ushered in a new generation
of web sites that used this technique; GMail is one famous early example that
dates from April 2004, [soon after][xhr-history] all browsers finished adding
support for the API.

[xhr-history]: https://en.wikipedia.org/wiki/XMLHttpRequest#History

These new applications used an approach that is now called a [single-page app,
or SPA][spa], as opposed to the earlier multi-page app, or MPA. An SPA replaces
page loads with mutations to the DOM. This led to more and more interactive and
complex web apps, which in turn greatly increased the need for browser
rendering to be faster and more efficiently scheduled.

[spa]: https://en.wikipedia.org/wiki/Single-page_application

:::

Rendering pipeline tasks
========================

So far we've focused on creating tasks that run JavaScript code. But
the results of that JavaScript code---and also the results of
interactions like loading new pages, scrolling, clicking, and
typing---are only available to the user after the browser renders the
page. In this sensem, the most important task in a browser is running
the [rendering pipeline][graphics-pipeline]: styling the HTML elements,
constructing the layout tree, computing sizes and positions, painting
layout objects to a display list, rastering the result into surfaces,
and drawing those surfaces to the screen.

[graphics-pipeline]: https://en.wikipedia.org/wiki/Graphics_pipeline

Right now, the browser executes these rendering steps eagerly: as soon
as the user scrolls or clicks, or as soon as JavaScript modifies the
document. But we want to make these interactions faster and smoother,
and the very first step in doing so is to make rendering a schedulable
task, so we can decide when it occurs.

At a high level, that requires code like this:

``` {.python expected=False}
self.task_runner.schedule_task(Task(self.render))
```

However, rendering is special in that it never makes sense to do
scheduling twice in a row, since the page wouldn't have changed in
between. To avoid having two rendering tasks we'll add a boolean
called `needs_animation_frame` to each `Tab` which indicates
whether a rendering task is scheduled:

``` {.python}
class Tab:
    def __init__(self, browser):
        # ...
        self.needs_animation_frame = False
```

A new `schedule_animation_frame`[^animation-frame] method will check
the flag before scheduling a new rendering task:

[^animation-frame]: It's called an "animation frame" because
sequential rendering of different pixels is an animation, and each
time you render it's one "frame"---like a drawing in a picture frame.

``` {.python expected=False}
class Tab:
    def schedule_animation_frame(self):
        if self.needs_animation_frame:
            return
        self.needs_animation_frame = True
        self.task_runner.schedule_task(Task(self.run_animation_frame))

    def run_animation_frame(self):
        self.render()
        self.needs_animation_frame = False
```

Now, take a look at all the other calls to `render` in your `Tab` and
`JSContext` methods. Instead of calling `render`, which causes the
browser to immediately rerun the rendering pipeline, these methods
should schedule the rendering pipeline to run later. For
future-proofing, I'm doing to do this in a new `set_needs_render`
call:

``` {.python expected=False}
class Tab
    def set_needs_render(self):
        self.schedule_animation_frame()
```

So, for example, the `load` method can call
`set_needs_render`:

``` {.python}
class Tab:
    def load(self, url, body=None):
        # ...
        self.set_needs_render()
```

As can `innerHTML_set`:

``` {.python}
class JSContext:
    def innerHTML_set(self, handle, s):
        # ...
        self.tab.set_needs_render()
```

There are more calls to `render`; you should find and fix all of them.

So this handles the front half of the rendering pipeline: style,
layout, and paint. The back half of the rendering pipeline (raster and
draw) is handled by `Browser`, so the `Tab` needs to tell the
`Browser` to run it. I'll add a new `raster_and_draw` method for the
`Tab` to call:

``` {.python expected=False}
class Tab:
    def __init__(self, browser):
        self.browser = browser

    def run_animation_frame(self):
        # ...
        browser.raster_and_draw()

class Browser:
    def raster_and_draw(self):
        self.raster_chrome()
        self.raster_tab()
        self.draw()
```

This system is getting complex, with the `Browser` and `Tab` each
requesting additional work of the other, so for now let's try to
simplify it by making everything go through the same series of steps.
Any time the `Browser` does anything that can affect the page, like
scrolling, it should call `set_needs_render` instead of calling
`raster_tab` or similar. Then it's up to `set_needs_render` to cause
the raster task to be run:

``` {.python expected=False}
class Browser:
    def handle_down(self):
        # ...
        self.active_tab.set_needs_render()
```

This lets us thinking of both halves of rendering as one single
pipeline that's either run or not in a single unit.

::: {.further}

It was not until the second decade of the 2000s that all modern browsers
finished adopting a scheduled, task-based approach to rendering. Once the need
became apparent due to the emergence of complex interactive web applications,
it still took years of effort to safely refactor all of the complex existing
browser codebases. In fact, in some ways it is
only [very recently][renderingng] that this process can perhaps be said to have
completed. Though since software can always be improved, in some sense the work
is never done.

:::

[renderingng]: https://developer.chrome.com/blog/renderingng/

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

::: {.further}

Before the `requestAnimationFrame` API, developers approximated it with code
like this:

``` {.javascript expected=False}
function callback() {
    // Mutate DOM for rendering
    setTimeout(callback, 16);
}
setTimeout(callback, 16);
```

This sort of worked, but had multiple drawbacks. One was that there is no
guarantee that the callbacks would cohere with the speed or timing of
rendering. For example, sometimes two callbacks in a row could happen without
any rendering between, which doubles the script work for rendering for no
benefit.

Another is that there is no guarantee that other tasks would not run between the
callback and rendering. If the callback was setting up the DOM for rendering,
but then a script click event handler occurs before *actually* rendering, the
app might be forced to re-do its DOM mutations to avoid a delayed response to
the click---yet another example of doubled rendering.

A third is that there is no great way to turn off "rendering" `setTimeout` work
when a web page window is backgrounded, minimized or otherwise throttled. If
the browser chooses to stop all tasks, then it would also break any important
background work the web app might want to do (such as syncing your information
to the server so it's not lost).

:::

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

Profiling rendering
===================

We now have a system for scheduling a rendering task every 16ms. But
what if rendering takes longer than 16ms to finish? Before we answer
this question, let's instrument the browser and measure how much time
is really being spent rendering. It's important to always measure
before optimizing, because the result is often surprising.

Let's implement some simple instrumentation to measure time. We'll
want to average across multiple raster-and-draw cycles:

``` {.python}
class MeasureTime:
    def __init__(self, name):
        self.name = name
        self.start_time = None
        self.total_s = 0
        self.count = 0

    def text(self):
        if self.count == 0:
            return
        avg = self.total_s / self.count
        return "Time in {} on average: {:>.0f}ms".format(self.name, avg * 1000)
```

We'll measure the time for something like raster and draw by just
calling `start` and `stop` methods on one of these `MeasureTime`
objects:

``` {.python}
class MeasureTime:
    def start(self):
        self.start_time = time.time()

    def stop(self):
        self.total_s += time.time() - self.start_time
        self.count += 1
        self.start_time = None
```

Let's measure the total time for both render:

``` {.python}
class Tab:
        # ...
        self.measure_render = MeasureTime("render")

    def render(self):
        if not self.needs_render:
            return
        self.measure_render.start()
        # ...
        self.measure_render.stop()
```

And raster-and-draw:


``` {.python}
class Browser:
    def __init__(self):
        self.measure_raster_and_draw = MeasureTime("raster-and-draw")

    def raster_and_draw(self):
        if not self.needs_raster_and_draw:
            return
        self.lock.acquire(blocking=True)
        self.measure_raster_and_draw.start()
        # ...
        self.measure_raster_and_draw.stop()
```

We can print out the timing measures when we quit:

``` {.python}
class Tab:
    def handle_quit(self):
        print(self.tab.measure_render.text())

class Browser:
    def handle_quit(self):
        print(self.measure_raster_and_draw.text())
```

Naturally we'll need to call the `Tab`'s `handle_quit` method before
quitting, so it has a chance to print its timing data.

Now fire up the server, open our timer script, wait for it to finish
counting, and then exit the browser. You should see it output timing
data like this (from my computer):

    Time in raster-and-draw on average: 66ms
    Time in render on average: 20ms

You can see that the browser spent about 20ms in `render` and about
66ms in `raster_and_draw` per animation frame. That clearly blows
through our 16ms budget. So, what can we do?

Well, one option, of course, is optimizing raster-and-draw, or even
render. And if we can, it's a great choice.[^see-go-further] But
another option---complex, but worthwhile and done by every major
browser---is to do the render step in parallel with the
raster-and-draw step by adopting a multi-threaded architecture.

[^see-go-further]: See the go further at the end of this section for
    some ideas on how to do this.

::: {.further}
In our browser, a lot of time is spent in each drawing-into-surface
step. That's why [optimizing surfaces][optimize-surfaces] is
important! Modern browsers go a step further and perform raster and
draw [on the GPU][skia-gpu], where a lot more parallelism is
available. Even so, on complex pages raster and draw really do
sometimes take a lot of time.
:::

[optimize-surfaces]: visual-effects.md#optimizing-surface-use

[skia-gpu]: https://skia.org/docs/user/api/skcanvas_creation/#gpu

::: {.further}
Even with a second thread, the browser thread can wait up to 66ms
before *starting* to handle a click event! For this reason, modern
browsers use [*yet more*][renderingng-architecture] threads or
processes. For example, raster-and-draw might run on its own thread,
so that it can't block event handling. This makes the browser thread
extremely responsive to input, at the cost of even more complexity.
:::

[renderingng-architecture]: https://developer.chrome.com/blog/renderingng-architecture/#process-and-thread-structure


::: {.further}
Threads are a much more powerful construct in recent decades, due to the
emergence of multi-core CPUs. Before that, threads existed, but were a
mechanism for improving *responsiveness* via pre-emptive multitasking, 
but without increasing *throughput* (fraames per second).

These days, a typical desktop computer can run many threads simultaneously, and
even phones have several cores plus a highly parallel GPU. However, on phones
it's difficult to make maximum use of all of the threads for rendering
parallelism, because if you turn on all of the cores, the battery will drain
quickly. In addition, there are usually system processes (such as to listen
to the wireless radio or manage the screen and input) running in the background
on one or more cores anyway, so the actual parallelism available to the browser
might be in effect just two cores.
:::

Two threads
===========

Running rendering in parallel with raster and draw would allow us to
produce a new frame every 66ms, instead of every 88ms. Moreover, since
there's no point to running render more often than raster-and-draw,
the render thread would have 66ms to render each frame, and after the
20ms spent rendering there would be 46ms left over for running
JavaScript. Finally, events could be handled with a delay of no more
than 20ms, which makes the browser much more responsive. That's more
than enough of a win to justify a second thread.

Let's call our two threads the *browser thread*[^also-compositor] and
the *main thread*.[^main-thread-name] The *browser thread* corresponds
to the `Browser` class and will handle raster and draw. It'll also
handle interactions with the browser chrome. The *main thread*, on the
other hand, corresponds to a `Tab` and will handle running scripts,
loading resources, and rendering, along with associated tasks like
running event handlers and callbacks. If you've got more than one tab
open, you'll have multiple main threads (one per tab) but only one
browser thread.

[^also-compositor]: In modern browsers the analogous thread is often
    called the [*compositor thread*][cc], though modern browsers have
    lots of threads and the correspondence isn't exact.

[cc]: https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/how_cc_works.md

[^main-thread-name]: Here I'm going with the name real browsers often
use. A better name might be the "JavaScript" or "DOM" thread (since
JavaScript can sometimes run on [other threads][webworker]).

[webworker]: https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API

Now, multi-threaded architectures are tricky, so let's do a little planning.

To start, the one thread that exists already---the one that runs when
you start the browser---will be the browser thread. We'll make a main
thread every time we create a tab. These two threads will need to
communicate to handle events and draw to the screen.

When the browser thread needs to communicate with the main thread (to
inform it of events), it'll place tasks on the main thread's
`TaskRunner`. In the other direction, the main thread will need to
communicate with the browser thread to request animation frames and to
send it a display list to raster and draw. The main thread will do
that via two methods on `browser`: `set_needs_animation_frame` to
request an animation frame and `commit` to send it a display list.

The overall control flow for rendering a frame will therefore be:

1. The main thread code requests an animation frame with
   `set_needs_animation_frame`, perhaps in response to an event
   handler or due to `requestAnimationFrame`.
2. The browser thread event loop schedules an animation frame on
   the main thread `TaskRunner`.
3. The main thread executes its part of rendering, then calls
   `browser.commit`.
4. The browser rasters the display list and draws to the screen.

Let's implement this design. To start, we'll add a `Thread` to
`TaskRunner` to be the main thread. This thread will need to run in a
loop, pulling tasks from the task queue and running them. We'll put
that loop inside the `TaskRunner`'s `run` method.

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
                task.run()
```

Because this loop runs forever, the main thread will live
indefinitely.

The `Browser` should no longer call any methods on the `Tab`. So, to
handle events, it now needs schedule tasks on the main thread instead.
For example, here is loading:

``` {.python}
class Browser:
    def schedule_load(self, url, body=None):
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.load, url, body)
        active_tab.task_runner.schedule_task(task)

    def handle_enter(self):
        if self.focus == "address bar":
            self.schedule_load(self.address_bar)
            # ...

    def load(self, url):
        # ...
        self.schedule_load(url)
```

Event handlers are mostly similar, except that we need to be careful
to distinguish events that affect the browser chrome from those that
affect the tab. For example, consider `handle_click`. If the user
clicked on the browser chrome (meaning `e.y < CHROME_PX`), we can
handle it right there in the browser thread. But if the user clicked
on the web page, we must schedule a task on the main thread:

``` {.python}
class Browser:
    def handle_click(self, e):
        self.lock.acquire(blocking=True)
        if e.y < CHROME_PX:
             # ...
        else:
            # ...
            active_tab = self.tabs[self.active_tab]
            task = Task(active_tab.click, e.x, e.y - CHROME_PX)
            active_tab.task_runner.schedule_task(task)
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
            task = Task(active_tab.keypress, char)
            active_tab.task_runner.schedule_task(task)
        self.lock.release()
```

Do the same with any other calls from the `Browser` to the `Tab`.

Communication in the other direction is a little subtler. We already
have the `set_needs_animation_frame` method, but now we need the `Tab`
to call `commit` when it's finished creating a display list.

If you look carefully at our raster-and-draw code, you'll see that to
draw a display list we also need to know the URL (to update the
browser chrome), the document height (to allocate a surface of the
right size), and the scroll position (to draw the right part of the
surface). Let's make a simple class for storing this data:

``` {.python}
class CommitForRaster:
    def __init__(self, url, scroll, height, display_list):
        self.url = url
        self.scroll = scroll
        self.height = height
        self.display_list = display_list
```

When running an animation frame, the `Tab` should construct one of
these objects and pass it to `commit`:

``` {.python replace=self.scroll%2c/scroll%2c,(self)/(self%2c%20scroll)}
class Tab:
    def __init__(self, browser):
        # ...
        self.browser = browser

    def run_animation_frame(self):
        # ...
        commit_data = CommitForRaster(
            url=self.url,
            scroll=self.scroll,
            height=document_height,
            display_list=self.display_list,
        )
        self.display_list = None
        self.browser.commit(self, commit_data)
```

We should think of the `CommitForRaster` object as being sent from the
main thread to browser thread. That means the main thread shouldn't
access it any more, and for this reason I'm resetting the
`display_list` field.

On the `Browser` side, the new `commit` method needs to read out all
of the data it was sent and call `set_needs_raster_and_draw` as
needed.

``` {.python}
class Browser:
    def __init__(self):
        self.url = None
        self.scroll = 0

    def commit(self, tab, commit):
        self.lock.acquire(blocking=True)
        if tab == self.tabs[self.active_tab]:
            self.display_scheduled = False
            self.url = commit.url
            self.scroll = commit.scroll
            self.active_tab_height = commit.height
            self.active_tab_display_list = commit.display_list
            self.set_needs_raster_and_draw()
        self.lock.release()
```

Note that `commit` is called on the main thread, but acquires the
browser thread lock. As a result, `commit` is a critical time when
both threads are both "stopped" simultaneously.[^fast-commit] Also
note that, it's possible for the browser thread to get a `commit` from
an inactive tab,[^inactive-tab-tasks] so the `tab` parameter is
compared with the active tab to before copying any data over from the
commit.

[^fast-commit]: For this reason commit needs to be as fast as
possible, to maximize parallelism and responsiveness. In modern browsers,
optimizing commit is quite challenging.

[^inactive-tab-tasks]: That's because even inactive tabs are still
running their main threads and responding to callbacks from
`setTimeout` or `XMLHttpRequest`.

This architecture broadly works, but we need to make sure that the
*browser thread* determines the cadence of animation frames, *not* the
main thread, since there's no point to rendering display lists faster
than they can be drawn to the screen. To do so, we need to prevent
inactive tabs from requesting animation frames.

We'll implement this with a `needs_animation_frame` dirty bit on
`Browser`. When a tab needs an animation frame,
`set_needs_animation_frame` will check whether the tab is active
before setting the dirty bit. Methods in `Browser` can just set
`needs_animation_frame` directly instead of calling
`set_needs_animation_frame`.

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.needs_animation_frame = False

    def set_needs_animation_frame(self, tab):
        self.lock.acquire(blocking=True)
        if tab == self.tabs[self.active_tab]:
            self.needs_animation_frame = True
        self.lock.release()

    def set_needs_raster_and_draw(self):
        # ...
        self.needs_animation_frame = True

    def set_active_tab(self, index):
        # ...
        self.needs_animation_frame = True
```

In the main thread, we'll need to pass in the current tab when
requesting an animation frame:

``` {.python}
class Tab:
    def set_needs_render(self):
        # ...
        self.browser.set_needs_animation_frame(self)

    def request_animation_frame_callback(self):
        # ...
        self.browser.set_needs_animation_frame(self)
```

Because only active tabs can request an animation frame,
`requestAnimationFrame` callbacks won't run on inactive frames, which
is what we want. For example, try making a second tab while the
counter demo is running, then go back to the demo tab. It should stop
counting while another tab is active, and resume when it is made
active again!

Now tabs only set the dirty bit, and the browser thread can decide how
often it should schedule an animation frame. For example it can do so
only once the browser thread is done drawing to the
screen:[^backpressure]

[^backpressure]: The technique of controlling the speed of the front of a
pipeline by means of the speed of its end is called *back pressure*.

``` {.python}
if __name__ == "__main__":
    while True:
        # ...
        browser.raster_and_draw()
        browser.schedule_animation_frame()
```

The `schedule_animation_frame` method on `Browser` works just like our
earlier implementation on `Tab`:

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

And that's it: we should now be doing render on one thread and raster
and draw on another!

::: {.further}
Unfortunately, Python currently has a [global interpreter lock][gil],
so our two Python threads don't truly run in parallel,[^why-gil]
so our browser's *throughput* won't increase much from multi-threading.
Nonetheless, the *responsiveness* of the browser thread is still
massively improved, since it often isn't blocked on JavaScript or the
front half of the rendering pipeline. This is an unfortunate
limitation of Python that doesn't affect real browsers, so try to
pretend it's not there.[^why-locks]
:::

[gil]: https://wiki.python.org/moin/GlobalInterpreterLock

[^why-gil]: It's possible to turn off the global interpreter lock
while running foreign C/C++ code linked into a Python library. Skia is
thread-safe, but SDL may not be.

[^why-locks]: Despite the global interpreter lock, we still need
locks. Each Python thread can still yield between bytecode operations,
so you can still get concurrent accesses to shared variables, and race
conditions are still possible. And in fact, while debugging the code
for this chapter, I encountered this kind of race condition when I
forgot to add a lock; try removing some of the locks from your browser
to see for yourself!


Threaded scrolling
==================

Splitting the main thread from the browser thread means that the main
thread can run a lot of JavaScript without slowing down the browser
much. But it's still possible for really slow JavaScript to slow the
browser down. For example, imagine our counter adds the following
artificial slowdown:

``` {.javascript file=eventloop}
function callback() {
    for (var i = 0; i < 5e6; i++);
    // ...
}
```

Now, every tick of the counter has an artificial pause during which
the main thread is stuck running JavaScript. This means it can't
respond to any events; for example, if you hold down the down key, the
scrolling will be janky and annoying. I encourage you to try this and
witness how annoying it is, because modern browsers usually don't have
this kind of jank.

To fix this, we need to move scrolling from the main thread to the
browser thread. This is harder than it might seem, because the scroll
offset can be affected by both the browser (when the user scrolls) and
the main thread (when loading a new page or changing the height of the
document via `innerHTML`). Now that the browser thread and the main
thread run in parallel, they can disagree about the scroll offset.

What should we do? The best we can do is to use the browser thread's
scroll offset until the main thread tells us otherwise, unless that
scroll offset is incompatible with the web page (by, say, exceeding
the document height). To do this, we'll need the browser thread to
inform the main thread about the current scroll offset, and then give
the main thread the opportunity to *override* that scroll offset or to
leave it unchanged.

Let's implement that. To start, we'll need to store a `scroll`
variable on the `Browser`, and update it when the user scrolls:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.scroll = 0

    def handle_down(self):
        # ...
        self.scroll = scroll
        self.set_needs_raster_and_draw()
```

This code sets `needs_raster_and_draw` to apply the new scroll offset.

The scroll offset also needs to change when the user switches tabs,
but in this case we don't know the right scroll offset yet. We need
the main thread to run in order to commit a new display list for the
other tab, and at that point we will have a new scroll offset as well.
So in `set_active_tab`, we simply schedule a new animation frame:

``` {.python}
class Browser:
    def set_active_tab(self, index):
        self.active_tab = index
        self.needs_animation_frame = True
```

So far, this is only updating the scroll offset on the browser thread.
But the main thread eventually needs to know about the scroll offset,
so it can pass it back to `commit`. So, when the `Browser` creates a
rendering task for `run_animation_frame`, it should pass in the scroll
offset. The `run_animation_frame` function can then store the scroll
offset before doing anything else.

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
            task = Task(active_tab.run_animation_frame, scroll)
            active_tab.task_runner.schedule_task(task)
            self.lock.release()
        # ...
```

Now the browser thread can update the scroll offset. But the main
thread can also modify the scroll offset, for example overriding it to
0 when it loads a new page. We'll set a `scroll_changed_in_tab` flag
to record when this happens:

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
        document_height = math.ceil(self.document.height)
        clamped_scroll = clamp_scroll(self.scroll, document_height)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_tab = True
        self.scroll = clamped_scroll
        # ...
        self.scroll_changed_in_tab = False
```

Now `commit` can override the browser-passed scroll offset if this
flag is set:

``` {.python}
class Tab:
    def run_animation_frame(self, scroll):
        # ...
        scroll = None
        if self.scroll_changed_in_tab:
            scroll = self.scroll
        commit_data = CommitForRaster(
            url=self.url,
            scroll=scroll,
            height=document_height,
            display_list=self.display_list,
        )
        # ...
```

Note that if the tab hasn't changed the scroll offset, we'll be
committing a scroll offset of `None`. The browser thread can ignore
the scroll offset in this case:

``` {.python}
class Browser:
    def commit(self, tab, commit):
        if tab == self.tabs[self.active_tab]:
            # ...
            if commit.scroll != None:
                self.scroll = commit.scroll
```

That's it! If you try the counting demo now, you'll be able to scroll
even during the artificial pauses. As you've seen, moving tasks to the
browser thread can be challenging, but can also lead to a much more
responsive browser. These same trade-offs are present in real
browsers, at a much greater level of complexity.

::: {.further}
Scrolling in real browsers goes *way* beyond what we've implemented
here. For example, in a real browser JavaScript can listen to a scroll
[`scroll`][scroll-event] event and call `preventDefault` to cancel
scrolling. And some rendering features like [`background-attachment:
fixed`][mdn-bg-fixed] are hard to implement on browser thread.[^not-supported] For this
reason, most real browsers implement both threaded and non-threaded
scrolling, and fall back to non-threaded scrolling when these advanced
features are used.[^real-browser-threaded-scroll] Concerns like this
also drive [new JavaScript APIs][designed-for].
:::

[scroll-event]: https://developer.mozilla.org/en-US/docs/Web/API/Document/scroll_event

[^real-browser-threaded-scroll]: Actually, a real browser only fall
back to non-threaded scrolling when necessary. For example, it might
disable threaded scrolling only if is a `scroll` event listener.

[mdn-bg-fixed]: https://developer.mozilla.org/en-US/docs/Web/CSS/background-attachment

[designed-for]: https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/addEventListener#improving_scrolling_performance_with_passive_listeners

[^not-supported]: Our browser doesn't support any of these features,
so it doesn't run into these difficulties. That's also a strategy;
until 2020, Chromium-based browsers on Android, for example, did not
support `background-attachment: fixed`.

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
setting aside JavaScript APIs, there are unfortunately *even more* sources of
forced style and layout. One example is our current implementation of `click`.
The first line of this method forces a layout:

``` {.python}
class Tab:
    def click(self, x, y):
        self.render()
        # ...
```

The call to `render` is a forced layout. It's needed because
clicking needs to run hit testing, which in turn requires layout. Fixing this
would require even more fancy technology.

It's not impossible to move style and layout off the main thread
"optimistically", but here I outlined some of the reasons it's challenging. I
 expect that at some point in the future it will be achieved (maybe you'll be
 the one to do it?).

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
screen, handles/dispatches input events, and scrolls.

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

* *Threaded loading*: When loading a page, our browser currently waits for each
   style sheet or script resource to load in turn. This is unnecessarily slow,
   especially on a bad network. Sending off all the network requests in
   parallel would speed up loading substantially (and all modern browsers do
   so). Now that we have threads available, this optimization is
   straightforward; implement it. (Tip: it may be convenient to use the `join`
   method on a `Thread`, which will block the thread calling `join` until the
   other thread completes. This will allow you to still have a single `load`
   method that only returns once everything is done.)

   If you want an additional challenge, try this: real browsers tend
   to have a separate thread for networking (and other I/O) instead of creating
   a one thread per request. Tasks are added to this thread in a similar
   fashion to the main thread. Implement a third *networking* thread and put
   all networking tasks on it.

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
