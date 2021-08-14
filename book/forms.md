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
    `select` and `textarea`. They work similarly enough; they just
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
I'll call `InputLayout`. Let's start by copying `TextLayout` and
renaming it to `InputLayout`. We'll then need to make some quick
edits.

First, there's no `word` argument to `InputLayout`s:

``` {.python}
class InputLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.children = []
        self.parent = parent
        self.previous = previous
```

Second, let's give `InputLayout` objects a fixed width:

``` {.python}
INPUT_WIDTH_PX = 200

class InputLayout:
    def layout(self):
        # ...
        self.width = INPUT_WIDTH_PX
        # ...
```

These `input` and `button` elements need to be visually distinct so
the user can easily find them. With our browser's limited styling
capabilities, let's go with a style like this:

``` {.css}
input {
    font-size: 16px; font-weight: normal; font-style: normal;
    background-color: lightblue;
}
button {
    font-size: 16px; font-weight: normal; font-style: normal;
    background-color: orange;
}
```

So when the browser paints an `InputLayout` it needs to draw both a
background:

``` {.python}
class InputLayout:
    def paint(self, display_list):
        bgcolor = self.node.style.get("background-color",
                                      "transparent")
        if bgcolor != "transparent":
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, bgcolor)
            display_list.append(rect)
```

And also the text inside:

``` {.python}
class InputLayout:
    def paint(self, display_list):
        # ...
        if self.node.tag == "input":
            text = self.node.attributes.get("value", "")
        elif self.node.tag == "button":
            text = self.node.children[0].text

        color = self.node.style["color"]
        display_list.append(
            DrawText(self.x, self.y, text, self.font, color))
```

By this point in the book, you've seen new layout objects plenty of
times. So I'm not describing this code in detail; new layout objects
is just one of the standard ways you extend the browser.

With `InputLayout` written we now need to create some of these layout
objects. We'll do so in `InlineLayout`:

``` {.python}
class InlineLayout:
    def recurse(self, node):
        if isinstance(node, Text):
            self.text(node)
        else:
            if node.tag == "br":
                self.new_line()
            elif node.tag == "input" or node.tag == "button":
                self.input(node)
            if node.tag != "button":
                for child in node.children:
                    self.recurse(child)
```

Note that text children of `button` elements are ignored. This is because
the text contains the content of the button, not text to go after it.
Text `input` elements, on the other hand, use the `value` attribute to draw
their contents, and any text children are laid out next to the `input` as if
they were sibligs in the document tree.

The new `input` method is based on how the `text` method handles each
word:

``` {.python}
class InlineLayout:
    def input(self, node):
        w = INPUT_WIDTH_PX
        if self.cursor_x + w > self.x + self.width:
            self.new_line()
        line = self.children[-1]
        input = InputLayout(node, line, self.previous_word)
        line.children.append(input)
        self.previous_word = input
        self.cursor_x += w + font.measure(" ")
```

With all of this done, you should be able to open a web page with
`input` and `button` elements, and see them show up as blue and orange
rectangles.

::: {.further}
The reason buttons surround their contents (instead of using an attribute) is
that a button might contain an image, styled text, or other content. Our
browser doesn't support that situation, which in real browsers relies on
something called the `inline-block` display mode - a way of putting a block
element within an inline. You could implement that by having the `InputLayout`
have a child `BlockLayout`, but I'm skipping it here for simplicity.

Real browsers can also nest inline layout objects. Inline layout objects in
general form a tree of their own. This tree is needed for styling and hit
testing parts of this tree.
:::

Interacting with widgets
========================

We've now got input elements rendering, but when you click on them
they don't yet do anything! We need to allow the user to type stuff
into an `input`. Let's make it work the same way the address bar
does---clicking on an input element will clear it, and then you can
type into it.

The clearing part is easy: we need another case inside `Tab`'s `click`
method:

``` {.python}
class Tab:
    def click(self, x, y):
        while elt:
            # ...
            elif elt.tag == "input":
                elt.attributes["value"] = ""
            # ...
```

