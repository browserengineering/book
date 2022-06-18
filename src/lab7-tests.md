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
    ... b"<div>This is a test<br>Also a test<br>And this too</div>")

Testing LineLayout and TextLayout
=================================

    >>> browser = lab7.Browser()
    >>> browser.load(url)
    >>> browser.tabs
    [Tab(history=['http://test.test/example'])]
    >>> lab7.print_tree(browser.tabs[0].document.node)
     <html>
       <body>
         <div>
           'This is a test'
           <br>
           'Also a test'
           <br>
           'And this too'

Here is how the lines are represented in chapter 7:

    >>> lab7.print_tree(browser.tabs[0].document)
     DocumentLayout()
       BlockLayout(x=13, y=18, width=774, height=45.0)
         BlockLayout(x=13, y=18, width=774, height=45.0)
           InlineLayout(x=13, y=18, width=774, height=45.0)
             LineLayout(x=13, y=18, width=774, height=15.0)
               TextLayout(x=13, y=20.25, width=48, height=12, font=Font size=12 weight=normal slant=roman style=None)
               TextLayout(x=73, y=20.25, width=24, height=12, font=Font size=12 weight=normal slant=roman style=None)
               TextLayout(x=109, y=20.25, width=12, height=12, font=Font size=12 weight=normal slant=roman style=None)
               TextLayout(x=133, y=20.25, width=48, height=12, font=Font size=12 weight=normal slant=roman style=None)
             LineLayout(x=13, y=33.0, width=774, height=15.0)
               TextLayout(x=13, y=35.25, width=48, height=12, font=Font size=12 weight=normal slant=roman style=None)
               TextLayout(x=73, y=35.25, width=12, height=12, font=Font size=12 weight=normal slant=roman style=None)
               TextLayout(x=97, y=35.25, width=48, height=12, font=Font size=12 weight=normal slant=roman style=None)
             LineLayout(x=13, y=48.0, width=774, height=15.0)
               TextLayout(x=13, y=50.25, width=36, height=12, font=Font size=12 weight=normal slant=roman style=None)
               TextLayout(x=61, y=50.25, width=48, height=12, font=Font size=12 weight=normal slant=roman style=None)
               TextLayout(x=121, y=50.25, width=36, height=12, font=Font size=12 weight=normal slant=roman style=None)

Whereas in chapter 6 there is no direct layout tree representation of text, but the inline
has the same total height:

    >>> import lab6
    >>> browser2 = lab6.Browser()
    >>> browser2.load(url)
    >>> lab6.print_tree(browser2.document)
     DocumentLayout()
       BlockLayout(x=13, y=18, width=774, height=45.0)
         BlockLayout(x=13, y=18, width=774, height=45.0)
           InlineLayout(x=13, y=18, width=774, height=45.0)

Testing Tab
===========

    >>> url2 = 'http://test.test/example2'
    >>> test.socket.respond(url2, b"HTTP/1.0 200 OK\r\n" +
    ... b"Header1: Value1\r\n\r\n" +
    ... b"<a href=\"http://test.test/example\">Click me</a>")

The browser can have multiple tabs:

    >>> browser.load(url2)
    >>> browser.tabs
    [Tab(history=['http://test.test/example']), Tab(history=['http://test.test/example2'])]

    >>> lab7.print_tree(browser.tabs[1].document.node)
     <html>
       <body>
         <a href="http://test.test/example">
           'Click me'

    >>> lab7.print_tree(browser.tabs[1].document)
     DocumentLayout()
       BlockLayout(x=13, y=18, width=774, height=15.0)
         InlineLayout(x=13, y=18, width=774, height=15.0)
           LineLayout(x=13, y=18, width=774, height=15.0)
             TextLayout(x=13, y=20.25, width=60, height=12, font=Font size=12 weight=normal slant=roman style=None)
             TextLayout(x=85, y=20.25, width=24, height=12, font=Font size=12 weight=normal slant=roman style=None)

Tabs supports navigation---clicking on a link to navigate a tab to a new site:

    >>> browser.tabs[1].click(14, 21)
    >>> browser.tabs[1].url
    'http://test.test/example'
    >>> lab7.print_tree(browser.tabs[1].document.node)
     <html>
       <body>
         <div>
           'This is a test'
           <br>
           'Also a test'
           <br>
           'And this too'

The old page is now in the history of the tab:

    >>> browser.tabs[1]
    Tab(history=['http://test.test/example2', 'http://test.test/example'])

Navigating back restores the old page:

    >>> browser.tabs[1].go_back()
    >>> browser.tabs[1].url
    'http://test.test/example2'
    >>> lab7.print_tree(browser.tabs[1].document.node)
     <html>
       <body>
         <a href="http://test.test/example">
           'Click me'

Clicking on a non-clickable area of the page does nothing:

    >>> browser.tabs[1].click(1, 1)
    >>> browser.tabs[1].url
    'http://test.test/example2'

Testing Browser
===============

Clicking on a browser tab focuses it:

    >>> browser.active_tab
    1
    >>> browser.handle_click(test.Event(40, 1))
    >>> browser.active_tab
    0
    >>> browser.handle_click(test.Event(120, 1))
    >>> browser.active_tab
    1

Clicking on the address bar focuses it:

    >>> browser.handle_click(test.Event(50, 41))
    >>> browser.focus
    'address bar'

The back button works:

    >>> browser.tabs[1].history
    ['http://test.test/example2']
    >>> browser.handle_click(test.Event(14, 21 + 100))
    >>> browser.tabs[1].history
    ['http://test.test/example2', 'http://test.test/example']
    >>> browser.handle_click(test.Event(10, 40))
    >>> browser.tabs[1].history
    ['http://test.test/example2']

Pressing enter with text in the address bar works:

    >>> browser.handle_click(test.Event(50, 41))
    >>> browser.focus
    'address bar'
    >>> browser.address_bar = "http://test.test/example"
    >>> browser.handle_enter(test.Event(0, 0))
    >>> browser.tabs[1].history
    ['http://test.test/example2', 'http://test.test/example']

The home button works:

    >>> browser_engineering = 'https://browser.engineering/'
    >>> test.socket.respond(browser_engineering, b"HTTP/1.0 200 OK\r\n" +
    ... b"Header1: Value1\r\n\r\n" +
    ... b"Web Browser Engineering homepage")
    >>> browser.handle_click(test.Event(10, 10))
    >>> browser.tabs
    [Tab(history=['http://test.test/example']), Tab(history=['http://test.test/example2', 'http://test.test/example']), Tab(history=['https://browser.engineering/'])]
