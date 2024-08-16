---
title: Glossary 
...

Web browsers can be quite confusing to understand, especially once you consider
the breadth of all their features. As with all software engineering---indeed,
all complex subjects---the best way to avoid confusion is to use *clear and
consistent names*.

Key Web Terms
=============

Accessibility

: The ability of any person to access and use a web page,
regardless of ability, or technology to achieve the same.

Browser chrome

: The UI of a browser, such as a tab or URL bar, not
including the web page the browser is displaying.

HTML

: HyperText Markup Language, the XML-like format used to describe web pages.

HTTP

: HyperText Transport Protocol, the network protocol for loading web pages.

HTTPS

: A variant of HTTP that uses cryptography to provide network security.

Hyperlink

: A reference from one web page to another.

Hypertext

: A non-linear form of information comprised of multiple documents
connected with contextual links.

JavaScript

: The main programming language for web scripts.

Rendering engine

: The part of a web browser concerned with drawing a
web page to the screen and interacting with it. There are three main
rendering engines actively maintained today: Chromium, WebKit, and
Gecko.

Script

: A piece of code that extends a web page with more functionality,
usually written in JavaScript. Also the name of the HTML tag that contains
scripts.

URL

: Uniform Resource Locator, the name used to uniquely refer to a web
page or resource.

Web

: Simplified name for the WWW.

Web browser

: Software that allows people to load and
navigate web pages. Also often just called a "browser".

Web page

: The basic unit of the web; defined by a unique URL that returns HTML.

Web resource

: Anything with its own URL on the web. Web pages are
resources, but so are many of their component parts, such as scripts,
images, and style sheets. Resources that are not the HTML page itself
are called *subresources*.

Web security

