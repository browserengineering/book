---
title: Drawing to the Screen
chapter: 2
cur: graphics
prev: http
next: text
...

A web browser doesn't just download web page; it also has to show that
page to the user. In the 21^st^ century, that means a graphical
application. How does that work? In this chapter we'll equip the toy
browser with a graphical user interface [^1].

[^1]: There are some obscure text-based browsers: I used `w3m` as my
    main browser for most of 2011. I don't anymore.

Creating windows
================

Desktop and laptop computers run operating systems that provide
*desktop environments*: windows, buttons, and a mouse. So programs
don't directly draw to the screen; the desktop environment controls
the screen. Instead:

-   The program asks for a new window and the desktop environment shows
    it somewhere on the screen.
-   The program draws things in its window and the desktop environment
    puts that on the screen.
-   The desktop environment tells the program about clicks and key
    presses.
-   The desktop environment periodically asks the program to redraw
    its window.

Though the desktop environment is responsible for displaying the window, the
program is responsible for drawing its contents. Applications have to redraw
these contents quickly for interactions to feel fluid,[^3] and must respond
quickly to clicks and key presses so the user doesn't get frustrated.

<a name="framebudget">
"Feel fluid" can be made more precise. Graphical applications such as browsers
typically aim to redraw at a speed equal to the refresh rate, or *frame rate*,
of the screen, and/or a fixed 60Hz[^sixty-hertz]. This means that the browser
has to finish all its work in less than 1/60th of a second, or 16ms, in order
to keep up. For this reason, 16ms is called the *frame budget* of the
application.

::: {.further}
You should also keep in mind that not all web page interactions are animations -
there are also discrete actions such as mouse clicks. Research has shown that it
usually suffices to respond to a discrete action in 100ms - below that
threshold, most humans are not sensitive to discrete action speed. This is very
different than interactions such as scroll, where speed less than 60Hz or so is
quite noticeable. The difference between the two has to do with the way the
human mind processes movement (animation) versus discrete action, and the time
it takes for the brain to decide upon such an action, execute it, and understand
its result.
:::

[^sixty-hertz]: Most screens today have a refresh rate of 60Hz, and that
is generally considered fast enough to look smooth. However, new hardware
is increasingly appearing with higher refresh rates, such as 120Hz. Sometimes
rendering engines, games in particular, refresh at lower rates on purpose if
they know the rendering speed can't keep up.

Doing all of this by hand is a bit of a drag, so programs usually use a
*graphical toolkit* to simplify these steps. These toolkits allow you to
describe your program's window in terms of *widgets* like buttons,
tabs, or text boxes, and take care of drawing and redrawing the window
contents to match that description.

Python comes with a graphical toolkit called Tk using the Python package
`tkinter`.[^4] Using it is quite simple:

``` {.python expected=False}
import tkinter
window = tkinter.Tk()
tkinter.mainloop()
```

Here `tkinter.Tk()` creates a window and `tkinter.mainloop()` starts
the process of redrawing the screen. Inside Tk, `tkinter.Tk()` asks
the desktop environment to create the window and returns its
identifier, while `tkinter.mainloop()` enters a loop that looks
similar to this [^5]:

``` {.python expected=False}
while True:
    drawScreen()
    for evt in pendingEvents():
        handleEvent(evt)
```

Here, `drawScreen` draws the various widgets, `pendingEvent` asks the
desktop environment for recent mouse clicks or key presses, and
`handleEvent` calls into library user code in response to that event.
This *event loop* pattern is common in many applications, from web
browsers to video games. A simple window does not need much event
handling (it ignores all events) or much drawing (it is a uniform
white or gray). But in more complex graphical applications the event
loop pattern makes sure that all events are eventually handled and the
screen is eventually updated, both essential to a good user
experience.

::: {.further}
Tk's event loop is the `Tk_UpdateObjCmd` function, found in
[`tkCmds.c`][tkcmds], which calls `XSync` to redraw the screen and
`Tcl_DoOneEvent` to handle an event. There's also a lot of code to
handle errors.
:::

[tkcmds]: https://core.tcl.tk/tk/artifact/51492a6da90068a5


Drawing to the window
=====================

