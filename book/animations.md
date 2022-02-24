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
var num_animation_frames = 100;
function animate() {
    if (num_animation_frames == 0) return;
    var div = document.querySelectorAll("div")[0];
    div.style = "opacity:" + (num_animation_frames / 100);
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

