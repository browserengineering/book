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
argument---`print`.[^5] We can register it using `export_function`:

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

::: {.quirk}
Our browser is making one major departure here from how real web
browsers work, a departure important enough to call out. In a real web
browser, JavaScript code is run as soon as the browser *parses* the
`<script>` tag, and at that point most of the page is not parsed and may
not even have been received over the network. But the way I\'ve written
the code, my toy browser only runs scripts after the page is fully
loaded. Given how we\'ve structured our browser, it would,
unfortunately, be pretty hard to do this right, and I don't think it's
essential to understanding how browsers run interactive scripts.
:::

As a side benefit of using one `JSInterpreter` for all scripts, it is
now possible to run two scripts and have one of them define a variable
that the other uses, say on a page like:

``` {.python}
<script src=a.js></script>
<script src=b.js></script>
```

where `a.js` is \"`var x = 2;`\" and `b.js` is \"`console.log(x + x)`\".


Handling Crashes
================

Crashes in JavaScript code are frustrating to debug. Try, for example:

``` {.javascript}
function bad() { throw "bad"; }
bad();
```

You won't see a backtrace to help you debug this crash. The issue is
that DukPy backtraces can go between JavaScript and Python several
times, so the feature isn't supported. I recommend wrapping Python
registered functions like so to print any backtraces they produce:

``` {.python}
try:
    # ...
except:
    import traceback
    traceback.print_exc()
    raise
```

Note that I re-raise the exception, so that I still get the crash.

When Python in calls JavaScript, you can wrap that JavaScript like
this:

``` {.javascript}
try {
    # ...
} catch(e) {
    console.log(e.stack);
    throw e;
}
```

That'll again ensure that some useful information will be printed that
can help you debug.

Querying the DOM
================

So far, JavaScript evaluation is fun but useless, because JavaScript
can't make any kinds of modifications to the page itself. Why even
run JavaScript if it can't do anything besides print? So let\'s work
on modifying the page from JavaScript.

The JavaScript functions that manipulate a web page are collectively
called the DOM API, for \"Document Object Model\". The DOM API is big,
and it keeps getting bigger, so I\'m not implementing all, or even
most, of it. But a few core functions have much of the power of the
full API:

-   `querySelectorAll` returns all the elements matching a selector;
-   `getAttribute` returns an element's value for some attribute; and
-   `innerHTML` replaces the contents of an element with new HTML.

I'm implemented a simplified version of these methods.
`querySelectorAll` will return an array, not this thing called a
`NodeList`; `innerHTML` will only write the HTML contents of an
element, and won't allow reading those contents.

Let\'s start with `querySelectorAll`. First, register a function:

``` {.python}
class Browser:
    def parse(self):
        # ...
        self.js.export_function("querySelectorAll", self.js_querySelectorAll)
        # ...

    def js_querySelectorAll(self, sel):
        # ...
```

Normally, `querySelectorAll` is a method on the `document` object, so
define one in the JavaScript runtime:

``` {.python}
document = { querySelectorAll: function(s) {
    return call_python("querySelectorAll", s);
}}
```

The `js_querySelectorAll` handler will first parse the selector, then
find and return the matching elements:

``` {.python}
selector, _ = CSSParser(sel + "{").selector(0)
return find_selected(self.nodes, selector, [])
```

I\'m parsing, say, `#id{` instead of `#id`, because that way the
selector parser won\'t go off the end of the string and throw an
error. I\'ve moved the actual selector matching to a recursive helper
function:[^6]

[^6]: Have you noticed that we now have a half-dozen of these functions?
    If our selector language was richer, like if it supported attribute
    selectors, we could replace most of them with `find_selected`.

``` {.python}
def find_selected(node, sel, out):
    if not isinstance(node, ElementNode): return
    if sel.matches(node):
        out.append(node)
    for child in node.children:
        find_selected(child, sel, out)
    return out
```

