---
title: Supporting Embedded Content
chapter: 15
prev: accessibility
next: invalidation
...

While our toy browser can render complex styles, visual effects, and
animations, all of those apply basically just to text. Yet web pages
contain a variety of non-text *embedded content*, from images to other
web pages. Support for embedded content has powerful implications for
browser architecture, performance, security, and open information
access, and has played a key role throughout the web's history.


Images
======

Images are certainly the most popular kind of embedded
content on the web,[^img-late] dating back to [early
1993][img-email].[^img-history] They're included on web pages via the
`<img>` tag, which looks like this:

    <img src="https://browser.engineering/im/hes.jpg">

[img-email]: http://1997.webhistory.org/www.lists/www-talk.1993q1/0182.html

[^img-late]: So it's a little ironic that images only make their
appearance in chapter 15 of this book! It's because Tkinter doesn't
support many image formats or proper sizing and clipping, so I had to
wait for the introduction of Skia.

[^img-history]: This history is also [the reason behind][srcname] a
    lot of inconsistencies, like `src` versus `href` or `img` versus
    `image`.

[srcname]: http://1997.webhistory.org/www.lists/www-talk.1993q1/0196.html

And which renders something like this:

<figure>
    <img src="/im/hes.jpg" alt="A computer operator using a hypertext editing system in 1969">
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
However, while all of the content we've downloaded so far---HTML, CSS,
and JavaScript---has been textual, images typically use binary data
formats. We'll need to extend `request` to support binary data.

The change is pretty minimal: instead of passing the `"r"` flag to
`makefile`, pass a `"b"` flag indicating binary mode:

``` {.python}
class URL:
    def request(self, top_level_url, payload=None):
        # ...
        response = s.makefile("b")
        # ...
```

Now every time we read from `response`, we will get `bytes` of binary
data, not a `str` with textual data, so we'll need to change some HTTP
parser code to explicitly `decode` the data:

``` {.python}
class URL:
    def request(self, top_level_url, payload=None):
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
        headers, body = url.request(self.url, body)
        body = body.decode("utf8")
        # ...
```

Make sure to make this change everywhere in your browser that you call
`request`, including inside `XMLHttpRequest_send` and in several other places
in `load`.

When we download images, however, we _won't_ call `decode`, and just
use the binary data directly.

``` {.python replace=Tab/Frame}
class Tab:
    def load(self, url, body=None):
        # ...
        images = [node
            for node in tree_to_list(self.nodes, [])
            if isinstance(node, Element)
            and node.tag == "img"]
        for img in images:
            src = img.attributes.get("src", "")
            image_url = url.resolve(src)
            assert self.allowed_request(image_url), \
                "Blocked load of " + image_url + " due to CSP"
            header, body = image_url.request(url)
```

Once we've downloaded the image, we need to turn it into a Skia
`Image` object. That requires the following code:

``` {.python replace=Tab/Frame}
class Tab:
    def load(self, url, body=None):
        for img in images:
            # ...
            img.encoded_data = body
            data = skia.Data.MakeWithoutCopy(body)
            img.image = skia.Image.MakeFromEncoded(data)
```

There are two tricky steps here: the requested data is turned into a
Skia `Data` object using the `MakeWithoutCopy` method, and then into
an image with `MakeFromEncoded`.

Because we used `MakeWithoutCopy`, the `Data` object just stores a
reference to the existing `body` and doesn't own that data. That's
essential, because encoded image data can be large---maybe
megabytes---and copying that data wastes memory and time. But that
also means that the `data` will become invalid if `body` is ever
garbage-collected; that's why I save the `body` in an `encoded_data`
field.[^memoryview]

[^memoryview]: This is a bit of a hack. Perhaps a better solution
    would be to write the response directly into a Skia `Data` object
    using the `writable_data` API. It would require some refactoring
    of the rest of the browser which is why I'm choosing to avoid it.
    
These download and decode steps can both fail; if that happens we'll
load a "broken image" placeholder (I used [this one][broken-image]):

[broken-image]: https://commons.wikimedia.org/wiki/File:Broken_Image.png

``` {.python replace=Tab/Frame}
BROKEN_IMAGE = skia.Image.open("Broken_Image.png")

class Tab:
    def load(self, url, body=None):
        for img in images:
            try:
                # ...
            except Exception as e:
                print("Exception loading image: url="
                    + str(image_url) + " exception=" + str(e))
                img.image = BROKEN_IMAGE
```

Now that we've downloaded and saved the image, we need to use it.
Recall that the `Image` object is created using a `MakeFromEncoded`
method. That name reminds us that the image we've downloaded isn't raw
image bytes. In fact, all of the image formats you know---JPG, PNG,
and the many more obscure ones---encode the image data using various
sophisticated algorithms. The image therefore needs to be *decoded*
before it can be used.

Luckily, Skia will automatically do the decoding for us, so drawing
the image is pretty simple:

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
    chunk of our render budget. Optimizing image handling is essential
    to a performant browser.
    
[^html-image-decode]: There's also is an [HTML API][html-image-decode]
    to control decoding, so that the web page author can indicate when
    to pay that cost.

[html-image-decode]: https://developer.mozilla.org/en-US/docs/Web/API/HTMLImageElement/decoding

But because image decoding can be so expensive, Skia actually has several
algorithms for decoding to different sizes, some of which are faster but result
in a worse-looking image.[^lossy] For example, just for resizing an image,
there's fast, simple, "nearest neighbor" resizing and the slower but
higher-quality "bilinear" or even "[Lanczos][lanczos]" resizing algorithms.

[^lossy]: Image formats like JPEG are also [*lossy*][lossy], meaning that
    they don't faithfully represent all of the information in the
    original picture, so there's a time/quality trade-off going on
    before the file is saved. Typically these formats try to drop
    "noisy details" that a human is unlikely to notice, just like
    different resizing algorithms might.

[lossy]: https://en.wikipedia.org/wiki/Lossy_compression

[lanczos]: https://en.wikipedia.org/wiki/Lanczos_resampling

To give web page authors control over this performance bottleneck,
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

With the images downloaded and decoded, all we need to see the
downloaded images is to add images into our browser's layout tree.

::: {.further}
The HTTP `Content-Type` header lets the web server tell the browser
whether a document contains text or binary data. The header contains a
value called a [MIME type][mime-type], such as `text/html`,
`text/css`, and `text/javascript` for HTML, CSS, and JavaScript;
`image/png` and `image/jpeg` for PNG and JPEG images; and [many
others][mime-list] for various font, video, audio, and data
formats.[^mime-history] Interestingly, we didn't need to the image
format in the code above. That's because many image formats start with
["magic bytes"][magic-bytes]; for example, PNG files always start with
byte 137 followed by the letters "PNG". These magic bytes are often
more reliable than web-server-provided MIME types, so such "format
sniffing" is common inside browsers and their supporting libraries.
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

Based on your experience with prior chapters, you can probably guess
how to add images to our browser's layout and paint process. We'll
need to create an `ImageLayout` method; add a new `image` case to
`BlockLayout`'s `recurse` method; and generate a `DrawImage` command
from `ImageLayout`'s `paint` method.

As we do this, you might recall doing something very similar for
`<input>` elements. In fact, text areas and buttons are very similar
to images: both are leaf nodes of the DOM, placed into lines, affected
by text baselines, and painting custom content.[^atomic-inline] Since
they are so similar, let's try to reuse the same code for both.

[^atomic-inline]: Images aren't quite like *text* because a text node is
potentially an entire run of text, split across multiple lines, while
an image is an [atomic inline][atomic-inline]. The other types of
embedded content in this chapter are also atomic inlines.

[atomic-inline]: https://drafts.csswg.org/css-display-3/#atomic-inline

Let's split the existing `InputLayout` into a superclass called
`EmbedLayout`, containing most of the existing code, and a new
subclass with the input-specific code, `InputLayout`:[^widgets]

[^widgets]: In a real browser, input elements are usually called
*widgets* because they have a lot of [special rendering
rules][widget-rendering] that sometimes involve CSS.

[widget-rendering]: https://html.spec.whatwg.org/multipage/rendering.html#widgets

``` {.python}
class EmbedLayout:
    def __init__(self, node, parent, previous, frame):
        # ...

    def get_ascent(self, font_multiplier=1.0):
        return -self.height

    def get_descent(self, font_multiplier=1.0):
        return 0

    def layout(self):
        self.zoom = self.parent.zoom
        self.font = font(self.node.style, self.zoom)
        if self.previous:
            space = self.previous.font.measureText(" ")
            self.x = \
                self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x
```

