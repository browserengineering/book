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
    >>> browser.new_tab(lab10.URL(url))
    >>> lab10.COOKIE_JAR["test.test"]
    ('foo=bar', {})
    
Moreover, the browser should now send a `Cookie` header with future
requests:

    >>> url2 = 'http://test.test/'
    >>> test.socket.respond(url2, b"HTTP/1.0 200 OK\r\n\r\n\r\n")
    >>> browser.new_tab(lab10.URL(url2))
    >>> test.socket.last_request(url2)
    b'GET / HTTP/1.0\r\nHost: test.test\r\nCookie: foo=bar\r\n\r\n'

Unrelated sites should not be sent the cookie:

    >>> url3 = 'http://other.site/'
    >>> test.socket.respond(url3, b"HTTP/1.0 200 OK\r\n\r\n\r\n")
    >>> browser.new_tab(lab10.URL(url3))
    >>> test.socket.last_request(url3)
    b'GET / HTTP/1.0\r\nHost: other.site\r\n\r\n'
    
Note that these three requests were across three different tabs. All
tabs should use the same cookie jar.

Cookie values can be updated:

    >>> lab10.COOKIE_JAR["test.test"]
    ('foo=bar', {})
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\nSet-Cookie: foo=baz\r\n\r\n")
    >>> browser.new_tab(lab10.URL(url))
    >>> lab10.COOKIE_JAR["test.test"]
    ('foo=baz', {})

The trailing slash is also optional:

    >>> url_no_slash = 'http://test.test'
    >>> test.socket.respond(url_no_slash + '/', b"HTTP/1.0 200 OK\r\n\r\n\r\n")
    >>> browser.new_tab(lab10.URL(url_no_slash))
    >>> test.socket.last_request(url_no_slash + '/')
    b'GET / HTTP/1.0\r\nHost: test.test\r\nCookie: foo=baz\r\n\r\n'

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
    >>> browser.new_tab(lab10.URL(url))
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
    >>> tab.load(lab10.URL(url))
    >>> lab10.COOKIE_JAR["test.test"]
    ('bar=baz', {'samesite': 'lax'})

Now the browser should have `bar=baz` as a `SameSite` cookie for
`test.test`. First, let's check that it's sent in a same-site `GET`
request:

    >>> url2 = "http://test.test/2"
    >>> test.socket.respond(url2, b"HTTP/1.0 200 OK\r\n\r\n2")
    >>> tab.load(lab10.URL(url2))
    >>> test.socket.last_request(url2)
    b'GET /2 HTTP/1.0\r\nHost: test.test\r\nCookie: bar=baz\r\n\r\n'

Now let's submit a same-site `POST` and check that it's also sent
there:

    >>> url3 = "http://test.test/add"
    >>> test.socket.respond(url3, b"HTTP/1.0 200 OK\r\n\r\nAdded!", method="POST")
    >>> tab.load(lab10.URL(url3), payload="who=me")
    >>> test.socket.last_request(url3)
    b'POST /add HTTP/1.0\r\nHost: test.test\r\nCookie: bar=baz\r\nContent-Length: 6\r\n\r\nwho=me'

Now we navigate to another site, navigate back by `GET`, and the
cookie should *still* be sent:

    >>> url4 = "http://other.site/"
    >>> test.socket.respond(url4, b"HTTP/1.0 200 OK\r\n\r\nHi!")
    >>> tab.load(lab10.URL(url4))
    >>> tab.load(lab10.URL(url))
    >>> test.socket.last_request(url)
    b'GET / HTTP/1.0\r\nHost: test.test\r\nCookie: bar=baz\r\n\r\n'

Finally, let's try a cross-site `POST` request and check that in this
case the cookie is *not* sent:

    >>> tab.load(lab10.URL(url4))
    >>> tab.load(lab10.URL(url3), payload="who=me")
    >>> test.socket.last_request(url3)
    b'POST /add HTTP/1.0\r\nHost: test.test\r\nContent-Length: 6\r\n\r\nwho=me'
    
