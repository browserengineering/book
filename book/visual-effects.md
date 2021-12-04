---
title: Adding Visual Effects
chapter: 12
prev: security
next: rendering-architecture
...

Right now our browser's visual capabilities are pretty boring, just
colored rectangles and text. Real browsers, one the other hand,
support all kinds of *visual effects* that affect how elements look.
Before we add these to our browser, we'll need to learn a bit about
pixels, colors, and blending on computer screens. We'll then be able
to implement these effects using the Skia graphics library, and you'll
see a bit of how Skia is implemented under the hood.

Installing Skia and SDL
=======================

Before we get any further, we'll need to upgrade our graphics system.
While Tkinter is great for basic shapes and handling input, it lacks
built-in visual effects routines.[^tkinter-before-gpu] Implementing
fast visual effects routines is fun, but it's outside the scope of
this book, so we need a new graphics library. Let's use [Skia][skia],
the library that Chromium uses. Unlike Tkinter, Skia doesn't handle
inputs or create graphical windows, so we'll pair it with the
[SDL][sdl] GUI library. We'll also add the [Pillow][pillow] library
for handling images.

[skia]: https://skia.org
[sdl]: https://www.libsdl.org/
[pillow]: https://python-pillow.org

[^tkinter-before-gpu]: That's because Tk, the graphics library that
Tkinter uses, dates from the early 90s, before high-performance
graphics cards and GPUs became widespread.

Start by installing [Pillow][install-pillow], [Skia][skia-python], and
[SDL][sdl-python]:

    pip3 install skia-python pysdl2 pysdl2-dll pillow

[skia-python]: https://github.com/kyamagu/skia-python
[sdl-python]: https://pypi.org/project/PySDL2/
[install-pillow]: https://pillow.readthedocs.io/en/stable/installation.html

::: {.install}
As elsewhere in this book, you may need to use `pip`, `easy_install`,
or `python3 -m pip` instead of `pip3` as your installer, or use your
IDE's package installer. If you're on Linux, you'll need to install
additional dependencies, like OpenGL and fontconfig. Also, you may not be
able to install `pysdl2-dll`; you'll need to find SDL in your system
package manager instead. Consult the [`pillow`][install-pillow],
[`skia-python`][skia-python], and [`pysdl2`][sdl-python] web pages for
more details.
:::

Once installed, remove `tkinter` from your Python imports and replace them with:

``` {.python}
import ctypes
import sdl2
import skia
import PIL.Image
```

If any of these imports fail, you probably need to check that Skia and
SDL were installed correctly. Note that the `ctypes` module comes
standard in Python; it helps convert between Python and C types.

SDL replaces Tkinter
====================

The main loop of the browser first needs some boilerplate to get SDL
started:

``` {.python}
if __name__ == "__main__":
    import sys
    sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
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
"surface" for it:[^surface]

[^surface]: In Skia and SDL, a *surface* is a representation of a
graphics buffer into which you can draw "pixels" (bits representing
colors). A surface may or may not be bound to the actual pixels on the
screen via a window, and there can be many surfaces. A *canvas* is an
API interface that allows you to draw into a surface with higher-level
commands such as for rectangles or text. Our browser uses separate
Skia and SDL surfaces for simplicity, but in a highly optimized
browser, minimizing the number of surfaces is important for good
performance.


``` {.python}
class Browser:
    def __init__(self):
        self.skia_surface = skia.Surface(WIDTH, HEIGHT)
```

Typically, we'll draw to the Skia surface, and then once we're done
with it we'll copy it to the SDL surface to display on the screen.
This looks a little hairy but really it's just copying pixels from one
place to another:

``` {.python}
class Browser:
    def draw_to_screen(self):
        # Raster the results and copy to the SDL surface:
        skia_image = self.skia_surface.makeImageSnapshot()
        skia_bytes = skia_image.tobytes()
        rect = sdl2.SDL_Rect(0, 0, WIDTH, HEIGHT)

        depth = 32 # 4 bytes per pixel
        pitch = 4 * WIDTH # 4 * WIDTH pixels per line on-screen
        # Skia uses an ARGB format - alpha first byte, then
        # through to blue as the last byte.
        alpha_mask = 0xff000000
        red_mask = 0x00ff0000
        green_mask = 0x0000ff00
        blue_mask = 0x000000ff
        sdl_surface = sdl2.SDL_CreateRGBSurfaceFrom(
            skia_bytes, WIDTH, HEIGHT, depth, pitch,
            red_mask, green_mask, blue_mask, alpha_mask)

        window_surface = sdl2.SDL_GetWindowSurface(self.sdl_window)
        sdl2.SDL_BlitSurface(sdl_surface, rect, window_surface, rect)
        sdl2.SDL_UpdateWindowSurface(self.sdl_window)
```

SDL doesn't have a `mainloop` or `bind` method; we have to implement
it ourselves:

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

Skia replaces Tkinter
=====================

Now our browser is creating an SDL window can draw to it via Skia. But
most of the browser codebase is still using Tkinter drawing commands,
which we now need to replace. Skia is a bit more verbose than Tkinter,
so let's abstract over some details with helper functions.[^skia-docs]
First, a helper function to convert colors to Skia colors:

[^skia-docs]: Consult the [Skia][skia] and [Skia-Python][skia-python]
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

Finally, for drawing rectangles we use `drawRect`:

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

``` {.python}
class DrawText:
    def execute(self, scroll, canvas):
        draw_text(canvas, self.left, self.top - scroll,
            self.text, self.font)

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

``` {.python}
class Browser:
    def draw(self):
        canvas = self.skia_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)

        self.tabs[self.active_tab].draw(canvas)
```

Then draw the browser UI elements. First, the tabs:

``` {.python}
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

``` {.python}
class Browser:
    def draw(self):
        # ...
        buttonfont = skia.Font(skia.Typeface('Arial'), 30)
        draw_rect(canvas, 10, 10, 30, 30)
        draw_text(canvas, 11, 4, "+", buttonfont)
```

Then the address bar, including text and cursor:

``` {.python}
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

``` {.python}
class Browser:
    def draw(self):
        # ...
        draw_rect(canvas, 10, 50, 35, 90)
        path = skia.Path().moveTo(15, 70).lineTo(30, 55).lineTo(30, 85)
        paint = skia.Paint(Color=skia.ColorBLACK, Style=skia.Paint.kFill_Style)
        canvas.drawPath(path, paint)
```

Once this is done, we need to copy from the Skia surface to the SDL window:

``` {.python}
class Browser:
    def draw(self):
        # ...
        self.draw_to_screen()
```

We've only got a few minor changes left elsewhere in the browser.
`Tab` also has a `draw` method and draws a cursor; it needs to use
`draw_line` for that:

``` {.python}
class Tab:
    def draw(self, canvas):
        if self.focus:
            # ...
            x = obj.x + obj.font.measureText(text)
            y = obj.y - self.scroll + CHROME_PX
            draw_line(canvas, x, y, x, y + obj.height)
```

Note that I've also replaced Tkinter's `measure` call with Skia's
`measureText` equivalent. We'll also need to create Skia fonts instead
of Tkinter ones. Update all the other places that `measure` was called
to use `measureText`. We also need to change everywhere `metrics` is
called to instead use Skia's `getMetrics`, which works a little
differently. In Skia, ascent and descent are accessible via:

``` {.python expected=False}
    -font.getMetrics().fAscent
```

and

``` {.python expected=False}
    font.getMetrics().fDescent
```

Note the negative sign when accessing the ascent. In Skia, ascent and
descent positive if they go downward and negative if they go upward,
so ascents will normally be negative, the opposite of Tkinter.

You should now be able to run the browser again. It should look and
behave just as it did in previous chapters, and it'll probably feel
faster, because Skia and SDL are faster than Tkinter.