``` {.python replace=previous/previous%2c%20frame}
class InputLayout(EmbedLayout):
    def __init__(self, node, parent, previous):
        super().__init__(node, parent, previous)

    def layout(self):
        super().layout()
```

The idea is that `EmbedLayout` should provide common layout code for
all kinds of embedded content, while its subclasses like `InputLayout`
should provide the custom code for that type of content. Different
types of embedded content might have different widths and heights, so
that should happen in `InputLayout`, and each subclass has its own unique
definition of `paint`:

``` {.python}
class InputLayout(EmbedLayout):
    def layout(self):
        # ...
        self.width = device_px(INPUT_WIDTH_PX, self.zoom)
        self.height = linespace(self.font)

    def paint(self, display_list):
        # ...
```

`ImageLayout` can now inherit most of its behavior from `EmbedLayout`,
but take its width and height from the image itself:

``` {.python replace=previous/previous%2c%20frame,self.node.image.height()/image_height,self.node.image.width()/image_width}
class ImageLayout(EmbedLayout):
    def __init__(self, node, parent, previous):
        super().__init__(node, parent, previous)
    def layout(self):
        super().layout()
        self.width = device_px(self.node.image.width(), self.zoom)
        self.img_height = device_px(self.node.image.height(), self.zoom)
        self.height = max(self.img_height, linespace(self.font))
```

Notice that the height of the image depends on the font size of the
element. Though odd, this is how image layout actually works: a line
with a single, very small, image on it will still be tall enough to
contain text.^[In fact, a page with only a single image and no text or
CSS at all still has its layout affected by a font---the default font.
This is a common source of confusion for web developers. In a
real browser, it can be avoided by forcing an image into a block or
other layout mode via the `display` CSS property.] The underlying
reason for this is because, as a type of inline layout, images are
designed to flow along with related text, which means the
bottom of the image should line up with the [text baseline][baseline-ch3]
(in fact, `img_height` is saved in the code above to ensure they line up).

[baseline-ch3]: text.html#text-of-different-sizes

Painting an image is also straightforward:

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

Now we need to create `ImageLayout`s in `BlockLayout`. Input elements
are created in an `input` method, so we could duplicate it
calling it `image`...but `input` is itself a duplicate of `text`, so
this would be a lot of almost-identical methods. The only part of
these methods that differs is the part that computes the width of the
new inline child; most of the rest of the logic is shared.

Let's instead refactor the shared code into new methods which `text`,
`input`, and `input` can call. First, all of these methods need a font
to determine how big of a space[^actual] to leave after the inline;
let's make a function for that:

[^actual]: Yes, this is how real browsers do it too.

``` {.python}
def font(style, zoom):
    weight = style["font-weight"]
    variant = style["font-style"]
    size = float(style["font-size"][:-2])
    font_size = device_px(size, zoom)
    return get_font(font_size, weight, variant)
```

There's also shared code that handles line layout; let's put that into
a new `add_inline_child` method. We'll need parameters for the layout
class to instantiate and a `word` parameter that is only passed for some
layout classes.

``` {.python replace=child_class%2c/child_class%2c%20frame%2c,previous_word)/previous_word%2c%20frame)}
class BlockLayout:
    def add_inline_child(self, node, w, child_class, word=None):
        if self.cursor_x + w > self.x + self.width:
            self.new_line()
        line = self.children[-1]
        if word:
            child = child_class(node, line, self.previous_word, word)
        else:
            child = child_class(node, line, self.previous_word, frame)
        line.children.append(child)
        self.previous_word = child
        self.cursor_x += w + font(node.style, self.zoom).measureText(" ")
```

We can redefine `word` and `input` in a satisfying way now:

``` {.python replace=TextLayout/TextLayout%2c%20self.frame,InputLayout/InputLayout%2c%20self.frame}
class BlockLayout:
    def word(self, node, word):
        node_font = font(node.style, self.zoom)
        w = node_font.measureText(word)
        self.add_inline_child(node, w, TextLayout, word)

    def input(self, node):
        w = device_px(INPUT_WIDTH_PX, self.zoom)
        self.add_inline_child(node, w, InputLayout) 
```

Adding `image` is now also straightforward:

``` {.python replace=ImageLayout/ImageLayout%2c%20self.frame}
class BlockLayout:
    def recurse(self, node):
            # ...
            elif node.tag == "img":
                self.image(node)
    
    def image(self, node):
        w = device_px(node.image.width(), self.zoom)
        self.add_inline_child(node, w, ImageLayout)
```

Now that we have `ImageLayout` nodes in our layout tree, we'll be
painting `DrawImage` commands to our display list and showing the
image on the screen!

But what about our second output modality, screen readers? That's what
the `alt` attribute is for. It works like this:

    <img src="https://browser.engineering/im/hes.jpg"
    alt="A computer operator using a hypertext editing system in 1969">

Implementing this in `AccessibilityNode` is very easy:

``` {.python replace=node)/node%2C%20parent%20%3d%20None)}
class AccessibilityNode:
    def __init__(self, node):
        else:
            # ...
            elif node.tag == "img":
                self.role = "image"

    def build(self):
        # ...
        elif self.role == "image":
            if "alt" in self.node.attributes:
                self.text = "Image: " + self.node.attributes["alt"]
            else:
                self.text = "Image"
```

As we continue to implement new features for the web platform, we'll
always need to think about how to make features work in multiple
modalities.

