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
succession that create the illusion of *movement* to the human
eye.[^general-movement] The pixel changes are *not* arbitrary, they are ones
that feel logical to a human mind trained by experience in the real world.

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
require main thread `render` calls). Most of the time, layout-inducing
animations are not a good idea for these reasons.^[One exception is a
layout-inducing animation when resizing a browser window via a mouse gesture;
in this case it's very useful for theuser to see the new layout as they animate.
Modern browsers are fast enough to do this, but it used to be that instead they
would leave a visual *gutter* (a gap between content and the edge of the window)
during the animation, to avoid updating layout on every animation frame.]

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
animates from 1 to 0.1, over 120 frames (about two seconds), then back up
to 1 for 120 more frames, and repeats.

``` {.html file=example-opacity-html}
<div>Test</div>
```

``` {.javascript file=example-opacity-js}
var start_value = 0.999;
var end_value = 0.1;
var num_animation_frames = 120;
var frames_remaining = num_animation_frames;
var go_down = true;
function animate() {
    var div = document.querySelectorAll("div")[0];
    var percent_remaining = frames_remaining / num_animation_frames;
    if (go_down) {
        div.style = "opacity:" +
            (percent_remaining * start_value +
                (1 - percent_remaining) * end_value);
    } else {
        div.style = "opacity:" +
            ((1-percent_remaining) * start_value +
                percent_remaining * end_value);
    }
    frames_remaining--;
    if (frames_remaining < 0) {
        frames_remaining = num_animation_frames;
        go_down = !go_down;
    }
    requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
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
<iframe src="examples/example13-width-raf.html" style="width: 450px"></iframe>
(click [here](examples/example13-width-raf.html) to load the example in
your browser)

``` {.javascript file=example-width-js}
var start_value = 400;
var end_value = 100;
var num_animation_frames = 120;
var frames_remaining = num_animation_frames;
var go_down = true;
function animate() {
    var div = document.querySelectorAll("div")[0];
    var percent_remaining = frames_remaining / num_animation_frames;
    if (go_down) {
        div.style = "background-color:lightblue;width:" +
            (percent_remaining * start_value +
            (1 - percent_remaining) * end_value) + "px";
    } else {
        div.style = "background-color:lightblue;width:" +
            ((1 - percent_remaining) * start_value +
             percent_remaining * end_value) + "px";
    }
    frames_remaining--;
    if (frames_remaining < 0) {
        frames_remaining = num_animation_frames;
        go_down = !go_down;
    }
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
new values, in basically the same way the `requestAnimationFrame` loop did it.
This is much more convenient for website authors than writing a bunch of
JavaScript, and also doesn't force them to account for each and every way in
which the styles can change.

<iframe src="examples/example13-opacity-transition.html"></iframe>
(click [here](examples/example13-opacity-transition.html) to load the example in
your browser; [here](examples/example13-width-transition.html) is the width
animation example)

Implement this CSS property. Start with a quick helper method that returns the
duration of a transition if it was set, and `None` otherwise. This requires
parsing the comma-separated `transition` syntax.^[Unfortunately, setting up
animations tends to have a lot of boilerplate code, so get ready for more code
than usual. The good news though is that it's all pretty simple to
understand.]

``` {.python}
def get_transition(property_value, style):
    if not "transition" in style:
        return None
    transition_items = style["transition"].split(",")
    found = False
    for item in transition_items:
        if property_value == item.split(" ")[0]:
            found = True
            break
    if not found:
        return None   
    duration_secs = float(item.split(" ")[1][:-1])
    return duration_secs / REFRESH_RATE_SEC 
```

Next let's add some code that detects if a transition should start, by comparing
two style objects---the ones before and after a style update for a DOM node. It
will add a `NumericAnimation` to `tab` if the transition was found. Both
`opacity` and `width` are *numeric* animations, but with different
units---unitless floating-point between 0 and 1, respectively.[^more-units] The
difference will be handled by an `is_px` parameter indicating which it is.

``` {.python}
def try_transition(name, node, old_style, new_style):
    if not get_transition(name, old_style):
        return None

    num_frames = get_transition(name, new_style)
    if num_frames == None:
        return None

    if name not in old_style or name not in new_style:
        return None

    if old_style[name] == new_style[name]:
        return None

    return num_frames

def try_numeric_animation(node, name,
    old_style, new_style, tab, is_px):
    num_frames = try_transition(name, node, old_style, new_style)
    if num_frames == None:
        return None;

    if is_px:
        old_value = float(old_style[name][:-2])
        new_value = float(new_style[name][:-2])
    else:
        old_value = float(old_style[name])
        new_value = float(new_style[name])

    if not node in tab.animations:
        tab.animations[node] = {}
    tab.animations[node][name] = NumericAnimation(
        node, name, is_px, old_value, new_value,
        num_frames, tab)
```

[^more-units]: In a real browsers, there are a [lot more][units] units to
contend with. I also didn't bother clamping opacity to a value between 0 and 1.

[units]: https://developer.mozilla.org/en-US/docs/Learn/CSS/Building_blocks/Values_and_units

Next, implement `NumericAnimation`. This class just encapsulates a bunch
of parameters, and has a single `animate` method. `animate` is in charge of
advancing the animation by one frame. It's the equivalent of the
`requestAnimationFrame` callback in a JavaScript-driven animation; it also
returns `False` if the animation has ended.[^animation-curve]

[^animation-curve]: Note that this class implements a linear animation
interpretation (or *easing function*). By default, real browsers
use a non-linear easing function, so your demo will not look quite the same.

``` {.python expected=False}
class NumericAnimation:
    def __init__(
        self, node, property_name, is_px,
        old_value, new_value, num_frames, tab):
        self.node = node
        self.property_name = property_name
        self.is_px = is_px
        self.old_value = old_value
        self.num_frames = num_frames
        self.change_per_frame = (new_value - old_value) / num_frames
        self.tab = tab
        self.frame_count = 0
        self.animate()

    def animate(self):
        self.frame_count += 1
        if self.frame_count >= self.num_frames: return False
        updated_value = self.old_value + \
            self.change_per_frame * self.frame_count
        if self.is_px:
            self.node.style[self.property_name] = \
                "{}px".format(updated_value)
        else:
            self.node.style[self.property_name] = \
                "{}".format(updated_value)
        self.tab.set_needs_layout()
        return True
```

Note that I called a new method `set_needs_layout` rather than
`set_needs_render`. This is to cause layout and the rest of rendering, but
*not* style recalc. Otherwise style recalc will re-create the
`NumericAnimation` on every single frame.[^even-more]


``` {.python expected=False}
class Tab:
    def __init__(self, browser):
        # ...
        self. needs_layout = False
    
    def set_needs_layout(self):
        self.needs_layout = True
        self.browser.set_needs_animation_frame(self)

    def render(self):
        if not self.needs_render \
            and not self.needs_layout:
            return

        if self.needs_render:
            style(self.nodes, sorted(self.rules,
                key=cascade_priority), self)

        # ...

        self.needs_layout = False
```

[^even-more]: This is not good enough for a real browser, but is a reasonable
expedient to make basic transition animations work. For example, it doesn't
correctly handle cases where styles changed on elements unrelated to the
animation---that situation shouldn't re-start the animation either.

Now for integrating this code into rendering. It has two main parts: detecting
style changes, and executing the animation. Both have some details that are
important to get right, but are conceptually straightforward:

First, in the `style` function, when a DOM node changes its style, check to see
if one or more of the properties with registered transitions are changed; if
so, start a new animation and add it to the `animations` dictionary on `tab`.
This logic will be in a new function called `animate_style`, which is called
just after the style update for `node` is complete:

``` {.python}
def style(node, rules, tab):
    # ...
    animate_style(node, old_style, node.style, tab)
```

And `animate_style` just has some pretty simple business logic to find
animations and start them. First, bail if there is not an old style. Then look
for `opacity` and `width` animations, and add them to the `animations` object
if so.[^corner-cases]

[^corner-cases]: Note that this code doesn't handle some corner cases
correctly, such as re-starting a transition if the node's style changes during
an animation.

``` {.python}
def animate_style(node, old_style, new_style, tab):
    if not old_style:
        return

    try_numeric_animation(node, "opacity",
        old_style, new_style, tab, is_px=False)
    try_numeric_animation(node, "width",
        old_style, new_style, tab, is_px=True)
```

Second, in `run_animation_frame` on `tab`, each animation in `animations`
should be updated just after running `requestAnimationFrame` callbacks and
before calling `render`. It's basically: loop over all animations, and call
`animate`; if `animate` returns `True`, that means it animated a new frame by
changing the node's style; if it returns `False`, it has completed and can be
removed from `animations`.[^delete-complicated]

[^delete-complicated]: Because we're iterating over a dictionary, we can't
delete entries right then. Instead, we have to save off a list of entries
to delete and then loop again to delete them. That's why there are two loops
and the `to_be_deleted` list.


``` {.python}
class Tab:
    def __init__(self, browser):
        # ...
        self.animations = {}

    def run_animation_frame(self, scroll):
        # ...
        self.js.interp.evaljs("__runRAFHandlers()")
        # ...
        to_delete = []
        for node in self.animations:
            for (property_name, animation) in \
                self.animations[node].items():
                if not animation.animate():
                    to_delete.append((node, property_name))

        for (node, property_name) in to_delete:
            del self.animations[node][property_name]
        # ...
        self.render()
```

Our browser now supports animations with just CSS! That's much more convenient
for website authors. It's also a bit faster, but not a whole lot (recall that
our [profiling in Chapter 12][profiling] showed rendering was almost all of the
time spent). That's not really acceptable, so let's turn our attention to how
to dramatically speed up rendering for these animations.

