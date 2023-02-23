---
title: Supporting Embedded Content
chapter: 15
prev: accessibility
next: invalidation
...

While our toy browser can render complex styles, visual effects, and
animations, all of those apply basically just to text. Yet web pages
contain a variety of non-text *embedded content*, from images through
to iframes that embed one web page inside another. Embedded content of
this sort has been essential throughout the web's history, and support
for embedded content has powerful implications for browser
architecture, performance, security, and open information access.


Images
======

Images are certainly the most popular kind of embedded content on the
web, dating back to [early 1993][img-email].[^img-history] They're
included on web pages via the `<img>` tag, which looks like this:

    <img src="https://browser.engineering/im/hes.jpg">

[img-email]: http://1997.webhistory.org/www.lists/www-talk.1993q1/0182.html

[^img-history]: So it's a little ironic that images only make their
appearance in chapter 15 of this book! My excuse is that Tkinter
doesn't support proper image sizing and clipping, and doesn't support
very many image formats, so we had to wait for the introduction of
Skia.

And which renders something like this:

<figure>
    <img src="im/hes.jpg">
    <figcaption>Hypertext Editing System <br/> (Gregory Lloyd from <a href="https://commons.wikimedia.org/wiki/File:HypertextEditingSystemConsoleBrownUniv1969.jpg">Wikipedia</a>, <a href="https://creativecommons.org/licenses/by/2.0/legalcode" rel="license">CC BY 2.0</a>)</figcaption>
</figure>

Luckily, implementing images isn't too hard, so let's just get
started. There are four steps to displaying images in our browser:

1. Download the image from a URL.
2. Decode the image into a buffer in memory.
3. Lay the image out on the page.
4. Paint the image in the display list.

Let's start with downloading images from a URL. Naturally, that
happens over HTTP, which we already have a `request` function for.
However, all of the content we've downloaded so far---HTML, CSS, and
JavaScript---has been textual, but images typically use binary data
formats. So we'll need to extend `request` to support binary data.

The change is pretty minimal: instead of passing the `"r"` flag to
`makefile`, pass a `"b"` flag indicating binary mode:

``` {.python}
def request(url, top_level_url, payload=None):
    # ...
    response = s.makefile("b")
    # ...
```

Now every type we read from `response`, we will get `bytes` of binary
data, not a `str` with textual data, so we'll need to change some HTTP
parser code to explicitly `decode` the data:

``` {.python}
def request(url, top_level_url, payload=None):
    # ...
    statusline = response.readline().decode("utf8")
    # ...
    while True:
        line = response.readline().decode("utf8")
        # ...
    # ...
```

Note that I _didn't_ add a `decode` call when we read the body; that's
because the body might actually be binary data, and we want to return
that binary data directly to the browser. Now, every existing call to
`request`, which wants textual data, needs to `decode` the response.
For example, in `load`, you'll want to do something like this:

``` {.python replace=Tab/Frame}
class Tab:
    def load(self, url, body=None):
        # ...
        headers, body = request(url, self.url, payload=body)
        body = body.decode("utf8")
        # ...
```

Make sure to make this change everywhere in your browser that you call
`request`, including inside `XMLHttpRequest_send` and in several other
places in `request`. When we download images, however, we _won't_ call
`decode`, and just use the binary data directly:

``` {.python replace=tab/frame}
def download_image(image_src, tab):
    image_url = resolve_url(image_src, tab.url)
    assert tab.allowed_request(image_url), \
        "Blocked load of " + image_url + " due to CSP"
    header, body = request(image_url, tab.url)
    data = skia.Data.MakeWithoutCopy(body)
    img = skia.Image.MakeFromEncoded(data)
    assert img, "Failed to recognize image format for " + image_url
    return body, img
```

Let's look at the steps between `request` and `return` carefully.
First, the requested data is turned into a Skia `Data` object using
the `MakeWithoutCopy` method. Then that `Data` is used to create an
`Image` using `MakeFromEncoded`.

`MakeWithoutCopy` means that the `Data` object just stores a reference
to the existing `body` and doesn't own that data. That's essential,
because encoded image data can be large---maybe megabytes---and
copying that data wastes memory and time. But that means that the
`data` is invalid if `body` is ever garbage-collected, so we return
the `body` from `download_image` and need to make sure to store it
somewhere for at least as long as we're using the image.[^memoryview]

[^memoryview]: This is a bit of a hack. Perhaps a better solution
    would be to write the request contents directly into a Skia `Data`
    object; the `writable_data` API could permit that, but it would
    require some refactoring of the rest of the browser that I'm
    choosing to avoid.
    
Once that `Data` object is created, it is passed to `MakeFromEncoded`.
The name of this method hints that the image we've downloaded isn't
raw image bytes: all of the image formats you know---JPG, PNG, and the
many more obscure ones---encode the image data using various
sophisticated algorithms. The image therefore needs to be *decoded*
before it can be used. Luckily, Skia will automatically do that for
us, so drawing the image is pretty simple:

``` {.python replace=%2c%20rect/%2c%20rect%2c%20quality,self.rect)/self.rect%2c%20paint)}
class DrawImage(DisplayItem):
    def __init__(self, image, rect):
        super().__init__(rect)
        self.image = image

    def execute(self, canvas):
        canvas.drawImageRect(self.image, self.rect)
```

Skia applies a variety of clever optimizations to decoding, such as
directly decoding the image to its eventual size and caching the
decoded image as long as possible.[^html-image-decode] That's because
raw image data can be quite large:[^time-memory] a pixel is usually
stored as four bytes, so a 12 megapixel camera (as you can find on
phones these days) produces 48 megabytes of raw data.

[^time-memory]: Decoding costs both a lot of memory and also a lot of
    time, since just writing out all of those bytes can take a big
    chunk of our render budget. More generally, images are more
    expensive than text in a lot of ways. They take a long time to
    download; decoding is slow; resizing is slow; and they can take up
    a lot of both CPU and GPU memory. Optimizing image handling is
    essential to a performant browser.
    
[^html-image-decode]: There's also is an [HTML API][html-image-decode]
    to control decoding, so that the web page author can indicate when
    to pay the cost of decoding.

