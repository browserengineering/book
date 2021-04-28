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
```

As a reminder, if you're using tkinter, the call to `tkinter.mainloop()`
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
shown on the screen. These events are: `handle_click`, `keypress`, `load`,
`js_innerHTML` and `scrolldown`. tkinter makes a task on the event loop for each
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
REFRESH_RATE=16 # 16ms

class Browser:
    def __init__(self):
        self.needs_display = False

    def set_needs_display(self):
        if not self.needs_display:
            self.needs_display = True
            self.canvas.after(REFRESH_RATE, self.run_rendering_pipeline)
```

For `handle_click`, this means replacing a call to `self.reflow(self.focus)`
with `self.set_needs_display`. But that's not all---if we just called
`set_needs_display`, the fact that it was `self.focus` that needed reflow
would be lost. To solve that we'll record the need for a reflow in a new
variable:

``` {.python}
class Browser:
    # ...
    self.


1. Optimize `run_rendering_pipeline()` and `handle_event()` to run as fast as
possible.
2. Avoid using up the frame budget calling `handle_event()` too many times.

You've already seen several ways to optimize `run_rendering_pipeline()`, such as
[not painting](graphics.md#faster-rendering)  content that is offscreen and
[optimizing](reflow.md) partial layouts. Real browsers implement many more such
optimizations, and some of those will be described in detail in later chapters.
What about `handleEvent()` though? While a browser might be fast to handle
keyboard input in a form control or when scrolling, input events can also be
handled by JavaScript. Browser developers can---and do---optimize JavaScript
runtimes to be faster and faster over time. But even so, it's always possible
that the JavaScript on the website is unavoidably slow; in addition it's
in general impossible for the browser to guess how fast it will run.

Anther complication is that the "event loop" is not just for handling input
events. It is also where javascript tasks of all kinds run [^except-webworkers].
For example, event listeners related to the DOM such as the
[`load`](https://developer.mozilla.org/en-US/docs/Web/API/Window/load_event) are
run on the event loop; while `load` is an event, it's certainly not related to
input. And there are plenty of event loop tasks that are not due to events at
all. An example is the JavaScript function `setTimeout`; calling
`setTimeout(foo, 100)` will place a task on the event loop to be executed 100ms
in the future. There are other tasks as well, such as parsing HTML or loading
objects such as images, style sheets, and fonts into the document after their
network fetches complete.

[event
loop](https://html.spec.whatwg.org/multipage/webappapis.html#event-loops)

There is often a required order to the tasks on the event loop; each such group
of ordered tasks is called a [task
queue](https://html.spec.whatwg.org/multipage/webappapis.html#task-queue). Input
events form a task queue, as it's not allowed to execute them in a different
order than they occured (imagine the chaos if the browser saw your keypresses
out of order while typing a sentence!). Likewise as you would
expect,`setTimeout` callbacks form a task queue --- ones scheduled to run
earlier must execute before ones scheduled to run later. Different task queues
need not coordinate with each other; the browser may handle as many input events
as it likes before the first `setTimeout` callback.

However, just because there are multiple task queues in a single event loop does
not mean that those task queues can run [in
parallel](https://html.spec.whatwg.org/multipage/infrastructure.html#in-parallel)
with each other. It just means that each queue must be run in queue order
[^not-even-a-queue]. In fact, the vast majority of JavaScript tasks cannot be
run in parallel with the event loop. This is due to a design choice for the web,
namely that JavaScript is a an event-based, single-threaded programming language
(at least wihin the same [execution
context](https://tc39.es/ecma262/#sec-execution-contexts); more on that
shortly). For these reasons, the event loop for a web page is more or less
required to happen on a single CPU thread (this primary web page thread is
called the *main thread*).

[^not-even-a-queue]: Fun fact: tasks queues are technnically not even tasks,
[they are
sets](https://html.spec.whatwg.org/multipage/webappapis.html#task-queue). In
practice they act like queues, but in certain corner cases, a task associated
with an inactive document is skipped. This is a good example of how the web
platform has a lot of subtlety in its fullest definition, but that subtlety
is not necessary to understand for anyone but browser developers.

Now let's come back to the problem of the frame budget. This is a huge problem
for web site performance, because CPU parallelism is one of the best ways to
reliably meet the requirements of the frame budget. This is for two reasons:
first, doing two things in parallel is up to twice as fast as doing them in
serial; second - and perhaps more importantly - two tasks need be slowed down by
either other if they don't depend on each other (this is the main benefit of
pre-emptive multitasking).

[^except-webworkers]: Exect for javascript that is part of a WebWorker or
Worklet, but we won't discuss that topic in this chapter.

The real event loop looks more like this:

``` {.python expected=False}
while True:
    now = currentTimeMs()
    while (currentTimeMs() - now < estimatedFrameBudget() and
          not pendingEventsAndTasks().empty()):
        handlePendingEventOrTask(pendingEventsAndTasks().dequeue()):
    processFrameAlignedEvents()
    updateTheRendering()
    drawScreen()
)
```

There is a priority queue[^priority-queue], here represented by
`pendingEventsAndTasks`. Each time through the while loop, the browser processes
as many events off the priority queue as it can until the estimated frame budget
(estimated because we can't really be sure how much time updateTheRendering or
any given task will take to complete) is exhausted, or the queue is empty. Then
we process the *frame-aligned events*, which are the *continuous* input events
[^continuous-input-event], such as touch or mouse moves. Finally, we "update the
rendering". In all its [gory
detail](https://html.spec.whatwg.org/multipage/webappapis.html#update-the-rendering),
there is a whole lot of work potentially happening. All of these steps are
important for a real browser, and most of them have to do with opportunities to
run more javascript, but for now let's just focus on the rendering pipeline.

One think you'll notice by looking closely at the spec is that the "update the
rendering" steps don't actually say anything about "rendering" - for example
they don't say when to run style or layout. This is because the spec
intentionally allows the browser to compute styles when and in whatever way it
chooses, so long as it:

* Always returns an up-to-date result when javascript asks for the results of
layout, such as when calling Element.getBoundingClientRect(). * Draws to the
screen in a reasonable amount of time after the "update the  rendering" steps
complete. [^spec-draw-screen]

[^spec-draw-screen]: However, even this isn't really spelled out or required 
per se in the spec; instead the speed of drawing to the screen is an expected
task of a good browser that one would want to use.

[^priority-queue]: In some cases the browser may execute in something other than
first-in-first-out order; for example input events are usually prioritized over
other tasks.

[^continuous-input-event]: These are events that are likely to be associated
with a user gestuure that requires quick feedback, such as scrolling. For that
reason, they are processed just before updating rendering. Other events such as
keyboard input or mouse clicks are called *discrete* events, and are handled in
regular tasks in the priority queue).

Browsers do a whole lot of performance work to optimize the event loop, with the following primary goals:

* *Responsiveness*: time from action to response. Example: time from click on a button on the webpage to the screen updating accordingly.

* *Smoothness*: consistency of responsiveness, and adherence to the frame
budget. Example: a nice, smoooth experience scrolling a web page.

* *Isolation*: avoiding slowness in one component causing unpredictable behavior
in another. Example: avoiding unpredictable slowdowns in performance of the web
page due to a javascript task taking too long to run.

Because of this flexibility there are all sorts of optimizations made by
real browsers to achieve the following goals:

1. Reduce the time to draw to the screen (responsiveness)
2. Make interactions with web pages more smooth (smoothness)
3. Do as much work as possible off the main thread (isolation)

Browsers can improve all of these with techniques such as:

* Optimize browser and javascript code to run faster (improves responsiveness
and smoothness in most cases)

* Do more rendering pipeline work on other threads or CPU processes (improves
isolation, and may (or may not) improve responsiveness or smoothness)

* Take advantage of hardware acceleration (usually improves responsiveness and smoothness, but not always)

* Schedule main thread work to reduce typical delay (can improve smoothness and
* responsiveness, depending on the work load)

* Perform some operations without using the main thread at all (improves
isolation massively for scrolling and animations, and usually improves
smoothness and responsiveness)

A typical real browser today has the following architecture for rendering web page:
 
* A main thread to run javascript and most of the rendering pipeline (everything
up to making a display list)

* A second CPU thread, group of threads, or CPU process, typically called the
*compositor* to coordinate compositing, rasterize display lists (typically using
the GPU), decode images, and perform scrolling and CSS animations (when possible
- some scrolling and CSS animations still involve the main thread).

IFrames, workers and worklets
=============================

The `<iframe>` element is the way to embed one website into another, like so:

```
<!doctype HTML>
<html>
  <body>
    ...
    <iframe style="width: 100%; height: 100px" src="http://iframe-website-url">
  ...
