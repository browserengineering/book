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

Parts 1--3 of this book construct a basic browser weighing in around
1000 lines of code, twice that with the exercises. The average chapter
takes 4--6 hours to read, implement, and debug for someone with a few
years' programming experience. Part 4 of this book covers advanced
topics; those chapters are longer and have more code.

Your web browser will "work" every step of the way, and every chapter
will build upon the last.[^jrwilcox-idea] That way, you will also
practice growing and improving complex software. If you feel
particularly interested in some component, please do flesh it out,
complete the exercises, and add missing features. We've tried to
arrange it so that this doesn't make later chapters more difficult.

[^jrwilcox-idea]: This idea is from [J.R. Wilcox][jrw], inspired in turn by
    [S. Zdancewic][sz]'s course on compilers.

The code in this book [uses Python 3](blog/why-python.md), and we
recommend you follow along in the same. When the book shows Python
command lines, it calls the Python binary `python3`.^[A few operating
systems use `python`, but on most that means Python 2.] That said, the
text avoids dependencies where possible and you can try to follow
along in another language. Make sure your language has libraries for
TLS connections (Python has one built in), graphics (the text uses
Tk), and JavaScript evaluation (the text uses DukPy).
    
[jrw]: https://jamesrwilcox.com
[sz]: https://www.cis.upenn.edu/~stevez/

This book's browser is irreverent toward standards: it handles only a
sliver of the full HTML, CSS, and JavaScript languages, mishandles
errors, and isn't resilient to malicious inputs. It is also quite
slow. Despite that, its architecture matches that of real browsers,
providing insight into those 10 million line of code behemoths.

That said, we've tried to explicitly note when the book's browser
simplifies or diverges from standards. And in general, when you're not
sure how your browser should behave in some edge case, fire up your
favorite web browser and try it out.

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

*Pavel*: [James R. Wilcox][jrw] and I dreamed up this course during a
late-night chat at ICFP 2018. [Max Willsey][mwillsey] proof-read and
helped sequence the chapters. [Zach Tatlock][ztatlock] encouraged me
to develop the book into a course. And the students of CS 6968 and CS
4962 at the University of Utah found countless errors and suggested
important simplifications. I am thankful to all of them. Most of all,
I am thankful to my wife [Sara][saras], who supported my writing the
book, listened to countless status updates, and gave me the strength
to finish this many-year-long project.

[mwillsey]: https://www.mwillsey.com/
[saras]: https://www.sscharmingds.com/
[ztatlock]: https://homes.cs.washington.edu/~ztatlock/

*Chris*: I am eternally grateful to my wife Sara for patiently
listening to my endless musings about the web, and encouraging me to
turn my idea for a browser book into reality. I am also grateful to
[Dan Gildea][dan-gildea] for providing feedback on my browser-book
concept on multiple occassions. Finally, I'm grateful to Pavel for
doing the hard work getting this project off the ground and allowing
me to join the adventure. (Turns out Pavel and I had the same idea!)

[dan-gildea]: https://www.cs.rochester.edu/u/gildea/

A final note
============

This book is, and will remain, a work in progress. Please leave
comments and mark typos; the book has built-in feedback tools, which
you can enable with `Ctrl+E`. The full source code is also available
[on GitHub](https://github.com/browserengineering/book), though we
prefer to receive comments through the built-in tools.
