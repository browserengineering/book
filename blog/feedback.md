---
title: Typos and Comments
author: Pavel Panchekha
date: 4 August 2020
prev: beginning
next: why-python
...

[Web Browser Engineering](../) is a book about the web, on the web,
and *of* the web. Less flippantly, I want the book to be strengthened
by the capabilities of the web. I'm starting with reader feedback.

Like any writer, I edit repeatedly; good writing is rewriting. But
typos slip through, and hunting them down is too hard: my attention
wavers and I stop focusing. But readers notice.

Now readers can let me know. Open a chapter of [Web Browser
Engineering](../) and press `Ctrl+E`. After entering your name, hover
over any text, and you will see options to suggest changes or add
comments.

The code is quite simple: when you select "Typo", that paragraph is
marked `contenteditable`, an [HTML feature][contenteditable] that
turns on rich text editing on the client side. Then, when focus leaves
the paragraph you are editing, I bundle up the old and new text
content[^1] and ship it to a server, which saves the results.

Submitting a typo doesn't change the book for anyone else.[^2] But I
can review all the changes, and fix any typos I find. The server uses
Python's [difflib][difflib] package, to show a word-level diff,[^3]
so the typos are easy to find and assess. Since I ask for your name
before enabling feedback, I can thank you in the final version of the
book.

[contenteditable]: https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/contenteditable
[difflib]: https://docs.python.org/3/library/difflib.html
[^1]: Dealing with HTML content and formatted text is too complex and
    not too important for a book.
[^2]: In fact, the book is statically compiled with Pandoc and then
    uploaded to the server. Only I make changes.
[^3]: I have different modes for code and for text, since whitespace
    is relevant in one but not the other.
