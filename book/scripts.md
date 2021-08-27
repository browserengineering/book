---
title: Running Interactive Scripts
chapter: 9
prev: forms
next: security
...

Forms allow our web browser to run dynamic web applications like that guest
book. But form-based web applications require page loads every time you do
anything, and fell out of favor in the early 2000s. What took their place are
JavaScript-enhanced web applications, which can respond to user input and update
pages dynamically, without reloads. Let's add support for that to our toy
web browser.

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

``` {.python expected=False}
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

The implementation here will look much like for CSS. First, we need to
find all of the scripts:

``` {.python replace=nodes/self.nodes}
class Tab:
    def load(self, url, body=None):
        # ...
        scripts = [node.attributes["src"] for node
                   in tree_to_list(nodes, [])
                   if isinstance(node, Element)
                   and node.tag == "script"
                   and "src" in node.attributes]
        # ...
```

This code should come before styling and layout. Next we run all of
the scripts:

``` {.python expected=False}
def load(self, url, body=None):
    # ...
    for script in scripts:
        header, body = request(resolve_url(script, url))
        print("Script returned: ", dukpy.evaljs(body))
    # ...
```

To try this out, create a simple web page with a `script` tag:

``` {.html}
<script src=test.js></script>
```

Then write some super simple script to `test.js`, maybe this:

``` {.javascript}
var x = 2
x + x
```

Point your browser at that page, and you should see:

    Script returned: 4

That's your browser running its first bit of JavaScript!

::: {.quirk}
Our browser is making one major departure here from how real web
browsers work, a departure important enough to call out. In a real web
browser, JavaScript code is run as soon as the browser *parses* the
`<script>` tag, and at that point most of the page is not parsed and may
not even have been received over the network. But that is only the default;
as you can see
[here][scriptElement] (check out the schematic diagram), there are multiple
ways scripts can be set up to load in a real web browser.

Our toy browser only runs scripts after loading and parsing the whole page,
similar to a script in a real browser that uses the [`defer`]
[deferAttr] attribute. I don't think the difference is essential to
understanding how browsers run interactive scripts, and not blocking parsing is
a lot easier to implement.

[scriptElement]: https://html.spec.whatwg.org/multipage/scripting.html#the-script-element
[deferAttr]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/script#attr-defer
:::

Registering functions
=====================

Browsers don't just print the last expression in a script; scripts
call the standard `console.log` function to print. To allow that, we
will need to *register a function* with DukPy, which would allow
Javascript code to run Python functions. There are going to be a lot
of these functions, so to avoid polluting the `Tab` object with many
new methods, let's put this code in a new `JSContext` class:

``` {.python replace=__init__(self)/__init__(self%2c%20tab)}
class JSContext:
    def __init__(self):
        self.interp = dukpy.JSInterpreter()

    def run(self, code):
        self.interp.evaljs(code)
```

This `JSInterpreter` object stores the values of all the JavaScript
variables and lets us run multiple JavaScript snippets while sharing
the same variables.

We create a `JSContext` while loading the page:

``` {.python replace=JSContext()/JSContext(self)}
class Tab:
    def load(self, url, body=None):
        # ...
        self.js = JSContext()
        for script in scripts:
            # ...
```

Let's start registering functions. The JavaScript function
`console.log` corresponds to the Python `print` function.[^5] We can
register this correspondence using `export_function`:

[^5]: If you're using Python 2, for some reason, you'll need to write
    a little wrapper function around `print` instead.

``` {.python replace=__init__(self)/__init__(self%2c%20tab)}
class JSContext:
    def __init__(self):
        # ...
        self.interp.export_function("log", print)
```

Then, in JavaScript, Dukpy provides a `call_python` function that you
can use to call `print`:

``` {.javascript}
call_python("log", "Hi from JS")
```

When this call happens, Dukpy converts the JavaScript string `"Hi from
JS"` into a Python string,^[This conversion also works on numbers,
string, and booleans, but I wouldn't try it with other objects.] and
then passes that Python string to the `print` function we registered.

