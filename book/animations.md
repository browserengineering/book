---
title: Animations and Compositing
chapter: 13
prev: scheduling
next: skipped
...

The UI of a complex web application requires not just fast loading, visually
interesting rendering, and responsiveness to input and scrolling. It also needs
smooth *animations* when transitioning between DOM states. These transitions
improve usability of the web application by helping users understand what
changed, and improve visual polish by replacing sudden jumps with smooth
interpolations.

Modern browsers have APIs that enable animating the styles of DOM elements. To
implement these APIs performantly, behind the scenes GPU acceleration and
compositing is needed to make those animations smooth and fast.

Types of animations
===================

An [animation] is a sequence of pictures shown in quick succession that create
an illusion of *movement* to the human eye.[^general-movement] The pixel
changes in an animation are *not* arbitrary; they are ones that feel logical to
a human mind trained by experience in the real world.

[^general-movement]: Here *movement* should be construed broadly to encompass
all of the kinds of visual changes humans are used to seeing and good at
recognizing---not just movement from side to side, but growing, shrinking,
rotating, fading, blurring, and sharpening.

[animation]: https://en.wikipedia.org/wiki/Animation

On web pages, there are several categories of common animations: DOM,
input-driven and video-like. A DOM animation is a movement or visual effect
change of elements on the screen, achieved by interpolating CSS properties of
elements such as color, opacity or sizing, or changes of text content.
Input-driven animations involve input of course: scrolling, page resizing,
pinch-zoom, draggable menus and similar effects.[^video-anim]  In this chapter
we'll focus mostly on DOM animations, with a bit of input-driven animations a
bit at the end.[^excuse]

[^video-anim]: And video-like animations include videos, animated images, and
animated canvases.

[^excuse]: Video animations is a topic unto itself, but is beyond the
scope of this book. Arguably, canvas is a bit different than the other two,
since it's implemented by developer scripts. And of course a canvas can have
animations within it that look about the same as some DOM animations.

DOM and input-driven animations can be sub-categorized into *layout-inducing*
and *visual*. An animation is layout-inducing if it changes an input to layout;
animating `width` is one example that we'll encounter in this chapter.
Otherwise the animation is visual, such as animations of `opacity` or
`background-color`.


::: {.further}

The distinction between visual effect and layout animations is important for two
reasons: animation quality and performance. In general, layout-inducing
animations often have undesirable qualities---animating `width` can lead to
text jumping around as line breaking changes---and performance implications
(the name says it all: these animations require (main-thread) layout). Most of
the time, layout-inducing animations are not a good idea for these reasons.

An exception is a layout-inducing animation when resizing a browser window via
a mouse gesture; in this case it's very useful for the user to see the new
layout as the window size changes. Modern browsers are fast enough to do this,
but it used to be that instead they would leave a visual *gutter* (a gap
between content and the edge of the window) during the animation, to avoid
updating layout on every animation frame.

:::

The animation loop
==================

Let's start by exploring some example animations. The simplest way to implement
them in our current browser is with some JavaScript and a few tiny extensions
to our browser's APIs, so we'll start there. Almost any animation
can in principle be implemented this way.

