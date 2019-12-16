---
title: Preface
type: Preface
next: preliminaries
...

A Computer Science degree traditionally includes courses like OS,
Databases, and Compilers. Students attach to these systems, leaving
them powerless over part of their computing environment. These classes
replace magic with code:[^1] Linux, Postgres, or LLVM look like
improvements, additions, and optimizations atop an understandable
core.

[^1]: Others reasons for these classes: a focus on speed; learning
    low-level APIs; practice with C; knowing the stack; using systems
    better; and the importance of the system covered.

But web browsers internals are still opaque to students, faculty, and
industry programmers. This book dissipates this mystery by
systematically explaining all major components of a web browser.

Reading this book
=================


If you follow along with the text, you will write a basic browser
weighing in around 1000 lines of code (twice that if you also do the
exercises). Most of the chapters will take 4--6 hours to read,
implement, and debug for someone with a few years\' programming
experience. However, [chapter 5 (Structuring Web Pages)](layout.md) and
[chapter 6 (Applying User Styles)](styles.md) are more difficult and
may take twice as long.

The code in this book uses Python 3, and I recommend you follow along in
the same. That said, the text avoids dependencies where possible. If you
choose to follow along in another language, you\'ll need to ensure that
your language has libraries for making encrypted connections (Python has
one built in), drawing simple graphics (the text uses Tk), and executing
JavaScript (the text uses DukPy).

Your web browser will "work" and be useful at every step of the way,
and every chapter will tackle a glaring problem.[^2] In that way, you
will also practice growing and improving complex software. The text
tries to avoid unnecessary changes and refactorings. That way, if you
feel particularly interested in a particular component, you can flesh
it out and add missing features, without making later chapters more
difficult.

[^2]: This idea is from J. Wilcox, inspired in turn by
    [S. Zdancewic](http://www.cis.upenn.edu/~stevez/)\'s course on
    compilers.

This book's browser does not attempt to conform to standards, and it
handles only a sliver of the full HTML, CSS, and JavaScript languages.
It also handles errors poorly, isn\'t resilient against malicious
inputs, and is quite slow---fatal flaws in a real browser, but
survivable in a teaching one. What makes the browser good is that its
architecture matches that of real browsers, giving you a real
understanding of those 10 million line of code behemoths.

Acknowledgements
================

[James R. Wilcox](https://homes.cs.washington.edu/~jrw12/) and I
dreamed up this course during a late-night chat at ICFP 2018. [Max
Willsey](https://mwillsey.com/) proof-read and helped sequence the
chapters. [Zach Tatlock](https://homes.cs.washington.edu/~ztatlock/)
encouraged me to develop this into a course. I am thankful to all of
them. I also thank the students of CS 6968, who found many errors and
suggested important simplifications.

This book is a work in progress, and I would love to [hear your
suggestions](mailto:me@pavpanchekha.com) on how to make it clearer,
shorter, and more complete.
You can find the source code in [my GitHub repo](https://github.com/pavpanchekha/emberfox). Feel free to send a PR ;)
