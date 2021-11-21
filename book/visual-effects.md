---
title: Adding Visual Effects
chapter: 12
prev: security
next: rendering-architecture
...

Right now our browser can draw text and rectangles of various colors. But that's
pretty boring: our guest book demo, for example, does cool stuff but doesn't
*look* very impressive. Real browsers have all sorts of great ways to make
 content look good on the screen, of course. These are called *visual
 effects*---visual because they affect how it looks, but not functionality per
 se, or layout. Therefore these effects are extensions to the *paint*
 and *draw* parts of rendering.

But to understand how this visual effects really work, you'll need to learn a
bit about colors and pixels on computer screens, and what happens when canvases
draw multiple times into the same pixel. Then we can proceed to implementing
some visual effects, but the first step (even before colors and pixels) will be
to replace Tkinter with Skia, a newer rendering library with sufficient
capabilities.

You'll see that implementing these effects in Skia won't be too hard, and with
prior understanding in hand, you'll know more about *how* Skia implements them
under the hood.

Then we'll be able to use these to make the guest book look more fun, by adding
an interactive "account info" menu similar to ones present on many real sites
today.

Skia replaces Tkinter
=====================

Before we get any further defining and implementing compositing and blend modes,
we'll need to upgrade our graphics system. While Tkinter is great for basic
painting and handling input, it has no built-in support at all for implementing
many visual effects.[^tkinter-before-gpu] And just as implementing the details
of text rendering or drawing rectangles is outside the scope of this book, so
is implementing visual effects---our focus should be on how to represent and
execute visual effects for web pages specifically.

[^tkinter-before-gpu]: That's because Tk, the library Tkinter uses to implement
its graphics, was built back in the early 90s, before high-performance graphics
cards and GPUs, and their software equivalents, became widespread.

