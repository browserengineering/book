Tests for WBE Chapter 15
========================

This file contains tests for Chapter 15 (Embedded Content).

    >>> from test import Event
    >>> import threading
    >>> import test14 as test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> _ = test.gtts.patch()
    >>> threading.Lock = test.MockLock
    >>> import lab13
    >>> import lab15
    >>> import time
    >>> import threading
    >>> import math
    >>> lab15.USE_BROWSER_THREAD = False
    >>> lab13.USE_GPU = False
    >>> lab15.USE_GPU = False

Test images
===========

This image is 5px wide and 16 px tall:

    >>> image_url = 'http://test.test/img.png'
    >>> test.socket.respond(image_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: image/png\r\n\r\n" +
    ... b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x05\x00\x00\x00\x05\x08\x03\x00\x00\x00\xba\xb1\xd6\xd7\x00\x00\x00\x08acTL\x00\x00\x00\x02\x00\x00\x00\x07m\xe9\x06\xd3\x00\x00\x00\x0fPLTE\x00\x00\x00?\x95d\x8f(\x1b\x00\x00\x00\xae\x00\x00|\xbf\xb9\xc7\x00\x00\x00\x03tRNS\x00\x8e\xd1\xae\xa2\x93Y\x00\x00\x00\x1bIDAT\x08\xd7=\x86\xb1\t\x00\x00\x00\x82\x84\xfe\xff\xb9\\R\x04\x89\x10X\xfa\x97\x02\x03\x1b\x004\xee\xba\xc9\xa4\x00\x00\x00\x1afcTL\x00\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00Z\xc7\x00\x00\x00\x0c\xb5\xcf\x19\x00\x00\x00\x13fdAT\x00\x00\x00\x01\x08\xd7\x01\x04\x00\xfb\xff\x01\x04\x00\x00\x00\x14\x00\x06cS\x8f\xf5\x00\x00\x00\x1afcTL\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x02\x00\xc8\x00d\x00\x01Uz\x1dN\x00\x00\x00\x17fdAT\x00\x00\x00\x03\x08\xd7\x01\x08\x00\xf7\xff\x00\x01\x00\x01\x00\x01\x01\x01\x00\x1a\x00\x061`\xa4\t\x00\x00\x00\x00IEND\xaeB`\x82")

Let's verify that a basic image loads and has the correct dimensions:

    >>> url = 'http://test.test/'
    >>> test.socket.respond(url, b'HTTP/1.0 200 OK\r\n' +
    ... b'content-type: text/html\r\n\r\n' +
    ... b'<img src="http://test.test/img.png">')

    >>> browser = lab15.Browser()
    >>> browser.load(url)
    >>> browser.tabs[0].advance_tab()
    >>> browser.render()
    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     DrawImage(rect=Rect(13, 18, 18, 34))

Now let's test setting a different width and height:

    >>> size_url = 'http://test.test/size'
    >>> test.socket.respond(size_url, b'HTTP/1.0 200 OK\r\n' +
    ... b'content-type: text/html\r\n\r\n' +
    ... b'<img width=10 height=20 src="http://test.test/img.png">')

    >>> browser = lab15.Browser()
    >>> browser.load(size_url)
    >>> browser.tabs[0].advance_tab()
    >>> browser.render()
    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     DrawImage(rect=Rect(13, 18, 23, 38))

Iframes
=======

Let's load the original image in an iframe.

    >>> iframe_url = 'http://test.test/iframe'
    >>> test.socket.respond(iframe_url, b'HTTP/1.0 200 OK\r\n' +
    ... b'content-type: text/html\r\n\r\n' +
    ... b'<iframe src="http://test.test/">')

    >>> browser = lab15.Browser()
    >>> browser.load(iframe_url)
    >>> browser.tabs[0].advance_tab()
    >>> browser.render()
    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     SaveLayer(alpha=1.0)
       ClipRRect(RRect(13, 18, 315, 170, 1))
         Transform(translate(14.0, 19.0))
           DrawImage(rect=Rect(13, 18, 18, 34))
         DrawOutline(top=18.0 left=13.0 bottom=170.0 right=315.0 border_color=black thickness=2)

And the sized one:

    >>> iframe_size_url = 'http://test.test/iframe_of_sized'
    >>> test.socket.respond(iframe_size_url, b'HTTP/1.0 200 OK\r\n' +
    ... b'content-type: text/html\r\n\r\n' +
    ... b'<iframe src="http://test.test/size">')

    >>> browser = lab15.Browser()
    >>> browser.load(iframe_size_url)
    >>> browser.tabs[0].advance_tab()
    >>> browser.render()
    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     SaveLayer(alpha=1.0)
       ClipRRect(RRect(13, 18, 315, 170, 1))
         Transform(translate(14.0, 19.0))
           DrawImage(rect=Rect(13, 18, 23, 38))
         DrawOutline(top=18.0 left=13.0 bottom=170.0 right=315.0 border_color=black thickness=2)

Iframes can be sized too:

    >>> sized_iframe_url = 'http://test.test/iframe_sized'
    >>> test.socket.respond(sized_iframe_url, b'HTTP/1.0 200 OK\r\n' +
    ... b'content-type: text/html\r\n\r\n' +
    ... b'.<br>.<br>.<br>.<br>.<br>.<br>.<br>.<br>.<br>.<br>.<br>.<br>.<br>.' +
    ... b'<br>.<br>.<br>.<br>.<br>.<br>.<br>.<br>.<br>.<br>.' +
    ... b'<iframe width=50 height=30 src="http://test.test/">')

    >>> browser = lab15.Browser()
    >>> browser.load(sized_iframe_url)
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
     SaveLayer(alpha=1.0)
       ClipRRect(RRect(45, 478, 95, 508, 1))
         Transform(translate(46.0, 479.0))
           DrawImage(rect=Rect(13, 18, 18, 34))
         DrawOutline(top=478.0 left=45.0 bottom=508.0 right=95.0 border_color=black thickness=2)

Now let's test scrolling of the root frame:

    >>> browser.scroll > 0
    False
    >>> browser.handle_down()
    >>> browser.scroll > 0
    True

Clicking the sub-frame focuses it:

    >>> browser = lab15.Browser()
    >>> browser.load(sized_iframe_url)
    >>> browser.tabs[0].advance_tab()
    >>> browser.render()
    >>> e = Event(50, 600)
    >>> browser.handle_click(e)
    >>> browser.render()
    >>> child_frame = browser.tabs[0].root_frame.nodes.children[0].children[47].frame

    >>> browser.tabs[0].focused_frame == child_frame
    True
    >>> browser.root_frame_focused
    False

And now scrolling affects just the child frame:

    >>> browser.tabs[0].root_frame.nodes.children[0].children[47].frame.scroll
    0
    >>> browser.handle_down()
    >>> browser.scroll > 0
    False
    >>> browser.tabs[0].root_frame.nodes.children[0].children[47].frame.scroll
    24.0

Accessibility
=============

Let's verify that it still works.

    >>> focus_url = 'http://test.test/focus'
    >>> test.socket.respond(focus_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b'<input><a href="/dest">Link</a>')

    >>> browser = lab15.Browser()
    >>> browser.load(focus_url)
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
    >>> browser.load(iframe_url)
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