[html-image-decode]: https://developer.mozilla.org/en-US/docs/Web/API/HTMLImageElement/decoding

But because image decoding can be so expensive, Skia actually has
several algorithms for decoding, some of which result in a
worse-looking image but are faster than the default.[^lossy] For
example, just for resizing an image, there's fast, simple, "nearest
neighbor" resizing and the slower but higher-quality "bilinear" or
even "[Lanczos][lanczos]" resizing algorithm.

[lanczos]: https://en.wikipedia.org/wiki/Lanczos_resampling

To give web page authors control over this performance bottleneck, can
there's an [`image-rendering`][image-rendering] CSS property that
indicates which algorithm to use. Let's add that as an argument to
`DrawImage`:

[image-rendering]: https://developer.mozilla.org/en-US/docs/Web/CSS/image-rendering

``` {.python}
class DrawImage(DisplayItem):
    def __init__(self, image, rect, quality):
        # ...
        if quality == "high-quality":
            self.quality = skia.FilterQuality.kHigh_FilterQuality
        elif quality == "crisp-edges":
            self.quality = skia.FilterQuality.kLow_FilterQuality
        else:
            self.quality = skia.FilterQuality.kMedium_FilterQuality

    def execute(self, canvas):
        paint = skia.Paint(FilterQuality=self.quality)
        canvas.drawImageRect(self.image, self.rect, paint)
```

So we've now got the helper functions we need to downloading and
decoding images. But to actually put images into web pages, we're
going to need to add images into our browser's layout tree.

[^lossy]: Image formats like JPEG are [*lossy*][lossy], meaning that
    they don't faithfully represent all of the information in the
    original picture, so there's a time/quality trade-off going on
    before the file is saved. Typically these formats try to drop
    "noisy details" that a human is unlikely to notice; different
    decoding algorithms are making the same trade-off.

[lossy]: https://en.wikipedia.org/wiki/Lossy_compression

::: {.further}
The HTTP `Content-Type` header lets the web server tell the browser
whether a document contains text or binary data. The header contains a
value called a [MIME type][mime-type]: `text/html`, `text/css`, and
`text/javascript` for HTML, CSS, and JavaScript; `image/png` and
`image/jpeg` for PNG and JPEG images; and [many others][mime-list] for
different font, video, audio, and data formats.[^mime-history]
Interestingly, when we used Skia's `MakeFromEncoded`, we didn't need
to pass in the image format. That's because many image formats start
with ["magic bytes"][magic-bytes]; for example, PNG files always start
with byte 137 followed by the letters "PNG". These magic bytes are
often more reliable than server-send MIME types, so this kind of
"format sniffing" is common inside browsers and their supporting
libraries.
:::

[mime-type]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types

[^mime-history]: "MIME" stands for Multipurpose Internet Mail
Extensions, and was originally intended for enumerating all of the
acceptable data formats for email attachments. These days the loop has
basically closed: most email clients are now "webmail" clients,
accessed through your browser, and most emails are now HTML, encoded
with the `text/html` MIME type. Many mail clients do still have an
option to encode the email in `text/plain`, however.

[mime-list]: https://www.iana.org/assignments/media-types/media-types.xhtml

[magic-bytes]: https://www.netspi.com/blog/technical/web-application-penetration-testing/magic-bytes-identifying-common-file-formats-at-a-glance/

Embedded layout
===============

An `<img>` is a leaf element of the DOM. In some ways, it's similar to a single
font glyph that has to paint in a single rectangle sized to the image (instead
of the glyph), takes up space in a `LineLayout`, and causes line breaking when
it reaches the end of the available space.

