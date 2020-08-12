---
title: Drawing to the Screen
chapter: 2
prev: http
next: text
...

Once a web browser has downloaded a web page, it has to show that web
page to the user. Since we're not savages,[^1] we browse the web
through a graphical user interface. How? In this chapter I'll equip my
toy browser with a graphical user interface.

[^1]: For most of 2011, I mostly used the command-line `w3m` browser. It
    built character.

Creating windows
================

Desktop and laptop computers run operating systems that provide *desktop
environments*, with windows, icons, menus, and a pointer.[^2] So in
order to draw to the screen, a program communicates with the desktop
environment:

[^2]: Terminal diehards call it a "WIMP environment" as a snide
    insult.

-   The program asks for a new window and the deskopt environment shows
    it somewhere on the screen
-   The desktop environment tells the program about clicks and key
    presses
-   The program draws things in its window
-   The desktop environment will periodically ask the program to redraw
    its window

Though the desktop environment is responsible for displaying the window,
the program is responsible for drawing its contents. Applications have
to redraw these contents sixty times per second or so for interactions
feel fluid,[^3] and must respond quickly to clicks and key presses so
the user doesn't get frustrated.

Doing all of this by hand is a bit of a drag, so programs usually use a
*graphical toolkit* to simplify these steps. These toolkits allow you to
describe your program\'s window in terms of *widgets* like buttons,
tabs, or text boxes, and take care of drawing and redrawing the window
contents to match that description.

Python comes with a graphical toolkit called Tk using the Python package
`tkinter`.[^4] Using it is quite simple:

``` {.python expected=False}
import tkinter
window = tkinter.Tk()
tkinter.mainloop()
```

Here we call `tkinter.Tk()` to create a window, and `tkinter.mainloop()`
to start the process of redrawing the screen. Internally, when we call
`tkiner.Tk()`, Tk is communicating with the desktop environment to
create the window, and returns an identifier for that window, which we
store in the `window` variable. When we call `tkinter.mainloop()`, Tk is
entering a loop that internally looks like this:

``` {.python expected=False}
while True:
    for evt in pendingEvents():
        handleEvent(evt)
    drawScreen()
```

Here, `pendingEvent` asks the desktop environment for any recent
*events*, like mouse clicks or key presses, `handleEvent` determines
what functions in our code to call in response to that event, and
`drawScreen` draws the various widgets. Applications that use the
graphical toolkit extend `drawScreen` and `handleEvent` to draw
interesting stuff on the screen and to react when the user clicks on
that stuff.

This *event loop* pattern is common in many applications, from web
browsers to video games. Our simple window above does not need much
event handling (it ignores all events) or much drawing (it is a uniform
white or gray). But in more complex graphical applications the event
loop pattern makes sure that all events are eventually handled and the
screen is eventually updated, both of which are essential to a good user
experience.

::: {.further}
Tk implements its event look in the `Tk_UpdateObjCmd` function,
found in [`tkCmds.c`][tkcmds], which calls `XSync` to redraw the
screen and `Tcl_DoOneEvent` to handle an event. There's also a lot of
code to handle errors.
:::

[tkcmds]: https://core.tcl.tk/tk/artifact/51492a6da90068a5

Drawing to the window
=====================

Our graphical browser will begin by writing the web page text to a
*canvas*, a rectangular widgets that we can draw circles, lines, and
text in.[^6] Tk also has widgets like buttons and dialog boxes, but for
writing a browser we will need the more fine-grained control over
appearance that a canvas provides.[^7]

`tkinter.Canvas` creates a canvas in Tk; we pass the window as an
argument so Tkinter knows where to display the canvas:

``` {.python expected=False}
window = tkinter.Tk()
canvas = tkinter.Canvas(window, width=800, height=600)
canvas.pack()
```

The first line creates the window, as above; the second creates the
`Canvas` inside that window. We pass `Canvas` some arguments that
define its size; I chose 800×600 because that was a common old-timey
monitor size.[^8] The third line is a Tk peculiarity, which positions
the canvas inside the window.

