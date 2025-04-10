Tests for WBE Chapter 7
=======================

Chapter 7 (Handling Buttons and Links) introduces hit testing, navigation
through link clicks, and browser chrome for the URL bar and tabs.

    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab7

7.2 Line Layout, Redux
----------------------

Let's load a page with multiple lines (using `<br>`):

    >>> url = test.socket.serve(
    ...   "<div>This is a test<br>Also a test<br>"
    ...   "And this too</div>")
    >>> browser = lab7.Browser()
    >>> browser.new_tab(lab7.URL(url))
    >>> browser.tabs
    [Tab(history=[URL(scheme=http, host=test, port=80, path='/page0')])]
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
               TextLayout(x=13, y=20.25, width=48, height=12, word=This)
               TextLayout(x=73, y=20.25, width=24, height=12, word=is)
               TextLayout(x=109, y=20.25, width=12, height=12, word=a)
               TextLayout(x=133, y=20.25, width=48, height=12, word=test)
             LineLayout(x=13, y=33.0, width=774, height=15.0)
               TextLayout(x=13, y=35.25, width=48, height=12, word=Also)
               TextLayout(x=73, y=35.25, width=12, height=12, word=a)
               TextLayout(x=97, y=35.25, width=48, height=12, word=test)
             LineLayout(x=13, y=48.0, width=774, height=15.0)
               TextLayout(x=13, y=50.25, width=36, height=12, word=And)
               TextLayout(x=61, y=50.25, width=48, height=12, word=this)
               TextLayout(x=121, y=50.25, width=36, height=12, word=too)

Whereas in chapter 6 there is no direct layout tree representation of
text.


7.3 Click Handling
------------------

Here's a web page with a link to that previous page:

    >>> url2 = test.socket.serve("<a href=" + url + ">Click me</a>")
    >>> browser = lab7.Browser()
    >>> browser.new_tab(lab7.URL(url2))
    >>> lab7.print_tree(browser.tabs[0].document)
     DocumentLayout()
       BlockLayout[block](x=13, y=18, width=774, height=15.0)
         BlockLayout[inline](x=13, y=18, width=774, height=15.0)
           LineLayout(x=13, y=18, width=774, height=15.0)
             TextLayout(x=13, y=20.25, width=60, height=12, word=Click)
             TextLayout(x=85, y=20.25, width=24, height=12, word=me)

Let's click on the link to test navigation. Here we need to do
something slightly odd to handle the introduction of tabs later in
this chapter:

    >>> tab = browser.tabs[0] if hasattr(browser, "tabs") else browser

Clicking on a non-clickable area of the page does nothing:

    >>> tab.click(1, 1)
    >>> tab.url
    URL(scheme=http, host=test, port=80, path='/page1')
    
Clicking the link navigates to a new page:

    >>> tab.url
    URL(scheme=http, host=test, port=80, path='/page1')
    >>> tab.click(15, 25)
    >>> tab.url
    URL(scheme=http, host=test, port=80, path='/page0')


7.4 Multiple Pages
------------------

The browser can have multiple tabs:

    >>> browser = lab7.Browser()
    >>> browser.new_tab(lab7.URL(url))
    >>> browser.new_tab(lab7.URL(url2))
    >>> browser.tabs #doctest: +NORMALIZE_WHITESPACE
    [Tab(history=[URL(scheme=http, host=test, port=80, path='/page0')]),
     Tab(history=[URL(scheme=http, host=test, port=80, path='/page1')])]

Here's the first page:

    >>> lab7.print_tree(browser.tabs[0].document)
     DocumentLayout()
       BlockLayout[block](x=13, y=18, width=774, height=45.0)
         BlockLayout[block](x=13, y=18, width=774, height=45.0)
           BlockLayout[inline](x=13, y=18, width=774, height=45.0)
             LineLayout(x=13, y=18, width=774, height=15.0)
               TextLayout(x=13, y=20.25, width=48, height=12, word=This)
               TextLayout(x=73, y=20.25, width=24, height=12, word=is)
               TextLayout(x=109, y=20.25, width=12, height=12, word=a)
               TextLayout(x=133, y=20.25, width=48, height=12, word=test)
             LineLayout(x=13, y=33.0, width=774, height=15.0)
               TextLayout(x=13, y=35.25, width=48, height=12, word=Also)
               TextLayout(x=73, y=35.25, width=12, height=12, word=a)
               TextLayout(x=97, y=35.25, width=48, height=12, word=test)
             LineLayout(x=13, y=48.0, width=774, height=15.0)
               TextLayout(x=13, y=50.25, width=36, height=12, word=And)
               TextLayout(x=61, y=50.25, width=48, height=12, word=this)
               TextLayout(x=121, y=50.25, width=36, height=12, word=too)