In Chapter 12 we [implemented](scheduling.md#animating-frames) the
`requestAnimationFrame` API and built a demo that modifies the `innerHTML`
of a DOM element on each frame. That is indeed an animation---a
*JavaScript-driven* animation. These animations all have the following
structure:

``` {.javascript file=example-opacity-js}
function run_animation_frame() {
    if (animate())
        requestAnimationFrame(run_animation_frame);
}
requestAnimationFrame(run_animation_frame);
```

where `animate` is a (custom-to-each-animation) function that updates the
animation from one frame to the next, and returns `true` as long as it needs to
keep animating. For example, the Chapter 12 equivalent of this method sets the
`innerHTML` of an element to increase a counter. The animation examples in this
chapter will modify CSS properties instead.

Even better would be to run these CSS property animations automatically in the
browser. As you might guess, there are huge performance, complexity and
architectural advantages to doing so.[^advantages] And that's what this chapter
is really about: how to go about doing that, and exploring all of these
advantages. But it's important to keep in mind that the way the browser will
implement these animations is at its root
*exactly the same*: run an animation loop at 60Hz and advance the animation
 frame-by-frame.

[^advantages]: Advantages such as optimizing which parts of the rendering
pipeline have to be re-run on each animation frame, and running animations
entirely on the browser thread.

The browser implementation ends up quite complicated, and it's easy to lose
track of where we're headed. So if you start to get lost, just remember: all
that's going on is optimizing animation loops by building them directly into
the rendering pipeline.

::: {.further}

The animation pattern presented in this section is yet another example
of the *event loop* first introduced [in Chapter 2][eventloop-ch2]
and evolved further [in Chapter 12][eventloop-ch12]. What's new in this
chapter is that we finally have enough tech built up to actually create
meaningful, practical animations.

And the same happened with the web. A whole lot of the
APIs for proper animations, from the `requestAnimationFrame` API to
CSS-native animations, came onto the scene only in the
decade of the [2010s][cssanim-hist].

[eventloop-ch2]: http://localhost:8001/graphics.html#creating-windows
[eventloop-ch12]: http://localhost:8001/scheduling.html#animating-frames
[cssanim-hist]: https://en.wikipedia.org/wiki/CSS_animations

:::

GPU acceleration
================

However, even before trying out any examples, it should be very clear from
chapters 11 and 12 that there is no way to animate reliably at 60Hz if
raster-and-draw takes
[66ms or more per frame](scheduling.md#profiling-rendering) on simple examples.

So the first order of business is to move raster and draw to the
[GPU][gpu]. Because both SDL and Skia support these modes, turning it on is
just a matter of passing the right configuration parameters. First you'll need
to import code for OpenGL. Install the library:

    pip3 install PyOpenGL

and then import it:

``` {.python}
import OpenGL.GL as GL
```

Then configure `sdl_window` and start/stop a
[GL context][glcontext] at the
beginning/end of the program; for our purposes consider it API
boilerplate.^[Starting a GL context is just OpenGL's way
of saying "set up the surface into which subsequent GL drawing commands will
draw". After doing so you can even execute OpenGL commands manually, to
draw polygons or other objects on the screen, without using Skia at all.
[Try it][pyopengl] if you're interested!]

[glcontext]: https://www.khronos.org/opengl/wiki/OpenGL_Context

[pyopengl]: http://pyopengl.sourceforge.net/

``` {.python expected=False}
class Browser:
    def __init__(self):
        self.sdl_window = sdl2.SDL_CreateWindow(b"Browser",
            sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
            WIDTH, HEIGHT,
            sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_OPENGL)
        self.gl_context = sdl2.SDL_GL_CreateContext(self.sdl_window)
        print("OpenGL initialized: vendor={}, renderer={}".format(
            GL.glGetString(GL.GL_VENDOR),
            GL.glGetString(GL.GL_RENDERER)))

    def handle_quit(self):
        # ...
        sdl2.SDL_GL_DeleteContext(self.gl_context)
        sdl2.SDL_DestroyWindow(self.sdl_window)

```

I've also added code above to print out the vendor and renderer of the GPU your
computer is using; this will help you verify that it's actually using the GPU
properly. I'm using a Chromebook to write this chapter, so for me it
says:[^virgl]

    OpenGL initialized: vendor=b'Red Hat', renderer=b'virgl'

[^virgl]: In this case, `virgl` stands for "virtual GL", a way of
hardware-accelerating the Linux subsystem of ChromeOS that works with the
ChromeOS Linux sandbox.

There are lots of resources online about how GPUs work and how to program them
via GL shaders and so on. But we won't be writing shaders or other
types of GPU programs in this book. Instead, let's focus on the basics of GPU
technologies and how they map to browsers. A GPU is essentially a computer chip
that is good at running very simple computer programs that specialize in
turning simple data structures into pixels. These programs are so simple that
the GPU can run one of them *in parallel* for each pixel, and this parallelism
is why GPU raster is usually much faster than CPU raster. GPU draw is also
much faster, because "copying" from one piece of GPU memory to another also
happens in parallel for each pixel.

At a high level, the steps to raster and draw using the GPU are:[^gpu-variations]

[^gpu-variations]: These steps vary a bit in the details by GPU architecture.

* *Upload* the input data structures (that describe the display list)
   to specialized GPU memory.

* *Compile* GPU programs to run on the data structures.[^compiled-gpu]

[^compiled-gpu]: That's right, GPU programs are dynamically compiled! This
allows GPU programs to be portable across a wide variety of implementations
that may have very different instruction sets or acceleration tactics.

* For each desired surface, *execute* the raster into GPU textures.[^texture]

[^texture]: A surface represented on the GPU is called a *texture*. There can be
more than one surface, and practically speaking they often can't be rastered in
parallel with each other.

* *Draw* the textures onto the screen.

You can configure any GPU program to draw directly to the *screen framebuffer*,
or to an *intermediate texture*.[^gpu-texture] Draw proceeds bottom-up: the
leaf textures are generated from raw display list data structures, and internal
surface tree textures are generated by computing visual effects on one or more
children. The root of the tree is the framebuffer texture.

[^gpu-texture]: Recall from [Chapter 11](visual-effects.md) that there can be
surfaces that draw into other surfaces, forming a tree. Skia internally does
this sometimes, based on various triggers such as blend modes. The internal
nodes draw into intermediate textures.

The time to run GPU raster is roughly the sum of the time for these four steps.
[^optimize] The total time can be dominated by any of the four steps. The
larger the display list, the longer the upload; the more complexity and variety
of display list commands, the longer the compile; the more surfaces to raster,
the longer the execute; the deeper the the nesting of surfaces in the web page,
the longer the draw. Without care, these steps can sometimes add up to be
longer than the time to just raster on the CPU. All of these slowdown
situations can and do happen in real browsers for various kinds of hard-to-draw
content.

[^optimize]: It's not necessary to compile GPU programs on every raster, so
this part can be optimized. Parts of the other steps can as well, such as
by caching font data in the GPU.

[gpu]: https://en.wikipedia.org/wiki/Graphics_processing_unit

The root Skia surface will need to be connected directly to the screen
framebuffer associated with the SDL window. The incantation for that is:

``` {.python expected=False}
class Browser:
    def __init__(self):
        #. ...
        self.skia_context = skia.GrDirectContext.MakeGL()

        self.root_surface = skia.Surface.MakeFromBackendRenderTarget(
            self.skia_context,
            skia.GrBackendRenderTarget(
                WIDTH, HEIGHT, 0, 0,
                skia.GrGLFramebufferInfo(0, GL.GL_RGBA8)),
                skia.kBottomLeft_GrSurfaceOrigin,
                skia.kRGBA_8888_ColorType, skia.ColorSpace.MakeSRGB())
        assert self.root_surface is not None

```

Note: this code never seems to reference `gl_context` or `sdl_window` directly,
but draws to the window anyway. That's because OpenGL is a strange API that
uses hidden global states; the `MakeGL` Skia method implicitly binds to the
existing GL context.

The `chrome_surface` incantation is a bit different, because it's creating
a GPU texture, but one that is independent of the framebuffer:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.chrome_surface =  skia.Surface.MakeRenderTarget(
                self.skia_context, skia.Budgeted.kNo,
                skia.ImageInfo.MakeN32Premul(WIDTH, CHROME_PX))
        assert self.chrome_surface is not None
```

As compared with Chapter 11 surfaces, this surface is associated explicitly with
the `skia_context` and uses a different color space that is required for GPU
mode. `tab_surface` should get exactly the same treatment (but with different
width and height arguments, of course).

Finally, `draw` is much simpler: `root_surface` need not blit into the
SDL surface, because they share a GPU framebuffer backing. (There are no
changes at all required to raster.) All it has to do is *flush* the Skia
surface (Skia surfaces draw lazily) and call `SDL_GL_SwapWindow` to activate
the new framebuffer (because of OpenGL [double-buffering][double]).

[double]: https://wiki.libsdl.org/SDL_GL_SwapWindow

``` {.python}
class Browser:
    def draw(self):
        canvas = self.root_surface.getCanvas()
        # ...
        chrome_rect = skia.Rect.MakeLTRB(0, 0, WIDTH, CHROME_PX)
        canvas.save()
        canvas.clipRect(chrome_rect)
        self.chrome_surface.draw(canvas, 0, 0)
        canvas.restore()

        self.root_surface.flushAndSubmit()
        sdl2.SDL_GL_SwapWindow(self.sdl_window)
```

Let's go back and test the [counter example](scheduling.md#animating-frames)
from Chapter 12. Without GPU, the results were:

    Time in raster-and-draw on average: 66ms
    Time in render on average: 23ms

Now, with GPU rendering, they are:

    Time in raster-and-draw on average: 24ms
    Time in render on average: 23ms

So GPU acceleration speeds up raster-and-draw by more than 60%. (If you're on a
computer with a non-virtualized GL driver you will probably see even more
speedup than that.)

::: {.further}

A high-speed, reliable and cross-platform GPU raster path in Skia has only
existed for a few years.[^timeline-gpu] In the very early days of Chromium,
there was only CPU raster. Scrolling was implemented much like in the eary
chapters of this book, by re-rastering content. This was deemed acceptable at
the time because computers were much slower than today in general, GPUs much
less reliable, animations much less frequent, and mobile platforms such as
Android and iOS still emerging. (In fact, the first versions of Android
also didn't have GPU acceleration.) The same is generally true of Firefox and
Safari, though Safari was able to accelerate content more easily because it
only targeted the limited number of GPUs supported by macOS and iOS.

[^timeline-gpu]: You can see a timeline [here][rng-gpu].

[rng-gpu]: https://developer.chrome.com/blog/renderingng/#gpu-acceleration-everywhere

There are *many* challenges to implementing GPU accelerated raster, among them
working correctly across many GPU architectures, gracefully falling back to CPU
raster in complex or error scenarios, and finding ways to efficiently GPU 
raster content in difficult situations like anti-aliased & complex shapes.

So while you might think it's odd to wait until Chapter 13 to turn on
GPU acceleration, this also mirrors the evolution timeline of
browsers.

:::

Opacity animations
==================

In Chapter 12 we [implemented](scheduling.md#animating-frames) the
`requestAnimationFrame` API and built a demo that modifies the `innerHTML`
of a DOM element on each frame. That is indeed an animation---a
*JavaScript-driven* animation---but `innerHTML` is generally not how
high-quality animations are done on the web. Instead, it almost always makes
sense to first render some content into layout objects, then apply a DOM
animation to the layout tree by animating CSS properties.

It's straightforward to see how this works for opacity: define some
HTML that you want to animate, then interpolate the `opacity` CSS property in
JavaScript smoothly from one value to another. Here's an example that animates
from 0.999[^why-not-one] to 0.1, over 120 frames (about two seconds), then back
up to 0.999 for 120 more frames, and repeats.

[^why-not-one]: The animation starts below 1 because most real browsers remove
certain animation-related optimizations when opacity is exactly 1. So it's
easier to dig into the performance of this example on a real browser with 0.999
opacity. Starting animations at 0.999 is also a common trick used on web sites
that want to avoid visual popping of the content as it goes in and out of
GPU-accelerated mode. I chose 0.999 because the visual difference from 1.0 is
imperceptible.

The HTML is:

``` {.html file=example-opacity-html}
<div>Test</div>
```

And here is the `animate` implementation for this example:
``` {.javascript file=example-opacity-js}
var frames_remaining = 120;
var go_down = true;
var div = document.querySelectorAll("div")[0];
function animate() {
    var percent_remaining = frames_remaining / 120;
    if (!go_down) percent_remaining = 1 - percent_remaining;
    div.style = "opacity:" +
        (percent_remaining * 0.999 +
            (1 - percent_remaining) * 0.1);
    if (frames_remaining-- == 0) {
        go_down = !go_down
        frames_remaining = 120;
    }
    return true;
}
```

Here's how it renders:

<iframe src="examples/example13-opacity-raf.html"></iframe>
(click [here](examples/example13-opacity-raf.html) to load the example in
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

::: {.further}

Opacity is a special kind of CSS filter. And where it makes sense, other filters
that parameterize on some numeric input (such as [blur]) can also be animated
just as easily. And as we'll see, all of them can be optimized to avoid raster
entirely during the animation.

Likewise, certain paint-only effects such as color and background-color are also
possible to animate, since colors are numeric and can be interpolated. (In that
ase, each color channel is interpolated independently.) These are also
visual effects, but not quite of the same character, because background color
doesn't apply a visual effect to a whole DOM subtree. It's instead a display
list parameter that happens not to cause layout, but generally still
needs raster. This makes them harder to optimize.

:::

[blur]: https://developer.mozilla.org/en-US/docs/Web/CSS/filter-function/blur

Width/height animations
=======================

What about layout-inducing DOM animations? As I explained earlier in the
chapter, these animations are usually not advisable because of the way text
layout jumps, but do make sense for some input-based resize animations---think
browser window resizing, or resizing the input area in a text input field, via
a mouse gesture. But as always, it's a good exercise to try it out and see how
it looks and performs for yourself. Let's do that.

At the moment, our browser doesn't support any layout-inducing CSS properties
that would be useful to animate, so let's add support for `width` and
`height`, then animate them. These CSS properties do pretty much what they
say: force the width or height of a layout object to be the specified value in
pixels, as opposed to the default behavior that sizes an element to contain
block and inline descendants. If as a result the descendants don't fit, they
will *overflow* in a natural way. This usually means overflowing the bottom
edge of the block ancestor, because we'll use `width` to determine the area
for line breaking.[^overflow]

[^overflow]: By default, overflowing content draws outside the bounds of
the parent layout object. We discussed overflow to some extent in
[Chapter 11](visual-effects.md#clipping-and-masking), and implemented
`overflow:clip`, which instead clips the overflowing content at the box
boundary. Other values include `scroll`, which clips it but allows the user
to see it via scrolling. And if scroll is specified in the x direction, the
descendant content will lay out as it if has an infinite width. Extra-long
words can also cause horizontal overflow.

Implementing `width` and `height` turns out to be pretty easy. Instead of
setting the width of a layout object to the widest it can be before recursing,
use the specified width instead. And likewise for `height`. Then, descendants
will use that width for their sizing automatically.

Start by implementing a `style_length` helper method that applies a
restricted length (either in the horizontal or vertical dimension) if it's
specified in the object's style. For example,

	style_length(node, "width", 300)

would return 300 if the `width` CSS property was not set on `node`,
and the `width` value otherwise.^[Interesting side note: while `width`
values can be specified as floating-point numbers, computer monitors
have discrete pixels, so real browsers need to convert these values to
integers. This process is called pixel-snapping, and in real browsers
it's pretty complicated. [This article][pixel-canvas] touches on some
of the complexities as they apply to canvases, but it's just as
complex for DOM elements. For example, if two block elements touch and
have fractional widths, it's important to round in such a way that
there is not a visual gap introduced between them.]

[pixel-canvas]: https://web.dev/device-pixel-content-box/#pixel-snapping

``` {.python}
def style_length(node, style_name, default_value):
    style_val = node.style.get(style_name)
    return float(style_val[:-2]) if style_val else default_value
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
            sum([line.height for line in self.children]))
```

Here is a simple animation of `width`. As the width of the `div` animates from
`400px` to `100px`, its height will automatically increase to contain the text
as it flows into multiple lines.^[And if automatic increase was not desired,
`height` could be specified to a fixed value. But that would of course cause
overflow, which needs to be dealt with in one way or another.] Notice how the
text flows during the animation. It makes sense when resizing, but is otherwise
confusing and jarring to look at, not to mention hard to read.

``` {.html file=example-width-html}
<div style="background-color:lightblue;width:100px">
	This is a test line of text for a width animation.
</div>
```
<iframe src="examples/example13-width-raf.html" style="width: 450px"></iframe>
(click [here](examples/example13-width-raf.html) to load the example in
your browser)

And `animate` looks like this (almost the same as the opacity example!):
``` {.javascript file=example-width-js}
var frames_remaining = 120;
var go_down = true;
var div = document.querySelectorAll("div")[0];
function animate() {
    var percent_remaining = frames_remaining / 120;
    if (!go_down) percent_remaining = 1 - percent_remaining;
    div.style = "background-color:lightblue;width:" +
        (percent_remaining * 400 +
        (1 - percent_remaining) * 100) + "px";
    if (frames_remaining-- == 0) {
        frames_remaining = 120;
        go_down = !go_down;
    }
    return true;
}
```

::: {.further}

Almost any CSS property with some sort of interpolable number can be animated in
a similar way. Here is a [list][anim-prop] of all of them. Most of them
are layout inducing, including some interesting ones that we *could* have
animated without introducing `width` and `height`, such as `font-size`.

[anim-prop]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_animated_properties

:::

CSS transitions
===============

But why do we need JavaScript just to smoothly interpolate `opacity` or `width`?
Well, that's what [CSS transitions][css-transitions] are for. But they're not
just a convenience for developers: they also allow the browser to optimize
performance. Animating `opacity`, for example, doesn't require re-running
layout, but because JavaScript is setting the `style` property, it can be
hard for the browser to figure that out. CSS transitions make it easy to
express an animation in a way browsers can easily
optimize.[^browser-detect-diff]

[^browser-detect-diff]: When DOM styles change, real browsers do in fact attempt
to figure out what changed and minimize re-computation. Chromium, for example,
has a bunch of code that tries to [diff][chromium-diff] the old and new styles,
and reduce work in situations such as changing only opacity. But this approach
will always be somewhat brittle and incomplete, because the browser has to
trade off time spent diffing two styles with the rendering work avoided and
added code complexity.

[chromium-diff]: https://source.chromium.org/chromium/chromium/src/+/main:third_party/blink/renderer/core/style/style_difference.h

The `transition` CSS property looks like this:

[css-transitions]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Transitions/Using_CSS_transitions

	transition: opacity 2s,width 2s;

This means that, whenever the `opacity` or `width` properties of the element
change---for any reason, including mutating its style attribute or loading a
style sheet---then the browser should smoothly interpolate between the old and
new values, in basically the same way the `requestAnimationFrame` loop did it.
This is much more convenient for website authors than writing a bunch of
JavaScript, and also doesn't force them to account for each and every way in
which the styles can change.

This is the opacity example, but using a CSS transition and JavaScript to
trigger it once every 2 seconds:

<iframe src="examples/example13-opacity-transition.html"></iframe>
(click [here](examples/example13-opacity-transition.html) to load the example in
your browser; [here](examples/example13-width-transition.html) is the width
animation example)

Implement this CSS property. The strategy will be almost the same as
in JavaScript: define an object on which we can call `animate` on each
animation frame, causing the animation to advance one frame. Multiple
elements can animate at a time, so let's store animations in an
`animations` dictionary on each node, keyed by the property being
animated:[^delete-complicated]

[^delete-complicated]: For simplicity, this code leaves animations in
    the `animations` dictionary even when they're done animating.
    Removing them would be necessary, however, for really long-running
    tabs where just looping over all the already-completed animations
    can take a while.

``` {.python}
class Text:
    def __init__(self, text, parent):
        # ...
        self.style = {}
        self.animations = {}

class Element:
    def __init__(self, tag, attributes, parent):
        # ...
        self.style = {}
        self.animations = {}
```

These animation objects will just record the start and and value they
are animating between, and then keep track of how many frames have
passed and what the current value should be. For example, the
`NumericAnimation` class, for animating properties like `opacity` and
`width`, is constructed from an old value, a new value, and a length
for the animation in frames:

``` {.python}
class NumericAnimation:
    def __init__(self, old_value, new_value, num_frames):
        self.is_px = old_value.endswith("px")
        if self.is_px:
            self.old_value = float(old_value[:-2])
            self.new_value = float(new_value[:-2])
        else:
            self.old_value = float(old_value)
            self.new_value = float(new_value)
        self.num_frames = num_frames
```

Note the little quirk that `width` is given in pixels while `opacity`
is given without units,[^more-units] so `NumericAnimation` looks at
the old value to determine the unit to use, and then stores the old
and new values parsed.

[^more-units]: In real browsers, there are a [lot more][units] units
to contend with. And other constraints, too---like the fact that
opacity should be a value between 0 and 1.

[units]: https://developer.mozilla.org/en-US/docs/Learn/CSS/Building_blocks/Values_and_units

Now add a frame count and an `animate` method that increments it:

``` {.python}
class NumericAnimation:
    def __init__(self, old_value, new_value, num_frames):
        # ...
        self.frame_count = 1

    def animate(self):
        self.frame_count += 1
        if self.frame_count >= self.num_frames: return
```

If the animation is animating, we'll need to compute the new value of
the property.[^animation-curve] Let's return that from the `animate`
method:[^precompute]

[^animation-curve]: Note that this class implements a linear animation
interpretation (or *easing function*). By default, real browsers use a
non-linear easing function, which looks better, so the demos from this
chapter will not look quite the same in your browser.

[^precompute]: Here I've chosen to compute `change_per_frame` in the
constructor. Of course, this is a very simple calculation and it
frankly doesn't matter much where exactly we do it, but if the
animation were more complex, we could precompute some information in
the constructor for use later.

``` {.python}
class NumericAnimation:
    def __init__(self, old_value, new_value, num_frames):
        # ...
        total_change = self.new_value - self.old_value
        self.change_per_frame = total_change / num_frames

    def animate(self):
        # ...
        current_value = self.old_value + \
            self.change_per_frame * self.frame_count
        if self.is_px:
            return "{}px".format(current_value)
        else:
            return "{}".format(current_value)
```

We're going to want to create these animation objects every time a
style value changes. We can do that in `style` by diffing the old and
the new styles of each node:

``` {.python}
def style(node, rules):
    old_style = node.style

    # ...

    if old_style:
        transitions = diff_styles(old_style, node.style)
```

This `diff_style` function is going to look for all properties that
are mentioned in the `transition` property and are different between
the old and the new style. So first, we're going to have to parse the
`transition` value:

``` {.python}
def parse_transition(value):
    properties = {}
    if not value: return properties
    for item in value.split(","):
        property, duration = item.split(" ", 1)
        frames = float(duration[:-1]) / REFRESH_RATE_SEC
        properties[property] = frames
    return properties
```

Note that this returns a dictionary mapping property names to
transition durations, measured in frames.

Next, `diff_style` will loop through all of the properties mentioned
in `transition` and see which ones changed. It returns a dictionary
containing only the transitioning properties, and mapping each such
property to its old value, new value, and duration (again in frames):

``` {.python}
def diff_styles(old_style, new_style):
    old_transitions = parse_transition(old_style.get("transition"))
    new_transitions = parse_transition(new_style.get("transition"))

    transitions = {}
    for property in old_transitions:
        if property not in new_transitions: continue
        num_frames = new_transitions[property]
        if property not in old_style: continue
        if property not in new_style: continue
        old_value = old_style[property]
        new_value = new_style[property]
        if old_value == new_value: continue
        transitions[property] = (old_value, new_value, num_frames)

    return transitions
```

Note that this code has to deal with subtleties like the `transition`
property being added or removed, or properties being removed instead
of changing values. 

Now, inside `style`, we're going to want to create a new animation
object for each transitioning property. Let's allow animating just
`width` and `opacity` for now; we can expand this to more properties
by writing new animation types:

``` {.python}
ANIMATED_PROPERTIES = {
    "width": NumericAnimation,
    "opacity": NumericAnimation,
}
```

Now `style` can animate any changed properties listed in
`ANIMATED_PROPERTIES`:

``` {.python}
def style(node, rules):
    if old_style:
        transitions = diff_styles(old_style, node.style)
        for property, (old_value, new_value, num_frames) in transitions.items():
            if property in ANIMATED_PROPERTIES:
                AnimationClass = ANIMATED_PROPERTIES[property]
                animation = AnimationClass(old_value, new_value, num_frames)
                node.animations[property] = animation
                node.style[property] = old_value
```

Now, any time a property listed in `transition` changes its value,
we'll create an animation and get ready to run it. Note that the
animation will start running in the next frame; until then, we want it to
show the old value.

So, let's run the animations! Basically, every frame, we're going to
want to find all the active animations on the page and call `animate`
on them. Since these animations are a variation of
JavaScript animations using `requestAnimationFrame`, let's run
animations right after handling those callbacks:

``` {.python}
class Tab:
    def run_animation_frame(self, scroll):
        # ...
        self.js.interp.evaljs("__runRAFHandlers()")
        for node in tree_to_list(self.nodes, []):
            for (property_name, animation) in node.animations.items():
                # ...
        # ...
```

The body of this loop needs to do two things. First, it needs to call
the animation's `animate` method and save the new value to the node's
`style`. Second, since that changes the web page, we need to set a
dirty bit; Recall that `render()` exits early if `needs_render` isn't
set, so that "dirty bit" is supposed to be set if there's rendering
work to do. When an animation is active, there is.

But it's not as simple as just setting `needs_render` any time an
animation is active, however. Setting `needs_render` means re-runs
`style`, which would notice that the animation changed a property
value and start a *new* animation! During an animation, we want to run
`layout` and `paint`, but we *don't* want to run `style`:[^even-more]

[^even-more]: While a real browser definitely has an analog of the
`needs_layout` and `needs_paint` flags, our fix for restarting
animations doesn't handle a bunch of edge cases. For example, if a
different style property than the one being animatied, the browser
shouldn't re-start the animation. Real browsers will store multiple
copies of the style---the computed style and the animated style---to
solve issues like this.

``` {.python}
class Tab:
    def run_animation_frame(self, scroll):
        for node in tree_to_list(self.nodes, []):
            for (property_name, animation) in node.animations.items():
                value = animation.animate()
                if value:
                    node.style[property_name] = value
                    self.set_needs_layout()
```

To support `set_needs_layout`, we've got to replace the single
`needs_render` flag with three flags: `needs_style`, `needs_layout`,
and `needs_paint`. The old `set_needs_render` would set all three:

``` {.python}
class Tab:
    def __init__(self, browser):
        # ...
        self.needs_style = False
        self.needs_layout = False
        self.needs_paint = False
        # ...

    def set_needs_render(self):
        self.needs_style = True
        self.browser.set_needs_animation_frame(self)
```

But now we can write a `set_needs_layout` method that sets flags for
the `layout` and `paint` phases, but not the `style` phase:

``` {.python}
class Tab:
    def set_needs_layout(self):
        self.needs_layout = True
        self.browser.set_needs_animation_frame(self)
```

Now `render` can check one flag for each phase instead of checking
`needs_render` at the start:

``` {.python}
class Tab:
    def render(self):
        self.measure_render.start()

        if self.needs_style:
            # ...
            self.needs_layout = True
            self.needs_style = False

        if self.needs_layout:
            # ...
            self.needs_paint = True
            self.needs_layout = False
    
        if self.needs_paint:
            # ...
            self.needs_paint = False

        self.measure_render.stop()
```

This *does* obsolete our timer for how long rendering takes. Rendering
now does different work on different frames, so measuring rendering
overall doesn't really make sense! I'm going to leave this be and just
not look at the rendering measures anymore, but the best fix would be
to have three timers for the three phases of `render`.

Well---with all that done, our browser now supports animations with
just CSS! That's much more convenient for website authors, which is
great. But it's not yet that much faster than a JavaScript-based
animation. That's because the JavaScript runs really quickly, while
layout and paint still consume a large amount of time (recall our
[profiling in Chapter 12][profiling]). So let's turn our attention to
dramatically speeding up rendering for animations.

[profiling]: http://localhost:8001/scheduling.html#profiling-rendering

::: {.further}

CSS transitions are great for adding animations triggered by DOM updates from
JavaScript. But what about animations that are just part of a page's UI, and
not connected to a visual transition? (For example, a pulse opacity
animation on a button or cursor.) In fact, the opacity and width animations
we've been working with are not really connected to DOM transitions at all, and
are instead infinitely repeating animations. This can be expressed directly in
CSS without any JavaScript via a [CSS animation][css-animations].

[css-animations]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Animations/Using_CSS_animations

You can see the CSS animation variant of the opacity demo
[here](examples/example13-opacity-animation.html), and width one
[here](examples/example13-width-animation.html). Implementing this feature
requires parsing a new `@keyframes` syntax and the `animation` CSS property.
Notice how `@keyframes` defines the start and end point declaratively, which
allows us to make the animation alternate infinitely
because a reverse is just going backward among the keyframes.

There is also the [Web Animations API][web-animations], which allows creation
and management of animations via JavaScript.

[web-animations]: https://developer.mozilla.org/en-US/docs/Web/API/Web_Animations_API
:::

Compositing
===========

*Compositing* is a technique to avoid raster during visual effect animations by
 caching raster results in GPU textures. These textures are re-used during
 the animation, so only `draw` is needed for each
 animation frame (with different parameters each time of course).[^compositing-def]

[^compositing-def]: The term [*compositing*][compositing] originally meant to
combine multiple images together into a final output. As it relates to
browsers, it usually means the performance optimization technique described
here, but the term is often overloaded to refer to OS and browser-level
compositing, and multi-threaded rendering.

[compositing]: https://en.wikipedia.org/wiki/Compositing

Let's consider the opacity animation example from this chapter. When we're
animating, opacity is changing, but the "Test" text underneath it is not. So
let's stop re-rastering that content on every frame of the animation, and
instead cache it in a GPU texture. This should directly reduce browser thread
work, because no raster work will be needed on each animation frame.

Below is the opacity animation with a red border "around" the surface that we
want to cache. Notice how it's sized to the width and height of the `<div>`,
which is as wide as the viewport and as tall as the text "Test".[^chrome] That's
because the surface will cache the raster output of the `DrawText` command,
and those are its bounds.

 <iframe src="http://localhost:8001/examples/example13-opacity-transition-borders.html">
 </iframe>

[^chrome]: You can see the same thing if you load the example when running
Chrome with the `--show-composited-layer-borders` command-line flag; there
is also a DevTools feature for it.

As I explained in [Chapter 11](visual-effects.md#browser-compositing), Skia
sometimes caches surfaces internally. So you might think that Skia has a way to
say "please cache this surface". And there is---keep around a `skia.Surface`
object across multiple raster-and-draw executions and use the `draw` method on
the surface to draw it into another canvas.^[Skia will keep alive the rastered
content associated with a `Surface` object until it's garbage collected.] In
other words, we'll need to do the caching ourselves. This feature is not
built into Skia itself in a trivial-to-use form.

Let's start digging into an implementation of compositing. The
plan is to cache the "contents" of an animating visual effect in a new
`skia.Surface` and store it somewhere. But what does "contents" mean exactly?
If opacity is animating, which parts of the web page should we cache in the
surface? To answer that, let's revisit the structure of our display
lists.

It'll be helpful to be able to print out the (recursive, tree-like) display list
in a useful form.[^debug] Add a base class called `DisplayItem` and make all
display list commands inherit from it, and move the `cmds` field to that class
(or pass nothing if they don't have any, like `DrawText`); here's `SaveLayer`
for example:

[^debug]: This code will also be very useful to you while debugging your
compositing implementation.

``` {.python expected=False}
class SaveLayer:
    def __init__(self, sk_paint, node, cmds,
        should_save=True, should_paint_cmds=True):
        # ...
        super().__init__(cmds=cmds, is_noop=not should_save)
```

Then add a `repr_recursive` method to `DisplayItem` for debugging. Also add an
`is_noop` parameter that indicates whether the `DisplayItem` has no
effect.^[Recall that most of the time, the visual effect `DisplayItem`s
generated by `paint_visual_effects` don't do anything, because most elements
don't have a transform, opacity or blend mode.] That way, printing out the
display list will skip irrelevant visual effects.

``` {.python expected=False}
class DisplayItem:
    def __init__(cmds=None, is_noop=False):
        self.cmds = cmds
        self.noop = is_noop

    def is_noop():
        return self.noop;

    def repr_recursive(self, indent=0):
        inner = ""
        if self.is_noop():
            if self.cmds:
                for cmd in self.cmds:
                   inner += cmd.repr_recursive(indent)
            return inner
        else:
            if self.cmds:
                for cmd in self.cmds:
                    inner += cmd.repr_recursive(indent + 2)
            return ("{indentation}{repr}:\n{inner} ").format(
                indentation=" " * indent,
                repr=self.__repr__(),
                inner=inner)
```

This lets you print out the display list while you're debugging:

``` {.python expected=False}
class Tab:
    def render(self):
        # ...
        for item in self.display_list:
            print(item.repr_recursive())
```

When run on the [opacity transition
example](examples/example13-opacity-transition.html) before the animation has
begun, it should print something like:

    SaveLayer(alpha=0.999): bounds=Rect(13, 18, 787, 40.3438)
        DrawText(text=Test): bounds=Rect(13, 21.6211, 44, 39.4961)

It seems logical to make a surface for the contents of the opacity `SaveLayer`,
in this case containing only a `DrawText`. In more complicated examples, it
could of course have any number of display list commands.[^command-note]

[^command-note]: Note that this is *not* the same as "cache the display list for
a DOM element subtree". To see why, consider that a single DOM element can
result in more than one `SaveLayer`, such as when it has both opacity *and* a
transform.

Putting the `DrawText` into its own surface sounds simple enough: just make a
surface and raster that sub-piece of the display list into it, then draw that
surface into its "parent" surface. In this example, the resulting code to draw
the child surface should ultimately boil down to something like this:

    opacity_surface = skia.Surface(...)
    draw_text.execute(opacity_surface.getCanvas())
    tab_canvas.saveLayer(paint=skia.Paint(AlphaF=0.999))
    opacity_surface.draw(tab_canvas, text_offset_x, text_offset_y)
    tab_canvas.restore()

Let's unpack what is going on in this code. First, raster `opacity_surface`.
Then create a new conceptual
"surface" on the Skia stack via `saveLayer`, draw `opacity_surface`,
and finally call `restore`. Observe how this is
*exactly* the way we described how it conceptually works *within* Skia
in [Chapter 11](visual-effects.html#blending-and-stacking). The only
difference is that here it's explicit that there is a `skia.Surface` between
the `saveLayer` and the `restore`.
Note also how we're using the `draw` method on `skia.Surface`, the very same
method we already use in `Browser.draw` to draw the surface to the screen.
In essence, we've moved a `saveLayer` command from the `raster` stage
to the `draw` stage of the pipeline.

::: {.further}

If you look closely at the example in this section, you'll see that the
`DrawText` command itself only has a rect with a width of 33 pixels, not the
width of the viewport. On the other hand, the `SaveLayer` has a width of 774
pixels. The reason they differ is that the text is only 33 pixels wide, but
the block element that contains it is 774 pixels wide, and the opacity is placed
on the block element, not the text.

So does the composited surface need to be 33 pixels wide or 774? In practice you
could implement either. The algorithm presented in this chapter actually
chooses 33 pixels, but real browsers sometimes choose 774 depending on their
algorithm. Also note that if there was any kind of paint command associated
with the block element itself, such as a background color, then the surface
would definitely have to be 774 pixels wide. Likewise, if there were multiple
inline children, the union of their bounds would contribute to the surface size.

:::

Compositing algorithms
======================

The most complex part of compositing and draw is dealing with the hierarchical
nature of the display list. To deal with this, you might try this algoritihm:
mark animating visual effects as composited, and raster a `skia.Surface` for
everything below it. This works fine for the single `DrawText` example we've
been looking at, but starts to get very complicated when you consider nested
surfaces. For example, multiple nested DOM nodes could be simultaneously
animating opacity, and we can't put the same subtree in two different surfaces.
Do we instead raster some of it in one surface and some in another? Where do we
put the combined result with all the opacities applied, or the first applied
but not yet the second?^[We'll cover another complication---overlap
testing---later in the chapter; see also the Go Further block at the end of
this section for discussion of even more complications.]

To handle all this complexity, let's break the problem down into two
pieces: *compositing* the display list into a linear list of `skia.Surface`s,
and *drawing* those surfaces to the screen. Compositing is in charge of finding
non-animating subtrees of the display list and putting them into groups that
raster together. Drawing  is in charge of re-creating a tree hierarchy that
mirrors the hierarchy of animating visual effects in the display list.
[^temp-surface]

[^temp-surface]: Nested visual effects will end up causing the need for
temporary GPU textures to be created during draw, in order to make sure visual
effects apply atomically to all the content within them. Recall that we
discussed this issue in [Chapter 11][stack-cont] in the context of stacking
contexts. See the Go Further block at the end of this section for additional
discussion.

[stack-cont]: visual-effects.md#blending-and-stacking

In fact, compositing can focus only on the leaves of this display list, which
we'll call *paint commands*.[^drawtext] These are exactly the same display list
commands that we had *before* Chapter 11 added visual effects. You can also
imagine these paint commands as being in a flat list---the output of
enumerating them in paint order. From this point of view, the visual
effects "merely" show how to add visual flourish to the paint commands.

The distinction between compositing and drawing is analogous to how you can
think of painting and visual effects as different but complementary: painting
is drawing some pixels to a canvas, and visual effects apply a group operation
to them; in the same way, compositing rasters some pixels and drawing applies
group operations.^[And just as visual effects in our browser (except for
scrolling) actually happen during paint at the moment, non-animating visual
effects will end up happening during raster and not draw. Either way way is
correct; choosing one or the other is just a matter of which has better
performance.]

[^drawtext]: `DrawText`, `DrawRect` etc---the display list commands that
don't have recursive children in `cmds`.

Notice that each paint command can be (individually) drawn to the screen by
executing it and the series of *ancestor [visual] effects* on it. Thus the
tuple (paint command, ancestor effects) suffices to describe that paint command
in isolation. This tuple is called a *paint chunk*. Here is how to generate all
the paint chunks from a display list:

``` {.python}
def display_list_to_paint_chunks(
    display_list, ancestor_effects, chunks):
    for display_item in display_list:
        if display_item.get_cmds() != None:
            display_list_to_paint_chunks(
                display_item.get_cmds(),
                ancestor_effects + [display_item], chunks)
        else:
            chunks.append((display_item, ancestor_effects))
```

In the `DrawText` example, there is one paint chunk with one ancestor effect
(opacity):

    (DrawText("Text"), [SaveLayer(opacity=0.999)])


When combined together, multiple paint chunks form a *composited layer*,
represented by the `CompositedLayer` class. This class will own a
`skia.Surface` that rasters its content, and also know how to draw
the result to the screen by applying an appropriate sequence of visual effects.

Two paint chunks in the flat list can be put into the same composited layer if
they have the exact same set of animating ancestor effects. (Otherwise the
animations would end up applying to the wrong paint commands.)

To satisfy this constraint, we *could* just put each paint command in its own
composited layer. But of course, for examples more complex than just one
`DrawText` that would result in a huge number of surfaces, and most likely
exhaust the computer's GPU memory. So the goal of the *compositing algorithm*
is to come up with a way to pack paint chunks into only a small number of
composited layers.^[There are many possible compositing algorithms, with their
own tradeoffs of memory, time and code complexity. I'll present a simplified
version of the one used by Chromium.]

Below is the algorithm we'll use; as you can see it's not very complicated. It
loops over the list of paint chunks; for each paint chunk it tries to add it to
an existing `CompositedLayer` by walking *backwards* through the
`CompositedLayer` list.[^why-backwards] If one is found, the paint chunk is
added to it; if not, a new `CompositedLayer` is added with that paint chunk to
start. The `can_merge` method on a `CompositedLayer` checks compatibility of
the paint chunk's animating ancestor effects with the ones already on it.

[^why-backwards]: Backwards, because we can't draw things in the wrong
order. Later items in the display list have to draw later.

``` {.python expected=False}
class Browser:
    def __init__(self):
        # ...
        self.composited_layers = []

    def composite(self):
        self.composited_layers = []
        chunks = []
        display_list_to_paint_chunks(
            self.active_tab_display_list, [], chunks)
        for (display_item, ancestor_effects) in chunks:
            placed = False
            for layer in reversed(composited_layers):
                if layer.can_merge(display_item, ancestor_effects):
                    layer.add_display_item(
                        display_item, ancestor_effects)
                    placed = True
                    break
            if not placed:
                layer = CompositedLayer(skia_context)
                layer.add_display_item(display_item, ancestor_effects)
                composited_layers.append(layer)
```

Once there is a list of `CompositedLayer`s, rastering the `CompositedLayer`s
will be look like this:

``` {.python}
    def raster_tab(self):
        for composited_layer in self.composited_layers:
            composited_layer.raster()
```

And drawing them to the screen will be like this:[^draw-incorrect]

[^draw-incorrect]: It's worth calling out once again that this is not
correct in the presence of nested visual effects; see the Go Further section.
I've left fixing the problem described there to an exercise.

``` {.python}
    def draw(self):
        canvas = self.root_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        
        draw_offset=(0, CHROME_PX - self.scroll)
        if self.composited_layers:
            for composited_layer in self.composited_layers:
                composited_layer.draw(canvas, draw_offset)
```

This is the overall structure. Now I'll show how to implement `can_merge`,
`raster` and `draw` on a `CompositedLayer`.

::: {.further}

As discussed earlier, the implementation of `Browser.draw` in this section is
incorrect for the case of nested visual effects, because it's not correct to
draw every paint chunk individually or even in groups; visual effects have to
apply atomically to all the content at once. To fix it requires determining the
necessary "draw hierarchy" of `CompositedLayer`s into a tree based on their
visual effect nesting, and allocating temporary intermediate GPU textures
called *render surfaces* for each internal node of this tree. The render
surface is a place to put the inputs to an (atomically-applied) visual effect.
Render surface textures are generally not cached from frame to frame.

A naive implementation of this tree (allocating one node for each visual effect)
is not too hard to implement, but each additional render surface requires a
*lot* more memory and slows down draw a bit more. So
 real browsers analyze the visual effect tree to determine which ones really
 need render surfaces, and which don't. Opacity, for example, often doesn't
 need a render surface, but opacity with at least two "descendant"
 `CompositedLayer`s does.[^only-overlapping] The reason is that opacity has to
 be applied *atomically* to all of the content under it; if it was applied
 separately to each of the child `CompositedLayer`s, the blending result on the
 screen would be potentially incorrect.

You might think that all this means I chose badly with my flattening
algorithm in the first place, but that is not the case. Render surface
optimizations are just as necessary (and complicated to get right!) even with
a "layer tree" approach, because it's so important to optimize GPU memory.

[^only-overlapping]: Actually, only if there are at least two children *and*
some of them overlap each other visually. Can you see why we can avoid the
render surface for opacity if there is no overlap?

For more details and information on how Chromium implements these concepts see
[here][renderingng-dl] and [here][rendersurface]; other browsers do something
similar.

Chromium's implementation of the "visual effect nesting" data structure is
called [property trees][prop-trees]. The name is plural because there is more
than one tree, due to the complex [containing block][cb] structure of scrolling
and clipping.

[cb]: https://developer.mozilla.org/en-US/docs/Web/CSS/Containing_block

[renderingng-dl]: https://developer.chrome.com/blog/renderingng-data-structures/#display-lists-and-paint-chunks
[rendersurface]: https://developer.chrome.com/blog/renderingng-data-structures/#compositor-frames-surfaces-render-surfaces-and-gpu-texture-tiles
[prop-trees]: https://developer.chrome.com/blog/renderingng-data-structures/#property-trees

:::

Composited display items
========================

Before getting to finishing off `CompositedLayer`, let's add some more features
to display items to help then support compositing.

The first thing we'll need is a way to signal that a visual effect "needs
compositing", meaning that it may be animating and so its contents should be
cached in a GPU texture. Indicate that with a new `needs_compositing` method on
`DisplayItem`. As a simple heuristic, we'll always composite `SaveLayer`s
(but only when they actually do something that isn't a no-op), regardless of
whether they are animating.

``` {.python expected=False}
class DisplayItem:
    def needs_compositing(self):
        return not self.is_noop() and type(self) is SaveLayer
```

And while we're at it, add another `DisplayItem` constructor parameter
indicating the `node` that the `DisplayItem` belongs to (the one that painted
it); this will be useful when keeping track of mappings between `DisplayItem`s
and GPU textures.[^cache-key]

[^cache-key]: Remember that these compositing GPU textures are simply a form of
cache, and every cache needs a stable cache key to be useful.

``` {.python expected=False}
class DisplayItem:
    def __init__(self, cmds=None, is_noop=False, node=None):
        # ...
        self.node = node
```

Next we need a `draw` method. This will be used to execute the visual effect in
either draw or raster, depending on the results of the compositing algorithm.
That's why it has an `op` function parameter.

For paint commands, this will be the same as `execute`, so just rename it
and add the (unused) `op` parameter:

``` {.python}
class DrawText(DisplayItem):
    def draw(self, canvas, op):
        draw_text(canvas, self.left, self.top,
            self.text, self.font, self.color)
```

For other commands, it should execute the command, but in place of recursing
it should call `op`:

``` {.python}
class SaveLayer(DisplayItem):
    # ...
    def draw(self, canvas, op):
        if not self.is_noop():
            canvas.saveLayer(paint=self.sk_paint)
        if self.should_paint_cmds:
            op()
        if not self.is_noop():
            canvas.restore()
```

Then we can redefine `execute` in terms of `draw` in `DisplayItem`. In this
case, the `op` performs recursive raster; later on we'll use it to draw a child
surface.

``` {.python}
class DisplayItem:
    def execute(self, canvas):
        def op():
            assert self.cmds
            for cmd in self.get_cmds():
                cmd.execute(canvas)
        self.draw(canvas, op)
```

The paint command subclasses like `DrawText` already define `execute`, which
will override this definition.

Finally, we'll need to be able to get the *composited bounds* of a
`DisplayItem`. This is necessary to figure out the size of a `skia.Surface` that
contains the item.

A display item's composited bounds is the union of its painting rectangle and
all descendants that are not themselves composited. Computing composited bounds
is pretty easy---there is already a `rect` field indicating the bounds, stored
on the various subclasses. So just pass them to the superclass instead and
define `composited_bounds` there:

``` {.python}
class DisplayItem:
    def __init__(self, rect, cmds=None, is_noop=False, node=None):
        self.rect = rect
    # ...
    def composited_bounds(self):
        rect = skia.Rect.MakeEmpty()
        self.composited_bounds_internal(rect)
        return rect

    def composited_bounds_internal(self, rect):
        rect.join(self.rect)
        if self.cmds:
            for cmd in self.cmds:
                if not cmd.needs_compositing():
                    cmd.composited_bounds_internal(rect)
```

The rect passed is the usual one; here's `DrawText`:

``` {.python}
class DrawText(DisplayItem):
    def __init__(self, x1, y1, text, font, color):
        # ...
        super().__init__(
            rect=skia.Rect.MakeLTRB(x1, y1, self.right, self.bottom))
```

The other classes are basically the same, including visual effects.

::: {.further}

Mostly for simplicity, our browser composites `SaveLayer` visual effects,
regardless of whether they are animating. But in fact, there are some good
reasons to always composite certain visual effects.

First, we'll be able to start the animation quicker, since raster won't have to
happen first. That's because whenever compositing reasons change, the browser
has to re-do compositing and re-raster the new surfaces.

Second, compositing sometimes has visual side-effects. Ideally, composited
textures would look exactly the same on the screen as non-composited ones. But
due to the details of pixel-sensitive raster technologies like
[sub-pixel rendering][subpixel], image resize filter algorithms, blending and
anti-aliasing, this isn't always possible. For example, it's common to have
subtle color differences in some pixels due to floating-point precision
differences. "Pre-compositing" the content avoids visual jumps on the page when
compositing starts.

Real browsers support the [`will-change`][will-change] CSS property for the
purpose of signaling pre-compositing.

[subpixel]: https://en.wikipedia.org/wiki/Subpixel_rendering
[will-change]: https://developer.mozilla.org/en-US/docs/Web/CSS/will-change

:::

Composited Layers
=================

We're now ready to implement the `CompositedLayer` class. Start by defining its
member variables: a Skia context, surface, list of paint chunks,
and the *composited ancestor index*.

``` {.python}
class CompositedLayer:
    def __init__(self, skia_context):
        self.skia_context = skia_context
        self.surface = None
        self.paint_chunks = []
        self.composited_ancestor_index = -1
```

Only paint chunks that have the same *nearest composited visual effect ancestor*
will be allowed to be in the same `CompositedLayer`.[^simpler] The composited
ancestor index is the index into the top-down list of ancestor effects
referring to this nearest ancestor. (If there is no composited ancestor, the
index is -1). Here's how to compute it it. Note how we are walking *up* the
display list tree (and therefore implicitly up the DOM tree also) via a
reversed iteration:

``` {.python}
def composited_ancestor_index(ancestor_effects):
    count = len(ancestor_effects) - 1
    for ancestor_item in reversed(ancestor_effects):
        if ancestor_item.needs_compositing():
            return count
            break
        count -= 1
    return -1
```

So all paint chunks in the same `CompositedLayer` will share the same composited
ancestor index. However, they need not have exactly the same ancestor effects
array---there could be additional non-composited visual effects at the bottom.

[^simpler]: Intuitively, this just means "part of the same composited
animation".

The `CompositedLayer` class will have the following methods:

* `can_merge`: returns whether the given paint chunk is compatible with being
  drawn into the same `CompositedLayer` as the existing ones. This will be true
  if they have the same nearest composited ancestor (or both have none).
 
``` {.python}
    def can_merge(self, display_item, ancestor_effects):
        if len(self.paint_chunks) == 0:
            return True
        (item, self_ancestor_effects) = self.paint_chunks[0]
        other_composited_ancestor_index = \
            composited_ancestor_index(ancestor_effects)
        if self.composited_ancestor_index != \
            other_composited_ancestor_index:
            return False
        if self.composited_ancestor_index == -1:
            return True
        return self_ancestor_effects[
            self.composited_ancestor_index] == \
            ancestor_effects[
                other_composited_ancestor_index]
```

* `add_paint_chunk`: adds a new paint chunk to the `CompositedLayer`. The first
  one being added will initialize its `composited_ancestor_index`.

``` {.python}
class CompositedLayer:
    # ...
    def add_paint_chunk(self, display_item, ancestor_effects):
        assert self.can_merge(display_item, ancestor_effects)
        if len(self.paint_chunks) == 0:
            self.composited_ancestor_index = \
            composited_ancestor_index(ancestor_effects)
        self.paint_chunks.append((display_item, ancestor_effects))
```

* `composited_bounds`: returns the union of the composited bounds of all
  paint chunks. The composited bounds of a paint chunk is its display item's
  composited bounds.

``` {.python}
class CompositedLayer:
    # ...
    def composited_bounds(self):
        retval = skia.Rect.MakeEmpty()
        for (item, ancestor_effects) in self.paint_chunks:
            retval.join(item.composited_bounds())
        return retval
```

* `raster`: rasters the chunks into `self.surface`. When rastering, we first
  translate by the `top` and `left` of the composited bounds. That's because we
  should allocate a surface exactly sized to the width and height of the
  bounds; its top/left is just a positioning offset.^[This will be taken into
  account in `draw` as well; see below.] Also, notice the second example of of
  the `op` parameter for executing the paint command.

``` {.python}
    def raster(self):
        bounds = self.composited_bounds()
        if bounds.isEmpty():
            return
        irect = bounds.roundOut()

        if not self.surface:
            self.surface = skia.Surface.MakeRenderTarget(
                self.skia_context, skia.Budgeted.kNo,
                skia.ImageInfo.MakeN32Premul(
                    irect.width(), irect.height()))
            assert self.surface is not None
        canvas = self.surface.getCanvas()

        canvas.clear(skia.ColorTRANSPARENT)
        canvas.save()
        canvas.translate(-bounds.left(), -bounds.top())
        for (item, ancestor_effects) in self.paint_chunks:
            def op():
                item.execute(canvas)
            self.draw_internal(
                canvas, op, self.composited_ancestor_index + 1,
                len(ancestor_effects), ancestor_effects)
        canvas.restore()
```

  The above code depends on a helper method `draw_internal`. This method
  recursively iterates over `ancestor_effects` from the start to the end,
  drawing each visual effect on the canvas.

``` {.python}
    def draw_internal(self, canvas, op, start, end, ancestor_effects):
        if start == end:
            op()
        else:
            ancestor_item = ancestor_effects[start]
            def recurse_op():
                self.draw_internal(canvas, op, start + 1, end,
                    ancestor_effects)
            ancestor_item.draw(canvas, recurse_op)
```

* `draw`: draws `self.surface` to the screen, taking into account the visual
  effects applied to each chunk. In this case, `op` is a call to `draw` on the
  `skia.Surface`.

``` {.python}
    def draw(self, canvas, draw_offset):
        if not self.surface: return
        def op():
            bounds = self.composited_bounds()
            surface_offset_x = bounds.left()
            surface_offset_y = bounds.top()
            self.surface.draw(canvas, surface_offset_x,
                surface_offset_y)

        (draw_offset_x, draw_offset_y) = draw_offset

        (item, ancestor_effects) = self.paint_chunks[0]

        canvas.save()
        canvas.translate(draw_offset_x, draw_offset_y)
        if self.composited_ancestor_index >= 0:
            self.draw_internal(
                canvas, op, 0, self.composited_ancestor_index + 1,
                ancestor_effects)
        else:
            op()
        canvas.restore()
```

We've now got enough code to make the browser composite!
The last bit is just to wire it up by generalizing `raster_and_draw` into
`composite_raster_and_draw` (plus renaming the corresponding dirty bit and
renaming at all callsites), and everything should work end-to-end.

``` {.python}
    def composite_raster_and_draw(self):
        # ...
        self.composite()
        self.raster_chrome()
        self.raster_tab()
        self.draw()
        # ...
```

::: {.further}

Interestingly enough, as of the time of writing this section, Chromium and
WebKit both perform the `compositing` step on the main thread, whereas our
browser does it on the browser thread. This is the only
way in which our browser is actually ahead of real browsers! The reason
compositing doesn't (yet) happen on another thread in Chromium is that to get
there took re-architecting the entire algorithm for compositing. The
re-architecture turned out to be extremely difficult, because the old one
was deeply intertwined with nearly every aspect of the rendering engine. The
re-architecture project only
[completed in 2021](https://developer.chrome.com/blog/renderingng/#compositeafterpaint),
so perhaps sometime soon this work will be threaded in Chromium.

:::

Composited animations
=====================

Compositing now works, but it doesn't yet achieve the goal of avoiding raster
during animations. That's because `composite` is constantly re-running on every
frame and keeps throwing away and re-creating the composited layers. In fact,
at the moment it's probably *slower* than before, because the compositing
algorithm takes time to run. Let's now add code to avoid all this work.

Avoiding raster and the compositing algorithm is simple in concept: keep track
of what is animating, and re-run `draw` with different opacity parameters on
the `CompositedLayer`s that are animating. If nothing else changes, then
we don't need to re-composite or re-raster anything.

Let's accomplish that. It will have multiple parts, starting with the main
thread.

* If a composited animation is running, and it's the only thing
  happening to the DOM, then only re-do `paint` (in order to update
  the animated `DisplayItem`s), not `layout`:

``` {.python replace=if%20property_name/if%20USE_COMPOSITING%20and%20property_name}
class Tab:
    def set_needs_paint(self):
        self.needs_paint = True
        self.browser.set_needs_animation_frame(self)
```

* Save off each `Element` that updates its composited animation, in a new
array called `composited_animation_updates`:

``` {.python expected=False}
class Tab:
    def __init__(self, browser):
        # ...
        self.composited_animation_updates = []

    def run_animation_frame(self, scroll):
        for node in tree_to_list(self.nodes, []):
            for (property_name, animation) in node.animations.items():
                if value:
                    node.style[property_name] = value
                    if property_name == "opacity":
                        self.composited_animation_updates.append(node)
                        self.set_needs_paint()
                    else:
                        self.set_needs_layout()
```

* When running animation frames, if only `needs_paint` is true, then compositing
  is not needed, and each animation in `composited_animation_updates` can be
  committed across to the browser thread. The data to be sent across for each
  animation update will be a DOM `Element` and a `SaveLayer` pointer.

  To accomplish this we'll need several steps. First, when painting a
  `SaveLayer`, record it on the `Element` if it was composited:

``` {.python expected=False}
def paint_visual_effects(node, cmds, rect):
    # ...
    if save_layer.needs_compositing():
        node.save_layer = save_layer
```

  Next rename `CommitForRaster` to `CommitData` and add a list of composited
  updates (each of which will contain the `Element` and `SaveLayer` pointers).

``` {.python}
class CommitData:
    def __init__(self, url, scroll, height,
        display_list, composited_updates, scroll_behavior):
        # ...
        self.composited_updates = composited_updates
```

  And finally, commit the new information:

``` {.python expected=False}
class Tab:
    def run_animation_frame(self, scroll):
        # ...
        needs_composite = self.needs_render or self.needs_layout

        self.render()

        composited_updates = []
        if not needs_composite:
            for node in self.composited_animation_updates:
                composited_updates.append(
                    (node, node.save_layer))
        self.composited_animation_updates.clear()

        commit_data = CommitData(
            # ...
            composited_updates=composited_updates,
        )
```

Now for the browser thread.

* Add `needs_composite`, `needs_raster` and `needs_draw` dirty bits and
  corresponding `set_needs_composite`, `set_needs_raster`, and
  `set_needs_draw` methods (and remove the old dirty bit):

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.needs_composite = False
        self.needs_raster = False
        self.needs_draw = False

    def set_needs_raster(self):
        self.needs_raster = True
        self.needs_draw = True
        self.needs_animation_frame = True

    def set_needs_composite(self):
        self.needs_composite = True
        self.needs_raster = True
        self.needs_draw = True

    def composite_raster_and_draw(self):
        if not self.needs_composite and \
            len(self.composited_updates) == 0 \
            and not self.needs_raster and not self.needs_draw:
            self.lock.release()
            return
        
        if self.needs_composite or len(self.composited_updates) > 0:
            self.composite()
        if self.needs_raster:
            self.raster_chrome()
            self.raster_tab()
        if self.needs_draw:
            self.draw()
```

* Call `set_needs_raster` from the places that
  currently call `set_needs_raster_and_draw`, such as `handle_down`:

``` {.python}
    def handle_down(self):
        # ...
        self.set_needs_raster()
```

* Use the passed data in `commit` to decide whether to  call
  `set_needs_composite` or `set_needs_draw`, and store off the updates in
  `composited_updates`:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.composited_updates = []

    def commit(self, tab, data):
        # ...
        if tab == self.tabs[self.active_tab]:
            # ...
            self.composited_updates = data.composited_updates
            if len(self.composited_updates) == 0:
                self.set_needs_composite()
            else:
                self.set_needs_draw()
```

Add a new method to `CompositedLayer` that returns the ancestor effects which
need compositing. (In this case, we need look only at the first paint chunk;
remember that all paint chunks in a `CompositedLayer` have the same composited
ancestors.)

``` {.python}
    def composited_items(self):
        items = []
        (item, ancestor_effects) = self.paint_chunks[0]
        for item in ancestor_effects:
            if item.needs_compositing():
                items.append(item)
        return items
```


* Now for the actual animation updates on the browser thread: if
  `needs_composite` is false, loop over each `CompositedLayer`'s
  `composited_items`, and update each one that matches the
  animation.[^ptrcompare] The update is accomplished by calling `copy`  on the
  `SaveLayer`, defined as:


``` {.python}
class SaveLayer(DisplayItem):
    def copy(self, other):
        self.sk_paint = other.sk_paint
```

[^ptrcompare]: This is done by comparing equality of `Element` object
references. Note that we are only using these objects for
pointer comparison, since otherwise it would not be thread-safe.

And here's the code with the loop over `composited_items`:

``` {.python expected=False}
class Browser:
    def composite(self):
        if self.needs_composite:
            # ...
        else:
            for (node, save_layer) in self.composited_updates:
                for layer in self.composited_layers:
                    if node != composited_item.node: continue
                    composited_items = layer.composited_items()
                    for composited_item in composited_items:
                        if type(composited_item) is SaveLayer:
                            composited_item.copy(save_layer)
```

The result will be automatically drawn to the screen, because the `draw` method
on each `CompositedLayer` will iterate through its `ancestor_effects` and
execute them.

Check out the result---animations that only update the draw step, and
not everything else!

::: {.further}

While visual effect animations in our browser are now efficient
and *composited*, they are not *threaded* in the sense of[Chapter 12]
[threaded-12]: the animation still ticks on the main thread, and if there is a
slow JavaScript or other task clogging the task queue, animations will stutter.
This is a significant problem for real browsers, so almost all of them support
threaded opacity, transform and filter animations; some support certain kinds
of clip animations as well. Adding threaded animations to our browser is
left as an exercise at the end of this chapter.

It's common to hear people use "composited" and "threaded" as synonyms, however.
That's because in most browsers, compositing is a *prerequisite* for threading.
The reason is that if you're going to animate efficiently, you usually need to
composite a texture anyway, and plumbing animations on GPU textures is much
easier to express in a browser than an animation on "part of a display list".

That being said, it's not impossible to animate display lists, and some browsers
have attempted it. For example, one aim of the [WebRender] project at Mozilla
is to get rid of cached composited layers entirely, and perform all animations
by rastering and drawing at 60Hz on the GPU directly from the display list.
This is called a *direct render* approach. In practice this goal is
hard to achieve with current GPU technology, because some GPUs are faster
than others. So browsers are slowly evolving to a hybrid of direct rendering
and compositing instead.

:::

[threaded-12]: http://localhost:8001/scheduling.html#threaded-scrolling

[WebRender]: https://hacks.mozilla.org/2017/10/the-whole-web-at-maximum-fps-how-webrender-gets-rid-of-jank/

Overlap testing
===============

The compositing algorithm our browser implemented works great in many cases.
Unfortunately, it doesn't work correctly for display list commands
that *overlap* each other. The easiest way to explain why it is by example.

Consider this content, which is a light blue square overlapped by a light green
one:

<div style="width:200px;height:200px;background-color:lightblue;transform:translate(50px,50px)"></div>
<div style="width:200px;height:200px;background-color:lightgreen; transform:translate(0px,0px)"></div>

Now suppose we want to animate opacity on the blue square, and so allocate a
`skia.Surface` and GPU texture for it. But we don't want to animate the green
square, so it draws into the root surface (and does not receive a change of
opacity, of course). Which will cause the blue to draw on top of the
green, because the blue-square surface draws after the root surface. Oops!

To fix this bug, we'll have to put the green square into its own
`skia.Surface` (whether we like it or not). This situation is called an *overlap
reason* for compositing, and is a major complication (and potential source of
extra memory use and slowdown) faced by all real browsers.

Let's fix the compositing algorithm to take into account overlap. It turns out
to be not that hard to do with the flat compositing algorithm we implemented in
this chapter:[^layer-tree-overlap-hard] when considering where to put a paint
chunk, simply check if it overlaps with an animated `CompositedLayer`. If so,
start a new `CompositedLayer` that has an overlap reason for compositing.

[^layer-tree-overlap-hard]: On the other hand, it's quite complicated for a
"layer tree" approach, which is another reason to prefer the flat algorithm.

The change to `composite` will be only a few lines of code and an `elif` to
check if the current paint chunk overlaps another `CompositedLayer` in the list
that needs to be animated.

``` {.python}
    def composite(self):
        if self.needs_composite:
            # ...
            for (display_item, ancestor_effects) in chunks:
                placed = False
                for layer in reversed(self.composited_layers):
                    if layer.can_merge(
                        display_item, ancestor_effects):
                        # ...
                    elif skia.Rect.Intersects(
                        layer.absolute_bounds(),
                        absolute_bounds(display_item,
                            ancestor_effects)):
                        layer = CompositedLayer(self.skia_context)
                        layer.add_paint_chunk(
                            display_item, ancestor_effects)
                        self.composited_layers.append(layer)
                        placed = True
                        break
                # ...
```

And then implementing the `absolute_bounds` methods used in the code above. As
it stands, this might as well be equivalent to `composited_bounds` because
there is no visual effect that can grow or move the bounding rect of paint
commands.[^grow] So by just defining `absolute_bounds` to be
`composited_bounds`, everything will work correctly:

``` {.python expected=False}
    def absolute_bounds(self, rect):
        return self.composited_bounds(rect)
```

[^grow]: By grow, I mean that the pixel bounding rect of the visual effect
when drawn to the screen is *larger* than the pixel bounding rect of a paint
command like `DrawText` within it. After all, blending, compositing, and
opacity all change the colors of pixels, but don't expand the set of affected
pixels. And clips and masking decrease rather than increase the set of pixels,
so they can't cause additional overlap either (though they might cause *less*
overlap).

But this is both unsatisfying and boring, because in fact there *are* visual
effects that can cause additional overlap. The most important is *transforms*,
which are a mechanism to move around the painted output of a DOM element
anywhere on the screen.[^blur-filter] In addition, transforms are one of the
most popular visual effects in browsers, because they allow you to move around
content efficiently on the GPU and the browser thread. That's because
transforms merely apply a linear transformation matrix to each pixel, which is
one of the things GPUs are good at doing efficiently.[^overlap-example]

[^blur-filter]: Certain [CSS filters][cssfilter], such as blurs, can also expand
pixel rects.

[cssfilter]: https://developer.mozilla.org/en-US/docs/Web/CSS/filter

[^overlap-example]: In addition, it's not possible to create the overlapping
squares example of this section without something like transforms. Real
browsers have many other methods, such as [position]. In fact, it's a bit
difficult to cause overlap at all in our current browser, though one way is to
set the `width` and `height` of elements such that it causes text to overflow
on top of siblings further down the page.

[position]: https://developer.mozilla.org/en-US/docs/Web/CSS/position

::: {.further}

Overlap reasons for compositing not only create complications in the code, but
without care from the browser and web developer can lead to a huge amount of
GPU memory usage, as well as page slowdown to manage all of the additional
composited layers. One way this could happen is that an additional composited
layer results from one element overlapping another, and then a third because it
overlaps the second, and so on. This phenomenon is called *layer explosion*.
Our browser's algorithm avoids this problem most of the time because it is able
to merge multiple paint chunks together as long as they have compatible
ancestor effects, but in practice there are complicated situations where it's
hard to make content merge efficiently.

In addition to overlap, there are other situations where compositing has
undesired side-effects leading to performance problems. For example, suppose we
wanted to *turn off* composited scrolling in certain situations, such as on a
machine without a lot of memory, but still use compositing for visual effect
animations. But what if the animation is on content underneath a scroller? In
practice, it is very difficulty to implement this situation correctly without
just giving up and compositing the scroller.

:::


Transform animations
====================

The `transform` CSS property lets you apply linear transform visual
effects to an element.[^not-always-visual] In general, you can apply
[any linear transform][transform-def] in 3D space, but I'll just cover really
basic 2D translations. Here's HTML for the overlap example mentioned in the
last section:[^why-zero]

[^why-zero]: The green square has a `transform` property also so that paint
order doesn't change when you try the demo in a real browser. I won't get into
it, but there are various rules for painting, and "positioned" elements (such as
with `transform`) are supposed to paint after regular (non-positioned) elements.
This particular rule is purely a historical artifact.

[^not-always-visual]: Technically, `transform` is not always just a visual
effect. In real browsers, transformed element positions contribute to scrolling
overflow. Real browsers mostly do this correctly, but sometimes cut corners to
avoid slowing down transform animations.

[transform-def]: https://developer.mozilla.org/en-US/docs/Web/CSS/transform

    <div style="width:200px;height:200px;
                background-color:lightblue;
                transform:translate(50px, 50px)"></div>
    <div style="width:200px;height:200px;
                background-color:lightgreen;
                transform:translate(0px, 0px)"></div>

Adding in support for this kind of transform is not too hard: first
just parse it:[^space-separated]

[^space-separated]: The CSS transform syntax allows multiple transforms in a
space-separated sequence; the end result involves applying each in sequence. I
won't implement that, just like I didn't implement many other parts of the
standardized transform syntax.

``` {.python}
def parse_transform(transform_str):
    if transform_str.find('translate') < 0:
        return (0, 0)
    left_paren = transform_str.find('(')
    right_paren = transform_str.find(')')
    (x_px, y_px) = \
        transform_str[left_paren + 1:right_paren].split(",")
    return (float(x_px[:-2]), float(y_px[:-2]))
```

And add some code to `paint_visual_effects`:

``` {.python}
def paint_visual_effects(node, cmds, rect):
    # ...
    translation = parse_transform(node.style.get("transform", ""))
    # ...
    save_layer = \
    # ...

    transform = Transform(translation, rect, node, [save_layer])
    # ...
    return [transform]
```

The `Transform` display list command is pretty straightforward as well: it calls
the `translate` Skia canvas method, which is conveniently built-in.

``` {.python expected=False}
class Transform(DisplayItem):
    def __init__(self, translation, rotation_degrees,
        rect, node, cmds):
        self.translation = translation
        self.self_rect = rect
        self.cmds = cmds

    def draw(self, canvas, op):
        if self.translation:
            (x, y) = self.translation
            canvas.save()
            canvas.translate(x, y)
            for cmd in self.cmds:
                cmd.execute(canvas)
            canvas.restore()
        else:
            for cmd in self.cmds:
                cmd.execute(canvas)

    def copy(self, other):
        self.translation = other.translation
        self.rect = other.rect
```

``` {.python}
ANIMATED_PROPERTIES = {
    # ...
    "transform": TranslateAnimation,
}
```

And `TranslateAnimation`:

``` {.python replace=True)/USE_COMPOSITING)}
class TranslateAnimation:
    def __init__(self, old_value, new_value, num_frames):
        (self.old_x, self.old_y) = parse_transform(old_value)
        (new_x, new_y) = parse_transform(new_value)
        self.num_frames = num_frames

        self.frame_count = 1
        self.change_per_frame_x = (new_x - self.old_x) / num_frames
        self.change_per_frame_y = (new_y - self.old_y) / num_frames

    def animate(self):
        self.frame_count += 1
        if self.frame_count >= self.num_frames: return
        new_x = self.old_x + self.change_per_frame_x * self.frame_count
        new_y = self.old_y + self.change_per_frame_y * self.frame_count
        return "translate({}px,{}px)".format(new_x, new_y)
