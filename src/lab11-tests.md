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
    ... b"div { background-color:blue; width:50px; height:50px}")

Elements can override their size...

    >>> size_url = 'http://test.test/size'
    >>> test.socket.respond(size_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='styles.css'>" +
    ... b"<div><div>Text</div></div>)")

    >>> browser = lab11.Browser()
    >>> browser.load(size_url)
    >>> browser.skia_surface.printTabCommands()
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawString(text=Text, x=13.0, y=136.10546875, color=ff000000)

Images can be specified as backgrounds. The test image below is a 1x1 solid
color.

    >>> image_url = 'http://test.test/image.png'
    >>> test.socket.respond(image_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: image/png\r\n\r\n" +
    ... b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00"
    ... b"\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x01sRGB\x00\xae\xce"
    ... b"\x1c\xe9\x00\x00\x00\x0cIDAT\x18Wcx\xf7u+\x00\x05m\x02\x99\x8a'"
    ... b"\x9d\x1d\x00\x00\x00\x00IEND\xaeB`\x82")

    >>> size_and_image_url = 'http://test.test/size_and_image'
    >>> test.socket.respond(size_and_image_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='styles.css'>" +
    ... b"<div style=\"background-image:url('image.png')\"><div>Text</div></div>)")

    >>> browser = lab11.Browser()
    >>> browser.load(size_and_image_url)
    >>> browser.skia_surface.printTabCommands()
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    save()
    clipRect(rect=Rect(13, 118, 63, 168))
    drawImage(<image>, left=13.0, top=118.0
    restore()
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawString(text=Text, x=13.0, y=136.10546875, color=ff000000)

Specifying `background-size: contain`is supported.

    >>> size_and_image_and_size_url = 'http://test.test/size_and_image_and_size'
    >>> test.socket.respond(size_and_image_and_size_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='styles.css'>" +
    ... b"<div style=\"background-image:url('image.png');background-size:contain\"><div>Text</div></div>)")

    >>> browser = lab11.Browser()
    >>> browser.load(size_and_image_and_size_url)
    >>> browser.skia_surface.printTabCommands()
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawImageRect(<image>, src=Rect(0, 0, 1, 1), dst=Rect(13, 118, 63, 168)
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawString(text=Text, x=13.0, y=136.10546875, color=ff000000)

Also note that urls can be non-relative. Since non-relative urls start with
"http://" or "https://", we needed some extra logic in the CSS parser to avoid
getting confused and thinking the colon is a property-value delimiter. Let's
test that that works:

    >>> lab11.CSSParser(
    ...    "div { background-image:url('http://test.com/test.png') }").parse()
    [(TagSelector(tag=div, priority=1), {'background-image': "url('http://test.com/test.png')"})]

Opacity can be applied.

    >>> size_and_opacity_url = 'http://test.test/size_and_opacity'
    >>> test.socket.respond(size_and_opacity_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='styles.css'>" +
    ... b"<div style=\"opacity:0.5\"><div>Text</div></div>)")

    >>> browser = lab11.Browser()
    >>> browser.load(size_and_opacity_url)
    >>> browser.skia_surface.printTabCommands()
    saveLayer(color=80000000, alpha=128)
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawString(text=Text, x=13.0, y=136.10546875, color=ff000000)
    restore()

So can `mix-blend-mode:multiply` and `mix-blend-mode: difference`.

    >>> size_and_mix_blend_mode_url = 'http://test.test/size_and_mix_blend_mode'
    >>> test.socket.respond(size_and_mix_blend_mode_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='styles.css'>" +
    ... b"<div style=\"mix-blend-mode:multiply\"><div>Mult</div></div>)" +
    ... b"<div style=\"mix-blend-mode:difference\"><div>Diff</div></div>)")

    >>> browser = lab11.Browser()
    >>> browser.load(size_and_mix_blend_mode_url)
    >>> browser.skia_surface.printTabCommands()
    saveLayer(color=ff000000, blend_mode=BlendMode.kMultiply)
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawString(text=Mult, x=13.0, y=136.10546875, color=ff000000)
    restore()
    drawString(text=), x=13.0, y=186.10546875, color=ff000000)
    saveLayer(color=ff000000, blend_mode=BlendMode.kDifference)
    drawRect(rect=Rect(13, 190.344, 63, 240.344), color=ff0000ff)
    drawRect(rect=Rect(13, 190.344, 63, 240.344), color=ff0000ff)
    drawString(text=Diff, x=13.0, y=208.44921875, color=ff000000)
    restore()

Non-rectangular clips via `clip-path:circle` are supported.

    >>> size_and_clip_path_url = 'http://test.test/size_and_clip_path'
    >>> test.socket.respond(size_and_clip_path_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='styles.css'>" +
    ... b"<div style=\"clip-path:circle(40%)\"><div>Clip</div></div>)")

There will be two save layers in this case---one to isolate the
div and its children so the clip only applies ot it, and one to
make a canvas in which to draw the circular clip mask.

    >>> browser = lab11.Browser()
    >>> browser.load(size_and_clip_path_url)
    >>> browser.skia_surface.printTabCommands()
    saveLayer(color=ff000000)
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawString(text=Clip, x=13.0, y=136.10546875, color=ff000000)
    saveLayer(color=ff000000, blend_mode=BlendMode.kDstIn)
    drawCircle(cx=38.0, cy=143.0, radius=20.0, color=ffffffff)
    restore()
    restore()

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
    >>> browser.skia_surface.printTabCommands()
    save()
    clipRRect(bounds=Rect(13, 118, 63, 168), radius=Point(20, 20))
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawString(text=Border-radius, x=13.0, y=136.10546875, color=ff000000)
    restore()

Finally, there are transforms--translation and 3D rotation. Let's start with 
parsing them:

    >>> lab11.parse_transform("translate(2px,3px)")
    ((2.0, 3.0), None)

    >>> lab11.parse_transform("rotate(30deg)")
    (None, 30.0)

    >>> lab11.parse_transform("Nonsense")
    (None, None)

For 2D rotation, there is as translate to adjust for
transform origin, then the rotation, then a reverse translation to go from
the transform origin back to the original origin.

    >>> size_and_rotate_url = 'http://test.test/size_and_transform'
    >>> test.socket.respond(size_and_rotate_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='styles.css'>" +
    ... b"<div style=\"transform:rotate(45deg)\"><div>Rotate</div></div>)")

Note that the negative transform-origin translation happens last, not first,
because transform matrices get applied in backwards order when rendering to 
the screen.

    >>> browser = lab11.Browser()
    >>> browser.load(size_and_rotate_url)
    >>> browser.skia_surface.printTabCommands()
    save()
    translate(x=38.0, y=143.0)
    rotate(degrees=45.0)
    translate(x=-38.0, y=-143.0)
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawString(text=Rotate, x=13.0, y=136.10546875, color=ff000000)
    restore()

For translation transforms, on the other hand, there is need to adjust for the
origin.

    >>> size_and_translate_url = 'http://test.test/size_and_translate'
    >>> test.socket.respond(size_and_translate_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='styles.css'>" +
    ... b"<div style=\"transform:translate(5px,6px)\"><div>Rotate</div></div>)")
    >>> browser = lab11.Browser()
    >>> browser.load(size_and_translate_url)
    >>> browser.skia_surface.printTabCommands()
    save()
    translate(x=5.0, y=6.0)
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawString(text=Rotate, x=13.0, y=136.10546875, color=ff000000)
    restore()

Now let's test the example compositing and blend mode functions.

    >>> import examples11
    >>> import skia
    >>> blue_opaque = skia.Color4f(0.0, 0.0, 1.0, 1.0)
    >>> red_opaque = skia.Color4f(1.0, 0.0, 0.0, 1.0)

Source-over compositing of blue over red yields blue.

    >>> examples11.composite(blue_opaque, red_opaque, "source-over") == blue_opaque
    True

And the other way around yields red.

    >>> examples11.composite(red_opaque, blue_opaque, "source-over") == red_opaque
    True

    >>> blue_semitransparent = skia.Color4f(0.0, 0.0, 1.0, 0.5)
    >>> red_semitransparent = skia.Color4f(1.0, 0.0, 0.0, 0.5)

Compositing a semitransparent blue on top of an opaque red yields a part-blue,
part-red color with an opaque alpha channel.

    >>> examples11.composite(blue_semitransparent, red_opaque, "source-over")
    Color4f(0.5, 0, 0.5, 1)

Compositing the blue over red if they are both half-transparent yields a result
that is less red then blue. This is because the definition of source-over
compositing applies a bit differently to the background and foreground
colors. Likewise, the final alpha is a bit different than you might think.

    >>> examples11.composite(blue_semitransparent, red_semitransparent, "source-over")
    Color4f(0.25, 0, 0.5, 0.75)

Destination-in compositing ignores the source color except for its alpha
channel, and multiplies the color of the backdrop by that alpha.

This means that compositing any opaque color on top of a backdrop with
destination-in compositing yields the backdrop.

    >>> examples11.composite(blue_opaque, red_opaque, "destination-in")
    Color4f(1, 0, 0, 1)

But transparency multiplies.

    >>> examples11.composite(blue_semitransparent, red_opaque, "destination-in")
    Color4f(0.5, 0, 0, 0.5)

And of course, a fully transparent source color yields a full-zero result.

    >>> green_full_transparent = skia.Color4f(0.0, 1.0, 0.0, 0.0)
    >>> examples11.composite(green_full_transparent, red_opaque, "destination-in")
    Color4f(0, 0, 0, 0)

Now for blending. Let's start by testing the `apply_blend` function, which
takes as input a source and backdrop color channel, and a blend mode, It applies
the blend to the color.

    >>> examples11.apply_blend(0.6, 0.0, "normal")
    0.6
    >>> examples11.apply_blend(0.6, 0.0, "multiply")
    0.0
    >>> examples11.apply_blend(0.6, 0.0, "difference")
    0.6
    >>> examples11.apply_blend(0.0, 0.6, "difference")
    0.6

Now let's test the full `blend` method.

    >>> examples11.blend(blue_opaque, red_opaque, "normal") == blue_opaque
    True
    >>> examples11.blend(red_opaque, blue_opaque, "normal") == red_opaque
    True
    >>> examples11.blend(blue_semitransparent, red_semitransparent, "normal") == blue_semitransparent
    True
    >>> examples11.blend(red_semitransparent, blue_semitransparent, "normal") == red_semitransparent
    True

'multiply' multiplies each channel, so like colors may remain brighter but
 dislike colors tend to darken each other each other out.

    >>> examples11.blend(blue_opaque, red_opaque, "multiply")
    Color4f(0, 0, 0, 1)
    >>> examples11.blend(blue_opaque, blue_semitransparent, "multiply")
    Color4f(0, 0, 1, 1)

'difference' only keeps around the differences.

    >>> examples11.blend(blue_opaque, red_opaque, "difference")
    Color4f(1, 0, 1, 1)
    >>> examples11.blend(blue_opaque, blue_semitransparent, "difference")
    Color4f(0, 0, 0.5, 1)
