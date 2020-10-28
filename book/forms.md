---
title: Sending Information to Servers
chapter: 8
prev: chrome
next: scripts
...

Modern browsers not only allow reading but also writing content:
making social media posts, filling out online forms, searching for
content, and so on. The next few labs implement these features. To
start, this lab implements *web forms*, which allow the user to fill
out form information and then send that form to the server. Web forms
are used almost everywhere: you fill one out to post on Facebook, to
register to vote, or to search Google.

Rendering widgets
=================

When your browser sends information to a web server, that is usually
information that you've typed into some kind of input area, or a
check-box of some sort that you've checked. So the first step in
communicating with other servers is going to be to draw input areas on
the screen and then allow the user to fill them out.

On the web, there are two kinds of input areas: `<input>` elements,
which are for short, one-line inputs, and `<textarea>` elements, which
are for long, multi-line text. I'll implement `<input>` only, because
because `<textarea>` has a lot of strange properties.[^sig-ws]
Usually, web browsers communicate with the operating system and ask
the OS to draw the input areas themselves, because that way the input
areas will match the behavior and appearance of OS input areas. That's
*possible* in Tk,[^1] but in the interests of simplicity we'll be
drawing the input areas ourselves.

[^sig-ws]: Whitespace inside a text area is significant, but text
    still wraps, an unsual combination. Plus, they are pretty similar
    to ordinary `<input>` elements in implementation.
[^1]: In Python, you use the `ttk` library.

`<input>` elements are inline content, like text, laid out in lines.
So to support inputs we'll need a new kind of layout object, which
I'll call `InputLayout`, implemented much like `TextLayout`:

``` {.python .browser}
class InputLayout:
    def __init__(self, node):
        self.node = node
        self.children = []
```

These `InputLayout` objects need a `layout` method needs to compute
their size, which for simplicity I'll hard-code:[^2]

[^2]: In real browsers, the `width` and `height` CSS properties can
    change the size of input elements.

``` {.python .browser}
class InputLayout:
    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(px(self.node.style["font-size"]) * .75)
        self.font = tkinter.font.Font(size=size, weight=weight, slant=style)
        self.w = 200
        self.h = 20
```

Finally, we'll need to add a `draw` method for input elements, which
needs to both draw the text contents and make the input area noticably
distinct, so the user can find and click on it. For `<input>`, the
text in the input area is the element's `value` attribute, like this:

``` {.example}
Name: <input value="Pavel Panchekha">
```


For simplicity, I'll make input elements have a light gray background:

``` {.python .browser replace="light%20gray"/bgcolor}
class InputLayout:
    def draw(self, to):
        x1, x2 = self.x, self.x + self.w
        y1, y2 = self.y, self.y + self.h
        to.append(DrawRect(x1, y1, x2, y2, "light gray"))

        text = self.node.attributes.get("value", "")
        color = self.node.style["color"]
        to.append(DrawText(self.x, self.y, text, self.font, color))
```

Note that the background has to come before the text, lest the text be
obscured!

Finally, we need to create these `InputLayout` objects; we can do that
in `InlineLayout.recurse`:

``` {.python .browser indent=4}
def recurse(self, node):
    if isinstance(node, TextNode):
        self.text(node)
    elif node.tag == "input":
        self.input(node)
    else:
        for child in node.children:
            self.recurse(child)
```

The new `input` function is similar to `text`, except that input areas
don't need to be split into multiple words:

``` {.python .browser indent=4}
def input(self, node):
    child = InputLayout(node)
    child.layout()
    if self.children[-1].cx + child.w > self.w:
        self.flush()
    self.children[-1].append(child)
```

Try it out: you should now be able to see basic input elements as
light gray rectangles.

Interacting with widgets
========================

We've now got input elements rendering, but only as empty rectangles.
We need the *input* part! Let's 1) draw the content of input elements;
and 2) allow the user to change that content. I'll start with the
second, since until we do that there's no content to draw.

In this toy browser, I'm going to require the user to click on an
input element to change its content. We detect the click in
`Browser.handle_click`:

``` {.python .browser indent=8}
elt = obj.node
while elt:
    if isinstance(elt, TextNode):
        pass
    elif is_link(elt):
        # ...
    elif elt.tag == "input":
        # ...
    elt = elt.parent
```