```

You should now be able to create this animation:^[In this
example, I added in a simultaneous opacity animation to demonstrate that our
browser supports it.]

<iframe src="examples/example13-transform-transition.html" style="width:350px;height:450px">
</iframe>
(click [here](examples/example13-transform-transition.html) to load the example in
your browser)

Finally, there is a bit more work to do to make transform visual effects animate
without re-raster on  every frame. Doing so is not hard, it just requires edits
to the code to handle transform in all the same places opacity was, in
particular:

* In `DisplayList.needs_compositing`.

* Setting `node.transform` in `paint_visual_effects` just like `save_layer`.

* Adding `transform` to each `composited_updates` field of `CommitData`.

* Considering transform during the fast-path update in `Browser.Composite`.

Each of these changes should be pretty straightforward and repetitive on top of
opacity, so I'll skip showing the code. Once updated, our browser should now
have fast, composited transform animations.

But if you try it on the example above, you'll find that the animation still
looks wrong---the blue square is supposed to be *under* the green one, but
now it's on top. Which is of course because of the lack of overlap testing,
which we should now complete.

Let's first add the implementation of a new `absolute_bounds` function. The
*absolute bounds* of a paint chunk or `CompositedLayer` are the bounds in the
 space of the root surface.^[Where the 0, 0 point is the top-left of the web
 page. This point is *not* screen coordinates; for example, the 0, 0 point may
 be offscreen due to scrolling.]

 Before we added support for `transform`, this was the same as the union of the
 rects of each paint command. But now we need to account for a transform moving
 content around on screen. The first step in accomplishing that is with a new
 `map` method on `Transform` that takes a rect in the coordinate space of
 the "contents" of the transform and outputs a rect in post-transform space.
 For example, if the transform was `translate(20px, 0px)` then the output of
 calling `map` on a rect would return a new rect with the x coordinate of all
 four corners increased by 20.

``` {.python}
class Transform(DisplayItem):
    def map(self, rect):
        if not self.translation:
            return rect
        matrix = skia.Matrix()
        if self.translation:
            (x, y) = self.translation
            matrix.setTranslate(x, y)
        return matrix.mapRect(rect)
