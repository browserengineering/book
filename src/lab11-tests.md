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
    ... b"<div style='width:50px;height:50px;" +
    ... b"position:relative;top:25px'>Text</div>)")

    >>> browser = lab11.Browser({})
    >>> browser.load(basic_url)
    >>> browser.skia_surface.printTabCommands()
    drawString(text=Text, x=13.0, y=136.10546875, color=ff000000)

    >>> browser = lab11.Browser({})
    >>> browser.load(size_and_position_url)
    >>> browser.skia_surface.printTabCommands()
    drawString(text=Text, x=13.0, y=136.10546875, color=ff000000)