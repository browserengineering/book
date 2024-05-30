---
title: Porting *WBE* to Recent Software Releases
...

The code in this book was developed for and tested on particular
versions of the libraries it depends on, including Python 3.12, Skia
87, Tk 8.6.14, DukPy 0.3.0, and PySDL2 0.9.15. This page documents
code changes necessary to port the code of *Web Browser Engineering*
to the most recent release of each library. It will be regularly
updated as new versions are released and tested.

Porting to Skia 124
===================

The text of this book uses Skia 87, and the associated skia-python
87.6 release. Skia 124, and the associated skia-python 124b7 release,
changes a couple of APIs used in this book. One major change is the
removal of `FilterQuality`, used in [Chapter 15](embeds.md), and its
replacement by `SamplingOptions`. This requires updating
`parse_image_rendering` like so:

``` {.python}
def parse_image_rendering(quality):
    if quality == "high-quality":
        return skia.SamplingOptions(skia.CubicResampler.Mitchell())
    elif quality == "crisp-edges":
        return skia.SamplingOptions(
            skia.FilterMode.kNearest, skia.MipmapMode.kNone)
    else:
        return skia.SamplingOptions(
            skia.FilterMode.kLinear, skia.MipmapMode.kLinear)
```

And changing the `execute` method of `DrawImage` like so:

``` {.python}
class DrawImage:
    def execute(self, canvas):
        canvas.drawImageRect(self.image, self.rect, self.quality)
```

The new API is somewhat cleaner and more customizable.

Finally, add these `SDL_GL_SetAttribute` calls to set GL version Skia
expects:

``` {.python}
class Browser:
    def __init__(self):
        self.sdl_window = sdl2.SDL_CreateWindow(b'Browser',
            sdl2.SDL_WINDOWPOS_CENTERED,
            sdl2.SDL_WINDOWPOS_CENTERED,
            WIDTH, HEIGHT,
            sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_OPENGL)

        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_MAJOR_VERSION, 3)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_MINOR_VERSION, 2)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_FORWARD_COMPATIBLE_FLAG, True)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_PROFILE_MASK,
                                 sdl2.SDL_GL_CONTEXT_PROFILE_CORE)
```
 