But keyboard input is harder. Think back to how we [implemented the
address bar](chrome.md): we added a `focus` field that remembered what
we clicked on and sent it key presses. We'll want something like that
for text entries---a `focus` field---but it's going to be more complex
because text entries live inside a `Tab`, not inside the `Browser`.

Naturally, we will need a `focus` field on each `Tab`, to remember
which text entry (if any) we've recently clicked on:

``` {.python}
class Tab:
    def __init__(self):
        # ...
        self.focus = None
```

Now when we click on an input element, we need to set `focus`:

``` {.python}
class Tab:
    def click(self, x, y):
        while elt:
            elif elt.tag == "input":
                # ...
                self.focus = elt
                return
```

But remember that keyboard input isn't handled by the `Tab`---it's
handled by the `Browser`. So how does the `Browser` even know that the
`Tab` should handle a certain keyboard event? Well, the answer is that
the `Browser` has to remember that the `Tab` is in focus!

So, when you click on the web page, the `Browser` updates its focus as
well:

``` {.python}
class Browser:
    def handle_click(self, e):
        if e.y < CHROME_PX:
            self.focus = None
            # ...
        else:
            self.focus = "content"
            # ...
        self.draw()
```

Now when a key press happens, the `Browser` can either send it to the
address bar or the active tab:

``` {.python}
class Browser:
    def handle_key(self, e):
        # ...
        elif self.focus == "content":
            self.tabs[self.active_tab].keypress(e.char)
            self.draw()
```

Each tab's `keypress` method would then use the tab's `focus` field to
add the character to the right text entry:

``` {.python}
class Tab:
    def keypress(self, char):
        if self.focus:
            self.focus.attributes["value"] += char
```

This hierarchical focus handling is an important pattern for combining
graphical widgets; in a real browser, where web pages can be embedded
into one another with `iframe`s, the focus tree can be arbitrarily deep.

So now we have user input working with `input` elements. Before we
move on, there is one last tweak that we need to make: drawing the
text cursor. We can do that in the `Tab`'s `draw` method:

``` {.python}
class Tab:
    def draw(self, canvas):
        # ...
        if self.focus:
            # ...
```

We'll first need to figure out where the text entry is located,
onscreen, by finding its layout object:

``` {.python indent=8}
if self.focus:
    obj = [obj for obj in tree_to_list(self.document, [])
           if obj.node == self.focus][0]
```

Then using that layout object we can find the coordinates where the
cursor starts:

``` {.python indent=8}
if self.focus:
    # ...
    text = self.focus.attributes.get("value", "")
    x = obj.x + obj.font.measure(text)
    y = obj.y - self.scroll + CHROME_PX
```

And finally draw the cursor itself:

``` {.python indent=8}
if self.focus:
    # ...
    canvas.create_line(x, y, x, y + obj.height)
```

Excellent: you can now click on a text entry to type into it and
modify its value. So with the form now filled out, we need to turn to
submitting it.



Implementing forms
==================

You submit a form by clicking on a `button`. So let's add another
condition to the big `while` loop in `click`:

``` {.python}
class Tab:
    def click(self, x, y):
        while elt:
            # ...
            elif elt.tag == "button":
                # ...
            # ...
```

Once we've found the button, we need to find the form that it's in, by
walking up the HTML tree:


``` {.python indent=12}
elif elt.tag == "button":
    while elt:
        if elt.tag == "form" and "action" in elt.attributes:
            return self.submit_form(elt)
        elt = elt.parent
```

The `submit_form` method is then in charge of finding all of the input
elements, encoding them in the right way, and sending the `POST`
request. First, we look through all the descendents of the `form` to
find `input` elements:

``` {.python}
class Tab:
    def submit_form(self, elt):
        inputs = [node for node in tree_to_list(elt, [])
                  if isinstance(node, Element)
                  and node.tag == "input"
                  and "name" in node.attributes]
```