```

We can use `map` to implement a new `absolute_bounds` function that determines
the absolute bounds of a paint chunk:

``` {.python}
def absolute_bounds(display_item, ancestor_effects):
    retval = display_item.composited_bounds()
    for ancestor_item in reversed(ancestor_effects):
        if type(ancestor_item) is Transform:
            retval = ancestor_item.map(retval)
    return retval
```

And add a method union all of the absolute bounds of the paint chunks in 
a `CompositedLayer`:

``` {.python}
class CompositedLayer:
    def absolute_bounds(self):
        retval = skia.Rect.MakeEmpty()
        for (item, ancestor_effects) in self.paint_chunks:
            retval.join(absolute_bounds(item, ancestor_effects))
        return retval
```

All this `absolute_bounds` code is already used in the `Browser.composite`
method I outlined in the previous section; don't forget to update that method
according to the code I outlined.

Overlap testing is now complete.[^not-really] Your animation should animate the
blue square underneath the green one.

[^not-really]: Actually, even the current code is not correct now that we have
transforms. Since a transform animation moves content around, it also affects
whether content overlaps. I conveniently chose a demo that starts out
overlapping, but if it didn't start out overlapping our browser would not
correctly notice when overlap starts happening during the animation. I've
left solving this to an exercise.

::: {.further}

At this point, the compositing algorithm and its effect on content is getting
pretty complicated. It will be very useful to you to add in more visual
debugging to help understand what is going on. One good way to do this is
to add a flag to our browser that draws a red border around `CompositedLayer`
content. This is a very simple addition to `CompositedLayer.raster`:

``` {.python}
class CompositedLayer:
    def raster(self):
        # ...
            draw_rect(
                canvas, 0, 0, irect.width() - 1,
                irect.height() - 1,
                border_color="red")
  
