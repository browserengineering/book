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


    >>> size_url = 'http://test.test/size'
    >>> test.socket.respond(size_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='styles.css'>" +
    ... b"<div><div>Text</div></div>)")

    >>> size_and_position_url = 'http://test.test/size-and-position'
    >>> test.socket.respond(size_and_position_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='styles.css'>" +
    ... b"<div style='position:relative;top:25px'><div>Text</div></div>)")

    >>> browser = lab11.Browser({})
    >>> browser.load(size_url)
    >>> browser.skia_surface.printTabCommands()
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawRect(rect=Rect(13, 118, 63, 168), color=ff0000ff)
    drawString(text=Text, x=13.0, y=136.10546875, color=ff000000)

    >>> browser = lab11.Browser({})
    >>> browser.load(size_and_position_url)

Since the elemnet has top:25px, the y coordinate should be 118 + 25 = 143
(143 comes from the y coordinate of the rect above) for each of the divs. The
text should be at a y coordinate of 136.105 + 25 = 161.105.
    >>> browser.skia_surface.printTabCommands()
    drawRect(rect=Rect(13, 143, 63, 193), color=ff0000ff)
    drawRect(rect=Rect(13, 143, 63, 193), color=ff0000ff)
    drawString(text=Text, x=13.0, y=161.10546875, color=ff000000)