Since we ultimately want JavaScript to call a `console.log` function,
not a `call_python` function, we need to define a `console` object
and then give it a `log` property. We can do that *in JavaScript*:

``` {.javascript}
console = { log: function(x) { call_python("log", x); } }
```

In case you're not too familiar with JavaScript,[^brush-up] this
defines a variable called `console`, whose value is an object literal
with the property `log`, whose value is the function you see defined
there.

[^brush-up]: Now's a good time to [brush up][mdn-js]---this chapter
    has a ton of JavaScript!
[mdn-js]: https://developer.mozilla.org/en-US/docs/Learn/JavaScript/First_steps/A_first_splash

Taking a step back, when we run JavaScript in our browser, we're
mixing: C code, which implements the JavaScript interpreter; Python
code, which handles certain JavaScript functions; and JavaScript code,
which wraps the Python API to look more like the JavaScript one. We
can call that JavaScript code our "JavaScript runtime"; we run it
before we run any user code, so let's stick it in a `runtime.js`
file that's run when the `JSContext` is created:

``` {.python replace=runtime/runtime9,__init__(self)/__init__(self%2c%20tab)}
class JSContext:
    def __init__(self):
        # ...
        with open("runtime.js") as f:
            self.interp.evaljs(f.read())
```

Now you should be able to run the script `console.log("Hi from JS!")`
and see output in your terminal. Do test that you can now call
`console.log`, even multiple times, from a script.

As a side benefit of using one `JSContext` for all scripts, it is now
possible to run two scripts and have one of them define a variable
that the other uses, say on a page like:

``` {.html}
<script src=a.js></script>
<script src=b.js></script>
```

where `a.js` is "`var x = 2;`" and `b.js` is "`console.log(x + x)`".
In real web browsers, that's important since one script might define
library functions that another script wants to call.

::: {.further}
What happens if a script runs for a long time, or even has an infinite loop in
it? In this situation, the browser has no choice but to "lock up" and become
completely unresponsive to the user, at least when they try to interact with
that particular tab via anything that requires DOM or JavaScript changes. The
reason is that the interaction model of the web
is for the most part single-threaded, and JavaScript has task-based,
[run-to-completion scheduling][rtc]. Once you allow a Turing-complete language
in your browser, all bets are off!

Chapter 13 will have more to say about ways browsers deal with potentially
slow JavaScript.
:::

[rtc]: https://en.wikipedia.org/wiki/Run_to_completion_scheduling

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

``` {.python indent=8}
try:
    print("Script returned: ", self.js.run(body))
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

``` {.python expected=False}
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
    // ...
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

``` {.python replace=__init__(self)/__init__(self%2c%20tab)}
class JSContext:
    def __init__(self):
        # ...
        self.interp.export_function("querySelectorAll",
            self.querySelectorAll)
        # ...
```

In JavaScript, `querySelectorAll` is a method on the `document`
object, so define one in the JavaScript runtime:

``` {.javascript}
document = { querySelectorAll: function(s) {
    return call_python("querySelectorAll", s);
}}
```

The `querySelectorAll` handler will first parse the selector, then
find and return the matching elements. To parse just the selector,
I'll call into the `CSSParser`'s `selector` method:

``` {.python}
class JSContext:
    def querySelectorAll(self, selector_text):
        selector = CSSParser(selector_text).selector()
```

If you pass `querySelectorAll` an invalid selector,
`CSSParser.selector` will throw an error and the registered function
crashes. At that point DukPy turns that Python-side exception into a
JavaScript-side exception in the web script we are running, which can
catch it or do something else.

Next we need to find and return all matching elements. To do that, we
need the `JSContext` to have access to the `Tab`, specifically to the
`nodes` field. So let's pass in the `Tab` object when creating a
`JSContext`:

``` {.python}
class JSContext:
    def __init__(self, tab):
        self.tab = tab
        # ...
```

