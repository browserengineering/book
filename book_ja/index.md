---
title: Web Browser Engineering
author: Pavel Panchekha & Chris Harrelson
main: true
...

Web browsers are ubiquitous, but how do they work? This book explains,
building a basic but complete web browser, from networking to
JavaScript, in a couple thousand lines of Python.

::: {.todo}
This draft version of the book includes unfinished chapters, and those
chapters make inaccurate claims, fail to match published chapters, or
misbehave. Read them at your own risk.
:::

::::: {.wide-ad}
![The cover for Web Browser Engineering, from Oxford University Press](im/cover.jpg)

::: {.description}
# Pre-order _Web Browser Engineering_

_Web Browser Engineering_ will be published by Oxford University
Press early this year. To get it as soon as it's out,
[pre-order now!](https://global.oup.com/academic/product/web-browser-engineering-9780198913863)
:::

:::::

Follow this book's [blog](https://browserbook.substack.com/archive) or
[Twitter](https://twitter.com/browserbook) for updates. You can also
talk about the book with others in our [discussion forum][forum].

[forum]: https://github.com/browserengineering/book/discussions

If you are enjoying the book online, consider supporting us by buying a
physical copy for your home bookshelf.

You can also email us [here](mailto:author@browser.engineering).

::: {.intro}
Introduction
============

1. [Preface](preface.md)
2. [Browsers and the Web](intro.md)
3. [History of the Web](history.md)
:::

Part 1: Loading Pages
=====================

1. [Downloading Web Pages](http.md)\
    URLs and HTTP requests
2. [Drawing to the Screen](graphics.md)\
    Creating windows and drawing to a canvas
3. [Formatting Text](text.md)\
    Word wrapping and line spacing

Part 2: Viewing Documents
=========================

4. [Constructing an HTML Tree](html.md)\
    Parsing and fixing HTML
5. [Laying Out Pages](layout.md)\
    Inline and block layout
6. [Applying Author Styles](styles.md)\
    Parsing and applying CSS
7. [Handling Buttons and Links](chrome.md)\
    Hyperlinks and browser chrome

Part 3: Running Applications
============================

8. [Sending Information to Servers](forms.md)\
    Form submission and web servers
9. [Running Interactive Scripts](scripts.md)\
    Changing the DOM and reacting to events
10. [Keeping Data Private](security.md)\
    Cookies and logins, XSS and CSRF

Part 4: Modern Browsers
=======================

11. [Adding Visual Effects](visual-effects.md)\
    Blending, clipping, and compositing
12. [Scheduling Tasks and Threads](scheduling.md)\
    The event loop and the rendering pipeline
13. [Animating and Compositing](animations.md)\
    Smooth animations using the GPU
14. [Making Content Accessible](accessibility.md)\
    Keyboard input, zooming, and the accessibility tree
15. [Supporting Embedded Content](embeds.md)\
    Images, iframes, and scripting
16. [Reusing Previous Computation](invalidation.md)\
    Invalidation, editing, and correctness

::: {.outro}
Conclusion
==========

1. [What Wasn't Covered](skipped.md)
2. [A Changing Landscape](change.md)

Appendix
========

3. [Glossary](glossary.md)
4. [Bibliography](bibliography.md)
5. [About the Authors](about.md)
6. [Contributors](/thanks)
7. [List of courses taught from this book](classes.md)
8. [One-page version](onepage.md)

:::
