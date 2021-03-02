---
title: Browsers and the Web
type: Introduction
next: http
prev: preliminaries
...

I[^chris] have known the web[^theweb] for all of my adult life. Ever since I
first encountered the web, and its predecessors,[^bbs] in the early 90s, I was
fascinated by browsers and the concept of networked user interfaces. When I
[surfed][websurfing] the web, even in its earliest form, I felt I was seeing the
future of computing. In some ways, the web and I grew together---for example, in
1994, the year the web went commercial, was the same year I started college;
while there I spent a fair amount of time surfing it, and by the time I
graduated in 1999, the browser had fueled the famous dot-com speculation gold
rush. The company for which I now work, Google, is a child of the web and was
founded during that time. The web for me is something of a technological
companion, and I’ve never been far from it in my studies or work.

[^chris]: This is Chris speaking!

[^theweb]: Broadly defined, the web is the interlinked network (“web”)
of [web pages](https://en.wikipedia.org/wiki/Web_page) on the
Internet. If you've never made a web page, I recommend MDN's [Learn
Web Development][learn-web] series, especially the [Getting
Started][learn-basics] guide. This book will be easier to read if
you're familiar with the core technologies.
    
[learn-web]: https://developer.mozilla.org/en-US/docs/Learn
[learn-basics]: https://developer.mozilla.org/en-US/docs/Learn/Getting_started_with_the_web

[websurfing]: https://www.pcmag.com/encyclopedia/term/web-surfing

[^bbs]: For me, [BBS](https://en.wikipedia.org/wiki/Bulletin_board_system)
systems over a dial-up modem connection. A BBS is not all that different from a
browser if you think of it as a window into dynamic content created somewhere
else on the Internet.

The browser and me
==================

In my freshman year at college, I attended a presentation by a RedHat salesman.
The presentation was of course aimed at selling RedHat Linux, probably calling
it the "operating system of the future" and speculating about the "year of the
Linux desktop". But when asked about challenges RedHat faced, the salesman
mentioned not Linux but _the web_: he said that someone "needs to make a good
browser for Linux."[^netscape-linux] Even back then, in the very first year or
so of the web, the browser was already a necessary component of every computer.
He even threw out a challenge: "how hard could it be to build a better browser?"
Indeed, how hard could it be? What makes it so hard? That question stuck with me
for a long time.[^meantime-linux]

[^netscape-linux]: Netscape Navigator was available for Linux at that time, but
it wasn’t viewed as especially fast or featureful compared to its implementation
on other operating systems.

[^meantime-linux]: Meanwhile, the "better Linux browser than Netscape" took a
long time to appear....

How hard indeed! After seven years in the trenches working on Chrome, I now know
the answer to his question: building a browser is both easy and incredibly hard,
both intentional and accidental, both planned and organic, both simple and
unimaginably complex. And everywhere you look, you see the evolution and history of
the web wrapped up in one codebase.

That's what this book is about. It's a fascinating and fun journey.
But first let's dig deeper into how the web works, where the web came
from, and the role browsers play.

The web in history
==================

It might seem natural to use a web browser to browse the Web over the Internet,
and many people experienced the Internet of the 1990s onward like this. That can
make the Web seem already-built, simple and obvious, with nothing left but to
browse it. But the Web is neither simple nor obvious. It is the result of
experiments and research reaching back to nearly the beginning of computing. And
the web _also_ needed rich computer displays, powerful UI-building libraries,
fast networks, and sufficient CPU power and information storage capacity. As so
often happens with technology, the web has many similar predecessors, but only
took its modern form once all the pieces came together.

In the early days, the Internet was a world wide network of computers, largely
at universities, labs, and major corporations, linked by physical cables and
communicating over application-specific protocols. The early web built on this
foundation. Web pages were files in a specific format stored on specific
computers, and web browsers used a custom protocol to request them. URLs for web
pages named the computer and the file, and early servers did little besides read
files from a disk. The logical structure of the web mirrored its physical
structure.

A lot has changed. While you can still write HTML files on disk, HTML is now
usually dynamically assembled on the fly[^server-side-rendering] and sent
on-demand to your browser. The pieces being assembled are themselves filled with
dynamic content---news, inbox contents, and advertisements adjusted to your
particular tastes. Even URLs no longer identify a specific computer---content
distribution networks route a URL to any of thousands of computers all around
the world. At a higher level, most web page are served not from someone's home
computer[^self-hosted] but from a social media platform or cloud computing
service.

[^server-side-rendering]: "Server-side rendering" is the process of assembling
HTML on the server when loading a web page. Server-side rendering often uses web
tech like JavaScript, and even a [headless
browser](https://en.wikipedia.org/wiki/Headless_browser). Yet one more place
browsers are taking over!

[^self-hosted]: People actually did this! And when their website became
popular, it often ran out of bandwidth or computing power and became
inaccessible.

With all that's changed, some things have stayed the same, the core building
blocks that are the essence of the web:

* The web is a _network of information_
  linked by _hyperlinks_.
* Information is contained in documents
  requested with the _HTTP network protocol_
  and structured with the _HTML information format_.
* Documents are identified by URLs, _not_ by their content, and may be dynamic.
* Web pages can link to auxiliary assets in different formats,
  including images, videos, CSS, and JavaScript.
* The user uses a _User Agent_, called a _browser_, to navigate the web.
* All these building blocks are open, standardized, and free to use or re-use.

As a philosophical matter, perhaps one or another of these principles is
secondary. One could try to distinguish between the networking and rendering
aspects of the web. One could abstract linking and networking from the
particular choice of protocol and data format. One could ask whether the browser
is necessary in theory, or argue that HTTP, URLs and hyperlinking are the only
truly essential parts of the Web.

Perhaps.[^perhaps] In practice, the web was born when these principles came
together, not before. They are not accidental; they are the original design of
the web. And all of them---HTTP, HTML, browsers, URLs---evolve and grow, and
will continue to do so. The web not only survived but thrived during the
virtualization of hosting and content, all thanks to the elegance and
effectiveness of this original design. And [ongoing change](change.md) will lead
to more changes and evolution in the future.

[^perhaps]: It is indeed true that one or more of the implementation choices
could be replaced, and perhaps that will happen over time. For example,
JavaScript might eventually be replaced by another language or technology, HTTP
by some other protocol, or HTML by its successor. Certainly all of these
technologies have been through many versions, but the Web has stayed the Web.

How browsers evolve
===================

Some time during my first few months of working on Chrome, I came across the
code implementing the [`<br>`][br-tag] tag---look at that, the good-old `<br>`
tag that I’ve used many times to insert newlines into web pages! And the
implementation turns out to be barely any code at all, both in Chrome and in
this book's simple browser.

[br-tag]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/br

But a browser with the features, speed, security, and reliability of today’s top
browsers---_wow_. _Thousands_ of person-years of effort have gone into the
browser you use today. And keeping a browser competitive is a lot of work as
well. Not only is there an inherent cost to maintaining large codebases, there
is also constant pressure to do more---to add more features, to improve
performance, to keep up with the "web ecosystem"---for the thousands of
businesses, millions of developers, and billions of users on the web.

Every browser has thousands of unfixed bugs, from the smallest of mistakes to
myriad mix ups and mismatches. Every browser has a complicated set of
optimizations to squeeze out that last bit of performance. Every browser
requires painstaking work to continuously refactor the code to reduce its
complexity, often through the careful[^browsers-abstraction-hard] introduction
of modularization and abstraction.

[^browsers-abstraction-hard]: Browsers are so performance-sensitive that, in
many places, merely the introduction of an abstraction---the function call or
branching overhead---has an unacceptable performance cost.

Working on such a codebase is often daunting. For one thing, there is the
weighty history of each browser. It’s not uncommon to find lines of code last
touched 15 years ago by someone who you’ve never met; or even after years of
working discover files and code that you didn’t even know existed; or see lines
of code that don’t look necessary, yet seem to do something important. How do I
learn what that 15-year-old code does? Does that code I just discovered matter
at all? Can I delete those lines of code, or are they there for a reason?

These questions are common to all complex codebases. But what makes a browser
different is that there is often an _urgency to fix_ them. Browsers are nearly
as old as any “legacy” codebase, but are _not_ legacy, not abandoned or
half-deprecated, not slated for replacement. On the contrary, they are vital to
the world’s economy. And since the character of the web itself is highly
decentralized, the use cases met by browsers are to a significant extent _not
determined_ by the companies “owning” or “controlling” a particular browser.
Other people, for example web developers, contribute ideas and proposals that
end up implemented inside browsers. Browser engineers must therefore fix and
improve rather than abandon and replace.

Every rendering engine today is open-source, which share the burden of
maintenance and feature development across that larger community of web
developers. So browsers evolve like giant R&D projects, where new ideas are
constantly being proposed and tested out. Like any R&D project, browsers have an
iterative and incremental planning and shipping process. And just as you would
expect, some features fail and some succeed. The ones that succeed end up in
specifications and are implemented by other browsers.

Explaining the black box
========================

HTML, CSS, HTTP, hyperlinks, and JavaScript---the core of the web---are
approachable enough, and if you've made a web page before you've seen that
programming ability is not required. That's because HTML & CSS are meant to be
black boxes---declarative APIs---where one specifies _what_ outcome to achieve,
and the _browser itself_ is responsible for figuring out the _how_ to achieve
it. Web developers don't, and mostly can't, draw their web page's pixels on
their own.

There are philosophical and practical reasons for this unusual design. Yes,
developers lose some control and agency---when those pixels are wrong,
developers cannot fix them directly.[^loss-of-control] But they gain the ability
to deploy content on the web without worrying about the details, to make that
content instantly available on almost every computing device in existence, and
to keep it accessible in the future, mostly avoiding the inevitable obsolescence
of most software.

[^loss-of-control]: Loss of control is not necessarily specific to the web---much
of computing these days relies on mountains of other peoples’ code.

As a black box, the browser is either magical or frustrating (depending on
whether it is working correctly or not!). Few people---even among professional
software developers[^software-developers]---know much about how a browser
renders web pages. But it turns out that a browser is a pretty unusual piece of
software, with unique challenges, interesting algorithms, and clever
optimizations invented just for this domain. That makes browsers worth studying
for the pure pleasure of it---even leaving aside their importance!

[^software-developers]: I usually prefer “engineer”---hence the title of this
book---but “developer” or “web developer” is much more common on the web. One
important reason is that anyone can build a web page---not just trained software
engineers and computer scientists. “Web developer” also is more inclusive of
additional, critical roles like designers, authors, editors, and photographers.
A web developer is anyone who makes web pages, regardless of how.

Inside the black box lie the web browser's implementations of [inversion of
control][inversion], [constraint programming][constraints], and [declarative
programming][declarative]. The web _inverts control_, with an intermediary---the
browser---handling most of the rendering, and the web developer specifying
parameters and content to this intermediary.[^forms] Further, these parameters
usually take the form of _constraints_ over relative sizes and positions instead
of specifying their values directly;[^constraints] the browser solves the
constraints to find those values. The same idea applies for actions: web pages
mostly require _that_ actions take place without specifying _when_ they do. This
_declarative_ style means that from the point of view of a developer, changes
"apply immediately," but under the hood, the browser can be [lazy][lazy] and
delay applying the changes until they become externally visible, either due to
subsequent API calls or because the page has to be displayed to the
user.[^style-calculation]

[inversion]: https://en.wikipedia.org/wiki/Inversion_of_control
[constraints]: https://en.wikipedia.org/wiki/Constraint_programming.
[declarative]: https://en.wikipedia.org/wiki/Declarative_programming
[lazy]: https://en.wikipedia.org/wiki/Lazy_evaluation

[^forms]: For example, in HTML there are many built-in [form control
elements][forms] that take care of the various ways the user of a web page can
provide input. The developer need only specify parameters such as button names,
sizing, and look-and-feel, or JavaScript extension points to handle form
submission to the server. The rest of the implementation is taken care of by the
browser.

[forms]: https://developer.mozilla.org/en-US/docs/Learn/Forms/Basic_native_form_controls

[^constraints]: Constraint programming is clearest during web page layout, where
font and window sizes, desired positions and sizes, and the relative arrangement
of widgets is rarely specified directly. A fun question to consider: what does
the browser "optimize for" when computing a layout?

[^style-calculation]: For example, when exactly does the browser compute which
CSS styles apply to which HTML elements, after a web page changes
those styles? The change is visible to all subsequent API calls, so in that
sense it applies "immediately." But it is better for the browser to delay style
re-calculation, avoiding redundant work if styles change twice in quick
succession. Maximally exploiting the opportunities afforded by declarative
programming makes real-world browsers very complex.

Understanding how the browser works yields true insights into computing. To me,
browsers are where algorithms _come to life_. A browser contains a rendering
engine more complex and powerful than any computer game; a full networking
stack; clever data structures and parallel programming techniques; a virtual
machine, an interpreted language, and a JIT; a world-class security sandbox; and
a uniquely dynamic system for storing data.


The role of the browser
=======================

The browser, and the web more broadly, is a marvel. It now goes far beyond its
original use for document-based information sharing, and every year it expands
its reach to more and more of what we do with computers. Many people now spend
their entire day in a browser, not using a single other application!

Moreover, desktop applications are now often built and delivered as _web apps_:
web pages loaded by a browser but used like installed applications.[^pwa] Even
on mobile devices, apps often embed a browser to render parts of the application
UI.[^hybrid] Perhaps in the future both desktop and mobile devices will largely
be a container for web apps. Already, browsers are a critical and indispensable
part of computing.

[^pwa]: Related to the notion of a web app is a Progressive Web App, which is a
web app that becomes indistinguishable from a native app through [progressive
enhancement][prog-enhance-def].

[^hybrid]: The fraction of such "hybrid" apps that are shown via a "web view" is
    likely increasing over time. In some markets like China, "super-apps" act
    like a mobile web browser for web-view-based games and widgets.

The basis of browsers is the web. And the web itself is built on a few simple,
yet revolutionary, concepts; concepts that that together present a vision of the
future of software and information. Among them are open, decentralized and safe
computing; a declarative document model for describing UIs; hyperlinks; and the
User Agent.[^useragent] 

[^useragent]: The User Agent concept views a computer, or software within the
    computer, as a trusted assistant and advocate of the human user.

From our point of view, the browser makes the web real. All these concepts and
principles therefore form the core architecture of the browser itself. The
browser is the User Agent, but also the _mediator_ of web interactions and
_enforcer_ of the rules. It ensures safety and fairness and represents you to
web pages. Not only that, the browser is the _implementer_ of all of the ways
information is explored. Its sandbox keeps web browsing safe; its algorithms
implement the declarative UI; its UI navigates links. For web pages to load fast
and react smoothly, the browser must be hyper-efficient.

Such lofty goals! How does the browser deliver on them? The best way to
understand that question is to build a web browser.

Browsers and you
================

This book explains how to build a simple web rendering engine plus browser
shell. As you’ll see, it’s surprisingly easy to write a very simple browser, one
that can---despite its simplicity---display interesting-looking web pages and
support many interesting behaviors.[^prog-enhance] Moreover, this simple browser
will demonstrate all the core concepts you need to understand to predict the
behavior of a real-world browser. You'll see what is easy and what is hard in
these engines; which algorithms are simple, and which are tricky; what makes a
browser fast, and what makes it slow.

[^prog-enhance]: You might relate this to the history of the web and the idea of
[progressive enhancement][prog-enhance-def].

[prog-enhance-def]:
https://en.wikipedia.org/wiki/Progressive_enhancement

The intention is for you to build your own browser as you work through the early
chapters. Once your browser is up and running, there are endless opportunities
to improve performance or add features. Many of the exercises at the ends of the
chapters are feature implemented in real browsers. We encourage you to try
them---adding features is one of the best parts of browser development! It is
lot of fun (and very satisfying) to compare your browser with a real one, or to
see how many websites you can successfully render.

This simple browser demonstrates the (intentionally!) easy-to-implement core of
the web architecture. The book then moves on to details about advanced features
and the architecture of a real browser’s rendering engine, based on my
experiences with Chrome. After finishing the book, you should be able to dig
into the source code for a real browser’s rendering engine and understand it
without too much trouble.

I hope the book lets you appreciate a browser's depth, complexity, and power. I
hope the book passes along its beauty---its clever algorithms and data
structures, its co-evolution with the culture and history of computing, its
centrality in our world. But most of all, I hope the book lets you see in
yourself someone building the browser of the future. The future doesn't just
arrive; it’s up to you to invent and discover and create it!