Now inside `querySelectorAll` we can return all matching nodes:

``` {.python expected=False}
def querySelectorAll(self, selector_text):
    # ...
    nodes = [node for node
             in tree_to_list(self.tab.nodes, [])
             if selector.matches(node)]
    return nodes
```

`querySelectorAll` looks complete, but if you try calling the function
from JavaScript, you'll see an error like this:[^7]

``` {.example}
_dukpy.JSRuntimeError: EvalError:
Error while calling Python Function:
TypeError('Object of type ElementNode is not JSON serializable')
```

[^7]: Yes, that's a confusing error message. Is it a `JSRuntimeError`,
    an `EvalError`, or a `TypeError`?

What DukPy is trying to tell you is that it has no idea what to do
with the `ElementNode` objects that `querySelectorAll` is returning,
since that class only exists in Python, not JavaScript. We can't pass
Python objects to JavaScript!

Python objects need to stay on the Python side of the browser, so
JavaScript code will need to refer to them by some kind of reference.
I'll use simple numeric identifier, which I'll call a *handle*.[^8]

[^8]: Handles are the browser analogs of file descriptors, which give
    user-level applications a handle to kernel data structures.

We'll need to keep track of the handle to node mapping. Let's create a
`node_to_handle` data structure to map nodes to handles, and a
`handle_to_node` map that goes the other way:

``` {.python}
class JSContext:
    def __init__(self, tab):
        # ...
        self.node_to_handle = {}
        self.handle_to_node = {}
        # ...
```

Then, I'll allocate new handles for each node being returned into
JavaScript:

``` {.python}
def querySelectorAll(self, selector_text):
    # ...
    return [self.get_handle(node) for node in nodes]
```

The `get_handle` function should create a new handle if one doesn't
exist yet:[^id-elt]

[^id-elt]: `node_to_handle` uses `id(elt)` instead of `elt` as its key
    because Python objects can't be used as hash keys by default.

``` {.python}
class JSContext:
    def get_handle(self, elt):
        if elt not in self.node_to_handle:
            handle = len(self.node_to_handle)
            self.node_to_handle[id(elt)] = handle
            self.handle_to_node[handle] = elt
        else:
            handle = self.node_to_handle[elt]
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
class JSContext:
    def getAttribute(self, handle, attr):
        elt = self.handle_to_node[handle]
        return elt.attributes.get(attr, None)
```

We can register this function as `getAttribute` and run a script like
this:[^9]

``` {.javascript}
scripts = document.querySelectorAll("script")
for (var i = 0; i < scripts.length; i++) {
    console.log(call_python("getAttribute",
        scripts[i].handle, "src"));
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

``` {.python expected=False}
class Tab:
    def click(self, x, y):
        # ...
        elt = objs[-1].node
        if elt:
            self.js.dispatch_event("click", elt)
        # ...
```

Second, before updating input area values:

``` {.python expected=False}
class Tab:
    def keypress(self, char):
        if self.focus:
            self.js.dispatch_event("keydown", self.focus)
            self.focus.attributes["value"] += char
```

And finally, when submitting forms but before actually sending the
request to the server:

``` {.python expected=False}
def submit_form(self, elt):
    self.js.dispatch_event("submit", elt)
    # ...
```

So far so good---but what should the `dispatch_event` method do? Well,
it needs to run the handlers set up by `addEventListener`, so those
need to be stored somewhere. Since those handlers are JavaScript
functions, we need to keep that data on the JavaScript side, in an
variable in the runtime. I'll call that variable `LISTENERS`; we'll
use it to look up handles and event types, so let's make it map handles
to a dictionary that maps event types to a list of handlers:

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

To run a handler, we need to look up the type and handle in the
`LISTENERS` array, like this:

``` {.javascript}
function __runListeners(handle, type) {
    var list = (LISTENERS[handle] && LISTENERS[handle][type]) || [];
    for (var i = 0; i < list.length; i++) {
        list[i].call(new Node(handle));
    }
}
```

Note that `__runListeners` uses JavaScript's `call` method on
functions, which allows it to set the value of `this` inside that
function. As is standard in JavaScript, I'm setting it to the node
that the event was generated on.

When an event happens in the browser, it can call `__runListeners` from
Python:

``` {.python expected=False}
class JSContext:
    def dispatch_event(self, type, elt):
        code = "__runListeners(dukpy.type, dukpy.handle)"
        handle = self.node_to_handle.get(elt, -1)
        self.interp.evaljs(code, type=type, handle=handle)
