---
title: Animations and Compositing
chapter: 13
prev: visual-effects
next: skipped
...

The UI of a complex web application these days requires not just fast loading,
visually interesting rendering, and responsiveness to input and scrolling. It
also needs smooth *animations* when transitioning between DOM
states. These transitions improve usability of web applications by helping
users understand what changed, and improve visual polish by replacing sudden
jumps with smooth interpolations.

Modern browsers have APIs that enable animating the styles of DOM elements.
To implement these APIs performantly, behind the scenes new technology is
needed to make those animations smooth and fast.

Types of animations
===================

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

[^excuse]: We'll get to images and a bit of canvas in Chapter 14; video is
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
qualities---animating `width` can lead to text jumping around as line breaking
changes---and performance implications (the name says it all: these animations
require main thread `render` calls).^[Sometimes it's a better user experience to
animate layout-inducing properties. The best example of this is resizing a
browser window via a mouse gesture, where it's very useful for the user to see
the new layout as they animate. Modern browsers are fast enough to do this,
but it used to be that instead they would leave a visual *gutter*
(a gap between content and the edge of the window) during the animation, to
avoid updating layout on every animation frame.]

This means we're in luck though! Visual effect animations can almost always
be run on the browser thread, and also GPU-accelerated. But I'm getting ahead
of myself---let's first take a tour through DOM animations and how to achieve
them, before figuring how to accelerate them.

Opacity animations
==================

