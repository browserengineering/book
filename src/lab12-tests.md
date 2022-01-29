Tests for WBE Chapter 11
========================

This file contains tests for Chapter 12 (Scheduling and Threading).

	>>> from test import Event
    >>> import test12 as test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab12
    >>> import time
    >>> import threading
    >>> lab12.USE_BROWSER_THREAD = False

Testing basic loading and dirty bits
====================================

Testing a multi-threaded program is quite complicated, so here we just mock
the MainThreadRunner and run all the tests on the same thread as the Browser.

	>>> lab12.MainThreadEventLoop = test.MockMainThreadEventLoop

    >>> test_url = 'http://test.test/'
    >>> test.socket.respond(test_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<div>Text<</div>)")

    >>> browser = lab12.Browser()

Before load, there is no tab height or display list.

	>>> browser.active_tab_height == None
	True
    >>> browser.active_tab_display_list == None
    True

Once the Tab has loaded, the browser should need raster and draw.

    >>> browser.load(test_url)
    >>> browser.render()
    >>> browser.needs_raster_and_draw
    True

The Tab has already committed:

	>>> browser.active_tab_height
	81
    >>> len(browser.active_tab_display_list)
    1

But no raster or draw should have occured, because that is the responsibility
of the Browser event loop, which we are running manually in this test.

    >>> browser.tab_surface == None
    True

After performing raster and draw, the display list should be present.

    >>> browser.raster_and_draw()
    >>> browser.tab_surface.printTabCommands()
    clear(color=ffffffff)
    drawString(text=Text, x=13.0, y=36.10546875, color=ff000000)
    drawString(text=), x=13.0, y=58.44921875, color=ff000000)

    >>> browser.needs_raster_and_draw
    False

The initial sroll offset is 0.

    >>> browser.tabs[browser.active_tab].scroll
    0

Scrolling down causes a draw but nothing else.

    >>> browser.handle_down()
    >>> browser.needs_raster_and_draw
    True

    Focusing the address bar and typing into it causes chrome raster and draw,
    but not tab raster

    >>> browser.handle_click(Event(51, 41))
    >>> browser.focus
    'address bar'
    >>> browser.handle_key('c')
    >>> browser.needs_raster_and_draw
    True

Testing TabWrapper
==================

	>>> lab12.MainThreadEventLoop = test.MockNoOpMainThreadEventLoop
    >>> browser = lab12.Browser()
    >>> browser.load(test_url)

 The URL is not set until the load has committed.

    >>> browser.url == None
    True
    >>> browser.scroll == 0
    True

    >>> browser.commit("test-url", 1, 24, [3])
    >>> browser.url
    'test-url'
    >>> browser.scroll
    1
    >>> browser.active_tab_height
    24
    >>> browser.active_tab_display_list
    [3]

Testing TaskQueue
=================

	>>> task_queue = lab12.TaskQueue()
	>>> def callback1():
	...		print('callback1')
	>>> def callback2():
	...		print('callback2')
	>>> task_queue.add_task(callback1)
	>>> task_queue.has_tasks()
	True
	>>> task_queue.get_next_task()()
	callback1
	>>> task_queue.has_tasks()
	False

	>>> task_queue.add_task(callback2)
	>>> task_queue.add_task(callback1)
	>>> task_queue.get_next_task()()
	callback2
	>>> task_queue.get_next_task()()
	callback1
	>>> task_queue.has_tasks()
	False