The same-site check should ignore ports, so if the hosts are the same
but the ports differ, the cookie should be sent:

    >>> tab.load(lab10.URL(url))
    >>> url5 = "http://test.test:8000/test"
    >>> test.socket.respond(url5, b"HTTP/1.0 200 OK\r\n\r\nHi!", method="POST")
    >>> tab.load(lab10.URL(url5), payload="who=me")
    >>> test.socket.last_request(url5)
    b'POST /test HTTP/1.0\r\nHost: test.test\r\nCookie: bar=baz\r\nContent-Length: 6\r\n\r\nwho=me'

Testing Content-Security-Policy
===============================

We test `Content-Security-Policy` by checking that subresources are
loaded / not loaded as required. To do that we need a page with a lot
of subresources:

    >>> url = "http://test.test/"
    >>> body = """<!doctype html>
    ... <link rel=stylesheet href=http://test.test/css />
    ... <script src=http://test.test/js></script>
    ... <link rel=stylesheet href=http://library.test/css />
    ... <script src=http://library.test/js></script>
    ... <link rel=stylesheet href=http://other.test/css />
    ... <script src=http://other.test/js></script>
    ... """
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\n\r\n" + body.encode("utf8"))
    
We also need to create all those subresources:

    >>> test.socket.respond_ok(url + "css", "")
    >>> test.socket.respond_ok(url + "js", "")
    >>> url2 = "http://library.test/"
    >>> test.socket.respond_ok(url2 + "css", "")
    >>> test.socket.respond_ok(url2 + "js", "")
    >>> url3 = "http://other.test/"
    >>> test.socket.respond_ok(url3 + "css", "")
    >>> test.socket.respond_ok(url3 + "js", "")

Now with all of these URLs set up, let's load the page without CSP and
check that all of these requests were made:

    >>> browser = lab10.Browser()
    >>> browser.new_tab(lab10.URL(url))
    >>> [test.socket.made_request(url + "css"),
    ...  test.socket.made_request(url + "js")]
    [True, True]
    >>> [test.socket.made_request(url2 + "css"),
    ...  test.socket.made_request(url2 + "js")]
    [True, True]
    >>> [test.socket.made_request(url3 + "css"),
    ...  test.socket.made_request(url3 + "js")]
    [True, True]

Now let's reload the page, but with CSP enabled for `test.test` and
`library.test` but not `other.test`:

    >>> test.socket.clear_history()
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\n" + \
    ... b"Content-Security-Policy: default-src http://test.test http://library.test\r\n\r\n" + \
    ... body.encode("utf8"))
    >>> browser = lab10.Browser()
    >>> browser.new_tab(lab10.URL(url))
    Blocked script http://other.test/js due to CSP
    Blocked style http://other.test/css due to CSP

The URLs on `test.test` and `library.test` should have been loaded:

    >>> [test.socket.made_request(url + "css"),
    ...  test.socket.made_request(url + "js")]
    [True, True]
    >>> [test.socket.made_request(url2 + "css"),
    ...  test.socket.made_request(url2 + "js")]
    [True, True]

However, neither script nor style from `other.test` should be loaded:

    >>> [test.socket.made_request(url3 + "css"),
    ...  test.socket.made_request(url3 + "js")]
    [False, False]

Let's also test that XHR is blocked by CSP. This requires a little
trickery, because cross-site XHR is already blocked, so we need a CSP
that restricts all sites---but then we can't load and run any
JavaScript!

    >>> url = "http://weird.test/"
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\n" + \
    ... b"Content-Security-Policy: default-src\r\n\r\n")
    >>> browser.new_tab(lab10.URL(url))
    >>> tab = browser.tabs[-1]
    >>> tab.js.run("""
    ... x = new XMLHttpRequest()
    ... x.open('GET', 'http://weird.test/xhr', false);
    ... x.send();""") #doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
      ...
    _dukpy.JSRuntimeError: <complicated wrapper around 'Cross-origin XHR blocked by CSP'>
