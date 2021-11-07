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

Images can be specified as backgrounds.

    >>> image_url = 'http://test.test/image.png'
    >>> test.socket.respond(image_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: image/png\r\n\r\n" +
    ... b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x0cIDAT\x18Wcx\xf7u+\x00\x05m\x02\x99\x8a'\x9d\x1d\x00\x00\x00\x00IEND\xaeB`\x82")

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