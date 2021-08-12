---
title: Sending Information to Servers
chapter: 8
prev: chrome
next: scripts
...

So far, our browser has seen the web as read only---but when you post
on Facebook, fill out a survey, or search Google, you're sending
information *to* servers as well as receiving information from them.
In this chapter, we'll start to transform our browser into a platform
for web applications by building out support for HTML forms, the
simplest way for a browser to send information to a server.

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
that draw `input` elements to handling buttons clicks. That makes it
a great starting point for transforming our toy browser into an
application platform---our goal for these next few chapters. Let's get
started implementing all that!


Rendering widgets
=================

First, let's draw the input areas that the user will fill
out.[^styled-widgets] Input areas are inline content, laid out in
lines next to text. So to support inputs we'll need a new kind of
layout object, which I'll call `InputLayout`. We can copy `TextLayout`
and use it as a template, but need to make some quick edits.

[^styled-widgets]: Most applications use OS libraries to draw input
areas, so that those input areas look like other applications on that
OS. But browsers need a lot of control over application styling, so
they often draw their own input areas.

First, there's no `word` argument to `InputLayout`s:

``` {.python}
class InputLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.children = []
        self.parent = parent
        self.previous = previous
```

Second, `input` elements usually have a fixed width:

``` {.python}
INPUT_WIDTH_PX = 200

class InputLayout:
    def layout(self):
        # ...
        self.width = INPUT_WIDTH_PX
        # ...
```

The `input` and `button` elements need to be visually distinct so the
user can find them easily. Our browser's styling capabilities are
limited, so let's use background color to do that:

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

When the browser paints an `InputLayout` it needs to draw the
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

It also needs to draw the text inside:

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
times. So I'm glossing over details; the point is that new layout
objects are one standard place to extend the browser.

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
            else:
                for child in node.children:
                    self.recurse(child)
```

Note we don't recurse into `button` elements, because the button
element is reponsible for drawing its contents. Meanwhile `input`
elements are self-closing, so they never have children.

Finally, this new `input` method is similar to the `text` method,
creating a new layout object and adding it to the current line:

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

With these changes the browser should now draw with `input` and
`button` elements as blue and orange rectangles.

::: {.further}
The reason buttons surround their contents but input areas don't is
that a buttons can contain images, styled text, or other content. In a
real browser, that relies on the `inline-block` display mode: a way of
putting a block element within an inline.
:::

Interacting with widgets
========================

We've got `input` elements rendering, but you can't edit their contents
yet. That's the whole point! Let's make `input` elements work like the
address bar does---clicking on one will clear it and let you type into
it.

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
we clicked on so we could send it our key presses. We need something
like that `focus` field for input areas, but it's going to be more
complex because the input areas live inside a `Tab`, not inside the
`Browser`.

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
handled by the `Browser`. So how does the `Browser` even know when
keyboard events should be sent to the `Tab`? The `Browser` has to
remember that in its own `focus` field!

In other words, when you click on the web page, the `Browser` updates
its `focus` field to remember that the user is interacting with the
page, not the browser interface:

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

Note that the `if` branch above, which corresponds to the user
clicking in the browser interface, unsets `focus` by default, but then
some existing code in that branch will set `focus` to `address bar` if
the user actually clicked in the address bar.

When a key press happens, the `Browser` sends it either to the address
bar or to the active tab `keypress` method:

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
text cursor in the `Tab`'s `draw` method. We'll first need to figure
out where the text entry is located, onscreen, by finding its layout
object:

``` {.python}
class Tab:
    def draw(self, canvas):
        # ...
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

Now you can click on a text entry, type into it, and modify its value.
So the next step is submitting the now-filled-out form.

::: {.further}
The code that draws the text cursor here is kind of clunky---you could
imagine each layout object knowing if it's focused and then being
responsible for drawing the cursor. That's the more traditional
approach in GUI frameworks, but Chrome uses [the design presented
here][focused-element] to make sure the cursor can be [globally
styled][frame-caret].
:::

[focused-element]: https://source.chromium.org/chromium/chromium/src/+/main:third_party/blink/renderer/core/dom/document.h;l=881;drc=80def040657db16e79f59e7e3b27857014c0f58d
[frame-caret]: https://source.chromium.org/chromium/chromium/src/+/main:third_party/blink/renderer/core/editing/frame_caret.h?q=framecaret&ss=chromium


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
the name or the value has an equal sign or an ampersand in it? So in
fact, "percent encoding" replaces all special characters with a
percent sign followed by those characters' hex codes. For example, a
space becomes `%20` and a period becomes `%2e`. Python provides a
percent-encoding function as `quote` in the `urllib.parse`
module:[^why-use-library]

``` {.python indent=8}
for input in inputs:
    # ...
    name = urllib.parse.quote(name)
    value = urllib.parse.quote(value)
    # ...
```