::: {.further}
Implementing high-quality raster libraries is very interesting in its own
right. These days, it's especially important to leverage GPUs when
they're available, and browsers often push the envelope. Browser teams
typically include raster library experts: Skia for Chromium and [Core
Graphics][core-graphics] for Webkit, for example. Both of these
libraries are used outside of the browser, too: Core Graphics in iOS
and macOS, and Skia in Android.
:::

[core-graphics]: https://developer.apple.com/documentation/coregraphics

Pixels, Color, Raster
=====================

Skia, like the Tkinter canvas we've been using until now, is a
_rasterization_ library: it converts shapes like rectangles and text
into pixels. Before we move on to Skia's advanced features, let's look
at how rasterization works at a deeper level.

You probably already know that computer screens are a 2D array of
pixels. Each pixel contains red, green and blue lights,[^lcd-design]
or _color channels_, that can shine with an intensity between 0 (off)
and 1 (fully on). By mixing red, green, and blue, which is formally
known as the [sRGB color space][srgb], any color in that space's _gamut_ can be
made.[^other-spaces]

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
more colors, so CSS now includes [new syntax][color-spec] for
expressing these new colors.

The job of a rasterization library is to determine the red, green, and
blue intensity of each pixel on the screen, based on the
shapes---lines, rectangles, text---that the application wants to
display. This is already a challenge for a single shape, but with
multiple shapes there's an additional question: what color should the
pixel be when two shapes overlap? So far, our browser has only handled
opaque shapes,[^nor-subpixel] and the answer has been simple: take the
color of the top shape. But now we need more nuance.

[^nor-subpixel]: Nor has our browser yet thought about subpixel
    geometry or anti-aliasing, which also rely on color mixing.

Many objects in nature are partially transparent: frosted glass,
clouds, or colored paper, for example. Looking through one, you see
multiple colors *blended* together. That's also why computer screens work:
the red, green, and blue lights [blend together][mixing] and appear to
our eyes as another color. Designers use this effect[^mostly-models]
in overlays, shadows, and tooltips, so our browser needs to support
color mixing.

[mixing]: https://en.wikipedia.org/wiki/Color_mixing

[^mostly-models]: Mostly. Some more advanced blending modes are
difficult, or perhaps impossible, in real-world physics.

<a name="alpha"></a>

The most important type of color mixing is transparency. Skia, SDL,
and many other color libraries account for transparency with a fourth
*alpha* channel.[^alpha-history] An alpha of 0 means the pixel is
fully transparent (meaning, no matter what the colors are, you can't
see them anyway), and an alpha of 1 means a fully opaque like the ones
we've been working with so far. When a pixel with alpha overlaps
another pixel, the final color is a mix of their two colors.

[^alpha-history]: Check out this [history of alpha][alpha-history],
written by its co-inventor (and co-founder of Pixar), or read this
[derivation of alpha][alpha-deriv] for how it is computed.

[alpha-history]: http://alvyray.com/Memos/CG/Microsoft/7_alpha.pdf
[alpha-deriv]: https://jcgt.org/published/0004/02/03/paper.pdf

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

Stacking contexts
=================

Color mixing means we need to think carefully about the order of
operations. For example, consider black text on an orange background,
placed semi-transparenly over a white background.[^example-1] The text
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
shapes but to a tree of [*stacking contexts*][stacking-context]. Each
stacking context is rastered into a single 2D array of pixels and then
blended into its parent stacking context. Note that to raster a
stacking context you first need to raster in and child stacking
contexts, so they can be blended into the stacking context. In other
words, rastering a web page requires a bottom-up traversal of the tree
of stacking contexts.

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
complex paint orders, in lockstep, to achieve scrolling.
:::

[^also-containing-block]: While we're at it, perhaps scrollable
elements should also be a [containing block][containing-block] for
descendants. Otherwise, a scrollable element can have non-scrolling
children via properties like `position`. This situation is very
complicated to handle in real browsers.

[containing-block]: https://developer.mozilla.org/en-US/docs/Web/CSS/Containing_block

Surfaces and canvases
=====================

The 2D pixel array for a group is called a *surface*.[^or-texture] Conceptually,
each layout object will now have its own surface,[^more-than-one] and perform a
blending operation when being drawn into the surface for its parent.
A *canvas*, on the other hand, is an API interface for drawing into a surface.
As you've seen, Tkinter has a canvas API, and so does Skia. The "`with surface
as canvas`" Python code pattern we've been using for Skia makes this extra
clear---in this case, the canvas is a temporary object created for the duration
of the `with` construct that, when its API methods are called, affects the
pixels in the surface.

[^more-than-one]: A layout object can have more than one surface, actually. For
the cases we'll see in this chapter, it's possible to optimize away most
of these extra surfaces, but we won't do that in cases where it gets in the way
of understanding blending.

In practice, however, new surfaces are only created when needed to perform
non-standard blending. For example, up to this point in the book, we could draw
the entire browser with only one surface. It's important to avoid creating
surfaces unless necessary, because it'll use up a ton of memory on complex
pages. 

[^or-texture]: Sometimes they are called *bitmaps* or *textures* as well, but
these words connote specific CPU or GPU technologies for implementing surfaces.

In Skia, surfaces are recursive and form a stack.[^tree] You can push a new
surface on the stack, and pop one off. To push a surface, you call
`SaveLayer` on a canvas.[^layer-surface] Parameters passed to this method
indicate the kind of blending that is desird when popped. To pop, call
`Restore`. Skia will keep track of the stack of surfaces for you, and perform
blending when you call `Restore`. (In fact, the only surface we'll create
explicitly is `Browser.skia_surface`).

[^layer-surface]: It's called `SaveLayer` instead of `BeginSurface` because Skia
doesn't actually promise to create a surface, it just promises not to keep
drawing directly to the current one. It will in fact optimize away
surfaces internally if it can. So what you're really doing with `SaveLayer` is
telling Skia that there is a new conceptual layer ("piece of paper") on the
stack. How Skia does the rest is an implementation detail (for now!).

[^tree]: A stack and a tree are very similar---the tree is a representation of
the push/pop sequences when executing commands on the stack in the course of
a program's execution. In our implementation, we'll call `SaveLayer` for
each new layout object that needs it, and `Restore` when the recursion is done.

As we'll see shortly, Skia also has canvas APIs for performing common operations
like clipping and transform---for example, there is a `rotate` method
that rotates the content on the screen. Once you call a method like that,
all subsequent canvas commands are rotated, until you tell Skia to stop. The
way to do that is with `Save` and `Restore`---you call `Save` before
calling `rotate`, and `Restore` after. `Save` means "snapshot the current
rotation, clip, etc. state of the canvas", and `Restore` rolls back to the
most recent snapshot.

You've probably noticed that `Restore` is used for both saving state and
pushing layers---what gives? That's because there is a combined stack of layers
and state in the Skia API. Transforms and clips sometimes do actually require
new surfaces to implement correctly, so in fact when we use `Save` it's
actually just a shortcut for `SaveLayer` that is often more efficient; if Skia
thinks it needs to, it'll make a surface. The rule
of thumb is: if you don't need a non-default blend mode, then you can use
`Save`, and you should always prefer `Save` to `SaveLayer`, all things being
equal.

<a name="compositing-blending"></a>

Compositing vs blending
=======================

In the web specifications, *compositing*[^not-to-be-confused] and *blending* are
treated differently. In the specification, compositing defines one or more way
of mixing colors from two groups. Blending, on the other hand, specifies more
advanced ways of how the colors mix, but is an extra step before compositing
(with a blend mode, in a sense the colors mix twice). In general, you can
have both blending and compositing for groups. Skia treats them all the same,
via a single blend mode concept in the API. If you need to apply both blending
and non-default compositing to groups, you just create an extra intermediate
group.

[^not-to-be-confused]: The word *compositing* here refers to the algorithm
used for blending groups. The same word is sometimes used for multiple other
concepts in browsers, graphics and operating systems. For example, a
"composited" animation on the web is one that typically uses a GPU texture for
 its contents, and an operating system "compositor" is in charge of drawing the
 pixels from multiple appliations together onto the screen. But of course, each
 of these situations requires the programmer to decide upon an algorithm for
 how to mix the pixels, so all the uses of the word "compositing" are indeed
 related.

Needless to say, this is all quite confusing. To break through that confusion,
I'll just spell out exactly what is going on mathematically later in this
chapter. For now, just know that there are two words, and they are very similar
concepts.

Now we're ready to implement some visual effects! Let's start with size and
transform, and then proceed to transparency and blend modes.

Size and transform
==================

At the moment, block elements size to the dimensions of their inline and input
content, and input elements have a fixed size. But real web sites often have
multiple layers of visuals on top of each other; for example, we'll be adding
just such a feature to the guest book.[^also-compositing] To achieve that kind
of look, we'll need to add support for sizing and transforms.

Sizing allows you to set a block element's[^not-inline] width and height to
whatever you want (not just the layout size of descendants), and transform
allows you to move it around on screen from where it started out. Sizing only
applies to the element itself.

[^also-compositing]: Another reason is that it'd be really hard to explain
compositing and blending modes without allowing content to overlap...

[^not-inline]: Inline elements can't have their width and height overridden. For
something like that you would need to switch them to a different layout mode
called `inline-block`, which we have not implemented.

For example, this HTML:

    <div style="background-color:lightblue;width:50px; height:100px">
    </div>
    <div style="background-color:orange;width:50px; height:100px">
    </div>

should render into a light blue 50x100 rectangle, with another orange one below
it:

<div style="background-color:lightblue;width:50px;height:100px"></div>
<div style="background-color:orange;width:50px;height:100px"></div>

Support for these properties turns out to be easy[^not-easy]---if `width` or
`height` is set, use it, and otherwise use the built-in sizing. For
`BlockLayout`:

[^not-easy]: Or more precisely, easy only because the layout engine of our
browser only has a few modes implemented.

``` {.python}
def style_length(node, style_name, default_value):
    style_val = node.style.get(style_name)
    if style_val:
        return int(style_val[:-2])
    else:
        return default_value