[profiling]: http://localhost:8001/scheduling.html#profiling-rendering

::: {.further}
TODO: explain css animations, which avoid having any js at all.
:::

GPU acceleration
================

The first order of business in making these animations smoother is to move
raster and draw to the [GPU][gpu]. Because both SDL and Skia support these
modes, the code to do so looks a lot like some configuration changes, and
doesn't really give any direct insight into why it's all-of-a-sudden faster. So
before showing the code let's discuss briefly how GPUs work and the
four---again, internal implementation detail to Skia and SDL---steps of running
GPU raster and draw.

There are lots of resources online about how GPUs work and how to program them.
But we won't generally be writing shaders or other types of GPU programs in
this book. Instead, let's focus on the basics of GPU technologies and how they
map to browsers. A GPU is essentially a hyper-specialized computer that is good
at running very simple computer programs that specialize in turning simple data
structures into pixels. These programs are so simple that the GPU can run one
of them *in parallel* for each pixel, and this parallelism is why GPU raster is
usually much faster than CPU raster.

At a high level, the steps to raster and draw using the GPU are:[^gpu-variations]

[^gpu-variations]: These steps vary a bit in the details by GPU architecture.

* *Upload* the input data structures (that describe the display list)
   to specialized GPU memory.

* *Compile* GPU programs to run on the data structures.[^compiled-gpu]

[^compiled-gpu]: That's right, GPU programs are dynamically compiled! This
allows the programs to be portable across a wide variety of GPU implementations
that may have very different instruction sets or acceleration tactics.

* *Execute* the raster into GPU textures.[^texture]

[^texture]: A surface represented on the GPU is called a *texture*.

* *Draw* the textures onto the screen.

You can configure any GPU program to draw directly to the screen *framebuffer*,
or to an *intermediate texture*.[^gpu-texture] Draw proceeds bottom-up: the
leaf textures are generated from raw display list data structures, and internal
surface tree textures are generated by computing visual effects on one or more
children. The root of the tree is the framebuffer texture.

[^gpu-texture]: Recall from [Chapter 11](visual-effects.md) that there can be
surfaces that draw into other surfaces, forming a tree. Skia internally does
this based on various triggers such as blend modes. 