```

You should see three red squares for the transform animation demo:
one for the blue square, one for the green square, and one for the root surface.

I also recommend you add a mode to your browser that disables compositing
(i.e. return `False` from `needs_compositing` for every `DisplayItem`), and
disables use of the GPU (i.e. go back to the old way of making Skia surfaces).
Everything should still work (albeit more slowly) in all of the modes, and you
can use these additional modes to debug your browser more fully and benchmark
its performance.
:::

Composited scrolling
====================

The last category of animations we haven't covered is the *input-driven* ones,
such as scrolling. I introduced this category of animations earlier, but didn't
really explain in much detail why it makes sense to categorize scrolling as
an *animation*. To my mind, there are two key reasons:

* Scrolling often continues after the input is done. For example, most browsers
  animate scroll in a smooth way when scrolling by keyboard or scrollbar
  clicks. Another example is that in a touch-driven scroll, browsers interpret
  the touch movement as a gesture with velocity, and therefore continue the
  scroll---a "fling" gesture---according to a physics-based model (with friction
  slowing it down).

* Touch or mouse drag-based scrolling is very performance sensitive. This is
  because humans are much more sensitive to things keeping up with the movement
  of their hand than they are to the latency of responding to a click. For
  example, a mouse-drag scrolling hiccup for even one frame, even for only a
  few tens of milliseconds, is easily noticeable and jarring to a person, but
  most people do not notice click input delays of up to 100ms or so. Therefore
  such gestures benefit greatly from the same GPU+compositing technology I
  introduced in this chapter.

Let's add composited scrolling to our browser, and then smooth scrolling on
keyboard events.

Composited scrolling (i.e. scrolling without raster) will be extremely easy,
because thanks to [Chapter 12](#threaded-scrolling), we have threaded scrolling
already, and the `scroll` offset is already present on `Browser`. All we have
to do is replace `set_needs_raster` with `set_needs_draw`:

``` {.python}
class Browser:
    # ...
    def handle_down(self):
        # ...
        self.set_needs_draw() 
