---
title: Web Browser Engineering
author: Pavel Panchekha & Chris Harrelson
main: true
...

Web browsers are ubiquitous, but how do they work? This book explains,
building a basic but complete web browser, from networking to
JavaScript, in a thousand lines of Python.

::: {.warning}
This book is a [work in progress](todo.md). Use at your own risk.
:::

Follow this book's [blog](blog/) or
[Twitter](https://twitter.com/browserbook) for updates.
Reach on [GitHub](https://github.com/pavpanchekha/emberfox)
to report issues or make suggestions.

Introduction
============

::: {.intro}
1. [Preface](preface.md)
2. [Browsers and the Web](intro.md)
3. [The History of the Web](history.md)
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
(@) [Saving Partial Layouts](reflow.md)\
    Two-phase layout and fast rendering
(@) [Keeping Data Private](security.md)\
    Cookies and logins, XSS and CSRF

Part 4: Modern Browsers
=======================

(@) [Adding Visual Effects](visual-effects.md)\
    Filters and transformations 

Conclusion
==========

::: {.outro}
1. [What Wasn't Covered](skipped.md)

2. [A Changing Landscape](change.md)
:::
