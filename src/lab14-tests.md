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

    >>> test_url = 'http://test.test/'
    >>> test.socket.respond(test_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<link rel=stylesheet href='/styles.css'>" +
    ... b'<div></div>')

    >>> browser = lab14.Browser()
    >>> browser.load(test_url)
    >>> browser.render()

    >>> test.print_display_list_skip_noops(browser.active_tab_display_list)
     DrawRect(top=18.0 left=13.0 bottom=94.0 right=787.0 border_color=white width=0 fill_color=white)
     DrawRect(top=18.0 left=13.0 bottom=58.0 right=43.0 border_color=red width=3 fill_color=None)