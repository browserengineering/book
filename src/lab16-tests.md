Tests for WBE Chapter 16
========================

This file contains tests for Chapter 16 (Invalidation).

    >>> from test import Event
    >>> import threading
    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> _ = test.gtts.patch()
    >>> _ = test.MockLock.patch().start()
    >>> import lab16
    >>> import time
    >>> import threading
    >>> import math
    >>> import wbetools
    >>> wbetools.USE_BROWSER_THREAD = False
    >>> wbetools.USE_GPU = False

Editing a web page
==================

Here's a simple editable web page:

    >>> url = lab16.URL(test.socket.serve("""
    ... <!doctype html>
    ... <p contenteditable>Here is some content.</p>
    ... """))
    >>> browser = lab16.Browser()
    >>> browser.new_tab(url)
    >>> browser.render()
    >>> lab16.print_tree(browser.tabs[0].root_frame.nodes)
     <html>
       <body>
         <p contenteditable="">
           'Here is some content.'

Now we can click on the page to focus on the editable element:

    >>> tab = browser.tabs[0]
    >>> tab.focus
    >>> tab.click(25, 20)
    >>> tab.focus
    <p contenteditable="">

Now that we're focused on the element, we can type into it:

    >>> tab.keypress(" ")
    >>> tab.keypress("H")
    >>> tab.keypress("i")
    >>> tab.keypress("!")
    >>> lab16.print_tree(browser.tabs[0].root_frame.nodes)
     <html>
       <body>
         <p contenteditable="">
           'Here is some content. Hi!'

Test web page
=============

Here's a simple test web page:

    >>> url = lab16.URL(test.socket.serve("""
    ... <!doctype html>
    ... <main>
    ...   <section>
    ...     <div>
    ...       This is the inner div #1.
    ...     </div>
    ...     <div>
    ...       This is the inner div #2. It has a very long body text
    ...       that will surely spill over two lines.
    ...     </div>
    ...   </section>
    ... </main>
    ... """))

