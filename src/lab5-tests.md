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

    >>> sample_html = "<div></div><div>text</div><div><div></div>text</div><span></span><span>text</span>"
    >>> parser = lab5.HTMLParser(
    ... sample_html)
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
     DocumentLayout
       BlockLayout(x=13, y=18, width=774, height=57.59999999999998
         BlockLayout(x=13, y=18, width=774, height=57.59999999999998
           BlockLayout(x=13, y=18, width=774, height=0
           InlineLayout(x=13, y=18, width=774, height=19.199999999999996 display_list=[(13, 20.4, 'text', Font size=16 weight=normal slant=roman style=None)]
           BlockLayout(x=13, y=37.199999999999996, width=774, height=19.199999999999996
             BlockLayout(x=13, y=37.199999999999996, width=774, height=0
             InlineLayout(x=13, y=37.199999999999996, width=774, height=19.199999999999996 display_list=[(13, 39.599999999999994, 'text', Font size=16 weight=normal slant=roman style=None)]
           BlockLayout(x=13, y=56.39999999999999, width=774, height=0
           InlineLayout(x=13, y=56.39999999999999, width=774, height=19.19999999999999 display_list=[(13, 58.79999999999998, 'text', Font size=16 weight=normal slant=roman style=None)]

