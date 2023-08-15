Tests for WBE Chapter 5
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

The `layout_mode` method returns "inline" if the object is a `Text` node
or has all inline children, and otherwise returns "block".

    >>> parser = lab5.HTMLParser("text")
    >>> document_tree = parser.parse()
    >>> lab5.print_tree(document_tree)
     <html>
       <body>
         'text'
    >>> lmode = lambda n: lab5.BlockLayout(n, None, None).layout_mode()
    >>> lmode(document_tree)
    'block'
    >>> lmode(document_tree.children[0])
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

    >>> lmode(document_tree.children[0])
    'block'

The first div has block layout mode, because it has no children.

    >>> lmode(document_tree.children[0].children[0])
    'block'

The second div has inline layout mode, because it has one text child.

    >>> lmode(document_tree.children[0].children[1])
    'inline'

The third div has block layout mode, because it has one block and one inline child.

    >>> lmode(document_tree.children[0].children[2])
    'block'

The first span has block layout mode, even though spans are inline normally:

    >>> lmode(document_tree.children[0].children[3])
    'block'

The span has block layout mode, even though spans are inline normally:

    >>> lmode(document_tree.children[0].children[4])
    'inline'

Testing the layout tree
=======================

    >>> url = lab5.URL(test.socket.serve(sample_html))
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
       BlockLayout[block](x=13, y=18, width=774, height=60.0, node=<html>)
         BlockLayout[block](x=13, y=18, width=774, height=60.0, node=<body>)
           BlockLayout[block](x=13, y=18, width=774, height=0, node=<div>)
           BlockLayout[inline](x=13, y=18, width=774, height=20.0, node=<div>)
           BlockLayout[block](x=13, y=38.0, width=774, height=20.0, node=<div>)
             BlockLayout[block](x=13, y=38.0, width=774, height=0, node=<div>)
             BlockLayout[inline](x=13, y=38.0, width=774, height=20.0, node='text')
           BlockLayout[block](x=13, y=58.0, width=774, height=0, node=<span>)
           BlockLayout[inline](x=13, y=58.0, width=774, height=20.0, node=<span>)

    >>> browser.display_list #doctest
    [DrawText(top=21.0 left=13 bottom=37.0 text=text font=Font size=16 weight=normal slant=roman style=None), DrawText(top=41.0 left=13 bottom=57.0 text=text font=Font size=16 weight=normal slant=roman style=None), DrawText(top=61.0 left=13 bottom=77.0 text=text font=Font size=16 weight=normal slant=roman style=None)]

Testing background painting
===========================

`<pre>` elements have a gray background.

    >>> url = lab5.URL(test.socket.serve("<pre>pre text</pre>"))
    >>> browser = lab5.Browser()
    >>> browser.load(url)
    >>> lab5.print_tree(browser.nodes)
     <html>
       <body>
         <pre>
           'pre text'

    >>> lab5.print_tree(browser.document)
     DocumentLayout()
       BlockLayout[block](x=13, y=18, width=774, height=20.0, node=<html>)
         BlockLayout[block](x=13, y=18, width=774, height=20.0, node=<body>)
           BlockLayout[inline](x=13, y=18, width=774, height=20.0, node=<pre>)

The first display list entry is now a gray rect, since it's for a `<pre>` element:

    >>> browser.display_list[0]
    DrawRect(top=18 left=13 bottom=38.0 right=787 color=gray)


Testing breakpoints in layout
=============================

Tree-based layout also supports debugging breakpoints.

    >>> test.patch_breakpoint()

    >>> browser = lab5.Browser()
    >>> browser.load(url)
    breakpoint(name='layout_pre', 'DocumentLayout()')
    breakpoint(name='layout_pre', 'BlockLayout[block](x=None, y=None, width=None, height=None, node=<html>)')
    breakpoint(name='layout_pre', 'BlockLayout[block](x=None, y=None, width=None, height=None, node=<body>)')
    breakpoint(name='layout_pre', 'BlockLayout[inline](x=None, y=None, width=None, height=None, node=<pre>)')
    breakpoint(name='layout_post', 'BlockLayout[inline](x=13, y=18, width=774, height=20.0, node=<pre>)')
    breakpoint(name='layout_post', 'BlockLayout[block](x=13, y=18, width=774, height=20.0, node=<body>)')
    breakpoint(name='layout_post', 'BlockLayout[block](x=13, y=18, width=774, height=20.0, node=<html>)')
    breakpoint(name='layout_post', 'DocumentLayout()')
