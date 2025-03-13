---
title: What Wasn't Covered
type: Conclusion
prev: invalidation
next: change 
...

The last 16 chapters have, I hope, given you a solid understanding
of all of the major components of a web browser, from the network
requests it makes to the way it stores your data safely. With
such a vast topic I had to leave a few things out. Here's my list of
the most important things not covered by this book, in no particular
order.

JavaScript Execution
====================

A large part of a modern web browser is a very-high-performance
implementation of JavaScript. Today, every major browser not only runs
JavaScript, but compiles it, in flight, to low-level machine code
using runtime type analysis. Plus, techniques like hidden classes
infer structure where JavaScript doesn't provide any, lowering memory
usage and garbage collection pressure. On top of all of that, modern
browsers also execute WebAssembly, a hardware-independent bytecode format
for many other programming languages to target, and which may one day be co-equal
to JavaScript on the web.

This book skips building the JavaScript engine, instead using DukPy. I
made this choice because, while JavaScript execution is central to a
modern browser, it uses techniques fairly similar to the execution of
other languages like Python, Lua, or Java. The best way to learn about
the insides of a modern JavaScript engine is a book on programming
language implementation.

Text & Graphics Rendering
=========================

Text rendering is much more complex than it may seem at the surface.
Letters differ in widths and heights. Accents may need to be stacked
atop characters. Characters may change shape when next to other
characters, like for ligatures or for *shaping* (for cursive fonts).
Sometimes languages are written right-to-left or top-to-bottom. Then
there are typographic features, like kerning and variants. But the
most complex of all is *hinting*, which is a little computer program
embedded in a font that modifies it to better match the discrete pixel
grid. Text rendering of course affects Skia, but it also affects
layout, determining the size and position of content on the screen.

And more broadly, graphics in general is pretty complex! Our
browser uses Skia, which is the actual rasterization engine used by Chromium
and some other browsers. But we didn't really talk at all about how
Skia actually works, and it turns out to be pretty complex. It not
only renders text but applies all sorts of blends and effects quickly
and with high quality on basically all CPUs and GPUs. In a real
browser this becomes even more complex, with fancy compositing
systems, graphics process security sandboxing, and various
platform-specific font and OS compositing integrations. And there is a
whole lot of additional effort to implement lower-level
JavaScript-exposed APIs like [Canvas], [WebGL], and [WebGPU].

[Canvas]: https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API
[WebGL]: https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API
[WebGPU]: https://developer.mozilla.org/en-US/docs/Web/API/WebGPU_API

I skipped this topic in the book because high-quality implementations
are available in libraries like Skia (for graphics) and Harfbuzz (for
text), as well as various system libraries, so are arguably not
browser-specific. But there is a depth here best served by a book on
these specific subjects.

Connection Security & Privacy
=============================

Web browsers now ship with a sophisticated suite of cryptographic
protocols with bewildering names like AES-GCM, ChaCha20, and
HMAC-SHA512. These protocols protect against malicious actors with the
ability to read or write network packets. At the broadest
level, connection security is established via the TLS protocol (which
cameos in [Chapter 1](http.md)) and is maintained by an ecosystem of
cryptographers, certificate authorities, and open-source projects.

I chose to skip an in-depth discussion of TLS because this book's
irreverent attitude toward completeness and validation is incompatible
with real security engineering. A minimal and incomplete version of
TLS is a broken and insecure version of it, contrary to the intended
goal and pedagogically counterproductive. The best way to learn about
modern cryptography and network security is a book on that topic.

[Privacy on the web][privacy] is another important topic that I
skipped. In some ways security and privacy are related (and certainly
complement one other), but they are not the same. And privacy on the
web is in flux, such as debates around [third-party cookies][tpc],
[fingerprinting], and whether there should be APIs to help with
advertising. I chose to skip this topic because many basic concepts
remain unsettled: what the standards of privacy are and what role
governments, browser developers, website authors, and users should
play in them.

[privacy]: https://developer.mozilla.org/en-US/docs/Web/Privacy

[tpc]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies#third-party_cookies

[fingerprinting]: https://developer.mozilla.org/en-US/docs/Glossary/Fingerprinting

Network Caching and Media
=========================

