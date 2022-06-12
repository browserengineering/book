Tests for WBE Chapter 14
========================

This file contains tests for Chapter 14 (Accessibility).

	>>> from test import Event
    >>> import test14 as test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
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

An outline causes a `DrawRect` with the given width and color:

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
    >>> browser.render()

    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     DrawRect(top=18.0 left=13.0 bottom=94.0 right=787.0 border_color=white width=0 fill_color=white)
     DrawRect(top=18.0 left=13.0 bottom=58.0 right=43.0 border_color=red width=3 fill_color=None)

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
     DrawRect(top=18.0 left=13.0 bottom=76.34375 right=787.0 border_color=white width=0 fill_color=white)
     DrawRRect(rect=RRect(13, 21.6211, 213, 39.4961, 1), color=lightblue)
     DrawText(text=)
     DrawText(text=Link)

But pressing `tab` will focus first the `input` and then the `a` element.

    >>> browser.handle_tab()
    >>> browser.render()

The 2px wide black display list command is the focus ring for the `input`:

    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     DrawRect(top=18.0 left=13.0 bottom=76.34375 right=787.0 border_color=white width=0 fill_color=white)
     DrawRRect(rect=RRect(13, 21.6211, 213, 39.4961, 1), color=lightblue)
     DrawText(text=)
     DrawRect(top=21.62109375 left=13.0 bottom=39.49609375 right=213.0 border_color=black width=2 fill_color=None)
     DrawText(text=Link)
     DrawLine top=21.62109375 left=13.0 bottom=39.49609375 right=13.0

And now it's for the `a`:

    >>> browser.handle_tab()
    >>> browser.render()
    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     DrawRect(top=18.0 left=13.0 bottom=76.34375 right=787.0 border_color=white width=0 fill_color=white)
     DrawRRect(rect=RRect(13, 21.6211, 213, 39.4961, 1), color=lightblue)
     DrawText(text=)
     DrawText(text=Link)
     DrawRect(top=21.62109375 left=217.0 bottom=39.49609375 right=247.0 border_color=black width=2 fill_color=None)

Accessibility
=============

The accessibility tree is automatically created.

    >>> focus_url = 'http://test.test/focus'
    >>> test.socket.respond(focus_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b'<input><a href="/dest">Link</a>')

    >>> browser = lab14.Browser()
    >>> browser.load(focus_url)
    >>> browser.render()
    >>> lab14.print_tree(browser.tabs[0].accessibility_tree)
     AccessibilityNode(node=<html> role=document
       AccessibilityNode(node=<input> role=textbox
       AccessibilityNode(node=<a href="/dest"> role=link
         AccessibilityNode(node='Link' role=link