There's going to be a window, a canvas, and later some other things,
so let's organize these things into an object:

``` {.python}
WIDTH, HEIGHT = 800, 600

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
the canvas:

``` {.python expected=False}
def layout(self):
    self.canvas.create_rectangle(10, 20, 400, 300)
    self.canvas.create_oval(100, 100, 150, 150)
    self.canvas.create_text(200, 150, text="Hi!")
```

We can run this code from the `if __name__` block:

``` {.python expected=False}
if __name__ == "__main__":
    # ...
    browser = Browser()
    browser.layout()
    tkinter.mainloop()
```

You ought to see a rectangle, starting near the top-left corner of the
canvas and ending at its center; then a circle inside that rectangle;
and then the text "Hi!" next to the circle.

Coordinates in Tk refer to X positions from left to right and to Y
positions from top to bottom. In other words, the bottom of the screen
has *larger* Y values, the opposite of what you might be used to from
math. Play with the coordinates above to figure out what each argumetn
refers to.[^tkdocs]

[^tkdocs]: The right answers are in the [online
    documentation](http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/canvas.html).

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

Now that we\'ve got a GUI window with a canvas, let\'s draw a simple web
page on it.

Remember that in the last chapter, we implemented a simple function that
stepped through the web page source code character by character and
printed the text (but not the tags) to the console window. Now we want
to print the characters to our GUI instead.

To start, let\'s change the `show` function from the previous chapter
into a function that I\'ll call `lex`[^9] which just *returns* the
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

`Browser.layout` can take this text content and draw it to the canvas,
character by character:

``` {.python expected=False}
def layout(self, text):
    for c in text:
        canvas.create_text(100, 100, text=c)
```

Let's test this code on a real webpage. For reasons that might seem
inscrutible[^10], let\'s test it on [this first chapter of <span
lang="zh">西游记</span> or "Journey to the
West"](http://www.zggdwx.com/xiyou/1.html), a classic Chinese novel
about a monkey. Run this URL[^11] through `request`,[^12] `lex`, and
`layout`. You should see a window with a big blob of black pixels
inset a bit from the top left corner of the window.

Why a blob instead of letters? Well, of course, because we are drawing
every letter in the same place, so they all overlap! Let\'s fix that:

``` {.python expected=False}
HSTEP, VSTEP = 13, 18
x, y = HSTEP, VSTEP
for c in text:
    canvas.create_text(x, y, text=c)
    x += HSTEP
```

Now the characters form a line from left to right, and individual
characters are readable. But with an 800 pixel wide canvas and 13 pixels
per character, you can only fit about 60 characters. You need more than
that to read a novel, so we now need to *wrap* the text once we reach
the edge of the screen:[^13]

``` {.python indent=8}
for c in text:
    # ...
    if x >= WIDTH - HSTEP:
        y += VSTEP
        x = HSTEP
```

Here, when we get past pixel 787 to the right[^14] we increase *y* and
reset *x* to the left hand side again. This moves us down a line and
makes it possible to see all of the text. Also, note that I\'ve got some
magic numbers here: 13 and 18. I got these from *font metrics*, which
are introduced in the next chapter.

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

Now we can read several paragraphs of text, but there\'s still a
problem. But if there\'s enough text, all of the lines of text don\'t
fit on the screen, and there\'s still content you can\'t read. Usually
users *scroll* the page to look at different parts of it.

Scrolling introduces a layer of indirection between page coordinates
(this text is 132 pixels from the top of the *page*) and screen
coordinates (since you've scrolled 60 pixels down, this text is 72
pixels from the top of the *screen*). Generally speaking, a browser
*lays out* the page---determines where everything on the page
goes---in terms of page coordinates and then *renders* the
page---draws everything---in terms of screen coordinates.

Our browser will have the same split. Right now `layout` both computes
the position of each character and draws it: layout and rendering.
Let's have `layout` just compute the position of each character, and
saves it. A separate `render` function will draw each character to the
canvas. This way, `layout` can operate with page coordinates and only
`render` needs to think about screen coordinates.

Let's start with `layout`. Instead of calling `canvas.create_text` on
each character it adds it to a list:

``` {.python}
self.display_list = []
for c in text:
    self.display_list.append((x, y, c))
    # ...