class BlockLayout:
    # ...
    def layout(self):
        # ...
        self.width = style_length(
            self.node, "width", self.parent.width)
        # ...
        self.height = style_length(
            self.node, "height",
            sum([child.height for child in self.children]))
```

And `InputLayout`:

``` {.python}
class InputLayout:
    # ...
    def layout(self):
        # ...
        self.width = style_length(
            self.node, "width", INPUT_WIDTH_PX)
        self.height = style_length(
            self.node, "height", linespace(self.font))
```

And `InlineLayout`:

``` {.python}
class InlineLayout:
    # ...
    def layout(self):
        self.width = style_length(
            self.node, "width", self.parent.width)
        # ...
        self.height = style_length(
            self.node, "height",
            sum([line.height for line in self.children]))
```

::: {.further}
Since we've added support for setting the size of a layout object to
be different than the sum of its children's sizes, it's easy for there to
be a visual mismatch. What are we supposed to do if a `LayoutBlock` is not
as tall as the text content within it? By default, browsers draw the content
anyway, and it might or might not paint outside the block's box.
This situation is called [*overflow*][overflow-doc]. There are various CSS
properties, such as [`overflow`][overflow-prop], to control what to do in
this situation. By far the most important (or complex, at least) value of
this property is `scroll`.

[overflow-doc]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Flow_Layout/Flow_Layout_and_Overflow

This value means, of course, for the browser to allow the user to scroll
the content in order to see it; the parts that don't overlap the block
are *clipped* out (we'll cover clipping later in this chater).

Basic scrolling for DOM elements is very similar to the scrolling you already
implemented in [Chapter 2](graphics.html#graphics-scrolling). But implementing
it in its full generality, and with excellent performance, is *extremely*
challenging. Scrolling is probably the single most complicated feature in a
browser rendering engine. The corner cases and subtleties involved are almost
endless.
:::

[overflow-prop]: https://developer.mozilla.org/en-US/docs/Web/CSS/overflow

Now let's add (2D) transforms.[^3d-matrix] In computer graphics, a linear
transformation of a point in a geometric space is usually represented by matrix
multiplication. The same concept exists on the web in the `transform` CSS
property. This property specifies a transform for a layout object's group when
drawing into its parent group. There is a `matrix(...)` syntax for the value
of `transform`, but we'll only implement `rotate(XXdeg)` and `translate(x,y)`,
which are shorthands for rotation and translation matrices. Unlike sizing,
transforms also apply to the entire element subtree.

[^3d-matrix]: 3D is also supported in real browsers, but we'll only discuss 2D
matrices in this chapter. There is a lot more complexity to 3D transforms
having to do with the definition of 3D spaces, flatting, backfaces, and plane
intersections.

[^except-scrolling]: The only exception is that transforms contribute to
[scrollable overflow](https://drafts.csswg.org/css-overflow/#scrollable),
though we won't implement that.

By default, the origin of the coordinate space in which the transform applies is
the center of the layout object's rectangular bounds.[^transform-origin] The
transform matrix specfied by the `transform` property
[maps][applying-a-transform] each of the four points to a new 2D pixel location,
and then blends them into the parent group at that location. You
can think of it also doing roughly the same thing for the pixels inside the
group.[^filter-transform]

[^transform-origin]: As you might expect, there is a CSS property called
`transform-origin` that allows changing this default.

[applying-a-transform]: https://drafts.csswg.org/css-transforms-1/#transform-rendering

[^filter-transform]: In reality, methods of rastering a group across a transform
is a nuanced topic. Generating high-quality results without visible blurring or
distortion in these situations involves a number of considerations, such as the
choice of filtering algorithms, pixel-snapping of lines and fonts, and how to
handle pixels near the edges. We won't discuss any of that here.

Transforms are almost entirely a visual effect, and do not affect layout.
[^except-scrolling] 

This example:

    <div style="width:200px;height:200px;
        transform:rotate(10deg);background-color:lightblue">
    </div>

paints like this:

<div style="width:200px;height:200px;
        transform:rotate(10deg);background-color:lightblue">
</div>

As mentioned earlier, we'll need to use `save` and `restore`
to implement transforms. Let's start by adding two new disply list commands for
them:

``` {.python}
class Save:
    def __init__(self, rect):
        self.rect = rect

    def execute(self, scroll, canvas):
        canvas.save()

class Restore:
    def __init__(self, rect):
        self.rect = rect

    def execute(self, scroll, canvas):
        canvas.restore()
```

Next, parse the `transform` property:

``` {.python}
def parse_rotation_transform(transform_str):
    left_paren = transform_str.find('(')
    right_paren = transform_str.find('deg)')
    return float(transform_str[left_paren + 1:right_paren])

def parse_translate_transform(transform_str):
    left_paren = transform_str.find('(')
    right_paren = transform_str.find(')')
    (x_px, y_px) = \
        transform_str[left_paren + 1:right_paren].split(",")
    return (float(x_px[:-2]), float(y_px[:-2]))

def parse_transform(transform_str):
    if transform_str.find('translate') >= 0:
        return (parse_translate_transform(transform_str), None)
    elif transform_str.find('rotate') >= 0:
        return (None, parse_rotation_transform(transform_str))
    else:
        return (None, None)
```

Also add the "," character to the list of characters in a CSS word:

``` {.python}
class CSSParser:
    # ...
            if cur.isalnum() or cur in ",/#-.%()\"'" \
