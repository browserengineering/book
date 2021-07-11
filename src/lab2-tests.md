Tests for WBE Chapter 2
=======================

Chapter 2 (Drawing to the Screen) is about how to get some simple data laid out
and drawn on the screen, plus a very simple implementation of scrolling. This
file contains tests for this functionality.

    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab2
