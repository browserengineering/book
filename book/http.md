---
title: Downloading Web Pages
chapter: 1
prev: preliminaries
next: graphics
...

A web browser displays information identified by a URL. And the first
step is to use that URL to connect to download that information from a
server somewhere on the Internet.

Connecting to a server
======================

To display a web page, the browser first needs to get a copy of it.
So, it asks the OS to put it in touch with a *server* somewhere on the
internet; the URL for the web page tells it the server's *host name*.
The OS then talks to a *DNS server* which converts[^5] a host name
like `example.org` into an *IP address* like `93.184.216.34`.[^6] Then
the OS decides which hardware is best for communicating with that IP
address (say, wireless or wired) using what is called a *routing
table*, and then uses device drivers to sends signals over a wire or
over the air.[^7] Those signals are picked up and transmitted by a
series of *routers*[^8] which each choose the best direction to send
your message so that it eventuall gets to that IP address.[^9]
Eventually the message reaches the server, and a connection is
created. Anyway, the point of this is that the browser tells the OS,
“Hey, put me in touch with `example.org`”, and it does.

On many systems, you can set up this kind of connection using the
`telnet` program, like this:^[The "80" is the port, discussed below.]

``` {.example}
telnet example.org 80
```

::: {.installation}
You might need to install `telnet`; it is often disabled by default.
On Windows, [go to Programs and Features / Turn Windows features on or
off](https://www.lifewire.com/what-is-telnet-2626026) in the Control
panel. On macOS, you can use the `nc -v` command as a replacement:

``` {.example}
nc -v example.org 80
```

The output from `nc` is a little different from `telnet` but it does
basically the same thing. You can install `telnet` on most Linux
systems; plus, the `nc` command is usually available from a package
called `netcat`.
:::

You\'ll get output that looks like this:

    Trying 93.184.216.34...
    Connected to example.org.
    Escape character is '^]'.

This means that the OS converted the host name `example.org` into the
IP address `93.184.216.34` and was able to connect to it.[^10] You can
now talk to `example.org`.

[^10]: The line about escape characters is just instructions on using
    obscure `telnet` features.

Requesting information
======================

Once it's connected, the browser requests information from the server
by name. The name is the part of a URL that comes after the host name,
like `/index.html`, called the *path*. The request looks like this:

``` {.example}
GET /index.html HTTP/1.0
Host: example.org
```

Here, the word `GET` means that the browser would like to receive
information,[^11] then comes the path, and finally there is the word
`HTTP/1.0` which tells the host that the browser speaks version 1.0 of
HTTP.[^12] There are several versions of HTTP ([0.9, 1.0, 1.1, and
2.0](https://medium.com/platform-engineer/evolution-of-http-69cfe6531ba0)).
The HTTP 1.1 standard adds a variety of useful features, like
keep-alive, but in the interest of simplicity our browser won\'t use
them. We\'re also not implementing HTTP 2.0; HTTP 2.0 is much more
complex than the 1.X series, and is intended for large and complex web
applications, which our browser can't run anyway.

After the first line, each line contains a *header*, which has a name
(like `Host`) and a value (like `example.org`). Different headers mean
different things; the `Host` header, for example, tells the host who you
think it is.[^13] There are lots of other headers one could send, but
let\'s stick to just `Host` for now.[^14]

Finally, after the headers comes a single blank line; that tells the
host that you are done with headers.

Enter all this into `telnet`, remembering to leave add a blank line
after the line that begins with `Host`. You should get a response.

[^11]: It could say `POST` if it intended to send information, plus
    there are some other obscure options.

[^12]: Why not 1.1? You can use 1.1, but then you need another header
    (`Connection`) to handle a feature called \"keep-alive\". Using 1.0
    avoids this complexity.

[^13]: This is useful when the same IP address corresponds to multiple
    host names (for example, `example.com` and `example.org`).

[^14]: Many websites, including `example.org`, basically require the
    `Host` header to function properly, since hosting multiple domains
    on a single computer is very common.


::: {.further}
The HTTP/1.0 standard is also known as [RFC
1945](https://tools.ietf.org/html/rfc1945). The HTTP/1.1 standard is
[RFC 2616](https://tools.ietf.org/html/rfc2616), so if you\'re
interested in `Connection` and keep-alive, look there.
:::

Understanding the Response
==========================

The server's response starts with this line:

``` {.example}
HTTP/1.0 200 OK
```

That tells you that the host confirms that it, too, speaks `HTTP/1.0`,
and that it found your request to be "OK" (which has a numeric code of
200). You may be familiar with `404 Not Found`; that's another numeric
code and response, as are `403 Forbidden` or `500 Server Error`. There
are lots of these codes,^[As any look at a [flow
chart](https://github.com/for-GET/http-decision-diagram) will show]
and they have a pretty neat organization scheme:^[The status text like
`OK` can actually be anything and is just there for humans, not for
machines.]

-   The 100s are informational messages
-   The 200s mean you were successful
-   The 300s request follow-up action (usually a redirect)
-   The 400s mean you sent a bad request
-   The 500s mean the server handled the request badly

Note the genius of having two sets of error codes (400s and 500s),
which tells you who is at fault, the server or the browser.^[More
precisely, who the server thinks is at fault.] You can find a full
list of the different codes [on
Wikipedia](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes),
and new ones do get added here and there.

After the `200 OK` line, the server sends its own headers. When I did
this, I got these headers (but yours will differ):

``` {.example}
Age: 545933
Cache-Control: max-age=604800
Content-Type: text/html; charset=UTF-8
Date: Mon, 25 Feb 2019 16:49:28 GMT
Etag: "1541025663+gzip+ident"
Expires: Mon, 04 Mar 2019 16:49:28 GMT
Last-Modified: Fri, 09 Aug 2013 23:54:35 GMT
Server: ECS (sec/96EC)
Vary: Accept-Encoding
X-Cache: HIT
Content-Length: 1270
Connection: close
```

There is *a lot* here, about the information you are requesting
(`Content-Type`, `Content-Length`, and `Last-Modified`), about the
server (`Server`, `X-Cache`), about how long the browser should cache
this information (`Cache-Control`, `Expires`, `Etag`), about all sorts
of other stuff. Let\'s move on for now.

After the headers there is a blank line followed by a bunch of HTML
code. This is called the *body* of the server's response, and your
browser knows that it is HTML because of the `Content-Type` header,
which says that it is `text/html`. It's this HTML code that contains
the content of the web page itself.

Let's now switch gears from manual connections to Python.

::: {.further}
Many common (and uncommon) HTTP headers are described
[on
Wikipedia](https://en.wikipedia.org/wiki/List_of_HTTP_header_fields).
:::

Telnet in Python
================

So far we\'ve communicated with another computer using `telnet`. But it
turns out that `telnet` is quite a simple program, and we can do the
same programmatically. It'll require extracting host name and path
from the URL, creating a *socket*, sending a request, and receiving a
response.

A URL like `http://example.org/index.html` has several parts:

-   The *scheme*, here `http`, explains *how* to get the information
-   The *host*, here `example.org`, explains *where* to get it
-   The *path*, here `/index.html`, explains *what* information to get

There are also optional parts to the URL. Sometimes, like in
`http://localhost:8080/`, there is a *port* that comes after the host,
and there can be something tacked onto the end, a *fragment* like
`#section` or a *query* like `?s=term`. We'll come back to ports later
in this chapter, and some other URL components appear in exercises.

In Python, there\'s a library called `urllib.parse` that splits a URL
into these pieces, but let's write our own.[^3] We\'ll start with the
scheme---our browser only supports `http`, so we just need to check
that the URL starts with `http://` and then strip that off:

[^3]: There's nothing wrong with using libraries, but implementing our
    own is good for learning. Plus, it makes this book easier to
    follow in a language besides Python.


``` {.python expected=False}
assert url.startswith("http://")
url = url[len("http://"):]
```

Now we must separate the host from the path. The host comes before the
first `/`, while the path is that slash and everything after it:

``` {.python}
host, path = url.split("/", 1)
path = "/" + path
```

The `split(s, n)` method splits a string at the first `n` copies of
`s`. The path is supposed to include the separating slash, so I make
sure to add it back after splitting on it.

With the host and path identified, the next step is to connect to the
host. The operating system provides a feature called "sockets" for
this. When you want to talk to other computers (either to tell them
something, or to wait for them to tell you something), you create a
socket, and then that socket can be used to send information back and
forth. Sockets come in a few different kinds, because there are
multiple ways to talk to other computers:

-   A socket has an *address family*, which tells you how to find the
    other computer. Address families have names that begin with `AF`. We
    want `AF_INET`, but for example `AF_BLUETOOTH` is another.
-   A socket has a *type*, which describes the sort of conversation
    that\'s going to happen. Types have names that begin with `SOCK`. We
    want `SOCK_STREAM`, which means each computer can send arbitrary
    amounts of data over, but there\'s also `SOCK_DGRAM`, in which case
    they send each other packets of some fixed size.[^15]
-   A socket has a *protocol*, which describes the steps by which the
    two computers will establish a connection. Protocols have names that
    depend on the address family, but we want `IPPROTO_TCP`.[^16]

By picking all of these options, we can create a socket like so:[^17]

``` {.python}
import socket
s = socket.socket(
    family=socket.AF_INET,
    type=socket.SOCK_STREAM,
    proto=socket.IPPROTO_TCP,
)
```

Once you have a socket, you need to tell it to connect to the other
computer. For that, you need the host and a *port*. The port depends
on the type of server you're connecting to; for now it should be 80.

``` {.python expected=False}
s.connect(("example.org", 80))
```

Note that there are two parentheses in the `connect` call: `connect`
takes a single argument, and that argument is a pair of a host and a
port. This is because different address families have different
numbers of arguments.

::: {.further}
The syntax of URLs is defined in [RFC
3987](https://tools.ietf.org/html/rfc3986), which is pretty readable.
Try to implement the full URL standard, including encodings for reserved
characters.
:::

::: {.further}
You can find out more about the \"sockets\" API on
[Wikipedia](https://en.wikipedia.org/wiki/Berkeley_sockets). Python
more or less implements that API directly.
:::

Request and Response
====================

Now that we have a connection, we make a request to the other server.
To do so, we send it some data using the `send` method:

``` {.python expected=False}
s.send(b"GET /index.html HTTP/1.0\r\n" + 
       b"Host: example.org\r\n\r\n")
```

There are a few things to be careful of here. First, it's important to
have the letter "b" before the string. Next, it\'s very important to
use `\r\n` instead of `\n` for newlines. And finally, it's essential
that you put *two* newlines `\r\n` at the end, so that you send that
blank line at the end of the request. If you forget that, the other
computer will keep waiting on you to send that newline, and you\'ll
keep waiting on its response. Computers are dumb.

::: {.quirk}
Time for a Python quirk. When you send data, it\'s important to
remember that you are sending raw bits and bytes; they could form text
or an image or video. That\'s why here I have a letter `b` in front of
the string of data: that tells Python that I mean the bits and bytes
that represent the text I typed in, not the text itself. You can
also see this in the type changing from `str` to  `bytes`:

``` {.python .example}
>>> type("asdf")
<class 'str'>
>>> type(b"asdf")
<class 'bytes'>
```

If you forget that letter `b`, you will get some error about `str`
versus `bytes`. You can turn a `str` into `bytes` by calling its
`encode("utf8")` method, and go the other way with
`decode("utf8")`.[^18]
:::

You\'ll notice that the `send` call returns a number, in this case `47`.
That tells you how many bytes of data you sent to the other computer;
if, say, your network connection failed midway through sending the data,
you might want to know how much you sent before the connection failed.

To read the response, you\'d generally use the `read` function on
sockets, which gives whatever bits of the response have already
arrived. Then you write a loop that collects bits of the response as
they arrive. However, in Python you can use the `makefile` helper
function, which hides the loop:[^19]

``` {.python}
response = s.makefile("r", encoding="utf8", newline="\r\n")
```

Here `makefile` returns a file-like object containing every byte we
receive from the server. I am instructing Python to turn those bytes
into a string using the `utf8` *encoding*, or method of associating
bytes to letters.[^21] I'm also informing Python of HTTP's weird line
endings.

Let\'s now split the response into pieces. The first line is the
status line:

``` {.python}
statusline = response.readline()
version, status, explanation = statusline.split(" ", 2)
assert status == "200", "{}: {}".format(status, explanation)
```

Note that I do *not* check that the server\'s version of HTTP is the
same as mine; this might sound like a good idea, but there are a lot
of misconfigured servers out there that respond in HTTP 1.1 even when
you talk to them in HTTP 1.0.^[Luckily the protocols are similar
enough to not cause confusion.]

After the status line come the headers:

``` {.python}
headers = {}
while True:
    line = response.readline()
    if line == "\r\n": break
    header, value = line.split(":", 1)
    headers[header.lower()] = value.strip()
```

For the headers, I split each line at the first colon and fill in a
map of header names to header values. Headers are case-insensitive, so
I normalize them to lower case. Also, white-space is insignificant in
HTTP header values, so I strip off extra whitespace at the beginning
and end.

Finally, the body is everything else the server sent us:

``` {.python}
body = response.read()
s.close()
```

It's that body that we're going to display. Before we do that, let's
gather up all of the connection, request, and response code into a
`request` function:

``` {.python}
def request(url):
    # ...
    return headers, body
```

Now let's display the text in the body.

::: {.further}
With the `Accept-Encoding` request header, a browser can
request a [compressed
response](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Accept-Encoding).
Large, text-heavy web pages compress well, and as a result the page
loads faster.
:::

Displaying the HTML
===================

The HTML code in the body defines the content you see in your browser
window when you go to <http://example.org/index.html>. I\'ll be
talking much, much more about HTML in future chapters, but for now let
me keep it very simple.

In HTML, there are *tags* and *text*. Each tag starts with a `<` and
ends with a `>`; generally speaking, tags tell you what kind of thing
some content is, while text is the actual content.[^22] Most tags come
in pairs of a start and an end tag; for example, the title of the page
is enclosed a pair of tags: `<title>` and `</title>`. Each tag, inside
the angle brackets, has a tag name (like `title` here), and then
optionally a space followed by *attributes*, and its pair has a `/`
followed by the tag name (and no attributes). Some tags do not have
pairs, because they don\'t surround text, they just carry information.
For example, on <http://example.org/index.html>, there is the tag:

``` {.example}
<meta charset="utf-8" />
```

This tag explains that the character set with which to interpret the
page body is `utf-8`. Sometimes, tags that don\'t contain information
end in a slash, but not always; it's a matter of preference.

The most important HTML tag is called `<body>` (with its pair,
`</body>`). Between these tags is the content of the page; outside of
these tags is various information about the page, like the
aforementioned title, information about how the page should look
(`<style>` and `</style>`), and metadata (the aforementioned `<meta>`
tag).

So, to create our very very simple web browser, let\'s take the page
HTML and print all the text, but not the tags, in it:[^23]

``` {.python}
in_angle = False
for c in body:
    if c == "<":
        in_angle = True
    elif c == ">":
        in_angle = False
    elif not in_angle:
        print(c, end="")
```

This code is pretty complex. It goes through the request body character
by character, and it has two states: `in_angle`, when it is currently
between a pair of angle brackets, and `not in_angle`. When the current
character is an angle bracket, changes between those states; when it is
not, and it is not inside a tag, it prints the current character.[^24]

Put this code into a new function, `show`:

``` {.python}
def show(body):
    # ...
```

We can now string together `request` and `show`:

``` {.python}
if __name__ == "__main__":
    import sys
    headers, body = request(sys.argv[1])
    show(body)
```

The first line here is Python's version of a `main` function. The code
reads the first argument (`sys.argv[1]`) from the command line using
the `sys` module. That first argument is used as the URL. Try running
this code on the URL `http://example.org/`:

    python3 browser.py http://example.org/

You should see some short text welcoming you to the official example
web page. You can also try using it on this chapter!

Encrypted connections
=====================

So far, our browser supports the `http` scheme. That's pretty good:
it's the most common scheme on the web today. But more and more,
websites are migrating to the `https` scheme. I'd like this toy
browser to support `https` because many websites today require it.

The difference between `http` and `https` is that `https` is more
secure---but let's be a little more specific. The `https` scheme, or
more formally HTTP over TLS, is identical to the normal `http` scheme,
except that all communication between the browser and the host is
encrypted. There are quite a few details to how this works: which
encryption algorithms are used, how a common encryption key is agreed
to, and of course how to make sure that the browser is connecting to
the correct host.

Luckily, the Python `ssl` library implements all of these details for
us, so making an encrypted connection is almost as easy as making a
regular connection. That ease of use comes with accepting some default
settings which could be inappropriate for some situations, but for
teaching purposes they are fine.

Making an encrypted connection with `ssl` is pretty easy. Suppose
you've already created a socket, `s`, and connected it to
`example.org`. To encrypt the connection, you use
`ssl.create_default_context` to create a *context* `ctx` and use that
context to *wrap* the socket `s`. That produces a new socket, `s`:

``` {.python}
import ssl
ctx = ssl.create_default_context()
s = ctx.wrap_socket(s, server_hostname=host)
```

When you wrap `s`, you pass a `server_hostname` argument, and it
should match the argument you passed to `s.connect`. Note that I save
the new socket back into the `s` variable. That's because you don't
want to send over the original socket; it would be unencrypted and
also confusing.

Let's try to take this code and add it to `request`. First, we need to
detect which scheme is being used:

``` {.python}
scheme, url = url.split("://", 1)
assert scheme in ["http", "https"], \
    "Unknown scheme {}".format(scheme)
```

Encrypted HTTP connections usually use port 443 instead of port 80:

``` {.python}
port = 80 if scheme == "http" else 443
```

While we're at it, let's add support for custom ports, which are
specified in a URL by putting a colon after the host name, like in
`http://example.org:8080/`:

``` {.python}
if ":" in host:
    host, port = host.split(":", 1)
    port = int(port)
```

Custom ports are handy [for debugging](preliminaries.md).

Next, we'll wrap the socket with the `ssl` library:

``` {.python}
if scheme == "https":
    ctx = ssl.create_default_context()
    s = ctx.wrap_socket(s, server_hostname=host)
```

Your browser should now be able to connect to HTTPS sites.

::: {.further}
TLS is pretty complicated. You can read the details in [RFC
8446](https://tools.ietf.org/html/rfc8446), but implementing your own is
not recommended. It's very difficult to write a custom TLS
implementation that is not only correct but secure.
:::

Summary
=======

This chapter went from an empty file to a rudimentary web browser that
can:

-   Parse a URL into a scheme, host, and path.
-   Connect to that host using the `sockets` and `ssl` libraries
-   Send an HTTP request to that host, including a `Host` header
-   Split the HTTP response into a status line, headers, and a body
-   Print the text (and not the tags) in the body

Yes, this is still more of a command-line tool than a web browser, but
it already has some of the core capabilities of a browser.

::: {.signup}
:::

Exercises
=========

*HTTP/1.1:* Along with `Host`, send the `Connection` header in the
`request` function with the value `close`. Your browser show now
declare that it is using `HTTP/1.1`. Also add a `User-Agent` header.
Its value can be whatever you want---it identifies your browser to the
host. Make it easy to add further headers in the future.

*Redirects:* Error codes in the 300 range refer to redirects. Change
the browser so that, for 300-range statuses, the browser repeats the
request with the URL in the `Location` header. Note that the
`Location` header might not include the host and scheme. If it starts
with `/`, prepend the scheme and host. You can test this with with the
URL <http://browser.engineering/redirect>, which should redirect back
to this page.

*Body tag:* Only show text in an HTML document if it is between
`<body>` and `</body>`. This avoids printing the title and style
information. The loop in `show` will need more variables to tag names
and whether it is currently between `<body>` and `</body>`.

*Encodings:* Add support for HTTP compression, in which the browser
[informs the
server](https://developer.mozilla.org/en-US/docs/Web/HTTP/Content_negotiation)
that it can compress data before sending it. Your browser must send
the `Accept-Encoding` header with the value `gzip`. If the server
supports compression, its response will have a `Content-Encoding`
header with value `gzip`. The body is then compressed. To decompress
it, you can use the `decompress` method in the `gzip` module. Calling
`makefile` with the `encoding` argument will no longer work, because
compressed data is not `utf8`-encoded. You can change the first
argument `"rb"` to work with raw bytes instead of encoded text.

*Caching:* Typically the same images, styles, and scripts are used on
multiple pages; downloading them over and over again would be a waste.
It's generally valid to cache any HTTP response, as long as it was
requested with `GET` and received a `200` response.^[Some other status
codes like `301` and `404` can also be cached.] Implement a cache in
your browser and test it by requesting the same file multiple times.
Servers control caches using the `Cache-Control` header. Add support
for this header, specifically for `no-store` and `max-age` values. If
the header contains some other value, it's best not to cache the
response.

[^5]: On some systems, you can run `dig +short example.org` to do this
    conversion yourself.

[^6]: Today there are two versions of IP: IPv4 and IPv6. IPv6 addresses
    are a lot longer and are usually in hex, but otherwise the
    differences don\'t matter here.

[^7]: I\'m skipping steps here. On wires you first have to wrap
    communications in ethernet frames, on wireless you have to do even
    more. I\'m trying to be brief.

[^8]: Or a switch, or an access point, there are a lot of possibilities,
    but eventually there is a router.

[^9]: They may also record where the message came from so they can
    forward the reply back, especially in the case of NATs.


[^15]: The `DGRAM` stands for \"datagram\" and think of it like a
    postcard.

[^16]: Nowadays some browsers support protocols that don\'t use TCP,
    like Google Chrome\'s [QUIC
    protocol](https://en.wikipedia.org/wiki/QUIC).

[^17]: While this code uses the Python `socket` library, your favorite
    language likely contains a very similar library. This API is
    basically standardized. In Python, the flags we pass are defaults,
    so you can actually call `socket.socket()`; I\'m keeping the flags
    here in case you\'re following along in another language.

[^18]: Well, to be more precise, you need to call `encode` and then tell
    it the *character encoding* that your string should use. This is a
    complicated topic. I\'m using `utf8` here, which is a common
    character encoding and will work on many pages, but in the real
    world you would need to be more careful.

[^19]: If you\'re in another language, you might only have `socket.read`
    available. You\'ll need to write the loop, checking the socket
    status, yourself.

[^21]: It would be more correct to use `utf8` to decode just the headers
    and then use the `charset` declaration in the `Content-Type` header
    to determine what encoding to use for the body. That\'s what real
    browsers do; browsers even guess the encoding if there isn\'t a
    `charset` declaration, and when they guess wrong you see those ugly
    � or some strange áççêñ£ß. I am skipping all that complexity and by
    again hardcoding `utf8`.

[^22]: That said, some tags, like `img`, are content, not information
    about it.

[^23]: If this example causes Python to produce a `SyntaxError` pointing
    to the `end` on the last line, it is likely because you are running
    Python 2 instead of Python 3. These chapters assume Python 3.

[^24]: The `end` argument tells Python not to print a newline after the
    character, which it otherwise would.