</body>
```

The *child* iframe's website is allocated a rectangular area within its *parent*
document, according to the usual rules of layout. In the above example, the
iframe is as wide as the `<body>` element, and `100px` tall. It is styled, laid
out and painted as if it was loaded into a browser window with those dimensions.
If the iframe's URL has the same [origin](security.md#same-origin-policy) as its
parent, then its javascript and DOM end up in the same event loop as the parent,
because javascript in the iframe has the ability to access the DOM of its parent
synchronously. If not, the child iframe can still talk to its parent, but only
via a special asynchronous `postMessage` API that is designed to allow the child
iframe to have its own independent event loop, and provides enough security
guarantees to make it safe to embed an un-trusted child iframe into your
website.

Of course, since the event loop of such iframes are different, they can in
principle be run on different threads or CPU processes. Interestingly enough, it
took about *twenty years* for a browser to successfully pull this off.
[^why-so-long-for-oopif] So far only Chromium has been able to ship such "out of
process iframes". The main reason to do this work is actually security, since
CPU processes provide a much more effective security sandbox against malicious
sites than other techniques. However, there is also a nice performance benefit
as well, in terms of the *isolation* goal presented in the previous section:
such *site-isolated* iframes automatically avoid making each other have
unpredictable performance, in the same way native applications on a computer
don't do that either.

[^why-so-long-for-oopif]: Some of the reasons are that the iframe element
actually has a lot of APIs on it, very difficult and potentially scary security
constraints,  and complex browser implementation details having to do with the
fact that such iframes are drawn together with their parent frames into the same
window. Another is that once you've built up a ton of code assuming one browser
architecture, it's really hard to change that architecture in a big way.

In addition to iframes, there are also multiple types of *workers* available to
javascript that can run in different threads or processes. As mentioned earlier,
it's not possible in javascript to run code from the same execution context
[^execution-context] at the same time in multiple threads, so all the types of
workers get their own execution contexts. This means that if you want to run the
same code on the main thread event loop and in a worker, you have to load it
twice. In addition, the DOM is not designed in a re-entrant or transactional
way, so it's also not possible to directly access the DOM from a worker. Since
input events are all targeted at the DOM, they are not available to workers
either.

Here are the types of workers:

* A [Web
Worker](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API/Using_web_workers)
is basically an extra thread on which you can run code. These workers can communicate
with the main thread and pass certain kinds of data back and forth, through the
`postMessage` API.

* A [Service
Worker](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API) is
a special kind of worker that sits between the network and the website, acting a
bit like a web proxy.

* A [Shared
Worker](https://developer.mozilla.org/en-US/docs/Web/API/SharedWorker) is like a
Web Worker, but is shared between all of the windows that have the same origin.

* A [Worklet](https://developer.mozilla.org/en-US/docs/Web/API/Worklet) is a
special kind of worker carefully defined to be able to fit into the rendering
pipeline, and may be run on a compositor thread or process accordingly. For
example a
[PaintWorket](https://developer.mozilla.org/en-US/docs/Web/API/PaintWorklet) is
a way of delegating to javascript the way to make a display list, and if paint
happens to be happening in a different thread or process, that is possible.

[^execution-context]: What is an execution context, you miht ask? It's quite
simple. When you write an imperative computer program like javascript, you
define your global variables, functions and classes, and call recursive
functions using a stack. All those things put togeter, basically, is an
execution context.

In recent years, Web Workers also acquired their own rendering event loop. Why you
might ask, if there is no DOM in such workers? It's because there is now a way
to use the Canvas API on a worker, through an API called OffscreenCanvas.
The Canvas API works very similarly to the `tkinter.Canvas` API first explored
in chapter 2 - there is a bit map, and methods to draw into it. This canvas
is then (asynchronously) drawn into the main page's overall canvas in a way
similar to out of process iframes.

Paint vs raster
===============

Up this point, we didn't draw much attention to the distinction between creating
a display list and executing the commands of the display list (e.g. via the
tkinter Python library). Nor did we really say much about what tkinter does
when you call its API methods. Now is the time to dig into this topic. :)

What typically happens during canvas APIs is what we'll call *raster* -
converting display list commands into pixels within a bitmap or texture. A
*bitmap* is a computer memory data structure representing a 2D array of colors
of a fixed width and height. Within the bitmap, each (x, y) position of the
array is called a *pixel*, and has a piece of memory representing its color. And
of course, if one wanted to map such a bitmap to the computer's screen, the
colors on the screen in the 2D rectangle of the same screen-pixel-dimension as
the bitmap would end up with those colors. A *texture* is the name typically
used for a bitmap when it is stored within GPU memory (the name has to do with
the way these objects are integrated into GPU rendering APIs).

One thing to keep in mind for now is that raster can be quite slow, depending
on how it's done and how complex the display list is. You saw examples of this
regarding fonts in [chapter 2](graphics.md#faster-rendering). There are
various ways to make raster faster that we'll get into in later chapters, but
in general it's a slow enough operation that keeping track of when it happens,
and minimizing the amount of it, will be important.

Raster is quite complex, and some of this complexity will be discussed in
[chapter 12](visual-effects.md). For now, it's good to know that fonts and
images are some of the most difficult parts to handle. Fonts are particularly
difficult to draw with high quality and speed on GPUs. Images have an additional
problem in that they are almost always represented in a highly compressed form
(to make them fast to download), but must be decompressed before being
rasterized. The decompression process can be slow and use a lot of memory,
and if a GPU is being used to raster, the decompressed image also has to be
uploaded to GPU kmemory.

Multi-process compositing, multiple canvases
============================================

Let's call a CPU process that is in charge of rendering a web page a *render
process*. If there are multiple render processes involved in rendering a web
page, then somehow those processes need to coordinate on how to compose their
painted output together on the screen. How is that done?

For example, suppose you want to render a web page like this:

```
<html>
  <iframe src="cross-origin-url">
