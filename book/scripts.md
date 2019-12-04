---
title: Running Interactive Scripts
chapter: 9
prev: forms
next: reflow
...

Forms allow our web browser to run dynamic web applications like that
guest book. But form-based web applications require page loads every
time you do anything, and fell out of favor in the early 2000s. What
took their place are JavaScript-based applications, which run user
code on web pages that can modify the pages dynamically, without
reloads. Let's add support for that to our toy web browser.

Installing DukPy
================

Actually writing a JavaScript interpreter is beyond the scope of this
book,^[fn::But check out a book on programming language implementation
if it sounds interesting!] so this chapter uses the `dukpy` library
for executing JavaScript.

[DukPy](https://github.com/amol-/dukpy) is a Python library that wraps a
JavaScript interpreter called [Duktape](https://duktape.org). There are,
for course, lots of JavaScript interpreters, such as the browser
implementations of TraceMonkey (Firefox), JavaScriptCore (Safari), and
V8 (Chrome). Unlike those implementations, which are extremely complex
because they aim for maximal speed, Duktape aims at simplicity and
extensibility, especially for people who need a simple scripting
language as part of a larger C or C++ project.[^1]

[^1]: For examples, games are usually written in C or C++ to take
    advantage of high-speed graphics, but use a simpler language to
    implement the actual plot of the game.

::: {.quirk}
If you\'re using C or C++, you may want to try binding to the `duktape`
C library, which `dukpy` uses internally. If you\'re using some other
language, you may need to switch to Python for this lab. The next lab,
on reflows, can be done without having done this one, though it won\'t
be particularly well motivated.
:::

Like any JavaScript engine, DukPy not only executes JavaScript code,
but also allows JavaScript code to call Python functions that you've
*registered*. We\'ll be heavily using this feature to allow JavaScript
code to modify the web page it's running on.

The first step to using DukPy is installing it. On most machines,
including on Windows, macOS, and Linux systems, you should be able to do
this with the command:

``` {.example}
pip install dukpy
```

There may be quirks depending on your computer, however. You might
need to install `pip`. Instead of `pip`, you might have to use `pip3`.
Or, perhaps, you may have `easy_install` instead of `pip`. Some Linux
distributions may package `dukpy` directly. If you do your Python
programming through an IDE, you may need to use your IDE\'s package
installer. In the worst case, you might have to build [from
source](https://github.com/amol-/dukpy).

To test whether you installed DukPy correctly, execute:

``` {.python}
import dukpy
dukpy.evaljs("2 + 2")
```

If you get an error on the first line, you probably failed to install
DukPy.[^2] If you get an error, or a segfault, on the second line,
there's a chance that Duktape failed to compile, and maybe doesn\'t
support your system. In that case you might need to skip this
chapter.

[^2]: Or, on my Linux machine, I sometimes get errors due to file
    ownership.


Running JavaScript code
=======================

The test code above shows you how to run JavaScript code with DukPy:
you just call `evaljs`! With this newfound knowledge, let\'s modify
our web browser to run JavaScript code.

On the web, JavaScript is found in `<script>` tags, in two different
ways. First, a `<script>` tag may have a `src` attribute with a
relative URL that points to a JavaScript file, much like with CSS
files. Second, a `<script>` tag may also have ordinary text contents,
which are run directly. In my toy browser, I'll only implement the
first; the second makes parsing a challenge.^[Unless you promise to
avoid less than and greater than comparisons in your code.]

The implementation here will look much like for CSS. First, let\'s
implement a `find_scripts` function:

``` {.python}
def find_scripts(node, out):
    if not isinstance(node, ElementNode): return
    if node.tag == "script" and \
       "src" in node.attributes:
        out.append(node.attributes["src"])
    for child in node.children:
        find_scripts(child, out)
    return out
```

Then, when we load a web page, we will find all of the scripts and run
them:

``` {.python}
def parse(self, body):
    # ...
    for script in find_scripts(self.nodes, []):
        header, body = request('GET', relative_url(script, self.history[-1]))
        print("Script returned: ", dukpy.evaljs(body))
    self.relayout()
```

Try this out on a simple web page, like this one:

``` {.python}
<script src=test.js></script>
```

where `test.js` is the following very simple script:

``` {.python}
var x = 2
x + x
```

Registering functions
=====================

It\'s cool to run JavaScript, but it's silly for the browser to print
the result. What if you don't want to print? Or want to print more
than once? The script should call the standard `console.log` function
when it wants to print instead of having the problem print at the end.

To allow that, we will need to *register a function* with DukPy, which
would allow Javascript code to run Python functions. Those functions
are registered on a `JSInterpreter` object, which we'll need to create:

``` {.python}
self.js = dukpy.JSInterpreter()
```

For `console.log`, we'll first need a Python function that print its
argument---`print`.^[5] We can register it using `export_function`:

[^5]: If you\'re using Python 2, for some reason, you\'ll need to write
    a little wrapper function around `print` instead.

``` {.python}
self.js.export_function("log", print)
```

You can now run the Javascript code:

``` {.javascript}
call_python("log", "Hi from JS")
```

That will take `x`, convert it from a Javascript to a Python
object,^[This conversion will do the expected things to numbers,
string, and booleans, but I wouldn't try it with more general
objects.] and run the `print` function with that argument.

That's pretty good, but what we actually want is a `console.log`
function, not a `call_python` function. So we need define a `console`
object and then give it a `log` field. We do that *in JavaScript*, by
executing code like this:

``` {.javascript}
console = { log: function(x) { call_python("log", x); } }
```

In case you're not too familiar with JavaScript,^[Now's a good time to
brush up on it! This chapter has a lot of JavaScript in it.] this defines a
variable called `console`, whose value is an object literal with the
field `log`, whose value is the function you see defined there.

Taking a step back, when we run JavaScript in our browser, we're
mixing: C code, which implements the JavaScript interpreter; Python
code, which handles certain JavaScript functions; and JavaScript code,
which wraps the Python API to look more like the JavaScript one. We
can call that JavaScript code our \"JavaScript runtime\"; we run it
before we run any user code. So let\'s stick it in a `runtime.js`
file, and run it after all of our functions are registered but before
any user code is run:

``` {.python}
with open("runtime.js") as f:
    self.js.evaljs(f.read())
```

Now you should be able to run the script `console.log("Hi from JS!")`
and see output in your terminal.

As a side benefit of using one `JSInterpreter` for all scripts, it is
now possible to run two scripts and have one of them define a variable
that the other uses, say on a page like:

``` {.python}
<script src=a.js></script>
<script src=b.js></script>
```

where `a.js` is \"`var x = 2;`\" and `b.js` is \"`console.log(x + x)`\".

Querying the DOM
================

So far, JavaScript evaluation is fun but useless, because JavaScript
can\'t make any kinds of modifications to the page itself. Why even run
JavaScript with a limitation like that? So let\'s work on making it
possible to modify the page from JavaScript.

Generally, the set of APIs that allow JavaScript to manipulate the web
page it is running on is called the DOM API, where DOM stands for
\"Document Object Model\". The DOM API is big, and it keeps getting
bigger, so I\'m definitely not planning on implementing all, or even
most, of it. But there are a few core APIs that give you a lot of the
power of the full API, granted in a kind of ugly way:

-   `querySelectorAll`, which returns a list of all elements matching a
    selectors;
-   `getAttribute`, which gets the value of an HTML attribute for some
    element; and
-   `innerHTML`, which allows you to replace the contents of any element
    by a new block of HTML.

Now, I should note that both of these are a little more complex than
I\'m making them out to be. `querySelectorAll` actually returns not a
list but a thing called a `NodeList`, and also `innerHTML` can be used
to both read and write the HTML contents of an element. I\'m going to
ignore those and just implement the very limited versions of these
functions described above.

Let\'s implement `querySelectorAll` and `getAttribute`, which are
read-only methods, first. Normally, `querySelectorAll` is a method on an
object called `document`, so we\'ll need to pull the same trick as
above. First, let\'s write a function to register:

``` {.python}
class Browser:
    def parse(self):
        # ...
        self.js.export_function("querySelectorAll", self.js_querySelectorAll)
        # ...

    def js_querySelectorAll(self, sel):
        # ...
```

We\'ll then define a `document` object in our JavaScript runtime with a
`querySelectorAll` function:

``` {.python}
document = { querySelectorAll: function(s) { return call_python("querySelectorAll", s); } }
```

`js_querySelectorAll` will first parse the selector, then find and
return the matching elements:

``` {.python}
selector, _ = css_selector(sel + "{", 0)
return find_selected(self.nodes, selector, [])
```

Here I\'m asking my parser to parse, for example, `#id{` instead of
`#id`, because that way the selector parser won\'t go off the end of the
string and throw an error. I\'ve moved the actual selector matching to a
recursive helper function:[^6]

``` {.python}
def find_selected(node, sel, out):
    if not isinstance(node, ElementNode): return
    if sel.matches(node):
        out.append(node)
    for child in node.children:
        find_selected(child, sel, out)
    return out
```

We\'re helped out here by some of the nice features of DukPy. For
example, `css_selector` can throw errors, so the function we register
can crash. But in that case DukPy will turn our Python-side exception
into a JavaScript-side exception in the web script we are running, which
can catch it or do something else. However, if you run this code, you
will likely see an error like this:[^7]

``` {.example}
_dukpy.JSRuntimeError: EvalError:
Error while calling Python Function:
TypeError('Object of type ElementNode is not JSON serializable')
```

But what it\'s trying to tell you is that DukPy has no idea what to do
with the `ElementNode` objects you\'re returning from
`querySelectorAll`, since there is no corresponding class in JavaScript.

Instead of returning browser objects directly to JavaScript, we need to
keep browser objects firmly on the Python side of the browser, and toss
references to those browser objects over the fence to JavaScript. Let\'s
pass the JavaScript code a simple numeric identifier, and keep track of
which identifer maps to which element inside the browser. I\'ll call
these identifiers *handles*.[^8]

To implement handles, I\'ll first create a `js_handles` browser field,
which will map handles to nodes:

``` {.python}
class Browser:
    def parse(self, body):
        # ...
        self.js = dukpy.JSInterpreter()
        self.js_handles = {}
        # ...
```

I\'ll also add a `handle` field to each `ElementNode`, where 0 means no
handles have been assigned yet:

``` {.python}
class ElementNode:
    def __init__(self, parent, tagname):
        # ...
        self.handle = 0
```

Then, in `js_querySelectorAll`, I\'ll allocate new handles for each of
the matched nodes:

``` {.python}
elts = find_selected(self.nodes, selector, [])
out = []
for elt in elts:
    if not elt.handle:
        handle = len(self.js_handles) + 1
        elt.handle = handle
        self.js_handles[handle] = elt
    out.append(handle)
return out
```

The curious expression `len(self.js_handles) + 1` happens to compute the
smallest handle not in the handles list. So now calling
`document.querySelectorAll` will return an output like `[1, 2, 3, 4]`.
Great! We can now execute a simple script to count, say, the number of
paragraphs on the page.

``` {.javascript}
console.log(document.querySelectorAll("p").length)
```

::: {.quirk}
Our browser is making one major departure here from how real web
browsers work, a departure important enough to call out. In a real web
browser, JavaScript code is run as soon as the browser *parses* the
`<script>` tag, and at that point most of the page is not parsed and may
not even have been received over the network. But the way I\'ve written
the code, my toy browser only runs scripts after the page is fully
loaded. This is so that I can test the JavaScript support before
implementing events (like the `load` event) that real web pages have to
listen for before making queries to the page. Given how we\'ve
structured our browser, it would, unfortunately, be pretty hard to do
this right.
:::

But returning handles to our JavaScript code isn\'t enough if we want
scripts to get any additional information about the elements that
`querySelectorAll` returns. For example: how could we call
`getAttribute` on them?

Well, the idea is that we need to register another function to implement
`getAttribute`, which will take in handles as input and internally
conver them into elements. It would look a bit like this:

``` {.python}
class Browser:
    def js_getAttribute(self, handle, attr):
        elt = self.js_handles[handle]
        return elt.attributes.get(attr, None)
```

Note that `None` is translated by DukPy to the `null` object in
JavaScript. We can register this function as `getAttribute`, and now we
can run a script like this:[^9]

``` {.python}
scripts = document.querySelectorAll("script")
for (var i = 0; i < scripts.length; i++) {
    console.log(call_python("getAttribute", scripts[i], "src"));
}
```

That should print out the URLs of all of the scripts on the page.

Finally, this still isn\'t \"normal\" JavaScript code, because normally
`querySelectorAll` returns `Node` obejcts and you call `getAttribute`
directly on those `Node` objects, with no `call_python` things involved.
Let\'s define this wrapper `Node` class in our runtime.[^10]

``` {.javascript}
function Node(handle) { this.handle = handle; }
Node.prototype.getAttribute = function(attr) {
    return call_python("getAttribute", self.handle, attr);
}
```

Then, in our `querySelectorAll` wrapper, we\'ll create these `Node`
objects:

``` {.python}
document = {
    querySelectorAll: function(s) {
        return call_python("querySelectorAll", s).map(function(h) {
            return new Node(h)
        });
    }
}
```

Note that we\'re creating new `Node` objects every time we call
`querySelectorAll`, even if we already have a `Node` for that handle.
That\'s actually a bad thing, since it means you can\'t use equality to
compare `Node` objects. I\'ll ignore that problem.

With this new code, we can actually write some useful functions. For
example, we might write a little character counter for input boxes:

``` {.python}
inputs = document.querySelectorAll('input')
for (var i = 0; i < inputs.length; i++) {
    if (input.getAttribute("value").length > 100) {
        console.log("Input with name " + input.getAttribute("name") + " has too much text.")
    }
}
```

Alas, we can\'t quite yet run this whenever the input value changes.
Let\'s fix that.

Event handling
==============

JavaScript code executes as soon as the browser loads the web page, but
most of that code doesn\'t actually make any changes to the page.
Instead, it installs various code to run when *page events* occur, like
clicks on links and buttons or changes to input areas. Here\'s how that
works. First, any time the user interacts with the page, the browser
generates *events*. Each event has a type, like `change`, `click`, or
`submit`, and an element (an input area, a link, or a form). JavaScript
code can call `addEventListener` to react to those events:
`elt.addEventListener('click', handler)` will run the JavaScript
function `handler` every time the element `elt` generates a `click`
event.

Let\'s implement that. We\'ll start on the browser side, where we have
to generate events. Let\'s add a `Browser.event` function which we\'ll
call every time an event has to be generated:

``` {.python}
class Browser:
    def event(self, type, elt):
        pass
```

Let\'s add calls to `self.event` in three places. First, any time we
click in the page:

``` {.python}
def handle_click(self, e):
    if e.y < 60:
        # ...
    else:
        x, y = e.x, e.y - 60 + self.scrolly
        elt = find_element(x, y, self.layout)
        if elt: self.event('click', elt)
        # ...
```

Second, after updating input area values:[^11]

``` {.python}
def edit_input(self, elt):
    # ...
    self.event("change", elt)
    self.relayout()
```

Finally, when submitting forms:

``` {.python}
def submit_form(self, elt):
    # while elt and elt.tag != "form"
    if not elt: return
    self.event("submit", elt)
    # ...
```

So far so good---but what should `event` actually do? Well, it needs to
run the handlers that JavaScript has defined with `addEventListener`, so
those need to be stored somewhere. But where? I propose we keep that
data on the JavaScript side, in an variable called `LISTENERS`.
`LISTENERS` will map handles to a dictionary that maps event types to a
list of handlers:

``` {.javascript}
LISTENERS = {}

Node.prototype.addEventListener = function(type, handler) {
    if (!LISTENERS[this.handle]) LISTENERS[this.handle] = {};
    var dict = LISTENERS[this.handle]
    if (!dict[type]) dict[type] = [];
    var list = dict[type];
    list.push(handler);
}
```

Now we can use the `LISTENERS` array to actually run the handlers. Still
in JavaScript:

``` {.javascript}
function __runHandlers(handle, type) {
    var list = (LISTENERS[handle] && LISTENERS[handle][type]) || [];
    for (var i = 0; i < list.length; i++) {
        list[i]();
    }
}
```

Now all we need to do when an event is generated is to call
`__runHandlers` from Python:

``` {.python}
def event(self, type, elt):
    if elt.handle:
        self.js.evaljs("__runHandlers({}, \"{}\")".format(elt.handle, type))
```

There are two quirks with this code. First, I\'m not running handlers if
the element with the event doesn\'t have a handle. That\'s because if it
doesn\'t have a handle, it couldn\'t have been made into a `Node`, and
then `addEventListener` couldn\'t have been called on it. Second, when I
call `__runHandlers` I need to pass it arguments, which I do by
generating JavaScript code that embeds those arguments directly. This
would be a bad idea if, say, `type` could contain a quote or a newline.
Luckily I control that value and can make sure it is always valid. DukPy
actually provides a better way to do this, using the `dukpy` object, but
in the interest of simplicity I\'m skipping that.

With all of this done, you should be able to take the input area
character counter above and run it every time an input area changes:

``` {.python}
function lengthCheck() {
    if (input.getAttribute("value").length > 100) {
        console.log("Input with name " + input.getAttribute("name") + " has too much text.")
    }
}

inputs = document.querySelectorAll("input")
for (var i = 0; i < inputs.length; i++) {
    inputs[i].addEventListener("change", lengthCheck);
}
```

This is great, but ideally the output of this length check would go on
the web page itself, not to the console, where the user probably won\'t
bother looking. To do that, we\'ll need to not only read from but also
write to the DOM.

Modifying the DOM
=================

So far, we\'ve only implemented DOM methods that read the DOM. Now we
need to write to it. The full DOM API provides a lot of different
methods for modifying the page, but I\'m going to focus on implementing
just one: `innerHTML`. That method works like this:

``` {.javascript}
node.innerHTML = "This is my <b>new</b> bit of content!";
```

In other words, `innerHTML` is a *field* on node objects, with a
*setter* that is run when the field is modified. That setter takes the
new value, which must be a string, parses it as HTML, and makes the new,
parsed HTML nodes children of the original node.

Let\'s implement this, starting on the JavaScript side. JavaScript has
the obscure `Object.defineProperty` function to define setters:

``` {.javascript}
Object.defineProperty(Node.prototype, 'innerHTML' {
    set: function(s) {
        call_python("innerHTML", this.handle, s);
    }
});
```

Now we need to register the `innerHTML` function:

``` {.python}
class Browser:
    def parse(self, body):
        # ...
        self.js.export_function("innerHTML", self.js_innerHTML)

    def js_innerHTML(self, handle, s):
        elt = self.js_handles[handle]
        # ?
```

Now, in `innerHTML`, we\'ll need to parse the new HTML string:

``` {.python}
new_node = parse(lex("<__newnodes>" + s + "</__newnodes>"))
```

Here I\'m adding a special `<__newnodes>` tag at the start of the source
because our HTML parser doesn\'t work right when you don\'t have a
single root node.[^12] Of course we don\'t want that new node, just its
children:

``` {.python}
elt.children = new_node.children
for child in elt.children:
    child.parent = elt
```

Note that we not only need to copy the children into the old node but
also update their parent pointers to point to it. This is almost
right---but if you look carefully at `TextNode` you\'ll notice that it
assigns its `style` field in its constructor, by using its parent\'s
style. That means if the new HTML content is a single `TextNode`, it\'ll
point at the wrong parent\'s style. So let\'s move that code to the
`style` function:

``` {.python}
def style(node, rules):
    if not isinstance(node, ElementNode):
        node.style = node.parent.style
        return
```

Finally, since the page changed, we need to lay it out again:

``` {.python}
self.relayout()
```

With that, it\'s now possible to update a web page from JavaScript
itself. Let\'s go ahead and use this in our guest book server. Do you
want people writing long political rants in *your* guest book? I don\'t,
so I\'m going to put a 200-character limit on guest book entries.

First, let\'s modify the guest book form so that after the
`<input name=guest>` we have a new paragraph `<p id=errors></p>`.
Initially this paragraph will be empty, but we\'ll update it with text
if the comment gets too long.

Next, let\'s add a script to the page. First of all that means a new
line of HTML output:

``` {.python}
out += "<script src=/comment.js></script>"
```

However, we also need to *serve* that new JavaScript file, and that
means our little web server will now need a special case for the
`/comment.js` URL:

``` {.python}
def handle_request(method, url, headers, body):
    if url == "/comment.js":
        with open("comment.js") as f:
            return f.read()
    # ...
```

Here the server is going to read from the file `common.js`, into which
we can put our little input length checker above, with the `lengthCheck`
function modified like so to use `innerHTML`:

``` {.javascript}
function lengthCheck() {
    if (input.getAttribute("value").length > 100) {
        document.querySelectorAll("#errors")[0].innerHTML = "Comment too long!"
    }
}

input = document.querySelectorAll("input")[0];
input.addEventListener("change", lengthCheck);
```

Try it out. Write a really long comment and you should see the page
warning you that the comment is too long. By the way, we might want to
make it stand out more, so let\'s go ahead and add another URL to our
web server, `/common.css`, with the contents:

``` {.css}
#errors { font-weight: bold; color: red; }
```

This is a good step toward limiting the length of guest book entries,
but there\'s still nothing stopping the user from writing a long
comment, ignoring the error message, and submitting the guest book entry
anway. So far...

Event defaults
==============

So far when an event is generated, my browser will run all of the
associated handlers, and then do whatever default action was associated
with that event. However, in real browsers, JavaScript code can also
*cancel* the default action.

There are a few moving pieces involved with that. First of all, event
handlers in JavaScript receive an *event object* as an argument. That
object has a `preventDefault` method, and if JavaScript calls it, the
default action won\'t occur. Let\'s implement that.

First of all, we\'ll need event objects. Back to our JS runtime:

``` {.javascript}
function Event() { this.cancelled = false; }
Event.prototype.preventDefault = function() {
    this.cancelled = true;
}
```

Next, we need to pass the event object to handlers, and then return to
Python a boolean telling it whether the event was cancelled:

``` {.javascript}
function __runHandlers(handle, type) {
    // ..
    var evt = new Event();
    for (var i = 0; i < list.length; i++) {
        list[i](evt);
    }
    return evt.cancelled;
}
```

That boolean will go to `event`, which will return that to its caller:

``` {.python}
def event(self, type, elt):
    cancelled = False
    if elt.handle:
        cancelled = self.js.evaljs(# ...)
    return cancelled
```

Finally, where we called `event` we need to check that return value to
determine whether or not to proceed. So in `handle_click`:

``` {.python}
def handle_click(self, e):
    # ...
    if elt and self.event('click', elt): return
    # ...
```

and in `submit_form`:

``` {.python}
def submit_form(self, form):
    # ...
    if self.event("submit", elt): return
```

There isn\'t any action associated with the `change` event on input
areas, so we don\'t need to modify that.

Now we can go back to `comment.js` and add a global variable tracking
whether or not submission is allowed:

``` {.javascript}
allow_submit = true;

function lengthCheck() {
    allow_submit = input.getAttribute("value").length <= 100;
    if (!allow_submit) {
        // ...
    }
}

form = document.querySelectorAll("form")[0];
form.addEventListener("submit", function(e) {
    if (!allow_submit) e.preventDefault();
});
```

Now it should be impossible to submit the form if the comment is too
long.

Well... Impossible in this browser. But there are browsers that don\'t
run JavaScript (like ours, one chapter back). So let\'s add a check on
the server side as well:

``` {.python}
def handle_request(method, url, headers, body):
    # if /comment.js or /comment.css
    else:
        if method == "POST":
            # ...
            if 'guest' in params and len(params['guest']) <= 100:
                ENTRIES.append(params["guest"])
        # ...
```

Summary
=======

Our browser has again grown by leaps and bounds, and now can run
JavaScript applications on behalf of websites. Sure, right now it
supports a pretty small portion of the DOM API, but with persistence
that could be slowly grown to provide everything real browsers provide.
More importantly, the functionality of web pages can now be extended not
just with new browser features but with new, clever scripts written by
the untold millions of web developers out there in the world.

Exercises
=========

-   Add support for the `children` DOM property, so that `node.children`
    returns an array of all children of a node. This array should only
    contain `ElementNode` children; `TextNode` children should be
    skipped.[^13]
-   The method `document.createElement` allows a script to create a new
    element, which it can then attach to the document with the
    `appendChild` and `insertBefore` methods on nodes. A big advantage
    over `innerHTML` is that these three methods bypass parsing.
    Implement these three methods.
-   If you try the above code, you\'ll find that it\'s actually
    impossible to bind an event handler to clicks on links. That\'s
    because when you click a link, the `elt` returned by `find_element`
    is the text inside the link, not the link element itself. On the
    web, this sort of quirk is handled by *event bubbling*: when an
    event is generated on an element, handlers are run on that element
    as well as all of its ancestors. Handlers can call `stopPropagation`
    on the event object to, well, stop bubbling the event up the tree.
    Implement event bubbling. Make sure `preventDefault` successfully
    prevents clicks on a link from actually following the link.
-   The `<canvas>` element is a new addition in HTML 5 that makes it
    possible from scripts to draw pictures using a simple Canvas API,
    much like the Tk canvas we\'ve been using to implement our browser.
    Using `<canvas>` takes [a few
    steps](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial).
    First, you select the element in JavaScript. Then, you call
    `canvas.getContext("2d")` on it, which returns a thing called a
    Context. Finally, the context provides methods like `fillRect` and
    `fillText` to actually draw on the canvas. Implement the basics of
    `<canvas>`, such as the two methods just mentioned. You\'ll want a
    custom layout type for canvases, which store a list of drawing
    commands and append to it when canvas methods are called.
-   The `XMLHttpRequest` object allows scripts to make HTTP requests and
    read the resulting contents. We want to implement this API, by
    creating the `XMLHttpRequest` class and implementing the
    `addEventListener`, `open`, and `send` methods. One quirk is that
    generally, `XMLHttpRequest` calls are asynchronous, which means we
    can\'t call the event listener until the currently-executing script
    is done running. For simplicity, you need not actually implement
    asynchronous requests, but you do need to respect the semantics.
    That means you will need some kind of queue to remember the requests
    you need to make (once the current script is done running) and the
    handlers to call afterwards.

[^6]: Have you noticed that we now have a half-dozen of these functions?
    If our selector language was richer, like if it supported attribute
    selectors, we could replace most of them with `find_selected`.

[^7]: Yes, that\'s a confusing error message. Is it a `JSRuntimeError`,
    an `EvalError`, or a `TypeError`?

[^8]: If you think about it, they are basically the same thing as file
    descriptors, which give user-level applications a handle to kernel
    data structures which they can\'t interpret without the kernel\'s
    help anyway.

[^9]: Note to JS experts: Dukpy does not implement a lot of the newer JS
    syntax, like `let` and `const` or arrow functions. You\'ll need to
    avoid them.

[^10]: If you\'re not familiar with JavaScript, you might want to read
    up on the crazy way you define classes in JavaScript. Modern
    JavaScript also provides the `class` syntax, which makes more sense,
    but it\'s not supported in DukPy.

[^11]: After, not before, so that any event handlers see the new value.

[^12]: Unless you did that exercise, in which case you\'ll have to
    adjust.

[^13]: The DOM method `childNodes` gives access to both elements and
    text. Feel free to implement it if you\'d like...
