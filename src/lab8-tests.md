Tests for WBE Chapter 8
=======================

Chapter 8 (Sending Information to Servers) introduces forms and shows how
to implement simple input and button elements, plus submit forms to the server.
It also includes the first implementation of an HTTP server, in order to show
how the server processes form submissions.

    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab6

    >>> url = 'http://test.test/example'
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\n" +
    ... b"Header1: Value1\r\n\r\n" +
    ... b"<div>Test</div>")

