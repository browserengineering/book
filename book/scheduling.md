---
title: Scheduling Tasks and Threads
chapter: 12
prev: visual-effects
next: animations
...

Modern browsers must handle user input, request remote files, run
various callbacks, and ultimately render to the screen, all while
staying fast and responsive. That requires a unified task abstraction
to keep track of the browser's pending work. Moreover, browser work
must be split across multiple CPU threads\index{thread}, with
different threads running tasks in parallel to maximize
responsiveness.

Tasks and Task Queues
=====================

So far, most of the work our browser's been doing has come from user
actions like scrolling, pressing buttons, and clicking on links. But
as the web applications our browser runs get more and more
sophisticated, they begin querying remote servers, showing animations,
and prefetching information for later. And while users are slow and
deliberative, leaving long gaps between actions for the browser to
catch up, applications can be very demanding. This requires a change
in perspective: the browser now has a never-ending queue of tasks to
do.

Modern browsers adapt to this reality by multitasking, prioritizing,
and deduplicating work. Every bit of work the browser might
do---loading pages, running scripts, and responding to user
actions---is turned into a *task*, which can be executed later,
where a task is just a function (plus its arguments) that can be
executed:

``` {.python}
class Task:
    def __init__(self, task_code, *args):
        self.task_code = task_code
        self.args = args

    def run(self):
        self.task_code(*self.args)
        self.task_code = None
        self.args = None
```

Note the special `*args` syntax in the constructor arguments and in
the call to `task_code`. This syntax indicates that a `Task` can be
constructed with any number of arguments, which are then available as
the list `args`. Then, calling a function with `*args` unpacks the
list back into multiple arguments.

The point of a task is that it can be created at one point in time,
and then run at some later time by a task runner of some kind,
according to a scheduling algorithm.[^event-loop] In our browser, the
task runner will store tasks in a first-in, first-out queue:

