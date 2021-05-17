---
title: Running Interactive Scripts
chapter: 9
prev: forms
next: security
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
book,^[But check out a book on programming language implementation
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

Like any JavaScript engine, DukPy not only executes JavaScript code,
but also allows JavaScript code to call Python functions that you've
*registered*. We'll be heavily using this feature to allow JavaScript
code to modify the web page it's running on.

The first step to using DukPy is installing it. On most machines,
including on Windows, macOS, and Linux systems, you should be able to do
this with the command:

``` {.example}
pip3 install dukpy
```

::: {.quirk}
Depending on your computer, the `pip3` command might be called `pip`,
or you might use `easy_install` instead. You may need to install
`pip3`. If you do your Python programming through an IDE, you may need
to use your IDE's package installer. If nothing else works, you can
build [from source](https://github.com/amol-/dukpy).

If you're following along in something other than Python, you might
need to skip this chapter. If you're using C or C++, you could try
binding directly to the `duktape` library that `dukpy` uses.
:::

To test whether you installed DukPy correctly, execute:

``` {.python}
import dukpy
dukpy.evaljs("2 + 2")
```

If you get an error on the first line, you probably failed to install
DukPy.[^2] If you get an error, or a segfault, on the second line,
there's a chance that Duktape failed to compile, and maybe doesn't
support your system. In that case you might need to skip this
chapter.

[^2]: Or, on my Linux machine, I sometimes get errors due to file
    ownership. You may have to do some sleuthing.


Running JavaScript code
=======================

The test code above shows you how to run JavaScript code with DukPy:
you just call `evaljs`! With this newfound knowledge, let's modify
our web browser to run JavaScript code.

On the web, JavaScript is found in `<script>` tags, in two different
ways. First, a `<script>` tag may have a `src` attribute with a
relative URL that points to a JavaScript file, much like with CSS
files. Second, a `<script>` tag may also have ordinary text contents,
which are run directly. For your toy browser, let's just implement the
first.^[The second makes parsing a challenge, since it's hard to avoid
less than and greater than comparisons in your code.]

The implementation here will look much like for CSS. First, let's
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
def load(self, url, body=None):
    # ... load, parse, style
    for script in find_scripts(self.nodes, []):
        header, body = request(relative_url(script, self.history[-1]))
        print("Script returned: ", dukpy.evaljs(body))
    self.layout(nodes)
```

That snippet refers to `self.nodes`; let's just create that field and
store the element tree in it.

Try this out on a simple script like this:

``` {.javascript}
var x = 2
x + x
```

Write that to `test.js` and try the following web page:

``` {.python}
<script src=test.js></script>
```

You should see your console print

    Script returned: 4

That's your browser's first bit of JavaScript!

::: {.quirk}
Our browser is making one major departure here from how real web
browsers work, a departure important enough to call out. In a real web
browser, JavaScript code is run as soon as the browser *parses* the
`<script>` tag, and at that point most of the page is not parsed and may
not even have been received over the network. But your toy browser
only runs scripts after loading and parsing the whole page. I don't
think the difference is essential to understanding how browsers run
interactive scripts.
:::

Registering functions
=====================

Browsers don't just print the last expression in a script; scripts
call the standard `console.log` function to print. To allow that, we
will need to *register a function* with DukPy, which would allow
Javascript code to run Python functions. Those functions are
registered on a `JSInterpreter` object, which we'll need to create:

``` {.python}
class Browser:
    def setup_js(self):
        self.js_environment = dukpy.JSInterpreter()
```

We can call this `setup_js` function when pages load:

``` {.python}
class Browser:
    def load(self, url, body=None):
        # ...
        self.setup_js()
        for script in find_scripts(self.nodes, []):
            # ...
```

For `console.log`, we'll first need a Python function that print its
argument---`print`.[^5] We can register it using `export_function`:

[^5]: If you're using Python 2, for some reason, you'll need to write
    a little wrapper function around `print` instead.

``` {.python}
def setup_js(self):
    # ...
    self.js_environment.export_function("log", print)
```

You can call this registered function via Dukpy's `call_python`
function:

``` {.javascript}
call_python("log", "Hi from JS")
```

That will convert the string `"Hi from JS"` from a Javascript to a
Python string,^[This conversion also works on numbers, string, and
booleans, but I wouldn't try it with other objects.] and run the
`print` function with that argument.

We actually want a `console.log` function, not a `call_python`
function, so we need to define a `console` object and then give it a
`log` property. We do that *in JavaScript*, with code like this:

``` {.javascript}
console = { log: function(x) { call_python("log", x); } }
```

In case you're not too familiar with JavaScript,^[Now's a good time to
brush up---this chapter has a ton of JavaScript!] this defines a
variable called `console`, whose value is an object literal with the
property `log`, whose value is the function you see defined there.

Taking a step back, when we run JavaScript in our browser, we're
mixing: C code, which implements the JavaScript interpreter; Python
code, which handles certain JavaScript functions; and JavaScript code,
which wraps the Python API to look more like the JavaScript one. We
can call that JavaScript code our "JavaScript runtime"; we run it
before we run any user code, so let's stick it in a `runtime.js`
file that's run in `setup_js`:

``` {.python}
def setup_js(self):
    # ...
    with open("runtime.js") as f:
        self.js_environment.evaljs(f.read())
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

where `a.js` is "`var x = 2;`" and `b.js` is "`console.log(x + x)`".
In real web browsers, that's important since one script might define
library functions that another script wants to call.

Handling Crashes
================

Crashes in JavaScript code are frustrating to debug. Try, for example:

``` {.javascript}
function bad() { throw "bad"; }
bad();
```

Your browser runs two kinds of JavaScript, and so there are two kinds
of crashes: crashes in web page scripts, and crashes in your own
JavaScript runtime. In the first case, you want to ignore those
crashes:

``` {.python}
try:
    print("Script returned: ", self.js.evaljs(body))
except dukpy.JSRuntimeError as e:
    print("Script", script, "crashed", e)
```

Note that besides printing the expression the error is ignored.
Crashes in web page scripts shouldn't crash our browser.

But crashes in the JavaScript runtime are different. We can't ignore
those, because we want our runtime to work, and by default Dukpy won't
show a backtrace to help you debug a crash. It's even worse if the
runtime code calls into a registered function that crashes.

To help, wrap each registered function to print any backtraces it
produces:

``` {.python}
try:
    # ...
except:
    import traceback
    traceback.print_exc()
    raise
```

Re-raise the exception so that you still get the crash.

Also wrap all functions in the JavaScript runtime so that they print
backtraces too:

``` {.javascript}
try {
    # ...
} catch(e) {
    console.log(e.stack);
    throw e;
}
```

That'll ensure that at least some useful information will be printed
when there's an error.

Querying the DOM
================

So far, JavaScript evaluation is fun but useless, because JavaScript
can't make any kinds of modifications to the page itself. Why even
run JavaScript if it can't do anything besides print? So let's work
on modifying the page from JavaScript.

The JavaScript functions that manipulate a web page are collectively
called the DOM API, for "Document Object Model". The DOM API is big,
and it keeps getting bigger, so I'm not implementing all, or even
most, of it. But a few core functions have much of the power of the
full API:

-   `querySelectorAll` returns all the elements matching a selector;
-   `getAttribute` returns an element's value for some attribute; and
-   `innerHTML` replaces the contents of an element with new HTML.

I've implemented a simplified version of these methods.
`querySelectorAll` will return an array, not this thing called a
`NodeList`; `innerHTML` will only write the HTML contents of an
element, and won't allow reading those contents.

Let's start with `querySelectorAll`. First, register a function:

``` {.python}
def setup_js(self):
    # ...
    self.js_environment.export_function(
        "querySelectorAll",
        self.js_querySelectorAll
    )
    # ...
```

In JavaScript, `querySelectorAll` is a method on the `document`
object, so define one in the JavaScript runtime:

``` {.python}
document = { querySelectorAll: function(s) {
    return call_python("querySelectorAll", s);
}}
```

The `js_querySelectorAll` handler will first parse the selector, then
find and return the matching elements. To parse just the selector,
I'll call into the `CSSParser`'s `selector` method:

``` {.python}
def js_querySelectorAll(self, selector_text):
    selector, _ = CSSParser(selector_text + "{").selector(0)
```

I'm parsing, say, `#id{` instead of `#id`, because that way the
selector parser won't go off the end of the string and throw an
error. I've moved the actual selector matching to a recursive helper
function:[^6]

``` {.python}
def js_querySelectorAll(self, selector_text):
    # ...
    return find_selected(self.nodes, selector, [])
```

[^6]: Have you noticed that we now have a half-dozen of these functions?
    If our selector language was richer, like if it supported attribute
    selectors, we could replace most of them with `find_selected`.
    
The `find_selected` function is just another recursive tree walk:

``` {.python}
def find_selected(node, sel, out):
    if not isinstance(node, ElementNode): return
    if sel.matches(node):
        out.append(node)
    for child in node.children:
        find_selected(child, sel, out)
    return out
```

By the way, now is a good time to wonder what would happen if you
passed `querySelectorAll` an invalid selector. We're helped out here
by some of the nice features of DukPy. For example, with an invalid
selector, `CSSParser.selector` throws an error and the registered
function crashes. DukPy would turn that Python-side exception into a
JavaScript-side exception in the web script we are running, which can
catch it or do something else.

So `querySelectorAll` looks complete, but if you try calling the
function from JavaScript, you'll see an error like this:[^7]


``` {.example}
_dukpy.JSRuntimeError: EvalError:
Error while calling Python Function:
TypeError('Object of type ElementNode is not JSON serializable')
```

[^7]: Yes, that's a confusing error message. Is it a `JSRuntimeError`,
    an `EvalError`, or a `TypeError`?

What DukPy is trying to tell you is that it has no idea what to do
with the `ElementNode` objects that `querySelectorAll` is returning,
since that class only exists in Python, not JavaScript.

Instead of returning browser objects directly to JavaScript, we need
to keep browser objects firmly on the Python side of the browser.
JavaScript will need to refer to them by some kind of reference; I'll
use simple numeric identifier. The browser has to keep track of which
identifer---which I'll call a *handle*---maps to which
`ElementNode`.[^8]

[^8]: Handles are the browser analogs of file descriptors, which give
    user-level applications a handle to kernel data structures.

Let's first create a `node_to_handle` data structure to map nodes to
handles, and a `handle_to_node` map that goes the other way:

``` {.python}
class Browser:
    def setup_js(self):
        self.node_to_handle = {}
        self.handle_to_node = {}
        # ...
```

Then, I'll allocate new handles for each node being returned into
JavaScript:

``` {.python}
def js_querySelectorAll(self, sel):)
    # ...
    elts = find_selected(self.nodes, selector, [])
    return [self.make_handle(elt) for elt in elts]
```

Where `make_handle` creates a new handle if one doesn't exist
yet:[^id-elt]

[^id-elt]: `node_to_handle` uses `id(elt)` instead of `elt` as its key
    because Python objects can't be used as hash keys by default.

``` {.python}
def make_handle(self, elt):
    if id(elt) not in self.node_to_handle:
        handle = len(self.node_to_handle)
        self.node_to_handle[id(elt)] = handle
        self.handle_to_node[handle] = elt
    else:
        handle = self.node_to_handle[id(elt)]
    return handle
```

Calling `document.querySelectorAll` will now return something like
`[1, 3, 4, 7]`, with each number being a handle for an element. That
fixes the error above, and also allows scripts to count the number of
paragraphs on the page:

``` {.javascript}
console.log(document.querySelectorAll("p").length)
```

But ideally `querySelectorAll` should return an array of `Node`
objects, which themselves have additional methods like `getAttribute`.
Let's work on setting that up next.

# Wrapping handles

JavaScript can now get element handles, but those handles are just
numbers. How do you call `getAttribute` on them?

Well, the idea is that `getAttribute` should take in handles and
convert those handles back into elements. It would look like this:

``` {.python}
class Browser:
    def js_getAttribute(self, handle, attr):
        elt = self.handle_to_node[handle]
        return elt.attributes.get(attr, None)
```

We can register this function as `getAttribute` and run a script like
this:[^9]

``` {.javascript}
scripts = document.querySelectorAll("script")
for (var i = 0; i < scripts.length; i++) {
    console.log(call_python("getAttribute", scripts[i].handle, "src"));
}
```

[^9]: Note to JS experts: Dukpy does not implement newer JS syntax
    like `let` and `const` or arrow functions. You'll need to use
    old-school JavaScript from the turn of the centry.

That should print out the URLs of all of the scripts on the page. Note
that the attribute is not assigned, the `None` value returned from
Python will be translated by DukPy to `null` in JavaScript.

Let's wrap this ugly `call_python` method so JavaScript can use the
standard `getAttribute` method on `Node` objects returned by
`querySelectorAll`. Let's define that `Node` class in our
runtime.[^10]

``` {.javascript}
function Node(handle) { this.handle = handle; }
Node.prototype.getAttribute = function(attr) {
    return call_python("getAttribute", this.handle, attr);
}
```

[^10]: If your JavaScript is rusty, you might want to read up on the
    crazy way you define classes in JavaScript. Modern JavaScript also
    provides the `class` syntax, which is more sensible, but it's not
    supported in DukPy.

Now we can create these `Node` objects in `querySelectorAll`'s
wrapper:[^11]

``` {.javascript}
document = { querySelectorAll: function(s) {
    var handles = call_python("querySelectorAll", s)
    return handles.map(function(h) { return new Node(h) });
}}
```

[^11]: This code creates new `Node` objects every time you call
    `querySelectorAll`, even if there's already a `Node` for that
    handle. That means you can't use equality to compare `Node`
    objects. I'll ignore that but a real browser wouldn't.

We finally have enough JavaScript features to implement a little
character count function for text areas:

``` {.javascript}
inputs = document.querySelectorAll('input')
for (var i = 0; i < inputs.length; i++) {
    var name = inputs[i].getAttribute("name");
    var value = inputs[i].getAttribute("value");
    if (value.length > 100) {
        console.log("Input " + name + " has too much text.")
    }
}
```

Now, we'd like to run the character count every time the user types
into an input box.

Event handling
==============

The browser executes JavaScript code as soon as it loads the web page,
but most changes to the page should be made *in response* to user
actions. Bridging the gap, most scripts set code to run when *page
events*, like button clicks or key presses, occur.

Here's how that works. First, any time the user interacts with the
page, the browser generates *events*. Each event has a name, like
`change`, `click`, or `submit`, and a target element (an input area, a
link, or a form). JavaScript code can call `addEventListener` to react
to those events: `node.addEventListener('click', handler)` sets
`handler` to run every time the element corresponding to `node`
generates a `click` event.

Let's start with generating events. First, create a `dispatch_event`
method and call it whenever an event is generated. First, any time we
click in the page:

``` {.python}
def handle_click(self, e):
    if e.y < 60:
        # ...
    else:
        # ...
        elt = obj.node
        if elt: self.dispatch_event('click', elt)
        # ...
```

Second, after updating input area values:[^edit-then-event]

``` {.python}
def keypress(self, e):
    # ...
    else:
        self.focus.node.attributes["value"] += e.char
        self.dispatch_event("change", self.focus.node)
        self.layout(self.document.node)
```

[^edit-then-event]: After, not before, so that any event handlers see
    the new value.

And finally, when submitting forms but before actually sending the
request to the server:

``` {.python}
def submit_form(self, elt):
    # ...
    if not elt: return
    self.dispatch_event("submit", elt)
    # ...
```

So far so good---but what should the `dispatch_event` method do? Well,
it needs to run the handlers set up by `addEventListener`, so those
need to be stored somewhere. Where? I propose we keep that data on the
JavaScript side, in an variable in the runtime. I'll call that
variable `LISTENERS`; we'll use it to look up handles and event types,
so let's make map handles to a dictionary that maps event types to a
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

We use the `LISTENERS` array to run the handlers. Still in JavaScript:

``` {.javascript}
function __runHandlers(handle, type) {
    var list = (LISTENERS[handle] && LISTENERS[handle][type]) || [];
    for (var i = 0; i < list.length; i++) {
        list[i].call(new Node(handle));
    }
}
```

When I call the handler I use JavaScript's `call` method on functions,
which allows me to set the value of `this` inside that function. As is
standard in JavaScript, I'm setting it to the node that the event was
generated on.

So `event` now just calls `__runHandlers` from Python:

``` {.python}
def dispatch_event(self, type, elt):
    handle = self.make_handle(elt)
    code = "__runHandlers({}, \"{}\")".format(handle, type)
    self.js_environment.evaljs(code)
```

Note that this code passes arguments to `__runHandlers` by generating
JavaScript code that embeds those arguments directly. This would be a
bad idea if, say, `type` contained a quote or a newline. But since the
browser supplies that value that won't ever happen.[^dukpy-object]

[^dukpy-object]: DukPy provides the `dukpy` object to do this better,
    but in the interest of simplicity I'm not using it

With all this event-handling machinery in place, we can run the
character count every time an input area changes:

``` {.python}
function lengthCheck() {
    var name = this.getAttribute("name");
    var value = this.getAttribute("value");
    if (value.length > 100) {
        console.log("Input " + name + " has too much text.")
    }
}

var inputs = document.querySelectorAll("input");
for (var i = 0; i < inputs.length; i++) {
    inputs[i].addEventListener("change", lengthCheck);
}
```

Note that `lengthCheck` uses `this` to reference the input element
that actually changed, as set up by `__runHandlers`.

So far so good---but ideally the length check wouldn't print to the
console; it would add a warning to the web page itself. To do that,
we'll need to not only read from but also write to the DOM.

Modifying the DOM
=================

So far, we've only implemented read-only DOM methods; now we need to
write to the DOM. The full DOM API provides a lot of such methods, but
for simplicity I'm going to implement only `innerHTML`, which is used
like this:

``` {.javascript}
node.innerHTML = "This is my <b>new</b> bit of content!";
```

In other words, `innerHTML` is a *property* of node objects, with a
*setter* that is run when the field is modified. That setter takes the
new value, which must be a string, parses it as HTML, and makes the
new, parsed HTML nodes children of the original node.

Let's implement this, starting on the JavaScript side. JavaScript has
the obscure `Object.defineProperty` function to define setters:

``` {.javascript}
Object.defineProperty(Node.prototype, 'innerHTML', {
    set: function(s) {
        call_python("innerHTML", this.handle, "" + s);
    }
});
```

I'm using `"" + s` to convert the new value of `innerHTML` to a
string. Next, we need to register the `innerHTML` function:

``` {.python}
def setup_js(self):
    # ...
    self.js_environment.export_function(
        "innerHTML",
        self.js_innerHTML
    )
    # ...
```

In `innerHTML`, we'll need to parse the HTML string. That turns out to
be trickier than you'd think, because our browser's HTML parser is
intended to parse whole HTML documents, not document fragments like
this. That means it inserts implicit tags, and also that it returns a
single HTML node instead of the multiple child nodes that `innerHTML`
is supposed to use. To bridge the gap, `js_innerHTML` must convert the
HTML string `s` into a full document:

``` {.python}
def js_innerHTML(self, handle, s):
    doc = parse(lex("<html><body>" + s + "</body></html>"))
    new_nodes = doc.children[0].children
```

Now the new nodes can be made the children of the element `innerHTML`
was called on:

``` {.python}
def js_innerHTML(self, handle, s):
    # ...
    elt = self.handle_to_node[handle]
    elt.children = new_nodes
    for child in elt.children:
        child.parent = elt
```

We need to update the parent pointers of those parsed child nodes
because until we do that, they point to the fake `<body>` element that
we added. Since the page changed, we need to lay it out again. You
might be tempted to do that by calling `layout`, like so:

``` {.python}
def js_innerHTML(self, handle, s):
    # ...
    self.layout(self.nodes)
```

But remember that before we lay out a node, we need to style it,
and the new nodes added from JavaScript haven't been styled yet.
To fix this, we'll need to save the CSS rules in `load`

``` {.python}
def load(self, url, body=None):
    # ...
    self.rules = rules
    self.layout(self.nodes)
```

and then move the call to `style` into `layout`:

``` {.python}
def layout(self, tree):
    style(tree, None, self.rules)
    # ...
```

JavaScript can now modify the web page!

Let's go ahead and use this in our guest book server. Do you want
people writing long rants in *your* guest book? I don't, so I'm
going to put a 100-character limit on guest book entries.

First, let's add a new paragraph `<p id=errors></p>` after the guest
book form. Initially this paragraph will be empty, but we'll write an
error message into it if the paragraph gets too long.

Next, let's add a script to the page. That means a new line of HTML:

``` {.python}
def show_comments():
    # ...
    out += "<script src=/comment.js></script>"
    # ...
```

We also need to *serve* that new JavaScript file, so our little web
server will now need to respond to the `/comment.js` URL:

``` {.python}
def handle_request(method, url, headers, body):
    if method == 'POST':
        # ..
    else:
        if url == '/comment.js':
            with open("comment.js") as f:
                return f.read()
        # ...
```

We can then put our little input length checker into `comment.js`,
with the `lengthCheck` function modified like so to use `innerHTML`:

``` {.javascript}
p_error = document.querySelectorAll("#errors")[0];

function lengthCheck() {
    var value = this.getAttribute("value");
    if (value.length > 100) {
        p_error.innerHTML = "Comment too long!"
    }
}

input = document.querySelectorAll("input")[0];
input.addEventListener("change", lengthCheck);
```

Try it out: write a long comment and you should see the page warning
you that the comment is too long. By the way, we might want to make it
stand out more, so let's go ahead and add another URL to our web
server, `/comment.css`, with the contents:

``` {.css}
#errors { font-weight: bold; color: red; }
```

But even though we tell the user that their comment is too long the
user can submit the guest book entry anyway. Oops!

Event defaults
==============

So far, when an event is generated, the browser will run the handlers,
and then *also* do whatever it normally does for that event. I'd now
like JavaScript code to be able to *cancel* that default action.

There are a few steps involved. First of all, event handlers should
receive an *event object* as an argument. That object should have a
`preventDefault` method. When that method is called, the default
action shouldn't occur.

First of all, we'll need event objects. Back to our JS runtime:

``` {.javascript}
function Event(type) {
    this.type = type
    this.do_default = true;
}

Event.prototype.preventDefault = function() {
    this.do_default = false;
}
```

Next, we need to pass the event object to handlers.

``` {.javascript}
function __runHandlers(handle, type) {
    // ...
    var evt = new Event(type);
    for (var i = 0; i < list.length; i++) {
        list[i].call(new Node(handle), evt);
    }
    // ...
}
```

After calling the handlers, `evt.cancelled` tells us whether
`preventDefault` was called; let's return that to Python:

``` {.javascript}
function __runHandlers(handle, type) {
    // ...
    return evt.do_default;
}
```

On the Python side, `event` can return that boolean to its handler

``` {.python}
def dispatch_event(self, type, elt):
    # ...
    do_default = self.js_environment.evaljs(code)
    return not do_default
```

Finally, whatever event handler runs `dispatch_event` should check
that return value and stop if it is `True`. So in `handle_click`:

``` {.python}
def handle_click(self, e):
    # ...
    if elt and self.dispatch_event('click', elt): return
    # ...
```

And also in `submit_form`:

``` {.python}
def submit_form(self, form):
    # ...
    if self.dispatch_event("submit", elt): return
```

There's no default action for the `change` event on input areas, so we
don't need to modify that.^[You can't stop the browser from changing
the value: it's already changed when the event handler is run.]

With this change, `comment.js` can use a global variable to track
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

Now it's impossible to submit the form when the comment is too long.

Well... Impossible in this browser. But there are browsers that don't
run JavaScript (like ours, one chapter back). So we should do the
check on the server side also:

``` {.python}
def add_entry(params):
    if 'guest' in params and len(params['guest']) <= 100:
        ENTRIES.append(params["guest"])
    return show_comments()
```

Summary
=======

Our browser now runs JavaScript applications on behalf of websites.
Granted, it supports just four methods from the vast DOM API, but even
those include:

- Generating handles to allow scripts to refer to page elements
- Reading attribute values from page elements
- Writing and modifying page elements
- Attaching event listeners so that scripts can respond to page events

A web page can now add functionality via a clever script, instead of
waiting for a browser developer to add it into the browser itself.

Exercises
=========

*Node.children*: Add support for the [`children` field][children] on
JavaScript `Node`s. `Node.children` returns the immediate
`ElementNode` children of a node, as an array. `TextNode` children are
not included.[^13]
    
[children]: https://developer.mozilla.org/en-US/docs/Web/API/ParentNode/children

[^13]: The DOM method `childNodes` gives access to both elements and
    text. Feel free to implement it if you'd like...

*createElement*: The [method `document.createElement`][createElement]
creates a new element, which can be attached to the document with the
[`appendChild`][appendChild] and [`insertBefore`][insertBefore]
methods on nodes; unlike `innerHTML`, there's no parsing involved.
Implement all three methods.

[createElement]: https://developer.mozilla.org/en-US/docs/Web/API/Document/createElement

[appendChild]: https://developer.mozilla.org/en-US/docs/Web/API/Node/appendChild

[insertBefore]: https://developer.mozilla.org/en-US/docs/Web/API/Node/insertBefore

*Event Bubbling*: Try to run an event handler when the user clicks on
a link: you'll find that it's actually impossible. That's because when
you click a link, the `elt` returned by `find_element` is the text
inside the link, not the link element itself. On the web, this sort of
quirk is handled by *event bubbling*: when an event is generated on an
element, handlers are run not just on that element but also on its
ancestors. Implement event bubbling, and make sure JavaScript can
attach to clicks on links. Handlers can call `stopPropagation` on the
event object to, well, stop bubbling the event up the tree. Make sure
`preventDefault` successfully prevents clicks on a link from actually
following the link.

*Canvas*: The [`<canvas>` element][canvas-tutorial] is a new addition
in HTML 5; scripts can draw pictures on the `<canvas>`, much like the
Tk canvas we've been using to implement our browser. To use the
`<canvas>`, you first select the element in JavaScript; then call
`canvas.getContext("2d")` on it, which returns a thing called a
"context"; and finally call methods like `fillRect` and `fillText` on
that context to draw on the canvas. Implement the basics of
`<canvas>`, including `fillRect` and `fillText`. Canvases will need a
custom layout object that store a list of drawing commands.
    
[canvas-tutorial]: https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial

*AJAX Requests*: The [`XMLHttpRequest` object][xhr-tutorial] allows
scripts to make HTTP requests and read the responses. Implement this
API, including the `addEventListener`, `open`, and `send` methods.
Beware that `XMLHttpRequest` calls are asynchronous: you need to
finish executing the script before calling any event listeners on an
`XMLHttpRequest`.[^sync-xhr-ok] That will require some kind of queue
of requests you need to make and the handlers to call afterwards. Make
sure `XMLHttpRequest`s work even if you create them inside event
handlers.
    
[^sync-xhr-ok]: It is OK for the browser make the request
    synchronously, using our `request` function. But the whole script
    should finish running before calling the callback.

[xhr-tutorial]: https://developer.mozilla.org/en-US/docs/Web/API/XMLHttpRequest/Using_XMLHttpRequest

