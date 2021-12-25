Tests for WBE Chapter 11
========================

This file contains tests for Chapter 12 (Scheduling and Threading).

    >>> import test12 as test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab12
    >>> import time

Testing a multi-threaded program is quite complicated, so here we just mock
the MainThreadRunner and run all the tests on the same thread as the Browser.

		>>> lab12.MainThreadRunner = test.MockMainThreadRunner

    >>> test_url = 'http://test.test/'
    >>> test.socket.respond(test_url, b"HTTP/1.0 200 OK\r\n" +
    ... b"content-type: text/html\r\n\r\n" +
    ... b"<div>Text<</div>)")

    >>> browser = lab12.Browser()
    >>> browser.load(test_url)

Once the Tab has loaded, the browser should need raster and draw.

    >>> browser.needs_chrome_raster
    True
    >>> browser.needs_tab_raster
    True
    >>> browser.needs_draw
    True

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

    >>> browser.needs_chrome_raster
    False
    >>> browser.needs_tab_raster
    False
    >>> browser.needs_draw
    False

    >>> browser.handle_down()
    >>> browser.needs_draw
    True
