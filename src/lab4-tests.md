Tests for WBE Chapter 4
=======================

Chapter 4 (Constructing a Document Tree) adds support for the document tree
(i.e. the DOM).  This file contains tests for the additional functionality.

    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab4

Testing HTMLParser
==================

HTMLParser is a class whose constructor takes HTML body text as an argument, and
can parse it.

The implicit `html` and `body` (and `head` when needed) tags are added:

	>>> parser = lab4.HTMLParser("<html><body>test</body></html>")
	>>> lab4.print_tree(parser.parse())
	 <html>
	   <body>
	     'test'

Missing tags are added in:

	>>> parser = lab4.HTMLParser("test")
	>>> lab4.print_tree(parser.parse())
	 <html>
	   <body>
	     'test'

	>>> parser = lab4.HTMLParser("<body>test")
	>>> lab4.print_tree(parser.parse())
	 <html>
	   <body>
	     'test'

Head tags are put in the head, and other tags, such as `div`, are put
in the body. Also, tags such as `base` are self-closing:

	>>> parser = lab4.HTMLParser("<base><basefont></basefont><title></title><div></div>")
	>>> lab4.print_tree(parser.parse())
	 <html>
	   <head>
	     <base>
	     <basefont>
	     <title>
 	   <body>
 	     <div>

Missing end tags are added:

	>>> parser = lab4.HTMLParser("<div>text")
	>>> lab4.print_tree(parser.parse())
	 <html>
	   <body>
	     <div>
	       'text'

Attributes can be set on tags:

	>>> parser = lab4.HTMLParser("<div name1=value1 name2=value2>text</div>")
	>>> lab4.print_tree(parser.parse())
	 <html>
	   <body>
	     <div name1="value1" name2="value2">
	       'text'

Testing Layout
==============

First, let's test that basic layout works as expected:

	>>> parser = lab4.HTMLParser("<p>text</p>")
	>>> tree = parser.parse()
    >>> lo = lab4.Layout(tree)
    >>> lo.display_list
    [(13, 21.0, 'text', Font size=16 weight=normal slant=roman style=None)]

Moreover, layout should work even if we don't use the
explicitly-supported tags like `p`:

	>>> parser = lab4.HTMLParser("<div>text</div>")
	>>> tree = parser.parse()
    >>> lo = lab4.Layout(tree)
    >>> lo.display_list
    [(13, 21.0, 'text', Font size=16 weight=normal slant=roman style=None)]