With these minimal changes, `querySelectorAll` finds the matching
elements. However, if you actually try calling the function from
JavaScript, you'll see an error like this:[^7]


``` {.example}
_dukpy.JSRuntimeError: EvalError:
Error while calling Python Function:
TypeError('Object of type ElementNode is not JSON serializable')
```

[^7]: Yes, that\'s a confusing error message. Is it a `JSRuntimeError`,
    an `EvalError`, or a `TypeError`?

But what DukPy is trying to tell you is that it has no idea what to do
with the `ElementNode` objects you\'re returning from
`querySelectorAll`, since there is no corresponding class in
JavaScript.

Instead of returning browser objects directly to JavaScript, we need
to keep browser objects firmly on the Python side of the browser, and
toss references to those browser objects over the fence to JavaScript.
Those references can be simple numeric identifier; the browser will
keep track of which identifer maps to which element. I\'ll call these
identifiers *handles*.[^8]

[^8]: Handles are the browser analogs of file descriptors, which give
    user-level applications a handle to kernel data structures which
    they can\'t interpret without the kernel\'s help anyway.

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

I\'ll also add a `handle` field to each `ElementNode` to store its
handle. If no handle has been assigned yet, I'll set the field to 0:

``` {.python}
class ElementNode:
    def __init__(self, parent, tagname):
        # ...
        self.handle = 0
```

::: {.todo}
I think I'd rather put two makes inside the JSEnvironment class.
:::

Then, in `js_querySelectorAll`, I\'ll allocate new handles for each of
the matched nodes:

``` {.python}
elts = find_selected(self.nodes, selector, [])
out = []
for elt in elts:
    out.append(self.make_handle(elt))
return out
```

The `make_handle` method merely creates a new handle if none exist yet:

``` {.python}
def make_handle(self, elt):
    if not elt.handle:
        handle = len(self.js_handles) + 1
        elt.handle = handle
        self.js_handles[handle] = elt
    return elt.handle
```

The curious `len(self.js_handles) + 1` expression computes the
smallest handle not in the handles list.

Calling `document.querySelectorAll` will now return something like
`[1, 3, 4, 7]`, with each number being a handle for an element. Great!
So now this script, say, will count the number of paragraphs on the
page:

``` {.javascript}
console.log(document.querySelectorAll("p").length)
```

By the way, now is a good time to wonder what would happen if you
passed `querySelectorAll` an invalid selector. We\'re helped out here
by some of the nice features of DukPy. For example, with an invalid
selector, `CSSParser.selector` would throw an error, and the
registered function would crash. But in that case DukPy will turn our
Python-side exception into a JavaScript-side exception in the web
script we are running, which can catch it or do something else.

# Wrapping handles

Our JavaScript code can now get references to elements, but those
references are opaque numbers. How do you call `getAttribute` on them?

Well, the idea is that `getAttribute` should take in handles and
convert those handles back into elements. It would look like this:

``` {.python}
class Browser:
    def js_getAttribute(self, handle, attr):
        elt = self.js_handles[handle]
        return elt.attributes.get(attr, None)
```

We can register this function as `getAttribute`, and now run:[^9]

``` {.python}
scripts = document.querySelectorAll("script")
for (var i = 0; i < scripts.length; i++) {
    console.log(call_python("getAttribute", scripts[i], "src"));
}
```

[^9]: Note to JS experts: Dukpy does not implement newer JS syntax
    like `let` and `const` or arrow functions.

That should print out the URLs of all of the scripts on the page. Note
that the attribute is not assigned, the `None` value returned from
Python will be translated by DukPy to `null` in JavaScript.

Finally, we'd like to wrap this ugly `call_python` method. Normally
`querySelectorAll` returns `Node` obejcts and you call `getAttribute`
directly on those `Node` objects. Let\'s define that `Node` class in
our runtime.[^10]

``` {.javascript}
function Node(handle) { this.handle = handle; }
Node.prototype.getAttribute = function(attr) {
    return call_python("getAttribute", self.handle, attr);
}
```