Once we find an input element, we need to edit it. First of all, like
with the address bar, clicking on an input should clear its
content:[^unless-cursor]

[^unless-cursor]: Unless you've implemented some basic editing
    controls, like the "Cursor" exercise in [Chapter 7](chrome.md).

``` {.python .browser indent=12}
elif elt.tag == "input":
    elt.attributes["value"] = ""
```

Next, typing on the keyboard needs to change the value, and in order
to do that, we need to set the `focus` to point to this element:

``` {.python .browser indent=12}
elif elt.tag == "input":
    # ...
    self.focus = obj
```

Until now, the `focus` field was either `None` (nothing has been
clicked on) or `"address bar"` (the address bar has been clicked on).
Now we're adding the additional possibility that it is a layout object
that the user is typing into.

Finally, since we've changed the content of the input element (by
clearing it) we need to redraw the screen. But unlike before, where a
simple `render` call was enough, we're now changing the web page HTML
itself! This means we must change the layout tree, and to do that, we
must call `layout`:

``` {.python .browser indent=12}
elif elt.tag == "input":
    # ...
    self.layout(self.document.node)
```

Once focus has been moved to an input element, typing on the keyboard
has to change the input's contents. Let's add that to our browser,
soliciting input on the command line and then updating the element
with it:

``` {.python .browser indent=4}
def keypress(self, e):
    if not (len(e.char) == 1 and 0x20 <= ord(e.char) < 0x7f):
        return

    if not self.focus:
        return
    elif self.focus == "address bar":
        # ...
    else:
        self.focus.node.attributes["value"] += e.char
        self.layout(self.document.node)
```

While we're at it, let's modify `render` to draw a cursor into the
focused input area:

``` {.python .browser indent=4}
def render(self):
    # ...
    if self.focus == "address bar":
        # ...
    elif isinstance(self.focus, InputLayout):
        text = self.focus.node.attributes.get("value", "")
        x = self.focus.x + self.focus.font.measure(text)
        y = self.focus.y - self.scroll + 60
        self.canvas.create_line(x, y, x, y + self.focus.h)
```

Note that again, `layout` needs to be called because adding text into
the input means changing the HTML. Most likely, `layout` is now quite
slow in your browser, so typing into input forms is actually going to
be quite painful. We'll return to this in [Chapter 10](reflow.md) and
implement incremental layout to resolve this issue.

How forms work
==============

Filled-out forms go to the server. The way this works in HTML is
pretty tricky.

First, in HTML, there is a `<form>` element, which describes how to
submit all the input elements it contains through its `action` and
`method` attributes. The `method` attribute is either `get` or `post`,
and refers to an HTTP method; the `action` attribute is a relative
URL. The browser generates an HTTP request by combining the two.

Let's focus on POST submissions (the default). Suppose you have the
following form, on the web page `http://my-domain.com/form`:

``` {.html}
<form action=submit method=post>
    <p>Name: <input name=name value=1></p>
    <p>Comment: <input name=comment value=2></p>
    <p><button>Submit!</button></p>
</form>
```

This is the same as the little example web page above, except there's
now a `<form>` element and also the two text areas now have `name`
attributes, plus I've added a new `<button>` element. That element,
naturally, draws a button, and clicking on that button causes the form
to be submitted.

When this form is submitted, the browser will first determine that it
is making a POST request to `http://my-domain.com/submit` (using the
normal rules of relative URLs). Then, it will gather up all of the
input areas inside that form and create a *form-encoded* string
containing those input area names and values, which in this case will
look like this:

``` {.example}
name=1&comment=2
```

This form-encoded string will be the *body* of the HTTP POST request
the browser is going to send. Bodies are allowed on HTTP requests just
like they are in responses, even though up until now we've been
sending requests without bodies. The only caveat is that if you send a
body, you must send the `Content-Length` header, so that the server
knows how much of the request to wait for. So the overall request is:

``` {.example}
POST /submit HTTP/1.0
Content-Length: 16

name=1&comment=2
```

The server will then respond to the POST request with a normal web page,
which the browser will render.

Implementing forms
==================

We're going to need to implement a couple of different things:

-   Buttons
-   Handling button clicks
-   Finding the form containing a button
-   Finding all the input areas in a form
-   Form-encoding their data
-   Making POST requests

We'll go in order.

