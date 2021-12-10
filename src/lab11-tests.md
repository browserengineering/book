Tests for WBE Chapter 11
========================

Chapter 11 (Adding Visual Effects) is a highly visual chapter. We won't
test the bitmap outputs directly, but instead the display lists generated.

    >>> import test11 as test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab11

    >>> styles = 'http://test.test/styles.css'
    >>> test.socket.respond(styles, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/css\r\n\r\n" +
    ... b"div { background-color:blue}")

Opacity can be applied.

    >>> size_and_opacity_url = 'http://test.test/size_and_opacity'
    >>> test.socket.respond(size_and_opacity_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='styles.css'>" +
    ... b"<div style=\"opacity:0.5\"><div>Text</div></div>)")

    >>> browser = lab11.Browser()
    >>> browser.load(size_and_opacity_url)
    >>> browser.tab_surface.printTabCommands()
    clear(color=ffffffff)
    saveLayer(color=80000000, alpha=128)
    drawRect(rect=Rect(13, 18, 787, 40.3438), color=ff0000ff)
    drawRect(rect=Rect(13, 18, 787, 40.3438), color=ff0000ff)
    drawString(text=Text, x=13.0, y=36.10546875, color=ff000000)
    restore()
    drawString(text=), x=13.0, y=58.44921875, color=ff000000)

So can `mix-blend-mode:multiply` and `mix-blend-mode: difference`.

    >>> size_and_mix_blend_mode_url = 'http://test.test/size_and_mix_blend_mode'
    >>> test.socket.respond(size_and_mix_blend_mode_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='styles.css'>" +
    ... b"<div style=\"mix-blend-mode:multiply\"><div>Mult</div></div>)" +
    ... b"<div style=\"mix-blend-mode:difference\"><div>Diff</div></div>)")

    >>> browser = lab11.Browser()
    >>> browser.load(size_and_mix_blend_mode_url)
    >>> browser.tab_surface.printTabCommands()
    clear(color=ffffffff)
    saveLayer(color=ff000000, blend_mode=BlendMode.kMultiply)
    drawRect(rect=Rect(13, 18, 787, 40.3438), color=ff0000ff)
    drawRect(rect=Rect(13, 18, 787, 40.3438), color=ff0000ff)
    drawString(text=Mult, x=13.0, y=36.10546875, color=ff000000)
    restore()
    drawString(text=), x=13.0, y=58.44921875, color=ff000000)
    saveLayer(color=ff000000, blend_mode=BlendMode.kDifference)
    drawRect(rect=Rect(13, 62.6875, 787, 85.0312), color=ff0000ff)
    drawRect(rect=Rect(13, 62.6875, 787, 85.0312), color=ff0000ff)
    drawString(text=Diff, x=13.0, y=80.79296875, color=ff000000)
    restore()
    drawString(text=), x=13.0, y=103.13671875, color=ff000000)

Non-rectangular clips via `clip-path:circle` are supported.

    >>> size_and_clip_path_url = 'http://test.test/size_and_clip_path'
    >>> test.socket.respond(size_and_clip_path_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='styles.css'>" +
    ... b"<div style=\"clip-path:circle(4px)\"><div>Clip</div></div>)")

There will be two save layers in this case---one to isolate the
div and its children so the clip only applies ot it, and one to
make a canvas in which to draw the circular clip mask.

    >>> browser = lab11.Browser()
    >>> browser.load(size_and_clip_path_url)
    >>> browser.tab_surface.printTabCommands()
    clear(color=ffffffff)
    saveLayer(color=ff000000)
    drawRect(rect=Rect(13, 18, 787, 40.3438), color=ff0000ff)
    drawRect(rect=Rect(13, 18, 787, 40.3438), color=ff0000ff)
    drawString(text=Clip, x=13.0, y=36.10546875, color=ff000000)
    saveLayer(color=ff000000, blend_mode=BlendMode.kDstIn)
    drawCircle(cx=400.0, cy=29.171875, radius=4.0, color=ffffffff)
    restore()
    restore()
    drawString(text=), x=13.0, y=58.44921875, color=ff000000)

