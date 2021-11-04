Tests for WBE Chapter 11
========================

Chapter 11 (Adding Visual Effects) is a highly visual chapter. We won't
test the bitmap outputs directly, but instead the display lists generated.

    >>> import test11 as test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab11

    >>> basic_url = 'http://test.test/basic'
    >>> test.socket.respond(basic_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<div style='background-color:blue;width:50px;height:50px></div>)")

    >>> size_and_position_url = 'http://test.test/size-and-position'
    >>> test.socket.respond(size_and_position_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<div style='background-color:blue;width:50px;height:50px;" +
    ... b"position:relative;top:25px'></div>)")

    >>> browser = lab11.Browser({})
    >>> browser.load(basic_url)
    >>> browser.skia_surface.printTabCommands()
    drawRect(rect=Rect(13, 118, 63, 123), color=ff0000ff)

    >>> browser = lab11.Browser({})
    >>> browser.load(size_and_position_url)

Since the elemnet has top:25px, the y coordinate should be 118 + 25 = 143
    >>> browser.skia_surface.printTabCommands()
    drawRect(rect=Rect(13, 143, 63, 193), color=ff0000ff)