First, buttons. Buttons are a bit like `<input>` elements, in that
they are little rectangles placed in lines. Unlike `<input>` elements,
`<button>` elements aren't self-closing, and the contents of that
`<button>` element is what text goes inside the button. Modify
`InlineLayout` to create `InputLayout` objects for `<button>`
elements; now, we need to make `InputLayout` do something different in
its `draw` call.

First, let's give buttons a different color:

``` {.python .browser}
class InputLayout:
    def draw(self, to):
        # ...
        bgcolor = "light gray" if self.node.tag == "input" else "yellow"
        to.append(DrawRect(x1, y1, x2, y2, bgcolor))
        # ...
```

Then, buttons should get text from their contents instead of their
attributes:

``` {.python .browser}
class InputLayout:
    def draw(self, to):
        # ...
        if self.node.tag == "input":
            text = self.node.attributes.get("value", "")
        else:
            text = self.node.children[0].text
        # ...
```

The real reason buttons surround their contents is because a button
might contain an image, or styled text, or something like that---this
code doesn't support that, which in real browsers relies on something
called the `inline-block` display mode. You could implement that by
having the `InputLayout` have a child `BlockLayout`, but I'm skipping
it here for simplicity.

Ok, next up, button clicks. We need to extend `handle_click` with
button support. That requires modifying the condition in the big
`while` loop and then adding a new case to the big `if` statement:

``` {.python .browser indent=16}
# ...
elif elt.tag == "button":
    self.submit_form(elt)
# ...
```

Third, we need to find the form containing our button. That can happen
inside `submit_form`:[^3]

[^3]: Fun fact: HTML standardizes the `form` attribute for _input
    elements_, which in principle allows an input element to be
    outside the form it is supposed to be submitted with. But no
    browser implements that.

``` {.python .browser}
def submit_form(self, elt):
    while elt and elt.tag != "form":
        elt = elt.parent
    if not elt: return
```

Fourth, we need to find all of the input elements inside this form:

``` {.python .browser}
def find_inputs(elt, out):
    if not isinstance(elt, ElementNode): return
    if elt.tag == "input" and "name" in elt.attributes:
        out.append(elt)
    for child in elt.children:
        find_inputs(child, out)
    return out
```

Fifth, we can form-encode the resulting parameters:


``` {.python .browser}
def submit_form(self, elt):
    # ...
    inputs = find_inputs(elt, [])
    body = ""
    for input in inputs:
        name = input.attributes["name"]
        value = input.attributes.get("value", "")
        body += "&" + name + "=" + value.replace(" ", "%20")
    body = body[1:]
```

This isn't real form-encoding; this just replaces spaces by `"%20"`,
while real form-encoding escapes characters like the equal sign, the
ampersand, and so on. But our browser is a toy anyway, so for now
let's just try to avoid typing equal signs, ampersands, and so on into
forms.

Finally, we need to submit this form-encoded data in a POST request:

``` {.python .browser}
def submit_form(self, elt):
    # ...
    url = relative_url(elt.attributes["action"], self.url)
    self.load(url, body)
```

This adds a new parameter to the browser's `load` method, which we can
pass to `request`:

``` {.python .browser}
def load(self, url, body=None):
    # ...
    header, body = request(url, body)
```

Sixth and finally, to actually send a POST request, we need to modify
the `request` function to support the new argument. First, the method
needs to be configurable:

``` {.python .browser}
def request(url, payload=None):
    # ...
    method = "POST" if payload else "GET"
```

We need to use this method:

``` {.python .browser}
def request(url, payload=None):
    # ...
    body = "{} {} HTTP/1.0\r\n".format(method, path)
    body += "Host: {}\r\n".format(host)
    body += "\r\n" + (payload or "")
    s.send(body.encode("utf8"))
```

Also, when you send a payload like this in the request, you need to
send the `Content-Length` header. That's because the server, which is
receiving the POST request, needs to know how much content to read
before responding. So let's add another header, after `Host` and
before the payload itself:

``` {.python .browser}
def request(url, payload=None):
    # ...
    content_length = len(payload.encode("utf8"))
    body += "Content-Length: {}\r\n".format(content_length)
```

Note that I grab the length of the payload in bytes, not the length in
letters.

By the way, here we have form submissions when you click on the form
button---but browsers usually also submit forms if you type "Enter"
inside a form input field. Implement that by calling `submit_form`
inside `pressenter` when a input element is in focus.

