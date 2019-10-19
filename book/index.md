---
title: Web Browser Engineering
author: Pavel Panchekha
main: true
...

Web browsers are ubiquitous, but how do they work? This book builds a
basic but complete web browser, including all of the major browser
components from networking to JavaScript, in a thousand lines of
Python.

1. [Preface](preface.md)

2. [Preliminaries](preliminaries.md)

Part 1: Drawing Graphics
========================

(@) [Downloading Web Pages](http.md)\
    URLs, HTTP, and some basic lexing for HTML
(@) [Drawing to the Screen](graphics.md)\
    Creating windows, drawing to a canvas, and laying out text
(@) [Formatting Text](text.md)\
    Fonts, line wrapping, and word spacing

Part 2: Viewing Documents
=========================

(@) [Constructing a Document Tree](html.md)\
    Creating a tree of nodes and doing layout from it
(@) [Laying Out Pages](layout.md)\
    Splitting inline from block layout and adding the box model
(@) [Applying User Styles](styles.md)\
    Downloading, parsing and applying CSS
(@) [Handling Buttons and Links](chrome.md)\
    Hyperlinks, browser chrome, and history

Part 3: Running Applications
============================

(@) [Sending Information to Servers](forms.md)\
    Input areas, form submission, and web servers
(@) [Running Interactive Scripts](scripts.md)\
    Responding to events and reading and writing the DOM
(@) [Saving Partial Layouts](reflow.md)\
    Hover styles, two-phase layout, and faster rendering
(@) [Keeping Data Private](security.md)\
    Cookies, logins, and XSS and CSRF
