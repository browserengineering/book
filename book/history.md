---
title: History of the Web
type: Background
next: http
prev: intro
...

If you've read this far, hopefully you're convinced that browsers are
interesting and important to study. Now we'll dig a bit into the web itself,
where it came from, and how the web and browsers have evolved to date. This
history is by no means exhaustive.[^sgml] Instead, it'll focus on some key
events and ideas that led to the web. These ideas and events will explain how
exactly a thing such as the web came to be, as well as the motivations and goals
of those who created it and its predecessors.

[^sgml]: For example, there is nothing much about
[SGML](https://en.wikipedia.org/wiki/Standard_Generalized_Markup_Language) or
other predecessors to HTML. (Except in this footnote!)

The Memex concept
=================

<style>
	figure {
		text-align: center;
	}
</style>

<figure>
  <img src="https://upload.wikimedia.org/wikipedia/commons/7/7f/The_Memex_%283002477109%29.jpg">
</figure>

The earliest exploration of how computers might revolutionize information is a
1945 essay by Vannevar Bush entitled [As We May
Think](https://en.wikipedia.org/wiki/As_We_May_Think). This essay envisioned a
machine called a [Memex](https://en.wikipedia.org/wiki/Memex) that helps an
individual human (think: User Agent) to see and
explore all the information in the world. It was described in terms of microfilm
screen technology of the time, but its purpose and concept has some clear
similarities to the web as we know it today, even if the user interface and
technology details differ.

The web is at its core organized around the Memex-like goal of _representing and
displaying information_, and how to provide a way for humans to effectively
learn and explore that information. The collective knowledge and wisdom of the
species long ago exceeded the capacity of a single mind, organization, library,
country, culture, group or language. However, while we as humans cannot possibly
know even a tiny fraction of what is possible to know, we can use technology to
learn more efficiently than before, and, *in particular*, to quickly access
information we need to learn, remember or recall. Consider this imagined
research session described in the article, one that is remarkably similar to
how we'd use the web for the same tasks:

> The owner of the memex, let us say, is interested in the origin and properties
> of the bow and arrow. [..] He has dozens of possibly pertinent books and
> articles in his memex. First he runs through an encyclopedia, finds an
> interesting but sketchy article, leaves it projected. Next, in a history, he
> finds another pertinent item, and ties the two together. Thus he goes,
> building a trail of many items.

Computers, and the internet, allow us to _process and store_ as mucph information
as we want. But it is _the web_ that plays the role of _organizing and finding_
that information and knowledge, making it useful.[^google-mission]

[^google-mission]: The Google search engine's well-known
[mission](https://about.google/) statement to “organize the world’s information
and make it universally accessible and useful” is almost exactly the same.
This is not a coincidence---the search engine concept is inherently
connected to the web, and was inspired by the web's design and antecedents.

Two features of the memex were highlighted in the essay: information record
lookup, and associations between related records. In fact, the essay emphasizes
the importance of the latter---we learn and improve not just by learning what is
known, but by making previously-unknown connections *between known things*:

> The human mind does not work that way. It operates by association.

By "association", Bush meant a trail of thought leading from one record
to the next via a human-curated link. He imagined not just a universal
library, but a universal way to record the results of what we learn. That is
what the web can do today.

The web emerges
===============

The concept of interlinked [hypertext](hypertext) documents and the [hyperlink]
concept was invented in
[1964-65](https://en.wikipedia.org/wiki/Hyperlink#History) by [Project
Xanadu](xanadu), led by Ted Nelson.[^literary-criticism] Hypertext is text that
is marked up with hyperlinks to other text. A successor called [Hypertext
Editing System] was the first to introduce the back button concept, which all
browsers now have. (Since the system just had text, the "button" was itself
text.)

Hypertext is text that is marked up with hyperlinks to other text. Sounds
familiar? A web page is hypertext, and links between web pages are hyperlinks.
The format for writing web pages is HTML, which is short for HyperText Markup
Language. The protocol for loading web pages is HTTP, which is short for
HyperText Transport Protocol.

[Hypertext
Editing System]: https://en.wikipedia.org/wiki/Hypertext_Editing_System

<figure>
	<img src="https://upload.wikimedia.org/wikipedia/commons/c/cd/HypertextEditingSystemConsoleBrownUniv1969.jpg">
<caption>Hypertext Editing System</caption>
</figure>

Independently of Project Xanadu, the first hyperlink system appeared for
scrolling within a single document; it was later generalized to linking between
multiple documents. And just like those original systems, the web has linking
within documents as well as between them. For example, the url
"http://example.com/doc.html#link" refers to a document "doc.html", as well as
the element with the name "link" within it; clicking on a link to tha URL will
load "doc.html" and scroll to the "link" element.

This work also formed and inspired one of the key parts of Douglas Engelbart's
[mother of all demos](https://en.wikipedia.org/wiki/The_Mother_of_All_Demos),
perhaps the most influential technology demonstration in the history of
computing. That same demo not only showcased the key concepts of the web, but
also introduced the computer mouse and graphical user interface, both of which
are of course central components of a browser UI.[^even-more]

<figure>
	<img src="https://cdn.arstechnica.net/wp-content/uploads/2015/04/Engelbart-68-demo_0-2-640x426.jpg">
	<figcaption>The mother of all demos!</figcaption>
</figure>

[^even-more]: That demo went beyond even this! There are some parts of it that
have not yet been realized in any computer system. I highly recommend watching
the demo yourself.

[hypertext]: https://en.wikipedia.org/wiki/Hypertext

[xanadu]: https://en.wikipedia.org/wiki/Project_Xanadu

[^literary-criticism]: These concepts are also the computer-based evolution of
the long tradition of citation in academics and literary criticism. The
Project Xanadu research papers were heavily motivated by this use case.

There is of course a very direct connection between this research and the
document+URL+hyperlink setup of the web, which built on this idea and applied it
in practice. The [HyperTIES](http://www.cs.umd.edu/hcil/hyperties/) system, for
example, highlighted hyperlinks and was used to develop the world’s first
electronically published academic journal, the 1988 issue of the [Communications
of the ACM](https://cacm.acm.org/). Tim Berners-Lee cites this 1988 event as the
source of the link concept in his World Wide Web
idea,[^world-wide-web-terminology] in which he proposed to join the link
concept with the availability of the internet, thus realizing many of the
original goals of all the work from previous decades.[^realize-web-decades]

The word "hyperlink" may have been coined in 1987, in connection with the
[HyperCard] system on Apple computers. This system also was one of the first, or
the first, to introduce the concept of augmenting hypertext with scripts that
handle user events, such as clicks, and perform actions that enhance the
UI--just like JavaScript on a web page! It also had graphical UI elements and
not just text, unlike most predecessors.

[HyperCard]: https://en.wikipedia.org/wiki/HyperCard

[^world-wide-web-terminology]: Nowadays the World Wide Web is called just “the
web”, or “the web ecosystem”---ecosystem being another way to capture the same
concept as “World Wide”. The original wording lives on in the "www" in many
website domain names.

[^realize-web-decades]: Just as the web itself is an example of the realization
of previous ambitions and dreams, today we strive to realize the vision laid out
by the web. (No, it's not done yet!)

In 1989-1990, the first web browser (named “WorldWideWeb”) and web server (named
“httpd”, for “HTTP Daemon” according to UNIX naming conventions) were born,
written by Tim Berners-Lee. Interestingly, while that browser’s capabilities were in
some ways inferior to the browser you will implement in this book,[^no-css]
in other ways they go beyond the capabilities available even in modern
browsers.[^more-less-powerful] On December 20, 1990 the [first web
page](http://info.cern.ch/hypertext/WWW/TheProject.html) was created. The
browser we will implement in this book is easily able to render this web page,
even today.[^original-aesthetics] In 1991, Berners-Lee advertised his browser
and the concept on the [alt.hypertext Usenet
group](https://www.w3.org/People/Berners-Lee/1991/08/art-6484.txt).

<figure>
	<img src="https://www.w3.org/History/1994/WWW/Journals/CACM/screensnap2_24c.gif">
	<caption>WorldWideWeb, the first web browser</caption>
</figure>

[^no-css]: No CSS!

[^more-less-powerful]: For example, the first browser included the concept of an
index page meant for searching within a site (vestiges of which exist today in
the “index.html” convention when a URL path ends in /”), and had a WYSIWYG web
page editor (the “contenteditable” HTML attribute and “html()” method on DOM
elements have similar semantic behavior, but built-in file saving is gone).
Today, the index is replaced with a search engine, and web page editors as a
concept are somewhat obsolete due to the highly dynamic nature of today’s web
page rendering.

[^original-aesthetics]: Also, as you can see clearly, that web page has not been
updated in the meantime, and retains its original aesthetics!

Berners-Lee's [Brief History of the
Web](https://www.w3.org/DesignIssues/TimBook-old/History.html) highlights a
number of other interesting factors leading to the establishment of the web as
we know it. One key factor was its decentralized nature, which he describes as
arising from the academic culture of [CERN](https://home.cern/), where he
worked. The decentralized nature of the web is a key feature that distinguishes
it from many systems that came before or after, and his explanation of it is
worth quoting here (highlight is mine):

> There was clearly a need for something like Enquire [ed: a predecessor
> web-like database system, also written by Berners-Lee] but accessible to
> everyone. I wanted it to scale so that if two people started to use it
> independently, and later started to work together, *they could start linking
> together their information without making any other changes*. This was the
> concept of the web.

This quote captures one of the key value propositions of the web. The web was
successful for several reasons, but I believe it’s primarily the following
three:

 - It provides a very low-friction way to publish information and applications.
There is no gatekeeper to doing anything, and it’s easy for novices to make a
simple web page and publish it.

 - Once bootstrapped, it builds quickly upon itself via [network
effects](https://en.wikipedia.org/wiki/Network_effect) made possible by
compatibility between sites and the power of the hyperlink to reinforce this
compatibility. Hyperlinks drive traffic between sites, but also into the web
_from the outside_, from sources such as email, social networking, and search
engines.

 - It is outside the control of any one entity---and kept that way via
standards organizations---and therefore not subject to problems of monopoly
control or manipulation.

Browsers
========

The first _widely distributed_ browser may have been
[ViolaWWW](https://en.wikipedia.org/wiki/ViolaWWW); this browser also pioneered
multiple interesting features such as applets and images. This browser was in
turn the inspiration for [NCSA
Mosaic](https://en.wikipedia.org/wiki/Mosaic_(web_browser)), which launched in
1993. One of the two original authors of Mosaic went on to co-found Netscape,
which built [Netscape
Navigator](https://en.wikipedia.org/wiki/Netscape_Navigator), the first
_commercial browser_,[^commercial-browser] which launched in 1994.

<div style="display: grid; grid-template-columns: repeat(2, 1fr);">
<figure>
		<img src="https://upload.wikimedia.org/wikipedia/commons/e/ea/NCSA_Mosaic_Browser_Screenshot.png">
	<figcaption>Mosaic</figcaption>
</figure>
<figure>
		<img src="https://upload.wikimedia.org/wikipedia/en/0/0e/ViolaWWW.png">
		<figcaption>ViolaWWW</figcaption>
</figure>
<figure>
		<img src="https://upload.wikimedia.org/wikipedia/en/c/c9/Navigator_1-22.png">
		<figcaption>Netscape Navigator</figcaption>
</figure>
<figure>
		<img src="https://upload.wikimedia.org/wikipedia/en/3/39/Internet_Explorer_1.0.png">
		<figcaption>Internet Explorer 1.0</figcaption>
</figure>

</div>

The era of the [”first browser
war”](https://en.wikipedia.org/wiki/Browser_wars#First_Browser_War_(1995%E2%80%932001))
ensued, in a competition between Netscape Navigator and [Internet Explorer]. In addition,
there were other browsers with smaller market shares; one notable example is
[Opera](https://en.wikipedia.org/wiki/Opera_(web_browser)). The
[WebKit](https://en.wikipedia.org/wiki/WebKit) project began in 1999
([Safari](https://en.wikipedia.org/wiki/Safari_(web_browser)) and
[Chromium](https://www.chromium.org/)-based browsers, such as Chrome and newer
versions of [Edge](https://en.wikipedia.org/wiki/Microsoft_Edge), descend from
this codebase). Likewise, the
[Gecko](https://en.wikipedia.org/wiki/Gecko_(software)) rendering engine was
originally developed by Netscape starting in 1997; the
[Firefox](https://en.wikipedia.org/wiki/Firefox) browser is descended from this
codebase. During the first browser war period, nearly all of the core features
of this book's simple browser were added, including CSS, DOM, and JavaScript.

[Internet Explorer]: https://en.wikipedia.org/wiki/Internet_Explorer

 The "second browser war", which according to Wikipedia was
[2004-2017](https://en.wikipedia.org/wiki/Browser_wars#Second_Browser_War_(2004%E2%80%932017)),
was fought between a variety of browsers---Internet Explorer, Firefox, Safari and
Chrome in particular. Chrome split off its rendering engine subsystem into its
own code base called
[Blink](https://en.wikipedia.org/wiki/Blink_(browser_engine)) in 2013.
The second browser war saw the development of many features of the modern web,
including AJAX requests, HTML5 features like `<canvas>`, and a huge explosion in
third-party JavaScript libraries and frameworks.

[^commercial-browser]: By commercial I mean built by a for-profit entity.
Netscape's early versions were also not free software---you had to buy them from
a store. They cost about $50.

Web standards
=============

In parallel with these developments was another, equally important, one---the
standardization of web APIs. In October 1994, the [World Wide Web
Consortium](https://www.w3.org/Consortium/facts) (W3C) was founded in order to
provide oversight and standards for web features. Prior to this point, browsers
would often introduce new HTML elements or APIs, and competing browsers would
have to copy them. With a standards organization, those elements and APIs could
subsequently be agreed upon and documented in specifications. (These days, an
initial discussion, design and specification precedes any new feature.) Later
on, the HTML specification ended up moving to a different standards body called
the [WHATWG](https://whatwg.org/), but [CSS](https://drafts.csswg.org/) and
other features are still standardized at the W3C. JavaScript is standardized at
[TC39](https://tc39.es/) (“Technical Committee 39” at
[ECMA](https://www.ecma-international.org/memento/history.htm), yet another
standards body). [HTTP](https://tools.ietf.org/html/rfc2616) is standardized by
the [IETF](https://www.ietf.org/about/). The point is that the standards process
set up in the mid-nignties is still with us.

In the first years of the web, it was not so clear that browsers would remain
standard and that one browser might not end up “winning” and becoming another
proprietary software platform. There are multiple reasons this didn’t happen,
among them the egalitarian ethos of the computing community and the presence and
strength of the W3C. Another important reason was the networked nature of the
web, and therefore the desire of web developers to make sure their pages worked
correctly in most or all of the browsers (otherwise they would lose customers),
leading them to avoid any proprietary extensions. On the contrary---browsers
worked hard to carefully reproduce each other's undocumented behaviors---even
bugs---to make sure they continued supporting the whole web.

Despite fears that this might happen, there never really was a point where any
browser openly attempted to break away from the standard. Instead, intense
competition for market share was channeled into very fast innovation and an
ever-expanding set of APIs and capabilities for the web, which we nowadays refer
to as _the web platform,_ not just the “World Wide Web”. This recognizes the
fact that the web is no longer a document viewing mechanism, but has evolved
into a fully realized computing platform and ecosystem.[^web-os]

[^web-os]: There have even been operating systems built around the web! Examples
include [webOS](https://en.wikipedia.org/wiki/WebOS), which powered some Palm
smartphones, [Firefox OS](https://en.wikipedia.org/wiki/Firefox_OS) (that today
lives on in [KaiOS](https://en.wikipedia.org/wiki/KaiOS)-based phones), and
[ChromeOS](https://en.wikipedia.org/wiki/Chrome_OS), which is a desktop
operating system. All of these OSes are based on using the Web as the UI layer
for all applications, with some JavaScript-exposed APIs on top for system
integration.

Given these outcomes---multiple competing browsers and well-developed
standards---in retrospect it is clearly not so relevant to know which browser
“won” or “lost” each of the browser “wars”. In both cases _the web won_ and was
preserved and enhanced for the future.

Open source
===========

Another important and interesting outcome of the _second_ browser war was that
all mainstream browsers today (of which there are *many* more than
three[^examples-of-browsers-today]) are based on _three open-source web
rendering / JavaScript engines_: Chromium, Gecko and WebKit.[^javascript-repo]
Since Chromium and WebKit have a common ancestral codebase, while Gecko is an
open-source descendant of Netscape, all three date back to the 1990s---almost to
the beginning of the web.

[^examples-of-browsers-today]: Examples of Chromium-based browsers include
Chrome, Edge, Opera (which switched to Chromium from the
[Presto](https://en.wikipedia.org/wiki/Presto_(browser_engine)) engine in 2013),
Samsung Internet, Yandex Browser, UC Browser and Brave. In addition, there are
many "embedded" browsers, based on one or another of the three engines, for a
wide variety of automobiles, phones, TVs and other electronic devices.

[^javascript-repo]: The JavaScript engines are actually in different
repositories (as are various other sub-components that we won’t get into here),
and can and do exist outside of browsers as JavaScript virtual machines. One
important such application is the use of
[v8](https://en.wikipedia.org/wiki/V8_(JavaScript_engine)) to power
[node.js](https://en.wikipedia.org/wiki/Node.js). However, each of the three
rendering engines does have a corresponding JavaScript implementation, so
conflating the two is reasonable.

That this occurred is not an accident, and in fact tells us something quite
interesting about the most cost-effective way to implement a rendering engine
based on a commodity set of platform APIs. For example, it's common for a wide
variety of independent developers (ones not paid by the company nominally
controlling the browser) to contribute code and features. There are even
companies and individuals that specialize in implementing these features! And
every major browser being open source strengthens the standards process.

Putting it all together
=======================

In summary, the history went like this:

1. Basic research was performed into the ways to represent and explore
information.

2. Once the technology became mature enough, the web proper was proposed and
implemented.

3. The web became popular quite quickly, and many browsers appeared in order to
capitalize on the web's opportunity.

4. Standards organizations were introduced in order to negotiate between the
browsers and avoid proprietary control.

5. Browsers continued to compete and evolve at a rapid pace; that pace has
overall not slowed in the years since.

6. Browsers appeared on all devices and operating systems, including all
desktop and mobile devices & OSes, as well as embedded devices such as
televisions, watches and kiosks.

7. The web continued to grow in power and complexity, even going beyond the
original conception of a web browser.

8. Eventually, all web rendering engines became open source, as a recognition of
their being a shared effort larger than any single entity.

The web has come a long way! It'll be interesting to see where it goes in the
future.

But one thing seems clear: it isn't done yet.

Exercises
=========

*What comes next*: Based on what you learned about how the web came about and
took its current form, what trends do you predict for its future evolution?
For example, do you think it'll compete effectively against other non-web
technologies and platforms?

*What became of the original ideas?* The way the web works in practice is
significantly different than the memex; one key differences is that there is no
built-in way for the *user* of the web to add links between pages or notate
them. Why do you think this is? Can you think of other goals from the original
work that remain unrealized?