Once we've made the POST request, the server will send back a new web
page to render, which our browser needs to lex, parse, style, and lay
that page out. That all happens in `load` in the same way.

With these changes we should now have a browser capable of submitting
simple forms!

Receiving POST requests
=======================

We need to test our browser's forms functionality. Let's test with
our own simple web server. This server will show a simple form with a
single text entry and remember anything submitted through that form.
Then, it'll show you all of the things that it remembers. Call it a
guest book.^[Online guest books... so 90s...]

A web server is a different program from a web browser, so let's start
a new file. The server will need to:

-   Open a socket and listen for connections
-   Parse HTTP requests it receives
-   Respond to those requests with an HTML web page

I should note that the server I am building will be exceedingly simple,
because this is, after all, a book on web *browser* engineering.

Let's start by opening a socket. Like for the browser, we need to
create an internet streaming socket using TCP:

``` {.python .server}
import socket
s = socket.socket(
    family=socket.AF_INET,
    type=socket.SOCK_STREAM,
    proto=socket.IPPROTO_TCP,
)
```

Now, instead of calling `connect` on this socket (which causes it to
connect to some other server), we'll call `bind`, which opens a port
waits for other computers to connect to it:

``` {.python .server}
s.bind(('', 8000))
```

Here, the first argument to `bind`, the address, is set to the empty
string, which means that the socket will accept connections from any
other computer. The second argument is the port on *your* machine that
you want the server to listen on. I've chosen `8000` here, since
that's probably open and, being larger than 1024, doesn't require
administrator privileges. But you can pick a different number if, for
whatever reason, port 8000 is taken on your machine.

::: {.quirk}
A note about debugging servers. If a server crashes with a connection
open on some port, your OS prevents the port from being
reused[^why-wait] for a few seconds. So if your server crashes, you
might need to wait about a minute before you restart it, or you'll
get errors about addresses being in use.
:::

[^why-wait]: When your process crashes, the computer on the end of the
    connection won't be informed immediately; if some other process
    opens the same port, it could receive data means for the old,
    now-dead process.

Now, we tell the socket we're ready to accept connections:

``` {.python .server}
s.listen()
```

To actually accept those connections, we enter a loop that runs once
per connection. At the top of the loop we call `s.accept` to wait for
a new connection:

``` {.python .server}
while True:
    conx, addr = s.accept()
    handle_connection(conx)
```

That connection object is, confusingly, also socket: it is the socket
corresponding to that one connection. We know what to do with those:
we read the contents and parse the HTTP message. But it's a little
trickier to do this in the server than in the browser, because the
browser waits for the server, and that means the server can't just
read from the socket until the connection closes.

Instead, we'll read from the socket line-by-line. First, we read the
request line:

``` {.python .server}
def handle_connection(conx):
    req = conx.makefile("rb")
    reqline = req.readline().decode('utf8')
    method, url, version = reqline.split(" ", 2)
    assert method in ["GET", "POST"]
```

Then we read the headers until we get to a blank line, accumulating the
headers in a dictionary:

``` {.python .server}
def handle_connection(conx):
    # ...
    headers = {}
    for line in req:
        line = line.decode('utf8')
        if line == '\r\n': break
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()
```

Finally we read the body, but only when the `Content-Length` header
tells us how much of it to read (that's why that header is mandatory on
`POST` requests):

``` {.python .server}
def handle_connection(conx):
    # ...
    if 'content-length' in headers:
        length = int(headers['content-length'])
        body = req.read(length).decode('utf8')
    else:
        body = None

    body = handle_request(method, url, headers, body)
```

Let's fill in `handle_request` later; it returns a string containing
the resulting HTML web page. We need to send it back to the browser:

``` {.python .server}
def handle_connection(conx):
    # ...
    response = "HTTP/1.0 200 OK\r\n"
    response += "Content-Length: {}\r\n".format(len(body.encode("utf8")))
    response += "\r\n" + body
    conx.send(response.encode('utf8'))
    conx.close()
```

This is a bare-bones server: it doesn't check that the browser is
using HTTP 1.0 to talk to it, it doesn't send back any headers at all
except `Content-Length`, and so on. But look: it's a toy web server
that talks to a toy web browser. Cut it some slack.

All that's left is implementing `handle_request`. We want some kind of
guest book, so let's create a list to store guest book entries:

``` {.python .server}
ENTRIES = [ 'Pavel was here' ]
```

The `handle_request` function outputs a little HTML page with those entries:

``` {.python .server}
def handle_request(method, url, headers, body):
    out = "<!doctype html>"
    for entry in ENTRIES:
        out += "<p>" + entry + "</p>"
    return out
```

This is---let's call it "minimal"---HTML, so it's a good thing our
browser will insert implicit tags and so on. For now, I'm ignoring the
method, the URL, the headers, and the body entirely.

You should be able to run this minimal core of a web server and then
direct your browser to `http://localhost:8000/`, `localhost` being
what your computer calls itself and `8000` being the port we chose
earlier. You should see a list of (one) guest book entry.

Let's now make it possible to add to the guest book. First, let's
add a form to the top of the page:

``` {.python .server}
def handle_request(method, url, headers, body):
    # ...
    out += "<form action=add method=post>"
    out +=   "<p><input name=guest></p>"
    out +=   "<p><button>Sign the book!</button></p>"
    out += "</form>"
    # ...
```

This form tells the browser to submit data to
`http://localhost:8000/add`; the server needs to react to such
submissions. First, we will need to undo the form-encoding:

``` {.python .server}
def form_decode(body):
    params = {}
    for field in body.split("&"):
        name, value = field.split("=", 1)
        params[name] = value.replace("%20", " ")
    return params
```

To handle submissions, `handle_request` will first need to figure out
what kind of request this is (browsing or form submission), then get
the guest book comment, add it to `ENTRIES`, and then draw the page
with the new comment shown. To keep this organized, let's rename
`handle_request` to `show_comments`:

``` {.python .server}
def show_comments():
    # ...
    return out
```

We can have a `add_entry` function to handle form submissions:

``` {.python .server}
def add_entry(params):
    if 'guest' in params:
        ENTRIES.append(params['guest'])
    return show_comments()
```

This frees up the `handle_request` function to just figure out which
of these two functions to call:

``` {.python .server}
def handle_request(method, url, headers, body):
    if method == 'POST':
        params = form_decode(body)
        if url == '/add':
            return add_entry(params)
        else:
            return show_comments()
    else:
        return show_comments()
```

Try it! You should be able to restart the server, open it in your
browser, and update the guest book a few times. You should also be
able to use the guest book from a real web browser.

Summary
=======

We've added an important new capability, form submission, to our web
browser. It is a humble beginning, but our toy web browser is no
longer just for reading pages: it is becoming an application platform.
Plus, we now have a little web server for our browser to talk to. Life
is better with friends!

Exercises
=========

*Check boxes*: Add check boxes. In HTML, check boxes `<input>`
elements with the `type` attribute set to `checkbox`. The check box is
checked if it has the `checked` attribute set, and unchecked
otherwise. Submitting check boxes in a form is a little tricky,
though. A check box named `foo` only appears in the form encoding if
it is checked. Its key is its identifier and its value is the empty
string.

*GET forms*: Forms can be submitted via GET requests as well as POST
requests. In GET requests, the form-encoded data is pasted onto the
end of the URL, separated from the path by a question mark, like
`/search?q=hi`; GET form submissions have no body. Implement GET form
submissions.

*Resubmit requests*: One reason to separate GET and POST requests is
that GET requests are supposed to be *idempotent* (read-only,
basically) while POST requests are assumed to change the web server
state. That means that going "back" to a GET request (making the
request again) is safe, while going "back" to a POST request is a bad
idea. Change the browser history to record what method was used to
access each URL, and the POST body if one was used. When you go back
to a POST-ed URL, ask the user if they want to resubmit the form.
Don't go back if they say no; if they say yes, submit a POST request
with the same body as before.

*Message board*: Right now our web server is a simple guest book.
Extend it into a simple message board by adding support for topics.
Each topic should have its own URL and its own list of messages. So,
for example, `/cooking` should be a page of posts (about cooking) and
comments submitted through the form on that page should only show up
when you go to `/cooking`, not when you go to `/cars`. Make the home
page, from `/`, show links to each topic's page.

*Tab*: In most browsers, the `<Tab>` key moves focus from one input
field to the next. Implement this behavior in your browser. The "tab
order" of input elements should be the same as the order of `<input>`
elements on the page.