[^why-use-library]: You can write your own `percent_encode` function
using Python's `ord` and `hex` functions if you'd like. I'm using the
standard function for expediency. [Earlier in the book](http.md),
using these library functions would have obscured key concepts, but by
this point percent encoding is necessary but not conceptually
interesting.

Now that `submit_form` has built a request body, it needs make a
`POST` request. I'm going to defer that responsibility to the `load`
function, which handles making requests:

``` {.python}
def submit_form(self, elt):
    # ...
    url = resolve_url(elt.attributes["action"], self.url)
    self.load(url, body)
```

The new argument `load` is then passed through to `request`:

``` {.python indent=4}
def load(self, url, body=None):
    # ...
    headers, body = request(url, body)
```

In `request`, this new argument is used to decide between a `GET` and
a `POST` request:

``` {.python}
def request(url, payload=None):
    # ...
    method = "POST" if payload else "GET"
    # ...
    body = "{} {} HTTP/1.0\r\n".format(method, path)
```

If there it's a `POST` request, the `Content-Length` header is mandatory:

``` {.python}
def request(url, payload=None):
    # ...
    if payload:
        length = len(payload.encode("utf8"))
        body += "Content-Length: {}\r\n".format(length)
    # ...
```

Note that I grab the length of the payload in bytes, not the length in
letters. Finally, we need send the payload itself:

``` {.python}
def request(url, payload=None):
    # ...
    body += "\r\n" + (payload or "")
    s.send(body.encode("utf8"))
    # ...
```

So that's how the `POST` request gets sent. Then the server responds
with an HTML page and the browser will render it in the totally normal
way. That's basically it for forms on the browser side. But before we
move on to the next chapter, let me explain how forms are used to
build browser applications.

::: {.further}
Something about event dispatching
:::

How web applications work
=========================

So... How do forms support web applications? When you use an
application from your browser---whether you are registering to vote,
looking at pictures of your baby cousin, or checking your
email---there are typically[^exceptions] two components involved: a
front-end that runs in your browser, and a back-end that runs on the
server. As you use an application, the front- and back-ends send data
to each other over HTTP requests.

[^exceptions]: Here's I'm talking in general terms. There are some
    browser applications without a backend, and others where the
    front-end is very simple and almost all the logic is in the
    backend.

For example, imagine a simple message board application. The server
stores the state of the message board---who has posted what---and has
logic for updating that state. But all the actual interaction with the
page---drawing the posts, letting the user enter new ones---happens in
the browser. Both components are necessary.

The browser and the server interact over HTTP. The browser first makes
a `GET` request to the server to load the current message board. You
can think of this as downloading and starting the front-end in the
browser. The user interacts with the browser to type a new post, and
submits it to the server (say, via a form). That causes the browser to
make a `POST` request to the server, which instructs the server to
update the message board state.

All considered, forms are a simplistic, old-fashioned implementation
of this paradigm. But they are a simple, minimal introduction to this
cycle of request and response and to how browser applications work.
Modern applications, which use asynchronous requests and Javascript
code and complex styling---all of which appear in later chapters---are
based on the same principles.

To better understand the request/response cycle---and also to give us
a way to test our browser's form support---let's take a small detour
and write a simple web server. Now, this is a book on web *browser*
engineering, so I won't be too thorough regarding implementation
choices. But it's valuable to know how the other side of the
connection works, as we start diving deeper into how browsers help run
full-fledged web applications.

::: {.further}
PUT and DELETE requests
:::

Receiving POST requests
=======================

Our simple web server will implement an online guest book:^[They were
very hip in the 90s---comment threads from before there was anything
to comment on.] anyone can leave a comment in the guest book, and
anyone who visits the guest book page can see all previous comments.

A web server is a different program from a web browser, so let's start
a new file. The server will need to:

-   Open a socket and listen for connections
-   Parse HTTP requests it receives
-   Respond to those requests with an HTML web page

Let's start by opening a socket. Like for the browser, we need to
create an internet streaming socket using TCP:

``` {.python file=server}
import socket
s = socket.socket(
    family=socket.AF_INET,
    type=socket.SOCK_STREAM,
    proto=socket.IPPROTO_TCP,
)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
```

The `setsockopt` call is optional. Normally, when a program has a
socket open and it crashes, your OS prevents that port from being
reused[^why-wait] for a short period. That's annoying when developing
a server, and calling `setsockopt` with the `SO_REUSEADDR` option
allows the OS to immediately reuse the port.

[^why-wait]: When your process crashes, the computer on the end of the
    connection won't be informed immediately; if some other process
    opens the same port, it could receive data meant for the old,
    now-dead process.

Now, with this socket, instead of calling `connect` (to connect to
some other server), we'll call `bind`, which waits for other computers
to connect:

``` {.python file=server}
s.bind(('', 8000))
s.listen()
```

Let's look at the `bind` call first. Its first argument is says who
should be allowed to make connections *to* the server. The empty
string means that anyone can. The second argument is the port others
will need to connect to to talk to our server; I've chosen `8000`. I
can't use 80, because ports below 1024 require administrator
privileges. But you can pick something other than 8000 if, for
whatever reason, port 8000 is taken on your machine.

Finally, after the `bind` call, the `listen` call tells the OS that
we're ready to accept connections.

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
little trickier in the server than in the browser, because the server
can't just read from the socket until the connection closes---the
browser is waiting for the server and won't close the connection.

So we've got to read from the socket line-by-line. First, we read the
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
```

Now the server needs to generate a web page in response. We'll get to
that later; for now, just abstract that away behind a `do_request`
call:

``` {.python file=server}
def handle_connection(conx):
    # ...
    status, body = do_request(method, url, headers, body)
```

The server then sends this page back to the browser:

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

This is all pretty bare-bones: our server doesn't check that the
browser is using HTTP 1.0 to talk to it, it doesn't send back any
headers at all except `Content-Length`, it doesn't support TLS, and so
on. Again---this is a web *browser* book. But it'll do.

Generating web pages
====================

So far all of this server code is "boilerplate"---any web application
will have similar code. What makes our server a guest book, on the
other hand, depends on what happens inside `do_request`. It needs to
store the guest book state, generate HTML pages, and respond to `POST`
requests.

Let's store guest book entries in a list:

``` {.python file=server}
ENTRIES = [ 'Pavel was here' ]
```

Usually web applications use *persistent* state, like a database, so
that the server can be restarted without losing state, but our guest
book need not be that resilient.

Next, `do_request` has to output HTML that shows those entries:

``` {.python file=server}
def do_request(method, url, headers, body):
    out = "<!doctype html>"
    for entry in ENTRIES:
        out += "<p>" + entry + "</p>"
    return "200 OK", out
```

This is definitely "minimal" HTML, so it's a good thing our browser
will inserts implicit tags and has some default styles. You can test
it out by run this minimal web server and, while it's running, direct
your browser to `http://localhost:8000/`, `localhost` being what your
computer calls itself and `8000` being the port we chose earlier. You
should see one guest book entry.

Note that as you debug debug this web server, it's probably easier to
use a real web browser instead of the toy one you're writing. That way
you don't have to worry about browser bugs. But this server should
support both real and toy browsers.

It should be possible for visitors to write in the guest book. That's
going to require the browser sending the server a `POST` request, and
forms are the easiest way to do that. So, let's add a form to the top
of the page:

``` {.python file=server}
def do_request(method, url, headers, body):
    # ...
    out += "<form action=add method=post>"
    out +=   "<p><input name=guest></p>"
    out +=   "<p><button>Sign the book!</button></p>"
    out += "</form>"
    # ...
```

When this form is submitted, the browser will send a `POST` request to
`http://localhost:8000/add`. So the server needs to react to these
submissions. That means `do_request` will field two kinds of requests:
regular browsing and form submissions. Let's separate the two kinds of
requests into different functions.

Rename the current `do_request` to `show_comments`:

``` {.python file=server}
def show_comments():
    # ...
    return out
```

This frees up the `do_request` function to figure out which function
to call:

``` {.python file=server}
def do_request(method, url, headers, body):
    if method == "GET" and url == "/":
        return "200 OK", show_comments()
    elif method == "POST" and url == "/add":
        params = form_decode(body)
        return "200 OK", add_entry(params)
    else:
        return "404 Not Found", not_found(url, method)
```

When a `POST` request to `/add` comes in, the first step is to decode
the request body:

``` {.python file=server}
def form_decode(body):
    params = {}
    for field in body.split("&"):
        name, value = field.split("=", 1)
        params[urllib.unquote(name)] = urllib.unquote(value)
    return params
```

The `add_entry` function just adds new guest book entries from the
form:

``` {.python file=server}
def add_entry(params):
    if 'guest' in params:
        ENTRIES.append(params['guest'])
    return show_comments()
```

Finally, I've added a "404" response. Fitting the austere stylings of
our web page, here's the 404 page:

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

Outline
=======

The complete set of functions, classes, and methods in our browser 
should now look something like this:

::: {.cmd .python .outline html=True}
    python3 infra/outlines.py --html src/lab8.py
:::

There's also a server now, but it is much simpler:

::: {.cmd .python .outline html=True}
    python3 infra/outlines.py --html src/server8.py
:::

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

*Rich buttons*: Make it possible for a button to contain arbitrary
elements as children, and render them correctly. The children should
be contained inside button instead of spilling out---this can make a
button really tall. Think about edge cases, like a button that
contains another button, an input area, or a link, and test real
browsers to see what they do.
