---
title: Supporting Embedded Content
chapter: 15
prev: accessibility
next: invalidation
...

Our toy browser has a lot of rendering features, but is still missing a few
present on pretty much every website. The most obvious is *images*---given how
ubiquitous they are, it seems silly to have even a toy browser without images.
But images are actually the simplest form of *embedded content* within a web
page, a much bigger topic, and one that has a lot of interesting implications
for how browser engines work.[^images-interesting] That's mostly due to how
powerful *iframes* are, since they allow you to embed one website in another.
A toy browser without iframes simply wouldn't cover some very important
architectural aspects of real browsers.^[And in keeping with the pattern you've
already seen, basic support for iframes is easy enough to implement in one 
chapter.]

[^images-interesting]: If I were to describe every single aspect
of *just images* in browsers, it would take up an entire chapter by itself. But
many of these details are quite specialized, or stray outside the core tasks of
a browser engine, so I've omitted or left them to footnotes.

Images
======

Images are relatively easy to implement in their simplest form (well, they are
"easy" if you have convenient libraries to decode and render them). So let's
 just get to it.[^img-history] We'll implement the `<img>` tag, which works
 like this:

    <img src="https://pavpanchekha.com/im/me-square.jpg">


[^img-history]: In fact, images have been around (almost) since the
beginning, being proposed in [early 1993][img-email]. This makes it ironic that
images only make their appearance in chapter 15 of the book. My excuse is that
Tkinter doesn't support proper image sizing and clipping, and doesn't support
very many image formats, so we had to wait for the introduction of Skia.

An `<img>` is a leaf element of the DOM. In some ways, it's similar to a single
font glyph that has to paint in a single rectangle (sized to the image instead
of the glyph), takes up space in a `LineLayout`, and causes line breaking when
it reaches the end of the available space. But it's different than a text node,
because the text in a text node is not just one glyph, but an entire run of
text of a potentially arbitrary length, and that can be split into words and
lines across multiple lines.