```

Then we need paint it into the display list (we need to `Save` before rotating,
to only rotate the element and its subtree, not the rest of the output). For
that, introduce a new method `paint_visual_efects` that is called by
`paint` for each layout object class.

``` {.python}
def paint_visual_effects(node, display_list, rect):
    restore_count = 0

    transform_str = node.style.get("transform", "")
    if transform_str:
        display_list.append(Save(rect))
        restore_count = restore_count + 1
        (translation, rotation) = parse_transform(transform_str)
        if translation:
            (x, y) = translation
            display_list.append(Translate(x, y, rect))
        elif rotation:
            display_list.append(Rotate(rotation, rect))
```

The change to `paint` for `BlockLayout` looks like this:

``` {.python}
class BlockLayout:
    # ...
    def paint(self, display_list):
        # ...
        restore_count = paint_visual_effects(
            self.node, display_list, rect)

        paint_background(self.node, display_list, rect)

        for child in self.children:
            child.paint(display_list)
        # ...
        for i in range(0, restore_count):
            display_list.append(Restore(rect))
```

Note how we kept track of a `restore_count` variable, and called `Restore` that
many times. At the moment, `restore_count` can only be 0 or 1, but later on it
might be higher. Another thing you should notice is that the recursive
calls to `child.paint` happen *before* `Restore`, which makes sense---a
transform applies to the entire subtree's groups, not just the current layout
object.


The implementation of `Rotate` in Skia looks like this:

``` {.python}
class Rotate:
    def __init__(self, degrees, rect):
        self.degrees = degrees
        self.rect = rect

    def execute(self, scroll, canvas):
        paint_rect = skia.Rect.MakeLTRB(
            self.rect.left(), self.rect.top() - scroll,
            self.rect.right(), self.rect.bottom() - scroll)
        (center_x, center_y) = center_point(paint_rect)
        canvas.translate(center_x, center_y)
        canvas.rotate(self.degrees)
        canvas.translate(-center_x, -center_y)
```

Note how we first translated to put the center of the layout object at the
origin before rotating (this is the negative translation), then rotation, then
translated back.

Anther strange thing to get used to is that the transforms seem to be in the
wrong order---didn't we say that first translation to apply is the negative
one? Yes, but the way canvas APIs work is that all *preceding* transforms,
clips etc apply to later commands. And they apply "inside-out", meaning last
one first.
[^transforms-hard]

[^transforms-hard]: This is also how matrix math is represented in mathematics.
Nevertheless, I find it very hard to remember this when programming! When in
doubt, work through an example, and remember that the computer is your friend to
test if the results look correct.

Finally, here is `Translate` as well:

``` {.python}
class Translate:
    def __init__(self, x, y, rect):
        self.x = x
        self.y = y
        self.rect = rect

    def execute(self, scroll, canvas):
        paint_rect = skia.Rect.MakeLTRB(
            self.rect.left(), self.rect.top() - scroll,
            self.rect.right(), self.rect.bottom() - scroll)
        canvas.translate(self.x, self.y)
```

Opacity and Compositing
=======================

With sizing and transform, we also now have the ability to make content
overlap! Consider this example of CSS & HTML:[^inline-stylesheet]

    <style>
        div { width:100px; height:100px }
    </style>
    <div style="background-color:lightblue">
    </div>
    <div style="background-color:orange;transform:translate(50px,-25px)">
    </div>
    <div style="background-color:blue;transform:translate(100px,-50px)">
    </div>

[^inline-stylesheet]: Here I've used an inline style sheet. If you haven't
completed the inline style sheet exercise for chapter 6, you'll need to
convert this into a style sheet file in order to load it in your browser.

Its rendering looks like this:

<div style="width:100px;height:100px;background-color:lightblue"></div>
<div style="width:100px;height:100px;background-color:orange;transform:translate(50px,-25px)"></div>
<div style="width:100px;height:100px;background-color:blue;transform:translate(100px,-50px)"></div>

Right now, the blue rectangle completely obscures part of the orange one, and
the orange one does the same to the light blue one. In order to explore
what happens with blending further, let's make the elements
semi-transparent.

We can easily implement that with `opacity`, a CSS property that takes a value
from 0 to 1, 0 being completely invisible (like a window in a house) to
completely opaque (the wall next to the window). After adding opacity to the
blue `div`, our example looks like:

    <style>
        div { width:100px; height:100px; position:relative }
    </style>
    <div style="background-color:lightblue">
    </div>
    <div style="background-color:orange;left:50px;top:-25px">
    </div>
    <div style="background-color:blue;left:100px;top:-50px;opacity: 0.5">
    </div>

<div style="width:100px;height:100px;position:relative;background-color:lightblue"></div>
<div style="width:100px;height:100px;position:relative;background-color:orange;left:50px;top:-25px"></div>
<div style="width:100px;height:100px;position:relative;background-color:blue;left:100px;top:-50px;opacity: 0.5"></div>

Note that you can now see part of the orange square through the blue one, and
part of the white background as well.

Let's implement `opacity`. The way to do this is to create a new surface with
`saveLayer`, draw the content with opacity into it, and then blend that
surface into the previous one. This will be our first occasion to use
`saveLayer`, so let's define a display list command for it:

``` {.python}
class SaveLayer:
    def __init__(self, sk_paint, rect):
        self.sk_paint = sk_paint
        self.rect = rect

    def execute(self, scroll, canvas):
        canvas.saveLayer(paint=self.sk_paint)