[^event-loop]: The event loops we discussed in [Chapter
2](graphics.md#eventloop) and [Chapter
11](visual-effects.md#sdl-creates-the-window) are task runners, where
the tasks to run are provided by the operating system.

``` {.python replace=(self)/(self%2c%20tab)}
class TaskRunner:
    def __init__(self):
        self.tab = tab
        self.tasks = []

    def schedule_task(self, task):
        self.tasks.append(task)
```

When the time comes to run a task, our task runner can just remove
the first task from the queue and run it:[^fifo]

[^fifo]: First-in, first-out is a simplistic way to choose which task
to run next, and real browsers have sophisticated *schedulers* which
consider [many different factors][chrome-scheduling].

[chrome-scheduling]: https://blog.chromium.org/2015/04/scheduling-tasks-intelligently-for_30.html

``` {.python expected=False}
class TaskRunner:
    def run(self):
        if len(self.tasks) > 0:
            task = self.tasks.pop(0)
            task.run()
```

To run those tasks, we need to call the `run` method on our
`TaskRunner`, which we can do in the main event loop:\index{event loop}

``` {.python expected=False}
class Tab:
    def __init__(self):
        self.task_runner = TaskRunner(self)
```

``` {.python expected=False}
def mainloop(browser):
    while True:
        # ...
        browser.active_tab.task_runner.run()
```

The `TaskRunner` allows us to choose when exactly different tasks are
handled. Here, I've chosen to check for user events between every
`Task` the browser runs, which makes our browser more responsive when
there are lots of tasks. I've also chosen to only run tasks on the
active tab, which means background tabs can't slow our browser down.

With this simple task runner, we can now queue up tasks and execute them
later. For example, right now, when loading a web page, our browser
will download and run all scripts before doing its rendering steps.
That makes pages slower to load. We can fix this by creating tasks for
running scripts:

``` {.python}
class Tab:
    def load(self, url, payload=None):
        # ...
        for script in scripts:
            # ...
            try:
                header, body = script_url.request(url)
            except:
                continue
            task = Task(self.js.run, script_url, body)
            self.task_runner.schedule_task(task)
```

Now our browser will not run scripts until after `load` has completed
and the event loop comes around again. And if there are lots of
scripts to run, we'll also be able to process user events while the
page loads.

::: {.further}
JavaScript uses a task-based [event loop][js-eventloop] even
[outside][nodejs-eventloop] of the browser. For example, JavaScript
uses message passing, handles input and output via
[asynchronous][async-js] APIs, and has run-to-completion semantics.
Of course, this programming model grew out of early browser
implementations, and is now another important reason to
architect a browser using tasks.
:::

[js-eventloop]: https://developer.mozilla.org/en-US/docs/Web/JavaScript/EventLoop
[nodejs-eventloop]: https://nodejs.dev/learn/the-nodejs-event-loop
[async-js]: https://developer.mozilla.org/en-US/docs/Web/JavaScript/EventLoop#never_blocking

Timers and `setTimeout`
=======================

Tasks are *also* a natural way to support several JavaScript APIs that
ask for a function to be run at some point in the future. For example,
[`setTimeout`][settimeout] lets you run a JavaScript function some
number of milliseconds from now. This code prints "Callback" to the
console one second from now:

[settimeout]: https://developer.mozilla.org/en-US/docs/Web/API/setTimeout

``` {.javascript .example}
function callback() { console.log('Callback'); }
setTimeout(callback, 1000);
```

As with `addEventListener` in [Chapter 9](scripts.md#event-handling),
we'll implement `setTimeout` by saving the callback in a JavaScript
variable and creating a handle by which the Python-side code can call
it:

``` {.javascript}
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

[^mem-leak]: Note that we never remove `callback` from the
    `SET_TIMEOUT_REQUESTS` dictionary. This could lead to a memory
    leak, if the callback is holding on to the last reference to some
    large data structure. [Chapter 9](scripts.md) had a similar issue
    with handles. Avoiding memory leaks in data structures shared
    between the browser and the browser application takes a lot of
    care and this book doesn't attempt to do it right.

``` {.javascript}
function __runSetTimeout(handle) {
    var callback = SET_TIMEOUT_REQUESTS[handle]
    callback();
}
```

Now let's implement the Python side of this API. We can use the
[`Timer`][timer] class in Python's [`threading`][threading] module.
You use the class like this:[^polling]

[^polling]: An alternative approach would be to record when each
`Task` is supposed to occur, and compare against the current time in
the event loop. This is called *polling*, and is what, for example,
the SDL event loop does to look for events and tasks. However, that
can mean wasting CPU\index{CPU} cycles in a loop until the task is ready,
so I expect the `Timer` to be more efficient.

[timer]: https://docs.python.org/3/library/threading.html#timer-objects
[threading]: https://docs.python.org/3/library/threading.html

``` {.python .example}
import threading
def callback():
    # ...
threading.Timer(1.0, callback).start()
```

This runs `callback` one second from now.
Simple! But `threading.Timer` executes its callback *on a new Python
thread*, and that introduces a lot of challenges. The callback can't
just call `evaljs` directly: we'd end up with JavaScript running on
two Python threads at the same time, which is not good.[^js-thread] So
as a workaround, the callback will add a new `Task` to the task queue
to call `__runSetTimeout`. That has the downside of potentially
delaying the callback, but it means that JavaScript will only ever
execute on the main thread.

[^js-thread]: JavaScript is not a multithreaded programming language.
It's possible on the web to create [workers] of various kinds, but they
all run independently and communicate only via special message-passing APIs.

[workers]: https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API

Let's implement that:

``` {.python}
SETTIMEOUT_JS = "__runSetTimeout(dukpy.handle)"

class JSContext:
    def __init__(self, tab):
        # ...
        self.interp.export_function("setTimeout",
            self.setTimeout)

    def dispatch_settimeout(self, handle):
        self.interp.evaljs(SETTIMEOUT_JS, handle=handle)

    def setTimeout(self, handle, time):
        def run_callback():
            task = Task(self.dispatch_settimeout, handle)
            self.tab.task_runner.schedule_task(task)
        threading.Timer(time / 1000.0, run_callback).start()
```

But this still isn't quite right. We now have two threads accessing
the `task_runner`: the primary thread, to run tasks, and the timer
thread, to add them. This is a [race condition][race-condition] that
can cause all sorts of bad things to happen, so we need to make sure
only one thread accesses the `task_runner` at a time.

[race-condition]: https://en.wikipedia.org/wiki/Race_condition

To do so we use a [`Condition`][condition-variable] object, which can
only be held
by one thread at a time. Each thread will try to acquire `condition` before
reading or writing to the `task_runner`, avoiding simultaneous
access.^[The `blocking` parameter to `acquire` indicates whether the thread
should wait for the condition to be available before continuing; in this chapter
you'll always set it to `True`. (When the thread is waiting, it's said to be
*blocked*.)]

The `Condition` class is actually a [`Lock`][lock-class], plus functionality to
be able to *wait* until a state condition occurs. If you have no more work to
do right now, acquire `condition` and then call `wait`. This will cause the
thread to stop at that line of code. When more work comes in to do, such as in
`schedule_task`, a call to `notify_all` will wake up the thread that called
`wait`.

``` {.python expected=False}
class TaskRunner:
    def __init__(self, tab):
        # ...
        self.condition = threading.Condition()

    def schedule_task(self, task):
        self.condition.acquire(blocking=True)
        self.tasks.append(task)
        self.condition.notify_all()
        self.condition.release()

    def run(self):
        task = None
        self.condition.acquire(blocking=True)
        if len(self.tasks) > 0:
            task = self.tasks.pop(0)
        self.condition.release()
        if task:
            task.run()

        self.condition.acquire(blocking=True)
        if len(self.tasks) == 0:
            self.condition.wait()
        self.condition.release()
```

It's important to call `wait` at the end of the `run` loop if there is nothing
left to do. Otherwise that thread will tend to use up a lot of the CPU,
plus constantly be acquiring and releasing `condition`. This busywork not only
slows down the computer, but also causes the callbacks from the `Timer` to
happen at erratic times, because the two threads are competing for the
lock.[^try-it]

[condition-variable]: https://docs.python.org/3/library/threading.html#threading.Condition

[lock-class]: https://docs.python.org/3/library/threading.html#threading.Lock

[^try-it]: Try removing this code and observe. The timers will become quite
erratic.

When using locks, it's super important to remember to release the lock
eventually and to hold it for the shortest time possible. The code
above, for example, releases the lock before running the `task`.
That's because after the task has been removed from the queue, it
can't be accessed by another thread, so the lock does not need to be
held while the task is running.

The `setTimeout` code is now thread-safe, but still has yet another bug: if we
navigate from one page to another, `setTimeout` callbacks still pending on the
previous page might still try to execute. That is easily prevented by adding a
`discarded` field on `JSContext` and setting it when loading a new page:

``` {.python}
class JSContext:
    def __init__(self, tab):
        # ...
        self.discarded = False

    def dispatch_settimeout(self, handle):
        if self.discarded: return
        self.interp.evaljs(SETTIMEOUT_JS, handle=handle)
```

``` {.python}
class Tab:
    def load(self, url, payload=None):
        # ...
        if self.js: self.js.discarded = True
        self.js = JSContext(self)
        # ...
```

::: {.further}
Unfortunately, Python currently has a [global interpreter lock][gil]
(GIL), so Python threads don't truly run in parallel. This unfortunate
limitation of Python has some effect on our browser, but not on real
browsers, so in this chapter I mostly pretend the GIL isn't there.
And perhaps a future version of Python will [get rid of it][no-gil].
We still need locks despite the global interpreter lock, because
Python threads can yield between bytecode operations or during calls
into C libraries. That means concurrent accesses and race conditions
are still possible.[^i-hit-them]
:::

[gil]: https://wiki.python.org/moin/GlobalInterpreterLock
[no-gil]: https://peps.python.org/pep-0703/

[^i-hit-them]: In fact, while debugging the code for this chapter, I
often encountered this kind of race condition when I forgot to add a
lock. Remove some of the locks from your browser and you can see for
yourself!

Long-lived threads
==================

Threads can also be used to add browser multitasking. For example, in
[Chapter 10](security.md#cross-site-requests) we implemented the
`XMLHttpRequest` class, which lets scripts make requests to the
server. But in our implementation, the whole browser would seize up
while waiting for the request to finish. That's obviously bad.^[For
this reason, the synchronous version of the API that we implemented in
Chapter 10 is not very useful and a huge performance footgun. Some
browsers are now moving to deprecate synchronous `XMLHttpRequest`.]
Python's `Thread` class lets us do better:

``` {.python .example}
threading.Thread(target=callback).start()
```
    
This code creates a new thread and then immediately returns. The
`callback` then runs in parallel, on the new thread, while the initial
thread continues to execute later code.

We'll implement asynchronous `XMLHttpRequest` calls using threads.
Specifically, we'll have the browser start a thread, do the request
and parse the response on that thread, and then schedule a `Task` to
send the response back to the script.

Like with `setTimeout`, we'll store the callback on the
JavaScript side and refer to it with a handle:

``` {.javascript}
XHR_REQUESTS = {}

function XMLHttpRequest() {
    this.handle = Object.keys(XHR_REQUESTS).length;
    XHR_REQUESTS[this.handle] = this;
}
```

When a script calls the `open` method on an `XMLHttpRequest` object,
we'll now allow the `is_async` flag to be true:[^async-default]

[^async-default]: In browsers, the `is_async` parameter is optional
    and defaults to `true`, but our browser doesn't implement that.

``` {.javascript}
XMLHttpRequest.prototype.open = function(method, url, is_async) {
    this.is_async = is_async;
    this.method = method;
    this.url = url;
}
```

The `send` method will need to send over the `is_async` flag and the
handle:

``` {.javascript}
XMLHttpRequest.prototype.send = function(body) {
    this.responseText = call_python("XMLHttpRequest_send",
        this.method, this.url, body, this.is_async, this.handle);
}
```

On the browser side, the `XMLHttpRequest_send` handler will have three
parts. The first part will resolve the URL and do security checks:

``` {.python}
class JSContext:
    def XMLHttpRequest_send(
        self, method, url, body, isasync, handle):
        full_url = self.tab.url.resolve(url)
        if not self.tab.allowed_request(full_url):
            raise Exception("Cross-origin XHR blocked by CSP")
        if full_url.origin() != self.tab.url.origin():
            raise Exception(
                "Cross-origin XHR request not allowed")
```

Then, we'll define a function that makes the request and enqueues a
task for running callbacks:

``` {.python}
class JSContext:
    def XMLHttpRequest_send(
        self, method, url, body, isasync, handle):
        # ...
        def run_load():
            headers, response = full_url.request(self.tab.url, body)
            task = Task(self.dispatch_xhr_onload, response, handle)
            self.tab.task_runner.schedule_task(task)
            return response
```

Note that the task runs `dispatch_xhr_onload`, which we'll define in
just a moment.

Finally, depending on the `is_async` flag the browser will either call
this function right away, or in a new thread:

``` {.python}
class JSContext:
    def XMLHttpRequest_send(
        self, method, url, body, isasync, handle):
        # ...
        if not isasync:
            return run_load()
        else:
            threading.Thread(target=run_load).start()
```

Note that in the asynchronous case, the `XMLHttpRequest_send` method starts a
thread and then immediately returns. That thread will run in parallel
with the browser's main work until the request is done.^[In theory two
parallel requests could race while accessing the cookie jar; I'm not
fixing this out of expediency but a proper implementation would have
locks for the cookie jar.]

To communicate the result back to JavaScript, we'll call a
`__runXHROnload` function from `dispatch_xhr_onload`:

``` {.python}
XHR_ONLOAD_JS = "__runXHROnload(dukpy.out, dukpy.handle)"

class JSContext:
    def dispatch_xhr_onload(self, out, handle):
        if self.discarded: return
        do_default = self.interp.evaljs(
            XHR_ONLOAD_JS, out=out, handle=handle)
```

The `__runXHROnload` method just pulls the relevant object from
`XHR_REQUESTS` and calls its `onload` function, which is the standard
callback for asynchronous `XMLHttpRequest`s:

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
running in the browser to delay tasks until later.

::: {.further}

`XMLHttpRequest` played a key role in helping the web evolve. In the
1990s, clicking on a link or submitting a form required loading a new
pages. With `XMLHttpRequest` web pages were able to act a whole lot
more like a dynamic application; GMail was one famous early
example.[^when-gmail] Nowadays, a web application that uses DOM
mutations instead of page loads to update its state is called a
[single-page app][spa]. Single-page apps enabled more interactive and
complex web apps, which in turn made browser speed and responsiveness
more important.

[^when-gmail]: GMail dates from April 2004, [soon after][xhr-history]
enough browsers finished adding support for the API. The first
application to use `XMLHttpRequest` was [Outlook Web Access][outlook],
in 1999, but it took a while for the API to make it into other
browsers.

[outlook]: https://en.wikipedia.org/wiki/Outlook_on_the_web
[xhr-history]: https://en.wikipedia.org/wiki/XMLHttpRequest#History
[spa]: https://en.wikipedia.org/wiki/Single-page_application

:::

The Cadence of Rendering
========================

There's more to tasks than just implementing some JavaScript APIs.
Once something is a `Task`, the task runner controls when it runs:
perhaps now, perhaps later, or maybe at most once a second, or even at
different rates for active and inactive pages, or according to its
priority. A browser could even have multiple task runners, optimized
for different use cases.

Now, it might be hard to see how the browser can prioritize which
JavaScript callback to run, or why it might want to execute JavaScript
tasks at a fixed cadence. But besides JavaScript the browser also has
to render the page, and as you may recall from [Chapter
2](graphics.md#framebudget), we'd like the browser to render the page
exactly as fast as the display hardware can refresh. On most
computers, this is 60 times per second, or 16 ms per frame. However, even
with today's computers, it's quite difficult to maintain such a high
frame rate, and certainly too high a bar for our toy browser.

So let's establish 30 frames per second---33 ms for each frame---as our refresh
rate target:[^why-33ms]

[^why-33ms]: Of course, 30 times per second is actually 33.33333...
    ms. But it's a toy browser, and having a more exact
    value also makes tests easier to write.


``` {.python}
REFRESH_RATE_SEC = .033
```

Now, drawing a frame\index{rendering pipeline} is split between the
`Tab` and `Browser`. The `Tab` needs to call `render` to compute a
display list. Then the `Browser` needs to raster and draw that display
list (and also the chrome display list). Let's put those `Browser`
tasks in their own method:

``` {.python}
class Browser:
    def raster_and_draw(self):
        self.raster_chrome()
        self.raster_tab()
        self.draw()
```

Now, we don't need _each_ tab redrawing itself every frame, because
the user only sees one tab at a time. We just need the _active_ tab
redrawing itself. Therefore, it's the `Browser` that should control
when we update the display, not individual `Tab`s. So let's write a
`schedule_animation_frame` method[^animation-frame] that schedules a
task to `render` the active tab:

[^animation-frame]: It's called an "animation frame" because
sequential rendering of different pixels is an animation, and each
time you render it's one "frame"---like a drawing in a picture frame.

``` {.python expected=False}
class Browser:
    def __init__(self):
        self.animation_timer = None

    def schedule_animation_frame(self):
        def callback():
            active_tab = self.active_tab
            task = Task(active_tab.render)
            active_tab.task_runner.schedule_task(task)
            self.animation_timer = None
        if not self.animation_timer:
            self.animation_timer = \
                threading.Timer(REFRESH_RATE_SEC, callback)
            self.animation_timer.start()
```

We can kick off the process when we start the browser. In the top-level loop,
after running a task on the active tab the browser will need to raster and
draw, in case that task was a rendering task:

``` {.python expected=False}
def mainloop(browser):
    while True:
        # ...
        browser.active_tab.task_runner.run()
        browser.raster_and_draw()
        browser.schedule_animation_frame()
```

The additional call to `schedule_animation_frame` will happen every time
through the loop. However, because of the check for `self.animation_timer`
being `None`, it will only have an effect once `callback` was called, which
only happens after 33 ms. Thus we're scheduling a new rendering task every
33 ms, just as we wanted to.

::: {.further}

There's nothing special about any particular refresh rate. Some displays
refresh 72 times per second, and displays that [refresh even more
often][refresh-rate] are becoming more common. Movies are often shot
at 24 frames per second (though [some directors advocate
48][hobbit-fps]) while television shows traditionally use 30 frames per
second. Consistency is often more important than the actual frame
rate: a consistant 24 frames per second can look a lot smoother than a
varying rate between 60 and 24.

:::

[refresh-rate]: https://www.intel.com/content/www/us/en/gaming/resources/highest-refresh-rate-gaming.html
[hobbit-fps]: https://www.extremetech.com/extreme/128113-why-movies-are-moving-from-24-to-48-fps

Optimizing with Dirty Bits
==========================

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
    def __init__(self, browser, tab_height):
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
`innerHTML_set`, `load`, `click`, and `keypress` when changing the DOM.
For example, in `load`, do this:

``` {.python}
class Tab:
    def load(self, url, payload=None):
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

There are more calls to `render`; you should find and fix all of
them ... except, let's take a closer look at `click`.

We now don't immediately render when something changes. That means that the
layout tree (and style) could be out of date when a method is called. Normally,
this isn't a problem, but in one important case it is: click handling. That's
because we need to read the layout tree to figure out what object was clicked
on, which means the layout tree needs to be up to date. To fix this, add a
call to `render` at the top of `click`:

``` {.python}
class Tab:
    def click(self, x, y):
        self.render()
        # ...
```

Another problem with our implementation is that the browser is now
doing `raster_and_draw` every time the active tab runs a task.
But sometimes that task is just running JavaScript that doesn't touch
the web page, and the `raster_and_draw` call is a waste.

We can avoid this using another dirty bit, which I'll call
`needs_raster_and_draw`:[^not-just-speed]

[^not-just-speed]: The `needs_raster_and_draw` dirty bit doesn't just
make the browser a bit more efficient. Later in this chapter, we'll
add multiple browser threads, and at that point this dirty bit is
necessary to avoid erratic behavior when animating. Try removing it
later and see for yourself!

``` {.python}
class Browser:
    def __init__(self):
        self.needs_raster_and_draw = False

    def set_needs_raster_and_draw(self):
        self.needs_raster_and_draw = True

    def raster_and_draw(self):
        if not self.needs_raster_and_draw:
            return
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
        if e.y < self.chrome.bottom:
            # ...
            self.set_needs_raster_and_draw()

    def handle_key(self, char):
        if self.chrome.keypress(char):
            # ...
            self.set_needs_raster_and_draw()

    def handle_enter(self):
        if self.chrome.enter():
            # ...
            self.set_needs_raster_and_draw()
```

Here I need a small change to make `enter` return whether something was done:

``` {.python}
class Chrome:
    def enter(self):
        if self.focus == "address bar":
            self.browser.active_tab.load(URL(self.address_bar))
            self.focus = None
            return True
        return False
```

And the `Tab` should also set this bit after running `render`:

``` {.python dropline=set_needs_raster_and_draw}
class Tab:
    def __init__(self, browser, tab_height):
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
    def new_tab(self, url):
        new_tab = Tab(self, HEIGHT - self.chrome.bottom)
        # ...
```

Now the rendering pipeline is only run if necessary, and the browser
should have acceptable performance again.

::: {.further}
This scheduled, task-based approach to rendering is necessary for
running complex interactive applications, but it still took until 
the 2010s for all modern browsers to adopt it, well after such web
applications became widespread. That's because it
typically required extensive refactors of vast browser codebases.
Chromium, for example, [only recently][renderingng] finished 100% of the work
to leverage this model, though of course work (always) remains to be done.
:::

[renderingng]: https://developer.chrome.com/docs/chromium/renderingng

Animating Frames
================

One big reason for a steady rendering cadence is so that animations
run smoothly. Web pages can set up such animations using the
[`requestAnimationFrame`][raf] API. This API allows scripts to run
code right before the browser runs its rendering pipeline, making the
animation maximally smooth. It works like this:

[raf]: https://developer.mozilla.org/en-US/docs/Web/API/window/requestAnimationFrame

``` {.javascript .example}
function callback() { /* Modify DOM */ }
requestAnimationFrame(callback);
```

By calling `requestAnimationFrame`, this code is doing two things:
scheduling a rendering task, and asking that the browser call
`callback` *at the beginning* of that rendering task, before any
browser rendering code. This lets web page authors change the page and
be confident that it will be rendered right away.

The implementation of this JavaScript API is straightforward. Like
before, we store the callbacks on the JavaScript side:

``` {.javascript}
RAF_LISTENERS = [];

function requestAnimationFrame(fn) {
    RAF_LISTENERS.push(fn);
    call_python("requestAnimationFrame");
}
```

In `JSContext`, when that method is called, we need to schedule a new
rendering task:

``` {.python}
class JSContext:
    def __init__(self, tab):
        # ...
        self.interp.export_function("requestAnimationFrame",
            self.requestAnimationFrame)
```

``` {.python expected=False}
    def requestAnimationFrame(self):
        task = Task(self.tab.render)
        self.tab.task_runner.schedule_task(task)
```

Then, when `render` is actually called, we need to call back into
JavaScript, like this:

``` {.python dropline=self.needs_render replace=render(self)/run_animation_frame(self%2c%20scroll)}
class Tab:
    def render(self):
        if not self.needs_render: return
        self.js.interp.evaljs("__runRAFHandlers()")
        # ...
```

This `__runRAFHandlers` function is a little tricky:

``` {.javascript}
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
happens during such a callback, the specification says that a *second*
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
animated count from 0 to 99. Serve this example web page from our HTTP
server:

``` {.python file=server replace=eventloop/eventloop12}
def do_request(session, method, url, headers, body):
    elif method == "GET" and url == "/count":
        return "200 OK", show_count()
# ...
def show_count():
    out = "<!doctype html>"
    out += "<div>";
    out += "  Let's count up to 99!"
    out += "</div>";
    out += "<div>Output</div>"
    out += "<script src=/eventloop.js></script>"
    return out
```

Load this up and observe an animation from 0 to 99.

One flaw with our implementation so far is that an inattentive coder
might call `requestAnimationFrame` multiple times and thereby schedule
more animation frames than expected. If other JavaScript tasks appear
later, they might end up delayed by many, many frames.

Luckily, rendering is special in that it never makes sense to have two
rendering tasks in a row, since the page wouldn't have changed in
between. To avoid having two rendering tasks we'll add a dirty bit
called `needs_animation_frame` to the `Browser` that indicates
whether a rendering task actually needs to be scheduled:

``` {.python}
class Browser:
    def __init__(self):
        self.needs_animation_frame = True
```

``` {.python}
    def schedule_animation_frame(self):
        # ...
        if self.needs_animation_frame and not self.animation_timer:
            # ...
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
        if tab == self.active_tab:
            self.needs_animation_frame = True
```

Note that `set_needs_animation_frame` will only actually set the dirty
bit if called from the active tab. This guarantees that inactive tabs
can't interfere with active tabs. Besides preventing scripts from
scheduling too many animation frames, this system also makes sure that
if our browser consistently runs slower than 30 frames per second, we
won't end up with an ever-growing queue of rendering tasks.

::: {.further}
Before the `requestAnimationFrame` API, developers approximated it with
`setTimeout`. This did run animations at a
(roughly) fixed cadence, but because it didn't line up with the
browser's rendering loop, events would sometimes be handled between the
callback and rendering, which might force an extra, unnecessary rendering step.
Not only does `requestAnimationFrame` avoid this, but it also lets the
browser turn off rendering work when a web page tab or window is
backgrounded, minimized or otherwise throttled, while still allowing
other background tasks like saving your work to the cloud.
:::

Profiling Rendering
===================

We now have a system for scheduling a rendering task every 33 ms. But
what if rendering takes longer than 33 ms to finish? Before we answer
this question, let's instrument the browser and measure how much time
is really being spent rendering. It's important to always measure
before optimizing, because the result is often surprising.

To instrument our browser, let's have it output the
[JSON][json] tracing format used by
[`chrome://tracing` in Chrome][chrome-tracing],
[Firefox Profiler](https://profiler.firefox.com/) or
[Perfetto UI](https://ui.perfetto.dev/).[^note-standards]

[json]: https://www.json.org/
[chrome-tracing]: https://www.chromium.org/developers/how-tos/trace-event-profiling-tool/

[^note-standards]: Though note that these three tools seem to have
    somewhat different interpretations of the JSON format and display
    the same trace in slightly different ways.

To start, let's wrap the actual file and format in a class:

``` {.python}
class MeasureTime:
    def __init__(self):
        self.file = open("browser.trace", "w")
```

A trace file is just a JSON object with a `traceEvents`
field[^and-other-fields] which contains a list of trace events:

[^and-other-fields]: There are other optional fields too, which
    provide various kinds of metadata. We won't need them here.

``` {.python}
class MeasureTime:
    def __init__(self):
        # ...
        self.file.write('{"traceEvents": [')
```

Each trace event has a number of fields. The `ph` and `name` fields
define the event type. For example, setting `ph` to `M` and `name` to
`process_name` allows us to change the displayed process name:

``` {.python}
class MeasureTime:
    def __init__(self):
        # ...
        ts = time.time() * 1000000
        self.file.write(
            '{ "name": "process_name",' +
            '"ph": "M",' +
            '"ts": ' + str(ts) + ',' +
            '"pid": 1, "cat": "__metadata",' +
            '"args": {"name": "Browser"}}')
        self.file.flush()
```

The new name ("Browser") is passed in `args`, and the other fields are
required. Since our browser only has one process, I just pass `1` for
the process ID, and the `cat`egory has to be `__metadata` for metadata
trace events. The `ts` field stores a timestamp; since this is the
first event, it'll set the start time for the whole trace, so it's
important to put in the actual current time.

We'll create this `MeasureTime` object when we start the browser, so
we can use it to measure how long various browser components take:

``` {.python}
class Browser:
    def __init__(self):
        self.measure = MeasureTime()
```

Now let's add trace events when our browser does something interesting.
We specifically want `B` and `E` events, which mark the beginning and
end of some interesting computation. Because we have that initial
trace event, every later trace event needs to be preceded by a comma:

``` {.python replace=1%7d/%27%20%2b%20str(tid)%20%2b%20%27%7d}
class MeasureTime:
    def time(self, name):
        ts = time.time() * 1000000
        self.file.write(
            ', { "ph": "B", "cat": "_",' +
            '"name": "' + name + '",' +
            '"ts": ' + str(ts) + ',' +
            '"pid": 1, "tid": 1}')
        self.file.flush()
```

Here, the `name` argument to `time` should describe what kind of
computation is starting, and it needs to match the name passed to the
corresponding `stop` event:

``` {.python replace=1%7d/%27%20%2b%20str(tid)%20%2b%20%27%7d}
class MeasureTime:
    def stop(self, name):
        ts = time.time() * 1000000
        self.file.write(
            ', { "ph": "E", "cat": "_",' +
            '"name": "' + name + '",' +
            '"ts": ' + str(ts) + ',' +
            '"pid": 1, "tid": 1}')
        self.file.flush()
```

We can measure tab rendering by just calling `time` and `stop`:

``` {.python}
class Tab:
    def render(self):
        if not self.needs_render: return
        self.browser.measure.time('render')
        # ...
        self.browser.measure.stop('render')
```

Do the same for `raster_and_draw`, and for all of the code that calls
`evaljs` to run JavaScript.

Finally, when we finish tracing (that is, when we close the browser
window), we want to leave the file a valid JSON file:

``` {.python}
class MeasureTime:
    def finish(self):
        self.file.write(']}')
        self.file.close()

class Browser:
    def handle_quit(self):
        # ...
        self.measure.finish()
```

By the way, note that I'm careful to `flush` after every write. This
makes sure that if the browser crashes, all of the log events---which
might help me debug---are already safely on disk.[^invalid-json]

[^invalid-json]: Some of the tracing tools listed above actually
accept invalid JSON files, in case the trace comes from a browser
crash.

::: {.web-only}

Fire up the server, open our timer script, wait for it to finish
counting, and then exit the browser. Then open up Chrome tracing or
one of the other tracing tools named above and load the trace.
If you don't want to do it yourself,
[here](examples/example12-count-single-threaded.trace) is a sample trace file
from my computer. You should see something like Figure 1.

:::

::: {.print-only}

Fire up the server, open our timer script, wait for it to finish
counting, and then exit the browser. Then open up Chrome tracing or
one of the other tracing tools named above and load the trace.
You should see something like Figure 1.

:::

::: {.center}
![Figure 1: Tracing for the timer script in single-threaded mode.](examples/example12-trace-count-single-threaded.png)
:::

In Chrome tracing, you can choose the cursor icon from the toolbar and
drag a selection around a set of trace events. That will show counts
and average times for those events in the details window at the bottom
of the screen. On my computer, my browser spent about 23 ms in `render`
and about 62 ms in `raster_and_draw` on average, as you can see in the zoomed-in
view in Figure 2. That clearly blows through our 33 ms budget. So, what can
we do?

::: {.center}
![Figure 2: Tracing for render and raster of one frame of the timer script.](examples/example12-trace-count-render-raster.png)
:::

::: {.further}

Our browser spends a lot of time copying pixels. That's why
[optimizing surfaces][optimize-surfaces] is important! It'll be faster
if you've completed Exercise 11-3, because making `tab_surface`
smaller also helps a lot. Modern browsers go a step further and
perform raster-and-draw [on the GPU][skia-gpu], where a lot more
parallelism is available. Even so, on complex pages raster and draw
really do sometimes take a lot of time. I'll dig into this more in
Chapter 13.

:::

[optimize-surfaces]: visual-effects.md#optimizing-surface-use

[skia-gpu]: https://skia.org/docs/user/api/skcanvas_creation/#gpu

Two Threads
===========

Well, one option, of course, is optimizing raster-and-draw, or even
render, and we'll do that in [Chapter 13](animations.md) But
another option---complex, but worthwhile and done by every major
browser---is to do the render step in parallel with the
raster-and-draw step by adopting a multithreaded architecture. Not
only would this speed up the rendering pipeline (dropping from 85 ms to
62 ms) but we could also execute JavaScript on one thread
while the expensive `raster_and_draw` task runs on the other.

Let's call our two threads the *browser thread*[^also-compositor] and
the *main thread*.[^main-thread-name] The browser thread corresponds
to the `Browser` class and will handle raster-and-draw. It'll also
handle interactions with the browser chrome. The main thread, on the
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
use. A better name might be the "DOM" thread (since
JavaScript can sometimes run on [other threads][webworker]).

[webworker]: https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API

Now, multithreaded architectures are tricky, so let's do a little planning.

To start, the one thread that exists already---the one that runs when
you start the browser---will be the browser thread. We'll make a main
thread every time we create a tab. These two threads will need to
communicate to handle events and draw to the screen.

When the browser thread needs to communicate with the main thread, to
inform it of events, it'll place tasks on the main thread's
`TaskRunner`.[^why-no-browser-taskrunner] The main thread will need to
communicate with the browser thread to request animation frames and to
send it a display list to raster-and-draw, and the main thread will do
that via two methods on `browser`: `set_needs_animation_frame` to request
an animation frame and `commit` to send it a display list.

[^why-no-browser-taskrunner]: You might be wondering why the main thread
doesn't also communicate back to the browser thread with a `TaskRunner`.
That could certainly be done. Here I chose to only do it in one direction,
because the main thread is generally the "slowest" thread in browsers,
due to the unpredictable nature of JavaScript and the unknown size of the
DOM.

The overall control flow for rendering a frame will therefore be:

1. The code running in the main thread requests an animation frame with
   `set_needs_animation_frame`, perhaps in response to an event
   handler or due to `requestAnimationFrame`.
2. The browser thread event loop schedules an animation frame on
   the main thread `TaskRunner`.
3. The main thread executes its part of rendering, then calls
   `browser.commit`.
4. The browser thread rasters the display list and draws to the screen.

Let's implement this design. To start, we'll add a `Thread` to each
`TaskRunner`, which will be the tab's main thread. This thread will
need to run in a loop, pulling tasks from the task queue and running
them. We'll put that loop inside the `TaskRunner`'s `run` method.

``` {.python}
class TaskRunner:
    def __init__(self, tab):
        # ...
        self.main_thread = threading.Thread(
            target=self.run,
            name="Main thread",
        )

    def start_thread(self):
        self.main_thread.start()
```

Note that I name the thread; this is a good habit that helps with
debugging. Let's also name the browser thread:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        threading.current_thread().name = "Browser thread"
```

Remove the call to `run` from the top-level `while True` loop, since
that loop is now going to be running in the browser thread. And `run` will
have its own loop:

``` {.python}
class TaskRunner:
    def run(self):
        while True:
            # ...
```

Because this loop runs forever, the main thread will live on
indefinitely. So if the browser quits, we'll want it to ask the main
thread to quit as well:

``` {.python}
class Browser:
    def handle_quit(self):
        for tab in self.tabs:
            tab.task_runner.set_needs_quit()
```

The `set_needs_quit` method sets a flag on `TaskRunner` that's checked
every time it loops:

``` {.python}
class TaskRunner:
    def set_needs_quit(self):
        self.condition.acquire(blocking=True)
        self.needs_quit = True
        self.condition.notify_all()
        self.condition.release()

    def run(self):
        while True:
            self.condition.acquire(blocking=True)
            needs_quit = self.needs_quit
            self.condition.release()
            if needs_quit:
                return
    
            # ...
    
            self.condition.acquire(blocking=True)
            if len(self.tasks) == 0 and not self.needs_quit:
                self.condition.wait()
            self.condition.release()
```

The `Browser` should no longer call any methods on the `Tab`. Instead,
to handle events, it should schedule tasks on the main thread. For
example, here is loading:

``` {.python}
class Browser:
    def schedule_load(self, url, body=None):
        self.active_tab.task_runner.clear_pending_tasks()
        task = Task(self.active_tab.load, url, body)
        self.active_tab.task_runner.schedule_task(task)
```

We need to clear any pending tasks before loading a new page, because
those previous tasks are now invalid:

``` {.python}
class TaskRunner:
    def clear_pending_tasks(self):
        self.condition.acquire(blocking=True)
        self.tasks.clear()
        self.condition.release()
```

We also need to split `new_tab` into a version that acquires a lock
and one that doesn't (`new_tab_internal`):

``` {.python}
class Browser:
    def new_tab(self, url):
        self.lock.acquire(blocking=True)
        self.new_tab_internal(url)
        self.lock.release()

    def new_tab_internal(self, url):
        new_tab = Tab(self, HEIGHT - self.chrome.bottom)
        self.tabs.append(new_tab)
        self.set_active_tab(new_tab)
        self.schedule_load(url)
```

This way `new_tab_internal` can be called directly by methods,
like `Chrome`'s `click` method, that already hold the lock.^[Using locks while
avoiding race conditions and deadlocks can be quite difficult!]

``` {.python}
class Chrome:
    def click(self, x, y):
        if self.newtab_rect.contains(x, y):
            self.browser.new_tab_internal(
                URL("https://browser.engineering/"))

    def enter(self):
        if self.focus == "address bar":
            self.browser.schedule_load(URL(self.address_bar))
```

Event handlers are mostly similar, except that we need to be careful
to distinguish events that affect the browser chrome from those that
affect the tab. For example, consider `handle_click`. If the user
clicked on the browser chrome, we can
handle it right there in the browser thread. But if the user clicked
on the web page, we must schedule a task on the main thread:

``` {.python}
class Browser:
    def handle_click(self, e):
        self.lock.acquire(blocking=True)
        if e.y < self.chrome.bottom:
             # ...
        else:
            # ...
            tab_y = e.y - self.chrome.bottom
            task = Task(self.active_tab.click, e.x, tab_y)
            self.active_tab.task_runner.schedule_task(task)
        self.lock.release()
```

The same logic holds for `keypress`:

``` {.python}
class Browser:
    def handle_key(self, char):
        if not (0x20 <= ord(char) < 0x7f): return
        if self.chrome.keypress(char):
            # ...
        elif self.focus == "content":
            task = Task(self.active_tab.keypress, char)
            self.active_tab.task_runner.schedule_task(task)
```

Do the same with any other calls from the `Browser` to the `Tab`.

So now we have the browser thread telling the main thread what to do.
Communication in the other direction is a little subtler.

::: {.further}

Originally, threads were a mechanism for improving *responsiveness*
via pre-emptive multitasking, but these days they also allow browsers
to increase *throughput* because even phones have several cores. But
different CPU architectures differ, and browser engineers (like you!)
have to use more or less hardware parallelism as appropriate to the
situation. For example, some devices have more [CPU cores][cores] than
others, or are more sensitive to battery power usage, or their system
processes such as listening to the wireless radio may limit the actual
parallelism available to the browser.

:::

[cores]: https://en.wikipedia.org/wiki/Multi-core_processor

Committing a Display List
=========================

We already have a `set_needs_animation_frame` method, but we also need
a `commit` method that a `Tab` can call when it's finished creating a
display list. And if you look carefully at our raster-and-draw code,
you'll see that to draw a display list we also need to know the URL
(to update the browser chrome), the document height (to allocate a
surface of the right size), and the scroll\index{scroll} position (to draw the
right part of the surface).

Let's make a simple class for storing this data:

``` {.python}
class CommitData:
    def __init__(self, url, scroll, height, display_list):
        self.url = url
        self.scroll = scroll
        self.height = height
        self.display_list = display_list
```

When running an animation frame, the `Tab` should construct one of
these objects and pass it to `commit`. To keep `render` from getting
too confusing, let's put this in a new `run_animation_frame` method,
and move `__runRAFHandlers` there too.^[Why not reuse `render` instead of
a new method? Because the `render` method is just about updating style, layout
and paint when needed; it's called for every frame, but it's also called from
`click`, and in real browsers from many other places too.
Meanwhile, `run_animation_frame` is only called for frames, and therefore
it, not `render`, runs RAF handlers and calls `commit`.]

``` {.python replace=self.scroll%2c/scroll%2c,(self)/(self%2c%20scroll)}
class Tab:
    def __init__(self, browser, tab_height):
        # ...
        self.browser = browser

    def run_animation_frame(self):
        self.js.interp.evaljs("__runRAFHandlers()")
        self.render()
        commit_data = CommitData(
            self.url, self.scroll, document_height, \
            self.display_list)
        self.display_list = None
        self.browser.commit(self, commit_data)
```

Think of the `CommitData` object as being sent from the main
thread to the browser thread. That means the main thread shouldn't access
it any more, and for this reason I'm resetting the `display_list`
field. The `Browser` should now schedule `run_animation_frame`:

``` {.python replace=frame)/frame%2c%20scroll)}
class Browser:
    def schedule_animation_frame(self):
        def callback():
            # ...
            task = Task(self.active_tab.run_animation_frame)
            # ...
```

On the `Browser` side, the new `commit` method needs to read out all of the data
it was sent and call `set_needs_raster_and_draw` as needed. Because this call
will come from another thread, we'll need to acquire a lock. Another important
step is to not clear the `animation_timer` object until *after* the next
commit occurs. Otherwise multiple rendering tasks could be queued at the same
time. Finally, store all the `CommitData`: save the `scroll` in `active_tab_scroll`,
the `url` in `active_tab_url`, and additionally store the `height` and, if available,
the `display_list`:

``` {.python}
class Browser:
    def __init__(self):
        self.lock = threading.Lock()

        self.active_tab_url = None
        self.active_tab_scroll = 0
        self.active_tab_height = 0
        self.active_tab_display_list = None

    def commit(self, tab, data):
        self.lock.acquire(blocking=True)
        if tab == self.active_tab:
            self.active_tab_url = data.url
            self.active_tab_scroll = data.scroll
            self.active_tab_height = data.height
            if data.display_list:
                self.active_tab_display_list = data.display_list
            self.animation_timer = None
            self.set_needs_raster_and_draw()
        self.lock.release()
```

Make sure to update the `Chrome` class to use this new `url` field, since we
don't want the chrome, running on the browser thread, to read from the
tab, running on the main thread.

Note that `commit` is called on the main thread, but acquires the
browser thread lock. As a result, `commit` is a critical time when
both threads are "stopped" simultaneously.[^fast-commit] Also
note that it's possible for the browser thread to get a `commit` from
an inactive tab,[^inactive-tab-tasks] so the `tab` parameter is
compared with the active tab before copying over any committed data.

[^fast-commit]: For this reason commit needs to be as fast as possible, to
maximize parallelism and responsiveness. In modern browsers, optimizing commit
is quite challenging, because their method of caching and sending data between
threads is much more sophisticated.

[^inactive-tab-tasks]: That's because even inactive tabs might be processing one last animation frame.

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

``` {.python}
class Browser:
    def schedule_animation_frame(self):
        def callback():
            self.lock.acquire(blocking=True)
            # ...
            self.lock.release()
            # ...
        self.lock.acquire(blocking=True)
        # ...
        self.lock.release()
```

Add locks to `raster_and_draw`, `handle_down`, `handle_click`,
`handle_key`, and `handle_enter` as well.

We also don't want the main thread doing rendering faster than the
browser thread can raster and draw. So we should only schedule
animation frames once raster and draw are done.[^backpressure]
Luckily, that's exactly what we're doing:

[^backpressure]: The technique of controlling the speed of the front of a
pipeline by means of the speed of its end is called *back pressure*.

``` {.python}
def mainloop(browser):
    while True:
        # ...
        browser.raster_and_draw()
        browser.schedule_animation_frame()
```

And that's it: we should now be doing render on one thread and raster
and draw on another!

::: {.further}
Due to the Python GIL, threading in Python doesn't increase
*throughput*, but it can increase *responsiveness* by, say,
running JavaScript tasks on the main thread while the browser does
raster and draw. It's also possible to turn off the global interpreter
lock while running foreign C/C++ code linked into a Python library;
Skia is thread-safe, but DukPy and SDL may not be, and don't seem to
release the GIL. If they did, then JavaScript or raster-and-draw truly
could run in parallel with the rest of the browser, and performance
would improve as well.
:::

Threaded Profiling
==================

Now that we have two threads, we'll want to be able to visualize this
in the traces we produce. Luckily, the Chrome tracing format supports
that. First of all, we'll want to make the `MeasureTime` methods
thread-safe, so they can be called from either thread:

``` {.python}
class MeasureTime:
    def __init__(self):
        self.lock = threading.Lock()
        # ...

    def time(self, name):
        self.lock.acquire(blocking=True)
        # ...
        self.lock.release()

    def stop(self, name):
        self.lock.acquire(blocking=True)
        # ...
        self.lock.release()

    def finish(self):
        self.lock.acquire(blocking=True)
        # ...
        self.lock.release()
```

Next, in every trace event, we'll want to provide a real thread ID in
the `tid` field, which we can get by calling `get_ident` from the
`threading` library:

``` {.python}
class MeasureTime:
    def time(self, name):
        # ...
        tid = threading.get_ident()
        self.file.write(
            ', { "ph": "B", "cat": "_",' +
            '"name": "' + name + '",' +
            '"ts": ' + str(ts) + ',' +
            '"pid": 1, "tid": ' + str(tid) + '}')
        # ...
```

Do the same thing in `stop`. We can also show human-readable thread
names by adding metadata events when finishing the
trace:[^no-closing-tabs]

[^no-closing-tabs]: Note that our browser doesn't let you close tabs,
    so any thread stays around until the trace is `finish`ed. If
    closing tabs were possible, we'd need to do thread names somewhat
    differently.

``` {.python}
class MeasureTime:
    def finish(self):
        self.lock.acquire(blocking=True)
        for thread in threading.enumerate():
            self.file.write(
                ', { "ph": "M", "name": "thread_name",' +
                '"pid": 1, "tid": ' + str(thread.ident) + ',' +
                '"args": { "name": "' + thread.name + '"}}')
        # ...
```

::: {.web-only}

Now, if you make a new trace from the counting animation and load it
into one of the tracing tools, you should see something like Figure 3 (
click [here](examples/example12-count-two-threads.trace) to download an example trace):

:::

::: {.print-only}

Now, if you make a new trace from the counting animation and load it
into one of the tracing tools, you should see something like Figure 3.

:::

::: {.center}
![Figure 3: Tracing for the timer script in two-threads mode.](examples/example12-trace-count-two-threads.png)
:::

You can see how the render and raster tasks now happen on different
threads, and how our multithreaded architecture allows them to happen
concurrently.^[However, in this case the two threads are *not* running
tasks concurrently. That's because all of the JavaScript tasks are
`requestAnimationFrame` callbacks, which are scheduled by the browser
thread, and those are only kicked off once the browser thread finishes
its raster and draw work. Execise 12-8 addresses that problem. ]

::: {.further}
The tracing system we introduced in this chapter comes directly from
real browsers. And it's used every day by browser engineers to
understand the performance characteristics of the browser in different
situations, find bottlenecks, and fix them. Without these tools,
browsers would not have been able to make many of the performance
leaps they did in recent years. Good debugging tools are essential to
software engineering!
:::

Threaded Scrolling
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
this kind of jank.[^adjust]

[^adjust]: Adjust the loop bound to make it pause for about a second
    or so on your computer.

To fix this, we need the browser thread to handle scrolling, not the
main thread. This is harder than it might seem, because the scroll
offset can be affected by both the browser (when the user scrolls) and
the main thread (when loading a new page or changing the height of the
document via JavaScript). Now that the browser thread and the main
thread run in parallel, they can disagree about the scroll offset.

The best we can do is to keep two scroll offsets, one on the browser
thread and one on the main thread. Importantly, the browser thread's
scroll offset refers to the browser's copy of the display list, while
the main thread's scroll offset refers to the main thread's display
list, which can be slightly different. We'll have the browser thread
send scroll offsets to the main thread when it renders, but then the
main thread will have to be able to *override* that scroll offset if
the new frame requires it.

Let's implement that. To start, we'll need to store an `active_tab_scroll`
variable on the `Browser`, and update it when the user scrolls:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.active_tab_scroll = 0

    def clamp_scroll(self, scroll):
        height = self.active_tab_height
        maxscroll = height - (HEIGHT - self.chrome.bottom)
        return max(0, min(scroll, maxscroll))

    def handle_down(self):
        self.lock.acquire(blocking=True)
        if not self.active_tab_height:
            self.lock.release()
            return
        self.active_tab_scroll = self.clamp_scroll(
            self.active_tab_scroll + SCROLL_STEP)
        self.set_needs_raster_and_draw()
        self.needs_animation_frame = True
        self.lock.release()
```

This code calls `set_needs_raster_and_draw` to redraw the screen with
a new scroll offset, and also sets `needs_animation_frame` to cause
the main thread to receive the scroll offset asynchronously in the
future. Even though the browser thread has already handled scrolling,
it's still important to synchronize the new value back to the main
thread soon because APIs like click handling depend on it.

The scroll offset also needs to change when the user switches tabs,
but in this case we don't know the right scroll offset yet. We need
the main thread to run in order to commit a new display list for the
other tab, and at that point we will have a new scroll offset as well.
Move tab switching (in `load` and `handle_click`) to a new method
`set_active_tab` that simply schedules a new animation frame:^[Note
that both callers already hold the lock, so this method doesn't need
to acquire it.]

``` {.python}
class Browser:
    def set_active_tab(self, tab):
        self.active_tab = tab
        self.active_tab_scroll = 0
        self.active_tab_url = None
        self.needs_animation_frame = True
        self.animation_timer = None
```

So far, this is only updating the scroll offset on the browser thread.
But the main thread eventually needs to know about the scroll offset,
so it can pass it back to `commit`. So, when the `Browser` creates a
rendering task for `run_animation_frame`, it should pass in the scroll
offset. The `run_animation_frame` function can then store the scroll
offset before doing anything else. Add a `scroll` parameter to
`run_animation_frame`:

``` {.python}
class Browser:
    def schedule_animation_frame(self):
        # ...
        def callback():
            self.lock.acquire(blocking=True)
            scroll = self.active_tab_scroll
            self.needs_animation_frame = False
            task = Task(self.active_tab.run_animation_frame, scroll)
            self.active_tab.task_runner.schedule_task(task)
            self.lock.release()
        # ...
```

But the main thread also needs to be able to modify the scroll offset.
We'll add a `scroll_changed_in_tab` flag that tracks whether it's done
so, and only store the browser thread's scroll offset if
`scroll_changed_in_tab` is not already true.[^scroll-complicated]

[^scroll-complicated]: Two-threaded scroll has a lot of edge cases,
including some I didn't anticipate when writing this chapter. For
example, it's pretty clear that a load should force scroll to 0
(unless the browser implements [scroll restoration][scroll-restoration]
for back-navigations!), but what about a scroll clamp followed by a browser
scroll that brings it back to within the clamped region? By splitting the
browser into two threads, we've brought in all of the challenges of
concurrency and distributed state.

[scroll-restoration]: https://developer.mozilla.org/en-US/docs/Web/API/History/scrollRestoration

``` {.python}
class Tab:
    def __init__(self, browser, tab_height):
        # ...
        self.scroll_changed_in_tab = False

    def run_animation_frame(self, scroll):
        if not self.scroll_changed_in_tab:
            self.scroll = scroll
        # ...
```

We'll set `scroll_changed_in_tab` when loading a new page or when the
browser thread's scroll offset is past the bottom of the page:

``` {.python}
class Tab:
    def load(self, url, payload=None):
        # ...
        self.scroll = 0
        self.scroll_changed_in_tab = True

    def clamp_scroll(self, scroll):
        height = math.ceil(self.document.height + 2*VSTEP)
        maxscroll = height - self.tab_height
        return max(0, min(scroll, maxscroll))

    def run_animation_frame(self, scroll):
        # ...
        self.browser.commit(self, commit_data)
        self.scroll_changed_in_tab = False

    def render(self):
        # ...
        clamped_scroll = self.clamp_scroll(self.scroll)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_tab = True
        self.scroll = clamped_scroll
        # ...
```

If the main thread *hasn't* overridden the browser's scroll offset,
we'll set the scroll offset to `None` in the commit data:

``` {.python}
class Tab:
    def run_animation_frame(self, scroll):
        # ...
        scroll = None
        if self.scroll_changed_in_tab:
            scroll = self.scroll
        commit_data = CommitData(
            self.url, scroll, document_height, \
            self.display_list)
        # ...
```

The browser thread can ignore the scroll offset in this case:

``` {.python}
class Browser:
    def commit(self, tab, data):
        if tab == self.active_tab:
            # ...
            if data.scroll != None:
                self.active_tab_scroll = data.scroll
```

::: {.web-only}

That's it! If you try the counting demo now, you'll be able to scroll
even during the artificial pauses.
[Here](examples/example12-count-with-scroll.trace) is a trace that
shows threaded scrolling at work (notice how raster and draw now
sometimes happen at the same time as main-thread work), and it's visualized
in Figure 4.

:::

::: {.print-only}

That's it! If you try the counting demo now, you'll be able to scroll even
during the artificial pauses. Figure 4 is a trace screenshot that shows threaded
scrolling at work (notice how raster and draw now sometimes happen at the same
time as main-thread work).

:::

::: {.center}
![Figure 4: Trace output of threaded scrolling on the counting demo.](examples/example12-count-with-scroll.png)
:::

As you've seen, moving tasks to the
browser thread can be challenging, but can also lead to a much more
responsive browser. These same trade-offs are present in real
browsers, at a much greater level of complexity.

::: {.further}

Scrolling in real browsers goes *way* beyond what we've implemented
here. For example, in a real browser JavaScript can listen to a
[`scroll`][scroll-event] event and call `preventDefault` to cancel
scrolling. And some rendering features like [`background-attachment:
fixed`][mdn-bg-fixed] are hard to implement on the browser
thread.[^not-supported] For this reason, most real browsers implement
both threaded and non-threaded scrolling, and fall back to
non-threaded scrolling when these advanced features are
used.[^real-browser-threaded-scroll] Concerns like this also drive
[new JavaScript APIs][designed-for].

:::

[scroll-event]: https://developer.mozilla.org/en-US/docs/Web/API/Document/scroll_event

[^real-browser-threaded-scroll]: Actually, a real browser only falls
back to non-threaded scrolling when necessary. For example, it might
disable threaded scrolling only if a `scroll` event listener calls
`preventDefault`.

[mdn-bg-fixed]: https://developer.mozilla.org/en-US/docs/Web/CSS/background-attachment

[designed-for]: https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/addEventListener#passive

[^not-supported]: Our browser doesn't support any of these features,
so it doesn't run into these difficulties. That's also a strategy. For
example, until 2020, Chromium-based browsers on Android did not
support `background-attachment: fixed`.

Threaded Style and Layout
=========================

Now that we have separate browser and main threads, and now that some
operations are performed on the browser thread, our browser's thread
architecture has started to resemble that of a real
browser.[^processes] But why not move even more browser components
into even more threads? Wouldn't that make the browser even faster?

[^processes]: Note that many browsers now run some parts of the
    browser thread and main thread in different processes, which has
    advantages for security and error handling.
    
In a word, yes. Modern browsers have [dozens of
threads][renderingng-architecture], which together serve to make the
browser even faster and more responsive. For example, raster-and-draw
often runs on its own thread so that the browser thread can handle
events even while a new frame is being prepared. Likewise, modern
browsers typically have a collection of network or input/output (I/O) threads, which
move all interaction with the network or the file system off the
main thread.

[renderingng-architecture]: https://developer.chrome.com/blog/renderingng-architecture/#process-and-thread-structure

On the other hand, some parts of the browser can't be easily threaded.
For example, consider the earlier part of the rendering pipeline:
style, layout and paint. In our browser, these run on the main thread.
But could they move to their own thread?

In principle, yes. The only thing browsers *have* to do is implement
all the web API specifications correctly, and draw to the screen after
scripts and `requestAnimationFrame` callbacks have completed. The
specification spells this out in detail in what it calls the
"[update-the-rendering]" steps. These steps don't mention
style or layout at all---because style and layout, just like paint and
draw, are implementation details of a browser. The specification's
update-the-rendering steps are the *JavaScript-observable* things that
have to happen before drawing to the screen.

[update-the-rendering]: https://html.spec.whatwg.org/multipage/webappapis.html#update-the-rendering

Nevertheless, in practice, no current modern browser runs style or
layout on any thread but the main one.[^servo] The reason is simple: there
are many JavaScript APIs that can query style or layout state. For
example, [`getComputedStyle`][gcs] requires first computing style, and
[`getBoundingClientRect`][gbcr] requires first doing
layout.[^nothing-later] If a web page calls one of these APIs, and
style or layout is not up to date, then it has to be computed then and
there. These computations are called *forced style* or *forced
layout*: style or layout are "forced" to happen right away, as opposed
to possibly 33 ms in the future, if they're not already computed.
Because of these forced style and layout situations, browsers have to
be able to compute style and layout on the main thread.[^or-stall]

[gcs]: https://developer.mozilla.org/en-US/docs/Web/API/Window/getComputedStyle
[gbcr]: https://developer.mozilla.org/en-US/docs/Web/API/Element/getBoundingClientRect

[^or-stall]: Or the main thread could force the browser thread to
do that work, but that's even worse, because forcing work on the
compositor thread will make scrolling janky unless you do even more work to
avoid that somehow.

[^servo]: Some browsers do use multiple threads *within* style and
    layout; the [Servo] research browser was the pioneer here,
    attempting a fully parallel style, layout, and paint phase. Some of
    Servo's code is now part of Firefox. Still, even if style or
    another phase uses threads internally, those steps still don't
    happen concurrently with, say, JavaScript execution.
    
[Servo]: https://en.wikipedia.org/wiki/Servo_(software)

[^nothing-later]: There is no JavaScript API that allows reading back
    state from anything later in the rendering pipeline than layout,
    which is what made it possible to move the back half of the pipeline to
    another thread.

One possible way to resolve these tensions is to optimistically move
style and layout off the main thread, similar to optimistically doing
threaded scrolling if a web page doesn't `preventDefault` a scroll. Is
that a good idea? Maybe, but forced style and layout aren't just
caused by JavaScript execution. One example is our implementation of
`click`, which causes a forced render before hit testing\index{hit testing}:

``` {.python}
class Tab:
    def click(self, x, y):
        self.render()
        # ...
```

It's possible (but very hard) to move hit testing off the main thread or to do
hit testing against an older version of the layout tree, or to come up with
some other technological fix. Thus it's not
*impossible* to move style and layout off the main thread
"optimistically", but it *is* challenging. That said, browser
developers are always looking for ways to make things faster, and I
expect that at some point in the future style and layout will be moved
to their own thread. Maybe you'll be the one to do it?

::: {.further}

Browser rendering pipelines are strongly influenced by graphics and
games. Many high-performance games are driven by event loops, update a
[scene graph][scene-graph] on each event, convert the scene graph
into a display list, and then convert the display list into pixels.
But in a game, the programmer knows *in advance* what scene graphs
will be provided, and can tune the graphics pipeline for those graphs.
Games can upload hyper-optimized code and pre-rendered data to the CPU
and GPU memory when they start. Browsers, on the other hand, need to
handle arbitrary web pages, and can't spend much time optimizing
anything. This makes for a very different set of trade-offs, and is why
browsers often feel less fancy and smooth than games.

:::

[scene-graph]: https://en.wikipedia.org/wiki/Scene_graph

Summary
=======

This chapter demonstrated the two-thread rendering system at the core
of modern browsers. The main points to remember are:

- The browser organizes work into task queues, with tasks for things
  like running JavaScript, handling user input, and rendering the page.
- The goal is to consistently generate frames to the screen at a 30 Hz
  cadence, which means a 33 ms budget to draw each animation frame.
- The browser has two key threads involved in rendering.
- The main thread runs JavaScript and the special rendering task.
- The browser thread draws the display list to the screen,
  handles/dispatches input events, and performs scrolling.
- The main thread communicates with the browser thread via `commit`,
  which synchronizes the two threads.

Additionally, you've seen how hard it is to move tasks between the two
threads, such as the challenges involved in scrolling on the browser
thread, or how forced style and layout makes it hard to fully isolate
the rendering pipeline from JavaScript.

::: {.web-only}

Click [here](widgets/lab12-browser.html) to try this chapter's
browser.

:::

Outline
=======

The complete set of functions, classes, and methods in our browser 
should now look something like this:

::: {.web-only .cmd .python .outline html=True}
    python3 infra/outlines.py --html src/lab12.py --template book/outline.txt
:::

::: {.print-only .cmd .python .outline}
    python3 infra/outlines.py src/lab12.py --template book/outline.txt
:::

::: {.web-only}
If you run it, it should look something like [this
page](widgets/lab12-browser.html); due to the browser sandbox, you
will need to open that page in a new tab.
:::

Exercises
=========

12-1 *`setInterval`*. [`setInterval`][setInterval] is similar to `setTimeout`
but runs repeatedly at a given cadence until
[`clearInterval`][clearInterval] is called. Implement these APIs. Make
sure to test `setInterval` with various cadences in a page that also
uses `requestAnimationFrame` with some expensive rendering pipeline
work to do. Record the actual timing of `setInterval` tasks; how
consistent is the cadence?

[setInterval]: https://developer.mozilla.org/en-US/docs/Web/API/WindowOrWorkerGlobalScope/setInterval
[clearInterval]: https://developer.mozilla.org/en-US/docs/Web/API/WindowOrWorkerGlobalScope/clearInterval

12-2 *Task timing*. Modify `Task` to add trace events every time a task
executes. You'll want to provide a good name for these trace events.
One option is to use the `__name__` field of `task_code`, which will
get the name of the Python function run by the task.

12-3 *Clock-based frame timing*. Right now our browser schedules each
animation frame exactly 33 ms after the previous one completes. This
actually leads to a slower animation frame rate cadence than 33 ms. Fix
this in our browser by using the absolute time to schedule animation
frames, instead of a fixed delay between frames. Also implement main-thread
animation frame scheduling that happens *before* raster and draw, not after,
allowing both threads to do animation work simultaneously.

12-4 *Scheduling*. As more types of complex tasks end up on the event
queue, there comes a greater need to carefully schedule them to ensure
the rendering cadence is as close to 33 ms as possible, and also to
avoid task starvation. Implement a task scheduler with a priority
system that balances these two needs: prioritize rendering tasks and
input handling, and deprioritize (but don't completely starve) tasks that
ultimately come from JavaScript APIs like `setTimeout`. Test it out on a
web page that taxes the system with a lot of `setTimeout`-based tasks.

12-5 *Threaded loading*. When loading a page, our browser currently waits
for each style sheet or script resource to load in turn. This is
unnecessarily slow, especially on a bad network. Instead, make your
browser send off all the network requests in parallel. You must
still process resources like styles in source order, however. It may
be convenient to use the `join` method on a `Thread`, which will block
the thread calling `join` until the thread being `join`ed completes.

12-6 *Networking thread*. Real browsers usually have a separate thread for
networking (and other I/O). Tasks are added to this thread in a
similar fashion to the main thread. Implement a third *networking*
thread and put all networking tasks on it.

12-7 *Optimized scheduling*. On a complicated web page, the browser may not
be able to keep up with the desired cadence. Instead of constantly
pegging the CPU in a futile attempt to keep up, implement a *frame
time estimator* that estimates the true cadence of the browser based
on previous frames, and adjust `schedule_animation_frame` to match.
This way complicated pages get consistently slower, instead of having
random slowdowns.

12-8 *Raster-and-draw thread*. Right now, if an input event arrives while
the browser thread is rastering or drawing, that input event won't be
handled immediately. This is especially a problem because [raster and
draw are slow](#profiling-rendering). Fix this by adding a separate
raster-and-draw thread controlled by the browser thread. While the
raster-and-draw thread is doing its work, the browser thread should be
available to handle input events. Be careful: SDL is not thread-safe,
so all of the steps that directly use SDL still need to happen on the
browser thread.
