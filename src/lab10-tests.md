Tests for WBE Chapter 10
========================

Chapter 10 (Keeping Data Private) introduces cookies.

    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab10

Testing basic cookies
=====================

When a server sends a `Set-Cookie` header, the browser should save it
in the cookie jar:

    >>> browser = lab10.Browser()
    >>> url = 'http://test.test/login'
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\nSet-Cookie: foo=bar\r\n\r\n")
    >>> browser.load(url)
    >>> lab10.COOKIE_JAR["test.test"]
    ('foo=bar', {})
    
Moreover, the browser should now send a `Cookie` header with future
requests:

    >>> url2 = 'http://test.test/'
    >>> test.socket.respond(url2, b"HTTP/1.0 200 OK\r\n\r\n\r\n")
    >>> browser.load(url2)
    >>> test.socket.last_request(url2)
    b'GET / HTTP/1.0\r\nHost: test.test\r\nCookie: foo=bar\r\n\r\n'

Unrelated sites should not be sent the cookie:

    >>> url3 = 'http://other.site/'
    >>> test.socket.respond(url3, b"HTTP/1.0 200 OK\r\n\r\n\r\n")
    >>> browser.load(url3)
    >>> test.socket.last_request(url3)
    b'GET / HTTP/1.0\r\nHost: other.site\r\n\r\n'
    
Note that these three requests were across three different tabs. All
tabs should use the same cookie jar.

Cookie values can be updated:

    >>> lab10.COOKIE_JAR["test.test"]
    ('foo=bar', {})
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\nSet-Cookie: foo=baz\r\n\r\n")
    >>> browser.load(url)
    >>> lab10.COOKIE_JAR["test.test"]
    ('foo=baz', {})

Moreover, the cookie value should be accessible from JavaScript:

    >>> browser.tabs[0].js.interp.evaljs("document.cookie")
    'foo=baz'

Note that tab 0 was loaded when the cookie value was `foo=bar`, but
`document.cookie` nonetheless returns the up-to-date value.
