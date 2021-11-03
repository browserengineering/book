Tests for WBE Chapter 11
========================

Chapter 11 (Adding Visual Effects) is a highly visual chapter. We won't
test the bitmap outputs directly, but instead the display lists generated.

    >>> import test11 as test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab11

    >>> url = 'http://test.test/size-and-position'
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<div style='width:50px;height:50px;" +
    ... b"position:relative;top:25px'>Text</div>)")

    >>> browser = lab11.Browser({})
    >>> browser.load(url)
    >>> browser.skia_surface.printTabCommands()
