Tests for WBE Chapter 2
=======================

Chapter 2 (Drawing to the Screen) is about how to get text parsed, laid out
and drawn on the screen, plus a very simple implementation of scrolling. This
file contains tests for this functionality.

    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab2

Testing `lex`
-------------

The lex function returns all text not contained in an HTML tag.

    >>> lab2.lex('<body>hello</body>')
    'hello'
    >>> lab2.lex('he<body>llo</body>')
    'hello'
    >>> lab2.lex('he<body>l</body>lo')
    'hello'
    >>> lab2.lex('he<body>l<div>l</div>o</body>')
    'hello'

Note that the tags do not have to match:

    >>> lab2.lex('he<body>l</div>lo')
    'hello'
    >>> lab2.lex('he<body>l<div>l</body>o</div>')
    'hello'

Breakpoints can be set after each character:
    >>> test.patch_breakpoint()

    >>> lab2.lex('abc')
    breakpoint(name='lex', 'a')
    breakpoint(name='lex', 'ab')
    breakpoint(name='lex', 'abc')
    'abc'

    >>> test.unpatch_breakpoint()


Testing `layout`
----------------

The layout function takes in text and outputs a display list. It uses WIDTH to
determine the maximum length of a line, HSTEP for the horizontal distance
between letters, and VSTEP for the vertical distance between lines. Each entry
in the display list is of the form (x, y, c), where x is the horizontal offset
to the right, y is the vertical offset downward, and c is the character to
draw.

Let's override those values to convenient ones that make it easy to do math
when testing:

    >>> lab2.WIDTH = 11
    >>> lab2.HSTEP = 1
    >>> lab2.VSTEP = 1

Both of these fit on one line:

    >>> lab2.layout("hello")
    [(1, 1, 'h'), (2, 1, 'e'), (3, 1, 'l'), (4, 1, 'l'), (5, 1, 'o')]
    >>> lab2.layout("hello mom")
    [(1, 1, 'h'), (2, 1, 'e'), (3, 1, 'l'), (4, 1, 'l'), (5, 1, 'o'), (6, 1, ' '), (7, 1, 'm'), (8, 1, 'o'), (9, 1, 'm')]

This does not though (notice that the 's' has a 2 in the y coordinate):

    >>> lab2.layout("hello moms")
    [(1, 1, 'h'), (2, 1, 'e'), (3, 1, 'l'), (4, 1, 'l'), (5, 1, 'o'), (6, 1, ' '), (7, 1, 'm'), (8, 1, 'o'), (9, 1, 'm'), (1, 2, 's')]

Layout also supports breakpoints after each addition to the display list:

    >>> test.patch_breakpoint()

    >>> lab2.layout("abc")
    breakpoint(name='layout', '[(1, 1, 'a')]')
    breakpoint(name='layout', '[(1, 1, 'a'), (2, 1, 'b')]')
    breakpoint(name='layout', '[(1, 1, 'a'), (2, 1, 'b'), (3, 1, 'c')]')
    [(1, 1, 'a'), (2, 1, 'b'), (3, 1, 'c')]

    >>> test.unpatch_breakpoint()

Testing `Browser`
-----------------

The Browser class defines a simple web browser, with methods to load,
draw to the screen, and scroll down.

Testing `Browser.load`
----------------------

Let's first mock a URL to load:

    >>> url = 'http://test.test/example1'
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\n" +
    ... b"Header1: Value1\r\n\r\n" +
    ... b"Body text")

Loading that URL results in a display list:

    >>> browser = lab2.Browser()
    >>> browser.load(lab2.URL(url))
    >>> browser.display_list
    [(1, 1, 'B'), (2, 1, 'o'), (3, 1, 'd'), (4, 1, 'y'), (5, 1, ' '), (6, 1, 't'), (7, 1, 'e'), (8, 1, 'x'), (9, 1, 't')]

