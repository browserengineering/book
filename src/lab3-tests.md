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
    [Tag('body'), Text('hello'), Tag('/body')]
    >>> lab3.lex('he<body>llo</body>')
    [Text('he'), Tag('body'), Text('llo'), Tag('/body')]
    >>> lab3.lex('he<body>l</body>lo')
    [Text('he'), Tag('body'), Text('l'), Tag('/body'), Text('lo')]
    >>> lab3.lex('he<body>l<div>l</div>o</body>')
    [Text('he'), Tag('body'), Text('l'), Tag('div'), Text('l'), Tag('/div'), Text('o'), Tag('/body')]

Note that the tags do not have to match:

    >>> lab3.lex('he<body>l</div>lo')
    [Text('he'), Tag('body'), Text('l'), Tag('/div'), Text('lo')]
    >>> lab3.lex('he<body>l<div>l</body>o</div>')
    [Text('he'), Tag('body'), Text('l'), Tag('div'), Text('l'), Tag('/body'), Text('o'), Tag('/div')]

Testing `Layout`
----------------

This chapter also creates a Layout class to output a display list that can
format text. However, note that this test doesn't use real tkinter fonts, but
rather a mock font that has faked metrics.

    >>> lab3.Layout(lab3.lex("abc")).display_list
    [(13, 20.25, 'abc', Font size=12 weight=normal slant=roman style=None)]

    >>> lab3.Layout(lab3.lex("<b>abc</b>")).display_list
    [(13, 20.25, 'abc', Font size=12 weight=bold slant=roman style=None)]
    
    >>> lab3.Layout(lab3.lex("<big>abc</big>")).display_list
    [(13, 21.0, 'abc', Font size=16 weight=normal slant=roman style=None)]

    >>> lab3.Layout(lab3.lex("<big><big>abc</big></big>")).display_list
    [(13, 21.75, 'abc', Font size=20 weight=normal slant=roman style=None)]

    >>> lab3.Layout(lab3.lex("<big><big><i>abc</i></big></big>")).display_list
    [(13, 21.75, 'abc', Font size=20 weight=normal slant=italic style=None)]

    >>> lab3.Layout(lab3.lex("<big><big><i>abc</i></big>def</big>")).display_list #doctest: +NORMALIZE_WHITESPACE
    [(13, 21.75, 'abc', Font size=20 weight=normal slant=italic style=None),
     (93, 24.75, 'def', Font size=16 weight=normal slant=roman style=None)]

Breakpoints can be set after each layout:

    >>> test.patch_breakpoint()

    >>> layout = lab3.Layout(lab3.lex("abc"))
    breakpoint(name='initial_y', '18', '[(13, 'abc', Font size=12 weight=normal slant=roman style=None)]')
    breakpoint(name='metrics', '[{'ascent': 9.0, 'descent': 3.0, 'linespace': 12}]')
    breakpoint(name='max_ascent', '9.0')
    breakpoint(name='aligned', '[(13, 20.25, 'abc', Font size=12 weight=normal slant=roman style=None)]')
    breakpoint(name='max_descent', '3.0')
    breakpoint(name='final_y', '33.0')
    
    >>> test.unpatch_breakpoint()

Lines of text are spaced to make room for the tallest text. Let's lay
out text with mixed font sizes, and then measure the line heights:

    >>> def baseline(word):
    ...     return word[1] + word[3].metrics("ascent")
    >>> l = lab3.Layout(lab3.lex("Start<br>Regular<br>Regular <big><big>Big"))
    >>> l.display_list #doctest: +NORMALIZE_WHITESPACE
    [(13, 20.25, 'Start', Font size=12 weight=normal slant=roman style=None),
     (13, 35.25, 'Regular', Font size=12 weight=normal slant=roman style=None),
     (13, 57.75, 'Regular', Font size=12 weight=normal slant=roman style=None),
     (109, 51.75, 'Big', Font size=20 weight=normal slant=roman style=None)]
    >>> baseline(l.display_list[1]) - baseline(l.display_list[0])
    15.0
    >>> baseline(l.display_list[3]) - baseline(l.display_list[1])
    22.5

The differing line heights don't occur when text gets smaller:

    >>> l = lab3.Layout(lab3.lex("Start<br>Regular<br>Regular <small><small>Small"))
    >>> l.display_list #doctest: +NORMALIZE_WHITESPACE
    [(13, 20.25, 'Start', Font size=12 weight=normal slant=roman style=None),
     (13, 35.25, 'Regular', Font size=12 weight=normal slant=roman style=None),
     (13, 50.25, 'Regular', Font size=12 weight=normal slant=roman style=None),
     (109, 53.25, 'Small', Font size=8 weight=normal slant=roman style=None)]
    >>> baseline(l.display_list[1]) - baseline(l.display_list[0])
    15.0
    >>> baseline(l.display_list[3]) - baseline(l.display_list[1])
    15.0


Testing `Browser`
-----------------

Now let's test integration of layout into the Browser class.

    >>> url = lab3.URL(test.socket.serve("<small>abc<i>def</i></small>"))
    >>> browser = lab3.Browser()
    >>> browser.load(url)

Testing the display list output of this URL:

    >>> browser.display_list #doctest: +NORMALIZE_WHITESPACE
    [(13, 19.875, 'abc', Font size=10 weight=normal slant=roman style=None),
     (53, 19.875, 'def', Font size=10 weight=normal slant=italic style=None)]

And the canvas:

    >>> test.patch_canvas()
    >>> browser = lab3.Browser()
    >>> browser.load(url)
    create_text: x=13 y=19.875 text=abc font=Font size=10 weight=normal slant=roman style=None anchor=nw
    create_text: x=53 y=19.875 text=def font=Font size=10 weight=normal slant=italic style=None anchor=nw
    >>> test.unpatch_canvas()

And with breakpoints:

    >>> test.patch_breakpoint()

    >>> browser.load(url)
    breakpoint(name='initial_y', '18', '[(13, 'abc', Font size=10 weight=normal slant=roman style=None), (53, 'def', Font size=10 weight=normal slant=italic style=None)]')
    breakpoint(name='metrics', '[{'ascent': 7.5, 'descent': 2.5, 'linespace': 10}, {'ascent': 7.5, 'descent': 2.5, 'linespace': 10}]')
    breakpoint(name='max_ascent', '7.5')
    breakpoint(name='aligned', '[(13, 19.875, 'abc', Font size=10 weight=normal slant=roman style=None)]')
    breakpoint(name='aligned', '[(13, 19.875, 'abc', Font size=10 weight=normal slant=roman style=None), (53, 19.875, 'def', Font size=10 weight=normal slant=italic style=None)]')
    breakpoint(name='max_descent', '2.5')
    breakpoint(name='final_y', '30.5')
    create_text: x=13 y=19.875 text=abc font=Font size=10 weight=normal slant=roman style=None anchor=nw
    create_text: x=53 y=19.875 text=def font=Font size=10 weight=normal slant=italic style=None anchor=nw

    >>> test.unpatch_breakpoint()

Testing font caching
--------------------

To test font caching, we call `get_font` twice and use Python's `is`
operator to test that we get identical `Font` objects back:

    >>> a = lab3.get_font(16, "normal", "roman")
    >>> b = lab3.get_font(16, "normal", "roman")
    >>> c = lab3.get_font(20, "normal", "roman")
    >>> d = lab3.get_font(16, "bold", "roman")
    >>> a is b
    True
    >>> a is c
    False
    >>> a is d
    False
