---
title: Supporting Embedded Content
chapter: 15
prev: accessibility
next: skipped
...

Our toy browser has a lot of rendering features, but is still missing a few
present on pretty much every website. The most obvious is *images*. So
we can and should add support for images to our browser to make it feel more
complete. But images are actually the simplest form of *embedded content*
within a web page, a much bigger topic, and one that has a lot of interesting
implications for how browser engines work.[^images-interesting] That's mostly
due to how powerful *iframes* are, since they allow you to embed one website
in another. We'll go through two aspects of embedded content in this chapter:
how to render them, and their impact on the rendering event loop.

[^images-interesting]: Actually, if I were to describe all aspects of images
in browsers, it would take up an entire chapter by itself. But many
of these details are quite specialized, or stray outside the
core tasks of a browser engine, so I've left them to footnotes.

Images
======

Images are everywhere on the web. They are relatively easy to implement in their
simplest form. Well, they are easy to implement if you have convenient
libraries to decode and render them. So let's just get to it.[^img-history]
We'll implement the `<img` tag, which works like this:

    <img src="https://pavpanchekha.com/im/me-square.jpg">

An `<img>` is a leaf element of the DOM. In some ways, it's similar to a single
font glyph that has to paint in a single rectangle (sized to the image instead
of the glyph), takes up space in a `LineLayout`, and causes line breaking when
it reaches the end of the available space. But it's different than a text node,
because the text in a text node is not just one glyph, but an entire run of
text of a potentially arbitrary length, and that can be split into words and
lines across multiple lines.