Caching makes network requests faster by skipping most of them. What
makes it more than a mere optimization, however, is the extent to
which HTTP is designed to enable caching. Implementing a network cache
deepens one's understanding of HTTP significantly. That said, the
networking portion of this book is long enough, and at no point in the
book did the lack of a cache feel painful, so I decided to leave this
topic out.

And since the majority of network bandwidth and battery life is today
eaten up by video playback and video conferencing, there is a whole
world of complexity in real-time video encoding, decoding and
rendering. Real browsers have large teams devoted to these services
and APIs, and many researchers across the world work on video
compression. Video codecs are fascinating, but again not very
browser-specific, so this book skips them entirely, and I advise
reading a dedicated book about them.

Fancier Layout Modes
====================

The layout algorithm used in real browsers is much more sophisticated
than that covered in the book, with features like floating layout,
positioned elements, flexible boxes, grids, tables, and more.
Implementing these layout modes is complex and requires care and
sophistication---especially if you want speed and incremental
performance. Important techniques here include multi-phase
layout[^text] and measure-layout phases, with tricky caching
strategies necessary to produce good performance.

I chose to skip fancier layout in this book because even the simple
layout algorithm described here is quite complex, and real-world
layout algorithms involve a lot of accidental complexity caused by old
standards and backwards compatibility, which I didn't want to talk
much about.

[^text]: We do a little bit of multi-phase layout in the book, with
    words in a line having their `x`, `width`, and `height` computed
    in the first phase and then their `y` computed in a separate phase
    based on the baseline. But we don't talk much about it as an
    example of multi-phase layout, and real browsers have much more
    complex sets of layout phases.

Browser UIs and Developer Tools
===============================

A real browser has a *much* more complex and powerful "browser
UI"---meaning the chrome around the web page, where you can enter
URLs, see tabs, and so on---than our browser. In fact, a large
fraction of a real browser team works just on this, and not on the
"web platform" itself. The multi-process nature of a modern browser
also makes it difficult to interact with synchronous OS APIs, as we
saw with accessibility in [Chapter
14](accessibility.md#the-accessibility-tree). Plus, many browsers
(desktop ones, at least) support powerful [extension
APIs](https://en.wikipedia.org/wiki/Browser_extension) that enable
developers to extend the browser UI. To help with that, browser UIs
are often implemented in HTML and rendered by the browser itself.

Also, it'd be almost impossible to build complex web apps without some
kind of debugging aid, so all real browsers have built-in debuggers.
Believe it or not, for quite a long time web developers just did a
lot of [`console.log` debugging][printf] (or even `alert` debugging,
before there was an easy way to see the console!). This changed in a big
way with the innovative [Firebug] browser extension for Firefox, and
eventually today's integrated developer tools. These developer tools have
deep integration with the browser engine itself to implement features like
observing the styles of elements in real time or pausing and stepping
through JavaScript execution.

[printf]: https://en.wikipedia.org/wiki/Debugging#printf_debugging
[firebug]: https://en.wikipedia.org/wiki/Firebug_(software)

I skipped this topic because many challenges in browser UI are the
same as those of any other UI: design, usability, complexity, and so
on. That would make for a tedious book. Even the debugger,
conceptually quite interesting, is only useful if a substantial amount
of UI work is done to make it usable. Unfortunately, I'm not aware of
any book on developer tools, but many books will cover basic user
interface development.

Testing
=======

Real browsers have evolved an incredibly impressive array of testing
techniques to ensure they maintain and improve quality over time. In total,
they have batteries of hundreds of thousands of [unit] and [integration] tests.
Recently, a lot of focus has been put on robust
[cross-browser tests](https://wpt.fyi) that allow a single automated test
to run on all browsers to verify that they all behave the same on the same
input. And there are now yearly [interoperability]^["Interop", for short.]
benchmarks that measure how well browsers are doing against this goal for
key features. Behind the scenes of testing is a whole world of code and
infrastructure to efficiently run these tests continuously and provide
extensive [frameworks][testing-features] to make testing easy.

[unit]: https://en.wikipedia.org/wiki/Unit_testing
[integration]: https://en.wikipedia.org/wiki/Integration_testing
[interoperability]: https://wpt.fyi/interop-2023
[testing-features]: https://web-platform-tests.org/
