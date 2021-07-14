Tests for WBE Chapter 3
=======================

Chapter 3 (Formatting Text) adds on font metrics and simple font styling via
HTML tags. This file contains tests for the additional functionality.

Testing `lex`
-------------

The `lex` function in chapter three has been beefed up to return an array
of `Tag` or `Text` objects, rather than just the stream of characters from the
input.

    >>> lab2.lex('<body>hello</body>')
    'hello'
    >>> lab2.lex('he<body>llo</body>')
    'hello'
    >>> lab2.lex('he<body>l</body>lo')
    'hello'
    >>> lab2.lex('he<body>l<div>l</div>o</body>')
    'hello'
