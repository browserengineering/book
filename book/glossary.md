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

__HTML__: HyperText Markup Language, the XML-like format of web pages.

__Hyperlink__: A reference from one web page to another.

__HTTP__: HyperText Transport Protocol, the network protocol for loading web
pages.

__HTTPS__: A variant of HTTP that uses public-key cryptography for
network security.

__URL__: Uniform Resource Locator. The name used to refer uniquely to a web
page.

__Rendering engine__: The part of a Web Browser concerned with drawing a web
page to the screen and interacting with it. There are three rendering engines
actively maintained today: Chromium, WebKit and Gecko.

__Web__: Simplified name for __WWW__.

__Web browser__: A software program that allows people to load and navigate
web pages.

__Web page__: The basic unit of the web; defined by unique __URL__.

__WWW__: World Wide Web. A name for the network of web pages built
on __HTTP__, __hyperlinks__, __HTML__, __CSS__ and __JavaScript__, as
well as the open and decentralized rules that (informally) govern them.

Standards
=========

__IETF__: Internet Engineering Task Force. The standardization organization
for __HTTP__ as well as some other APIs.

__TC39__: Technical Committe 39. The standardization organization for
JavaScript.

__Khronos__: The Khronos Group. The standardization organization for WebGL
and WebGPU.

__W3C__: World Wide Web Consortioum. The central standardization organization of
the __WWW__. Among many other APIs, this is where __CSS__ is standardized.

__WHATWG__: Web Hypertext Application Technology Working Group. The
standardization organization for __HTML__, __DOM__, and a few other key web
APIs.




Document model
==============

__Animation__: A sequence of visual changes on a computer screen
interpreted by humans to look like movement.

__CSS__: Cascading Style Sheet. A format for storing rules that specify the
(mostly visual) styling of __element__s in the __DOM__.

__Document__: The conceptual object created when loading a web page. Web pages
use the metaphor of physical documents to explain how they work.

__DOM__: Document Object Model. The object-oriented API interface to JavaScript
for mutating the __document__. It contains in particular a tree of __Nodes__;
on first page load this tree corresponds to the nested structure of the
__HTML__.

__Element__: Most __Nodes__ in the __DOM__ tree are Elements (except for
text and the document object). (Inherits from __Node__.)

__Focus__: the property of an __element__ being the highlight, or "focus",
of user interaction, and therefore receiving keyboard events and being
visually highlighted on the screen.

__IFrame__: a way of embedding a child __document__ within a parent, through
a rectangular window on the screen reserved for it that participates in the
layout of the parent.

__Node__: A point in the __DOM__ tree, with parent and child pointers.

__Page__: The conceptual container for a __document__. Unlike its physical
analogue, a page can have multiple documents (through use of __iframes__).


Box model
=========

![](https://www.w3.org/TR/CSS2/images/boxdim.png)

__Margin rectangle__: The rectangle that encloses the margin (dark dashed line
in the figure). Margin in the spacing between elements.

__Border rectangle__: The rectangle that encloses the border (dark solid line
in the figure). Borders can have a styled visual representation.

__Padding rectangle__: The rectangle that encloses the padding (light dashed
line in the figure). The spacing between the border and the content.

__Content rectangle__: The rectangle that enloses the content (light solid line
in the figure). Child elements and text are normally enclosed by this
rectangle.

CSS
===
__Style__: All the pieces of information necessary to determine the visual
display of an __Element__.

__CSS property__: A single concept (such as "color" or "width") used to style
a specific part of an __element__.

__Property value__: a key-value pair of a __CSS property__ and its value
(e.g. "color" and "blue" or "width" and "30px").

__Selector__: A way of specifying to which __Elements__ a given list of
__property values__ apply.

__Rule__: The combination of a __selector__ and __property values__.

__Cascade__: The order in which to apply multiple rules to the same
__Element__.

__Computed Style__: The values for the __CSS Properties__ that apply to
elements after applying all __rules__ according to the __cascade__ order.

Coordinate spaces
=================

There are several 2D coordinate spaces that are very conveinient to answer
questions like: where is this element relative to another one? Where is it
relative to the web page? where is it on the screen?

Most of the coordinate systems we'll cover in this book are __physical__, meaning
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

__Element__: The origin is at the top-left of the __border rectangle__ of the
element.

Rendering
=========

__Compositing__: The phase oof a browser rendering pipeline that divides the
display list into pieces suitable for rendering into independent
__surfaces__ on a __GPU__, in order to speed up animations.

__Display list__: A sequence of graphics commands explaining how to draw a
web page to a computer screen.

__Draw__: The phase of a browser rendering pipeline that puts a set of surfaces
onto the screen with various positions and __visual effects__.

__Event Loop__: An infinite loop in browsers that alternates between receiving
user input and drawing to the screen.

__Layout__: The phase of a browser rendering pipeline that determines the
size and position of __elements__ in the __DOM__. 

__Paint__: The phase of a browser rendering pipeline that creates a display
list from the __DOM__.

__Rendering pipeline__: The sequence of phases by which a browser draws
a web page onto a computer screen.

__Raster__: THe process of excuting a __display list__ and outputting pixels
into a __surface__.

__Scroll__: adjusting the horizontal or vertical offset of a web page
in response to user input, in order to see parts of it not currently visible.

__Style__: The phase of a browser rendering pipeline that applies CSS rules to
determine the visual appearance and behavior of __elements__ in the __DOM__.
Or, the set of CSS properties applied to an element after this phase.

__Surface__: A buffer or texture within a GPU that represents a 2D array of
pixels.

__Visual effect__: A CSS property that does not affect __layout__.

Computer technologies
=====================

__GPU__: Graphics Processing Unit, a specialized computing chip optimized for
tasks common to generating pixel output on computer screens.