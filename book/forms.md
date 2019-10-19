---
title: Sending Information to Servers
chapter: 8
prev: chrome
next: scripts
...

[Up until now](chrome.md), our web browser has merely allowed its user
to read HTML content on the internet. However, modern browsers not only
allow reading content but also writing it, including making social media
posts, filling out online forms, searching for content, and so on. The
next few labs implement these features. To start, this lab implements
*web forms*, which allow the user to fill out form information and then
send that form to the server. Web forms are used almost everywhere: you
fill one out to post on Facebook, to register to vote, or to search
Google.

Rendering widgets
=================

Usually, when your browser sends information to a web server, that is
information that you\'ve typed into some kind of input area, or a
check-box of some sort that you\'ve checked. So the first step in
communicating with other servers is going to be to draw input areas on
the screen and then allow the user to fill them out.

On the web, there are two kinds of input areas: `<input>` elements,
which are for short, one-line text inputs, and `<textarea>` elements,
which are for long, multi-line text inputs. I\'d like to implement both,
because I\'d like to support both search boxes (where queries are short,
single-line things) and comment forms (where text inputs are a lot
longer). Usually, web browsers communicate with the operating system and
ask the OS to draw the input areas themselves, because that way the
input areas will match the behavior and appearance of OS input areas.
That\'s *possible* in Tk,[^1] but in the interests of simplicity we\'ll
be drawing the input areas ourselves.

Both input areas are inline content, much like text, and they\'re laid
out next to text in lines. So to support inputs we\'ll need to add a new
kind of layout object, which I\'m going to call `InputLayout`. Since
it\'ll be laid out in a line, we\'re going to need to support the same
kind of API as `TextLayout`. Looking over how methods on `TextLayout`
are called, we\'re going to need to support `attach` and `add_space`,
and `layout` will need to take both an *x* and a *y* argument:

    class InputLayout:
        def __init__(self, node, multiline=False):
            self.children = []
            self.node = node
            self.space = 0
            self.multiline = multiline

        def layout(self, x, y):
            pass

        def attach(self, parent):
            self.parent = parent
            parent.children.append(self)
            parent.w += self.w

        def add_space(self):
            if self.space == 0:
                gap = 5
                self.space = gap
                self.parent.w += gap

You\'ll note the `add_space` function hardcodes a 5-pixel space, unlike
`TextLayout`, which uses the current font. That\'s because the
*contents* of a text input generally use a custom font, not the same
font used by surrounding text, so I might as well hard-code in the size
of spaces.

Next, we need to fill in `layout`, which is going to hard-code a
specific size for input elements.[^2] One quirk is that
`InlineLayout.text` requires `w` to be set on text layout objects even
before we call `layout`, so we\'ll set the size in the constructor and
the position in `layout`:

``` {.python}
class InputLayout:
    def __init__(self, node, multiline=False):
        # ...
        self.w = 200
        self.h = 60 if self.multiline else 20

    def layout(self, x, y):
        self.x = x
        self.y = y
```

Finally, we\'ll need to draw the input element itself, which is going to
be a large rectangle:

``` {.python}
def display_list(self):
    border = DrawRect(self.x, self.y, self.x + self.w, self.y + self.h)
    return [border]
```

Finally, we need to create these `InputLayout` objects; we can do that
in `InlineLayout.recurse`:

``` {.python}
def recurse(self, node):
    if isinstance(node, ElementNode) and node.tag in ["input", "textarea"]:
        self.input(node)
    elif isinstance(node, ElementNode):
        for child in node.children:
            self.recurse(child)
    else:
        self.text(node)
```

The new `input` function is similar to `text`, except that input areas
are like a single word and don\'t have to worry about spaces:

``` {.python}
def input(self, node):
    tl = InputLayout(node, node.tag == "textarea")
    line = self.children[-1]
    if line.w + tl.w > self.w:
        line = LineLayout(self)
    tl.attach(line)
```

Finally, to make sure these elements are parsed and styled right, we
need to inform our HTML parser that `<input>` is self-closing (but not
`<textarea>`, see below) and, since both `<input>` and `<textarea>` are
supposed to be drawn inline, we need to set `display: inline` in the
browser stylesheet as well.

Interacting with widgets
========================

We\'ve now got input elements rendering, but only as empty rectangles.
There\'s more to input elements, most importantly the *input* part! We
have to change our browser so that it can: 1) draw the contents of input
elements, when they have contents; and 2) allow the user to change that
content. Let\'s start with the second, since until we do that there\'s
no content to draw.