::: {.further}
Videos are similar to images, but demand more bandwidth, time, and
memory; they also have complications like [Digital Rights Management
(DRM)][drm]. The `<video>` tag addresses some of that, with built-in
support for advanced video [*codecs*][codec],^[In video, it's called a
"codec", but in images it's called a "format"--go figure.] DRM, and
hardware acceleration. It also provides media controls like a
play/pause button and volume controls.
:::

[drm]: https://en.wikipedia.org/wiki/Digital_rights_management
[codec]: https://en.wikipedia.org/wiki/Video_codec


Modifying Image Sizes
=====================

So far, an image's size on the screen is its size in pixels, possibly
zoomed.^[Note that zoom already may cause an image to render at a size
different than its regular size, even before introducing the features in this
section.] But in fact it's generally valuable for
authors to control the size of embedded content. There are a number of ways to
do this,^[For example, the `width` and `height` CSS properties (not to be
confused with the `width` and `height` attributes!), which were an exercise in
Chapter 13.] but one way is the special `width` and `height`
attributes.^[Images have these mostly for historical reasons, because these
attributes were invented before CSS existed.]

If _both_ those attributes are present, things are pretty easy: we
just read from them when laying out the element, both in `image`:

``` {.python}
class BlockLayout:
    def image(self, node):
        if "width" in node.attributes:
            w = device_px(int(node.attributes["width"]), self.zoom)
        else:
            w = device_px(node.image.width(), self.zoom)
        # ...
```

And in `ImageLayout`:

``` {.python}
class ImageLayout(EmbedLayout):
    def layout(self):
        # ...
        width_attr = self.node.attributes.get("width")
        height_attr = self.node.attributes.get("height")
        image_width = self.node.image.width()
        image_height = self.node.image.height()

        if width_attr and height_attr:
            self.width = device_px(int(width_attr), self.zoom)
            self.img_height = device_px(int(height_attr), self.zoom)
        else:
            self.width = device_px(image_width, self.zoom)
            self.img_height = device_px(image_height, self.zoom)
        # ...
```

This works great, but it has a major flaw: if the ratio of `width` to
`height` isn't the same as the underlying image size, the image ends
up stretched in weird ways. Sometimes that's on purpose but usually
it's a mistake. So browsers let authors specify *just one* of `width`
and `height`, and compute the other using the image's *aspect
ratio*.[^only-recently-aspect-ratio]

[^only-recently-aspect-ratio]: Despite it being easy to implement, this
feature of real web browsers only appeared in 2021. Before that, developers
resorted to things like the [padding-top hack][padding-top-hack]. Sometimes
design oversights take a long time to fix.

[padding-top-hack]: https://web.dev/aspect-ratio/#the-old-hack-maintaining-aspect-ratio-with-padding-top

Implementing this aspect ratio tweak is easy:

``` {.python}
class ImageLayout(EmbedLayout):
    # ...
    def layout(self):
        # ...
        aspect_ratio = image_width / image_height

        if width_attr and height_attr:
            # ...
        elif width_attr:
            self.width = device_px(int(width_attr), self.zoom)
            self.img_height = self.width / aspect_ratio
        elif height_attr:
            self.img_height = device_px(int(height_attr), self.zoom)
            self.width = self.img_height * aspect_ratio
        else:
            # ...
        # ...
```

Your browser should now be able to render <a
href="/examples/example15-img.html">this example page</a> correctly.

::: {.further}
Our browser computes an aspect ratio from the loaded image dimensions,
but that's not available before an image loads, which is a problem in
real browsers where images are loaded asynchronously and where the
image size can [respond to][resp-design] layout parameters. Not
knowing the aspect ratio can cause the [layout to shift][cls] when the
image loads, which can be frustrating for users. The [`aspect-ratio`
property][aspect-ratio] is one way web pages can address this issue.
:::

[resp-design]: https://developer.mozilla.org/en-US/docs/Learn/CSS/CSS_layout/Responsive_Design
[cls]: https://web.dev/cls/

Interactive widgets
===================

So far, our browser has two kinds of embedded content: images and
input elements. While both are important and widely-used,[^variants]
they don't offer quite the customizability[^openui] and flexibility
that complex embedded content use cases like maps, PDFs, ads, and social media
controls require. So in modern browsers, these are handled by
*embedding one web page within another* using the `<iframe>` element.

[^variants]: As are variations like the [`<canvas>`][canvas-elt]
    element. Instead of loading an image from the network, JavaScript
    can draw on a `<canvas>` element via an API. Unlike images,
    `<canvas>` element's don't have intrinsic sizes, but besides that
    they are pretty similar.

[canvas-elt]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/canvas
    
[^openui]: There's actually [ongoing work](https://open-ui.org/) aimed at
    allowing web pages to customize what input elements look like, and it
    builds on earlier work supporting [custom elements][web-components] and
    [forms][form-el]. This problem is quite challenging, interacting with
    platform independence, accessibility, scripting, and styling.

[web-components]: https://developer.mozilla.org/en-US/docs/Web/Web_Components
[form-el]: https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/attachInternals

Semantically, an `<iframe>` is almost exactly a `Tab` inside a
`Tab`---it has its own HTML document, CSS, and scripts. And
layout-wise, an `<iframe>` is a lot like the `<img>` tag, with `width`
and `height` attributes. So implementing basic iframes just requires
handling three significant differences:

* Iframes have *no browser chrome*. So any page navigation has to happen from
   within the page (either through an `<a>` element or script), or as a side
   effect of navigation on the web page that *contains* the `<iframe>`
   element.

* Iframes can *share a rendering event loop*.[^iframe-event-loop] In
  real browsers, [cross-origin] iframes are often "site isolated",
  meaning that the iframe has its own CPU process for [security
  reasons][site-isolation]. In our toy browser we'll just make all
  iframes (even nested ones---yes, iframes can include iframes!) use
  the same rendering event loop.

* Cross-origin iframes are *script-isolated* from the containing page.
  That means that a script in the iframe [can't access][cant-access]
  the containing page's variables or DOM, nor can scripts in the
  containing page access the iframe's variables or DOM. Same-origin
  iframes, however, can.

[^iframe-event-loop]: For example, if an iframe has the same origin as
    the web page that embeds it, then scripts in the iframe can
    synchronously access the parent DOM. That means that it'd be
    basically impossible to put that iframe in a different thread or
    CPU process, and in practice it ends up in the same rendering
    event loop as a result.

[cross-origin]: https://developer.mozilla.org/en-US/docs/Web/Security/Same-origin_policy

[site-isolation]: https://www.chromium.org/Home/chromium-security/site-isolation/

[cant-access]: https://developer.mozilla.org/en-US/docs/Web/Security/Same-origin_policy#cross-origin_script_api_access

We'll get to these differences, but for now, let's start working on
the idea of a `Tab` within a `Tab`. What we're going to do is split
the `Tab` class into two pieces: `Tab` will own the event loop and
script environments, `Frame`s that do the rest.

It's good to plan out complicated refactors like this in some detail.
A `Tab` will:

* Interface between the `Browser` and the `Frame`s to handle events.
* Proxy communication between frames.
* Kick off animation frames and rendering.
* Paint and own the display list for all frames in the tab.
* Construct and own the accessibility tree.
* Commit to the browser thread.

And the new `Frame` class will:

* Own the DOM, layout trees, and scroll offset for its HTML document.
* Run style and layout on the its DOM and layout tree.
* Implement loading and event handling (focus, hit testing, etc) for its HTML
  document.

Create these two classes and split the methods between them accordingly.
  
Naturally, every `Frame` will need a reference to its `Tab`; it's also
convenient to have access to the parent frame and the corresponding
`<iframe>` element:
  
``` {.python}
class Frame:
    def __init__(self, tab, parent_frame, frame_element):
        self.tab = tab
        self.parent_frame = parent_frame
        self.frame_element = frame_element
        # ...
```

Now let's look at how `Frame`s are created. The first place is in
`Tab`'s load method, which needs to create the *root frame*:

``` {.python}
class Tab:
    def __init__(self, browser):
        # ...
        self.root_frame = None

    def load(self, url, body=None):
        self.history.append(url)
        # ...
        self.root_frame = Frame(self, None, None)
        self.root_frame.load(url, body)
```

Note that the guts of `load` now lives in the `Frame`, because
the `Frame` owns the DOM tree. The `Frame` can *also* construct child
`Frame`s, for `<iframe>` elements:

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
            document_url = url.resolve(iframe.attributes["src"])
            if not self.allowed_request(document_url):
                print("Blocked iframe", document_url, "due to CSP")
                iframe.frame = None
                continue
            iframe.frame = Frame(self.tab, self, iframe)
            iframe.frame.load(document_url)
        # ...
```

So we've now got a tree of frames inside a single tab. But because we
will sometimes need direct access to an arbitrary frame, let's also
give each frame an identifier, which I'm calling a *window ID*:

``` {.python}
class Frame:
    def __init__(self, tab, parent_frame, frame_element):
        # ...
        self.window_id = len(self.tab.window_id_to_frame)
        self.tab.window_id_to_frame[self.window_id] = self

class Tab:
    def __init__(self, browser):
        # ...
        self.window_id_to_frame = {}
```

Now that we have frames being created, let's work on rendering those
frames to the screen.

::: {.further}
For quite a while, browsers also supported embedded content in the
form of *plugins* like [Java applets][java-applets] or [Flash]. But
there were [performance, security, and accessibility
problems][embedding] because plugins typically implemented their own
rendering, sandboxing, and UI primitives. Over time, new APIs have
closed the gap between web-native content and "non-web"
plugins,[^like-canvas] and plugins have therefore become less common.
Personally, I think that's a good thing: the web is about making
information accessible to everyone, and that requires open standards,
including for embedded content.
:::

[java-applets]: https://en.wikipedia.org/wiki/Java_applet
[Flash]: https://en.wikipedia.org/wiki/Adobe_Flash
[embedding]: https://developer.mozilla.org/en-US/docs/Learn/HTML/Multimedia_and_embedding/Other_embedding_technologies#the_embed_and_object_elements
[^like-canvas]: For example, in the last decade the `<canvas>` element
has gained support for hardware-accelerated 3D content, while
[WebAssembly][webassembly] can run at near-native speed.

[webassembly]: https://en.wikipedia.org/wiki/WebAssembly

Iframe rendering
================

Rendering is split between the `Tab` and its `Frame`s: the `Frame`
does style and layout, while the `Tab` does accessibility and
paint.[^why-split] We'll need to implement that split, and also add code
to trigger each `Frame`'s rendering from the `Tab`.

[^why-split]: Why split the rendering pipeline this way? Because the
    output of accessibility and paint is combined across all
    frames---a single display list, and a single accessibility
    tree---while the DOMs and layout trees don't intermingle.
    
Let's start with splitting the rendering pipeline. The main method
here is still the `Tab`'s `render` method, which first calls `render`
on each frame to do style and layout:

``` {.python}
class Tab:
    def render(self):
        self.browser.measure.start('render')

        for id, frame in self.window_id_to_frame.items():
            frame.render()

        if self.needs_accessibility:
            # ...

        if self.pending_hover:
            # ...

        # ...
```

Note that the `needs_accessibility`, `pending_hover`, and other flags
are all still on the `Tab`, because they relate to the `Tab`'s part of
rendering. Meanwhile, style and layout happen in the `Frame` now:

``` {.python}
class Frame:
    def __init__(self, tab, parent_frame, frame_element):
        # ...
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

Again, these dirty bits move to the `Frame` because they relate to the
frame's part of rendering.

Yet unlike images, iframes have
*no [intrinsic size][intrinsic-size]*--the layout size of an `<iframe>` element
 does not depend on its content.[^seamless-iframe] That means there's a crucial
 extra bit of communication that needs to happen between the parent and child
 frames: how wide and tall should a frame be laid out? This is defined by the
 attributes and CSS of the `iframe` element:

[intrinsic-size]: https://developer.mozilla.org/en-US/docs/Glossary/Intrinsic_Size

[^seamless-iframe]: There was an attempt to provide iframes with
intrinsic sizing in the past, but it was [removed][seamless-removed]
from the HTML specification when no browser implemented it. This may
change [in the future][seamless-back], as there are good use cases for
a "seamless" iframe whose layout coordinates with its parent frame.

[seamless-removed]: https://github.com/whatwg/html/issues/331
[seamless-back]: https://github.com/w3c/csswg-drafts/issues/1771

``` {.python}
class BlockLayout:
    # ...
    def recurse(self, node):
        # ...
            elif node.tag == "iframe" and \
                 "src" in node.attributes:
                self.iframe(node)
    # ...
    def iframe(self, node):
        if "width" in self.node.attributes:
            w = device_px(int(self.node.attributes["width"]),
            self.zoom)
        else:
            w = IFRAME_WIDTH_PX + device_px(2, self.zoom)
        self.add_inline_child(node, w, IframeLayout, self.frame)
```

The `IframeLayout` layout code is also similar, inheriting from
`EmbedLayout`, but without the aspect ratio code:

``` {.python}
class IframeLayout(EmbedLayout):
    def __init__(self, node, parent, previous, parent_frame):
        super().__init__(node, parent, previous, parent_frame)

    def layout(self):
        # ...
        if width_attr:
            self.width = device_px(int(width_attr) + 2, self.zoom)
        else:
            self.width = device_px(IFRAME_WIDTH_PX + 2, self.zoom)

        if height_attr:
            self.height = device_px(int(height_attr) + 2, self.zoom)
        else:
            self.height = device_px(IFRAME_HEIGHT_PX + 2, self.zoom)
```

Note that if the `width` isn't specified, it uses a [default
value][iframe-defaults], chosen a long time ago based on the average
screen sizes of the day:

[iframe-defaults]: https://www.w3.org/TR/CSS2/visudet.html#inline-replaced-width

``` {.python}
IFRAME_WIDTH_PX = 300
IFRAME_HEIGHT_PX = 150
```

The extra 2 pixels (corrected for zoom, of course) provide room for a border
later on.

Now, note that this code is run in the *parent* frame. We need to get
this width and height over to the *child* frame, so it can know its
width and height during layout. So let's add a field for that in the
child frame:

``` {.python}
class Frame:
    def __init__(self, tab, parent_frame, frame_element):
        # ...
        self.frame_width = 0
        self.frame_height = 0
```

And we can set those when the parent frame is laid out:[^no-set-needs]

[^no-set-needs]: You might be surprised that I'm not calling
    `set_needs_render` on the child frame here. That's a shortcut: the
    `width` and `height` attributes can only change through
    `setAttribute`, while `zoom` can only change in `zoom_by` and
    `reset_zoom`. All of those handlers already invalidate all frames.

``` {.python}
class IframeLayout(EmbedLayout):
    def layout(self):
        # ...
        if self.node.frame:
            self.node.frame.frame_height = \
                self.height - device_px(2, self.zoom)
            self.node.frame.frame_width = \
                self.width - device_px(2, self.zoom)
```

The conditional is only there to handle the (unusual) case of an
iframe blocked due by CSP.

The root frame, of course, fills the whole window:

``` {.python}
class Tab:
    def load(self, url, body=None):
        # ...
        self.root_frame.frame_width = WIDTH
        self.root_frame.frame_height = HEIGHT - CHROME_PX
```

Note that there's a tricky dependency order here. We need the parent
frame to do layout before the child frame, so the child frame has an
up-to-date width and height when it does layout. That order is
guaranteed for us by Python (3.7 or later), where dictionaries are
sorted by insertion order, but if you're following along in another
language, you might need to sort frames before rendering them.

Alright, we've now got frames styled and laid out, and just need to
paint them. Unlike layout and style, all the frames in a tab produce a
single, unified display list, so we're going to need to work
recursively. We'll have the `Tab` paint the root `Frame`:

``` {.python}
class Tab:
    def render(self):
        if self.needs_paint:
            self.display_list = []
            self.root_frame.paint(self.display_list)
            self.needs_paint = False
```

We'll then have the `Frame` call the layout tree's `paint` method:

``` {.python expected=False}
class Frame:
    def paint(self, display_list):
        self.document.paint(display_list)
```

Most of the layout tree's `paint` methods don't need to change, but to
paint an `IframeLayout`, we'll need to paint the child frame:

``` {.python}
class IframeLayout(EmbedLayout):
    def paint(self, display_list):
        frame_cmds = []

        rect = skia.Rect.MakeLTRB(
            self.x, self.y,
            self.x + self.width, self.y + self.height)
        bgcolor = self.node.style.get("background-color",
                                 "transparent")
        if bgcolor != "transparent":
            radius = device_px(float(
                self.node.style.get("border-radius", "0px")[:-2]),
                self.zoom)
            frame_cmds.append(DrawRRect(rect, radius, bgcolor))

        if self.node.frame:
            self.node.frame.paint(frame_cmds)
```

Note the last line, where we recursively paint the child frame. 

Before putting those commands in the display list, though, we need to
add a border, clip content outside of it, and transform the coordinate
system:

``` {.python}
class IframeLayout(EmbedLayout):
    def paint(self, display_list):
        # ...

        diff = device_px(1, self.zoom)
        offset = (self.x + diff, self.y + diff)
        cmds = [Transform(offset, rect, self.node, frame_cmds)]
        inner_rect = skia.Rect.MakeLTRB(
            self.x + diff, self.y + diff,
            self.x + self.width - diff, self.y + self.height - diff)
        cmds = paint_visual_effects(self.node, cmds, inner_rect)
        paint_outline(self.node, cmds, rect, self.zoom)
        display_list.extend(cmds)
```

The `Transform` shifts over the child frame contents so that its
top-left corner starts in the right place,[^content-box] while
`paint_outline` adds the border and `paint_visual_effects` clips
content outside the viewable area of the iframe. Conveniently, we've
already implemented all of these features and can simply trigger them
from our browser CSS file:^[Another good reason to delay iframes and
images until chapter 15 perhaps?]

[^content-box]: This book doesn't go into the details of the [CSS box
model][box-model], but the `width` and `height` attributes of an
iframe refer to the *content box*, and adding the border width yields
the *border box*. Note also that the clip we're appling is an overflow
clip, which is not quite the same as an iframe clip, and the differences have
to do with the box model as well. As a result, what we've implemented is
somewhat incorrect with respect to all of those factors.

