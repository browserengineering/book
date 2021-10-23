---
title: Adding Visual Effects
chapter: 12
prev: security
next: rendering-architecture
...

Right now our browser can draw text and rectangles of various colors. But that's
pretty boring! Browsers have all sorts of great ways to make content look good
on the screen. These are called *visual effects*---visual because they affect
how it looks, but not functionality per se, or layout. Therefore these effects are
extensions to the *paint* and *draw* parts of rendering.

Skia replaces Tkinter
=====================

But before we get to how visual effects are implemented, we'll need to upgrade
our graphics system. While Tkinter was great for basic painting and handling input,
it has no built-in support at all for implementing many visual
effects.[^tkinter-before-gpu] And just as implementing the details of text
rendering or drawing rectangles is outside the scope of this book, so is
implementing visual effects---our focus should be on how to represent and
execute visual effects for web pages specifically.

[^tkinter-before-gpu]: That's because Tk, the library Tkinter uses to implement
its graphics, was built back in the early 90s, before high-performance graphics
cards and GPUs, and their software equivalents, became widespread.

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
advanced GPUs in today's devices, and often browsers are pushing the envelope
of graphics technology. So in practice browser teams include experts
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

Now integrate with the `Browser` class. We need a surface[^surface] for
drawing to the window, and a surface into which Skia will draw.

``` {.python}
class Browser:
    def __init__(self, sdl_window):
        self.window_surface = SDL_GetWindowSurface(
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

[^surface]: In Skia and SDL, a surface is a representation of a graphics buffer
into which you can draw "pixels" (bits representing colors). A surface may or
may not be bound to the actual pixels on the screen via a window, and there can
be many surfaces. A *canvas* is an API interface that allows you to draw
into a surface with higher-level commands such as for lines or text. In
our implementation, we'll start with separate surfaces for Skia and SDL for
simplicity. In a highly optimized browser, minimizng the number of surfaces
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

Update also all the other places that `measure` was called to use the Skia
method (and also create Skia fonts instead of Tkinter ones, of course).

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

Size and position
=================

Right now, block elements size to the dimensions of their inline and input
content, and input elements have a fixed size. But we're not just displaying
text and forms any more---now we're planning to draw visual effects such as
arbitrary colors, images and so on. So we should be able to do things like draw
a rectangle of a given color on the screen. That is accomplished with the
`width` and `height` CSS properties.

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
        self.width = style_length(self.node, "width", INPUT_WIDTH_PX)
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

Great. We can now draw rectangles of a specified width and height. But they
still end up positioned one after another, in a way that we can't control. It'd
be great to be able to put the rectangle anywhere on the screen, and not just
in a place dictated by layout. That can be done with the `position` CSS
property. This property has a whole lot of complexity to it, so let's just add
in a relatively simple-to-implement subset: `position:relative`,[^posrel-caveat]
 plus `top` and `left`. Setting these tells the browser that it
should take the x, y position that the element's top-left corner had, and add
the values of `left` to x and `top` to y. If `position` is not specified, then
`top` and `left` are ignored.

[^posrel-caveat]: Note that we won't even implement all of the effects of
`position:relative`. For example, this property has an effect on paint order,
but we'll ignore it.

This will still "take up space" where it used to be, in terms of the sizing
of the parent element. This makes it pretty easy to implement---just figure
out the layout without taking into account this property, then add in the
adjustments at the end. To make things even easier, we'll treat it as a
purely paint-time property that adjusts the display list.[^posrel-caveat2]

Here's an example:

    <div style="background-color:lightblue;width:50px; height:100px">
    </div>
    <div style="background-color:orange;width:50px; height:100px;
                position:relative;top:-50px;left:50px">
    </div>

This renders into a light blue 50x100 rectangle, with another orange one below
it, but this time they overlap.

<div style="background-color:lightblue;width:50px;height:100px"></div>
<div style="background-color:orange;width:50px;height:100px;position:relative;top:-50px;left:25px"></div>


[^posrel-caveat2]: Again, this is not fully correct! But it
suffices for playing around with visual effects.

To implement `position:relative`, we'll add a new helper method `paint_coords`:

``` {.python}
def paint_coords(node, x, y):
    if not node.style.get("position") == "relative":
        return (x, y)

    paint_x = x
    paint_y = y

    left = node.style.get("left")
    if left:
        paint_x = paint_x + int(left[:-2])
    top = node.style.get("top")
    if top:
        paint_y = paint_y + int(top[:-2])

    return (paint_x, paint_y)