An image, on the other hand, is an [atomic inline][atomic-inline]---it doesn't
make sense to split it across multiple lines.^[There are other things that can
be atomic inlines, and we'll encounter more later in this chapter.]


[atomic-inline]: https://drafts.csswg.org/css-display-3/#atomic-inline


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
responses, all lines will be `utf8` except for the body, which is raw
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

Then when we get to the body, check for the `content-type` header, which will
tell us how to decode the body of the HTTP response. We encountered this header
briefly in [Chapter 1](/http.html#the-servers-response), where I noted that
HTML web page responses have a value of `text/html` for this header. This value
is a [MIME type][mime-type]. MIME stands for Multipurpose Internet Mail
Extensions, and was originally intended for enumerating all of the acceptable
data formats for email attachments.^[Most email these days is actually HTML,
and is encoded with the `text/html` MIME type. Gmail, for example, by default
uses this format, but can be put in a "plain text mode" that encodes the email
in `text/plain`.] We've actually encountered two more content types already:
`text/css` and `application/javascript`, but since we assumed both were in
`utf8` there was no need to differentiate in the code.^[That's not a correct
thing to do in a real browser, and alternate character sets are an exercise in
chapter 1.]

[mime-type]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types

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
data, which varies for each image format.] First, reinterpret
the image "file" as a `BytesIO` object and pass it to Pillow. Then convert
it to RGBA format (the same RGBA as in
[Chapter 11](/visual-effects.html#sdl-creates-the-window)), call `tobytes`
(which performs the decode and puts the result in a raw byte
array[^maybe-decode]), and wrap the result in a Skia `Image` object.

[^maybe-decode]: Maybe. As with Skia, Pillow tries to be lazy about when to
decode, so probably the decode happens at this time. But there is nothing
in the Pillow API that requires it to decode right then, rather than say in
the `open` call. For our toy browser it doesn't matter very much, but in a
real browser the timing of a decode is important for performance. That's also
why there is an [HTML API][html-image-decode] to control decoding.

[html-image-decode]: https://developer.mozilla.org/en-US/docs/Web/API/HTMLImageElement/decoding

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

Let's now load `<img>` tags found in a web page. In `load` we need to
first find all of the images in the document:

``` {.python replace=Tab/Frame}
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
on the `Element` object for each image:

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

Images have inline layout, so we'll need to add a new `image` method in
`InlineLayout`. In this case, the width contributed to the line is the width of
the image; otherwise it's the same as the existing `input` method.

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

And a new `ImageLayout` class. The height of the object is defined by the
height of the image. Again, this class is almost the same as `InputLayout`,
except for that height.

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

Notice how the positioning of an image depends on the font size of the element
(the `ImageLayout` class coming up has some code for that also). Input elements
already had that, but those elements generally have text in them, but images do
not. That means that a "line" consisting of only an image still has has an
implicit font affecting its layout somehow.^[In fact, a page with only a single
image and no text or CSS at all still has a font size (the default font size of
a web page), and the image's layout depends on it. This is a very common source
of confusion for web developers. In a real browser, it can be fixed by forcing
an image into a block or other layout mode via the `display` CSS property.]

That's unintuitive---there is no font in an image, why does this happen?
The reason is that, as a type of inline layout, images are designed to flow
along with related text. For example, the baseline of the image should line up
with the [baseline][baseline-ch3] of the text next to it. And so the font of
that text affects the layout of the image. Rather than special-case situations
where there happens to be no adjacent text, the layout algorithm simply lays
out the same as no text at all---similar to how `<br>` also implicitly has
an associated font.

[baseline-ch3]: text.html#text-of-different-sizes

In fact, now that you see images alongside input elements, notice how actually
the input elements we defined in Chapter 8 *are also a form of embedded
content*---after all, the way they are drawn to the screen is certainly not
defined by HTML tags and CSS. The web specifications call input, images and
other embedded content
[*replaced elements*][replaced-elements]---characterized by putting stuff
"outside of HTML" into an inline HTML context, and "replacing" what HTML might
have drawn.

[replaced-elements]: https://developer.mozilla.org/en-US/docs/Web/CSS/Replaced_element

Painting an image is quite straightforward, and uses a new `DrawImage type`
and the Skia `drawImage` API method.

``` {.python}
class DrawImage(DisplayItem):
    def __init__(self, image, rect):
        super().__init__(rect)
        self.image = image

    def execute(self, canvas):
        canvas.drawImage(
            self.image, self.rect.left(), self.rect.top())
```

Finally, the `paint` method of `ImageLayout` emits a single `DrawImage`:

``` {.python expected=False}
class ImageLayout:
    # ...
    def paint(self, display_list):
        cmds = []
        # ...
        rect = skia.Rect.MakeLTRB(
            self.x, self.y, self.x + self.width,
            self.y + self.height)

        cmds.append(DrawImage(self.node.image, rect)

        display_list.extend(cmds)
```

Images should now work and display on the page. But our implementation is
very basic and missing several important features for layout and rendering
quality.

::: {.further}
Discuss shadow DOM and "explaining input elements" in terms of HTML.
:::

Image sizing
============

At the moment, our browser can only draw an `<img>` element at its
[intrinsic size][intrinsic-size], i.e. the size of the source image data. But
that's only because we don't support any way to change it.

There are of course several ways for a web page to change an image's rendered
size.^[For example, the `width` and `height` CSS properties (not to be
confused with the `width` and `height` attributes!), which were an
exercise in Chapter 13.] But images *also* have, mostly for historical reasons
(because these attributes were invented before CSS existed), special `width`
and `height` attributes that override the intrinsic size. Let's implement
those.

[intrinsic-size]: https://developer.mozilla.org/en-US/docs/Glossary/Intrinsic_Size#

It's pretty easy: every place we deduce the width or height of an image layout
object from its intrinsic size, first consult the corresponding attribute and
use it instead if present. Let's start with `image` on `InlineLayout`. The width
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

``` {.python expected=False}
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
to specify `width` and not `height`, to infer the correct height from the
aspect ratio of the original image.

Implementing this change is very easy:[^only-recently-aspect-ratio] it's
just a few lines of edited code in `ImageLayout` to apply the aspect
ratio when only one attribute is specified.

[^only-recently-aspect-ratio]: Despite it being easy to implement, this
feature of real web browsers only appeared in 2021. Before that, developers
resorted to things like the ["padding-top hack"][padding-top-hack]. Sometimes
design oversights take a long time to fix.

[padding-top-hack]: https://web.dev/aspect-ratio/#the-old-hack-maintaining-aspect-ratio-with-padding-top

``` {.python}
class ImageLayout:
    def layout(self, zoom):
        # ...
        aspect_ratio = self.node.image.width / self.node.image.height
        has_width = "width" in self.node.attributes
        has_height = "height" in self.node.attributes

        if has_width:
            # ...
        elif has_height:
            self.width = aspect_ratio * \
                device_px(int(self.node.attributes["height"]), zoom)
        else:
            # ...   

        if has_height:
            # ...
        elif has_width:
            self.height = (1 / aspect_ratio) * \
                device_px(int(self.node.attributes["width"]), zoom)
        else:
            # ...
```

::: {.further}
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
screen, there are several different algorithms available for how to do it.
Decoding and resizing are both expensive.

To understand why, it's time to dig into what decoding actually does. *Decoding*
is the process of converting an *encoded* image from a binary form optimized
for quick download over a network into a *decoded* one suitable for rendering,
typically a raw bitmap in memory that can be a direct input into
rasterization on the GPU. It's called "decoding" and not "decompression"
because many encoded image formats are [*lossy*][lossy], meaning that
they "cheat": they don't faithfully represent all of the information in the
original picture, in cases where it's unlikely that a human viewing the decoded
image will notice the difference.

[lossy]: https://en.wikipedia.org/wiki/Lossy_compression

Many encoded image formats are very good at compression. This means that when a
browser decodes it, the resuting bitmap may take up quite a bit of memory, even
if the downloaded file size is not so big. As a result, it's very important for
browsers to do as little decoding as possible. Two ways they achieve that are
by avoiding decode for images not currently on the screen, and decoding
directly to the size actually needed to draw pixels on the screen. 

In addition, there is a big question of the *quality* of the decoding, in cases
where the decoded size is not the same as the intrinsic size. In this
situation, there are more (or fewer) pixels of intrinsic content than pixels on
the screen, and some algorithm is needed to decide which ones to pick and how
to mix adjacent pixels together. There are a bunch of possible *image
filtering* algorithms, such as choosing the "nearest" source image pixel,
a "bilinear" mix of pixels adjacent to the desired source pixel location, and
other fancier algorithms like
[Lanczos](https://en.wikipedia.org/wiki/Lanczos_resampling).

Let's optimize to take advantage of these new observations. We'll
decode directly the painted size rather than intrinsic, and utilize the
[`image-rendering`][image-rendering] CSS property to decide which image filter
algorithm to use.

[image-rendering]: https://developer.mozilla.org/en-US/docs/Web/CSS/image-rendering

This is not too hard, but requires doing the decode during paint rather than
load (because we don't know the painted size until after layout!). So first
store the *encoded* image instead of the *decoded* one during load:

``` {.python replace=Tab/Frame}
class Tab:
    # ...
    def load(self, url, body=None):
        # ...
        for img in images:
            # ...
                header, body = request(image_url, url)
                img.image = PIL.Image.open(io.BytesIO(body))
```

Then in layout, use that image for sizing.^[It's the same as the previous code
but on a `PIL` image instead of a Skia one, and now it's an attribute access,
so the only change is to remove some parentheses. I won't show the code here
since it's trivial.] And `decode_image` will also need to change:^[Note: Pillow
may not actually save any memory by doing this; nevertheless it should be clear
that it *can*. Real browsers optimize such things whenever possible.]

``` {.python}
def decode_image(encoded_image, width, height, image_quality):
    resample = None
    if image_quality == "crisp-edges":
        resample = PIL.Image.Resampling.LANCZOS
    pil_image = encoded_image.resize(\
        (int(width), int(height)), resample)
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
support, but real ones do). Another way is that an image may be animated from
one size to another, and it doesn't make sense to re-decode it at every size.

Real browsers push the image decoding step even further the rendering pipeline
(e.g. in the raster phase) for this reason---to avoid a double resize or worse
image quality. Yet another reason to do so is because raster happens on another
thread, and so that way image decoding won't block the main thread.
:::

Video & other embedded content
==============================

Images can also be animated.[^animated-gif] So if a website can load an image,
and the image can be animated, then that image is something very close to
a *video*. But in practice, videos need very advanced encoding and encoding
formats to minimize network and CPU costs, *and* these formats incure a lot of
other complications, chief among them [Digital Rights Mangement][drm]. To
support all this, the `<video>` tag supported by real browsers provide built-in
support for several common video [*codecs*][codec].^[In video, it's called a
codec, but in images it's called a *format*--go figure.] And on top of all
this, videos need built-in *media controls*, such as play and pause buttons,
and volume controls.

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

* External content that is "outside the web", meaning it's not HTML & CSS.

* External content that is "inside the web".

The first type is a *plugin*. There have been many attempts at plugins on the
web over the years. Some provided a programming language and mechanism for
interactive UI, such as [Java applets][java-applets] or [Flash].^[YouTube
originally used Flash for videos.] Others
provided a way to embed other content types into a web page, such as
[PDF]. These days, PDF rendering is pretty much the only plugin-style embedded
content type, and is referenced with the `<object>` or `<embed>` tag.^[You
might ask: why is it the only one left? The short answer is that the web is
already a fully functional UI system that should be general enough for any UI
(and if it isn't, the web should be extended to support it). So why have the
all the complications (security issues, compatibility, bugs, etc) of
yet another UI system that duplicates HTML? (Another reason is that plugins
tend to be proprietery. Note that PDF, originally developed as a proprietary
format, is [now an open standard][pdf-standard].)]

[java-applets]: https://en.wikipedia.org/wiki/Java_applet
[Flash]: https://en.wikipedia.org/wiki/Adobe_Flash
[PDF]: https://developer.mozilla.org/en-US/docs/Learn/HTML/Multimedia_and_embedding/Other_embedding_technologies#the_embed_and_object_elements
[pdf-standard]: https://en.wikipedia.org/wiki/PDF

But what about the other option: "inside the web" external content? One approach
for that is to provide a way for JavaScript to dynamically draw its own
content within an image. That approach is supported via the
[`<canvas>`][canvas-elt] element, which is an element that has all the same
layout features as an image,^[Except that canvases have no intrinsic sizing, so 
the `width` & `height` attributes, or their CSS equivalents, are necessary to
size the canvas.] plus an API that allows the developer to draw to it with
an API very similar to Skia.^[This element is not too hard to implement in a
basic form, so I've left it to an exercise.]

Canvas is a handy way to do a lot of things, but it comes with some pretty big
downsides. In particular, any content drawn inside of a `<canvas>` gets none of
the nice browser features such as accessibility, non-trivial^[It does have APIs
for drawing text, but no line breaking or block layout.] layout, automatic
rendering, or [navigation](chrome.md).

So the web has a second approach that retains all of those features: let the
developer embed one webpage inside another, via the `<iframe>` element. As
you'll see, this approach neatly solves all of these problems---accessibility,
etc come "for free". And as it turns out, iframes are a great way to include
"untrusted" content.

[canvas-elt]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/canvas

::: {.further}

Discuss ads as a form of embedded content.

:::


Iframes
=======

Iframes are websites embedded within other websites. With sufficient APIs
present,[^extensible-web] they are just as powerful as any plugin system, but
come with all of the security, accessibility, code reuse,
performance[^yes-performance] and open standards benefits of the web.

[^extensible-web]: In other words, over time APIs have been added that close
the gap between the use cases supported by iframes and "non-web" plugin
systems like Flash. For example, in the last decade the `<canvas>` element
(which can of course be placed within an iframe) supports hardware-accelerated
3D content, and [near-native-speed][webassembly] code.

[webassembly]: https://en.wikipedia.org/wiki/WebAssembly

[^yes-performance]: Yes, performance! While it's true that in principle
a non-web plugin can have higher peak performance, in practice they usually
have worse overall performance when embedded within a web plage, especially
on lower-end computers or mobile devices. That's because the plugin has its
own, entirely different, rendering and execution system, which leads to more
code and memory use, and worse performance coordination with the web page that
embeds it.

The `<iframe>` tag is a lot like the `<img>` tag: it has the `src` attribute and
`width` and `height` attributes. And an iframe is almost exactly the same as a
`Tab` within a `Tab`---it has its own HTML document, CSS, and scripts. There
are three significant differences though:

* *Iframes have no browser chrome*. So any page navigation has to happen from
   within the page (either through an `<a>` element or script), or as a side
   effect of navigation on the web page that *contains* the `<iframe>`
   element.

* Iframes do not necessarily have their own rendering event
loop. [^iframe-event-loop] In real browsers, [cross-origin] iframes are often
"site isolated", meaning that the iframe has its own CPU process for
[security reasons][site-isolation]. In our toy browser we'll just make all
iframes (even nested ones---yes, iframes can include iframes!) use the same
rendering event loop.

* Cross-origin iframes are *script-isolated* from their containing web page.
That means that a script in the iframe [can't access][cant-access] variables
or DOM in the containing page, nor can scripts in the containing page access
the iframe's variables or DOM.

[^iframe-event-loop]: For example, if an iframe has the same origin as the web
page that embeds it, then scripts in the iframe can synchronously access the
parent DOM. That means that it'd be basically impossible to put that iframe in
a different thread or CPU process, and in practice it ends up in the same
rendering event loop as a result.

[cross-origin]: https://developer.mozilla.org/en-US/docs/Web/Security/Same-origin_policy

[site-isolation]: https://www.chromium.org/Home/chromium-security/site-isolation/

[cant-access]: https://developer.mozilla.org/en-US/docs/Web/Security/Same-origin_policy#cross-origin_script_api_access

Since iframes are HTML documents, they can contain iframes. So in general each
`Tab` has a tree of HTML documents---*frames*---nested within each other. Each
node in this tree will be an object from a new `Frame` class. We'll use one
rendering event loop for all `Frame`s.

In terms of code, basically, we'll want to refactor `Tab` so that it's a
container for a new `Frame` class. The `Frame` will implement the rendering
work that the `Tab` used to do, and the `Tab` becomes a coordination and
container class for the frame tree. More specifically, the `Tab` class will:

* Kick off animation frames and rendering.
* Impement accessibility.
* Provide glue code between `Browser` and the documents to implement event
  handling.
* Proxy communication between frame documents.
* Own the display list for all frames in the tab.
* Commit to the browser thread.

And the `Frame` class will:

* Own the DOM, layout trees, and scroll offset for its HTML document.
* Own a `JSContext` if it is cross-origin to its parent.
* Run style, layout and paint on the its DOM and layout tree.
* Implement loading and event handling (focus, hit testing, etc) for its HTML
  document.

A `Frame` will also recurse into child `Frame`s for additional rendering and hit
testing. 

The `Tab`'s load method, for example, now simply manages history state and asks
its root frame to load:

``` {.python}
class Tab:
    def __init__(self, browser):
        self.root_frame = None

    def load(self, url, body=None):
        self.history.append(url)
        # ...
        self.root_frame = Frame(self, None, None)
        self.root_frame.load(url, body)
```
as do various event handlers, here's `click` for example:

``` {.python}
    def click(self, x, y):
        self.render()
        self.root_frame.click(x, y)
```

The `Frame` class has all of the rest of loading and event handling
that used to be in `Tab`. I won't go into those details except the part where
a `Frame` can load subframes via the `<iframe>` tag. In the code below, we
collect all of the `<iframe>` elements in the DOM in just the same way as we
did for `<img>`, but instead of loading the one resource and caching it,
we create a new `Frame` object, store it on the iframe element, and call
`load` recursively. Note that all the code in the "..." below is the same
as what used to be on `Tab`'s `load` method.


``` {.python}
class Frame:
    def load(self, url, body=None):
        # ...
        iframes = [node
                   for node in tree_to_list(self.nodes, [])
                   if isinstance(node, Element)
                   and node.tag == "iframe"
                   and "src" in node.attributes]
        for iframe in iframes:
            document_url = resolve_url(iframe.attributes["src"],
                self.tab.root_frame.url)
            iframe.frame = Frame(self.tab, self, iframe)
            iframe.frame.load(document_url)
```

That's pretty much it for loading, now let's investigate rendering.

::: {.further}
Expand on the security, performance, and open standards reasons iframes are
preferrable to plugins.
:::


Iframe layout and rendering
===========================

Just like with loading, a `Tab` delegates rendering to its root frame:

``` {.python replace=WIDTH/WIDTH%2C%20HEIGHT%20-%20CHROME_PX}
    # ...
    def render(self):
        # ...
            self.root_frame.style()
            # ...
            self.root_frame.layout(
                self.zoom, WIDTH)
            # ...
            self.root_frame.build_accessibility_tree()
            # ...
            self.root_frame.paint(self.display_list)
```

During style, recurse into iframes when they are found:[^style-real-browsers]

``` {.python}
def style(node, rules, tab):
    # ...

    if isinstance(node, Element) and node.tag == "iframe" \
        and node.frame:
        node.frame.style()
```

[^style-real-browsers]: In real browsers this doesn't work, because the output
of style for a frame depends on *layout* of the parent frame. That happens when
the child frame has [media queries][media-queries-15] that depend on the
iframe's size. But we don't have this problem because our toy browser doesn't
support media queries.

[media-queries-15]: https://developer.mozilla.org/en-US/docs/Web/CSS/Media_Queries

Now for layout. Let's start with the biggest layout difference between iframes
and images: unlike images, *iframes have no intrinsic size*. So their layout is
defined entirely by the attributes and CSS of the `iframe` element, and not at
all by the content of the iframe.[^seamless-iframe]

[^seamless-iframe]: There were attempts to provide such an intrinsic sizing in
the past, but it was [removed][seamless-removed] from the HTML specification
when no browser implemented it. This may change
[in the future][seamless-back], as there are good use cases for a *seamless*
iframe whose layout coordinates with its parent frame. 

[seamless-removed]: https://github.com/whatwg/html/issues/331
[seamless-back]: https://github.com/w3c/csswg-drafts/issues/1771

For iframes, if the `width` or `height` is not specified, it has a default
value.^[These numbers were chosen by someone a long time ago as reasonable
[defaults][iframe-defaults] based on average screen sizes of the day.]

[iframe-defaults]: https://www.w3.org/TR/CSS2/visudet.html#inline-replaced-width

``` {.python}
IFRAME_DEFAULT_WIDTH_PX = 300
IFRAME_DEFAULT_HEIGHT_PX = 150
```


Iframe layout looks like this in `InlineLayout`. The only difference from images
is the width and height calculation, so I've omitted that part with "..."
instead.

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
            w = IFRAME_DEFAULT_WIDTH_PX
        # ...
```

And the `IframeLayout` layout code is also similar; again, I've omitted the
unchanged parts from images. (Note however that there is no code regarding
aspect ratio, because iframes don't have an intrinsic size.) And at the end,
recurse into the layout method of the child frame.

TODO: fix expected here.
``` {.python replace=%2C%20self.width/%2C%20self.width%2C%20self.height}
class IframeLayout:
    # ...
    def layout(self, zoom):
        # ...
        if has_width:
            # ...
        else:
            self.width = device_px(IFRAME_DEFAULT_WIDTH_PX, zoom)

        if has_height:
            # ...
        else:
            self.height = device_px(IFRAME_DEFAULT_HEIGHT_PX, zoom)

        # ...

        self.node.frame.layout(zoom, self.width)
```

As for painting, iframes by default have a border around their content when
painted. They also clip the iframe painted content to the bounds of the 
`<iframe>` element.

``` {.python expected=false}
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


::: {.further}

Before iframes, there were the [`<frameset>` and `<frame>`][frameset] elements.
These elements define a special layout of multiple web pages in a single
browser window; if present, a `<frameset` replaces the
`<body>` tag and splits the screen among the `<frame>`s specified. In the early
days of the web, this was an alternate model to the CSS-based model I've
presented in this book. The old model had confusing navigation and
accessibility, and was strictly less flexible than use of `<iframe>`, so
although all real browsers support them for legacy reasons, this feature is
obsolete.
:::

[frameset]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/frameset

Iframe scripts
==============

Now we need to implement script behavior for iframes. All frames in the frame
tree have their own global script namespace. In fact, the `Window` class
(and `window` variable object) represents the [global object][global-object],
and all global variables declared in a script are implicitly defined on this
object. The simplest way to achieve this is by having each `Frame` object own
its own `JSContext`, and by association its own DukPy interpreter. That's what
`Tab` already did, and we can just copy all of its code for it.

[global-object]: https://developer.mozilla.org/en-US/docs/Glossary/Global_object

But that only works if we consider every frame *cross-origin* from all of the
others. Two frames that have the same origin each get a global namespace for
their scripts, but they can access each other's frames through, for example,
the [`parent` attribute][window-parent] on their `Window`.^[There are various
other APIs; see the related exercise.] For example, JavaScript in a same-origin
child frame can access the `document` object for the DOM of its parent frame
like this:

    console.log(window.parent.document)

We need to implement that somehow. Unfortunately, DukPy doesn't natively support
the feature of
"evaluate this script under the given global variable". 

[window-parent]: https://developer.mozilla.org/en-US/docs/Web/API/Window/parent

Instead of switching to whole new JavaScript runtime, I'll just approximate the
feature with two tricks: overwriting the `window` object and the `with`
operator. The `with` operator is pretty obscure, but what it does is
evaluate the content of a block by looking up objects on the given 
object.^[It's important to reiterate that this is a hack and doesn't actually
do things correctly, but it suffices for our toy browser.]
This example:

    var win = {}
    win.foo = 'bar'
    with (win) { console.log(foo); }

will print "bar", whereas without the "with" clause foo will not resolve to any
variable.^[The `with` hack is only needed to support "unqualified" global
variable access; if instead, you change all the example web pages we've been
testing with this book to replace globals references such as `foo` with
`window.foo`, then the hack will be unnecessary to make those examples work.]

For each `JSContext`, we'll keep track of the set of frames that all use it, and
store a `Window` object for each, associated with the frame it comes from, in
variables called `window_0`, `window_1`, etc. Then whenever we need to evaluate
a script from a particular frame, we'll wrap it in some code that overwrites
the `window` object and evalutes via `with`. 

``` {.python}
def wrap_in_window(js, window_id):
    return ("window = window_{window_id}; " + \
    "with (window) {{ {js} }}").format(js=js, window_id=window_id)
```

When multiple frames will have just one `JSContext`, we'll just store
the `JSContext` on the "root" one---the frame closest to the frame tree root
that has a particular origin, and reference it from descendant
frames.[^disconnected]

All this will require passing the parent frame as a
constructor parameter and keeping track of window ids:

[^disconnected]: This isn't actually correct. Any frame with the same origin
should be in the "same origin" set, even if they are in disconnected pieces
of the frame tree. For example, if a root frame with origin A embeds an
iframe with origin B, and the iframe embeds *another* iframe with origin A,
then the two A frames can access each others' variables. I won't implement
this complication and instead left it as an exercise.

``` {.python}
WINDOW_COUNT = 0

class Frame:
    def __init__(self, tab, parent_frame, frame_element):
        self.parent_frame = parent_frame
        # ...
        global WINDOW_COUNT
        self.window_id = WINDOW_COUNT
        WINDOW_COUNT += 1
    # ...
    def get_js(self):
        if self.js:
            return self.js
        else:
            return self.parent_frame.get_js()
```

The `JSContext` needs a way to create the `window_*` objects:

``` {.python}
class JSContext:
    def add_window(self, frame):
        self.interp.evaljs(
            "var window_{window_id} = \
                new Window({window_id});".format(
                window_id=frame.window_id))
```

And then initializing the `JSContext` for the root. Here we need to evaluate
definition of the `Window` class separately from `runtime.js`, because
`runtime.js` needs to be passed to `wrap_in_window`. And `wrap_in_window`
needs `Window` defined exactly once, not each time it's called. The `Window`
constructor stores its id, which will be useful later.

``` {.python replace=%20or%20/%20or%20CROSS_ORIGIN_IFRAMES%20or%20}
    def load(self, url, body=None):
        # ...
        if not self.parent_frame or \
            url_origin(self.url) != url_origin(self.parent_frame.url):
            self.js = JSContext(self.tab)
            self.js.interp.evaljs(\
                "function Window(id) { this._id = id };")
        js = self.get_js()
        js.add_window(self)
        # ...
        for iframe in iframes:
            # ...
                iframe.frame = Frame(self.tab, self, iframe)
```


And whenever scripts are evaluated, they are wrapped (note the extra window
id parameter):

``` {.python}
class JSContext:
    def run(self, script, code, window_id):
        try:
            print("Script returned: ", self.interp.evaljs(
               wrap_in_window(code, window_id)))
        except dukpy.JSRuntimeError as e:
            print("Script", script, "crashed", e)
        self.current_window = None
```

And pass that argument from the `load` method:

``` {.python}
class Frame:
    def load(self, url, body=None):
        # ...
        with open("runtime15.js") as f:
            wrapped = wrap_in_window(f.read(), self.window_id)
            js.interp.evaljs(wrapped)
        # ...
        for script in scripts:
            # ...
            task = Task(\
                self.get_js().run, script_url, body.decode('utf8)'),
                self.window_id)
```

Iframe script APIs
==================

With these changes, you should be able to load basic scripts in iframes. But
none of the runtime browser APIs work yet, because they don't know which
`Window` to reference. There are two types of such APIs:

* Synchronous APIs that modify the DOM or query it (e.g. `querySelectorAll`).

* Event-driven APIs that execute JavaScript callbacks or event handlers
(`requestAnimationFrame` and `addEventListener`).

Let's first tackle the former. We'll start by implementing the `parent`
attribute on the `Window` object. It isn't too hard---mostly passing the window
id to Python so that it knows on which frame to run the API.

On the Python side, the `parent` method on `JSContext` will be passed the id of
the window that wants its parent computed. We'll need to convert that id into a
`Frame` object, and then return the `parent_frame` of that object.
(The `parent_frame` `Frame` member variable was implemented earlier in the
chapter.)

To convert from window id to `Frame`, we'll need a mapping on `Tab` that does
so:

``` {.python}
class Tab:
    def __init__(self, browser):
        self.window_id_to_frame = {}
```

And in each `Frame`, adding itself to the mapping:

``` {.python}
class Frame:
    def __init__(self, tab, parent_frame, frame_element):
        # ...
        self.tab.window_id_to_frame[self.window_id] = self
```

And now we can use it:

``` {.python}
class JSContext:
    # ...
    def parent(self, window_id):
        parent_frame = \
            self.tab.window_id_to_frame[window_id].parent_frame
        if not parent_frame:
            return None
        return parent_frame.window_id
```

On the JavaScript side, the most interesting bit is what to do with the id
returned from Python. What it will do is to find the "`window_<id>`" object,
which we can obtain via the `eval` JavaScript function.^[If you don't know
about `eval`,, it does the same thing as the DukPy `evaljs` method.] And if the
eval throws a "variable not defined" exception, that means the window object is
not defined, which can only be the case if the parent is cross-origin to the
current window. In that case, return a fresh `Window` object with the fake id
`-1`.^[Which is also correct, because cross-oriign frames can't access each
others' variables. However, in a real browser this `Window` object is not
totally fake---see the related exercise at the end of the chapter.]

``` {.html}
Object.defineProperty(Window.prototype, 'parent', {
  configurable: true,
  get: function() {
    parent_id = call_python('parent', window._id);
    if (parent_id != undefined) {
        try {
            target_window = eval("window_" + parent_id);
            // Same-origin
            return target_window;
        } catch (e) {
            // Cross-origin
            return new Window(-1)
        }

    }
    return undefined;
  }
});
```

The same technique works for other runtime APIs, such as `querySelectorAll`.
The Python for that API is:

``` {.python}
class JSContext:
    def querySelectorAll(self, selector_text, window_id):
        frame = self.tab.window_id_to_frame[window_id]
        selector = CSSParser(selector_text).selector()
        nodes = [node for node
                 in tree_to_list(frame.nodes, [])
                 if selector.matches(node)]
        return [self.get_handle(node) for node in nodes]
```

And JavaScript:

``` {.javascript}
window.document = { querySelectorAll: function(s) {
    var handles = call_python("querySelectorAll", s, window._id);
    return handles.map(function(h) { return new Node(h) });
}}
```

Next let's do callback-based APIs, starting with `requestAnimationFrame`.
On the JavaScript side, the only change needed is to store `RAF_LISTENERS`
on the `window` object instead of the global scope, so that each
window gets its own separate listeners.

``` {.javascript}
window.RAF_LISTENERS = [];

window.requestAnimationFrame = function(fn) {
    window.RAF_LISTENERS.push(fn);
    call_python("requestAnimationFrame");
}

window.__runRAFHandlers = function() {
    # ...
    for (var i = 0; i < window.RAF_LISTENERS.length; i++) {
        handlers_copy.push(window.RAF_LISTENERS[i]);
    }
    window.RAF_LISTENERS = [];
}

```

The Python side will just cause the `Tab` to run an animation frame, just like
before, so no change there. But we do need to change `run_animation_frame`
to loop over all frames and call callbacks registered. Because each one
uses `wrap_in_window`, the correct `Window` object is bound to the `window`
variable and `RAF_LISTENERS` resolves to the correct variable for each frame.

``` {.python}
class Tab:
    def run_animation_frame(self, scroll):
        # ...
        for (window_id, frame) in self.window_id_to_frame.items():
            frame.get_js().interp.evaljs(
                wrap_in_window("__runRAFHandlers()", window_id))
```

Event listeners are similar. Registering one is now stored on the window:

``` {.javascript}
window.LISTENERS = {}
# ...
Node.prototype.addEventListener = function(type, listener) {
    if (!window.LISTENERS[this.handle])
        window.LISTENERS[this.handle] = {};
    var dict = window.LISTENERS[this.handle];
    # ...
}

Node.prototype.dispatchEvent = function(evt) {
    # ...
    var list = (window.LISTENERS[handle] &&
        window.LISTENERS[handle][type]) || [];
    # ...
}

```

Dispatching the event requires `wrap_in_window`.^[All of the callsites of
`dispatch_event` (`cick`, `submit_form`, and `keypress`) will need an additional
parameter of the window id; I've omitted those code fragments.]

``` {.python}
class JSContext:
    def dispatch_event(self, type, elt, window_id):
        # ...
        do_default = self.interp.evaljs(
            wrap_in_window(EVENT_DISPATCH_CODE, window_id),
            type=type, handle=handle)
```

And that's it! I've omitted `setTimeout` and `XMLHTTPRequest`, but each of them uses
one or both of the above techniques. As an exercise, migrate each of them
to the new pattern..

On the other hand, the rest work as-is: `getAttribute`, `innerHTML`, `style` and
`Date`.^[Another good exercise: can you explain why these don't need any
changes?]


::: {.quirk}
Demos from previous chapters might not work, because the `with` operator hack
doesn't always work. To fix them you'll have to replace some global variable
references with one on `window`. For example, `setTimeout` might need to change
to `window.setTimeout`, etc.

The DukPy version you're using might also have a bug in the interaction between
functions defined with the `function foo() { ... } ` syntax and the `with`
operator. To work around it and run the animation tests from Chapter 13 with
the runtime changes from this chapter, you'll probably need to edit the
examples from that chapter to use the `foo = function() { ... } ` syntax
instead.
:::


::: {.further}
Same-origin iframes can not only synchronously access each others' variables,
they can also change their origin! That is done via the
[`domain`][domain-prop] property on the `Document` object. If this sounds weird,
hard to implement correctly, and a mis-feature of the web, then you're right.
That's why this feature is gradually being removed from the web.
There are also [various headers][origin-headers] available for sites to opt
into iframes having fewer features along these lines, with the benefit being
better security and performance (isolated iframes can run in their own thread
or CPU process).

[origin-headers]: https://html.spec.whatwg.org/multipage/browsers.html#origin-isolation

You could also argue that it's questionable whether same-origin iframes should
be able to access each others' variables. That may also be a
mis-feature---what do you think?
:::

[domain-prop]: https://developer.mozilla.org/en-US/docs/Web/API/Document/domain

Iframe message passing
======================

Cross-origin iframes can't access each others' variables, but that doesn't
mean they can't communicate. Instead they communicate via
[*message passing*][message-passing], a technique for structured communication
between two different event loops that doesn't require any shared variable
state or locks.

[message-passing]: https://en.wikipedia.org/wiki/Message_passing

Message-passing in JavaScript works like this: you call the
[`postMessage` API][postmessage] on the `Window` object you'd like to talk to,
with the message itself as the first parameter, and `*` as the
second.^[The second parameter has to do with
origin restrictions, see the accompanying exercise.] Calling:

[postmessage]: https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage

    window.parent.postMessage("message contents", '*')

will broadcast "message contents" to the parent frame. A frame can listen to
the message by adding an event listener on its `Window` object for the
"message" event. Note that in this case `window` is *not* the same object! It's
 the `Window` object for some other frame.

    window.addEventListener("message", function(e) {
        console.log(e.data);
    });

In a real browser, you can also pass data that is not a string, such as numbers
and objects. It works via a *serialization* algorithm called
[structured cloning][structured-clone]. Structured cloning converts a
JavaScript object of arbitrary^[Mostly. For example, DOM notes cannot be sent
across, because it's not OK to access the DOM in multiple threads, and
different event loops might be assigned different threads in a browser.]
structure to a sequence of raw bytes, which are *deserialized* on the other end
into a new object that has the same structure.

[structured-clone]: https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API/Structured_clone_algorithm

Let's implement `postMessage`.^[I won't provide support for cloning anything
other than basic types like string and number, because DukPy doesn't support
structured cloning natively.]

In the JavaScript runtime, we'll need a new `WINDOW_LISTENERS` array
to keep track of event listeners for messages (the old `LISTENERS` was only
for events on `Node` objects).

``` {.javascript}
    window.WINDOW_LISTENERS = {}
```

Then we need a way to structure the event object passed to the listener:

``` {.javascript}
window.PostMessageEvent = function(data) {
    this.type = "message";
    this.data = data;
}
```

The event listener and dispatching code is the same as for `Node`, except
it's on `Window`:

``` {.javascript}
Window.prototype.addEventListener = function(type, listener) {
    if (!window.WINDOW_LISTENERS[this.handle])
        window.WINDOW_LISTENERS[this.handle] = {};
    var dict = window.WINDOW_LISTENERS[this.handle];
    if (!dict[type]) dict[type] = [];
    var list = dict[type];
    list.push(listener);
}

Window.prototype.dispatchEvent = function(evt) {
    var type = evt.type;
    var handle = this.handle
    var list = (window.WINDOW_LISTENERS[handle] &&
        window.WINDOW_LISTENERS[handle][type]) || [];
    for (var i = 0; i < list.length; i++) {
        list[i].call(this, evt);
    }

    return evt.do_default;
}
```

And finally, there is the `postMessage` method itself. It has to pass `self._id`
because the post message is broadcast to all windows *except* the current one:

``` {.javascript}
Window.prototype.postMessage = function(message, origin) {
    call_python("postMessage", this._id, message, origin)
}
```

Over in Python land, `postMessage` schedules a `post_message` task on the
`Tab`. Why schedule a task instead of sending the messages synchrously, you
might ask? It's because `postMessage` is an *async* API that expressly does
not allow synchronous bi-directly (or uni-directional, for that matter)
communication. Asynchrony, callbacks and message-passing are inherent
features of the JavaScript+event loop programming model.

``` {.python}
class JSContext:
    def postMessage(self, target_window_id, message, origin):
        task = Task(self.tab.post_message, message, target_window_id)
        self.tab.task_runner.schedule_task(task)
```

Which then runs this code, that loops over all other frames and dispatches
an event:

``` {.python}
class Tab:
    def post_message(self, message, target_window_id):
        frame = self.window_id_to_frame[target_window_id]
        frame.get_js().dispatch_post_message(
            message, target_window_id)
```

The event happens in the usual way:

``` {.python}
class JSContext:
    def dispatch_post_message(self, message, window_id):
        self.interp.evaljs(
            wrap_in_window(
                "dispatchEvent(new PostMessageEvent(dukpy.data))",
                window_id),
            data=message)    
```

Try it out on [this demo](examples/example15-iframe.html). You should see
"Message received from iframe: This is the contents of postMessage." printed to
 the console.

Iframe input events
===================

Scripts and events now function properly in iframes, but user input does not.
It's not (yet) possible to click on a element in an iframe, rotate through
its focusable elements, scroll it, or generate an acccessibility tree.

Let's fix that. Clicking requires checking for an `<iframe>` element:

TODO: logic for click moved to `Frame`.

``` {.python}
class Frame:
    def click(self, x, y):
        # ...
        while elt:
            # ...
            elif elt.tag == "iframe":
                obj = elt.layout_object
                elt.frame.click(x - obj.x, y - obj.y)
                return
```

And now that clicking works, clicking on `<a>` elements will work. Which means
that you can now cause a frame to navigate to a new page. And because a
`Frame` has all the loading and navigation logic that `Tab` used to have, it
just works without any more changes! That's satisfying.

Focusing an element now also needs to store the frame the focused element is
on (the `focus` value will still be stored on the `Tab`, not the `Frame`:

``` {.python}
class Tab:
    def __init__(self, browser):
        self.focus = None
        self.focused_frame = None
```

``` {.python}
class Frame:
    def focus_element(self, node):
        if node and node != self.tab.focus:
            self.needs_focus_scroll = True
        if self.tab.focus:
            self.tab.focus.is_focused = False
        self.tab.focus = node
        self.tab.focused_frame = self
        if node:
            node.is_focused = True
        self.tab.set_needs_render()
```

Advancing a tab will use the focused frame (and move the rest of the business
logic for `advance_tab` to `Frame`:

``` {.python}
class Tab:
    def advance_tab(self):
        frame = self.focused_frame
        if not frame:
            frame = self.root_frame
        frame.advance_tab()
```

Now for scrolling. This will require moving scrolling onto `Frame` instead of
`Browser` or `Tab`. TODO: explain nuances

``` {.python}
class Frame:
    def __init__(self, tab, parent_frame, frame_element):
        self.scroll = 0
```

Clamping will now happen differently, because non-root frames have a height
that is not defined by the size of the browser window, but rather their
containing `<iframe>` element. To handle this let's add a paramter to `layout`
indicating this height, and record it in `frame_height`:

``` {.python}
class Frame:
    def __init__(self, tab, parent_frame, frame_element):
        self.frame_height = 0
    # ...
    def layout(self, zoom, width, height):
        self.frame_height = height
```

The root frame will have a browser window-based height:

``` {.python}
class Tab:
    def render(self):
        # ...
            self.root_frame.layout(
                self.zoom, WIDTH, HEIGHT - CHROME_PX)
```

And in `IframeLayout`, the height of the `<iframe>` element:

``` {.python}
class IframeLayout:
    def layout(self, zoom):
        # ...
        self.node.frame.layout(zoom, self.width, self.height)
```

We'll use this to do clamping based on this height:

``` {.python}
class Frame:
    def clamp_scroll(self, scroll):
        return max(0, min(
            scroll,
            math.ceil(
                self.document.height) - self.frame_height))
```

Now change all callsites of `clamp_scroll` to use the method rather than the
global function:

``` {.python}
class Frame:
    def scroll_to(self, elt):
        # ...
        self.scroll = self.clamp_scroll(new_scroll)
```

``` {.python}
class Frame:
    def layout(self, zoom, width, height):
        # ...
        clamped_scroll = self.clamp_scroll(self.scroll)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_frame = True
```

Our browser supports browser-thread scrolling, but only for the root frame.
To handle both cases, we'll need a new commit parameter:

``` {.python}
class CommitData:
    def __init__(self, url, scroll, root_frame_focused, height, display_list,
                 composited_updates, accessibility_tree, focus):
        # ...
        self.root_frame_focused = root_frame_focused
```

``` {.python}
class Tab:
    def run_animation_frame(self, scroll):
        commit_data = CommitData(
            # ...
            root_frame_focused=not self.focused_frame or \
                (self.focused_frame == self.root_frame),
            # ...
        )
```

``` {.python}
class Browser:
    def commit(self, tab, data):
        # ...
            self.root_frame_focused = data.root_frame_focused

```

And now we can use this parameter to keep browser scrolling for the root frame.

``` {.python}
class Browser:
    def handle_down(self):
        self.lock.acquire(blocking=True)
        if self.root_frame_focused:
            # ...
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.scrolldown)
        active_tab.task_runner.schedule_task(task)
        self.lock.release()        
```

``` {.python}
class Tab:
    def scrolldown(self):
        frame = self.focused_frame
        if not frame: frame = self.root_frame
        frame.scrolldown()
        self.set_needs_paint()
```

``` {.python}
class Frame:
    def scrolldown(self):
        self.scroll = self.clamp_scroll(self.scroll + SCROLL_STEP)
```

Accessibility trees for iframes are also relatively simple to get the basics
working. There will be only one tree for all frames, and so we just need
a role for iframes:

``` {.python}
class AccessibilityNode:
    def __init__(self, node):
            elif node.tag == "iframe":
                self.role = "iframe"
```

And to recurse into them in `build`:

``` {.python}
class AccessibilityNode:
   def build(self):
        if isinstance(self.node, Element) \
            and self.node.tag == "iframe":
            self.build_internal(self.node.frame.nodes)
        # ... 
```

::: {.further}
While our toy browser only has threaded scrolling of the root frame, a real
browser should aim to make scrolling threaded (and composited) for all
the other frames, and via all the ways you can scroll---keyboard, touch,
mouse wheel, scrollbars of different types, and so on.
(And of course, due to the [`overflow`][overflow-css]
CSS property, there can be any number of nested scrollers within each 
other in a single frame.)

Getting this right in all the corner cases
is pretty hard, and it took each major browser quite a while to get it right.
Only [in 2016][renderingng-scrolling], for example, was Chromium able to
achieve it, and even then, there turned out be a very long tail of more or
less obscure bugs to fix involving different combinations of complex
containing blocks, stacking order, scrolbars, transforms and other visual
effects.
:::

[overflow-css]: https://developer.mozilla.org/en-US/docs/Web/CSS/overflow
[renderingng-scrolling]: https://developer.chrome.com/articles/renderingng/#threaded-scrolling-animations-and-decode

Iframe security
===============

I've already discussed security in Chapter 10, but iframes cause new classes
of security problem that are worth briefly covering here. However, there
isn't anything new to implement in our browser for this section, so consider
it optional reading.

Iframes are very powerful, because they allow a web page to embed another one.
But with that power comes a commensurate security risk in cases where the
embedded web page is cross-origin to the main page. After all, it's literally a
website controlled by someone else that renders into the same page as yours.
And since it's unlikely that you really trust that other web page, you want to
be protected from any security or privacy risks that page may represent.

The fact that cross-origin iframes can't access their parents directly already
provides a reasonable starting point. But it doesn't protect you if a
browser bug allows JavaScript in an iframe to cause a
[buffer overrun][buffer-overrun], which an attacker exploints to run
arbitrary code. To protect against such a situation, browsers these days
load webpages in a security [*sandbox*][sandbox], which prevents arbitrary
code from such an attack from escaping the sandbox, thus (usually) protecting
your OS, cookies, personal data and so on from being compromised.
But we'd also like to separate the frames in a web page from each other,
because there is also of plenty of user data embedded directly in each page.

[buffer-overrun]: https://en.wikipedia.org/wiki/Buffer_overflow

That's the reason many browsers these days place each iframe in its own CPU
process sandbox; this technique is called
[*site isolation*][site-isolation]. Implementing site isolation seems
conceptually "straightforward", in the same sense that the browser thread we
added in chapter 13 is "straightforward". In practice, there are so many
browser APIs and subtleties that both features are extremely complex and subtle
in their full glory. That's why it took many years for Chromium to ship the
first implementation of site isolation.

[sandbox]: https://en.wikipedia.org/wiki/Sandbox_(computer_security)

[site-isolation]: https://www.chromium.org/Home/chromium-security/site-isolation/

The importance of site isolation has greatly increased in recent years, due to
the discovery of certain CPU cache timing attacks called *spectre*
and *meltdown*.^[There's even a
[website devoted to them][spectre-meltdown]---check out the videos and links on
the website to see it in action!] In short, these attacks allow an attacker to
read arbitrary locations in memory (e.g., the user's data!)
as long as you have access to a high-precision timer. They do so by exploiting
the timing of various features in modern CPUs. Placing sensitive content
in different CPU processes (which come with their own memory address spaces) is
a good protection against these attacks, and that's just what site isolation
does.

[spectre-meltdown]: https://meltdownattack.com/

But that's not the only protection needed. It's also important to 
*remove high-precision timers*^[A *high precision timer* is anything that can
 measure duration of execution of code very accurately.] from the platform. So
 browsers did things like reducing the accuracy of APIs like `Date.now` or
 `setTimeout`. But there are some browser APIs that don't seem like timers yet
 still are, such as [SharedArrayBuffer].^[Check out[this explanation]
 [sab-attack] if you want to learn more.] Since this API is still useful, and
 there is no good way to make it "less accurate", browsers now require
 [certain optional HTTP headers][sab-headers] to be present on the parent *and*
 child frames' HTTP responses in order to allow use of `SharedArrayBuffer`.

[SharedArrayBuffer]: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer

[sab-attack]: https://security.stackexchange.com/questions/177033/how-can-sharedarraybuffer-be-used-for-timing-attacks

[sab-headers]: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer#security_requirements


::: {.further}
The required headers for `SharedArrayBuffer` also caused problems for
the *Web Browser Engineering* website, when I [added JavaScript support][js-blog]
to embedded widgets. These widgets use `SharedArrayBuffer` to polyfill the way
that runtime JavaScript APIs talk to the browser. It worked, but in order
to make it an embeded widget required setting the opt-in headers for that API.
Unfortunaely, doing so broke an embedded YouTube video in Chapter 14,
because YouTube does not (yet?) set this header.

I worked around the issue by not embedding the widget as a sub-frame of the
website in chapter 9, and instead [asking the reader](scripts.html#outline) to
open a new browser window. This kind of complication---ensuring headers are set
correctly on all frames, including third-party dependencies---is very common
when trying to implement more advanced features on websites.
:::

[js-blog]: https://browserbook.substack.com/p/javascript-in-javascript

Summary
=======

This chapter introduced embedded content, via the examples of images and
iframes. Reiterating the main points:

* Embedded content is a way to allow "non-HTML" content---images, video, canvas,
  iframes, input elements or plugins---to be added to a webpage.

* Over time, plugins that are not PDF viewers, images or video have been
  replaced with the more general-purpose *iframe* element, which over time has
  become just as powerful as any plugin, and benefits from all the hard-won
  attributes of a browser such as its rendering pipeline, accessibility, and
  open standards.

* Because iframes contain an entire web page and all its
complexities---rendering, event handling, navigation, security---as well as
the ability to embed other iframes, they add quite a lot of complexity to
a browser implementation. However, this complexity is justified, because they
enable many important cross-origin use cases, such as ads, video, and social
media references, to be safely added to web sites.

* On the whole, canvases,^[Try the exercise about the `<canvas>` element to see
  for yourself!] and even iframes, are not *that* hard to implement in a very
  basic form, because they reuse a lot of the code and concepts I've explained
  in earlier chapters. But implementing them really well---as with all good
  things in this life---takes a lot of effort and attention to detail.

Exercises
=========

*Canvas element*: Implement the [`<canvas>`][canvas-elt] element, the 2D aspect
 of the [`getContext`][getcontext] API, and some of the drawing commands on
 [`CanvasRenderingContext2D`][crc2d]. Canvas layout is just like an iframe, but
 doesn't have nearly as much internal complexity. Instead you just need to
 allocate a Skia canvas of an appropriate size when `getContext("2d")` is
 called, and implement some of the APIs that draw to the canvas.
 [^eager-canvas] It should be straightforward to translate these to Skia
 methods.

 [crc2d]: https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D

[^eager-canvas]: Note that once JavaScript draws to a canvas, the drawing
persists forever until [`reset`][canvas-reset] or similar is called. This
allows a web developer to build up a display list with a sequence of commands,
but also places the burden on them to decide when to do so, and also when to
clear it when needed. This approach is called an *immediate mode* of
rendering---as opposed to the [*retained mode*][retained-mode] used by HTML,
which does not have this complexity.

[retained-mode]: https://en.wikipedia.org/wiki/Retained_mode


[canvas-reset]: https://html.spec.whatwg.org/multipage/canvas.html#dom-context-2d-reset

[getcontext]: https://developer.mozilla.org/en-US/docs/Web/API/HTMLCanvasElement/getContext

*Background images*: elements can have not just `background-color`, but also
[`background-image`][bg-img]. Implement the basics of this CSS property for
images loaded by URL. Also implement the [`background-size`][bg-size] CSS
property so the image can be sized in various ways.

[bg-img]: https://developer.mozilla.org/en-US/docs/Web/CSS/background-image

[bg-size]: https://developer.mozilla.org/en-US/docs/Web/CSS/background-size

*Object-fit*: implement the [`object-fit`][obj-fit] CSS property. It determines
how the image within an `<img>` element is sized relative to its container
element.

[obj-fit]: https://developer.mozilla.org/en-US/docs/Web/CSS/object-fit

*Lazy decoding*: Decoding images can take time and use up a lot of memory.
But some images, especially ones that are "below the fold"[^btf]---meaning they
are further down in a web page and not visible and only exposed after some
scrolling by the user. Implement an optimization in your browser that only
decodes images that are visible on the screen.

[^btf]: "Below the fold" is a term borrowed from newspapers, meaning content
you can't see when the newspaper is folded in half.

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

*Same-origin frame tree*: same-origin iframes can access each others' variables
 and DOM, even if they are not adjacent in the frame tree. Implement this.

*Iframe media queries*. Implement.

*Iframe aspect ratio*. Implement the [`aspect-ratio`][aspect-ratio] CSS
property and use it to provide an implicit sizing to iframes and images
when only one of `width` or `height` is specified (or when the image is not
yet loaded, if you did the lazy loading exercise).

[aspect-ratio]: https://developer.mozilla.org/en-US/docs/Web/CSS/aspect-ratio

*Target origin for `postMessage`*: implement the second parameter of
[`postMssage`][postmessage]: `targetOrigin`. This parameter is a protocol,
hostname and port string that indicates which origin is allowed to receive
the message.

*Iframe history*: when iframes navigate (e.g. via a click on an `<a>` element,
it affects browser history. In other words, if an iframe navigates, then the
user presses the back button, it should navigate the iframe back to where it
was; a second back button press navigates the parent page to its previous state.
Implement this feature.^[It's debatable whether this is a good feature of
iframes, as it causes a lot of confusion for web developers who embed iframes
they don't plan on navigating.]

*Multi-frame focus*: in our toy browser, pressing `tab` repeatedly goes through
 the elemnts in a single frame. But this is bad for accessibility, because
 it doesn't allow a user of the keyboard to obtain access to focusable elements
 in other frames.