An image, on the other hand is *atomic*---it doesn't make sense to split it.
This is why images are defined in the layout specification as a
[atomic inline][atomic-inline].^[There are other things that can be atomic
inlines, and we'll encounter more later in this chapter.]

[atomic-inline]: https://drafts.csswg.org/css-display-3/#atomic-inline

[^img-history]: In fact, images have been around (almost) since the
beginning, being proposed in [early 1993][img-email]. This makes it ironic that
images only make their appearance in chapter 15 of the book. My excuse is that
Tkinter doesn't support proper image sizing and clipping, and doesn't support
very many image formats, so we had to wait for the introduction of Skia.

[img-email]: http://1997.webhistory.org/www.lists/www-talk.1993q1/0182.html

There are three steps to displaying images:

1. Download it from a URL.
2. Decode it into a buffer in memory.^[I'll get into how this works in a bit;
for now just think of it like decompressing a zip file.]
3. Lay it out on the page.
4. Paint it in the right place in the display list.

Skia doesn't come with built-in image decoding, so first download and install
the [Pillow/PIL][pillow] library for this task:

[pillow]: https://pillow.readthedocs.io/en/stable/reference/Image.html

    pip3 install Pillow

and include it:^[Pillow is a fork of a project called PIL---for
Python Image Library---which is why the import says PIL.]

``` {.python}
import PIL.Image
```

For step 1 (download), we'll need to make some changes to the `request`
function to add support for binary data formats; currently it assumes an HTTP
response is always `utf8`. We'll start by creating a binary file object
from the response instead of `utf8`:

``` {.python}
def request(url, top_level_url, payload=None):
    # ...
    response = s.makefile("b", newline="\r\n")
```
Now each time we read a line we need to decode it individually; for image
responses, all lines will be `utf8` except for the body, which be raw
encoded image data.

``` {.python}
def request(url, top_level_url, payload=None):
    # ...
    statusline = response.readline().decode("utf8")
    # ...
    while True:
        line = response.readline().decode("utf8")
        # ...    
```

Then when we get to the body, check for the `content-type` header. We encountered
this header briefly in [Chapter 1](/http.html#the-servers-response), where I
noted that HTML web page responses have a value of `text/html` for this header.
This value is a *MIME type*. MIME stands for Multipurpose Internet
Mail Extensions, and was originally intended for enumerating all of the
acceptable data formats for email attachments.^[Most email these days is
actually HTML, and is encoded with the "text/html" MIME type. Gmail, for example,
by default uses this format, but can be put in a "plain text mode" that
encodes the email in "text/plain".] We've actually encountered two more content
types already: `text/css` and `application/javascript`, but since we assumed
both were in `utf8` there was no need to differentiate in the code.^[That's
not a correct thing to do in a real browser, and alternate character sets are
an exercise in chapter 1.]

The `content-type` of an image depends on its format. For example, JPEG is
`image/jpeg`; PNG is `image/png`. Arbitrary binary data with no specific
format is `application/octet-stream`.^[An "octet" is a number with 8 bits,
hence "oct" from the Latin root "octo".] So as a cheat, we'll look at
`content-type` and assume that if it starts with `text` the content is
`utf8`, and otherwise return it as undecoded data:

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
    return headers, body
```

Now let's define a method that decodes a response body that we know is an image
(even if we don't know its format).^[Interestingly, to make it work for our toy
browser we don't need to consult `content-type`. That's because Pillow already
auto-detects the image format by peeking at the first few bytes of the binary
image data, which varies for each image format.] First, reinterpret
the image "file" as a `BytesIO` object and pass it to Pillow. Then convert
it to RGBA format (the same RGBA in
[Chapter 11](/visual-effects.html#sdl-creates-the-window), call `tobytes`
(which performs the decode and puts the result in a raw byte array), and wrap
the result in a Skia `Image` object.

``` {.python expected=False}
def decode_image(image_bytes):
    picture_stream = io.BytesIO(image_bytes)
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

Let's now load `<img>` tags found in a web page.In `load` we need to
first find all of the images in the document:

``` {.python replace=Tab/Document}
class Tab:
    # ...
    def load(self, url, body=None):
        # ...
        images = [node
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "img"
                 and "src" in node.attributes]
```

and then request them from the network and decode them, placing the result
on the `Element` object for each image.

``` {.python expected=False}
        # ...
        for img in images:
            link = img.attributes["src"]
            image_url = resolve_url(link, url)
            if not self.allowed_request(image_url):
                print("Blocked image", link, "due to CSP")
                continue
            try:
                header, body = request(image_url, url)
                img.image = decode_image(body)
            except:
                continue
```

Images have inline layout, so we'll need to add a new value in `InlineLayout`
and a new `ImageLayout` class. In this case, the width contributed to the line
is the width of the image.

``` {.python expected=False}
class InlineLayout:
    # ...
    def recurse(self, node, zoom):
            # ...
            elif node.tag == "img":
                self.image(node, zoom)
    
    def image(self, node, zoom):
        w = device_px(node.image.width(), zoom)
        if self.cursor_x + w > self.x + self.width:
            self.new_line()
        line = self.children[-1]
        input = ImageLayout(node, line, self.previous_word)
        line.children.append(input)
        self.previous_word = input
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        size = device_px(float(node.style["font-size"][:-2]), zoom)
        font = get_font(size, weight, size)
        self.cursor_x += w + font.measureText(" ")
```

`ImageLayout` is almost exactly the same as other kinds of inline layout. Notice
in particular how the positioning of an image depends on the font size of the
element (the `image` function has some code for that also). That's at first
unexpected---there is no font in an image, why does this happen? The reason is
that, as a type of inline layout, images are designed to flow along with
related text. For example, the baseline of the image should line up with the
baseline of the text next to it. And so the font of that text affects the
layout of the image.^[In fact, a page with only a single image and no text at
all still has a font size (e.g. the default font size of a web page), and the
image's layout depends on it. This is a very common source of confusion for web
developers.]

``` {.python expected=False}
class ImageLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.children = []
        self.parent = parent
        self.previous = previous
        self.x = None
        self.y = None
        self.width = None
        self.height = None

    def get_ascent(self, font_multiplier=1.0):
        return -self.height

    def get_descent(self, font_multiplier=1.0):
        return 0

    def layout(self, zoom):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = device_px(
            float(self.node.style["font-size"][:-2]), zoom)
        self.font = get_font(size, weight, style)

        self.width = style_length(
            self.node, "width", self.node.image.width(), zoom)
        self.height = style_length(self.node, "height",
            max(device_px(self.node.image.height(), zoom),
            linespace(self.font)), zoom)

        if self.previous:
            space = self.previous.font.measureText(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

    def __repr__(self):
        return ("ImageLayout(src={}, x={}, y={}, width={}," +
            "height={})").format(self.node.attributes["src"],
                self.x, self.y, self.width, self.height)
```

Painting the image is quite straightforward, and uses a new `DrawImage type`
and the Skipa `drawImage` API method.

``` {.python expected=False}
class DrawImage(DisplayItem):
    def __init__(self, image, rect, image_rendering):
        super().__init__(dst_rect)
        self.image = image
        self.rect = rect

    def execute(self, canvas):
        canvas.drawImage(
            self.image, self.rect.left(), self.rect.top()
```

Finally, the `paint` method of `ImageLayout` emits a single `DrawImage`:

``` {.python expected=False}
class ImageLayout:
    # ...
    def paint(self, display_list):
        cmds = []

        rect = skia.Rect.MakeLTRB(
            self.x, self.y, self.x + self.width,
            self.y + self.height)
        cmds.append(DrawImage(self.node.image, dst_rect)

        display_list.extend(cmds)
```

Image should now work and display on the page. But our implementation is
very basic and missing several important features for layout and rendering
quality.

Image sizing
============

At the moment, our browser can only draw an `<img` element at its
[intrinsic size][intrinsic-size], i.e. the size of the source image data. But
that's only because we don't support and CSS properties that can change this
size. If the image was much bigger than the desired rendered pixel size, then
it'd be much more efficient to decode into a smaller buffer.^[[And if it was
much bigger, it'd be convenient to somehow store only up to its intrinsic
size. I don't know if any browsers implement this optimization, and I won't
implement it.]

There are of course several properties to chnage an image's rendered size ^
[For example, the `width` and `height` CSS properties, which were an exercise
in Chapter 13]. But images have, mostly for historical reasons (because these
attributes were invented before CSS existed), ended up with `width` and
`height` that override the intrinsic size. Let's implement those.

[intrinsic-size]: https://developer.mozilla.org/en-US/docs/Glossary/Intrinsic_Size#

It's pretty easy: every place we deduce the width or height of an image layout
object from its intrinsic size, first consult the corresponding attribute and
use it instead if present. First, in `image` on `InlineLayout`. The width
and height attributes are in CSS pixels without unit suffixes, so parsing is
easy, and we need to multiply by zoom to get device pixels:

``` {.pythhon}
class InlineLayout:
    # ...
    def image(self, node, zoom):
        if "width" in node.attributes:
            w = device_px(int(node.attributes["width"]), zoom)
        else:
            w = device_px(node.image.width(), zoom)
```

And in `ImageLayout`:

``` {.python}
class ImageLayout:
    # ...
    def layout(self, zoom):
        # ...
        if "width" in self.node.attributes:
            self.width = \
            device_px(int(self.node.attributes["width"]), zoom)
        else:
            # ...

        if "height" in self.node.attributes:
            self.height = \
                device_px(int(self.node.attributes["height"]), zoom)
        else:
            # ...        
```

This works great to draw the image at a different size, if the web page wants
to scale it up or down from the intrinsic size it happened to be encoded with.
But it also allows the web page to screw up the image pretty badly if the
*aspect ratio* (ratio of width to height) of the width and height attributes
 chosen are not the same as the intrinsic ones. If the ratio of them is double
 the intrinsic sizing, for example, then the image on the screen will look
 stretched horizontally.

 We can avoid this problem by only providing a *scale* for the image rather than
 new width and heights. One way to achieve it is, if the web page happens only
 to specify `width` and not `height`, to infer the correct height from the aspect
 ratio of the original image. Let's implement that.

 TODO: implementation.

::: {further}
Discuss placeholder images while they are loading, and the need to avoid layout
shift or changes of aspect ratio. Describe the aspect-ratio CSS property.

object-fit.
:::

Image quality and performance
=============================

Images are expensive relative to text content. To start with, they take a
long time to download. But decoding is even more expensive in some ways, in
particular how it can slow down the rendering pipeline and use up a lot of
memory. On top of this, if the image is sized to a non-intrinsic size on
screen, there are several different algorithms to choose how to do it. Some
of the algorithms are more expensive than others to run.

To understand why, it's time to dig into what decoding actually does. *Decoding*
is the process of converting an *encoded* image from a binary form optimized
for quick download over a network into a *decoded* one suitable for rendering,
typically a raw bitmap in memory that's suitable for direct input into
rasterization on the GPU. It's called "decoding" and not "decompression"
because many encoded image formats are [*lossy*][lossy], meaning that
they "cheat": they don't faithfully represent all of the information in the
original picture, in cases where it's unlikely that a human viewing the decoded
image will notice the difference.

[lossy]: https://en.wikipedia.org/wiki/Lossy_compression

Many encoded image formats are very good at compression. This means that when a
browser decodes it, the image may take up quite a bit of memory, even if the
downloaded file size is not so big. As a result, it's very important for
browsers to do as little decoding and use as little memory as possible. Two
ways they achieve that are by avoiding decode for images not currently on the
screen, and decoding directly to the size actually needed to draw pixels on the
screen. I've left the first technique to an exercise, but let's dig into the
second one here.

Let's optimize to take advantage of these new observations. The first is to
decode directly the painted size rather than intrinsic. But what about the
algorithm to resize? For that we'll obey the[`image-rendering`]
[image-rendering] CSS property.

[image-rendering]: https://developer.mozilla.org/en-US/docs/Web/CSS/image-rendering

This is not too hard, but requires doing the decode during paint rather than
load. So first store the *encoded* image instead during load:

``` {.python replace=Tab/Document}
class Tab:
    # ...
    def load(self, url, body=None):
        # ...
        for img in images:
            # ...
                header, body = request(image_url, url)
                img.image = PIL.Image.open(io.BytesIO(body))
```

Then in layout, since use that image for sizing.^[It's the same as the previous
code but on a `PIL` image instead of a Skia one, and now it's an attribute
access, so the only change is to remove some parentheses. I won't show the code
here since it's trivial.]

And `decode_image` will also need to change:

TODO: figure out if PIL.Image actually saves any bytes doing this.

``` {.python}
def decode_image(encoded_image, width, height, image_quality):
    resample=None
    if image_quality == "crisp-edges":
        resample = PIL.Image.ANTIALIAS
    pil_image = encoded_image.resize((int(width), int(height)), resample)
    # ...
```

And then in `paint` on `ImageLayout`:

``` {.python}
class ImageLayout:
    # ...
    def paint(self, display_list):
        # ...

        decoded_image = decode_image(self.node.image,
            self.width, self.height,
            self.node.style.get("image-rendering", "auto"))
```

::: {.further}
All the same resize quality options are present in Skia. That's because
resizing may occur during raster, just as it does during decode. One way
for this to happen is via a scale transform (which our toy browser doesn't
support, but real ones do.

Real browsers push the image decoding step even further the rendering pipeline
(e.g. in the raster phase for this reason---to avoid a double resize or worse
image quality. Yet another reason to do so is because raster happens on another
thread, and so that way image decoding won't block the main thread.
:::

Video & other embedded content
==============================

Animations can also be animated.[^animated-gif] So if a website can load an
image, and the image can be animated, then that image is something very close
to a *video*. But in practice, videos need very advanced encoding and encoding
formats to minimize network and CPU costs, *and* these formats incure a lot of
other complications, chief among them [Digital Rights Mangement][drm]. On top
of which, videos need built-in *media controls*, such as play and pause
buttons, and volume controls. The `<video>` tag supported by real browsers
provide built-in support for several common video [*codecs*][codec].^[In video,
it's called a codec, but in images it's called a *format*--go figure.]

[^animated-gif]: See the exercise for animated images at the end of this
chapter.

[drm]: https://en.wikipedia.org/wiki/Digital_rights_management
[codec]: https://en.wikipedia.org/wiki/Video_codec

But what if the web page author wants to display a UI that is more than just an
image or a video? Well, one thing they can do is simply put text or other
content next to the video in the DOM. But if the video is supplied by a *third
party* such as YouTube, or some other external source, the external source will
want to control the UI of their videos, in such a way that other sites can't
mess it up (or violate the privacy and security of user data). It'd be nice to
be able to reserve a portion of the layout for this content, and delegate
rendering of that content to the external provider, in such a way that the
provider can customize their UI and the web page author need not worry about
the details.

There are two possible ways to achieve this:

* External content that is "outside the web", meaning it's not HTML. Audio
and video are types of external content.

* External content that is "inside the web": HTML, CSS.

The first type is a *plugin*. There have been many attempts at plugins on the
web over the years. Some provided a programming language and mechanism for
interactive UI, such as [Java applets][java-applets] or [Flash]. Others
provided a way to embed other content types into a web page, such as
[PDF]. These days, PDF plugins are pretty much the only "non-web" embedded
content type, and is referenced with the `<object>` or `<embed>` tag.^[You
might ask: why? The short answer is that the web is already a fully functional
UI system that should be general enough for any UI (and if it isn't,
the web should be extended to support it). So why have the complication
(security issues, compatibility problems, proprietary overhead) of
yet another such system?]

[java-applets]: https://en.wikipedia.org/wiki/Java_applet
[Flash]: https://en.wikipedia.org/wiki/Adobe_Flash
[PDF]: https://developer.mozilla.org/en-US/docs/Learn/HTML/Multimedia_and_embedding/Other_embedding_technologies#the_embed_and_object_elements


But what about the other option: "inside the web" external content? Well,
that's an iframe.

::: {.further}

Discuss ads as a form of embedded content.

:::

Iframes
=======

Iframes are websites embedded within other websites. The `<iframe>` tag is a
lot like the `<img>` tag: it has the `src` attribute and `width` and `height`
attributes. Beyond that, there is one small difference and one big one.
The big one, of course, is that it somehow contains an entire webpage. That's
a lot of work, so let's start instead with the small difference: unlike images,
iframes have no intrnisic size. So their layout is defined entirely by the
attributes and CSS of the `iframe` element, and not at all by the content of
the iframe.

For iframes, if the `width`or `height` is not specified, it has a default
value.^[These numbers were chosen by someone a long time ago as reasonable
defaults based on average screen sizes of the day.]

``` {.python}
IFRAME_DEFAULT_WIDTH_PX = 300
IFRAME_DEFAULT_HEIGHT_PX = 150
```

So let's get to it. Iframe layout looks like this in `InlineLayout` (pretty
much the only difference from images is the width and height calculation).

``` {.python}
class InlineLayout:
    # ...
    def recurse(self, node, zoom):
        # ...
            elif node.tag == "iframe":
                self.iframe(node, zoom)
    # ...
    def iframe(self, node, zoom):
        if "width" in self.node.attributes:
            w = device_px(int(self.node.attributes["width"]), zoom)
        else:
            w = IFRAME_WIDTH_PX
        if self.cursor_x + w > self.x + self.width:
            self.new_line()
        line = self.children[-1]
        input = IframeLayout(
            node, line, self.previous_word, self.tab)
        line.children.append(input)
        self.previous_word = input
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        size = device_px(float(node.style["font-size"][:-2]), zoom)
        font = get_font(size, weight, size)
        self.cursor_x += w + font.measureText(" ")
```

And the `IframeLayout` layout code is also similar:


``` {.python}
class IframeLayout:
    def __init__(self, node, parent, previous, tab):
        self.node = node
        self.node.layout_object = self
        self.children = []
        self.parent = parent
        self.previous = previous
        self.x = None
        self.y = None
        self.tab = tab

    def get_ascent(self, font_multiplier=1.0):
        return -self.height

    def get_descent(self, font_multiplier=1.0):
        return 0

    def layout(self, zoom):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = float(self.node.style["font-size"][:-2])
        self.font = get_font(size, weight, style)

        if "width" in self.node.attributes:
            self.width = \
                device_px(int(self.node.attributes["width"]), zoom)
        else:
            self.width = device_px(IFRAME_DEFAULT_WIDTH_PX, zoom)

        if "height" in self.node.attributes:
            self.height = \
                device_px(int(self.node.attributes["height"]), zoom)
        else:
            self.height = device_px(IFRAME_DEFAULT_HEIGHT_PX, zoom)

        if self.previous:
            space = self.previous.font.measureText(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.node.document.style()
        self.node.document.layout(zoom, self.width)
```

Iframes by default have a border around their content when painted.
Here I have one line of code not yet implemented, the one that calls `paint`
on a `document` object that doesn't yet exist.

``` {.python}
class IframeLayout:
    # ...
    def paint(self, display_list):
        cmds = []

        rect = skia.Rect.MakeLTRB(
            self.x, self.y,
            self.x + self.width, self.y + self.height)
        bgcolor = self.node.style.get("background-color",
                                 "transparent")
        if bgcolor != "transparent":
            radius = float(
                self.node.style.get("border-radius", "0px")[:-2])
            cmds.append(DrawRRect(rect, radius, bgcolor))

        self.node.document.paint(cmds)

        cmds = [Transform((self.x, self.y), rect, self.node, cmds)]

        paint_outline(self.node, cmds, rect)

        cmds = paint_visual_effects(self.node, cmds, rect)
        display_list.extend(cmds)
```

So that's everything, except for the actual hard part, which is the entire
document contained within.


TODO: make all JS APIs and keyboard events properly target iframes in lab15.py.

Same-origin iframes: same interpreter, postMessage, parent

caveat: bug in duktape regarding use of function() foo() {} syntax and the
    `with` operator

Cross-origin iframes
====================

Cross-origin iframes: postMessage

Iframe security
===============

TODO

Other embedded content
======================

Summary
=======

This chapter introduced embedded content, via the examples of images and
iframes.

Exercises
=========

*Background images*: elements can have not just `background-color`, but also
[`background-image`][bg-img]. Implement this CSS property for images loaded
by URL. Also implement the [`background-size`][bg-size] CSS property so the
image can be sized in various ways.

[bg-img]: https://developer.mozilla.org/en-US/docs/Web/CSS/background-image

[bg-size]: https://developer.mozilla.org/en-US/docs/Web/CSS/background-size

*Object-fit*: implement the [`object-fit`][obj-fit] CSS property. It determines
how the image within an `<img>` element is sized relative to its container
element.

[obj-fit]: https://developer.mozilla.org/en-US/docs/Web/CSS/object-fit

*Lazy decoding*: Decoding images can take time and use up a lot of memory.
But some images, especially ones that are "below the fold"^[btf]---meaning they
are further down in a web page and not visible and only exposed after some
scrolling by the user. Implement an optimization in your browser that only
decodes images that are visible on the screen.

*Lazy loading*: Even though image compression works quite well these days,
the encoded size can still be enough to noticeably slow down web page loads.
Implement an optimization in your browser that only loads images that are
within a certain number of pixels of the being visible on the
screen.^[Real browsers have special [APIs][lli] and optimizations for this
purpose; they don't actually lazy-load images by default, because otherwise
some web sites would break or look ugly. In the early days of the web,
computer networks were slow enought that browsers had a user setting to
disable downloading of images until the usre expresssly asked for them.]

[lli]: https://developer.mozilla.org/en-US/docs/Web/Performance/Lazy_loading

*Animated images*: Add support for animated GIFs. Pillow supports this via the
 `is_animated` and `n_frames` property, and the `seek()` (switch to a different
 animation frame) and `tell()` (find out the current animation frame) methods
 on a `PIL.Image`. (Hint: assume it runs at 60 Hz and integrate it with the 
 `run_animation_frame` method.) If you want an additional challenge, try
 running the animations on the browser thread.^[Real browsers do this as
 an important performance optimization.]