```

Then we can use it in `BlockLayout`:

``` {.python}
class BlockLayout:
    # ...
    def paint(self, display_list):
        (paint_x, paint_y) = paint_coords(self.node, self.x, self.y)
        rect = skia.Rect.MakeLTRB(
            paint_x, paint_y,
            paint_x + self.width, paint_y + self.height)
        # ...
```

A similar change should be made to `InlineLayout` and `InputLayout`.

::: {.further}
Since we've added support for setting the size of a layout object to
be different than the sum of its children's sizes, it's easy for there to
be a visual mismatch. What are we supposed to do if a `LayoutBlock` is not
as tall as the text content within it? By default, browsers draw the content
anyway, and it might or might not paint out side the block's box.
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

    <div style="width:194px; height:194px;background-image:
            url('https://pavpanchekha.com/im/me-square.jpg')">
    </div>

It renders like this:[^exact-size]

<div style="width:194px; height:194px;background-image:url('https://pavpanchekha.com/im/me-square.jpg')"></div>

[^exact-size]: Note that I cleverly chose the width and height of the `div` to
be exactly `194px`, the dimensions of the JPEG image.

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
only decode[^image-decode] it as utf-8 if it starts with `text/`:

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
into an `images` dictionary on a `Tab` keyed by URL. However, to actually show
an image on the first screen, we have to first *decode* it. Images are sent
over the network in one of many optimized encoding formats, such as PNG or
JPEG; when we need to draw them to the screen, we need to convert from the
encoded format into a raw array of pixels. These pixels can then be efficiently
drawn onto the screen.[^image-decoding]

[^image-decoding]: While image decoding technologies are beyond the
scrope of this book, it's very important for browsers to make optimized use
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
        print(rect)
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

Here we're not just drawing the image though---we're also doing something
new that we haven't seen before. We are applying a *clip*. A clip is a way
to cut off parts of a drawing that exceed a given set of bounds. Here we are
asking to clip to the rect that bounds the element, because the
image for `background-image`  never exceeds the size of the element.
Clips have to be preceded by a call to `Save`, which says to Skia to 
snapshot the current parameters to the canvas, so that when `Restore` is called
later these parameters (including presence or absence of a clip) can be
restored.[^not-savelayer]

This example should clip out parts of the image:

    <div style="width:100px; height:100px;background-image:
        url('https://pavpanchekha.com/im/me-square.jpg')">
    </div>

Like this:

<div style="width:100px; height:100px;background-image:url('https://pavpanchekha.com/im/me-square.jpg')">
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

And this is without even getting into the complex topic of the various
algorithms for [image scaling][image-rendering] algorithms (for situations
where we want the image to grow or shrink to fit its container).

[image-rendering]: https://developer.mozilla.org/en-US/docs/Web/CSS/image-rendering

In its full generality, the *paint order* of drawing backgrounds and other
painted aspects of a single element, and the interaction of its paint order
with painting descendants, is[quite complicated]
[paint-order-stacking-context].
:::

[paint-order-stacking-context]: https://www.w3.org/TR/CSS2/zindex.html


Opacity and Compositing
=======================

With sizing and position, we also now have the ability to make content overlap!
[^overlap-new]. Consider this example of CSS & HTML:[^inline-stylesheet]

    <style>
        div { width:100px; height:100px; position:relative }
    </style>
    <div style="background-color:lightblue"></div>
    <div style="background-color:orange;left:50px;top:-25px"></div>
    <div style="background-color:blue;left:100px;top:-50px"></div>

[^inline-stylesheet]: Here I've used an inline style sheet. If you haven't
completed the inline style sheet exercise for chapter 6, you'll need to
convert this into a style sheet file in order to load it in your browser.


Its rendering looks like this:

<div style="width:100px;height:100px;position:relative;background-color:lightblue"></div>
<div style="width:100px;height:100px;position:relative;background-color:orange;left:50px;top:-25px"></div>
<div style="width:100px;height:100px;position:relative;background-color:blue;left:100px;top:-50px"></div>

[^overlap-new]: That's right, it was not previously possible to do this in
our browser. Avoiding overlap is generally good thing for text-based layouts,
because otherwise you might accidentally obscure content and not be able
to read it. But it's needed for many kinds of UIs that need to *layer*
content on top of other content--for instance, to show an overlap menu or
tooltip.

Right now, the blue rectangle completely obscures part of the orange one, and
the orange one does the same to the light blue one. It would be
nice[^why-opacity] for *some* of the orange and light blue to peek through.

[^why-opacity]: Because it's a cool-looking effect, and can make sites
easier to understand. For example, if you can see some of the content underneath
an overlay, you know that conceptually it's there and somehow you should be
able to make the site show it.

We can easily implement that with `opacity`, a CSS property that takes a value
from 0 to 1, 0 being completely invisible (like a window in a house) to
completely opaque (the wall next to the window). The way to do this in Skia
is to create a new canvas, draw the overlay content into it, and then *blend*
that canvas into the previous canvas. It's a little complicated to think
about without first seeing it in action, so let's do that.

Because we'll be adding things other than opacity soon, let's put opacity
into a new function called `paint_visual_effects` that will be called from
the `paint` method of the various layout objects, just like `paint_background`
already is:

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

What this code does is this: if the layout object needs to be painted with
opacity, create a new canvas that draws the layout object and its descendants,
and then blend that canvas into the previous canvas with the provided opacity.


This makes use of two new display list types, `SaveLayer` and `Restore`. Here
is how they are implemented:

``` {.python}
class SaveLayer:
    def __init__(self, sk_paint, rect):
        self.sk_paint = sk_paint
        self.rect = rect

    def execute(self, scroll, rasterizer):
        with rasterizer.surface as canvas:
            canvas.saveLayer(paint=self.sk_paint)
