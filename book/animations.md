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
recognizing---not just movement from side to side, but growing, shrinking,
rotating, fading, blurring, nad sharpening.

[animation]: https://en.wikipedia.org/wiki/Animation

On web pages, there are several broad categories of common animations:

* DOM: movement of elements on the screen, by interpolating CSS properties of
elements such as color, opacity or sizing.[^innerHTML]

* Input-driven: scrolling, page resizing, pinch-zoom, draggable menus and similar
effects.

* Video-like: videos, animated images, and animated canvases.

[^innerHTML]: Animating by setting `innerHTML` is not very common, mostly
since its performance and developer ergonomics are poor. An exception is
animating the text content of leaf nodes of the DOM, such as in stock tickers
or counters.

In this chapter we'll focus on the first and second categories.[^excuse]

[^excuse]: We'll get to images in Chapter 14 and touch a bit on canvas; video is
a fascinating topic unto itself, but is beyond the scope of this book. Arguably,
canvas is a bit different than the other two, since it's implemented by
developer scripts. And of course a canvas can have animations within
it that look about the same as some DOM animations.

DOM and input-driven animations can be sub-categorized into *layout-inducing*
and *visual*. An animation is layout-inducing if the changing CSS property
is an input to layout; `width` is one example that we'll encounter in this
chapter. Otherwise the animation is visual, such as animations of `opacity` or
`background-color`.

The distinction is important for two reasons: animation quality and performance.
In general, layout-inducing animations often have undesirable
quality---animating `width` can lead to text jumping around as line breaking
changes---and performance implication (the name says it all: these animations
require main thread `render` calls.^[Sometimes it's a better user experience to
animate layout-inducing properties. The best example of this is resizing a
browser window via a mouse gesture, where it's very useful for the user to see
the new layout as they animate. Modern browsers are fast enough to do this,
but it used to be that instead they would leave a visual "gutter"
(a gap between content and the edge of the window) during the animation, to
avoid updating layout on every animation frame.]

This means we're in luck though! Visual effect animations can almost always
be run on the browser thread, and also GPU-accelerated. But I'm getting ahead
of myself---let's now take a tour through DOM animations and how to achieve
them, before showing how to accelerate them.

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

``` {.html file=example-opacity-html}
<div>Test</div>
```

``` {.javascript file=example-opacity-js}
var start_value = 1;
var end_value = 0.1;
var num_animation_frames = 120;
var frames_remaining = num_animation_frames;
function animate() {
    if (frames_remaining == 0) return;
    var div = document.querySelectorAll("div")[0];
    var percent_remaining = frames_remaining / num_animation_frames;
    div.style = "opacity:" +
        (percent_remaining * start_value +
        (1 - percent_remaining) * end_value);
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

Width/height animations
=======================

What about layout-inducing DOM animations? At the moment, our browser doesn't
support any layout-inducing CSS properties that would be useful to animate,
so let's add support for `width` and `height`, then animate them. These
CSS properties do pretty much what they say: force the width or height of
a layout object to be the specified value in pixels, as opposed to the default
behavior that sizes a block to contain block and inline descendants. If
as a result the descendants don't fit, they will *overflow* in a natural
way. This generally means overflowing the bottom edge of the block
ancestor, because we'll use `width` to determine the area for line
breaking.[^overflow]

[^overflow]: By default, overflowing content draws outside the bounds of
the parent layout object. We discussed overflow to some extent in
[Chapter 11](visual-effects.md#clipping-and-masking), and implemented
`overflow:clip`, which instead clips the overflowing content at the box
boundary. Other values include `scroll`, which clips it but allows the user
to see it via scrolling. And if scroll is specified in the x direction, the
descendant content will lay out as it if has an infinite width.

Implementing `width` and `height` turns out to be pretty easy. Instead
of setting the width of a layout object to the widest it can be before recursing,
use the specified width instead. Then, descendants will use that width their
sizing automatically.

Start by implementing a `style_length` helper method that applies a
restricted length(either in the horizontal or vertical dimension) if it's
specified in the object's style. For example,

	style_length(node, "width", 300)

would return 300 if the `width` CSS property was not set
on `node`, and the `width` value otherwise.^[Interesting side note: pixel
values specified in CSS can be floating-point numbers, but computer monitors
have discrete pixels, so browsers need to apply some method of converting to
integers. This process is called pixel-snapping, and in real browsers it's much
more complicated than just a call to `math.floor`. [This article][pixel-canvas]
touches on some of the complexities as they apply to canvases, but it's just
as complex for DOM elements. For example, if two block elements touch
and have fractional widths, it's important to round in such a way that there
is not a gap introduced between them.]

[pixel-canvas]: https://web.dev/device-pixel-content-box/#pixel-snapping

``` {.python}
def style_length(node, style_name, default_value):
    style_val = node.style.get(style_name)
    if style_val:
        return int(math.floor(float(style_val[:-2])))
    else:
        return default_value
```

With that in hand, the changes to `BlockLayout`, `InlineLayout` and
`InputLayout` are satisfyingly small. Here is `BlockLayout`; the other
two are basically the same so I'll omit the edits here, but don't forget to
update them.

``` {.python}
class BlockLayout:
	def layout(self):
		# ...
        self.width = style_length(
            self.node, "width", self.parent.width)
		# ...
        self.height = style_length(
            self.node, "height",
            sum([child.height for child in self.children]))
```

Here is a simple animation of `width`. As the width animates from
`400px` to `100px`, its height will automatically increase to contain the
text as it flows into multiple lines.

``` {.html file=example-width-html}
<div style="background-color:lightblue;width:100px">
	This is a test line of text for a width animation</div>
```

``` {.javascript file=example-width-js}
var start_value = 400;
var end_value = 100;
var num_animation_frames = 120;
var frames_remaining = num_animation_frames;
function animate() {
    if (frames_remaining == 0) return;
    var div = document.querySelectorAll("div")[0];
    var percent_remaining = frames_remaining / num_animation_frames;
    div.style = "background-color:lightblue;width:" +
        (percent_remaining * start_value +
        (1 - percent_remaining) * end_value) + "px";
    frames_remaining--;
    requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
```

pTransform animations
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