But it's different than a text *node*, because the text in a text node is not
just one glyph, but an entire run of text of a potentially arbitrary length,
and that can be split into words and lines across multiple lines. An image, on
the other hand, is an [atomic inline][atomic-inline]---it doesn't make sense to
split it across multiple lines.^[There are other elements that can be atomic
inlines, and we'll encounter more later in this chapter.]


[atomic-inline]: https://drafts.csswg.org/css-display-3/#atomic-inline

Images will be laid out by a new `ImageLayout` class. The height and width of
the object is defined by the height of the image, but other aspects of it will be almost
the same as `InputLayout`. In fact, so similar that
let's make them inherit from a new `EmbedLayout` base class to share a lot of
code about inline layout and fonts. (And for completeness, make a new
`LayoutObject` root class for all types of object, and make `BlockLayout`,
`InlineLayout` and `DocumentLayout` inherit from it.

``` {.python}
class LayoutObject:
    def __init__(self):
        pass
```

``` {.python}
class EmbedLayout(LayoutObject):
    def __init__(self, node, parent=None, previous=None):
        super().__init__()
        self.node = node
        node.layout_object = self
        self.children = []
        self.parent = parent
        self.previous = previous
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.font = None

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

        if self.previous:
            space = self.previous.font.measureText(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x
```

Now `InputLayout` looks like this:

``` {.python}
class InputLayout(EmbedLayout):
    def __init__(self, node, parent, previous):
        super().__init__(node, parent, previous)

    def layout(self, zoom):
        super().layout(zoom)

        self.width = device_px(INPUT_WIDTH_PX, zoom)
        self.height = linespace(self.font)
```

And `ImageLayout` is almost the same. The two key differences
are the need to actually load the image off the network, and then use
the size of the image to size the `ImageLayout`. Let's start with loading.
After loading, the image is stored on the `node`. But this adds some complexity
in the `image` function we need to add on `InlineLayout`, because first it needs
to load the image and only then set its `parent` and `previous` fields. That'll
be via a new `init` method call.

``` {.python}
class InlineLayout(LayoutObject):
    def recurse(self, node, zoom):
            # ...
            elif node.tag == "img":
                self.image(node, zoom)
    
    def image(self, node, zoom):
        img = ImageLayout(node, self.frame)
        w = device_px(node.image.width(), zoom)
        if self.cursor_x + w > self.x + self.width:
            self.new_line()
        line = self.children[-1]
        img.init(line, self.previous_word)
        line.children.append(img)
        self.previous_word = img
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        size = device_px(float(node.style["font-size"][:-2]), zoom)
        font = get_font(size, weight, size)
        self.cursor_x += w + font.measureText(" ")
```

And here is `ImageLayout`. Note how we're loading the image, but not
yet decoding it, because we don't know the painted size until layout is done.

``` {.python}
class ImageLayout(EmbedLayout):
    def __init__(self, node, frame):
        super().__init__(node)
        if not hasattr(self.node, "image"):
            self.load(frame)

    def load(self, frame):
        assert "src" in self.node.attributes
        link = self.node.attributes["src"]
        try:
            data, image = download_image(link, frame)
        except Exception as e:
            print("Image error:", e)
            data, image = None, None
        self.node.encoded_data = data
        self.node.image = image

    def init(self, parent, previous):
        self.parent = parent
        self.previous = previous
    # ...
```

Note that we save both the encoded data and the image, because of the
`MakeWithoutCopy` optimizaion we used in `download_image`

Then there is layout, which shares all the code except sizing:

``` {.python expected=False}
class ImageLayout(EmbedLayout):
    def layout(self, zoom):
        super().layout(zoom)
        self.width = device_px(self.node.image.width(), zoom)
        self.img_height = device_px(self.node.image.height(), zoom)
        self.height = max(self.img_height, linespace(self.font))
```

Notice how the positioning of an image depends on the font size of the element,
via the call to the the layout method of `EmbedLayout` in the superclass. Input
elements already had that, but those elements generally have text in them, but
images do not. That means that a "line" consisting of only an image still has
has an implicit font affecting its layout somehow.^[In fact, a page with only a
single image and no text or CSS at all still has a font size (the default font
size of a web page), and the image's layout depends on it. This is a very
common source of confusion for web developers. In a real browser, it can be
avoided by forcing an image into a block or other layout mode via the `display`
CSS property.]

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
defined by HTML tags and CSS in our toy browser. That's why I called the
superclass `EmbedLayout`.^[The details are complicated
in a real browser, but input elements are usually called *widgets* instead,
and have a lot of
[special rendering rules][widget-rendering] that sometimes involve CSS.]

The web specifications call images
[*replaced elements*][replaced-elements]---characterized by putting stuff
"outside of HTML" into an inline HTML context, and "replacing" what HTML might
have drawn. In real browsers, input elements are some sort of hybrid between
a replaced element and a regular element.

[widget-rendering]: https://html.spec.whatwg.org/multipage/rendering.html#widgets

[replaced-elements]: https://developer.mozilla.org/en-US/docs/Web/CSS/Replaced_element

Painting an image is quite straightforward:

``` {.python}
class ImageLayout(EmbedLayout):
    def paint(self, display_list):
        cmds = []
        rect = skia.Rect.MakeLTRB(
            self.x, self.y + self.height - self.img_height,
            self.x + self.width, self.y + self.height)
        quality = self.node.style.get("image-rendering", "auto")
        cmds.append(DrawImage(self.node.image, rect, quality))
        display_list.extend(cmds)
```

::: {.further}
The `<img>` tag uses a `src` attribute and not `href`. Why is that? And
why is the tag name `img` and not `image`? The answer to the first is
apparently that an image is not a "hypertext reference" (which
is what `href` stands for), but instead a page sub-resource. However,
sub-resources actually have inconsistent naming. For example, the `<link>`
tag can refer to a style sheet with `href`, but the `<script>` tag
uses `src`. The true reason may simply be [design disagreements][srcname]
before such things were mediated by a standards organization.
:::

[srcname]: http://1997.webhistory.org/www.lists/www-talk.1993q1/0196.html

Images should now work and display on the page. But our implementation is very
basic and actually has no way for the image's painted size to differ from its
decoded size. There are of course several ways for a web page to change an
image's rendered size.^[For example, the `width` and `height` CSS properties
(not to be confused with the `width` and `height` attributes!), which were an
exercise in Chapter 13.] But images *also* have, mostly for historical reasons
(because these attributes were invented before CSS existed), special `width`
and `height` attributes that override the intrinsic size. Let's implement
those.

It's pretty easy: every place we deduce the width or height of an image layout
object from its intrinsic size, first consult the corresponding attribute and
use it instead if present. Let's start with `image` on `InlineLayout`. The width
and height attributes are in CSS pixels without unit suffixes, so parsing is
easy, and we need to multiply by zoom to get device pixels:

``` {.python}
class InlineLayout(LayoutObject):
    # ...
    def image(self, node, zoom):
        if "width" in node.attributes:
            w = device_px(int(node.attributes["width"]), zoom)
        else:
            w = device_px(node.image.width(), zoom)
```

And in `ImageLayout`:

``` {.python expected=False}
class ImageLayout(EmbedLayout):
    # ...
    def layout(self, zoom):
        # ...
        if "width" in self.node.attributes:
            self.width = \
            device_px(int(self.node.attributes["width"]), zoom)
        else:
            # ...

        if "height" in self.node.attributes:
            self.img_height = \
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
new width and heights. One way to represent scale is to infer it if the web
page happens only to specify only one of the `width` or `height`.

Implementing this change is very easy:[^only-recently-aspect-ratio] it's
just a few lines of edited code in `ImageLayout` to apply the aspect
ratio when only one attribute is specified.

[^only-recently-aspect-ratio]: Despite it being easy to implement, this
feature of real web browsers only appeared in 2021. Before that, developers
resorted to things like the [padding-top hack][padding-top-hack]. Sometimes
design oversights take a long time to fix.

[padding-top-hack]: https://web.dev/aspect-ratio/#the-old-hack-maintaining-aspect-ratio-with-padding-top

``` {.python}
class ImageLayout(EmbedLayout):
    # ...
    def layout(self, zoom):
        # ...
        aspect_ratio = self.node.image.width() / self.node.image.height()
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
            self.img_height = (1 / aspect_ratio) * \
                device_px(int(self.node.attributes["width"]), zoom)
        else:
            # ...
```

Images are now present in our browser, with several nice features to control
their layout and quality. Your browser should now be able to render
<a href="/examples/example15-img.html">this
example page</a> correctly.

But what about accessibility? A screen reader can read out text, but how
does it describe an image in words? That's what the `alt` attribute is for.
It works like this:

    <img src="https://browser.engineering/im/hes.jpg"
    alt="A computer operator using a hypertext editing system in 1969">

Implementing this in `AccessibilityNode` is very easy:

``` {.python}
class AccessibilityNode:
    def __init__(self, node):
            # ...
            elif node.tag == "img":
                self.role = "image"

    def build(self):
        elif self.role == "image":
            if "alt" in self.node.attributes:
                self.text = "Image: " + self.node.attributes["alt"]
            else:
                self.text = "Image"
```

However, since alt text is generally a phrase or sentence, and those contain
whitespace, `HTMLParser`'s attribute parsing is not good enough (it can't
handle quoted whitespace in attribute values). It'll need to look a
lot more like how `CSSParser` statefully handles whitespace and quoting. I
won't include the code here since the concept for how to parse it is the same.

::: {.further}
I discussed preserving aspect ratio for a loaded image, but what about before
it loads? In our toy browser, images are loaded synchronously during `load`,
but real browsers don't do that because it would slow down page load
accordingly. So what should a browser render if the image hasn't loaded?
It doesn't have the image intrinsic sizing, so it has to use other available
information such as `width` and `height` to size it (and also style it---see
the corresponding exercise at the end of the chapter).

This is another reason why the inferred aspect ratio feature I implemented in
this section is important, because in cases where the size of an image depends
on [responsive design][resp-design] parameters, it's important to preserve the
aspect ratio accordingly. Otherwise the page layout will look bad and cause
[layout shift][cls] when the image loads.
:::

[resp-design]: https://developer.\mozilla.org/en-US/docs/Learn/CSS/CSS_layout/Responsive_Design
[cls]: https://web.dev/cls/

Interactive widgets
===================

So far, our browser has two kinds of embedded content: images and
input elements. While both are important and widely-used,[^variants]
they don't offer quite the customizability and flexibility[^openui]
that more complex embedded content---like maps, PDFs, ads, and social
media controls---requires. In modern browsers, these are handled by
*embedding one web page within another* using the `<iframe>` element.

[^variants]: As are variations like the [`<canvas>`][canvas-elt]
    element. Instead of loading an image from the network, JavaScript
    can draw on a `<canvas>` element via an API. Unlike images,
    `<canvas>` element's don't have intrinsic sizes, but besides that
    they are pretty similar.

[canvas-elt]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/canvas
    
[^openui]: There's actually [ongoing work](https://open-ui.org/) aimed at
    allowing web pages to customize what input elements look like, and it
    builds on earlier work supporting [custom elements][shadow-dom] and
    [forms][form-el]. This problem is quite challenging, interacting with
    platform independence, accessibility, scripting, and styling.

[shadow-dom]: https://developer.mozilla.org/en-US/docs/Web/Web_Components/Using_shadow_DOM
[form-el]: https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/attachInternals

The `<iframe>` tag's layout is a lot like the `<img>` tag: it has the `src`
attribute and `width` and `height` attributes. And an iframe is almost exactly
the same as a `Tab` within a `Tab`---it has its own HTML document, CSS, and
scripts. There are three significant differences though:

* *Iframes have no browser chrome*. So any page navigation has to happen from
   within the page (either through an `<a>` element or script), or as a side
   effect of navigation on the web page that *contains* the `<iframe>`
   element.

* *Iframes do not necessarily have their own rendering event
loop.* [^iframe-event-loop] In real browsers, [cross-origin] iframes are often
"site isolated", meaning that the iframe has its own CPU process for
[security reasons][site-isolation]. In our toy browser we'll just make all
iframes (even nested ones---yes, iframes can include iframes!) use the same
rendering event loop.

* *Cross-origin iframes are *script-isolated *from their containing web page.*
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
`Tab` has a tree of objects---*frames* containing HTML documents---nested
within each other. Each node in this tree will be an object from a new `Frame`
class. We'll use one rendering event loop for all `Frame`s.

In terms of code, basically, we'll want to refactor `Tab` so that it's a
container for a new `Frame` class. The `Frame` will implement the rendering
work that the `Tab` used to do, and the `Tab` becomes a coordination and
container class for the frame tree. More specifically, the `Tab` class will:

* Kick off animation frames and rendering.
* Paint and own the display list for all frames in the tab.
* Implement accessibility.
* Provide glue code between `Browser` and the documents to implement event
  handling.
* Proxy communication between frame documents.
* Commit to the browser thread.

And the `Frame` class will:

* Own the DOM, layout trees, and scroll offset for its HTML document.
* Own a `JSContext` if it is cross-origin to its parent.
* Run style and layout on the its DOM and layout tree.
* Implement loading and event handling (focus, hit testing, etc) for its HTML
  document.

A `Frame` will also recurse into child `Frame`s for additional painting,
accessibility and hit testing. 

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

The `Frame` class has all of the rest of loading and event handling that used to
be in `Tab`. I won't go into those details right now,  except the part where a
`Frame` can load sub-frames via the `<iframe>` tag. In the code below, we
collect all of the `<iframe>` elements in the DOM, load them, create a new
`Frame` object, store it on the iframe element, and call `load` recursively.
Note that all the code in the "..." below is the same as what used to be on
`Tab`'s `load` method.

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
For quite a while, browsers also supported another kind of embedded
content: plugins. Some provided a programming language and mechanism
for interactive UI, such as [Java applets][java-applets] or
[Flash];^[YouTube originally used Flash for videos, for example.]
others provided support for new content types like [PDF]. But plugins
suffer from accessibility, integration, and performance issues,
because they must implement a separate rendering, sandboxing, and
execution system, duplicating all of the browser's own subsystems.
Improving the browser to allow richer UI, by contrast, benefits all
pages, not just those using a particular plugin.[^extensible-web]

These days, plugins are less common---which I personally think is a
good thing. The web is about making information accessible to
everyone, and that requires open standards, including for embedded
content. That means open formats and codecs for images and videos, but
also open source plugins. Today, PDF is [standardized][pdf-standard],
but for most of their history as plugins, these formats were closed off.

[java-applets]: https://en.wikipedia.org/wiki/Java_applet
[Flash]: https://en.wikipedia.org/wiki/Adobe_Flash
[PDF]: https://developer.mozilla.org/en-US/docs/Learn/HTML/Multimedia_and_embedding/Other_embedding_technologies#the_embed_and_object_elements
[pdf-standard]: https://www.iso.org/standard/51502.html

[^extensible-web]: In other words, over time APIs have been added that close
the gap between the use cases supported by iframes and "non-web" plugin
systems like Flash. For example, in the last decade the `<canvas>` element
(which can of course be placed within an iframe) supports hardware-accelerated
3D content, and [near-native-speed][webassembly] code.

[webassembly]: https://en.wikipedia.org/wiki/WebAssembly

:::

::: {.further}
Images can also be animated.[^animated-gif] So if a website can load an image,
and the image can be animated, then that image is something very close to
a *video*. But in practice, videos need very advanced encoding and encoding
formats to minimize network and CPU costs, *and* these formats incur a lot of
other complications, chief among them [Digital Rights Management (DRM)][drm]. To
support all this, the `<video>` tag supported by real browsers provides
built-in support for several common video [*codecs*][codec] with DRM and
hardware acceleration.^[In video, it's called a codec, but in images it's
called a *format*--go figure.] And on top of all this, videos need built-in
*media controls*, such as play and pause buttons, and volume controls.

[^animated-gif]: See the exercise for animated images at the end of this
chapter.

[drm]: https://en.wikipedia.org/wiki/Digital_rights_management
[codec]: https://en.wikipedia.org/wiki/Video_codec

Perhaps the most common use case for embedded content other than images and
video is ads. Inline ads have been around since the beginning
of the web, and are often (for good reasons or bad depending on your
perspective) big users of third-party embedding and whatever
animation/attention-drawing features the web has.

From a browser engineering perspective, ads are also a very challenging source
of performance and [user experience][ux] problems. For example, ads often load
a lot of data, run a lot of code to measure various kinds of
[analytics]---such as "was this ad viewed by the user and for how long?"---and
are delay-loaded (similar to an async-loaded image) and so cause layout shift.

A lot of browser engineering has gone into ways to improve or mitigate these
problems---everything from ad blocker [browser extensions][extensions] to APIs
such as [Intersection Observer][io] that make analytics computation more
efficient.
:::

[ux]: https://en.wikipedia.org/wiki/User_experience
[analytics]: https://en.wikipedia.org/wiki/Web_analytics
[extensions]: https://en.wikipedia.org/wiki/Browser_extension
[io]: https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API


Iframe rendering
================

A `Tab` will delegate style and layout to each frame, and each frame will
maintain its own dirty bits. Accessibility and paint will still be done at the
`Tab` level, because the output of each of them is a combined result across
all frames---a single display list, and a single accessibility tree. So that
code doesn't change.

``` {.python}
class Tab:
    def render(self):
        self.measure_render.start()

        for frame in self.window_id_to_frame.values():
            frame.render()

        if self.needs_accessibility:
            # ...

        if self.pending_hover:
            # ...
```

Style and layout dirty bits are stored on `Frame` and control that part of
rendering:

``` {.python}
class Frame:
    def __init__(self, tab, parent_frame, frame_element):
        self.tab = tab
        self.parent_frame = parent_frame
        self.frame_element = frame_element
        self.needs_style = False
        self.needs_layout = False

    def set_needs_render(self):
        self.needs_style = True
        self.tab.set_needs_accessibility()
        self.tab.set_needs_paint()

    def set_needs_layout(self):
        self.needs_layout = True
        self.tab.set_needs_accessibility()
        self.tab.set_needs_paint()

    def render(self):
        if self.needs_style:
            # ...

        if self.needs_layout:
            # ...
```

Now for `<iframe>` layout. Let's start with the biggest layout difference
between iframes and images: unlike images, *an `<iframe>` element has no
intrinsic size*. So its layout is defined entirely by the attributes and CSS of
the `iframe` element, and not at all by the content of the iframe.
[^seamless-iframe]

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

Iframe layout in `InlineLayout` is a lot like images. The only difference
is the width calculation, so I've omitted the rest with "..."
instead. I've added 2 to the width and height in these calculations to provide
room for the painted border to come.

``` {.python}
class InlineLayout(LayoutObject):
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
            w = IFRAME_DEFAULT_WIDTH_PX + 2
        # ...
```

And the `IframeLayout` layout code is also similar, and also inherits from
`EmbedLayout`. (Note however that there is no code regarding
aspect ratio, because iframes don't have an intrinsic size.)

``` {.python}
class IframeLayout(EmbedLayout):
    def __init__(self, node, parent, previous, parent_frame):
        super().__init__(node, parent, previous)

    def layout(self, zoom):
        # ...
        if has_width:
            self.width = \
                device_px(int(self.node.attributes["width"]), zoom)
        else:
            self.width = device_px(
                IFRAME_DEFAULT_WIDTH_PX + 2, zoom)

        if has_height:
            self.height = \
                device_px(int(self.node.attributes["height"]), zoom)
        else:
            self.height = device_px(
                IFRAME_DEFAULT_HEIGHT_PX + 2, zoom)
```

Each `Frame` will also needs its width and height, as an input to layout:

``` {.python}
class Frame:
    def __init__(self, tab, parent_frame, frame_element):
        self.frame_width = 0
        self.frame_height = 0
```

And set here:

``` {.python}
class IframeLayout(EmbedLayout):
    def layout(self, zoom):
        # ...
        self.node.frame.frame_height = self.height - 2
        self.node.frame.frame_width = self.width - 2
```

The root frame is sized to the window:

``` {.python}
class Tab:
    def load(self, url, body=None):
        # ...
        self.root_frame.frame_width = WIDTH
        self.root_frame.frame_height = HEIGHT - CHROME_PX
```

As for painting, iframes by default have a border around their content when
painted.^[Which, again, is why I added 2 to the width and height. It's
also why I added 1 to the `Transform`  in `paint`. This book
doesn't go into the details of the [CSS box model][box-model], but the `width`
and `height` attributes of an iframe refer to the *content box*, and adding 2
yields the *border box*.] They also clip the iframe painted content to the
bounds of the `<iframe>` element.

[box-model]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Box_Model/Introduction_to_the_CSS_box_model

``` {.python expected=False}
class IframeLayout(EmbedLayout):
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

        cmds = [Transform(
            (self.x + 1 , self.y + 1), rect, self.node, cmds)]

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

Iframe input events
===================

Rendering now functions properly in iframes, but user input does not:
it's not (yet) possible to click on a element in an iframe in our toy browser,
iterate through its focusable elements, scroll it, or generate an accessibility
tree.

Let's fix that. But all this code in `click` is getting a little unwieldy, so
first some refactoring. We'll push object-type-specific behavior down into the
various `LayoutObject` subclasses, via a new `dispatch` method that does any
special behavior and then returns `True` if the element tree walk should
stop.^[In our toy browser, we never implemented [event bubbling][bubbling]. So
all we're trying to do is walk up the tree until an element with special
behavior is found. To see how bubbling affects this code, try the related
exercise in chapter 9.]

[bubbling]: https://developer.mozilla.org/en-US/docs/Learn/JavaScript/Building_blocks/Events#event_bubbling

The existing `click` method will now simply walk up the element tree until
`dispatch` returns true:

``` {.python}
class Frame:
    def click(self, x, y):
        # ...
        while elt:
            if elt.layout_object and elt.layout_object.dispatch(x, y):
                return
            elt = elt.parent

```

By default, the tree walk is not stopped:

``` {.python}
class LayoutObject:
    def dispatch(self, x, y):
        return False
```

For an inline element it stops if focusable:

``` {.python}
class InlineLayout(LayoutObject):
   def dispatch(self, x, y):
        if isinstance(self.node, Element) and is_focusable(self.node):
            self.frame.focus_element(self.node)
            self.frame.activate_element(self.node)
            self.frame.set_needs_render()
            return True
        return False
```

While for inputs, they are always focusable:

``` {.python}
class InputLayout(EmbedLayout):
   def dispatch(self, x, y):
        self.frame.focus_element(self.node)
        self.frame.activate_element(self.node)
        self.frame.set_needs_render()
        return True
```

And now we're ready to implement `dispatch` for iframe elements. In this
case, we should re-target the click to the iframe, after adjusting for its local
coordinate space, and then stop the tree walk:


``` {.python}
class IframeLayout(EmbedLayout):
    def dispatch(self, x, y):
        self.node.frame.click(x - self.x, y - self.y)
        return True
```

Now that clicking works, clicking on `<a>` elements will work. Which means
that you can now cause a frame to navigate to a new page. And because a
`Frame` has all the loading and navigation logic that `Tab` used to have, it
just works without any more changes! That's satisfying.

Focusing an element now also needs to store the frame the focused element is
on (the `focus` value will still be stored on the `Tab`, not the `Frame`,
though, since there is only one focus at a time in the tab):

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
        self.set_needs_render()
```

Advancing a tab will use the focused frame (and you should move the rest of the
business logic for `advance_tab` to `Frame`):

``` {.python}
class Tab:
    def advance_tab(self):
        frame = self.focused_frame
        if not frame:
            frame = self.root_frame
        frame.advance_tab()
```

Now for scrolling. This will require moving scrolling onto `Frame` instead of
`Browser` or `Tab`.

``` {.python}
class Frame:
    def __init__(self, tab, parent_frame, frame_element):
        self.scroll = 0
```

Clamping will now happen differently, because non-root frames have a height
that is not defined by the size of the browser window, but rather their
containing `<iframe>` element.

We'll use this to do clamping based on this height:

``` {.python}
class Frame:
    def clamp_scroll(self, scroll):
        return max(0, min(
            scroll,
            math.ceil(
                self.document.height) - self.frame_height))
```

Now change all call sites of `clamp_scroll` to use the method rather than the
global function:

``` {.python}
class Frame:
    def scroll_to(self, elt):
        # ...
        self.scroll = self.clamp_scroll(new_scroll)
```

``` {.python}
class Frame:
    def layout(self, zoom):
        self.document = DocumentLayout(self.nodes, self)
        self.document.layout(zoom, self.frame_width)

        clamped_scroll = self.clamp_scroll(self.scroll)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_frame = True
```

Our browser supports browser-thread scrolling, but only for the root frame.
To handle both cases, we'll need a new commit parameter:

``` {.python}
class CommitData:
    def __init__(self, url, scroll, root_frame_focused, height,
        display_list, composited_updates, accessibility_tree, focus):
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
The part in "..." is what used to be in `handle_down`.

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
            self.child_tree = AccessibilityTree(self.node.frame)
            self.child_tree.build()
            return
        # ... 
```

But actually, accessibility still doesn't work for hover hit testing. That's for
two reasons:^[Observe that frame-based `click` already works correctly, because
we don't recurse into iframes unless the click intersects the `iframe`
element's bounds.]

* It doesn't properly take into account scroll of iframes. (In Chapter 14,
we did this just for the root frame.)

* It doesn't know how to apply clipping when hovering outside of an iframe's
bounds. (Before iframes, we didn't need to do that, because the SDL
window system already did it for us.)

Fixing these problems requires some re-jiggering of the accessibility hit testing
code to track scroll and iframe bounds, and applying them when recursing into
child frames. We'll make a new `AccessibilityTree` class and create one for
each frame and store on it the useful information:^[Real browsers such as
Chromium also do this, for similar reasons.]

``` {.python}
class AccessibilityTree:
    def __init__(self, frame):
        self.root_node = AccessibilityNode(frame.nodes)
        self.width = frame.frame_width
        self.height = frame.frame_height
        self.scroll = frame.scroll

    def build(self):
        self.root_node.build()
```

And `AccessibilityNode` will create subtrees:

``` {.python}
class AccessibilityNode:
    def __init__(self, node):
        # ...
        self.child_tree = None

    def build(self):
        if isinstance(self.node, Element) \
            and self.node.tag == "iframe":
            self.child_tree = AccessibilityTree(self.node.frame)
            self.child_tree.build()
            return

        # ...
```

Then we'll add a `to_list` method that does the same thing as `tree_to_list`
(including recursing into child frames), that is suitable for all call sites
of accessibility `tree_to_list` that are not hit testing:

``` {.python}
class AccessibilityTree:
    def to_list(self, list):
        return self.root_node.to_list(list)
```

``` {.python}
class AccessibilityNode:
    def to_list(self, list):
        list.append(self)
        if self.child_tree:
            self.child_tree.to_list(list)
            return list
        for child in self.children:
            child.to_list(list)
        return list
```

Update all of the callsites of `tree_to_list` to call `to_list`; there are
three in `update_accessibility` and one in `speak_document`.

Hit testing will first need to check for hover outside the bounds, then apply
scroll:

``` {.python}
class AccessibilityTree:
    def hit_test(self, x, y):
        if x > self.width or y > self.height:
            return None
        y += self.scroll
        nodes = []
        self.root_node.hit_test(x, y, nodes)
        if nodes:
            return nodes[-1]
```

And then ask the node tree to do its usual thing:

``` {.python}
class AccessibilityTree:
    def hit_test(self, x, y):
        # ...
        nodes = []
        self.root_node.hit_test(x, y, nodes)
        if nodes:
            return nodes[-1]
```

Except that `AccessibilityNode` will now have special code to recurse into
child trees:

``` {.python}
class AccessibilityNode:
    def hit_test(self, x, y, nodes):
        if self.intersects(x, y):
            nodes.append(self)
        if self.child_tree:
            child_node = self.child_tree.hit_test(
                x - self.bounds.x(), y - self.bounds.y())
            if child_node:
                nodes.append(child_node)
        for child in self.children:
            child.hit_test(x, y, nodes)
```

Finally, the call site needs to no longer adjust for scroll and just call
`hit_test`:

``` {.python}
class Browser:
    def paint_draw_list(self):
        # ...
        if self.pending_hover:
            (x, y) = self.pending_hover
            a11y_node = self.accessibility_tree.hit_test(x, y)
```

See how easy it is to add accessibility for iframes? That's a great reason
not to use a plugin.

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
containing blocks, stacking order, scrollbars, transforms and other visual
effects.
:::

[overflow-css]: https://developer.mozilla.org/en-US/docs/Web/CSS/overflow
[renderingng-scrolling]: https://developer.chrome.com/articles/renderingng/#threaded-scrolling-animations-and-decode

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

But that only works if we consider every frame *cross-origin* to all of the
others. That's not right, because two frames that have the same origin each get
a global namespace for their scripts, but they can access each other's frames
through, for example, the [`parent` attribute][window-parent] on their
`Window`.^[There are various other APIs; see the related exercise.] For
example, JavaScript in a same-origin child frame can access the `document`
object for the DOM of its parent frame like this:

    console.log(window.parent.document)

We need to implement that somehow. Unfortunately, DukPy doesn't natively support
the feature of
"evaluate this script under the given global variable". 

[window-parent]: https://developer.mozilla.org/en-US/docs/Web/API/Window/parent

Instead of switching to whole new JavaScript runtime, I'll just approximate the
feature with two tricks: overwriting the `window` object and the `with`
operator. The `with` operator is pretty obscure, but what it does is evaluate
the content of a block by looking up objects on the given object first, and
only after falling back to the global scope.^[It's important to reiterate that
this is a hack and doesn't actually do things correctly, but it suffices to
show the concept in our toy browser.] This example:

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
the `window` object and evaluates via `with`. 

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
`runtime.js` itself needs to be evaluated by `wrap_in_window`. And
`wrap_in_window` needs `Window` defined exactly once, not each time it's
called. The `Window` constructor stores its id, which will be useful later.

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
                self.get_js().run, script_url, body,
                self.window_id)
```

::: {.further}
There are proposals to add the concept of different global namespaces natively
to the JavaScript language. One current proposal is the
[ShadowRealm API](https://github.com/tc39/proposal-shadowrealm). This
API would have helped me implement this chapter, but it's aimed at various
use cases where code modularity or isolation (e.g. for injected testing code)
is desired.
:::

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
about `eval`, it does the same thing as the DukPy `evaljs` method.] And if the
eval throws a "variable not defined" exception, that means the window object is
not defined, which can only be the case if the parent is cross-origin to the
current window. In that case, return a fresh `Window` object with the fake id
`-1`.^[Which is also correct, because cross-origin frames can't access each
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

Next let's implement callback-based APIs, starting with `requestAnimationFrame`.
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
            for node in tree_to_list(frame.nodes, []):
                 #...
```

Event listeners are similar. Registering one is now stores a reference on the
window:

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

Dispatching the event requires `wrap_in_window`.^[All of the call sites of
`dispatch_event` (`click`, `submit_form`, and `keypress`) will need an additional
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
changes?] However, `innerHTML` can cause an iframe to be added to or removed
from the document. Our browser does not handle that correctly, and I've left
a solution for this problem to an exercise.

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
mean they can't communicate. Instead of direct access, they use
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
"message" event.

    window.addEventListener("message", function(e) {
        console.log(e.data);
    });


Note that in this case `window` is *not* the same object! It's the `Window`
object for some other frame (e.g. the parent frame in the example above).

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
structured cloning natively.] In the JavaScript runtime, we'll need a new
`WINDOW_LISTENERS` array to keep track of event listeners for messages (the old
`LISTENERS` was only for events on `Node` objects).

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
`Tab`. Why schedule a task instead of sending the messages synchronously, you
might ask? It's because `postMessage` is an *async* API that expressly does
not allow synchronous bi-directional (or uni-directional, for that matter)
communication. Asynchrony, callbacks and message-passing are inherent
features of the JavaScript+event loop programming model.

In any event, here is `postMessage`:

``` {.python}
class JSContext:
    def postMessage(self, target_window_id, message, origin):
        task = Task(self.tab.post_message, message, target_window_id)
        self.tab.task_runner.schedule_task(task)
```

Which then runs this code, which finds the frame for the given window id and
dispatches an event on it:

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

::: {.further}
Message-passing between event loops is by no means a JavaScript invention. Other
languages, going back to [SmallTalk][smalltalk] or even earlier, have used this
model of computing for many years. And more recently, even systems languages
like [Rust][rust] have message-passing as a core language feature.
:::

[smalltalk]: https://en.wikipedia.org/wiki/Smalltalk
[rust]: https://en.wikipedia.org/wiki/Rust_(programming_language)


Iframe security
===============

I've already discussed security in Chapter 10, but iframes cause new classes of
serious security problems that are worth briefly covering here. However, there
isn't anything new to implement in our browser for this section, so consider it
optional reading.

Iframes are very powerful, because they allow a web page to embed another one.
But with that power comes a commensurate security risk in cases where the
embedded web page is cross-origin to the main page. After all, it's literally a
web page controlled by someone else that renders into the same tab as yours.
And since it's unlikely that you really trust that other web page, you want to
be protected from any security or privacy risks that page may represent.

The fact that cross-origin iframes can't access their parents directly already
provides a reasonable starting point. But it doesn't protect you if a
browser bug allows JavaScript in an iframe to cause a
[buffer overrun][buffer-overrun], which an attacker exploits to run
arbitrary code. To protect against such a situation, browsers these days
load web pages in a security [*sandbox*][sandbox], which prevents arbitrary
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
 still are, such as [SharedArrayBuffer].^[Check out
 [this explanation][sab-attack] if you want to learn more.] Since this API
 is still useful, and there is no good way to make it "less accurate", browsers
 now require [certain optional HTTP headers][sab-headers] to be present on the
 parent *and* child frames' HTTP responses in order to allow use of
 `SharedArrayBuffer`.

[SharedArrayBuffer]: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer

[sab-attack]: https://security.stackexchange.com/questions/177033/how-can-sharedarraybuffer-be-used-for-timing-attacks

[sab-headers]: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer#security_requirements


::: {.further}
The required headers for `SharedArrayBuffer` also caused problems for
the *Web Browser Engineering* website, when I [added JavaScript support][js-blog]
to embedded widgets. These widgets use `SharedArrayBuffer` to polyfill the way
that runtime JavaScript APIs talk to the browser. It worked, but in order
to make it an embedded widget required setting the opt-in headers for that API.
Unfortunately, doing so broke an embedded YouTube video in Chapter 14,
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

* Embedded content is a way to allow (potentially non-HTML) content---images,
  video, canvas, iframes, input elements or plugins---to be added to a web
  page.

* Images are relatively easy to add as long as you have a good decoding library
  at hand, but need some care for layout and decoding optimizations.

* Over time, plugins that are not PDF viewers, images or video have been
  replaced with the more general-purpose *iframe* element, which has evolved to
  become just as powerful as any plugin, and benefits from all the hard-won
  attributes of a browser such as its rendering pipeline, accessibility, and
  open standards.

* Because iframes contain an entire web page and all its
  complexities---rendering, event handling, navigation, security---as well as
  the ability to embed other iframes, they add quite a lot of complexity to a
  browser implementation. However, this complexity is justified, because they
  enable many important cross-origin use cases, such as ads, video, and social
  media references, to be safely added to websites.

* On the whole, images, canvases,^[Try the exercise about the `<canvas>` element
  to see for yourself! Video was not really covered at all in this chapter;
  depending on what you consider "basic", implementing them could be relatively
  simple or quite hard.] and even iframes, are not *that* hard to implement in
  a very basic form, because they reuse a lot of the code and concepts I've
  explained in earlier chapters. But implementing them really well---as with
  all good things in this life---takes a lot of effort and attention to
  detail.

Exercises
=========

*Canvas element*: Implement the [`<canvas>`][canvas-elt] element, the 2D aspect
of the [`getContext`][getcontext] API, and some of the drawing commands on
[`CanvasRenderingContext2D`][crc2d]. Canvas layout is just like an iframe,
including its default width and height. You should allocate a Skia canvas of
an appropriate size when `getContext("2d")` is called, and implement some of
the APIs that draw to the canvas.[^eager-canvas] It should be straightforward
to translate these to Skia methods.

[crc2d]: https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D

[^eager-canvas]: Note that once JavaScript draws to a canvas, the drawing
persists forever until [`reset`][canvas-reset] or similar is called. This
allows a web developer to build up a display list with a sequence of commands,
but also places the burden on them to decide when to do so, and also when to
clear it when needed. This approach is called an *immediate mode* of
rendering---as opposed to the [*retained mode*][retained-mode] used by HTML,
which does not have this complexity for developers. (Instead, the complexity
is borne by the browser.)

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
But some images, especially ones that are "below the fold":[^btf] they
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
some websites would break or look ugly. In the early days of the web,
computer networks were slow enough that browsers had a user setting to
disable downloading of images until the user expressly asked for them.]

[lli]: https://developer.mozilla.org/en-US/docs/Web/Performance/Lazy_loading

*Image placeholders*: Building on top of lazy loading, implement placeholder
styling of images that haven't loaded yet. This is typically done by putting
an icon representing an unloaded image in its place. If `width` or
`height` is not specified, the resulting size in that dimension should be sized
to fit the icon.

*Same-origin frame tree*: same-origin iframes can access each others' variables
 and DOM, even if they are not adjacent in the frame tree. Implement this.

*Iframe media queries*. Implement the [width][width-mq] media query.

[width-mq]: https://developer.mozilla.org/en-US/docs/Web/CSS/@media/width

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
the elements in a single frame. But this is bad for accessibility, because it
doesn't allow a user of the keyboard to obtain access to focusable elements in
other frames. Fix it to move between frames after iterating through all
focusable elements in one frame.

*Iframes under transforms*: painting an iframe that has a CSS `transform` on it
or an ancestor should already work, but event targeting for clicks doesn't work,
because `click` doesn't account for that transform. Fix this. Also check if
accessibility handles iframes under transform correctly in all cases.

*Iframes added or removed by script*: the `innerHTML` API can cause iframes
to be added or removed, but our browser doesn't load or unload them
when this happens. Fix this: new iframes should be loaded and old ones unloaded.
