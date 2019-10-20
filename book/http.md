---
title: Downloading Web Pages
chapter: 1
prev: preliminaries
next: graphics
...

::: {.todo}
I plan to simplify response parsing, and possibly either merge
`split_url` and `request`, or have one call the other, instead of
making both available at the top level.
:::


The primary goal of a web browser is to display the information
identified by a URL. To do so, a browser splits the URL into parts,
uses those parts to connects to a server somewhere on the Internet,
and requests information from that server. It then displays the data
contained in the server's reply.

The parts of a URL
==================

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


``` {.python}
assert url.startswith("http://")
url = url[len("http://"):]
```

Now we must separate the host from the path. The host comes before the
first `/`, while the path is that slash and everything after it:

``` {.python}
if "/" in url:
    host, path = url.split("/", 1)
    path = "/" + path
else:
    host, path = url, "/"
```

Here I\'m using the `split(s, n)` function, which splits a string by
`s`, starting from the beginning, at most `n` times. The path always
includes the separating slash, so I make sure to add it back after
splitting on it.

Let's combine these code snippets into a function, `split_url`, which
takes in a URL and returns the host and the path:

``` {.python}
def split_url(url):
    # ...
    return host, path
```

With the host and path identified, the next step is to connect to the
host and request the information at that path.

::: {.further}
The syntax of URLs is defined in [RFC
3987](https://tools.ietf.org/html/rfc3986), which is pretty readable.
Try to implement the full URL standard, including encodings for reserved
characters.
:::

::: {.further}
[Data URLs](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/Data_URIs)
are a pretty interesting type of URL that embed the whole reasource into
the URL. Try to implement them; most languages have libraries that
handle the `base64` encoding used in Data URLs.[^4]
:::

Connecting to the host
======================

First, a browser needs to find the host on the Internet and make a
connection.

Usually, the browser asks the operating system to make the connection
for it. The OS then talks to a *DNS server* which converts[^5] a host
name like `example.org` into a *IP address* like `93.184.216.34`.[^6]
Then the OS decides which hardware is best for communicating with that
IP address (say, wireless or wired) using what is called a *routing
table*, and uses that hardware to send a sort of greeting to that IP
address. That greeting names a *port*, which for web pages is usually
80 (or 443 for encrypted connections).^[A might run multiple services,
like a website and also email, and the port identifies which one the
browser is interested in.] The OS communicates with the selected
hardware via a driver, and so sends signals on a wire or over the
air.[^7] On the other side of that wire (or those airwaves) is a
series of *routers*[^8] which each send your message in the direction
they think will take it toward that IP address.[^9] Anyway, the point
of this is that the browser tells the OS, “Hey, put me in touch with
`example.org` on port `80`”, and it does.

On many systems, you can set up this kind of connection manually using
the `telnet` program, like this:^[Port 80 is the standard port for
unencrypted HTTP connections, and the default if you don't specify one.]

``` {.example}
telnet example.org 80
```

You\'ll get output that looks like this:

    Trying 93.184.216.34...
    Connected to example.org.
    Escape character is '^]'.

::: {.installation}
You might need to install `telnet`. Nowadays, it is usually disabled by
default; on Windows, for example, you need to [go to Programs and
Features / Turn Windows features on or
off](https://www.lifewire.com/what-is-telnet-2626026) in the Control
panel. On macOS, you can use the `nc` command as a replacement:

``` {.example}
nc -v example.org 80
```

On Linux the `nc` command is usually available in the repos in a package
called `netcat` or similar. The output with `nc` is a little different
from `telnet` but it does basically the same thing. You can also install
`telnet` on most Linux systems.
:::

This means that the OS converted `example.org` to the IP address of
`93.184.216.34` and was able to connect to it.[^10] You can now type
in text and press enter to talk to `example.org`.

Requesting information
======================

Once it\'s been connected, the browser explains to the host what
information it is looking for. In our case, the browser must do that
explanation using the `http` protocol, and it must explain to the host
that it is looking for `/index.html`. In HTTP, this request looks like
this:

``` {.example}
GET /index.html HTTP/1.0
Host: example.org
```

Here, the word `GET` means that the browser would like to receive
information,[^11] then comes the path, and finally there is the word
`HTTP/1.0` which tells the host that the browser speaks version 1.0 of
HTTP.[^12] There are several versions of HTTP, [at least 0.9, 1.0, 1.1,
and
2.0](https://medium.com/platform-engineer/evolution-of-http-69cfe6531ba0).
The later standards add a variety of useful features, like virtual
hosts, cookies, referrers, and so on, but in the interest of simplicity
our browser won\'t use them yet. We\'re also not implementing HTTP 2.0;
HTTP 2.0 is much more complex than the 1.X series, and is intended for
large and complex web applications, which our browser won\'t much
support, anyway.

After the first line, each line contains a *header*, which has a name
(like `Host`) and a value (like `example.org`). Different headers mean
different things; the `Host` header, for example, tells the host who you
think it is.[^13] There are lots of other headers one could send, but
let\'s stick to just `Host` for now.[^14] Finally, after the headers are
sent, you need to enter one blank line; that tells the host that you are
done with headers.

Enter all this into `telnet` and see what happens. Remember to leave add
one more blank line after the line that begins with `Host`.

::: {.further}
The HTTP/1.0 standard is also known as [RFC
1945](https://tools.ietf.org/html/rfc1945). The HTTP/1.1 standard is
[RFC 2616](https://tools.ietf.org/html/rfc2616), so if you\'re
interested in `Connection` and keep-alive, look there.
:::

Telnet in Python
================

So far we\'ve communicated with another computer using `telnet`. But it
turns out that `telnet` is quite a simple program, and we can do the
same programmatically, without starting another program and typing into
it.

To communicate with another computer, the operating system provides a
feature called \"sockets\". When you want to talk to other computers
(either to tell them something, or to wait for them to tell you
something), you create a socket, and then that socket can be used to
send information back and forth. Sockets come in a few different kinds,
because there are multiple ways to talk to other computers:

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
computer. For that, you need the host and the port. Note that there
are two parentheses in the `connect` call: `connect` takes a single
argument, and that argument is a pair of a host and a port. This is
because different address families have different numbers of
arguments.

``` {.python}
s.connect(("example.org", 80))
```

Finally, once you\'ve made the connection, you can send it some data
using the `send` method.

``` {.python}
s.send(b"GET /index.html HTTP/1.0\r\nHost: example.org\r\n\r\n")
```

Be careful with what you type here. It\'s very important to put *two*
newlines `\r\n` at the end, so that you send that blank line at the
end of the request. If you forget that, the other computer will keep
waiting on you to send that newline, and you\'ll keep waiting on its
reply. Computers are dumb.

::: {.quirk}
Time for some Python-specific quirks. When you send data, it\'s
important to remember that you are sending raw bits and bytes. It
doesn\'t have to be text---though in this case it is---and could instead
be images or video. That\'s why here I have a letter `b` in front of the
string of data: that tells Python that I mean the bits and bytes that
represent the text I typed in, not the text itself, which you can tell
because it has type `bytes` not `str`:

``` {.python}
>>> type("asdf")
<class 'str'>
>>> type(b"asdf")
<class 'bytes'>
```

If you forget that letter `b`, you will get some error about `str`
versus `bytes`. You can turn a `str` into `bytes` by calling its
`encode("utf8")` method.[^18]
:::

You\'ll notice that the `send` call returns a number, in this case `44`.
That tells you how many bytes of data you sent to the other computer;
if, say, your network connection failed midway through sending the data,
you might want to know how much you sent before the connection failed.

::: {.further}
You can find out more about the \"sockets\" API on
[Wikipedia](https://en.wikipedia.org/wiki/Berkeley_sockets). Python
mostly implements that API directly.
:::

::: {.further}
Secure HTTP (the `https` protocol) uses something called
TLS to encrypt all traffic on a socket. TLS is [pretty
complicated](https://tools.ietf.org/html/rfc8446), but your language
might have a simple library for using it. In Python, it\'s called `ssl`.
:::

Understanding the reply
=======================

If you look at your `telnet` session, you should see that the other
computer\'s response starts with this line:

``` {.example}
HTTP/1.0 200 OK
```

That tells you that the host confirms that it, too, speaks `HTTP/1.0`,
and that it found your request to be \"OK\" (which has a corresponding
numeric code of 200). You may be familiar with `404 Not Found`. That\'s
something the server could say instead of `200 OK`, or it could even say
`403 Forbidden` or `500 Server Error`. There are lots of these codes,
and they have a pretty neat organization scheme:

-   The 100s are informational messages
-   The 200s mean you were successful
-   The 300s request follow-up action (usually to follow a redirect)
-   The 400s mean you sent a bad request
-   The 500s mean the server handled the request badly

Note the genius of having two sets of error codes (400s and 500s),
which tells you who is at fault, the server or the browser.^[More
precisely, who the server thinks is at faul.t] You can find a full
list of the different codes [on
Wikipedia](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes).

After the `200 OK` line, the server sends its own headers. When I did
this, I got these headers (but yours will differ):

``` {.example}
Cache-Control: max-age=604800
Content-Type: text/html; charset=UTF-8
Date: Mon, 25 Feb 2019 16:49:28 GMT
Etag: "1541025663+ident"
Expires: Mon, 04 Mar 2019 16:49:28 GMT
Last-Modified: Fri, 09 Aug 2013 23:54:35 GMT
Server: ECS (sec/96EC)
Vary: Accept-Encoding
X-Cache: HIT
Content-Length: 1270
Connection: close
```

There is **a lot** here, including information about the information you
are requesting (`Content-Type`, `Content-Length`, and `Last-Modified`),
information about the server (`Server`, `X-Cache`), information about
how long the browser should cache this information (`Cache-Control`,
`Expires`, `Etag`), and a bunch of random other information. Let\'s move
on for now.

After the headers there is a blank line, and then there is a bunch of
HTML code. Your browser knows that it is HTML because of the
`Content-Type` header, which says that it is `text/html`. That HTML code
is the *body* of the server\'s reply.

Let\'s read the HTTP response programmatically. Generally, you\'d use
the `read` function on sockets, which gives whatever bits of the
response have already arrived. Then you write a loop that collects bits
of the response as they arrive. However, in Python you can use the
`makefile` helper function, which hides the loop:[^19]

``` {.python}
response = s.makefile("rb").read().decode("utf8")
```

Here `s.makefile("rb")` is the file-like object corresponding to what
the other computer said on the socket `s`, and we call `read` on it to
get that output. That output is returned as \"bytes\",[^20] which I am
instructing Python to turn into a string using the `utf8` *encoding*, or
method of associating bytes to letters.[^21]

Let\'s split the response into pieces. The first line is the status
line, then the headers, and then the body:

``` {.python}
head, body = response.split("\r\n\r\n", 1)
lines = head.split("\r\n")
version, status, explanation = lines[0].split(" ", 2)
assert status == "200", "{}: {}".format(status, explanation)
headers = {}
for line in lines[1:]:
    header, value = line.split(":", 1)
    headers[header.lower()] = value.strip()
```

Note that I do *not* check that the server\'s version of HTTP is the
same as mine; this might sound like a good idea, but there are a lot of
misconfigured servers out there that respond in HTTP 1.1 even when you
talk to them in HTTP 1.0. For the headers, I split each line at the
first colon and make a dictionary (a key-value map) of header name to
header value. Headers are case-insensitive, so I normalize them to lower
case. Also, white-space is insignificant in HTTP header values, so I
strip off extra whitespace at the beginning and end

::: {.further}
Many common (and uncommon) HTTP headers are described
[on
Wikipedia](https://en.wikipedia.org/wiki/List_of_HTTP_header_fields).
:::

::: {.further}
Instead of calling `decode` on the whole response, parse
the headers first and then use the `Content-Type` header to determine
which codec to `decode` the body with.
:::

Displaying the HTML
===================

The HTML code that the server sent us defines the content you see in
your browser window when you go to <http://example.org/index.html>.
I\'ll be talking much, much more about HTML in the future chapters, but
for now let me keep it very simple.

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

This tag once again repeats that the character set with which to
interpret the page body is `utf-8`. Sometimes, tags that don\'t contain
information end in a slash, but not always, because web developers
aren\'t always so diligent.

The most important HTML tag is called `<body>` (with its pair,
`</body>`). Between these tags is the content of the page; outside of
these tags is various information about the page, like the
aforementioned title, information about how the page should look
(`<style>` and `</style>`), and metadata using the aforementioned
`<meta/>` tag.

So, to create our very very simple web browser, let\'s take the page
HTML and print all the text in it (but not the tags):[^23]

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

It's now possible to string together `split_url`, `request`, and `show`:

``` {.python}
import sys
host, path = split_url(sys.argv[1])
headers, body = request(host, path)
show(body)
```

This code uses the `sys` library to read the first argument
(`sys.argv[1]`) from the command line to use as the URL.

::: {.further}
The `Accept-Encoding` header allows a web browser to
advertise that it supports [receiving compressed
documents](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Accept-Encoding).
Try implementing support for one of the common compression formats (like
`deflate` or `gzip`)!
:::


Encrypted connections
=====================

So far, our browser supports the `http` scheme. That's pretty good:
it's the most common scheme used for web browsing today. But more and
more, websites are migrating to the `https` scheme. I'd like this toy
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
context to *wrap* the socket `s`. That produces a new socket, `ss`:

``` {.python}
import ssl
ctx = ssl.create_default_context()
ss = ctx.wrap_socket(s, server_hostname="example.org")
```

It's important to always use the new socket, `ss`, instead of the old
one, `s`. Everything you send over `s` is unencrypted; everything you
send over `ss` is encrypted, and then sent over `s`. When you wrap
`s`, you pass a `server_hostname` argument, and it should match the
argument you passed to `s.connect`.

Let's try to take this code and add it to `split_url` and `request`.

::: {.todo}
I plan to extend `split_url` to return the scheme and the port here.
The scheme is then used to choose whether to use encrypted sockets,
while the port is also useful for debugging.
:::

[^1]: To be clear, the server decides which port you have to use. If you
    connect over any old port, like 22, the server will be expecting an
    SSH connection (or whatever), not an HTTP connection.

[^2]: Numbers below 1024 are front doors and those above 1024 are back
    doors.


Summary
=======

This chapter went from an empty file to a rudimentary web browser that
can:

-   Parse a URL into a host, a port, and a path.
-   Connect to that host at that port using `sockets`
-   Send an HTTP request to that host, including a `Host` header
-   Split the HTTP response into a status line, headers, and a body
-   Print the text (and not the tags) in the body

Yes, this is still more of a command-line tool than a web browser, but
what we have already has some of the core capabilities of a browser.

Collect the code samples given in this chapter into a file. You should
have three functions:

`split_url(url)`
:   Takes in a string URL and returns a host string, a numeric port, and
    a path string. The path should include the initial slash.

`request(host, port, path)`
:   Takes in a host, a port, and a path; connects to the host/port using
    sockets; sends it an HTTP request (including the `Host` header);
    splits the response into a status line, headers, and a body; checks
    that the status line starts with `HTTP/1.0` and has the status code
    `200`[^25]; and then returns the headers as a dictionary and the
    body as a string.

`show(body)`
:   Prints the text, but not the tags, in an HTML document

Exercises
=========

-   Along with `Host`, send the `User-Agent` header in the `request`
    function. Its value can be whatever you want---it identifies your
    browser to the host.
-   Add support for the `file://` scheme to `split_url`. Unlike `http://`,
    the file protocol has an empty host and port, because it always
    refers to a path on your local computer. You will need to modify
    `split_url` to return the scheme as an extra output, which will be
    either `http` or `file`. Then, you\'ll need to modify `request` to
    take in the scheme and to \"request\" `file` URLs by calling `open`
    on the path and reading it. Naturally, in that case, there will be
    no headers.
-   Error codes in the 300 range refer to redirects. Change the browser
    so that, for 300-range statuses, the browser repeats the request
    with the URL in the `Location` header. Note that the `Location`
    header might not include the host and scheme. If it starts with `/`,
    prepend the scheme and host. You can test this with with the URL
    <http://tinyurl.com/yyutdgeu>, which should redirect back to this
    page.
-   Only show the text of an HTML document between `<body>` and
    `</body>`. This will avoid printing the title and various style
    information. You will need to add additional variables `in_body` and
    `tag` to that loop, to track whether or not you are between `body`
    tags and to keep around the tag name when inside a tag.
-   Support multiple file formats in `show`: use the `Content-Type`
    header to determine the content type, and if it isn\'t `text/html`,
    just show the whole document instead of stripping out tags and only
    showing text in the `<body>`.

[^4]: In Python, the library is called `base64`.

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

[^10]: The line about escape characters is just instructions on using
    obscure `telnet` features.

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

[^20]: Because I used `"rb"` as the argument to `makefile`. If you
    don\'t pass an argument, or you pass `rt`, Python would guess how to
    convert the response from `bytes` to `str`. I\'m doing it this way
    because who knows what it would guess!.

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

[^25]: The status text like `OK` can actually be anything and is just
    there for humans, not for machines
