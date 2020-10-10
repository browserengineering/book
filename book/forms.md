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

::: {.todo}
I may decide to implement focus tracking and GUI text entry.
:::

Rendering widgets
=================

When your browser sends information to a web server, that is usually
information that you\'ve typed into some kind of input area, or a
check-box of some sort that you\'ve checked. So the first step in
communicating with other servers is going to be to draw input areas on
the screen and then allow the user to fill them out.

On the web, there are two kinds of input areas: `<input>` elements,
which are for short, one-line inputs, and `<textarea>` elements, which
are for long, multi-line text. I\'d like to implement both, because
I\'d like to support both search boxes (where queries are short,
single-line things) and comment forms (where text inputs are a lot
longer).

Both `<input>` and `<textarea>` elements are inline content, like
text, laid out in lines. So to support inputs we\'ll need a new kind
of layout object, which I\'ll call `InputLayout`. It\'ll need to
support the same kind of API as `TextLayout`, namely `attach` and
`add_space`, so that it won't confuse `InlineLayout`:

``` {.python}
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
```

You\'ll note the `add_space` function hardcodes a 5-pixel space, unlike
`TextLayout`, which uses the current font. That\'s because the
*contents* of a text input generally use a custom font, not the same
font used by surrounding text, so I might as well hard-code in the size
of spaces.

::: {.todo}
This explanation is very odd: the size of the space should be the size
of the surrounding text. Perhaps `add_space` should execute a `max`
operation?
:::

For simplicity, the `layout` method hard-codes a specific size for
input elements.[^2] One quirk is that `InlineLayout.text` requires `w`
to be set on text layout objects even before we call `layout`, so
we\'ll set the size in the constructor and the position in `layout`:

[^2]: In real browsers, the `width` and `height` CSS properties can
    change the size of input elements. The reason we need to hard-code
    is that an input element is not sized to the text inside of it; in turn
    this is because text may not exist yet!


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
    _ol, _or = self.x, self.x + self.w
    _ot, _ob = self.y, self.y + self.h
    return [DrawRect(_ol, _ot, _or, _ob)]
```

Finally, we need to create these `InputLayout` objects; we can do that
in `InlineLayout.recurse`:

``` {.python}
def recurse(self, node):
    if isinstance(node, ElementNode):
        if node.tag in ["input", "textarea"]:
            self.input(node)
        else:
            for child in node.children:
                self.recurse(child)
    else:
        self.text(node)
```

The new `input` function is similar to `text`, except that input areas
don't need to be split into multiple words:

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
`<textarea>`, see below) and, since both `<input>` and `<textarea>`
are supposed to be drawn inline, we need to set `display: inline` for
them in the browser stylesheet as well.

Interacting with widgets
========================

We\'ve now got input elements rendering, but only as empty rectangles.
We need the *input* part! Let's 1) draw the content of input elements;
and 2) allow the user to change that content. I'll start with the
second, since until we do that there\'s no content to draw.

In this toy browser, I'm going to require the user to click on an
input element to change its content. We detect the click in
`Browser.handle_click`, which must now search for an ancestor link
*or* input element:

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

So, how does editing an input element work? Well, `<input>` and
`<textarea>` work differently. For `<input>`, the text in the input
area is the element\'s `value` attribute, like this:

``` {.example}
Name: <input value="Pavel Panchekha">
```

Meanwhile, `<textarea>` tags enclose text that is their
content:^[The text area can also contain manual line
breaks, unlike normal text (but it does wrap lines, unlike `<pre>`),
which I'm ignoring here.]

``` {.example}
<textarea>This is the content.</textarea>
```

Whereever the content is, editing the input has to change it. Let\'s
add that to our browser, soliciting input on the command line and then
updating the element with it:^[GUI text input is hard, which is why
I'm soliciting input on the command line. See the last exercise.]

``` {.python}
def edit_input(self, elt):
    new_text = input("Enter new text: ")
    if elt.tag == "input":
        elt.attributes["value"] = new_text
    else:
        elt.children = [TextNode(elt, new_text)]
```

Now that input areas have text content, we need to draw that text. For
single-line input elements, we just add a `DrawText` command to the
display list:

``` {.python}
def display_list(self):
    border = # ...
    font = self.node.font()
    value = self.node.attributes.get("value", "")
    x, y = self.x + 1, self.y + 1
    text = DrawText(x, y, value, font, 'black')
    return [border, text]
```

This won't work for multi-line inputs, though, because we need to do
line breaking on that text. Instead of implementing line breaking
*again*, let's reuse `InlineLayout` by constructing one as a child of
our `InputLayout`:

``` {.python}
def layout(self, x, y):
    # ...
    for child in self.node.children:
        layout = InlineLayout(self, child)
        self.children.append(layout)
        layout.layout(y)
```

Since `InlineLayout` requires them, let\'s add some of these helper
functions:

::: {.todo}
It's ugly that I have these
:::

``` {.python}
def content_left(self):
    return self.x + 1

def content_top(self):
    return self.y + 1

def content_width(self):
    return self.w - 2
