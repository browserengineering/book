Tests for WBE Chapter 12
========================

This file contains tests for Chapter 12 (Scheduling and Threading).

	>>> from test import Event
    >>> import threading
    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> _ = test.MockLock.patch().start()
    >>> import lab12
    >>> import time
    >>> import threading
    >>> import wbetools
    >>> wbetools.USE_BROWSER_THREAD = False

Testing basic loading and dirty bits
====================================

Testing a multi-threaded program is quite complicated, so here we just mock
the TaskRunner and run all the tests on the same thread as the Browser.

	>>> lab12.TaskRunner = test.MockTaskRunner
    >>> test_url = test.socket.serve("<div>Text</div>)")

Before load, there is no tab height or display list.

    >>> browser = lab12.Browser()
	>>> browser.active_tab_height == 0
	True
    >>> browser.active_tab_display_list == None
    True

Once the Tab has loaded, the browser should need raster and draw.

    >>> browser.new_tab(lab12.URL(test_url))
    >>> browser.render()
    >>> browser.needs_raster_and_draw
    True

The Tab has already committed:

	>>> browser.active_tab_height
	76
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
    drawString(text=Text, x=13.0, y=33.0, color=ff000000)
    drawString(text=), x=13.0, y=53.0, color=ff000000)

    >>> browser.needs_raster_and_draw
    False

The initial sroll offset is 0.

    >>> browser.active_tab.scroll
    0

Scrolling down causes a draw but nothing else.

    >>> browser.handle_down()
    >>> browser.needs_raster_and_draw
    True

    Focusing the address bar and typing into it causes chrome raster and draw,
    but not tab raster

    >>> browser.handle_click(Event(51, 51))
    >>> browser.chrome.focus
    'address bar'
    >>> browser.handle_key('c')
    >>> browser.needs_raster_and_draw
    True

Testing TabWrapper
==================

	>>> lab12.TaskRunner = test.MockNoOpTaskRunner
    >>> browser = lab12.Browser()
    >>> browser.new_tab(lab12.URL(test_url))

 The URL is not set until the load has committed.

    >>> browser.active_tab_url == None
    True
    >>> browser.active_tab_scroll == 0
    True

    >>> commit_data = lab12.CommitData("test-url", 1, 24, [3])
    >>> browser.commit(browser.tabs[0], commit_data)
    >>> browser.active_tab_url
    'test-url'
    >>> browser.active_tab_scroll
    1
    >>> browser.active_tab_height
    24
    >>> browser.active_tab_display_list
    [3]
