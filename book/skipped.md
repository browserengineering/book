---
title: What Wasn't Covered
type: Conclusion
cur: skipped
prev: security
next: change 
...

The last eleven chapters have, I hope, given you a solid understanding
of all of the major components of a web browser, from the network
requests it makes to way it stores your data and keeps it safe. With
such a vast topic I had to leave a few things out. Here's my list of
the most important things not covered by this book, listed in order of
importance.

When I teach from this book, I often cover these topics in lecture.
That not only saves me from ignoring important topics but also gives
me the flexibility to cover topics where implementation would be
inappropriate.

JavaScript Execution
====================

A large part of a modern web browser is a very-high-performance
implementation of JavaScript. Today, every major browser not only runs
JavaScript, but compiles it, in flight, to low-level machine code
using runtime type analysis. Plus, techniques like hidden classes
infer structure where JavaScript doesn't provide any, lowering memory
usage and garbage collection pressure. On top of all of that, modern
browsers also execute WebAssembly, an alternative programming language
that may one day be co-equal to JavaScript on the web.

This book skips building the JavaScript engine, instead using Dukpy. I
made this choice because while JavaScript execution is central to a
modern browser, it uses techniques fairly similar to the execution of
other languages like Python, Lua, or Java. The best way to learn about
the insides of a modern JavaScript engine is a book on programming
language implementation.

Accessibility
=============

Web pages should be usable despite physical (blind, difficulty seeing,
Parkinson's), mental (learning disabilities, dyslexia), or situational
(car console, gloves, eye dilation) disabilities. The web has grown a
rich garden of accessibility technologies. Not only is this a topic of
technical interest and moral imperative, the developing legal landscape in
many countries means it will only grow in importance over time.

To be honest I skipped this topic because I worried that web
accessibility was a difficult topic to engage students in. I also
could not figure out where in the book it would go. Adding it as a
twelfth chapter would also make the last part of the book even longer,
while adding it earlier would add a significant maintenance burden.

Connection Security
===================

Web browsers now ship with a sophisticated suite of cryptographic
protocols with bewildering names like AES-GCM, ChaCha20, and
HMAC-SHA512. These protocols protect against malicious actors with the
ability to read or write network packets, like national security
agencies and ex-boyfriends in the same coffee shop. At the broadest
level, connection security is established via the TLS protocol (which
cameos in [Chapter 1](http.md)) and maintained by an ecosystem of
cryptographers, certificate authorities, and open-source projects.

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
which HTTP is designed to enable caching. Implementing a network cache
deepens one's understanding of HTTP significantly.

That said, the networking portion of this book is long enough, and at
no point in the book did the lack of a cache feel painful, so I
decided to leave this topic out. Nor, sadly, did I find a chapter
where caching would make a good exercise.

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
slower than (highly optimized) reflow, and browsers use various tricky
data structures to speed it up.

The browser in this book, however, only implemented cheap selectors,
so restyling was never slow to begin with. And personally, I don't
find restyling algorithms particularly compelling, and don't think
teaching them would be that enlightening.

