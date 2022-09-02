Tests for WBE Chapter 14
========================

This file contains tests for Chapter 14 (Accessibility).

	>>> from test import Event
    >>> import threading
    >>> import test14 as test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> threading.Lock = test.MockLock
    >>> import lab13
    >>> import lab14
    >>> import time
    >>> import threading
    >>> import math
    >>> lab14.USE_BROWSER_THREAD = False
    >>> lab14.USE_GPU = False
    >>> lab13.USE_GPU = False
    >>> lab14.TaskRunner = test.MockTaskRunner

Outlines
========

The outline css property can be parsed:

    >>> lab14.parse_outline("12px solid red")
    (12, 'red')

Values other than "solid" for the secnod word are ignored:

    >>> lab14.parse_outline("12px dashed red")

An outline causes a `DrawOutline` with the given width and color:

    >>> styles = 'http://test.test/styles.css'
    >>> test.socket.respond(styles, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/css\r\n\r\n" +
    ... b"div { width: 30px; height: 40px; outline: 3px solid red; }")

    >>> outline_url = 'http://test.test/'
    >>> test.socket.respond(outline_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='/styles.css'>" +
    ... b'<div></div>')

    >>> browser = lab14.Browser()
    >>> browser.load(outline_url)
    >>> browser.tabs[0].advance_tab()
    >>> browser.render()

    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     DrawOutline(top=18.0 left=13.0 bottom=58.0 right=43.0 border_color=red thickness=3)

Focus
=====

    >>> focus_url = 'http://test.test/focus'
    >>> test.socket.respond(focus_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b'<input><a href="/dest">Link</a>')

    >>> browser = lab14.Browser()
    >>> browser.load(focus_url)
    >>> browser.render()

On load, nothing is focused:

    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     DrawRRect(rect=RRect(13, 21, 213, 37, 1), color=lightblue)
     DrawText(text=)
     DrawText(text=Link)

But pressing `tab` will focus first the `input` and then the `a` element.

    >>> browser.handle_tab()
    >>> browser.render()

The 2px wide black display list command is the focus ring for the `input`:

    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     DrawRRect(rect=RRect(13, 21, 213, 37, 1), color=lightblue)
     DrawText(text=)
     DrawLine top=21.62109375 left=13.0 bottom=39.49609375 right=13.0
     DrawOutline(top=21.62109375 left=13.0 bottom=39.49609375 right=213.0 border_color=black thickness=2)
     DrawText(text=Link)

And now it's for the `a`:

    >>> browser.handle_tab()
    >>> browser.render()
    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     DrawRRect(rect=RRect(13, 21, 213, 37, 1), color=lightblue)
     DrawText(text=)
     DrawText(text=Link)
     DrawOutline(top=21.62109375 left=217.0 bottom=39.49609375 right=247.0 border_color=black thickness=2)

Tabindex changes the order:

    >>> focus2_url = 'http://test.test/focus'
    >>> test.socket.respond(focus2_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b'<input tabindex=2><a tabindex=1 href="/dest">Link</a>')

    >>> browser = lab14.Browser()
    >>> browser.load(focus_url)
    >>> browser.render()

This time the `a` element is focused first:

    >>> browser.handle_tab()
    >>> browser.render()
    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     DrawRRect(rect=RRect(13, 21, 213, 37, 1), color=lightblue)
     DrawText(text=)
     DrawText(text=Link)
     DrawRect(top=21.62109375 left=217.0 bottom=39.49609375 right=247.0 border_color=black thickness=2)

And then the `input`:

    >>> browser.handle_tab()
    >>> browser.render()
    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     DrawRRect(rect=RRect(13, 21, 213, 37, 1), color=lightblue)
     DrawText(text=)
     DrawLine top=21.62109375 left=13.0 bottom=39.49609375 right=13.0
     DrawOutline(top=21.62109375 left=13.0 bottom=39.49609375 right=213.0 border_color=black thickness=2)
     DrawText(text=Link)

Regular elements aren't focusable, but if the `tabindex` attribute is set, they
are:

    >>> focus_tabindex_url = 'http://test.test/focus-tabindex'
    >>> test.socket.respond(focus_tabindex_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b'<div>Not focusable</div><div tabindex=1>Is focusable</div>')

    >>> browser = lab14.Browser()
    >>> browser.load(focus_tabindex_url)
    >>> browser.render()

The first `div` is not focusable.

    >>> lab14.is_focusable(browser.tabs[0].nodes.children[0].children[0])
    False

But the second one is, because it has a `tabindex` attribute.

    >>> lab14.is_focusable(browser.tabs[0].nodes.children[0].children[1])
    True

Accessibility
=============

The accessibility tree is automatically created.

    >>> focus_url = 'http://test.test/focus'
    >>> test.socket.respond(focus_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b'<input><a href="/dest">Link</a>')

    >>> browser = lab14.Browser()
    >>> browser.load(focus_url)
    >>> browser.tabs[0].toggle_accessibility()

Rendering will read out the accessibility instructions:

    >>> browser.render()
    Here are the document contents: 
    Input box: 
    Link
    Link

From this tree:

    >>> lab14.print_tree(browser.tabs[0].accessibility_tree)
     AccessibilityNode(node=<html> role=document
       AccessibilityNode(node=<input> role=textbox
       AccessibilityNode(node=<a href="/dest"> role=link
         AccessibilityNode(node='Link' role=link


Dark mode
=========

The browser supports light and dark mode rendering.

    >>> focus_url = 'http://test.test/focus'
    >>> test.socket.respond(focus_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b'<input><a href="/dest">Link</a>')

The tab contents are light:

    >>> browser = lab14.Browser()
    >>> browser.load(focus_url)
    >>> browser.render()
    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     DrawRRect(rect=RRect(13, 21, 213, 37, 1), color=lightblue)
     DrawText(text=)
     DrawText(text=Link)

But when we toggle to dark, it switches:

    >>> browser.toggle_dark_mode()
    >>> browser.render()
    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     DrawRRect(rect=RRect(13, 21, 213, 37, 1), color=blue)
     DrawText(text=)
     DrawText(text=Link)

The rules parsed by the browser style sheet should also indicate dark mode:

    >>> for guard, selector, body in browser.tabs[0].rules:
    ...     if guard == "dark":
    ...         print(str(selector) + " " + str(body))
    TagSelector(tag=a, priority=1) {'color': 'lightblue'}
    TagSelector(tag=input, priority=1) {'background-color': 'blue'}
    TagSelector(tag=button, priority=1) {'background-color': 'orangered'}
    PseudoclassSelector(focus, TagSelector(tag=input, priority=1)) {'outline': '2px solid white'}
    PseudoclassSelector(focus, TagSelector(tag=button, priority=1)) {'outline': '2px solid white'}
    PseudoclassSelector(focus, TagSelector(tag=div, priority=1)) {'outline': '2px solid white'}
    PseudoclassSelector(focus, TagSelector(tag=a, priority=1)) {'outline': '2px solid white'}

Focus
=====

Tab order causes focus:

    >>> browser.tabs[0].advance_tab()
    >>> browser.tabs[0].focus
    <input>

It also nd also causes a painted outline:

    >>> browser.render()
    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     DrawRRect(rect=RRect(13, 21, 213, 37, 1), color=blue)
     DrawText(text=)
     DrawLine top=21.62109375 left=13.0 bottom=39.49609375 right=13.0
     DrawOutline(top=21.62109375 left=13.0 bottom=39.49609375 right=213.0 border_color=white thickness=2)
     DrawText(text=Link)
