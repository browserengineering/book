---
title: Adding Visual Effects
chapter: 11
prev: security
next: rendering-architecture
...

Right now our browser's visual capabilities are pretty boring, just colored
rectangles and text. Real browsers, one the other hand, support all kinds
of *visual effects* that affect how elements look. Before we add these to our
browser, we'll need to learn a bit about pixels, colors, and blending of
surfaces onto computer screens. We'll then be able to implement these effects
using the Skia graphics library, and you'll see a bit of how Skia is
implemented under the hood. Finally we'll see how surfaces also play a key role
in *browser compositing* to accelerate animations like scrolling.

Installing Skia and SDL
=======================

Before we get any further, we'll need to upgrade our graphics system.
While Tkinter is great for basic shapes and handling input, it lacks
built-in visual effects routines.[^tkinter-before-gpu] Implementing
fast visual effects routines is fun, but it's outside the scope of
this book, so we need a new graphics library. Let's use [Skia][skia],
the library that Chromium uses. Unlike Tkinter, Skia doesn't handle
inputs or create graphical windows, so we'll pair it with the
[SDL][sdl] GUI library.

[skia]: https://skia.org
[sdl]: https://www.libsdl.org/

[^tkinter-before-gpu]: That's because Tk, the graphics library that
Tkinter uses, dates from the early 90s, before high-performance
graphics cards and GPUs became widespread.

Start by installing [Skia][skia-python] and
[SDL][sdl-python]:

    pip3 install skia-python pysdl2 pysdl2-dll

[skia-python]: https://kyamagu.github.io/skia-python/
[sdl-python]: https://pypi.org/project/PySDL2/

::: {.install}
As elsewhere in this book, you may need to use `pip`, `easy_install`,
or `python3 -m pip` instead of `pip3` as your installer, or use your
IDE's package installer. If you're on Linux, you'll need to install
additional dependencies, like OpenGL and fontconfig. Also, you may not be
able to install `pysdl2-dll`; if so, you'll need to find SDL in your system
package manager instead. Consult the  [`skia-python`][skia-python] and
[`pysdl2`][sdl-python] web pages for more details.
:::

Once installed, remove `tkinter` from your Python imports and replace them with:

``` {.python}
import ctypes
import sdl2
import skia
```

If any of these imports fail, you probably need to check that Skia and
SDL were installed correctly. Note that the `ctypes` module comes
standard in Python; it is used to convert between Python and C types.

SDL creates the window
======================

The main loop of the browser first needs some boilerplate to get SDL
started:

``` {.python}
if __name__ == "__main__":
    import sys
    sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS)
    browser = Browser()
    browser.load(sys.argv[1])
    # ...
```

Next, we need to create an SDL window, instead of a Tkinter window,
inside the Browser, and set up Skia to draw to it. Here's the SDL
incantation to create a window:

``` {.python}
class Browser:
    def __init__(self):
        self.sdl_window = sdl2.SDL_CreateWindow(b"Browser",
            sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
            WIDTH, HEIGHT, sdl2.SDL_WINDOW_SHOWN)
```

To set up Skia to draw to this window, we also need create a
*surface* for it:[^surface]

[^surface]: In Skia and SDL, a *surface* is a representation of a
graphics buffer into which you can draw *pixels* (bits representing
colors). A surface may or may not be bound to the physical pixels on the
screen via a window, and there can be many surfaces. A *canvas* is an
API interface that allows you to draw into a surface with higher-level
commands such as for rectangles or text. Our browser uses separate
Skia and SDL surfaces for simplicity, but in a highly optimized
browser, minimizing the number of surfaces is important for good
performance.


``` {.python}
class Browser:
    def __init__(self):
        self.root_surface = skia.Surface.MakeRaster(
            skia.ImageInfo.Make(
                WIDTH, HEIGHT,
                ct=skia.kRGBA_8888_ColorType,
                at=skia.kUnpremul_AlphaType))
```

Typically, we'll draw to the Skia surface, and then once we're done
with it we'll copy it to the SDL surface to display on the screen.
This will be a little hairy, because we are moving data between two
low-level libraries, but really it's just copying pixels from one
place to another.

First, get the sequence of bytes representing the Skia surface:

``` {.python replace=draw_to_screen/draw}
class Browser:
    def draw_to_screen(self):
        # This makes an image interface to the Skia surface, but
        # doesn't actually copy anything yet.
        skia_image = self.root_surface.makeImageSnapshot()
        skia_bytes = skia_image.tobytes()
```

Next, we need to copy the data to an SDL surface. This requires
telling SDL what order the pixels are stored in (which we specified to
be `RGBA_8888` when constructing the surface) and on your computer's
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

The `CreateRGBSurfaceFrom` method then copies the data:

``` {.python replace=draw_to_screen/draw}
class Browser:
    def draw_to_screen(self):
        # ...
        depth = 32 # Bits per pixel
        pitch = 4 * WIDTH # Bytes per row
        sdl_surface = sdl2.SDL_CreateRGBSurfaceFrom(
            skia_bytes, WIDTH, HEIGHT, depth, pitch,
            self.RED_MASK, self.GREEN_MASK,
            self.BLUE_MASK, self.ALPHA_MASK)
```

Finally, we draw all this pixel data on the window itself:

``` {.python replace=draw_to_screen/draw}
class Browser:
    def draw_to_screen(self):
        # ...
        rect = sdl2.SDL_Rect(0, 0, WIDTH, HEIGHT)
        window_surface = sdl2.SDL_GetWindowSurface(self.sdl_window)
        # SDL_BlitSurface is what actually does the copy.
        sdl2.SDL_BlitSurface(sdl_surface, rect, window_surface, rect)
        sdl2.SDL_UpdateWindowSurface(self.sdl_window)
```

Next, SDL doesn't have a `mainloop` or `bind` method; we have to
implement it ourselves:

``` {.python}
if __name__ == "__main__":
    # ...
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

We'll also need to handle all of the other events in this
loop---clicks, typing, and so on:

``` {.python}
if __name__ == "__main__":
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

You can now remove all of the `bind` calls in the `Browser`
constructor; this main loop replaces them. Also note that I've changed
the signatures of the various `handle_xxx` methods; you'll need to
make analogous changes in `Browser` where they are defined.

