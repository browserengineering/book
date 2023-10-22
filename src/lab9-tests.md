Tests for WBE Chapter 9
=======================

Chapter 9 (Running Interactive Scripts) introduces JavaScript and the DOM API,
The focus of the chapter is browser-JS
interaction.

    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab9

Note that we aren't mocking `dukpy`. It should just run JavaScript normally!

Testing basic <script> support
==============================

The browser should download JavaScript code mentioned in a `<script>` tag:

    >>> url2 = lab9.URL(test.socket.serve(""))
    >>> url = lab9.URL(test.socket.serve("<script src=" + str(url2) + "></script>"))
    >>> lab9.Browser().new_tab(url)
    >>> test.socket.last_request(str(url2))
    b'GET /0 HTTP/1.0\r\nHost: test\r\n\r\n'

If the script succeeds, the browser prints nothing:

    >>> test.socket.respond(str(url2), b"HTTP/1.0 200 OK\r\n\r\nvar x = 2; x + x")
    >>> lab9.Browser().new_tab(url)

If instead the script crashes, the browser prints an error message:

    >>> test.socket.respond(str(url2), b"HTTP/1.0 200 OK\r\n\r\nthrow Error('Oops');")
    >>> lab9.Browser().new_tab(url) #doctest: +ELLIPSIS
    Script http://test/0 crashed Error: Oops
    ...

Note that in the last test I set the `ELLIPSIS` flag to elide the duktape stack
trace.

Testing JSContext
=================

For the rest of these tests we're going to use `console.log` for most testing:

    >>> script = "console.log('Hello, world!')"
    >>> test.socket.respond(str(url2), b"HTTP/1.0 200 OK\r\n\r\n" + script.encode("utf8"))
    >>> lab9.Browser().new_tab(url)
    Hello, world!

Note that you can print other data structures as well:

    >>> script = "console.log([2, 3, 4])"
    >>> test.socket.respond(str(url2), b"HTTP/1.0 200 OK\r\n\r\n" + script.encode("utf8"))
    >>> lab9.Browser().new_tab(url)
    [2, 3, 4]

Let's test that variables work:

    >>> script = "var x = 'Hello!'; console.log(x)"
    >>> test.socket.respond(str(url2), b"HTTP/1.0 200 OK\r\n\r\n" + script.encode("utf8"))
    >>> lab9.Browser().new_tab(url)
    Hello!
    
Next let's try to do two scripts:

    >>> url2 = 'http://test.test/js1'
    >>> url3 = 'http://test.test/js2'
    >>> html_page = "<script src=" + url2 + "></script>" + "<script src=" + url3 + "></script>"
    >>> test.socket.respond(str(url), b"HTTP/1.0 200 OK\r\n\r\n" + html_page.encode("utf8"))
    >>> test.socket.respond(str(url2), b"HTTP/1.0 200 OK\r\n\r\nvar x = 'Testing, testing';")
    >>> test.socket.respond(str(url3), b"HTTP/1.0 200 OK\r\n\r\nconsole.log(x);")
    >>> lab9.Browser().new_tab(url)
    Testing, testing

Testing querySelectorAll
========================

The `querySelectorAll` method is easiest to test by looking at the number of
matching nodes:

    >>> page = """<!doctype html>
    ... <div>
    ...   <p id=lorem>Lorem</p>
    ...   <p class=ipsum>Ipsum</p>
    ... </div>"""
    >>> test.socket.respond(str(url), b"HTTP/1.0 200 OK\r\n\r\n" + page.encode("utf8"))
    >>> b = lab9.Browser()
    >>> b.new_tab(url)
    >>> js = b.tabs[0].js
    >>> js.run("document.querySelectorAll('div').length")
    1
    >>> js.run("document.querySelectorAll('p').length")
    2
    >>> js.run("document.querySelectorAll('html').length")
    1
    
That last query is finding an implicit tag. Complex queries are also supported

    >>> js.run("document.querySelectorAll('html p').length")
    2
    >>> js.run("document.querySelectorAll('html body div p').length")
    2
    >>> js.run("document.querySelectorAll('body html div p').length")
    0

