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
    >>> lab16.print_tree(frame.document) #doctest: +ELLIPSIS
     DocumentLayout()
       BlockLayout(x=13.0, y=13.0, width=774.0, height=45.0, node=<html>)
         BlockLayout(x=13.0, y=13.0, width=774.0, height=45.0, node=<body>)
           BlockLayout(x=13.0, y=13.0, width=774.0, height=45.0, node=<main>)
             BlockLayout(x=13.0, y=13.0, width=774.0, height=45.0, node=<section>)
               BlockLayout(x=13.0, y=13.0, width=774.0, height=15.0, node=<div>)
                 LineLayout(x=13.0, y=18.0, width=774.0, height=15.0)
                   TextLayout(x=13.0, y=20.25, width=48.0, height=15.0, word=This)
                   TextLayout(x=73.0, y=20.25, width=24.0, height=15.0, word=is)
                   TextLayout(x=109.0, y=20.25, width=36.0, height=15.0, word=the)
                   TextLayout(x=157.0, y=20.25, width=60.0, height=15.0, word=inner)
                   TextLayout(x=229.0, y=20.25, width=36.0, height=15.0, word=div)
                   TextLayout(x=277.0, y=20.25, width=36.0, height=15.0, word=#1.)
               BlockLayout(x=13.0, y=13.0, width=774.0, height=30.0, node=<div>)
                 LineLayout(x=13.0, y=33.0, width=774.0, height=15.0)
                   TextLayout(x=13.0, y=35.25, width=48.0, height=15.0, word=This)
                   TextLayout(x=73.0, y=35.25, width=24.0, height=15.0, word=is)
                   TextLayout(x=109.0, y=35.25, width=36.0, height=15.0, word=the)
                   TextLayout(x=157.0, y=35.25, width=60.0, height=15.0, word=inner)
                   TextLayout(x=229.0, y=35.25, width=36.0, height=15.0, word=div)
                   TextLayout(x=277.0, y=35.25, width=36.0, height=15.0, word=#2.)
                   TextLayout(x=325.0, y=35.25, width=24.0, height=15.0, word=It)
                   TextLayout(x=361.0, y=35.25, width=36.0, height=15.0, word=has)
                   TextLayout(x=409.0, y=35.25, width=12.0, height=15.0, word=a)
                   TextLayout(x=433.0, y=35.25, width=48.0, height=15.0, word=very)
                   TextLayout(x=493.0, y=35.25, width=48.0, height=15.0, word=long)
                   TextLayout(x=553.0, y=35.25, width=48.0, height=15.0, word=body)
                   TextLayout(x=613.0, y=35.25, width=48.0, height=15.0, word=text)
                   TextLayout(x=673.0, y=35.25, width=48.0, height=15.0, word=that)
                   TextLayout(x=733.0, y=35.25, width=48.0, height=15.0, word=will)
                 LineLayout(x=13.0, y=48.0, width=774.0, height=15.0)
                   TextLayout(x=13.0, y=50.25, width=72.0, height=15.0, word=surely)
                   TextLayout(x=97.0, y=50.25, width=60.0, height=15.0, word=spill)
                   TextLayout(x=169.0, y=50.25, width=48.0, height=15.0, word=over)
                   TextLayout(x=229.0, y=50.25, width=36.0, height=15.0, word=two)
                   TextLayout(x=277.0, y=50.25, width=72.0, height=15.0, word=lines.)

Next, we can execute some JavaScript to change the page:

    >>> script = """
    ... window.document.querySelectorAll("div")[1].innerHTML = 'Short body';
    ... """
    >>> frame.js.run("<test>", script, frame.window_id)
    >>> frame.render()
    >>> lab16.print_tree(frame.document) #doctest: +ELLIPSIS
     DocumentLayout()
       BlockLayout(x=13.0, y=13.0, width=774.0, height=30.0, node=<html>)
         BlockLayout(x=13.0, y=13.0, width=774.0, height=30.0, node=<body>)
           BlockLayout(x=13.0, y=13.0, width=774.0, height=30.0, node=<main>)
             BlockLayout(x=13.0, y=13.0, width=774.0, height=30.0, node=<section>)
               BlockLayout(x=13.0, y=13.0, width=774.0, height=15.0, node=<div>)
                 LineLayout(x=13.0, y=18.0, width=774.0, height=15.0)
                   TextLayout(x=13.0, y=20.25, width=48.0, height=15.0, word=This)
                   TextLayout(x=73.0, y=20.25, width=24.0, height=15.0, word=is)
                   TextLayout(x=109.0, y=20.25, width=36.0, height=15.0, word=the)
                   TextLayout(x=157.0, y=20.25, width=60.0, height=15.0, word=inner)
                   TextLayout(x=229.0, y=20.25, width=36.0, height=15.0, word=div)
                   TextLayout(x=277.0, y=20.25, width=36.0, height=15.0, word=#1.)
               BlockLayout(x=13.0, y=13.0, width=774.0, height=15.0, node=<div>)
                 LineLayout(x=13.0, y=33.0, width=774.0, height=15.0)
                   TextLayout(x=13.0, y=35.25, width=60.0, height=15.0, word=Short)
                   TextLayout(x=85.0, y=35.25, width=48.0, height=15.0, word=body)

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
           LineLayout(x=13.0, y=18.0, width=774.0, height=152.0)
             IframeLayout(src=http://test/2, x=13.0, y=18.0, width=52.0, height=152.0)
    >>> lab16.print_tree(frame2.document)
     DocumentLayout()
       BlockLayout(x=13.0, y=13.0, width=24.0, height=60.0, node=<html>)
         BlockLayout(x=13.0, y=13.0, width=24.0, height=60.0, node=<body>)
           BlockLayout(x=13.0, y=13.0, width=24.0, height=60.0, node=<p>)
             LineLayout(x=13.0, y=18.0, width=24.0, height=15.0)
               TextLayout(x=13.0, y=20.25, width=12.0, height=15.0, word=A)
             LineLayout(x=13.0, y=33.0, width=24.0, height=15.0)
               TextLayout(x=13.0, y=35.25, width=12.0, height=15.0, word=B)
             LineLayout(x=13.0, y=48.0, width=24.0, height=15.0)
               TextLayout(x=13.0, y=50.25, width=12.0, height=15.0, word=C)
             LineLayout(x=13.0, y=63.0, width=24.0, height=15.0)
               TextLayout(x=13.0, y=65.25, width=12.0, height=15.0, word=D)

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
           LineLayout(x=13.0, y=18.0, width=774.0, height=152.0)
             IframeLayout(src=http://test/2, x=13.0, y=18.0, width=102.0, height=152.0)

But also the child frame should have resized as well:

    >>> lab16.print_tree(frame2.document)
     DocumentLayout()
       BlockLayout(x=13.0, y=13.0, width=74.0, height=30.0, node=<html>)
         BlockLayout(x=13.0, y=13.0, width=74.0, height=30.0, node=<body>)
           BlockLayout(x=13.0, y=13.0, width=74.0, height=30.0, node=<p>)
             LineLayout(x=13.0, y=18.0, width=74.0, height=15.0)
               TextLayout(x=13.0, y=20.25, width=12.0, height=15.0, word=A)
               TextLayout(x=37.0, y=20.25, width=12.0, height=15.0, word=B)
               TextLayout(x=61.0, y=20.25, width=12.0, height=15.0, word=C)
             LineLayout(x=13.0, y=33.0, width=74.0, height=15.0)
               TextLayout(x=13.0, y=35.25, width=12.0, height=15.0, word=D)