In Chapter 12 we [implemented](scheduling.md#animating-frames) the
`requestAnimationFrame` API, and built a demo that modifies the `innerHTML`
of a DOM element on each frame. That is indeed an animation---a
*JavaScript-driven* animation---but `innerHTML` is generally not how
high-quality animations are done on the web. Instead, it almost always makes
sense to first render some content into layout objects, then apply a DOM
animation to the layout tree.

It's straightforward to imagine how this might work for opacity: define
some HTML that you want to animate, then interpolate the `opacity` CSS property
in JavaScript smoothly from one value to another. Here's an example that
animates from 1 to 0.1, over 120 frames (about two seconds).

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

(click <a href="examples/example13-opacity.html">here</a> to load the example in
your browser)

This example uses a new feature we haven't added to our browser yet: modifying
the inline style of an element with JavaScript. Doing so has the same effect as
having specified the new `style` attribute value in HTML.

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

Load up the example, and observe text fading to white!

Width/height animations
=======================

What about layout-inducing DOM animations? At the moment, our browser doesn't
support any layout-inducing CSS properties that would be useful to animate,
so let's add support for `width` and `height`, then animate them. These
CSS properties do pretty much what they say: force the width or height of
a layout object to be the specified value in pixels, as opposed to the default
behavior that sizes a block to contain block and inline descendants. If
as a result the descendants don't fit, they will *overflow* in a natural
way. This usually means overflowing the bottom edge of the block
ancestor, because we'll use `width` to determine the area for line
breaking.[^overflow]

[^overflow]: By default, overflowing content draws outside the bounds of
the parent layout object. We discussed overflow to some extent in
[Chapter 11](visual-effects.md#clipping-and-masking), and implemented
`overflow:clip`, which instead clips the overflowing content at the box
boundary. Other values include `scroll`, which clips it but allows the user
to see it via scrolling. And if scroll is specified in the x direction, the
descendant content will lay out as it if has an infinite width. Extra long
words can also cause horizontal overflow.

Implementing `width` and `height` turns out to be pretty easy. Instead
of setting the width of a layout object to the widest it can be before recursing,
use the specified width instead. Then, descendants will use that width for their
sizing automatically.

Start by implementing a `style_length` helper method that applies a
restricted length (either in the horizontal or vertical dimension) if it's
specified in the object's style. For example,

	style_length(node, "width", 300)

would return 300 if the `width` CSS property was not set
on `node`, and the `width` value otherwise. Floating-point values for `width`
need to be rounded to an integer.^[Interesting side note: pixel
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

Here is a simple animation of `width`. As the width of the `div` animates from
`400px` to `100px`, its height will automatically increase to contain the
text as it flows into multiple lines.^[And if automic increase was not desired,
`height` coupld specified to a fixed value. But that would of course cause
overflow, which needs to be dealt with in one way or another.]

``` {.html file=example-width-html}
<div style="background-color:lightblue;width:100px">
	This is a test line of text for a width animation.
</div>
```

(click <a href="examples/example13-width.html">here</a> to load the example in
your browser)

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

CSS transitions
===============

But why do we need JavaScript just to smoothly interpolate `opacity` or `width`?
Well, that's what [CSS transitions][css-transitions] are for. The `transition` CSS
property works like this:

[css-transitions]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Transitions/Using_CSS_transitions

	transition: opacity 2s,width 2s;

This means that, whenever the `opacity` or `width` propertes of the element
change---for any reason, including mutating its style attribute or loading a
style sheet---then the browser should smoothly interpolate between the old and
new values, in basically the same way the `requestAnimationFrame` loop did id.
This is much more convenient than writing a bunch of JavaScript, and also
doesn't force you to remember each and every way in which the styles can
change.

Implement this CSS property. Start with a quick helper method that returns
true if `transition` was set set for a particular property. (Unfortunately,
setting up animations tends to have a lot of boilerplate code, but it's all
pretty simple to understand.)

```
def has_transition(property_value, style):
    if not "transition" in style:
        return False
    transition_items = style["transition"].split(",")
    for item in transition_items:
        if property_value == item.split(" ")[0]:
            return True
    return False
```

Next let's add some code that detects if a transition should start, by comparing
two style objects---the ones before and after a style update for a DOM node. It
will return a `NumericAnimation` object that handles the animation if so, and
otherwise `None.` Both `opacity` and `width` are *numeric* animations, but with
different units---unitless floating-point between 0 and 1, respectively.
[^more-units] The difference will be handled by an `is_px` parameter indicating
which it is.

``` {.python}
def try_numeric_animation(node, name, is_px, old_style, new_style, tab):
    if not has_transition(name, old_style) or \
        not has_transition(name, new_style):
        return None

    if old_style[name] == new_style[name]:
        return None

    if is_px:
        old_value = float(old_style[name][:-2])
        new_value = float(new_style[name][:-2])
    else:
        old_value = float(old_style[name])
        new_value = float(new_style[name])

    change_per_frame = (new_value - old_value) / ANIMATION_FRAME_COUNT
    return NumericAnimation(
        node, name, is_px, old_value, change_per_frame, new_style, tab)
```

[^more-units]: In a real browsers, there are a [lot more][units] units to
contend with.

[units]: https://developer.mozilla.org/en-US/docs/Learn/CSS/Building_blocks/Values_and_units

Now for implementing `NumericAnimation`. This class just encapsulates a bunch
of parameters, and has a single `animate` method. `animate` is in charge of
advancing the animation by one frame; it's the equivalent of the
`requestAnimationFrame` callback in a JavaScript-driven animation. It also
returns `False` if the animation has ended.

``` {.python}
class NumericAnimation:
    def __init__(
        self, node, property_name, is_px, old_value, change_per_frame,
        computed_style, tab):
        self.node = node
        self.property_name = property_name
        self.is_px = is_px
        self.old_value = old_value
        self.change_per_frame = change_per_frame
        self.computed_style = computed_style
        self.tab = tab
        self.frame_count = 0
        self.animate()

    def animate(self):
        self.frame_count += 1
        updated_value = self.old_value + self.change_per_frame * self.frame_count
        if self.is_px:
            self.computed_style[self.property_name] = "{}px".format(updated_value)
        else:
            self.computed_style[self.property_name] = "{}".format(updated_value)
        self.tab.set_needs_render()
        return self.frame_count < ANIMATION_FRAME_COUNT
```

Now for integrating this code into rendering. It has main parts: detecting style
changes, and executing the animation. Both have some details that are important
to get right, but are conceptually straightforward:

* In the `style` function, when a DOM node changes its style, check to see if
  one or more of the properties with registered transitions are changed; if so,
  start a new animation and add it to the `animations` dictionary on the `Tab`.
  This logic will be in a new function called `animate_style`, which is called
  just after the style update for `node` is complete:

``` {.python}
def style(node, rules, tab):
    old_style = None
    if hasattr(node, 'style'):
        old_style = node.style

    # ...

    animate_style(node, old_style, node.style, tab)
```

And `animate_style` just has some pretty simple business logic to
find animations and start them. First, bail if there is not an old style,
new style. Then look for `opacity` and `width` animations, and add them
to the `animations` object if so.[^corner-cases]

[^corner-cases]: Note that this code doesn't handle some corner cases
correctly, such as re-starting a transition if the node's style changes during
an animation.

``` {.python}
def animate_style(node, old_style, new_style, tab):
    if not old_style:
        return

    opacity_animation = \
        try_numeric_animation(node, "opacity", False, old_style, new_style, tab)
    width_animation = \
        try_numeric_animation(node, "width", True, old_style, new_style, tab)

    if opacity_animation or width_animation:
        tab.animations[node] = []

    if opacity_animation:
        tab.animations[node].append(opacity_animation)
    if width_animation:
        tab.animations[node].append(width_animation)
```

* In `run_animation_frame` on the `Tab`, each animation in `animations` is
  updated just after running `requestAnimationFrame` callbacks and before
  calling `render`. The basics are: loop over all animations, and all
  `animate`, which will modify the node's style and call `set_needs_render`.
  The call to `set_needs_render` will cause the call to `render` to update
  rendering with the new style. It will *also* call `set_needs_animation_frame`
  on the `Browser`. This causes yet another call to `run_animation_frame` to
  happen 16ms in the future.

``` {.python expected=False}
class Tab:
    def __init__(self, browser):
        # ...
        self.animations = {}

    def run_animation_frame(self, scroll):
        # ...
        self.js.interp.evaljs("__runRAFHandlers()")
        # ...
        for node in self.animations:
            for animation in self.animations[node]:
                animation.animate()
        # ...
        self.render()
```

But there is one more detail missing that we need to add: we haven't
figured out what happens at the end of an animation. When that happens,
we should remove the animation from `animations`. This will be tricky, because

GPU acceleration
================

Move raster and draw to the GPU. Show how just that makes things much faster,

Compositing
===========

Show how to provide independent textures for animated content to avoid expensive
raster costs.

Transform animations
====================

Motivated by overlap in compositing.

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

*Background-color*: implement animations of the `background-color` CSS property.
You'll have to define a new kind of interpolation that applies to all the
color channels.

*Easing functions*: our browser only implements a linear interpolation between
 start and end values, but there are many other [easing functions][easing] 
 (in fact, the default one in real browsers is
 `cubic-bezier(0.25, 0.1, 0.25, 1.0)`, not linear). Implement this easing
 function, and one or two others.

 [easing]: https://developer.mozilla.org/en-US/docs/Web/CSS/easing-function