Our toy browser will draw the web page text to a *canvas*, a
rectangular Tk widget that you can draw circles, lines, and text
in.[^6] Tk also has widgets like buttons and dialog boxes, but our
browser won't use them: we will need finer-grained control over
appearance, which a canvas provides:[^7]

``` {.python expected=False}
WIDTH, HEIGHT = 800, 600
window = tkinter.Tk()
canvas = tkinter.Canvas(window, width=WIDTH, height=HEIGHT)
canvas.pack()
```

The first line creates the window, as above; the second creates the
`Canvas` inside that window. We pass the window as an argument, so
that Tk knows where to display the canvas, and some arguments that
define the canvas's size; I chose 800×600 because that was a common
old-timey monitor size.[^8] The third line is a Tk peculiarity, which
positions the canvas inside the window.

There's going to be a window, a canvas, and later some other things,
so to keep it all organized let's make an object:

``` {.python}
class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window, 
            width=WIDTH,
            height=HEIGHT
        )
        self.canvas.pack()
```

Once you've made a canvas, you can call methods that draw shapes on
the canvas. Let's do that inside `load`, which we'll move into the new
`Browser` class:

``` {.python expected=False}
class Browser:
    def load(self, url):
        # ...
        self.canvas.create_rectangle(10, 20, 400, 300)
        self.canvas.create_oval(100, 100, 150, 150)
        self.canvas.create_text(200, 150, text="Hi!")
```

To run this code, create a `Browser`, call `layout`, and then start
the Tk `mainloop`:

``` {.python}
if __name__ == "__main__":
    import sys
    Browser().load(sys.argv[1])
    tkinter.mainloop()
```

You ought to see: a rectangle, starting near the top-left corner of
the canvas and ending at its center; then a circle inside that
rectangle; and then the text "Hi!" next to the circle.

Coordinates in Tk refer to X positions from left to right and to Y
positions from top to bottom. In other words, the bottom of the screen
has *larger* Y values, the opposite of what you might be used to from
math. Play with the coordinates above to figure out what each argument
refers to.[^tkdocs]

[^tkdocs]: The answers are in the [online documentation][tkdocs].

[tkdocs]: http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/canvas.html

