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
3. Layout the image.
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

``` {.python}
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

Let's now load images found in a web page. Images appear in the `<img>` tag,
and the URL of the image is in the `src` attribute. In `load` we need to
first find all of the images in the document:

``` {.python expected=False}
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

``` {.python}
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
and a new `ImageLayout` class.

``` {.python}
class InlineLayout:
    # ...
    def recurse(self, node, zoom):
            # ...
            elif node.tag == "img":
                self.image(node, zoom)
    
    def image(self, node, zoom):
        w = style_length(
            node, "width", node.image.width(), zoom)
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
element. That's unexpected---there is no font in an image, why does this
happen? The reason is that, as a type of inline layout, images are designed to
flow along with related text. For example, the baseline of the image should
line up with the baseline of the text next to it. And so the font of that text
affects the layout of the image.

TODO: discussion about width and height.

``` {.python}
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
            max(self.node.image.height(), linespace(self.font)), zoom)

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

Painting the image is quite straightforward, and uses a new `DrawImage type`.
There's not much to say, because Skia supports drawing images. The only
somewhat complicated thing here is the difference between `src_rect` and
`dst_rect`. The `src_rect` variable indicates a rectangle within the coordinate
space of the *image* to raster (in our case we're rastering the whole image, so
it'd be `(0, 0, width-of-image, height-of-image)`). The `dst_rect` variable is
a rectangle in the coordinates of the web page---the position and sizing on the
page of the final image. (For now, assume this rectangle has the same width
and height, but later we'll see that they can differ.)

``` {.python expected=False}
class DrawImage(DisplayItem):
    def __init__(self, image, src_rect, dst_rect, image_rendering):
        super().__init__(dst_rect)
        self.image = image
        self.src_rect = src_rect
        self.dst_rect = dst_rect

    def execute(self, canvas):
        canvas.drawImageRect(
            self.image, self.src_rect, self.dst_rect)
```

Finally, the `paint` method of `ImageLayout` emits a single `DrawImage`:

``` {.python expected=False}
class ImageLayout:
    # ...
    def paint(self, display_list):
        cmds = []

        src_rect = skia.Rect.MakeLTRB(
            0, 0, self.node.image.width(), self.node.image.height())

        dst_rect = skia.Rect.MakeLTRB(
            self.x, self.y, self.x + self.width,
            self.y + self.height)

        cmds.append(DrawImage(self.node.image, src_rect, dst_rect)

        display_list.extend(cmds)
```

Now it's time to dig into what decoding actually does. *Decoding* is the process
of converting an *encoded* image from a binary form optimized for quick
download over a network into a *decoded* one suitable for rendering, typically
a raw bitmap in memory that's suitable for direct input into rasterization on
the GPU. It's called "decoding" and not "decompression" because many encoded
image formats are [*lossy*][lossy], meaning that they "cheat": they don't
faithfully represent all of the information in the original picture, in cases
where it's unlikely that a human viewing the decoded image will notice the
difference.

[lossy]: https://en.wikipedia.org/wiki/Lossy_compression

Many encoded image formats are very good at compression. This means that when
a browser decodes it, the image may take up quite a bit of memory, even if
the downloaded file size is not so big. As a result, it's very important
for browsers to do as little decoding and use as little memory as possible.
Two ways they achieve that are by avoiding decode for images not currently
on the screen, and decoding directly to the size of the image. I've left the
first technique to an exercise, but let's dig into the second one here.

Embedded content layout
=======================

TODO

Image sizing and quality
==========================

TODO

Iframes
=======

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

