Tests for WBE Chapter 7
=======================

Chapter 7 (Handling Buttons and Links) introduces hit testing, navigation
through link clicks, and browser chrome for the URL bar and tabs.

    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab7

Testing LineLayout and TextLayout
=================================

    >>> url = lab7.URL(test.socket.serve(
    ...   "<div>This is a test<br>Also a test<br>And this too</div>"))

    >>> browser = lab7.Browser()
    >>> browser.new_tab(url)
    >>> browser.tabs
    [Tab(history=[URL(scheme=http, host=test, port=80, path='/0')])]
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
       BlockLayout[block](x=13, y=18, width=774, height=45.0)
         BlockLayout[block](x=13, y=18, width=774, height=45.0)
           BlockLayout[inline](x=13, y=18, width=774, height=45.0)
             LineLayout(x=13, y=18, width=774, height=15.0)
               TextLayout(x=13, y=20.25, width=48, height=12, node='This is a test', word=This)
               TextLayout(x=73, y=20.25, width=24, height=12, node='This is a test', word=is)
               TextLayout(x=109, y=20.25, width=12, height=12, node='This is a test', word=a)
               TextLayout(x=133, y=20.25, width=48, height=12, node='This is a test', word=test)
             LineLayout(x=13, y=33.0, width=774, height=15.0)
               TextLayout(x=13, y=35.25, width=48, height=12, node='Also a test', word=Also)
               TextLayout(x=73, y=35.25, width=12, height=12, node='Also a test', word=a)
               TextLayout(x=97, y=35.25, width=48, height=12, node='Also a test', word=test)
             LineLayout(x=13, y=48.0, width=774, height=15.0)
               TextLayout(x=13, y=50.25, width=36, height=12, node='And this too', word=And)
               TextLayout(x=61, y=50.25, width=48, height=12, node='And this too', word=this)
               TextLayout(x=121, y=50.25, width=36, height=12, node='And this too', word=too)

Whereas in chapter 6 there is no direct layout tree representation of text.

Testing Tab
===========

    >>> url2 = lab7.URL(test.socket.serve(
    ...   "<a href=\"http://test/0\">Click me</a>"))

The browser can have multiple tabs:

    >>> browser.new_tab(url2)
    >>> browser.tabs #doctest: +NORMALIZE_WHITESPACE
    [Tab(history=[URL(scheme=http, host=test, port=80, path='/0')]),
     Tab(history=[URL(scheme=http, host=test, port=80, path='/1')])]

    >>> lab7.print_tree(browser.tabs[1].document.node)
     <html>
       <body>
         <a href="http://test/0">
           'Click me'

    >>> lab7.print_tree(browser.tabs[1].document)
     DocumentLayout()
       BlockLayout[block](x=13, y=18, width=774, height=15.0)
         BlockLayout[inline](x=13, y=18, width=774, height=15.0)
           LineLayout(x=13, y=18, width=774, height=15.0)
             TextLayout(x=13, y=20.25, width=60, height=12, node='Click me', word=Click)
             TextLayout(x=85, y=20.25, width=24, height=12, node='Click me', word=me)

Tabs supports navigation---clicking on a link to navigate a tab to a new site:

    >>> browser.tabs[1].click(14, 21)
    >>> browser.tabs[1].url
    URL(scheme=http, host=test, port=80, path='/0')
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

    >>> browser.tabs[1] #doctest: +NORMALIZE_WHITESPACE
    Tab(history=[URL(scheme=http, host=test, port=80, path='/1'),
                 URL(scheme=http, host=test, port=80, path='/0')])

Navigating back restores the old page:

    >>> browser.tabs[1].go_back()
    >>> browser.tabs[1].url
    URL(scheme=http, host=test, port=80, path='/1')
    >>> lab7.print_tree(browser.tabs[1].document.node)
     <html>
       <body>
         <a href="http://test/0">
           'Click me'

Clicking on a non-clickable area of the page does nothing:

    >>> browser.tabs[1].click(1, 1)
    >>> browser.tabs[1].url
    URL(scheme=http, host=test, port=80, path='/1')

Testing Browser
===============

Clicking on a browser tab focuses it:

    >>> browser.active_tab
    Tab(history=[URL(scheme=http, host=test, port=80, path='/1')])
    >>> rect = browser.chrome.tab_rect(0)
    >>> browser.handle_click(test.Event(rect.left + 1, rect.top + 1))
    >>> browser.active_tab
    Tab(history=[URL(scheme=http, host=test, port=80, path='/0')])
    >>> rect = browser.chrome.tab_rect(1)
    >>> browser.handle_click(test.Event(rect.left + 1, rect.top + 1))
    >>> browser.active_tab
    Tab(history=[URL(scheme=http, host=test, port=80, path='/1')])

Clicking on the address bar focuses it:

    >>> browser.handle_click(test.Event(50, 51))
    >>> browser.chrome.focus
    'address bar'

The back button works:

    >>> browser.tabs[1].history
    [URL(scheme=http, host=test, port=80, path='/1')]
    >>> browser.handle_click(test.Event(14, browser.chrome.bottom + 21))
    >>> browser.tabs[1].history #doctest: +NORMALIZE_WHITESPACE
    [URL(scheme=http, host=test, port=80, path='/1'),
     URL(scheme=http, host=test, port=80, path='/0')]
    >>> rect = browser.chrome.back_rect
    >>> browser.handle_click(test.Event(rect.left + 1, rect.top + 1))
    >>> browser.tabs[1].history
    [URL(scheme=http, host=test, port=80, path='/1')]

Pressing enter with text in the address bar works:

    >>> browser.handle_click(test.Event(50, 51))
    >>> browser.chrome.focus
    'address bar'
    >>> browser.chrome.address_bar = "http://test/0"
    >>> browser.handle_enter(test.Event(0, 0))
    >>> browser.tabs[1].history #doctest: +NORMALIZE_WHITESPACE
    [URL(scheme=http, host=test, port=80, path='/1'),
     URL(scheme=http, host=test, port=80, path='/0')]

The home button works:

    >>> browser_engineering = 'https://browser.engineering/'
    >>> test.socket.respond(browser_engineering, b"HTTP/1.0 200 OK\r\n" +
    ... b"Header1: Value1\r\n\r\n" +
    ... b"Web Browser Engineering homepage")
    >>> browser.handle_click(test.Event(10, 10))
    >>> browser.tabs #doctest: +NORMALIZE_WHITESPACE
    [Tab(history=[URL(scheme=http, host=test, port=80, path='/0')]),
     Tab(history=[URL(scheme=http, host=test, port=80, path='/1'),
                  URL(scheme=http, host=test, port=80, path='/0')]),
     Tab(history=[URL(scheme=https, host=browser.engineering, port=443, path='/')])]