::: {.further}
The Tk canvas widget is quite a bit more powerful than what we're
using it for here. As you can see from [the
tutorial](https://tkdocs.com/tutorial/canvas.html), you can move
the individual things you've drawn to the canvas, listen to click
events on each one, and so on. In this book, I'm not using those
features, because I want to teach you how to implement them.
:::

Laying out text
===============

Let's draw a simple web page on this canvas. So far, the toy browser
steps through the web page source code character by character and
prints the text (but not the tags) to the console window. Now we want
to draw the characters on the canvas instead.

To start, let's change the `show` function from the previous chapter
into a function that I'll call `lex`[^9] which just *returns* the
text-not-tags content of an HTML document, without printing it:

``` {.python}
def lex(body):
  text = ""
  # ...
  for c in body:
      # ...
      elif not in_angle:
          text += c
    return text
```

Then, `load` will draw that text, character by character:

``` {.python expected=False}
def load(self, url):
    # ...
    for c in text:
        self.canvas.create_text(100, 100, text=c)
```

Let's test this code on a real webpage. For reasons that might seem
inscrutible[^10], let's test it on the [first chapter of <span
lang="zh">西游记</span> or "Journey to the
West"](http://www.zggdwx.com/xiyou/1.html), a classic Chinese novel
about a monkey. Run this URL[^11] through `request`, `lex`, and
`layout`.[^12] You should see a window with a big blob of black pixels
inset a bit from the top left corner of the window.

Why a blob instead of letters? Well, of course, because we are drawing
every letter in the same place, so they all overlap! Let's fix that:

``` {.python expected=False}
HSTEP, VSTEP = 13, 18
cursor_x, cursor_y = HSTEP, VSTEP
for c in text:
    self.canvas.create_text(cursor_x, cursor_y, text=c)
    cursor_x += HSTEP
```

The variables `cursor_x` and `cursor_y` point to where the next
character will go, as if you were typing the text with in a word
processor. I picked the magic numbers—13 and 18—by trying a few
different values and picking one that looked most readable. In the
[next chapter](text.md), we'll replace magic numbers with font
metrics.

The text now forms a line from left to right. But with an 800 pixel
wide canvas and 13 pixels per character, one line only fits about 60
characters. You need more than that to read a novel, so we also need
to *wrap* the text once we reach the edge of the screen:

``` {.python indent=8}
for c in text:
    # ...
    if cursor_x >= WIDTH - HSTEP:
        cursor_y += VSTEP
        cursor_x = HSTEP
```

The code increases `cursor_y` and resets `cursor_x`[^crlf] once
`cursor_x` goes past 787 pixels.[^not-800] Wrapping the text this way
makes it possible to read more than a single line.

[^crlf]: In the olden days of type writers, increasing *y* meant
    *feed*ing in a new *line*, and resetting *x* meant *return*ing the
    *carriage* that printed letters to the left edge of the page. So
    ASCII standardizes two separate characters—"carriage return" and
    "line feed"—for these operations, so that ASCII could be directly
    executed by teletypewriters. That's why headers in HTTP are
    separated by `\r\n`, even though modern computers have no
    mechanical carriage.

[^not-800]: Not 800, because we started at pixel 13 and I want to leave an
    even gap on both sides.

::: {.further}
Chinese characters are usually, but not always, independent: <span
lang="zh">开关</span> means "button" but is composed of <span
lang="zh">开</span> "on" and <span lang="zh">关</span> "off". A line
break between them would be confusing, because you'd read "on off"
instead of "button". The [ICU library][icu], used by both Firefox and
Chrome, [uses dynamic programming][icu-wb] to guess phrase boundaries
based on a [word frequency table][cjdict].
:::

[icu]: http://site.icu-project.org
[icu-wb]: http://userguide.icu-project.org/boundaryanalysis/break-rules
[cjdict]: https://github.com/unicode-org/icu/blob/master/icu4c/source/data/brkitr/dictionaries/cjdict.txt

Scrolling text
==============

Now we can read a lot of text, still not all of it: if there's enough
text, all of the lines of text don't fit on the screen. We want users
to *scroll* the page to look at different parts of it.

Scrolling introduces a layer of indirection between page coordinates
(this text is 132 pixels from the top of the *page*) and screen
coordinates (since you've scrolled 60 pixels down, this text is 72
pixels from the top of the *screen*). Generally speaking, a browser
*lays out* the page---determines where everything on the page
goes---in terms of page coordinates and then *renders* the
page---draws everything---in terms of screen coordinates.[^screen-coordinates]

[^screen-coordinates]: Sort of. What actually happens is that the page is
first drawn into a bitmap or GPU texture, then that bitmap/texture is shifted
according to the scroll, and the result is rendered to the screen. [Chapter 12](visual-effects.md)
will have more on this topic.

Our browser will have the same split. Right now `load` both computes
the position of each character and draws it: layout and rendering.
Let's have a `layout` function to compute and store the position of
each character, and a separate `render` function to then draw each
character based on the stored position. This way, `layout` can operate
with page coordinates and only `render` needs to think about screen
coordinates.

Let's start with `layout`. Instead of calling `canvas.create_text` on
each character let's add it to a list, together with its position.
Since `layout` doesn't need to access anything in `Browser`, it can be
a standalone function:

``` {.python}
def layout(self, text):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        display_list.append((cursor_x, cursor_y, c))
        # ...
    return display_list
```

The resulting list is called a *display list*: it is a list of things
to display.^[The term is standard.] Since `layout` is all about page
coordinates, we don't need to change anything else about it to support
scrolling.

Once the display list is computed, `render` needs to loop through
the display list and draw each character:

``` {.python expected=False}
class Browser:
    def render(self):
        for x, y, c in self.display_list:
          self.canvas.create_text(x, y, text=c)
```

Since `render` does need access to the canvas, we keep it a method on
`Browser`. Now the `load` just needs to call `layout` followed by
`render`:

```
class Browser:
    def load(self, url):
        headers, body = request(url)
        text = lex(body)
        self.display_list = layout(text)
        self.render()
```

Now we can add scrolling. Let's have a variable for how far you've
scrolled:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.scroll = 0
```

The page coordinate `y` then has screen coordinate `y - self.scroll`:

```
def render(self):
    for x, y, c in display_list:
        self.canvas.create_text(x, y - self.scroll, text=c)
```

If you change the value of `scroll` the page will now scroll up and
down. But how does the *user* change `scroll`?

::: {.further}
Storing the display list makes scrolling faster: the browser isn't 
doing `layout` every time you scroll. Modern browsers [take this
further][webrender], retaining much of the display list even when the
web page changes due to JavaScript or user interaction.
:::

[webrender]: 
https://hacks.mozilla.org/2017/10/the-whole-web-at-maximum-fps-how-webrender-gets-rid-of-jank/

Reacting to the user
====================

Most browsers scroll the page when you press the up and down keys,
rotate the scroll wheel, drag the scroll bar, or apply a touch gesture to the
screen. To keep things simple, let's just implement the down key.

Tk allows you to *bind* a function to a key, which instructs Tk to
call that function when the key is pressed. For example, to bind to
the down arrow key, write:

``` {.python}
def __init__(self):
    # ...
    self.window.bind("<Down>", self.scrolldown)
```

Here, `self.scrolldown` is an *event handler*, a function that Tk will
call whenever the down arrow key is pressed.[^event-arg] All it needs
to do is increment `y` and re-draw the canvas:

[^event-arg]: `scrolldown` is passed an *event object* as an argument
    by Tk, but since scrolling down doesn't require any information
    about the key press, besides the fact that it happened,
    `scrolldown` ignores that event object.

``` {.python}
SCROLL_STEP = 100

def scrolldown(self, e):
    self.scroll += SCROLL_STEP
    self.render()
```

If you try this out, you'll find that scrolling draws all the text a
second time. That's because we didn't erase the old text before
drawing the new text. Call `canvas.delete` to clear the old text:

``` {.python}
def render(self):
    self.canvas.delete("all")
    # ...
```

Scrolling should now work!

Faster Rendering
================

But this scrolling is pretty slow.[^slow-scroll] Why? It turns out
that loading information about the shape of a character, inside
`create_text`, takes a while. To speed up scrolling we need to make
sure to do it only when necessary (while at the same time ensuring the
pixels on the screen are always correct).

[^slow-scroll]: How fast exactly seems to depend a lot on your
    operating system and default font.

Real browsers incorporate a lot of quite tricky optimizations to this
process, but for this toy browser let's limit ourselves to a simple
improvement: on a long page most characters are outside the viewing
window, and we can skip drawing them in `render`:

``` {.python}
for x, y, c in self.display_list:
    if y > self.scroll + HEIGHT: continue
    if y + VSTEP < self.scroll: continue
    # ...
```

The first `if` statement skips characters below the viewing window;
the second skips characters above it. In that second `if` statement,
`y + VSTEP` computes the bottom edge of the character, so that
character that are halfway inside the viewing window are still drawn.

Scrolling should now be pleasantly fast, and hopefully well within the 16ms
frame budget. And because we split `layout` and `render`, we don't need to
change `layout` at all to implement this optimization.

Mobile devices
==============

Though you're probably writing your browser on a desktop computer, many people
access the web through mobile devices such as phones or tablets. On mobile
devices, there's still a screen, a rendering loop, and most other things discussed in this book.[^same-code-on-mobile] But there are several differences worth noting:

* Applications are usually full-screen, with only one
application drawing to the screen at a time. Also, "background"
applications may be killed and restarted at any time.
* There is always a touch screen, no mouse, and a virtual keyboard instead of a
physical one.
* There is a concept of a "visual viewport" not present on
desktop. [^meta-viewport]
* Screen pixel density is much higher, and the total screen resolution is lower.
* Power efficiency is much more important, because the device runs on a battery,
while at the same time the CPU and memory are significantly slower and less
capable. As a a result, it becomes more important to take advantage of GPU
hardware on these devices, as well as an even greater focus on performance than
usual.

[^same-code-on-mobile]: For example, most real browsers have both desktop and
mobile editions, and the rendering engine code is almost exactly the same for
both.

[^meta-viewport]: Look at the source of this webpage. In the `<head>` you'll see
a "viewport" `<meta>` tag. This tag gives instructions to the browser for how to
handle zooming on a mobile device. Without this tag, the browser makes
assumptions, for historical reasons, that the site is "desktop-only" and needs
some special tricks to make it readable on a mobile device, such as allowing the
user to use a pinch-zoom or double-tap touchscreen gesture to focus in on one
part of the page. Once zoomed in, the part of the page visible on the screen is
the "visual viewport" and the whole documents' bounds are the "layout viewport".

Summary
=======

This chapter went from a rudimentary command-line browser to a
graphical user interface with text that can be scrolled. The browser
now:

- Talks to your operating system to create a window
- Lays out the text and draws it to that window
- Listens for keyboard commands
- Scrolls the window in response

Next, we'll make this browser work on English text, with all its
complexities of variable width characters, line layout, and
formatting.

::: {.signup}
:::

Outline
=======

The complete set of functions, classes, and methods in our browser 
should look something like this:

::: {.cmd .python .outline html=True}
    python3 outlines.py --html src/lab2.py
:::

Exercises
=========

*Line breaks*: Change `layout` to end the current line and start a new
one when it sees a newline character. Increment *y* by more than
`VSTEP` to give the illusion of paragraph breaks. There are poems
embedded in "Journey to the West"; you'll now be able to make them
out.

*Mouse wheel*: Add support for scrolling up when you hit the up arrow.
Make sure you can't scroll past the top of the page. Then bind the
`<MouseWheel>` event, which triggers when you scroll with the mouse
wheel.[^laptop-mousewheel] The associated event object has an
`event.delta` value which tells you how far and in what direction to
scroll.

[^laptop-mousewheel]: It will also trigger with touchpad gestures,
    if you don't have a mouse.

*Emoji*: Add support for emoji 😀 to our browser. Emoji are
characters, and you can call `create_text` to draw them, but the
results aren't very good. Instead, head to [the OpenMoji
project](https://openmoji.org), download the emoji for ["grinning
face"](https://openmoji.org/library/#search=smiley%20face&emoji=1F600)
as a PNG file, convert to GIF, resize it to 16×16 pixels, and save it
to the same folder as the browser. Use Tk's `PhotoImage` class to load
the image and then `canvas.create_image` to draw it to the screen. You
can add other emojis if you'd like!

*Resizing*: Make the browser resizable. To do so, pass the `fill` and
`expand` arguments to `canvas.pack`, call and bind to the
`<Configure>` event, which happens when the window is resized. The
window's new width and height can be found in the `width` and `height`
fields on the event object. Remember that when the window is resized,
the line breaks must change, so you will need to call `layout` again.

*Zoom*: Make the `+` and `-` keys change the text size. You will need
to use the `font` argument in `create_text` to change the size of
text. Be careful in how you split the task between `layout` and
`render`. Make sure that scrolling also works when zoomed in.

[^3]: On older systems, applications drew directly to the screen, and if
    they didn't update, whatever was there last would stay in place,
    which is why in error conditions you'd often have one window leave
    "trails" on another. Modern systems use a technique called
    [compositing](https://en.wikipedia.org/wiki/Compositing_window_manager),
    in part to avoid trails (performance and application isolation are
    additional reasons). Even while using compositing, applications
    must redraw their window contents to change what is
    displayed. [Chapter 12](visual-effects.md) will discuss compositing in more detail.

[^4]: The library is called Tk, and it was originally written for a
    different language called Tcl. Python contains an interface to it,
    hence the name.

[^5]: The example event loop above may look like an infinite loop that
locks up the computer, but it's not, because of preemptive multitasking
among threads and processes and/or a variant of the event loop that
sleeps unless it has inputs that wake it up from another thread or process.

[^6]: You may be familiar with the HTML `<canvas>` element, which is a
    similar idea: a 2D rectangle in which you can draw shapes.

[^7]: This is why desktop applications are more uniform than web pages:
    desktop applications generally use the widgets provided by a common
    graphical toolkit, which limits their creative possibilities.

[^8]: This size, called Super Video Graphics Array, was standardized in
    1987, and probably did seem super back then.

[^9]: Foreshadowing future developments...

[^10]: It's to delay a discussion of basic typography to the next chapter...

[^11]: Right click on the link and "Copy URL".

[^12]: If you're not in Asia, you'll probably see this phase take a
    while: China is far away!