```

Here the `code` variable contains a string of JavaScript code, code
that uses the `dukpy` object to receive a string and integer object
from Python. So when `dispatch_event` is called on an element, the
browser generates a handle for that element and calls `__runListeners`
to run all of its event listeners.

With all this event-handling machinery in place, we can run the
character count every time an input area changes:

``` {.javascript}
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
that actually changed, as set up by `__runListeners`.

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

::: {.further}
`Node` objects in the DOM are now both JavaScript objects and part
of the document tree. They can have JavaScript object *properties*, and they
can have node *attributes*. It's easy to confuse one for the other, because
they are so similar in concept. To make matters worse, there are a number of
special attributes that [*reflect*][reflection] from property to attribute
automatically, and vice-versa. The [`id` attribute][idAttr] is one example.
Consider the following code:
``` {.javascript}
node.id = "someId";
```
This will cause the `id` attribute on the node to change (just as if the
[setAttribute] method had been called), in addition to settting the property.
Likewise, changing the attribute will reflect back on the property.

On the other hand, this code:
``` {.javascript}
node.otherProperty = "something";
```
will not reflect to the attribute, because `otherProperty` is not special.
Most built-in attributes reflect, because it's very convenient when writing
JavaScript not to have to write `setAttribute` and `getAttribute` all over the
place.
:::

[idAttr]: https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/id
[reflection]: https://html.spec.whatwg.org/multipage/common-dom-interfaces.html#reflecting-content-attributes-in-idl-attributes
[setAttribute]: https://developer.mozilla.org/en-US/docs/Web/API/Element/setAttribute

Let's implement this, starting on the JavaScript side. JavaScript has
the obscure `Object.defineProperty` function to define setters:

``` {.javascript}
Object.defineProperty(Node.prototype, 'innerHTML', {
    set: function(s) {
        call_python("innerHTML", this.handle, s.toString());
    }
});
```

In `innerHTML`, we'll need to parse the HTML string. That turns out to
be trickier than you'd think, because our browser's HTML parser is
intended to parse whole HTML documents, not document fragments like
this. As an expedient but incorrect hack,[^hack] I'll just wrap the
HTML string in an `html` and `body` element:

[^hack]: Real browsers follow HTML's standard parsing algorithm for
    HTML fragments.

``` {.python indent=4}
def innerHTML(self, handle, s):
    doc = HTMLParser("<html><body>" + s + "</body></html>").parse()
    new_nodes = doc.children[0].children
```

Don't forget to register the `innerHTML` function: Note that we
extract all children of the `body` element, because an `innerHTML`
call can create multiple nodes at a time. These new nodes must now be
made children of the element `innerHTML` was called on:

``` {.python indent=4}
def innerHTML(self, handle, s):
    # ...
    elt = self.handle_to_node[handle]
    elt.children = new_nodes
    for child in elt.children:
        child.parent = elt
```

We need to update the parent pointers of those parsed child nodes
because until we do that, they point to the fake `body` element that
we added to aid parsing.

It might look like we're done---but try this out and you'll realize
that nothing happens when a script calls `innerHTML`. That's because,
while we have changed the HTML tree, we haven't regenerated the layout
tree or the display list, so the browser is still showing the old page.

Right now, the layout tree and display list are computed in `load`,
but we don't want to reload the whole page; we just want to redo the
styling, layout, and painting phases. So let's extract these styling,
layout, and painting phases into a new `Tab` method, `render`:

