Tests for WBE Chapter 1
=======================

Chapter 1 (Downloading Web Pages) covers parsing URLs, HTTP requests
and responses, and a very very simplistic print function that writes
to the screen. This file contains tests for those components.

Here's the testing boilerplate.

    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab1
    
You can run this file with `doctest` to run the tests.

Testing `show`
--------------

The `show` function is supposed to print some HTML to the screen, but
skip the tags inside.

    >>> lab1.show('<body>hello</body>')
    hello
    >>> lab1.show('he<body>llo</body>')
    hello
    >>> lab1.show('he<body>l</body>lo')
    hello
    >>> lab1.show('he<body>l<div>l</div>o</body>')
    hello

Note that the tags do not have to match:

    >>> lab1.show('he<body>l</div>lo')
    hello
    >>> lab1.show('he<body>l<div>l</body>o</div>')
    hello

Testing `URL`
-------------

Constructing a `URL` object parses a URL:

    >>> lab1.URL('http://test.test/example1')
    URL(scheme=http, host=test.test, port=80, path='/example1')

This works even if there is no path:

    >>> lab1.URL('http://test.test')
    URL(scheme=http, host=test.test, port=80, path='/')

An explicit port will be used:

    >>> lab1.URL('http://test.test:90')
    URL(scheme=http, host=test.test, port=90, path='/')

Testing `request`
-----------------

The `request` function makes HTTP requests.

To test it, we use the `test.socket` object, which mocks the HTTP server:

    >>> url = 'http://test.test/example1'
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\n" +
    ... b"Header1: Value1\r\n\r\n" +
    ... b"Body text")

Then we request the URL and test both request and response:

    >>> body = lab1.URL(url).request()
    >>> test.socket.last_request(url)
    b'GET /example1 HTTP/1.0\r\nHost: test.test\r\n\r\n'
    >>> body
    'Body text'

With an unusual `Transfer-Encoding` the request should fail:

    
    >>> url = 'http://test.test/te'
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\n" +
    ... b"Transfer-Encoding: chunked\r\n\r\n" +
    ... b"0\r\n\r\n")
    >>> lab1.URL(url).request()
    Traceback (most recent call last):
      ...
    AssertionError

Likewise with `Content-Encoding`:
    
    >>> url = 'http://test.test/ce'
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\n" +
    ... b"Content-Encoding: gzip\r\n\r\n" +
    ... b"\x00\r\n\r\n")
    >>> lab1.URL(url).request()
    Traceback (most recent call last):
      ...
    AssertionError

Testing SSL support
-------------------

Here we're making sure that SSL support is enabled.

    >>> url = 'https://test.test/example2'
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\n\r\n")
    >>> body = lab1.URL(url).request()
    >>> body
    ''

SSL support also means some support for ports:

    >>> url = 'https://test.test:400/example3'
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\n\r\nHi")
    >>> body = lab1.URL(url).request()
    >>> body
    'Hi'

Requesting the wrong port is an error:

    >>> lab1.URL("http://test.test:401/example3").request()
    Traceback (most recent call last):
      ...
    KeyError: 'http://test.test:401/example3'