self.render()
```

I've made `layout` store each character, and its location, to a
*display list*. It's named that because it is a list of things to
display; the term is standard. Since `layout` is all about page
coordinates, we don't need to change anything else about it.

Once the display list is computed, `render` needs to loops through
the display list and draws each tuple:

``` {.python expected=False}
def render(self):
    for x, y, c in self.display_list:
      self.canvas.create_text(x, y, text=c)
```

There's no scrolling yet, but let's add it. Let's use the `scroll`
field to store how far you've scrolled:

``` {.python}
def __init__(self):
    # ...
    self.scroll = 0
```

To scroll the page we use `y - self.scroll` in place of
`y` when we call `create_text`:

```
def render(self):
    for x, y, c in display_list:
        self.canvas.create_text(x, y - self.scroll, text=c)
```

If you change the value of `scroll` the page will now scroll up and
down. But how does the *user* change `scroll`?

::: {.further}
Storing the display list makes scrolling faster because you don't need
to redo `layout` every time you scroll. Modern browsers [take this
further][webrender], retaining much of the display list even when the
web page changes due to JavaScript or user interaction.
:::

[webrender]: 
https://hacks.mozilla.org/2017/10/the-whole-web-at-maximum-fps-how-webrender-gets-rid-of-jank/

Reacting to keyboard input
==========================

Most browsers scroll the page when you press the up and down keys,
rotate the scroll wheel, or drag the scroll bar. To keep things simple,
let\'s stick to one: the down key.

Tk allows you to *bind* a function to a key, which instructs Tk to
call that function when the key is pressed. For example, to bind to
the down arrow key, write:

``` {.python}
def __init__(self):
    # ...
    self.window.bind("<Down>", self.scrolldown)
```

Here, `self.scrolldown` is an *event handler*, a function that Tk will
call whenever the down arrow key is pressed. That function is passed a
*event object* as an argument, though scrolling down doesn't require
doing anything with that event object. It just needs to increment `y`
and re-draw the canvas:

``` {.python}
SCROLL_STEP = 100

def scrolldown(self, e):
    self.scroll += SCROLL_STEP
    self.render()
```

If you try this out, you'll find that scrolling draws all the text a
second time. That's because we didn't erase the old text when we
started drawing the new text. We need to call `canvas.delete` to clear
the old text:

``` {.python}
def render(self):
    self.canvas.delete("all")
    # ...
```

Scrolling should now work!

Faster Rendering
================

Scrolling works, but it's probably not as fast as you'd
like.[^slow-scroll] Why? It turns out drawing text on the screen takes
a while, so we need to make sure to do it only when necessary.

[^slow-scroll]: How fast exactly seems to depend a lot on your
    operating system and default font.

In reality, browsers incorporate a lot of quite tricky optimizations
to this process, but for this toy browser let's limit ourselves to a
single simple improvement: don't waste time drawing off-screen
characters. On a long page—the kind you might be scrolling—most
characters are outside the viewing window, and we can skip drawing
them in `render`:

``` {.python}
for x, y, c in self.display_list:
    if y > self.scroll + HEIGHT: continue
    if y + VSTEP < self.scroll: continue
    # ...