[^10]: If your JavaScript is rusty, you might want to read up on the
    crazy way you define classes in JavaScript. Modern JavaScript also
    provides the `class` syntax, which is more sensible, but it\'s not
    supported in DukPy.

Then, in our `querySelectorAll` wrapper, we\'ll create these `Node`
objects:[^11]

``` {.python}
document = { querySelectorAll: function(s) {
    var handles = call_python("querySelectorAll", s)
    return handles.map(function(h) { return new Node(h) });
}}
```

[^11]: This code creates new `Node` objects every time you call
    `querySelectorAll`, even if there's already a `Node` for that
    handle. That means you can\'t use equality to compare `Node`
    objects. I\'ll ignore that but a real browser wouldn't.

We can now implement a little character count function:

``` {.python}
inputs = document.querySelectorAll('input')
for (var i = 0; i < inputs.length; i++) {
    var name = inputs[i].getAttribute("name");
    var value = inputs[i].getAttribute("value");
    if (value.length > 100) {
        console.log("Input " + name + " has too much text.")
    }
}
```

Now, ideally, we'd run the character count every time the user typed
something in an input box.

Event handling
==============

The browser executes JavaScript code as soon as it loads the web page,
but most changes to the page should be made *in response* to user
actions. Bridging the gap, most scripts set code to run when *page
events*, like clicks on buttons or changes to input areas, occur.

Here\'s how that works. First, any time the user interacts with the
page, the browser generates *events*. Each event has a type, like
`change`, `click`, or `submit`, and a target element (an input area, a
link, or a form). JavaScript code can call `addEventListener` to react
to those events: `elt.addEventListener('click', handler)` sets
`handler` to run every time the element `elt` generates a `click`
event.

Let's start our implementation with generating events. First, I'll
create an `event` method and call it in three places. First, any time
we click in the page:

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

Second, after updating input area values:[^edit-then-event]

``` {.python}
def edit_input(self, elt):
    # ...
    self.event("change", elt)
    self.relayout()
```

[^edit-then-event]: After, not before, so that any event handlers see
    the new value.

And finally, when submitting forms:

``` {.python}
def submit_form(self, elt):
    # while elt and elt.tag != "form"
    if not elt: return
    self.event("submit", elt)
    # ...
```

So far so good---but what should the `event` method do? Well, it needs
to run the handlers set up by `addEventListener`, so those need to be
stored somewhere—where? I propose we keep that data on the JavaScript
side, in an variable in the runtime. I'll call that variable
`LISTENERS`; we'll use it to look up handles and event types, so let's
make it a dictionary from handles to a dictionary from event types to
a list of handlers:

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
which allows me to set the value of `this` inside that function. Here
I set it to the element we're calling the handler on, as is standard
in JavaScript.

So `event` now just calls `__runHandlers` from Python:

``` {.python}
def event(self, type, elt):
    if not elt.handle: return
    self.js.evaljs("__runHandlers({}, \"{}\")".format(elt.handle, type))
```