</html>
```

In this example, there may be two processes - one for the main
document of the web site, and one for the cross-origin iframe. The main document
has a canvas that's the size of its laid-out document, as constrained by the
size of the browser window. The iframe document, likewise, is rendered into a
canvas that is constrained by the laid-out size of the `<iframe>` element in
it's parent's document.

Combining these two canvases mostly involves drawing the iframe document's
canvas on top of the main document one. [^compositing-can-be-complex] This
process is called *compositing*. In art or graphics design, there is often a
distinction between drawing of individual images, and "compositing" (sometimes
also called layering) those images on top of each other to create the final
artwork. Likewise, web browsers have the same concept: there can be multiple
"canvases" on which to paint content, which are then *drawn* together to make
the final display on the computer screen.

[^compositing-can-be-complex]: As you will see in [chapter
12](visual-effects.md), the `<iframe>` element in the main document could have
any number of visual effects applied to it, such as a more complex clip,
transform, opacity or filter, which makes this process significantly more
complex.

Let's also take a moment to draw a distinction between *compositing* and *draw*.
The term *compositing* is often overloaded to mean many things in descriptions
of rendering. In this book it means "the strategy or technique for using
multiple canvases to render a web page". The term *draw* refers to the
"algorithm or rendering step to combine these canvases into screen pixels".
In other words, compositing is deciding to break up the work into multiple
canvses, and drawing is putting them back together at the end.

The browser has a choice - as part of its *compositing strategy* - for whether
to render an iframe's contents into its own canvas. You might think that if
the iframe has its own render process, it's required to have its own canvas,
but that's not necessary. For example, the browser might generate the display
list from the content of the iframe and then send it to the parent's render
process, without first drawing to a canvas. This display list would then be
merged into the display list for the parent document and drawn together into a
common canvas.

As it turns out, no browser with out-of-process iframes actually does this.
But it's not an inherently bad idea, and might happen in the future. (One
reason to do so is that having fewer canvases saves memory.)

Multiple canvases within one document
=====================================

Multiple render processes are not the only way to end up with multiple canvases.
Even on a web page without iframes, it is certainly possible to break up the
page into multiple logical pieces and have display lists and canvases for each
piece. 

TBD: fill in the rest

Forced renders
==============

Up to this point, we've described a rendering pipeline that runs to completion
on all frames. However, there are several scenarios where we don't need to
run the entire pipeline, because the desired output is not the final pixels
on screen, but some intermediate piece of information related to style
or layout specifically. These cases are called *forced renders*; developers
often called them "forced styles" or "forced layouts". Examples include:

* Hit testing. Hit testing is what you implemented in [chapter
7](chrome.md#hit-testing) to figure out which element is underneath a mouse
click. Hit testing depends on layout being already done, so if it is not done
yet, then it must be force-completed.

* Javascript style readbacks. There are a number of JavaScript APIs that allow inspecting
the style of an element, for example the `Element.getComputedStyle` method.

* Javascript layout readbacks. Likewise, there are various APIs that can read the laid-out
position and size of an element; an example is `element.getBoundingClientRect`.

* Javascript APIs that that need to compute style or layout as part of their
algorithm. This is because there are various APIs that can do things like
changing focus (`Element.focus`) or scroll offset `Element.scrollTop`, but
whether an element is focusable or scrollable depends on its style. In the case
of scrolling, the actual scroll offset also depends on layout.

These situations complicate the story for rendering pipelining. The browser
would like to do rendering at convenient time - during the "update the
rendering" steps, but these APIs force it to happen right away - synchronously
- and certainly not on a different CPU thread or process. Even worse, it's
possible, and sometimes happens in practice, where style or layout have to happen over and over inside a single
frame. Consider javascript code like this:

```
  changeDOM1();
  document.body.getBoundingClientRect();
  changeDOM2();
  document.body.getBoundingClientRect();
