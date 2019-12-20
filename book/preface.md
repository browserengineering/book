---
title: Preface
type: Preface
next: preliminaries
...

Computer science students find operating systems, compilers, and
databases mysterious, leaving them powerless over part of their
computing environment. So,[^1] a computer science degree traditionally
includes courses that replace mystery with code, so that Linux,
Postgres, and LLVM look like improvements, additions, and
optimizations atop an understandable core.

[^1]: Others reasons for these classes: a focus on speed; learning
    low-level APIs; practice with C; knowing the stack; using systems
    better; and the importance of the system covered.

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

Your web browser will "work" every step of the way, and every chapter
will build upon the last.[^2] That way, you will also practice growing
and improving complex software. The text tries to avoid unnecessary
changes and refactorings. If you feel particularly interested in some
component, you can flesh it out and add missing features without
making later chapters more difficult.

[^2]: This idea is from J. Wilcox, inspired in turn by
    [S. Zdancewic](http://www.cis.upenn.edu/~stevez/)\'s course on
    compilers.

This book's browser is irreverant toward standards: it handles only a
sliver of the full HTML, CSS, and JavaScript languages, mishandles
errors, and isn't resilient to malicious inputs. It is also quite
slow. Despite that, its architecture matches that of real browsers,
providing insight into those 10 million line of code behemoths.


Acknowledgements
================

[James R. Wilcox](https://homes.cs.washington.edu/~jrw12/) and I
dreamed up this course during a late-night chat at ICFP 2018. [Max
Willsey](https://mwillsey.com/) proof-read and helped sequence the
chapters. [Zach Tatlock](https://homes.cs.washington.edu/~ztatlock/)
encouraged me to develop this into a course. I am thankful to all of
them. I also thank the students of CS 6968, who found many errors and
suggested important simplifications.

This book is, and will remain, a work in progress. Please leave
comments and mark typos; the book has built-in feedback tools, which
you can enable with `Ctrl+E`. Full source code is available [on
GitHub](https://github.com/pavpanchekha/emberfox).
