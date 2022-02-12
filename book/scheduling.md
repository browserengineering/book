---
title: Scheduling Tasks and Threads
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

Here I've chosen to only run tasks on the active tab, which means
background tabs can't slow our browser down.

With this simple task runner, we can now save tasks and execute them
later. For example, right now, when loading a web page, our browser
will download and run all scripts before doing its rendering steps.
That makes pages slower to load. We can fix this by creating tasks for
running scripts later:

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
            task = Task(self.run_script, script_url, body)
            self.task_runner.schedule_task(task)
```

Now our browser will not run scripts until after `load` has completed
and the event loop comes around again.

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
[`setTimeout`][settimeout] lets you run a JavaScript function some
number of milliseconds from now. This code prints "Callback" to the
console one second frow now:

[settimeout]: https://developer.mozilla.org/en-US/docs/Web/API/setTimeout

``` {.javascript expected=false}
function callback() { console.log('Callback'); }
setTimeout(callback, 1000);
```

We can implement `setTimeout` using the [`Timer`][timer] class in
Python's [`threading`][threading] module. You use the class like
this:[^polling]

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

This runs `callback` one second from now on a new Python thread.
Simple, but it's going to be a little tricky to use `Timer` to
implement `setTimeout` because multiple threads will be involved.

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
requested time period, and then ask the JavaScript runtime to run the
callback. That last part will happen via `__runSetTimeout`:[^mem-leak]

[^mem-leak]: Note that we never remove `callback` from
    `SET_TIMEOUT_REQUESTS` dictionary. This could lead to a memory
    leak, if the callback it holding on to the last reference to some
    large data structure. We saw a similar issue in [Chapter
    9](scripts.md). In general, avoiding memory leaks when you have
    data structures shared between the browser and the browser
    application takes a lot of care.

``` {.javascript file=runtime}
function __runSetTimeout(handle) {
    var callback = SET_TIMEOUT_REQUESTS[handle]
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
SETTIMEOUT_CODE = "__runSetTimeout(dukpy.handle)"

class JSContext:
    def __init__(self, tab):
        # ...
        self.interp.export_function("setTimeout",
            self.setTimeout)

    def dispatch_settimeout(self, handle):
        self.interp.evaljs(SETTIMEOUT_CODE, handle=handle)

    def setTimeout(self, handle, time):
        def run_callback():
            task = Task(self.dispatch_settimeout, handle)
            self.tab.task_runner.schedule_task(task)
        threading.Timer(time / 1000.0, run_callback).start()

```

This way it's ultimately the primary thread that calls `evaljs`,. But
now we have two threads accessing the `task_runner`: the main thread,
to run tasks, and the timer thread, to add them. This is a [race
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
browsers are now moving to deprecate synchronous `XMLHttpRequest`.]

Threads let us do better. In Python, the code

    threading.Thread(target=callback).start()
    
creates a new thread that runs the `callback` function. Importantly,
this code returns right away, and `callback` runs in parallel with any
other code. We'll implement asynchronous `XMLHttpRequest` calls using
threads. Specifically, we'll have the browser start a thread, do the
request and parse the response on that thread, and then schedule a
`Task` to send the response back to the script.

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
    which the code below does not implement.

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
    def XMLHttpRequest_send(self, method, url, body, isasync, handle):
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
    def XMLHttpRequest_send(self, method, url, body, isasync, handle):
        # ...
        def run_load():
            headers, response = request(
                full_url, self.tab.url, payload=body)
            task = Task(self.dispatch_xhr_onload, response, handle)
            self.tab.task_runner.schedule_task(task)
            return response
```

Note that the task runs `dispatch_xhr_onload`, which we'll define in
just a moment.

Finally, depending on the `is_async` flag the browser will either call
this function right away, or in a new thread using the `target`
argument to the `Thread` constructor:

``` {.python}
class JSContext:
    def XMLHttpRequest_send(self, method, url, body, isasync, handle):
        # ...
        if not isasync:
            return run_load()
        else:
            load_thread = threading.Thread(target=run_load)
            load_thread.start()
```

Note that in the async case, the `XMLHttpRequest_send` method starts a
thread and then immediately returns. That thread will run in parallel
to the browser's main work until the request is done.

To communicate the result back to JavaScript, we'll call a
`__runXHROnload` function from `dispatch_xhr_onload`:

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

As you can see, tasks allow not only the browser but also applications
running in the browser to delay tasks until later. However, there's a
whole other category of work done by the browser not directly related
to running JavaScript.

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

The cadence of rendering
========================

There's more to tasks than just implementing some JavaScript APIs.
Once something is a `Task`, the task runner controls when it runs:
now, later, at most once a second, at different rates for active and
inactive pages, or according to its priority. A browser could even
have multiple task runners, optimized for different use cases.

Now, it might be hard to see how the browser can prioritize which
JavaScript callback to run, or why it might want to execute JavaScript
tasks at a fixed cadence. But besides JavaScript the browser also has
to render the page, and as you may recall from [Chapter
2](graphics.md#framebudget), we'd like the browser to render the page
exactly as fast as the display hardware can refresh. On most
computers, this is 60 times per second, or 16ms per frame.

Let's establish 16ms our ideal refresh rate:[^why-16ms]

[^why-16ms]: 16 milliseconds isn't that precise, since it's 60 times
    16.66666...ms that is just about equal to 1 second. But it's a toy
    browser!

``` {.python}
REFRESH_RATE_SEC = 0.016 # 16ms
```

Now, there's some complexity here, because we have multiple tabs. We
don't need _each_ tab redrawing itself every 16ms, because the user
only sees one frame at a time. We just need the _active_ tab redrawing
itself. That means that one tab needs to redo styling, layout, and
painting (its `render` method), and then the browser needs to
re-raster itself.

First, let's can write a `schedule_animation_frame`
method[^animation-frame] that schedules a `render` task to run the
`Tab` half of the rendering pipeline:

[^animation-frame]: It's called an "animation frame" because
sequential rendering of different pixels is an animation, and each
time you render it's one "frame"---like a drawing in a picture frame.

``` {.python expected=False}
class Browser:
    def schedule_animation_frame(self):
        def callback():
            active_tab = self.tabs[self.active_tab]
            task = Task(active_tab.render)
            active_tab.task_runner.schedule_task(task)
            self.schedule_animation_frame()
        threading.Timer(REFRESH_RATE_SEC, callback).start()
```

Note how every time a frame is scheduled, we set up a timer to
schedule the next one. We can kick off the process when we start the
Browser:

``` {.python}
if __name__ == "__main__":
    # ...
    browser = Browser()
    browser.schedule_animation_frame()
    # ...
```

Next, let's put the rastering and drawing tasks that the `Browser`
does into their own method:

``` {.python}
class Browser:
    def raster_and_draw(self):
        self.raster_chrome()
        self.raster_tab()
        self.draw()
```

In the top-level loop, when run a task on the active tab the browser
will need to raster-and-draw, in case that task was a rendering task:

``` {.python expected=False}
if __name__ == "__main__":
    while True:
        # ...
        browser.tabs[browser.active_tab].task_runner.run()
        browser.raster_and_draw()
```

Now we're scheduling a new rendering task every 16 milliseconds, just
as we wanted to.

Optimizing the rendering tasks
==============================

If you run this on your computer, there's a good chance your CPU usage
will spike and your batteries will start draining. That's because
we're calling `render` every frame, which means our browser is now
constantly styling elements, building layout trees, and painting
display lists. Most of that work is wasted, because on most frames,
the web page will not have changed at all, so the old styles, layout
trees, and display lists would have worked just as well as the new
ones.

Let's fix this using a *dirty bit*, a piece of state that tells us if
some complex data structure is up to date. Since we want to know if we
need to run `render`, let's call our dirty bit `needs_render`:

``` {.python}
class Tab:
    def __init__(self, browser):
        # ...
        self.needs_render = False

    def set_needs_render(self):
        self.needs_render = True

    def render(self):
        if not self.needs_render: return
        # ...
        self.needs_render = False
```

One advantage of this flag is that we can now set `needs_render` when
the HTML has changed instead of calling `render` directly. The
`render` will still happen, but later. This makes scripts faster,
especially if they modify the page multiple times. Make this change in
`innerHTML_set`, `load`, `click`, and `keypress`. For example, in
`load`, do this:

``` {.python}
class Tab:
    def load(self, url, body=None):
        # ...
        self.set_needs_render()
```

And in `innerHTML_set`, do this:

``` {.python}
class JSContext:
    def innerHTML_set(self, handle, s):
        # ...
        self.tab.set_needs_render()
```

There are more calls to `render`; you should find and fix all of them.

Another problem with our implementation is that the browser is now
doing `raster_and_draw` every time the active tab runs a task.
But sometimes that task is just running JavaScript that doesn't touch
the web page, and the `raster_and_draw` call is a waste.

We can avoid this using another dirty bit, which I'll call
`needs_raster_and_draw`:

``` {.python}
class Browser:
    def __init__(self):
        self.needs_raster_and_draw = False

    def set_needs_raster_and_draw(self):
        self.needs_raster_and_draw = True

    def raster_and_draw(self):
        if not self.needs_raster_and_draw: return
        # ...
        self.needs_raster_and_draw = False
```

We will need to call `set_needs_raster_and_draw` every time either the
`Browser` changes something about the browser chrome, or any time the
`Tab` changes its rendering. The browser chrome is changed by event
handlers:

``` {.python}
class Browser:
    def handle_click(self, e):
        if e.y < CHROME_PX:
            # ...
            self.set_needs_raster_and_draw()

    def handle_key(self, char):
        if self.focus == "address bar":
            # ...
            self.set_needs_raster_and_draw()

    def handle_enter(self):
        if self.focus == "address bar":
            # ...
            self.set_needs_raster_and_draw()
```

And the `Tab` should also set this bit after running `render`:

``` {.python expected=False}
class Tab:
    def __init__(self, browser):
        # ...
        self.browser = browser
        
    def render(self):
        # ...
        self.browser.set_needs_raster_and_draw()
```

You'll need to pass in the `browser` parameter when a `Tab` is
constructed:

``` {.python}
class Browser:
    def load(self, url):
        new_tab = Tab(self)
        # ...
```

Now the rendering pipeline is only run if necessary, and the browser
should have acceptable performance again.

::: {.further}
The `needs_raster_and_draw` dirty bit is not just for making the browser a
bit more efficient. Later in the chapter, we'll move raster and draw to another
thread. If that bit was not there, then that thread would cause very erratic
behavior when animating. Once you've read the whole chapter and implemented
that thread, try removing this dirty bit and see for yourself!
:::

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

One big reason for a steady rendering cadence is so that animations
run smoothly. Web pages set up such animations using the
[`requestAnimationFrame`][raf] API. This API allows scripts to run
code right before the browser runs its rendering pipeline, making the
animation maximally smooth. It works like this:

[raf]: https://developer.mozilla.org/en-US/docs/Web/API/window/requestAnimationFrame

``` {.javascript.example}
/* This is JavaScript */
function callback() {
    console.log("I was called!");
}
requestAnimationFrame(callback);
```

By calling `requestAnimationFrame`, this code is doing two things:
scheduling a rendering task, and asking that the browser call
`callback` *at the beginning* of that rendering task, before any
browser rendering code. This lets web page authors change the page and
be confident that it will be rendered right away.

The implementation of this JavaScript API is straightforward. We store
the callbacks on the JavaScript side:

``` {.javascript file=runtime}
RAF_LISTENERS = [];

function requestAnimationFrame(fn) {
    RAF_LISTENERS.push(fn);
    call_python("requestAnimationFrame");
}
```

In `JSContext`, when that method is called, we need to schedule a new
rendering task:

``` {.python expected=False}
class JSContext:
    def __init__(self, tab):
        # ...
        self.interp.export_function("requestAnimationFrame",
            self.requestAnimationFrame)

    def requestAnimationFrame(self):
        task = Task(self.tab.render)
        self.tab.task_runner.schedule_task(task)
```

Then, when `render` is actually called, we need to call back into
JavaScript, like this:

``` {.python expected=False}
class Tab:
    def render(self):
        if not self.needs_render: return
        self.js.interp.evaljs("__runRAFHandlers()")
        # ...
```

This `__runRAFHandlers` function is a little tricky:

``` {.javascript file=runtime}
function __runRAFHandlers() {
    var handlers_copy = RAF_LISTENERS;
    RAF_LISTENERS = [];
    for (var i = 0; i < handlers_copy.length; i++) {
        handlers_copy[i]();
    }
}
```

Note that `__runRAFHandlers` needs to reset `RAF_LISTENERS` to the
empty array before it runs any of the callbacks. That's because one of
the callbacks could itself call `requestAnimationFrame`. If this
happens during such a callback, the spec says that a *second*
animation frame should be scheduled. That means we need to make sure
to store the callbacks for the *current* frame separately from the
callbacks for the *next* frame.

This situation may seem like a corner case, but it's actually very
important, as this is how pages can run an *animation*: by iteratively
scheduling one frame after another. For example, here's a simple
counter "animation":

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

This script will cause 100 animation frame tasks to run on the
rendering event loop. During that time, our browser will display an
animated count from 0 to 99.

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

One flaw with our implementation so far is that an unattentive coder
might call `requestAnimationFrame` multiple times and thereby schedule
more animation frames than expected. If other JavaScript tasks appear
later, they might end up delayed by many, many frames.

Luckily, rendering is special in that it never makes sense to have two
rendering tasks in a row, since the page wouldn't have changed in
between. To avoid having two rendering tasks we'll add a dirty bit
called `needs_animation_frame` to the `Browser` which indicates
whether a rendering task actually needs to be scheduled:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.needs_animation_frame = True

    def schedule_animation_frame(self):
        # ...
        if self.needs_animation_frame:
            threading.Timer(REFRESH_RATE_SEC, callback).start()
            self.needs_animation_frame = False
```

A tab will set the `needs_animation_frame` flag when an animation
frame is requested:

``` {.python}
class JSContext:
    def requestAnimationFrame(self):
        self.tab.browser.set_needs_animation_frame(self.tab)

class Tab:
    def set_needs_render(self):
        # ...
        self.browser.set_needs_animation_frame(self)

class Browser:
    def set_needs_animation_frame(self, tab):
        if tab == self.tabs[self.active_tab]:
            self.needs_animation_frame = True
```

Note that `set_needs_animation_frame` will only actually set the dirty
bit if called from the active tab. This guarantees that inactive tabs
can't interfere with active tabs. Besides preventing scripts from
scheduling too many animation frames, this system also makes sure that
if our browser consistently runs slower than 60 frames per second, we
won't end up with an ever-growing queue of rendering tasks.

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
        if self.count == 0: return ""
        avg = self.total_s / self.count
        return "Time in {} on average: {:>.0f}ms".format(
            self.name, avg * 1000)
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

Let's measure the total time for render:

``` {.python}
class Tab:
        # ...
        self.measure_render = MeasureTime("render")

    def render(self):
        if not self.needs_render: return
        self.measure_render.start()
        # ...
        self.measure_render.stop()
```

And also raster-and-draw:


``` {.python}
class Browser:
    def __init__(self):
        self.measure_raster_and_draw = MeasureTime("raster-and-draw")

    def raster_and_draw(self):
        if not self.needs_raster_and_draw: return
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

Fire up the server, open our timer script, wait for it to finish
counting, and then exit the browser. You should see it output timing
data. On my computer, it looks like this:

    Time in raster-and-draw on average: 66ms
    Time in render on average: 20ms

On every animation frame, my browser spent about 20ms in `render` and
about 66ms in `raster_and_draw`. That clearly blows through our 16ms
budget. So, what can we do?

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

Remove the call to `run` from the top-level `while True` loop, since
that loop is now going to be the browser thread.

Each iteration of the `run` loop will pick which scheduled task to run
next. I'll stick with first-in first-out:

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
        if e.y < CHROME_PX:
             # ...
        else:
            # ...
            active_tab = self.tabs[self.active_tab]
            task = Task(active_tab.click, e.x, e.y - CHROME_PX)
            active_tab.task_runner.schedule_task(task)
```

The same logic holds for `keypress`:

``` {.python}
class Browser:
    def handle_key(self, char):
        if not (0x20 <= ord(char) < 0x7f): return
        if self.focus == "address bar":
            # ...
        elif self.focus == "content":
            active_tab = self.tabs[self.active_tab]
            task = Task(active_tab.keypress, char)
            active_tab.task_runner.schedule_task(task)
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
these objects and pass it to `commit`. To keep `render` from getting
too confusing, let's put this in a new `run_animation_frame` method,
and move `__runRAFHandlers` there too:

``` {.python replace=self.scroll%2c/scroll%2c,(self)/(self%2c%20scroll)}
class Tab:
    def __init__(self, browser):
        # ...
        self.browser = browser

    def run_animation_frame(self):
        self.js.interp.evaljs("__runRAFHandlers()")
        self.render()
        commit_data = CommitForRaster(
            url=self.url,
            scroll=self.scroll,
            height=document_height,
            display_list=self.display_list,
        )
        self.display_list = None
        self.browser.commit(self, commit_data)
```

Think of the `CommitForRaster` object as being sent from the main
thread to browser thread. That means the main thread shouldn't access
it any more, and for this reason I'm resetting the `display_list`
field. The `Browser` should now schedule `run_animation_frame`:

``` {.python replace=frame)/frame%2c%20scroll)}
class Browser:
    def schedule_animation_frame(self):
        def callback():
            # ...
            task = Task(active_tab.run_animation_frame)
            # ...
```

Also, remove the `set_needs_raster_and_draw` call from `render`. We'll
do that inside `commit`.

On the `Browser` side, the new `commit` method needs to read out all
of the data it was sent and call `set_needs_raster_and_draw` as
needed. Because this call will come from another thread, we'll need to
acquire a lock:

``` {.python}
class Browser:
    def __init__(self):
        self.lock = threading.Lock()

        self.url = None
        self.scroll = 0
        self.active_tab_height = 0
        self.active_tab_display_list = None

    def commit(self, tab, commit):
        self.lock.acquire(blocking=True)
        if tab == self.tabs[self.active_tab]:
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

Now that we have a browser lock, we also need to acquire the lock any
time the browser thread accesses any of its variables. For example, in
`set_needs_animation_frame`, do this:

``` {.python}
class Browser:
    def set_needs_animation_frame(self, tab):
        self.lock.acquire(blocking=True)
        # ...
        self.lock.release()
```

In `schedule_animation_frame` you'll need to do it both inside and
outside the callback:

<!-- TODO: I'm not sure why this lint fails. -->

``` {.python expected=False}
class Browser:
    def schedule_animation_frame(self):
        def callback():
            self.lock.acquire(blocking=True)
            # ...
            self.lock.release()
        self.lock.acquire(blocking=True)
        # ...
        self.lock.release()
```

Add locks to `raster_and_draw`, `handle_down`, `handle_click`,
`handle_key`, and `handle_enter` as well.

We also don't want the main thread doing rendering faster than the
browser thread can raster and draw. So we should only schedule
animation frames once raster and draw are done:[^backpressure]

[^backpressure]: The technique of controlling the speed of the front of a
pipeline by means of the speed of its end is called *back pressure*.

``` {.python}
if __name__ == "__main__":
    while True:
        # ...
        browser.raster_and_draw()
        browser.schedule_animation_frame()
```

Remove the `schedule_animation_frame` call from inside the callback
inside `schedule_animation_frame`. We're now scheduling an animation
frame every time raster-and-draw is finished.

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

Now that we have separate browser and main threads, and now that some
operations are performed on the browser thread, our browser's thread
architecture has started to resemble that of a real
browser.[^processes] But why not move more parts of the browser into
even more threads? Wouldn't that make the browser even faster?

[^processes]: Note that many browsers now run some parts of the
    browser thread and main thread in different processes, which has
    some advantages for security and error handling.
    
In a word, yes. Modern browsers have [dozens of
threads][renderingng-architecture], which together serve to make the
browser even faster and more responsive. For example, raster-and-draw
typically runs on its own thread so that the browser thread can handle
events even while a new frame is being prepared. Likewise, modern
browsers typically have a collection of network or IO threads, which
move all interaction with the network or the file system off of the
main thread.

[renderingng-architecture]: https://developer.chrome.com/blog/renderingng-architecture/#process-and-thread-structure

On the other hand, some parts of the browser can't be easily threaded.
For example, consider the earlier part of the rendering pipeline:
style, layout and paint. In our browser, these run on the main thread.
But could they move to their own thread?

In principle, Yes. The only thing browsers *have* to do is implement
all the web API specifications correctly, and draw to the screen after
scripts and `requestAnimationFrame` callbacks have completed. The
specification spells this out in detail in what it calls the
[update-the-rendering] steps. But if you click that link, you might
notice something missing: the specification it doesn't mention style
or layout at all! All it says is "update the rendering or user
interface" at the very end. That's because style and layout---just
like paint and draw---are implementation details of a browser, not a
*JavaScript-observable* component of the browser. To the
specification, the update-the-rendering steps are the sequence of
*JavaScript-observable* things that have to happen before drawing to
the screen.

[update-the-rendering]: https://html.spec.whatwg.org/multipage/webappapis.html#update-the-rendering

Nevertheless, in practice, no current modern browser runs style or
layout on off the main thread.[^servo] The reason is simple: there are
many JavaScript APIs that can query style or layout state. For
example, [`getComputedStyle`][gcs] can't be implemented without the
browser first computing style, and [`getBoundingClientRect`][gbcr]
needs layout.[^nothing-later] If a web page calls one of these APIs,
and style or layout is not up-to-date, then is has to be computed
synchronously, then and there. These computations are called *forced
style* or *forced layout*. The world "forced" refers to forcing the
computation to happen right away, as opposed to possibly 16ms in the
future if it didn't happen to be already computed. Because there are
forced style and layout situations, browsers have to be able to do
that work on the main thread if necessary.[^or-stall]

[gcs]: https://developer.mozilla.org/en-US/docs/Web/API/Window/getComputedStyle
[gbcr]: https://developer.mozilla.org/en-US/docs/Web/API/Element/getBoundingClientRect

[^or-stall]: Or stall the compositor thread and ask it to do it synchronously,
but that is generally a worse option because it'll make scrolling janky.

[^servo]: The [Servo] rendering engine uses multiple threads to take
advantage of parallelism in style and layout, but those steps still
block, for example, JavaScript execution on the main thread.

[Servo]: https://en.wikipedia.org/wiki/Servo_(software)

[^nothing-later]: There is no JavaScript API that allows reading back state
from anything later in the rendering pipeline than layout. It's for
this reason that we're able to move raster and draw to the browser
thread.

One possible way to resolve these tensions is to optimistically move
style and layout off the main thread, similar to optimistically doing
threaded scrolling if a web page doesn't `preventDefault` a scroll. Is
that a good idea? Maybe, but forced style and layout aren't just
caused by JavaScript execution. One example is our implementation of
`click`, which causes a render to run hit testing:

``` {.python}
class Tab:
    def click(self, x, y):
        self.render()
        # ...
```

It's maybe possible to move hit testing off the main thread (but very
hard) or to do hit testing against an older version of the layout
tree, or to come up with some other technological fix. Thus it's not
*impossible* to move style and layout off the main thread
"optimistically", but it *is* challenging. That said, browser
developers are always looking for ways to make things faster, and I
expect that at some point in the future style and layout will be moved
to their own thread. Maybe you'll be the one to do it?

Summary
=======

This chapter explained in some detail the two-thread rendering system
at the core of modern browsers. The main points to remember are:

- The browser organizes work into task queues, with tasks for things
  like running JavaScript, handling user input, and rendering the page.
- The goal is to consistently generate frames to the screen at a 60Hz
  cadence, which means a 16ms budget to draw each animation frame.
- The browser has two main threads. The main thread runs JavaScript
  and the special rendering task.
- The browser draws the display list to the screen, handles/dispatches
  input events, and performs scrolling. The main thread communicates
  with the browser thread via `commit`, which synchronizes the two threads.

Additionally, you've seen how hard it is to move tasks between the two
threads, such as the challenges involved in scrolling on the browser
thread, or how forced style and layout makes it hard to fully isolate
the rendering pipeline from JavaScript.

Outline
=======

The complete set of functions, classes, and methods in our browser 
should now look something like this:

::: {.cmd .python .outline html=True}
    python3 infra/outlines.py --html src/lab12.py
:::

Exercises
=========

*setInterval*: [`setInterval`][setInterval] is similar to `setTimeout`
but runs repeatedly at a given cadence until
[`clearInterval`][clearInterval] is called. Implement these. Make sure
to test `setInterval` with various cadences in a page that also uses
`requestAnimationFrame` with some expensive rendering pipeline work to
do. Record the actual timing of `setInterval` tasks; how consistent is
the cadence?

[setInterval]: https://developer.mozilla.org/en-US/docs/Web/API/WindowOrWorkerGlobalScope/setInterval
[clearInterval]: https://developer.mozilla.org/en-US/docs/Web/API/WindowOrWorkerGlobalScope/clearInterval

*Clock-based frame timing*: Right now our browser schedules the next
animation frame to happen exactly 16ms later than the first time
`set_needs_animation_frame` is called. However, this actually leads to
a slower animation frame rate cadence than 16ms, for example if
`render` takes say 10ms to run. Can you see why? Fix this in our
browser by using the absolute time to schedule animation frames,
instead of a fixed delay between frames. You will need to choose a
slower cadence than 16ms so that the frames don't overlap.

*Scheduling*: As more types of complex tasks end up on the event
queue, there comes a greater need to carefully schedule them to ensure
the rendering cadence is as close to 16ms as possible, and also to
avoid task starvation. Implement a task scheduler with a priority
system that balances these two needs. Test it out on a web page that
taxes the system with a lot of `setTimeout`-based tasks.

*Threaded loading*: When loading a page, our browser currently waits
for each style sheet or script resource to load in turn. This is
unnecessarily slow, especially on a bad network. Instead, make your
browser sending off all the network requests in parallel. It may be
convenient to use the `join` method on a `Thread`, which will block
the thread calling `join` until the other thread completes. This way
your `load` method can block until all network requests are complete.

*Networking thread*: Real browsers usually have a separate thread for
networking (and other I/O). Tasks are added to this thread in a
similar fashion to the main thread. Implement a third *networking*
thread and put all networking tasks on it.

*Fine-grained dirty bits*: at the moment, the browser always re-runs
the entire rendering pipeline if anything changed. For example, it
re-rasters the browser chrome every time (which chapter 11 didn't do).
Add separate dirty bits for raster and draw stages.[^layout-dirty]

[^layout-dirty]: You can also try adding dirty bits for whether layout
needs to be run, but be careful to think very carefully about all the
ways this dirty bit might need to end up being set.

*Condition variables*: the main thread's event loop will spin in a
loop if there are no tasks available. This wastes CPU
time.[^browser-thread-burn] Use a *condition variable* to put the main
thread to sleep until there is a task to run. In Python, you need the
`threading` module's [`Condition`][condition] class: call `wait` on a
condition variable to stop the calling thread, and call `notify_all`
on a condition variable to wake all threads waiting on it.

[condition]: https://docs.python.org/3/library/threading.html#condition-objects

[^browser-thread-burn]: The browser thread's `while True` loop, which
asks SDL for new events, is also wasteful. Unfortunately, we couldn't
find a way to avoid this in SDL.

*Optimized scheduling*: On a complicated web page, the browser may not
be able to keep up with the desired cadence. Instead of constantly
pegging the CPU in a futile attempt to keep up, implement a *frame
time estimator* that estimates the true cadence of the browser based
on previous frames, and adjust `schedule_animation_frame` to match.
This way complicated pages get consistently slower, instead of having
random slowdowns.

*Raster-and-draw thread*: Right now, if an input event arrives while
the browser thread is rastering or drawing, that input event won't be
handled immediately. This is especially a problem because [raster and
draw are slow](#profiling-rendering). Fix this by adding a separate
raster-and-draw thread controlled by the browser thread. While the
raster-and-draw thread is doing its work, the browser thread should be
available to handle input events. Be careful: SDL is not thread-safe,
so all of the steps that directly use SDL still need to happen on the
browser thread.