And with breakpoints:

    >>> test.patch_breakpoint()

    >>> browser.load(lab2.URL(url))
    breakpoint(name='lex', 'B')
    breakpoint(name='lex', 'Bo')
    breakpoint(name='lex', 'Bod')
    breakpoint(name='lex', 'Body')
    breakpoint(name='lex', 'Body ')
    breakpoint(name='lex', 'Body t')
    breakpoint(name='lex', 'Body te')
    breakpoint(name='lex', 'Body tex')
    breakpoint(name='lex', 'Body text')
    breakpoint(name='layout', '[(1, 1, 'B')]')
    breakpoint(name='layout', '[(1, 1, 'B'), (2, 1, 'o')]')
    breakpoint(name='layout', '[(1, 1, 'B'), (2, 1, 'o'), (3, 1, 'd')]')
    breakpoint(name='layout', '[(1, 1, 'B'), (2, 1, 'o'), (3, 1, 'd'), (4, 1, 'y')]')
    breakpoint(name='layout', '[(1, 1, 'B'), (2, 1, 'o'), (3, 1, 'd'), (4, 1, 'y'), (5, 1, ' ')]')
    breakpoint(name='layout', '[(1, 1, 'B'), (2, 1, 'o'), (3, 1, 'd'), (4, 1, 'y'), (5, 1, ' '), (6, 1, 't')]')
    breakpoint(name='layout', '[(1, 1, 'B'), (2, 1, 'o'), (3, 1, 'd'), (4, 1, 'y'), (5, 1, ' '), (6, 1, 't'), (7, 1, 'e')]')
    breakpoint(name='layout', '[(1, 1, 'B'), (2, 1, 'o'), (3, 1, 'd'), (4, 1, 'y'), (5, 1, ' '), (6, 1, 't'), (7, 1, 'e'), (8, 1, 'x')]')
    breakpoint(name='layout', '[(1, 1, 'B'), (2, 1, 'o'), (3, 1, 'd'), (4, 1, 'y'), (5, 1, ' '), (6, 1, 't'), (7, 1, 'e'), (8, 1, 'x'), (9, 1, 't')]')
    breakpoint(name='draw')
    breakpoint(name='draw')
    breakpoint(name='draw')
    breakpoint(name='draw')
    breakpoint(name='draw')
    breakpoint(name='draw')
    breakpoint(name='draw')
    breakpoint(name='draw')
    breakpoint(name='draw')

    >>> test.unpatch_breakpoint()

Testing `Browser.scrolldown`
----------------------------

Let's install a mock canvas that prints out the x and y coordinates, plus
the text drawn:

    >>> test.patch_canvas()
    >>> browser = lab2.Browser()
    >>> browser.load(lab2.URL(url))
    create_text: x=1 y=1 text=B
    create_text: x=2 y=1 text=o
    create_text: x=3 y=1 text=d
    create_text: x=4 y=1 text=y
    create_text: x=5 y=1 text= 
    create_text: x=6 y=1 text=t
    create_text: x=7 y=1 text=e
    create_text: x=8 y=1 text=x
    create_text: x=9 y=1 text=t

SCROLL_STEP configures how much to scroll by each time. Let's set it to
a convenient value:

    >>> lab2.SCROLL_STEP = lab2.VSTEP + 2

After scrolling, all of the text is offscreen, so no text is output to the
canvas:

    >>> browser.scrolldown({})

Now let's load a different URL that provides three lines of text:

    >>> url = 'http://test.test/example2'
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\n" +
    ... b"Header1: Value1\r\n\r\n" +
    ... b"Body text that is longer")

    >>> browser = lab2.Browser()
    >>> browser.load(lab2.URL(url))
    create_text: x=1 y=1 text=B
    create_text: x=2 y=1 text=o
    create_text: x=3 y=1 text=d
    create_text: x=4 y=1 text=y
    create_text: x=5 y=1 text= 
    create_text: x=6 y=1 text=t
    create_text: x=7 y=1 text=e
    create_text: x=8 y=1 text=x
    create_text: x=9 y=1 text=t
    create_text: x=1 y=2 text= 
    create_text: x=2 y=2 text=t
    create_text: x=3 y=2 text=h
    create_text: x=4 y=2 text=a
    create_text: x=5 y=2 text=t
    create_text: x=6 y=2 text= 
    create_text: x=7 y=2 text=i
    create_text: x=8 y=2 text=s
    create_text: x=9 y=2 text= 
    create_text: x=1 y=3 text=l
    create_text: x=2 y=3 text=o
    create_text: x=3 y=3 text=n
    create_text: x=4 y=3 text=g
    create_text: x=5 y=3 text=e
    create_text: x=6 y=3 text=r

Scrolling down will now still show some of the text on-screen, because it took
up three lines, not just one:

    >>> browser.scrolldown({})
    create_text: x=1 y=-1 text= 
    create_text: x=2 y=-1 text=t
    create_text: x=3 y=-1 text=h
    create_text: x=4 y=-1 text=a
    create_text: x=5 y=-1 text=t
    create_text: x=6 y=-1 text= 
    create_text: x=7 y=-1 text=i
    create_text: x=8 y=-1 text=s
    create_text: x=9 y=-1 text= 
    create_text: x=1 y=0 text=l
    create_text: x=2 y=0 text=o
    create_text: x=3 y=0 text=n
    create_text: x=4 y=0 text=g
    create_text: x=5 y=0 text=e
    create_text: x=6 y=0 text=r