```

::: {.todo}
I'd rather the recursion be external.
:::

We also need to propagate this child's display list to its parent:

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
        text = # ...
        return [border, text]
```

The browser now displays text area contents!

One final thing: when we enter new text in a text area, we change the
node tree, and that means that the layout that we derived from that tree
is now invalid and needs to be recomputed, and we can\'t just call
`browse`, since that will reload the web page and wipe out our changes.
Instead, let\'s split the second half of `browse` into its own function,
which `browse` will now call:

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

Now `edit_input` can call `self.relayout()` to update the layout
and redraw the page.

You should now be able to run the browser on the following example web
page:^[Don\'t worry---the mangled HTML should be just fine for our [HTML parser](html.md).]

``` {.example}
<body>
<p>Name: <input value=1></p>
<p>Comment: <textarea>2</textarea></p>
</body>
```

One quirk---if you add `style=font-weight:bold` to the `<body>`, so
that the labels are bold, you\'ll find that the input area content
isn't bolded (because we override the font) but the text area content
is. We can fix that by adding to the browser stylesheet:

``` {.css}
textarea {
    font-style: normal;
    font-weight: normal;
}
```

That'll prevent the text area from inheriting its font styles from its
parent.

How forms work
==============

Filled-out forms go to the server. The way this works in HTML is
pretty tricky.

First, in HTML, there is a `<form>` element, which describes how to
submit all the input elements it contains through its `action` and
`method` attributes. The `method` attribute is either `get` or `post`,
and refers to an HTTP method; the `action` attribute is a relative
URL. The browser generates an HTTP request by combining the two.

Let\'s focus on POST submissions (the default). Suppose you have the
following form, on the web page `http://my-domain.com/form`:

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
making a POST request to `http://my-domain.com/submit`. It does this by
observing that the `method` attribute says `post`, and that the `action`
attribute has a (relative) URL of `submit`, which we can turn into the
mentioned URL using the rules for resolving relative URLs into absolute
ones. Then it will gather up all of the input areas inside that form and
create a big dictionary where the keys are the `name` attributes and the
values are the text content:

``` {.example}
{ "name": "1", "comment": "2" }
```

Finally, this content has the be *form-encoded*, which in this case will
look like this:

``` {.example}
name=1&comment=2
```

This form-encoded string will be the *body* of the HTTP POST request
the browser is going to send. Bodies are allowed on HTTP requests just
like they are in responses, even though up until now we\'ve been
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

[^3]: Fun fact: HTML standardizes the `form` attribute for input
    elements, which in principle allows an input element to be outside
    the form it is supposed to be submitted with. But no browser
    implements that.

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
    if elt.tag in ['input', 'textarea'] and 'name' in elt.attributes:
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
            value = input.attributes.get('value', '')
        else:
            if input.children:
                value = input.children[0].text
            else:
                value = ""
        params[input.attributes['id']] = value
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

::: {.todo}
Having `post` and `browse` methods is crazy.
:::

This isn't real form-encoding---I'm just replacing spaces by `"%20"`.
Real form-encoding escapes characters like the equal sign, the
ampersand, and so on; but given that our browser is a toy anyway,
let\'s just try to avoid typing equal signs, ampersands, and so on
into forms.

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

::: {.todo}
This needs to match the actual `request` code (and fit on screen).
:::

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

::: {.todo}
I don't like `parse` for this.
:::

With these changes we should now have a browser capable of submitting
simple forms!

Receiving POST requests
=======================

We need to test our browser's forms functionality. Let\'s test with
our own simple web server. This server will show a simple form with a
single text entry and remember anything submitted through that form.
Then, it\'ll show you all of the things that it remembers. Call it a
guest book.^[Online guest books... so 90s...]

A web server is a different program from a web browser, so let\'s start
a new file. The server will need to:

-   Open a socket and listen for connections
-   Parse HTTP requests it receives
-   Respond to those requests with an HTML web page

I should note that the server I am building will be exceedingly simple,
because this is, after all, a book on web *browser* engineering.

Let's start by opening a socket. Like for the browser, we need to
create an internet streaming socket using TCP:

``` {.python}
import socket
s = socket.socket(
    family=socket.AF_INET,
    type=socket.SOCK_STREAM,
    proto=socket.IPPROTO_TCP,
)
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
open on some port, your OS prevents the port from being
reused[^why-wait] for a few seconds. So if your server crashes, you
might need to wait about a minute before you restart it, or you\'ll
get errors about addresses being in use.
:::

[^why-wait]: When your process crashes, the computer on the end of the
    connection won't be informed immediately; if some other process
    opens the same port, it could receive data means for the old,
    now-dead process.

Now, we tell the socket we\'re ready to accept connections:

``` {.python}
s.listen()
```

To actually accept those connections, we enter a loop that runs once
per connection. At the top of the loop we call `s.accept` to wait for
a new connection:

``` {.python}
while True:
    conx, addr = s.accept()
    handle_connection(conx)
```

That connection object is, confusingly, also socket: it is the socket
corresponding to that one connection. We know what to do with those:
we read the contents and parse the HTTP message. But it\'s a little
trickier to do this in the server than in the browser, because the
browser waits for the server, and that means the server can\'t just
read from the socket until the connection closes.

Instead, we\'ll read from the socket line-by-line. First, we read the
request line:

``` {.python}
def handle_connection(conx):
    req = conx.makefile("rb")
    reqline = req.readline().decode('utf8')
    method, url, version = reqline.split(" ", 2)
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

    response = handle_request(method, url, headers, body)
```

Let's fill in `handle_request` later; it returns a string containing
the resulting HTML web page. We need to send it back to the browser:

``` {.python}
response = response.encode("utf8")
conx.send('HTTP/1.0 200 OK\r\n'.encode('utf8'))
conx.send('Content-Length: {}\r\n\r\n'.format(len(response)).encode('utf8'))
conx.send(response)
conx.close()
```

::: {.todo}
I need to do something about the Content-Length line being so long.
:::

This is a bare-bones server: it doesn\'t check that the browser is
using HTTP 1.0 to talk to it, it doesn\'t send back any headers at all
except `Content-Length`, and so on. But look: it\'s a toy web server
that talks to a toy web browser. Cut it some slack.

All that\'s left is implementing `handle_request`. We want some kind of
guest book, so let\'s create a list to store guest book entries:

``` {.python}
ENTRIES = [ 'Pavel was here' ]
```

The `handle_request` function outputs a little HTML page with those entries:

``` {.python}
def handle_request(method, url, headers, body):
    out = "<!doctype html><body>"
    for entry in ENTRIES:
        out += "<p>" + entry + "</p>"
    out += "</body>"
    return out
```

For now, I\'m ignoring the method, the URL, the headers, and the body
entirely.

You should be able to run this minimal core of a web server and then
direct your browser to `http://localhost:8000/`, `localhost` being
what your computer calls itself and `8000` being the port we chose
earlier. You should see a list of (one) guest book entry.

Let\'s now make it possible to add to the guest book. First, let\'s
add a form to the top of the page:

``` {.python}
out += "<form action=add method=post>"
out +=   "<p><input name=guest></p>"
out +=   "<p><button>Sign the book!</button></p>"
out += "</form>"
```

This form tells the browser to submit data to
`http://localhost:8000/add`; the server needs to react to such
submissions. First, we will need to undo the form-encoding:

``` {.python}
def form_decode(body):
    params = {}
    for field in body.split("&"):
        name, value = field.split("=", 1)
        params[name] = value.replace("%20", " ")
    return params
```

To handle submissions, we'll want to get the guest book comment, add
it to `ENTRIES`, and then draw the page with the new comment shown.
Furthermore, `handle_request` will first need to figure out what kind
of request this is (browsing or form submission) and then executed the
relevant code. To keep this organized, let's rename `handle_request`
to `show_comments`:

``` {.python}
def show_comments():
    # ...
    return out
```

We can have a `add_entry` function to handle form submissions:

``` {.python}
def add_entry(params):
    if 'guest' in params:
        ENTRIES.append(params['guest'])
    return show_comments()
```

This frees up the `handle_request` function to just figure out which
of these two functions to call:

``` {.python}
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

-   Add check boxes. In HTML, check boxes are `<input>` elements with the
    `type` attribute set to `checkbox`. The check box is checked if it
    has the `checked` attribute set, and unchecked otherwise.
    Submitting check boxes in a form is a little tricky, though. A
    check box named `foo` only appears in the form encoding if it is
    checked. Its key is its `name` attribute and its value is the empty
    string.

-   Forms can be submitted via GET requests as well as POST requests.
    In GET requests, the form-encoded data is pasted onto the end of
    the URL, separated from the path by a question mark, like
    `/search?q=hi`; GET form submissions have no body. Implement GET
    form submissions.

-   One reason to separate GET and POST requests is that GET requests
    are supposed to be *idempotent* (read-only, basically) while POST
    requests are assumed to change the web server state. That means
    that going "back" to a GET request (making the request again) is
    safe, while going "back" to a POST request is a bad idea. Change
    the browser history to record what method was used to access each
    URL, and the POST body if one was used. When you go back to a
    POST-ed URL, ask the user if they want to resubmit the form. Don't
    go back if they say no; if they say yes, submit a POST request
    with the same body as before.

-   Right now our web server is a simple guest book. Extend it into a
    simple message board by adding support for topics. Each URL should
    correspond to a topic, and each topic should have its own list of
    messages. So, for example, `/cooking` should be a page of posts
    (about cooking) and comments submitted through the form on that
    page should only show up when you go to `/cooking`, not when you
    go to `/cars`.

-   Implement proper GUI text entry. When the user clicks on an input
    area, store the input element to a new `Browser.focus` field.
    Clicks elsewhere should clear that field. Next, bind the `<Key>`
    event in Tkinter and use the event's `char` field in the event
    handler to determine the character the user typed. Add that
    character the value of the element in `Browser.focus`. If there's
    no focused element, don't do anything.[^4]

[^4]: You can implement more features if you'd like, but it quickly
    gets difficult. Backspace: doable; arrow keys: hard; selection:
    crazy!