For each of those `input` elements, we need to extract the `name`
attribute and the `value` attribute, and _form-encode_ both of them.
Form encoding is how the name/value pairs are formatted in the HTTP
`POST` request. Basically: name, then equal sign, then value; and
name-value pairs are separated by ampersands:

``` {.python}
class Tab:
    def submit_form(self, elt):
        # ...
        body = ""
        for input in inputs:
            name = input.attributes["name"]
            value = input.attributes.get("value", "")
            body += "&" + name + "=" + value
        body = body [1:]
```

Now, any time you see something like this, you've got to ask: what if
the name or the value has an equal sign or an ampersand in it? In
fact, there is special handling for special characters: "percent
encoding" replaces all special characters with a percent sign followed
by those characters' hex codes. For example, a space becomes `%20` and
a period becomes `%2e`. Python provides a percent-encoding function as
`quote` in the `urllib.parse` module:


``` {.python indent=8}
for input in inputs:
    # ...
    name = urllib.parse.quote(name)
    value = urllib.parse.quote(value)
    # ...
```

You can write your own `percent_encode` function using Python's `ord`
and `hex` functions instead if you'd like,[^why-use-library] but here
we're using the standard function for expediency; it's not a
particularly interesting funciton, but it is necessary. (If you skip
percent encoding, your browser won't handle requests with equal signs,
percent signs, or ampersands correctly).

[^why-use-library]: Why use the `urllib` library here, but not
    elsewhere in our browser? Why, for example, use its `quote` method
    here but not its `parse` method in [Chapter 1](http.md)?
    Basically, because while percent encoding is necessary, it is
    not conceptually interesting, and in these later chapters my goal
    is to show how conceptual extensions to the browser get built.
    Some details are necessarily elided.

Now that `submit_form` has built the request body, it needs to finally
send that request:

``` {.python}
def submit_form(self, elt):
    # ...
    url = resolve_url(elt.attributes["action"], self.url)
    self.load(url, body)
```

This uses a new parameter to the browser's `load` method for the
request body. Let's pass that through to `request`:

``` {.python indent=4}
def load(self, url, body=None):
    # ...
    headers, body = request(url, body)
```

Then `request` can send that request body. That requires a few
changes to `request`. First, it needs to use `POST`, not `GET`:

``` {.python}
def request(url, payload=None):
    # ...
    method = "POST" if payload else "GET"
    # ...
    body = "{} {} HTTP/1.0\r\n".format(method, path)
```

Then we need to send the `Content-Length` header, which is mandatory
on `POST` requests:

``` {.python}
def request(url, payload=None):
    # ...
    if payload:
        length = len(payload.encode("utf8"))
        body += "Content-Length: {}\r\n".format(length)
    # ...
```

Note that I grab the length of the payload in bytes, not the length in
letters. Finally, we need to add the actual payload and send it:

``` {.python}
def request(url, payload=None):
    # ...
    body += "\r\n" + (payload or "")
    s.send(body.encode("utf8"))
    # ...
```

So---now we've sent the `POST` request. From the point of view of the
browser, that's about it: the server will respond with a web page and
the browser will render it in the totally normal way. But to better
understand the whole cycle---and also to make it easier to test our
browser's form support---let's take a small detour out of the browser
and look at how the server will handle these requests.


Receiving POST requests
=======================

Let's test our web browser by making our own simple web server. This
server will show a simple form with a single text entry and remember
anything submitted through that form. Then, it'll show you all of the
things that it remembers. Call it a guest book.^[Online guest books...
so 90s...]

A web server is a different program from a web browser, so let's start
a new file. The server will need to:

-   Open a socket and listen for connections
-   Parse HTTP requests it receives
-   Respond to those requests with an HTML web page

