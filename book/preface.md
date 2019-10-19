---
title: Preface
type: Preface
next: preliminaries
...

A Computer Science degree traditionally includes courses like OS,
Databases, and Compilers. Among the reasons for these courses,[^1] one
stands out: the mystery students attach to these systems, leaving them
powerless over part of their computing environment. These classes
replace magic with code. They are successful when Linux, Postgres, or
LLVM look like improvements, additions, and optimizations atop a
conceptually simple core.

[^1]: A focus on performance, learning the low-level APIs, practice writing C,
    knowing your stack, writing better C/SQL/network code, and of course
    the importance of these systems in your ordinary computing
    experience...

But web browsers maintain their air of mystery---I know this from
speaking to industry programmers, students, and faculty. This book
corrects this flaw and dissipates the mystery by systematically
developing all of the major components of a web browser.

Reading this book
=================


If you follow along with the text, you will write a basic browser
weighing in around 1000 lines of code (twice that if you also do the
exercises). Most of the chapters will take 4--6 hours to read,
implement, and debug for someone with a few years\' programming
experience. However, [chapter 5 (Structuring Web Pages)](layout.md) and
[chapter 6 (Applying User Styles)](styles.md) are more difficult and
may take twice as long.

The browser this book builds does not attempt to conform to standards,
and it handles only a sliver of the full HTML, CSS, and JavaScript
languages. It also handles errors poorly, isn\'t resilient against
malicious inputs, and is quite slow---fatal flaws for a real browser,
but survivable in a teaching one. What makes the browser good is that
its architecture matches that of real browsers, giving you a real
understanding of those 10 million line of code behemoths. As you go
through the book, you focus more and more directly on what separates a
web browser from the other programs on your computer.

At every step, your web browser will "work" and be useful for some
task. Every chapter will tackle one of the browser\'s glaring
problems.[^2] In that way, you will also practice growing and
improving complex software. The text tries to avoid unnecessary
changes and refactorings. If you feel particularly interested in a
particular component, you can stop for a while to flesh it out and add
missing features. Continue with the rest of the book when you have
sated your curiosity.

[^2]: This idea is from J. Wilcox, who was inspired by [S.
    Zdancewic](http://www.cis.upenn.edu/~stevez/)\'s compilers
    course.

The code in this book uses Python 3, and I recommend you follow along in
the same. That said, the text avoids dependencies where possible. If you
choose to follow along in another language, you\'ll need to ensure that
your language has libraries for making encrypted connections (Python has
one built in), drawing simple graphics (the text uses Tk), and executing
JavaScript (the text uses DukPy).

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