[box-model]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Box_Model/Introduction_to_the_CSS_box_model

``` {.css}
iframe {
    outline: 1px solid black;
    overflow: clip;
}
```

Finally, let's also add iframes to the accessibility tree. Like the
display list, the accessibility tree is global across all frames.
We can have iframes create `iframe` nodes:

``` {.python replace=node)/node%2C%20parent%20%3d%20None)}
class AccessibilityNode:
    def __init__(self, node):
        else:
            elif node.tag == "iframe":
                self.role = "iframe"
```

To `build` such a node, we just recurse into the frame:

``` {.python replace=AccessibilityNode(child_node.frame.nodes)/FrameAccessibilityNode(child_node%2C%20self)}
class AccessibilityNode:
   def build_internal(self, child_node):
        if isinstance(child_node, Element) \
            and child_node.tag == "iframe" and child_node.frame:
            child = AccessibilityNode(child_node.frame.nodes)
        # ... 
```

So we've now got iframes showing up on the screen. The next step is
interacting with them.

::: {.further}
Before iframes, there were the [`<frameset>` and `<frame>`][frameset] elements.
A `<frameset>` replaces the `<body>` tag and splits browser window
screen among multiple `<frame>`s; this was an early alternative layout
algorithm to the one presented in this book. Frames had confusing
navigation and accessibility, and lacked the flexibility of
`<iframe>`s, so aren't used much these days.
:::

[frameset]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/frameset

Iframe input events
===================

Now that we've got iframes rendering to the screen, let's close the
loop with user input. We want to add support for clicking on things
inside an iframe, and also for tabbing around or scrolling inside one.

At a high level, event handlers just delegate to the root frame:

``` {.python}
class Tab:
    def click(self, x, y):
        self.render()
        self.root_frame.click(x, y)
```