First, we have to detect when the user has clicked on an input element
to change its value. That means a change to `Browser.handle_click`, so
that it searches for an ancestor link *or* input element to click on:

``` {.python}
# ...
while elt and not \
    (isinstance(elt, ElementNode) and \
     (elt.tag == "a" and "href" in elt.attributes or \
      elt.tag in ["input", "textarea"])):
    elt = elt.parent
if not elt:
    pass
elif elt.tag == "a":
    # ...
else:
    self.edit_input(elt)
```

Clicking on a link calls `self.edit_input`, so we need to implement
that. So, how does editing an input element work? Well, the two input
elements work differently. For `<input>`, the text in the input area is
the element\'s `value` attribute, like this:

``` {.example}
Name: <input value="Pavel Panchekha">
```

Meanwhile, `<textarea>` tags enclose text that is their content:

``` {.example}
<textarea>Hello! This is the content.</textarea>
```

In real browsers, the text inside the text area can also have manual
line breaks, so it works a little differently from normal text (and it
can wrap, so it also works differently from `<pre>` elements) but I\'m
going to ignore that in my toy browser.

The point is that editing the input has to change either the `value`
attribute or the text area content. So let\'s change our browser to do
that, soliciting input on the command line and then updating the
elements to reflect the new <content:%5Bfn>::Why solicit text input on
the command line? Because GUI text input is hard; see the last exercise,
marked \"hard\", which adds just a simple version GUI text input.\]

``` {.python}
new_text = input("Enter new text: ")
if elt.tag == "input":
    elt.attributes["value"] = new_text
else:
    elt.children = [TextNode(elt, new_text)]
```

Now that we have input areas with text in them, we need some way to draw
that to the screen. For single-line input elements, that is easy: we
just need to update `display_list` to add a single `DrawText` command:

``` {.python}
def display_list(self):
    border = # ...
    font = tkinter.font.Font(family="Times", size=16)
    text = DrawText(self.x + 1, self.y + 1, self.node.attributes.get("value", ""), font, 'black')
    return [border, text]
```

However, for multi-line input this won\'t work as cleanly, because we
need to do line breaking on the text. Instead of implementing line
breaking *again*, let\'s reuse `InlineLayout` by constructing one as a
child of our `InputLayout`:

``` {.python}
def layout(self, x, y):
    # ...
    for child in self.node.children:
        layout = InlineLayout(self, child)
        layout.layout(y)
```

Since `InlineLayout` requires them, let\'s add some of these helper
functions:

``` {.python}
def content_left(self):
    return self.x + 1

def content_top(self):
    return self.y + 1

def content_width(self):
    return self.w - 2
```

We also need to propagate this child\'s display list to its parent:

``` {.python}
def display_list(self):
    border = # ...
    if self.children:
        dl = []
        for child in self.children:
            dl.extend(child.display_list())
        dl.append(border)
        return dl
    else:
        font = # ...
        text = # ...
        return [border, text]
```

We can now display the contents of text areas!

One final thing: when we enter new text in a text area, we change the
node tree, and that means that the layout that we derived from that tree
is now invalid and needs to be recomputed, and we can\'t just call
`browse`, since that will reload the web page and wipe out our changes.
Instead, let\'s split the second half of `browse` into its own function,
which `browse` just calls:

``` {.python}
def relayout(self):
    style(self.nodes, self.rules)
    self.page = Page()
    self.layout = BlockLayout(self.page, self.nodes)
    self.layout.layout(0)
    self.max_h = self.layout.h
    self.display_list = self.layout.display_list()
    self.render()
```

Now `edit_input` can call `self.relayout()` at the end of the function.

You should now be able to run the browser on the following example web
page:

``` {.example}
<body>
<p>Name: <input value=1></p>
<p>Comment: <textarea>2</textarea></p>
```

Don\'t worry---the mangled HTML should be just fine for our [HTML
parser](html.md).

One quirk---if you change the `<body>` tag to `<b>`, so that the labels
are bold, you\'ll find that the contents of the input area aren\'t
bolded (because we override the font) but the contents of the text area
are. We can fix that by adding to the browser stylesheet:

``` {.css}
textarea { font-style: normal; font-weight: normal; }
```

That\'ll prevent the text area from inheriting its font styles from its
parent.

How forms work
==============

Now the forms are full of data, and our browser needs to submit them to
the server. The way this works in HTML is pretty tricky.

First, in HTML, there is a `<form>` element. All the input areas inside
that element are intended to be used together as part of the same form.
Furthermore, the `<form>` element has `action` and `method` attributes.
These tell the browser how to submit the form. The `method` attribute is
either `get` or `post`, and refers to an HTTP method, while `action` is
a relative URL. Combining the two allows the browser to generate an HTTP
request.