`border-radius` clipping is also supported.

    >>> size_and_border_radius_url = 'http://test.test/size_and_clip_path'
    >>> test.socket.respond(size_and_border_radius_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='styles.css'>" +
    ... b"<div style=\"border-radius:20px\"><div>Border-radius</div></div>)")

In this case there will be a `save`, but no `saveLayer`, since the latter
is implicit/an implementation detail of Skia, and a `clipRRect` call with a
radius equal to the `20px` radius specified above.

    >>> browser = lab11.Browser()
    >>> browser.load(size_and_border_radius_url)
    >>> browser.tab_surface.printTabCommands()
    clear(color=ffffffff)
    save()
    clipRRect(bounds=Rect(13, 18, 787, 40.3438), radius=Point(11.1719, 11.1719))
    drawRect(rect=Rect(13, 18, 787, 40.3438), color=ff0000ff)
    drawRect(rect=Rect(13, 18, 787, 40.3438), color=ff0000ff)
    drawString(text=Border-radius, x=13.0, y=36.10546875, color=ff000000)
    restore()
    drawString(text=), x=13.0, y=58.44921875, color=ff000000)
    
Testing example compositing and blending functions
==================================================

Now let's test the example compositing and blend mode functions.

    >>> import examples11
    >>> blue_opaque = examples11.Pixel(0.0, 0.0, 1.0, 1.0)
    >>> red_opaque = examples11.Pixel(1.0, 0.0, 0.0, 1.0)

Source-over compositing of blue over red yields blue.

    >>> red_opaque.copy().source_over(blue_opaque) == blue_opaque
    True

And the other way around yields red.

    >>> blue_opaque.copy().source_over(red_opaque) == red_opaque
    True

Compositing a semitransparent blue on top of an opaque red yields a part-blue,
part-red color with an opaque alpha channel.

    >>> blue_semitransparent = examples11.Pixel(0.0, 0.0, 1.0, 0.5)
    >>> red_semitransparent = examples11.Pixel(1.0, 0.0, 0.0, 0.5)
    >>> red_opaque.copy().source_over(blue_semitransparent)
    Pixel(0.5, 0.0, 0.5, 1.0)

Compositing the blue over red if they are both half-transparent yields a result
that is less red then blue. This is because the definition of source-over
compositing applies a bit differently to the background and foreground
colors. Likewise, the final alpha is a bit different than you might think.

    >>> red_semitransparent.copy().source_over(blue_semitransparent)
    Pixel(0.25, 0.0, 0.5, 0.75)

Destination-in compositing ignores the source color except for its alpha
channel, and multiplies the color of the backdrop by that alpha.

This means that compositing any opaque color on top of a backdrop with
destination-in compositing yields the backdrop.

    >>> red_opaque.copy().destination_in(blue_opaque)
    Pixel(1.0, 0.0, 0.0, 1.0)

But transparency multiplies.

    >>> red_opaque.copy().destination_in(blue_semitransparent)
    Pixel(0.5, 0.0, 0.0, 0.5)

And of course, a fully transparent source color yields a full-zero result.

    >>> green_full_transparent = examples11.Pixel(0.0, 1.0, 0.0, 0.0)
    >>> red_opaque.copy().destination_in(green_full_transparent)
    Pixel(0.0, 0.0, 0.0, 0.0)

Now for blending. Let's start by testing the `apply_blend` function, which
takes as input a source and backdrop color channel, and a blend mode, It applies
the blend to the color.

    >>> gray = examples11.gray(0.6)
    >>> black = examples11.gray(0.0)
    >>> gray.copy().multiply(black) == black
    True
    >>> gray.copy().difference(black) == gray
    True
    >>> gray.copy().difference(gray) == black
    True

'multiply' multiplies each channel, so like colors may remain brighter but
 dislike colors tend to darken each other each other out.

    >>> red_opaque.copy().multiply(blue_opaque)
    Pixel(0.0, 0.0, 0.0, 1.0)
    >>> blue_opaque.copy().multiply(blue_semitransparent)
    Pixel(0.0, 0.0, 1.0, 1.0)

'difference' only keeps around the differences.

    >>> red_opaque.copy().difference(blue_opaque)
    Pixel(1.0, 0.0, 1.0, 1.0)
