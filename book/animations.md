---
title: Animations and Compositing
chapter: 13
prev: scheduling
next: skipped
...

Complex web application use *animations* when transitioning between
DOM states. These transitions improve usability by helping users
understand what changes are occurring. They also improve visual polish
by replacing sudden jumps with gradual changes. But to execute these
animations smoothly, the browser must make use of the computer's GPU
and minimize work using compositing.

JavaScript Animations
=====================

An [animation] is a sequence of still pictures shown in quick
succession that create an illusion of *movement* to the human
eye.[^general-movement] Web pages typically animate effects like
changing color, fading an element in or out, or resizing an element.
Browsers also use animations in response to user actions like
scrolling, resizing, and pinch-zoom. And some types of animated media,
like videos, can also be included in web pages.[^video-anim] In this
chapter we'll focus mostly on web page animations, though we'll touch
on scrolling at the end.

[^general-movement]: Here *movement* should be construed broadly to
encompass all of the kinds of visual changes humans are used to seeing
and good at recognizing---not just movement from side to side, but
growing, shrinking, rotating, fading, blurring, and sharpening. The
point is that an animation is not an *arbitrary* sequence of pictures;
the sequence must feel continuous to a human mind trained by experience in the
real world.

[animation]: https://en.wikipedia.org/wiki/Animation

[^video-anim]: Video-like animations also include animated images, and
animated canvases. Since our browser doesn't support images, this
topic is beyond the scope of this book, but it has its own
[fascinating complexities][videong].

[videong]: https://developer.chrome.com/blog/videong/