When an iframe is clicked, it passes the click through to the child
frame, and immediately return afterwards, because iframes capture
click events:

``` {.python}
class Frame:
    def click(self, x, y):
        # ...
        while elt:
            # ...
            elif elt.tag == "iframe":
                new_x = x - elt.layout_object.x
                new_y = y - elt.layout_object.y
                elt.frame.click(new_x, new_y)
                return

```

Now, clicking on `<a>` elements will work, which means that you can
now cause a frame to navigate to a new page. And because a `Frame` has
all the loading and navigation logic that `Tab` used to have, it just
works without any more changes!

You should now be able to load [this
example](examples/example15-iframe.html). Repeatedly clicking on the
link will add another recursive iframe.

Let's get the other interactions working as well, starting with
focusing an element. You can focus on *only one element per tab*, so we
will still store the `focus` on the `Tab`, but we'll need to store the
frame the focused element is on too:

``` {.python}
class Tab:
    def __init__(self, browser):
        self.focus = None
        self.focused_frame = None
```

When a frame tries to focus on an element, it sets itself as the
focused frame, but before it does that, it needs to un-focus the
previously-focused frame:

``` {.python}
class Frame:
    def focus_element(self, node):
        # ...
        if self.tab.focused_frame and self.tab.focused_frame != self:
            self.tab.focused_frame.set_needs_render()
        self.tab.focused_frame = self
        # ...
```

We need to re-render the previously-focused frame so that it
stops drawing the focus outline.

Another interaction is pressing `Tab` to cycle through focusable
elements in the current frame. Let's move the `advance_tab` logic into
`Frame` and just dispatch to it from the `Tab`:

``` {.python}
class Tab:
    def advance_tab(self):
        frame = self.focused_frame or self.root_frame
        frame.advance_tab()
```

Do the same exact thing for `keypress` and `enter`, which are used for
interacting with text inputs and buttons.

Another big interaction we need to support is scrolling. We'll store
the scroll offset in each `Frame`:

``` {.python}
class Frame:
    def __init__(self, tab, parent_frame, frame_element):
        self.scroll = 0
```

Now, as you might recall from [Chapter 13](animations.md), scrolling
happens both inside `Browser` and inside `Tab`, to reduce latency.
That was already quite complicated, so to keep things simple, we won't
support both for non-root iframes. We'll need a new commit parameter
so the browser thread knows whether the root frame is focused:

``` {.python}
class CommitData:
    def __init__(self, url, scroll, root_frame_focused, height,
        display_list, composited_updates, accessibility_tree, focus):
        # ...
        self.root_frame_focused = root_frame_focused

class Tab:
    def run_animation_frame(self, scroll):
        root_frame_focused = not self.focused_frame or \
                self.focused_frame == self.root_frame
        # ...
        commit_data = CommitData(
            # ...
            root_frame_focused,
            # ...
        )
        # ...
```

The `Browser` thread will save this information in `commit` and use it
when the user requests a scroll:

``` {.python}
class Browser:
    def commit(self, tab, data):
        # ...
            self.root_frame_focused = data.root_frame_focused

    def handle_down(self):
        self.lock.acquire(blocking=True)
        if self.root_frame_focused:
            # ...
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.scrolldown)
        active_tab.task_runner.schedule_task(task)
        self.lock.release()
```

When a tab is asked to scroll, it then scrolls the focused frame:

``` {.python}
class Tab:
    def scrolldown(self):
        frame = self.focused_frame or self.root_frame
        frame.scrolldown()
        self.set_needs_paint()
```

There's one more subtlety to scrolling. After we scroll, we want to
*clamp* the scroll position, to prevent the user scrolling past the
last thing on the page. Right now `clamp_scroll` uses the window
height to determine the maximum scroll amount; let's move that
function inside `Frame` so it can use the current frame's height:

``` {.python}
class Frame:
    def scrolldown(self):
        self.scroll = self.clamp_scroll(self.scroll + SCROLL_STEP)

    def clamp_scroll(self, scroll):
        height = math.ceil(self.document.height)
        maxscroll = height - self.frame_height
        return max(0, min(scroll, maxscroll))
```

Make sure to use the new `clamp_scroll` in place of the old one,
everywhere in `Frame`:

``` {.python}
class Frame:
    def scroll_to(self, elt):
        # ...
        self.scroll = self.clamp_scroll(new_scroll)
```

Scroll clamping can also come into play if a layout causes a page's
maximum height to shrink. You'll need to move the scroll clamping
logic out of `Tab`'s `run_animation_frame` method and into the
`Frame`'s `render` to handle this:

``` {.python}
class Frame:
    def render(self):
        clamped_scroll = self.clamp_scroll(self.scroll)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_frame = True
        self.scroll = clamped_scroll
```


There's also a set of accessibility hover interactions that we need to
support. This is hard, because the accessibility interactions happen
in the browser thread, which has limited information:

- The accessibility tree doesn't know where the iframe is, so it
  doesn't know how to transform the hover coordinates when it goes
  into a frame.
  
- It also doesn't know how big the iframe is, so it doesn't ignore things that
  are clipped outside an iframe's bounds.^[Observe that frame-based `click`
  already works correctly, because we don't recurse into iframes unless the
  click intersects the `iframe` element's bounds. And before iframes, we didn't
  need to do that, because the SDL window system already did it for us.]

- It also doesn't know how far a frame has scrolled, so it doesn't
  adjust for scrolled frames.

We'll make a subclass of `AccessibilityNode` to store this information:

``` {.python}
class FrameAccessibilityNode(AccessibilityNode):
    pass
```

We'll create one of those below each `iframe` node:

``` {.python replace=(child_node)/(child_node%2C%20self)}
class AccessibilityNode:
    def build_internal(self, child_node):
        if isinstance(child_node, Element) \
            and child_node.tag == "iframe" and child_node.frame:
            child = FrameAccessibilityNode(child_node)
```

Hit testing now has to become recursive, so that
`FrameAccessibilityNode` can adjust for the iframe location:

``` {.python}
class AccessibilityNode:
    def hit_test(self, x, y):
        node = None
        if self.intersects(x, y):
            node = self
        for child in self.children:
            res = child.hit_test(x, y)
            if res: node = res
        return node
```

Hit testing `FrameAccessibilityNodes` will use the frame's bounds to
ignore clicks outside the frame bounds, and adjust clicks against the
frame's coordinates:

``` {.python}
class FrameAccessibilityNode(AccessibilityNode):
    def hit_test(self, x, y):
        if not self.intersects(x, y): return
        new_x = x - self.bounds.x()
        new_y = y - self.bounds.y() + self.scroll
        node = self
        for child in self.children:
            res = child.hit_test(new_x, new_y)
            if res: node = res
        return node
```

Hit testing should now work, but the bounds of the hovered node when drawn
to the screen are still wrong. For that, we'll need a method that returns
the absolute screen rect of an `AccessibilityNode`. And that method in turn
needs parent pointers to walk up the accessibility tree, so let's add that first:

``` {.python}
class AccessibilityNode:
    def __init__(self, node, parent = None):
        # ...
        self.parent = parent

    def build_internal(self, child_node):
        # ...
            child = FrameAccessibilityNode(child_node, self)
        else:
            child = AccessibilityNode(child_node, self)
```

And now the method to map to absolute coordinates:

``` {.python}
class AccessibilityNode:
    def absolute_bounds(self):
        rect = skia.Rect.MakeXYWH(
            self.bounds.x(), self.bounds.y(),
            self.bounds.width(), self.bounds.height())
        obj = self
        while obj:
            obj.map_to_parent(rect)
            obj = obj.parent
        return rect
```

This method depends on calls `map_to_parent` to adjust the bounds. For
 most accessibility nodes we don't need to do anything, because they are in the same
coordinate space as their parent:

``` {.python}
class AccessibilityNode:
    def map_to_parent(self, rect):
        pass
```

A `FrameAccessibilityNode`, on the other hand, adjusts for the iframe's position:

``` {.python}
class FrameAccessibilityNode(AccessibilityNode):
    def map_to_parent(self, rect):
        rect.offset(self.bounds.x(), self.bounds.y() - self.scroll)
```

You should now be able to hover on nodes and have them read out by our
accessibility subsystem.

Alright, we've now got all of our browser's forms of user interaction
properly recursing through the frame tree. It's time to add more
capabilities to iframes.

