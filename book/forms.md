---
title: Sending Information to Servers
chapter: 8
prev: chrome
next: scripts
...

So far, our browser has seen the web as read only---but when you post
on Facebook, fill our a survey, or search Google, you're sending
information *to* servers as well as receiving information from them.
In this chapter, we'll build out support for HTML forms to understand
how the browser writes as well as reads the web.

How forms work
==============

HTML forms have a couple of moving pieces.

First, in HTML, there is a `form` element, which contains `input`
elements,[^or-others] which in turn can be edited by the user. So a
form might look like this:

[^or-others]: There are other elements similar to `input`, such as
    `select` or `textarea`. They work similarly enough; they just
    represent different kinds of user controls, like dropdowns and
    multi-line inputs.

``` {.html}
<form action="/submit">
    <p>Name: <input name=name value=1></p>
    <p>Comment: <input name=comment value=2></p>
    <p><button>Submit!</button></p>
</form>
```

This form contains two text entry boxes called `name` and `comment`.
When the user goes to this page, they can click on those boxes to edit
their values. Then, when they click the button at the end of the form,
the browser collects all of the name/value pairs and bundles them into
a format that looks like this:

``` {.example}
name=1&comment=2
```

This data is then sent to the server in an HTTP `POST` request,
specifically to the URL given by the `form` element's `action`
attribute and the usual rules of relative URLs. That `POST` request
looks a lot like a regular request, except that it has a body---you've
already seen HTTP responses with bodies, but requests can have them
too. So the overall `POST` request looks like this:

``` {.example}
POST /submit HTTP/1.0
Host: example.org
Content-Length: 16

name=1&comment=2
```

Note the `Content-Length` header; it's mandatory for `POST` requests.
The server then responds to this request with a web page, just like
normal, and the browser then does everything it normally does.

Forms require extensions across the whole browser to function
properly, from implementing HTTP `POST` through new layout objects
that draw `<input>` elements to handling buttons clicks. Let's get
started implementing all that!


Rendering widgets
=================

First, let's draw the input areas that the user will fill out.
Normally, applications want their input areas to look the same as in
other applications on the same OS, so they use OS libraries to draw an
input area directly.[^ttk] But browsers need a lot of control over
application styling, so they often draw input areas directly.

[^ttk]: For Python's Tk library, that's possible with the `ttk` library.

`<input>` elements are inline content, like text, laid out in lines.
So to support inputs we'll need a new kind of layout object, which
I'll call `InputLayout`, implemented much like `TextLayout`:

``` {.python}
class InputLayout:
    def __init__(self, node):
        self.node = node
        self.children = []
```

These `InputLayout` objects need a `layout` method to compute
their size, which for simplicity I'll hard-code:[^2]

[^2]: In real browsers, the `width` and `height` CSS properties can
    change the size of input elements.

``` {.python}
class InputLayout:
    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(px(self.node.style["font-size"]) * .75)
        self.font = tkinter.font.Font(size=size, weight=weight,
            slant=style)
        self.w = 200
        self.h = 20
```

Finally, we'll need to add a `draw` method for input elements, which
needs to both draw the text contents and make the input area noticably
distinct, so the user can find and click on it. For `<input>`, the
initial text in the input area is the element's `value` attribute, like this:

``` {.example}
Name: <input value="Pavel Panchekha">
```

For simplicity, I'll make input elements have a light gray background:

``` {.python replace=%22light%20gray%22/bgcolor }
class InputLayout:
    def paint(self, to):
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

``` {.python indent=4}
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

``` {.python indent=4}
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
We need the *input* part! Let's 1) allow the user to change that content, and 2) draw the content when it changes.

In this toy browser, I'm going to require the user to click on an
input element to change its content. We detect the click in
`Browser.handle_click`:

``` {.python indent=8}
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

``` {.python indent=12}
elif elt.tag == "input":
    elt.attributes["value"] = ""
```

Next, typing on the keyboard needs to change the value, and in order
to do that, we need to set the `focus` to point to this element:

``` {.python indent=12}
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
simple `draw` call was enough, we're now changing the web page HTML
itself! This means we must change the layout tree, and to do that, we
must call `layout`:

``` {.python indent=12}
elif elt.tag == "input":
    # ...
    self.layout(self.document.node)
```

Once focus has been moved to an input element, typing on the keyboard
has to change the input's contents:

``` {.python indent=4}
def keypress(self, e):
    # ...

    if not self.focus:
        return
    elif self.focus == "address bar":
        # ...
    else:
        self.focus.node.attributes["value"] += e.char
        self.layout(self.document.node)
```

While we're at it, let's modify `draw` to draw a cursor into the
focused input area:

``` {.python indent=4}
def draw(self):
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

Implementing forms
==================

We're going to need to implement a few different things:

-   Buttons
-   Handling button clicks
-   Finding the form containing a button
-   Finding all the input areas in a form
-   Form-encoding their data
-   Making POST requests

