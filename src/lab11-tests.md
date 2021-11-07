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

    >>> browser = lab11.Browser({})
    >>> browser.load(size_url)
    >>> browser.skia_surface.printTabCommands()
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawString(text=Text, x=13.0, y=136.10546875, color=ff000000)

and relative position.

    >>> size_and_position_url = 'http://test.test/size-and-position'
    >>> test.socket.respond(size_and_position_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='styles.css'>" +
    ... b"<div style='position:relative;top:25px'><div>Text</div></div>)")

    >>> browser = lab11.Browser({})
    >>> browser.load(size_and_position_url)

Since the elemnet has top:25px, the y coordinate should be 118 + 25 = 143
(143 comes from the y coordinate of the rect above) for each of the divs. The
text should be at a y coordinate of 136.105 + 25 = 161.105.

    >>> browser.skia_surface.printTabCommands()
    drawRect(rect=Rect(13, 143, 63, 193), color=ff0000ff)
    drawRect(rect=Rect(13, 143, 63, 193), color=ff0000ff)
    drawString(text=Text, x=13.0, y=161.10546875, color=ff000000)

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

    >>> browser = lab11.Browser({})
    >>> browser.load(size_and_image_url)
    >>> browser.skia_surface.printTabCommands()
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    save()
    clipRect(rect=Rect(13, 118, 63, 168))
    drawImage(<image>, left=13.0, top=118.0
    restore()
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawString(text=Text, x=13.0, y=136.10546875, color=ff000000)

Opacity can be applied.

    >>> size_and_opacity_url = 'http://test.test/size_and_opacity'
    >>> test.socket.respond(size_and_opacity_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='styles.css'>" +
    ... b"<div style=\"opacity:0.5\"><div>Text</div></div>)")

    >>> browser = lab11.Browser({})
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

    >>> browser = lab11.Browser({})
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

    >>> browser = lab11.Browser({})
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

    >>> browser = lab11.Browser({})
    >>> browser.load(size_and_border_radius_url)
    >>> browser.skia_surface.printTabCommands()
    save()
    clipRRect(bounds=Rect(13, 118, 63, 168), radius=Point(20, 20))
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawString(text=Border-radius, x=13.0, y=136.10546875, color=ff000000)
    restore()

Finally, there are 2D rotation transforms. There is as translate to adjust for
transform origin, then the rotation, then a reverse translation to go from
the transform origin back to the original origin.

    >>> size_and_transform_url = 'http://test.test/size_and_transform'
    >>> test.socket.respond(size_and_transform_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='styles.css'>" +
    ... b"<div style=\"transform:rotateZ(45deg)\"><div>Rotate</div></div>)")

    >>> browser = lab11.Browser({})
    >>> browser.load(size_and_transform_url)
    >>> browser.skia_surface.printTabCommands()
    save()
    translate(x=-38.0, y=-143.0)
    rotate(degrees=45.0)
    translate(x=38.0, y=143.0)
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawString(text=Rotate, x=13.0, y=136.10546875, color=ff000000)
    restore()