::: {.further}
Our browser can only scroll the root frame on the browser thread, but
real browsers have put in [a lot of work][threaded-scroll] to make
scrolling happen on the browser thread as much as possible, including
for iframes. The hard part is handling the many obscure combinations
of containing blocks, [stacking orders][stacking-order], [scroll
bars][overflow], transforms, and iframes: with scrolling on the
browser thread, all of these complex interactions have be communicated
from the main thread to the browser thread, and correctly interpreted
by both sides.
:::

[stacking-order]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Positioning/Understanding_z_index/The_stacking_context
[overflow]: https://developer.mozilla.org/en-US/docs/Web/CSS/overflow
[threaded-scroll]: https://developer.chrome.com/articles/renderingng/#threaded-scrolling-animations-and-decode



Iframe scripts
==============

We've now got users interacting with iframes---but what about scripts
interacting with them? Of course, each frame can _already_ run
scripts---but right now, each `Frame` has its own `JSContext`, so
these scripts can't really interact with each other. Instead
*same-origin* iframes should run in the same JavaScript context and
should be able to access each other's globals, call each other's
functions, and modify each other's DOMs. Let's implement that.

For two frames' JavaScript environments to interact, we'll need to put
them in the same `JSContext`. So, instead of each `Frame` having a
`JSContext` of its own, we'll want to store `JSContext`s on the `Tab`,
in a dictionary that maps origins to JS contexts:

``` {.python}
class Tab:
    def __init__(self, browser):
        # ...
        self.origin_to_js = {}

    def get_js(self, origin):
        if origin not in self.origin_to_js:
            self.origin_to_js[origin] = JSContext(self, origin)
        return self.origin_to_js[origin]
```

Each `Frame` will then ask the `Tab` for its JavaScript context:

``` {.python}
class Frame:
    def load(self, url, body=None):
        # ...
        self.js = self.tab.get_js(url.origin())
        # ...
```

So we've got multiple pages' scripts using one JavaScript context. But now we've
got to keep their variables in their own namespaces somehow. The key is going
to be the `window` global, of type `Window`. In the browser, this refers to the
[global object][global-object], and instead of writing a global variable like
`a`, you can always write `window.a` instead.[^shadow-realms] To keep our
implementation simple, in our browser, scripts will always need to reference
variable and functions via `window`.^[This also means that all global variables
in a script need to do the same, even if they are not browser APIs.] We'll need
to do the same in our runtime:

[^shadow-realms]: There are [various proposals][shadowrealm] to expose
multiple global namespaces as a JavaScript API. It would definitely be
convenient to have that capability in this chapter, to avoid this
restriction!

[shadowrealm]: https://github.com/tc39/proposal-shadowrealm


``` {.js}
window.console = { log: function(x) { call_python("log", x); } }

// ...

window.Node = function(handle) { this.handle = handle; }

// ...
```

Do the same for every function or variable in the `runtime.js` file.
If you miss one, you'll get errors like this:

    _dukpy.JSRuntimeError: ReferenceError: identifier 'Node' undefined
    	duk_js_var.c:1258
    	eval src/pyduktape.c:1 preventsyield

Then you'll need to go find where you forgot to put `window.` in front
of `Node`. You'll also need to modify `EVENT_DISPATCH_CODE` to prefix
classes with `window`:

``` {.python}
EVENT_DISPATCH_CODE = \
    "new window.Node(dukpy.handle)" + \
    ".dispatchEvent(new window.Event(dukpy.type))"
```

::: {.quirk}
Demos from previous chapters will need to be similarly fixed up before
they work. For example, `setTimeout` might need to change to
`window.setTimeout`.
:::

[global-object]: https://developer.mozilla.org/en-US/docs/Glossary/Global_object

To get multiple frames' scripts to play nice inside one JavaScript
context, we'll create multiple `Window` objects: `window_1`,
`window_2`, and so on. Before running a frame's scripts, we'll set
`window` to that frame's `Window` object, so that the script uses the
correct `Window`.[^dukpy-limitation]

[^dukpy-limitation]: Some JavaScript engines support a simple API for
    changing the global object, but the DukPy library that we're using
    isn't one of them. There *is* a standard JavaScript operator
    called `with` which sort of does this, but the rules are
    complicated and not quite what we need here. It's also not
    recommended these days.

So to begin with, let's define the `Window` class when we create a
`JSContext`:

``` {.python}
class JSContext:
    def __init__(self, tab, url_origin):
        self.url_origin = url_origin
        # ...
        self.interp.evaljs("function Window(id) { this._id = id };")
```

Now, when a frame is created and wants to use a `JSContext`, it needs
to ask for a `window` object to be created first:

``` {.python}
class JSContext:
    def add_window(self, frame):
        code = "var window_{} = new Window({});".format(
            frame.window_id, frame.window_id)
        self.interp.evaljs(code)
```

Before running any JavaScript, we'll want to change which window the
`window` global refers to:

``` {.python}
class JSContext:
    def wrap(self, script, window_id):
        return "window = window_{}; {}".format(window_id, script)
```

We can use this to, for example, set up the initial runtime
environment for each `Frame`:

``` {.python}
class JSContext:
    def add_window(self, frame):
        # ...
        with open("runtime15.js") as f:
            self.interp.evaljs(self.wrap(f.read(), frame.window_id))
```

We'll need to call `wrap` any time we use `evaljs`, which also means
we'll need to add a window ID argument to a lot of methods. For
example, in `run` we'll add a `window_id` parameter:

``` {.python}
class JSContext:
    def run(self, script, code, window_id):
        try:
            code = self.wrap(code, window_id)
            self.interp.evaljs(code)
        except dukpy.JSRuntimeError as e:
            print("Script", script, "crashed", e)
```

And we'll pass that argument from the `load` method:

``` {.python}
class Frame:
    def load(self, url, body=None):
        for script in scripts:
            # ...
            task = Task(self.js.run, script_url, body,
                self.window_id)
            # ...
```

The same holds for various dispatching APIs. For example, to dispatch
an event, we'll need the `window_id`:

``` {.python}
class JSContext:
    def dispatch_event(self, type, elt, window_id):
        # ...
        code = self.wrap(EVENT_DISPATCH_CODE, window_id)
        do_default = self.interp.evaljs(code,
            type=type, handle=handle)
```

Likewise, we'll need to pass a window ID argument in `click`,
`submit_form`, and `keypress`; I've omitted those code fragments. Note
that you should have modified your `runtime.js` file to store the
`LISTENERS` on the `window` object, meaning each `Frame` will have its
own set of event listeners to dispatch to:

``` {.js}
window.LISTENERS = {}

// ...


window.Node.prototype.dispatchEvent = function(evt) {
    var type = evt.type;
    var handle = this.handle
    var list = (window.LISTENERS[handle] &&
        window.LISTENERS[handle][type]) || [];
    for (var i = 0; i < list.length; i++) {
        list[i].call(this, evt);
    }
    return evt.do_default;
}
```

Do the same for `requestAnimationFrame`, passing around a window ID
and wrapping the code so that it correctly references `window`.

For calls _from_ JavaScript into the browser, we'll need JavaScript to
pass in the window ID it's calling from:

``` {.javascript}
window.document = { querySelectorAll: function(s) {
    var handles = call_python("querySelectorAll", s, window._id);
    return handles.map(function(h) { return new window.Node(h) });
}}
```

Then on the browser side we can use that window ID to get the `Frame`
object:

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

We'll need something similar in `innerHTML` and `style` because we
need to `set_needs_render` on the relevant `Frame`.

Finally, for `setTimeout` and `XMLHttpRequest`, which involve a call
from JavaScript into the browser and later a call from the browser
into JavaScript, we'll likewise need to pass in a window ID from
JavaScript, and use that window ID when calling back into JavaScript.

I've omitted many of the code changes in this section because they are
quite repetitive. You can find all of the needed locations by
searching your codebase for `evaljs`; once you've got scripts working
again, let's make it possible for scripts in different frames to
interact.

::: {.further}
Same-origin iframes can access each other's state, but cross-origin
ones can't. But the obscure [`domain`][domain-prop] property lets an
iframe change its origin, moving itself in or out of same-origin
status in some cases. I personally think it's a misfeature: it's hard
to implement securely, and interferes with various sandboxing techniques;
I hope it is eventually removed from the web. Instead, there are [various
headers][origin-headers] where an iframe can opt into less sharing in
order to get better security and performance.
:::

[domain-prop]: https://developer.mozilla.org/en-US/docs/Web/API/Document/domain
[origin-headers]: https://html.spec.whatwg.org/multipage/browsers.html#origin-isolation

Communicating between frames
============================