How data is included in that request depends on the method, but let\'s
focus on POST here. Suppose you have the following form, on the web page
`http://my-domain.com/form`:

``` {.html}
<form action=submit method=post>
    <p>Name: <input name=name value=1></p>
    <p>Comment: <textarea name=comment>2</textarea></p>
    <p><button>Submit!</button></p>
</form>
```

This is the same as the little example web page above, except there\'s
now a `<form>` element and also the two text areas now have `name`
attributes, plus I\'ve added a new `<button>` element. That element,
naturally, draws a button, and clicking on that button causes the form
to be submitted.

When this form is submitted, the browser will first determine that it is
making a POST request to `http://my-domain.com/submit` (using the normal
rules of relative URLs). Then, it will gather up all of the input areas
inside that form and create a big dictionary where the keys are the
`name` attributes and the values are the text content:

``` {.example}
{ "name": "1", "comment": "2" }
```

Finally, this content has the be *form-encoded*, which in this case will
look like this:

``` {.example}
name=1&comment=2
```

Finally, this form-encoded string will be the *body* of the HTTP POST
request the browser is going to send. Bodies are allowed on HTTP
requests just like they are in responses, even though up until now
we\'ve been sending HTTP GET requests without bodies. The only caveat is
that if you send a body, you must send the `Content-Length` header, so
that the server knows how much of the request to wait for.

The server will then respond to the POST request with a normal web page,
which the browser will render.

Let\'s implement these steps in our toy browser.

Implementing forms
==================

We\'re going to need to implement a couple of different things:

-   Buttons
-   Handling button clicks
-   Finding the form containing a button
-   Finding all the input areas in a form
-   Form-encoding their data
-   Making POST requests

We\'ll go in order.

First, buttons. Buttons are a lot like input elements, and can use
`InputLayout`. They get their contents like `<textarea>` but are only
one line tall; luckily, the way I\'ve implemented `InputLayout` allows
those two aspects to be mixed, so we just need to modify
`InlineLayout.recurse` to handle buttons.

Second, button clicks. We need to extend `handle_click` with button
support. That requires modifying the condition in the big `while` loop
and then adding a new case to the big `if` statement:

``` {.python}
# ...
elif elt.tag == "button":
    self.submit_form(elt)
# ...
```

Third, we need to find the form containing our button. That can happen
inside `submit_form`:[^3]

``` {.python}
def submit_form(self, elt):
    while elt and elt.tag != 'form':
        elt = elt.parent
    if not elt: return
```

Fourth, we need to find all of the input elements inside this form:

``` {.python}
def find_inputs(elt, out):
    if not isinstance(elt, ElementNode): return
    if (elt.tag == 'input' or elt.tag == 'textarea') and 'name' in elt.attributes:
        out.append(elt)
    for child in elt.children:
        find_inputs(child, out)
    return out
```

We can use this in `submit_form` to make a dictionary mapping
identifiers to values:

``` {.python}
def submit_form(self, elt):
    # ...
    inputs = find_inputs(elt, [])
    params = {}
    for input in inputs:
        if input.tag == 'input':
            params[input.attributes['id']] = input.attributes.get('value', '')
        else:
            params[input.attributes['id']] = input.children[0].text if input.children else ""
    self.post(relative_url(elt.attributes['action'], self.history[-1]), params)
```

Fifth, we can form-encode the resulting parameters:

``` {.python}
def post(self, url, params):
    body = ""
    for param, value in params.items():
        body += "&" + param + "="
        body += value.replace(" ", "%20")
    body = body[1:]
    host, port, path = parse_url(url)
    headers, body = request('POST', host, port, path, body)
```

Here the form-encoding is pretty minimal, with us just replacing spaces
by `"%20"`. In reality there are more things you\'ve got to do, but
given that our browser is a toy anyway, let\'s just try to avoid typing
equal signs, ampersands, and a few other punctuation characters into our
forms.

Sixth and finally, to actually send a POST request, we need to modify
the `request` function to allow multiple methods:

``` {.python}
def request(method, host, port, path, body=None):
    # create socket s
    s.send("{} {} HTTP/1.0\r\nHost: {}\r\n".format(method, path, host).encode("utf8"))
    if body:
        body = body.encode("utf8")
        s.send("Content-Length: {}\r\n\r\n".format(len(body)).encode("utf8"))
        s.send(body)
    else:
        s.send("\r\n".encode('utf8'))
    response = s.makefile("rb").read().decode("utf8")
    s.close()
    # ...
```

