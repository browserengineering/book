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
animates from 1 to 0.1, over 120 frames (about two seconds), then back up
to 1 for 120 more frames, and repeats.

``` {.html file=example-opacity-html}
<div>Test</div>
```

``` {.javascript file=example-opacity-js}
var start_value = 1;
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
new values, in basically the same way the `requestAnimationFrame` loop did it.
This is much more convenient for website authors than writing a bunch of
JavaScript, and also doesn't force them to account for each and every way in
which the styles can change.

<iframe src="examples/example13-opacity-transition.html"></iframe>
(click [here](examples/example13-opacity-raf.html) to load the example in
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
interpretation (also called an *easing function*. By default, real browsers
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
        self.tab.set_needs_render()
        return True
```

Now for integrating this code into rendering. It has main parts: detecting style
changes, and executing the animation. Both have some details that are important
to get right, but are conceptually straightforward:

First, in the `style` function, when a DOM node changes its style, check to see
if one or more of the properties with registered transitions are changed; if
so, start a new animation and add it to the `animations` dictionary on the
`Tab`. This logic will be in a new function called `animate_style`, which is
called just after the style update for `node` is complete:

``` {.python}
def style(node, rules, tab):
    old_style = None
    if hasattr(node, 'style'):
        old_style = node.style

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

Second; in `run_animation_frame` on the `Tab`, each animation in `animations`
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

GPU acceleration
================

The first order of business in making these animations smoother is to move
raster and draw to the [GPU][gpu]. Because both SDL and Skia support these
modes, the code to do so looks a lot like some configuration changes, and
doesn't really give any direct insight into why it's all-of-a-sudden faster. So
before showing the code let's discuss briefly how GPUs work and the four
(again, internal implementation detail to Skia and SDL) steps of running GPU
raster and draw.

There are lots of resources online about how GPUs work and how to program them;
we won't generally be writing shaders or other types of GPU programs in this
book. Instead, let's focus on the basics of GPU technologies and how they
map to browsers. A GPU is essentially a hyper-specialized computer that is
good at running very simple computer programs that specialize in turning
simple data structures into pixels. These programs are so simple that the
GPU can run one of them *in parallel* for each pixel, and this parallelism is
why GPU raster is usually much faster than CPU raster.

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
or to an *intermediate texture*.[^gpu-texture]. Draw proceeds bottom-up: the
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
one constant actually). Install the library:

    pip3 install PyOpenGL

and then import it:

``` {.python}
from OpenGL import GL
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
backing.(There are no changes at all required to raster). All you have to do
is *flush* the Skia surface and call `SDL_GL_SwapWindow` to activate the new
framebuffer (because of OpenGL [double-buffering][double]).

[double]: https://wiki.libsdl.org/SDL_GL_SwapWindow

``` {python}
    def draw(self):
        canvas = self.root_surface.getCanvas()

        # ...

        self.root_surface.flushAndSubmit()
        sdl2.SDL_GL_SwapWindow(self.sdl_window)
```

With this change, on my computer raster and draw are about three times as fast
as before. If you're on a computer with a non-virtualized GL driver you will
probably see even more speedup than that.

Let's go back and test the `opacity` and `width` animations, to see how much GPU
acceleration helped. The results on my computer are:[^same-perf]

    Without GPU:

    Time in raster-and-draw on average: 22ms
    Time in render on average: 1ms

    With GPU:

    Time in raster-and-draw on average: 8ms
    Time in render on average: 1ms

[^same-perf]: It turns out the cost is about the same for both threads in this
case, because the size of the DOM is so small.

So GPU acceleration yields something like a 60% reduction in browser thread
time. This is a great improvement, but still 8ms is a lot for such a simple
example, and also requires a main-thread task that might be slowed down by
JavaScript. Can we do better? Yes we can, by using compositing.

Why Compositing
===============

The term [*compositing*][compositing] means to combine multiple images together
into a final output. As it relates to browsers, it usually means the
performance optimization technique of caching rastered GPU textures that are
the inputs to animated[visual effects](visual-effects.md).

[compositing]: https://en.wikipedia.org/wiki/Compositing

Let's unpack that into simpler terms with an example. Opacity is one kind of
visual effect. When we're animating it, the opacity is changing, but the
"DOM content"[^more-precise] underneath it
is not. So let's stop re-rastering that content on every frame of the
animation, and instead cache it in a GPU texture. This *should* directly
reduce raster-and-draw work because less raster work will be needed on each
animation frame.

[^more-precise]: We'll be precise about what exactly is cached in a moment;
suffice it to say that it's *not* "rendering only some DOM elements".

But there's actually another benefit that is just as important: we can run the
animation entirely off the main thread. That's because the browser thread can
play tricks to save off intermediate GPU textures from a display list.[^not-dom]
I'll show you one way how.^[Since you already learned in chapter 11
that Skia often creates GPU textures for [various intermediate
surfaces](visual-effects.html#blending-and-stacking), it is hopefully clear
that it *should* be possible to do this.]

[^not-dom]: On the other hand, the browser thread does *not* have the ability
to do something with the DOM or JavaScript.

You might think that Skia has ways to say "please cache this surface". And there
is---the way is for the user of Skia to keep around a `skia.Surface` across
multiple raster-and-draw executions.^[Skia will keep alive the rastered content
associated with the surface] In other words, we'll need to do the caching
ourselves, and this feature is not built into Skia itself in a simple-to-use
form.

The main difficulty with implementing compositing turns out to be dealing
with its *side-effects for overlapping content*. To understand the concept,
consider this simple example of a blue square overlapped by an green one.

<div style="width:200px;height:200px;background-color:lightblue"></div>
<div style="width:200px;height:200px;background-color:lightgreen;transform:translate(100px, -100px)"></div>

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

We're now ready to start digging into the compositing algorithm and how to
implement it, except for one thing: there is no way in our current browser for
content to overlap! The example in this section used the `transform` CSS
property, which is not yet present in our browser. Because of that, and also
because transforms are a common visual effect animation on websites, let's
implement that and then come back to implementing compositing.

::: {.further}
TODO: describe the problem of layer explosion. Explain how this can actually
lead to compositing slowing down a web page rather than speeding it up.
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
                background-color:lightblue"></div>
    <div style="width:200px;height:200px;
                background-color:lightgreen;
                transform:translate(100px, -100px)"></div>

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


Implementing compositing
========================

Implement the compositing algorithm.

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