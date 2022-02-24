---
title: Animations and Compositing
chapter: 13
prev: visual-effects
next: skipped
...

The UI of a modern web application is not just fast to load, visually
interesting and responsive to input and scrolling. It also needs to support
smooth *animations* when transitioning between DOM states. These transitions
improve usability of web applications by helping users understand what changed
through visual movement from one state to another, and improve visual polish by
replacing sudden visual jumps with smooth interpolations.

Modern browsers have APIs that enable animating the styles of DOM elements.
To implement these APIs, behind the scenes a new technology is
needed to make those animations smooth and fast.

Animations in CSS
=================

In Chapter 12 we [implemented](scheduling.md#animating-frames) the
`requestAnimationFrame` API, and built a demo that modifies the `innerHTML`
of a DOM element on each frame. That is indeed an animation---a
*JavaScript-driven* animation---but this is generally not how high-quality
animations are done on the web. Instead, it almost always makes sense to first
render some content into layout objects, then apply various kinds of
animations to it, such as *transform* (moving it around, growing or
shrinking it) or *opacity* (fading pixels in or out).

It's pretty easy to imagine how this might work for opacity. We added this
feature to our browser in [Chapter 11](visual-effects.md#opacity-and-alpha);
opacity is represented by a `SaveLayer` display 

GPU acceleration
================

Move raster and draw to the GPU. Show how just that makes things much faster,

Compositing
===========

Show how to provide independent textures for animated content to avoid expensive
raster costs.

Composited animations
=====================

Show how to run the animations only on the compositor thread, to isolate
from main-thread jank.

Accelerated scrolling
=====================

Show how the same technology accelerates scrolling, and implement smooth
scrolling, as a way of demonstrating that scrolling is best thought of as an
animation.

