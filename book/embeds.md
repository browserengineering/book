---
title: Supporting Embedded Content
chapter: 15
prev: accessibility
next: invalidation
...


Plan:

* intro: images! iframes! video!

* download, decode, draw a simple image

* line layout w/replaced elements

* image resizing, filter quality, decoding to match rendered size

* background-image: positioning, clipping

* iframes
  * Same-origin iframes: same interpreter, postMessage, parent
  * Cross-origin iframes: postMessage
  * caveat: bug in duktape regarding use of function() foo() {} syntax and the
    `with` operator

  TODO: make all JS APIs and keyboard events properly target iframes

* postMessage

Exercises:

* Tiled images

* object-fit

