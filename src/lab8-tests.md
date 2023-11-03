Tests for WBE Chapter 8
=======================

Chapter 8 (Sending Information to Servers) introduces forms and shows how
to implement simple input and button elements, plus submit forms to the server.
It also includes the first implementation of an HTTP server, in order to show
how the server processes form submissions.

    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab8

Testing request
===============

This chapter adds the ability to submit a POST request in addition to a GET
one.

    >>> url = 'http://test/submit'
    >>> request_body = "name=1&comment=2%3D3"
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\n" +
    ... b"Header1: Value1\r\n\r\n" +
    ... b"<div>Form submitted</div>", method="POST", body=request_body)
    >>> body = lab8.URL(url).request(request_body)
    >>> test.socket.last_request(url)
    b'POST /submit HTTP/1.0\r\nContent-Length: 20\r\nHost: test\r\n\r\nname=1&comment=2%3D3'

Testing InputLayout
===================

    >>> url2 = lab8.URL(test.socket.serve(
    ... b"<form action=\"/submit\">" +
    ... b"  <p>Name: <input name=name value=1></p>" +
    ... b"  <p>Comment: <input name=comment value=\"2=3\"></p>" +
    ... b"  <p><button>Submit!</button></p>" +
    ... b"</form>"))
    >>> browser = lab8.Browser()
    >>> browser.new_tab(url2)
    >>> lab8.print_tree(browser.tabs[0].document.node)
     <html>
       <body>
         <form action="/submit">
           <p>
             'Name: '
             <input name="name" value="1">
           <p>
             'Comment: '
             <input name="comment" value="2=3">
           <p>
             <button>
               'Submit!'
    >>> lab8.print_tree(browser.tabs[0].document)
     DocumentLayout()
       BlockLayout[block](x=13, y=18, width=774, height=45.0, node=<html>)
         BlockLayout[block](x=13, y=18, width=774, height=45.0, node=<body>)
           BlockLayout[block](x=13, y=18, width=774, height=45.0, node=<form action="/submit">)
             BlockLayout[inline](x=13, y=18, width=774, height=15.0, node=<p>)
               LineLayout(x=13, y=18, width=774, height=15.0)
                 TextLayout(x=13, y=20.25, width=60, height=12, node='Name: ', word=Name:)
                 InputLayout(x=85, y=20.25, width=200, height=12, type=input)
             BlockLayout[inline](x=13, y=33.0, width=774, height=15.0, node=<p>)
               LineLayout(x=13, y=33.0, width=774, height=15.0)
                 TextLayout(x=13, y=35.25, width=96, height=12, node='Comment: ', word=Comment:)
                 InputLayout(x=121, y=35.25, width=200, height=12, type=input)
             BlockLayout[inline](x=13, y=48.0, width=774, height=15.0, node=<p>)
               LineLayout(x=13, y=48.0, width=774, height=15.0)
                 InputLayout(x=13, y=50.25, width=200, height=12, type=button text=Submit!)

The display list of a button should include its contents, and the display list
of a text input should be its `value` attribute:

    >>> form = browser.tabs[0].document.children[0].children[0].children[0]
    >>> text_input = form.children[0].children[0].children[1]
    >>> button = form.children[2].children[0].children[0]
    >>> text_input.paint()
    [DrawRect(top=20.25 left=85 bottom=32.25 right=285 color=lightblue), DrawText(text=1)]
    >>> button.paint()
    [DrawRect(top=50.25 left=13 bottom=62.25 right=213 color=orange), DrawText(text=Submit!)]

Testing form submission
=======================

Forms are submitted via a click on the submit button.

    >>> browser.handle_click(test.Event(20, 55 + browser.chrome.bottom))
    >>> lab8.print_tree(browser.tabs[0].document.node)
     <html>
       <body>
         <div>
           'Form submitted'

Testing the server
==================

    >>> import server8

The server handles a GET request to the "/" URL:

    >>> server8.do_request("GET", "/", {}, "")
    ('200 OK', '<!doctype html><form action=add method=post><p><input name=guest></p><p><button>Sign the book!</button></p></form><p>Pavel was here</p>')

GET requests to other URLs return a 404 page:

    >>> server8.do_request("GET", "/unknown", {}, "")
    ('404 Not Found', '<!doctype html><h1>GET /unknown not found!</h1>')

A POST request is supported at the "/add" URL, which will parse out the `guest`
parameter from the body, insert it into the guestbook, and return it as part of
the response page:

    >>> server8.do_request("POST", "/add", {}, "guest=Chris")
    ('200 OK', '<!doctype html><form action=add method=post><p><input name=guest></p><p><button>Sign the book!</button></p></form><p>Pavel was here</p><p>Chris</p>')

POST requsts to other URLs return 404 pages:

    >>> server8.do_request("POST", "/", {}, "")
    ('404 Not Found', '<!doctype html><h1>POST / not found!</h1>')

Testing layout_mode
===================

    >>> block_inline_url = lab8.URL(test.socket.serve(
    ... b"<input>" +
    ... b"<div></div>"))
    >>> browser = lab8.Browser()
    >>> browser.new_tab(block_inline_url)
    >>> lab8.print_tree(browser.tabs[0].document.node)
     <html>
       <body>
         <input>
         <div>

In this case, because there is an inline element (the `<input>`) and a block'
sibling (the `<div`), they should be contianed in a `BlockLayout[block]`, but the
`<input>` element is in an `BlockLayout[inline]`:

    >>> lab8.print_tree(browser.tabs[0].document)
     DocumentLayout()
       BlockLayout[block](x=13, y=18, width=774, height=15.0, node=<html>)
         BlockLayout[block](x=13, y=18, width=774, height=15.0, node=<body>)
           BlockLayout[inline](x=13, y=18, width=774, height=15.0, node=<input>)
             LineLayout(x=13, y=18, width=774, height=15.0)
               InputLayout(x=13, y=20.25, width=200, height=12, type=input)
           BlockLayout[block](x=13, y=33.0, width=774, height=0, node=<div>)

The painted output also is only drawing the input as 200px wide:

    >>> browser.tabs[0].display_list
    [DrawRect(top=20.25 left=13 bottom=32.25 right=213 color=lightblue), DrawText(text=)]
    
If a `<button>` contains rich markup inside of it, it should print nothing:

    >>> url3 = lab8.URL(test.socket.serve(
    ... b"<form action=\"/submit\">" +
    ... b"<button><b>Rich markup</b></button>" +
    ... b"</form>"))
    >>> browser = lab8.Browser()
    >>> browser.new_tab(url3)
    Ignoring HTML contents inside button
    >>> browser.tabs[0].display_list
    [DrawRect(top=20.25 left=13 bottom=32.25 right=213 color=orange), DrawText(text=)]

Testing focus
=============

    Clicking on the address bar focuses it
    >>> browser.handle_click(test.Event(51, 51))
    >>> browser.focus
    >>> browser.chrome.focus
    'address bar'

    Clicking back on the content area unfocuses it
    >>> browser.handle_click(test.Event(200, 200))
    >>> browser.focus
    'content'
    >>> browser.chrome.focus

    Clicking on the back button 
    >>> rect = browser.chrome.back_rect
    >>> browser.handle_click(test.Event(rect.left + 1, rect.top + 1))
    >>> browser.focus
    >>> browser.chrome.focus

    >>> browser.handle_click(test.Event(200, 200))
    >>> browser.focus
    'content'
    >>> browser.chrome.focus