Here's the second page:

    >>> lab7.print_tree(browser.tabs[1].document)
     DocumentLayout()
       BlockLayout[block](x=13, y=18, width=774, height=15.0)
         BlockLayout[inline](x=13, y=18, width=774, height=15.0)
           LineLayout(x=13, y=18, width=774, height=15.0)
             TextLayout(x=13, y=20.25, width=60, height=12, word=Click)
             TextLayout(x=85, y=20.25, width=24, height=12, word=me)
             

7.5 Browser Chrome
------------------

Clicking on a browser tab focuses it:

    >>> browser.active_tab
    Tab(history=[URL(scheme=http, host=test, port=80, path='/page1')])
    >>> rect = browser.chrome.tab_rect(0)
    >>> browser.handle_click(test.Event(rect.left + 1, rect.top + 1))
    >>> browser.active_tab
    Tab(history=[URL(scheme=http, host=test, port=80, path='/page0')])
    >>> rect = browser.chrome.tab_rect(1)
    >>> browser.handle_click(test.Event(rect.left + 1, rect.top + 1))
    >>> browser.active_tab
    Tab(history=[URL(scheme=http, host=test, port=80, path='/page1')])

Click on the "new tab" button also works:

    >>> browser_engineering = 'https://browser.engineering/'
    >>> test.socket.respond_ok(browser_engineering, "Web Browser Engineering homepage")
    >>> rect = browser.chrome.newtab_rect
    >>> browser.handle_click(test.Event(rect.left + 1, rect.top + 1))
    >>> browser.tabs #doctest: +NORMALIZE_WHITESPACE
    [Tab(history=[URL(scheme=http, host=test, port=80, path='/page0')]),
     Tab(history=[URL(scheme=http, host=test, port=80, path='/page1')]),
     Tab(history=[URL(scheme=https, host=browser.engineering, port=443, path='/')])]
    
    
7.6 Navigation History
----------------------

When you navigate with links, you add to the browser history

    >>> browser.tabs[1].click(14, 21)
    >>> browser.tabs[1].url
    URL(scheme=http, host=test, port=80, path='/page0')
    >>> browser.tabs[1] #doctest: +NORMALIZE_WHITESPACE
    Tab(history=[URL(scheme=http, host=test, port=80, path='/page1'),
                 URL(scheme=http, host=test, port=80, path='/page0')])

Navigating back restores the old page:

    >>> browser.tabs[1].go_back()
    >>> browser.tabs[1].url
    URL(scheme=http, host=test, port=80, path='/page1')
    >>> lab7.print_tree(browser.tabs[1].document.node)
     <html>
       <body>
         <a href="http://test/page0">
           'Click me'


7.7 Editing the URL
-------------------

Clicking on the address bar focuses it:

    >>> browser.handle_click(test.Event(50, 51))
    >>> browser.chrome.focus
    'address bar'

The back button works:

    >>> browser.active_tab = browser.tabs[1]
    >>> browser.tabs[1].url
    URL(scheme=http, host=test, port=80, path='/page1')
    >>> browser.tabs[1].history
    [URL(scheme=http, host=test, port=80, path='/page1')]
    >>> browser.tabs[1].click(15, 25)
    >>> browser.tabs[1].url
    URL(scheme=http, host=test, port=80, path='/page0')
    >>> browser.tabs[1].history #doctest: +NORMALIZE_WHITESPACE
    [URL(scheme=http, host=test, port=80, path='/page1'),
     URL(scheme=http, host=test, port=80, path='/page0')]
    >>> rect = browser.chrome.back_rect
    >>> browser.handle_click(test.Event(rect.left + 1, rect.top + 1))
    >>> browser.tabs[1].url
    URL(scheme=http, host=test, port=80, path='/page1')
    >>> browser.tabs[1].history
    [URL(scheme=http, host=test, port=80, path='/page1')]

Pressing enter with text in the address bar works:

    >>> browser.handle_click(test.Event(50, 51))
    >>> browser.chrome.focus
    'address bar'
    >>> browser.chrome.address_bar = "http://test/page0"
    >>> browser.handle_enter(test.Event(0, 0))
    >>> browser.tabs[1].history #doctest: +NORMALIZE_WHITESPACE
    [URL(scheme=http, host=test, port=80, path='/page1'),
     URL(scheme=http, host=test, port=80, path='/page0')]
