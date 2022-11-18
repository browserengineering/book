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

[^images-interesting]: Actually, if I were to describe all aspects of images
in browsers, it would take up an entire chapter by itself. But many
of these details are quite specialized, or stray outside the
core tasks of a browser engine, so I've left them to footnotes.

Images
======

Images are everywhere on the web. They are relatively easy to implement in their
simplest form. Well, they are easy to implement if you have convenient
libraries to decode and render them. So let's just get to it.[^img-history]

[^img-history]: In fact, images  have been around (almost) since the
beginning, being proposed in [early 1993][img-email]. This makes it ironic that
images only make their appearance in chapter 15 of the book. My excuse is that
Tkinter doesn't support proper image sizing and clipping, so we had to wait
for the introduction of Skia.

[img-email]: http://1997.webhistory.org/www.lists/www-talk.1993q1/0182.html

Skia doesn't come with built-in image decoding, so first download and install
the [Pillow/PIL][pillow] library for this task:

[pillow]: https://pillow.readthedocs.io/en/stable/reference/Image.html

    pip3 install Pillow

and include it:^[Pillow is a fork of a project called PIL---for
Python Image Library---which is why the import says PIL.]

``` {.python}
import PIL.Image
```

But what is decoding? *Decoding* is the process of converting an *encoded* image
from a binary form optimized for quick download over a network into a
*decoded* one suitable for rendering, typically a raw bitmap in memory that's
suitable for direct input into rasterization on the GPU. It's
called "decoding" and not "decompression" because many encoded image formats
are [*lossy*][lossy], meaning that they "cheat": they don't faithfully represent all of
the information in the original picture, in cases where it's unlikely that a
human viewing the decoded image will notice the difference.

[lossy]: https://en.wikipedia.org/wiki/Lossy_compression

Many encoded image formats are very good at compression. This means that when
a browser decodes it, the image may take up quite a bit of memory, even if
the downloaded file size is not so big. As a result, it's very important
for browsers to optimize decoding in a few ways. 

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
screen.^[Real browsers have specal [APIs][lli] and optimizations for this
purpose.]

[lli]: https://developer.mozilla.org/en-US/docs/Web/Performance/Lazy_loading

