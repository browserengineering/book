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

<figure>
  <img src="im/memex.jpg" alt="A photograph of the first few lines of As You May Think">
  <figcaption>
    (<a href="https://www.flickr.com/people/79255326@N00">Dunkoman</a>
    from <a href="https://commons.wikimedia.org/wiki/File:The_Memex_(3002477109).jpg">Wikipedia</a>,
    <a href="https://creativecommons.org/licenses/by/2.0/legalcode" rel="license">CC BY 2.0</a>)
  </figcaption>
</figure>

The earliest exploration of how computers might revolutionize information is a
1945 essay by Vannevar Bush entitled [As We May
Think](https://en.wikipedia.org/wiki/As_We_May_Think). This essay envisioned a
machine called a [Memex](https://en.wikipedia.org/wiki/Memex) that helps (think:
User Agent) an individual human see and explore all the information in the
world. It was described in terms of the microfilm screen technology of the time,
but its purpose and concept has some clear similarities to the web as we know it
today, even if the user interface and technology details differ.

The web is at its core organized around the Memex-like goal of _representing and
displaying information_, providing a way for humans to effectively learn and
explore. The collective knowledge and wisdom of the species long ago exceeded
the capacity of a single mind, organization, library, country, culture, group or
language. However, while we as humans cannot possibly know even a tiny fraction
of what it is possible to know, we can use technology to learn more efficiently
than before, and, *in particular*, to quickly access information we need to
learn, remember or recall. Consider this imagined research session described by
Vannevar Bush--one that is remarkably similar to how we sometimes use the web:

> The owner of the memex, let us say, is interested in the origin and properties
> of the bow and arrow. [...] He has dozens of possibly pertinent books and
> articles in his memex. First he runs through an encyclopedia, finds an
> interesting but sketchy article, leaves it projected. Next, in a history, he
> finds another pertinent item, and ties the two together. Thus he goes,
> building a trail of many items.

Computers, and the internet, allow us to _process and store_ the information we
want. But it is _the web_ that helps us _organize and find_ that information,
that knowledge, making it useful.[^google-mission]

[^google-mission]: The Google search engine's well-known
[mission](https://about.google/) statement to “organize the world’s information
and make it universally accessible and useful” is almost exactly the same.
This is not a coincidence---the search engine concept is inherently
connected to the web, and was inspired by the web's design and antecedents.

_As We May Think_ highlighted two features of the memex: information record
lookup, and associations between related records. In fact, the essay emphasizes
the importance of the latter---we learn by making previously unknown
*connections between known things*:

> When data of any sort are placed in storage, they are filed alphabetically or
> numerically. [...] The human mind does not work that way. It operates by
> association.

By "association", Bush meant a trail of thought leading from one record
to the next via a human-curated link. He imagined not just a universal
library, but a universal way to record the results of what we learn. That is
what the web can do today.

The web emerges
===============

The concept of [hypertext][hypertext] documents linked by
[hyperlinks][hyperlink] was invented in 1964-65 by [Project Xanadu][xanadu], led
by Ted Nelson.[^literary-criticism] Hypertext is text that is marked up with
hyperlinks to other text. A successor called the [Hypertext Editing System] was
the first to introduce the back button, which all browsers now have. (Since the
system just had text, the "button" was itself text.)

[Hypertext Editing System]: https://en.wikipedia.org/wiki/Hypertext_Editing_System

[hyperlink]: https://en.wikipedia.org/wiki/Hyperlink#History

[^literary-criticism]: He was inspired by the long tradition of citation and
criticism in academic and literary communities. The Project Xanadu research
papers were heavily motivated by this use case.

Hypertext is text that is marked up with hyperlinks to other text. Sounds
familiar? A web page is hypertext, and links between web pages are hyperlinks.
The format for writing web pages is HTML, which is short for HyperText Markup
Language. The protocol for loading web pages is HTTP, which is short for
HyperText Transport Protocol.

<figure>
	<img src="im/hes.jpg" alt="A computer operator using a hypertext editing system in 1969">
    <figcaption>Hypertext Editing System <br/> (Gregory Lloyd from <a href="https://commons.wikimedia.org/wiki/File:HypertextEditingSystemConsoleBrownUniv1969.jpg">Wikipedia</a>, <a href="https://creativecommons.org/licenses/by/2.0/legalcode" rel="license">CC BY 2.0</a>)</figcaption>
</figure>

Independently of Project Xanadu, the first hyperlink system appeared for
scrolling within a single document; it was later generalized to linking between
multiple documents. And just like those original systems, the web has linking
within documents as well as between them. For example, the url
"http://example.com/doc.html#link" refers to a document called "`doc.html`",
specifically to the element with the name "`link`" within it. Clicking on a link
to that URL will load `doc.html` and scroll to the `link` element.

This work also formed and inspired one of the key parts of Douglas Engelbart's
[mother of all demos](https://en.wikipedia.org/wiki/The_Mother_of_All_Demos),
perhaps the most influential technology demonstration in the history of
computing. That demo not only showcased the key concepts of the web, but also
introduced the computer mouse and graphical user interface, both of which are of
course central components of a browser UI.[^even-more]

<figure>
	<img src="im/engelbart.jpg" alt="A picture of Doug Engelbart presenting the mother of all demos">
	<figcaption>The mother of all demos, 1968 <br/> (SRI International, via the <a
	href="https://www.dougengelbart.org/content/view/374/464/">Doug Engelbart Institute</a>)</figcaption>
</figure>

[^even-more]: That demo went beyond even this! There are some parts of it that
have not yet been realized in any computer system. I highly recommend watching
the demo yourself.

[hypertext]: https://en.wikipedia.org/wiki/Hypertext

[xanadu]: https://en.wikipedia.org/wiki/Project_Xanadu

There is of course a very direct connection between this research and the
document-URL-hyperlink setup of the web, which built on the hypertext idea and
applied it in practice. The [HyperTIES](http://www.cs.umd.edu/hcil/hyperties/)
system, for example, had highlighted hyperlinks and was used to develop the
world’s first electronically published academic journal, the 1988 issue of the
[Communications of the ACM](https://cacm.acm.org/). Tim Berners-Lee cites that
1988 issue as inspiration for the World Wide Web,[^world-wide-web-terminology]
in which he joined the link concept with the availability of the internet, thus
realizing many of the original goals of all this work from previous
decades.[^realize-web-decades]

The word "hyperlink" may have been coined in 1987, in connection with the
[HyperCard] system on Apple computers. This system was also one of the first, or
perhaps the first, to introduce the concept of augmenting hypertext with scripts
that handle user events like clicks and perform actions that enhance the
UI--just like JavaScript on a web page! It also had graphical UI elements, not
just text, unlike most predecessors.

[HyperCard]: https://en.wikipedia.org/wiki/HyperCard

[^world-wide-web-terminology]: Nowadays the World Wide Web is called just “the
web”, or “the web ecosystem”---ecosystem being another way to capture the same
concept as “World Wide”. The original wording lives on in the "www" in many
website domain names.

[^realize-web-decades]: Just as the web itself is a realization of previous
ambitions and dreams, today we strive to realize the vision laid out by the web.
(No, it's not done yet!)

In 1989-1990, the first web browser (named “WorldWideWeb”) and web server (named
“`httpd`”, for “HTTP Daemon” according to UNIX naming conventions) were born,
written by Tim Berners-Lee. Interestingly, while that browser’s capabilities
were in some ways inferior to the browser you will implement in this
book,[^no-css] in other ways they go beyond the capabilities available even in
modern browsers.[^more-less-powerful] On December 20, 1990 the [first web
page](http://info.cern.ch/hypertext/WWW/TheProject.html) was created. The
browser we will implement in this book is easily able to render this web page,
even today.[^original-aesthetics] In 1991, Berners-Lee advertised his browser
and the concept on the [alt.hypertext Usenet
group](https://www.w3.org/People/Berners-Lee/1991/08/art-6484.txt).

<figure>
	<img src="im/worldwideweb.gif" alt="A screenshot of the WorldWideWeb browser">
	<caption>WorldWideWeb, the first web browser <br/> (<a
	href="https://dl.acm.org/doi/10.1145/179606.179671">Communications of the
	ACM</a>, August 1994)</caption>
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
number of other key factors that led to the World Wide Web becoming the web we
know today. One key factor was its decentralized nature, which he describes as
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

<div class="grid" style="display: grid; grid-template-columns: repeat(2, 1fr);">
<figure>
<img src="im/mosaic.png" alt="A screenshot of the Mosaic browser">
<figcaption>Mosaic (<a href="https://commons.wikimedia.org/wiki/File:NCSA_Mosaic_Browser_Screenshot.png">Wikipedia</a>, <a href="https://creativecommons.org/publicdomain/zero/1.0/legalcode" rel="license">CC0 1.0</a>)</figcaption>
</figure>
<figure>
<img src="im/violawww.png" alt="A screenshot of the ViolaWWW browser">
<figcaption>
ViolaWWW (<a href="https://web.archive.org/web/20200706084621/http://viola.org/viola/book/preface.html">Viola in a Nutshell</a>)
</figcaption>
</figure>
<figure>
<img src="im/netscape.png" alt="A screenshot of the Netscape browser">
<figcaption>Netscape Navigator (<a href="https://en.wikipedia.org/wiki/File:Navigator_1-22.png#filehistory">Wikipedia</a>)</figcaption>
</figure>
<figure>
<img src="im/ie1.png" alt="A screenshot of the IE 1.0 browser">
<figcaption>Microsoft Internet Explorer 1.0
<br/>
(<a href="https://en.wikipedia.org/wiki/File:Internet_Explorer_1.0.png">Wikipedia</a>,
used <a href="https://www.microsoft.com/en-us/legal/copyright/permissions">with permission from Microsoft</a>)</figcaption>
</figure>
</div>

The era of the ["first browser
war"](https://en.wikipedia.org/wiki/Browser_wars#First_Browser_War_(1995%E2%80%932001))
ensued: a competition between Netscape Navigator and [Internet Explorer]. There
were also other browsers with smaller market shares; one notable example is
[Opera](https://en.wikipedia.org/wiki/Opera_(web_browser)). The
[WebKit](https://en.wikipedia.org/wiki/WebKit) project began in 1999;
[Safari](https://en.wikipedia.org/wiki/Safari_(web_browser)) and
[Chromium](https://www.chromium.org/)-based browsers, such as Chrome and newer
versions of [Edge](https://en.wikipedia.org/wiki/Microsoft_Edge), descend from
this codebase. Likewise, the
[Gecko](https://en.wikipedia.org/wiki/Gecko_(software)) rendering engine was
originally developed by Netscape starting in 1997; the
[Firefox](https://en.wikipedia.org/wiki/Firefox) browser is descended from this
codebase. During the first browser war, nearly all of the core features of this
book's simple browser were added, including CSS, DOM, and JavaScript.

[Internet Explorer]: https://en.wikipedia.org/wiki/Internet_Explorer

The "second browser war", which according to Wikipedia was
[2004-2017](https://en.wikipedia.org/wiki/Browser_wars#Second_Browser_War_(2004%E2%80%932017)),
was fought between a variety of browsers, in particular Internet Explorer,
Firefox, Safari and Chrome. Chrome split off its rendering engine subsystem into
its own code base called
[Blink](https://en.wikipedia.org/wiki/Blink_(browser_engine)) in 2013. The
second browser war saw the development of many features of the modern web,
including widespread use of AJAX requests, HTML5 features like
`<canvas>`, and a huge explosion in third-party JavaScript libraries
and frameworks.

[^commercial-browser]: By commercial I mean built by a for-profit entity.
Netscape's early versions were also not free software---you had to buy them from
a store. They cost about $50.

Web standards
=============

In parallel with these developments was another, equally important, one---the
standardization of web APIs. In October 1994, the [World Wide Web
Consortium](https://www.w3.org/Consortium/facts) (W3C) was founded to provide
oversight and standards for web features. Prior to this point, browsers would
often introduce new HTML elements or APIs, and competing browsers would have to
copy them. With a standards organization, those elements and APIs could
subsequently be agreed upon and documented in specifications. (These days, an
initial discussion, design and specification precedes any new feature.) Later
on, the HTML specification ended up moving to a different standards body called
the [WHATWG](https://whatwg.org/), but [CSS](https://drafts.csswg.org/) and
other features are still standardized at the W3C. JavaScript is standardized at
[TC39](https://tc39.es/) (“Technical Committee 39” at
[ECMA](https://www.ecma-international.org/about-ecma/history/), yet another
standards body). [HTTP](https://tools.ietf.org/html/rfc2616) is standardized by
the [IETF](https://www.ietf.org/about/). The point is that the standards process
set up in the mid-nineties is still with us.

In the first years of the web, it was not so clear that browsers would remain
standard and that one browser might not end up “winning” and becoming another
proprietary software platform. There are multiple reasons this didn’t happen,
among them the egalitarian ethos of the computing community and the presence and
strength of the W3C. Another important reason was the networked nature of the
web, and therefore the necessity for web developers to make sure their pages
worked correctly in most or all of the browsers (otherwise they would lose
customers), leading them to avoid proprietary extensions. On the
contrary---browsers worked hard to carefully reproduce each other's undocumented
behaviors---even bugs---to make sure they continued supporting the whole web.

There never really was a point where any browser openly attempted to break away
from the standard, despite fears that that might happen.[^dhtml] Instead, intense
competition for market share was channeled into very fast innovation and an
ever-expanding set of APIs and capabilities for the web, which we nowadays refer
to as _the web platform,_ not just the “World Wide Web”. This recognizes the
fact that the web is no longer a document viewing mechanism, but has evolved
into a fully realized computing platform and ecosystem.[^web-os]

[^dhtml]: Perhaps the closest the web came to fragmenting was with the late-90s
introduction of features for
[DHTML](https://en.wikipedia.org/wiki/Dynamic_HTML)---early versions of the Document
Object Model you'll learn about in this book. Netscape and Internet Explorer at
first had incompatible implementations of these features, and it took years,
development of a common specification, and significant pressure campaigns on
the browsers before standardization was achieved. You can read about this story in
much more depth [here](https://css-tricks.com/chapter-7-standards/).

[^web-os]: There have even been operating systems built around the web! Examples
include [webOS](https://en.wikipedia.org/wiki/WebOS), which powered some Palm
smartphones, [Firefox OS](https://en.wikipedia.org/wiki/Firefox_OS) (that today
lives on in [KaiOS](https://en.wikipedia.org/wiki/KaiOS)-based phones), and
[ChromeOS](https://en.wikipedia.org/wiki/Chrome_OS), which is a desktop
operating system. All of these OSes are based on using the Web as the UI layer
for all applications, with some JavaScript-exposed APIs on top for system
integration.

Given the outcomes---multiple competing browsers and well-developed
standards---it is in retrospect not that relevant which browser “won” or “lost”
each of the browser “wars”. In both cases _the web won_ and was preserved and
enhanced for the future.

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
and can and do get used outside the browser as JavaScript virtual machines. One
important application is the use of
[v8](https://en.wikipedia.org/wiki/V8_(JavaScript_engine)) to power
[node.js](https://en.wikipedia.org/wiki/Node.js). However, each of the three
rendering engines does have a corresponding JavaScript implementation, so
conflating the two is reasonable.

This is not an accident, and in fact tells us something quite interesting about
the most cost-effective way to implement a rendering engine based on a commodity
set of platform APIs. For example, it's common for a wide variety of independent
developers (ones not paid by the company nominally controlling the browser) to
contribute code and features. There are even companies and individuals that
specialize in implementing these features! And every major browser being open
source feeds back into the standards process, reinforcing the web's
decentralized nature.

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
significantly different than the memex; one key difference is that there is no
built-in way for the *user* of the web to add links between pages or notate
them. Why do you think this is? Can you think of other goals from the original
work that remain unrealized?
