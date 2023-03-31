Tests for WBE Chapter 13
========================

This file contains tests for Chapter 13 (Animations and Compositing).

  	>>> from test import Event
    >>> import threading
    >>> import test12 as test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> _ = test.MockLock.patch().start()
    >>> import lab13
    >>> import time
    >>> import threading
    >>> import math
    >>> lab13.TaskRunner = test.MockTaskRunner
    >>> import wbetools
    >>> wbetools.USE_BROWSER_THREAD = False
    >>> wbetools.USE_GPU = False

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

    >>> for item in browser.draw_list:
    ...     lab13.print_tree(item)
     Transform(<no-op>)
       SaveLayer(<no-op>)
         ClipRRect(<no-op>)
           DrawCompositedLayer()
     Transform(<no-op>)
       SaveLayer(<no-op>)
         ClipRRect(<no-op>)
           Transform(<no-op>)
             SaveLayer(<no-op>)
               ClipRRect(<no-op>)
                 Transform(<no-op>)
                   SaveLayer(alpha=0.5)
                     DrawCompositedLayer()
     Transform(<no-op>)
       SaveLayer(<no-op>)
         ClipRRect(<no-op>)
           Transform(<no-op>)
             SaveLayer(<no-op>)
               ClipRRect(<no-op>)
                 DrawCompositedLayer()
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

Testing CSS transforms
======================

The `parse_transform` function parses the value of the `transform` CSS property.
    >>> lab13.parse_transform("translate(12px,45px)")
    (12.0, 45.0)
    >>> lab13.parse_transform("translate(12px, 45px)")
    (12.0, 45.0)

Unsupported values are ignored.

    >>> lab13.parse_transform("rotate(45deg)")
    >>> lab13.parse_transform("translateY(10px)")

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

A particular challenge is handling clicks on transformed content.
Here's a page with a button translated via CSS:

    >>> transitions_url4 = 'http://test.test/transitions4'
    >>> test.socket.respond(transitions_url4, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<div style=\"transform:translate(80px,90px)\">" +
    ... b"<a href='http://test.test/success'>Click me</form>" +
    ... b"</div>")
    >>> success_url = 'http://test.test/success'
    >>> test.socket.respond(success_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n")
    >>> browser = lab13.Browser()
    >>> browser.load(transitions_url4)
    >>> browser.render()
    
Let's click it at (100, 120). Those numbers are an offset of (80, 90)
plus an initial position of (13, 21) plus a little bit to make sure
we're inside the button:

    >>> tab = browser.tabs[browser.active_tab]
    >>> tab.click(100, 120)
    >>> tab.url
    'http://test.test/success'

Note that I use `tab.click` instead of `browser.handle_click` to avoid
locking problems with the `SingleThreadedRunner`.