Testing getAttribute
====================

`querySelectorAll` should return `Node` objects:

    >>> js.run("document.querySelectorAll('html')[0] instanceof Node")
    True


Once we have a `Node` object we can call `getAttribute`:

    >>> js.run("document.querySelectorAll('p')[0].getAttribute('id')")
    'lorem'

Note that this is "live": as the page changes `querySelectorAll` gives new results:

    >>> b.tabs[0].nodes.children[0].children[0].children[0].attributes['id'] = 'blah'
    >>> js.run("document.querySelectorAll('p')[0].getAttribute('id')")
    'blah'

Testing innerHTML
=================

Testing `innerHTML` is tricky because it knowingly misbehaves on hard-to-parse
HTML fragments. So we must purposely avoid testing those.

One annoying thing about `innerHTML` is that, since it is an assignment, it
returns its right hand side. I use `void()` to avoid testing that.

    >>> js.run("void(document.querySelectorAll('p')[0].innerHTML" +
    ...     " = 'This is a <b id=new>new</b> element!')")

Once we've changed the page, the browser should re-render:

    >>> lab9.print_tree(b.tabs[0].document)
     DocumentLayout()
       BlockLayout[block](x=13, y=18, width=774, height=30.0, node=<html>)
         BlockLayout[block](x=13, y=18, width=774, height=30.0, node=<body>)
           BlockLayout[block](x=13, y=18, width=774, height=30.0, node=<div>)
             BlockLayout[inline](x=13, y=18, width=774, height=15.0, node=<p id="blah">)
               LineLayout(x=13, y=18, width=774, height=15.0)
                 TextLayout(x=13, y=20.25, width=48, height=12, node='This is a ', word=This)
                 TextLayout(x=73, y=20.25, width=24, height=12, node='This is a ', word=is)
                 TextLayout(x=109, y=20.25, width=12, height=12, node='This is a ', word=a)
                 TextLayout(x=133, y=20.25, width=36, height=12, node='new', word=new)
                 TextLayout(x=181, y=20.25, width=96, height=12, node=' element!', word=element!)
             BlockLayout[inline](x=13, y=33.0, width=774, height=15.0, node=<p class="ipsum">)
               LineLayout(x=13, y=33.0, width=774, height=15.0)
                 TextLayout(x=13, y=35.25, width=60, height=12, node='Ipsum', word=Ipsum)

Note that there's now many `TextLayout`s inside the first `LineLayout`, one per
new word.

Now that we've modified the page we should be able to find the new elements:

    >>> js.run("document.querySelectorAll('b').length")
    1

We should also be able to delete nodes this way:

    >>> js.run("var old_b = document.querySelectorAll('b')[0]")
    >>> js.run("void(document.querySelectorAll('p')[0].innerHTML = 'Lorem')")
    >>> js.run("document.querySelectorAll('b').length")
    0
    
The page is rer-endered again:

    >>> lab9.print_tree(b.tabs[0].document)
     DocumentLayout()
       BlockLayout[block](x=13, y=18, width=774, height=30.0, node=<html>)
         BlockLayout[block](x=13, y=18, width=774, height=30.0, node=<body>)
           BlockLayout[block](x=13, y=18, width=774, height=30.0, node=<div>)
             BlockLayout[inline](x=13, y=18, width=774, height=15.0, node=<p id="blah">)
               LineLayout(x=13, y=18, width=774, height=15.0)
                 TextLayout(x=13, y=20.25, width=60, height=12, node='Lorem', word=Lorem)
             BlockLayout[inline](x=13, y=33.0, width=774, height=15.0, node=<p class="ipsum">)
               LineLayout(x=13, y=33.0, width=774, height=15.0)
                 TextLayout(x=13, y=35.25, width=60, height=12, node='Ipsum', word=Ipsum)

Despite this, the old nodes should stick around:

    >>> js.run("old_b.getAttribute('id')")
    'new'

Testing events
==============

