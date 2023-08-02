---
title: Glossary 
...

Web browsers can be quite confusing to understand, especially once you consider
the breadth of all their features. As with all software engineering - and indeed
all complex subjects - *the best way to avoid confusion is to use consistent and
clear names*.

Key web terms
=============

__Accessibility__: The ability of any person to access and use a web page,
regardless of ability; technology to achieve the same.

__Browser chrome__: The UI of a browser, such as tabs or a URL bar,
outside of any web pages it's currently displaying.

__HTML__: HyperText Markup Language, the XML-like format of web pages.

__Hyperlink__: A reference from one web page to another.

__HTTP__: HyperText Transport Protocol, the network protocol for loading web
pages.

__HTTPS__: A variant of HTTP that uses public-key cryptography for
network security.

__Hypertext__: A non-linear form of information comprised of multiple documents
connected with contextual links.

__JavaScript__: The scripting language for the web. (WebAssembly also now
exists but is much less common.)

__URL__: Uniform Resource Locator. The name used to refer uniquely to a web
page.

__Rendering engine__: The part of a web browser concerned with drawing a web
page to the screen and interacting with it. There are three rendering engines
actively maintained today: Chromium, WebKit and Gecko.

__Script__: A piece of code that extends a web page with more functionality,
usually written in JavaScript.