Remember to modify all other calls to `request` (there are several calls
in `Browser.browse`) to pass in the method.

Once we\'ve made the POST request, the server will send back a new web
page to render. We need to lex, parse, style, and lay that page out.
Once again, let\'s split `browse` into a simpler `browse` function that
just makes the GET request and a more complex `parse` function that does
lexing, parsing, and style, and call that from the end of `post`:

``` {.python}
def post(self, url, params):
    # ...
    self.history.append(url)
    self.parse(body)
```

With these changes we should now have a browser capable of submitting
simple forms!

Receiving POST requests
=======================

With all these changes, we need to test our browser to make sure it does
the right thing. But in lieu of using a real web page with forms, let\'s
make our own simple web server! This server will show a simple form with
a single text entry and remember anything submitted through that form.
Then, it\'ll show you all of the things that it remembers. Call it a
guest book. Online guest books... so 90s...

A web server is a different program from a web browser, so let\'s start
a new file. The server will need to:

-   Open a socket and listen for connections
-   Parse HTTP requests it receives
-   Respond to those requests with an HTML web page

I should note that the server I am building will be exceedingly simple,
because this is, after all, a web browser, not web server, blog post
series.

Let\'s start by opening a socket. Like for the browser, we need to
create an internet streaming socket using TCP:

``` {.python}
import socket
s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
```

Now, instead of calling `connect` on this socket (which causes it to
connect to some other server), we\'ll call `bind`, which opens a port
waits for other computers to connect to it:

``` {.python}
s.bind(('', 8000))
```

Here, the first argument to `bind`, the address, is set to the empty
string, which means that the socket will accept connections from any
other computer. The second argument is the port on *your* machine that
you want the server to listen on. I\'ve chosen `8000` here, since
that\'s probably open and, being larger than 1024, doesn\'t require
administrator privileges. But you can pick a different number if, for
whatever reason, port 8000 is taken on your machine.

::: {.quirk}
A note about debugging servers. If a server crashes with a connection
open on some port, the computer at the other end won\'t be informed.
Your OS therefore prevents the port from being reused for a few seconds,
because the other computer might send more data, and that data would go
to the wrong process if the port were reused. So if you crash your
server after binding to a port, you might need to wait a little bit to
restart it---about a minute, though it depends on your OS---or you\'ll
get errors about addresses being in use.
:::

Now, we tell the socket we\'re ready to accept connections:

``` {.python}
s.listen()
```

To actually accept those connections, we enter a loop which will iterate
once per connection. At the top of the loop we call `s.accept` to wait
for a new connection:

``` {.python}
while True:
    conx, addr = s.accept()
    handle_connection(conx)
```

That connection object is, confusingly, its own socket, but it is the
socket corresponding to the single connection. We know what to do with
those: we read the contents and parse the HTTP message. But it\'s a
little trickier to do this in the server than in the browser, because
the server acts first, and that means it can\'t just read from the
socket until the browser closes its connection. Instead, we\'ll read
from the socket line-by-line. First, we read the request line:

``` {.python}
def handle_connection(conx):
    req = conx.makefile("rb")
    method, url, version = req.readline().decode('utf8').split(" ", 2)
    assert method in ["GET", "POST"]
```

Then we read the headers until we get to a blank line, accumulating the
headers in a dictionary:

``` {.python}
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
tells us how much of it to read (that\'s why that header is mandatory on
`POST` requests):

``` {.python}
def handle_connection(conx):
    # ...
    if 'content-length' in headers:
        length = int(headers['content-length'])
        body = req.read(length).decode('utf8')
    else:
        body = None

    response = handle_request(method, url, headers, body).encode('utf8')
```

Let\'s skip `handle_request` for now to focus on responding to the
browser that has connected to our server. We need to send it back some
data:

``` {.python}
response = response.encode("utf8")
conx.send('HTTP/1.0 200 OK\r\n'.encode('utf8'))
conx.send('Content-Length: {}\r\n\r\n'.format(len(response)).encode('utf8'))
conx.send(response)
conx.close()
```

This is a pretty bare-bones server, with a lot of corners cut: it
doesn\'t check that the browser is using HTTP 1.0 to talk to it, it
doesn\'t send back any headers at all except `Content-Length`, and so
on. But look: it\'s a toy web server to talk to a toy web browser. Cut
it some slack.

All that\'s left is implementing `handle_request`. We want some kind of
guest book, so let\'s create a list to store guest book entries:

``` {.python}
ENTRIES = [ 'Pavel was here' ]
```

Now `handle_request` can output a little HTML page with those entries:

``` {.python}
def handle_request(method, url, headers, body):
    out = "<!doctype html><body>"
    for entry in ENTRIES:
        out += "<p>" + entry + "</p>"
    out += "</body>"
    return out
