---
title: Glossary 
...

Web browsers can be quite confusing to understand, especially once you consider
the breadth of all their features. As with all software engineering - and indeed
all complex subjects - *the best way to avoid confusion is to use consistent and
clear names*.

Key web terms
=============

*Accessibility*: The ability of any person to access and use a web page,
regardless of ability; technology to achieve the same.

*Browser chrome*: The UI of a browser, such as tabs or a URL bar,
outside of any web pages it's currently displaying.

*HTML*: HyperText Markup Language, the XML-like format of web pages.

*Hyperlink*: A reference from one web page to another.

*HTTP*: HyperText Transport Protocol, the network protocol for loading web
pages.

*HTTPS*: A variant of HTTP that uses public-key cryptography for
network security.

*Hypertext*: A non-linear form of information comprised of multiple documents
connected with contextual links.

*JavaScript*: The scripting language for the web. (WebAssembly also now
exists but is much less common.)

*URL*: Uniform Resource Locator. The name used to refer uniquely to a web
page.

*Rendering engine*: The part of a web browser concerned with drawing a web
page to the screen and interacting with it. There are three rendering engines
actively maintained today: Chromium, WebKit and Gecko.

*Script*: A piece of code that extends a web page with more functionality,
usually written in JavaScript.

*Web Security*: The ability of the web (or individual browsers or
applications that are part of it) to be used without causing unintentional
harm. There are lots of different aspects of security: browser security (the
computer system a browser is running on can't be harmed by it), web application
security (a web application can't be harmed by its users), privacy (a third
party can't harm a web user by observing their use of the web), and many
others.

*Web*: Simplified name for WWW.

*Web browser*: A software program that allows people to load and navigate
web pages.

*Web page*: The basic unit of the web; defined by unique URL.

*WWW*: World Wide Web. A name for the network of web pages built
on HTTP, hyperlinks, HTML, CSS and JavaScript, as
well as the open and decentralized rules that (informally) govern them.

Standards
=========

*IETF*: Internet Engineering Task Force. The standardization organization
for HTTP as well as some other APIs.

*TC39*: Technical Committee 39. The standardization organization for
JavaScript.

*Khronos*: The Khronos Group. The standardization organization for WebGL
and WebGPU.

*W3C*: World Wide Web Consortium. The central standardization organization of
the WWW. Among many other APIs, this is where CSS is standardized.

*WHATWG*: Web Hypertext Application Technology Working Group. The
standardization organization for HTML, DOM, and a few other key web
APIs.

Web Documents
=============

*Animation*: A sequence of visual changes on a computer screen
interpreted by humans to look like movement.

*HTML Attribute*: A parameter on an element indicating some
information, such as the source of an image or URL of a style sheet.

*Parsing*: Turning a serialized representation (such as HTML or CSS) into a data structure such as the document tree or a style sheet.

*CSS*: Cascading Style Sheet. A format for representing rules that specify the
(mostly visual) styling of elements in the DOM.

*Document*: The conceptual object created when loading a web page. Web pages
use the metaphor of physical documents to explain how they work.

*Document tree*: The tree created from parsing HTML. Also sometimes called
the DOM.

*DOM*: Document Object Model. The object-oriented API interface to JavaScript
for mutating the document It contains in particular a tree of nodes;
on first page load this tree corresponds to the nested structure of the
HTML.

*Element*: Most nodes in the DOM tree are elements (except for
text and the document object).

*Event*: A way for JavaScript to observe that something has happened on the
document, and customize its results.

*Focus*: The property of an element (sometimes in the web page, sometimes
in the browser chrome) being the highlight, or "focus",
of user interaction, and therefore receiving keyboard events and being
visually highlighted on the screen.

*Font*: A particular stylistic way of drawing a particular human language to
computer screens. Times New Roman is one common example for Latin-based
languages.

*Iframe*: A way of embedding a child document within a parent, through
a rectangular window on the screen reserved for it that participates in the
layout of the parent.

*Image*: A representation of a picture to draw on a computer screen. An
HTML element of the same name, for the same purpose.

*Node*: A point in the DOM tree, with parent and child pointers.

*Page*: The conceptual container for a document. Unlike its physical
analogue, a page can have multiple documents (through use of iframes).

*Style sheet*: A document resource that contains CSS rules.

*Tag name*: The name of a particular type of HTML element, indicating its
semantic function in the document. Usually comes with special style rules
and functionality specific to it.

Networking
==========

*GET*: The mode of HTTP that retrieves a server resource without changing it.

*Cookie*: A piece of persistent, per-site state stored by web browsers
to enable use cases like user logged-in status for access-controlled content.

*Domain*: The name of a website, used to locate it on the internet.

*Path*: The part of a URL after the domain and port.

*Port*: A number after the domain and before the path in a URL, indicating
a numbered place on that domain with which to communicate.

*POST*: The mode of HTTP that submits a change to server state and expects
a newly updated web page in response.

*Scheme*: The first part of a URL, indicating which protocol to use for
communication, such as HTTP or HTTPS.

*TLS/SSL*: Secure Sockets Layer. An encryption-based protocol that enables
secure HTTP (i.e., HTTPS) connections. TLS is a newer protocol
replacing SSL, but SSL is often used to describe both.

CSS
===

*Cascade order*: The order of application of multiple CSS rules to a
single element.

*Computed Style*: The values for the CSS Properties that apply to
elements after applying all rules according to the cascade order.

*CSS property*: A single concept (such as "color" or "width") used to style
a specific part of an element.

*CSS Property value*: a key-value pair of a CSS property and its value
(e.g. "color" and "blue" or "width" and "30px").

*CSS Rule*: The combination of a selector and property values.

*CSS Selector*: A way of specifying to which Elements a given list of
*property values* apply.

*Inheritance*: The property of certain CSS styles (such as font sizing) applying to descendant elements in the document tree by default.

*Style*: All the pieces of information necessary to determine the visual
display of an element.

*Cascade*: The order in which to apply multiple rules to the same
element.

Coordinate spaces
=================

There are several 2D coordinate spaces that are very convenient to answer
questions like: where is this element relative to another one? Where is it
relative to the web page? where is it on the screen?

Most of the coordinate systems we'll cover in this book are physical, meaning
that all that is needed is the `(x=0, y=0)` origin of the coordinate space; `x`
grows in the horizontal direction towards the right, and `y` grows in the
vertical direction towards the bottom. Unless otherwise indicated, all
coordinate systems.[^logical-coordinates]

[^logical-coordinates]: There are also some *logical* coordinate systems, which
differ in that they may flip the direction of `x` and `y` accordingly to the
direction of the writing mode of the language. Coordinate spaces for web pages
can be quite confusing once one takes into account all of the complexities of
containing blocks, scrolling and positioning. For example, in Arabic it makes
sense for `x` to grow towards the left, and the origin is often at the
top-right, not the top-left.

*Viewport*: The origin is at the top-left of the rectangle on the screen into
which the web page is drawn.

*Page*: The origin is at the top-left of the web page's root element. When
a web page is scrolled, this top-left may be off the top of the screen.

*Element*: The origin is at the top-left of the layout bounds of the
element.

Rendering
=========

*Accessibility tree*: A tree representing the semantic meaning of a web page
meant for consumption by assistive technologies.

*Canvas*: A conceptual object which can execute drawing commands, typically
backed by a surface. Also a web API of the same name that serves the same
purpose.

*Compositing*: The phase of a browser rendering pipeline that divides the
display list into pieces suitable for rendering into independent
surfaces on a GPU, in order to speed up animations.

*Decode*: converting from a compressed format for a resource (such as an 
an image) into a simpler format in memory (such as a bitmap).

*Display list*: A sequence of graphics commands explaining how to draw a
web page to a computer screen.

*Draw*: The phase of a browser rendering pipeline that puts a set of surfaces
onto the screen with various positions and visual effects.

*Event loop*: An infinite loop in browsers that alternates between receiving
user input and drawing to the screen.

*Hit testing*: Determining which element or accessibility tree node
is  at a given pixel location on the screen.

*Invalidation*: Marking some rendering state as no longer valid, because its
input dependencies have changed.

*Layout*: The phase of a browser rendering pipeline that determines the
size and position of elements in the DOM. 

*Layout tree*: A second tree that mirrors the DOM, except that it represents
the output of the layout pipeline phase.

*Paint*: The phase of a browser rendering pipeline that creates a display
list from the DOM.

*Rendering pipeline*: The sequence of phases by which a browser draws
a web page onto a computer screen.

*Raster*: The process of executing a display list and outputting pixels
into a surface.

*Scroll*: adjusting the horizontal or vertical offset of a web page
in response to user input, in order to see parts of it not currently visible.

*Style*: The phase of a browser rendering pipeline that applies CSS rules to
determine the visual appearance and behavior of elements in the DOM.
Or, the set of CSS properties applied to an element after this phase.

*Surface*: A buffer or texture within a GPU that represents a 2D array of
pixels.

*Visual effect*: A CSS property that does not affect layout.

*Zoom*: Changing the ratio of CSS sizes to pixels in order to  make
content on a web page larger or smaller.

Computer technologies
=====================

*Assistive technology*: Computer software used to assist people in using
the computer or web browser. The most common are screen readers.

*CPU*: Central Processing Unit, the hardware component in a computer that
executes generic compute programs.

*DukPy*: A JavaScript interpreter used in this book.

*GPU*: Graphics Processing Unit, a specialized computing chip optimized for
tasks common to generating pixel output on computer screens.

*Process*: A conceptual execution environment with its own code and
memory, isolated from other processes by hardware and software computer
mechanisms.

*Python*: A common computer programming language, used in this
book to implement a toy browser.

*Thread*: A single execution command sequence on a CPU. Most CPUs have
these days can execute multiple threads at once within a single process.

*SDL*: A windowing library for computer programs used in later chapters of
this book.

*Skia*: A raster drawing library for computer programs used in later chapters
of this book.

*Tk*: A UI drawing library for computer programs used in early chapters of
this book.

