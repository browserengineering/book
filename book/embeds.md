---
title: Supporting Embedded Content
chapter: 15
prev: accessibility
next: skipped
...

Our toy browser has a lot of rendering features, but is still missing a few
features present on pretty much every website. The most obvious is *images*. So
we can and should add support for images to our browser to make it feel more
complete. But images are actually the simplest form of *embedded content*
within a web page, a much bigger topic, and one that has a lot of interesting
implications for how browser engines work.[^images-interesting] That's mostly
due to how powerful *iframes* are, since they allow you to embed one website
in another. We'll go through two aspects of embedded content in this chapter:
how to render them, and their impact on the rendering event loop.

[^images-interesting]: Actually, if I were to go in depth into all the
complexities of images in a browser, it would already be an entire chapter. But
many of this topics are pretty advanced details, or get outside of the core
tasks of a browser engine.

Images
======

Images are everywhere on the web. They are relatively easy to implement in their
simplest form. Well, they are easy to implement if you have convenient
libraries to decode and render them. So let's just get to it.[^img-history]

Skia doesn't come with built-in image decoding, so first download and install
the [Pillow/PIL][pillow] library:

    pip3 install Pillow

and include it:

``` {.python}
import Pillow
```

[pillow]: https://pillow.readthedocs.io/en/stable/reference/Image.html

[^img-history] In fact, images  have been around (almost) since the
beginning, being proposed in [early 1993][img-email]. This makes it ironic that
images only make their appearance in chapter 15 of the book. My excuse is that
`tkinter` doesn't support proper image sizing and clipping, so we had to wait
for the introduction of Skia.

[img-email]: http://1997.webhistory.org/www.lists/www-talk.1993q1/0182.html

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
