Tests for WBE Chapter 7
=======================

Chapter 7 (Handling Buttons and Links) introduces hit testing, navigation
through link clicks, and browser chrome for the URL bar and tabs.

    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab7

    >>> url = 'http://test.test/example'
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\n" +
    ... b"Header1: Value1\r\n\r\n" +
    ... b"<div>Test<br>test2<br>test3</div>")

Testing LineLayout
==================

    >>> browser = lab7.Browser()
    >>> browser.load(url)
    >>> browser.tabs
    [Tab(history=['http://test.test/example'])]
    >>> lab7.print_tree(browser.tabs[0].document)
     DocumentLayout()
       BlockLayout(x=13, y=18, width=774, height=57.59999999999998)
         BlockLayout(x=13, y=18, width=774, height=57.59999999999998)
           InlineLayout(x=13, y=18, width=774, height=57.59999999999998)