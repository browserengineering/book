---
title: Preface
type: Preface
next: intro
...

A computer science degree traditionally includes courses in operating
systems, compilers, and databases in order to replace mystery with
code. These courses transform Linux, Postgres, and LLVM into
improvements, additions, and optimizations to an understandable core
architecture. The lesson transcends the specific system studied: _all_
computer systems, no matter how big and seemingly complex, can be
studied and understood[^other-reasons].

[^other-reasons]: Others reasons for these classes: a focus on speed; learning
low-level APIs; practice with C; knowing the stack; using systems better; and
the importance of the system covered.

But web browsers are still opaque, not just to students but to faculty
and industry programmers. This book dissipates this mystery by
systematically explaining all major components of a web browser.


Reading this book
=================

The text constructs a basic browser weighing in around 1000 lines of
code (twice that if you also do the exercises). Most of the chapters
will take 4--6 hours to read, implement, and debug for someone with a
few years' programming experience, though some chapters (like
[5](layout.md) and [6](styles.md)) are more difficult and may take
twice as long.

The code in this book uses Python 3, and I recommend you follow along
in the same. That said, the text avoids dependencies where possible.
If you choose to follow along in another language, you'll need to
ensure that your language has libraries for encrypted connections
(Python has one built in), simple graphics (the text uses Tk), and
JavaScript evaluation (the text uses DukPy).

Your web browser will "work" every step of the way, and every chapter will build
upon the last.[^jrwilcox-idea] That way, you will also practice growing and
improving complex software. The text tries to avoid unnecessary changes and
refactors. If you feel particularly interested in some component, you can flesh
it out and add missing features without making later chapters more difficult.

[^jrwilcox-idea]: This idea is from [J.R. Wilcox][jrw], inspired in turn by
    [S. Zdancewic][sz]'s course on compilers.
    
[jrw]: https://jamesrwilcox.com
[sz]: http://www.cis.upenn.edu/~stevez/

This book's browser is irreverent toward standards: it handles only a
sliver of the full HTML, CSS, and JavaScript languages, mishandles
errors, and isn't resilient to malicious inputs. It is also quite
slow. Despite that, its architecture matches that of real browsers,
providing insight into those 10 million line of code behemoths.

Acknowledgments
===============

We'd like to start by recognizing the countless people who have helped to build
those wonders of the modern world that are browsers and the web. Thank
you!

Much of the background for for the history of the web came from Wikipedia (as
you can see from the many links back to it within the text). We are grateful for
this amazing resource, one which in turn was made possible by the very thing
this book is about.



#### Pavel

[James R. Wilcox](https://homes.cs.washington.edu/~jrw12/) and I
dreamed up this course during a late-night chat at ICFP 2018. [Max
Willsey](https://mwillsey.com/) proof-read and helped sequence the
chapters. [Zach Tatlock](https://homes.cs.washington.edu/~ztatlock/)
encouraged me to develop this into a course. I am thankful to all of
them. I also thank the students of CS 6968 at the University of Utah,
who found many errors and suggested important simplifications.

#### Chris

I am eternally grateful to my wife Sara for patiently listening to my endless
musings about the web, and encouraging me to turn my idea for a browser book
into reality. (Turns out Pavel and I had the same idea!) I am also grateful to
[Dan Gildea][dan-gildea] for providing feedback on my browser-book concept on
multiple occassions. Finally, I'm grateful to Pavel for doing the hard work
getting this project off the ground and allowing me to join the adventure.

[dan-gildea]: https://www.cs.rochester.edu/u/gildea/

A final note
============

This book is, and will remain, a work in progress. Please leave
comments and mark typos; the book has built-in feedback tools, which
you can enable with `Ctrl+E`. Full source code is available [on
GitHub](https://github.com/pavpanchekha/emberfox).
