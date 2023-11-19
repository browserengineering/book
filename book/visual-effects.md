---
title: Adding Visual Effects
chapter: 11
prev: security
next: scheduling
...

Right now our browser can only draw colored rectangles and
text---pretty boring! Real browsers support all kinds of *visual
effects*\index{visual effect} that change how pixels and colors blend
together. To implement those effects, and also make our browser
faster, we'll need control over *surfaces*\index{surface}, the key
low-level feature behind fast scrolling, visual effects, animations,
and many other browser features. To get that control, we'll also
switch to using the Skia graphics library and even take a peek under
its hood.

Installing Skia and SDL
=======================

While Tkinter is great for basic shapes and input handling, it doesn't
give us control over surfaces[^tkinter-before-gpu] and lacks
implementations of most visual effects.
Implementing them ourselves would be fun, but
it's outside the scope of this book, so we need a new graphics library.
Let's use [Skia][skia],\index{Skia} the library that Chromium uses.
Unlike Tkinter, Skia doesn't handle inputs or create graphical windows,
so we'll pair it with the [SDL][sdl] GUI library.\index{SDL} Beyond
new capabilities, switching to Skia will allow us to control graphics
and rasterization at a lower level.

[skia]: https://skia.org
[sdl]: https://www.libsdl.org/

[^tkinter-before-gpu]: That's because Tk, the graphics library that
Tkinter uses, dates from the early 90s, before high-performance
graphics cards and GPUs became widespread.

Start by installing [Skia][skia-python] and [SDL][sdl-python]:

    python3 -m pip install skia-python pysdl2 pysdl2-dll

[skia-python]: https://kyamagu.github.io/skia-python/
[sdl-python]: https://pypi.org/project/PySDL2/

::: {.install}
As elsewhere in this book, you may need to install the `pip` package
first, or use your IDE's package installer. If you're on Linux, you'll
need to install additional dependencies, like OpenGL and fontconfig.
Also, you may not be able to install `pysdl2-dll`; if so, you'll need
to find SDL in your system package manager instead. Consult the
[`skia-python`][skia-python] and [`pysdl2`][sdl-python] web pages for
more details.
:::

Once installed, remove the `tkinter` imports from browser and replace
them with these:

``` {.python}
import ctypes
import sdl2
import skia
```

The `ctypes` module is a standard part of Python; we'll use it to
convert between Python and C types. If any of these imports fail,
check that Skia and SDL were installed correctly.

::: {.further}
The [`<canvas>`][canvas]\index{canvas} HTML element provides a JavaScript
API that is similar to Skia and Tkinter. Combined with [WebGL][webgl],
it's possible to implement basically all of SDL and Skia in
JavaScript. Alternatively, one can [compile Skia][canvaskit]
to [WebAssembly][webassembly] to do the same.
:::

SDL creates the window
======================

The first big task is to switch to using SDL to create the window and
handle events.
The main loop of the browser first needs some boilerplate to get SDL
started:

``` {.python}
if __name__ == "__main__":
    sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS)
    browser = Browser()
    browser.new_tab(URL(sys.argv[1]))
    # ...
```

Next, we need to create an SDL window, instead of a Tkinter window,
inside the Browser. Here's the SDL incantation:

``` {.python}
class Browser:
    def __init__(self):
        self.sdl_window = sdl2.SDL_CreateWindow(b"Browser",
            sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
            WIDTH, HEIGHT, sdl2.SDL_WINDOW_SHOWN)
```

When we create this SDL window, we're asking SDL to allocate a
*surface*, a chunk of memory representing the pixels on the
screen.[^surface] On today's large screens, surfaces take up a lot of
memory and drawing to them can take a lot of time, so managing
surfaces is going to be a big focus of this chapter.

[^surface]: In Skia and SDL, a *surface* is a representation of a
graphics buffer into which you can draw *pixels* (bits representing
colors). A surface may or may not be bound to the physical pixels on the
screen via a window, and there can be many surfaces. A *canvas* is an
API interface that allows you to draw into a surface with higher-level
commands such as for rectangles or text. Our browser uses separate
Skia and SDL surfaces for simplicity, but in a highly optimized
browser, minimizing the number of surfaces is important for good
performance.

Let's also create a surface for Skia to draw to:

``` {.python}
class Browser:
    def __init__(self):
        self.root_surface = skia.Surface.MakeRaster(
            skia.ImageInfo.Make(
                WIDTH, HEIGHT,
                ct=skia.kRGBA_8888_ColorType,
                at=skia.kUnpremul_AlphaType))
```

Note the `ct` argument, meaning "color type", which indicates that
each pixel of this surface should be represented as *r*ed, *g*reen,
*b*lue, and *a*lpha values, each of which should take up 8 bits. In
other words, pixels are basically defined like so:

``` {.python file=examples}
class Pixel:
    def __init__(self, r, g, b, a):
        self.r = r
        self.g = g
        self.b = b
        self.a = a
```

Note that this `Pixel` code is an illustrative example, not something
our browser has to define. It's standing in for somewhat more complex
code within Skia itself.

Now there's an SDL surface for the window contents and a Skia surface
that we can draw to. We'll raster\index{raster} to the Skia surface,
and then once we're done we'll copy it to the SDL surface to
display on the screen.

This is a little hairy, because we are moving data between two
low-level libraries, but really it's just copying pixels from one
place to another. First, get the sequence of bytes representing the
Skia surface:

``` {.python}
class Browser:
    def draw(self):
        # ...

        # This makes an image interface to the Skia surface, but
        # doesn't actually copy anything yet.
        skia_image = self.root_surface.makeImageSnapshot()
        skia_bytes = skia_image.tobytes()
```

Next, we need to copy the data to an SDL surface. This requires
telling SDL what order the pixels are stored in and on your computer's
[endianness][wiki-endianness]:

[wiki-endianness]: https://en.wikipedia.org/wiki/Endianness

``` {.python}
class Browser:
    def __init__(self):
        if sdl2.SDL_BYTEORDER == sdl2.SDL_BIG_ENDIAN:
            self.RED_MASK = 0xff000000
            self.GREEN_MASK = 0x00ff0000
            self.BLUE_MASK = 0x0000ff00
            self.ALPHA_MASK = 0x000000ff
        else:
            self.RED_MASK = 0x000000ff
            self.GREEN_MASK = 0x0000ff00
            self.BLUE_MASK = 0x00ff0000
            self.ALPHA_MASK = 0xff000000
```

The `CreateRGBSurfaceFrom` method then wraps the data in an SDL surface
(without copying the bytes):[^use-after-free]

[^use-after-free]: Note that since Skia and SDL are C++ libraries, they are not
always consistent with Python's garbage collection system. So the link between
the output of `tobytes` and `sdl_window` is not guaranteed to be kept
consistent when `skia_bytes` is garbage collected. Instead, the SDL surface
will be pointing at a bogus piece of memory, which will lead to memory
corruption or a crash. The code here is correct because all of these are local
variables that are garbage-collected together, but if not you need to be
careful to keep all of them alive at the same time.

``` {.python}
class Browser:
    def draw(self):
        # ...
        depth = 32 # Bits per pixel
        pitch = 4 * WIDTH # Bytes per row
        sdl_surface = sdl2.SDL_CreateRGBSurfaceFrom(
            skia_bytes, WIDTH, HEIGHT, depth, pitch,
            self.RED_MASK, self.GREEN_MASK,
            self.BLUE_MASK, self.ALPHA_MASK)
```

Finally, we draw all this pixel data on the window itself by blitting (copying)
it from `sdl_surface` to `sdl_window`'s surface:

``` {.python}
class Browser:
    def draw(self):
        # ...
        rect = sdl2.SDL_Rect(0, 0, WIDTH, HEIGHT)
        window_surface = sdl2.SDL_GetWindowSurface(self.sdl_window)
        # SDL_BlitSurface is what actually does the copy.
        sdl2.SDL_BlitSurface(sdl_surface, rect, window_surface, rect)
        sdl2.SDL_UpdateWindowSurface(self.sdl_window)
```

So that's that: we're now creating a window and copying pixels to it.
But if you run your browser now, you'll find that it exits
immediately.

That's because SDL doesn't have a `mainloop` or `bind` method; we have
to implement it ourselves:

``` {.python}
def mainloop(browser):
    event = sdl2.SDL_Event()
    while True:
        while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == sdl2.SDL_QUIT:
                browser.handle_quit()
                sdl2.SDL_Quit()
                sys.exit()
            # ...
```

The details of `ctypes` and `PollEvent` aren't too important here, but
note that `SDL_QUIT` is an event, sent when the user closes the last
open window. The `handle_quit` method it calls just cleans up the
window object:

``` {.python}
class Browser:
    def handle_quit(self):
        sdl2.SDL_DestroyWindow(self.sdl_window)
```

Call `mainloop` in place of `tkinter.mainloop`:

``` {.python}
if __name__ == "__main__":
    # ...
    mainloop(browser)
```

In place of all the `bind` calls in the `Browser` constructor, we can
just directly call methods for various types of events, like clicks,
typing, and so on. The SDL syntax looks like this:

``` {.python}
def mainloop(browser):
    while True:
        while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            # ...
            elif event.type == sdl2.SDL_MOUSEBUTTONUP:
                browser.handle_click(event.button)
            elif event.type == sdl2.SDL_KEYDOWN:
                if event.key.keysym.sym == sdl2.SDLK_RETURN:
                    browser.handle_enter()
                elif event.key.keysym.sym == sdl2.SDLK_DOWN:
                    browser.handle_down()
            elif event.type == sdl2.SDL_TEXTINPUT:
                browser.handle_key(event.text.text.decode('utf8'))
```

I've changed the signatures of the various event handler methods. For
example, the `handle_click` method is now passed a `MouseButtonEvent`
object, which thankfully contains `x` and `y` coordinates, while the
`handle_enter` and `handle_down` methods aren't passed any argument at
all, because we don't use that argument anyway. You'll need to change
the `Browser` methods' signatures to match.