```

Smooth scrolling will have a few steps. First we'll have to parse a new 
[scroll-behavior] CSS property that applies to scrolling of the `<body>` element,
[^body] plumb it to the browser thread, and then trigger a
(main-thread) animation in `Browser.handle_down`. The animation will run a
`ScrollAnimation` that is very similar to a `NumericAnimation`.[^threaded]

[scroll-behavior]: https://developer.mozilla.org/en-US/docs/Web/CSS/scroll-behavior

[^body]: The difference between the `<body>` and `<html>` tag for scrolling is a
[little complicated][scrollingelement], and I won't get into it here.

[scrollingelement]: https://developer.mozilla.org/en-US/docs/Web/API/document/scrollingElement

[^threaded]: And with some more work, the animation could run on the browser
thread and avoid main-thread delay. I'll leave that to an exercise.

The concrete steps are:

* Parsing in `Tab` (there's some complication in finding the `<body>` element,
  because the `<head>` may or may not be present):

``` {.python}
class Tab:
    def __init__(self, browser):
        # ...
        self.scroll_behavior = 'auto'

    def render(self):
        # ...
            if self.nodes.children[0].tag == "body":
                body = self.nodes.children[0]
            else:
                body = self.nodes.children[1]
            if 'scroll-behavior' in body.style:
                self.scroll_behavior = body.style['scroll-behavior']