``` {.python}
class Tab:
    def load(self, url, body=None):
        # ...
        self.render()

    def render(self):
        style(self.nodes, sorted(self.rules, key=cascade_priority))
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        self.document.paint(self.display_list)
```

For this code to work, you'll also need to change `nodes` and `rules`
from local variables in the `load` method to new fields on a `Tab`.
Note that styling moved from `load` to `render`, but downloading the
stylesheets didn't. That's because `innerHTML` created new elements
that have to be styled, but we don't need to re-download the styles to
do that; we just need to re-apply the styles we already have.

Now, whenever the page changes, we can lay it out again by calling
`render`:

``` {.python}
class JSContext:
    def innerHTML(self, handle, s):
        # ...
        self.tab.render()
```

JavaScript can now modify the web page!

Let's try this out this in our guest book server. I don't want people
writing long rants in my guest book, so I'm going to put a
100-character limit on guest book entries.

First, let's add a new paragraph `<p id=errors></p>` after the guest
book form. Initially this paragraph will be empty, but we'll write an
error message into it if the paragraph gets too long.

Next, let's add a script to the page. Switch to the server codebase
and add a new line of HTML to the guest book page:

``` {.python file=server}
def show_comments():
    # ...
    out += "<script src=/comment.js></script>"
    # ...
```

Now the browser will request `comment.js`, so our server needs to
*serve* that JavaScript file:

``` {.python file=server}
def do_request(method, url, headers, body):
    # ...
    elif method == "GET" and url == "/comments.js":
        with open("comment.js") as f:
            return "200 OK", f.read()
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
input.addEventListener("keydown", lengthCheck);
```

Try it out: write a long comment and you should see the page warning
you that the comment is too long. By the way, we might want to make it
stand out more, so let's go ahead and add another URL to our web
server, `/comment.css`, with the contents:

``` {.css}
#errors { font-weight: bold; color: red; }
```

But even though we tell the user that their comment is too long the
user can submit the guest book entry anyway. Oops! Let's fix that.

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

Note the `do_default` field, to record whether `preventDefault` has
been called. We pass one of these event objects to handlers:

``` {.javascript}
function __runListeners(handle, type) {
    // ...
    var evt = new Event(type);
    for (var i = 0; i < list.length; i++) {
        list[i].call(new Node(handle), evt);
    }
    // ...
}
```

After calling the handlers, `evt.do_default` tells us whether
`preventDefault` was called; let's return that to Python:

``` {.javascript}
function __runListeners(handle, type) {
    // ...
    return evt.do_default;
}
```

On the Python side, `event` can return that boolean to its handler:

``` {.python}
class JSContext:
    def dispatch_event(self, type, elt):
        # ...
        do_default = self.interp.evaljs(code, type=type, handle=handle)
        return not do_default
```

Finally, whatever event handler runs `dispatch_event` should check
that return value and stop if it is `True`. So in `click`:

``` {.python}
class Tab:
    def click(self, x, y):
        # ...
        if elt and self.js.dispatch_event("click", elt): return
        # ...
```

And also in `submit_form`:

``` {.python}
class Tab:
    def submit_form(self, elt):
        if self.js.dispatch_event("submit", elt): return
```

And in `keypress`:

``` {.python}
class Tab:
    def keypress(self, char):
        if self.focus:
            if self.js.dispatch_event("keydown", self.focus): return
```

With this change, `comment.js` can use a global variable to track
whether or not submission is allowed, and then when submission is
attempted it can cancel that action.

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

