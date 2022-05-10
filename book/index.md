---
title: Web Browser Engineering
author: Pavel Panchekha & Chris Harrelson
main: true
...

Web browsers are ubiquitous, but how do they work? This book explains,
building a basic but complete web browser, from networking to
JavaScript, in a thousand lines of Python.

::: {.todo}
This draft version of the book includes unfinished chapters, and those
chapters make inaccurate claims, fail to match published chapters, or
misbehave. Read them at your own risk.
:::

::: {.signup}
:::

Follow this book's [blog](blog/) or
[Twitter](https://twitter.com/browserbook) for updates. You can also
talk about the book with others in our [discussion forum][forum].

[forum]: https://github.com/browserengineering/book/discussions

If you are enjoying the book, consider supporting us on [Patreon](https://patreon.com/browserengineering).

Or just [send us an email](mailto:author@browser.engineering)!

::: {.intro}
Introduction
============

1. [Preface](preface.md)
2. [Browsers and the Web](intro.md)
3. [History of the Web](history.md)
:::

Part 1: Drawing Graphics
========================

(@) [Downloading Web Pages](http.md)\
    URLs and HTTP requests
(@) [Drawing to the Screen](graphics.md)\
    Creating windows and drawing to a canvas
(@) [Formatting Text](text.md)\
    Word wrapping and line spacing

Part 2: Viewing Documents
=========================

(@) [Constructing a Document Tree](html.md)\
    Parsing and fixing HTML
(@) [Laying Out Pages](layout.md)\
    Inline and block layout, plus the box model
(@) [Applying User Styles](styles.md)\
    Parsing and applying CSS
(@) [Handling Buttons and Links](chrome.md)\
    Hyperlinks and browser chrome

Part 3: Running Applications
============================

(@) [Sending Information to Servers](forms.md)\
    Form submission and web servers
(@) [Running Interactive Scripts](scripts.md)\
    Changing the DOM and reacting to events
(@) [Keeping Data Private](security.md)\
    Cookies and logins, XSS and CSRF

Part 4: Modern Browsers
=======================

(@) [Adding Visual Effects](visual-effects.md)\
    Blending, clipping, and compositing
(@) [Scheduling Tasks and Threads](scheduling.md)\
    The event loop and the rendering pipeline
(@) [Animating and Compositing](animations.md)\
    Smooth animations using the GPU

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

:::
