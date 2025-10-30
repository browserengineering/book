---
title: Porting *WBE* to Recent Software Releases
...

The code in this book was developed for and tested on particular
library versions, including Python 3.14, Skia 138, Tk 8.6.14, DukPy
0.3.0, and PySDL2 0.9.15. Earlier editions of the book, however,
relied on earlier versions, and future editions might rely on later
ones. This page documents code changes necessary to port the code of
*Web Browser Engineering* to other relevant releases of each library.
It will be regularly updated as new versions are released and tested.

Porting to Skia 87
==================

The text of this online book uses Skia 138, but the printed 1^st^
edition used the earlier version 87. This earlier version was missing
the `SamplingOptions` API used in [Chapter 15](embeds.md) of this
book. Skia 87 instead provides the older `FilterQuality` API.

Readers of the 1^st^ edition thus saw a different implementation of
`parse_image_rendering`:

``` {.python}
def parse_image_rendering(quality):
    if quality == "high-quality":
        return skia.FilterQuality.kHigh_FilterQuality
    elif quality == "crisp-edges":
        return skia.FilterQuality.kLow_FilterQuality
    else:
        return skia.FilterQuality.kMedium_FilterQuality
```

And changing the `execute` method of `DrawImage` like so:

``` {.python}
class DrawImage:
    def execute(self, canvas):
        paint = skia.Paint(
            FilterQuality=self.quality,
        )
        canvas.drawImageRect(self.image, self.rect, paint)
```

The `SDL_GL_SetAttribute` method calls in the `Browser` constructor
were also not necessary on this older version.

We recommend new readers use a recent Skia version, as described in
the main text, but the old code is documented here to preserve the
code of the 1^st^ edition.
