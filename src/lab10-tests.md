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

Testing XMLHttpRequest
======================

First, let's test the basic `XMLHttpRequest` functionality. We'll be
making a lot of `XMLHttpRequest` calls so let's add a little helper
for that:

    >>> def xhrjs(url):
    ...     return """x = new XMLHttpRequest();
    ... x.open("GET", """ + repr(url) + """, false);
    ... x.send();
    ... console.log(x.responseText);"""

Now let's test a simple same-site request:

    >>> url = "http://about.blank/"
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\n\r\n")
    >>> url2 = "http://about.blank/hello"
    >>> test.socket.respond(url2, b"HTTP/1.0 200 OK\r\n\r\nHello!")
    >>> browser = lab10.Browser()
    >>> browser.load(url)
    >>> tab = browser.tabs[0]
    >>> tab.js.run(xhrjs(url2))
    Hello!

Relative URLs also work:

    >>> tab.js.run(xhrjs("/hello"))
    Hello!
    
Non-synchronous XHRs should fail:

    >>> tab.js.run("XMLHttpRequest().open('GET', '/', true)") #doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    _dukpy.JSRuntimeError: <complicated error message>
    
If cookies are present, they should be sent:

    >>> lab10.COOKIE_JAR["about.blank"] = ('foo=bar', {})
    >>> tab.js.run(xhrjs(url2))
    Hello!
    >>> test.socket.last_request(url2)
    b'GET /hello HTTP/1.0\r\nHost: about.blank\r\nCookie: foo=bar\r\n\r\n'

Note that the cookie value is sent.

Now let's see that cross-domain requests fail:

    >>> url3 = "http://other.site/"
    >>> test.socket.respond(url3, b"HTTP/1.0 200 OK\r\n\r\nPrivate")
    >>> tab.js.run(xhrjs(url3)) #doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    _dukpy.JSRuntimeError: <complicated error message>

It's not important whether the request is _ever_ sent; the CORS
exercise requires sending it but the standard implementation does not
send it.

Testing SameSite cookies and CSRF
=================================

`SameSite` cookies should be sent on cross-site `GET`s and
same-site `POST`s but not on cross-site `POST`s.

Cookie without `SameSite` have already been tested above. Let's create
a `SameSite` cookie to start.

    >>> url = "http://test.test/"
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\nSet-Cookie: bar=baz; SameSite=Lax\r\n\r\n")
    >>> tab.load(url)
    >>> lab10.COOKIE_JAR["test.test"]
    ('bar=baz', {'samesite': 'lax'})

Now the browser should have `bar=baz` as a `SameSite` cookie for
`test.test`. First, let's check that it's sent in a same-site `GET`
request:

    >>> url2 = "http://test.test/2"
    >>> test.socket.respond(url2, b"HTTP/1.0 200 OK\r\n\r\n2")
    >>> tab.load(url2)
    >>> test.socket.last_request(url2)
    b'GET /2 HTTP/1.0\r\nHost: test.test\r\nCookie: bar=baz\r\n\r\n'

Now let's submit a same-site `POST` and check that it's also sent
there:

    >>> url3 = "http://test.test/add"
    >>> test.socket.respond(url3, b"HTTP/1.0 200 OK\r\n\r\nAdded!", method="POST")
    >>> tab.load(url3, body="who=me")
    >>> test.socket.last_request(url3)
    b'POST /add HTTP/1.0\r\nHost: test.test\r\nCookie: bar=baz\r\nContent-Length: 6\r\n\r\nwho=me'

Now we navigate to another site, navigate back by `GET`, and the
cookie should *still* be sent:

    >>> url4 = "http://other.site/"
    >>> test.socket.respond(url4, b"HTTP/1.0 200 OK\r\n\r\nHi!")
    >>> tab.load(url4)
    >>> tab.load(url)
    >>> test.socket.last_request(url)
    b'GET / HTTP/1.0\r\nHost: test.test\r\nCookie: bar=baz\r\n\r\n'

Finally, let's try a cross-site `POST` request and check that in this
case the cookie is *not* sent:

    >>> tab.load(url4)
    >>> tab.load(url3, body="who=me")
    >>> test.socket.last_request(url3)
    b'POST /add HTTP/1.0\r\nHost: test.test\r\nContent-Length: 6\r\n\r\nwho=me'
