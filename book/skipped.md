---
title: What Wasn't Covered
type: Conclusion
prev: security
...

The last eleven chapters have, I hope, given you a solid understanding
of how web browsers work, from the network requests they make to way
they store your data and keep it safe. I've endeavored to cover all of
the major components of a web browser, but with such a vast topic I
had to leave a few things out. Here's my list of the most important
things not covered by this book.

When I teach from this book, I often cover these topics in lecture.
That not only saves me from ignoring important topics but also gives
me the flexibility to cover topics where implementation would be
inappropriate.

JavaScript Execution
====================

A solid third of a modern web browser is a very-high-performance
implementation of JavaScript. Today, every major browser not only runs
JavaScript, but compiles it, in flight, to low-level machine code
using runtime type analysis. Plus, techniques like hidden classes
infer structure where JavaScript doesn't provide any, lowering memory
usage and garbage collection pressure. On top of all of that, modern
browsers also execute WebAssembly, an alternative programming language
that may one day be co-equal to JavaScript on the web.

This book skips build the JavaScript engine, instead using Dukpy. I
made this choice because while JavaScript execution is central to a
modern browser, it uses techniques fairly similar to the execution of
other languages (like Python, Lua, or Java). The best way to learn
about the insides of a modern JavaScript engine is a book on
programming language implementation.

Connection Security
===================

Web browsers now ship with a sophisticated suite of cryptographic
protocols, with bewildering names like AES-GCM, ChaCha20, and
HMAC-SHA512. These cryptographic protocols are used to ensure
*connection security*, that is, to protect against a malicious actor
with the ability to read or write network packets, like national
security agencies, evil corporations, and ex-boyfriends on the same
unsecured wireless connection. At the broadest level, connection
security is established via the TLS protocol (which cameos in the
first chapter) and maintained using an ecosystem of cryptographers,
certificate authorities, and server maintainers.

I chose to skip an in-depth discussion of TLS because this book's
irreverant attitude toward completeness and validation is incompatible
with real security engineering. A minimal and incomplete version of
TLS is a broken and insecure version of it: contrary to the intended
goal and pedagogically counterproductive. The best way to learn about
modern cryptography and network security is a book on that topic.

Caching
=======

Caching makes network requests faster by skipping most of them. What
makes it more than a mere optimization, however, is the extent to
which HTTP was designed to enable it. Implementing a network cache
deepens one's understanding of HTTP significantly.

That said, the networking portion of this book is long enough, and at
no point in the book did the lack of a cache feel painful, so I
decided to leave this topic out. Nor, sadly, did I find a chapter
where caching would make a good exercise.

High-speed Graphics
===================

Web browsers now include impressive graphics engines for getting a
picture to the screen as fast as possible. This has become ever more
important as the web gains graphical bells and whistles.^[Shadows,
rounded corners, and transparency all feel like new features to me,
since I started web development with IE 5.5. The truly new stuff is
even wilder.] High-speed graphics may mean retaining display lists
(instead of recomputing them after every reflow), compositing portions
of the display list (to avoid rerendering expensive shapes like text),
and even moving rendering to the graphics card. The major browsers
have recently (as of late 2019) been pushing especially vigorously on
this front.

[Chapter 10](reflow.md) does talk a bit about fast graphics, since
rendering eventually takes more time than reflow, but to be honest
graphics speed is hurt more by the choice of Tk and Python than any
algorithm or implementation decision in the browser itself. More
broadly, I didn't want to focus too much on the low-level details of
performance. Those change frequently and usually don't teach broader
lessons for students to apply elsewhere.

Text Rendering
==============

The book's use of Tk as a rendering engine is an odd one. Tk provides
much more than the simple canvas the book uses, and even that canvas
is implemented more like a scene graph, making it unnecessarily slow.
But since we don't use that complexity, I don't feel bad hiding it
from readers. However, Tk does implement text rendering for us, and
that is a complex component the book relies on without explaining.

Text rendering is much more complex than it may seem at the surface.
Letters differ in widths and heights. Accents may need to be stacked
atop characters. Characters may change shape by proximity to other
characters, like for ligatures or for *shaping* (for cursive fonts).
Then there are typographic features, like kerning and variants. But
the most complex of all is *hinting*, which is a little computer
program embedded in a font that modifies it to better match the
discrete pixel grid.

Text rendering is always available in system libraries, and
implementing it is a huge pain, so it seemed reasonable to skip it in
this book. A book on computer typography is the best place to learn
more.

Restyling
=========

Browsers must not only *reflow* layouts every time the page changes,
but also *restyle* them, recomputing the CSS properties and values
that apply to each element. For many modern browsers, restyling is
slower than reflow, and browsers use various tricky data structure to
speed it up.

The browser in this book, however, only implemented cheap selectors,
so restyling was never slow to begin with. Restyling was thus
unnecessary. Personally, I don't find restyling algorithms
particularly compelling, and don't think teaching them would be that
enlightening.

