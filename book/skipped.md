---
title: What Wasn't Covered
type: Conclusion
prev: invalidation
next: change 
...

The last sixteen chapters have, I hope, given you a solid understanding
of all of the major components of a web browser, from the network
requests it makes to way it stores your data and keeps it safe. With
such a vast topic I had to leave a few things out. Here's my list of
the most important things not covered by this book, in no particular
order.

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
browsers also execute WebAssembly, a hardware-independent bytecode format
target for many other programming languages that may one day be co-equal
to JavaScript on the web.

This book skips building the JavaScript engine, instead using DukPy. I
made this choice because while JavaScript execution is central to a
modern browser, it uses techniques fairly similar to the execution of
other languages like Python, Lua, or Java. The best way to learn about
the insides of a modern JavaScript engine is a book on programming
language implementation.

Text & Graphics Rendering
=========================

Text rendering is much more complex than it may seem at the surface.
Letters differ in widths and heights. Accents may need to be stacked
atop characters. Characters may change shape by proximity to other
characters, like for ligatures or for *shaping* (for cursive fonts).
Sometimes languages are written right-to-left or top-to-bottom.
Then there are typographic features, like kerning and variants. But
the most complex of all is *hinting*, which is a little computer
program embedded in a font that modifies it to better match the
discrete pixel grid. Some of text rendering is in Skia, but a whole
lot of it actually has to be done in layout to determine sizing and
positions of content on the screen.


As for graphics in general, our toy browser ended up using Skia,
which is the real rasterization engine of Chromium and some other
browsers. But we didn't really talk at all about how Skia actually
works (just how to use it and create surfaces for different pieces
of the display list). Skia is, of course, a tremendously complex
piece of software, which solves the problems of high-quality, fast text
and shape rendering on basically all CPUs and GPU architectures. But
even that is only part of the story. In addition to Skia, real browsers
have a much more complicated and fancy compositing system, graphics
process security sandboxing, and various platform-specific font and
OS compositing integrations. And there is a whole lot of additional
effort to support high-quality implementations
of all details of JavaScript-exposed APIs like [Canvas], [WebGL], and
[WebGPU].

[Canvas]: https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API
[WebGL]: https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API
[WebGPU]: https://developer.mozilla.org/en-US/docs/Web/API/WebGPU_API

Text and graphics rendering are always available in system libraries, and
implementing them is very difficult and arguably not browser-specific, so
it seemed reasonable to skip them in this book. A book on these
subjects is the best place to learn more.

Connection Security
===================

Web browsers now ship with a sophisticated suite of cryptographic
protocols with bewildering names like AES-GCM, ChaCha20, and
HMAC-SHA512. These protocols protect against malicious actors with the
ability to read or write network packets. At the broadest
level, connection security is established via the TLS protocol (which
cameos in [Chapter 1](http.md)) and maintained by an ecosystem of
cryptographers, certificate authorities, and open-source projects.

I chose to skip an in-depth discussion of TLS because this book's
irreverent attitude toward completeness and validation is incompatible
with real security engineering. A minimal and incomplete version of
TLS is a broken and insecure version of it: contrary to the intended
goal and pedagogically counterproductive. The best way to learn about
modern cryptography and network security is a book on that topic.

Network Caching
===============

Caching makes network requests faster by skipping most of them. What
makes it more than a mere optimization, however, is the extent to
which HTTP is designed to enable caching. Implementing a network cache
deepens one's understanding of HTTP significantly.

That said, the networking portion of this book is long enough, and at
no point in the book did the lack of a cache feel painful, so I
decided to leave this topic out. Nor, sadly, did I find a chapter
where caching would make a good exercise.

Browser UI
==========

A real browser has a *much* more complex and powerful "browser UI"---meaning
the chrome around the web page, where you can enter URLs, see tabs, and so
on---than our toy browser. In fact, a pretty big proportion of a real browser
team works just on this, and not on the "web platform" itself. The challenges
of browser UI are mostly the same as any other application, except for the
multi-process nature of a modern browser, which can make things like
integration with synchronous OS APIs very difficult.^[A well-known example
is accessibility, which I touched on in [Chapter 14](accessibility.md#the-accessibility-tree).]

Media
=====

There is a whole world of complexity in real-time video encoding, decoding and
rendering. Real browsers have large teams devoted to these services and APIs,
since most network bandwidth and battery life is eaten up by video
and video conferencing these days. This book skips it entirely, and I suggest
dedicated books on these subjects.

Debugging & Extensions
======================

It'd be almost impossible to build complex web apps without some kind of
debugging aid. But believe it or not, there were not actually any good web
page debuggers for quite a long time---just a lot of [printf debugging][printf].
This changed in a big way with the advent of debuggers built into web browsers,
starting with the innovative [Firebug] browser extension for Firefox. Today
such debuggers are indispensable for a real browser, and integrating one
is quite challenging and interesting.^[For example, to implement features like
observing the styles of elements in real time, pausing/stepping through
execution, and being written in HTML themselves.]

[printf]: https://en.wikipedia.org/wiki/Debugging#printf_debugging
[firebug]: https://en.wikipedia.org/wiki/Firebug_(software)

All real browsers (desktop ones, at least) support powerful
[extension APIs](https://en.wikipedia.org/wiki/Browser_extension)
that allow developers to inject JavaScript into web pages to add useful
features. Implementing these APIs, and in a relatively secure and performant
way, is very challenging. I'm not aware of a book on this topic; conceptually
it is somewhat similar to building a debugger.

Testing
=======

Real browsers have evolved an incredibly impressive array of testing
techniques to ensure they maintain and improve quality over time. In total,
they have batteries of hundreds of thousands of [unit], and [integration] tests.
Recently, a lot of focus has been put on robust
[cross-browser tests](https://wpt.fyi) that allow a single automated test
to run on all browsers to verify that they all behave the same on the same
input. And there are now yearly [Interoperability]^["Interop", for short.]
benchmarks that measure how well browsers are doing against this goal for
key features. Behind the scenes of testing is a whole world of code and
infrastructure to efficiently run these tests continuously and provide
extensive [frameworks][testing-features] to make testing easy.

[unit]: https://en.wikipedia.org/wiki/Unit_testing
[integration]: https://en.wikipedia.org/wiki/Integration_testing
[interoperability]: https://wpt.fyi/interop-2023
[testing-features]: https://web-platform-tests.org/

Privacy
=======

[Privacy on the web](https://developer.mozilla.org/en-US/docs/Web/Privacy)
is an important topic, and one we have not covered at all. In some ways
security and privacy are related (and certainly complement one other),
but they are not the same, and I haven't covered the latter at all. Privacy
is also a tricky subject, because it involves additional concepts such as what
does or does not constitute privacy, or what changes the web should take to
increase privacy, that are actively debated today. For example, there are
debates about what to do if [third-party cookies][tpc] are removed, reduce
the risk of [fingerprinting], and whether there should be APIs to help with
advertising use cases.

[tpc]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies#third-party_cookies

[fingerprinting]: https://developer.mozilla.org/en-US/docs/Glossary/Fingerprinting