```

``` {.python}
class Restore:
    def __init__(self, rect):
        self.rect = rect

    def execute(self, scroll, rasterizer):
        with rasterizer.surface as canvas:
            canvas.restore()
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
<span style="font-style: normal">applied to</span> content, but alpha as a
<span style="font-style: normal">part of</span> content. In fact, whether there
is an alpha channel in a color representation at all is often an implementation
choice---sometimes graphics libraries instead multiply the other color channels
by the alpha amount, which is called a <span style="font-style:
normal">premultiplied</span> representation of the color.

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

Here you can see that the intersection of the orange and blue[^note-yellow] rectangle renders
as pink. Let's work through the math to see why. Here we are blending a blue
color with orange, via the "difference" blend mode. Blue has (red, green, blue)
color channels of (0, 0, 1.0), and orange has (1.0, 0.65, 0.0). The blended
result will then be (1.0 - 0, 0.65 - 0, 1.0 - 0) = (1.0, 0.65, 1.0),
which is pink.

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
contexts also blend, which is why the blue and orange rectangles in the example
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

In CSS, this is expressed with the `clip-path` property. The
[full definition](https://developer.mozilla.org/en-US/docs/Web/CSS/clip-path)
is quite complicated, so as usual we'll just implement a simple subset.
In this case we'll only support the `circle(xx%)` syntax, where XX is a
percentage and defines the radius of the circle. The percentage is calibrated
so that if the layout object was a perfect square, a 100% circle would inscribe
the bounds of the square.

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
def paint_clip_path(node, display_list, rect):
    clip_path = node.style.get("clip-path")
    if clip_path:
        percent = parse_clip_path(clip_path)
        if percent:
            width = rect.right() - rect.left()
            height = rect.bottom() - rect.top()
            reference_val = math.sqrt(width * width + height * height) / math.sqrt(2)
            center_x = rect.left() + (rect.right() - rect.left()) / 2
            center_y = rect.top() + (rect.bottom() - rect.top()) / 2
            radius = reference_val * percent / 100
            display_list.append(CircleMask(
                center_x, center_y, radius, rect))
```

The only tricky part is how to implement the `CircleMask` class. This will use a
new compositing mode[^blend-compositing] called destination-in. It is defined
as the backdrop color multiplied by the alpha channel of the source color.
The circle drawn in the code above defines a region of non-zero
alpha, and so all pixels fo the backdrop not within the circle will become
transparent black.

Here is the implementation in Python:

``` {.python expected=False}
def composite(source_color, backdrop_color):
    (source_r, source_g, source_b, source_a) = tuple(source_color)
    (backdrop_r, backdrop_g, backdrop_b, backdrop_a) = tuple(backdrop_color)
    return skia.Color4f(
        backdrop_a * source_a * backdrop_r,
        backdrop_a * source_a * backdrop_g,
        backdrop_a * source_a * backdrop_b,
        backdrop_a * source_a)
```

As a result, here is how `CircleMask` is implemented. It creates a new source
canvas via `saveLayer` (and at the same time specifhying a `kDstIn` blend mode)
for when it is drawn into the backdrop), draws a circle in white (or really
any opaque color, it's only the alpha channel that matters), then `restore`.
[^mask]


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
            canvas.restore()
```

Finally, we call `paint_clip_path` for each layout object type. Note however
that we have to paint it *after* painting children, unlike visual effects
or backgrounds. This is because you have to paint the other content into the
backdrop canvas before drawing the circle and applying the clip. For
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
entire web page. TO achieve that we add an extra `saveLayer` in
`paint_visual_effects`:

``` {.python}
def paint_visual_effects(node, display_list, rect):
    # ...

        clip_path = node.style.get("clip-path")
    if clip_path:
        display_list.append(SaveLayer(skia.Paint(), rect))
        restore_count = restore_count + 1
```


[^blend-compositing]: It's actually specified as a blend mode to Skia. TODO:
explain why.

This technique described here for implementing `clip-path` is called *masking* -
draw an auxilliary canvas and reject all pixels of the main that don't overlap
with the auxilliary one. The circle in this case is the mask image. In general,
the mask image could be any arbitrary bitmap, including one that is not a
filled shape. The[`mask`]
(https://developer.mozilla.org/en-US/docs/Web/CSS/mask) CSS property is a way
to do this, for example by specifying an image at a URL that supplies the
mask.

While the `mask` CSS property is relatively uncommonly used (as is `clip-path`
actually), there is a special kind of mask that is very common: rounded
corners. Now that we know how to implement masks, this one is also easy to
add to our browser. Because it's so common in fact, Skia has special-purpose
methods to draw rounded corners: `clipRRect`.

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

Now why is it that rounded rect clips are applied in `paint_visual_effects`
but masks and clip paths happen later on in the `paint` method? What's going
on here? It is indeed the same, but Skia only optimizes for rounded rects
because they are so common. Skia could easily add a `clipCircle` command
if it was popular enough.

What Skia does under the covers may actually equivalent to the clip path
case, and sometimes that is indeed the case. But in other situations, various
optimizations can be applied to make the clip more efficient. For example,
`clipRect` clips to a rectangle, which makes it esaier for Skia to skip
subsequent draw operations that don't intersect that rectangle[^see-chap-1],
or dynamically draw only the parts of drawings that interset the rectangle.
Likewise, the first optimization mentiond above also applies to
`clipRRect` (but the second is trickier because you have to account for the
space cut out in the corners).

[^see-chap-1]: This is basically the same optimization as we added in Chapter
1 to avoid painting offscreen text.

::: {.further}

TODO: the story of rounded corners: Macintosh, early web via nine-patch, GPU
acceleration.

:::


Transforms
==========

The last visual effect we'll implement is 2D transforms. In computer
graphics, a transform is a linear transformation of a point in space, typically
represented as multiplication of that point by a transformation matrix. The
same concept exists on the web in the `transform` CSS property. This property
allows transforming the four points of a rectangular layout object by a
matrix[^3d-matrix] when drawing to the screen.

[^3d-matrix]: The matrix can be 3D, but we'll only discuss 2D matrices in this
chapter. There is a lot more complexity to 3D transforms, having to do with
the definition of 3D spaces, flatting, backfaces, and plane intersections.

[^except-scrolling]: The only exception is that transform contribute to
[scrollable overflow](https://drafts.csswg.org/css-overflow/#scrollable).

By default, the origin of the coordinate space in which the transform applies is
the center of the layout object's box[^transform-origin], which means that each
of the four corners will be in a different quadrant of the 2D plane. The
transform matrix specfied by the `transform` property
[maps][applying-a-transform] each of the four points to a new 2D location.
You can also roughly think of it also doing the same for the pixels inside
the rectangle.[^filter-transform]

[^transform-origin]: As you might expect, there is a CSS property called
`transform-origin` that allows changing this default.

[applying-a-transform]: https://drafts.csswg.org/css-transforms-1/#transform-rendering

[^filter-transform]: In reality, the method of generating the bitmap transform
(A) is a nuanced topic. Generating high-quality bitmaps in these situations
involves a number of considerations, such as bilinear or trilinear filtering,
and how to handle pixels near the edges.

Transforms are almost entirely a visual effect, and do not affect layout.
[^except-scrolling] As you would expect, this means we can implement
2D transforms with a simple addition to `paint_visual_effects`. Let's do it
now. We'll implement just a syntax for simple rotation about the Z axis
(which means that the element should rotate on the screen; the Z axis
is the one that points from your eye to the screen; the X and Y axes
are the same ones we've been working with to this point for layout and paint).

So we'll need to parse it:

``` {.python}
def parse_rotation_transform(transform_str):
    left_paren = transform_str.find('(')
    right_paren = transform_str.find('deg)')
    return float(transform_str[left_paren + 1:right_paren])
```

Then paint it (we need to `Save` before rotating, to only rotate
the element and its subtree, not the rest of the output):

``` {.python}
def paint_visual_effects(node, display_list, rect):
    transform_str = node.style.get("transform", "")
    if transform_str:
        display_list.append(Save(rect))
        restore_count = restore_count + 1
        degrees = parse_rotation_transform(transform_str)
        display_list.append(Rotate(degrees, rect))
```

The implementation of `Rotate` in Skia looks like this:

``` {.python}
class Rotate:
    def __init__(self, degrees, rect):
        self.degrees = degrees
        self.rect = rect

    def execute(self, scroll, rasterizer):
        with rasterizer.surface as canvas:
            canvas.rotate(self.degrees)
```

Summary
=======

So there you have it. Now we don't have just a boring browser that can only
draw simple input boxes plus text. It now supports:

* Arbitrary position and size of boxes
* Background images
* Opacity
* Blending
* Clips
* Masks
* 2D transforms

Exercises
=========

*z-index*: Right now, the order of paint is a depth-first traversal of the
 layout tree. By using the `z-index` CSS property, pages can change that order.
 An element with lower z-index than another one paints before it. Elements with
 the same z-index paint in depth-first order. Elements with no z-index
 specified paint at the same time as z-index 0. Implement this CSS property.
 [^nested-z-index]

 [^nested-z-index]: You don't need to add support for nested z-index (an
 elemnet with z-index that has an ancestor also witih z-index). In order
 to do that properly, you'd need to add support for
 [stacking contexts][stacking-context] to our browser. In addition, the true
 paint order depends not only on z-index but also on `position`, and is
 broken into multiple phases. See [here][elaborate] for the gory details.

 [stacking-context]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Positioning/Understanding_z_index/The_stacking_context

 [elaborate]: https://www.w3.org/TR/CSS2/zindex.html

*Overflow clipping*: As mentioned at the end of the section introducing the
`width` and `height` CSS properties, sizing boxes with CSS means that the
contents of a layout object can exceed its size. Implement the `clip` value of
the `overflow` CSS property+value. When set, this should clip out the parts
of the content that exceed the box size of the element .

*Overflow scrolling*: Implement a very basic version of the `overflow:scroll` 
property+value. (This exercise builds on the previous one). You'll need to
have a way to actually process input to cause scrolling, and also keep
track of the total height of the [*layout overflow*][overflow-doc]. One
way to allow the user to scroll is to use built-in arrow key handlers
that apply when the `overflow:scroll` element has focus.

*Image elements*: the `<img>` element is a way (the original way, back in the
90s, in fact) to draw an image to the screen. The image URL is specified
by the `src` attribute, it has inline layout, and is by default sized to the
intrinsic size of the image, which is its bitmap dimensions. Before an image
has loaded, it has 0x0 intrinsic sizing. Implement this element.