There are two quirks with this code. First, I\'m not running handlers
if the element with the event doesn\'t have a handle. That\'s because
if it doesn\'t have a handle, it couldn\'t have been made into a
`Node`, and then `addEventListener` couldn\'t have been called on it.
Second, when I call `__runHandlers` I need to pass it arguments, which
I do by generating JavaScript code that embeds those arguments
directly. This would be a bad idea if, say, `type` contained a quote
or a newline. But the browser supplies that value, and it'll never be
weird.^[DukPy provides the `dukpy` object to do this better, but in
the interest of simplicity I\'m not using it]

With all of this done, we can now run the character count above on
every input area change:

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

Note how `lengthCheck` uses `this` to reference the input element that
actually changed.

So far so good—but ideally the length check wouldn't print to the
console; it would add a warning to the web page itself. To do that,
we'll need to not only read from but also write to the DOM.

Modifying the DOM
=================

So far, we've only implemented read-only DOM methods. Now we need to
write to the DOM. The full DOM API provides a lot of such methods, but
for simplicity I'm going implementing only `innerHTML`. That method
works like this:

``` {.javascript}
node.innerHTML = "This is my <b>new</b> bit of content!";
```

In other words, `innerHTML` is a *field* on node objects, with a
*setter* that is run when the field is modified. That setter takes the
new value, which must be a string, parses it as HTML, and makes the
new, parsed HTML nodes children of the original node.

Let\'s implement this, starting on the JavaScript side. JavaScript has
the obscure `Object.defineProperty` function to define setters:

``` {.javascript}
Object.defineProperty(Node.prototype, 'innerHTML' {
    set: function(s) {
        call_python("innerHTML", this.handle, "" + s);
    }
});
```

I'm using `"" + s` to convert the new value of `innerHTML` to a
string. Next, we need to register the `innerHTML` function:

``` {.python}
class Browser:
    def parse(self, body):
        # ...
        self.js.export_function("innerHTML", self.js_innerHTML)

    def js_innerHTML(self, handle, s):
        elt = self.js_handles[handle]
        # ?
```

In `innerHTML`, we\'ll need to parse the HTML string:

``` {.python}
new_node = parse(lex("<__newnodes>" + s + "</__newnodes>"))
```

Here I\'m adding a special `<__newnodes>` tag at the start of the source
because our HTML parser doesn\'t work right when you don\'t have a
single root node.[^12] Of course we don\'t want that new node, just its
children:

[^12]: Unless you did that exercise, in which case you\'ll have to
    adjust.

``` {.python}
elt.children = new_node.children
for child in elt.children:
    child.parent = elt
```

We need to update the parent pointers of those parsed child nodes
because until we do that, they point to the old `<__newnodes>`
element. Finally, since the page changed, we need to lay it out again:

``` {.python}
self.relayout()
```

JavaScript can now modify the web page!

Let\'s go ahead and use this in our guest book server. Do you want
people writing long rants in *your* guest book? I don\'t, so I\'m
going to put a 200-character limit on guest book entries.

First, let's add a new paragraph `<p id=errors></p>` after the guest
book form. Initially this paragraph will be empty, but we\'ll write an
error message into it if the paragraph gets too long.

Next, let\'s add a script to the page. That means a new line of HTML:

``` {.python}
out += "<script src=/comment.js></script>"
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
    if (value.length > 200) {
        p_error.innerHTML = "Comment too long!"
    }
}

input = document.querySelectorAll("input")[0];
input.addEventListener("change", lengthCheck);
```

Try it out: write a long comment and you should see the page warning
you that the comment is too long. By the way, we might want to make it
stand out more, so let\'s go ahead and add another URL to our web
server, `/comment.css`, with the contents:

``` {.css}
#errors { font-weight: bold; color: red; }
```

Now we tell the user that their comment is too long, but—oops!— the
user can still ignore the error message, and submitting the guest book
entry anyway.

Event defaults
==============

So far, when an event is generated, the browser will run the handlers,
and then *also* do whatever it normally does for that event. I'd now
like JavaScript code to be able to *cancel* that default action.

There are a few steps involved. First of all, event handlers should
receive an *event object* as an argument. That object should have a
`preventDefault` method. When that method is called, the default
action shouldn\'t occur.

First of all, we\'ll need event objects. Back to our JS runtime:

``` {.javascript}
function Event() { this.cancelled = false; }
Event.prototype.preventDefault = function() {
    this.cancelled = true;
}
```

Next, we need to pass the event object to handlers.

``` {.javascript}
function __runHandlers(handle, type) {
    // ...
    var evt = new Event();
    for (var i = 0; i < list.length; i++) {
        list[i](evt);
    }
    // ...
}
```

After calling the handlers, `evt.cancelled` tells us whether
`preventDefault` was called; let's return return that to Python:

``` {.javascript}
function __runHandlers(handle, type) {
    // ...
    return evt.cancelled;
}
```

On the Python side, `event` can return that boolean to its handler

``` {.python}
def event(self, type, elt):
    if not elt.handle: return False
    return self.js.evaljs(...)
```

Finally, `event`'s called should check that return value and stop if
it is `True`. So in `handle_click`:

``` {.python}
def handle_click(self, e):
    # ...
    if elt and self.event('click', elt): return
    # ...
```

A similar change happens in `submit_form`:

``` {.python}
def submit_form(self, form):
    # ...
    if self.event("submit", elt): return
```

There's no action associated with the `change` event on input areas,
so we don\'t need to modify that.^[You can't stop the browser from
changing the value: it's already changed when the event handler is run.]

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

Well... Impossible in this browser. But there are browsers that don\'t
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

Our browser has again grown by leaps and bounds: it now runs
JavaScript applications on behalf of websites. Granted, it supports
just four methods from the vast DOM API, but with enough time you
could add all the methods real browsers provide. More importantly, a
web page can now add functionality via clever script, instead of
waiting for a browser developer to add it into the browser itself.

Exercises
=========

-   Add support for the [`children` DOM property][children].
    `Node.children` returns the immediate `ElementNode`[^13] children
    of a node, as an array.
    
[children]: https://developer.mozilla.org/en-US/docs/Web/API/ParentNode/children

[^13]: The DOM method `childNodes` gives access to both elements and
    text. Feel free to implement it if you\'d like...

-   The [method `document.createElement`][createElement] creates a new
    element, which can be attached to the document with the
    [`appendChild`][appendChild] and [`insertBefore`][insertBefore]
    methods on nodes; unlike `innerHTML`, there's no parsing involved.
    Implement all three methods.

[createElement]: https://developer.mozilla.org/en-US/docs/Web/API/Document/createElement

[appendChild]: https://developer.mozilla.org/en-US/docs/Web/API/Node/appendChild

[insertBefore]: https://developer.mozilla.org/en-US/docs/Web/API/Node/insertBefore

-   Try to run an event handler when the user clicks on a link:
    you\'ll find that it\'s actually impossible. That\'s because when
    you click a link, the `elt` returned by `find_element` is the text
    inside the link, not the link element itself. On the web, this
    sort of quirk is handled by *event bubbling*: when an event is
    generated on an element, handlers are run not just on that element
    but also on its ancestors. Handlers can call `stopPropagation` on
    the event object to, well, stop bubbling the event up the tree.
    Implement event bubbling. Make sure `preventDefault` successfully
    prevents clicks on a link from actually following the link.

-   The [`<canvas>` element][canvas-tutorial] is a new addition in
    HTML 5; scripts can draw pictures on the `<canvas>`, much like the
    Tk canvas we\'ve been using to implement our browser. To use the
    `<canvas>`, you first select the element in JavaScript; then call
    `canvas.getContext("2d")` on it, which returns a thing called a
    "context"; and finally call methods like `fillRect` and `fillText`
    on that context to draw on the canvas. Implement the basics of
    `<canvas>`, including `fillRect` and `fillText`. Canvases will
    need a custom layout object that store a list of drawing commands.
    
[canvas-tutorial]: https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial

-   The [`XMLHttpRequest` object][xhr-tutorial] allows scripts to make
    HTTP requests and read the responses. Implement this API,
    including the `addEventListener`, `open`, and `send` methods.
    Beware that `XMLHttpRequest` calls are asynchronous: you need to
    finish executing the script before calling any event listeners on
    an `XMLHttpRequest`.[^sync-xhr-ok] That will require some kind of
    queue of requests you need to make and the handlers to call
    afterwards. Make sure `XMLHttpRequest`s work even if you create
    them inside event handlers.
    
[^sync-xhr-ok]: It is OK for the browser make the request
    synchronously, using our `request` function.

[xhr-tutorial]: https://developer.mozilla.org/en-US/docs/Web/API/XMLHttpRequest/Using_XMLHttpRequest