::: {.further}
SDL is most popular for making games. Their site lists [a selection of
books](https://wiki.libsdl.org/Books) about game programming in SDL.
:::

Rasterizing with Skia
=====================

\index{canvas}Now our browser has an SDL surface, a Skia surface, and
can copy between them. Now we want to draw text, rectangles, and so on
to that Skia surface. This step---coloring in the pixels of a surface
to draw shapes on it---is called "rasterization"\index{raster} and is
one important task of a graphics library.

We'll need our browser's drawing commands to invoke Skia, not Tk
methods. Skia is a bit more verbose than Tkinter, so let's abstract
over some details with helper functions.[^skia-docs] First, let's talk
about parsing colors.

[^skia-docs]: Consult the [Skia][skia] and [skia-python][skia-python]
documentation for more on the Skia API.

Skia represents colors as simple 32-bit integers, with the most
significant byte representing the alpha value (255 meaning opaque and
0 meaning transparent) and then the next three bytes representing the
red, green, and blue color channels. Parsing a CSS color like
`#ffd700` to this representation is pretty easy:

``` {.python}
def parse_color(color):
    if color.startswith("#") and len(color) == 7:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        return skia.Color(r, g, b)
```

Skia's `Color` constructor packs the red, green, and blue values into
its integer representation for us. (Alpha is implicitly 255, meaning
opaque, in this case.)

However, there are also a whole lot of named colors. Supporting this
is necessary to see many of the examples in this book:

``` {.python}
NAMED_COLORS = {
    "black": "#000000",
    "white": "#ffffff",
    "red":   "#ff0000",
    # ...
}

def parse_color(color):
    # ...
    elif color in NAMED_COLORS:
        return parse_color(NAMED_COLORS[color])
    else:
        return skia.ColorBLACK
```

You can add more named colors from [the list][named-colors] as you
come across them; the demos in this book use `blue`, `green`,
`lightblue`, `lightgreen`, `orange`, `orangered`, and `gray`. Note
that unsupported colors are interpreted as black, so that at least
something is drawn to the screen.[^not-standard]

[^not-standard]: This is not the standards-required behavior---the
    invalid value should just not participate in styling, so an
    element styled with an unknown color might inherit a color other
    than black---but I'm doing it as a convenience.

[named-colors]: https://developer.mozilla.org/en-US/docs/Web/CSS/named-color


Note that the `Color` constructor takes alpha, red, green, and blue
values, closely matching (except for the order) our `Pixel` definition.

You can add "elif" blocks to support any other color names you use;
modern browsers support [quite a lot][css-colors]. If you'd like to
use a color Skia doesn't pre-define, you can use the `skia.Color`
constructor, which takes red, green, and blue parameters from 0 to
255.

[css-colors]: https://developer.mozilla.org/en-US/docs/Web/CSS/color_value

To draw a line, you use Skia's `Path` object:

``` {.python replace=%2c%20scroll/,%20-%20scroll/}
class DrawLine:
    def execute(self, canvas, scroll):
        path = skia.Path().moveTo(self.x1 - scroll, self.y1) \
                          .lineTo(self.x2 - scroll, self.y2)
        paint = skia.Paint(Color=parse_color(self.color))
        paint.setStyle(skia.Paint.kStroke_Style)
        paint.setStrokeWidth(self.thickness)
        canvas.drawPath(path, paint)
```

Note the steps involved here. We first create a `Path` object, and
then call `drawPath` to actually draw this path to the canvas. This
`drawPath` call takes a second argument, `paint`, which defines how to
actually perform this drawing. We specify the color, but we also need
to specify that we want to draw a line *along* the path, instead of
filling in the interior of the path, which is the default. To do that
we set the style to "stroke", a standard term referring to drawing
along the border of some shape.[^opposite-fill]

[^opposite-fill]: The opposite is "fill", meaning filling in the
    interior of the shape.

We do something similar to draw text using `drawString`:

``` {.python replace=%2c%20scroll/,%20-%20scroll/}
class DrawText:
    def execute(self, canvas, scroll):
        paint = skia.Paint(
            AntiAlias=True, Color=parse_color(self.color))
        baseline = self.top - scroll - self.font.getMetrics().fAscent
        canvas.drawString(self.text, float(self.left), baseline,
            self.font, paint)
```

Note again that we create a `Paint` object identifying the color, the
fact that we want anti-aliased text.[^anti-alias] We don't specify the
"style" because we want to fill the interior of the text, the default.

[^anti-alias]: "Anti-alias"ing just means drawing some
    semi-transparent pixels to better approximate the shape of the
    text. This is important when drawing shapes with fine details,
    like text, but is less important when drawing large shapes like
    rectangles and lines.

Finally, for drawing rectangles you use `drawRect`:

``` {.python replace=%2c%20scroll/,rect.makeOffset(0%2c%20-scroll)/rect}
class DrawRect:
    def execute(self, canvas, scroll):
        paint = skia.Paint()
        paint.setColor(parse_color(self.color))
        canvas.drawRect(self.rect.makeOffset(0, -scroll), paint)
```

Here the `rect` field needs to become a Skia `Rect` object, which you can
construct using `MakeLTRB` (for "make left-top-right-bottom") or `MakeXYWH`
(for "make *x*-*y*-width-height"). Get rid of the old `Rect` class that was
introduced in [Chapter 7](chrome.md) in favor of `skia.Rect`. Everywhere
that a `Rect` was constructed, instead put `skia.Rect.MakeLTRB`, and
everywhere that the sides of the rectangle (e.g. `left`) where checked,
replace them with the corresponding function on a Skia `Rect` (e.g. `left()`).
Also replace calls to `containsPoint` with Skia's `contains`.

While we're here, let's also add a `rect` field to the other drawing
commands, replacing its `top`, `left`, `bottom`, and `right`
fields:

``` {.python}
class DrawText:
    def __init__(self, x1, y1, text, font, color):
        # ...
        self.rect = \
            skia.Rect.MakeLTRB(x1, y1, self.right, self.bottom)

class DrawLine:
    def __init__(self, x1, y1, x2, y2, color, thickness):
        # ...
        self.rect = skia.Rect.MakeLTRB(x1, y1, x2, y2)
```

To draw just the outline, set the `Style` parameter of the `Paint` to
`Stroke_Style`:

``` {.python replace=%2c%20scroll/,rect.makeOffset(0%2c%20-scroll)/rect}
class DrawOutline:
    def execute(self, scroll, canvas):
        paint = skia.Paint()
        paint.setStyle(skia.Paint.kStroke_Style)
        paint.setStrokeWidth(self.thickness)
        paint.setColor(parse_color(self.color))
        canvas.drawRect(self.rect.makeOffset(0, -scroll), paint)
```

Since we're replacing Tkinter with Skia, we are also replacing
`tkinter.font`. In Skia, a font object has two pieces: a `Typeface`,
which is a type family with a certain weight, style, and width; and a
`Font`, which is a `Typeface` at a particular size. It's the
`Typeface` that contains data and caches, so that's what we need to
cache:

``` {.python}
def get_font(size, weight, style):
    key = (weight, style)
    if key not in FONTS:
        if weight == "bold":
            skia_weight = skia.FontStyle.kBold_Weight
        else:
            skia_weight = skia.FontStyle.kNormal_Weight
        if style == "italic":
            skia_style = skia.FontStyle.kItalic_Slant
        else:
            skia_style = skia.FontStyle.kUpright_Slant
        skia_width = skia.FontStyle.kNormal_Width
        style_info = \
            skia.FontStyle(skia_weight, skia_width, skia_style)
        font = skia.Typeface('Arial', style_info)
        FONTS[key] = font
    return skia.Font(FONTS[key], size)
```

Our browser also needs font metrics and measurements. In Skia, these
are provided by the `measureText` and `getMetrics` methods. Let's
start with `measureText` replacing all calls to `measure`. For
example, in the `paint` method in `InputLayout`, we must do:

``` {.python}
class InputLayout:
    def paint(self):
        if self.node.is_focused:
            cx = self.x + self.font.measureText(text)
            # ...
```

There are `measure` calls in several other layout objects (both in
`paint` and `layout`), in `DrawText`, in the `draw` method on
`Chrome`, in the `text` method in `BlockLayout`, and in the `layout`
method in `TextLayout`. Update all of them to use `measureText`.

Also, in the `layout` method of `LineLayout` and in `DrawText` we make
calls to the `metrics` method on fonts. In Skia, this method is called
`getMetrics`, and to get the ascent and descent we use

``` {.python expected=False}
    -font.getMetrics().fAscent
```

and

``` {.python expected=False}
    font.getMetrics().fDescent
```

Note the negative sign when accessing the ascent. In Skia, ascent and
descent are positive if they go downward and negative if they go
upward, so ascents will normally be negative, the opposite of Tkinter.
There's no analog for the `linespace` field that Tkinter provides,
but you can use descent minus ascent instead:

``` {.python}
def linespace(font):
    metrics = font.getMetrics()
    return metrics.fDescent - metrics.fAscent

```

You should now be able to run the browser again. It should look and behave just
as it did in previous chapters, and it might feel faster on complex pages,
because Skia and SDL are in general faster than Tkinter. This is one advantage
of Skia: since it is also used by the Chromium browser, we know it has fast,
built-in support for all of the shapes we might need. And if the transition
felt easy---well, that's one of the benefits to abstracting over the drawing
backend using a display list!\index{display list}

::: {.further}
[Font rasterization](https://en.wikipedia.org/wiki/Font_rasterization)
is surprisingly deep, with techniques such as
[subpixel rendering](https://en.wikipedia.org/wiki/Subpixel_rendering)
and [hinting][font-hinting] used to make fonts look better on
lower-resolution screens. These techniques are much less necessary on
[high-pixel-density](https://en.wikipedia.org/wiki/Pixel_density)
screens, though. It's likely that eventually, all screens will be
high-density enough to retire these techniques.
:::

[font-hinting]: https://en.wikipedia.org/wiki/Font_hinting

Browser compositing
===================

Skia and SDL have just made our browser more complex, but the
low-level control offered by these libraries is important because it
allows us to optimize commonly-used operations like scrolling.

So far, any time the user scrolled a web page, we had to clear
the canvas and re-raster everything on it from scratch. This is
inefficient---we're drawing the same pixels, just in a different
place. When the context is complex or the screen is large,
rastering too often produces a visible slowdown and drains laptop and mobile
batteries. Real browsers optimize scrolling
using a technique I'll call *browser compositing*:
drawing the whole web page to a hidden surface, and only copying the
relevant pixels to the window itself.

To implement this, we'll need two new Skia surfaces:
a surface for browser chrome and a surface
for the current `Tab`'s contents. We'll only need to
re-raster the `Tab` surface if page contents change, but not when
(say) the user types into the address bar. And we can scroll the `Tab`
without any raster at all---we just copy a different part of the
current `Tab` surface to the screen. Let's call those surfaces
`chrome_surface` and `tab_surface`:[^multiple-tabs]

[^multiple-tabs]: We could even use a different surface for each `Tab`,
but real browsers don't do this, since each surface uses up a lot of
memory, and typically users don't notice the small raster delay when
switching tabs.

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.chrome_surface = skia.Surface(
            WIDTH, math.ceil(self.chrome.bottom))
        self.tab_surface = None
```

I'm not explicitly creating `tab_surface` right away, because we need
to lay out the page contents to know how tall the surface needs to be.

We'll also need to split the browser's `draw` method into three parts:

- `draw` will composite the chrome and tab surfaces and copy the
  result from Skia to SDL;[^why-two-steps]
- `raster_tab` will raster the page to the `tab_surface`; and
- `raster_chrome` will raster the browser chrome to the `chrome_surface`.

[^why-two-steps]: It might seem wasteful to copy from the chrome and
    tab surface to an intermediate Skia surface, instead of directly
    to the SDL surface. It is, but skipping that copy requires a lot
    of tricky low-level code. In [Chapter 13](animations.md) we'll
    avoid this copy in a different, better way.

Let's start by doing the split:

``` {.python}
class Browser:
    def raster_tab(self):
        canvas = self.tab_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        # ...

    def raster_chrome(self):
        canvas = self.chrome_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        # ...

    def draw(self):
        canvas = self.root_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        # ...
```

Since we didn't create the `tab_surface` on startup, we need to create
it at the top of `raster_tab`:[^really-big-surface]

[^really-big-surface]: For a very big web page, the `tab_surface` can
be much larger than the size of the SDL window, and therefore take up
a very large amount of memory. We'll ignore that, but a real browser
would only paint and raster surface content up to a certain distance
from the visible region, and re-paint/raster as the user scrolls.

``` {.python}
import math

class Browser:
    def raster_tab(self):
        tab_height = math.ceil(
            self.active_tab.document.height + 2*VSTEP)

        if not self.tab_surface or \
                tab_height != self.tab_surface.height():
            self.tab_surface = skia.Surface(WIDTH, tab_height)

        # ...
```

The way we compute the page bounds here, based on the layout tree's
height, would be incorrect if page elements could stick out below (or
to the right) of their parents---but our browser doesn't support any
features like that. Note that we need to recreate the tab surface if
the page's height changes.

Next, `draw` should copy from the chrome and tab surfaces to the root
surface. Moreover, we need to translate the `tab_surface` down by
`chrome_bottom` and up by `scroll`, and clips it to only the area of
the window that doesn't overlap the browser chrome:

``` {.python}
class Browser:
    def draw(self):
        # ...
        
        tab_rect = skia.Rect.MakeLTRB(
            0, self.chrome.bottom, WIDTH, HEIGHT)
        tab_offset = self.chrome.bottom - self.active_tab.scroll
        canvas.save()
        canvas.clipRect(tab_rect)
        canvas.translate(0, tab_offset)
        self.tab_surface.draw(canvas, 0, 0)
        canvas.restore()

        chrome_rect = skia.Rect.MakeLTRB(
            0, 0, WIDTH, self.chrome.bottom)
        canvas.save()
        canvas.clipRect(chrome_rect)
        self.chrome_surface.draw(canvas, 0, 0)
        canvas.restore()

        # ...
```

Note the `draw` calls: these copy the `tab_surface` and
`chrome_surface` to the `canvas`, which is bound to `root_surface`.
The `clipRect` and `translate` make sure we copy the right parts.

Finally, everywhere in `Browser` that we call `draw`, we now need to
call either `raster_tab` or `raster_chrome` first. For example, in
`handle_click`, we do this:

``` {.python}
class Browser:
    def handle_click(self, e):
        if e.y < self.chrome.bottom:
            # ...
            self.raster_chrome()
        else:
            # ...
            self.raster_tab()
        self.draw()
```

Notice how we don't redraw the chrome when only the tab changes, and
vice versa. Likewise, in `handle_down`, we don't need to call
`raster_tab` at all, since scrolling doesn't change the page.

However, clicking on a web page can cause it to navigate to a new one,
so we do need to detect that and raster the browser chrome if the URL
changed:

``` {.python}
class Browser:
    def handle_click(self, e):
        if e.y < self.chrome.bottom:
            # ...
        else:
            # ...
            url = self.active_tab.url
            tab_y = e.y - self.chrome.bottom
            self.active_tab.click(e.x, tab_y)
            if self.active_tab.url != url:
                self.raster_chrome()
            self.raster_tab()
```

We also have some related changes in `Tab`. First, we no longer need
to pass around the scroll offset to the `execute` methods, or account
for `chrome_bottom`, because we always draw the whole tab to the tab
surface:

``` {.python}
class Tab:
    def raster(self, canvas):
        for cmd in self.display_list:
            cmd.execute(canvas)
```

Likewise, we can remove the `scroll` parameter from each drawing
command's `execute` method:

``` {.python}
class DrawRect:
    def execute(self, canvas):
        paint = skia.Paint()
        paint.setColor(parse_color(self.color))
        canvas.drawRect(self.rect, paint)
```

Our browser now uses composited scrolling, making scrolling faster and
smoother, all because we are now using a mix of intermediate surfaces
to store already-rastered content and avoid re-rastering unless the
content has actually changed.

::: {.further}
Real browsers allocate new surfaces for various different situations,
such as implementing accelerated overflow scrolling and animations of
certain CSS properties such as [transform][transform-link] and opacity
that can be done without raster. They also allow scrolling arbitrary
HTML elements via [`overflow: scroll`][overflow-prop] in CSS. Basic
scrolling for DOM elements is very similar to what we've just
implemented. But implementing it in its full generality, and with
excellent performance, is *extremely* challenging. Scrolling may well
be the single most complicated feature in a browser rendering engine.
The corner cases and subtleties involved are almost endless.
:::

[transform-link]: https://developer.mozilla.org/en-US/docs/Web/CSS/transform
[overflow-prop]: https://developer.mozilla.org/en-US/docs/Web/CSS/overflow

What Skia gives us
==================

Skia not only gives us low-level control but also new features. For
example, let's implement rounded corners via the `border-radius` CSS property:

    <div style="border-radius: 10px; background: lightblue">
        This is some example text.
    </div>

Which looks like this:[^not-clipped]

[^not-clipped]: If you're very observant, you may notice that the text
    here protrudes past the background by just a handful of pixels.
    This is the correct default behavior, and can be modified by the
    `overflow` CSS property, which we'll see later this chapter.

<div style="border-radius:10px;background:lightblue">
This is some example text.
</div>

Implementing `border-radius` requires drawing a rounded rectangle, so
let's add a new `DrawRRect` command:

``` {.python replace=scroll%2c%20/}
class DrawRRect:
    def __init__(self, rect, radius, color):
        self.rect = rect
        self.rrect = skia.RRect.MakeRectXY(rect, radius, radius)
        self.color = color

    def execute(self, scroll, canvas):
        sk_color = parse_color(self.color)
        canvas.drawRRect(self.rrect,
            paint=skia.Paint(Color=sk_color))
```

Note that Skia supports `RRect`s, or rounded rectangles, natively, so
we can just draw one right to a canvas. Now we can draw these rounded
rectangles for the background:

``` {.python replace=is_atomic/self.is_atomic()}
class BlockLayout:
    def paint(self):
        if bgcolor != "transparent":
            radius = float(
                self.node.style.get(
                    "border-radius", "0px")[:-2])
            cmds.append(DrawRRect(
                self.self_rect(), radius, bgcolor))
```

Similar changes should be made to `InputLayout`. So that's one thing
Skia gives us: new rasterization features, meaning new shapes we can
draw.

Another feature natively supported by Skia is transparency. In CSS,
you can use a hex color with eight hex digits to indicate that
something should be drawn semi-transparently. For example, the
color `#00000080` is 50% transparent black. Over a white background,
that looks gray, but over an orange background it looks like this:

<div style="background-color: #ffa500; color: #00000080">Test</div>

Note that the text is a kind of dark orange. Skia supports these
"RGBA" colors by setting the "alpha" field in the color:

``` {.python}
def parse_color(color):
    elif color.startswith("#") and len(color) == 9:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        a = int(color[7:9], 16)
        return skia.Color(r, g, b, a)
```

Check that your browser can render the example above with slightly
orange-tinged text. This demonstrates that the text is semitransparent
and is letting some background color through.

::: {.further}
Implementing high-quality raster libraries is very interesting in its own
right---check out [Real-Time Rendering][rtr-book] for more.[^cgpp]
These days, it's especially important to leverage GPUs when they're
available, and browsers often push the envelope. Browser teams
typically include or work closely with raster library experts: Skia
for Chromium and [Core Graphics][core-graphics] for WebKit, for
example. Both of these libraries are used outside of the browser, too:
Core Graphics in iOS and macOS, and Skia in Android.
:::

[^cgpp]: There is also [Computer Graphics: Principles and
Practice][classic], which incidentally I remember buying---this is
Chris speaking---back in the days of my youth (1992 or so). At the time I
didn't get much further than rastering lines and polygons (in assembly
language!). These days you can do the same and more with Skia and a
few lines of Python.

[core-graphics]: https://developer.apple.com/documentation/coregraphics
[rtr-book]: https://www.realtimerendering.com/
[classic]: https://en.wikipedia.org/wiki/Computer_Graphics:_Principles_and_Practice

Pixels, color, and raster
=========================

Skia, like the Tkinter canvas we've been using until now, is a
_rasterization_\index{raster} library: it converts shapes like rectangles and
text into pixels. Before we move on to Skia's advanced features, let's talk
about how rasterization works at a deeper level. This will help to understand
how exactly those features work.

You probably already know that computer screens are a 2D array of
pixels. Each pixel contains red, green and blue lights,[^lcd-design]
or _color channels_, that can shine with an intensity between 0 (off)
and 1 (fully on). By mixing red, green, and blue, which is formally
known as the [sRGB color space][srgb], any color in that space's
_gamut_ can be made.[^other-spaces] In a rasterization library, a 2D
array of pixels like this is called a *surface*.[^or-texture] Since
modern devices have lots of pixels, surfaces require a lot of memory,
and we'll typically want to create as few as possible.

[^or-texture]: Sometimes they are called *bitmaps* or *textures* as
well, but these words connote specific CPU or GPU technologies for
implementing surfaces.

[^lcd-design]: Actually, some screens contain [pixels besides red,
    green, and blue][lcd-design], including white, cyan, or yellow.
    Moreover, different screens can use slightly different reds,
    greens, or blues; professional color designers typically have to
    [calibrate their screen][calibrate] to display colors accurately.
    For the rest of us, the software still communicates with the
    display in terms of standard red, green, and blue colors, and the
    display hardware converts to whatever pixels it uses.
    
[lcd-design]: https://geometrian.com/programming/reference/subpixelzoo/index.php
[calibrate]: https://en.wikipedia.org/wiki/Color_calibration
[srgb]: https://en.wikipedia.org/wiki/SRGB
[CRT]: https://en.wikipedia.org/wiki/Cathode-ray_tube
[color-spec]: https://drafts.csswg.org/css-color-4/

[^other-spaces]: The sRGB color space dates back to [CRT
displays][CRT]. New technologies like LCD, LED, and OLED can display
more colors, so CSS now includes [syntax][color-spec] for expressing
these new colors. All color spaces have a limited gamut of expressible
colors.

The job of a rasterization library is to determine the red, green, and
blue intensity of each pixel on the screen, based on the
shapes---lines, rectangles, text---that the application wants to
display. The interface for drawing shapes onto a surface is called a
*canvas*; both Tkinter and Skia had canvas APIs. In Skia, each surface
has an associated canvas that draws to that surface.

::: {.further}
Screens use red, green, and blue color channels to match the three
types of [cone cells][cones] in a human eye. We take it for granted,
but color standards like [CIELAB][cielab] derive from attempts to
[reverse-engineer human vision][opponent-process]. These cone cells
vary between people: some have [more][tetrachromats] or
[fewer][colorblind] (typically an inherited condition carried on the X
chromosome). Moreover, different people have different ratios of cone
types and those cone types use different protein structures that vary
in the exact frequency of green, red, and blue that they respond to.
The study of color thus combines software, hardware, chemistry,
biology, and psychology.
:::

[cones]: https://en.wikipedia.org/wiki/Cone_cell
[cielab]: https://en.wikipedia.org/wiki/CIELAB_color_space
[opponent-process]: https://en.wikipedia.org/wiki/Opponent_process
[colorblind]: https://en.wikipedia.org/wiki/Color_blindness
[tetrachromats]: https://en.wikipedia.org/wiki/Tetrachromacy#Humans

Blending and stacking
=====================

Drawing shapes quickly is already a challenge, but with multiple
shapes there's an additional question: what color should the pixel be
when two shapes overlap? So far, our browser has only handled opaque
shapes,[^nor-subpixel] and the answer has been simple: take the color
of the top shape. But now we need more nuance.

[^nor-subpixel]: It also hasn't considered subpixel geometry or
    anti-aliasing, which also rely on color mixing.

Many objects in nature are partially transparent: frosted glass,
clouds, or colored paper, for example. Looking through one, you see
multiple colors *blended* together. That's also why computer screens work:
the red, green, and blue lights [blend together][mixing] and appear to
our eyes as another color. Designers use this effect[^mostly-models]
in overlays, shadows, and tooltips, so our browser needs to support
color mixing.

[mixing]: https://en.wikipedia.org/wiki/Color_mixing

[^mostly-models]: Mostly. Some more advanced blending modes on the web are
difficult, or perhaps impossible, in real-world physics.

Color mixing means we need to think carefully about the order of
operations. For example, consider black text on an orange background,
placed semi-transparently over a white background. The text
is gray while the background is yellow-orange. That's due to blending:
the text and the background are both partially transparent and let
through some of the underlying white:

<div style="opacity: 0.5; background: orange; color: black; font-size: 50px;
    padding: 15px; text-align: center;flex:1;">Text</div>

But importantly, the text isn't orange-gray: even though the text is
partially transparent, none of the orange shines through. That's
because the order matters: the text is *first* blended with the
background; since the text is opaque, its blended pixels are black and
overwrite the orange background. Only *then* is this black-and-orange
image blended with the white background. Doing the operations in a
different order would lead to dark-orange or black text.

To handle this properly, browsers apply blending not to individual shapes but to
a tree of surfaces. Conceptually, each surface is drawn individually,
and then blended into its parent surface. Rastering a web page requires a
bottom-up traversal of the tree: to raster a surface you first need to raster
its contents, including its child stacking contexts, and then the whole
contents need to be blended together into the parent.[^stacking-context-disc]

[^stacking-context-disc]: This tree of surfaces is an implementation strategy
and not something required by any specific web API. However, the web does
define the concept of a [*stacking context*][stacking-context], which is
related. A stacking context is technically a mechanism to define groups and
ordering during paint, and stacking contexts need not correspond to a surface
(e.g. ones created via [`z-index`][z-index] do not). However, for ease of
implementation, all visual effects in CSS that generally require surfaces to
implement are specified to go hand-in-hand with a stacking context, so the tree
of stacking contexts is very related to the tree of surfaces.

[stacking-context]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Positioning/Understanding_z_index/The_stacking_context
[z-index]: https://developer.mozilla.org/en-US/docs/Web/CSS/z-index

To match this use pattern, in Skia, surfaces form a stack. You can
push a new surface on the stack, raster things to it, and then pop it
off by blending it with surface below. When traversing the tree of
stacking contexts, you push a new surface onto the stack every time
you recurse into a new stacking context, and pop-and-blend every time
you return from a child stacking context to its parent.
 
In real browsers, stacking contexts are formed by HTML elements with
certain styles, up to any descendants that themselves have such
styles. The full definition is actually quite complicated, so in this
chapter we'll simplify by treating every layout object as a stacking
context.

::: {.further}
Mostly, elements [form a stacking context][stacking-context] because
of CSS properties that have something to do with layering (like
`z-index`) or visual effects (like `mix-blend-mode`). On the other
hand, the `overflow` property, which can make an element scrollable,
does not induce a stacking context, which I think was a
mistake.[^also-containing-block] The reason is that inside a modern
browser, scrolling is done on the GPU by offsetting two surfaces.
Without a stacking context the browser might (depending on the web
page structure) have to move around multiple independent surfaces with
complex paint orders, in lockstep, to achieve scrolling. Fixed- and
sticky-positioned elements also form stacking contexts because of
their interaction with scrolling.
:::

[^also-containing-block]: While we're at it, perhaps scrollable
elements should also be a [containing block][containing-block] for
descendants. Otherwise, a scrollable element can have non-scrolling
children via properties like `position`. This situation is very
complicated to handle in real browsers.

[containing-block]: https://developer.mozilla.org/en-US/docs/Web/CSS/Containing_block

Opacity and alpha
=================

[canvas]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/canvas
[webgl]: https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API
[webassembly]: https://developer.mozilla.org/en-US/docs/WebAssembly
[canvaskit]: https://skia.org/docs/user/modules/canvaskit/

Color mixing happens when multiple page elements overlap. The easiest
way that happens in our browser is child elements overlapping their
parents, like this:[^transforms-etc]

[^transforms-etc]: There are many more ways elements can overlap in a
real browser: the `transform` property, `position`ed elements,
negative margins, and so many more. But color mixing works the same
way each time.

``` {.html .example}
<div style="background-color:orange">
    Parent
    <div style="background-color:white;border-radius:5px">Child</div>
    Parent
</div>
```

It looks like this:

<div style="background-color:orange">
Parent
<div style="background-color:white;border-radius:5px">Child</div>
Parent
</div>

Right now, the white rectangle completely obscures part of the orange
one; the two colors don't really need to "mix", and in fact it kind of
looks like two orange rectangles instead of an orange rectangle with a
white one on top. Now let's make the white child element
semi-transparent, so the colors have to mix. In CSS, that requires
adding an `opacity` property with a value somewhere between 0
(completely transparent) and 1 (totally opaque). With 50% opacity on
the white child element, it looks like this:

<div style="background-color:orange">
Parent
<div style="background-color:white;border-radius:5px;opacity:0.5">Child</div>
Parent
</div>

Notice that instead of being pure white, the child element now has a
light-orange background color, resulting from orange and white mixing.
Let's implement this in our browser.

The way to mix colors in Skia is to first create two surfaces, and
then draw one into the other. The most convenient way to do that is
with `saveLayer`[^layer-surface] and `restore`:

[^layer-surface]: It's called `saveLayer` instead of `createSurface` because
Skia doesn't actually promise to create a new surface, if it can optimize that
away. So what you're really doing with `saveLayer` is telling Skia that there
is a new conceptual layer ("piece of paper") on the stack. Skia's terminology
distinguishes between a layer and a surface for this reason as well, but for
our purposes it makes sense to assume that each new layer comes with a
surface.

``` {.python .example}
# draw parent
canvas.saveLayer(paint=skia.Paint(Alphaf=0.5))
# draw child
canvas.restore()
```

We first draw the parent, then create a new surface with `saveLayer`
to draw the child into, and then when the `restore` call is made the
`paint` parameters passed into `saveLayer` are used to mix the colors
in the two surfaces together. Here we're using the `Alphaf` parameter,
which describes the opacity as a floating-point number from 0 to 1.

Note that `saveLayer` and `restore` are like a pair of parentheses
enclosing the child drawing operations. This means our display list is
no longer just a linear sequence of drawing operations, but a tree. So
in our display list, let's handle `opacity` with an `Alpha`
command that takes a sequence of other drawing commands as an
argument:

``` {.python file=examples11.py}
class Opacity:
    def __init__(self, opacity, children):
        self.opacity = opacity
        self.children = children
        self.rect = skia.Rect.MakeEmpty()
        for cmd in self.children:
            self.rect.join(cmd.rect)

    def execute(self, canvas):
        paint = skia.Paint(Alphaf=self.opacity)
        canvas.saveLayer(paint=paint)
        for cmd in self.children:
            cmd.execute(canvas)
        canvas.restore()
```

Now let's look at how we can add this to our existing `paint` method for
`BlockLayout`s. Now, _before_ we add its `cmds` command list to the overall
display list, we can use `Opacity` to add transparency to the whole element.
I'm going to do this in a new `paint_effects` method, which will wrap `cmds`
in a `Opacity`. The actual `Opacity` command will be computed in a new
global `paint_visual_effects` method (because other object types will need it
also).

``` {.python}
class BlockLayout:
    def paint_effects(self, cmds):
        cmds = paint_visual_effects(
            self.node, cmds, self.self_rect())
        return cmds
```

A change is now needed in `paint_tree` to call this method, but only *after*
recursing into children, and only if `should_paint` is true. That's because
these visual effects apply to the entire subtree's display list, not just the
current object, and don't apply to "anonymous" objects (see Chapter 8).

``` {.python}
def paint_tree(layout_object, display_list):
    if layout_object.should_paint():
        cmds = layout_object.paint()
    for child in layout_object.children:
        paint_tree(child, cmds)

    if layout_object.should_paint():
        cmds = layout_object.paint_effects(cmds)
    display_list.extend(cmds)
```

Inside `paint_visual_effects`, we'll parse the opacity value and
construct the appropriate `Opacity` command:

``` {.python expected=False}
def paint_visual_effects(node, cmds, rect):
    opacity = float(node.style.get("opacity", "1.0"))

    return [
        Opacity(opacity, cmds)
    ]
```

Note that `paint_visual_effects` receives a list of commands and
returns another list of commands. It's just that the output list is
always a single `Opacity` command that wraps the original
content---which makes sense, because first we need to draw the
commands to a surface, and *then* apply transparency to it when
blending into the parent.

::: {.further}
[This blog post](https://ciechanow.ski/alpha-compositing/) gives a really nice
visual overview of many of the same concepts explored in this chapter,
plus way more content about how a library such as Skia might implement features
like raster sampling of vector graphics for lines and text, and interpolation
of surfaces when their pixel arrays don't match resolution or orientation. I
highly recommend it.
:::

Compositing pixels
==================

Now let's pause and explore how opacity actually works under the hood.
Skia, SDL, and many other color libraries account for opacity with a
fourth *alpha* value for each pixel.[^alpha-vs-opacity] An alpha of 0
means the pixel is fully transparent (meaning, no matter what the
colors are, you can't see them anyway), and an alpha of 1 means a
fully opaque.

[^alpha-vs-opacity]: The difference between opacity and alpha can be
confusing. Think of opacity as a visual effect *applied to* content,
but alpha as a *part of* content. Think of alpha as implementation
technique for representing opacity.

When a pixel with alpha overlaps another pixel, the final color is a
mix of their two colors. How exactly the colors are mixed is defined
by Skia's `Paint` objects. Of course, Skia is pretty complex, but we
can sketch these paint operations in Python as methods on an imaginary
`Pixel` class.

``` {.python file=examples}
class Pixel:
    def __init__(self, r, g, b, a):
        self.r = r
        self.g = g
        self.b = b
        self.a = a
```

When we apply a `Paint` with an `Alphaf` parameter, the first thing
Skia does is add the requested opacity to each pixel:

``` {.python file=examples}
class Pixel:
    def alphaf(self, opacity):
        self.a = self.a * opacity
```

I want to emphasize that this code is not a part of our browser---I'm
simply using Python code to illustrate what Skia is doing internally.

That `Alphaf` parameter applies to pixels in one surface. But with
`saveLayer` we will end up with two surfaces, with all of their pixels
aligned, and therefore we will need to combine, or *blend*,
corresponding pairs of pixels.

Here the terminology can get confusing: we imagine that the pixels "on
top" are blending into the pixels "below", so we call the top surface
the *source surface*, with source pixels, and the bottom surface the
*destination surface*, with destination pixels. When we combine them,
there are lots of ways we could do it, but the default on the web is
called "simple alpha compositing"\index{compositing} or *source-over*
compositing. In Python, the code to implement it looks like
this:[^simple-alpha]

[^simple-alpha]: The formula for this code can be found
[here](https://www.w3.org/TR/SVG11/masking.html#SimpleAlphaBlending).
Note that that page refers to *premultiplied* alpha colors, but Skia's API
generally does not use premultiplied representations, and the code below
doesn't either. (Skia does represent colors internally in a premultiplied form,
however.)

``` {.python file=examples}
class Pixel:
    def source_over(self, source):
        new_a = source.a + self.a * (1 - source.a)
        if new_a == 0: return self
        self.r = \
            (self.r * (1 - source.a) * self.a + \
                source.r * source.a) / new_a
        self.g = \
            (self.g * (1 - source.a) * self.a + \
                source.g * source.a) / new_a
        self.b = \
            (self.b * (1 - source.a) * self.a + \
                source.b * source.a) / new_a
        self.a = new_a
```

Here the destination pixel `self` is modified to blend in the source
pixel `source`. The mathematical expressions for the red, green, and
blue color channels are identical, and basically average the source
and destination colors, weighted by alpha.[^source-over-example] You
might imagine the overall operation of `saveLayer` with an `Alphaf`
parameter as something like this:[^no-pixel-loop]

[^source-over-example]: For example, if the alpha of the source pixel
    is 1, the result is just the source pixel color, and if it is 0
    the result is the backdrop pixel color.
    
[^no-pixel-loop]: In reality, reading individual pixels into memory to
manipulate them like this is slow. So libraries such as Skia don't
make it convenient to do so. (Skia canvases do have `peekPixels` and
`readPixels` methods that are sometimes used, but not for this.)

``` {.python file=examples}
for (x, y) in destination.coordinates():
    source[x, y].alphaf(opacity)
    destination[x, y].source_over(source[x, y])
```

Source-over compositing is one way to combine two pixel values. But
it's not the only method---you could write literally any computation
that combines two pixel values if you wanted. Two computations that
produce interesting effects are traditionally called "multiply" and
"difference" and use simple mathematical operations. "Multiply"
multiplies the color values:

``` {.python file=examples}
class Pixel:
    def multiply(self, source):
        self.r = self.r * source.r
        self.g = self.g * source.g
        self.b = self.b * source.b
```

And "difference" computes their absolute differences:

``` {.python file=examples}
class Pixel:
    def difference(self, source):
        self.r = abs(self.r - source.r)
        self.g = abs(self.g - source.g)
        self.b = abs(self.b - source.b)
```

CSS supports these and many other blending modes[^photoshop-panel] via
the [`mix-blend-mode` property][mix-blend-mode-def], like this:

[^photoshop-panel]: Many of these blending modes are
    [common][wiki-blend-mode] to other graphics editing programs like
    Photoshop and GIMP. Some, like ["dodge" and "burn"][dodge-burn],
    go back to analog photography, where photographers would expose
    some parts of the image more than others to manipulate their
    brightness.

[mix-blend-mode-def]: https://drafts.fxtf.org/compositing-1/#propdef-mix-blend-mode

[dodge-burn]: https://en.wikipedia.org/wiki/Dodging_and_burning

[wiki-blend-mode]: https://en.wikipedia.org/wiki/Blend_modes

``` {.html .example}
<div style="background-color:orange">
    Parent
    <div style="background-color:blue;mix-blend-mode:difference">
        Child
    </div>
    Parent
</div>
```

This HTML will look like:

<div style="background-color:orange">
Parent
<div style="background-color:blue;mix-blend-mode:difference">Child</div>
Parent
</div>

Here, when blue overlaps with orange, we see pink: blue has (red,
green, blue) color channels of `(0, 0, 1)`, and orange has `(1, .65,
0)`, so with "difference" blending the resulting pixel will be `(1,
0.65, 1)`, which is pink. On a pixel level, what's happening is
something like this:

``` {.python file=examples}
for (x, y) in destination.coordinates():
    source[x, y].alphaf(opacity)
    source[x, y].difference(destination[x, y])
    destination[x, y].source_over(source[x, y])
```

This looks weird, but conceptually it blends the destination into the
source (which ignores alpha) and then draws the source over the
destination (with alpha considered). In some sense, blending thus
[happens twice][blending-def].

[blending-def]: https://drafts.fxtf.org/compositing-1/#blending

Skia supports the [multiply][mbm-mult]
and [difference][mbm-diff] blend modes natively:

[mbm-mult]: https://drafts.fxtf.org/compositing-1/#blendingmultiply
[mbm-diff]: https://drafts.fxtf.org/compositing-1/#blendingdifference

``` {.python}
def parse_blend_mode(blend_mode_str):
    if blend_mode_str == "multiply":
        return skia.BlendMode.kMultiply
    elif blend_mode_str == "difference":
        return skia.BlendMode.kDifference
    elif blend_mode_str == "normal":
        return skia.BlendMode.kSrcOver
    else:
        return skia.BlendMode.kSrcOver
```

We can then support blending in our browser by defining a new `Blend`
operation:

``` {.python expected=False}
class Blend:
    def __init__(self, blend_mode, children):
        self.blend_mode = blend_mode

        self.children = children
        self.rect = skia.Rect.MakeEmpty()
        for cmd in self.children:
            self.rect.join(cmd.rect)

    def execute(self, canvas):
        paint = skia.Paint(
            BlendMode=self.blend_mode)
        canvas.saveLayer(paint=paint)
        for cmd in self.children:
            cmd.execute(canvas)
        canvas.restore()
```

Applying it when `mix-blend-mode` is set just requires a simple change
to `paint_visual_effects`:

``` {.python expected=False}
def paint_visual_effects(node, cmds, rect):
    # ...
    blend_mode = parse_blend_mode(node.style.get("mix-blend-mode"))
    
    return [
        Blend(blend_mode, [
            Opacity(opacity, cmds),
        ]),
    ]
```

Note the order of operations here: we _first_ apply transparency, and
_then_ blend the result into the rest of the page. If we switched the
`Opacity` and `Blend` calls there wouldn't be anything to blend it into!

::: {.further}
Alpha might seem intuitive, but it's less obvious than you think: see,
for example, this [history of alpha][alpha-history] written by its
co-inventor (and co-founder of Pixar). And there are several different
implementation options. For example, many graphics libraries, Skia
included, multiply the color channels by the opacity instead of
allocating a whole color channel. This [premultiplied][premultiplied]
representation is generally more efficient; for example, `source_over`
above had to divide by `self.a` at the end, because otherwise the
result would be premultiplied. Using a premultiplied representation
throughout would save a division. Nor is it obvious how alpha [behaves
when resized][alpha-deriv].
:::

[alpha-history]: http://alvyray.com/Memos/CG/Microsoft/7_alpha.pdf
[alpha-deriv]: https://jcgt.org/published/0004/02/03/paper.pdf
[premultiplied]: https://limnu.com/premultiplied-alpha-primer-artists/

Clipping and masking
====================

The "multiply" and "difference" blend modes can seem kind of obscure,
but blend modes are a flexible way to implement per-pixel operations.
One common use case is clipping---intersecting a surface with a given
shape. It's called clipping because it's like putting a second piece
of paper (called a *mask*) over the first one, and then using scissors
to cut along the mask's edge.

There are all sorts of powerful methods[^like-clip-path] for clipping
content on the web, but the most common form involves the `overflow`
property. This property has lots of possible values,[^like-scroll] but
let's focus here on `overflow: clip`, which cuts off contents of an
element that are outside the element's bounds.

[^like-clip-path]: The CSS [`clip-path` property][mdn-clip-path] lets
specify a mask shape using a curve, while the [`mask`
property][mdn-mask] lets you instead specify a image URL for the mask.

[^like-scroll]: For example, `overflow: scroll` adds scroll bars and
    makes an element scrollable, while `overflow: hidden` is similar
    to but subtly different from `overflow: clip`.

[mdn-mask]: https://developer.mozilla.org/en-US/docs/Web/CSS/mask

[mdn-clip-path]: https://developer.mozilla.org/en-US/docs/Web/CSS/clip-path

Usually, `overflow: clip` is used with properties like `height` or
`rotate` which can make an element's children poke outside their
parent. Our browser doesn't support these, but there is one edge case
where `overflow: clip` is relevant: rounded corners.^[Technically,
clipping is also relevant for our browser with single words that are longer
than the browser window's width. [Here][longword] is an example.] Consider this
example:

[longword]: examples/example11-longword.html

``` {.html .example}
<div 
  style="border-radius:30px;background-color:lightblue;overflow:clip">
    This test text exists here to ensure that the "div" element is
    large enough that the border radius is obvious.
</div>
```

That HTML looks like this:

<div style="border-radius:30px;background-color:lightblue;overflow:clip">
This test text exists here to ensure that the "div" element is
large enough that the border radius is obvious.
</div>

Observe that the letters near the corner are cut off to maintain a sharp rounded
edge. That's clipping; without the `overflow: clip` property these letters
would instead be fully drawn, like we saw earlier in this chapter.

Counterintuitively, we'll implement clipping using blending modes.
We'll make a new surface (the mask), draw a rounded rectangle into it,
and then blend it with the element contents. But we want to see the
element contents, not the mask, so when we do this blending we will
use *destination-in* compositing.

[Destination-in compositing][dst-in] basically means keeping the
pixels of the destination surface that intersect with the source
surface. The source surface's color is not used---just its alpha. In
our case, the source surface is the rounded rectangle mask and the
destination surface is the content we want to clip, so destination-in
fits perfectly. In code, destination-in looks like this:

[dst-in]: https://drafts.fxtf.org/compositing-1/#porterduffcompositingoperators_dstin

``` {.python file=examples}
class Pixel:
    def destination_in(self, source):
        self.a = self.a * source.a
```

Now, in `paint_visual_effects`, we need to create a new layer, draw
the mask image into it, and then blend it with the element contents
with destination-in blending:

``` {.python expected=False}
def paint_visual_effects(node, cmds, rect):
    # ...
    if node.style.get("overflow", "visible") == "clip":
        border_radius = \
            float(node.style.get("border-radius", "0px")[:-2])
        cmds.append(Blend("destination-in", [
            DrawRRect(rect, border_radius, "white")
        ]))

    return [
        Blend(blend_mode, [
            Opacity(opacity, cmds),
        ]),
    ]
```

Here I pass `destination-in` as the blend mode, though note that this
is a bit of a hack and that isn't actually a valid value of
`mix-blend-mode`:

``` {.python}
def parse_blend_mode(blend_mode_str):
    # ...
    elif blend_mode_str == "destination-in":
        return skia.BlendMode.kDstIn
    # ...
```

After drawing all of the element contents with `cmds` (and applying
opacity), this code draws a rounded rectangle on another layer to
serve as the mask, and uses destination-in blending to clip the
element contents. Here I chose to draw the rounded rectangle in white,
but the color doesn't matter as long as it's opaque. On the other
hand, if there's no clipping, I don't round the corners of the mask,
which means nothing is clipped out.

Notice how similar this masking technique is to the physical analogy
with scissors described earlier, with the two layers playing the role
of two sheets of paper and destination-in compositing playing the role
of the scissors. This implementation technique for clipping is called
*masking*, and it is very general---you can use it with arbitrarily
complex mask shapes, like text, bitmap images, or anything else you
can imagine.

::: {.further}
Rounded corners have an [interesting history][mac-story] in computing.
Features that are simple today were [very complex][quickdraw] to
implement on early personal computers with limited memory and no
hardware floating-point arithmetic. Even when floating-point hardware
and eventually GPUs became standard, the `border-radius` CSS property
didn't appear in browsers until around 2010.[^didnt-stop] More
recently, the introduction of animations, visual effects, multi-process
compositing, and [hardware overlays][hardware-overlays] have again
rounded corners pretty complex. The `clipRRect` fast path, for example,
can fail to apply for cases such as hardware video overlays and nested
rounded corner clips.
:::

[^didnt-stop]: The lack of support didn't stop web developers from
putting rounded corners on their sites before `border-radius` was
supported. There are a number of clever ways to do it; [this
video][rr-video] walks through several.

[mac-story]: https://www.folklore.org/StoryView.py?story=Round_Rects_Are_Everywhere.txt
[quickdraw]: https://raw.githubusercontent.com/jrk/QuickDraw/master/RRects.a
[hardware-overlays]: https://en.wikipedia.org/wiki/Hardware_overlay
[rr-video]: https://css-tricks.com/video-screencasts/24-rounded-corners/

Optimizing surface use
======================

Our browser now works correctly, but uses way too many surfaces. For
example, for a single, no-effects-needed div with some text content,
there are currently 18 surfaces allocated in the display list. If
there's no blending going on, we should only need one!

Let's review all the surfaces that our code can create for an element:

- The top-level surface is used to apply *blend modes*. Since it's the
top-level surface, it also *isolates* the element from other parts of
the page, so that clipping only applies to that element.
- The first nested surface is used for applying *opacity*.
- The second nested surface is used to implement *clipping*.

But not every element has opacity, blend modes, or clipping applied,
and we could skip creating those surfaces most of the time. For
example, there's no reason to create a surface in `Opacity` if no
opacity is actually applied:

``` {.python file=examples11.py}
class Opacity:
    def execute(self, canvas):
        paint = skia.Paint(Alphaf=self.opacity)
        if self.opacity < 1:
            canvas.saveLayer(paint=paint)
        for cmd in self.children:
            cmd.execute(canvas)
        if self.opacity < 1:
            canvas.restore()
```

Similarly, `Blend` doesn't necessarily need to create a layer if
there's no blending going on. But the logic here is a little trickier:
`Blend` operation not only applies blending but also
isolates the element contents `cmds`, which matters if they are being clipped by
`overflow`. So let's skip creating a layer in `Blend` when there's no
blending mode other than `kSrcOver`, or isolation is needed:

``` {.python expected=False}
def paint_visual_effects(node, cmds, rect):
    needs_isolation = False
    if node.style.get("overflow", "visible") == "clip":
        needs_isolation = True
        # ...

    return [
        Blend(blend_mode, needs_isolation [
            Opacity(opacity, cmds),
        ]),
    ]
```

``` {.python replace=blend_mode%2c/opacity%2c%20blend_mode%2c,kSrcOver/kSrcOver%20or%20\\}
class Blend:
    def __init__(self, blend_mode, needs_isolation, children):
        # ...
        self.should_save = needs_isolation or \
            self.blend_mode != skia.BlendMode.kSrcOver

    def execute(self, canvas):
        paint = skia.Paint(
            BlendMode=self.blend_mode)
        if self.should_save:
            canvas.saveLayer(paint=paint)
        for cmd in self.children:
            cmd.execute(canvas)
        if self.should_save:
            canvas.restore()
```

So now we skip creating extra surfaces when `Opacity` and `Blend` aren't
really necessary. But there's still one case where we use too many:
both `Opacity` and `Blend` can create a surface instead of sharing one.
Let's fix that by just merging opacity into `Blend`:[^filters]

[^filters]: This works for opacity, but not for filters that "move
pixels" such as [blur][mdn-blur]. Such a filter needs to be applied
before clipping, not when blending into the parent surface. Otherwise,
the edge of the blur will not be sharp.

[mdn-blur]: https://developer.mozilla.org/en-US/docs/Web/CSS/filter-function/blur()

``` {.python}
class Blend:
    def __init__(self, opacity, blend_mode, needs_isolation, \
        children):
        self.opacity = opacity
        self.blend_mode = blend_mode
        self.should_save = needs_isolation or \
            self.blend_mode != skia.BlendMode.kSrcOver or \
            self.opacity < 1

        self.children = children
        self.rect = skia.Rect.MakeEmpty()
        for cmd in self.children:
            self.rect.join(cmd.rect)

    def execute(self, canvas):
        paint = skia.Paint(
            Alphaf=self.opacity,
            BlendMode=self.blend_mode)
        if self.should_save:
            canvas.saveLayer(paint=paint)
        for cmd in self.children:
            cmd.execute(canvas)
        if self.should_save:
            canvas.restore()
```

Now `paint_visual_effects` looks like this:

``` {.python expected=False}
def paint_visual_effects(node, cmds, rect):
    # ...

    if node.style.get("overflow", "visible") == "clip":
        # ...
        cmds.append(Blend(1.0, "destination-in", [
            DrawRRect(rect, border_radius, "white")
        ]))

    return [Blend(opacity, blend_mode, cmds)]
```

Note that I've specified an opacity of `1.0` for the clip `Blend`.

There's one more optimization to make: using Skia's `clipRRect`
operation to get rid of the destination-in blended surface. This
operation takes in a rounded rectangle and changes the *canvas state*
so that all future commands skip drawing any pixels outside that
rounded rectangle.

There are multiple advantages to using `clipRRect` over an explicit
destination-in surface. First, most of the time, it allows Skia to
avoid making a surface for the mask.[^shader-rounded] It also allows
Skia to skip draw operations that don't intersect the mask, or
dynamically draw only the parts of operations that intersect it. It's
basically the optimization we implemented for scrolling
[in Chapter 2](graphics.md#faster-rendering).[^no-other-shapes]

[^shader-rounded]: At a high level, this is achieved by having the GPU
*shaders*---the code---for various drawing commands check for clipping
when they draw. In effect, the clip region is stored implicitly, in
the code and state of the canvas, instead of explicitly in a surface.
GPU programs are out of scope for this book, but if you're curious
there are many online resources with more information.

[^no-other-shapes]: This kind of code is complex for Skia to implement,
so it only makes sense to do it for common patterns, like rounded
rectangles. This is why Skia only supports optimized clips for a few
common shapes.

Since `clipRRect` changes the canvas state, we'll need to restore it
once we're done with clipping. That uses the `save` and `restore`
methods---you call `save` before calling `clipRRect`, and `restore`
after finishing drawing the commands that should be clipped:

``` {.python .example}
# Draw commands that should not be clipped.
canvas.save()
canvas.clipRRect(rounded_rect)
# Draw commands that should be clipped.
canvas.restore()
# Draw commands that should not be clipped.
```

You might notice the similarity between `save`/`restore` and the
`saveLayer`/`restore` operations created by `Blend`. That's
because Skia has a combined stack of surfaces and canvas states.
Unlike `saveLayer`, however, `save` never creates a new surface;
it just changes the canvas state to change how commands are executed,
in this case to clip those commands to a rounded rectangle.

Let's wrap this pattern into a `ClipRRect` drawing command, which like
`Blend` takes a list of subcommands:[^save-clip]

[^save-clip]: If you're doing two clips at once, or a clip and a
transform, or some other more complex setup that would benefit from
only saving once but doing multiple things inside it, this pattern of
always saving canvas parameters might be wasteful, but since it
doesn't create a surface it's still a big optimization here.

``` {.python}
class ClipRRect:
    def __init__(self, rect, radius, children):
        self.rect = rect
        self.rrect = skia.RRect.MakeRectXY(rect, radius, radius)
        self.children = children

    def execute(self, canvas):
        canvas.save()
        canvas.clipRRect(self.rrect)

        for cmd in self.children:
            cmd.execute(canvas)

        canvas.restore()
```

Now, in `paint_visual_effects`, we can use `ClipRRect` instead of
destination-in blending with `DrawRRect` (and we can
fold the opacity into the `skia.Paint` passed to the outer
`Blend`, since that is defined to be applied before blending):

``` {.python}
def paint_visual_effects(node, cmds, rect):
    if node.style.get("overflow", "visible") == "clip":
        # ...
        cmds = [ClipRRect(rect, border_radius, cmds)]
```

Of course, `clipRRect` only applies for rounded rectangles, while
masking is a general technique that can be used to implement all
sorts of clips and masks (like CSS's `clip-path` and `mask`), so a
real browser will typically have both code paths.

So now, each element uses at most one surface, and even then only if
it has opacity or a non-default blend mode. Everything else should
look visually the same, but will be faster and use less memory.

::: {.further}
Besides using fewer surfaces, real browsers also need to avoid
surfaces getting too big. Real browsers use *tiling* for this,
breaking up the surface into a grid of tiles which have their own
raster surfaces and their own *x* and *y* offset to the page. Whenever
content that intersects a tile changes its display list, the tile is
re-rastered. Tiles that are not on or "near"[^near] the screen are not
rastered at all. This all happens on the GPU, since surfaces (Skia
ones [in particular](https://kyamagu.github.io/skia-python/reference/skia.Surface.html))
can be stored on the GPU.
:::

[^near]: For example, tiles that just scrolled off-screen.


Summary
=======

So there you have it: our browser can draw not only boring
text and boxes but also:

- Partial transparency via an alpha channel
- User-configurable blending modes via `mix-blend-mode`
- Rounded rectangle clipping via destination-in blending or direct clipping
- Optimizations to avoid surfaces when possible
- Browser compositing with extra surfaces for faster scrolling

Besides the new features, we've upgraded from Tkinter to SDL and Skia,
which makes our browser faster and more responsive, and also sets a
foundation for more work on browser performance to come.


Outline
=======

The complete set of functions, classes, and methods in our browser 
should now look something like this:

::: {.cmd .python .outline html=True}
    python3 infra/outlines.py --html src/lab11.py
:::

If you run it, it should look something like [this
page](widgets/lab11-browser.html); due to the browser sandbox, you
will need to open that page in a new tab.

Exercises
=========

*Filters*: The `filter` CSS property allows specifying various kinds
of more [complex effects][filter-css], such as grayscale or blur.
These are fun to implement, and some, like `blur`, have built-in
support in Skia. Implement `blur`. Think carefully about when blurring
occurs, relative to other effects like transparency, clipping, and
blending.

[filter-css]: https://developer.mozilla.org/en-US/docs/Web/CSS/filter

*Hit testing*: If you have an element with a `border-radius`, it's
possible to click outside the element but inside its containing
rectangle, by clicking in the part of the corner that is "rounded
off". This shouldn't result in clicking on the element, but in our
browser it currently does. Modify the `click` method to take border
radii into account.

*Interest region*: Our browser now draws the whole web page to a
single surface, which means a very long web page (like this one!)
creates a large surface, thereby using a lot of memory. Instead, only
draw an "interest region" of limited height, say `4 * HEIGHT` pixels.
You'll need to keep track of where the interest region is on the page,
draw the correct part of it to the screen, and re-raster the interest
region when the user attempts to scroll outside of it. Use Skia's
`clipRect` operation to avoid drawing outside the interest region.

*Overflow scrolling*: An element with the `overflow` property set to
`scroll` and a fixed pixel `height` is scrollable. (You'll want to
implement the width/height exercise from [Chapter
6](styles.md#exercises) so that `height` is supported.) Implement some
version of `overflow: scroll`. I recommend the following user
interaction: the user clicks within a scrollable element to focus it,
and then can press the arrow keys to scroll up and down. You'll need
to keep track of the *[layout overflow][overflow-doc]*. For an extra
challenge, make sure you support scrollable elements nested within
other scrollable elements.

 [overflow-doc]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Flow_Layout/Flow_Layout_and_Overflow

*Touch input*: Many desktop (and all mobile, of course) screens these
days support touch and multitouch input. And SDL has [APIs][sdl-touch]
to support it. Implement a touch-input variant of `click`.^[You might want
to go back and look at a go-further block in [Chapter 7](chrome.md) for some
hints about good ways to implement touch input.]

[sdl-touch]: https://wiki.libsdl.org/SDL2/SDL_MultiGestureEvent
