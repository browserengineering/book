---
title: Adding Visual Effects
chapter: 12
prev: security
next: rendering-architecture
...

Right now our browser can draw text and rectangles of various colors. But
that's pretty boring! Browsers have all sorts of great ways to make content
look great on the screen. These are called *visual effects*---visual because
they affect how it looks, but not how it functions under the hood or lays out.
Therefore these effects are extensions to the *paint* and *draw* parts of
rendering.

Skia replaces Tkinter
=====================

But before we get to how visual effects are implemented, we'll need to upgrade
our graphics system. While Tkinter was great for painting and handling input,
it has no built-in support at all for implementing visual
effects.[^tkinter-before-gpu] And just as implementing the details of text
rendering or drawing rectangles is outside the scope of this book, so is
implementing visual effects---our focus should be on how to represent and
execute visual effects for web pages specifically.

[^tkinter-before-gpu]: That's because Tk, the library Tkinter uses to implement
its graphics, was built back in the early 90s, before high-performance graphics
cards and GPUs became widespread.

So we need a new library that can perform visual effects. We'll use
[Skia](https://skia.org), the library that Chromium uses. However, Skia is just
a library for raster and compositing, so we'll also use
[SDL](https://www.libsdl.org/) to provide windows, input events, and OS-level
integration.

::: {.further}
While this book is about browsers, and not how to implement high-quality
raster libraries, that topic is very interesting in its own right.
(todo: find a reference) and (todo: another one) are two resources you can dig
into if you are curious to learn more about how they work. That being said,
it is very important these days for browsers to work smoothly with the
advanced GPUs in today's devices, so in practice browser teams include experts
in these areas.
:::

To install Skia, you'll need to install the
[`skia-python`](https://github.com/kyamagu/skia-python)
library (via `pip3 install skia-python`); as explained on the linked site, you
might need to install additional dependencies. Instructions
[here](https://pypi.org/project/PySDL2/) explain how to install SDL on your
computer (short version: `pip3 install PySDL2` and `pip3 install pysdp2-dll`).

Once installed, remove `tkinter` from your Python imports and replace them with:

``` {.python}
import ctypes
from sdl2 import *
import skia
```

The additional `ctypes` module is for interfacing between Python types and C
types.

The main loop of the browser first needs some boilerplate to get SDL started:

``` {.python}
if __name__ == "__main__":
    # ...
    SDL_Init(SDL_INIT_VIDEO)
    sdl_window = SDL_CreateWindow(b"Browser",
        SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
        WIDTH, HEIGHT, SDL_WINDOW_SHOWN)

    browser = Browser(sdl_window)
    browser.load(sys.argv[1])
```

In SDL, you have to implement the event loop yourself (rather than calling
`tkinter.mainloop()`). This loop also has to handle input events:

``` {.python}
    running = True
    event = SDL_Event()
    while running:
        while SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == SDL_MOUSEBUTTONUP:
                browser.handle_click(event.button)
            if event.type == SDL_KEYDOWN:
                if event.key.keysym.sym == SDLK_RETURN:
                    browser.handle_enter()
                if event.key.keysym.sym == SDLK_DOWN:
                    browser.handle_down()
            if event.type == SDL_TEXTINPUT:
                browser.handle_key(event.text.text.decode('utf8'))
            if event.type == SDL_QUIT:
                running = False
                break

    SDL_DestroyWindow(sdl_window)
    SDL_Quit()
```

Next let's factor a bunch of the tasks of drawing into a new class we'll call
`Rasterizer`. The implementation in Skia should be relatively
self-explanatory:

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

`DrawText` and `DrawRect` use the rasterizer in the obvious way. For exampe,
here is `DrawText.execute`:

``` {.python}
    def execute(self, scroll, rasterizer):
        rasterizer.draw_text(
            self.rect.left(), self.rect.top() - scroll,
            self.text,
            self.font,
            self.color,
        )
```

Now let's integrate with the `Browser` class. We need a surface[^surface] for
drawing to the window, and a surface into which Skia will draw.

``` {.python}
class Browser:
    def __init__(self, sdl_window):
        self.window_surface = SDL_GetWindowSurface(
            self.sdl_window)
        self.skia_surface = skia.Surface(WIDTH, HEIGHT)
```

Next we need to re-implement the `draw` method on `Browser` using Skia. I'll
walk through it step-by-step. First we make a rasterizer and draw the current
`Tab` into it:

``` {.python}
    def draw(self):
        rasterizer = Rasterizer(self.skia_surface)
        rasterizer.clear(skia.ColorWHITE)

        self.tabs[self.active_tab].draw(rasterizer)
```

Then we draw the browser UI elements:

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

Finally we perform the incantations to save off a rastered bitmap and copy it
from the Skia surface to the SDL surface:

``` {.python}
        # Raster the results and copy to the SDL surface:
        skia_image = self.skia_surface.makeImageSnapshot()
        skia_bytes = skia_image.tobytes()
        rect = SDL_Rect(0, 0, WIDTH, HEIGHT)
        skia_surface = Browser.to_sdl_surface(skia_bytes)
        SDL_BlitSurface(
            skia_surface, rect, self.window_surface, rect)
        SDL_UpdateWindowSurface(self.sdl_window)
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
        return SDL_CreateRGBSurfaceFrom(
            skia_bytes, WIDTH, HEIGHT, depth, pitch,
            red_mask, green_mask, blue_mask, alpha_mask)
```

Finally, `handle_enter` and `handle_down` no longer need an event parameter.

[^surface]: In Skia and SDL, a surface is representation of a graphics buffer
into which you can draw "pixels" (bits representing colors). A surface may or
may not be bound to the actual pixels on the screen via a window, and there can
be many surfaces. A *canvas* is an API interface that allows you to draw
into the surface with higher-level commands such as drawing lines or text. In
our implementation, we'll start with separate surfaces for Skia and SDL for
simplicity.

In the `Tab` class, the differences in `draw` is the new rasterizer parameter
that gets passed around, and a Skia API to measure font metrics. Skia's
`measureText` method on a font is the same as the `measure` method on a Tkinter
font.

``` {.python}
    def draw(self, rasterizer):
        # ...
            x = obj.x + obj.font.measureText(text)
```

Update also all the other places that `measure` was called to use the Skia
method (and also create Skia fonts instead of Tkinter ones, of course).

Skia font metrics are accessed via a `getMetrics` method on a font. Then metrics
like ascent and descent are accessible via:
``` {.python expected=False}
    font.getMetrics().fAscent
```
and
``` {.python expected=False}
    font.getMetrics().fDescent
```

Note that in Skia, ascent and descent are
positive if they go downward and negative if upward, so ascents will normally
be negative.

Now you should be able to run the browser just as it did in previous chapters,
and have all of the same visuals. It'll probably also feel faster, because
Skia and SDL are highly optimized libraries written in C & C++.

Background images
=================

Now let's add our first visual effect: background images. A background image
is specified in css via the `background-image` CSS property. Its true syntax
has many options, but let's just implement a simple version of it. We'll support
the `background-image: url("relative-url")` syntax, which says to draw an image
as the background of an element, with the given relative URL.

We'll implement this by loading all of the image URLs specified in CSS rules
for a `Tab`. Firt we collect the image URLs:

``` {.python}
    def load(self, url, body=None):
        # ...

        image_url_strs = [rule[1]['background-image']
                for rule in self.rules
                if 'background-image' in rule[1]]
```

And then load them. But to load them we'll have to augment the `request`
function to support binary image content types (currently it only supports
`text/html` and `text/css` encoded in `utf-8`). A PNG image has the content
type `image/png`, and is of course not `utf-8`, it's an encoded PNG file.
Adding this support is pretty easy. When reading the response, first read the
headers, then check for the `content-type header`, and if it's not HTML
or CSS then don't decode it and instead return the raw bytes:
``` {.python}
    if not 'content-type' in headers or \
        headers['content-type'] in ['text/html', 'text/css']:
        body = response.read()
    else:
        # binary data
        body_length = int(headers['content-length'])
        chunk_size = 2**14
        body = s.recv(chunk_size)
        while len(body) < body_length:
            body = body + s.recv(chunk_size)
```

Now we are ready to load the images. Each image found will be loaded and
stored into an `images` dictionary on a `Tab` keyed by URL. To load an image
we have to first *decode* it. Images are sent over the network in one of many
encoding formats, such as PNG or JPEG; when we need to draw them to the screen,
we need to convert from the encoded format into a raw array of pixels. These
pixels can then be efficiently drawn onto the screen.

Skia doesn't come with image decoders built-in. In Python, the Pillow library is
a convenient way to decode images.

::: {.installation}
`pip3 install Pillow` should install Pillow. See [here][install-pillow] for
more details.
:::

[install-pillow]: https://pillow.readthedocs.io/en/stable/installation.html

Once decoded, its output can then be converted into a byte stream and drawn
into a canvas with Skia, like this:

``` {.python}
    def load(self, url, body=None):
        # ...

        self.images = {}
        for image_url_str in image_url_strs:
            image_url = parse_style_url(image_url_str)
            header, body_bytes = request(
                resolve_url(image_url, url),
                headers=req_headers)
            picture_stream = io.BytesIO(body_bytes)

            pil_image = Image.open(picture_stream)
            self.images[image_url] = skia.Image.frombytes(
                array=pil_image.tobytes(),
                dimensions=skia.ISize(
                    pil_image.width, pil_image.height))
```

Next we need to provide access to this image from the `paint` method of a
layout object. Since those objects don't have access to the `Tab`, the easiest
way to do this is to save a pointer to the image on the layout object's node
during `style`:

``` {.python}
def style(node, rules, images):
    # ...
    if node.style.get('background-image'):
        node.backgroundImage = \
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
                self.image, self.rect.top(),
                self.rect.left() - scroll)
```

Some code that draws the background for a node into a display list; here
we also paint `background-color`:[^paint-order]

``` {.python}
def paint_background(node, display_list, rect):
    bgcolor = node.style.get("background-color",
                                  "transparent")
    if bgcolor != "transparent":
        display_list.append(DrawRect(rect, bgcolor))

    background_image = node.style.get("background-image")
    if background_image:
        display_list.append(DrawImage(node.backgroundImage,
            rect))

```

And finally some code to paint the background image for each layout object
type. For `BlockLayout`: it's

``` {.python expected=False}
class BlockLayout:
    # ...
    def paint(self, display_list):
        # ...
        paint_background(self.node, display_list, rect)
        
        for child in self.children:
            child.paint(display_list)
```

Note how the background image is painted *before* children, just like
`background-color`.

::: {.further}
Notice that the background image is drawn after the background
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

To add even more complication, in its full generality the *paint order* of
drawing backgrounds and other painted aspects of a single element, and the
interaction of its paint order with painting descendants, is
[quite complicated][paint-order-stacking-context].
:::

[paint-order-stacking-context]: https://www.w3.org/TR/CSS2/zindex.html

Size and position
=================

Next let's add a way to set the width and height of block and input elements.
Right now, block elements size to the dimensions of their inline and input
content, and input elements have a fixed size. But we're not just displaying
text and forms any more---now that we're drawing visual effects such as colors,
images and so on. So we should be able to do things like draw a rectangle
of a given color on the screen. That is accomplished with the `width` and
`height` CSS properties.

Support for these properties turns out to be easy---if the property is set, use
it, and otherwise use the built-in sizing. For `BlockLayout`:

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
        self.width = style_length(self.node, "width", INPUT_WIDTH_PX)
        self.height = style_length(
            self.node, "height", linespace(self.font))
```

Great. We can now draw rectangles of a specified width and height. But they
still end up positioned one after another, in a way that we can't control.
It'd be great to be able to put the rectangle anywhere on the screen. That
can be done with the `position` CSS property. This property has a whole lot
of complexity to it, so let's just add in a simplistic subset:
`position:absolute`[^posabs-caveat]

[^posabs-caveat]: Actually, we'll implement a hacky approximation to
`position:absolute`. In reality, `position:absolute` elements are not
positioned according relative to the root element, but the "containing"
positioned elements.

Visual effects
==============

Browsers can not only draw text and colored boxes to the screen, but can apply
various visual effects to those boxes and text. A visual effect in HTML is one
that does not affect layout (see chapter 5), but does affect how pixels are
drawn to the screen.

Before getting to those effects, we first need to discuss colors, how they are
specified, and how this translates to the color of a pixel on a computer
screen. Colors are specified on a computer via a particular choice of color
space. A color space is a specific organization of colors, comprising a
mathematical color model and a mapping function to other color spaces or
computer screen technologies. The default color space of the web is [sRGB]
(srgb); even now, most browsers only support sRGB[^1], though newer screen
technologies are starting to support a much wider range of visible colors
outside of the sRGB [gamut](gamut). sRGB was defined in the 90s for the
purposes of drawing to the monitor technologies of the time, as well as
defining colors on the Web. 

[srgb]: https://developer.mozilla.org/en-US/docs/Web/CSS/color_value
[gamut]: https://en.wikipedia.org/wiki/Gamut

[^1]: Except for images and video, which can be encoded in different color
spaces, and are converted to a common color space by the browser.

sRGB in CSS is quite straightforward. There are three color channels: red, green
and blue. “s” stands for “standard”. Each has a one-byte resolution, and
therefore values between 0 and 255. The mapping function for sRGB is
intuitively simple: the larger the red value, the more red, and likewise green
and blue. Usually, we specify the colors in the order (Red, Green, Blue). For
example, `rgb(255, 255, 255)` is white,
`rgb(0,0,0)` is black, and `rgb(255,0,0)` is red. Cyan is `rgb(0,255,255)`.
The mapping function to screen pixel colors actually used is derived from
specific technology choices of the past and present, and while very
interesting, is beyond the scope of this chapter. It’s important to note only
that the function is nonlinear. While in the examples below it looks linear,
there is also a nonlinear function being applied behind the scenes that maps to
the screen color brightness values.

Opacity
=======

The simplest visual effect is opacity. Opacity is a way to apply transparency to
content drawn to the screen, in the same way that a thin piece of paper has a
certain amount of transparency through which one can look at objects behind it.
The equivalent on a computer screen is that one bitmap B is drawn, and then
another A is drawn on top, and their pixels in common are interpolated between
the colors of B and A. The interpolation parameter is called alpha, which is a
real number in `[0, 1]`. For a particular pixel, the final color is computed with
this formula:

    blend(B, A) = (Color from B) * (1-alpha_A) * alpha_B + (color from A) * alpha_A

where `alpha_{A, B}` is a number in `[0, 1]` (remember that both A and B can
have opacity!).

One source of opacity is an additional “alpha channel” of a color. For example,
the color from a pixel of A might be rgba(0, 255, 255, 64), which is cyan with
an alpha of 64/255 = 0.25. If the color from B in the example above was also
`rgb(255, 0, 0, 255)`, then the above equation would become:

    blend(B, A) = rgb(255, 0, 0) * 0.75 * 1 + rgb(0, 255, 255) * 0.25 = rgb(191, 191, 191)

Note that each channel averages according to alpha independently. If three or
more bitmaps are drawn to the screen, then the final pixel is the result of
blending pairwise in sequence. For example, if the bitmaps are C, B and A, in
that order, the final pixel value is `blend(C, blend(B, A))`.

You might also be wondering: what happens if all of the colors have an alpha
value less than 1? Is that allowed? Yes it is allowed, and blend() will always
output an RGB value that can be interpreted by the computer (worst case
scenario, the monitor can just ignore a residual alpha, since there is no such
concept in an LED pixel). However, it doesn’t make sense - in almost all cases
at least - for web pages to blend with windows behind them in the OS; for that
reason, browsers always paint a white backdrop behind everything. (You can even
see the specification text for it [here](root-group)!)

[root-group]: https://drafts.fxtf.org/compositing-1/#rootgroup

Paint order
===========

The next thing to know is that content on the web draws to the screen in a
particular order. When display list entries’ drawn outputs don’t overlap, it’s
not necessary to specify what the order is, because it doesn’t matter, which is
why paint order was not necessary for Chapter 2. If not, then it does, since we
need to figure out what color is on top, as well as the inputs to the sequential
blend() functions. Paint order on the web is a complicated topic with a number
of special rules and ways for the web page to force certain elements to paint
in a different order. For the purposes of this chapter, it’s most important to
start with two facts:

 - The HTML elements *do not* paint in a simple tree order such as depth-first
   or breadth-first.
 - The elements are painted in contiguous groups called stacking contexts. Each
   stacking context consists of the complete painted output of all of the
   elements that are part of the stacking context. The stacking contexts draw to
   the screen in a well-defined order.

For the purpose of understanding all of the visual effects described in this
chapter[^2], you can forget about how stacking contexts are painted, and that
they ultimately come from laying out and painting boxes and text, and just focus
on the bitmaps generated by executing the display list of the stacking context.
From now on, when I say “stacking context”, I will almost always refer to that
bitmap.

::: {.further}
See [here](stacking-context) for more information on the rules for stacking
contexts and [here](paint-order) for the gory details of the basic rules for
paint order. Interestingly enough, even these descriptions are out of date. The
exact behavior of painting in browsers is somewhat under-specified.
:::

[stacking-context]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Positioning/Understanding_z_index/The_stacking_context
[paint-order]: https://www.w3.org/TR/CSS21/zindex.html

Stacking contexts also form a tree[^3]. Each stacking context S has a display
list and a list of child stacking contexts. Each of the children has a z-index,
which is an integer. Child stacking contexts with a z-index less than zero paint
before S (and in the order of their z-index, starting with most negative); the
others paint after (and in the order of their z-index, starting with lowest). In
pseudocode it looks like:

[^2]: In reality, rounded corners and certain clips can and often do apply to
non-stacking contexts. This was perhaps the single biggest mistake made when
designing the painting algorithms of the web in the past, and leads to an
enormous amount of complexity in real-world browser implementations. After
reading this chapter, can you guess why?

[^3]: In fact, his tree is of the same shape as the HTML node tree, because a
stacking context always starts at a node with a
[“stacking context-inducing”](stacking-context) style and includes all
descendants that are not stacking contexts.

``` {.javascript}
function paint(stacking_context) {
    let bitmap = (black fully transparent bitmap)
    /* blend negative-z-index children */
    For negative_child in stacking_context.negative_z_index_children_sorted()
        bitmap = blend(bitmap, paint(negative_child), blending_operation(negative_child))

    /* draw self with default blending. The blend mode of self will apply when drawing
       into the parent */ 
    bitmap = blend(bitmap, draw_into_bitmap(stacking_context))

    /* blend nonnegative-z-index children */
    For nonnegative_child in stacking_context.nonnegative_z_index_children_sorted()
        bitmap = blend(bitmap, paint(nonnegative_child), blending_operation(nonnegative_child))
    
    /* return result to be blended into parent */
    return bitmap
}

/* final_bitmap will be what is seen on the screen */
Let final_bitmap = paint(root stacking context (i.e. the stacking context for the `<html>` element))
```

We’ll study various different values for `blending_operation()`; so far you have
already seen the simplest one - opacity.

Blend-mode
==========

Blend modes allow for various blending operations other than opacity. The blend
modes are based on the “Porter Duff” operators, first defined in a
[research paper](porter-duff) in 1984[^4]. The [specification](compositing-1)
does a pretty good job of explaining the various blend modes, you can read more
there, including seeing examples. The intuitive “draw one bitmap on top of
another” method we’ve discussed already in this chapter is called
[“source over”](src-over) in blend-mode terminology;
[“destination over”](dst-over) means to draw them in the opposite order. Another
important one is [“destination in”](dst-in). We’ll use this later to explain how
 clipping works. The other basic blend modes are less commonly encountered.

[porter-duff]: http://graphics.pixar.com/library/Compositing/paper.pdf
[compositing-1]: https://drafts.fxtf.org/compositing-1/#porterduffcompositingoperators
[src-over]: https://drafts.fxtf.org/compositing-1/#porterduffcompositingoperators_srcover
[dst-over]: https://drafts.fxtf.org/compositing-1/#porterduffcompositingoperators_dstover
[dst-in]: https://drafts.fxtf.org/compositing-1/#porterduffcompositingoperators_dstin

[^4]: Porter and Duff worked at Lucasfilm, the film company that produced the
origial Star Wars movies.

Source over blend-mode is the default; let’s specify other blend modes with an
additional parameter to blend():

    blend(B, A, destination-in) = ...

In prose, this means to output a bitmap that is the pixels of B that overlap A.
Additional blend modes exist that combine a Porter Duff blend mode with additional features, such as transparency or other color manipulations. For historical reasons, [opacity] is represented as special and listed in a different spec, but otherwise functions [the same](opacity-blending) as the other blend modes. In addition, there are [“non-separable”](non-separable) blend modes where the color channels influence one another, such as hue, saturation, color and luminosity.

[opacity]: https://drafts.csswg.org/css-color/#transparency
[opacity-blending]: https://drafts.csswg.org/css-color/#alpha
[non-separable]: https://drafts.fxtf.org/compositing-1/#blendingnonseparable

Another subtle point to consider is that blending always occurs between a
stacking context and the stacking context parent. Even though the specification
uses the term “backdrop”, blending does *not* apply to the entire “backdrop”
behind a stacking context, meaning all things you could see in place of that
stacking context if it was invisible. There are good reasons that web designers
want to apply the latter semantics (in fact, this is what tools like Photoshop
often do), but as we will see later, this would come at a high performance cost,
so the web uses a different definition.

Opacity vs alpha?
=================

You might also be wondering what the difference is between opacity and alpha.
The answer is that they are very similar, but not quite the same thing. Opacity
is a visual effect that applies alpha to a stacking context when blending it
with its parent stacking context. Alpha is transparency within a bitmap. When
blending a bitmap with 0.5 alpha into its ancestor via source-over transparency,
the result is equivalent to blending the same bitmap but without alpha and with
an 0.5 opacity blend mode. Another way to look at it is that alpha has opacity
already baked into the bitmap (and also alpha can vary pixel-by-pixel), whereas
opacity is a single floating-point value that is applied as a visual effect.

Filters
=======

[Filters](filters) are a way to apply a wider variety of pixel-manipulation
algorithms. A good example is a blur filter. This applies a blurring effect,
where pixels near each other influence each other's colors in a way that looks
similar to blurry eyesight. Pixels are also “spread out” according to the radius
of the blur.

[filters]: https://drafts.fxtf.org/filter-effects/#FilterPrimitivesOverviewIntro

Filters can be somewhat expensive to compute. In addition, filters such as blur
cause a lot of headache in browser implementations, because of the spreading-out
behavior. This makes it difficult to know the true size of the painted region
of an element in many cases, which as we will see is very important to get
right for fast and correct implementations on GPU hardware.

Backdrop filter
===============

There is a special kind of filter called a backdrop filter. Backdrop filters
apply an effect sometimes called the “glass effect”, where the content behind
the glass has a filter, such as blur, applied to it, but content in front of the
glass does not. An effect like this is present in some OS window managers; some
versions of Windows offer it for example.

Backdrop filters ideally should apply to the entire backdrop of a stacking
context S. This means that if you computed the pixels drawn by all stacking
contexts that paint *before* S, and looked at the pixels that
intersect S, those pixels comprise S’s backdrop. Unfortunately this definition
of backdrop has multiple [problems](backdrop-root-problems) with it, including:

 - Performance: It’s expensive to read back some of the pixels of a GPU texture
   partway through drawing, because it interferes with the pipelining and
   parallelism that makes GPUs fast.
 - That the definition of backdrop is otherwise circular and therefore
   ill-defined.

[backdrop-root-problems]: https://drafts.fxtf.org/filter-effects-2/#BackdropRootMotivation

For these reasons, backdrop filters filter only the backdrop up to the [backdrop
root](backdrop-root).

[backdrop-root]: https://drafts.fxtf.org/filter-effects-2/#BackdropRoot

::: {.further}
Think carefully about the definition of the backdrop root and how backdrop
filters work, and work through some examples. This will give you some idea of
the complexity of the problem space.
:::

As mentioned above, other blend-modes and filters only blend with the stacking
context parent; you might be wondering why they don’t blend up to the backdrop
root. The reason is merely historical, and this may change in the future.

Clips
=====

Clips are the way to cut out parts of content that are outside of a given set of
bounds. There are two common reasons to do this:

 - Avoiding content being larger on the screen than desired (this use-case is
   called “clipping overflow”)
 - Applying visual flourish, such as rounded corners or other shapes

Let’s pretend that clips always apply to stacking contexts. (On the web this is
unfortunately often not true, but the consequences are much too complicated to
discuss here, and not relevant to the description of *how* clips work.)

To start, let’s consider a simple rectangular clip. The inputs are a stacking
context A and a rectangle. The rectangle has a size and position relative to the
corner of the stacking context (remember, in this chapter, “stacking context”
and “bitmap” are the same). The output of the clipping operation is another
bitmap. This bitmap is then blended with the parent stacking context B of A. In
equation form this is:

    Output = blend(B, clip(A, clip_rect_A))

The clip() operation can be viewed as a kind of blend, as long as the rectangle
is re-interpreted as an opaque bitmap of the same size and position as the
rectangle:

    Output = blend(B, blend(A, clip_rect_A, destination-in), source-over)

Remember that from the blend-mode section, blend(A, clip_rect_A, destination-in)
means to draw “the pixels of A that overlap clip_rect_A”, which of course is the
result of clipping A to the rectangle. This formulation also hints at an
implementation approach: convert the rectangle to a bitmap  (by drawing it into
one) and blend it with A via destination-in.

The second most common kind of clipping is rounded corners. From the formulation
we just discussed, it’s simple to see how to generalize rectangular clips to
rounded corners: when drawing the bitmap for the rectangle, exclude the parts
outside of the rounded corners. By “exclude”, I mean set the alpha channel to 0
for that pixel. For pixels that are adjacent to the edge of a rounded corner
curve, anti-aliasing techniques can be used to supply an alpha value somewhere
between 0 and 1 according to their overlap with the curve.

Other clips can use the same technique, but more complex shapes when generating
the clip bitmap.

2D Transforms
=============

Stacking contexts can also be transformed in 2D (or 3D, which we’ll get to in
the next section). This is done by considering a stacking context as a rectangle
in a 2D space and [applying a transform](applying-a-transform) to it, which
means multiplying the coordinates of the rectangle’s four corners by the matrix.
Note that the resulting polygon - called a “quad” in graphics still has four
corners and straight sides, but may no longer be a rectangle, or the sides may
no longer be horizontal or vertical. Similarly, the contents of the stacking
context are also transformed accordingly, and due to the linearity of the
transform always end up inside the quad.

[applying-a-transform]: https://drafts.csswg.org/css-transforms-1/#transform-rendering

The process of drawing a stacking context A with a transform into its ancestor B
looks like this:

    blend(B, transform(A))

Here `transform(A)` is a different bitmap, that may be generated with an
algorithm similar to this:

 - For each pixel P of A, compute its transformed location. Blend in the color
   of the pixels next to the transformed location according to their closeness
   to it.
 - Other pixels that are not next to one mapped to from A are transparent.
Note also that adjacent pixels don’t overwrite each other when they conflict,
they add/blend [^5]. Further, we haven’t discussed it much, but there is also the
question of the size and shape of transform(A). The answer is that it’s sized to
the [axis-aligned bounding box](axis-aligned-bounding-box) of the transformed
polygon. The “axis” in the previous sentence is the orientation of B’s stacking
context.

[^5]: In reality, the method of generating the bitmap transform(A) is a nuanced
topic. Generating high-quality bitmaps in these situations involves a number of
considerations, such as bilinear or trilinear filtering, and how to handle
pixels near the edges.

[axis-aligned-bounding-box]: https://en.wikipedia.org/wiki/Bounding_volume

::: {.further}
We never discussed how to generate the bounds of the bitmap of a stacking
context. How do you imagine that can be done?
:::

3D transforms
=============

3D transforms are significantly more complex than 2D, for several reasons:

 a. How and when to “flatten” (aka 2D projection) 3D transformed stacking
   contexts back into a 2D bitmap
 b. Perspective
 c. What happens if the transformed polygon is turned around backward
In this section I’ll give a quick sketch of how those concerns can be resolved
in a web browser.

Reason (a) can be solved by putting a boolean on each stacking context
indicating whether it flattens when it draws into its ancestor stacking context.
Groups of tree-adjacent stacking contexts with the “3D” bit are drawn into the
same 3D space, and only flattened as a group when drawing into their parent.
Reason (b) can be solved by specifying a perspective matrix to apply when the
“3D” bit is false. Reason (c) can be solved by another bit saying whether the
stacking context is [“backface visible”](backface-visible).

[backface-visible]: https://drafts.csswg.org/css-transforms-2/#propdef-backface-visibility

<a name=hardware-acceleration>

Hardware Acceleration
=====================

All of the visual effects described in this chapter can be implemented very
efficiently on modern [GPU architectures](gpu-architectures); let’s see how
[^6].
GPUs are designed to make it easy to compute, in a [pixel shader](pixel-shader)
(plus [vertex shaders](vertex-shader) for geometry),
in-parallel, all pixels of a bitmap from the combination of:

 - One or more other bitmaps
 - Some arrays, matrices or other floating-point variables

[^6]: However, it should be noted that it is not surprising at all that this is
possible, because those same visual effects were first developed by earlier
generations of graphical computer programs that co-evolved with GPUs before
being adopted by the web.

[gpu-architectures]: https://en.wikipedia.org/wiki/Graphics_processing_unit
[pixel-shader]: https://en.wikipedia.org/wiki/Shader#Pixel_shaders
[vertex-shader]: https://en.wikipedia.org/wiki/Shader#Vertex_shaders

As long as the computation is a non-looping sequence of simple
mathematical operations, each pixel is independent of the other
ones[^7]. It is also easy to apply transforms via vertex shaders.

[^7]: This is why filters and blend modes that do introduce such dependencies
are more expensive, because they require multiple passes over the data.

Because they don’t depend on each other, and GPUs have special-purpose hardware
to do so, computations for each pixel runs in parallel. Due to this parallelism,
it’s often much faster to compute visual effects on the GPU than on the CPU.
(However, it is not free, and in some cases can be slower or more expensive, as
we will see in the next section.) It is also often more CPU and power-efficient
to do this work on the GPU.

The details of the languages used to program GPUs are somewhat complicated, but
it’s easy to reason through how a pixel shader might be written in a C-like
function without loops. For the simple case of opacity, the shader is literally
a function that takes in two colors and two alpha values, and implements the
blend() function with a few lines of code. Other blend modes are also easy, as
the spec text makes pretty clear from its [pseudocode](blend-mode-pseudocode).

[blend-mode-pseudocode]: https://drafts.fxtf.org/compositing-1/#porterduffcompositingoperators

Filters are sometimes more complicated, and sometimes require some clever tricks
to make them very efficient. Rectangular clips are easy to write as direct
numerical  inputs to the shader (skipping the intermediate bitmap). Rounded
corners can often be implemented with shaders as well, via parameterized
descriptions of the shape of the rounded corner curve; the corresponding math
to determine whether a pixel is inside or outside can run in the shader. Other
clip shapes are often implemented via the generate-bitmap-on-the-CPU+GPU
blend-mode method described in the Clipping section. 

Transforms also have special support in GPUs that makes them relatively easy to
implement. GPUs also often have built-in support for different common approaches
for bilinear and other filtering.

Compositing
===========

In chapter 2, you saw how to produce a display list of low-level painting
commands, which can then be replayed to draw to the screen. The example you
worked through in that case was to optimize scrolling by repainting only part of
the display list - the part visible on the screen - when scrolling. Compositing
takes this even further, by saving the pixels generated drawing display lists
into auxiliary bitmaps that can be saved for future re-use.

Let’s look at scrolling as an example. You know from the previous section that
if we can create a bitmap, then we can use the GPU to transform that bitmap
extremely efficiently. Since scrolling is equivalent to a translation transform
in the *x* or *y* direction, we can use the following technique to implement HTML
document scrolling very efficiently:

 1. Draw a solid white background bitmap
 2. Draw the entire web page into a separate bitmap from the background
 3. On scroll, use a GPU shader to shift the bitmap relative to the white
    background by the scroll amount and then blend it into the background

I’ll also quickly note for now that once the web page has been drawn into such a
bitmap, and that bitmap is stored in immutable memory, then scrolling can be
performed in parallel with javascript or other tasks, on a separate CPU thread.
This technique is called threaded scrolling, or composited scrolling. The thread
performing scrolling is often called the compositor thread, and the other one
you already know about the main thread.

Earlier in the chapter, I used the term blending to refer to how stacking
contexts (aka bitmaps) get put together. In graphics and image processing, the
process of putting together multiple bitmaps into a final image is actually
called [compositing][compositing]; blending refers more to the particular math to use when
compositing. However, in browsers the word compositing is often overloaded to
mean not just this concept, but also the optimization technique - hence the
term “composited scrolling”. To make sure everything is clear, let’s define and
review a list of rendering concepts, as we know of them so far:

 - Stacking context: a group of HTML elements that paint contiguously together;
   the stacking contexts form a tree
 - Paint: the process of emitting display lists from stacking contexts, in order
 - Display list: the output of paint
 - Raster: the process of executing the commands in a display list to create a
   bitmap of defined dimensions
 - Compositing: the process or strategy for putting different parts of the
   display list into different bitmaps
 - Bitmap (usually called a composited layer in browser terminology): the output
   of raster
 - Draw: the process of executing a sequence of blends, filters, clips and
   transforms to generate a final screen bitmap. Typically implemented with GPU
   shaders

[compositing]: https://en.wikipedia.org/wiki/Compositing

Let’s now get back to the scrolling example. There is an immediately noticeable
flaw in this three-step process for hardware accelerated scrolling. Just like
you saw in Chapter 2, it’s not only expensive to draw the display list for the
entire document if it is much bigger than the screen, it’s even more expensive
to raster all of this content [^8]. For this reason, it’s much better to raster only
content on or near the screen. This is easy enough for a single-threaded browser
like was discussed in Chapter 2; for threaded scrolling it becomes more complex
because:

 - Any scrolls happening on the compositor thread need to be communicated
   periodically back to the main thread, so that it can paint or raster
   additional content that has come into view
 - Scrolling on the compositor thread may happen faster than the main thread can
   keep up, leading to missing content on the screen, which usually exhibits as
   a solid-color background. At least in Chromium, this situation is called
   checkerboarding, by analogy with the
   [checkerboard rendering](checkerboard-rendering) technique for
   incrementally rendering an image or scene. Scheduling thread synchronization,
   raster, and paints to minimize checkerboarding is tricky.

[checkerboard-rendering]: https://en.wikipedia.org/wiki/Checkerboard_rendering
[^8]:  It’s usually a good rule of thumb to consider raster more expensive than
paint, but these days that is becoming less  true as browsers make more use of
the GPU itself to execute raster.

Beyond scrolling
================

In addition, there is the possibility of rastering one or more stacking contexts
into separate bitmaps. This has two potential benefits:

 a. Less raster cost when rastering *other* stacking contexts that are nearby or
    overlapping on-screen
 b.. Faster animations when those stacking contexts move on-screen

Benefit (b) is the one we observed with scrolling, which is one type of
animation. On the web, there are ways to
[declare animations](declare-animations) of opacity, filters and transform as
part of element styles. Scrolling parts of the page that are not the root
element is also supported, and can be accelerated in a similar way to document
scrolling, via a translation transform. Browsers use this information as a hint
to raster the stacking contexts within the animation into a different bitmap, so
that the opacity, filter or transform can be efficiently run on the GPU without
incurring any additional cost, and also running on the compositor thread.

[declare-animations]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Animations/Using_CSS_animations

Downsides of compositing
========================

Compositing sounds like an amazing technique that should always be used, so as
to use the GPU as much as possible to make web pages faster. However, it is by
no means a silver bullet, and can easily make pages slower, not faster. Here are
some of the reasons compositing might be slower:

 - *Increased memory use*. Every extra bitmap created takes up memory. If every
    stacking context gets its own bitmap, for example, the total memory used is
    almost always much higher than a single bitmap for all stacking contexts.
    GPU operations can also cause extra memory use, because they result in more
    intermediate textures to represent the output of blending steps, or because
    sometimes CPU and GPU copies of the same bitmap are necessary.
 - *GPU setup overhead*. GPUs are very fast once started, but there is a large
    overhead to set them up. This is mostly in the form of the cost to copy
    bitmaps to and from the GPU, and to install and compile the shader programs.
 - *Main thread processing overhead*. All of these bitmaps need to be kept track
   of by the browser, because it needs to know where to re-paint and re-raster
   when content changes. In addition, if two stacking contexts overlap on the
   screen, and one of them is composited and draws first in paint order, then
   the second needs to be composited as well [^9]; detecting this situation in all
   cases is quite expensive.
 - *Layer explosion*. Compositing and GPU acceleration has a tendency to bleed
   out into other seemingly unrelated parts of the web page, causing more
   overhead than was originally desired. The overlap situation just mentioned is
   one such situation. Others include visual effects applied to ancestors of
   composited stacking contexts (for example: if a composited stacking context
   is clipped by an ancestor, the clip must be applied on the GPU, or else there
   will be an extremely expensive CPU pixel readback).
 - *Loss of quality*. High-quality and precise rendering is very important for
   browsers. This is especially important for text and images, where humans are
   very sensitive to issues of blurriness in particular. It’s easy to cause loss
   of precision or quality when using GPU-accelerated compositing due to rounding
   or quality/speed tradeoffs.
 - *Dependence on GPUs*. GPU hardware and software varies in quality, speed and
   features. Dependence on these technologies leads to exposure to the flaws in
   various GPU/driver/OS combinations, and a corresponding worsened reliability
   or need for bug workarounds[^10].

[^9]: Do you see why?
[^10]: Chromium solves this in part by providing a
[complete implementation](swiftshader) of
all GPU APIs in a software library! This library is used for cases when a
particular GPU has too many bugs or other limitations.

[swiftshader]: https://github.com/google/swiftshader

GPU raster
==========

It’s possible on today’s GPUs not only to execute visual effects, but also
perform raster itself on the GPU. This technique, if it can be made to work
well, has the following benefits:

 - Utilize GPU parallelism to raster much faster in many cases, and reduce CPU
  and battery utilization for raster
 - Eliminate the overhead of copying bitmaps to and from the GPU

The hardest content to accelerate via GPU programs are [text](gpu-raster-text)
and [paths](gpu-raster-paths) (the most common example of complicated paths on
the web is [SVG icons](svg-icons). In some cases, text and paths are still rastered on the
CPU and then uploaded as GPU auxiliary textures, for reasons of performance and
quality. Image and video decoding cannot in general be GPU accelerated without
special-purpose hardware.

[gpu-raster-text]: http://litherum.blogspot.com/2016/04/gpu-text-rendering-overview.html
[gpu-raster-paths]: https://community.khronos.org/t/gpu-accelerated-path-rendering/65247
[svg-icons]: https://www.google.com/search?q=svg+icons

GPU raster, if it’s fast enough, would allow browsers to raster the entire
screen on-demand every time, and skip the complexities of compositing. This
approach is being explored in various projects, such as [this one](webrender).
To date, it has not succeeded, because GPUs are not yet fast enough to handle
very complex content, or reliable enough across the huge variety of computing
devices available.

[webrender]: https://hacks.mozilla.org/2017/10/the-whole-web-at-maximum-fps-how-webrender-gets-rid-of-jank/

Image decoding
==============

Images are a complex and difficult space unto themselves, but conceptually
relatively simple. Images are encoded into various formats by people who make
websites; browsers need to download, decode and filter those images when
displaying them to the screen.

 - Encoding: processing an image file and compressing it into a particular
   format, such as JPEG or [WebP], optimizing for
   quality/file-size/speed-of-decoding tradeoffs. This task is not performed by
   web browsers when rendering, but during authoring of web sites.
 - Decoding: uncompressing an encoded image into some representation in memory.
   The time to decode, and memory size relative to compressed form, is
   conceptually similar to ZIP files. In other words, decoding is a relatively
   slow process, and the decompressed size is often one or more orders of
   magnitude larger than the compressed size.
 - Filtering: resizing the image to match a particular screen size for
   presentation on the screen. The intrinsic size of an image is the resolution
   of the decoded bitmap of the image before resizing.

[WebP]: https://en.wikipedia.org/wiki/WebP

The main challenges with rendering images on the web are:

 - Slow image decodes, or time to copy the decoded bitmap to the GPU
 - Excessive memory use due to putting the decoded bitmap of images in memory
 - Appropriate algorithms to implement filtering with good quality

Real-world browsers all have complex machinery to handle these situations, such
as:

 - Only decode images are on or near the screen (and not immediately upon
   downloading them), and ideally only when the screen size of the image is
   already known
 - Decoding on a background thread in parallel with other work
 - Special-purpose [APIs] allowing website authors to control the quality/speed
    tradeoffs used
 - Storing decoded image bitmaps in an LRU cache of limited size

[APIs]: https://html.spec.whatwg.org/multipage/embedded-content.html#dom-img-decoding

Summary
=======

This chapter gave a high-level overview of many of the complex algorithms
involved in actually rendering typical web pages in real-world web browsers, as
well as more advanced visual effects than we had encoutered so far in this book.
It also explains how to use today's computer hardware to greatly accelerate the
speed of web page rendering, and the some of the subtleties and tradeoffs
involved.