```

The first `if` statement skips characters below the viewing window;
the second skips characters above it. Because we split `layout` and
`render`, we don't need to change `layout` at all to implement this
optimization.

Scrolling should now be pleasantly fast.

Summary
=======

This chapter went from a rudimentary command-line browser to a
graphical user interface with text that can be scrolled. The browser
now:

- Creates a window by talking to your operating system
- Lays out the text and draws it to that window
- Listens for keyboard commands
- Scrolls the window in response

Right now our browser works well on Chinese web pages. But if you try
it on an English page, all of the characters are spaced far apart,
lines break in the middle of words, and there\'s no support for
paragraphs, links, or formatting. We\'ll fix these problems in the
next chapter.

::: {.signup}
:::

Exercises
=========

*Line breaks*: Change `layout` to handle newline characters by ending
the line and starting a new one. Increment *y* by more than 18 to give
the illusion of paragraph breaks. There are poems embedded in "Journey
to the West"; you'll now be able to make them out.

*Mouse wheel*: Add support for scrolling up when you hit the up arrow.
Make sure you can't scroll past the top of the page. Then bind the
`<MouseWheel>` event, which triggers when you scroll with the mouse
wheel.[^laptop-mousewheel] The associated event object has an
`event.delta` value which tells you how far and in what direction to
scroll.

[^laptop-mousewheel]: It also seems to trigger with touchpad gestures,
    if you don't have a mouse.

*Emoji*: Add support for emoji to our browser. Emoji are characters,
and you can call `create_text` to draw them, but the results aren't
very good. Instead, head to [the OpenMoji
project](https://openmoji.org), download the emoji for ["grinning
face"](https://openmoji.org/library/#search=smiley%20face&emoji=1F600)
as a PNG file, resize it to 16×16 pixels, and save it to the same
folder as the browser. Use `tkinter.PhotoImage` to load the image and
then `canvas.create_image` to draw it to the screen. You can add other
emojis if you'd like 😀!

*Resizing*: Make browser resizable. To do so, pass the `fill` and
`expand` arguments to `canvas.pack` call and bind to the `<Configure>`
event to run code when the window is resized. You can get the new
window width and height with the `width` and `height` fields on the
event object. Remember that when the window is resized, the line
breaks will change, so you will need to call `layout` again.

*Zoom*: Make the `+` and `-` keys change the text size. You will need
to use the `font` argument in `create_text` to change the size of
text. Be careful in how you split the task between `layout` and
`render`. Make sure that scrolling also works when zoomed in.

[^3]: On older systems, applications drew directly to the screen, and if
    they didn\'t update, whatever was there last would stay in place,
    which is why in error conditions you\'d often have one window leave
    "trails" on another. Modern systems use a technique called
    [compositing](https://en.wikipedia.org/wiki/Compositing_window_manager)
    to avoid trails (at the cost of using more memory), but applications
    must still redraw their window contents to change what is displayed.

[^4]: The library is called Tk, and it was originally written for a
    different language called Tcl. Python contains an interface to it,
    hence the name.

[^6]: You may be familiar with the HTML `<canvas>` element, which is a
    similar idea: a 2D rectangle in which you can draw shapes.

[^7]: This is why desktop applications are more uniform than web pages:
    desktop applications generally use the widgets provided by a common
    graphical toolkit, which limits their creative possibilities.

[^8]: This size, called Super Video Graphics Array, was standardized in
    1987, and probably did seem super back then.

[^9]: Foreshadowing future developments...

[^10]: It\'s to delay a discussion of basic typography to next class...

[^11]: Right click on the link and \"Copy URL\".

[^12]: If you\'re in the US, you\'ll probably see this phase take a
    while: China is far away!

[^13]: In the olden days of type writers, going to a new line would be
    two operations: to move down the page you would *feed* in a new
    *line*, and then you\'d *return* the *carriage* that printed letters
    to the left margin. You can see the same two operations below. When
    ASCII was standardized, they added separate characters for these
    operations: CR and LF. That\'s why headers in HTTP are separated by
    `\r\n`, or CR followed by LF, even though computers have nothing
    mechanical inside that necessitates separate operations. In most
    contexts, however, you generally just use `\n` create a new line.

[^14]: Not 800, because we started at pixel 13 and I want to leave an
    even gap on both sides.