First, buttons. Buttons are a bit like `<input>` elements, in that
they are little rectangles placed in lines. Unlike `<input>` elements,
`<button>` elements aren't self-closing, and the contents of that
`<button>` element is what text goes inside the button. Modify
`InlineLayout` to create `InputLayout` objects for `<button>`
elements; now, we need to make `InputLayout` do something different in
its `draw` call.

First, let's give buttons a different color:

``` {.python}
class InputLayout:
    def paint(self, to):
        # ...
        bgcolor = \
            "light gray" if self.node.tag == "input" else "yellow"
        to.append(DrawRect(x1, y1, x2, y2, bgcolor))
        # ...
```

Then, buttons should get text from their contents instead of their
attributes:

``` {.python}
class InputLayout:
    def paint(self, to):
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

``` {.python indent=16}
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

``` {.python}
def submit_form(self, elt):
    while elt and elt.tag != "form":
        elt = elt.parent
    if not elt: return
```

Fourth, we need to find all of the input elements inside this form:

``` {.python}
def find_inputs(elt, out):
    if not isinstance(elt, ElementNode): return
    if elt.tag == "input" and "name" in elt.attributes:
        out.append(elt)
    for child in elt.children:
        find_inputs(child, out)
    return out
```

Fifth, we can form-encode the resulting parameters:


``` {.python}
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

``` {.python}
def submit_form(self, elt):
    # ...
    url = resolve_url(elt.attributes["action"], self.url)
    self.load(url, body)
```

This adds a new parameter to the browser's `load` method, which we can
pass to `request`:

``` {.python}
def load(self, url, body=None):
    # ...
    header, body = request(url, body)
```

Sixth and finally, to actually send a POST request, we need to modify
the `request` function to support the new argument. First, the method
needs to be configurable:

``` {.python}
def request(url, payload=None):
    # ...
    method = "POST" if payload else "GET"
```

We need to use this method:

``` {.python}
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

``` {.python}
def request(url, payload=None):
    # ...
    content_length = len(payload.encode("utf8"))
    body += "Content-Length: {}\r\n".format(content_length)
```

Note that I grab the length of the payload in bytes, not the length in
letters.

By the way, here we have form submissions when you click on the form
button---but browsers usually also submit forms if you press the
"Enter" key inside a form input field.[^mac-return] Implement that by
calling `submit_form` inside `pressenter` when a input element is in
focus.

[^mac-return]: Which macOS calls "Return", in homage to old type
    writers and referencing the fact that very old Mac operating
    systems used the carriage return character (instead of the line
    feed character) for new lines.

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

``` {.python file=server}
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

``` {.python file=server}
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
    opens the same port, it could receive data meant for the old,
    now-dead process.

Now, we tell the socket we're ready to accept connections:

``` {.python file=server}
s.listen()
```

To actually accept those connections, we enter a loop that runs once
per connection. At the top of the loop we call `s.accept` to wait for
a new connection:

``` {.python file=server}
while True:
    conx, addr = s.accept()
    handle_connection(conx)
```

That connection object is, confusingly, also a socket: it is the
socket corresponding to that one connection. We know what to do with
those: we read the contents and parse the HTTP message. But it's a
little trickier to do this in the server than in the browser, because
the browser waits for the server, and that means the server can't just
read from the socket until the connection closes.

Instead, we'll read from the socket line-by-line. First, we read the
request line:

``` {.python file=server}
def handle_connection(conx):
    req = conx.makefile("rb")
    reqline = req.readline().decode('utf8')
    method, url, version = reqline.split(" ", 2)
    assert method in ["GET", "POST"]
```

Then we read the headers until we get to a blank line, accumulating the
headers in a dictionary:

``` {.python file=server}
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

``` {.python file=server}
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

``` {.python file=server}
def handle_connection(conx):
    # ...
    response = "HTTP/1.0 200 OK\r\n"
    response += "Content-Length: {}\r\n".format(
        len(body.encode("utf8")))
    response += "\r\n" + body
    conx.send(response.encode('utf8'))
    conx.close()
```

This is a bare-bones server: it doesn't check that the browser is
using HTTP 1.0 to talk to it, it doesn't send back any headers at all
except `Content-Length`, and so on.

Now all that's left is implementing `handle_request`. We want some kind
of guest book, so let's create a list to store guest book entries:

``` {.python file=server}
ENTRIES = [ 'Pavel was here' ]
```

The `handle_request` function outputs a little HTML page with those entries:

``` {.python file=server}
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

``` {.python file=server}
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

``` {.python file=server}
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

``` {.python file=server}
def show_comments():
    # ...
    return out
```

We can have a `add_entry` function to handle form submissions:

``` {.python file=server}
def add_entry(params):
    if 'guest' in params:
        ENTRIES.append(params['guest'])
    return show_comments()
```

This frees up the `handle_request` function to just figure out which
of these two functions to call:

``` {.python file=server}
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

*Check boxes*: Add checkboxes. In HTML, checkbox `<input>`
elements with the `type` attribute set to `checkbox`. The checkbox is
checked if it has the `checked` attribute set, and unchecked
otherwise. Submitting checkboxes in a form is a little tricky,
though. A checkbox named `foo` only appears in the form encoding if
it is checked. Its key is its `name` and its value is the empty string.

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
