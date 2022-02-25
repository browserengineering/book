---
title: Animations and Compositing
chapter: 13
prev: visual-effects
next: skipped
...

The UI of a complex web application these days is not just fast to load,
visually interesting and responsive to input and scrolling. It also needs to
support smooth *animations* when transitioning between DOM states. These
transitions improve usability of web applications by helping users understand
what changed through visual movement from one state to another, and improve
visual polish by replacing sudden visual jumps with smooth interpolations.

Modern browsers have APIs that enable animating the styles of DOM elements.
To implement these APIs, behind the scenes a new technology is
needed to make those animations smooth and fast.

Visual effect animations
========================

Defined broadly, an [animation] is a sequence of pictures shown in quick
succession, leading to the illusion of *movement* to the human
eye.[^general-movement] So it's not arbitrary changes, but ones that seem
logical to a person.

[^general-movement]: Here movement should be defined broadly to encompass all of
the kinds of visual changes humans are used to seeing and good at
recognizing---not just movement from side to side, but growning, shrinking,
rotating, fading, blurring, nad sharpening.

[animation]: https://en.wikipedia.org/wiki/Animation

On web pages, there are several broad categories of common animations:

* DOM: movement of elements on the screen, by changing CSS properties of
elements.[^innerHTML]

* Input-linked: scrolling, page resizing, pinch-zoom, drawers and similar
effects

* Video-like: videos, animated images, and animated canvases

[^innerHTML]: Animating by setting `innerHTML` is not very common, mostly
since its performance and developer ergonomics are poor. An exception is
animating the text content of leaf nodes of the DOM, such as in stock tickers
or counters.

In this chapter we'll focus on the first and second category.[^excuse]

[^excuse]: We'll get to images in Chapter 14 and touch a bit on canvas; video is
a fascinating topic unto itself, but is beyond the scope of this book.

The DOM category can be sub-categorized into *layout-inducing* and *visual*.
A DOM animation is layout-inducing if the changing CSS property is an input
to layout; `width` is one example that we'll encounter in this chapter.
Otherwise the animation is visual, such as animations of `opacity` or
`background-color`.

The distinction is important for two reasons: animation quality and performance.
In general, layout-inducing animations often have undesirable quality
(animationg `width` can lead to text jumping around as line breaking changes)
and performance implication (the name says it all: these animations require
main thread `render` calls).

This means we're in luck though! Visual effect animations can almost always
be run on the browser thread, and also GPU accelerated. But I'm getting ahead
of myself---let's now take a tour through DOM animations and how to achieve
them, before showing how to accelerate them.

Width/height animations
=======================

todo

Opacity animations
==================

In Chapter 12 we [implemented](scheduling.md#animating-frames) the
`requestAnimationFrame` API, and built a demo that modifies the `innerHTML`
of a DOM element on each frame. That is indeed an animation---a
*JavaScript-driven* animation---but this is generally not how high-quality
animations are done on the web. Instead, it almost always makes sense to first
render some content into layout objects, then apply various kinds of
animations to it, such as *transform* (moving it around, growing or
shrinking it) or *opacity* (fading pixels in or out).

It's straightforward to imagine how this might work for opacity. We added this
feature to our browser in [Chapter 11](visual-effects.md#opacity-and-alpha);
opacity is represented by a `SaveLayer` display list command that applies
transparency to a stacking context. To animate opacity from one value to
another, you could animate the `opacity` CSS property in JavaScript smoothly
from one value to another, with code like this code, which animates from
opacity 1 to 0 in 100 steps:

``` {.html file=examplehtml}
<script src="example13.js"></script>
<div>Test</div>
```

``` {.javascript file=examplejs}
var end_opacity = 0;
var num_animation_frames = 120;
var frames_remaining = num_animation_frames;
function animate() {
    if (frames_remaining == 0) return;
    var div = document.querySelectorAll("div")[0];
    div.style = "opacity:" + (frames_remaining / num_animation_frames);
    frames_remaining--;
    requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
```

This example uses a new feature we haven't added to our browser yet: modifying
the inline style of an element with JavaScript. In this case, setting
`myElement.style.opacity` changes the value of the `style` HTML attribute to a
new value.

Let's go ahead and add that feature. We'll need to register a setter on
the `style` attribute of `Node` in the JavaScript runtime:

``` {.javascript file=runtime}
Object.defineProperty(Node.prototype, 'style', {
    set: function(s) {
        call_python("style_set", this.handle, s.toString());
    }
});
```

And some simple Python code:

``` {.python}
class JSContext:
    def __init__(self, tab):
        self.interp.export_function("style_set", self.style_set)

     def style_set(self, handle, s):
        elt = self.handle_to_node[handle]
        elt.attributes["style"] = s;
        self.tab.set_needs_render()
```

Load up the example, and observe text fading to white! But why do we need
JavaScript just to smoothly interpolate opacity? Well, that's what
[CSS transitions[css-transitions] are. `transition` CSS property is for. The
CSS rule

	transition: opacity 2s;

means that, whenver the `opacity` property of the element changes---for any
reason, including mutating its style attribute or loading a style sheet---then
the browser should smoothly interpolate 

[css-transitions]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Transitions/Using_CSS_transitions

Transform animations
====================

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

Exercises
=========

*Easing functions*: our browser only implements a linear interpolation between
 start and end values, but there are many other [easing functions][easing] 
 (in fact, the default one in real browsers is
 `cubic-bezier(0.25, 0.1, 0.25, 1.0)`, not linear). Implement this easing
 function, and one or two others.

 [easing]: https://developer.mozilla.org/en-US/docs/Web/CSS/easing-function