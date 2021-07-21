`Tests for WBE Chapter 4
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

		>>> parser = lab4.HTMLParser("test")
		>>> lab4.print_tree(parser.parse())
		 <html>
		   <body>
		     'test'

		>>> parser = lab4.HTMLParser("<div>text</div>")
		>>> lab4.print_tree(parser.parse())
		 <html>
		   <body>
		     <div>
		       'text'