```

* Plumbing to `Browser`:

``` {.python}
class CommitData:
    def __init__(self, url, scroll, height,
        display_list, composited_updates, scroll_behavior):
        # ...
        self.scroll_behavior = scroll_behavior
```

``` {.python}
class Tab:
    # ...
    def run_animation_frame(self, scroll):
        commit_data = CommitData(
            # ...
            scroll_behavior=self.scroll_behavior
        )
```

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.scroll_behavior = 'auto'

    def commit(self, tab, data):
        # ...
            self.scroll_behavior = data.scroll_behavior
```

* Initiating smooth scroll from the browser thread:

``` {.python}
    def handle_down(self):
        # ...
        if self.scroll_behavior == 'smooth':
            active_tab.task_runner.schedule_task(
                Task(active_tab.run_animation_frame, scroll))
        else:
            self.scroll = scroll
```

* Responding to it:

``` {.python}
class Tab:
    def run_animation_frame(self, scroll):
        # ...
        if not self.scroll_changed_in_tab:
            if scroll != self.scroll and not self.scroll_animation:
                if self.scroll_behavior == 'smooth':
                    animation = ScrollAnimation(self.scroll, scroll)
                    self.scroll_animation = animation
                else:
                    self.scroll = scroll
        # ...

    def render(self):
        # ...
        if self.scroll_animation:
            value = self.scroll_animation.animate()
            if value:
                self.scroll = value
                self.scroll_changed_in_tab = True
                self.browser.set_needs_animation_frame(self)
            else:
                self.scroll_animation = None
        # ...
```