```

In this situation, style and layout may have to be computed twice in succession,
because `changeDOM1` and `changeDOM2` might have changed the inputs to style or
layout. And of course it could happen more than two times. Because style or
layout are run over and over without finishing a frame, this situation is called
*render thrashing*, by analogy with the constant page faults and grinding to a
halt that happens when computers start to run out of memory. This situation may
look contrived, but in a large website, it can be surprisingly easy to
accidentally have a situation like this occur, because large websites have a lot
of code to render different elements, and they are hard to coordinate.

Components of a web rendering pipeline
======================================

We're now ready to put together all the sequential steps  of the rendering
pipeline of a real web browser. Each of these components can be optimized,
scheduled to run at convenient times, and in some cases run on parallel CPU
threads or processes.

1. DOM Parsing & updating. This happens when loading a web page, a script
task during the rendering event loop that changes DOM state in some way, or
the browser reacts to input such as typing characters in an input form element
or a scroll. While scripts are out of control of the browser, *when* the script
runs is to some extent within the control of the browser. The loading of a
web page and when & how to do this loading is entirely within the control of the
browser. Likewise, when to issue input events and react to them is within the
control of the browser.

2. Style. This is the first stage of rendering that can in many cases be delayed
only until necessary, and in principle run in parallel with the main thread
during the "update the rendering" step of the event loop.
Subsequent steps can also in principle run in parallel with the main thread.

3. Layout. The *layout tree* is created, and the sizes and 
positions of the layout objects are determined.

4. Paint. An algorithm walks the layout tree in a specified order and generates
a display list that depends on the layout and style of each object.

5. Compositing. A strategy is applied to break up the display list into
independent contiguous pieces, and each of the pieces is assigned to a different
canvas. The strategy is optimized for reducing expected raster costs, and for
allowing more expected interactions to avoid depending on the main thread.

6. Raster. Converting the display lists for canvases in to bitmaps or textures.
This can get quite complicated when trying to use advanced GPU features, and
in the presence of fonts and images.

7. Draw. combining the rastered canvases together to produce on-screen pixels.
This is typically done on a GPU, but in more advanced situations can be complex
and slow to run unless optimized properly.

::: {.further}
These days, many web sites are developed using a *web rendering framework*; the
most popular example at the moment is [React](https://reactjs.org/), but there
are a number of others that are also popular. These frameworks often have the
concept of "virtual DOM" - application state stored in JavaScript data
structures similar to the DOM. The web site developer writes JavaScript that
creates virtual DOM, but does not interact directly with regular DOM.
Periodically, the framework does work to convert the virtual DOM to regular DOM;
it is the job of the framework to decide how and when to do so. Hit testing and
DOM-related events are to some extent also proxied through the framework.

There are several advantages for the developer when using a framework. Perhaps
the biggest is that the framework takes care of much of the work of optimizing
*invalidation* (caching for performance) of DOM when application state changes. 

Therefore the *virtual DOM commit*, as we might call it, looks a lot like an
additional step of the pipeline between steps one and two.
:::

Summary
=======

This chapter explained in more detail rendering architectures of browsers. The
main points to remember are:

- A main thread event loop that runs regular JavaScript tasks, DOM manipulations,
and other tasks related to input and resources.

- The difficulties of statying within the frame budget given the lack of
predictability of JavaScript tasks and even rendering work itself

- Techniques to deal with this complexity, and how they all work to exploit
isolation, improve smoothness and/or improve responsiveness,

- How cross-origin iframes have their own event loop and possibly run in a
different process that runs in parallel with the main one

- All the steps in a multi-process rendering pipeline's update-the-rendering
- steps:
  
  * Parse & update DOM
  
  * Style
  
  * Layout
  
  * Paint

  * Compositing

  * Raster 

  * Draw 