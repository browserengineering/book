Tests for WBE Chapter 15
========================

This file contains tests for Chapter 15 (Embedded Content).

    >>> from test import Event
    >>> import threading
    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> _ = test.gtts.patch()
    >>> _ = test.MockLock.patch().start()
    >>> import lab15
    >>> import time
    >>> import threading
    >>> import math
    >>> import wbetools
    >>> wbetools.USE_BROWSER_THREAD = False
    >>> wbetools.USE_GPU = False

Test images
===========

This image is 5px wide and 5px tall:

    >>> image_url = 'http://test.test/img.png'
    >>> test.socket.respond(image_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: image/png\r\n\r\n" +
    ... b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x05\x00\x00\x00\x05\x08\x03\x00\x00\x00\xba\xb1\xd6\xd7\x00\x00\x00\x08acTL\x00\x00\x00\x02\x00\x00\x00\x07m\xe9\x06\xd3\x00\x00\x00\x0fPLTE\x00\x00\x00?\x95d\x8f(\x1b\x00\x00\x00\xae\x00\x00|\xbf\xb9\xc7\x00\x00\x00\x03tRNS\x00\x8e\xd1\xae\xa2\x93Y\x00\x00\x00\x1bIDAT\x08\xd7=\x86\xb1\t\x00\x00\x00\x82\x84\xfe\xff\xb9\\R\x04\x89\x10X\xfa\x97\x02\x03\x1b\x004\xee\xba\xc9\xa4\x00\x00\x00\x1afcTL\x00\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00Z\xc7\x00\x00\x00\x0c\xb5\xcf\x19\x00\x00\x00\x13fdAT\x00\x00\x00\x01\x08\xd7\x01\x04\x00\xfb\xff\x01\x04\x00\x00\x00\x14\x00\x06cS\x8f\xf5\x00\x00\x00\x1afcTL\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x02\x00\xc8\x00d\x00\x01Uz\x1dN\x00\x00\x00\x17fdAT\x00\x00\x00\x03\x08\xd7\x01\x08\x00\xf7\xff\x00\x01\x00\x01\x00\x01\x01\x01\x00\x1a\x00\x061`\xa4\t\x00\x00\x00\x00IEND\xaeB`\x82")
    
Let's verify that we can request the image:

    >>> url = 'http://test.test/'
    >>> test.socket.respond(url, b'HTTP/1.0 200 OK\r\n' +
    ... b'content-type: text/html\r\n\r\n' +
    ... b'<img src="http://test.test/img.png">')
    >>> browser = lab15.Browser()
    >>> browser.new_tab(lab15.URL(url))
    >>> browser.render()
    >>> frame = browser.tabs[0].root_frame
    >>> headers, body = lab15.URL(image_url).request(frame.url)
    >>> type(body)
    <class 'bytes'>

The browser has now downloaded a Skia `Image` object:

    >>> img = frame.nodes.children[0].children[0].image
    >>> img # doctest: +ELLIPSIS
    Image(5, 5, ..., AlphaType.kPremul_AlphaType)
    >>> img.width()
    5
    >>> img.height()
    5
    
The `...` in the image description is because Skia will convert to the
native byte order, and that can differ between platforms.
    
Now let's make sure it actually renders:

    >>> browser.tabs[0].advance_tab()
    >>> browser.render()
    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     DrawImage(rect=Rect(13, 29, 18, 34))

Now let's test setting a different width and height:

    >>> size_url = 'http://test.test/size'
    >>> test.socket.respond(size_url, b'HTTP/1.0 200 OK\r\n' +
    ... b'content-type: text/html\r\n\r\n' +
    ... b'<img width=10 height=20 src="http://test.test/img.png">')

    >>> browser = lab15.Browser()
    >>> browser.new_tab(lab15.URL(size_url))
    >>> browser.render()
    >>> browser.tabs[0].advance_tab()
    >>> browser.render()
    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     DrawImage(rect=Rect(13, 18, 23, 38))

And double-check the layout mode:
    >>> browser.tabs[0].root_frame.document.children[0].children[0].layout_mode()
    'inline'

Iframes
=======

Let's load the original image in an iframe.

    >>> iframe_url = 'http://test.test/iframe'
    >>> test.socket.respond(iframe_url, b'HTTP/1.0 200 OK\r\n' +
    ... b'content-type: text/html\r\n\r\n' +
    ... b'<iframe src="http://test.test/">')

    >>> browser = lab15.Browser()
    >>> browser.new_tab(lab15.URL(iframe_url))
    >>> browser.render()
    >>> browser.tabs[0].advance_tab()
    >>> browser.render()
    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     Blend(blend_mode=source-over)
       Transform(translate(14.0, 19.0))
         DrawImage(rect=Rect(13, 29, 18, 34))
       Blend(blend_mode=destination-in)
         DrawRRect(rect=RRect(14, 19, 314, 169, 1), color=white)
     DrawOutline(top=18.0 left=13.0 bottom=170.0 right=315.0 border_color=black thickness=1.0)

Iframe layout mode is inline:
    >>> browser.tabs[0].root_frame.document.children[0].children[0].layout_mode()
    'inline'


And the sized one:

    >>> iframe_size_url = 'http://test.test/iframe_of_sized'
    >>> test.socket.respond(iframe_size_url, b'HTTP/1.0 200 OK\r\n' +
    ... b'content-type: text/html\r\n\r\n' +
    ... b'<iframe src="http://test.test/size">')

    >>> browser = lab15.Browser()
    >>> browser.new_tab(lab15.URL(iframe_size_url))
    >>> browser.render()
    >>> browser.tabs[0].advance_tab()
    >>> browser.render()
    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     Blend(blend_mode=source-over)
       Transform(translate(14.0, 19.0))
         DrawImage(rect=Rect(13, 18, 23, 38))
       Blend(blend_mode=destination-in)
         DrawRRect(rect=RRect(14, 19, 314, 169, 1), color=white)
     DrawOutline(top=18.0 left=13.0 bottom=170.0 right=315.0 border_color=black thickness=1.0)

Iframes can be sized too:

    >>> sized_iframe_url = 'http://test.test/iframe_sized'
    >>> test.socket.respond(sized_iframe_url, b'HTTP/1.0 200 OK\r\n' +
    ... b'content-type: text/html\r\n\r\n' +
    ... b'.<br>.<br>.<br>.<br>.<br>.<br>.<br>.<br>.<br>.<br>.<br>.<br>.<br>.' +
    ... b'<br>.<br>.<br>.<br>.<br>.<br>.<br>.<br>.<br>.<br>.' +
    ... b'<br>.<br>.<br>.<br>.<br>.<br>.<br>.<br>.<br>.<br>.' +
    ... b'<iframe width=50 height=30 src="http://test.test/">')

    >>> browser = lab15.Browser()
    >>> browser.new_tab(lab15.URL(sized_iframe_url))
    >>> browser.render()
    >>> browser.tabs[0].advance_tab()
    >>> browser.render()
    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     DrawText(text=.)
     Blend(blend_mode=source-over)
       Transform(translate(46.0, 679.0))
         DrawImage(rect=Rect(13, 29, 18, 34))
       Blend(blend_mode=destination-in)
         DrawRRect(rect=RRect(46, 679, 96, 709, 1), color=white)
     DrawOutline(top=678.0 left=45.0 bottom=710.0 right=97.0 border_color=black thickness=1.0)

Now let's test scrolling of the root frame:

    >>> browser.active_tab_scroll > 0
    False
    >>> browser.handle_down()
    >>> browser.active_tab_scroll > 0
    True

Clicking the sub-frame focuses it:

    >>> browser = lab15.Browser()
    >>> browser.new_tab(lab15.URL(sized_iframe_url))
    >>> browser.render()
    >>> browser.tabs[0].advance_tab()
    >>> browser.render()
    >>> e = Event(50, browser.chrome.bottom + 700)
    >>> browser.handle_click(e)
    >>> browser.render()
    >>> child_frame = browser.tabs[0].root_frame.nodes.children[0].children[67].frame
    >>> browser.tabs[0].focused_frame == child_frame
    True
    >>> browser.root_frame_focused
    False

And now scrolling affects just the child frame:

    >>> browser.tabs[0].root_frame.nodes.children[0].children[67].frame.scroll
    0
    >>> browser.handle_down()
    >>> browser.render()
    >>> browser.active_tab_scroll > 0
    False
    >>> browser.tabs[0].root_frame.nodes.children[0].children[67].frame.scroll
    22.0

Accessibility
=============

Let's verify that it still works.

    >>> focus_url = 'http://test.test/focus'
    >>> test.socket.respond(focus_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b'<input><a href="/dest">Link</a>')

    >>> browser = lab15.Browser()
    >>> browser.new_tab(lab15.URL(focus_url))
    >>> browser.render()
    >>> browser.toggle_accessibility()

Rendering will read out the accessibility instructions:

    >>> browser.render()
    >>> browser.composite_raster_and_draw()
    Here are the document contents: 
    Document
    Input box: 
    Link
    Focusable text: Link

It also works for iframes:

    >>> browser = lab15.Browser()
    >>> browser.new_tab(lab15.URL(iframe_url))
    >>> browser.render()
    >>> browser.toggle_accessibility()

Rendering will read out the accessibility instructions:

    >>> browser.render()
    >>> browser.composite_raster_and_draw()
    Here are the document contents: 
    Document
    Document
    Image

    Alt text parsing from HTML works:

    >>> parser = lab15.HTMLParser('<img src=my-url alt="This is alt text">')
    >>> document = parser.parse()
    >>> lab15.print_tree(document)
     <html>
       <body>
         <img src="my-url" alt="This is alt text">
    
    >>> document.children[0].children[0].attributes
    {'src': 'my-url', 'alt': 'This is alt text'}

Here are some brief tests for the attribute parser. First, that it allows
spaces:

    >>> lab15.AttributeParser('tag a="a b c" b=def').parse()
    ('tag', {'a': 'a b c', 'b': 'def'})

Next, that it allows the equals sign within quoted text:

    >>> lab15.AttributeParser('tag a="a=b c"').parse()
    ('tag', {'a': 'a=b c'})

Test iframe resizing
====================

Here's web page with an iframe inside of it. We make it narrow so that
resizing is dramatic:

    >>> url2 = test.socket.serve("""
    ... <!doctype html>
    ... <p>A B C D</p>
    ... """)
    >>> url1 = test.socket.serve("""
    ... <!doctype html>
    ... <iframe width=50 src=""" + url2 + """ />
    ... """)
    >>> browser = lab15.Browser()
    >>> browser.new_tab(lab15.URL(url1))
    >>> browser.render()
    >>> frame1 = browser.tabs[0].root_frame
    >>> iframe = [
    ...    n for n in lab15.tree_to_list(frame1.nodes, [])
    ...    if isinstance(n, lab15.Element) and n.tag == "iframe"][0]
    >>> frame2 = iframe.frame
    >>> lab15.print_tree(frame1.document)
     DocumentLayout()
       BlockLayout(x=13.0, y=13.0, width=774.0, height=152.0, node=<html>)
         BlockLayout(x=13.0, y=13.0, width=774.0, height=152.0, node=<body>)
           LineLayout(x=13.0, y=18.0, width=774.0, height=152.0, node=<body>)
             IframeLayout(src=http://test/0, x=13.0, y=18.0, width=52.0, height=152.0)
    >>> lab15.print_tree(frame2.document)
     DocumentLayout()
       BlockLayout(x=13.0, y=13.0, width=24.0, height=80.0, node=<html>)
         BlockLayout(x=13.0, y=13.0, width=24.0, height=80.0, node=<body>)
           BlockLayout(x=13.0, y=13.0, width=24.0, height=80.0, node=<p>)
             LineLayout(x=13.0, y=18.0, width=24.0, height=20.0, node=<p>)
               TextLayout(x=13.0, y=21.0, width=16.0, height=16.0, node='A B C D', word=A)
             LineLayout(x=13.0, y=38.0, width=24.0, height=20.0, node=<p>)
               TextLayout(x=13.0, y=41.0, width=16.0, height=16.0, node='A B C D', word=B)
             LineLayout(x=13.0, y=58.0, width=24.0, height=20.0, node=<p>)
               TextLayout(x=13.0, y=61.0, width=16.0, height=16.0, node='A B C D', word=C)
             LineLayout(x=13.0, y=78.0, width=24.0, height=20.0, node=<p>)
               TextLayout(x=13.0, y=81.0, width=16.0, height=16.0, node='A B C D', word=D)

Now, let's resize it:

    >>> script = """
    ... var iframe = window.document.querySelectorAll("iframe")[0]
    ... iframe.setAttribute("width", "100");
    ... """
    >>> frame1.js.run("<test>", script, frame1.window_id)
    >>> browser.render()

The parent frame should now have resized the iframe:

    >>> lab15.print_tree(frame1.document)
     DocumentLayout()
       BlockLayout(x=13.0, y=13.0, width=774.0, height=152.0, node=<html>)
         BlockLayout(x=13.0, y=13.0, width=774.0, height=152.0, node=<body>)
           LineLayout(x=13.0, y=18.0, width=774.0, height=152.0, node=<body>)
             IframeLayout(src=http://test/0, x=13.0, y=18.0, width=102.0, height=152.0)

But also the child frame should have resized as well:

    >>> lab15.print_tree(frame2.document)
     DocumentLayout()
       BlockLayout(x=13.0, y=13.0, width=74.0, height=40.0, node=<html>)
         BlockLayout(x=13.0, y=13.0, width=74.0, height=40.0, node=<body>)
           BlockLayout(x=13.0, y=13.0, width=74.0, height=40.0, node=<p>)
             LineLayout(x=13.0, y=18.0, width=74.0, height=20.0, node=<p>)
               TextLayout(x=13.0, y=21.0, width=16.0, height=16.0, node='A B C D', word=A)
               TextLayout(x=45.0, y=21.0, width=16.0, height=16.0, node='A B C D', word=B)
             LineLayout(x=13.0, y=38.0, width=74.0, height=20.0, node=<p>)
               TextLayout(x=13.0, y=41.0, width=16.0, height=16.0, node='A B C D', word=C)
               TextLayout(x=45.0, y=41.0, width=16.0, height=16.0, node='A B C D', word=D)