We've now managed to run multiple `Frame`s' worth of JavaScript in a
single `JSContext`, and isolated them somewhat so that they don't mess
with each others' state. But the whole point of this exercise is to
allow *some* interaction between same-origin frames. Let's do that now.

The simplest way two frames can interact is that they can get access
to each other's state via the `parent` attribute on the `Window`
object. If the two frames have the same origin, that lets one frame
calls methods, access variables, and modify browser state for the
other frame. Because we've had these same-origin frames share a
`JSContext`, this isn't too hard to implement. Basically, we'll need a
way to go from a window ID to its parent frame's window ID:

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

On the JavaScript side, we now need to look up the `Window` object
given its window ID. There are lots of ways you could do this, but the
easiest is to have a global map:

``` {.python}
class JSContext:
    def __init__(self, tab, url_origin):
        # ...
        self.interp.evaljs("WINDOWS = {}")
```

We'll add each window to the global map as it's created:

``` {.python}
class JSContext:
    def add_window(self, frame):
        # ...
        self.interp.evaljs("WINDOWS[{}] = window_{};".format(
            frame.window_id, frame.window_id))
```

Now `window.parent` can look up the correct `Window` object in this
global map:

``` {.html}
Object.defineProperty(Window.prototype, 'parent', {
  configurable: true,
  get: function() {
    var parent_id = call_python('parent', window._id);
    if (parent_id != undefined) {
        var parent = WINDOWS[parent_id];
        if (parent === undefined) parent = new Window(parent_id);
        return parent;
    }
  }
});
```

Note that it's possible for the lookup in `WINDOWS` to fail, if the
parent frame is not in the same origin as the current one and
therefore isn't running in the same `JSContext`. In that case, this
code return a fresh `Window` object with that id. But iframes are not
allowed to access each others' documents across origins (or call various
other APIs that are unsafe), so add a method that checks for this situation
and raises an exception:

``` {.python}
class JSContext:
    def throw_if_cross_origin(self, frame):
        if frame.url.origin() != self.url_origin:
            raise Exception(
                "Cross-origin access disallowed from script")
```

Then use this method in all `JSContext` methods that access documents:^[Note
that in a real browser this is woefully inadequate security. A real browser
would need to very carefully lock down the entire `runtime.js` code and
audit every single JavaScript API with a fine-toothed comb.]

``` {.python}
class JSContext:
    def querySelectorAll(self, selector_text, window_id):
        frame = self.tab.window_id_to_frame[window_id]
        self.throw_if_cross_origin(frame)
        # ...

    def setAttribute(self, handle, attr, value, window_id):
        frame = self.tab.window_id_to_frame[window_id]
        self.throw_if_cross_origin(frame)
        # ...

    def innerHTML_set(self, handle, s, window_id):
        frame = self.tab.window_id_to_frame[window_id]
        self.throw_if_cross_origin(frame)
        # ...

    def style_set(self, handle, s, window_id):
        frame = self.tab.window_id_to_frame[window_id]
        self.throw_if_cross_origin(frame)
        # ...
```

So via `parent`, same-origin iframes can communicate. But what about
cross-origin iframes? It would be insecure to let them access each
other's variables or call each other's methods, so instead browsers
allow a form of [*message passing*][message-passing], a technique for
structured communication between two different event loops that
doesn't require any shared state or locks.

[message-passing]: https://en.wikipedia.org/wiki/Message_passing

Message-passing in JavaScript works like this: you call the
[`postMessage` API][postmessage] on the `Window` object you'd like to
talk to, with the message itself as the first parameter and `*` as the
second:^[The second parameter has to do with origin restrictions; see
the exercises.]

[postmessage]: https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage

    window.parent.postMessage("...", '*')

This will send the first argument[^structured-cloning] to the parent
frame, which can receive the message by handling the `message` event
on its `Window` object:

    window.addEventListener("message", function(e) {
        console.log(e.data);
    });

[^structured-cloning]: In a real browser, you can also pass data that
is not a string, such as numbers and objects. It works via a
*serialization* algorithm called [structured
cloning][structured-clone], which converts most JavaScript objects
(though not, for example, DOM nodes) to a sequence of bytes that the
receiver frame can convert back into a JavaScript object. DukPy
doesn't support structured cloning natively for objects, so our browser won't
support this either.

Note that in this second code snippet, `window` is the receiving
`Window`, a different `Window` from the `window` in the first snippet.

[structured-clone]: https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API/Structured_clone_algorithm

Let's implement `postMessage`, starting on the *receiver* side. Since
this event happens on the `Window`, not on a `Node`, we'll need a new
`WINDOW_LISTENERS` array:

``` {.javascript}
    window.WINDOW_LISTENERS = {}
```

Each listener will be called with a `MessageEvent` object:

``` {.javascript}
window.MessageEvent = function(data) {
    this.type = "message";
    this.data = data;
}
```

The event listener and dispatching code is the same as for `Node`, except
it's on `Window` and uses `WINDOW_LISTENERS`. You can just duplicate
those methods:

``` {.javascript}
Window.prototype.addEventListener = function(type, listener) {
    // ...
}

Window.prototype.dispatchEvent = function(evt) {
    // ...
}
```

That's everything on the receiver side; now let's do the sender side.
First, let's implement the `postMessage` API itself. Note that `this`
is the receiver or target window:

``` {.javascript}
Window.prototype.postMessage = function(message, origin) {
    call_python("postMessage", this._id, message, origin)
}
```

In the browser, `postMessage` schedules a task on the `Tab`:

``` {.python}
class JSContext:
    def postMessage(self, target_window_id, message, origin):
        task = Task(self.tab.post_message,
            message, target_window_id)
        self.tab.task_runner.schedule_task(task)
```

Scheduling the task is necessary because `postMessage` is an
asynchronous API; sending a synchronous message might involve
synchronizing multiple `JSContext`s or even multiple processes, which
would add a lot of overhead and probably result in deadlocks.

The task finds the target frame and call a dispatch method:

``` {.python}
class Tab:
    def post_message(self, message, target_window_id):
        frame = self.window_id_to_frame[target_window_id]
        frame.js.dispatch_post_message(
            message, target_window_id)
```

Which then calls into the JavaScript `dispatchEvent` method we just
wrote:

``` {.python}
POST_MESSAGE_DISPATCH_CODE = \
    "window.dispatchEvent(new window.MessageEvent(dukpy.data))"

class JSContext:
    def dispatch_post_message(self, message, window_id):
        self.interp.evaljs(
            self.wrap(POST_MESSAGE_DISPATCH_CODE, window_id),
            data=message)
```

You should now be able to use `postMessage` to send messages between
frames,[^postmessage-demo] including cross-origin frames running in
different `JSContext`s, in a secure way.

[^postmessage-demo]: In [this demo](examples/example15-iframe.html), for
example, you should see "Message received from iframe: This is the contents of
postMessage." printed to the console. (This particular example uses a
same-origin postMessage. You can test cross-origin locally by starting two
local HTTP servers on different ports, then changing the URL of the
`example15-img.html` iframe document to point to the second port.)

::: {.further}
Ads are commonly served with iframes and are big users of the web's
sandboxing, embedding, and animation primitives. This means they are a
challenging source of performance and [user experience][ux] problems.
For example, ad [analytics] are important to the ad economy, but
involve running a lot of code and measuring lots of data. Some web
APIs, such as [Intersection Observer][io], basically exist to make
analytics computations more efficient. And, of course, the most
popular [browser extensions][extensions] are probably ad blockers.
:::

[ux]: https://en.wikipedia.org/wiki/User_experience
[analytics]: https://en.wikipedia.org/wiki/Web_analytics
[extensions]: https://en.wikipedia.org/wiki/Browser_extension
[io]: https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API



Isolation and timing
====================

Iframes add a whole new layer of security challenges atop what we
discussed in [Chapter 10](security.md). The power to embed one web
page into another creates a commensurate security risk when the two
pages don't trust each other---both in the case of embedding an
untrusted page into your own page, and the reverse, where an attacker
embeds your page into their own, malicious one. In both cases, we want
to protect your page from any security or privacy risks caused by the
other frame.

The starting point is that cross-origin iframes can't access each
other directly through JavaScript. That's good---but what if a bug in
the JavaScript engine, like a [buffer overrun][buffer-overrun], lets
an iframe circumvent those protections? Unfortunately, bugs like this
are common enough that browsers have to defend against them. For
example, browsers these days run frames from different origins in
[different operating system processes][site-isolation], and use
operating system features to limit how much access those
processes have.