``` {.python file=server}
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

A web page can now add functionality via a clever script, instead of waiting for
a browser developer to add it into the browser itself. And as a side-benefit,
earn the title of "web application" instead of just web page.

Note that these applications are only *enhanced* by JavaScript---they still use
HTML, CSS, form elements and all the other features we've built so far into our
browser. This is in contrast to the recently-departed
[Adobe Flash], and before that [Java Applets][javaApplets], which are
self-contained plug-ins that handle all of input and rendering with their own
technologies.

Instead of that approach, JavaScript builds on top of HTML and CSS, allowing web
applications to go beyond what is built into the browser via custom code. In
this way, JavaScript is conceptually similar in some ways to a
[browser extension][browserExtension], as it enhances the experience of using a
web page. Ideally, web pages should be written so that they work correctly
without JavaScript, but work better with it---this is the concept of
[progressive enhancement][progEnhancement]. (In addition to user experience
benefits, progressive enhancement makes life a lot easier for users of
JavaScript and browser engineers---no need to re-invent HTML and CSS!)

[Adobe Flash]: https://www.adobe.com/products/flashplayer/end-of-life.html
[javaApplets]: https://en.wikipedia.org/wiki/Java_applet

[browserExtension]: https://en.wikipedia.org/wiki/Browser_extension
[progEnhancement]: https://en.wikipedia.org/wiki/Progressive_enhancement

::: {.further}
JavaScript first appeared in 1995, as part of Netscape Navigator. Its name
was chosen to indicate a similarity to the [Java][javaLang]
language, and the syntax is Java-esque for that reason. However, under the
surface JavaScript is a much more dynamic language than Java, as is
appropriate given its role as a progressive enhancement mechanism for the web.
You can learn more about the interesting history of JavaScript
[here][historyJS].

[javaLang]: https://en.wikipedia.org/wiki/Java_(programming_language)
[historyJS]: https://auth0.com/blog/a-brief-history-of-javascript/
:::



Exercises
=========

*Node.children*: Add support for the [`children`][children] property on
JavaScript `Node`s. `Node.children` returns the immediate
`ElementNode` children of a node, as an array. `TextNode` children are
not included.[^13]
    
[children]: https://developer.mozilla.org/en-US/docs/Web/API/ParentNode/children

[^13]: The DOM method `childNodes` gives access to both elements and
    text. Feel free to implement it if you'd like...

*createElement*: The [`document.createElement`][createElement] method
creates a new element, which can be *attached* to the document with the
[`appendChild`][appendChild] and [`insertBefore`][insertBefore]
methods on `Node`s; unlike `innerHTML`, there's no parsing involved.
Implement all three methods.

[createElement]: https://developer.mozilla.org/en-US/docs/Web/API/Document/createElement

[appendChild]: https://developer.mozilla.org/en-US/docs/Web/API/Node/appendChild

[insertBefore]: https://developer.mozilla.org/en-US/docs/Web/API/Node/insertBefore

*removeChild*: The [`removeChild`][removeChild] method on `Node`s detaches the
provided child and returns it, bringing that child---and its subtree---back
into an *unnattached* state. (It can then be *reattached* elsewhere, or
deleted.) Implement this method. It's more challenging to implement this one,
because you'll need to also remove the subtree from the Python side, and
delete any layout objects associated with it.

[removeChild]: https://developer.mozilla.org/en-US/docs/Web/API/Node/removeChild

*IDs*: When an HTML element on a page has an `id` attribute, a
variable is predefined in the JavaScript context refering to that
element.[^standard] So, if a page has a `<div id="foo"></div>`, then the variable
`foo` refers to that node. Implement this in your browser. Make sure
to handle the case of nodes being added and removed (such as with
`innerHTML`).

[^standard]: This is [standard][html5-varnames] behavior.

[html5-varnames]: http://www.whatwg.org/specs/web-apps/current-work/#named-access-on-the-window-object

*Event Bubbling*: Try to run an event handler when the user clicks on a link:
 you'll find that it's actually impossible. That's because when you click a
 link, the `elt` returned by `find_element` is the text inside the link, not
 the link element itself. On the web, this sort of quirk is handled by
 [*event bubbling*][eventBubbling]: when an event is generated on an element,
 handlers are run not just on that element but also on its ancestors.
 Implement event bubbling, and make sure JavaScript can attach to clicks on
 links. Handlers can call `stopPropagation` on the event object to, well, stop
 bubbling the event up the tree. Make sure `preventDefault` successfully
 prevents clicks on a link from actually following the link.

 [eventBubbling]: https://developer.mozilla.org/en-US/docs/Learn/JavaScript/Building_blocks/Events#event_bubbling_and_capture

*Canvas*: The [`<canvas>`][canvas-tutorial] element allows scripts to draw
 content on a `<canvas>` element with an API very similar to the
 `tkinter.Canvas` API we've been using to implement our browser. To drawe to the
 `<canvas>`, you first select the element in JavaScript; then call
 `canvas.getContext("2d")` on it, which returns a thing called a
"context"; and finally call methods like `fillRect` and `fillText` on
that context to draw on the canvas. Implement the basics of
`<canvas>`, including `fillRect` and `fillText`. Canvases will need a
custom layout object that store a list of drawing commands, and then inject
them into the display list when `paint` is called.

[canvas-tutorial]: https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial

*HTTP Requests*: The [`XMLHttpRequest` object][xhr-tutorial] allows scripts to
 make HTTP requests and read the responses.  Implement this API, including the
 `addEventListener`, `open`, and `send` methods. Beware that `XMLHttpRequest`
 calls are asynchronous:[^sync-xhr] you need to finish executing the script
 before calling any event listeners on an `XMLHttpRequest`.[^sync-xhr-ok] That
 will require some kind of queue of requests you need to make and the handlers
 to call afterwards. Make sure `XMLHttpRequest`s work even if you create them
 inside event handlers.
    
[^sync-xhr]: Technically, `XMLHttpRequest` supports synchronous requests as an
option in its API, and this is supported in all browsers, though
[strongly discouraged](https://xhr.spec.whatwg.org/#sync-warning) for web
developers to actually use. It's discouraged because it "freezes" the website
completely while waiting for the response, in the same way form submissions do.
However, it's even worse, than that: because of the single-threaded nature of
the web, other browser tabs might also be frozen at the same time if they share
this thread.

[^sync-xhr-ok]: It's ok for you to cut corners and implement this by making the
browser make the request synchronously, using our `request` function. But the
whole script should finish running before calling the callback.

[xhr-tutorial]: https://developer.mozilla.org/en-US/docs/Web/API/XMLHttpRequest/Using_XMLHttpRequest

*Inline styling*: The `style` property allows JavaScript to set and get inline
 styles (ones set in the `style` attribute). An inline style can be modified by
 setting properties on the object returned by `node.style`. These properties
 have the same name as the corresponding CSS property, except that dashes are
 replaced by camel-casing. For example `node.style.backgroundColor = "blue"`
 will change the `background-color` to blue. Implement this behavior. Note that
 these changes are supposed to reflect^[See the go-further block about
 reflection earlier in this chapter.] in the [`style` attribute][styleAttr];
 you can try implementing that also if you wish. Another add-on can be to
 implement the behavior of *reading* this attribute as well---`node.style`
 returns a [`CSSStyleDeclaration`][cssstyle] object.

[cssstyle]: https://developer.mozilla.org/en-US/docs/Web/API/CSSStyleDeclaration
[styleAttr]: https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/style

*Serializing HTML*: Reading from the [`element.innerHTML`][innerHTML] property
 in JavaScript returns a string with a serialized representation of the DOM
 subtree below `element` (but not including it). `element.outerHTML` returns a
 string including `element`. Here is an example:

``` {.javascript} 
    element.innerHTML = '<span id=foo>Chris was here</span>';
    element.id = 'bar';
    // Prints "<span id=bar>Chris was here</span>":
    console.log(element.innerHTML);
```

 Implement object getters for `innerHTML` and `outerHTML`.

[innerHTML]: https://developer.mozilla.org/en-US/docs/Web/API/Element/innerHTML
