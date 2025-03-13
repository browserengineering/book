Tests for WBE Chapter 4
=======================

Chapter 4 (Constructing a Document Tree) adds support for the document tree
(i.e. the DOM).  This file contains tests for the additional functionality.

    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab4
    

Testing Tweaks
--------------

Once you get to adding attributes in Section 4.4, please make sure to
modify `Element.__repr__` to print those attributes.

    
4.2 Constructing the Tree
-------------------------

HTMLParser is a class whose constructor takes HTML body text as an
argument, and can parse it:

	>>> parser = lab4.HTMLParser("<html><body>test</body></html>")
    >>> root = parser.parse()
    >>> root.tag
    'html'
    >>> len(root.children)
    1
    >>> root.children[0].tag
    'body'
    >>> len(root.children[0].children)
    1
    >>> root.children[0].children[0].text
    'test'

Various mixes of open and close tags work:

	>>> parser = lab4.HTMLParser("<html><head></head><body>test <b>Test</b> test</body></html>")
    >>> root = parser.parse()
    >>> root.tag
    'html'
    >>> len(root.children)
    2
    >>> root.children[0].tag
    'head'
    >>> len(root.children[0].children)
    0
    >>> root.children[1].tag
    'body'
    >>> len(root.children[1].children)
    3
    >>> root.children[1].children[0].text
    'test '
    >>> root.children[1].children[1].tag
    'b'
    >>> root.children[1].children[2].text
    ' test'


4.3 Debugging a Parser
----------------------

We can now print the HTML tree:

	>>> parser = lab4.HTMLParser("<html><head></head><body>test <b>Test</b> test</body></html>")
    >>> lab4.print_tree(parser.parse())
     <html>
       <head>
       <body>
         'test '
         <b>
           'Test'
         ' test'

Doctype nodes are dropped:

	>>> parser = lab4.HTMLParser("<!doctype html><html><body>test</body></html>")
    >>> lab4.print_tree(parser.parse())
     <html>
       <body>
         'test'

Whitespace nodes are also skipped:

	>>> parser = lab4.HTMLParser("<!doctype html> <html> <body> <b>test</b> </body> </html>")
    >>> lab4.print_tree(parser.parse())
     <html>
       <body>
         <b>
           'test'
           

4.4 Self-closing Tags
---------------------

Self-closing tags should self-close:

	>>> parser = lab4.HTMLParser("<html><head><meta><link><base></head></html>")
    >>> lab4.print_tree(parser.parse())
     <html>
       <head>
         <meta>
         <link>
         <base>

	>>> parser = lab4.HTMLParser("<html><body>a<br>b<br>c<br>d</html>")
    >>> lab4.print_tree(parser.parse())
     <html>
       <body>
         'a'
         <br>
         'b'
         <br>
         'c'
         <br>
         'd'

Attributes can be set on tags:

	>>> parser = lab4.HTMLParser("<div name1=value1 name2=value2>text</div>")
	>>> lab4.print_tree(parser.parse())
	 <html>
	   <body>
	     <div name1="value1" name2="value2">
	       'text'

Tag and attribute names are lower-cased:

    >>> parser = lab4.HTMLParser('<A HREF=my-url attr=my-attr>')
    >>> document = parser.parse()
    >>> lab4.print_tree(document)
     <html>
       <body>
         <a href="my-url" attr="my-attr">
         
         
4.5 Using the Node Tree
-----------------------

First, let's test that basic layout works as expected:

	>>> parser = lab4.HTMLParser("<p>text</p>")
	>>> tree = parser.parse()
    >>> lo = lab4.Layout(tree)
    >>> lo.display_list
    [(13, 20.25, 'text', Font size=12 weight=normal slant=roman style=None)]

Moreover, layout should work even if we don't use the
explicitly-supported tags like `p`:

	>>> parser = lab4.HTMLParser("<div>text</div>")
	>>> tree = parser.parse()
    >>> lo = lab4.Layout(tree)
    >>> lo.display_list
    [(13, 20.25, 'text', Font size=12 weight=normal slant=roman style=None)]


4.6 Handling Author Errors
--------------------------

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
