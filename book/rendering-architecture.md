---
title: The Rendering Architecture
chapter: 13
prev: visual-effects
next: skipped
...

The Rendering Event Loop
========================

Our browser now knows how to load a web page with HTTP and parse it into an
HTML tree & style sheets. It can also *render* the page, by constructing the
layout tree, computing styles on it, laying out its contents, and painting the
result to the screen. These rendering steps make up a basic
[*rendering pipeline*](https://en.wikipedia.org/wiki/Graphics_pipeline) for the
browser.

But of course, there is more to web pages than just running the rendering
pipeline. There is keyboard/mouse/touch input, scrolling, interacting with
browser chrome, submitting forms, executing scripts, loading things off the
network, and so on. All of these are *tasks* that the browser executes. The
rendering pipeline is also a task. To keep track of the list of tasks that it
needs to execute next, a browser maintains a set of *task queues*.

When the browser is free to do work, it finds the next task in line from one of
the queues and runs it; when it's done it repeats, and so on. This process is
called an *event loop*.[^event-loop] There is more than one event loop in a
real browser, but the most important one is the *rendering event loop*.

[^event-loop]: Event loops were also briefly touched on in
[chapter 2](graphics.md#eventloop). Tkinter uses an event loop behind the scenes
to run our browser code (that's what `tkinter.mainloop` does).

In this chapter we'll first introduce the task queue concept into our browser.
Then we'll dive into the rendering event loop, its performance, and its
complexities. All this work will then pay off handsomely---we'll be ready to
implement the compositor thread.[^compositor-thread] Once that is done, our
browser will have an structure that is recognizably similar to real
browsers, and start to have simi\lar performance characteristics. Not bad for a
thousand lines of code or so!

[^compositor-thread]: As you'll see, the compositor thread is an extremely
important optimization present in all modern browsers. By using two CPU threads
instead of one to render, we can make pages run faster and have dramatically
better scrolling performance.

Task queues
===========

Let's implement a `Task` and a `TaskQueue` class. Then we can move all of the
rendering event loop tasks into task queues.

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

But we can't do much with this unless we implement our own rendering event loop
first, instead of relying on the tkinter one. Let's go ahead and make one now.

Implementation
==============

A simple version of the rendering event loop looks approximately like this:

``` {.python expected=False}
while True:
    while there_is_enough_time():
        run_a_task_from_a_task_queue()
    run_rendering_pipeline()
```

In other words, run some tasks from the task queue until enough time has passed
that it's time to draw to the screen. Then run the rendering pipeline. The
rendering pipeline is a task, but it's a special kind of task that is not really
in its own event queue.

How long should "enough time" be? This was first discussed in Chapter 2, which
introduced the [animation frame budget](graphics.md#framebudget), The animation
frame budget is the amount of time allocated to re-draw the screen after an
something has changed. The animation frame budget is typically about 16ms, in
order to draw at 60Hz (60 * 16.66ms ~ 1s), and matches the refresh rate of
most displays. This means that each iteration through the `while` loop should
ideally complete in at most 16ms.

It also means that the browser should not run the while loop faster than that
speed, even if the CPU is up to it, because there is no point---the screen
can't keep up anyway. For this reason, `16ms` is not just an animation frame
budget but also a desired rendering *cadence*. If an iteration of the `while`
loop finishes faster than `16ms`, the browser should wait a bit before
the next iteration.

Let's implement the rendering event loop and try to match this cadence. As a
first step, rename `layout` to `run_rendering_pipeline`, since that's
what it does:

``` {.python}
def run_rendering_pipeline(self):
    # ...
```

Next, let's work on the cadence. Currently, our browser runs the rendering
pipeline  *immediately* after each possible event that might cause a change to
what is shown on the screen. Instead of running the rendering pipeline
immediately, the browser should *schedule* it to run up to 16ms in the
future, if needed. Those methods also call `reflow` directly and not `layout`;
we'll need to fix that too.

Let's add a new `set_needs_animation_frame` method, and use the `after` method
on a tkinter canvas to do the scheduling for us on its internal event loop:

``` {.python expected=False}
REFRESH_RATE_MS = 16 # 16ms

class Browser:
    def __init__(self):
        self.needs_animation_frame = False

    def set_needs_animation_frame(self):
        if not self.needs_animation_frame:
            self.needs_animation_frame = True
            self.canvas.after(REFRESH_RATE_MS,
                              Task(self.run_rendering_pipeline))
```

We'll also need to store off which elements need reflow via a new
`set_needs_reflow` method:

``` {.python expected=False}
class Browser:
    # ...
    self.reflow_roots = []

    def set_needs_reflow(self, layout_object):
        self.reflow_roots.append(layout_object)
        self.set_needs_animation_frame()

    def run_rendering_pipeline():
        # ...
        for reflow_root in self.reflow_roots:
            self.reflow(reflow_root)
        self.reflow_roots = []
```

Now modify `handle_click`, `keypress`, `load`, `js_innerHTML` and
`scrolldown` to use these methods. Here's `handle_click`:

``` {.python}
    def handle_click(self, e):
        # ...
        self.set_needs_reflow(self.focus)
```

Next, wrap each of the event handler callbacks in a `Task` object (this doesn't
use the `TaskList` class yet, but we'll get to that soon):[^currying]

``` {.python expected=False}
class Browser
    def __init__:
        self.window.bind("<Down>",
            self.bind_task(self.scrolldown))
        self.window.bind("<Button-1>",
            self.bind_task(self.handle_click))
        self.window.bind("<Key>",
            self.bind_task(self.keypress))
        self.window.bind("<Return>",
            self.bind_task(self.press_enter))

    def bind_task(self, task):
        return functools.partial(self.schedule_task, task)

    def schedule_task(self, task, event):
        self.canvas.after(0, Task(task, event))
```

[^currying]: In case you haven't seen it before, `functools.partial` takes a
function and some arguments and binds them together in a new function; this
technique is called [currying](https://en.wikipedia.org/wiki/Currying). It's
called "partial" because you can curry only some of the arguments and add the
rest later. This ends up happening in the above code in a somewhat complicated
way: tkinter will call the `Task` object like it's a function, which will in
turn execute the `__call__` method on the `Task` class, which finally passes
the `event` object to the curried task function. Complicated, but once
implemented it's pretty easy to read and think about.

Now you have an event loop that renders every 16ms!

Scripts in the event loop
=========================

In addition to event handlers, it's also of course possible for scripts to run
in the rendering event loop. In general, the rendering event loop can run any of
a wide variety of tasks, only some of which respond to input events. As we saw in
[chapter 9](scripts.md), the first way in which scripts can be run is that when
a `<script>` tag is inserted into the DOM, the script subsequently loads and
then runs. We can easily wrap all this in a `Task`, like so:

``` {.python expected=False}
    for script in find_scripts(self.nodes, []):
        header, body = request(relative_url(
            script, self.history[-1]), headers=req_headers)
        self.canvas.after(0, Task(self.js.evaljs, body))
```

Of course, scripts are not just for running straight through in one task, or
responding to input events. They can also schedule more events to be put on the
rendering event loop and run later. There are multiple JavaScript APIs in
browsers to do this, but for now let's focus on the one most related to
rendering: `requestAnimationFrame`. It's used like this:

``` {.javascript}
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
JavaScript API is as follows:

``` {.python}
    def js_requestAnimationFrame(self):
        self.needs_raf_callbacks = True
        self.set_needs_animation_frame()
```

We'll also need to wrap `run_rendering_pipeline` in a new method,
`run_animation_frame`, that first executes the JavaScript callbacks. The full
definition is below; I've taken the liberty to move `update_idletasks` out
of `run_rendering_pipeline`, since it's not really part of it:

``` {.python}
    def setup_js(self):
        # ...
        self.js.export_function(
            "requestAnimationFrame",
            self.js_requestAnimationFrame)

    def js_requestAnimationFrame(self):
        self.needs_raf_callbacks = True
        self.set_needs_animation_frame()

    def run_animation_frame(self):
        self.needs_animation_frame = False

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
    if (count < 100)
        requestAnimationFrame(callback);
    cur_frame_time = Date.now()
}
requestAnimationFrame(callback);
```

To make the above code work, you'll need this small addition to the runtime 
code:
```
function Date() {}
Date.now = function() {
    return call_python("now");
}
```
and Python bindings:
``` {.python}
def setup_js(self):
    # ...
    self.js.export_function("now", self.js_now)

def js_now(self):
    return int(time.time() * 1000)

```

This script will cause 100 animation frame tasks to run on the rendering event
loop. During that time, our browser will display an animated count from 0 to
99.

Event loop speedup
==================

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

What could we do to make Paint, for example, faster? There are a few
micro-optimizations we could try, such as pre-allocating `self.display_list`
rather than appending to it each time. I tried this on my machine, and it
showed no benefit.[^interpreted]

[^interpreted]: That may or may not be due to the interpred nature of Python
vs compiled languages such as C++.

Ok that didn't work. What now? It can be hard to guess the right
micro-optimizations, especially for interpreted languages which have speed
characteristics that are hard to predict without a lot of experience. Instead,
let's take the next step beyond using per-rendering pipeline stage timing---a
CPU profile. We can do that by using the `cPython` profiler that comes with
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
       51    0.001    0.000    6.482    0.127 lab13.py:1016(run_animation_frame)
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
mentioned above and see if you can find anything that might be optimized out.
As it turns out, there is one that is pretty easy to fix, which is the lines
that perform font measure-ment.[^how-found] Apparently, tkinter fonts don't
have a good internal cache (or perhaps they have a cache keyed off the font
object), and loading fonts is expensive.[^why-fonts-slow] But on our test page,
there is only one font! There's got to be a way to not repeat this cost for
every single layout object. Let's optimize for that situation with a font
cache:

[^how-found]: How did I figure this out? Process of elimination---comment out
some code and re-profile to see if it got faster; repeat until I found an
improvement.

[^why-fonts-slow]: Fonts are surprisingly large, sometimes on the order of
multiple megabytes. This is especially so for scripts like Chinese that have a
lot of different, complex characters. For this reason they are generally stored
on disk and only loaded into memory on-demand, and it is therefore slow to load
them. Optimizing font loading (and the cost to shape them and lay them out,
since many web pages have a *lot* of text) turns out to be one of the most
important parts of speeding up text rendering.

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
in layout *and* paint. How simple and convenient!

```
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
     65/1    0.000    0.000    1.143    1.143 {built-in method builtins.exec}
        1    0.000    0.000    1.143    1.143 lab13.py:1(<module>)
        1    0.000    0.000    1.007    1.007 __init__.py:601(mainloop)
        1    0.435    0.435    1.007    1.007 {method 'mainloop' of '_tkinter.tkapp' objects}
       51    0.000    0.000    0.572    0.011 __init__.py:1887(__call__)
       51    0.001    0.000    0.572    0.011 __init__.py:812(callit)
       51    0.002    0.000    0.570    0.011 lab13.py:1016(run_animation_frame)
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

As you can see, everything became a lot faster. This is because font measurement
overhead was making both layout and paint slower for every single object. The
new timings show that we're easily meeting the 16ms animation frame budget:

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

Various kinds of caches are the single most effective class of optimizations for
browsers. Real browsers have caches all over the place---network resource
caches and font caches are two. (Well, we haven't actually implemented a
network cache yet---maybe in a future chapter?) The rendering pipeline is no
different: there are caches of various kinds throughout style, layout, and
paint. In fact, we already saw an example of this in
[chapter 10](reflow.md). Notice that the layout tree itself is a cache, as is
the display list.)

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
component of the remaining cost, with the following breakdown (this data
is the time spent, aggregated over 50 animation frames):

```
ncalls  tottime  percall  cumtime  percall filename:lineno(function)
    52    0.005    0.000    0.391    0.008 lab13.py:1075(draw)
    873   0.003    0.000    0.201    0.000 lab13.py:676(draw)
```

Line 676 is `DrawText.draw`. Half the time drawing is in drawing text. (I
told you that fonts and text rendering are big time hogs and sources of 
optimization!)  Also note that the total
time spent drawing text is only 0.201s in this case, and therefore about 2ms per
animation frame. If the amount of text was much larger, this would become a big
problem, and we'd start missing the 16ms animation frame budget again.

Unfortunately, in this case it appears there is nothing further we can do,
without finding out where to optimize tkinter further...or is there? Let's go
back to the list of ways to make the event loop faster. We alreedy talked about
the techniques of do-less-work less work and cache. How about *parallelize*?
Can't we run these draw commands on a different thread? Yes, we can!

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
    def __init__(self, browser):
        self.lock = threading.Lock()
        self.browser = browser
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
                browser.run_animation_frame()
                self.browser.commit()

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
    def commit(self):
        self.compositor_lock.acquire(blocking=True)
        self.needs_draw = True
        self.draw_display_list = self.display_list.copy()
        self.compositor_lock.release()
```

[^fast-commit]: `commit` is the one time when both threads are both "stopped"
simultaneously---in the sense that neither is running a different task at the
same time. For this reason commit needs to be as fast as possible, so as to
lose the minimum possible amount of parallelism.

Over on the compositor thread, we need a loop that keeps looking for
opportunities to draw (when `self.needs_draw` is true), and then doing so:

``` {.python}
    def maybe_draw(self):
        self.compositor_lock.acquire(blocking=True)
        if self.needs_quit:
            sys.exit()
        if self.needs_animation_frame and not self.display_scheduled:
            self.canvas.after(
                REFRESH_RATE_MS,
                self.main_thread_runner.schedule_animation_frame)
            self.display_scheduled = True

        if self.needs_draw:
            self.draw()
        self.needs_draw = False
        self.compositor_lock.release()
        self.canvas.after(1, self.maybe_draw)
```

And of course, draw itself draws `self.draw_display_list`, not
`self.display_list`:

```
    def draw(self):
        # ....
        for cmd in self.draw_display_list:
        # ...
```

Other tasks
===========

Next up we'll move browser tasks such as loading to the main thread. Now that
we have `MainThreadRunner`, this is super easy! Whenever the compositor thread
needs to schedule a task on the main thread event loop, we just call
`schedule_browser_task`:

``` {.python}
    # Runs on the compositor thread
    def schedule_load(self, url, body=None):
        self.main_thread_runner.schedule_browser_task(
            Task(self.load, url, body))

    # Runs on the main thread
    def load(self, url, body=None):
        # ...

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
    def __init__(self):
        # ...
        self.window.bind("<Button-1>", self.compositor_handle_click)

    # Runs on the compositor thread
    def compositor_handle_click(self, e):
        self.focus = None
        if e.y < 60:
            # Browser chrome clicks can be handled without the main thread...
            if 10 <= e.x < 35 and 10 <= e.y < 50:
                self.go_back()
            elif 50 <= e.x < 790 and 10 <= e.y < 50:
                self.focus = "address bar"
                self.address_bar = ""
                self.set_needs_animation_frame()
        else:
            # ...but not clicks within the web page contents area
            self.main_thread_runner.schedule_browser_task(
                Task(self.handle_click, e))

    # Runs on the main thread
    def handle_click(self, e):
        # ...
```

The same logic holds for `keypress`:

``` {.python}
    def __init__(self):
        # ...
        self.window.bind("<Key>", self.compositor_keypress)

    # Runs on the compositor thread
    def compositor_keypress(self, e):
        if len(e.char) == 0: return
        if not (0x20 <= ord(e.char) < 0x7f): return

        if not self.focus:
            return
        elif self.focus == "address bar":
            self.address_bar += e.char
            self.set_needs_animation_frame()
        else:
            self.main_thread_runner.schedule_browser_task(
                Task(self.keypress, e))

    # Runs on the main thread
    def keypress(self, e):
        self.focus.node.attributes["value"] += e.char
        self.dispatch_event("change", self.focus.node)
        self.set_needs_reflow(self.focus)

```

As it turns out, the return key and scrolling have no use at all for the main
thread:

``` {.python}
    def __init__(self):
        # ...
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Return>", self.press_enter)

    # Runs on the compositor thread
    def press_enter(self, e):
        if self.focus == "address bar":
            self.focus = None
            self.schedule_load(self.address_bar)

    # Runs on the compositor thread
    def scrolldown(self, e):
        self.compositor_lock.acquire(blocking=True)
        self.scroll = self.scroll + SCROLL_STEP
        self.scroll = min(self.scroll, self.max_y)
        self.scroll = max(0, self.scroll)
        self.compositor_lock.release()
        self.set_needs_animation_frame()

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
    def js_innerHTML(self, handle, s):
        try:
            self.run_rendering_pipeline()
            doc = parse(lex("<!doctype><html><body>" +
                            s + "</body></html>"))
            new_nodes = doc.children[0].children
            elt = self.handle_to_node[handle]
            elt.children = new_nodes
            for child in elt.children:
                child.parent = elt
            if self.document:
                self.set_needs_reflow(
                    layout_for_node(self.document, elt))
            else:
                self.set_needs_layout_tree_rebuild()
        except:
            import traceback
            traceback.print_exc()
            raise
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
    # Runs on the main thread
    def handle_click(self, e):
        # ...
        self.run_rendering_pipeline()
        obj = find_layout(x, y, self.document)
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