```

Note that I\'m ignoring the method, the URL, the headers, and the body
entirely. Toy web server, folks.

With this minimal core complete, you should be able to run this toy web
server on the command line and then direct your browser to
`http://localhost:8000/`, `localhost` being what your computer calls
itself and `8000` being the port we chose earlier. You should see a list
of (one) guest book entry.

Finally, let\'s make it possible to add to the guest book. First, let\'s
add a form to the top of the page:

``` {.python}
out = # ...
out += "<form action=add method=post><p><input name=guest></p><p><button>Sign the book!</button></p></form>"
# ...
```

Note that this form tells your browser to submit the form to
`http://localhost:8000/add`. This is performative but meaningless, since
the server doesn\'t care about the URL anyway.

With browsers now able to submit forms, we need to handle those
submissions:

``` {.python}
def handle_request(method, url, headers, body):
    if method == 'POST':
        params = {}
        for field in body.split("&"):
            name, value = field.split("=", 1)
            params[name] = value.replace("%20", " ")
        if 'guest' in params:
            ENTRIES.append(params['guest'])
    # ...
```

All we\'re doing here is undoing the form-encoding and then using the
`guest` parameter to add to the guest list. We need to process the POST
request at the top of `handle_request`, so that `ENTRIES` is updated
with the new entry when we go to print it.

Try it! You should be able to restart the server, point your browser to
it, and update the guest book a few times. You should also be able to go
visit the server from a real web browser and submit guest book entries
that way as well.

Summary
=======

We\'ve added an important new capability, form submission, to our web
browser. Though this is a humble beginning, we are turning our toy web
browser from a tool for consumption into a broad application platform.
Plus, we now have a little web server for our browser to talk to. Life
is better with friends!

Exercises
=========

-   Add support for check boxes. Check boxes are also represented by
    `<input>` elements, but specifically those `<input>` elements with
    the `type` attribute set to `checkbox`. The check box is checked if
    it has the `checked` attribute set, and unchecked otherwise.
    Submitting check boxes in a form is a little tricky, though. A check
    box named `foo` only appears in the form encoding if it is checked.
    Its key is its identifier and its value is the empty string.
-   Forms can be submitted via GET requests as well as POST requests. In
    the GET case, the form-encoded data is pasted onto the end of the
    URL, separated from the path by a question mark, like
    `/search?q=hi`. GET form submissions have no body. Implement GET
    form submissions.
-   One reason to separate GET and POST requests is that GET requests
    are supposed to be *idempotent*, or read-only in simpler terms,
    while POST requests are assumed to change the web server state. That
    means that going \"back\" to a GET request (making the request
    again) is safe, while going \"back\" to a POST request is a bad
    idea. Change the browser history to record what method was used to
    access each URL, and the POST body if one was used. When you go back
    to a POST-ed URL, ask the user if they are sure on the command line,
    and if they are sure submit a new POST request with the same body.
-   Right now our web server is a simple guest book. Extend it into a
    simple message board by adding support for topics. Each URL should
    correspond to a topic, and each topic should have its own list of
    messages. So, for example, `http://localhost:8000/cooking` should be
    a page of posts (about cooking) and comments submitted through the
    form on that page should only show up when you go to `/cooking`, not
    when you go to `/cars`.
-   **Hard**: Inputting text on the command line is supremely ugly.
    Replace it with proper GUI text entry. To do so, you\'ll need to
    bind the `<Key>` event in Tkinter to an event handler which uses the
    event\'s `char` field to extract the character you just typed.
    Usually those characters shouldn\'t do anything, but when you click
    in an input area you should update a new `Browser.focus` field to
    point to that element. When that field is set, typing a character
    should append it to that input area\'s text. Clicking outside an
    input area should unset `focus`. Feel free to implement more
    features (like changing the input area\'s border color when it is
    focused, or adding support for `<Backspace>`). Just don\'t get
    carried away...[^4]

[^1]: In Python, you use the `ttk` library.

[^2]: In real browsers, the web page can use the `width` and `height`
    CSS properties to change the size of input elements.

[^3]: Fun fact: HTML standardizes the `form` attribute for input
    elements, which in principle allows an input element to be outside
    the form it is supposed to be submitted with. But no browser
    implements that feature.

[^4]: Backspace is not crazy, but adding support for the arrow keys is
    going to be hard. Adding support for selection is just crazy!