[buffer-overrun]: https://en.wikipedia.org/wiki/Buffer_overflow
[sandbox]: https://chromium.googlesource.com/chromium/src/+/main/docs/linux/sandboxing.md

Other parts of the browser mix content from multiple frames, like our
browser's `Tab`-wide display list. That means that a bug in the
rasterizer could allow one frame to take over the rasterizer and then
read data that ultimately came from another frame. This might seem
like a rather complex attack, but it's worth defending against, so
modern browsers use [sandboxing][sandbox] techniques to prevent it. For
example, Chromium can place the rasterizer in its own process and use
a Linux feature called `seccomp` to limit what system calls that
process can make. Even if a bug compromised the rasterizer, that
rasterizer wouldn't be able to exfiltrate data over the network,
preventing private date from leaking.

These isolation and sandboxing features may seem "straightforward", in
the same sense that the browser thread we added in [Chapter
13](scheduling.md) is "straightforward". In practice, the many browser
APIs mean the implementation is full of subtleties and ends up being
extremely complex. Chromium, for example, took many years to ship the
first implementation of site isolation.

[site-isolation]: https://www.chromium.org/Home/chromium-security/site-isolation/

Site isolation has become much more important recent years, due to the
CPU cache timing attacks called [*spectre* and
*meltdown*][spectre-meltdown]. In short, these attacks allow an
attacker to read arbitrary locations in memory---including another
frame's data, if the two frames are in the same process---by measuring
the time certain operations take. Placing sensitive content in
different CPU processes (which come with their own memory address
spaces) is a good protection against these attacks.

[spectre-meltdown]: https://meltdownattack.com/

That said, these kinds of *timing attacks* can be subtle, and there
are doubtless more that haven't been discovered yet. To try to dull
this threat, browsers currently prevent access to *high-precision
timers* that can provide the accurate timing data typically required
for timing attacks. For example, browsers reduce the accuracy of APIs
like `Date.now` or `setTimeout`.

Worse yet, there are browser APIs that don't seem like timers but can
be used as such.[^sharedarraybuffer-attack] These API are useful, so
browsers don't quite want to remove it, but there is also no way to
make it "less accurate", since it's not primarily a clock anyway.
Browsers now require [certain optional HTTP headers][sab-headers] to
be present in the parent *and* child frames' HTTP responses in order
to allow use of `SharedArrayBuffer`, though this is not a perfect
solution.

[^sharedarraybuffer-attack]: For example, the [SharedArrayBuffer] API lets
two JavaScript threads run concurrently and share memory, which can be
used to [construct a clock][sab-attack].

[SharedArrayBuffer]: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer

[sab-attack]: https://security.stackexchange.com/questions/177033/how-can-sharedarraybuffer-be-used-for-timing-attacks

[sab-headers]: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer#security_requirements


::: {.further}
The `SharedArrayBuffer` issue caused problems when I [added JavaScript
support][js-blog] to the embedded browser widgets on this website. I
was using `SharedArrayBuffer` to allow synchronous calls from a
`JSContext` to the browser, and that required APIs that browsers
restrict for security reasons. Setting the security headers wouldn't
work, because [Chapter 14](accessibility.md) embeds a Youtube video,
and YouTube doesn't send those headers. In the end, I worked around
the issue by not embedding the browser widget and [asking the
reader](scripts.html#outline) to open a new browser window.
:::

[js-blog]: https://browserbook.substack.com/p/javascript-in-javascript

Summary
=======

This chapter introduced how the browser handles embedded content use cases like
images and iframes. Reiterating the main points:

* Non-HTML *embedded content*---images, video, canvas, iframes, input elements,
  and plugins---can be embedded in a web page.

* Embedded content comes with its own performance concerns---like
  image decoding time---and necessitates custom optimizations.

* Iframes are a particularly important kind of embedded content,
  having over time replaced browser plugins as the standard way to
  easily embed complex content into a web page.

* Iframes introduce all the complexities of the web---rendering, event
  handling, navigation, security---into the browser's handling of
  embedded content. However, this complexity is justified, because
  they enable important cross-origin use cases like ads, video, and
  social media buttons.

And as we hope you saw in this chapter, none of these features are too
difficult to implement, though---as you'll see in the exercises
below---implementing them well requires a lot of attention to detail.

Outline
=======

The complete set of functions, classes, and methods in our browser 
should now look something like this:

::: {.cmd .python .outline html=True}
    python3 infra/outlines.py --html src/lab15.py
:::

Exercises
=========

*Canvas element*: Implement the [`<canvas>`][canvas-elt] element, the 2D aspect
of the [`getContext`][getcontext] API, and some of the drawing commands on
[`CanvasRenderingContext2D`][crc2d]. Canvas layout is just like an iframe,
including its default width and height. You should allocate a Skia canvas of
an appropriate size when `getContext("2d")` is called, and implement some of
the APIs that draw to the canvas.[^eager-canvas] It should be straightforward
to translate most API methods to their Skia equivalent.

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

*Background images*: Elements can have a [`background-image`][bg-img].
Implement the basics of this CSS property: a `url(...)` value for the
`background-image` property. Avoid loading the image if the
`background-image` property does not actually end up used on any
element. For a bigger challenge, also allow the web page set the size
of the background image with the [`background-size`][bg-size] CSS
property.

[bg-img]: https://developer.mozilla.org/en-US/docs/Web/CSS/background-image

[bg-size]: https://developer.mozilla.org/en-US/docs/Web/CSS/background-size

*Object-fit*: implement the [`object-fit`][obj-fit] CSS property. It determines
how the image within an `<img>` element is sized relative to its container
element.

[obj-fit]: https://developer.mozilla.org/en-US/docs/Web/CSS/object-fit

*Iframe aspect ratio*: Implement the [`aspect-ratio`][aspect-ratio] CSS
property and use it to provide an implicit sizing to iframes and images
when only one of `width` or `height` is specified (or when the image is not
yet loaded, if you did the lazy loading exercise).

[aspect-ratio]: https://developer.mozilla.org/en-US/docs/Web/CSS/aspect-ratio

*Lazy loading*: Even encoded images can be quite
large.[^early-lazy-loading] Add support for the
[`loading` attribute][img-loading] on `img` elements. Your browser should only
download images if they are close to the visible area of the page.
This kind of optimization is generally called [lazy loading][lli].
Implement a second optimization in your browser that only renders images that
are within a certain number of pixels of the being visible on the
screen.

[^early-lazy-loading]: In the early days of the web, computer networks
were slow enough that browsers had a user setting to disable
downloading of images until the user expressly asked for them.

[lli]: https://developer.mozilla.org/en-US/docs/Web/Performance/Lazy_loading

[img-loading]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img#loading

*Image placeholders*: Building on top of lazy loading, implement placeholder
styling of images that haven't loaded yet. This is done by setting a 0x0 sizing,
unless `width` or `height` is specified. Also add support for hiding the
"broken image" if the `alt` attribute is missing or empty.^[That's because
if `alt` text is provided, the browser can assume the image is important
to the meaning of the website, and so it should tell the user that they
are missing out on some of the content if it fails to load. But otherwise,
the broken image icon is probably just ugly clutter.]

*Media queries*: Implement the [width][width-mq] media query. Make
sure it works inside iframes. Also make sure it works even when the
width of an iframe is changed by its parent frame.

[width-mq]: https://developer.mozilla.org/en-US/docs/Web/CSS/@media/width

*Target origin for `postMessage`*: Implement the `targetOrigin`
parameter to [`postMessage`][postmessage]. This parameter is a string
which indicates the frame origins that are allowed to receive the
message.

*Multi-frame focus*: in our toy browser, pressing `Tab` cycles through
the elements in the focused frame. But means it's impossible to access
focusable elements in other frames via the keyboard alone. Fix it to move
between frames after iterating through all focusable elements in one
frame.

*Iframe history*: Ensure that iframes affect browser history. For
example, if you click on a link inside an iframe, and then hit
back button, it should go back inside the iframe. Make sure that this
works even when the user clicks links in multiple frames in various
orders.^[It's debatable whether this is a good feature of iframes, as
it causes a lot of confusion for web developers who embed iframes they
don't plan on navigating.]

*Iframes under transforms*: painting an iframe that has a CSS `transform` on it
or an ancestor should already work, but event targeting for clicks doesn't work,
because `click` doesn't account for that transform. Fix this. Also make sure
that accessibility handles iframes under transform correctly in all cases.

*Iframes added or removed by script*: the `innerHTML` API can cause iframes
to be added or removed, but our browser doesn't load or unload them
when this happens. Fix this: new iframes should be loaded and old ones
unloaded.
