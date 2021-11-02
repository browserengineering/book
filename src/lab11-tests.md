Tests for WBE Chapter 11
========================

Chapter 11 (Adding Visual Effects) is a highly visual chapter. We won't
test the bitmap outputs directly, but instead the display lists generated.

    >>> import test11 as test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab11

    >>> url = 'http://test.test/example'
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"Test")

    >>> browser = lab11.Browser({})
    >>> browser.load(url)
    >>> browser.tabs[0].display_list
    [DrawText(text=Test)]