__Web Security__: The ability of the web (or individual browsers or
applications that are part of it) to be used without causing unintentional
harm. There are lots of different aspects of security: browser security (the
computer system a browser is running on can't be harmed by it), web application
security (a web application can't be harmed by its users), privacy (a third
party can't harm a web user by observing their use of the web), and many
others.

__Web__: Simplified name for WWW.

__Web browser__: A software program that allows people to load and navigate
web pages.

__Web page__: The basic unit of the web; defined by unique URL.

__WWW__: World Wide Web. A name for the network of web pages built
on HTTP, hyperlinks, HTML, CSS and JavaScript, as
well as the open and decentralized rules that (informally) govern them.

Standards
=========

__IETF__: Internet Engineering Task Force. The standardization organization
for __HTTP__ as well as some other APIs.

__TC39__: Technical Committee 39. The standardization organization for
JavaScript.

__Khronos__: The Khronos Group. The standardization organization for WebGL
and WebGPU.

__W3C__: World Wide Web Consortium. The central standardization organization of
the __WWW__. Among many other APIs, this is where CSS is standardized.

__WHATWG__: Web Hypertext Application Technology Working Group. The
standardization organization for HTML, DOM, and a few other key web
APIs.

Web Documents
=============

__Animation__: A sequence of visual changes on a computer screen
interpreted by humans to look like movement.

__HTML Attribute__: A parameter on an element indicating some
information, such as the source of an image or URL of a style sheet.

__Parsing__: Turning a serialized representation (such as HTML or CSS) into a data structure such as the document tree or a style sheet.

__CSS__: Cascading Style Sheet. A format for representing rules that specify the
(mostly visual) styling of elements in the DOM.

__Document__: The conceptual object created when loading a web page. Web pages
use the metaphor of physical documents to explain how they work.

__Document tree__: The tree created from parsing HTML. Also sometimes called
the DOM.

__DOM__: Document Object Model. The object-oriented API interface to JavaScript
for mutating the document It contains in particular a tree of nodes;
on first page load this tree corresponds to the nested structure of the
HTML.

__Element__: Most nodes in the DOM tree are elements (except for
text and the document object).

__Event__: A way for JavaScript to observe that something has happened on the
document, and customize its results.

__Focus__: The property of an element (sometimes in the web page, sometimes
in the browser chrome) being the highlight, or "focus",
of user interaction, and therefore receiving keyboard events and being
visually highlighted on the screen.

__Font__: A particular stylistic way of drawing a particular human language to
computer screens. Times New Roman is one common example for Latin-based
languages.

__Iframe__: A way of embedding a child document within a parent, through
a rectangular window on the screen reserved for it that participates in the
layout of the parent.

__Image__: A representation of a picture to draw on a computer screen. An
HTML element of the same name, for the same purpose.

__Node__: A point in the DOM tree, with parent and child pointers.

__Page__: The conceptual container for a document. Unlike its physical
analogue, a page can have multiple documents (through use of iframes).

__Style sheet__: A document resource that contains CSS rules.

__Tag name__: The name of a particular type of HTML element, indicating its
semantic function in the document. Usually comes with special style rules
and functionality specific to it.

Networking
==========

__GET__: The mode of HTTP that retrieves a server resource without changing it.

__Cookie__: A piece of persistent, per-site state stored by web browsers
to enable use cases like user logged-in status for access-controlled content.

__Domain__: The name of a website, used to locate it on the internet.

__Path__: The part of a URL after the domain and port.

__Port__: A number after the domain and before the path in a URL, indicating
a numbered place on that domain with which to communicate.

__POST__: The mode of HTTP that submits a change to server state and expects
a newly updated web page in response.

__Scheme__: The first part of a URL, indicating which protocol to use for
communication, such as HTTP or HTTPS.

__TLS/SSL__: Secure Sockets Layer. An encryption-based protocol that enables
secure HTTP (i.e., HTTPS) connections. TLS is a newer protocol
replacing SSL, but SSL is often used to describe both.

CSS
===

__Cascade order__: The order of application of multiple CSS rules to a
single element.

__Computed Style__: The values for the CSS Properties that apply to
elements after applying all rules according to the cascade order.

__CSS property__: A single concept (such as "color" or "width") used to style
a specific part of an element.

__CSS Property value__: a key-value pair of a CSS property and its value
(e.g. "color" and "blue" or "width" and "30px").

__CSS Rule__: The combination of a selector and property values.

__CSS Selector__: A way of specifying to which Elements a given list of
__property values__ apply.

__Inheritance__: The property of certain CSS styles (such as font sizing) applying to descendant elements in the document tree by default.

__Style__: All the pieces of information necessary to determine the visual
display of an element.

__Cascade__: The order in which to apply multiple rules to the same
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

__Viewport__: The origin is at the top-left of the rectangle on the screen into
which the web page is drawn.

__Page__: The origin is at the top-left of the web page's root element. When
a web page is scrolled, this top-left may be off the top of the screen.

__Element__: The origin is at the top-left of the layout bounds of the
element.

Rendering
=========

__Accessibility tree__: A tree representing the semantic meaning of a web page
meant for consumption by assistive technologies.

__Canvas__: A conceptual object which can execute drawing commands, typically
backed by a surface. Also a web API of the same name that serves the same
purpose.

__Compositing__: The phase of a browser rendering pipeline that divides the
display list into pieces suitable for rendering into independent
surfaces on a GPU, in order to speed up animations.

__Decode__: converting from a compressed format for a resource (such as an 
an image) into a simpler format in memory (such as a bitmap).

__Display list__: A sequence of graphics commands explaining how to draw a
web page to a computer screen.

__Draw__: The phase of a browser rendering pipeline that puts a set of surfaces
onto the screen with various positions and visual effects.

__Event loop__: An infinite loop in browsers that alternates between receiving
user input and drawing to the screen.

__Hit testing__: Determining which element or accessibility tree node
is  at a given pixel location on the screen.

__Invalidation__: Marking some rendering state as no longer valid, because its
input dependencies have changed.

__Layout__: The phase of a browser rendering pipeline that determines the
size and position of elements in the DOM. 

__Layout tree__: A second tree that mirrors the DOM, except that it represents
the output of the layout pipeline phase.

__Paint__: The phase of a browser rendering pipeline that creates a display
list from the DOM.

__Rendering pipeline__: The sequence of phases by which a browser draws
a web page onto a computer screen.

__Raster__: The process of executing a display list and outputting pixels
into a surface.

__Scroll__: adjusting the horizontal or vertical offset of a web page
in response to user input, in order to see parts of it not currently visible.

__Style__: The phase of a browser rendering pipeline that applies CSS rules to
determine the visual appearance and behavior of elements in the DOM.
Or, the set of CSS properties applied to an element after this phase.

__Surface__: A buffer or texture within a GPU that represents a 2D array of
pixels.

__Visual effect__: A CSS property that does not affect layout.

__Zoom__: Changing the ratio of CSS sizes to pixels in order to  make
content on a web page larger or smaller.

Computer technologies
=====================

__Assistive technology__: Computer software used to assist people in using
the computer or web browser. The most common are screen readers.

__CPU__: Central Processing Unit, the hardware component in a computer that
executes generic compute programs.

__DukPy__: A JavaScript interpreter used in this book.

__GPU__: Graphics Processing Unit, a specialized computing chip optimized for
tasks common to generating pixel output on computer screens.

__Process__: A conceptual execution environment with its own code and
memory, isolated from other processes by hardware and software computer
mechanisms.

__Python__: A common computer programming language, used in this
book to implement a toy browser.

__Thread__: A single execution command sequence on a CPU. Most CPUs have
these days can execute multiple threads at once within a single process.

__SDL__: A windowing library for computer programs used in later chapters of
this book.

__Skia__: A raster drawing library for computer programs used in later chapters
of this book.

__Tk__: A UI drawing library for computer programs used in early chapters of
this book.