First of all, we can load and render it:

    >>> browser = lab16.Browser()
    >>> browser.new_tab(url)
    >>> browser.render()
    >>> frame = browser.tabs[0].root_frame
    >>> lab16.print_tree(frame.document) # doctest: +ELLIPSIS
     DocumentLayout()
       BlockLayout(x=13.0, y=13.0, width=774.0, height=60.0, node=<html>)
         BlockLayout(x=13.0, y=13.0, width=774.0, height=60.0, node=<body>)
           BlockLayout(x=13.0, y=13.0, width=774.0, height=60.0, node=<main>)
             BlockLayout(x=13.0, y=13.0, width=774.0, height=60.0, node=<section>)
               BlockLayout(x=13.0, y=13.0, width=774.0, height=20.0, node=<div>)
                 LineLayout(x=13.0, y=18.0, width=774.0, height=20.0, node=<div>)
                   TextLayout(x=13.0, y=21.0, width=64.0, height=20.0, node=..., word=This)
                   TextLayout(x=93.0, y=21.0, width=32.0, height=20.0, node=..., word=is)
                   TextLayout(x=141.0, y=21.0, width=48.0, height=20.0, node=..., word=the)
                   TextLayout(x=205.0, y=21.0, width=80.0, height=20.0, node=..., word=inner)
                   TextLayout(x=301.0, y=21.0, width=48.0, height=20.0, node=..., word=div)
                   TextLayout(x=365.0, y=21.0, width=48.0, height=20.0, node=..., word=#1.)
               BlockLayout(x=13.0, y=13.0, width=774.0, height=40.0, node=<div>)
                 LineLayout(x=13.0, y=38.0, width=774.0, height=20.0, node=<div>)
                   TextLayout(x=13.0, y=41.0, width=64.0, height=20.0, node=..., word=This)
                   TextLayout(x=93.0, y=41.0, width=32.0, height=20.0, node=..., word=is)
                   TextLayout(x=141.0, y=41.0, width=48.0, height=20.0, node=..., word=the)
                   TextLayout(x=205.0, y=41.0, width=80.0, height=20.0, node=..., word=inner)
                   TextLayout(x=301.0, y=41.0, width=48.0, height=20.0, node=..., word=div)
                   TextLayout(x=365.0, y=41.0, width=48.0, height=20.0, node=..., word=#2.)
                   TextLayout(x=429.0, y=41.0, width=32.0, height=20.0, node=..., word=It)
                   TextLayout(x=477.0, y=41.0, width=48.0, height=20.0, node=..., word=has)
                   TextLayout(x=541.0, y=41.0, width=16.0, height=20.0, node=..., word=a)
                   TextLayout(x=573.0, y=41.0, width=64.0, height=20.0, node=..., word=very)
                   TextLayout(x=653.0, y=41.0, width=64.0, height=20.0, node=..., word=long)
                 LineLayout(x=13.0, y=58.0, width=774.0, height=20.0, node=<div>)
                   TextLayout(x=13.0, y=61.0, width=64.0, height=20.0, node=..., word=body)
                   TextLayout(x=93.0, y=61.0, width=64.0, height=20.0, node=..., word=text)
                   TextLayout(x=173.0, y=61.0, width=64.0, height=20.0, node=..., word=that)
                   TextLayout(x=253.0, y=61.0, width=64.0, height=20.0, node=..., word=will)
                   TextLayout(x=333.0, y=61.0, width=96.0, height=20.0, node=..., word=surely)
                   TextLayout(x=445.0, y=61.0, width=80.0, height=20.0, node=..., word=spill)
                   TextLayout(x=541.0, y=61.0, width=64.0, height=20.0, node=..., word=over)
                   TextLayout(x=621.0, y=61.0, width=48.0, height=20.0, node=..., word=two)
                   TextLayout(x=685.0, y=61.0, width=96.0, height=20.0, node=..., word=lines.)

Next, we can execute some JavaScript to change the page:

    >>> script = """
    ... window.document.querySelectorAll("div")[1].innerHTML = 'Short body';
    ... """
    >>> frame.js.run("<test>", script, frame.window_id)
    >>> frame.render()
    >>> lab16.print_tree(frame.document) # doctest: +ELLIPSIS
     DocumentLayout()
       BlockLayout(x=13.0, y=13.0, width=774.0, height=40.0, node=<html>)
         BlockLayout(x=13.0, y=13.0, width=774.0, height=40.0, node=<body>)
           BlockLayout(x=13.0, y=13.0, width=774.0, height=40.0, node=<main>)
             BlockLayout(x=13.0, y=13.0, width=774.0, height=40.0, node=<section>)
               BlockLayout(x=13.0, y=13.0, width=774.0, height=20.0, node=<div>)
                 LineLayout(x=13.0, y=18.0, width=774.0, height=20.0, node=<div>)
                   TextLayout(x=13.0, y=21.0, width=64.0, height=20.0, node=..., word=This)
                   TextLayout(x=93.0, y=21.0, width=32.0, height=20.0, node=..., word=is)
                   TextLayout(x=141.0, y=21.0, width=48.0, height=20.0, node=..., word=the)
                   TextLayout(x=205.0, y=21.0, width=80.0, height=20.0, node=..., word=inner)
                   TextLayout(x=301.0, y=21.0, width=48.0, height=20.0, node=..., word=div)
                   TextLayout(x=365.0, y=21.0, width=48.0, height=20.0, node=..., word=#1.)
               BlockLayout(x=13.0, y=13.0, width=774.0, height=20.0, node=<div>)
                 LineLayout(x=13.0, y=38.0, width=774.0, height=20.0, node=<div>)
                   TextLayout(x=13.0, y=41.0, width=80.0, height=20.0, node=..., word=Short)
                   TextLayout(x=109.0, y=41.0, width=64.0, height=20.0, node=..., word=body)

Test iframe resizing
====================

(This duplicates a test from [the Chapter 15 tests](lab15-tests.md),
but modifies the styling because leading works differently in the two
chapters.)

Here's web page with an iframe inside of it. We make it narrow so that
resizing is dramatic:

    >>> url2 = lab16.URL(test.socket.serve("""
    ... <!doctype html>
    ... <p>A B C D</p>
    ... """))
    >>> url1 = lab16.URL(test.socket.serve("""
    ... <!doctype html>
    ... <iframe width=50 src=""" + str(url2) + """ />
    ... """))
    >>> browser = lab16.Browser()
    >>> browser.new_tab(url1)
    >>> browser.render()
    >>> frame1 = browser.tabs[0].root_frame
    >>> iframe = [
    ...    n for n in lab16.tree_to_list(frame1.nodes, [])
    ...    if isinstance(n, lab16.Element) and n.tag == "iframe"][0]
    >>> frame2 = iframe.frame
    >>> lab16.print_tree(frame1.document)
     DocumentLayout()
       BlockLayout(x=13.0, y=13.0, width=774.0, height=152.0, node=<html>)
         BlockLayout(x=13.0, y=13.0, width=774.0, height=152.0, node=<body>)
           LineLayout(x=13.0, y=18.0, width=774.0, height=152.0, node=<body>)
             IframeLayout(src=http://test/2, x=13.0, y=18.0, width=52.0, height=152.0)
    >>> lab16.print_tree(frame2.document)
     DocumentLayout()
       BlockLayout(x=13.0, y=13.0, width=24.0, height=80.0, node=<html>)
         BlockLayout(x=13.0, y=13.0, width=24.0, height=80.0, node=<body>)
           BlockLayout(x=13.0, y=13.0, width=24.0, height=80.0, node=<p>)
             LineLayout(x=13.0, y=18.0, width=24.0, height=20.0, node=<p>)
               TextLayout(x=13.0, y=21.0, width=16.0, height=20.0, node='A B C D', word=A)
             LineLayout(x=13.0, y=38.0, width=24.0, height=20.0, node=<p>)
               TextLayout(x=13.0, y=41.0, width=16.0, height=20.0, node='A B C D', word=B)
             LineLayout(x=13.0, y=58.0, width=24.0, height=20.0, node=<p>)
               TextLayout(x=13.0, y=61.0, width=16.0, height=20.0, node='A B C D', word=C)
             LineLayout(x=13.0, y=78.0, width=24.0, height=20.0, node=<p>)
               TextLayout(x=13.0, y=81.0, width=16.0, height=20.0, node='A B C D', word=D)

Now, let's resize it:

    >>> script = """
    ... var iframe = window.document.querySelectorAll("iframe")[0]
    ... iframe.setAttribute("width", "100");
    ... """
    >>> frame1.js.run("<test>", script, frame1.window_id)
    >>> browser.render()

The parent frame should now have resized the iframe:

    >>> lab16.print_tree(frame1.document)
     DocumentLayout()
       BlockLayout(x=13.0, y=13.0, width=774.0, height=152.0, node=<html>)
         BlockLayout(x=13.0, y=13.0, width=774.0, height=152.0, node=<body>)
           LineLayout(x=13.0, y=18.0, width=774.0, height=152.0, node=<body>)
             IframeLayout(src=http://test/2, x=13.0, y=18.0, width=102.0, height=152.0)

But also the child frame should have resized as well:

    >>> lab16.print_tree(frame2.document)
     DocumentLayout()
       BlockLayout(x=13.0, y=13.0, width=74.0, height=40.0, node=<html>)
         BlockLayout(x=13.0, y=13.0, width=74.0, height=40.0, node=<body>)
           BlockLayout(x=13.0, y=13.0, width=74.0, height=40.0, node=<p>)
             LineLayout(x=13.0, y=18.0, width=74.0, height=20.0, node=<p>)
               TextLayout(x=13.0, y=21.0, width=16.0, height=20.0, node='A B C D', word=A)
               TextLayout(x=45.0, y=21.0, width=16.0, height=20.0, node='A B C D', word=B)
             LineLayout(x=13.0, y=38.0, width=74.0, height=20.0, node=<p>)
               TextLayout(x=13.0, y=41.0, width=16.0, height=20.0, node='A B C D', word=C)
               TextLayout(x=45.0, y=41.0, width=16.0, height=20.0, node='A B C D', word=D)