: The ability to intentionally limit the behavior of web
browsers, servers, or applications, usually to prevent
harm, unintentional or not. There are lots of different aspects of security:
browser security (so the user's computer isn't harmed by their browser), web
application security (so a web application can't be harmed by its
users), privacy (so a third party can't harm a web user), and many
others.

Website

: A collection of web pages that together provide some user
service.

WWW

: World Wide Web. A name for the network of web pages built on
HTTP, hyperlinks, HTML, CSS and JavaScript, as well as the open and
decentralized rules that govern them.

Standards
=========

IETF

: Internet Engineering Task Force. The standardization organization
for HTTP as well as some other APIs.

Khronos

: The Khronos Group. The standardization organization for WebGL
and WebGPU.

TC39

: Technical Committee 39. The standardization organization for JavaScript.

W3C

: World Wide Web Consortium. The central standardization organization of
the WWW. Among many other APIs, this is where CSS is standardized.

WHATWG

: Web Hypertext Application Technology Working Group. The
standardization organization for HTML, DOM, and a few other key web
APIs.

Web Documents
=============

Animation

: A sequence of visual changes on a computer screen
interpreted by humans to look like movement.

CSS

: Cascading Style Sheet. A format for representing rules that
specify the (mostly visual) styling of elements in the DOM.

Document

: The conceptual object created by loading a web page and
modified by interacting with it, an analogy to physical documents.

DOM

: Document Object Model. The object-oriented API interface to JavaScript
for mutating the document. It contains in particular a tree of nodes;
this tree initially corresponds to the nested structure of the
HTML.

Element

: Most nodes in the HTML tree are elements (except for
text and the document object).

Event

: A way for JavaScript to observe that something has happened on the
document and customize its results.

Focus

: The property of an element (sometimes in the web page,
sometimes in the browser chrome) being set to receive future keyboard
events and other user interactions. Typically, the focused element is
visually highlighted on the screen.

Font

: A particular stylistic way of drawing a particular human language to
computer screens. Times New Roman is one common example for Latin-based
languages.

HTML attribute

: A parameter on an element indicating some
information, such as the source of an image or the URL of a style sheet.

HTML tree

: The tree created from parsing HTML. Also sometimes
called the DOM.

Iframe

: A way of embedding one document within another. A
rectangular window in the parent document shows the child document and
participates in the layout of the parent.

Image

: A representation of a picture to draw on a computer screen.

Node

: A point in the DOM tree, with parent and child pointers.

Page

: The conceptual container for a document. A page can have
multiple documents through use of iframes.

Parsing

: Turning a serialized representation (such as HTML or CSS)
into a data structure such as the document tree or a style sheet.

Style sheet

: A web resource that contains CSS rules.

Tag name

: The name of a particular type of HTML element, indicating its
semantic function in the document. Usually comes with special style rules
and functionality specific to it.

Networking
==========

Cookie

: A piece of persistent, per-site state stored by web browsers
to enable use cases like user login for access-controlled content.

Domain

: The name of a website, used to locate it on the internet.

GET

: The mode of HTTP that retrieves a server resource without changing it.

Path

: The part of a URL after the domain and port.

Port

: A number after the domain and before the path in a URL, indicating
a numbered place on that domain with which to communicate.

POST

: The mode of HTTP that submits a change to server state and expects
a newly updated web page in response.

Scheme

: The first part of a URL, indicating which protocol to use for
communication, such as HTTP or HTTPS.

TLS/SSL

: Transport Layer Security and Secure Sockets Layer. An
encrypted protocol atop which other protocols like HTTP can take place
securely (i.e., HTTPS). TLS is a newer protocol replacing SSL, but SSL
is often used to describe both.

CSS
===

Cascade order

: The order of application of multiple CSS rules to a
single element.

Computed style

: The values for the CSS properties that apply to
elements after applying all rules according to the cascade order.

CSS property

: A single concept (such as `color` or `width`) used to style
a specific aspect of an element.

CSS property–value

: A key–value pair of a CSS property and its value
(e.g. `color` and `blue` or `width` and `30px`).

CSS rule

: The combination of a CSS selector and CSS property-values.

CSS selector

: The part of a CSS rule that specifies to which elements a
given list of property values applies.

Inheritance

: When an element takes its computed style for a property
from its parent element. Sometimes mistakenly called "cascading". Some
CSS properties (such as font sizing) are inherited by default.

Style

: All the pieces of information necessary to determine the visual
display of an element. Also the name of a corresponding attribute to
specify inline styles.

Coordinate Spaces
=================

In the browser, 2D coordinate spaces are used to determine where
elements are relative to one another, the web page, and the screen.
Most of these coordinate systems use the standard *x* and *y*
directions but with different origins, though not all.[^logical-coordinates]

[^logical-coordinates]: Some *logical* coordinate systems flip the
direction of *x* and *y* according to the direction of the writing
mode of the language. For example, in Arabic it makes sense for *x* to
grow towards the left, and the origin is often at the top-right, not
the top-left. This becomes confusing when nesting, containing blocks,
scrolling, and positioning are used together.

Element

: This coordinate system's origin is at the top-left of the
layout bounds of the element, which may be off the top or left of the
viewport if margins or positioning is used.

Layer

: This coordinate system's origin is at the top-left of a
composited layer, which is chosen so as to include all of the paint
objects within the layer.

Page

: This coordinate system's origin is at the top-left of the web
page's root element. When a web page is scrolled, this top-left may be
off the top of the viewport.

Paint

: This coordinate system's origin is at the top-left of the
paint bounds of the element, which may not match the element
coordinate system if transforms like `translate` are used. Real
browsers also support more complex transforms such as `rotate`.

Viewport

: This coordinate system's origin is at the top-left of the
rectangle on the screen into which the web page is drawn.

Rendering
=========

Accessibility tree

: A tree representing the semantic meaning of a web page
meant for consumption by assistive technologies.

Canvas

: A conceptual object which can execute drawing commands. Also
a web API of the same name that serves the same purpose. Typically
backed by a surface.

Compositing

: The phase of a browser rendering pipeline that divides the
display list into pieces suitable for rendering into independent
surfaces on a GPU, in order to speed up animations.

Decode

: Convert from a compressed format for a resource (such as
an image) into a simpler format in memory (such as a bitmap).

Device pixel ratio

: The ratio between the screen pixel resolution and a
"typical" screen (defined as the pixel resolution of a 1990s CRT).

Display list

: A sequence of graphics commands explaining how to draw a
web page to a computer screen.

Draw

: The phase of a browser rendering pipeline that puts a set of surfaces
onto the screen with various positions and visual effects.

Event loop

: A loop that alternates between receiving user input and
drawing to the screen.

Hit testing

: Determining which element or accessibility tree node
is at a given pixel location on the screen.

Invalidation

: Marking some rendering state as no longer valid, because its
input dependencies have changed.

Layout

: The phase of a browser rendering pipeline that determines the
size and position of elements in the DOM. 

Layout tree

: A second tree that mirrors the DOM, except that it represents
the output of the layout pipeline phase.

Paint

: The phase of a browser rendering pipeline that creates a display
list from the DOM.

Raster

: The process of executing a display list by coloring the
pixels of a surface.

Rendering pipeline

: The sequence of phases by which a browser draws
a web page onto a computer screen.

Scroll

: Adjusting the horizontal or vertical offset of a web page
in response to user input, in order to see parts of it not currently visible.

Style

: The phase of a browser rendering pipeline that applies CSS rules to
determine the visual appearance and behavior of elements in the DOM.
Or, the set of CSS properties applied to an element after this phase.

Surface

: A buffer or texture within a GPU that represents a 2D array of
pixels.

Visual effect

: A CSS property that does not affect layout.

Zoom

: Changing the ratio of CSS sizes to pixels in order to make
content on a web page larger or smaller.

Computer Technologies
=====================

Assistive technology

: Computer software used to assist people in using
the computer or web browser. The most common are screen readers.

CPU

: Central processing unit, the hardware component in a computer that
executes generic compute programs.

DukPy

: A Python binding library for Duktape, a JavaScript engine used in
this book.

GPU

: Graphics processing unit, a specialized computing chip optimized for
tasks like generating pixel output on computer screens.

Process

: A conceptual execution environment with its own code and
memory, isolated from other processes by hardware and software computer
mechanisms.

Python

: A common computer programming language, used in this
book to implement a toy browser.

SDL

: A windowing library for computer programs used in later chapters of
this book.

Skia

: A raster drawing library for computer programs used in later chapters
of this book.

Thread

: A single sequence of commands executed on a CPU. Most CPUs 
these days can execute multiple threads at once.

Tk

: A UI drawing library for computer programs used in early chapters of
this book.

Tkinter

: A Python library wrapping Tk.
