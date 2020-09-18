---
title: Why Python?
author: Pavel Panchekha
date: 5 September 2020
prev: feedback
...

Why use Python for [Web Browser Engineering](../)?

# Why not C, C++, or Rust?

All existing browsers are written in C++, with maybe a little bit of
Rust sneaking in these days. Browsers need to be as fast as possible,
and using Python makes is slower for minimal benefit.

That's true, but the browser of *Web Browser Engineering* is not going
to be fast. Its Javascript engine is bytecode interpreted, its
rendering engine is Tk's canvas, and its parsers are hand-coded.
In fact, there's a benefit to being slow: this toy browser is simple
enough, and readers are likely to test it on small enough pages, that
some important optimizations (such as reflow or clipping) wouldn't be
necessary if the systems they optimize were faster to begin with. For
example, the chapter on [Drawing to the Screen](../graphics.md)
implements clipping for a visible impact even on moderately-sized
pages. But if the code were written in C against Harfbuzz, instead of
in Python against Tk, that optimization wouldn't make a noticable
impact until the browser became much more graphically complex.
That may be good for usability, but it's bad for pedagogy.

Writing good C, C++, and Rust also means being very careful to handle
errors, because errors cause compiler errors or mysterious runtime
behaviors. But while error handling is essential on the web, it's not
a focus of *Web Browser Engineering* because exhaustive error handling
should only come after understanding the underlying algorithms being
implemented. And in some cases, key concepts are purposely ignored in
the book. For example, there's no discussion of character
encodings—`utf8` is used any time one is needed. But `utf8` decoding
can throw errors! Being forced to handle those errors is important in
a production browser, but would get in the way of explaining
networking in the book.

Finally, systems languages usually present more details than helpful.
Rust has *how* many string types? Which is still better than C's count
of zero! And string processing is a big part of the book. Similarly,
large, mutable, interlinked data structures are a bit part of the
browser, and deciding ownership or memory management for those is
difficult. I wouldn't want readers to be writing `unsafe` code or
handling use-after-free errors.

# Why not Javascript?

Writing a book on web browsers seems like a great opportunity to *use*
web technologies to improve the book. For example, why not write the
browser in JavaScript? It could draw to a `<canvas>`, and those could
be included in-line with the text. Readers could modify code snippets,
and have the modifications automatically run against a set of tests.
Graphics and figures could be generated directly from a running
browser, and could allow deeper explorations into the browser.
Finally, JavaScript has native support far beyond Python: could *Web
Browser Engineering* could implement a compositing rendering engine
using WebGL, for example?

Yet technical details sour me on JavaScript. Were the browser written
in JavaScript, the browser code and the code on web pages themselves
would look similar. Running JavaScript would be easier, thanks to
`eval`, but making sure `eval`'d code didn't affect the surrounding
page would be harder, and in any case the resulting page-browser
interop would look nothing like it does in a browser. Using Web
Workers or a similar API would make isolation easier, but would
introduce a multi-process messaging model that again looks nothing
like existing browsers.

Networking likewise couldn't use raw HTTP, so this important aspect of
the browser couldn't be covered, and network requests would be subject
to the same-origin policy. That could be avoided with some kind of
proxy, but then the book would either have to explain that or accept
the proxy as magic. Introducing magic is exactly what this book
*doesn't* want to do, especially so early!

Finally, the book purposely sticks to a restricted subset of Python
both for readability and for ease of translation to other languages.
When I teach from *Web Browser Engineering* I do require students to
use Python[^why-teach-python], but I try to avoid using anything too
Python-specific, or I do so only when the readability benefits are
large and translation to another langauge is reasonably clear. (List
comprehensions fall into this bucket.)

[^why-teach-python]: I didn't do this in the past, but I found that
    changing languages also pushed students to change the browser
    architecture, for example making things more immutable or changing
    where state is stored, and those changes would inevitably make
    later chapters much harder. *Web Browser Engineering* can look
    simple, but go off the beaten path and you get stuck easily!

None of this is to say that a browser *can't* be written in
JavaScript; in fact, one of my students last year did just that, even
implementing the Canvas API in his browser so that it could self-host.
The result was very cool, but it did require elaborate workarounds to
the issues above.

# Why not Go, Java, Swift, Ruby? Or Racket, Dart, Haskell?

Python is one of the most popular programming languages in the world.
It has an extensive universe of libraries (which readers can use for
testing or extending their toy browser), a built-in cross-platform UI
framework, and a concision and readability that make the book work
even if the reader isn't coding as they read. Most alternatives to
Python fail one of those tests. Plus, I like Python.

As to the more obscure options, I'm certainly not opposed to obscure
languages, and most of work over the last decade has been in Lisp
variants like Racket. But with more obscure languages readability
suffers heavily as readers struggle to understand the language itself.
Obscure languages also seem to consistently lack good facilities for
manipulating strings, something Python excells at and which is a big
part of the book. Finally, functional languages tend to fight against
large, mutually-linked, mutable data structures, yet the layout engine
of a browser is all about that. That makes those languages further
impede readability, and moreover in the most important and complex
chapters.