The time to run GPU raster is then the roughly sum of the time for these four
steps.[^optimize] Usually, the *execute* step is very fast, and total time is
instead dominated by one or more of the other three steps. The larger the
display list, the longer the upload; the more complexity and variety of display
list commands, the longer the compile; the deeper the the nesting of surfaces
in the web page, the longer the draw. Without care, these steps can sometimes
add up to be longer than the time to just raster on the CPU. All of these 
slowdown situations can and do happen in real browsers for some kinds of
hard-to-draw content.

[^optimize]: It's not necessary to compile GPU programs on every raster, so
this part can be optimized. Parts of the other steps can as well, such as
by caching font data in the GPU.

[gpu]: https://en.wikipedia.org/wiki/Graphics_processing_unit

Ok, now for the code. First you'll need to import code for OpenGL (just for
one constant and one debugging method, actually). Install the library:

    pip3 install PyOpenGL

and then import it:

``` {.python}
import OpenGL.GL as GL
```

Then we'll need to configure `sdl_window` and start/stop a
[GL context][glcontext] at the
beginning/end of the program; for our purposes consider it API
boilerplate.^[Starting a GL context is just OpenGL's way
of saying "set up the surface into which subsequent GL drawing commands will
draw". After doing so you can execute OpenGL commands manually, to
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

The root Skia surface will need to be connected directly to the *framebuffer*
(the screen) associated with the SDL window. The incantation for that is:

``` {.python expected=False}
class Browser:
    def __init__(self):
        #. ...
        self.skia_context = skia.GrDirectContext.MakeGL()

        self.root_surface = skia.Surface.MakeFromBackendRenderTarget(
            self.skia_context,
            skia.GrBackendRenderTarget(
                WIDTH, HEIGHT,
                0,  # sampleCnt
                0,  # stencilBits
                skia.GrGLFramebufferInfo(0, GL.GL_RGBA8)),
                skia.kBottomLeft_GrSurfaceOrigin,
                skia.kRGBA_8888_ColorType, skia.ColorSpace.MakeSRGB())
        assert self.root_surface is not None

```

Note that this code never seems to reference `gl_context` or `sdl_window`
directly, but draws to the window anyway. That's because OpenGL is a strange
API that uses hidden global states; the `MakeGL` Skia method just binds to the
existing GL context.

The `chrome_surface` incantation is a bit different, because it's creating
a GPU texture, but one that is independent of the framebuffer:

``` {.python}
    self.chrome_surface =  skia.Surface.MakeRenderTarget(
            self.skia_context, skia.Budgeted.kNo,
            skia.ImageInfo.MakeN32Premul(WIDTH, CHROME_PX))
    assert self.chrome_surface is not None
```

The difference from the old way of doing surfaces was that it's associated
explicitly with the `skia_context` and uses a different color space that is
required for GPU mode. `tab_surface` should get exactly the same treatment
(but with different width and height arguments, of course).

The final change to make is that `draw` is now simpler, because `root_surface`
need not blit into the SDL surface, because they share a GPU framebuffer
backing. (There are no changes at all required to raster.) All you have to do
is *flush* the Skia surface (Skia surfaces draw lazily) and call
`SDL_GL_SwapWindow` to activate the new framebuffer (because of OpenGL
[double-buffering][double]).

[double]: https://wiki.libsdl.org/SDL_GL_SwapWindow

``` {python}
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

Let's go back and test the
[`opacity` animation](examples/example13-opacity-transition.html), to see how
much GPU acceleration helped. The results on my computer are:

    Without GPU:

    Time in raster-and-draw on average: 22ms
    Time in render on average: 1ms

    With GPU:

    Time in raster-and-draw on average: 8ms
    Time in render on average: 1ms


So GPU acceleration yields something like a 65% reduction in browser thread
time.  (If you're on a computer with a non-virtualized GL driver you will
probably see even more speedup than that.) This is a great improvement, but
still 8ms is a lot for such a simple example, and also requires a main-thread
task that might be slowed down by JavaScript. Can we do better? Yes we can, by
using compositing.

Compositing
===========

*Compositing* is the technique that lets us avoid raster costs during visual
 effect animations; on the browser thread, only draw is needed for each
 animation frame (with different parameters each time).[^compositing-def]

[^compositing-def]: The term [*compositing*][compositing] at its root means to
combine multiple images together into a final output. As it relates to
browsers, it usually means the performance optimization technique of caching
rastered GPU textures that are the inputs to animated visual effects, but the
term is usually overloaded to refer to OS and browser-level compositing
and multi-threaded rendering.

[compositing]: https://en.wikipedia.org/wiki/Compositing

Let's consider the opacity animation example from this chapter. When we're
animating, the opacity is changing, but the
"Test" text underneath it is not. So let's stop re-rastering that content on
 every frame of the animation, and instead cache it in a GPU texture.
 This should directly reduce browser thread work, because no raster work
 will be needed on each animation frame.

Below is the opacity animation with a red border "around" the surface that we
want to cache. Notice how it's sized to the width and height of the `<div>`,
which is as wide as the viewport and as tall as the text "Test".[^chrome]

 <iframe src="http://localhost:8001/examples/example13-opacity-transition-borders.html">
 </iframe>

[^chrome]: You can see the same thing if you load the example when running
Chrome with the `--show-composited-layer-borders` command-line flag; there
is also a DevTools feature for it.

As I explained in [Chapter 11](visual-effects.md#browser-compositing), Skia
sometimes caches surfaces internally. So you might think that Skia has a way to
say "please cache this surface". And there is---keep around a `skia.Surface`
object across multiple raster-and-draw executions and use the `draw` method on
the surface to draw it into the canvas.^[Skia will keep alive the rastered
content associated with the `Surface` object until it's garbage collected.] In
other words, we'll need to do the caching ourselves. This feature is not
built into Skia itself in a trivial-to-use form.

Let's start digging into the compositing algorithm and how to implement it. The
plan is to cache the "contents" of an animating visual effect in a new
`skia.Surface` and store it somewhere. But what does "contents" mean exactly?
If opacity is animating, which parts of the web page should we cache in the
surface? To answer that, let's revisit the \structure of our display
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
        super().__init__(cmds=cmds)
```

Then add a `repr_recursive` method to `DisplayItem`. Also add an `is_noop`
parameter that indicates whether the `DisplayItem` has no effect.^[Recall that
most of the time, the visual effect `DisplayItem`s generated by
`paint_visual_effects` don't do anything, because most elements don't have
a transform, oapcity or blend mode.] That way, printing out the display list
will skip irrelevant visual effects.

``` {.python expected=False}
class DisplayItem:
    def __init__(cmds=None, is_noop=False):
        self.cmds = cmds
        self.noop = is_noop

    def is_noop():
        return self.noop;

    def repr_recursive(self, indent=0):
        inner = ""
        if self.cmds:
            for cmd in self.cmds:
                inner += cmd.repr_recursive(indent + 2, include_noop)
        return ("{indentation}{repr}"").format(
            indentation=" " * indent,
            repr=self.__repr__())
```

And add code to print it out after updating the display list, with something
like:

    for item in self.display_list:
        print(item.repr_recursive())

When run on the [opacity transition
example](examples/example13-opacity-transition.html) before the animation has
begun, it should print something like:

    SaveLayer(alpha=0.999): bounds=Rect(13, 18, 787, 40.3438)
        DrawText(text=Test): bounds=Rect(13, 21.6211, 44, 39.4961)

Now that we can see the example, it seems pretty clear that we should make
a surface for the contents of the opacity `SaveLayer`, in this case containing
only a `DrawText`. In more complicated examples, it could have any number of
display list commands.^[Note that this is *not* the same as "cache the display
list for a DOM element subtree". To see why, consider that a single
DOM element can result in more than one `SaveLayer`, such as when it has
both opacity *and* a transform.]

Putting the `DrawText` into its own surface sounds simple enough: just make a
surface and raster that sub-piece of the display list into it, then draw that
surface into its "parent" surface. In this example, the resulting code to draw
the child surface should ultimately boil down to something like this:

    opacity_surface = skia.Surface(...)
    draw_text.execute(opacity_surface.getCanvas())
    tab_canvas.saveLayer(paint=sk_paint)
    opacity_surface.draw(tab_canvas, text_offset_x, text_offset_y)
    tab_canvas.restore()

Let's unpack what is going on in this code. First, raster `opacity_surface`.
Then create a new conceptual
"surface" on the Skia stack via `saveLayer`, then draw `opacity_surface`,
and finally `restore`. Observe how this is
*exactly* the way we described how it conceptually works *within* Skia
in [Chapter 11](visual-effects.html#blending-and-stacking). The only
difference is that here it's explicit that there is a `skia.Surface` between
the `saveLayer` and the `restore`.
Note also how we are using the `draw` method on `skia.Surface`, the very same
method we already use in `Browser.draw` to draw the surface to the screen.
In essence, we've moved a `saveLayer` command from the `raster` stage
to the `draw` stage of the pipeline.

In a way, we're implementing a way to put "subtrees of the display list" into
different surfaces. But it's not quite just subtrees, because multiple nested
DOM nodes could be simultaneously animating, and we can't put the same subtree
in two different surfaces. We *could* potentially handle cases like this by
making a tree of `skia.Surface` object. But it turns out that that approach
pgets quite complicated when you get into the details.^[We'll cover one of these
details---overlap testing---later in the chapter. Another is that there may be
multiple "child" pieces of content, only some of which may be animating. There
even more in a real browser.]

Instead, think of the display list as a flat list of "leaf" *paint commands*
like `DrawText`.^[The tree of visual effects is applied to some of those paint
commands, but ignore that for now and focus on the paint commands.] Each paint
command can be (individually) drawn to the screen by executing it and the
series of *ancestor [visual] effects* on it. Thus the tuple `(paint command,
ancestor effects)` suffices to describe that paint command in isolation.

We'll call this tuple a *paint chunk*. Here is how to generate all the paint
chunks from a display list:

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

When combined together, multiple paint chunks form a *composited layer*,
represented by the `CompositedLayer` class. This class will own a
`skia.Surface` that rasters its content, and also know how to draw
the result to the screen by applying an appropriate sequence of visual effects.

Two paint chunks in the flat list can be put into the same composited layer if
they are:

* adjacent in paint order,^[otherwise, overlapping content wouldn't draw
correctly] and

* have the exact same set of animating ancestor effects.^[otherwise the
  animations would end up applying to the wrong paint commands]

Notice that, to satisfy these constraints, we could just put each paint command
in its own composited layer. But of course, that would result in a huge number
of surfaces, and most likely exhaust the computer's GPU memory. So the goal of
the *compositing algorithm* is to come up with a way to pack paint chunks into
only a small number of composited layers.^[There are many possible compositing
algorithms, with their own tradeoffs of memory, time and code complexity. I'll
present the one used by Chromium.]

Below is the algorithm we'll use; as you can see it's not very complicated. It
loops over the list of paint chunks; for each paint chunk it tries to reuse an
existing `CompositedLayer` by walking *backwards* through the `CompositedLayer`
list. If one is found, the paint chunk is added to it; if not, a new
`CompositedLayer` is added with that paint chunk to start.
The `can_merge` method on a `CompositedLayer` checks compatibility of the paint
chunk's animating ancestor effects with the ones already on it.

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.composited_layers = []

    def composite(self):
        self.display_list = []
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

And drawing them to the screen will be like this:

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
Why is it that flattening a recursive display list into paint chunks is
possible? After all, visual effects in the DOM really are nested.

The implementation of `Browser.draw` in this section is
indeed incorrect for the case of nested visual effects (such as if there is a
composited animation on a DOM element underneath another one). To fix it
requires determining the necessary "draw hierarchy" of `CompositedLayer`s into
a tree based on their visual effect nesting, and allocating intermediate
GPU textures called *render surfaces* for each internal node of this tree.

A naive implementation of this tree (allocating one node for each visual effect)
is not too hard to implement, but each additional render surface requires a
*lot* more memory and slows down draw a bit more (this might a good time to
 re-read the start of the [GPU acceleration](#gpu-acceleration) section). So
 real browsers analyze the visual effect tree to determine which ones really
 need render surfaces, and which don't. Opacity, for example, often doesn't
 need a render surface, but opacity with at least two descendant
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

Chromium's implementation of the "visual effect nesting" data structure
is called [property trees][prop-trees]. The name is plural because there is
more than one tree, due to the complex containing block structure of scrolling
and clipping.

[renderingng-dl]: https://developer.chrome.com/blog/renderingng-data-structures/#display-lists-and-paint-chunks
[rendersurface]: https://developer.chrome.com/blog/renderingng-data-structures/#compositor-frames-surfaces-render-surfaces-and-gpu-texture-tiles
[prop-trees]: https://developer.chrome.com/blog/renderingng-data-structures/#property-trees

:::

Composited display items
========================

The first thing we'll need is a way to signal that a visual effect "needs
compositing", meaning that it is animating and so its contents should be cached
in a GPU texture. Indicate that with a new `needs_compositing` method on
`DisplayItem`. As a heuristic, we'll always composite transform and opacity
(but only when they actually do something that isn't a no-op), regardless of
whether they are animating.

``` {.python expected=False}
class DisplayItem:
    def needs_compositing(self):
        return not self.is_noop() and \
            (type(self) is Transform or type(self) is SaveLayer)
```

And while we're at it, add another `DisplayItem` constructor parameter
indicating the `node` that the `DisplayItem` belongs to (the one that painted
it); this will be useful when keeping track of mappinges betwen `DisplayItem`s
and GPU textures.[^cache-key]

[^cache-key]: Remember that these compositing GPU textures are simply a form of
cache, and every cache needs a stable cache key to be useful.

``` {.python expected=False}
class DisplayItem:
    def __init__(self, cmds=None, is_noop=False, node=None):
        # ...
        self.node = node
```

Next we need a `draw` draw. This only does something for visual effect
subclasses:

``` {.python}
class DisplayItem:
    def draw(self, canvas, op):
        pass
```

But for those it is like `execute`, except that it has a parameterized `op`
parameter. Here's `SaveLayer`:

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

For visual effects, we can then redefine `execute` in terms of draw; remove the
existing `execute` methods on those classes.

``` {.python}
class DisplayItem:
    def execute(self, canvas):
        assert self.cmds
        def op():
            for cmd in self.get_cmds():
                cmd.execute(canvas, True, False)
        self.draw(canvas, op, True)
```

The paint command subclasses like `DrawText` already define `execute`, which
will override this definition.

::: {.further}
But why composite always, and not just when the property is animating? It's
for two reasons.

First, we'll be able to start the animation quicker,
since raster won't have to happen first. (Note that whenever we change the 
compositing reasons or display list, we might have to re-raster a number of 
surfaces.)

Second, compositing sometimes has visual side-effects. Ideally, composited
textures would look exactly the same on the screen. But due to the details of
pixel-sensitive raster technologies like sub-pixel positioning for fonts, image
resize filter algorithms, and anti-aliasing, this isn't always possible.
"Pre-compositing" the content avoid visual jumps on the page when compositing
starts.

(A third reason is that having to deal with all of the permutations of
composited and non-composited objects requires a lot of attention to detail
and extra code to get right, so I omitted it from this book's code.)
:::

Composited Layers
=================

We're now ready to implement the `CompositedLayer` class. Start by defining
its member variables: a Skia context, surface, list of display items, ancestor
effects, and the "composited ancestor index".

``` {.python}
class CompositedLayer:
    def __init__(self, skia_context):
        self.skia_context = skia_context
        self.surface = None
        self.display_items = []
        self.ancestor_effects = None
        self.composited_ancestor_index = -1
```

The class will have the following methods:

* `add_display_item`: adds a display_item. The first one being added will
initialize the `composited_ancestor_index` of the `CompositedLayer`, which
is the index into `ancestor_effects` that is the "lowest" ancestor which 
needs compositing, or -1 otherwise.

``` {.python}
def composited_ancestor_index(ancestor_effects):
    count = len(ancestor_effects) - 1
    for ancestor_item in reversed(ancestor_effects):
        if ancestor_item.needs_compositing():
            return count
            break
        count -= 1
    return -1

class CompositedLayer:
    # ...
    def add_display_item(self, display_item, ancestor_effects):
        if len(self.display_items) == 0:
            self.composited_ancestor_index = \
                composited_ancestor_index(ancestor_effects)
            self.ancestor_effects = ancestor_effects
        self.display_items.append(display_item)
```

* `can_merge`: returns whether the `display_item` plus `ancestor_effects` passed
  as parameters are compatible with being drawn into the same
  `CompositedLayer`. This will be true if they has the same `composited_item`
  as the existing `DisplayItems`---i.e. it's animating the same visual effect,
  or none in the `CompositedLayer` are animating.[^not-animating]

``` {.python}
    def can_merge(self, display_item, ancestor_effects):
        if len(self.display_items) == 0:
            return True
        return  \
            self.composited_ancestor_index == \
            composited_ancestor_index(ancestor_effects)
```

[^not-animating]: Recall that there are two types of `CompositedLayer`s that
aren't animating: the root layer (what used to be called `tab_surface`), or
one that is created just because of overlap.

* `composited_bounds`: returns the union of the composited bounds of all
  `DisplayItem`s. The composited bounds of a `DisplayItem` is its bounds,
  plus all non-composited ancestor visual effects.

``` {.python}
def bounds(display_item, ancestor_effects, include_composited=False):
    retval = display_item.composited_bounds()
    for ancestor_item in reversed(ancestor_effects):
        if ancestor_item.needs_compositing() and \
            not include_composited:
            break
        if type(ancestor_item) is Transform:
            retval = ancestor_item.transform(retval)
    return retval

class CompositedLayer:
    # ...
    def composited_bounds(self):
        retval = skia.Rect.MakeEmpty()
        for item in self.display_items:
            retval.join(bounds(item, self.ancestor_effects,
                include_composited=False))
        return retval
```

On the `CompositedLayer` class we'll need:

* `absolute_bounds`: returns the union of the absolute bounds of all
`DisplayItems`. This is like `composited_bounds`, except that all ancestor
visual effects are applied. So these bounds are the bounds relative
to the top-left point of `tab_surface`. This will help us know the scroll height
of the web page.

``` {.python}
    def absolute_bounds(self):
        retval = skia.Rect.MakeEmpty()
        for item in self.display_items:
            retval.join(bounds(item, self.ancestor_effects,
                include_composited=True))
        return retval
```

* `composited_item`: returns the ancestor effect that is composited, or `None`
if none is.

``` {.python}
    def composited_item(self):
        if self.composited_ancestor_index < 0:
            return None
        return self.ancestor_effects[self.composited_ancestor_index]
```

* `composited_items`: returns a list of all ancestor visual effects that are
  composited.


``` {.python}
    def composited_items(self):
        items = []
        for item in reversed(self.ancestor_effects):
            if item.needs_compositing():
                items.append(item)
        return items
```

* `raster`: rasters the chunks into `self.surface`. Note that there is no
  parameter to this method, because raster of a `CompositdLayer` is
  self-contained. Note that we first translate by the `top` and `left` of the
  composited bounds. That's because we should allocate a surface exactly sized
  to the width and height of the bounds; its top/left is just a positioning
  offset. (It will be taken into acocunt in `draw`; see below.)

``` {.python}
    def draw_internal(self, canvas, op, start, end):
        if start == end:
            op()
        else:
            ancestor_item = self.ancestor_effects[start]
            def recurse_op():
                self.draw_internal(canvas, op, start + 1, end)
            ancestor_item.draw(canvas, recurse_op)

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
        for item in self.display_items:
            def op():
                item.execute(canvas)
            self.draw_internal(
                canvas, op, self.composited_ancestor_index + 1,
                len(self.ancestor_effects))
        canvas.restore()
```

* `draw`: draws `self.surface` to the screen, taking into account the visual
  effects applied to each chunk. (Note that because of the definition of
  `can_merge`, all the `DisplayItem`s will have the same visual effects, which
  is why we can do this to the surface and not each chunk individually.)


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

        canvas.save()
        canvas.translate(draw_offset_x, draw_offset_y)
        if self.composited_ancestor_index >= 0:
            self.draw_internal(
                canvas, op, 0, self.composited_ancestor_index + 1)
        else:
            op()
        canvas.restore()
```

The last bit to make the code work end-to-end is a new `Browser.composite`
method, and to generalize to `composite_raster_and_draw` (plus renaming the
corresponding dirty bit and renaming at all callsites), and everything should
work end-to-end.

``` {.python expected=False}
    def composite(self):
        self.composited_layers = do_compositing(
            self.active_tab_display_list, self.skia_context)

        self.active_tab_height = 0
        for layer in self.composited_layers:
            self.active_tab_height = \
                max(self.active_tab_height,
                    layer.absolute_bounds().bottom())

    def composite_raster_and_draw(self):
        self.lock.acquire(blocking=True)
        if not self.needs_composite_raster_draw:
            self.lock.release()
            return

        self.measure_composite_raster_and_draw.start()
        start_time = time.time()
        self.composite()
        self.raster_chrome()
        self.raster_tab()
        self.draw()
        self.measure_composite_raster_and_draw.stop()
        self.needs_composite_raster_draw = False
        self.lock.release()
```

Composited animations
=====================

Compositing now works, but it doesn't yet achieve the goal of avoiding raster
during animations. In fact, at the moment it's *slower* than before, because
the compositing algorithm---and use of the GPU---is not free, if you have
to constantly re-upload display lists and re-raster all the time.

Avoiding raster (and also the compositing algorithm) is relatively simple in
concept: keep track of what is animating, and re-run `draw` with different
visual effect transform or opacity parameters on the `CompositedLayer`s that
are animating.

Let's accomplish that. It will have multiple parts, starting with the main
thread.

* If an animation is running, and it's the only thing happening to the DOM, then
  only re-do `paint` (in order to update the animated `DisplayItem`s). For
  this, add a `needs_paint` dirty bit (`needs_layout` will also need to set
  `needs_paint`):

``` {.python}
class Tab:
    def __init__(self, browser):
        self.needs_paint = False

    def set_needs_layout(self):
        self.needs_layout = True
        self.needs_paint = True
        self.browser.set_needs_animation_frame(self)

    def render(self):
        if not self.needs_render \
            and not self.needs_layout \
            and not self.needs_paint:
            return

        self.measure_render.start()

        if self.needs_render:
            style(self.nodes, sorted(self.rules,
                key=cascade_priority), self)

        if self.needs_layout:
            # ...
            self.document.layout()
        
        if self.needs_paint:
            self.display_list = []

            self.document.paint(self.display_list)
            # ...
        self.needs_layout = False
        self.needs_paint = False

        self.measure_render.stop()
```

and a method that sets it:

``` {.python}
class Tab:
   def set_needs_animation(self, node, property_name, is_composited):
        if is_composited:
            self.needs_paint = True
            # ...
            self.browser.set_needs_animation_frame(self)
        else:
            self.set_needs_layout()
```

and to call `set_needs_animation` from animation instead of `set_needs_render`:

``` {.python expected=False}
class NumericAnimation:
    # ...
    def animate(self):
        # ...
        self.tab.set_needs_animation(self.node, self.property_name,
            self.property_name == "opacity")

class TranslationAnimation:
    # ...
    def animate(self):
        # ...
        self.tab.set_needs_animation(self.node, "transform", True)
```

* Save off each `Element` that updates its composited animation, in a new
array called `composited_animation_updates`:

``` {.python}
class Tab:
    def __init__(self, browser):
        # ...
        self.composited_animation_updates = []

    def set_needs_animation(self, node, property_name, is_composited):
        if is_composited:
            # ...
            self.composited_animation_updates.append(node)
```

* When running animation frames, if only `needs_paint` is true, then compositing
is not needed, and each animation in `composited_animation_updates` can be
committed across to the browser thread. Also, rename `CommitForRaster` to
`CommitData`, because raster is not necessarily going to happen:

``` {.python}

    def run_animation_frame(self, scroll):
        # ...
        needs_composite = self.needs_render or self.needs_layout

        self.render()

        composited_updates = []
        if not needs_composite:
            for node in self.composited_animation_updates:
                composited_updates.append(
                    (node, node.transform, node.save_layer))
        self.composited_animation_updates.clear()

        commit_data = CommitData(
            # ...
            composited_updates=composited_updates,
        )
```

* Add `needs_composite`, `needs_raster` and `needs_draw` dirty bits and
  correspondiing `set_needs_composite`, `set_needs_raster`, and
  `set_needs_draw` methods (and remove the old
  `needs_raster_and_draw` dirty bit):

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.needs_composite = False
        self.needs_raster = False

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

* Use the passed data in `commit` to decide wheter to  call
  `set_needs_composite` or `set_needs_draw`, and store off the updates in
  `compostited_upates`:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.needs_composite = False
        # ...
        self.composited_updates = []

    def commit(self, tab, data):
        # ...
        if tab == self.tabs[self.active_tab]:
            # ...
            self.composited_updates = data.composited_updates
            if len(self.composited_layers) == 0:
                self.set_needs_composite()
            else:
                self.set_needs_draw()
```

* Now for the actual animation updates: if `needs_composite` is false, loop over
  each `CompositedLayer`'s `composited_items`, and update each one that matches
  the animation (by comparing the `Element` pointers for the animation's DOM
  node).

``` {.python}
    def composite(self):
        if self.needs_composite:
            # ...
        else:
            for (node, transform,
                save_layer) in self.composited_updates:
                success = False
                for layer in self.composited_layers:
                    composited_items = layer.composited_items()
                    for composited_item in composited_items:
                        if type(composited_item) is Transform:
                            composited_item.copy(transform)
                            success = True
                        elif type(composited_item) is SaveLayer:
                            composited_item.copy(save_layer)
                            success = True
                assert success
```

The result will be automatically drawn to the screen, because the `draw` method
on each `CompositedLayer` will iterate through its `composited_items` and
execute them.

Now check out the result---animations that only update the draw step, and
not everything else!

::: {.further}
Threaded animations (exercise).

Rastering only some content, partial raster, partial draw.
:::

Transform animations
====================

The `transform` CSS property lets you apply linear transform visual
effects to an element.[^not-always-visual] In general, you can apply
[any linear transform][transform-def] in 3D space, but I'll just cover really
basic 2D translations. Here's HTML for the overlap example mentioned in the
last section:

[^not-always-visual]: Technically it's not always just a visual effect. In
real browsers, transformed element positions contribute to scrolling overflow.

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
space-separated sequence; the end result is the composition of the transform.
I won't implement that, just like I didn't implement many other parts of the
standardized transform syntax.

``` {.python}
def parse_transform(transform_str):
    if transform_str.find('translate') < 0:
        return None
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
TODO:verify that translation does indeed come after blending.

The `Transform` display list command is pretty straightforward as well: it calls
the `translate` Skia canvas method, which s conveniently built-in.

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
```

Now that we can render transforms, we also need to animate them. Similar
to `try_numeric_animation`, add a `try_transform_animation` method:

``` {.python}
def try_transform_animation(node, old_style, new_style, tab):
    num_frames = try_transition("transform", node,
    old_style, new_style)
    if num_frames == None:
        return None;

    old_translation = parse_transform(old_style["transform"])
    new_translation = parse_transform(new_style["transform"])

    if old_translation == None or new_translation == None:
        return None

    if not node in tab.animations:
        tab.animations[node] = {}
    tab.animations[node]["transform"] = TranslateAnimation(
        node, old_translation, new_translation, num_frames, tab)
```

And `TranslateAnimation`:


``` {.python expected=False}
class TranslateAnimation:
    def __init__(
        self, node, old_translation, new_translation,
        num_frames, tab):
        self.node = node
        (self.old_x, self.old_y) = old_translation
        (new_x, new_y) = new_translation
        self.change_per_frame_x = (new_x - self.old_x) / num_frames
        self.change_per_frame_y = (new_y - self.old_y) / num_frames
        self.num_frames = num_frames
        self.tab = tab
        self.frame_count = 0
        self.animate()

    def animate(self):
        self.frame_count += 1
        if self.frame_count >= self.num_frames: return False
        self.node.style["transform"] = \
            "translate({}px,{}px)".format(
                self.old_x +
                self.change_per_frame_x * self.frame_count,
                self.old_y +
                self.change_per_frame_y * self.frame_count)
        self.tab.set_needs_render()
        return True
```

You should now be able to create this animation with your browser:

<iframe src="examples/example13-transform-transition.html" style="width:350px;height:450px">
</iframe>
(click [here](examples/example13-transform-transition.html) to load the example in
your browser)

But if you try it, you'll find that the animation looks wrong---the blue
rectangle is supposed to be *under* the green one, but now it's on top. That's
because it is drawn into its own surface that is then drawn on top of the
other surface. To fix that requires yet more surfaces, plus overlap testing.

Overlap testing
===============

The main difficulty with implementing compositing turns out to be dealing
with its *side-effects for overlapping content*. To understand the concept,
consider this simple example of a green square overlapped by an blue one,
except that the blue one is *earlier* in the DOM painting order.

<div style="width:200px;height:200px;background-color:lightblue;transform:translate(50px,50px)"></div>
<div style="width:200px;height:200px;background-color:lightgreen; transform:translate(0px,0px)"></div>

Suppose we want to animate opacity on the blue square, and so allocate a
`skia.Surface` and GPU texture for it. But we don't want to animate the green
square, so it is supposed to draw to the screen without opacity change.
But how can that work? How can we make it paint on top of this new surface?
Two things we could do are: start painting the green
square *before* the blue one, or re-raster the green square into the
root surface on every frame, after drawing the blue square.

The former is obviously not ok, because we can't just ignore the website
developer's wishes and paint in the wrong order. The latter is *also* not ok,
because it negates the first benefit of compositing (avoiding raster).

So we have to choose a third option: allocating a `skia.Surface` for the
green rectangle as well. This is called an *overlap reason* for compositing.
Overlap makes compositing algorithms signficantly more complicated, because
when allocating a surface for animated content, we'll have to check the
remainder of the display list for potential overlaps.

Next we'll need to be able to get the *composited bounds* of a `DisplayItem`.
Its composited bounds is the union of its painting rectangle and all
descendants that are not themselves composited. This will be needed to
determine the absolute bounds of a `CompositedLayer`. This is pretty easy---there is
already a `rect` field stored on the various subclasses, so just pass them to
the superclass instead:

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

The other classes are basically the same, including `SaveLayer` and `transform`.

The `Transform` class is special: it is the only subclass of
`DisplayItem` that can *move pixels*---cause other `DisplayItem`s to draw in
some new location other than its bounding rectangle. For this reason, we
will need a method on it to determine the new rectangle after appling the
translation transform:

``` {.python expected=False}
class Transform:
    # ...
    def transform(self, rect):
        if not self.translation:
            return rect
        matrix = skia.Matrix()
        if self.translation:
            (x, y) = self.translation
            matrix.setTranslate(x, y)
        return matrix.mapRect(rect)
```

TODO: implement abs bounds for a transform animation that takes into account
the path traveled.

::: {.further}
TODO: describe the problem of layer explosion. Explain how this can actually
lead to compositing slowing down a web page rather than speeding it up.
:::

Composited scrolling
====================

The last category of animations we haven't covered is the *input-driven* ones,
such as scrolling. I introduced this category of animations earlier, but didn't
really explain in much detail why it makes sense to categorize scrolling as
an *animation*. In my mind, there are two key reasons:

* Scrolling often continues after the input is done. For example, most browsers
  animate scroll in a smooth way when scrolling by keyboard or scrollbar
  clicks. Another example is that in a touch-driven scroll, browsers interpret
  the touch movement as a gesture with velocity, and therefore continue the
  scroll according to a physics-based model (with friction slowing it down).

* Touch or mouse drag-based scrolling is very performance sensitive. This is
  because humans are much more sensitive to things keeping up with the movement
  of their hand than they are to the latency of responding to a click. For
  example, a scrolling hiccup for even one frame, even for only a few tens of
  milliseconds, is easily noticeable and jarring to= a person, but most people
  do not able to perceive click input delays of about to 100ms or so in a
  negative way.

Let's add composited scrolling to our browser, and then smooth scrolling on
keyboard events.

Composited scrolling will be extremely easy, because thanks
to [Chapter 12](#threaded-scrolling), we have threaded scrolling already,
and the `scroll` offset is already present on `Browser`.
All we have to do is replace `set_needs_raster` with `set_needs_draw`:

``` {.python}
class Browser:
    # ...
    def handle_down(self):
        # ...
        self.set_needs_draw() 
```

Smooth scrolling will have a few steps. First we'll have to parse the new CSS
property that applies to scrolling of the `<body>` element[^body], plumb it to
the browser thread, and then animate in `Browser.handle_down`. The animation
will run an `ScrollAnimation` that is very similar on the main
thread. [^threaded]

[^body]: The difference between the `<body>` and `<html>` tag for scrolling is a
[little complicated][scrollingelement], and I won't get into it here.

[scrollingelement]: https://developer.mozilla.org/en-US/docs/Web/API/document/scrollingElement

[^threaded]: And with some more work, the animation could run on the browser
thread and avoid main-thread delay. I'll leave that to an exercise.

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

* Initiating smoooth scroll from the browser thread:

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
        if not self.scroll_changed_in_tab:
            if scroll != self.scroll and not self.scroll_animation:
                if self.scroll_behavior == 'smooth':
                    self.scroll_animation = ScrollAnimation(
                        self.scroll, scroll, self)
                else:
                    self.scroll = scroll
        # ...

        if self.scroll_animation:
            if not self.scroll_animation.animate():
                self.scroll_animation = None
```

* Implementing `ScrollAnimation`:

``` {.python}
class ScrollAnimation:
    def __init__(
        self, old_scroll, new_scroll, tab):
        self.old_scroll = old_scroll
        self.new_scroll = new_scroll
        self.num_frames = 30
        self.change_per_frame = \
            (new_scroll - old_scroll) / self.num_frames
        self.tab = tab
        self.frame_count = 0
        self.animate()

    def animate(self):
        self.frame_count += 1
        if self.frame_count >= self.num_frames: return False
        updated_value = self.old_scroll + \
            self.change_per_frame * self.frame_count
        self.tab.scroll = updated_value
        self.tab.scroll_changed_in_tab = True
        self.tab.browser.set_needs_animation_frame(self)
        return True
```

Yay, smooth scrolling! You can try it on
[this example](examples/example13-transform-transition.html), which combines
a smooth scroll and transform animation at the same time. And it's got
super smooth animation performance!

::: {.further}
parallax, scroll-linked effects
:::

Summary
=======

This chapter introduced the concept of animations. The key takeaways should be:

- Animations come in DOM-based, input-driven and video-like varieties

- Animations can be *layout-inducing* or *visual effect only*, and the
  difference has important performance and animation quality implications

- GPU acceleration is necessary for smooth animations

- Compositing is necessary for smooth visual effect animations

We then proceed to implement GPU acceleration and composited animations.

Finally, we briefly touched on *input-driven* animations, and showed how to
implement smooth scrolling.

Outline
=======

The complete set of functions, classes, and methods in our browser 
should now look something like this:

::: {.cmd .python .outline html=True}
    python3 infra/outlines.py --html src/lab13.py
:::

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

*Render surfaces*: as described in the go-further block at the end of
 [this section](#implementing-compositing), our browser doesn't currently draw
 nested, composited visual effects correctly. Fix this by building a "draw
 tree" for all of the `CompositedLayer`s and allocating a `skia.Surface` for
 each internal node.