::: {.further}
SDL is most popular for making games. A selection of books about
game programming and SDL are listed [here](https://wiki.libsdl.org/Books).
:::

Skia is the canvas
==================

Now our browser is creating an SDL window can draw to it via Skia. But
most of the browser codebase is still using Tkinter drawing commands,
which we now need to replace. Skia is a bit more verbose than Tkinter,
so let's abstract over some details with helper functions.[^skia-docs]
First, a helper function to convert colors to Skia colors:

[^skia-docs]: Consult the [Skia][skia] and [skia-python][skia-python]
documentation for more on the Skia API.

``` {.python}
def color_to_sk_color(color):
    if color == "white":
        return skia.ColorWHITE
    elif color == "lightblue":
        return skia.ColorSetARGB(0xFF, 0xAD, 0xD8, 0xE6)
    # ...
    else:
        return skia.ColorBLACK
```

You can add more "elif" blocks to support your favorite color names;
modern browsers support [quite a lot][css-colors].

[css-colors]: https://developer.mozilla.org/en-US/docs/Web/CSS/color_value

To draw a line, you use Skia's `Path` object:

``` {.python}
def draw_line(canvas, x1, y1, x2, y2):
    path = skia.Path().moveTo(x1, y1).lineTo(x2, y2)
    paint = skia.Paint(Color=skia.ColorBLACK)
    paint.setStyle(skia.Paint.kStroke_Style)
    paint.setStrokeWidth(1);
    canvas.drawPath(path, paint)
```

To draw text, you use `drawString`:

``` {.python}
def draw_text(canvas, x, y, text, font, color=None):
    sk_color = color_to_sk_color(color)
    paint = skia.Paint(AntiAlias=True, Color=sk_color)
    canvas.drawString(
        text, float(x), y - font.getMetrics().fAscent,
        font, paint)
```

Finally, for drawing rectangles you use `drawRect`:

``` {.python}
def draw_rect(canvas, l, t, r, b, fill=None, width=1):
    paint = skia.Paint()
    if fill:
        paint.setStrokeWidth(width);
        paint.setColor(color_to_sk_color(fill))
    else:
        paint.setStyle(skia.Paint.kStroke_Style)
        paint.setStrokeWidth(1);
        paint.setColor(skia.ColorBLACK)
    rect = skia.Rect.MakeLTRB(l, t, r, b)
    canvas.drawRect(rect, paint)
```

If you look at the details of these helper methods, you'll see that
they all use a Skia `Paint` object to describe a shape's borders and
colors. We'll be seeing a lot more features of `Paint` in this chapter.

With these helper methods we can now upgrade our browser's drawing
commands to use Skia:

``` {.python replace=%2c%20scroll/,%20-%20scroll/}
class DrawText:
    def execute(self, scroll, canvas):
        draw_text(canvas, self.left, self.top - scroll,
            self.text, self.font, self.color)

class DrawRect:
    def execute(self, scroll, canvas):
        draw_rect(canvas,
            self.left, self.top - scroll,
            self.right, self.bottom - scroll,
            fill=self.color, width=0)
```

Finally, the `Browser` class also uses Tkinter commands in its `draw`
method, which we'll also need to change to use Skia. It's a long
method, so we'll need to go step by step.

First, clear the canvas and and draw the current `Tab` into it:

``` {.python expected=False}
class Browser:
    def draw(self):
        canvas = self.root_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)

        self.tabs[self.active_tab].draw(canvas)
```

Then draw the browser UI elements. First, the tabs:

``` {.python replace=draw%28/raster%28}
class Browser:
    def draw(self):
        # ...
        tabfont = skia.Font(skia.Typeface('Arial'), 20)
        for i, tab in enumerate(self.tabs):
            name = "Tab {}".format(i)
            x1, x2 = 40 + 80 * i, 120 + 80 * i
            draw_line(canvas, x1, 0, x1, 40)
            draw_line(canvas, x2, 0, x2, 40)
            draw_text(canvas, x1 + 10, 10, name, tabfont)
            if i == self.active_tab:
                draw_line(canvas, 0, 40, x1, 40)
                draw_line(canvas, x2, 40, WIDTH, 40)
```

Next, the plus button for adding a new tab:[^move-plus]

[^move-plus]: I also changed the *y* position of the plus sign. The
    change from Tkinter to Skia changes how fonts are drawn, and the
    new *y* position keeps the plus centered in the box.

``` {.python replace=draw%28/raster%28}
class Browser:
    def draw(self):
        # ...
        buttonfont = skia.Font(skia.Typeface('Arial'), 30)
        draw_rect(canvas, 10, 10, 30, 30)
        draw_text(canvas, 11, 4, "+", buttonfont)
```

Then the address bar, including text and cursor:

``` {.python replace=draw%28/raster%28}
class Browser:
    def draw(self):
        # ...
        draw_rect(canvas, 40, 50, WIDTH - 10, 90)
        if self.focus == "address bar":
            draw_text(canvas, 55, 55, self.address_bar, buttonfont)
            w = buttonfont.measureText(self.address_bar)
            draw_line(canvas, 55 + w, 55, 55 + w, 85)
        else:
            url = self.tabs[self.active_tab].url
            draw_text(canvas, 55, 55, url, buttonfont)
```

And finally the "back" button:

``` {.python replace=draw%28/raster%28}
class Browser:
    def draw(self):
        # ...
        draw_rect(canvas, 10, 50, 35, 90)
        path = \
            skia.Path().moveTo(15, 70).lineTo(30, 55).lineTo(30, 85)
        paint = skia.Paint(
            Color=skia.ColorBLACK, Style=skia.Paint.kFill_Style)
        canvas.drawPath(path, paint)
```

Once this is done, we need to copy from the Skia surface to the SDL window:

``` {.python expected=False}
class Browser:
    def draw(self):
        # ...
        self.draw_to_screen()
```

`Tab` also has a `draw` method, which draws a cursor; it needs to use
`draw_line` for that:

``` {.python replace=draw%28/raster%28,%20-%20self.scroll%20+%20CHROME_PX/}
class Tab:
    def draw(self, canvas):
        if self.focus:
            # ...
            draw_line(canvas, x, y, x, y + obj.height)
```

That's most of it. The last few changes we need to upgrade from
Tkinter to SDL and Skia relate to fonts and text.

::: {.further}
Implementing high-quality raster libraries is very interesting in its own
right. These days, it's especially important to leverage GPUs when
they're available, and browsers often push the envelope. Browser teams
typically include raster library experts: Skia for Chromium and [Core
Graphics][core-graphics] for Webkit, for example. Both of these
libraries are used outside of the browser, too: Core Graphics in iOS
and macOS, and Skia in Android.

If you're looking for another book on how these libraries are implemented, check
out [Real-Time Rendering][rtr-book]. There is also [Computer Graphics:
Principles and Practice][classic], which incidentally I remember buying back
the days of my youth (1992 or so). At the time I didn't get much further than
rastering lines and a few polygons (and in assembly language!). These days you
can do the same and more with Skia and a few lines of Python.
:::

[core-graphics]: https://developer.apple.com/documentation/coregraphics
[rtr-book]: https://www.realtimerendering.com/
[classic]: https://en.wikipedia.org/wiki/Computer_Graphics:_Principles_and_Practice


Skia is also the font library
=============================

Since we're replacing `tkinter`, we are also replacing `tkinter.font`.
In Skia, a font object has two pieces: a `Typeface`, which is a type
family with a certain weight, style, and width; and a `Font`, which is
a `Typeface` at a particular size. It's the `Typeface` that contains
data and caches, so that's what we need to cache:

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
are provided by the `measureText` and `getMetrics` measurements. Let's
start with `measureText`---it needs to replace all calls to `measure`.
For example, in the `draw` method on `Tab`s, we must do:

``` {.python replace=draw/raster}
class Tab:
    def draw(self, canvas):
        if self.focus:
            # ...
            x = obj.x + obj.font.measureText(text)
            # ...
```

There are also `measure` calls in `DrawText`, in the `draw` method on
`Browser`, in the `text` method in `InlineLayout`, and in the `layout`
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
descent are positive if they go downward and negative if they go upward,
so ascents will normally be negative, the opposite of Tkinter.

You should now be able to run the browser again. It should look and
behave just as it did in previous chapters, and it'll probably feel
faster, because Skia and SDL are faster than Tkinter.

Let's reward ourselves for the big refactor with a simple feature that Skia
enables: rounded corners of a rectangle via the `border-radius` CSS property,
like this:

    <div style="border-radius: 10px; background: lightblue">
        This is some example text.
    </div>

Which looks like this (note that the text is *not* cut out):

<div style="border-radius:10px;background:lightblue">
This is some example text.
</div>

Implementing requires drawing a rounded rectangle, so let's add a new
`DrawRRect` command:

``` {.python}
class DrawRRect:
    def __init__(self, rect, radius, color):
        self.rect = rect
        self.rrect = skia.RRect.MakeRectXY(rect, radius, radius)
        self.color = color_to_sk_color(color)

    def execute(self, canvas):
        canvas.drawRRect(self.rrect,
            paint=skia.Paint(Color=self.color))
```

Note that Skia supports `RRect`s, or rounded rectangles, natively, so
we can just draw one right to a canvas. Now we can draw these rounded
rectangles for the background:

``` {.python replace=display_list./cmds.}
class BlockLayout:
    def paint(self, display_list):
        if bgcolor != "transparent":
            radius = float(
                self.node.style.get("border-radius", "0px")[:-2])
            cmds.append(DrawRRect(rect, radius, bgcolor))
```

Similar changes should be made to `InputLayout` and `InlineLayout`

After all, one advantage of using Skia is that, since it is also used
in the Chrome browser, we know it has fast, built-in support for all
of the shapes we might need.

::: {.further}
[Font rasterization](https://en.wikipedia.org/wiki/Font_rasterization) is yet
another interesting subject. There are, for example,
techniques such as
[subpixel rendering](https://en.wikipedia.org/wiki/Subpixel_rendering) to
make fonts look better on lower-resolution screens, often using all three
color channels to fool the eye into seeing more detail. These techniques
are much less necessary on
[high-pixel-density](https://en.wikipedia.org/wiki/Pixel_density) screens.
It's likely that eventually, all screens will be high-density enough to retire
these techniques.
:::

Pixels, Color, and Raster
=========================

Skia, like the Tkinter canvas we've been using until now, is a
_rasterization_ library: it converts shapes like rectangles and text
into pixels. Before we move on to Skia's advanced features, let's talk
about how rasterization works at a deeper level.

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
The human perception of color is a topic that combines software,
hardware, chemistry, biology, and psychology.
:::

[cones]: https://en.wikipedia.org/wiki/Cone_cell
[cielab]: https://en.wikipedia.org/wiki/CIELAB_color_space
[opponent-process]: https://en.wikipedia.org/wiki/Opponent_process
[colorblind]: https://en.wikipedia.org/wiki/Color_blindness
[tetrachromats]: https://en.wikipedia.org/wiki/Tetrachromacy#Humans

::: {.further}
The [`<canvas>`][canvas] HTML element provides a similar API to JavaScript. Combined
with [WebGL][webgl], it's possible to implement basically all of SDL and Skia
in JavaScript. Alternatively, it's possible to [compile Skia][canvaskit] to
[WebAssembly][webassembly] to do the same.
:::

Blending and Stacking Contexts
==============================

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
placed semi-transparenly over a white background. The text
is gray while the background is yellow-orange. That's due to blending:
the text and the background are both partially transparent and let
through some of the underlying white:

<div style="opacity: 0.5; background: orange; color: black; font-size: 50px; padding: 15px; text-align: center;flex:1;">Test</div>

But importantly, the text isn't orange-gray: even though the text is
partially transparent, none of the orange shines through. That's
because the order matters. First, the text is blended with the
background; since the text is opaque, its blended pixels are black and
overwrite the orange background. Then, this black-and-orange is
blended with the white background. Doing the operations in a different
order would lead to dark-orange or black text.

To handle this properly, browsers apply blending not to individual
shapes but to a tree of [*stacking contexts*][stacking-context].
Conceptually, each stacking context is drawn onto its own surface, and
then blended into its parent stacking context. Rastering a web page
requires a bottom-up traversal of the tree of stacking contexts: to
raster a stacking context you first need to raster its contents,
including its child stacking contexts, and then the whole contents
need to be blended together into the parent.

To match this use pattern, in Skia, surfaces form a stack. You can
push a new surface on the stack, raster things to it, and then pop it
off by blending it with surface below. When traversing the tree of
stacking contexts, you push a new surface onto the stack every time
you recurse into a new stacking context, and pop-and-blend every time
you return from a child stacking context to its parent.

[stacking-context]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Positioning/Understanding_z_index/The_stacking_context

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
sticky-positioned elements also form a stacking context because of
their interaction with scrolling.
:::

[^also-containing-block]: While we're at it, perhaps scrollable
elements should also be a [containing block][containing-block] for
descendants. Otherwise, a scrollable element can have non-scrolling
children via properties like `position`. This situation is very
complicated to handle in real browsers.

[containing-block]: https://developer.mozilla.org/en-US/docs/Web/CSS/Containing_block

Compositing and Alpha
=====================

[canvas]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/canvas
[webgl]: https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API
[webassembly]: https://developer.mozilla.org/en-US/docs/WebAssembly
[canvaskit]: https://skia.org/docs/user/modules/canvaskit/

Color mixing happens when multiple page elements overlap. The easiest
way that happens in our browser is child elements overlapping their
parents, like this:[^transforms-etc]

[^transforms-etc]: There are way more ways elements can overlap in a
real browser: the `transform` property, `position`ed elements,
negative margins, and so many more. But color mixing works the same
way each time.

``` {.html.example}
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
one; The two colors don't really need to "mix", and in fact it kind of
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

``` {.python.example}
# draw parent
canvas.saveLayer(paint=skia.Paint(Alphaf=0.5))
# draw child
canvas.restore()
```

We first draw the parent, then create a new surface with `saveLayer`
to draw the child into, and then when the `restore` call is made the
`paint` parameters passed into `saveLayer` are used to mix the colors
in the two surfaces together. Here we're using the `Alphaf` parameter,
which describes the alpha as a floating-point number.

Note that `saveLayer` and `restore` are like a pair of parentheses
enclosing the child drawing operations. This means our display list is
no longer just a linear sequence of drawing operations, but a tree.
The `SaveLayer` drawing operation reflects this by taking a sequence
of other drawing commands as an argument:

``` {.python expected=False}
class SaveLayer:
    def __init__(self, sk_paint, cmds):
        self.sk_paint = sk_paint
        self.cmds = cmds

    def execute(self, scroll, canvas):
        canvas.saveLayer(paint=self.sk_paint)
        for cmd in self.cmds:
            cmd.execute(scroll, canvas)
        canvas.restore()
```

Now let's look at how we can add this to our existing `paint` method
for `BlockLayout`s. Right now, this method draws a background and then
recurses into its children, adding each drawing command straight to
the global display list. Let's instead add those drawing commands to a
temporary list first:

``` {.python expected=False}
class BlockLayout:
    def paint(self, display_list):
        cmds = []

        # ...
        if bgcolor != "transparent":
            cmds.append(DrawRect(rect, bgcolor))

        for child in self.children:
            child.paint(cmds)
        # ...        
        display_list.extend(cmds)
```

Now, _before_ we add our temporary command list to the overall display
list, we can use `SaveLayer` to add transparency to the whole element.
I'm going to do this in a new `paint_visual_effects` method, because
we'll want to make the same changes to all of our other layout
objects:

``` {.python}
class BlockLayout:
    def paint(self, display_list):
        # ...
        cmds = paint_visual_effects(self.node, cmds, rect)
        display_list.extend(cmds)
```

Inside `paint_visual_effects`, we'll parse the opacity value and
construct the appropriate `SaveLayer`:

``` {.python expected=False}
def paint_visual_effects(node, cmds, rect):
    opacity = float(node.style.get("opacity", "1.0"))

    return [
        SaveLayer(skia.Paint(Alphaf=opacity), cmds),
    ]
```

Note that `paint_visual_effects` receives a list of commands and
returns another list of commands. It's just that the output list is
always a single `SaveLayer` command that wraps the original content---which makes sense, because
first we need to draw the commands to a surface, and *then* apply transparency to it when blending into
the parent.

Compositing Pixels
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

That `Alphaf` operation applies to pixels in one surface. But with
`SaveLayer` we will end up with two surfaces, with all of their pixels
aligned, and therefore we will need to combine, or *blend* pairs of
corresponding pixels.

Here the terminology can get confusing: we imagine that the pixels "on
top" are blending into the pixels "below", so we call the top surface
the *source surface*, with source pixels, and the bottom surface the
*destination surface*, with destination pixels. When we combine them,
there are lots of ways we could do it, but the default on the web is
called "simple alpha compositing" or *source-over* compositing. In
Python, the code to implement it looks like this:[^simple-alpha]

[^simple-alpha]: The formula for this code can be found
[here](https://www.w3.org/TR/SVG11/masking.html#SimpleAlphaBlending).
Note that that page refers to *premultiplied* alpha colors, but Skia's API
does not use premultiplied representations, and the code below doesn't either.


``` {.python file=examples}
class Pixel:
    def source_over(self, source):
        self.a = 1 - (1 - source.a) * (1 - self.a)
        self.r = \
            (self.r * (1 - source.a) * self.a + \
                source.r * source.a) / self.a
        self.g = \
            (self.g * (1 - source.a) * self.a + \
                source.g * source.a) / self.a
        self.b = \
            (self.b * (1 - source.a) * self.a + \
                source.b * source.a) / self.a
```

Here the destination pixel `self` is modified to blend in the source
pixel `source`. The mathematical expressions for the red, green, and
blue color channels are identical, and basically average the source
and destination colors, weighted by alpha.[^source-over-example] You
might imagine the overall operation of `SaveLayer` with an `Alphaf`
parameter as something like this:

[^source-over-example]: For example, if the alpha of the source pixel
    is 1, the result is just the source pixel color, and if it is 0
    the result is the backdrop pixel color.

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

``` {.html.example}
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
    destination[x, y].difference(source[x, y])
    destination[x, y].source_over(source[x, y])
```

[wiki-blend-mode]: https://en.wikipedia.org/wiki/Blend_modes

[dodge-burn]: https://en.wikipedia.org/wiki/Dodging_and_burning

Skia supports the [multiply][mbm-mult] and [difference][mbm-diff]
blend modes natively:

``` {.python}
def parse_blend_mode(blend_mode_str):
    if blend_mode_str == "multiply":
        return skia.BlendMode.kMultiply
    elif blend_mode_str == "difference":
        return skia.BlendMode.kDifference
    else:
        return skia.BlendMode.kSrcOver
```

This makes adding support for blend modes to our browser as simple as
passing the `BlendMode` parameter to the `Paint` object:

``` {.python expected=False}
def paint_visual_effects(node, cmds, rect):
    # ...
    blend_mode = parse_blend_mode(node.style.get("mix-blend-mode"))
    
    return [
        SaveLayer(skia.Paint(BlendMode=blend_mode), [
            SaveLayer(skia.Paint(Alphaf=opacity), cmds),
        ]),
    ]
```

Note the order of operations here: we _first_ apply transparency, and
_then_ blend the result into the rest of the page. If we switched the
two `SaveLayer` calls, so that we first applied blending, there
wouldn't be anything to blend it into!

[mbm-mult]: https://drafts.fxtf.org/compositing-1/#blendingmultiply
[mbm-diff]: https://drafts.fxtf.org/compositing-1/#blendingdifference

::: {.further}
In reality, reading individual pixels into memory to manipulate them
like this is slow. Instead, it should be done on the GPU. So libraries
such as Skia don't make it convenient to do so. (Skia canvases do have
`peekPixels` and `readPixels` methods that are sometimes used, but not
for this use case).

Many graphics libraries, Skia included, don't usually represent a separate alpha
channel internally , and instead multiply the color channels by the opacity,
which is called a *premultiplied* representation of the color. Premultiplied
pixel representations of colors are generally more efficient. For example,
observe that `source_over` has to divide by `self.a` at the end, because
otherwise the result would be premultiplied. If we stuck with premultiplied
throughout, this would not be necessary.

There are also in fact a few Skia APIs that expose premultiplied colors:
You can create images from blocks of them and read them back from surfaces,
for example.
:::

::: {.further}
Check out this [history of alpha][alpha-history],
written by its co-inventor (and co-founder of Pixar), or read this
[derivation of alpha][alpha-deriv] for how it is computed.
:::

[alpha-history]: http://alvyray.com/Memos/CG/Microsoft/7_alpha.pdf
[alpha-deriv]: https://jcgt.org/published/0004/02/03/paper.pdf

Clipping and masking
====================

The "multiply" and "difference" blend modes can seem kind of obscure,
but blend modes are a flexible way to implement per-pixel operations.
One common use case is clipping---erasing the pixels in a surface that
don't intersect with a given shape. It's called clipping because it's
like putting a second piece of paper (called a *mask*) over the first
one, and then using scissors to cut along the mask's edge.

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
    but subtly different from `overflow: clip`.

[mdn-mask]: https://developer.mozilla.org/en-US/docs/Web/CSS/mask

[mdn-clip-path]: https://developer.mozilla.org/en-US/docs/Web/CSS/clip-path

Usually, `overflow: clip` is used with properties like `height` or
`rotate` which can make an element's children poke outside their
parent. Our browser doesn't support these, but there is one edge case
where `overflow: clip` is relevant: with rounded corners. Consider
this example:

``` {.html.example}
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

Look at how the letters near the corner are cut off to maintain a
sharp rounded edge. (Uhh... actually, at the time of this writing,
Safari does not support `overflow: clip`, so if you're using Safari
you won't see this effect.[^hidden]) That's clipping; without the
`overflow:clip` property these letters would instead be fully drawn.

[^hidden]: Other values of `overflow`, such as `hidden`, are supported by
all browsers. However, if you change to this value in a real browser, you'll
notice that the height of the blue box increases, and the rounded corners
no longer clip out the text. This is because `overflow:hidden` has different
rules for sizing boxes, having to do with the possibility of the child content
being scrolled (`hidden` means "clipped, but might be scrolled by JavaScript").
If the blue box had not been taller, than it would have been impossible to
see the text, which is really bad if it's intended that there should be a way
to scroll it onscreen.

Counterintuitively, we'll implement clipping using blending modes.
We'll make a new surface (the mask), draw a rounded rectangle into it,
and then blend it with the element contents. But we want to see the
element contents, not the mask, so when we do this blending we will
use *destination-in* compositing.

[Destination-in compositing][dst-in] basically means keeping the
pixels of the destination surface that intersect with the source
surface. The source surface's color is not used---just its alpha. In
our case, the source surface is the circular mask and the destination
surface is the content we want to clip, so destination-in fits
perfectly. In code, destination-in looks like this:

[dst-in]: https://drafts.fxtf.org/compositing-1/#porterduffcompositingoperators_dstin

``` {.python file=examples}
class Pixel:
    def destination_in(self, source):
        self.r = self.r * self.a * source.a
        self.g = self.g * self.a * source.a
        self.b = self.b * self.a * source.a
        self.a = self.a * source.a
```

Now, in `paint_visual_effects`, we need to create a new layer, draw
the mask image into it, and then blend it with the element contents
with destination-in blending:

``` {.python expected=False}
def paint_visual_effects(node, cmds, rect):
    # ...
    border_radius = float(node.style.get("border-radius", "0px")[:-2])
    if node.style.get("overflow", "visible") == "clip":
        clip_radius = border_radius
    else:
        clip_radius = 0


    return [
        SaveLayer(skia.Paint(BlendMode=blend_mode), [
            SaveLayer(skia.Paint(Alphaf=opacity), cmds),
            SaveLayer(skia.Paint(BlendMode=skia.kDstIn), [
                DrawRRect(rect, clip_radius, skia.ColorWHITE)
            ]),
        ]),
    ]
```

Note that after drawing all of the element contents with `cmds` (and
applying opacity), this code then draws a rounded rectangle on another
layer to serve as the mask, and uses destination-in blending to clip
the element contents. Here I chose to draw the rounded rectangle in
white, but the color doesn't matter as long as it's opaque. On the
other hand, if there's no clipping, I don't round the corners of the
mask, which means nothing is clipped off.

Notice how similar this masking technique is to the physical analogy
with scissors described earlier, with the two layers playing the role
of two sheets of paper and destination-in compositing playing the role
of the scissors. This implementation technique for clipping is called
*masking*, and it is very general---you can use it with arbitrarily
complex mask shapes, like text, bitmap images, or anything else you
can imagine.

Optimizing Surface Use
======================

Our browser now works correctly, but uses way too many surfaces. For example,
for a single, no-effects-needed div with some text content, there are currently
18 surfaces allocated in the display list. For that example, we should need
only one!

It's pretty easy to fix this situation. Let's review the full list of surfaces
that can be needed for an element, and then devise logic to omit them when
not needed:

* *Blending/isolation*: the top-level surface returned by
`paint_visual_effects`. It's used to apply any blend mode other than
source-over, and also to isolate the element from other parts of the page before
applying an overflow clip.

* *Opacity*: the first nested surface within the blending/isolation
surface, used for applying opacity transparency.

* *Clipping*: the second nested surface, used to implement
overflow clipping.

We can skip each of the above surfaces if the conditions mentioned don't hold.
Implement that logic by changing `SaveLayer` to take two additional optional
parameters: `should_paint` and `should_paint_cmds`. These control whether
`saveLayer/restore`, and execution of the `cmds` parameter, actually happen
during `execute`:

``` {.python}
class SaveLayer:
    def __init__(self, sk_paint, cmds, should_save=True,
        should_paint_cmds=True):
        self.should_save = should_save
        self.should_paint_cmds = should_paint_cmds
        # ...

    def execute(self, canvas):
        if self.should_save:
            canvas.saveLayer(paint=self.sk_paint)
        if self.should_paint_cmds:
            for cmd in self.cmds:
                cmd.execute(canvas)
        if self.should_save:
            canvas.restore()
```

Now set those parameters via some simple logic:

``` {.python expected=False}
def paint_visual_effects(node, cmds, rect):
    # ...

    needs_clip = node.style.get("overflow", "visible") == "clip"
    needs_blend_isolation = blend_mode != skia.BlendMode.kSrcOver or \
        needs_clip
    needs_opacity = opacity != 1.0

   return [
        SaveLayer(skia.Paint(BlendMode=blend_mode), [
            SaveLayer(skia.Paint(Alphaf=opacity), cmds,
                should_save=needs_opacity),
            SaveLayer(skia.Paint(BlendMode=skia.kDstIn), [
                DrawRRect(rect, clip_radius, skia.ColorWHITE)
            ], should_save=needs_clip, should_paint_cmds=needs_clip),
        ], should_save=needs_blend_isolation),
    ]
```

With these changes, the example I mentioned above goes from 18 to 1 surface.

You might wonder if we can save even more surfaces. For example, what if there
is a blend mode and opacity at the same time, can we use the same surface?
Indeed, yes you can! That's also pretty simple:

``` {.python expected=False}
def paint_visual_effects(node, cmds, rect):
    # ...

    needs_clip = node.style.get("overflow", "visible") == "clip"
    needs_blend_isolation = blend_mode != skia.BlendMode.kSrcOver or \
        needs_clip
    needs_opacity = opacity != 1.0

   return [
        SaveLayer(skia.Paint(BlendMode=blend_mode, Alphaf=opacity), [
            cmds,
            SaveLayer(skia.Paint(BlendMode=skia.kDstIn), [
                DrawRRect(rect, clip_radius, skia.ColorWHITE)
            ], should_save=needs_clip, should_paint_cmds=needs_clip),
        ], should_save=needs_blend_isolation or needs_opacity),
    ]
```

There's one more important optimization to make: getting rid of the
destination-in compositing surface for rounded corners. While this approach
works just fine, and is a good idea for general masks, rounded corners are
so common on the web that Skia has a special `clipRRect` command just for this
use case.

There are multiple advantages to using `clipRRect` over an explicit
destination-in surface. First, it allows Skia to internally optimize away even
more surfaces in common situations, replacing them with an equivalent
implementation directly on the GPU, via a shader.[^shader-rounded] Second,
`clipRRect` makes it much easier for Skia to skip subsequent draw operations
that don't intersect the rounded rectangle,[^see-chap-1] or dynamically draw
only the parts of commands that intersect it.

[^shader-rounded]: GPU programs are out of scope for this book, but if you're
curious there are many online resources describing ways to to do this. Skia
of course also has an implementation in its GPU-accelerated code paths.

[^see-chap-1]: This is basically the same optimization we added in Chapter
1 to avoid painting offscreen text.

To use `clipRect`, we'll also need another method: `save`. Once you call a
method like `clipRect`, all subsequent canvas commands are clipped, until you
tell Skia to stop. The way to make it stop is with `save` and `restore`---you
call `save` before calling `clipRect`, and `restore` after finishing drawing
the commands that should be clipped. `save` means "snapshot the current clip
state of the canvas", and `restore` rolls back to the most recent snapshot.

You've probably noticed that `restore` is used for both saving state and pushing
surfaces---what gives? That's because there is a combined stack of surfaces and
state in the Skia API. However, `save` never creates a new surface, so 
you should use it whenever possible over `saveLayer`.

Using `clipRRect` is pretty easy. It needs to be preceded by `save`, because
once the clip has been set, all subsequent canvas are clipped until `restore`
is called. The general pattern is:

``` {.example}
    canvas.save()
    canvas.clipRRect(rounded_rect)
    # Draw commands that should be clipped...
    canvas.restore()
```

To implement, first add a `ClipRRect` display list command. It should take a
`should_clip` parameter indicating whether the clip is necessary (just like the
optimization we made above for `SaveLayer`). It also includes a call to `save`
and `restore`, since you should not clip without a `save`/`restore` pair.
[^save-clip]

[^save-clip]: Well, unless you're doing two clips at once, or a clip and a
transform, or some other more complex setup that would benefit from only
saving once but doing multiple things inside it.

``` {.python}
class ClipRRect:
    def __init__(self, rect, radius, cmds, should_clip=True):
        self.rect = rect
        self.radius = radius
        self.cmds = cmds
        self.should_clip = should_clip

    def execute(self, canvas):
        if self.should_clip:
            canvas.save()
            if self.radius > 0.0:
                rect = canvas.clipRRect(skia.RRect.MakeRectXY(
                    skia.Rect.MakeLTRB(
                        self.rect.left(),
                        self.rect.top(),
                        self.rect.right(),
                        self.rect.bottom()),
                    self.radius, self.radius))
            else:
                rect = canvas.clipRect(self.rect)

        for cmd in self.cmds:
            cmd.execute(canvas)

        if self.should_clip:
            canvas.restore()
```

Then use them in `paint_visual_effects`:

``` {.python}
def paint_visual_effects(node, cmds, rect):
    # ...
    return [
        SaveLayer(skia.Paint(BlendMode=blend_mode, Alphaf=opacity), [
            ClipRRect(rect, clip_radius, cmds, should_clip=needs_clip)
            ],
            should_save=needs_blend_isolation),
    ]
```

That's it! Everything should look visually the same, but will be faster and use
less memory.

::: {.further}

Rounded corners have an interesting history in computing. Their
[inclusion][mac-story] into the original Macintosh is a fun story to read, and
also demonstrates how computers often end up echoing reality. It also reminds us
of just how hard it was to implement features that appear simple to us today,
due to the very limited memory, and lack of hardware floating-point arithmetic,
of early personal computers (here's some [example source code][quickdraw] used
on early Macintosh computers to implement this feature).

Later on, floating-point coprocessors, and then over time GPUs, became standard
equipment on new computers. This made it much easier to implement fast rounded
corners. Unfortunately, the `border-radius` CSS property didn't appear in
browsers until around 2010 (but that didn't stop web developers from putting
rounded corners on their sites before then!). There are a number of clever ways
to do it even without `border-radius`; [this video][rr-video] walks through
several.

It's a good thing `border-radius` is now a fully supported browser feature,
and not just because it saves developers a lot of time and effort.
More recently, the introduction of complex, mix-and-match, hardware-accelerated
animations of visual effects, multi-process compositing, and
[hardware overlays][hardware-overlays] have made the task of rounded corners
harder---certainly way beyond the ability of web developers to polyfill.
In today's browsers there is a fast path to clip to rounded corners on the GPU
without using any more memory, but this fast path can fail to apply for
cases such as hardware video overlays and nested rounded corner clips. With
a polyfill, the fast path would never occur, and complex visual effects combined
with rounded corners would be infeasible.
:::

[mac-story]: https://www.folklore.org/StoryView.py?story=Round_Rects_Are_Everywhere.txt
[quickdraw]: https://raw.githubusercontent.com/jrk/QuickDraw/master/RRects.a
[hardware-overlays]: https://en.wikipedia.org/wiki/Hardware_overlay
[rr-video]: https://css-tricks.com/video-screencasts/24-rounded-corners/

Browser compositing
===================

Optimizing away surfaces is great when they're not needed, but they have
even more uses than blending---they can be used to efficiently scroll and animate
as well.

Chapter 2 introduced the Tkinter canvas associated with the browser window.
Chapter 7 added in browser chrome, also drawing to the same canvas. Any time
anything changed, we had to clear the canvas and paint & raster everything from
scratch. This is inefficient---ideally, pixels should be re-rastered only if
their colors actually change, and pixels that "move around" on the screen, such
as with scrolling, should not need re-raster either. When context is complex or
the screen is large, the slowdown becomes visible, and laptop and mobile
batteries are drained unnecessarily.

Real browsers optimize these situations by using a technique I'll call
*browser compositing*. The idea is to create a tree of explicitly cached
 surfaces for different pieces of content. Whenever content needs to re-raster,
 we'll re-raster only the surface for that content, and then draw the entire
 tree to the screen. For example, if we had a surface for browser chrome and a
 surface for the `Tab`'s contents, we'd only need to re-raster the `Tab`
 surface if page contents needed update, and vice-versa. This technique
 also allows us to scroll the `Tab` without any raster at all---we can just
 apply an adjusted transform on the surface when drawing it.

Let's see how to implement this with Skia. We'll store two new surfaces on
`Browser`: `chrome_surface` and `tab_surface`.[^multiple-tabs] These will
raster independently, in a new `raster` method on `Browser` and `Tab`, and draw
into `root_surface` with the `skia.Surface.draw` method, via a renamed `draw`
method on `Browser` (what used to be called `draw_to_screen`.

[^multiple-tabs]: We could even store a different surface for each `Tab`; this
would make switching between tabs faster. Real browsers don't do this, however,
since storing the pixels for a surface uses up a lot of memory, and raster is
fast enough on today's computers that switching between tabs is already quite
fast, compared with a human's typical ability to detect a delay in responding
to a click.

Implement modifications to `draw` first.  A call to the `translate` and
`clipRect` methods on the canvas for `root_surface` first shifts the
`tab_surface` down by `CHROME_PX` and up by `-scroll`, then clips it to only
the area of the window that doesn't overlap the browser chrome. Then
`chrome_surface` is drawn, with a clip to also ensure it doesn't exceed its
bounds.

``` {.python}
class Browser:
    def draw(self):
        root_canvas = self.root_surface.getCanvas()
        root_canvas.clear(skia.ColorWHITE)
        
        root_canvas.save()
        root_canvas.clipRect(skia.Rect.MakeLTRB(
            0, CHROME_PX, WIDTH, HEIGHT))
        root_canvas.translate(
            0, CHROME_PX- self.tabs[self.active_tab].scroll)
        self.tab_surface.draw(root_canvas, 0, 0)
        root_canvas.restore()

        root_canvas.save()
        root_canvas.clipRect(skia.Rect.MakeLTRB(
            0, 0, WIDTH, CHROME_PX))
        self.chrome_surface.draw(root_canvas, 0, 0)
        root_canvas.restore()

        # ...
```

Next up are the changes to introduce `raster`; this is mainly a refactoring
and rename of the method previously called `draw`. The only
new tricky part is the need to make sure that `tab_surface` is large enough
to contain all of the web page contents.[^really-big-surface]

[^really-big-surface]: For a very big web page, this means `tab_surface` can be
much larger than the size of the SDL window, and therefore take up a very large
amount of memory. We'll ignore that, but a real browser would not. They
only paint and raster surface content up to a certain distance from
the visible region. and re-paint/raster as necessary as surfaces move around.

``` {.python}
class Browser:
        def raster(self):
        active_tab = self.tabs[self.active_tab]

        # Re-allocate the tab surface if its size changes.
        tab_bounds = active_tab.display_list_bounds()
        assert tab_bounds.top() >= 0
        assert tab_bounds.left() >= 0
        if not self.tab_surface or \
                tab_bounds.bottom() != self.tab_surface.height() or \
                tab_bounds.right() != self.tab_surface.width():
            self.tab_surface = skia.Surface(
                tab_bounds.right(),
                tab_bounds.bottom())

        tab_canvas = self.tab_surface.getCanvas()
        tab_canvas.clear(skia.ColorWHITE)
        active_tab.raster(tab_canvas)

        self.raster_browser_chrome()

    def raster_browser_chrome(self):
        canvas = self.chrome_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
    
        # Draw the tabs UI:
        # ...
```

On `Tab`, there are two changes other than renaming `draw` to `raster`: first,
we no longer need to pass around the scroll offset to the `execute`
methods, or account for `CHROME_PX`:[^why-no-scroll]

[^why-no-scroll]: Previously, we had baked the scroll offset into the display
list, which is why it had to be re-painted on every scroll. Now we only need
to re-run draw, and the code here is simpler than before!

``` {.python}
class Tab:
    def raster(self, canvas):
        for cmd in self.display_list:
            cmd.execute(canvas)

        if self.focus:
            obj = [obj for obj in tree_to_list(self.document, [])
                   if obj.node == self.focus][0]
            text = self.focus.attributes.get("value", "")
            x = obj.x + obj.font.measureText(text)
            y = obj.y
            draw_line(canvas, x, y, x, y + obj.height)
```

Likewise, each of the display list commands should have the `scroll` parameter
removed from their `execute` methods. Here's `DrawRect`, for example:

``` {.python}
class DrawRect:
    def execute(self, canvas):
        draw_rect(canvas,
            self.left, self.top,
            self.right, self.bottom,
            fill=self.color, width=0)
```

The second is the new `display_list_bounds` method,
which is used to determine the size of `tab_surface`:

``` {.python}
class Tab:
    def display_list_bounds(self):
        bounds = skia.Rect()
        for cmd in self.display_list:
            bounds.join(cmd.rect)
        return bounds.roundOut()
```

As far as implementing the concept of browser-surface composited scrolling goes,
we're done. But to get the desired performance in reality, we'd need to avoid
`paint` and `raster` when they aren't needed, and also run on a second CPU
thread. That isn't too hard either, but let's leave that for exercises and the
next chapter.

::: {.further}
In terms of conceptual phases of execution, our browser is now very close to
real browsers: real browsers paint display lists, break content up into
different rastered surfaces, and finally draw the tree of surfaces to the
screen. We only did it for browser chrome vs web content, but browsers allocate
new surfaces for various different situations, such as implementing accelerated
overflow scrolling and animations of certain CSS properties such as
[transform][transform-link] and opacity that can be done without raster.

In addition, real browsers use *tiling* to solve the problem of surfaces getting
too big, or the desire to only re-raster the parts that actually changed
(instead of the whole surface, like our browser does). As you might guess from
the name, the surface is broken up into a grid of tiles which have their own
raster surfaces. Whenever content that intersects a tile changes its display
list, the tile is re-rastered. Tiles are draw into their parent surface with
an x and y offset according to their position in the grid. Tiles that are not
on or "near"^[For example, scrolled just offscreen.] the screen are not rastered
at all.

Finally, all of this lends itself naturally to hardware acceleration with a GPU,
since surfaces (Skia ones [in particular][gpu-surface]) can be easily
represented on the GPU, making the execution of `draw` extremely efficent.
:::

[gpu-surface]: https://kyamagu.github.io/skia-python/reference/skia.Surface.html

[transform-link]: https://developer.mozilla.org/en-US/docs/Web/CSS/transform

::: {.further}
Scrolling of arbitray DOM elements is possible via the
[`overflow`][overflow-prop] CSS propery, and in particular `overflow:scroll`.
This value means, of course, for the browser to allow the user to scroll
the content in order to see it; the parts that don't currently overlap the 
clipping element are clipped out.

Basic scrolling for DOM elements is very similar to what we've just implemented.
But implementing it in its full generality, and with excellent performance,
is *extremely* challenging. Scrolling is probably the single most complicated
feature in a browser rendering engine. The corner cases and subtleties involved
are almost endless.
:::

[overflow-prop]: https://developer.mozilla.org/en-US/docs/Web/CSS/overflow


Summary
=======

So there you have it: our browser can draw not only boring
text and boxes but also:

- Partial transparency via an alpha channel
- User-configurable blending modes via `mix-blend-mode`
- Rounded rectangle clipping via destination-in blending or direct clipping
- Optimizations to avoid surfaces when possible
- Surfaces for scrolling and animations

Besides the new features, we've upgraded from Tkinter to SDL and Skia,
which makes our browser faster and more responsive, and also sets a
foundation for more work on browser performance to come.

::: {.further}
[This blog post](https://ciechanow.ski/alpha-compositing/) gives a really nice
visual overview of many of the same concepts explored in this chapter,
plus way more content about how a library such as Skia might implement features
like raster sampling of vector graphics for lines and text, and interpolation
of surfaces when their pixel arrays don't match resolution or orientation. I
highly recommend it.
:::


Outline
=======

The complete set of functions, classes, and methods in our browser 
should now look something like this:

::: {.cmd .python .outline html=True}
    python3 infra/outlines.py --html src/lab11.py
:::

Exercises
=========

*CSS transforms*: Add support for the [transform][transform-css] CSS
property, specifically the `translate` and `rotate` transforms.[^3d]
Skia has built-in support for these via canvas state.

[transform-css]: https://developer.mozilla.org/en-US/docs/Web/CSS/transform

[^3d]: There is a lot more complexity to 3D transforms
having to do with the definition of 3D spaces, flatting, backfaces, and plane
intersections.

*Filters*: The `filter` CSS property allows specifying various kinds
of more [complex effects][filter-css], such as grayscale or blur.
These are fun to implement, and a number of them have built-in support
in Skia. Implement, for example, the `blur` filter. Think carefully
about when filters occur, relative to other effects like transparency,
clipping, and blending.

[filter-css]: https://developer.mozilla.org/en-US/docs/Web/CSS/filter

*Hit testing*: If you have an element with a `border-radius`, it's
possible to click outside the element but inside its containing
rectangle, by clicking in the part of the corner that is "rounded
off". This shouldn't result in clicking on the element, but in our
browser it currently does. Modify the `click` method to take border
radii into account.

*Interest region*: Our browser now draws the whole web page to a
single surface, and then shows parts of that surface as the user
scrolls. That means a very long web page (like this one!) can create a
large surface, thereby using a lot of memory. Modify the browser so
that the size of that surface is limited, say to `4 * HEIGHT` rows.
The (limited) region of the page drawn to this surface is called the
interest region; you'll need to track what part of the interest region
is being shown on the screen, and re-raster the interest region when
the user attempts to scroll outside of it.

*Z-index*: Right now, elements later in the HTML document are drawn
"on top" of earlier ones. The `z-index` CSS property changes that
order: an element with the larger `z-index` draws on top (with ties
broken by the current order, and with the default `z-index` being 0).
For `z-index` to have any effect, the element's `position` property
must be set to something other than `static` (the default). Add
support for `z-index`. One thing you'll run into is that with our
browser's minimal layout features, you might not be able to *create*
any overlapping elements to test this feature! However, lots of
exercises throughout the book allow you to create overlapping
elements, including `transform` and `width`/`height`. For an extra
challenge, add support for [nested elements][stacking-context] with
`z-index` properties.

[stacking-context]:  https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Positioning/Understanding_z_index/The_stacking_context


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
