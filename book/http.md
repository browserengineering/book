---
title: Downloading Web Pages
chapter: 1
prev: history
next: graphics
...

A web browser displays information identified by a URL. And the first
step is to use that URL to connect to and download that information
from a server somewhere on the Internet.

Connecting to a server
======================

Browsing the internet starts with a URL,[^url] a short string that
identifies a particular web page that the browser should visit. A URL
looks like this:

[^url]: "URL" stands for "Uniform Resource Locator", meaning that it
    is a portable (uniform) way to identify web pages (resources) and
    also that it describes how to access those files (locator).

::: {.cmd html=True}
    python3 infra/annotate_code.py <<EOF
    [http][tl|Scheme]://[example.org][bl|Hostname][/index.html][tl|Path]
    EOF
:::

This URL has three parts: the scheme explains *how* to get the
information; the host explains *where* to get it; and the path
explains *what* information to get. There are also optional parts to
the URL, like ports, queries, and fragments, which we'll see later.

From a URL, the browser can start the process of downloading the web
page. The browser first asks the OS to put it in touch with the
*server* described by the *host name*. The OS then talks to a *DNS*
server which converts[^5] a host name like `example.org` into a
*destination IP address* like `93.184.216.34`.[^6] Then the OS decides
which hardware is best for communicating with that destination IP
address (say, wireless or wired) using what is called a *routing
table*, and then uses device drivers to send signals over a wire or
over the air.[^7] Those signals are picked up and transmitted by a
series of *routers*[^8] which each choose the best direction to send
your message so that it eventually gets to the destination.[^9] When
the message reaches the server, a connection is created. Anyway, the
point of this is that the browser tells the OS, “Hey, put me in touch
with `example.org`”, and it does.

On many systems, you can set up this kind of connection using the
`telnet` program, like this:^[The "80" is the port, discussed below.]

``` {.example}
telnet example.org 80
```