* Implementing `ScrollAnimation`:[^thirty]

[^thirty]: The choice of a half-second animation---30 animation frames---is an
arbitrary choice that is intentionally left up to the browser in the definition
of the `scroll-behavior` CSS property.

``` {.python}
class ScrollAnimation:
    def __init__(self, old_scroll, new_scroll):
        self.old_scroll = old_scroll
        self.new_scroll = new_scroll
        self.num_frames = 30
        self.change_per_frame = \
            (new_scroll - old_scroll) / self.num_frames
        self.frame_count = 1

    def animate(self):
        self.frame_count += 1
        if self.frame_count >= self.num_frames: return
        updated_value = self.old_scroll + \
            self.change_per_frame * self.frame_count
        return updated_value
```

Yay, smooth scrolling! You can try it on
[this example](examples/example13-transform-transition.html), which combines a
smooth scroll, opacity and transform animation *at the same time*. And it's got
super smooth animation performance. That's quite satisfying, and I hope makes
the hard slog of this chapter worth it!

On top of that, notice how once we have an animation framework implemented,
adding new features to it becomes easier and easier. This is a pattern I hope
you've noticed through many parts of this book. It's yet another reason to know
how browsers work on the inside---this knowledge will help you know what they
might be capable of in the future, and how to propose new features that are
easy enough to implement.

::: {.further}

These days, many websites implement a number of *scroll-linked* animation
effects. One common one is *parallax*. In real life, parallax is the phenomenon
that objects further away appear to move slower than closer-in objects (due to
the angle of light changing less quickly). For example, when riding a train,
the trees nearby move faster across your field of view than the hills in the
distance. The same mathematical result can be applied to web contents by way of
the the [`perspective`][perspective] CSS property.
[This article][parallax] explains how, and [this one][csstricks-perspective]
gives a much deeper dive into perspective in CSS generally.

[parallax]: https://developer.chrome.com/blog/performant-parallaxing/
[perspective]: https://developer.mozilla.org/en-US/docs/Web/CSS/perspective
[csstricks-perspective]: https://css-tricks.com/how-css-perspective-works/

There are also animations that are tied to scroll offset but are not, strictly
speaking, part of the scroll. An example is a rotation or opacity fade on an
element that advances as the user scrolls down the page (and reverses as they
scroll back up). Or there are *scroll-triggered* animations that start once an
element has reached a certain point on the page, or when scroll changes
direction. An example of that is animation of a top-bar onto the page when the
user starts to change scroll direction.

Scroll-linked animations implemented in JavaScript work ok most of the time, but
suffer from the problem that they cannot perfectly sync with real browsers'
threaded scrolling architectures. This will be solved by the upcoming
[scroll-linked animations][scroll-linked] specification.

[scroll-linked]: https://drafts.csswg.org/scroll-animations-1/
:::

Summary
=======

This chapter introduced the concept of animations. The key takeaways you should
remember are:

- Animations come in DOM-based, input-driven and video-like varieties.

- DOM animations can be *layout-inducing* or *visual effect only*, and the
  difference has important performance and animation quality implications.

- GPU acceleration is necessary for smooth animations.

- Compositing is necessary for smooth and threaded visual effect animations, and
  generally not feasible (at least at present) for layout-inducing animations.

- Input-driven animations have tight performance constraints, and so must
  generally be composited to behave well.


Outline
=======

The complete set of functions, classes, and methods in our browser 
should now look something like this:

::: {.cmd .python .outline html=True}
    python3 infra/outlines.py --html src/lab13.py
:::

Exercises
=========

*Multiple animations*: create some demos of nested transform and opacity
 animations. They should still work of course, but these situations usually
 uncover bugs. If you find bugs, fix them!

*Background-color*: implement animations of the `background-color` CSS property.
You'll have to define a new kind of interpolation that applies to all the
color channels.

*Easing functions*: our browser only implements a linear interpolation between
 start and end values, but there are many other [easing functions][easing] 
 (in fact, the default one in real browsers is
 `cubic-bezier(0.25, 0.1, 0.25, 1.0)`, not linear). Implement this easing
 function, and one or two others.

 [easing]: https://developer.mozilla.org/en-US/docs/Web/CSS/easing-function

*Threaded animations*: despite Chapter 12 being all about threading, we didn't
 actually implement threaded animations in this chapter---they are all driven
 by code running on the main thread. But just like scrolling, in a real browser
 this is not acceptable, since there could be many main-thread tasks slowing
 things down. Add support for threaded animations. Doing so will require
 replicating some event loop code from the main thread, but if you're careful
 you should be able to reuse all of the animation classes. (Don't worry too
 much about how to synchronize these animations with the main thread, except to
 cause them to stop after the next commit when DOM changes occur that
 invalidate the animation. Real browsers encounter a lot of complications in
 this area.)

*Threaded smooth scrolling*: once you've completed the threaded animations
 exercise, you should be able to add threaded smooth scrolling without much
 more work.

*CSS animations*: implement the basics of the
[CSS animations][css-animations] API, in particular enough of the `animation`
CSS property and parsing of `@keyframe` to implement the demos
 [here](examples/example13-opacity-animation.html) and
 [here](examples/example13-width-animation.html).

*Overlap testing w/transform animations*: as mentioned in one of the Go Further
 blocks, our browser currently does not overlap test correctly in the presence
 of transform animations. First create a demo that exhibits the bug, and then
 fix it. One way to fix it is to enter "assume overlap mode" whenever an
 animated transform paint chunk is encountered. This means that every
 subsequent paint chunk is assumed to overlap the animating one (even if it
 doesn't at the moment), and therefore can't merge into any `CompositedLayer`
 earlier in the list than the animating one. Another way is to run overlap
 testing on every animation frame in the browser thread, and if the results
 differ from the prior frame, re-do compositing and raster.
 [^css-animation-transform]

[^css-animation-transform]: And if you've done the CSS animations exercise, and
a transform animation is defined in terms of a CSS animation, you can
analytically determine the bounding box of the animation, and use that for
overlap instead.

*Avoiding sparse composited layers*: our browser's algorithm currently always
 merges paint chunks that have compatible ancestor effects. But this can lead
 to inefficient situations, where two paint chunks that are visually very far
 away on the web page (e.g. one at the very top and one thousands of pixels
 lower down) end up in the same `CompositedLayer`. That can be very bad,
 because it results in a huge `skia.Surface` that is mostly wasted GPU memory.
 One way to reduce that problem is to stop merging paint chunks that would make
 the total area of the `skia.Surface` larger than some fixed value. Implement
 that.[^tiling-helps]

 [^tiling-helps]: Another way is via surface tiling (this technique was briefly
 discussed in a Go Further block in Chapter 11).

 *Short display lists*: it's relatively common in real browsers to encounter
  `CompositedLayer`s that are only a single solid color, or only a few
  simple paint commands.[^real-browser-simple] Implement an optimization that
  skips storing a `skia.Surface` on a `CompositedLayer` with less than a fixed
  number (3, say) of paint commands, and instead execute them directly. In
  other words, `raster` on these `CompositedLayer`s will be a no-op and `draw`
  will execute the paint commands instead.

[^real-browser-simple]: A real browser would use as its criterion whether the
time to raster the provided paint commands is low enough to not justify a GPU
texture. This will be true for solid color rectangles, but probably not complex
shapes or text.

*Render surfaces*: as described in the go-further block at the end of
 [this section](#implementing-compositing), our browser doesn't currently draw
 nested, composited visual effects correctly. Fix this by building a "draw
 tree" for all of the `CompositedLayer`s and allocating a `skia.Surface` for
 each internal node. Bonus points for avoiding internal surfaces that are not
 needed.