```

Notice how `SaveLayer` takes an `SkPaint` object as a parameter. This will
be how we'll define opacity and blend modes. In the example below, we're
setting the `Alphaf` parameter (floating-point alpha) to apply the opacity.

Adding opacity to our existing `paint_visual_effects` function is a breeze.
We won't need to make any further changes to any of the `paint` methods,
since they already call `paint_visual_effects`.

``` {.python expected=False}
def paint_visual_effects(node, display_list, rect):
    restore_count = 0
    # ...
    opacity = float(node.style.get("opacity", "1.0"))
    if opacity != 1.0:
        paint = skia.Paint(Alphaf=opacity
        display_list.append(SaveLayer(paint, rect))
        restore_count = restore_count + 1

    return restore_count
```

Let's see how opacity and compositing actually work under the hood, so we can
know what is actually going on in these simple-looking Skia APIs. We'll write
some Python functions[^pedagogical] that do the math of these operations,
starting with `apply_opacity`, which simply multiplies the alpha channel by the
given opacity.[^see-alpha]

[^see-alpha]: Now might be a good time to go back and re-read the paragraph
about alpha [here](#alpha).

[^pedagogical]: These Python functions will not end up as part of your browser.
We're writing them down only so that it's clear what exactly Skia is doing.

Let's assume that pixels are represented in a `skia.Color4f`, which has three
color properties `fR`, `fG`, and `fB` (floating-point red/green/blue, between 0
and 1), and one alpha property `fA` (floating-point alpha).[^alpha-vs-opacity]

[^alpha-vs-opacity]: The difference between opacity and alpha is often
confusing. To remember the difference, think of opacity as a visual effect
*applied to* content, but alpha as a *part of* content. In fact, whether there
is an alpha channel in a color representation at all is often an implementation
choice---sometimes graphics libraries instead multiply the other color channels
by the alpha amount, which is called a *premultiplied* representation of the color.

``` {.python.example}
# Returns |color| with opacity applied. |color| is a skia.Color4f.
def apply_opacity(color, opacity):
    new_color = color
    new_color.fA = color.fA * opacity
    return new_color
```

Next, compositing: let's also assume that the coordinate spaces and pixel
densities of the two surfaces are the same, and therefore their pixels overlap
and have a 1:1 relationship. Therefore we can "composite" each pixel in the
popped surface on top of (into, really) its corresponding pixel in the restored
surface. Let's call the popped surface the *source surface* and the restored
surface the *backdrop surface*. Likewise each pixel in the popped surface is
a *source pixel* and each pixel in the restored surface is a *backdrop pixel*.

The default compositing mode for the web is called *simple alpha compositing* or
*source-over compositing*.[^other-compositing]
In Python, the code to implement it looks like this:[^simple-alpha]

[^simple-alpha]: The formula for this code can be found
[here](https://www.w3.org/TR/SVG11/masking.html#SimpleAlphaBlending). Note that
that page refers to premultiplied alpha colors. Skia does not
use premultiplied color representations.


``` {.python file=examples}
# Note: this is sample code to explain the concept, it is not part
# of the actual browser.
def composite(source_color, backdrop_color, compositing_mode):
    if compositing_mode == "source-over":
        (source_r, source_g, source_b, source_a) = \
            tuple(source_color)
        (backdrop_r, backdrop_g, backdrop_b, backdrop_a) = \
            tuple(backdrop_color)
        return skia.Color4f(
            backdrop_r * (1-source_a) * backdrop_a + \
                source_r * source_a,
            backdrop_g * (1-source_a) * backdrop_a + \
                source_g * source_a,
            backdrop_b * (1-source_a) * backdrop_a + \
                source_b * source_a,
            1 - (1 - source_a) * (1 - backdrop_a))
```

[^other-compositing]: We'll shortly encounter other compositing modes.

This algorithm is basically "average the source and backdrop pixel colors,
weighted by their their alpha".^[Examples: if the alpha of the source pixel
was 1, the result is just the source pixel color, and if it was 0 the
result is the backdrop pixel color.]

Putting it all together, if we were to implement the `restore` command
ourselves from one canvas to another, we could write the following
(pretend we have
a `getPixel` method that returns a `skia.Color4f` and a `setPixel` one that
sets a pixel color):[^real-life-reading-pixels]

``` {.python.example}
# Note: this is sample code to explain the concept, it is not part
# of the actual browser.
def restore(source_surface, backdrop_surface, width, height, opacity):
    for x in range(0, width):
        for y in range(0, height):
            backdrop_surface.setPixel(
                x, y,
                composite(
                    apply_opacity(source_surface.getPixel(x, y)),
                    backdrop_surface.getPixel(x, y)))
```

[^real-life-reading-pixels]: In real browsers it's a bad idea to read canvas
pixels into memory and manipulate them like this, because it would be very
slow. Instead, it should be done on the GPU. So libraries such as Skia don't
make it convenient to do so. (Skia canvases do have `peekPixels` and
`readPixels` methods that are sometimes used, but not for this use case).

Blending
========

Blending, as the CSS specifications define it, is a way to mix source and
backdrop colors together, but is not the same thing as
compositing.[^vs-blending-2] Blending mixes the source and backdrop colors.
The mixed result is then composited with the backdrop pixel. The changes to our
Python code for `restore` to incorporate blending looks like this:

[^vs-blending-2]: Again, see [here](#compositing-blending) for compositing vs
blending.

``` {.python.example}
# Note: this is sample code to explain the concept, it is not part
# of the actual browser.
def restore(source_surface, backdrop_surface,
            width, height, opacity, blend_mode):
    # ...
            backdrop_surface.setPixel(
                x, y,
                composite(
                    blend(
                        apply_opacity(source_surface.getPixel(x, y)),
                        backdrop_surface.getPixel(x, y), blend_mode),
                    backdrop_surface.getPixel(x, y)))
```

and blend is implemented like this:

``` {.python file=examples}
# Note: this is sample code to explain the concept, it is not part
# of the actual browser.
def blend(source_color, backdrop_color, blend_mode):
    (source_r, source_g, source_b, source_a) = tuple(source_color)
    (backdrop_r, backdrop_g, backdrop_b, backdrop_a) = \
        tuple(backdrop_color)
    return skia.Color4f(
        (1 - backdrop_a) * source_r +
            backdrop_a * apply_blend(
                source_r, backdrop_r, blend_mode),
        (1 - backdrop_a) * source_g +
            backdrop_a * apply_blend(
                source_g, backdrop_g, blend_mode),
        (1 - backdrop_a) * source_b +
            backdrop_a * apply_blend(
                source_b, backdrop_b, blend_mode),
        source_a)
```

There are various algorithms `blend_mode` could use. Examples include "multiply",
which multiplies the colors as floating-point numbers between 0 and 1,
and "difference", which subtracts the darker color from the ligher one. The
default is "normal", which means to ignore the backdrop color.

``` {.python file=examples}
# Note: this is sample code to explain the concept, it is not part
# of the actual browser.
def apply_blend(source_color_channel,
                backdrop_color_channel, blend_mode):
    if blend_mode == "multiply":
        return source_color_channel * backdrop_color_channel
    elif blend_mode == "difference":
        return abs(backdrop_color_channel - source_color_channel)
    elif blend_mode == "normal":
        return source_color_channel
```

These are specified with the [`mix-blend-mode`][mix-blend-mode-def] CSS
property. Here's a demo to see how it will look:[^isolation]

    <style>
        html { background-color: white }
        div { width:100px; height:100px }
    </style>
    <div style="background-color:lightblue"></div>
    <div style="background-color:orange;left:50px;top:-25px"></div>
    <div style="background-color:blue;left:100px;top:-50px"></div>

This will look like:

<style>
    html { background-color: white }
</style>
<div style="width:100px;height:100px;position:relative;background-color:lightblue"></div>
<div style="width:100px;height:100px;position:relative;background-color:orange;left:50px;top:-25px;mix-blend-mode:multiply"></div>
<div style="width:100px;height:100px; position:relative;background-color:blue;left:100px;top:-50px;mix-blend-mode:difference"></div>

[^isolation]: Here I had to explicitly set a background color of white on the
`<html>` element, even though web pages have a default white background. This
is because `mix-blend-mode` is defined in terms of stacking contexts. In a real
browser, if a stacking context doesn't paint anything, then its blending
surface is empty; in our browser, blending happens whith whatever surface
happened to be there before `saveLayer` was called. This is a bug in our
browser, which can be fixed by calling `saveLayer` on the parent layout
object.

Here you can see that the intersection of the orange and
blue[^note-yellow] square renders as pink. Let's work through the math to see
why. Here we are blending a blue color with orange, via the "difference" blend
mode. Blue has (red, green, blue) color channels of (0, 0, 1.0), and orange
has (1.0, 0.65, 0.0). The blended result will then be (1.0 - 0, 0.65 - 0, 1.0 -
0) = (1.0, 0.65, 1.0), which is pink.

[^note-yellow]: The "difference" blend mode on the blue rectangle makes it look
yellow over a white background!

Now add support for [multiply][mbm-mult] and [difference][mbm-diff] to our
browser. Implementing these blend modes in our browser will be very easy,
because Skia supports these blend mode natively. It's as simple as parsing the
property and adding a `blend_mode` parameter to the `Skpaint` object.

``` {.python}
def parse_blend_mode(blend_mode_str):
    if blend_mode_str == "multiply":
        return skia.BlendMode.kMultiply
    elif blend_mode_str == "difference":
        return skia.BlendMode.kDifference
    else:
        return skia.BlendMode.kSrcOver

def paint_visual_effects(node, display_list, rect):
    # ...

    blend_mode_str = node.style.get("mix-blend-mode")
    blend_mode = skia.BlendMode.kSrcOver
    if blend_mode_str:
        blend_mode = parse_blend_mode(blend_mode_str)

    opacity = float(node.style.get("opacity", "1.0"))
    if opacity != 1.0 or blend_mode_str:
        paint = skia.Paint(Alphaf=opacity, BlendMode=blend_mode)
        display_list.append(SaveLayer(paint, rect))
        restore_count = restore_count + 1
```

[mbm-mult]: https://drafts.fxtf.org/compositing-1/#blendingmultiply
[mbm-diff]: https://drafts.fxtf.org/compositing-1/#blendingdifference

[mix-blend-mode-def]: https://drafts.fxtf.org/compositing-1/#propdef-mix-blend-mode

Non-rectangular clips and rounded corners
=========================================

Let's now explore compositing modes other than source-over. They are generally
not very common, with the exception of *destination-in*. This mode is used to
represent clipping---cutting out parts of a surface that don't intersect with a
given shape. Clipping is like putting a second piece of paper (called a *mask*)
over the first one, and then using scissors to cut along the edge of the
mask.

One way this is expressed in CSS is with the `clip-path` property. The
[full definition](https://developer.mozilla.org/en-US/docs/Web/CSS/clip-path)
is quite complicated, so as usual we'll just implement a simple subset. In this
case we'll only support the `circle(XX%)` syntax, which cuts out all the content
that doesn't intersect a circle. XX is a percentage and defines the radius
of the circle; the percentage is calibrated so that if the layout object was
a perfect square, a 100% circle would inscribe the bounds of the square.

Let's apply a circular mask to our image example:

    <div style="width:256px; height:256px;
        clip-path:circle(50%);background-color:lightblue">
    </div>

Which paints like this:

<div style="width:256px;height:256px;clip-path:circle(50%);background-color:lightblue">
</div>

Implementing circular clips is once again pretty easy with Skia in our back
pocket, but has some differences from other visual effects. We'll make a new
surface (the mask), draw the circle into it, and then blend it with
destination-in compositing. Let's first get the code in place and then
investigate more about how it works.

Parse the `clip-path` CSS property:

``` {.python}
def parse_clip_path(clip_path_str):
    if clip_path_str.find("circle") != 0:
        return None
    return int(clip_path_str[7:][:-2])
```

And define how to paint it:

``` {.python}
def center_point(rect):
    return (rect.left() + (rect.right() - rect.left()) / 2,
        rect.top() + (rect.bottom() - rect.top()) / 2)
# ...

def paint_clip_path(node, display_list, rect):
    clip_path = node.style.get("clip-path")
    if clip_path:
        percent = parse_clip_path(clip_path)
        if percent:
            width = rect.right() - rect.left()
            height = rect.bottom() - rect.top()
            reference_val = \
                math.sqrt(width * width +
                    height * height) / math.sqrt(2)
            radius = reference_val * percent / 100
            (center_x, center_y) = center_point(rect)
            display_list.append(CircleMask(
                center_x, center_y, radius, rect))
```

Destination-in compositing is defined [here][dst-in], and basically means
"keep the pixels of the backdrop surface that intersect with the source
 surface". The color is not important, it's just the alpha that matters.
In this case, the source surface is the circle, and the backdrop surface is the
thing we want to clip, so destination-in fits perfectly.

[dst-in]: https://drafts.fxtf.org/compositing-1/#porterduffcompositingoperators_dstin

Here is `composite` with destination-in compositing added:

``` {.python file=examples}
# Note: this is sample code to explain the concept, it is not part
# of the actual browser.
def composite(source_color, backdrop_color, compositing_mode):
    # ...
    elif compositing_mode == "destination-in":
        (source_r, source_g, source_b, source_a) = tuple(source_color)
        (backdrop_r, backdrop_g, backdrop_b, backdrop_a) = \
            tuple(backdrop_color)
        return skia.Color4f(
            backdrop_a * source_a * backdrop_r,
            backdrop_a * source_a * backdrop_g,
            backdrop_a * source_a * backdrop_b,
            backdrop_a * source_a)
```

Now let's implement `CircleMask`  in terms of destination-in compositing. It
creates a new source surface via `saveLayer` (and at the same time specifying a
`kDstIn` blend mode for when it is drawn into the backdrop), then draws a
circle in white (or really any opaque color, it's only the alpha channel that
matters).

``` {.python}
class CircleMask:
    def __init__(self, cx, cy, radius, rect):
        self.cx = cx
        self.cy = cy
        self.radius = radius
        self.rect = rect

    def execute(self, scroll, canvas):
        canvas.saveLayer(paint=skia.Paint(
            Alphaf=1.0, BlendMode=skia.kDstIn))
        canvas.drawCircle(
            self.cx, self.cy - scroll,
            self.radius, skia.Paint(Color=skia.ColorWHITE))
```

Finally, we call `paint_clip_path` for each layout object type. Note however
that we have to paint it *after* painting children, unlike visual effects
or backgrounds. This is because you have to paint the other content into the
backdrop surface before drawing the circle and applying the clip. For
`BlockLayout`, this is:

``` {.python}
    def paint(self, display_list):
        # ...

        for child in self.children:
            child.paint(display_list)

        paint_clip_path(self.node, display_list, rect)

        for i in range(0, restore_count):
            display_list.append(Restore(rect))
```

But we're not quite done. We still need to *isolate* the element and its
subtree, in order to apply the clip path to only these elements, not to the
entire backdrop.[^extra-surface] To achieve that we add an extra `saveLayer` in
`paint_visual_effects`:

[^extra-surface]: This is one of the extra surfaces I mentioned earlier,
and an example of why there may be more surfaces than groups.

``` {.python}
def paint_visual_effects(node, display_list, rect):
    # ...

    clip_path = node.style.get("clip-path")
    if clip_path:
        display_list.append(SaveLayer(skia.Paint(), rect))
        restore_count = restore_count + 1
```

This technique described here for implementing `clip-path` is
called *masking*---drawing to an auxiliary image and removing all pixels of
the backdrop that don't overlap with the image. The circle in this
case is the mask image. The
[`mask`](https://developer.mozilla.org/en-US/docs/Web/CSS/mask) CSS property is
another a way to do this, for example by specifying an image at a URL that
supplies the mask.

While the `mask` CSS property is relatively uncommon used (as is `clip-path`
actually), there is a special kind of mask that is very common: rounded
corners. Now that we know how to implement masks, this one is also easy to
add to our browser (draw a mask image with the `drawRRect` Skia canvas method).
But because it's so common, Skia provides a special-purpose
method to clip to rounded corners: `clipRRect`.

Rounded corners are specified in CSS via `border-radius`. Here's an example:

    <div style="width:256px; height:256px;
        border-radius: 20px;background-color:lightblue">
    </div>

Which paints like this (notice the curved corners):

<div style="width:256px; height:256px;border-radius:20px;background-color:lightblue">
</div>

To implement it, a `ClipRRect` display list command will go in
`paint_visual_effects`:

``` {.python}
def paint_visual_effects(node, display_list, rect):
    border_radius = node.style.get("border-radius")
    if border_radius:
        radius = int(border_radius[:-2])
        display_list.append(Save(rect))
        display_list.append(ClipRRect(rect, radius))
        restore_count = restore_count + 1
```

``` {.python}
class ClipRRect:
    def __init__(self, rect, radius):
        self.rect = rect
        self.radius = radius

    def execute(self, scroll, canvas):
        canvas.clipRRect(
            skia.RRect.MakeRectXY(
                skia.Rect.MakeLTRB(
                    self.rect.left(),
                    self.rect.top() - scroll,
                    self.rect.right(),
                    self.rect.bottom() - scroll),
                self.radius, self.radius))
```

Now why is it that rounded rect clips are applied in `paint_visual_effects` but
masks and clip paths happen later on in the `paint` method? What's going on
here? It is indeed the same, but Skia only optimizes for rounded rects because
they are so common. What it means is "clip the content drawn after this point
until restore is called". Skia could easily add a `clipCircle` command if it
was popular enough.

What Skia does under the covers may be equivalent to the clip path
case,[^skia-opts] and sometimes that is indeed the case. But in other
situations, various optimizations can be applied to make the clip more
efficient. For example, there is another method called `clipRect` that clips to
a rectangle, which makes it easier for Skia to skip subsequent draw operations
that don't intersect that rectangle,[^see-chap-1] or dynamically draw only the
parts of drawings that intersect the rectangle. Likewise, the first
optimization mentiond above also applies to `clipRRect`. (The second is
trickier because you have to account for the space cut out in the corners.)

[^skia-opts]: Skia has many internal optimizations, and by design does not
expose whether they are used to the caller.

[^see-chap-1]: This is basically the same optimization as we added in Chapter
1 to avoid painting offscreen text.

Our journey though compositing and blending modes is now complete, and we're
almost ready to make our guest book look more fun. But there's one visual
conspicuously missing that would make it much more interesting---images.
Images are visual, but aren't really effects...but hey, thet are worth a
thousand words each, so let's add them anyway.

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
rounded corners on their sites before then)! There are a number of clever ways
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

Background images
=================

Let's add support for background images. A background image is
specified in CSS via the `background-image` CSS property. Its full syntax has
[many options][background-image], so let's just implement a simple version of
it. We'll support the `background-image: url("relative-url")` syntax, which
says to draw an image as the background of an element, with the given relative
URL.

[background-image]: https://developer.mozilla.org/en-US/docs/Web/CSS/background-image

Here is an example:

    <div style="width:256px;height:256px;background-image:
            url('/avatar.png')">
    </div>

It paints like this:[^exact-size]

<div style="width:256px;height:256px;background-image:url('/avatar.png')"></div>

[^exact-size]: Note that I cleverly chose the width and height of the `div` to
be exactly `256px`, the dimensions of the JPEG image.

To implement this property, first we'll need to load the background image,
if specified by CSS, and store it on the `node`:

``` {.python}
def parse_style_url(url_str):
    return url_str[5:][:-2]

def style(node, rules, url):
    # ...
    if node.style.get('background-image'):
        node.background_image = \
            get_image(parse_style_url(
                node.style.get('background-image')), url)
    for child in node.children:
        style(child, rules, url)
```

This does not yet define the `get_image` function; I'll get to that in a moment.
This function is in charge of downloading the image and decoding it.

To make non-relative URLs work, we'll also need to modify the CSS parser,
because these URLs start with "https://" or "http://". Since they contain
the ":" character, this will confuse the parser because it thinks it's the
property-value delimiter of CSS. We can fix that by tracking whether we're
inside a quote---if so, we treat the ":" character as part of a word;
otherwise, not.[^only-single-quote]

[^only-single-quote]: We're only adding support for single quotes here, but
double quotes are accepted in real CSS. Single and double quotes can be
interchanged in CSS and JavaScript, just like in Python.

``` {.python expected=False}
class CSSParser:
    # ...
    def word(self):
        start = self.i
        in_quote = False
        while self.i < len(self.s):
            cur = self.s[self.i]
            if cur == "'":
                in_quote = not in_quote
            if cur.isalnum() or cur in "/#-.%()\"'" \
                or (in_quote and cur == ':'):
                self.i += 1
            else:
                break
        assert self.i > start
        return self.s[start:self.i]
```

Now let's figure out how to load the image URL. To do this we'll have to start
by augmenting the `request` function to support binary image content types
(currently it only supports `text/html` and `text/css` encoded in `utf-8`). A
PNG image, for instance, has the content type `image/png`, and is of course not
`utf-8`, it's an encoded PNG file. To fix this, we will need to decode in
smaller chunks: the status line and headers are still `utf-8`, but the body
encoding depends on the image type.

First, when we read from the socket with `makefile`, pass the argument
`b` instead of `r` to request raw bytes as output:

``` {.python}
def request(url, top_level_url, payload=None):
    # ...
    response = s.makefile("b")
    # ...
```

Now you'll need to call `decode` every time you read from the file.
First, when reading the status line:

``` {.python}
def request(url, top_level_url, payload=None):
    # ...
    statusline = response.readline().decode("utf8")
    # ...
```

Then, when reading the headers:

``` {.python}
def request(url, top_level_url, payload=None):
    # ...
    while True:
        line = response.readline().decode("utf8")
        # ...
    # ...
```

And finally, when reading the response, we check for the `Content-Type`, and
only decode[^image-decode] it as `utf-8` if it starts with `text/`:

``` {.python}
def request(url, top_level_url, payload=None):
    # ...
    if headers.get(
        'content-type', 
        'application/octet-stream').startswith("text"):
        body = response.read().decode("utf8")
    else:
        body = response.read()
    # ...
```

While we're at it, add theh `Content-Type` header to the server response:

``` {.python file=server}
def handle_connection(conx):
    # ...
    response = "HTTP/1.0 {}\r\n".format(status)
    response += "Content-Type: text/html\r\n"
    # ...
```

[^image-decode]: Not to be confused with image decoding, which will be done 
later.

Now we are ready to actually load the images. This will involve calling
`request` and then decoding the image. Images are sent over the network in one
of many optimized encoding formats, such as PNG or JPEG; when we need to draw
them to the screen, we need to convert from the encoded format into a raw array
of pixels. These pixels can then be efficiently drawn onto the screen.
[^image-decoding]

[^image-decoding]: While image decoding technologies are beyond the
scope of this book, it's very important for browsers to make optimized use
of image decoding, because the decoded bytes are often take up *much* more
memory than the encoded representation. For a web page with a lot
of images, it's easy to accidentally use up too much memory unless you're very
careful.

Here's how to load, decode and convert images into a `skia.Image` object.
Note that there are two `Image` classes, which is a little confusing.
The Pillow `Image` class's role is to decode the image, and the Skia `Image`
class is an interface between the decoded bytes and Skia's internals. Note
that nowhere do we pass the content type of the image (such as `image/png`)
to a Pillow `Image`. Instead, the format is auto-detected by looking
for content type [signatures] in the bytes of the encoded image.

[signatures]: https://en.wikipedia.org/wiki/List_of_file_signatures

``` {.python}
def get_image(image_url, base_url):
    header, body_bytes = request(
        resolve_url(image_url, base_url), base_url)
    picture_stream = io.BytesIO(body_bytes)

    pil_image = PIL.Image.open(picture_stream)
    if pil_image.mode == "RGBA":
        pil_image_bytes = pil_image.tobytes()
    else:
        pil_image_bytes = pil_image.convert("RGBA").tobytes()
    return skia.Image.frombytes(
        array=pil_image_bytes,
        dimensions=pil_image.size,
        colorType=skia.kRGBA_8888_ColorType)
```

Now that the images are loaded, the next step is to paint them into the display
list. We'll need a new display list object called `DrawImage`:

``` {.python}
class DrawImage:
    def __init__(self, image, rect):
        self.image = image
        self.rect = rect

    def execute(self, scroll, canvas):
        canvas.drawImage(
            self.image, self.rect.left(),
            self.rect.top() - scroll)
```

Then add a `DrawImage`, plus a few additional things, to a new
`paint_background` function that also paints other parts of the background:


``` {.python}
def paint_background(node, display_list, rect):
    bgcolor = node.style.get("background-color",
                             "transparent")
    if bgcolor != "transparent":
        display_list.append(DrawRect(rect, bgcolor))

    background_image = node.style.get("background-image")
    if background_image:
        display_list.append(Save(rect))
        display_list.append(ClipRect(rect))
        display_list.append(DrawImage(node.background_image,
            rect))
        display_list.append(Restore(rect))
```

This will need to be called from each of the layout object types. Here is
`BlockLayout`:

``` {.python expected=False}
class BlockLayout:
    # ...
    def paint(self, display_list):
        # ...
        paint_background(self.node, display_list, rect)
        
        for child in self.children:
            child.paint(display_list)
```

Here we're not just drawing the image though, we're also clipping it to the
size of the layout object. This example should clip out parts of the image:

    <div style="width:100px; height:100px;background-image:
        url('/avatar.png')">
    </div>

Like this:

<div style="width:100px; height:100px;background-image:url('/avatar.png')">
</div>

The `ClipRect` class looks like this:

``` {.python}
class ClipRect:
    def __init__(self, rect):
        self.rect = rect

    def execute(self, scroll, canvas):
        canvas.clipRect(skia.Rect.MakeLTRB(
            self.rect.left(), self.rect.top() - scroll,
            self.rect.right(), self.rect.bottom() - scroll))
```

Note how the background image is painted *before* children, just like
`background-color`.[^paint-order]

Ok, we can now put background images on an element of any size, and the image
will be clipped if it's too big (and it'll reveal the background color or
backdrop if it's too small). But as soon as you're trying to make a web page
(such as an extension to the guest book to show an avatar image), the fact that
you can't resize the image to fit the size of the element is pretty annoying,
because the only way to fix it is to manually resize the image with a utility
program and store an additional image of the new size on the server.

To fix this situation, let's add support for
[`background-size:contain`][background-size], which
means "scale the image so it fits in the size of the element". This is super
easy to implement in Skia, by using the `drawImageRect` method. This method
takes two extra `skia.Rect` arguments: a source rect and a destination rect.
It takes the parts of the image bitmap within the source rect and rescales
it as necessary to fit into the destination rect.
p
[background-size]: https://developer.mozilla.org/en-US/docs/Web/CSS/background-size

This modified example:

    <div style="width:100px; height:100px;background-image:
        url('/avatar.png');background-size:contain">
    </div>

Paints like:

<div style="width:100px; height:100px;
    background-image:url('/avatar.png');background-size:contain">
</div>

The code to add it requires a slight tweak to `paint_background` (note how
we were able to optimize away the save and clip):

``` {.python}
def paint_background(node, display_list, rect):
    # ...
    if background_image:
        background_size = node.style.get("background-size")
        if background_size and background_size == "contain":
            display_list.append(DrawImageRect(node.background_image, rect))
        else:
            display_list.append(Save(rect))
            display_list.append(ClipRect(rect))
            display_list.append(DrawImage(node.background_image,
                rect))
            display_list.append(Restore(rect))
```

and a new display list command:

``` {.python}
class DrawImageRect:
    def __init__(self, image, rect):
        self.image = image
        self.rect = rect

    def execute(self, scroll, canvas):
        source_rect = skia.Rect.Make(self.image.bounds())
        dest_rect = skia.Rect.MakeLTRB(
            self.rect.left(),
            self.rect.top() - scroll,
            self.rect.right(),
            self.rect.bottom() - scroll)
        canvas.drawImageRect(
            self.image, source_rect, dest_rect)
```

::: {.further}

There are a lot more options in the specification for the different ways to
account for this, via additional CSS properties like 
[`background-repeat`][background-repeat].

[intrinsic-size]: https://developer.mozilla.org/en-US/docs/Glossary/Intrinsic_Size
[background-repeat]: https://developer.mozilla.org/en-US/docs/Web/CSS/background-repeat

In addition to these considerations, there are also cases where we want to scale
the image to match the size of its container. This is a somewhat complex
topic---there are various algorithms for [image scaling][image-rendering] to
choose from, each with pros and cons.

[image-rendering]: https://developer.mozilla.org/en-US/docs/Web/CSS/image-rendering

:::

[^paint-order]: In its full generality, the *paint order* of drawing backgrounds and other
painted aspects of a single element, and the interaction of its paint order
with painting descendants, is [quite complicated][paint-order-stacking-context].

[paint-order-stacking-context]: https://www.w3.org/TR/CSS2/zindex.html


The Account Info demo
=====================

TODO: Implement guest book menu overlay using all of the things we've built so
far.

Summary
=======

So there you have it. Now we don't have just a boring browser that can only
draw simple input boxes plus text. It now supports:

* Arbitrary position and size of boxes
* Background images
* Opacity
* Blending
* Non-rectangluar clips
* 2D transforms

::: {.further}
[This blog post](https://ciechanow.ski/alpha-compositing/) gives a really nice
visual overview of many of the same concepts explored in this chapter,
plus way more content about how a library such as Skia might implement features
like raster sampling of vector graphics for lines and text, and interpolation
of surfaces when their pixel arrays don't match resolution or orientation. I
highly recommend it.
:::


Exercises
=========

*z-index*: Right now, the order of paint is a depth-first traversal of the
 layout tree. By using the `z-index` CSS property, pages can change that order.
 An element with lower `z-index` than another one paints before it. Elements
 with the same z-index paint in depth-first order. Elements with no `z-index`
 specified paint at the same time as z-index 0. And lastly, `z-index` only
 applies to elements that have a `position` value other than the default
 (meaning `relative`, for our browser's partial implementation). Implement this
 CSS property. You don't need to add support for nested z-index (an element
with z-index that has an ancestor also witih z-index), unless you do the next
exercise also.

*Z-order stacking contexts*: (this exercise builds on z-index) A
stacking context is a painting feature allowing^[Or
forcing, depending on your perspective...] web pages to specify groups of
elements that paint contiguously. Because they paint continguously, it won't
be possible for `z-index` specified on other elements not in the group to
paint somewhere within the group---only before the entire group or after it.
An element induces a stacking context if one or more of the conditions listed
[here][stacking-context] apply to it. Any descendants (up to stacking
context-inducing descendants) with `z-index` have paint order relative to each 
other, but not elements not in the stacking context. The stacking
context-inducing element itself may have a `z-index`, but that only changes
the paint order of the whole stacking context relative to other contributors to
its parent stacking context.

(Note: in addition, the true paint order for stacking contexts is quite
[elaborate][elaborate]. You don't need to implement all those details.)

 [stacking-context]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Positioning/Understanding_z_index/The_stacking_context

 [elaborate]: https://www.w3.org/TR/CSS2/zindex.html

*Filters* The `filter` CSS property allows specifying various kinds of more
 [complex effects][filter-css], such as grayscale or blur. Try to implement as
 many of these as you can. A number of them (including blur and drop shadow)
 have built-in support in Skia.

*Overflow clipping*: As mentioned at the end of the section introducing the
`width` and `height` CSS properties, sizing boxes with CSS means that the
contents of a layout object can exceed its size. Implement the `clip` value of
the `overflow` CSS property. When set, this should clip out the parts
of the content that exceed the box size of the element.

[filter-css]: https://developer.mozilla.org/en-US/docs/Web/CSS/filter

*Overflow scrolling*: (this exercise builds on overflow clipping) Implement a
 very basic version of the `scroll` value of the `overflow` CSS property.
 You'll need to have a way to actually process input to cause scrolling, and
 also keep track of the total height (and width, for horizontal scrolling!) of
 the [*layout overflow*][overflow-doc]. (Hint: one way to allow the user to
 scroll is to use built-in arrow key handlers that apply when the
 `overflow:scroll` element has focus.)

*Image elements*: the `<img>` element is a way (the original way, back in the
90s, in fact) to draw an image to the screen. The image URL is specified
by the `src` attribute, it has inline layout, and is by default sized to the
intrinsic size of the image, which is its bitmap dimensions. Before an image
has loaded, it has 0x0 intrinsic sizing. Implement this element.

*Transform origin* Add support for some of the keywords of the
[`transform-origin`][transform-origin] CSS property.

[transform-origin]: https://developer.mozilla.org/en-US/docs/Web/CSS/transform-origin
