Tests for WBE Chapter 3
=======================

Chapter 3 (Formatting Text) adds on font metrics and simple font styling via
HTML tags. This file contains tests for the additional functionality.

    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab3

Testing `lex`
-------------

The `lex` function in chapter three has been beefed up to return an array
of `Tag` or `Text` objects, rather than just the stream of characters from the
input.

    >>> lab3.lex('<body>hello</body>')
    [Tag('body'), Text('hello''), Tag('/body')]
    >>> lab3.lex('he<body>llo</body>')
    [Text('he''), Tag('body'), Text('llo''), Tag('/body')]
    >>> lab3.lex('he<body>l</body>lo')
    [Text('he''), Tag('body'), Text('l''), Tag('/body'), Text('lo'')]
    >>> lab3.lex('he<body>l<div>l</div>o</body>')
    [Text('he''), Tag('body'), Text('l''), Tag('div'), Text('l''), Tag('/div'), Text('o''), Tag('/body')]

Note that the tags do not have to match:

    >>> lab3.lex('he<body>l</div>lo')
    [Text('he''), Tag('body'), Text('l''), Tag('/div'), Text('lo'')]
    >>> lab3.lex('he<body>l<div>l</body>o</div>')
    [Text('he''), Tag('body'), Text('l''), Tag('div'), Text('l''), Tag('/body'), Text('o''), Tag('/div')]

Testing `Layout`
----------------

This chapter also creates a Layout class to output a display list that can
format text. However, note that this test doesn't use real tkinter fonts, but
rather a mock font that has faked metrics.

    >>> lab3.Layout(lab3.lex("abc")).display_list
    [(13, 19.6, 'abc', Font size=16 weight=normal slant=roman style=None)]

    >>> lab3.Layout(lab3.lex("<b>abc</b>")).display_list
    [(13, 19.6, 'abc', Font size=16 weight=bold slant=roman style=None)]
    
    >>> lab3.Layout(lab3.lex("<big>abc</big>")).display_list
    [(13, 20.0, 'abc', Font size=20 weight=normal slant=roman style=None)]

    >>> lab3.Layout(lab3.lex("<big><big>abc</big></big>")).display_list
    [(13, 20.4, 'abc', Font size=24 weight=normal slant=roman style=None)]

    >>> lab3.Layout(lab3.lex("<big><big><i>abc</i></big></big>")).display_list
    [(13, 20.4, 'abc', Font size=24 weight=normal slant=italic style=None)]

    >>> lab3.Layout(lab3.lex("<big><big><i>abc</i></big>def</big>")).display_list
    [(13, 20.4, 'abc', Font size=24 weight=normal slant=italic style=None), (109, 22.4, 'def', Font size=20 weight=normal slant=roman style=None)]

Breakpoints can be set after each layout:

    >>> test.patch_breakpoint()

    >>> layout = lab3.Layout(lab3.lex("abc"))
    breakpoint: name=initial_y value1=18 value2=[(13, 'abc', Font size=16 weight=normal slant=roman style=None)]
    breakpoint: name=metrics value1=[{'ascent': 8.0, 'descent': 8.0, 'linespace': 32}]
    breakpoint: name=max_ascent value1=8.0
    breakpoint: name=aligned value1=[(13, 19.6, 'abc', Font size=16 weight=normal slant=roman style=None)]
    breakpoint: name=max_descent value1=8.0
    breakpoint: name=final_y value1=37.2
    
    >>> test.unpatch_breakpoint()

Testing `Browser`
-----------------

Now let's test integration of layout into the Browser class.

    >>> url = 'http://test.test/example2'
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\n" +
    ... b"Header1: Value1\r\n\r\n" +
    ... b"<small>abc<i>def</i></small>")
    >>> browser = lab3.Browser()
    >>> browser.load(url)

Testing the display list output of this URL:

    >>> browser.display_list
    [(13, 19.4, 'abc', Font size=14 weight=normal slant=roman style=None), (69, 19.4, 'def', Font size=14 weight=normal slant=italic style=None)]

And the canvas:

    >>> test.patch_canvas()
    >>> browser = lab3.Browser()
    >>> browser.load(url)
    create_text: x=13 y=19.4 text=abc font=Font size=14 weight=normal slant=roman style=None anchor=nw
    create_text: x=69 y=19.4 text=def font=Font size=14 weight=normal slant=italic style=None anchor=nw
    >>> test.unpatch_canvas()

And with breakpoints:

    >>> test.patch_breakpoint()

    >>> browser.load(url)
    breakpoint: name=initial_y value1=18 value2=[(13, 'abc', Font size=14 weight=normal slant=roman style=None), (69, 'def', Font size=14 weight=normal slant=italic style=None)]
    breakpoint: name=metrics value1=[{'ascent': 7.0, 'descent': 7.0, 'linespace': 28}, {'ascent': 7.0, 'descent': 7.0, 'linespace': 28}]
    breakpoint: name=max_ascent value1=7.0
    breakpoint: name=aligned value1=[(13, 19.4, 'abc', Font size=14 weight=normal slant=roman style=None)]
    breakpoint: name=aligned value1=[(13, 19.4, 'abc', Font size=14 weight=normal slant=roman style=None), (69, 19.4, 'def', Font size=14 weight=normal slant=italic style=None)]
    breakpoint: name=max_descent value1=7.0
    breakpoint: name=final_y value1=34.8
    create_text: x=13 y=19.4 text=abc font=Font size=14 weight=normal slant=roman style=None anchor=nw
    create_text: x=69 y=19.4 text=def font=Font size=14 weight=normal slant=italic style=None anchor=nw

    >>> test.unpatch_breakpoint()
