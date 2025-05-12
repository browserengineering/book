Tests for WBE Chapter 3
=======================

Chapter 3 (Formatting Text) adds on font metrics and simple font styling via
HTML tags. This file contains tests for the additional functionality.

    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab3

Testing Mocks
-------------

This section handles a refactor that's introduced later in in Section
3.5; you can ignore it. Basically, if you've already created a
`Layout` class it creates a stub `layout` function that calls it and
undoes a lot of later changes like font changes, leading, and so on,
for testing previous sections.

    >>> lab3.WIDTH
    800
    >>> if not hasattr(lab3, "layout"):
    ...     def layout(text):
    ...         if isinstance(text, str):
    ...             return [(x, int(y - 2.25), w) for x, y, w, font
    ...                 in lab3.Layout(lab3.lex(text)).display_list]
    ...         else:
    ...             return [(x, int(y - 2.25), w, font) for x, y, w, font
    ...                 in lab3.Layout(text).display_list]
    ...     lab3.layout = layout
    ... else:
    ...      old_layout = lab3.layout
    ...      def layout(text):
    ...          try:
    ...              return old_layout(text)
    ...          except AttributeError as e:
    ...              expected_error = "'str' object has no attribute 'tag'"
    ...              if str(e) == expected_error:
    ...                  return old_layout(lab3.lex(text))
    ...              else:
    ...                  raise e
    ...      lab3.layout = layout

Note that these test doesn't use real `tkinter` fonts, but rather a
mock font that has faked metrics; in this font every character is N
pixels wide, where N is the font size.

3.3 Word by Word
----------------

The `layout` display list should now output one word at a time:

    >>> lab3.layout("abc")
    [(13, 18, 'abc')]
    >>> lab3.layout("abc def")
    [(13, 18, 'abc'), (61, 18, 'def')]
    
Different words should have different lengths:

    >>> lab3.layout("a bb ccc dddd")
    [(13, 18, 'a'), (37, 18, 'bb'), (73, 18, 'ccc'), (121, 18, 'dddd')]

Line breaking still works:

    >>> lab3.WIDTH
    800
    >>> lab3.WIDTH = 70
    >>> lab3.layout("a b c") #doctest: +NORMALIZE_WHITESPACE
    [(13, 18, 'a'), (37, 18, 'b'), (13, 33, 'c')]
    >>> lab3.WIDTH = 800


Note that the step sizes are 24, 36, and 48 pixels; that's because
it's measuring 2, 3, and 4 letters---note the space character!


3.4 Styling Text
----------------

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

The `layout` function should now be called with tokens:

    >>> lab3.layout(lab3.lex("abc"))
    [(13, 18, 'abc', Font size=12 weight=normal slant=roman style=None)]

    >>> lab3.layout(lab3.lex("<b>abc</b>"))
    [(13, 18, 'abc', Font size=12 weight=bold slant=roman style=None)]
    
    >>> lab3.layout(lab3.lex("<i>abc</i>"))
    [(13, 18, 'abc', Font size=12 weight=normal slant=italic style=None)]
    
HTML tags split words:

    >>> lab3.layout(lab3.lex('he<body>l</div>lo')) #doctest: +NORMALIZE_WHITESPACE
    [(13, 18, 'he', Font size=12 weight=normal slant=roman style=None),
     (49, 18, 'l', Font size=12 weight=normal slant=roman style=None),
     (73, 18, 'lo', Font size=12 weight=normal slant=roman style=None)]

You can combine bold and italic in various orders:

    >>> lab3.layout(lab3.lex('h<b>e<i>l</b>l</i>o')) #doctest: +NORMALIZE_WHITESPACE
    [(13, 18, 'h', Font size=12 weight=normal slant=roman style=None),
     (37, 18, 'e', Font size=12 weight=bold slant=roman style=None),
     (61, 18, 'l', Font size=12 weight=bold slant=italic style=None),
     (85, 18, 'l', Font size=12 weight=normal slant=italic style=None),
     (109, 18, 'o', Font size=12 weight=normal slant=roman style=None)]


3.5 A Layout Object
-------------------

This chapter creates a Layout class to output a display list that can
format text. It stores a display list and can handle text size changes:

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


3.6 Text of Different Sizes
---------------------------

Lines of text are spaced to make room for the tallest text. Let's lay
out text with mixed font sizes, and then measure the line heights:

    >>> lab3.Layout(lab3.lex("<big><big><i>abc</i></big>def</big>")).display_list #doctest: +NORMALIZE_WHITESPACE
    [(13, 21.75, 'abc', Font size=20 weight=normal slant=italic style=None),
     (93, 24.75, 'def', Font size=16 weight=normal slant=roman style=None)]

Let's make sure the actual positions are correct:

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

Let's also test that `</p>` tags are handled correctly:

    >>> l = lab3.Layout(lab3.lex("<p>Para1</p><p>Para2</p>"))
    >>> l.display_list #doctest: +NORMALIZE_WHITESPACE
    [(13, 20.25, 'Para1', Font size=12 weight=normal slant=roman style=None),
     (13, 53.25, 'Para2', Font size=12 weight=normal slant=roman style=None)]
     
Note that in this chapter it's the `</p>`, not `<p>`, tags that
introduce the extra whitespace:

    >>> l = lab3.Layout(lab3.lex("<p>Para1<p>Para2"))
    >>> l.display_list #doctest: +NORMALIZE_WHITESPACE
    [(13, 20.25, 'Para1', Font size=12 weight=normal slant=roman style=None),
     (85, 20.25, 'Para2', Font size=12 weight=normal slant=roman style=None)]


3.7 Font Caching
----------------

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
