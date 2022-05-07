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
    >>> import math
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
    >>> browser.composite_raster_and_draw()

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
    30.0
    >>> lab13.style_length(div, "height", 14)
    40.0

The actual width and height from layout should match:

	>>> div_obj = tab.document.children[0].children[0].children[0]
	>>> div_obj.width
	30.0
	>>> div_obj.height
	40.0

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
    >>> browser.composite_raster_and_draw()

    >>> tab = browser.tabs[browser.active_tab]
    >>> div = tab.nodes.children[1].children[0]

There is a transition defined for opacity, for a duration of 2 seconds. This is
about 125 animation frames, so `parse_transition` should return 125.

	>>> lab13.parse_transition(div.style.get("transition"))
	{'opacity': 125.0}

At first there is not a transition running:

    >>> div.animations
    {}

But once opacity changes, one starts:

    >>> div.attributes["style"] = "opacity:0.1"
    >>> tab.set_needs_render()
    >>> tab.run_animation_frame(0)
    >>> div.animations
    {'opacity': NumericAnimation(old_value=0.5, change_per_frame=-0.0032, num_frames=125.0)}

Now let's try it for width:

    >>> styles = 'http://test.test/styles2.css'
    >>> test.socket.respond(styles, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/css\r\n\r\n" +
    ... b"div { transition:width 2s;}")

    >>> transitions_url2 = 'http://test.test/transitions2'
    >>> test.socket.respond(transitions_url2, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='/styles2.css'>" +
    ... b"<div style=\"width:400px\">Text</div>)")

    >>> browser = lab13.Browser()
    >>> browser.load(transitions_url2)
    >>> browser.render()
    >>> browser.composite_raster_and_draw()

    >>> tab = browser.tabs[browser.active_tab]
    >>> div = tab.nodes.children[1].children[0]

	>>> lab13.parse_transition(div.style.get("transition"))
	{'width': 125.0}
    >>> div.animations
    {}
    >>> div.attributes["style"] = "width:100px"
    >>> tab.set_needs_render()
    >>> tab.run_animation_frame(0)
    >>> div.animations
    {'width': NumericAnimation(old_value=400.0, change_per_frame=-2.4, num_frames=125.0)}

Testing CSS transforms
======================

The `parse_transform` function parses the value of the `transform` CSS property.
    >>> lab13.parse_transform("translate(12px,45px)")
    (12.0, 45.0)
    >>> lab13.parse_transform("translate(12px, 45px)")
    (12.0, 45.0)

Unsupported values are ignored.

    >>> lab13.parse_transform("rotate(45deg)")
    (0, 0)

Animations work:

    >>> styles = 'http://test.test/styles3.css'
    >>> test.socket.respond(styles, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/css\r\n\r\n" +
    ... b"div { transition:transform 2s;}")

    >>> transitions_url3 = 'http://test.test/transitions3'
    >>> test.socket.respond(transitions_url3, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='/styles3.css'>" +
    ... b"<div style=\"transform:translate(80px,90px)\">Text</div>)")

    >>> browser = lab13.Browser()
    >>> browser.load(transitions_url3)
    >>> browser.render()
    >>> browser.composite_raster_and_draw()
    >>> tab = browser.tabs[browser.active_tab]
    >>> div = tab.nodes.children[1].children[0]
    >>> lab13.parse_transition(div.style.get("transition"))
    {'transform': 125.0}
    >>> div.animations
    {}
    >>> div.attributes["style"] = "transform:translate(0px,0px)"
    >>> tab.set_needs_render()
    >>> tab.run_animation_frame(0)
    >>> div.animations
    {'transform': TranslateAnimation(old_value=(80.0,90.0), change_per_frame=(-0.64,-0.72), num_frames=125.0)}

Smooth scrolling
================


    >>> scroll_url = 'http://test.test/scroll'
    >>> test.socket.respond(scroll_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<body style=\"scroll-behavior:smooth\"><div style=\"height:4000px\">Text</div></body>)")

    >>> browser = lab13.Browser()
    >>> browser.load(scroll_url)
    >>> browser.render()
    >>> browser.composite_raster_and_draw()
    >>> tab = browser.tabs[browser.active_tab]

The tab should have smooth scroll set:

    >>> tab.scroll_behavior
    'smooth'

As well as the browser:

    >>> browser.scroll_behavior
    'smooth'

    >>> browser.scroll
    0

Scrolling is not immediate, but shows the result after one frame:

    >>> browser.handle_down()
    >>> math.floor(browser.scroll)
    6