Events are the trickiest thing to test here. First, let's do a basic test of
adding an event listener and then triggering it. I'll use the `div` element to
test things:

    >>> div = b.tabs[0].nodes.children[0].children[0]
    >>> js.run("var div = document.querySelectorAll('div')[0]")
    >>> js.run("div.addEventListener('test', function(e) { console.log('Listener ran!')})")
    >>> js.dispatch_event("test", div)
    Listener ran!
    False

The `False` is from our `preventDefault` handling (we didn't call it).

Let's test each of our automatic event types. We'll need a new web page with a
link, a button, and an input area:

    >>> page = """<!doctype html>
    ... <a href=page2>Click me!</a>
    ... <form action=/post>
    ...   <input name=input value=hi>
    ...   <button>Submit</button>
    ... </form>"""
    >>> test.socket.respond(str(url), b"HTTP/1.0 200 OK\r\n\r\n" + page.encode("utf8"))
    >>> b.new_tab(url)
    >>> js = b.tabs[1].js

Now we're going test five event handlers: clicking on the link, clicking on the
input, typing into the input, clicking on the button, and submitting the form.
We'll have a mix of `preventDefault` and non-`preventDefault` handlers to test
that feature as well.

    >>> js.run("var a = document.querySelectorAll('a')[0]")
    >>> js.run("var form = document.querySelectorAll('form')[0]")
    >>> js.run("var input = document.querySelectorAll('input')[0]")
    >>> js.run("var button = document.querySelectorAll('button')[0]")
    
Note that the `input` element has a value of `hi`:

    >>> js.run("input.getAttribute('value')")
    'hi'

Clicking on the link should be canceled because we don't actually want to
navigate to a new page.

    >>> js.run("a.addEventListener('click', " +
    ...     "function(e) { console.log('a clicked'); e.preventDefault()})")

For the `input` element, clicking should work, because we need to focus it to
type into it. But let's cancel the `keydown` event just to test that that works.

    >>> js.run("input.addEventListener('click', " +
    ...     "function(e) { console.log('input clicked')})")
    >>> js.run("input.addEventListener('keydown', " +
    ...     "function(e) { console.log('input typed'); e.preventDefault()})")

Finally, let's allow clicking on the button but then cancel the form submission:

    >>> js.run("button.addEventListener('click', " +
    ...     "function(e) { console.log('button clicked')})")
    >>> js.run("form.addEventListener('submit', " +
    ...     "function(e) { console.log('form submitted'); e.preventDefault()})")

With these all set up, we need to do some clicking and typing to trigger these
events. The display list gives us coordinates for clicking.

    >>> lab9.print_tree(b.tabs[1].document)
     DocumentLayout()
       BlockLayout[block](x=13, y=18, width=774, height=30.0, node=<html>)
         BlockLayout[block](x=13, y=18, width=774, height=30.0, node=<body>)
           BlockLayout[inline](x=13, y=18, width=774, height=15.0, node=<a href="page2">)
             LineLayout(x=13, y=18, width=774, height=15.0)
               TextLayout(x=13, y=20.25, width=60, height=12, node='Click me!', word=Click)
               TextLayout(x=85, y=20.25, width=36, height=12, node='Click me!', word=me!)
           BlockLayout[inline](x=13, y=33.0, width=774, height=15.0, node=<form action="/post">)
             LineLayout(x=13, y=33.0, width=774, height=15.0)
               InputLayout(x=13, y=35.25, width=200, height=12, type=input)
               InputLayout(x=225, y=35.25, width=200, height=12, type=button text=Submit)

    a clicked
    >>> b.tabs[1].click(14, 40)
    input clicked
    >>> b.tabs[1].keypress('t')
    input typed
    >>> b.tabs[1].click(230, 40)
    button clicked
    form submitted

However, we should not have navigated away from the original URL, because we
prevented submission:

    >>> b.tabs[1].history
    [URL(scheme=http, host=test, port=80, path='/1')]
    
Similarly, when we clicked on the `input` element its `value` should be cleared,
but when we then typed `t` into it that was canceled so the value should still
be empty at the end:

    >>> js.run("input.getAttribute('value')")
    ''
