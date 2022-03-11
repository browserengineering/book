Tests for WBE Chapter 13
========================

This file contains tests for Chapter 13 (Animations and Compositing).

	>>> from test import Event
    >>> import test12 as test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab13
    >>> import time
    >>> import threading
    >>> lab13.USE_BROWSER_THREAD = False
    >>> lab13.USE_GPU = False
		>>> lab13.TaskRunner = test.MockTaskRunner


Testing the `width` and `height` CSS properties
===============================================

    >>> test_url = 'http://test.test/'
    >>> test.socket.respond(test_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b'<div style="width:30px;height:40px;">Text</div>')

    >>> browser = lab13.Browser()
    >>> browser.load(test_url)
    >>> browser.render()

    >>> tab = browser.tabs[browser.active_tab]
    >>> body = tab.nodes.children[0]
    >>> div = body.children[0]

`style_length` is a function that returns the computed style for the specified
css property value (interpreted as "px" units) if it's set, and the default
parameter otherwise.

    >>> lab13.style_length(body, "width", 11)
    11
    >>> lab13.style_length(body, "height", 12)
    12

The div in this example has `width` and `height` set to `30px` and `40px`
respectively.

    >>> lab13.style_length(div, "width", 13)
    30
    >>> lab13.style_length(div, "height", 14)
    40

The actual width and height from layout should match:

	>>> div_obj = tab.document.children[0].children[0].children[0]
	>>> div_obj.width
	30
	>>> div_obj.height
	40

Testing CSS transtions
======================

    >>> styles = 'http://test.test/styles.css'
    >>> test.socket.respond(styles, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/css\r\n\r\n" +
    ... b"div { transition:opacity 2s;}")

    >>> transitions_url = 'http://test.test/transitions'
    >>> test.socket.respond(transitions_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='/styles.css'>" +
    ... b"<div style=\"opacity:0.5\">Text</div>)")

    >>> browser = lab13.Browser()
    >>> browser.load(transitions_url)
    >>> browser.render()

    >>> tab = browser.tabs[browser.active_tab]
    >>> div = tab.nodes.children[1].children[0]

There is a transition defined for opacity, for a duration of 2 seconds. This is
about 125 animation frames, so `get_transition` should return 125.

	>>> lab13.get_transition("opacity", div.style)
	125.0