---
title: Running Interactive Scripts
chapter: 9
prev: forms
next: security
...

But form-based web applications, like [last chapter's guest
book](forms.md), reload the page every time the user does anything,
and fell out of favor in the early 2000s. What took their place are
JavaScript-enhanced web applications, which can respond to user input
and update pages dynamically, without reloads. Let's add support for
that to our toy web browser.

Installing DukPy
================

Actually writing a JavaScript interpreter is beyond the scope of this
book,^[But check out a book on programming language implementation
if it sounds interesting!] so this chapter uses the `dukpy` library
for executing JavaScript.

[DukPy](https://github.com/amol-/dukpy) is a Python library that wraps
a JavaScript interpreter called [Duktape](https://duktape.org). The
most famous JavaScript interpreters are those used in browsers:
TraceMonkey (Firefox), JavaScriptCore (Safari), and V8 (Chrome).
Unlike those implementations, which are extremely fast but also
extremely complex, Duktape aims to be simple and extensible, and is
usually used as a simple scripting language used inside a larger C or
C++ project.[^1]

[^1]: For examples, games are usually written in C or C++ to implement
    high-speed graphics, but use a simpler language to implement the
    actual plot of the game.

Like any JavaScript engine, DukPy not only executes JavaScript code,
but also allows JavaScript code to call Python functions that have
been *exported* to it. We'll be using this feature to allow JavaScript
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
need to skip this chapter, though you could try binding directly to
the `duktape` library that `dukpy` uses.
:::

To test whether you installed DukPy correctly, execute this:

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

::: {.quirk}
Note to JS experts: Dukpy does not implement newer JS syntax like
`let` and `const` or arrow functions. You'll need to use old-school
JavaScript from the turn of the centry.
:::


Running JavaScript code
=======================

The test code above shows you how to run JavaScript code with DukPy:
you just call `evaljs`! With this newfound knowledge, let's modify
our web browser to run JavaScript code.

On the web, JavaScript is found in `<script>` tags. Normally, a
`<script>` tag has a `src` attribute with a relative URL that points
to a JavaScript file, much like with CSS files. A `<script>` tag could
also contain JavaScript source code between the start and end tag, but
we won't implement that.^[It's a challenge for parsing, since it's
hard to avoid less than and greater than signs in JavaScript code.]

Finding and downloading those scripts is similar to what we did for
CSS. First, we need to find all of the scripts:

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

Next we run all of the scripts:

``` {.python expected=False}
def load(self, url, body=None):
    # ...
    for script in scripts:
        header, body = request(resolve_url(script, url))
        print("Script returned: ", dukpy.evaljs(body))
    # ...
```

This code should come before styling and layout. To try this out,
create a simple web page with a `script` tag:

``` {.html}
<script src=test.js></script>
```

Then write a super simple script to `test.js`, maybe this:

``` {.javascript}
var x = 2
x + x
```

Point your browser at that page, and you should see:

    Script returned: 4

That's your browser running its first bit of JavaScript!

::: {.further}
Actually, real browsers run JavaScript code as soon as the browser
*parses* the `<script>` tag, not after the whole page is parsed. Or,
at least, that is the default; there are [many options][scriptElement].
What our toy browser does is what a real browser does when the the
[`defer`][deferAttr] attribute is set. What browsers do by default is
much trickier to [implement efficiently][speculative].
:::

[scriptElement]: https://html.spec.whatwg.org/multipage/scripting.html#the-script-element
[deferAttr]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/script#attr-defer
[speculative]: https://developer.mozilla.org/en-US/docs/Glossary/speculative_parsing

Exporting functions
=====================

Right now our browser just prints the last expression in a script; but
in a real browser scripts must call the `console.log` function to
print. To support that, we will need to *export a function* from
Python into JavaScript. We'll be exporting a lot of functions, so to
avoid polluting the `Tab` object with many new methods, let's put this
code in a new `JSContext` class:

``` {.python replace=__init__(self)/__init__(self%2c%20tab)}
class JSContext:
    def __init__(self):
        self.interp = dukpy.JSInterpreter()

    def run(self, code):
        return self.interp.evaljs(code)
```

DukPy's `JSInterpreter` object stores the values of all the JavaScript
variables and lets us run multiple JavaScript snippets while sharing
state like variable values between them.

We create a `JSContext` while loading the page:

``` {.python replace=JSContext()/JSContext(self)}
class Tab:
    def load(self, url, body=None):
        # ...
        self.js = JSContext()
        for script in scripts:
            # ...
```

As a side benefit of using one `JSContext` for all scripts, it is now
possible to run two scripts and have one of them define a variable
that the other uses, say on a page like this:

``` {.html}
<script src=a.js></script>
<script src=b.js></script>
```

Suppose `a.js` is "`var x = 2;`" and `b.js` is "`console.log(x + x)`";
the variable `x` is set in `a.js` but used in `b.js`. In real web
browsers, that's important since one script might define library
functions that another script wants to call.

Let's start exporting functions. The JavaScript function `console.log`
corresponds to the Python `print` function.[^5] We can leverage this
correspondence using `export_function`:

[^5]: If you're using Python 2, for some reason, you'll need to write
    a little wrapper function around `print` instead.

``` {.python replace=__init__(self)/__init__(self%2c%20tab)}
class JSContext:
    def __init__(self):
        # ...
        self.interp.export_function("log", print)
```

We can call an exported function from JavaScript using Dukpy's
`call_python` function. For example:

``` {.javascript}
call_python("log", "Hi from JS")
```

When this JavaScript code runs, Dukpy converts the JavaScript string
`"Hi from JS"` into a Python string,^[This conversion also works on
numbers, string, and booleans, but I wouldn't try it with other
objects.] and then passes that Python string to the `print` function
we exported. Then `print` prints that string.

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
code, which implements certain JavaScript functions; and JavaScript
code, which wraps the Python API to look more like the JavaScript one.
We can call that JavaScript code our "JavaScript runtime"; we run it
before we run any user code, so let's stick it in a `runtime.js` file
and execute it when the `JSContext` is created, before we run any user
code:

``` {.python replace=runtime/runtime9,__init__(self)/__init__(self%2c%20tab)}
class JSContext:
    def __init__(self):
        # ...
        with open("runtime.js") as f:
            self.interp.evaljs(f.read())
```

Now you should be able to put `console.log("Hi from JS!")` into a
JavaScript file, run it from your browser, and see output in your
terminal. You should also be able to call `console.log` multiple
times.

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

Crashes in JavaScript code are frustrating to debug. You can cause a
crash by writing the wrong code, or by explicitly raising an
exception, like so:

``` {.javascript}
throw Error("bad");
```

When a web page runs some JavaScript that crashes, the browser should
ignore the crash. Web pages shouldn't be able to crash our browser!
You can implement that like this:

``` {.python indent=12}
try:
    print("Script returned:", self.js.run(body))
except dukpy.JSRuntimeError as e:
    print("Script", script, "crashed", e)
```

But as you go through this chapter, you'll also run into another type
of crash: crashes in the JavaScript runtime. We can't ignore those,
because we want our runtime to work. Debugging these crashes is a
bear: by default Dukpy won't show a backtrace, and if the runtime code
calls into a exported function that crashes it gets even more
confusing.

Here's a few tips to help with these crashes. First, if you get a
crash inside some JavaScript function, wrap the body of the function
like this:

``` {.javascript expected=False}
function foo() {
    try {
        // ...
    } catch(e) {
        console.log("Crash in function foo()", e.stack);
        throw e;
    }
}
```

This code catches all exceptions and prints a stack trace before
re-raising them. If you instead are getting crashes inside an exported
function you will need to wrap that function, on the Python side:

``` {.python expected=False}
class JSContext:
    def foo(self, arg):
        try:
            # ...
        except:
            import traceback
            traceback.print_exc()
            raise
```

Debugging these issues is not easy, because all these calls between
Python and JS get pretty complicated. *Because* these bugs are hard,
it's worth approaching debugging systematically and gather a lot of
information before attempting a fix.

Returning handles
=================

So far, JavaScript evaluation is fun but useless, because JavaScript
can't make any kinds of modifications to the page itself. Why even run
JavaScript if it can't do anything besides print? (Who looks at a
browser's console output?) We need to allow JavaScript to modify the
page.

The JavaScript functions that manipulate a web page are collectively
called the DOM API, for "Document Object Model". The DOM API is big,
and it keeps getting bigger, so we won't implementing all, or even
most, of it. But a few core functions show the range of the full API:

-   `querySelectorAll` returns all the elements matching a selector;
-   `getAttribute` returns an element's value for some attribute; and
-   `innerHTML` replaces the contents of an element with new HTML.

We'll implement simplified versions of these APIs.[^simplified]

[^simplified]: The simplifications will be minor. `querySelectorAll`
will return an array, not this thing called a `NodeList`; `innerHTML`
will only write the HTML contents of an element, and won't allow
reading those contents. The goal is to demonstrate how the JS-browser
communication happens.

Let's start with `querySelectorAll`. First, export a function:

``` {.python replace=__init__(self)/__init__(self%2c%20tab)}
class JSContext:
    def __init__(self):
        # ...
        self.interp.export_function("querySelectorAll",
            self.querySelectorAll)
        # ...
```

In JavaScript, `querySelectorAll` is a method on the `document`
object, which we need to define in the JavaScript runtime:

``` {.javascript}
document = { querySelectorAll: function(s) {
    return call_python("querySelectorAll", s);
}}
```

On the Python side, `querySelectorAll` has first parse the selector
and then find and return the matching elements.

To parse just the selector, I'll call into the `CSSParser`'s
`selector` method:

``` {.python}
class JSContext:
    def querySelectorAll(self, selector_text):
        selector = CSSParser(selector_text).selector()
```

If you pass `querySelectorAll` an invalid selector, the `selector`
call will throw an error, and DukPy will convert that Python-side
exception into a JavaScript-side exception in the web script we are
running, which can catch it or do something else.

Next we need to find and return all matching elements. To do that, we
need the `JSContext` to have access to the `Tab`, specifically to the
`nodes` field. So let's pass in the `Tab` when creating a `JSContext`:

``` {.python}
class JSContext:
    def __init__(self, tab):
        self.tab = tab
        # ...

class Tab:
    def load(self, url, body=None):
        # ...
        self.js = JSContext(self)
        # ...
```

Now `querySelectorAll` will find all nodes matching the selector:

``` {.python}
def querySelectorAll(self, selector_text):
    # ...
    nodes = [node for node
             in tree_to_list(self.tab.nodes, [])
             if selector.matches(node)]
```

Finally we need to return those nodes back to JavaScript. You might
try something like this:

``` {.python expected=False}
def querySelectorAll(self, selector_text):
    # ...
    return nodes
```

However, this throws an error:[^7]

    _dukpy.JSRuntimeError: EvalError:
    Error while calling Python Function:
    TypeError('Object of type Element is not JSON serializable')

[^7]: Yes, that's a confusing error message. Is it a `JSRuntimeError`,
    an `EvalError`, or a `TypeError`?

What DukPy is trying to tell you is that it has no idea what to do
with the `Element` objects in the `nodes` array that
`querySelectorAll` is returning. After all, the `Element` class only
exists in Python, not JavaScript!

Python objects need to stay on the Python side of the browser, so
JavaScript code will need to refer to them via some kind of
indirection. I'll use simple numeric identifier, which I'll call a
*handle*.[^8]

[^8]: Note the similarity to file descriptors, which give user-level
    applications a handle to kernel data structures.

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

Now, instead of the `querySelectorAll` handler returning `nodes`
directly, it can allocate handles for each node and return those
handles instead:

``` {.python}
def querySelectorAll(self, selector_text):
    # ...
    return [self.get_handle(node) for node in nodes]
```

The `get_handle` function should create a new handle if one doesn't
exist yet:[^id-elt]

``` {.python}
class JSContext:
    def get_handle(self, elt):
        if elt not in self.node_to_handle:
            handle = len(self.node_to_handle)
            self.node_to_handle[elt] = handle
            self.handle_to_node[handle] = elt
        else:
            handle = self.node_to_handle[elt]
        return handle
```

So now the `querySelectorAll` handler returns something like `[1, 3,
4, 7]`, with each number being a handle for an element, which DukPy
can easily convert into JavaScript objects without issue.


Wrapping handles
================

Now of course, on the JavaScript side, `querySelectorAll` shouldn't
return a bunch of numbers: it should return a list of `Node`
objects.[^nodelist] So let's define a `Node` object in our runtime
that wraps a handle:[^10]

[^nodelist]: In a real browser, `querySelectorAll` actually returns a
    [`NodeList` object][nodelist-mdn], for kind-of abstruse reasons
    that aren't relevant here.
    
[nodelist-mdn]: https://developer.mozilla.org/en-US/docs/Web/API/NodeList

[^10]: If your JavaScript is rusty, you might want to read up on the
    crazy way you define classes in JavaScript. Modern JavaScript also
    provides the `class` syntax, which is more sensible, but it's not
    supported in DukPy.

``` {.javascript}
function Node(handle) { this.handle = handle; }
```

We create these `Node` objects in `querySelectorAll`'s wrapper:[^11]

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

Now that we've got some `Node`s, what can we do with them?

One simple DOM method is `getAttribute`, a method on `Node` objects
that lets you get the value of HTML attributes. Implementing
`getAttribute` means solving the opposite problem to
`querySelectorAll`: taking `Node` objects on the JavaScript side, and
shipping them over to Python.

The solution is similar to `querySelectorAll`: instead of shipping the
`Node` object itself, we send over its handle:

``` {.javascript}
Node.prototype.getAttribute = function(attr) {
    return call_python("getAttribute", this.handle, attr);
}
```

On the Python side, the `getAttribute` function must take two
arguments, a handle and an attribute:

``` {.python}
class JSContext:
    def getAttribute(self, handle, attr):
        elt = self.handle_to_node[handle]
        return elt.attributes.get(attr, None)
```

Note that if the attribute is not assigned, the `get` method will
return `None`, which DukPy will translate to JavaScript's `null`.
Don't forget to export this function as `getAttribute`.

You should now be able to run a script like this:

``` {.javascript}
scripts = document.querySelectorAll("script")
for (var i = 0; i < scripts.length; i++) {
    console.log(call_python("getAttribute",
        scripts[i].handle, "src"));
}
```

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

Ideally, we'd update the character count every time the user types
into an input box.

::: {.further}
`Node` objects in the DOM are now both JavaScript objects and part of
the document tree. They can have JavaScript object *properties*, and
they can have node *attributes*. It's easy to confuse one for the
other, because they are so similar in concept. To make matters worse,
there are a number of special attributes that [*reflect*][reflection]
from property to attribute automatically, and vice-versa. The [`id`
attribute][idAttr] is one example. Consider the following code: ```
{.javascript} node.id = "someId"; ``` This will cause the `id`
attribute on the node to change (just as if the [setAttribute] method
had been called), in addition to settting the property. Likewise,
changing the attribute will reflect back on the property.

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


Event handling
==============

The browser executes JavaScript code as soon as it loads the web page,
but most changes to the page should be made *in response* to user
actions. To bridge the gap, scripts ask for code to run when *page
events*, like button clicks or key presses, occur.

Here's how that works. First, any time the user interacts with the
page, the browser generates *events*. Each event has a name, like
`change`, `click`, or `submit`, and a target element (an input area, a
link, or a form). JavaScript code can call `addEventListener` to react
to those events: `node.addEventListener('click', handler)` sets
`handler` to run every time the element corresponding to `node`
generates a `click` event. It's basically Tk's `bind`, but in the
browser. Let's implement it.

Let's start with generating events. I'll create a `dispatch_event`
method and call it whenever an event is generated. That includes,
first, any time we click in the page:

``` {.python expected=False}
class Tab:
    def click(self, x, y):
        while elt:
            # ...
            elif elt.tag == "a" and "href" in elt.attributes:
                self.js.dispatch_event("click", elt)
                # ...
            elif elt.tag == "input":
                self.js.dispatch_event("click", elt)
                # ...
            elif elt.tag == "button":
                self.js.dispatch_event("click", elt)
                # ...
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
Node.prototype.dispatchEvent = function(type) {
    var handle = this.handle;
    var list = (LISTENERS[handle] && LISTENERS[handle][type]) || [];
    for (var i = 0; i < list.length; i++) {
        list[i].call(this);
    }
}
```

Note that `dispatchEvent` uses the `call` method on functions, which
sets the value of `this` inside that function. As is standard in
JavaScript, I'm setting it to the node that the event was generated
on.

When an event occurs, the browser calls `dispatchEvent` from Python:

``` {.python replace=self.interp.evaljs/do_default%20=%20self.interp.evaljs}
class JSContext:
    def dispatch_event(self, type, elt):
        handle = self.node_to_handle.get(elt, -1)
        self.interp.evaljs(DISPATCH_CODE, type=type, handle=handle)
```

Here the `DISPATCH_CODE` constant is a string of JavaScript code that
dispatches a new event:

``` {.python replace=dukpy.type/new%20Event(dukpy.type)}
DISPATCH_CODE = "new Node(dukpy.handle).dispatchEvent(dukpy.type)"
```

Here the `dukpy` object stores the named `type` and `handle` arguments
passed above. So when `dispatch_event` is called on the Python side,
that runs `dispatchEvent` on the JavaScript side, and that in turn
runs all of the event listeners.

With all this event-handling machinery in place, we can update the
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

Let's implement this, starting on the JavaScript side. JavaScript has
the obscure `Object.defineProperty` function to define setters:

``` {.javascript}
Object.defineProperty(Node.prototype, 'innerHTML', {
    set: function(s) {
        call_python("innerHTML_set", this.handle, s.toString());
    }
});
```

In `innerHTML`, we'll need to parse the HTML string. That turns out to
be trickier than you'd think, because our browser's HTML parser is
intended to parse whole HTML documents, not these document fragments.
As an expedient but incorrect hack,[^hack] I'll just wrap the HTML in
an `html` and `body` element:

[^hack]: Real browsers follow the standardized parsing algorithm for
    HTML fragments defined by [HTML 5][html5-fragment].
    
[html5-fragment]: https://html.spec.whatwg.org/#parsing-html-fragments

``` {.python indent=4}
def innerHTML_set(self, handle, s):
    doc = HTMLParser("<html><body>" + s + "</body></html>").parse()
    new_nodes = doc.children[0].children
```

Don't forget to export the `innerHTML_set` function. Note that we extract
all children of the `body` element, because an `innerHTML_set` call can
create multiple nodes at a time. These new nodes must now be made
children of the element `innerHTML_set` was called on:

``` {.python indent=4}
def innerHTML_set(self, handle, s):
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
that nothing happens when a script calls `innerHTML_set`. That's
because, while we have changed the HTML tree, we haven't regenerated
the layout tree or the display list, so the browser is still showing
the old page.

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
do that; we just need to re-apply the styles we already have.[^update-styles]

[^update-styles]: Actually, using `innerHTML` you could in theory
    delete existing `link` nodes or create new ones. Real browser
    respond to this correctly, either removing the rules corresponding
    to deleted `link` nodes or downloading new style sheets when new
    `link` nodes are created. This is tricky to get right, so I'm
    skipping it here.

Now, whenever the page changes, we can lay it out again by calling
`render`:

``` {.python}
class JSContext:
    def innerHTML_set(self, handle, s):
        # ...
        self.tab.render()
```

JavaScript can now modify the web page!

Let's try this out this in our guest book server. I don't want people
writing long rants in my guest book, so I'm going to put a
100-character limit on guest book entries.

First, switch to the server codebase and add a new paragraph `<p
id=errors></p>` after the guest book form. Initially this paragraph
will be empty, but we'll write an error message into it if the
paragraph gets too long.

``` {.python file=server}
def show_comments():
    # ...
    out += "<p id=errors></p>"
    # ...
```

Also add a script to the page.

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

::: {.further}
This code has a subtle memory leak: if you access an HTML element from
JavaScript (thereby creating a handle for it) and then remove the
element from the page (using `innerHTML`), Python won't be able to
garbage-collect the `Element` object because it is still stored in the
`node_to_handle` map. And that's good, if JavaScript can still access
that `Element` via its handle, but bad otherwise. Solving this is
quite tricky, because it requires the Python and JavaScript garbage
collectors to [cooperate][cross-component].
:::

[cross-component]: https://research.google/pubs/pub47359/

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
been called. We'll now be passing an `Event` object to
`dispatchEvent`, instead of just the event type:

``` {.javascript}
Node.prototype.dispatchEvent = function(evt) {
    var type = evt.type;
    // ...
    for (var i = 0; i < list.length; i++) {
        list[i].call(this, evt);
    }
    // ...
    return evt.do_default;
}
```

In Python, we now need to create an `Event` to call `dispatchEvent`:

``` {.python}
DISPATCH_CODE = "new Node(dukpy.handle).dispatchEvent(new Event(dukpy.type))"
```

Also note that `dispatchEvent` returns `evt.do_default`, which is not
only standard in JavaScript but also helpful when dispatching events
from Python, because Python's `dispatch_event` can return that boolean
to its handler:

``` {.python}
class JSContext:
    def dispatch_event(self, type, elt):
        # ...
        do_default = self.interp.evaljs(DISPATCH_CODE, type=type, handle=handle)
        return not do_default
```

This way, every time an event happens, the browser can check the
return value of `dispatch_event` and stop if it is `True`. We have
three such places in the `click` method:

``` {.python}
class Tab:
    def click(self, x, y):
        while elt:
            # ...
            elif elt.tag == "a" and "href" in elt.attributes:
                if self.js.dispatch_event("click", elt): return
                # ...
            elif elt.tag == "input":
                if self.js.dispatch_event("click", elt): return
                # ...
            elif elt.tag == "button":
                if self.js.dispatch_event("click", elt): return
                # ...
            # ...
         # ...
```

And also one in `submit_form`:

``` {.python}
class Tab:
    def submit_form(self, elt):
        if self.js.dispatch_event("submit", elt): return
```

And one in `keypress`:

``` {.python}
class Tab:
    def keypress(self, char):
        if self.focus:
            if self.js.dispatch_event("keydown", self.focus): return
```

Now our character count code can prevent the user from submitting a
form! It can use a global variable to track whether or not submission
is allowed, and then when submission is attempted it can cancel that
action if submission shouldn't be allowed.

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

This way it's impossible to submit the form when the comment is too long.

Well... Impossible in this browser. But since there are browsers that
don't run JavaScript (like ours, one chapter back), we should check
the length on the server side too:

``` {.python file=server}
def add_entry(params):
    if 'guest' in params and len(params['guest']) <= 100:
        ENTRIES.append(params["guest"])
    return show_comments()
```

A closing thought
=================

Note that while our guest book is *enhanced* by JavaScript, it still
uses HTML, CSS, form elements and all the other features we've built
so far into our browser. This is in contrast to the recently-departed
[Adobe Flash][flash], and before that [Java Applets][javaApplets],
which were self-contained plug-ins that handled input and rendering
with their own technologies.

Because JavaScript builds on top of HTML and CSS, it allows web
applications to go beyond what is built into the browser, similar in
some ways to a [browser extension][browserExtension]. Ideally, web
pages should be written so that they work correctly without
JavaScript, but work better with it---this is the concept of
[progressive enhancement][progEnhancement]. (In addition to supporting
more browsers, progressive enhancement makes saves you from needing to
re-invent HTML and CSS---even if you now know how!)

[flash]: https://www.adobe.com/products/flashplayer/end-of-life.html
[javaApplets]: https://en.wikipedia.org/wiki/Java_applet

[browserExtension]: https://en.wikipedia.org/wiki/Browser_extension
[progEnhancement]: https://en.wikipedia.org/wiki/Progressive_enhancement

::: {.further}
JavaScript [first appeared in 1995][historyJS], as part of Netscape
Navigator. Its name was chosen to indicate a similarity to the
[Java][javaLang] language, and the syntax is Java-esque for that
reason. However, under the surface JavaScript is a much more dynamic
language than Java, as is appropriate given its role as a progressive
enhancement mechanism for the web.
:::

[javaLang]: https://en.wikipedia.org/wiki/Java_(programming_language)
[historyJS]: https://auth0.com/blog/a-brief-history-of-javascript/


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
