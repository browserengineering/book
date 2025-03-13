---
title: Preface
type: Preface
next: intro
...

A computer science degree traditionally includes courses in operating
systems, compilers, and databases that replace mystery with code.
These courses transform Linux, Postgres, and LLVM into improvements,
additions, and optimizations of an understandable core architecture.
The lesson transcends the specific system studied: _all_ computer
systems, no matter how big and seemingly complex, can be studied and
understood.

But web browsers are still opaque, not just to students but to
industry programmers and even to researchers. This book dissipates
that mystery by systematically explaining all major components of a
modern web browser.

Reading This Book
=================

Parts 1--3 of this book construct a basic browser weighing in at around
1000 lines of code, twice that after exercises. The average chapter
takes 4--6 hours to read, implement, and debug for someone with a few
years' programming experience. Part 4 of this book covers advanced
topics; those chapters are longer and have more code. The final
browser weighs in at about 3000 lines.

Your browser[^yours-ours] will "work" at each step of the way, and
every chapter will build upon the last.[^jrwilcox-idea] That way, you will
also practice growing and improving complex software. If you feel
particularly interested in some component, please do flesh it out,
complete the exercises, and add missing features. We've tried to
arrange it so that this doesn't make later chapters more difficult.

[^yours-ours]: This book assumes that you will be building a web browser along
the way while reading it. However, it does present nearly
all the code---inlined into the book---for a working browser for every
chapter. So most of the time, the book uses the term "our browser",
which refers to the conceptual browser we (you and us, the
authors) have built so far. In cases where the book is referring specifically
to the implementation you have built, the book says "your browser".

[^jrwilcox-idea]: This idea is from [J. R. Wilcox][jrw], inspired in
turn by [S. Zdancewic's][sz] course on compilers.

The code in this book uses [Python 3](https://browserbook.substack.com/p/why-python),\index{Python} and we recommend you follow
along in the same. When the book shows Python command lines, it calls
the Python binary `python3`.[^py3-cmd] That said, the text avoids
dependencies where possible and you can try to follow along in another
language. Make sure your language has libraries for TLS connections
(Python has one built in), graphics (the text uses Tk, Skia, and SDL),
and JavaScript evaluation (the text uses DukPy).
    
[^py3-cmd]: This is for clarity. On some operating systems, `python`
means Python 3, but on others that means Python 2. Check which version
you have!

[sz]: https://www.cis.upenn.edu/~stevez/

This book's browser is irreverent toward standards: it handles only a
sliver of the full HTML, CSS, and JavaScript languages, mishandles
errors, and isn't resilient to malicious inputs. It is also quite
slow. Despite that, its architecture matches that of real browsers,
providing insight into those 10 million line of code behemoths.

That said, we've tried to explicitly note when the book's browser
simplifies or diverges from standards. If you're not sure how your
browser should behave in some edge case, fire up your favorite web
browser and try it out.

Acknowledgments
===============

We'd like to recognize the countless people who built the web and the
various web browsers. They are wonders of the modern world. Thank you!
We learned a lot from the books and articles listed in this book's
[bibliography](bibliography.md)---thank you to their authors. And
we're especially grateful to the many contributors to articles on
Wikipedia (especially those on historic software, formats, and
protocols). We are grateful for this amazing resource, one which in
turn was made possible by the very thing this book is about.

*Pavel*: [James R. Wilcox][jrw] and I dreamed up this book during a
late-night chat at ICFP 2018. [Max Willsey][mwillsey] proofread and
helped sequence the chapters. [Zach Tatlock][ztatlock] encouraged me
to develop the book into a course. And the students of CS 6968,
CS 4962, and CS 4560 at the University of Utah found countless errors and suggested
important simplifications. I am thankful to all of them. Most of all,
I am thankful to my wife [Sara][saras], who supported my writing and
gave me the strength to finish this many-year-long project.

[mwillsey]: https://www.mwillsey.com/
[saras]: https://www.sscharmingds.com/
[ztatlock]: https://homes.cs.washington.edu/~ztatlock/
[jrw]: https://jamesrwilcox.com

*Chris*: I am eternally grateful to my wife Sara for patiently
listening to my endless musings about the web, and encouraging me to
turn my idea for a browser book into reality. I am also grateful to
[Dan Gildea][dan-gildea] for providing feedback on my browser-book
concept on multiple occasions. Finally, I'm grateful to Pavel for
doing the hard work of getting this project off the ground and allowing
me to join the adventure. (Turns out Pavel and I had the same idea!)

[dan-gildea]: https://www.cs.rochester.edu/u/gildea/

::: {.web-only}

A final note
============

This book is, and will remain, a work in progress. Please leave
comments and mark typos; the book has built-in feedback tools, which
you can enable with `Ctrl-E` (or `Cmd-E` on a Mac). The full source
code is also available [on GitHub][github], though we prefer to
receive comments through the built-in tools.

[github]: https://github.com/browserengineering/book

:::
