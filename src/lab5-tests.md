`Tests for WBE Chapter 5
=======================

Chapter 5 (Laying Out Pages) introduces inline and block layout modes on
the document tree, and introduces the concept of the document tree, and
adds support for drawing the background colors of document tree elements.

    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab5

Testing layout_mode
===================

The ``layout_mode` function returns "inline" if the object is a `Text` node
or has all inline children, and otherwise returns "block".

    >>> parser = lab5.HTMLParser("text")
    >>> document_tree = parser.parse()
    >>> lab5.print_tree(document_tree)
     <html>
       <body>
         'text'
    >>> lab5.layout_mode(document_tree)
    'block'
    >>> lab5.layout_mode(document_tree.children[0])
    'inline'
    
Here's some tests on a bigger, more complex document

    >>> sample_html = "<div></div><div>text</div><div><div></div>text</div><span></span><span>text</span>"
    >>> parser = lab5.HTMLParser(sample_html)
    >>> document_tree = parser.parse()
    >>> lab5.print_tree(document_tree)
     <html>
       <body>
         <div>
         <div>
           'text'
         <div>
           <div>
           'text'
         <span>
         <span>
           'text'

The body element has block layout mode, because it has two block-element children.

    >>> lab5.layout_mode(document_tree.children[0])
    'block'

The first div has block layout mode, because it has no children.

    >>> lab5.layout_mode(document_tree.children[0].children[0])
    'block'

The second div has inline layout mode, because it has one text child.

    >>> lab5.layout_mode(document_tree.children[0].children[1])
    'inline'

The third div has block layout mode, because it has one block and one inline child.

    >>> lab5.layout_mode(document_tree.children[0].children[2])
    'block'

The first span has block layout mode, even though spans are inline normally:

    >>> lab5.layout_mode(document_tree.children[0].children[3])
    'block'

The span has block layout mode, even though spans are inline normally:

    >>> lab5.layout_mode(document_tree.children[0].children[4])
    'inline'

Testing the layout tree
=======================

    >>> url = 'http://test.test/example1'
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\n" +
    ... b"Header1: Value1\r\n\r\n" +
    ... sample_html.encode("utf-8"))

    >>> browser = lab5.Browser()
    >>> browser.load(url)
    >>> lab5.print_tree(browser.nodes)
     <html>
       <body>
         <div>
         <div>
           'text'
         <div>
           <div>
           'text'
         <span>
         <span>
           'text'

    >>> lab5.print_tree(browser.document)
     DocumentLayout()
       BlockLayout(x=13, y=18, width=774, height=57.59999999999998)
         BlockLayout(x=13, y=18, width=774, height=57.59999999999998)
           BlockLayout(x=13, y=18, width=774, height=0)
           InlineLayout(x=13, y=18, width=774, height=19.199999999999996)
           BlockLayout(x=13, y=37.199999999999996, width=774, height=19.199999999999996)
             BlockLayout(x=13, y=37.199999999999996, width=774, height=0)
             InlineLayout(x=13, y=37.199999999999996, width=774, height=19.199999999999996)
           BlockLayout(x=13, y=56.39999999999999, width=774, height=0)
           InlineLayout(x=13, y=56.39999999999999, width=774, height=19.19999999999999)

    >>> browser.display_list
    [DrawText(top=20.4 left=13 bottom=36.4 text=text font=Font size=16 weight=normal slant=roman style=None), DrawText(top=39.599999999999994 left=13 bottom=55.599999999999994 text=text font=Font size=16 weight=normal slant=roman style=None), DrawText(top=58.79999999999998 left=13 bottom=74.79999999999998 text=text font=Font size=16 weight=normal slant=roman style=None)]

Testing background painting
===========================

`<pre>` elements have a gray background.

    >>> url = 'http://test.test/example2'
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\n" +
    ... b"Header1: Value1\r\n\r\n" +
    ... b"<pre>pre text</pre>")

    >>> browser = lab5.Browser()
    >>> browser.load(url)
    >>> lab5.print_tree(browser.nodes)
     <html>
       <body>
         <pre>
           'pre text'

    >>> lab5.print_tree(browser.document)
     DocumentLayout()
       BlockLayout(x=13, y=18, width=774, height=19.199999999999996)
         BlockLayout(x=13, y=18, width=774, height=19.199999999999996)
           InlineLayout(x=13, y=18, width=774, height=19.199999999999996)

The first display list entry is now a gray rect, since it's for a `<pre>` element:

    >>> browser.display_list[0]
    DrawRect(top=18 left=13 bottom=37.199999999999996 right=787 color=gray)


Testing breakpoints in layout
=============================

Tree-based layout also supports debugging breakpoints.

    >>> test.patch_breakpoint()

    >>> browser = lab5.Browser()
    >>> browser.load(url)
    breakpoint(name='layout_pre', 'DocumentLayout')
    breakpoint(name='layout_pre', 'BlockLayout(x=None, y=None, width=None, height=None)')
    breakpoint(name='layout_pre', 'BlockLayout(x=None, y=None, width=None, height=None)')
    breakpoint(name='layout_pre', 'InlineLayout(x=None, y=None, width=None, height=None)')
    breakpoint(name='layout_post', 'InlineLayout(x=13, y=18, width=774, height=19.199999999999996)')
    breakpoint(name='layout_post', 'BlockLayout(x=13, y=18, width=774, height=19.199999999999996)')
    breakpoint(name='layout_post', 'BlockLayout(x=13, y=18, width=774, height=19.199999999999996)')
    breakpoint(name='layout_post', 'DocumentLayout()')