::: {.installation}
You might need to install `telnet`; it is often disabled by default.
On Windows, [go to Programs and Features / Turn Windows features on or
off](https://www.lifewire.com/what-is-telnet-2626026) in the Control
panel; you'll need to reboot. When you run it, it'll clear the screen
instead of printing something, but other than that works normally. On
macOS, you can use the `nc -v` command as a replacement for `telnet`:

``` {.example}
nc -v example.org 80
```

The output is a little different but it works in the same way.
On most Linux systems, you can install `telnet` from the package
manager; plus, the `nc` command is usually available from a package
called `netcat`.
:::

You'll get output that looks like this:

    Trying 93.184.216.34...
    Connected to example.org.
    Escape character is '^]'.

This means that the OS converted the host name `example.org` into the
IP address `93.184.216.34` and was able to connect to it.[^10] You can
now talk to `example.org`.

[^10]: The line about escape characters is just instructions on using
    obscure `telnet` features.

::: {.further}
The syntax of URLs is defined in [RFC
3987](https://tools.ietf.org/html/rfc3986), which is pretty readable.
Try to implement the full URL standard, including encodings for reserved
characters.
:::

Requesting information
======================

Once it's connected, the browser requests information from the server
by giving its *path*, the path being the part of a URL that comes after
the host name, like `/index.html`. The request looks like this; you
should type it into `telnet`:

::: {.cmd html=True}
    python3 infra/annotate_code.py <<EOF
    [GET][tl|Method] [/index.html][tr|Path] [HTTP/1.0][tl|HTTP Version]
    [Host][bl|Header]: [example.org][bl|Value]

    EOF
:::

Make sure to type a blank line after the `Host` line.

Here, the word `GET` means that the browser would like to receive
information,[^11] then comes the path, and finally there is the word
`HTTP/1.0` which tells the host that the browser speaks version 1.0 of
HTTP.[^12] There are several versions of HTTP ([0.9, 1.0, 1.1, and
2.0](https://medium.com/platform-engineer/evolution-of-http-69cfe6531ba0)).
The HTTP 1.1 standard adds a variety of useful features, like
keep-alive, but in the interest of simplicity our browser won't use
them. We're also not implementing HTTP 2.0; HTTP 2.0 is much more
complex than the 1.X series, and is intended for large and complex web
applications, which our browser can't run anyway.

After the first line, each line contains a *header*, which has a name
(like `Host`) and a value (like `example.org`). Different headers mean
different things; the `Host` header, for example, tells the server who
you think it is.[^13] There are lots of other headers one could send,
but let's stick to just `Host` for now.

Finally, after the headers comes a single blank line; that tells the
host that you are done with headers. So type a blank line into
`telnet` (hit Enter twice after typing the two lines of request above)
and you should get a response from `example.org`.

[^11]: It could say `POST` if it intended to send information, plus
    there are some other, more obscure options.

[^12]: Why not 1.1? You can use 1.1, but then you need another header
    (`Connection`) to handle a feature called "keep-alive". Using 1.0
    avoids this complexity.

[^13]: This is useful when the same IP address corresponds to multiple
    host names and hosts multiple websites (for example, `example.com`
    and `example.org`). The `Host` header tells the server which of
    multiple websites you want. These websites basically require the
    `Host` header to function properly. Hosting multiple domains on a
    single computer is very common.


::: {.further}
The HTTP/1.0 standard is also known as [RFC
1945](https://tools.ietf.org/html/rfc1945). The HTTP/1.1 standard is
[RFC 2616](https://tools.ietf.org/html/rfc2616), so if you're
interested in `Connection` and keep-alive, look there.
:::

The server's response
=====================

The server's response starts with this line:

::: {.cmd html=True}
    python3 infra/annotate_code.py <<EOF
    [HTTP/1.0][tr|HTTP Version] [200][bl|Response Code] [OK][tl|Response Description]
    EOF
:::

That tells you that the host confirms that it, too, speaks `HTTP/1.0`,
and that it found your request to be "OK" (which has a numeric code of
200). You may be familiar with `404 Not Found`; that's another numeric
code and response, as are `403 Forbidden` or `500 Server Error`. There
are lots of these codes,^[As any look at a [flow
chart](https://github.com/for-GET/http-decision-diagram) will show.]
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
of other stuff. Let's move on for now.

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

So far we've communicated with another computer using `telnet`. But it
turns out that `telnet` is quite a simple program, and we can do the
same programmatically. It'll require extracting host name and path
from the URL, creating a *socket*, sending a request, and receiving a
response.[^why-not-parse]

[^why-not-parse]: In Python, there's a library called `urllib.parse`
    for parsing URLs, but I think implementing our own will be good
    for learning. Plus, it makes this book less Python-specific.

Let's start with parsing the URL. I'm going to make parsing a URL
return a `URL` object, and I'll put the parsing code into the
constructor:

``` {.python}
class URL:
    def __init__(self, url):
        # ...
```

The `__init__` method is Python's peculiar syntax for class
constructors, and the `self` parameter, which you must always make the
first parameter of any method, is Python's analog of `this`.

Let's start with the scheme, which is separated from the rest of the
URL by `://`. Our browser only supports `http`, so I check that, too:

``` {.python replace=%3d%3d/in,%22http%22/[%22http%22%2c%20%22https%22]}
class URL:
    def __init__(self, url):
        self.scheme, url = url.split("://", 1)
        assert self.scheme == "http", \
            "Unknown scheme {}".format(self.scheme)
```

Now we must separate the host from the path. The host comes before the
first `/`, while the path is that slash and everything after it. Let's
add function that parses all parts of a URL:

``` {python}
class URL:
    def __init__(self, url):
        # ...
        if "/" not in url:
            url = url + "/"
        self.host, url = url.split("/", 1)
        self.path = "/" + url
```

(When you see a code block with a `# ...`, like this one, that you're
adding code to an existing method or block.) The `split(s, n)` method
splits a string at the first `n` copies of `s`. Note that there's some
tricky logic here for handling the slash between the host name and the
path. That (optional) slash is part of the path.

Our browser will create a `URL` object based on user input, and then
it will want to download the web page at that URL. We'll do that in a
new method, `request`:

``` {.python}
class URL:
    def request(self):
        # ...
```

Note that you always need to write the `self` parameter for methods in
Python. In the future, I won't always make such a big deal out of
defining a method---if you see a code block with code in a method or
function that doesn't exist yet, that means we're defining it.

The first step to downloading a web page is connecting to the host.
The operating system provides a feature called "sockets" for this.
When you want to talk to other computers (either to tell them
something, or to wait for them to tell you something), you create a
socket, and then that socket can be used to send information back and
forth. Sockets come in a few different kinds, because there are
multiple ways to talk to other computers:

-   A socket has an *address family*, which tells you how to find the
    other computer. Address families have names that begin with `AF`. We
    want `AF_INET`, but for example `AF_BLUETOOTH` is another.
-   A socket has a *type*, which describes the sort of conversation
    that's going to happen. Types have names that begin with `SOCK`. We
    want `SOCK_STREAM`, which means each computer can send arbitrary
    amounts of data over, but there's also `SOCK_DGRAM`, in which case
    they send each other packets of some fixed size.[^15]
-   A socket has a *protocol*, which describes the steps by which the
    two computers will establish a connection. Protocols have names that
    depend on the address family, but we want `IPPROTO_TCP`.[^16]

By picking all of these options, we can create a socket like so:[^17]

``` {.python}
import socket

class URL:
    def request(self):
        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
```

Once you have a socket, you need to tell it to connect to the other
computer. For that, you need the host and a *port*. The port depends
on the type of server you're connecting to; for now it should be 80.

``` {.python replace=80/self.port}
class URL:
    def request(self):
        # ...
        s.connect((self.host, 80))
```

This talks to `example.org` to set up the connection and ready both
computers to exchange data.

::: {.quirk}
Naturally this won't work if you're offline. It also might not work if
you're behind a proxy, or in a variety of more complex networking
environments. The workaround will depend on your setup---it might be
as simple as disabling your proxy, or it could be much more complex.
:::

Note that there are two parentheses in the `connect` call: `connect`
takes a single argument, and that argument is a pair of a host and a
port. This is because different address families have different
numbers of arguments.

::: {.further}
You can find out more about the "sockets" API on
[Wikipedia](https://en.wikipedia.org/wiki/Berkeley_sockets). Python
more or less implements that API directly.
:::

Request and response
====================

Now that we have a connection, we make a request to the other server.
To do so, we send it some data using the `send` method:

``` {.python}
class URL:
    def request(self):
        # ...
        s.send(("GET {} HTTP/1.0\r\n".format(self.path) + \
                "Host: {}\r\n\r\n".format(self.host)) \
               .encode("utf8"))
```

There are a few things to note here that have to be exactly right. First,
it's very important to use `\r\n` instead of `\n` for newlines. It's
also essential that you put *two* newlines `\r\n` at the end, so that
you send that blank line at the end of the request. If you forget
that, the other computer will keep waiting on you to send that
newline, and you'll keep waiting on its response.[^literal]

[^literal]: Computers are endlessly literal-minded.

Also note the `encode` call. When you send data, it's important to
remember that you are sending raw bits and bytes; they could form text
or an image or video. But a Python string is specifically for
representing text. The `encode` method converts text into bytes, and
there's a corresponding `decode` method that goes the other
way.[^charset] Python reminds you to be careful by giving different
types to text and to bytes:

[^charset]: When you call `encode` and `decode` you need to tell the
    computer what *character encoding* you want it to use. This is a
    complicated topic. I'm using `utf8` here, which is a common
    character encoding and will work on many pages, but in the real
    world you would need to be more careful.

``` {.python .example}
>>> type("text")
<class 'str'>
>>> type("text".encode("utf8"))
<class 'bytes'>
```

If you see an error about `str` versus `bytes`, it's because you
forgot to call `encode` or `decode` somewhere.

If you run this in the REPL, you'll notice that the `send` call
returns a number, in this case `47`. That tells you how many bytes of
data you sent to the other computer; if, say, your network connection
failed midway through sending the data, you might want to know how
much you sent before the connection failed.

To read the response, you'd generally use the `read` function on
sockets, which gives whatever bits of the response have already
arrived. Then you write a loop that collects bits of the response as
they arrive. However, in Python you can use the `makefile` helper
function, which hides the loop:[^19]

``` {.python}
class URL:
    def request(self):
        # ...
        response = s.makefile("r", encoding="utf8", newline="\r\n")
```

Here `makefile` returns a file-like object containing every byte we
receive from the server. I am instructing Python to turn those bytes
into a string using the `utf8` *encoding*, or method of associating
bytes to letters.[^21] I'm also informing Python of HTTP's weird line
endings.

Let's now split the response into pieces. The first line is the
status line:

``` {.python}
class URL:
    def request(self):
        # ...
        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)
        assert status == "200", "{}: {}".format(status, explanation)
```

Note that I do *not* check that the server's version of HTTP is the
same as mine; this might sound like a good idea, but there are a lot
of misconfigured servers out there that respond in HTTP 1.1 even when
you talk to them in HTTP 1.0.^[Luckily the protocols are similar
enough to not cause confusion.]

After the status line come the headers:

``` {.python}
class URL:
    def request(self):
        # ...
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

Headers can describe all sorts of information, but a couple of headers
are especially important because they tell us that the data we're
trying to access is being sent in an unusual way. Let's make sure none
of those are present:[^if-te]

[^if-te]: The "compression" exercise at the end of this chapter
    describes how your browser should handle these headers if they are
    present.

``` {.python}
class URL:
    def request(self):
        # ...
        assert "transfer-encoding" not in headers
        assert "content-encoding" not in headers
```

The usual way to send the data, then, is everything after the headers:

``` {.python}
class URL:
    def request(self):
        # ...
        body = response.read()
        s.close()
```

It's that body that we're going to display, so let's return that.
Let's also return the headers, in case they are useful to someone:

``` {.python}
class URL:
    def request(self):
        # ...
        return headers, body
```

Now let's actually display the text in the response body.

::: {.further}
The [`Content-Encoding`][ce-header] header lets the server compress
web pages before sending them. Large, text-heavy web pages compress
well, and as a result the page loads faster. The browser needs to send
an [`Accept-Encoding` header][ae-header] in its request to list
compression algorithms it supports. [`Transfer-Encoding`][te-header]
is similar and also allows the data to be "chunked", which many
servers seem to use together with compression.
:::

[ce-header]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Encoding
[te-header]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Transfer-Encoding
[ae-header]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Accept-Encoding

Displaying the HTML
===================

The HTML code in the body defines the content you see in your browser
window when you go to <http://example.org/index.html>. I'll be
talking much, much more about HTML in future chapters, but for now let
me keep it very simple.

In HTML, there are *tags* and *text*. Each tag starts with a `<` and
ends with a `>`; generally speaking, tags tell you what kind of thing
some content is, while text is the actual content.[^22] Most tags come
in pairs of a start and an end tag; for example, the title of the page
is enclosed in a pair of tags: `<title>` and `</title>`. Each tag, inside
the angle brackets, has a tag name (like `title` here), and then
optionally a space followed by *attributes*, and its pair has a `/`
followed by the tag name (and no attributes). Some tags do not have
pairs, because they don't surround text, they just carry information.
For example, on <http://example.org/index.html>, there is the tag:

``` {.example}
<meta charset="utf-8" />
```

This tag explains that the character set with which to interpret the
page body is `utf-8`. Sometimes, tags that don't contain information
end in a slash, but not always; it's a matter of preference.

The most important HTML tag is called `<body>` (with its pair,
`</body>`). Between these tags is the content of the page; outside of
these tags is various information about the page, like the
aforementioned title, information about how the page should look
(`<style>` and `</style>`), and metadata (the aforementioned `<meta>`
tag).

So, to create our very, very simple web browser, let's take the page
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
character is an angle bracket, it changes between those states; 
normal characters not inside a tag, are printed.[^24]

Let's put this code into a new function, `show`:

``` {.python}
def show(body):
    # ...
```

We can now load a web page just by stringing together `request` and
`show`:

``` {.python}
def load(url):
    headers, body = url.request()
    show(body)
```

Add the following code to run `load` from the command line:

``` {.python}
if __name__ == "__main__":
    import sys
    load(URL(sys.argv[1]))
```

This is Python's version of a `main` function---it reads the first
argument (`sys.argv[1]`) from the command line and uses it as a URL.
Try running this code on the URL `http://example.org/`:

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

``` {.python .example}
import ssl
ctx = ssl.create_default_context()
s = ctx.wrap_socket(s, server_hostname=host)
```

When you wrap `s`, you pass a `server_hostname` argument, and it
should match the `Host` header. Note that I save the new socket back
into the `s` variable. That's because you don't want to send over the
original socket; it would be unencrypted and also confusing.

::: {.installation}
On macOS, you'll need to [run a program called "Install
Certificates"][macos-fix] before you can use Python's `ssl` package on
most websites.
:::

[macos-fix]: https://stackoverflow.com/questions/52805115/certificate-verify-failed-unable-to-get-local-issuer-certificate

Let's try to take this code and add it to `request`. First, we need to
detect which scheme is being used:

``` {.python}
class URL:
    def __init__(self, url):
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https"], \
            "Unknown scheme {}".format(self.scheme)
        # ...
```

Note that here you're supposed to replace the existing scheme parsing
code with this new code. It's usually clear from context and the code
itself what you need to replace.

Encrypted HTTP connections usually use port 443 instead of port 80:

``` {.python}
class URL:
    def __init__(self, url):
        # ...
        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443
```

We can use that port when creating the socket:

``` {.python}
class URL:
    def request(self):
        # ...
        s.connect((self.host, self.port))
        # ...
```

Next, we'll wrap the socket with the `ssl` library:

``` {.python}
class URL:
    def request(self):
        # ...
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
        # ...
```

Your browser should now be able to connect to HTTPS sites.

While we're at it, let's add support for custom ports, which are
specified in a URL by putting a colon after the host name:

::: {.cmd html=True}
    python3 infra/annotate_code.py <<EOF
    http://example.org:[8080][tl|Port]/index.html
    EOF
:::

If the URL has a port we can parse it out and use it:

``` {.python}
class URL:
    def __init__(self, url):
        # ...
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)
```

Custom ports are handy for debugging. Python has a built-in web server
you can use to serve files on your computer. For example, if you run

    python3 -m http.server 8000

from some directory, then going to `http://localhost:8000/` should
show you all the files in that directory. This is going to be a good
way to test your browser.

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

-   Parse a URL into a scheme, host, port and path.
-   Connect to that host using the `sockets` and `ssl` libraries
-   Send an HTTP request to that host, including a `Host` header
-   Split the HTTP response into a status line, headers, and a body
-   Print the text (and not the tags) in the body

Yes, this is still more of a command-line tool than a web browser, but
it already has some of the core capabilities of a browser.

::: {.signup}
:::

Outline
=======

The complete set of functions, classes, and methods in our browser 
should look something like this:

::: {.cmd .python .outline html=True}
    python3 infra/outlines.py --html src/lab1.py
:::

Exercises
=========

*HTTP/1.1:* Along with `Host`, send the `Connection` header in the
`request` function with the value `close`. Your browser can now
declare that it is using `HTTP/1.1`. Also add a `User-Agent` header.
Its value can be whatever you want---it identifies your browser to the
host. Make it easy to add further headers in the future.

*File URLs*: Add support for the `file` scheme, which allows the browser
to open local files. For example, `file:///path/goes/here` should
refer to the file on your computer at location `/path/goes/here`. Also
make it so that, if your browser is started without a URL being given,
some specific file on your computer is opened. You can use that file
for quick testing.

*data:* Yet another scheme is *data*, which
allows inlining HTML content into the URL itself. Try navigating to
`data:text/html,Hello world!` in a real browser to see what happens. Add
support for this scheme to your browser. The *data* scheme is especially
convenient for making tests without having to put them in separate files.

*Body tag:* Only show text in an HTML document if it is between
`<body>` and `</body>`. This avoids printing the title and style
information. Try to do this in a single pass through the
document---that means not using string methods like `split` or similar. The
loop in `show` will need more variables to track tag names.

*Entities:* Implement support for the less-than (`&lt;`) and
greater-than (`&gt;`) entities. These should be printed as `<` and
`>`, respectively. For example, if the HTML response was
`&lt;div&gt;`, the `show` method of your browser should print `<div>`.
Entities allow web pages to include these special characters without
the browser interpreting them as tags.

*view-source:* In addition to HTTP and HTTPS, there are other schemes,
such as *view-source*; navigating in a real browser to
`view-source:http://browser.engineering/http.html` shows the HTML
source of this chapter rather than its rendered output. Add support
for the view-source scheme. Your browser should print the entire HTML
file as if it was text. *Hint*: To do so, you can utilize the entities
from the previous exercise, and add an extra `transform()` method that
adjusts the input to `show()` when in view-source mode, like this:
`show(transform(body))`.

*Compression:* Add support for HTTP compression, in which the browser
[informs the server][negotiate] that compressed data is acceptable.
Your browser must send the `Accept-Encoding` header with the value
`gzip`. If the server supports compression, its response will have a
`Content-Encoding` header with value `gzip`. The body is then
compressed. Add support for this case. To decompress the data, you can
use the `decompress` method in the `gzip` module. Calling `makefile`
with the `encoding` argument will no longer work, because compressed
data is not `utf8`-encoded. You can change the first argument `"rb"`
to work with raw bytes instead of encoded text. Most web servers send
compressed data in a `Transfer-Encoding` called [`chunked`][chunked].
You'll need to add support for that, too, to access most web servers
that support compressed data.[^te-gzip]

[negotiate]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Content_negotiation

[chunked]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Transfer-Encoding

[^te-gzip]: There's also a couple of `Transfer-Encoding`s that
    compress the data. Those aren't commonly used.

*Redirects:* Error codes in the 300 range request a redirect. When
your browser encounters one, it should make a new request to the URL
given in the `Location` header. Sometimes the `Location` header is a
full URL, but sometimes it skips the host and scheme and just starts
with a `/` (meaning the same host and scheme as the original request).
The new URL might itself be a redirect, so make sure to handle that
case. You don't, however, want to get stuck in a redirect loop, so
make sure limit how many redirects your browser can follow in a row.
You can test this with with the URL
<http://browser.engineering/redirect>, which redirects back to this
page.

*Caching:* Typically the same images, styles, and scripts are used on
multiple pages; downloading them repeatedly is a waste. It's generally
valid to cache any HTTP response, as long as it was requested with
`GET` and received a `200` response.^[Some other status codes like
`301` and `404` can also be cached.] Implement a cache in your browser
and test it by requesting the same file multiple times. Servers
control caches using the `Cache-Control` header. Add support for this
header, specifically for `no-store` and `max-age` values. If the
`Cache-Control` header contains any other value than these two, it's best not
to cache the response.

[^5]: On some systems, you can run `dig +short example.org` to do this
    conversion yourself.

[^6]: Today there are two versions of IP: IPv4 and IPv6. IPv6 addresses
    are a lot longer and are usually in hex, but otherwise the
    differences don't matter here.

[^7]: I'm skipping steps here. On wires you first have to wrap
    communications in ethernet frames, on wireless you have to do even
    more. I'm trying to be brief.

[^8]: Or a switch, or an access point, there are a lot of possibilities,
    but eventually there is a router.

[^9]: They may also record where the message came from so they can
    forward the reply back, especially in the case of NATs.


[^15]: The `DGRAM` stands for "datagram" and think of it like a
    postcard.

[^16]: Newer versions of HTTP use something called
    [QUIC](https://en.wikipedia.org/wiki/QUIC) instead of TCP, but our
    browser will stick to HTTP 1.0.

[^17]: While this code uses the Python `socket` library, your favorite
    language likely contains a very similar library. This API is
    basically standardized. In Python, the flags we pass are defaults,
    so you can actually call `socket.socket()`; I'm keeping the flags
    here in case you're following along in another language.

[^19]: If you're in another language, you might only have `socket.read`
    available. You'll need to write the loop, checking the socket
    status, yourself.

[^21]: Hard-coding `utf8` is not correct, but it's a shortcut that
    will work alright on most English-language websites. In fact, the
    `Content-Type` header usually contains a `charset` declaration
    that specifies encoding of the body. If it's absent, browsers
    still won't default to `utf8`; they'll guess, based on letter
    frequencies, and you see ugly � strange áççêñ£ß when they guess
    wrong. Incorrect-but-common `utf8` skips all that complexity.

[^22]: That said, some tags, like `img`, are content, not information
    about it.

[^23]: If this example causes Python to produce a `SyntaxError` pointing
    to the `end` on the last line, it is likely because you are running
    Python 2 instead of Python 3. These chapters assume Python 3.

[^24]: The `end` argument tells Python not to print a newline after the
    character, which it otherwise would.
