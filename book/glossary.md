---
title: Glossary 
...

Web browsers can be quite confusing to understand, especially once you consider
the breadth of all their features. As with all software engineering - and indeed
all complex subjects - *the best way to avoid confusion is to use consistent and
clear names*.

Key web terms
=============

__HTTP__: HyperText Transport Protocol, the network protocol for loading web
pages.

__HTTPS__: A variant of HTTP that uses public-key cryptography for
network security.

__URL__: Uniform Resource Locator. The name used to refer uniquely to a web
page.

__Web page__: The basic unit of the web; defined by unique __URL__.

__HTML__: HyperText Markup Language, the XML-like format of web pages.

__Hyperlink__: A reference from one web page to another.

__WWW__: World Wide Web. A name for the network of web pages built
on __HTTP__, __hyperlinks__, __HTML__, __CSS__ and __JavaScript__, as
well as the open and decentralized rules that (informally) govern them.

__Web__: Simplified name for __WWW__.

__Web Browser__: A software program that allows people to load and navigate
web pages.

__Rendering Engine__: The part of a Web Browser concerned with drawing a web
page to the screen and interacting with it.

Standards
=========

__W3C__: World Wide Web Consortioum. The central standardization organization of
the __WWW__. Among many other APIs, this is where __CSS__ is standardized.

__WHATWG__: Web Hypertext Application Technology Working Group. The
standardization organization for __HTML__, __DOM__, and a few other key web
APIs.

__TC39__: Technical Committe 39. The standardization organization for
JavaScript.

__IETF__: Internet Engineering Task Force. The standardization organization
for __HTTP__ as well as some other APIs.


Document model
==================

__Document__: The conceptual object created when loading a web page. Web pages
use the metaphor of physical documents to explain how they work.

__Page__: The conceptual container for a __document__. Unlike its physical
analogue, a page can have multiple documents (through use of __iframes__).

__IFrame__: a way of embedding a child __document__ within a parent, through
a rectangular window on the screen reserved for it that participates in the
layout of the parent.


__DOM__: Document Object Model. The object-oriented API interface to JavaScript
for mutating the __document__. It contains in particular a tree of __Nodes__;
on first page load this tree corresponds to the nested structure of the
__HTML__.

__Node__: A point in the __DOM__ tree, with parent and child pointers.

__Element__: Most __Nodes__ in the __DOM__ tree are Elements (except for
text and the document object). (Inherits from __Node__.)

__CSS__: Cascading Style Sheet. A format for storing rules that specify the
(mostly visual) styling of __element__s in the __DOM__.

Box model
=========

![](https://www.w3.org/TR/CSS2/images/boxdim.png)

__Margin rectangle__: The rectangle that encloses the margin (dark dashed line
in the figure). Margin in the the spacing between elements.

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