Let's write a simple animation using the `requestAnimationFrame` API
[implemented in Chapter 12](scheduling.md#animating-frames). This
animation lets us request that some JavaScript code run on the next
frame, and we can have that code change the page slightly.
To do this repeatedly, we'll need code like this:

``` {.javascript file=example-opacity-js replace=animate/fade_out,animation_frame/fade_out}
function run_animation_frame() {
    if (animate())
        requestAnimationFrame(run_animation_frame);
}
requestAnimationFrame(run_animation_frame);
```

Here `animate` makes some small change to the page to give the
impression of continuous change. It returns `true` until it's done
animating, and then stops. By changing what `animate` does we can
change what animation occurs.

Let's write a fade animation. We can fade in something out by smoothly
transitioning its `opacity` value from 0.1 to 0.999.[^why-not-one] If we
want to do this animation over 120 frames (about two seconds), that
means we need to increase the opacity by about 0.008 on each frame.

[^why-not-one]: Real browsers apply certain optimizations when opacity
is exactly 1, so real-world websites often start and end animations at
0.999 so that each frame is drawn the same way and the animation is
smooth. Starting animations at 0.999 is also a common trick used on
web sites that want to avoid visual popping of the content as it goes
in and out of GPU-accelerated mode. I chose 0.999 because the visual
difference from 1.0 is imperceptible.

For example, let's animate this `div` containing the word "Test":

``` {.html file=example-opacity-html}
<div>This text fades out</div>
```

The `animate` function will track how many frames have occurred and 

``` {.javascript file=example-opacity-js replace=animate/fade_in}
var div = document.querySelectorAll("div")[0];
var total_frames = 120;
var current_frame = 0;
var change_per_frame = (0.999 - 0.1) / total_frames;
function animate() {
    current_frame++;
    var new_opacity = current_frame * change_per_frame + 0.1;
    div.style = "opacity:" + new_opacity;
    return current_frame < total_frames;
}
```

You could, of course, fade the text out by making `change_per_frame`
negative. Here's how it looks; click the buttons to start a fade:

<iframe src="examples/example13-opacity-raf.html"></iframe>

This animation will almost run in our browser, except that our browser
doesn't yet support JavaScript changing an element's `style`
attribute. Let's go ahead and add that feature. Register
a setter on the `style` attribute of `Node` in the JavaScript runtime:

``` {.javascript file=runtime}
Object.defineProperty(Node.prototype, 'style', {
    set: function(s) {
        call_python("style_set", this.handle, s.toString());
    }
});
```

Then, inside the browser, define a handler for `style_set`:

``` {.python}
class JSContext:
    def __init__(self, tab):
        # ...
        self.interp.export_function("style_set", self.style_set)

     def style_set(self, handle, s):
        elt = self.handle_to_node[handle]
        elt.attributes["style"] = s;
        self.tab.set_needs_render()
```

Note that the `style_set` function sets the `needs_render` flag. That
makes sure that the browser re-renders the web page with the new
`style` parameter, and therefore shows the user the word "Test" slowly
fading into view.

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


::: {.further}

Opacity is a special kind of CSS filter. And where it makes sense, other filters
that parameterize on some numeric input (such as [blur]) can also be animated
just as easily. And as we'll see, all of them can be optimized to avoid raster
entirely during the animation.

Likewise, certain paint-only effects such as color and background-color are also
possible to animate, since colors are numeric and can be interpolated. (In that
case, each color channel is interpolated independently.) These are also
visual effects, but not quite of the same character, because background color
doesn't apply a visual effect to a whole DOM subtree. It's instead a display
list parameter that happens not to cause layout, but generally still
needs raster. This makes them harder to optimize.

:::

[blur]: https://developer.mozilla.org/en-US/docs/Web/CSS/filter-function/blur

GPU acceleration
================

If you try the fade animation in our browser, you'll probably notice
that it's not particularly smooth. And that shouldn't be surprising;
after all, [last chapter](scheduling.md#profiling-rendering) had the
following figures for our browser:

    Time in raster-and-draw on average: 66ms
    Time in render on average: 23ms

With 66ms per frame, our browser is barely doing fifteen frames per
second, not sixty. For smooth animations we'll need to speed up raster
and draw.

The best way to do that is to move raster and draw to the [GPU][gpu].
A GPU is essentially a chip in your computer that runs programs, much
like your CPU. But the GPU is specialized toward running very simple
programs with massive parallelism; it was developed to apply simple
operations, in parallel, for every pixel on the screen. This makes GPUs faster for
drawing simple shapes and *much* faster for applying visual effects.

At a high level, to raster and draw on the GPU our browser
must:[^gpu-variations]

[^gpu-variations]: These steps vary a bit in the details by GPU architecture.

* *Upload* the display list to specialized GPU memory.

* *Compile* GPU programs that raster and draw the display list.[^compiled-gpu]

[^compiled-gpu]: That's right, GPU programs are dynamically compiled! This
allows GPU programs to be portable across a wide variety of implementations
that may have very different instruction sets or acceleration tactics.
Of course, between frames these compiled programs will typically be
cached, so this step won't occur on every frame.

* *Raster* every drawing command into GPU textures.[^texture]

[^texture]: A surface represented on the GPU is called a *texture*. There can be
more than one texture, and practically speaking they often can't be rastered in
parallel with each other.

* *Draw* the textures onto the screen.

SDL and Skia support all of these steps---in fact, it's mostly a
matter of passing them the right parameters. Let's do that. Note that
a real browser typically implements both CPU and GPU raster and draw,
because in some cases CPU raster and draw can be faster than using the
GPU.[^example-cpu-fast] In our browser, for simplicity, we'll stick
to GPU mode for all pages.

[^example-cpu-fast]: Any of the four steps can make GPU raster and
 draw slow. Large display lists take a while to upload. Complex
 display list commands take longer to compile. Raster can be slow if
 there are many surfaces, and draw can be slow if surfaces are deeply
 nested. On a CPU, the upload step and compile steps aren't necessary,
 and more memory is available for raster and draw. Of course, many
 optimizations are available for both GPU and CPU, so choosing the
 best way to raster and draw a given page can be quite complex.

[gpu]: https://en.wikipedia.org/wiki/Graphics_processing_unit

First we'll need to install the OpenGL library:

    pip3 install PyOpenGL

and import it:

``` {.python}
import OpenGL.GL as GL
```

Now we'll need to configure SDL to use OpenGL and and start/stop a [GL
context][glcontext] at the beginning/end of the program. For our
purposes, just consider this API boilerplate.[^glcontext]

[^glcontext]: Starting a GL context is just OpenGL's way of saying
"set up the surface into which subsequent GL drawing commands will
draw". After creating one you can even execute OpenGL commands
manually, [without using Skia at all][pyopengl], to draw polygons or
other objects on the screen.

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

I've made our browser print out the GPU vendor and renderer that it's
using; this will help you verify that it's actually using your GPU.
I'm using a Chromebook to write this chapter, so for me it
says:[^virgl]

    OpenGL initialized: vendor=b'Red Hat', renderer=b'virgl'

[^virgl]: The `virgl` renderer stands for "virtual GL", a way of
hardware-accelerating the Linux subsystem of ChromeOS that works with
the ChromeOS Linux sandbox. This is a bit slower than using the GPU
directly, so you'll probably see even faster raster and draw than I
do.

Now we can configure Skia to draw directly to the screen. The
incantation is:[^weird]

[^weird]: Weirdly, this code draws to the window without referencing
`gl_context` or `sdl_window` directly. That's because OpenGL is a
strange API with a lot of hidden global state; the `MakeGL` Skia
method implicitly binds to the existing GL context.

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

An extra advantage of this is that we won't need to copy data between
Skia and SDL anymore. All it has to do is *flush* the Skia surface
(Skia surfaces draw lazily) and call `SDL_GL_SwapWindow` to activate
the new framebuffer (because of OpenGL [double-buffering][double]):

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

Finally, our browser also creates a Skia surfaces for the
`chrome_surface` and `tab_surface`. We don't want to draw these
straight to the screen, so the incantation is a bit different:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.chrome_surface =  skia.Surface.MakeRenderTarget(
                self.skia_context, skia.Budgeted.kNo,
                skia.ImageInfo.MakeN32Premul(WIDTH, CHROME_PX))
        assert self.chrome_surface is not None
```

Again, you should think of these changes mostly as boilerplate, since
the details of GPU operation aren't our focus here.[^color-space] Make
sure to apply the same treatment to `tab_surface` (with different
width and height arguments).

[^color-space]: For example, a different color space that is required
for GPU mode.

Thanks to SDL's and Skia's thorough support for GPU rendering, that
should be all that's necessary for our browser to raster and draw on
the GPU. And as expected, speed is much improved:

    Time in raster-and-draw on average: 24ms
    Time in render on average: 23ms

That's about three times faster, almost fast enough to hit sixty
frames per second. And on your computer, you'll likely see even more
speedup than that, so perhaps your animations are already quite
smooth. But if we want to go faster yet, we'll need to reduce the
total amount of work in raster and draw.

::: {.further}

A high-speed, reliable and cross-platform GPU raster path in Skia has only
existed for a few years.[^timeline-gpu] In the very early days of Chromium,
there was only CPU raster. Scrolling was implemented much like in the early
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

Compositing
===========

So, how do we do less work in the raster and draw phase? The answer is
a technique called *compositing*, which just means caching some
rastered images on the GPU and reusing them during later
frames.[^compositing-def]

[^compositing-def]: The term [*compositing*][compositing] means
combining multiple images together into a final output. In browsers,
we're typically combining rastered images into the final image of the
page, but a similar technique is used in many operating systems to
combine the contents of multiple windows. "Compositing" can also refer
to multi-threaded rendering.

[compositing]: https://en.wikipedia.org/wiki/Compositing

To explain compositing, we'll need to think about our browser's display list,
and to do that it's useful to print it out. Printing it is going to require
similar code in every display command, so let's give a new `DisplayItem`
superclass to display commands. This makes it easy to create default behavior
that's overridden for specific display commands. For example, we can make sure
that every display command has a `children` field:

``` {.python replace=children=[]/rect%2c%20children=[]%2c%20node=None}
class DisplayItem:
    def __init__(self, children=[]):
        self.children = children
```

Each display command now needs to indicate the superclass when the
class is declared and use special syntax in the constructor:

``` {.python expected=False}
class DrawRect(DisplayItem):
    def __init__(self, x1, y1, x2, y2, color):
        super().__init__()
        # ...
```

Commands that already had a `children` field need to pass it to the
`__init__` call:

``` {.python replace=children=children/rect%2c%20children=children}
class ClipRRect(DisplayItem):
    def __init__(self, rect, radius, children, should_clip=True):
        super().__init__(children=children)
        # ...
```

To print the display list in a useful form, let's add a printable form
to each display command. For example, for `DrawRect` you might print:

``` {.python}
class DrawRect(DisplayItem):
    def __repr__(self):
        return ("DrawRect(top={} left={} " +
            "bottom={} right={} color={})").format(
            self.left, self.top, self.right,
            self.bottom, self.color)
```

Some of our display commands have a flag to do nothing, like
`ClipRRect`'s `should_clip` flag. It's useful to explicitly indicate
that:

``` {.python}
class ClipRRect(DisplayItem):
    def __repr__(self):
        if self.should_clip:
            return "ClipRRect({})".format(str(self.rrect))
        else:
            return "ClipRRect(<no-op>)"
```

Now we can print out our browser's display list:

``` {.python expected=False}
class Tab:
    def render(self):
        # ...
        for item in self.display_list:
            print_tree(item)
```

For our opacity example, the display list looks like this:

    SaveLayer(alpha=0.112375)
      DrawText(text=This)
      DrawText(text=text)
      DrawText(text=fades)

On the next frame, it instead looks like this:

    SaveLayer(alpha=0.119866666667)
      DrawText(text=This)
      DrawText(text=text)
      DrawText(text=fades)

In each case, rastering this display list means first drawing the three words to
a Skia surface created by `saveLayer`, and then copying that to the root
surface while applying transparency. Crucially, the drawing is identical in
both frames; only the copy differs. This means we can speed it up with
caching.

The idea is to first draw the three words to a separate surface (but this time
owned by us, not Skia), which we'll call a *composited layer*:

    Composited Layer 1:
      DrawText(text=This)
      DrawText(text=text)
      DrawText(text=fades)

Now instead of drawing those three words, we can just copy over the
layer:

    SaveLayer(alpha=0.112375)
      DrawCompositedLayer()

Importantly, on the next frame, the `SaveLayer` changes but the
`DrawText`s don't, so on the next frame all we need to do is rerun the
`SaveLayer`:

    SaveLayer(alpha=0.119866666667)
      DrawCompositedLayer()

In other words, the idea behind compositing is to split the display
list into two pieces: a set of composited layers, which are rastered
during the browser's raster phase and then cached, and a *draw display
list*, which is drawn during the browser's draw phase and which uses
the composited layers.

Compositing helps when different frames of the animation have the same
composited layers, which can then be reused, and only change the draw
display list. That's the case here, because the only difference
between frames is the `SaveLayer`, which is in the draw display list.
Now, a browser can choose what composited layers to create however it
wants. Typically visual effects like opacity are very fast to execute on a
GPU, but *paint commands* that draw shapes---in our browser,
`DrawText`, `DrawRect`, `DrawRRect`, and `DrawLine`---can be slower.[^many]
Since it's the visual effects that are typically animated, this means
browsers usually leave animated visual effects in the draw display list and move paint
commands into composited layers. Of course, in a real browser,
hardware capabilities, GPU memory, and application data all play into
these decisions, but the basic idea of compositing is the same no matter what
goes where.

[^many]: And there are usually a lot more of them to execute.

Some animations can't be composited because they affect more than just
the display tree. For example, imagine we animate the `width` of the
`div` above, instead of animating its opacity. Here's how it looks;
click the buttons to animate.

<iframe width=500 src="examples/example13-width-transition.html"></iframe>

Here, different frames have different *layout trees*, not just display
trees. That totally changes the coordinates for the `DrawText` calls,
and we wouldn't necessarily be able to reuse the composited layer.
Such animations are called *layout-inducing* and speeding them up
requires [different techniques](reflow.md).[^not-advisable]

[^not-advisable]: Because layout-inducing animations can't easily make use of
compositing, they're usually not a good idea on the web. Not only are they
slower, but they cause page elements to move around, often in sudden
jumps, meaning they don't create that illusion of continuous movement. An
exception is a layout-inducing animation when resizing a browser window via a
mouse gesture; in this case it's very useful for the user to see the new layout
as the window size changes. Modern browsers are fast enough to do this, but it
used to be that instead they would leave a visual *gutter* (a gap between
content and the edge of the window) during the animation, to avoid updating
layout on every animation frame.

::: {.further}

If you look closely at the example in this section, you'll see that the
`DrawText` command's rect is about 30 pixels wide. On the other hand, the
`SaveLayer` rect is almost as wide as the viewport. The reason they differ is
that the text is only about 30 pixels wide, but the block element that contains
it is as wide as the available width.

So does the composited surface need to be 30 pixels wide or the whole viewport?
In practice you could implement either. The algorithm presented in this chapter
ends up with the smaller one but real browsers sometimes choose the larger,
depending on their algorithm. Also note that if there was any kind of paint
command associated with the block element containing the text, such as a
background color, then the surface would definitely have to be as wide as the
viewport. Likewise, if there were multiple inline children, the union of their
bounds would contribute to the surface size.

:::

Compositing leaves
==================

Let's start implementing compositing. We'll put paint commands (the leaves of
the display list) in composited layers, and all other display items in the draw
display list. To do that we'll need to traverse the display list, identify all
paint commands, and move them to composited layers. Then we'll need to create
the draw display list that combines the composited layers.

Let's start by identifying paint commands with an `is_paint_command`
method. It'll return `False` for generic display items:

``` {.python}
class DisplayItem:
    def is_paint_command(self):
        return False
```

However, for the `DrawLine`, `DrawRRect`, `DrawRect`, and `DrawText`
commands it'll return `True` instead. For example, here's `DrawLine`:

``` {.python}
class DrawLine(DisplayItem):
    def is_paint_command(self):
        return True
```

We can now list all of the paint_commands using `tree_to_list`:

``` {.python expected=False}
class Browser:
    def composite(self):
        all_commands = []
        for cmd in self.active_tab_display_list:
            all_commands = tree_to_list(cmd, all_commands)
        paint_commands = [cmd
            for cmd in all_commands if cmd.is_paint_command()]
```

We now need to group paint commands into layers. For now, let's do the
simplest possible thing and put each paint command into its own
`CompositedLayer`:

``` {.python replace=paint_commands/non_composited_commands}
class Browser:
    def __init__(self):
        # ...
        self.composited_layers = []

    def composite(self):
        self.composited_layers = []
        # ...
        for display_item in paint_commands:
            layer = CompositedLayer(self.skia_context)
            layer.add(display_item)
            self.composited_layers.append(layer)
```

Here, a `CompositedLayer` just stores a list of display items (and a
surface that they'll be drawn to). The `add` method adds a paint command to
the list.^[For now, it's just one display item, but that will change pretty
soon.]

``` {.python}
class CompositedLayer:
    def __init__(self, skia_context):
        self.skia_context = skia_context
        self.surface = None
        self.display_items = []

    def add(self, display_item):
        self.display_items.append(display_item)
```

Now let's turn to the draw display list that contains the composited layers.
We'll build this by taking each composited layer we've generated and make a
recursive chain of all visual effects applied to it. This will
involve *cloning* each of the ancestors of the layer's paint commands and
injecting new children, with a `DrawCompositedLayer` at the bottom of the
tree.

So let's add a new `clone` method to the visual effects
classes. For `SaveLayer`, it'll create a new
`SaveLayer` with the same parameters but new children:


``` {.python}
class SaveLayer(DisplayItem):
    # ...
    def clone(self, children):
        return SaveLayer(self.sk_paint, self.node, children, \
            self.should_save)
```

The other visual effect, `ClipRRect`, should do something similar.

We won't be cloning paint commands, since they're all going to be inside a
composited layer, so we don't need to implement `clone` for them:

``` {.python}
class DisplayItem:
    def clone(self, children):
        assert False
```

We can now build the draw display list. For each composited layer,
create a `DrawCompositedLayer` command (which we'll define in just a
moment). Then, walk up the display list, wrapping that
`DrawCompositedLayer` in each visual effect that needs to apply:

``` {.python replace=parent.clone(/self.clone_latest(parent%2c%20}
class Browser:
    def __init__(self):
        # ...
        self.draw_list = []

    def paint_draw_list(self):
        self.draw_list = []
        for composited_layer in self.composited_layers:
            current_effect = \
                DrawCompositedLayer(composited_layer)
            if not composited_layer.display_items: continue
            parent = composited_layer.display_items[0].parent
            while parent:
                current_effect = \
                    parent.clone([current_effect])
                parent = parent.parent
            self.draw_list.append(current_effect)
```

Now that we've split the display list into composited layers and a
draw display list, we need to update the rest of the browser to use
these pieces for raster and draw.

Let's start with raster. In the raster step, the browser needs to walk the list
of composited layers, allocate a surface for each one, and raster every display
command in the composited layer to that surface. That surface is then saved to
the composited layer, so that we can reuse it next frame.

To start with, we'll need to know how big a surface to allocate for a
`CompositedLayer`. That's just the union of the bounding boxes of all
of its paint commands. We'll first add a `rect` field:


``` {.python expected=False}
class DisplayItem:
    def __init__(self, rect, children=[]):
        self.rect = rect
```

Drawing commands then need to pass that argument to the superclass
constructor. Here's `DrawText`, for example:

``` {.python}
class DrawText(DisplayItem):
    def __init__(self, x1, y1, text, font, color):
        # ...
        super().__init__(skia.Rect.MakeLTRB(x1, y1,
            self.right, self.bottom))
```

Now a `CompositedLayer` can just union the bounding boxes of its
display items:

``` {.python expected=False}
class CompositedLayer:
    # ...
    def composited_bounds(self):
        rect = skia.Rect.MakeEmpty()
        for item in self.display_items:
            rect.join(item.rect)
        return rect
```

These bounds can then be used to make a surface with the right size. Note that
we're creating a surface just big enough to store the items in this composited
layer. This reduces how much GPU memory we need.

``` {.python}
class CompositedLayer:
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
```

To raster the composited layer, draw all of its display items to this surface.
The only tricky part is the need to offset by the top and left of the
composited bounds, since the surface bounds don't include that offset. To do
that, subtract that offset offset so that the display items execute in
the *local coordinate space* of the surface.

``` {.python}
class CompositedLayer:
    def raster(self):
        # ...
        canvas.clear(skia.ColorTRANSPARENT)
        canvas.save()
        canvas.translate(-bounds.left(), -bounds.top())
        for item in self.display_items:
            item.execute(canvas)
        canvas.restore()
```

The browser's raster phase is easy: just raster each layer.

``` {.python}
class Browser:
    def raster_tab(self):
        for composited_layer in self.composited_layers:
            composited_layer.raster()
```

For the draw phase, we'll first need to implement the
`DrawCompositedLayer` command. All it needs is a composited layer to
draw:

``` {.python}
class DrawCompositedLayer(DisplayItem):
    def __init__(self, composited_layer):
        self.composited_layer = composited_layer
        super().__init__(
            self.composited_layer.composited_bounds())

    def __repr__(self):
        return "DrawCompositedLayer()"
```

Executing a `DrawCompositedLayer` is straightforward---just draw its surface
into the parent surface. We just need to keep track of the correct offset:

``` {.python}
class DrawCompositedLayer(DisplayItem):
    def execute(self, canvas):
        layer = self.composited_layer
        bounds = layer.composited_bounds()
        surface_offset_x = bounds.left()
        surface_offset_y = bounds.top()
        layer.surface.draw(
            canvas, surface_offset_x, surface_offset_y)
```

And `draw` is satisfyingly simple now: simply execute the draw display list.

``` {.python}
class Browser:
    def draw(self):
        # ...        
        canvas.save()
        canvas.translate(0, CHROME_PX - self.scroll)
        for item in self.draw_list:
            item.execute(canvas)
        canvas.restore()
        # ...
```

All that's left is wiring these methods up in `raster_and_draw`; let's
also rename it to `composite_raster_and_draw` to remind us that
there's now an additional composite step. (And don't forget to rename
the corresponding dirty bit and call sites.)

``` {.python}
class Browser:
    def composite_raster_and_draw(self):
        # ...
        self.composite()
        self.raster_chrome()
        self.raster_tab()
        self.paint_draw_list()
        self.draw()
        # ...
```

So simple and elegant! Now, on every frame, we are simply splitting the display
list into composited layers and the draw display list, and then running each of
those it their own phase.

Some problems remains in the way of great animation performance, though. The
biggest is that we're doing *all* of these steps on every frame...but the whole
point of compositing was to avoid re-rastering layers! Let's work on that
next.

[profiling]: http://localhost:8001/scheduling.html#profiling-rendering

::: {.further}

The implementation of `Browser.draw` in this section is incorrect for the case
of nested visual effects, because it's not correct to draw every paint chunk
individually; visual effects have to apply *atomically* (i.e., all at once) to
all the content at once. Consider [this example][nested-op] of nested opacity
effects. Its draw display list looks like this:^[Once no-ops are removed;
there are three composited layers because there is one for the background color
of the page.]

     DrawCompositedLayer()
     SaveLayer(alpha=0.999)
       DrawCompositedLayer()
     SaveLayer(alpha=0.999)
       SaveLayer(alpha=0.5)
         DrawCompositedLayer()

[nested-op]: examples/example13-nested-opacity.html

Notice how there are two `SaveLayer(alpha=0.999)` commands, when there should be
one. This will cause incorrect results if the two pieces of text overlap. Fixing
this problem requires some post-processing of the draw display list to merge
common intermediate visual effects, and allocating temporary surfaces for them.
In general, we'd end up with a tree of such temporary surfaces. These are
called *render surfaces*.^["Render", since they are a transient and internal
artifact of the rendering pipeline.]

A naive implementation of this tree (allocating one node for each visual effect)
is not too hard to implement---and there is an exercise at the end of this
chapter for it---but each additional render surface requires more memory and
slows down draw a bit more. So real browsers analyze the visual effect tree to
determine which ones really need render surfaces, and which don't. Opacity, for
example, often doesn't need a render surface, but opacity with at least
two "descendant" `CompositedLayer`s does.[^only-overlapping]

You might think that all this means I chose badly with the "paint commands"
compositing algorithm presented here, but that is not the case. Render surface
optimizations are just as necessary (and complicated to get right!) even with
a "layer tree" approach, because it's so important to optimize GPU memory.
In addition, the algorithm presented here is a simplified version of what
Chromium actually implements.

[^only-overlapping]: Actually, only if there are at least two children *and*
some of them overlap each other visually. Can you see why we can avoid the
render surface for opacity if there is no overlap?

For more details and information on how Chromium implements these concepts see
[here][renderingng-dl] and [here][rendersurface]; other browsers do something
similar. Chromium's implementation of the "visual effect nesting" data
structure is called [property trees][prop-trees]. The name is plural because
there is more than one tree, due to the complex
[containing block][cb] structure of scrolling and clipping.

[cb]: https://developer.mozilla.org/en-US/docs/Web/CSS/Containing_block

[renderingng-dl]: https://developer.chrome.com/blog/renderingng-data-structures/#display-lists-and-paint-chunks
[rendersurface]: https://developer.chrome.com/blog/renderingng-data-structures/#compositor-frames-surfaces-render-surfaces-and-gpu-texture-tiles
[prop-trees]: https://developer.chrome.com/blog/renderingng-data-structures/#property-trees

:::

CSS transitions
===============

The key to avoiding re-rastering layers is to know which layers have
changed, and which haven't. Right now, we're basically always assuming
all layers have changed, but ideally we'd know exactly what's changed
between frames. Browsers have all sorts of complex methods to achieve
this,[^browser-detect-diff] but to keep things simple, let's implement
a CSS feature perfect for compositing: [CSS transitions][csstransitions].

[csstransitions]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Transitions/Using_CSS_transitions

[^browser-detect-diff]: Chromium, for example, tries to
[diff][chromium-diff] the old and new styles any time a style changes
on the page. But this is tricky, because a change in style on one
element could be inherited by a different element, so diffing will
always be somewhat brittle and incomplete.

[chromium-diff]: https://source.chromium.org/chromium/chromium/src/+/main:third_party/blink/renderer/core/style/style_difference.h

CSS transitions basically take the `requestAnimationFrame` loop we
used to implement animation and move it into the browser. The web page
just needs to interpret the CSS [`transition` property][css-transitions],
which defines properties to animate and how long to animate them for. Here's
how to say opacity changes should animate for two seconds:

[css-transitions]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Transitions/Using_CSS_transitions

``` {.css}
transition: opacity 2s;
```

Then, whenever the `opacity` property of the target element
changes for any reason---including mutating its style attribute or
loading a style sheet---the browser smoothly interpolates between the
old and new values for two seconds.  Here is an example:

<iframe src="examples/example13-opacity-transition.html"></iframe>
(click [here](examples/example13-opacity-transition.html) to load the example in
your browser)


It looks more or less identical[^animation-curve] to the JavaScript animation,
but is a lot easier to write. But much more importantly, since the browser
*understands* the animation going on, it can easily detect that it's safe to
avoid rendering pipeline stages. For example, it's easy to see that an 
`opacity` animation does not require layout or raster, just paint and draw.

[^animation-curve]: It's not quite exactly the same, because our
JavaScript code used a linear interpretation (or *easing function*)
between the old and new values. Real browsers use a non-linear easing
function for CSS transitions because it looks better. We'll implement
a linear easing function for our browser, so it will look identical to
the JavaScript and subtly different from real browsers.

To implement CSS transitions, we'll need to move the variables like
`current_frame` and `change_per_frame` from JavaScript into the
browser, and save them on some kind of animation object. Multiple
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

The simplest type of animation is a `NumericAnimation`, which animates
simple numeric properties like `opacity`:

``` {.python}
class NumericAnimation:
    def __init__(self, old_value, new_value, num_frames):
        self.old_value = float(old_value)
        self.new_value = float(new_value)
        self.num_frames = num_frames

        self.frame_count = 1
        total_change = self.new_value - self.old_value
        self.change_per_frame = total_change / num_frames
```

[units]: https://developer.mozilla.org/en-US/docs/Learn/CSS/Building_blocks/Values_and_units

Much like in JavaScript, we'll need an `animate` method that
increments the frame count and computes the new value and returns it; this
value will be placed in the style of an element.

``` {.python}
class NumericAnimation:
    def animate(self):
        self.frame_count += 1
        if self.frame_count >= self.num_frames: return
        current_value = self.old_value + \
            self.change_per_frame * self.frame_count
        return "{}".format(current_value)
```

We're going to want to create these animation objects every time a
style value changes. We can do that in `style` by diffing the old and
the new styles of each node:

``` {.python expected=False}
def style(node, rules):
    old_style = node.style

    # ...

    if old_style:
        transitions = diff_styles(old_style, node.style)
```

This `diff_style` function is going to look for all properties that are
mentioned in the `transition` property and are different between the old and
the new style. So first, we're going to have to parse the `transition`
value:^[Note that this returns a dictionary mapping property names to transition
durations, measured in frames.]

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


Now `diff_style` can loop through all of the properties mentioned in
`transition` and see which ones changed:^[It returns a dictionary
containing only the transitioning properties, and mapping each such
property to its old value, new value, and duration (again in frames).
Note also that this code has to deal with subtleties like the `transition`
property being added or removed, or properties being removed instead
of changing values.]

``` {.python}
def diff_styles(old_style, new_style):
    old_transitions = \
        parse_transition(old_style.get("transition"))
    new_transitions = \
        parse_transition(new_style.get("transition"))

    transitions = {}
    for property in old_transitions:
        if property not in new_transitions: continue
        num_frames = new_transitions[property]
        if property not in old_style: continue
        if property not in new_style: continue
        old_value = old_style[property]
        new_value = new_style[property]
        if old_value == new_value: continue
        transitions[property] = \
            (old_value, new_value, num_frames)

    return transitions
```


Now, back inside `style`, we're going to want to create a new
animation object for each transitioning property. Let's allow
animating just `opacity` for now; we can expand this to
more properties by writing new animation types.

``` {.python}
ANIMATED_PROPERTIES = {
    "opacity": NumericAnimation,
}
```

The `style` function can animate any changed properties listed in
`ANIMATED_PROPERTIES`:

``` {.python}
def style(node, rules, tab):
    if old_style:
        transitions = diff_styles(old_style, node.style)
        for property, (old_value, new_value, num_frames) in \
            transitions.items():
            if property in ANIMATED_PROPERTIES:
                tab.set_needs_render()
                AnimationClass = ANIMATED_PROPERTIES[property]
                animation = AnimationClass(
                    old_value, new_value, num_frames)
                node.animations[property] = animation
                node.style[property] = old_value
```

Any time a property listed in a `transition` changes its value,
we'll create an animation and get ready to run it.^[Note that the
animation will start running in the next frame; until then, we want it
to use the old value of the style property. Scheduling that frame is also
why we need to call `set_needs_render` here. Real browsers would not delay 
a frame, but doing so simplifies our browser's code.]

Finally, we need to run the animations! Basically, every frame, we're
going to want to find all the active animations on the page and call
`animate` on them. Since these animations are a variation of
JavaScript animations using `requestAnimationFrame`, let's run
animations right after handling those callbacks:

``` {.python}
class Tab:
    def run_animation_frame(self, scroll):
        # ...
        self.js.interp.evaljs("__runRAFHandlers()")

        for node in tree_to_list(self.nodes, []):
            for (property_name, animation) in \
                node.animations.items():
                # ...
```

The body of this loop needs to do two things. First, it needs to call
the animation's `animate` method and save the new value to the node's
`style`. Second, since that changes the web page, we need to set a
dirty bit; Recall that `render` exits early if `needs_render` isn't
set, so that dirty bit is supposed to be set if there's rendering
work to do. When an animation is active, there is.^[We also need to
schedule an animation frame for the next frame of the animation, but
`set_needs_render` already does that for us.]

But it's not as simple as just setting `needs_render` any time an
animation is active, however. Setting `needs_render` means re-running
`style`, which would notice that the animation changed a property
value and start a *new* animation! During an animation, we want to run
`layout` and `paint`, but we *don't* want to run `style`:[^even-more]

[^even-more]: While a real browser definitely has an analog of the
`needs_layout` and `needs_paint` flags, our fix for restarting animations
doesn't handle a bunch of edge cases. For example, if a different style
property than the one being animated changes, the browser shouldn't re-start
the animation. Real browsers do things like storing multiple copies of the
style---the computed style and the animated style---to solve issues like this.

``` {.python}
class Tab:
    def run_animation_frame(self, scroll):
        for node in tree_to_list(self.nodes, []):
            for (property_name, animation) in \
                node.animations.items():
                value = animation.animate()
                if value:
                    node.style[property_name] = value
                    self.set_needs_layout()
```

To support `set_needs_layout`, we've got to replace the single
`needs_render` flag with three flags: `needs_style`, `needs_layout`,
and `needs_paint`. The old `set_needs_render` would set all
three:^[In our implementation, setting a dirty bit earlier in the pipeline
will end up causing everything after it to also run. This is yet another
difference from real browsers, which optimize some cases that just require
style and paint, or other combinations.]

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
`needs_render` at the start:[^timer-obsolete]

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

[^timer-obsolete]: By the way, this *does* obsolete our timer for how long
rendering takes. Rendering now does different work on different frames, so
measuring rendering overall doesn't really make sense! I'm going to leave this
be and just not look at the rendering measures anymore, but the best fix would
be to have three timers for the three phases of `render`.

Well---with all that done, our browser now supports animations with
just CSS! And let's use the presence of such an animation to avoid re-raster.

::: {.further}

CSS transitions are great for adding animations triggered by DOM updates from
JavaScript. But what about animations that are just part of a page's UI, and
not connected to a visual transition? (For example, a pulse opacity animation
on a button or cursor.) This can be expressed directly in CSS without any
JavaScript via a [CSS animation][css-animations].

[css-animations]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Animations/Using_CSS_animations

You can see the CSS animation variant of the opacity demo
[here](examples/example13-opacity-animation.html). Implementing this feature
requires parsing a new `@keyframes` syntax and the `animation` CSS property.
Notice how `@keyframes` defines the start and end point declaratively, which
allows us to make the animation alternate infinitely
because a reverse is just going backward among the keyframes.

There is also the [Web Animations API][web-animations], which allows creation
and management of animations via JavaScript.

[web-animations]: https://developer.mozilla.org/en-US/docs/Web/API/Web_Animations_API
:::

Composited animations
=====================

We're finally ready to teach the browser how to avoid raster (and layout) when
running certain animations. These are called *composited animations*, since
they are compatible with the compositing optimization to avoid raster on every
frame.

Avoiding `raster` and `composite` is simple in concept: keep track of what is
animating, and re-run only `paint`, `paint_draw_list` and `draw` on each frame.

To do this we'll need to keep track of animations by some sort of identifier,
and pass that identifier from the main thread to the browser thread. Let's use
the `node` pointer (but the pointer only). Add another `DisplayItem`
constructor parameter indicating the `node` that the `DisplayItem` belongs to
(the one that painted it).

``` {.python
class DisplayItem:
    def __init__(self, rect, children=[], node=None):
        # ...
        self.node = node
```

When animations update, add code to pass the node and visual effects that
changed from one thread to the other. This will have multiple steps.

First, if a composited animation is running, and it's the only thing happening
to the DOM, then only re-do `paint` (in order to update the animated
`DisplayItem`s), not `layout`, and save off each `Element` that updates its
composited animation, in a new array called `composited_updates`. This array
will be set across as part of `commit`.

``` {.python expected=False}
class Tab:
    def __init__(self, browser):
        # ...
        self.composited_updates = []

    def run_animation_frame(self, scroll):
        for node in tree_to_list(self.nodes, []):
            for (property_name, animation) in \
                node.animations.items():
                if value:
                    node.style[property_name] = value
                    if property_name == "opacity":
                        self.composited_updates.append(node)
                        self.set_needs_paint()
                    else:
                        self.set_needs_layout()
```

Second. when running animation frames, if only `needs_paint` is true, then
`composite` is not needed, and each animation in `composited_updates` can be
committed accordingly across to the browser thread to communicate that fact.
The data to be sent across for each animation update will be a DOM `Element`
and a `SaveLayer` pointer.

  To accomplish this we'll need several steps. First, when painting a
  `SaveLayer`, record it on the `Element`:

``` {.python}
def paint_visual_effects(node, cmds, rect):
    # ...
    node.save_layer = save_layer
```

  Next rename `CommitForRaster` to `CommitData` and add a list of composited
  updates (each of which will contain the `Element` and `SaveLayer` pointers).

``` {.python}
class CommitData:
    def __init__(self, url, scroll, height,
        display_list, composited_updates):
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

        composited_updates = {}
        if not needs_composite:
            for node in self.composited_updates:
                composited_updates[node] = \
                    (node, node.save_layer))
        self.composited_updates.clear()

        commit_data = CommitData(
            # ...
            composited_updates=composited_updates,
        )
```

Now for the browser thread. First, add `needs_composite`, `needs_raster` and
`needs_draw` dirty bits and corresponding `set_needs_composite`,
`set_needs_raster`, and `set_needs_draw` methods (and remove the old dirty
bit):

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
        
        if self.needs_composite:
            self.composite()
        if self.needs_raster:
            self.raster_chrome()
            self.raster_tab()
        if self.needs_draw:
            self.draw()
```

Then, call `set_needs_raster` from the places that currently call
`set_needs_raster_and_draw`, such as `handle_down`:

``` {.python}
    def handle_down(self):
        # ...
        self.set_needs_raster()
```

Use the passed data in `commit` to decide whether to call `set_needs_composite`
or `set_needs_draw`, and store off the updates in `composited_updates`:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.composited_updates = {}

    def commit(self, tab, data):
        # ...
        if tab == self.tabs[self.active_tab]:
            # ...
            self.composited_updates = data.composited_updates
            if not self.composited_updates:
                self.composited_updates = {}
                self.set_needs_composite()
            else:
                self.set_needs_draw()
```

Now we need to update `draw_list` to take into account the latest value, which
should be looked up in `composited_updates`. Define a method `clone_latest`
that clones the update visual effect from `composited_updates` if there is one,
and otherwise clones the original.[^ptrcompare]

``` {.python}
class Browser:
    # ...
    def clone_latest(self, visual_effect, current_effect):
        node = visual_effect.node
        if not node in self.composited_updates:
            return visual_effect.clone(current_effect)
        (transform, save_layer) = self.composited_updates[node]
        if type(visual_effect) is Transform:
            return transform.clone(current_effect)
        elif type(visual_effect) is SaveLayer:
            return save_layer.clone(current_effect)
```

Using `clone_latest` in `paint_draw_list` is a one-liner:

``` {.python}
class Browser:
    def paint_draw_list(self):
        for composited_layer in self.composited_layers:
            while parent:
                current_effect = \
                    self.clone_latest(parent, [current_effect])
                # ...
```

[^ptrcompare]: This is done by comparing equality of `Element` object
references. Note that we are only using these objects for
pointer comparison, since otherwise it would not be thread-safe.

The result will be automatically drawn to the screen, because the `draw` method
on each `CompositedLayer` will iterate through its `ancestor_effects` and
execute them.

Test the result in your browser---animations that only update the draw step, and
not everything else!

Unfortunately, we're not done. Raster is avoided, but there are *way*
too many composited layers---one per paint command! That is a big waste
of GPU memory and time.

::: {.further}

While visual effect animations in our browser are now efficient
and *composited*, they are not *threaded* in the sense of
[Chapter 12][threaded-12]: the animation still ticks on the main thread, and
if there is a slow JavaScript or other task clogging the task queue, animations
will stutter. This is a significant problem for real browsers, so almost all of
them support threaded opacity, transform and filter animations; some support
certain kinds of clip animations as well. Adding threaded animations to our
browser is left as an exercise at the end of this chapter.

But it's super easy to thread scroll at this point, with only one line of code
changed: replace the dirty bit for compositing and raster with just
`set_needs_draw` when handing a scroll:

``` {.python}
class Browser:
    # ...
    def handle_down(self):
        # ...
        self.set_needs_draw() 
```

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


While all modern browsers have threaded animations, it's interesting to note
that, as of the time of writing this section, Chromium and WebKit both perform
the `compositing` step on the main thread, whereas our browser does it on the
browser thread. This is the only way in which our browser is actually ahead of
real browsers! The reason compositing doesn't (yet) happen on another thread in
Chromium is that to get there took re-architecting the entire algorithm for
compositing. The re-architecture turned out to be extremely difficult, because
the old one was deeply intertwined with nearly every aspect of the rendering
engine. The re-architecture project only [completed in 2021][cap], so perhaps
sometime soon this work will be threaded in Chromium.

:::

[cap]: (https://developer.chrome.com/blog/renderingng/#compositeafterpaint)

[threaded-12]: http://localhost:8001/scheduling.html#threaded-scrolling

[WebRender]: https://hacks.mozilla.org/2017/10/the-whole-web-at-maximum-fps-how-webrender-gets-rid-of-jank/

Optimizing Compositing
======================

Right now, every paint command it put in its own composited layer. But
composited layers are expensive: each of them allocates a surface, and each of
those allocates and holds on to GPU memory. GPU memory is limited, and we want
to use less of it when possible. To that end, we'd like to use fewer composited
layers.

The simplest thing we can do is put paint commands into the same composited
layer if they have the exact same set of ancestor visual effects in the display
list. This  condition will be determined by the `can_merge` method on
`CompositedLayer`s.

Let's implement that. But first, to make it easy to access those ancestor visual
effects and compare them, add parent pointers to our display list tree:

``` {.python}
def add_parent_pointers(nodes, parent=None):
    for node in nodes:
        node.parent = parent
        add_parent_pointers(node.children, node)

class Browser:
    def composite(self):
        add_parent_pointers(self.active_tab_display_list)
        # ...
```

And so `can_merge` looks like this:

``` {.python}
class CompositedLayer:
    # ...
    def can_merge(self, display_item):
        if self.display_items:
            return display_item.parent == \
                self.display_items[0].parent
        else:
            return True

    def add(self, display_item):
        assert self.can_merge(display_item)
        self.display_items.append(display_item)
```

Using it in `composite` is pretty easy: instead of making a new composited layer
for every single paint command, walk backwards[^why-backwards] through
`composited_layers` trying to merge into each one. If one is found, the paint
chunk is added to it; if not, add a new `CompositedLayer` with that paint chunk
to start.^[If you're not familiar with Python's `for ... else` syntax, the
`else` block executes only if the loop never executed `break`.]

[^why-backwards]: Backwards, because we can't draw things in the wrong
order. Later items in the display list have to draw later.


``` {.python replace=paint_commands/non_composited_commands}
class Browser:
    def composite(self):
        for display_item in paint_commands:
            for layer in reversed(self.composited_layers):
                if layer.can_merge(display_item):
                    layer.add(display_item)
                    break
            else:
                # ...
```



With this implementation, multiple paint commands will sometimes end up in the
same composited layer, but the ancestor effects don't *exactly* match, they
won't. Now let's do one better, and place entire display list *subtrees* that
aren't animating together.

So far, every internal node (ones that aren't leaves) of our display list runs
in the draw phase, while every paint command runs in the raster phase. But some
internal nodes (visual effects) can't be animated. So we can run them in the
raster phase, which will reduce the number of composed layers even more.

To implement this, we'll first need a way to signal that a visual effect
*needs compositing*, meaning that it may be animating and so its
contents should be cached in a GPU texture. Indicate that with a new
`needs_compositing` method on `DisplayItem`. As a simple heuristic,
we'll always composite `SaveLayer`s (but only when they actually do
something that isn't a no-op), regardless of whether they are
animating, but we won't animate `ClipRRect` commands by default.

We'll *also* need to mark a visual effect as needing compositing if any of its
descendants do (even if it's a `ClipRRect`). That's because if one effect is
run on the GPU, then one way or another the ones above it will have to be as
well.[^needs-inefficient]

[^needs-inefficient]: As written, our use of `needs_compositing` is quite
inefficient, because it walks the entire subtree each time it's called. In a
real browser, this property would be computed by walking the entire display
list once and setting boolean attributes on each tree node.


``` {.python replace=self.should_save/USE_COMPOSITING%20and%20self.should_save}
class DisplayItem:
    def needs_compositing(self):
        return any([child.needs_compositing() \
            for child in self.children])

class SaveLayer(DisplayItem):
    def needs_compositing(self):
        return self.should_save or \
            any([child.needs_compositing() \
                for child in self.children])
```

Now, instead of layers containing bare paint commands, they can
contain subtrees of non-composited commands:

``` {.python}
class Browser:
    def composite(self):
        # ...
        non_composited_commands = [cmd
            for cmd in all_commands
            if not cmd.needs_compositing() and \
                (not cmd.parent or \
                 cmd.parent.needs_compositing())
        ]
        # ...
        for display_item in non_composited_commands:
            # ...

```

Since internal nodes can now be in a `CompositedLayer`, there is also a bit of
added complexity to `composited_bounds`.  We'll need to recursively union the
rects of the subtree of non-composited display items, so let's add a
`DisplayItem` method to do that:

``` {.python}
class DisplayItem:
    def __init__(self, rect, children=[], node=None):
        self.rect = rect
    # ...

    def add_composited_bounds(self, rect):
        rect.join(self.rect)
        for cmd in self.children:
            cmd.add_composited_bounds(rect)
```

Now we can use this new method as follows:

``` {.python}
class CompositedLayer:
    # ...
    def composited_bounds(self):
        rect = skia.Rect.MakeEmpty()
        for item in self.display_items:
            item.add_composited_bounds(rect)
        return rect
```

Our compositing algorithm is now pretty well optimized! It does a good job of
grouping together non-animating content to reduce the number of composited
layers (which saves GPU memory), and doing as much work as possible in raster
rather than draw (which makes composited animations faster).

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


Overlap and transforms
======================

The compositing algorithm we implemented works great in many cases.
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
green, because the blue square surface draws after the root surface. Oops!

To fix this bug, we'll have to put the green square into its own
`skia.Surface` (whether we like it or not). This situation is called an *overlap
reason for compositing*, and is a major complication (and potential source of
extra memory use and slowdown) faced by all real browsers.

Let's fix the compositing algorithm to take into account overlap. It turns out
to be not that hard to do: when considering where to put a paint chunk, simply
check if it overlaps with an animated `CompositedLayer`. If so, start a new
`CompositedLayer` that has an overlap reason for compositing.


The change to `composite` will be only a few lines of code and an `elif` to
check if the current paint chunk overlaps another `CompositedLayer` in the list
that needs to be animated.

``` {.python}
class Browser:
    def composite(self):
        # ...
        for display_item in non_composited_commands:
            for layer in reversed(self.composited_layers):
                if layer.can_merge(display_item):
                    # ...
                elif skia.Rect.Intersects(
                    layer.absolute_bounds(),
                    absolute_bounds(display_item)):
                    layer = CompositedLayer(self.skia_context)
                    layer.add(display_item)
                    self.composited_layers.append(layer)
                    break
```

And then implementing the `absolute_bounds` methods used in the code above. As
it stands, this might as well be equivalent to `composited_bounds` because
there is no visual effect that can grow or move the bounding rect of paint
commands.[^grow] So by just defining `absolute_bounds` to be
`composited_bounds`, everything will work correctly:

``` {.python expected=False}
class DisplayItem:
    def absolute_bounds(self, rect):
        return self.composited_bounds(rect)
```

[^grow]: By grow, I mean that the pixel bounding rect of the visual effect
when drawn to the screen is *larger* than the pixel bounding rect of a paint
command like `DrawText` within it. After all, blending, compositing, and
opacity all change the colors of pixels, but don't expand the set of affected
pixels. And clips and masking decrease rather than increase the set of pixels,
so they can't cause additional overlap either (though they might cause *less*
overlap). Certain [CSS filters][cssfilter], such as blurs, can also expand
pixel rects.

But this is both unsatisfying and boring, because in real browsers there *are*
visual effects that can cause overlap. The most important (for animations, at
least) is *transforms*, which are a mechanism to move around the painted output
of a DOM element anywhere on the screen. In addition, transforms are one of the
most popular visual effects in browsers, because they allow you to move around
content efficiently on the GPU and the browser
thread.[^not-always-visual] That's because transforms merely apply a linear
transformation matrix to each pixel, which is one of the things GPUs are good
at doing efficiently.[^overlap-example]

[^not-always-visual]: Technically, `transform` is not always just a visual
effect. In real browsers, transformed element positions contribute to scrolling
overflow. Real browsers mostly do this correctly, but sometimes cut corners to
avoid slowing down transform animations.


[cssfilter]: https://developer.mozilla.org/en-US/docs/Web/CSS/filter

[^overlap-example]: In addition, it's not possible to create the overlapping
squares example of this section without something like transforms. Real
browsers have many other methods, such as [position]. In fact, it's very
difficult to cause overlap at all in our current browser.

[position]: https://developer.mozilla.org/en-US/docs/Web/CSS/position

The `transform` CSS property in general lets you apply
[any linear transform][transform-def] in 3D space, but I'll just cover really
basic 2D translations. Here's HTML for the overlap example mentioned in the
last section:[^why-zero]

[^why-zero]: The green square has a `transform` property also so that paint
order doesn't change when you try the demo in a real browser. I won't get into
it, but there are various rules for painting, and "positioned" elements (such as
with `transform`) are supposed to paint after regular (non-positioned) elements.
This particular rule is purely a historical artifact.


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
    translation = parse_transform(
        node.style.get("transform", ""))
    # ...
    save_layer = \
    # ...

    transform = Transform(translation, rect, node, [save_layer])
    # ...
    return [transform]
```

The `Transform` display list command is pretty straightforward as well: it calls
the `translate` Skia canvas method, which is conveniently built-in.

``` {.python replace=self.translation%20or/USE_COMPOSITING%20and%20self.translation%20or}
class Transform(DisplayItem):
    def __init__(self, translation, rect, node, children):
        super().__init__(rect, children=children, node=node)
        self.translation = translation

    def execute(self, canvas):
        if self.translation:
            (x, y) = self.translation
            canvas.save()
            canvas.translate(x, y)
        for cmd in self.children:
            cmd.execute(canvas)
        if self.translation:
            canvas.restore()

    def clone(self, children):
        return Transform(self.translation, self.rect,
            self.node, children)

    def __repr__(self):
        if self.translation:
            (x, y) = self.translation
            return "Transform(translate({}, {}))".format(x, y)
        else:
            return "Transform(<no-op>)"
```

Add it as an animating property:

``` {.python}
ANIMATED_PROPERTIES = {
    # ...
    "transform": TranslateAnimation,
}
```

Via `TranslateAnimation`:

``` {.python replace=True)/USE_COMPOSITING)}
class TranslateAnimation:
    def __init__(self, old_value, new_value, num_frames):
        (self.old_x, self.old_y) = parse_transform(old_value)
        (new_x, new_y) = parse_transform(new_value)
        self.num_frames = num_frames

        self.frame_count = 1
        self.change_per_frame_x = \
            (new_x - self.old_x) / num_frames
        self.change_per_frame_y = \
            (new_y - self.old_y) / num_frames

    def animate(self):
        self.frame_count += 1
        if self.frame_count >= self.num_frames: return
        new_x = self.old_x + \
            self.change_per_frame_x * self.frame_count
        new_y = self.old_y + \
            self.change_per_frame_y * self.frame_count
        return "translate({}px,{}px)".format(new_x, new_y)
```

You should now be able to create this animation:^[In this
example, I added in a simultaneous opacity animation to demonstrate that our
browser supports it.]

<iframe src="examples/example13-transform-transition.html" style="width:350px;height:350px">
</iframe>
(click [here](examples/example13-transform-transition.html) to load the example in
your browser)

Finally, transforms are compatible with composited animations, so there is a bit
more work to do to make transforms plug into that system. Doing so is not hard,
it just requires edits to the code to handle transform in all the same places
opacity was, in particular:

* Write `Transform.needs_compositing`. It should return `True` if
  there is a transformation active.

* Set `node.transform` in `paint_visual_effects` just like `save_layer`.

* Consider it composited in `run_animation_frame`.

* Add `transform` to each `composited_updates` field of `CommitData`.

* Consider transform during `paint_draw_list`.

Each of these changes should be pretty straightforward and repetitive on top of
opacity, so I'll skip showing the code. Once updated, our browser should now
have fast, composited transform animations.

But if you try it on the example above, you'll find that the animation still
looks wrong---the blue square is supposed to be *under* the green one, but
now it's on top. Which is of course because of the lack of overlap testing,
which we should now complete.

Let's first add the implementation of the `absolute_bounds` function. Before we
added support for `transform`, this was the same as the union of the rects of
each paint command. But now we need to account for a transform moving content
around on screen. The first step in accomplishing that is with a new `map`
method on `Transform` that takes a rect in the coordinate space of
the "contents" of the transform and outputs a rect in post-transform space. For
example, if the transform was `translate(20px, 0px)` then the output of calling
`map` on a rect would return a new rect with the x coordinate of all four
corners increased by 20.

``` {.python}
class DisplayItem:
    def map(self, rect):
        return rect

class Transform(DisplayItem):
    def map(self, rect):
        if not self.translation:
            return rect
        else:
            (x, y) = self.translation
            matrix = skia.Matrix()
            matrix.setTranslate(x, y)
            return matrix.mapRect(rect)
```

We can use `map` to implement a new `absolute_bounds` function that determines
the absolute bounds of a display item:

``` {.python}
def absolute_bounds(display_item):
    rect = skia.Rect.MakeEmpty()
    display_item.add_composited_bounds(rect)
    effect = display_item.parent
    while effect:
        rect = effect.map(rect)
        effect = effect.parent
    return rect
```

And add a method union all of the absolute bounds of the display items in 
a `CompositedLayer`:

``` {.python}
class CompositedLayer:
    def absolute_bounds(self):
        rect = skia.Rect.MakeEmpty()
        for item in self.display_items:
            rect.join(absolute_bounds(item))
        return rect
```

All this `absolute_bounds` code is already used in the `Browser.composite`
method I outlined in the previous section; don't forget to update that method
according to the code I outlined.

Overlap testing is now complete.[^not-really] Your animation should animate the
blue square underneath the green one. And with that, we now have completed
the story of a pretty high-performance implementation of composited animations.

[^not-really]: Actually, even the current code is not correct now that we have
transforms. Since a transform animation moves content around, it also affects
whether content overlaps. I conveniently chose a demo that starts out
overlapping, but if it didn't start out overlapping our browser would not
correctly notice when overlap starts happening during the animation. I've
left solving this to an exercise.

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

- It's important to optimize the number of composited layers.

- Overlap testing can cause additional GPU memory use and needs to be
  implemented witih care.

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

*Width animations*: Implement the CSS `width` property; when `width` is set to
 some number of pixels on an element, the element should be that many pixels
 wide, regardless of how its width would normally be computed. Make `width`
 animatable; you'll need a variant of `NumericAnimation` that parses and
 produces pixel values (the "px" suffix in the string). Since `width`
 is layout-inducing, make sure that animating `width` sets `needs_layout`.
 Check that animating width should change line breaks.[This example]
 (examples/example13-width-transition.html) should work once you've implemented
 width animations.

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

*Atomic effects*: Our browser currently uses a simplistic algorithm
for building the draw tree which doesn't handle nested, composited
visual effects correctly, especially when there are overlapping
elements on the page. Fix this. You can still walk up the display list
from each composited layer, but you'll need to avoid making two clones
of the same visual effect node. You should end up with the following
draw display list for [this example][nested-op], with one
(probably internal-to-Skia) render surface:[^see-render-surface]
    
     DrawCompositedLayer()
     SaveLayer(alpha=0.999)
       DrawCompositedLayer()
       SaveLayer(alpha=0.5)
         DrawCompositedLayer()

[^see-render-surface]: See the Go Further block about render surfaces for more
information.

*Animated scrolling*: Real browsers have many kinds of animations during scroll.
 For example, pressing the down key or the down-arrow in a scrollbar causes a
 pleasant animated scroll, rather than the immediate scroll our browser current
 implements. Or on mobile, a touch interaction often causes a "fling" scroll
 according to a physics-based model of scroll momentum with friction. Implement
 the [`scroll-behavior`][scroll-behavior] CSS property on the `<body>` element,
 and use it to cause animated scroll in `handle_down`, by delegating scroll to
 a main thread animation.[^main-thread-scroll] You'll need to implement a new
 `ScrollAnimation` class and some logic in `run_animation_frame`. Scrolling in
 the [transform transition](examples/example13-transform-transition.html)
 example should now be smooth, as that example uses `scroll-behavior`.

[scroll-behavior]: https://developer.mozilla.org/en-US/docs/Web/CSS/scroll-behavior
[^main-thread-scroll]: This will lose threaded scrolling. If you've implemented
the threaded animations exercise, you could build on that code to animate
scroll on the browser thread.

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
