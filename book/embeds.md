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

The most obvious missing feature

Plan:

* intro: images! iframes! video!

* download, decode, draw a simple image

* line layout w/replaced elements

* image resizing, filter quality, decoding to match rendered size


* iframes
  * Same-origin iframes: same interpreter, postMessage, parent
  * Cross-origin iframes: postMessage
  * caveat: bug in duktape regarding use of function() foo() {} syntax and the
    `with` operator

  TODO: make all JS APIs and keyboard events properly target iframes

* postMessage

Exercises:
* background-image: positioning, clipping
* Tiled images

* object-fit

