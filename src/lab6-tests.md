`Tests for WBE Chapter 6
=======================

Chapter 6 (Applying User Styles) introduces a 

    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab6

    >>> url = 'http://test.test/example'
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\n" +
    ... b"Header1: Value1\r\n\r\n" +
    ... b"Test")

Testing tree_to_list
====================

    >>> browser = lab6.Browser()
    >>> browser.load(url)
    >>> list = []
    >>> retval = lab6.tree_to_list(browser.document, list)
    >>> retval
    >>> retval == list
    True