Now, this is a book on web *browser* engineering, so I won't focus too
much on the implementation choices. But it's valuable to know how the
other side of the connection works, as we start diving deeper into how
browsers help run full-fledged web applications.

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
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('', 8000))
s.listen()
```

Let's look at the `bind` call first. Its first argument is says who
should be allowed to make connections *to* the server. The empty
string means that anyone can. The second argument is the port on
*your* machine that you want the server to listen on. I've chosen
`8000` here. `8000` is similar to 80, the default port, but because
it's larger than 1024 it doesn't require administrator privileges. You
can pick a different number if, for whatever reason, port 8000 is
taken on your machine.

Now, before the `bind` call is a `setsockopt` call. If a server
crashes with a connection open on some port, your OS prevents the port
from being reused[^why-wait] for a short period. So if your server
crashes, normally you need to wait about a minute before you restart
it, or you'll get errors about addresses being in use. By calling
`setsockopt` with the `SO_REUSEADDR` option we change that default and
allow the OS to immediately reuse the port---which makes debugging our
server a lot easier.

[^why-wait]: When your process crashes, the computer on the end of the
    connection won't be informed immediately; if some other process
    opens the same port, it could receive data meant for the old,
    now-dead process.

Finally, after bind, the `listen` call tells the OS that we're ready
to accept connections.

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

    status, body = handle_request(method, url, headers, body)
```

Let's fill in `handle_request` later; it returns a string containing
the resulting HTML web page. We need to send it back to the browser:

``` {.python file=server}
def handle_connection(conx):
    # ...
    response = "HTTP/1.0 {}\r\n".format(status)
    response += "Content-Length: {}\r\n".format(
        len(body.encode("utf8")))
    response += "\r\n" + body
    conx.send(response.encode('utf8'))
    conx.close()
```

This is a bare-bones server: it doesn't check that the browser is
using HTTP 1.0 to talk to it, it doesn't send back any headers at all
except `Content-Length`, and so on. Again---this is a web *browser*
book. But it'll do.

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
    return "200 OK", out
```

This is---let's call it "minimal"---HTML, so it's a good thing our
browser will insert implicit tags and so on. For now, I'm ignoring the
method, the URL, the headers, and the body entirely.

Run this minimal web server and then open a browser to
`http://localhost:8000/`, `localhost` being what your computer calls
itself and `8000` being the port we chose earlier. You should see a
list of (one) guest book entry. As you debug this web server, it's
probably easier to use a real web browser instead of the one you're
writing. That way you don't have to worry about browser bugs.

Now, let's make it possible to add to the guest book. First, let's add
a form to the top of the page:

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
        params[urllib.unquote(name)] = urllib.unquote(value)
    return params
```

Now that we have form submissions, `handle_request` will field two
kinds of requests: regular browsing and form submissions. Let's
separate the two kinds of requests into different functions. Rename
the current `handle_request` to `show_comments`:

``` {.python file=server}
def show_comments():
    # ...
    return out
```

A new `add_entry` function can handle form submissions:

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
    if method == "POST" and url == "/add":
        params = form_decode(body)
        return "200 OK", add_entry(params)
    elif method == "GET" and url == "/":
        return "200 OK", show_comments()
    else:
        return "404 Not Found", not_found(url, method)
```

Now that the browser request matters, I've added a "404" response.
Fitting the austere stylings of our web page, here's the 404 page:

``` {.python file=server}
def not_found(url, method):
    out = "<!doctype html>"
    out += "<h1>{} {} not found!</h1>".format(method, url)
    return out
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

*Enter key*: In most browsers, if you hit the "Enter" or "Return" key
while inside a text entry, that submits the form that the text entry
was in. Add this feature to your browser.

*Check boxes*: Add checkboxes. In HTML, checkbox `<input>`
elements with the `type` attribute set to `checkbox`. The checkbox is
checked if it has the `checked` attribute set, and unchecked
otherwise. Submitting checkboxes in a form is a little tricky,
though. A checkbox named `foo` only appears in the form encoding if
it is checked. Its key is its `name` and its value is the empty string.

*Blurring*: Right now, if you click inside a text entry, and then
inside the address bar, two cursors will appear on the screen. To fix
this, add a `blur` method to each `Tab` which unfocuses anything that
is focused, and call it before changing focus.

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