So we need a new library that can implement visual effects. We'll use
[Skia](https://skia.org), the library that Chromium uses. However, Skia is just
a library for rastering content on the CPU and GPU, so we'll also use
[SDL](https://www.libsdl.org/) to provide windows, input events, and OS-level
integration.

::: {.further}
While this book is about browsers, and not how to implement high-quality
raster libraries, that topic is very interesting in its own right.
In addition, it is very important these days for browsers to work smoothly with
the advanced GPUs in today's devices, and often browsers are pushing the
envelope of graphics technology. So in practice browser teams include experts
in these areas: Skia for Chromium and [Core Graphics][core-graphics] for Webkit,
for example. In both cases these libraries are used outside of the
browser---Core Graphics is used for iOS and macOS apps, and Skia for Android.
:::

[core-graphics]: https://developer.apple.com/documentation/coregraphics

To install Skia, you'll need to install the
[`skia-python`](https://github.com/kyamagu/skia-python)
library (via `pip3 install skia-python`); as explained on the linked site, you
might need to install additional dependencies. Instructions
[here](https://pypi.org/project/PySDL2/) explain how to install SDL on your
computer (short version: `pip3 install PySDL2` and `pip3 install pysdl2-dll`).

Once installed, remove `tkinter` from your Python imports and replace them with:

``` {.python}
import ctypes
import sdl2
import skia
```

The additional `ctypes` module is for interfacing between Python types and C
types.

The main loop of the browser first needs some boilerplate to get SDL started:

``` {.python}
if __name__ == "__main__":
    # ...
    sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
    sdl_window = sdl2.SDL_CreateWindow(b"Browser",
        sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
        WIDTH, HEIGHT, sdl2.SDL_WINDOW_SHOWN)

    browser = Browser(sdl_window)
    browser.load(sys.argv[1])
```

In SDL, you have to implement the event loop yourself (rather than calling
`tkinter.mainloop()`). This loop also has to handle input events:

``` {.python}
    running = True
    event = sdl2.SDL_Event()
    while running:
        while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == sdl2.SDL_MOUSEBUTTONUP:
                browser.handle_click(event.button)
            if event.type == sdl2.SDL_KEYDOWN:
                if event.key.keysym.sym == sdl2.SDLK_RETURN:
                    browser.handle_enter()
                if event.key.keysym.sym == sdl2.SDLK_DOWN:
                    browser.handle_down()
            if event.type == sdl2.SDL_TEXTINPUT:
                browser.handle_key(event.text.text.decode('utf8'))
            if event.type == sdl2.SDL_QUIT:
                running = False
                break

    sdl2.SDL_DestroyWindow(sdl_window)
    sdl2.SDL_Quit()
```

Next factor a bunch of the tasks of drawing into a new class we'll call
`Rasterizer`. The implementation in Skia should be relatively
self-explanatory (there is also more complete documentation
[here](https://kyamagu.github.io/skia-python/)
or at the [Skia site](https://skia.org)):

``` {.python}
class Rasterizer:
    def __init__(self, surface):
        self.surface = surface

    def clear(self, color):
        with self.surface as canvas:
            canvas.clear(color)

    def draw_rect(self, rect,
        fill=None, width=1):
        paint = skia.Paint()
        if fill:
            paint.setStrokeWidth(width);
            paint.setColor(color_to_sk_color(fill))
        else:
            paint.setStyle(skia.Paint.kStroke_Style)
            paint.setStrokeWidth(1);
            paint.setColor(skia.ColorBLACK)
        with self.surface as canvas:
            canvas.drawRect(rect, paint)


    def draw_polyline(self, x1, y1, x2, y2, x3=None,
        y3=None, fill=False):
        path = skia.Path()
        path.moveTo(x1, y1)
        path.lineTo(x2, y2)
        if x3:
            path.lineTo(x3, y3)
        paint = skia.Paint()
        paint.setColor(skia.ColorBLACK)
        if fill:
            paint.setStyle(skia.Paint.kFill_Style)
        else:
            paint.setStyle(skia.Paint.kStroke_Style)
        paint.setStrokeWidth(1);
        with self.surface as canvas:
            canvas.drawPath(path, paint)

    def draw_text(self, x, y, text, font, color=None):
        paint = skia.Paint(
            AntiAlias=True, Color=color_to_sk_color(color))
        with self.surface as canvas:
            canvas.drawString(
                text, x, y - font.getMetrics().fAscent,
                font, paint)
```

Change `DrawText` and `DrawRect` to use the rasterizer in a straightforward
way. For example, here is `DrawText.execute`:

``` {.python}
    def execute(self, scroll, rasterizer):
        rasterizer.draw_text(
            self.rect.left(), self.rect.top() - scroll,
            self.text,
            self.font,
            self.color,
        )
```

Now integrate with the `Browser` class. We need a surface[^surface] for
drawing to the window, and a surface into which Skia will draw.

``` {.python}
class Browser:
    def __init__(self, sdl_window):
        self.window_surface = sdl2.SDL_GetWindowSurface(
            self.sdl_window)
        self.skia_surface = skia.Surface(WIDTH, HEIGHT)
```

Next, re-implement the `draw` method on `Browser` using Skia. I'll
walk through it step-by-step. First make a rasterizer and draw the current
`Tab` into it:

``` {.python}
    def draw(self):
        rasterizer = Rasterizer(self.skia_surface)
        rasterizer.clear(skia.ColorWHITE)

        self.tabs[self.active_tab].draw(rasterizer)
```

Then draw the browser UI elements:

``` {.python}
        # Draw the tabs UI:
        tabfont = skia.Font(skia.Typeface('Arial'), 20)
        for i, tab in enumerate(self.tabs):
            name = "Tab {}".format(i)
            x1, x2 = 40 + 80 * i, 120 + 80 * i
            rasterizer.draw_polyline(x1, 0, x1, 40)
            rasterizer.draw_polyline(x2, 0, x2, 40)
            rasterizer.draw_text(x1 + 10, 10, name, tabfont)
            if i == self.active_tab:
                rasterizer.draw_polyline(0, 40, x1, 40)
                rasterizer.draw_polyline(x2, 40, WIDTH, 40)

        # Draw the plus button to add a tab:
        buttonfont = skia.Font(skia.Typeface('Arial'), 30)
        rasterizer.draw_rect(skia.Rect.MakeLTRB(10, 10, 30, 30))
        rasterizer.draw_text(11, 0, "+", buttonfont)

        # Draw the URL address bar:
        rasterizer.draw_rect(
            skia.Rect.MakeLTRB(40, 50, WIDTH - 10, 90))
        if self.focus == "address bar":
            rasterizer.draw_text(55, 55, self.address_bar, buttonfont)
            w = buttonfont.measureText(self.address_bar)
            rasterizer.draw_polyline(55 + w, 55, 55 + w, 85)
        else:
            url = self.tabs[self.active_tab].url
            rasterizer.draw_text(55, 55, url, buttonfont)

        # Draw the back button:
        rasterizer.draw_rect(skia.Rect.MakeLTRB(10, 50, 35, 90))
        rasterizer.draw_polyline(
            15, 70, 30, 55, 30, 85, True)
```

Finally perform the incantations to save off a rastered bitmap and copy it
from the Skia surface to the SDL surface:

``` {.python}
        # Raster the results and copy to the SDL surface:
        skia_image = self.skia_surface.makeImageSnapshot()
        skia_bytes = skia_image.tobytes()
        rect = sdl2.SDL_Rect(0, 0, WIDTH, HEIGHT)
        skia_surface = Browser.to_sdl_surface(skia_bytes)
        sdl2.SDL_BlitSurface(
            skia_surface, rect, self.window_surface, rect)
        sdl2.SDL_UpdateWindowSurface(self.sdl_window)
```

And here is the `to_sdl_surface` method:

``` {.python}
    def to_sdl_surface(skia_bytes):
        depth = 32 # 4 bytes per pixel
        pitch = 4 * WIDTH # 4 * WIDTH pixels per line on-screen
        # Skia uses an ARGB format - alpha first byte, then
        # through to blue as the last byte.
        alpha_mask = 0xff000000
        red_mask = 0x00ff0000
        green_mask = 0x0000ff00
        blue_mask = 0x000000ff
        return sdl2.SDL_CreateRGBSurfaceFrom(
            skia_bytes, WIDTH, HEIGHT, depth, pitch,
            red_mask, green_mask, blue_mask, alpha_mask)
```

Finally, `handle_enter` and `handle_down` no longer need an event parameter.

[^surface]: In Skia and SDL, a *surface* is a representation of a graphics buffer
into which you can draw "pixels" (bits representing colors). A surface may or
may not be bound to the actual pixels on the screen via a window, and there can
be many surfaces. A *canvas* is an API interface that allows you to draw
into a surface with higher-level commands such as for rectangles or text. In
our implementation, we'll start with separate surfaces for Skia and SDL for
simplicity. In a highly optimized browser, minimizing the number of surfaces
is important for good performance.

In the `Tab` class, the differences in `draw` is the new `rasterizer` parameter
that gets passed around, and using the Skia API to measure font metrics. Skia's
`measureText` method on a font is the same as the `measure` method on a Tkinter
font.

``` {.python}
    def draw(self, rasterizer):
        # ...
            x = obj.x + obj.font.measureText(text)
```

Update all the other places that `measure` was called to use the Skia method
(and also create Skia fonts instead of Tkinter ones, of course).

Skia font metrics are accessed via the `getMetrics` method on a font. Then metrics
like ascent and descent are accessible via:
``` {.python expected=False}
    font.getMetrics().fAscent
```
and
``` {.python expected=False}
    font.getMetrics().fDescent
```

Note that in Skia, ascent and descent are baseline-relative---positive if they
go downward and negative if upward, so ascents will normally be negative.

Now you should be able to run the browser just as it did in previous chapters,
and have all of the same visuals. It'll probably also feel faster, because
Skia and SDL are highly optimized libraries written in C & C++.

Pixels, Color, Raster
=====================

Now that we've gotten code upgrades out of the way, it's time to learn about
how reasterization works.

Rasterization---turning display lists into pixels---is the main sub-task of
the "draw" rendering step. Skia^[And Tkinter also, of course.] does raster for
us. But so far we just called APIs on those libraries, and didn't really
dig into what is going on at any deeper level. Let's start to do that
now.

As you probably already know, computer screens are a 2D array of pixels. Each
pixel has a color, which looks that way to a human because it emits a mix of
light at different *color channel* frequencies. For example, there could be a
red, green and blue light embedded within the physical pixel at a frequency
closely matching the light-detecting [cones][cones] in a human
eye.[^human-color] And as you learned in physics class, adding together these
colors results in a combined color that, for different values of red, green and
blue, looks like most any color a human can see. The three colors and how they
mix define what is called a *color space*, and the set of colors you can
express from them is called its *gamut*.

[^human-color]: We all take color for granted in our lives. But just as computer
screens simulate colors humans happen to be able to see, the colors we can see
are not random at all, and have to do with the frequencies of light emitted by
the sun, which our brains interpret as color. Color, and human perception of
it, is a very interesting topic.

[cones]: https://en.wikipedia.org/wiki/Cone_cell

Red, green and blue was the approach taken in many computer screens, in
particular monitors from the 80s and 90s using [CRT] technology. Since that was
when the web came into existence, CSS uses a [sRGB] color space derived from
and calibrated for this technology.[^other-spaces] In thos color space, each of
the three color channels (red, green and blue) have a floating-point value
between 0 and 1, with 0 being "off" 1 being "as bright as possible".

[CRT]: https://en.wikipedia.org/wiki/Cathode-ray_tube

[^other-spaces]: Since then, there have been lots of new technologies like LCD,
LED and so on that can achieve different and wider gamuts. And as you would
expect, there are [ways][color-spec] now to express those colors spaces in CSS.

[sRGB]: https://en.wikipedia.org/wiki/SRGB
[color-spec]: https://drafts.csswg.org/css-color-5/

To *raster* pixels, we need to determine the color channel values for each
pixel, which ultimately come from commands in the display list. The first
command in an empty canvas is easy---you just set the color channels directly
in the pixels indicated by the command. But what if a pixel already has a
certain color and then another color is written to it? You might say the answer
is obvious---just change the color to the new color, just as a variable's value
in Python is overwritten when assigned.

That is true for the situations we've seen so far,[^explains] but it gets more
complicated when there is *transparency* "embedded" in the color, or there is
an alternate  blending mode present. Observe that this is nothing
new---the reason you can "add" a green light to a red light a red one on a
computer screen and get one that [looks yellow][mixing] is that they blend
together. In this case there is a kind of transparency to the red light, in
that it lets the green light through it. But if you have a piece of thick red
paper with a thick green paper behind it, the result will look red, because the
paper is opaque. Transparency and blend modes in computer graphics
merely model surfaces we see in the real world.[^mostly-models]

[mixing]: https://en.wikipedia.org/wiki/Color_mixing

[^explains]: This is why we haven't had to bother with understanding blending
until this chapter.

[^mostly-models]: Mostly. Some more advanced blending modes are difficult, or
perhaps impossible, to represent with real-world physics.

So if display list commands write multiple times to the same pixel, the result
will in general be a mix of the colors written. But that's not all. In computer
graphics, it's common to apply blending not command-by-command or
pixel-by-pixel, but in groups, arranged into a tree. Each group is rastered
into a single 2D array of pixels, including its subtree. The the group is
blended into its *parent*. Overall, this happens in a reverse depth-first order
of the tree. The root group is then drawn to the screen.[^not-sequential]

Group-based blending will look different on the screen than individual display
list command-based blending. The difference is a like drawing on stacks of
semi-transparent paper and then holding the stack up to the light. As an
example, consider painting green and red rectangles. If they were both opaque
colors and drew on top of each other in that order on the same
semi-transparent sheet,^[And the rectangle were made transparent by something
about the sheet technology, perhaps by subsequently shaving the paper very
thin.] the resulting color will be a pale red. But the rectangles were on
separate sheets, the result would be be a pale yellow.

[^not-sequential]: Note that we don't simply raster each group individually, and
then do blending. Raster of a group can, and usually does, interleave with
blending of children groups into the parent. This is not nearly as weird or
complicated as it sounds; in our browser we alread encountered it, such as
when the background color of a layout object rasters into its group before the
raster of descendant layout object groups blend on top.

On the web, the groups are [*stacking contexts*][stacking-context], which are
the layout object subtrees of a layout object for DOM elements with certain
styles, up to any descendants that themselves have such styles. Since stacking
contexts are quite complicated to define and maintain, we'll skip that
complexity in this chapter and simply consider every layout object a stacking
context. This simplification is good enough for understanding all the concepts.

[stacking-context]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Positioning/Understanding_z_index/The_stacking_context

With this simplication, the layout object tree has one raster group for each
layout object, and the display list commands that raster the group are the
ones added during the call to `paint()` on that layout object.

Surfaces and canvases
=====================

The 2D pixel array for a group is called a *surface*.[^or-texture] Conceptually,
each layout object will now have its own surface,[^more-than-one] and perform a
blending operation when being drawn into the surface for its parent.
A *canvas*, on the other hand, is an API interface for drawing into a surface.
As you've seen, Tkinter has a canvas API, and so does Skia. The `with surface
as canvas` Python code pattern we've been using for Skia makes this even more
clear---in this case, the canvas is a temporary object created for the duration
of the `with` construct that, when its API methods are called, affect the
pixels in the surface.

[^more-than-one]: A layout object can have more than one surface, actually.
For the cases we'll see in this chapter, it's possible to optimize most or all
of these extra surfaces, but we won't do that in cases where it gets in the
way of understanding blending.

In practice, however, new surfaces are only created when needed to perform
non-standard blending. For example, up to this point in the book, we could draw
the entire browser with only one surface. It's important to avoid creating
surfaces unless necessary, because it'll use up a ton of memory on complex
pages. 

[^or-texture]: Sometimes they are called *bitmaps* or *textures* as well, but
these words connote specific CPU or GPU technologies for implementing surfaces.

In Skia, surfaces are recursive and form a stack.[^tree] You can push a new
surface on the stack, and pop one off. To push a surface, you call
`BeginLayer()` on a canvas.[^layer-surface] Parameters passed to this method
indicate the kind of blending that is desird when popped. To pop, call
`Restore()`. Skia will keep track of the stack of surfaces for you, and perform
blending when you call `Restore()`. (In fact, the only surface we'll create
explicitly is `Browser.skia_surface`).

[^layer-surface]: It's called `BeginLayer` instead of `BeginSurface` because Skia
doesn't actually promise to create a surface. It will in fact optimize away
surfaces internally if it can. So what you're really doing with `BeginLayer` is
telling Skia that there is a new conceptual layer ("piece of paper") on the
stack. How Skia does the rest is an implementation detail (for now!).

[^tree]: A stack and a tree are very similar---the tree is a representation of
the push/pop sequences when executing commands on the stack in the course of
a program's execution.

As we'll see shortly, Skia also has canvas APIs for performing common operations
like clipping and transform---for example, there is a `rotate()` method
that rotates the content on the screen. Once you call a method like that,
all subsequent canvas commands are rotated, until you tell Skia to stop. The
way to do that is with `Save()` and `Restore()`---you call `Save()` before
calling `rotate()`, and `Restore()` after. `Save()` means "remember the current
rotation, clip, etc. state of the canvas" and `Restore()` rolls back to the
last snapshot.

You've probably noticed that `Restore()` is used for both saving state and
pushing layers---what gives? That's because there is a combined stack of layers
and state in the Skia API. Transforms and clips sometimes do actually require
new surfaces to implement correctly, so in fact when we use `Save` it's
actually just a shortcut for `SaveLayer` that is often more efficient. The rule
of thumb is: if you don't need a non-standard blend mode, then you can use
`Save`, and you should always perfer `Save` to `SaveLayer` all things being
equal.

Size and transform
==================

At the moment, block elements size to the dimensions of their inline and input
content, and input elements have a fixed size. But real web sites often have
multiple layers of visuals on top of each other; we'll be adding just such a
feature to the guest book.[^also-compositing] To achieve that kind of look,
we'll need to add support for sizing and transforms. Sizing allows you to set a
block elements[^not-inline] width and height to whatever you want (not just the
layout size of descendants), and transform allows you to move it around on
screen from where it started out.

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
properties, such as [`overflow`][overflow-prop], to control what to do with
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

Now let's add (2D) transforms.[^3d-matrix] In computer
graphics, a linear transform is a transformation of a point in space
represented by multiplication of the point as a (x,y,z,1) vector by a
[4x4 matrix][44matrix]. The same concept exists on the web in the `transform`
CSS property. This property specifies a transform for the contents of a
layout object when drawing to the screen.

[44matrix]: https://en.wikipedia.org/wiki/Transformation_matrix

[^3d-matrix]: 3D is also supported in real browsers , but we'll only discuss 2D
matrices in this chapter. There is a lot more complexity to 3D transforms
having to do with the definition of 3D spaces, flatting, backfaces, and plane
intersections.

[^except-scrolling]: The only exception is that transforms contribute to
[scrollable overflow](https://drafts.csswg.org/css-overflow/#scrollable),
though we won't implement that here.

By default, the origin of the coordinate space in which the transform applies is
the center of the layout object's box.[^transform-origin] The transform matrix
specfied by the `transform` property [maps][applying-a-transform] each of the
four points to a new 2D location. You can also roughly think of it also doing
the same for the pixels inside the rectangle.[^filter-transform]

[^transform-origin]: As you might expect, there is a CSS property called
`transform-origin` that allows changing this default.

[applying-a-transform]: https://drafts.csswg.org/css-transforms-1/#transform-rendering

[^filter-transform]: In reality, the method of rasterng mapping a canvas across
a transform is a nuanced topic. Generating high-quality results without visible
blurring or distortion in these situations involves a number of considerations,
such as the choice of filtering algorithms, and how to handle pixels near the
edges. We won't discuss any of that here.

Transforms are almost entirely a visual effect, and do not affect layout.
[^except-scrolling] 

This example:

    <div style="width:191px; height:191px;
        transform:rotate(10deg);background-color:lightblue">
    </div>

renders like this:

<div style="width:191px; height:191px;
        transform:rotate(10deg);background-color:lightblue">
</div>

First let's parse the `transform` property:

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

Then paint it (we need to `Save` before rotating, to only rotate
the element and its subtree, not the rest of the output):

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

For the example above, the display list commands to paint the rotated light
blue `div` are:

``` {.example}
Save()
Rotate()
Restore()
```

The implementation of `Rotate` in Skia looks like this:

``` {.python}
class Rotate:
    def __init__(self, degrees, rect):
        self.degrees = degrees
        self.rect = rect

    def execute(self, scroll, rasterizer):
        paint_rect = skia.Rect.MakeLTRB(
            self.rect.left(), self.rect.top() - scroll,
            self.rect.right(), self.rect.bottom() - scroll)
        (center_x, center_y) = center_point(paint_rect)
        with rasterizer.surface as canvas:
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
Nevertheless, I find it very hard to remember this when programming! when in
doubt work through an example, and remember that the computer is your friend to
test if the results look correct.


Opacity and Compositing
=======================

With sizing and transform, we also now have the ability to make content overlap!
[^overlap-new]. Consider this example of CSS & HTML:[^inline-stylesheet]

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

[^overlap-new]: That's right, it was not previously possible to do this in
our browser. Avoiding overlap is generally good thing for text-based layouts,
because otherwise you might accidentally obscure content and not be able
to read it. But it's needed for many kinds of UIs that need to *layer*
content on top of other content--for instance, to show an overlap menu or
tooltip.

Right now, the blue rectangle completely obscures part of the orange one, and
the orange one does the same to the light blue one. In order to explore
what happens with compositing and blending further, let's make the elements
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

Let's implement `opacity`. The way to do this is to create a new
canvas, draw the content with opacity into it, and then composite that canvas
into the previous canvas. It's a little complicated to think about without
first seeing it in action, so let's do that with Skia. 

Because we'll be adding things other than opacity soon, let's put opacity
into a new function called `paint_visual_effects` that will be called from
the `paint` method of the various layout objects, just like `paint_background`
already is. It returns a `restore_count`, which well get to in a moment.

``` {.python expected=False}
def paint_visual_effects(node, display_list, rect):
    restore_count = 0

    opacity = float(node.style.get("opacity", "1.0"))
    if opacity != 1.0:
        paint = skia.Paint(Alphaf=opacity
        display_list.append(SaveLayer(paint, rect))
        restore_count = restore_count + 1

    return restore_count
```

`BlockLayout`, `InlineLayout` and `InputLayout` all need to call
`paint_visual_effects`. Here is `BlockLayout`:

``` {.python}
class BlockLayout:
    # ...
    def paint(self, display_list, parent_offset_x, parent_offset_y):
        # ...
        restore_count = paint_visual_effects(
            self.node, display_list, rect)

        paint_background(self.node, display_list, rect)

        for child in self.children:
            child.paint(display_list, paint_offset_x, paint_offset_y)
        # ...
        for i in range(0, restore_count):
            display_list.append(Restore(rect))
```

The display list commands for drawing the blue `div` will be:

```  {.example}
Save()
Translate(100, -50)
SaveLayer(0.5)
DrawRect()
Restore()
Restore()
```

What this code does is this: if the layout object needs to be painted with
opacity, create a new canvas that draws the layout object and its descendants,
and then blend that canvas into the previous canvas with the provided opacity.

This makes use of a new display list type, `SaveLayer`. Here
is how it's implemented:

``` {.python}
class SaveLayer:
    def __init__(self, sk_paint, rect):
        self.sk_paint = sk_paint
        self.rect = rect

    def execute(self, scroll, rasterizer):
        with rasterizer.surface as canvas:
            canvas.saveLayer(paint=self.sk_paint)
```

To understand why `canvas.saveLayer()` is the command that does this, and what
it does under the hood, the first thing you have to know that Skia thinks of a
drawing as a stack of layers (like the layers of a cake). You can, at any time,
stop drawing into one layer and either push a new layer on the stack
(via `canvas.saveLayer()`), or pop up to the next lower level via
`restore()`. The words "save" and "restore" are there because all of the state
of the canvas is saved off before pushing the new canvas on on the stack, and
automatically restored when popping.[^save-like-function-call]

[^save-like-function-call]: This is a lot like function calls in Python or many
other computer languages. When you call a function, the local "state"
(variables etc) of the code that calls the function is implicitly saved, and is
available unchanged when the call completes. The *compositing* that occurs during
a `restore` is analogous to how a function return value is set into a local
variable of the calling code.

Let's see how opacity and compositing actually work.

First, opacity: this simply multiplies the alpha channel by the given opacity.

Let's assume that pixels are represented in a `skia.Color4f`, which has three
color properties `fR`, `fG`, and `fB` (floating-point red/green/blue, between 0
and 1), and one alpha property `fA` (floating-point alpha). Alpha indicates the
amount of transparency---an alpha of 1 means fully opaque, and 0 means fully
transparent, just like for `opacity`.[^alpha-vs-opacity]

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
densities of the two canvases are the same, and therefore their pixels overlap
and have a 1:1 relationship. Therefore we can "composite" each pixel in the
popped canvas on top of (into, really) its corresponding pixel in the restored
canvas. Let's call the popped canvas the *source canvas* and the restored canvas the
*backdrop canvas*. Likewise each pixel in the popped canvas is a *source pixel*
and each pixel in the restored canvas is a *backdrop pixel*.

The default compositing mode for the web is called *simple alpha compositing* or
*source-over compositing*.[^other-compositing]
In Python, the code to implement it looks like this:[^simple-alpha]

``` {.python.example}
# Composites |source_color| into |backdrop_color| with simple
# alpha compositing.
# Each of the inputs are skia.Color4f objects.
def composite(source_color, backdrop_color):
    (source_r, source_g, source_b, source_a) = \
        tuple(source_color)
    (backdrop_r, backdrop_g, backdrop_b, backdrop_a) = \
        tuple(backdrop_color)
    return skia.Color4f(
        backdrop_r * (1-source_a) * backdrop_a + source_r * source_a,
        backdrop_g * (1-source_a) * backdrop_a + source_g * source_a,
        backdrop_b * (1-source_a) * backdrop_a + source_b * source_a,
        1 - (1 - source_a) * (1 - backdrop_a))
```

[^other-compositing]: We'll shortly encounter other compositing modes.

Putting it all together, if we were to implement the `Restore` command
ourselves from one canvas to another, we could write the following
(pretend we have
a `getPixel` method that returns a `skia.Color4f` and a `setPixel` one that
sets a pixel color):[^real-life-reading-pixels]

``` {.python.example}
def restore(source_canvas, backdrop_canvas, width, height, opacity):
    for x in range(0, width):
        for y in range(0, height):
            backdrop_canvas.setPixel(
                x, y,
                composite(
                    apply_opacity(source_canvas.getPixel(x, y)),
                    backdrop_canvas.getPixel(x, y)))
```

[^real-life-reading-pixels]: In real browsers it's a bad idea to read canvas
pixels into memory and manipulate them like this, because it would be very
slow. Instead, it should be done on the GPU. So libraries such as Skia don't
make it convenient to do so. (Skia canvases do have `peekPixels` and
`readPixels` methods that are sometimes used, but not for this use case).

[^simple-alpha]: The formula for this code can be found
[here](https://www.w3.org/TR/SVG11/masking.html#SimpleAlphaBlending). Note that
that page refers to premultiplied alpha colors. Skia does not
use premultiplied color representations. Graphics systems sometimes use a
premultiplied representation of colors, because it allows them to skip storing
the alpha channel in memory.

Blending
========

Blending is a way to mix source and backdrop colors together, but is not the
same thing as compositing, even though they are very similar. In fact, it's a
step before compositing but after opacity. Blending mixels the source and
backdrop colors. The mixed result is then composited with the backdrop pixel.
The changes to our Python code for `restore` looks like this:

``` {.python.example}
def restore(source_canvas, backdrop_canvas,
            width, height, opacity, blend_mode):
    # ...
            backdrop_canvas.setPixel(
                x, y,
                composite(
                    blend(
                        apply_opacity(source_canvas.getPixel(x, y)),
                        backdrop_canvas.getPixel(x, y), blend_mode),
                    backdrop_canvas.getPixel(x, y)))
```

and blend is implemented like this:

``` {.python.example}
def blend(source_color, backdrop_color, blend_mode):
    (source_r, source_g, source_b, source_a) = tuple(source_color)
    (backdrop_r, backdrop_g, backdrop_b, backdrop_a) = \
        tuple(backdrop_color)
    return skia.Color4f(
        (1 - backdrop_a) * source_r +
            backdrop_a * apply_blend(
                blend_mode, source_r, backdrop_r),
        (1 - backdrop_a) * source_g +
            backdrop_a * apply_blend(
                blend_mode, source_g, backdrop_g),
        (1 - backdrop_a) * source_b +
            backdrop_a * apply_blend(
                blend_mode, source_b, backdrop_b),
        source_a)
```

There are various algorithms `blend_mode` could take. Examples include "multiply",
which multiplies the colors as floating-point numbers between 0 and 1,
and "difference", which subtracts the darker color from the ligher one. The
default is "normal", which means to ignore the backdrop color.

``` {.python.example}
# Note: this code assumes a floating-poit color channel value.
def apply_blend(blend_mode, source_color_channel,
                backdrop_color_channel):
    if blend_mode == "multiply":
        return source_color_channel * backdrop_color_channel
    elif blend_mode == "difference":
        return abs(backdrop_color_channel - source_color_channel)
    else
        # Assume "normal" blend mode.
        return source_color_channel

```

These are specified with the `mix-blend-mode` CSS property. Let's add support
for [multiply][mbm-mult] and [difference][mbm-diff] to our browser. Let's modify
the previous example to see how it will look:[^isolation]

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
`<html>` element, even thoiugh web pages have a default white background. This
is because `mix-blend-mode` is defined in terms of stacking contexts (see below
for more on that topic).

Here you can see that the intersection of the orange and blue
[^note-yellow] square renders as pink. Let's work through the math to see
why. Here we are blending a blue color with orange, via the "difference" blend
mode. Blue has (red, green, blue) color channels of (0, 0, 1.0), and orange
has (1.0, 0.65, 0.0). The blended result will then be (1.0 - 0, 0.65 - 0, 1.0 -
0) = (1.0, 0.65, 1.0), which is pink.

[^note-yellow]: The "difference" blend mode on the blue redctangle makes it look
yellow over a white background!

Implementing these blend modes in our browser will be very easy, because Skia
supports these blend mode natively. It's as simple as parsing the property and
adding a parameter to `SaveLayer`:

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

::: {.further}
CSS has a concept that is similar in many ways to Skia's nexted canvases,
called a *stacking context*. If an element *induces a stacking context*,
it means that that element and its descendants (up to any descendants that
themselves induce a stacking contexts) paint together into one contiguous group.
That means a browser can paint each stacking context into its own
canvas, and composite & blend those canvses together in a hierarchical
manner (hierarchical in the same way we've been using `saveLayer` and
`restore` in this capter) in order to generate pixels on the screen.

The `mix-blend-mode` CSS property's [definition][mix-blend-mode-def] actually
says that the blending should occur with "the stacking context that contains
the element" (actually, it's even more complicated---earlier sibling stacking
contexts also blend, which is why the blue and orange squares in the example
above blend to pink). Now that you know how saving and resoring canvases work,
you can see why it is defined this way. This also explains why I had to put an
explicit white background on the `<html>` element, because that element always
induces a [stacking context][stacking-context] in a real browser.

Most stacking contexts on the web don't actually have any non-normal blend modes
or other complex visual effects. In those cases, these stacking contexts don't
actually require their own canvases, and real browsers take advantage of this
to reuse canvases thereby save time and memory. In these cases, the above
definition for properties like `mix-blend-mode` are therefore overly strict.
However, there is a tradeoff betweeen memory and speed for complex
visual effects and animations in general, having to do with maximal use of
the GPU---sometimes browsers allocate extra GPU canvases on purpose to speed up
content, and sometimes they do it because it's necessary to perform multiple
execution passes on the GPU for complex visual effects.

There is now a [backdrop root][backdrop-root] concept for some features that
generalizes beyond stacking contexts, but takes into account the need for
performant use of GPUs.
:::

[mix-blend-mode-def]: https://drafts.fxtf.org/compositing-1/#propdef-mix-blend-mode
[stacking-context]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Positioning/Understanding_z_index/The_stacking_context
[backdrop-root]: https://drafts.fxtf.org/filter-effects-2/#BackdropRoot

Non-rectangular clips
=====================

When we added support for images, we also had to implement clipping in case
the image was larger than the layout object bounds. In that case, the
clip was to a rectangular box. But there is no particular reason that the clip
has to be a rectangle. It could be any 2D path that encloses a region and
finishes back where it staretd.

One way this is expressed in CSS is with the `clip-path` property. The
[full definition](https://developer.mozilla.org/en-US/docs/Web/CSS/clip-path)
is quite complicated, so as usual we'll just implement a simple subset.
In this case we'll only support the `circle(XX%)` syntax, where XX is a
percentage and defines the radius of the circle. The percentage is calibrated
so that if the layout object was a perfect square, a 100% circle would inscribe
the bounds of the square.

Let's apply a circular mask to our image example:

    <div style="width:256px; height:256px;
        clip-path:circle(50%);background-image:
        url('/avatar.png')">
    </div>

Which paints like this:

<div style="width:256px;height:256px;clip-path:circle(50%);background-image:url('/avatar.png')">
</div>

Implementing circular clips is once again easy with Skia in our back pocket.
We just parse the `clip-path` CSS property:

``` {.python}
def parse_clip_path(clip_path_str):
    if clip_path_str.find("circle") != 0:
        return None
    return int(clip_path_str[7:][:-2])
```

and paint it:

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
            return 1
    return 0
```

`CircleMask` is new, and means "clip the content to a circle".^[It's called
"mask" because masking is the generalization of clipping. A mask can be
 an arbitrary bitmap that need not be closed or define any specific shape.]
The only tricky part is how to implement the `CircleMask` class. This will use a
new compositing mode called [destination-in][dst-in]. It is defined
as the backdrop color multiplied by the alpha channel of the source color.
The circle drawn in the code above defines a region of non-zero
alpha, and so all pixels fo the backdrop not within the circle will become
transparent black.

[dst-in]: https://drafts.fxtf.org/compositing-1/#porterduffcompositingoperators_dstin

Here is the implementation in Python:

``` {.python expected=False}
def composite(source_color, backdrop_color):
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
creates a new source canvas via `saveLayer` (and at the same time specifying a
`kDstIn` blend mode for when it is drawn into the backdrop), then draws a
circle in white (or really any opaque color, it's only the alpha channel that
matters) and increments the restore count.


``` {.python}
class CircleMask:
    def __init__(self, cx, cy, radius, rect):
        self.cx = cx
        self.cy = cy
        self.radius = radius
        self.rect = rect

    def execute(self, scroll, rasterizer):
        with rasterizer.surface as canvas:
            canvas.saveLayer(paint=skia.Paint(
                Alphaf=1.0, BlendMode=skia.kDstIn))
            canvas.drawCircle(
                self.cx, self.cy - scroll,
                self.radius, skia.Paint(Color=skia.ColorWHITE))
```

Finally, we call `paint_clip_path` for each layout object type. Note however
that we have to paint it *after* painting children, unlike visual effects
or backgrounds. This is because you have to paint the other content into the
backdrop canvas before drawing the circle and applying the clip. For
`BlockLayout`, this is:

``` {.python}
    def paint(self, display_list, parent_offset_x, parent_offset_y):
        # ...

        for child in self.children:
            child.paint(display_list, paint_offset_x, paint_offset_y)

        paint_clip_path(self.node, display_list, rect)

        for i in range(0, restore_count):
            display_list.append(Restore(rect))
```

But we're not quite done. We still need to *isolate* the element and its
subtree, in order to apply the clip path to only these elements, not to the
entire backdrop. To achieve that we add an extra `saveLayer` in
`paint_visual_effects`:

``` {.python}
def paint_visual_effects(node, display_list, rect):
    # ...

    clip_path = node.style.get("clip-path")
    if clip_path:
        display_list.append(SaveLayer(skia.Paint(), rect))
        restore_count = restore_count + 1
```

This technique described here for implementing `clip-path` is
called *masking*---drawing an auxilliary canvas and reject all pixels of the
main that don't overlap with the auxilliary one. The circle in this case is the
mask image. The
[`mask`](https://developer.mozilla.org/en-US/docs/Web/CSS/mask) CSS property is
another a way to do this, for example by specifying an image at a URL that
supplies the mask bitmap.

While the `mask` CSS property is relatively uncommonly used (as is `clip-path`
actually), there is a special kind of mask that is very common: rounded
corners. Now that we know how to implement masks, this one is also easy to
add to our browser. Because it's so common in fact, Skia has special-purpose
methods to draw rounded corners: `clipRRect`.

Rounded corners are specified in CSS via `border-radius`. Example

    <div style="width:256px; height:256px;
        border-radius: 20px;background-image:url('/avatar.png')">
    </div>

Which paints like this:

<div style="width:256px; height:256px;border-radius:20px;background-image:url('/avatar.png')">
</div>

This call will go in `paint_visual_effects`:

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

    def execute(self, scroll, rasterizer):
        with rasterizer.surface as canvas:
            canvas.clipRRect(
                skia.RRect.MakeRectXY(
                    skia.Rect.MakeLTRB(
                        self.rect.left(),
                        self.rect.top() - scroll,
                        self.rect.right(),
                        self.rect.bottom() - scroll),
                    self.radius, self.radius))
```

Now why is it that rounded rect clips are applied in `paint_visual_effects`
but masks and clip paths happen later on in the `paint` method? What's going
on here? It is indeed the same, but Skia only optimizes for rounded rects
because they are so common. Skia could easily add a `clipCircle` command
if it was popular enough.

What Skia does under the covers may be equivalent to the clip path
case[^skia-opts], and sometimes that is indeed the case. But in other situations, various
optimizations can be applied to make the clip more efficient. For example,
`clipRect` clips to a rectangle, which makes it esaier for Skia to skip
subsequent draw operations that don't intersect that rectangle,[^see-chap-1]
or dynamically draw only the parts of drawings that interset the rectangle.
Likewise, the first optimization mentiond above also applies to
`clipRRect` (but the second is trickier because you have to account for the
space cut out in the corners).

[^skia-opts]: Skia has many internal optimizations, and by design does not
expose whether they are used to the caller.

[^see-chap-1]: This is basically the same optimization as we added in Chapter
1 to avoid painting offscreen text.

::: {.further}

Rounded corners have an interesting history in computing. Their[inclusion]
[mac-story] into the original Macintosh is a fun story to read, and also
demonstrates how computers often end up echoing reality. It also shows just how
hard it was to implement features that appear simple to us today, due to the
very limited memory, and lack of hardware floating-point arithmetic, of early
personal computers (here's some [example source code][quickdraw] used on early
Macintosh computers to implement this feature).

Later on, floating-point coprocessors, and then over time GPUs, became
standard equipment on new computers. This made it much easier to implement fast
rounded corners. Unfortunately, the `border-radius` CSS property didn't appear in
browsers until around 2010, but that didn't stop web developers from putting
rounded corners on their sites! There are a number of ways to do it even without
`border-radius`; [this video][rr-video] walks through several.

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

Now let's add our first visual effect: background images. A background image is
specified in css via the `background-image` CSS property. Its full syntax has
[many options][background-image], so let's just implement a simple version of
it. We'll support the `background-image: url("relative-url")` syntax, which
says to draw an image as the background of an element, with the given relative
URL.

[background-image]: https://developer.mozilla.org/en-US/docs/Web/CSS/background-image

Here is an example:

    <div style="width:256px;height:256px;background-image:
            url('/avatar.png')">
    </div>

It renders like this:[^exact-size]

<div style="width:256px;height:256px;background-image:url('/avatar.png')"></div>

[^exact-size]: Note that I cleverly chose the width and height of the `div` to
be exactly `256px`, the dimensions of the JPEG image.

To implement this property, first we'll need to load all of the image URLs
specified in CSS rules for a `Tab`. Firt collect the image URLs:

``` {.python}
    def load(self, url, body=None):
        # ...

        image_url_strs = [rule[1]['background-image']
                for rule in self.rules
                if 'background-image' in rule[1]]
```

The same will need to be done for inline styles:

``` {.python}
def style(node, rules, url, images):
    # ...
    if isinstance(node, Element) and "style" in node.attributes:
        pairs = CSSParser(node.attributes["style"]).body()
        image_url_strs = []
        for property, value in pairs.items():
            # ...
            if property == 'background-image':
                image_url_strs.append(value)
```

To make non-relative URLs work, we'll also need to modify the CSS parser,
because these URLs start with "https://" or "http://". Since they contain
the ":" character, this will confuse the parser because it thinks it's the
property-value delimiter of CSS. We can fix that by tracking whether we're
inside a quote---if so, we treat the ":" character as part of a word;
otherwise, not.[^only-single-quote]

[^only-single-quote]: We're only adding support for single quotes here, but
double quotes are accepted in real CSS. Single and double quotes can be
interchanged in CSS and JavaScript, just like in Python.

``` {.python}
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

And then load them. But to load them we'll have to augment the `request`
function to support binary image content types (currently it only supports
`text/html` and `text/css` encoded in `utf-8`). A PNG image, for instance, has
the content type `image/png`, and is of course not `utf-8`, it's an encoded PNG
file. To fix this, we will need to decode in smaller chunks:
the status line and headers are still `utf-8`, but the body encoding depends
on the image type.

First, when we read from the socket with `makefile`, pass the argument
`b` instead of `r` to request raw bytes as output:

``` {.python}
def request(url, headers={}, payload=None):
    # ...
    response = s.makefile("b")
    # ...
```

Now you'll need to call `decode` every time you read from the file.
First, when reading the status line:

``` {.python}
def request(url, headers={}, payload=None):
    # ...
    statusline = response.readline().decode("utf8")
    # ...
```

Then, when reading the headers:

``` {.python}
def request(url, headers={}, payload=None):
    # ...
    while True:
        line = response.readline().decode("utf8")
        # ...
    # ...
```

And finally, when reading the response, we check for the `Content-Type`, and
only decode[^image-decode] it as `utf-8` if it starts with `text/`:

``` {.python}
def request(url, headers={}, payload=None):
    # ...
    if headers.get(
        'content-type', 
        'application/octet-stream').startswith("text"):
        body = response.read().decode("utf8")
    else:
        body = response.read()
    # ...
```

[^image-decode]: Not to be confused with image decoding, which will be done 
later.

Now we are ready to load the images. Each image found will be loaded and stored
in an `images` dictionary on a `Tab` keyed by URL. However, to actually show
an image on the first screen, we have to first *decode* it. Images are sent
over the network in one of many optimized encoding formats, such as PNG or
JPEG; when we need to draw them to the screen, we need to convert from the
encoded format into a raw array of pixels. These pixels can then be efficiently
drawn onto the screen.[^image-decoding]

[^image-decoding]: While image decoding technologies are beyond the
scope of this book, it's very important for browsers to make optimized use
of image decoding, because the decoded bytes are often take up *much* more
memory than the encoded representation. For a web page with a lot
of images, it's easy to accidentally use up too much memory unless you're very
careful.

Skia doesn't come with image decoders built-in. In Python, the Pillow library is
a convenient way to decode images.

::: {.installation}
`pip3 install Pillow` should install Pillow. See [here][install-pillow] for
more details.
:::

[install-pillow]: https://pillow.readthedocs.io/en/stable/installation.html

Here's how to load, decode and convert images into a `skia.Image` object.
Note that there are two `Image` classes, which is a little confusing.
The Pillow `Image` class's role is to decode the image, and the Skia `Image`
class is an interface between the decoded bytes and Skia's internals. Note
that nowhere do we pass the content type of the image (such as `image/png`)
to a Pillow `Image`. Instead, the format is auto-detected by looking
for content type [signatures] in the bytes of the encoded image.

[signatures]: https://en.wikipedia.org/wiki/List_of_file_signatures

``` {.python}
def get_images(image_url_strs, base_url, images):
    for image_url_str in image_url_strs:
        image_url = parse_style_url(image_url_str)
        header, body_bytes = request(
            resolve_url(image_url, base_url),
            headers={})
        picture_stream = io.BytesIO(body_bytes)

        pil_image = Image.open(picture_stream)
        if pil_image.mode == "RGBA":
            pil_image_bytes = pil_image.tobytes()
        else:
            pil_image_bytes = pil_image.convert("RGBA").tobytes()
        images[image_url] = skia.Image.frombytes(
            array=pil_image_bytes,
            dimensions=pil_image.size,
            colorType=skia.kRGBA_8888_ColorType)

    def load(self, url, body=None):
        # ...

        self.images = {}
        get_images(image_url_strs, url, self.images)
```

Next we need to provide access to this image from the `paint` method of a
layout object. Since those objects don't have access to the `Tab`, the easiest
way to do this is to save a pointer to the image on the layout object's node
during `style`:

``` {.python}
def style(node, rules, url, images):
    # ...
    if isinstance(node, Element) and "style" in node.attributes:
        # ...
        get_images(image_url_strs, url, images)
    if node.style.get('background-image'):
        node.background_image = \
            images[parse_style_url(
                node.style.get('background-image'))]
```

Now that the images are loaded, the next step is to paint them into the display
list. We'll need a new display list object called `DrawImage`:

``` {.python}
class DrawImage:
    def __init__(self, image, rect):
        self.image = image
        self.rect = rect

    def execute(self, scroll, rasterizer):
        with rasterizer.surface as canvas:
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

``` {.python}
class BlockLayout:
    # ...
    def paint(self, display_list, parent_offset_x, parent_offset_y):
        # ...
        paint_background(self.node, display_list, rect)
        
        for child in self.children:
            child.paint(display_list, paint_offset_x, paint_offset_y)
```

Here we're not just drawing the image though---we're also doing something
new that we haven't seen before. We are applying a *clip*. A clip is a way
to cut off parts of a drawing that exceed a given set of bounds. Here we are
asking to clip to the rect that bounds the element, because the
image for `background-image`  never exceeds the size of the element.
Clips have to be preceded by a call to `Save`, which says to Skia to 
snapshot the current parameters to the canvas, so that when `Restore` is called
later these parameters (including presence or absence of a clip) can be
restored.[^not-savelayer]

`Save` and `Restore` are implemented like this:

``` {.python}
class Save:
    def __init__(self, rect):
        self.rect = rect

    def execute(self, scroll, rasterizer):
        with rasterizer.surface as canvas:
            canvas.save()

class Restore:
    def __init__(self, rect):
        self.rect = rect

    def execute(self, scroll, rasterizer):
        with rasterizer.surface as canvas:
            canvas.restore()
```

This example should clip out parts of the image:

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

    def execute(self, scroll, rasterizer):
        with rasterizer.surface as canvas:
            canvas.clipRect(skia.Rect.MakeLTRB(
                self.rect.left(), self.rect.top() - scroll,
                self.rect.right(), self.rect.bottom() - scroll))
```

[^not-savelayer]: Note: `Save` is not the same as `SaveLayer` (which will
be introduced later in this chapter). `Save` just saves off parameters;
`SaveLayer` creates am entirely new canvas.

Note how the background image is painted *before* children, just like
`background-color`.[^paint-order]

::: {.further}
Notice that the background image is also drawn after the background
color. One interesting question to ask about this is:
if the image paints on top of the background color, what's the point of 
painting the background color in the presence of a background image? One
reason is *transparency*, which we'll get to in a bit.

Another is that the
background image may not have the same [*intrinsic size*][intrinsic-size] as
the element it's associated with. There are a lot of options
in the specification for the different ways to account for
this, via CSS properties like [`background-size`][background-size] and
[`background-repeat`][background-repeat].

[intrinsic-size]: https://developer.mozilla.org/en-US/docs/Glossary/Intrinsic_Size
[background-size]: https://developer.mozilla.org/en-US/docs/Web/CSS/background-size
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