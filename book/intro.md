---
title: Browsers and the Web
type: Introduction
next: history
prev: preface
...

I---this is Chris speaking---have known the web[^theweb] for all of my
adult life. The web for me is something of a technological companion,
and I’ve never been far from it in my studies or my work. Perhaps it's
been the same for you. And using the web means using a browser. I
hope, as you read this book, that you fall in love with web browsers,
just like I did.

The browser and me
==================

Since I first encountered the web and its predecessors,[^bbs] in the
early 90s, I've been fascinated by browsers and the concept of networked user
interfaces. When I [surfed][websurfing] the web, even in its earliest form, I
felt I was seeing the future of computing. In some ways, the web and I grew
together---for example, in 1994, the year the web went commercial, was the same
year I started college; while there I spent a fair amount of time surfing it,
and by the time I graduated in 1999, the browser had fueled the famous dot-com
speculation gold rush. Not only that, but he company for which I now work,
Google, is a child of the web and was founded during that time. 

[^theweb]: Broadly defined, the web is the interlinked network (“web”)
of [web pages](https://en.wikipedia.org/wiki/Web_page) on the
internet. If you've never made a web page, I recommend MDN's [Learn
Web Development][learn-web] series, especially the [Getting
Started][learn-basics] guide. This book will be easier to read if
you're familiar with the core technologies.
    
[learn-web]: https://developer.mozilla.org/en-US/docs/Learn
[learn-basics]: https://developer.mozilla.org/en-US/docs/Learn/Getting_started_with_the_web

[websurfing]: https://www.pcmag.com/encyclopedia/term/web-surfing

[^bbs]: For me, [BBS](https://en.wikipedia.org/wiki/Bulletin_board_system)
systems over a dial-up modem connection. A BBS, like a browser is a
window into dynamic content somewhere else on the internet.

In my freshman year at college, I attended a presentation by a RedHat salesman.
The presentation was of course aimed at selling RedHat Linux, probably calling
it the "operating system of the future" and speculating about the "year of the
Linux desktop". But when asked about challenges RedHat faced, the salesman
mentioned not Linux but _the web_: he said that someone "needs to make a good
browser for Linux."[^netscape-linux] Even back then, in the first
first years of the web, the browser was already a necessary component
of every computer.
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
both intentional and accidental. And everywhere you look, you see the evolution
and history of the web wrapped up in one codebase. It's fun and
endlessly interesting.

So that's how I fell in love with web browsers. Now let me tell you why you
will, too.

The web in history
==================

The web is a grand, crazy experiment. It's natural, nowadays, to watch videos,
read news, and connect with friends on the web. That can make the web seem
simple and obvious, finished, already built. But the web is neither simple nor
obvious (and is certainly not finished). It is the result of experiments and
research, reaching back to nearly the beginning of computing,[^precursors] about
how to help people connect and learn from each other.

[^precursors]: And the web _also_ needed rich computer displays, powerful
UI-building libraries, fast networks, and sufficient CPU power and information
storage capacity. As so often happens with technology, the web had many similar
predecessors, but only took its modern form once all the pieces came together.

In the early days, the internet was a world-wide network of computers, largely
at universities, labs, and major corporations, linked by physical cables and
communicating over application-specific protocols. The (very) early web mostly
built on this foundation. Web pages were files in a specific format stored on
specific computers. URLs for web pages named the computer and the file, and
early servers did little besides read files from a disk. The logical structure
of the web mirrored its physical structure.

A lot has changed. HTML is now usually dynamically assembled on the
fly[^server-side-rendering] and sent on demand to your browser. The pieces being
assembled are themselves filled with dynamic content---news, inbox contents, and
advertisements adjusted to your particular tastes. Even URLs no longer identify
a specific computer---content distribution networks route a URL to any of
thousands of computers all around the world. At a higher level, most web pages
are served not from someone's home computer[^self-hosted] but from a
major corporation's social media platform or cloud computing service.

[^server-side-rendering]: "Server-side rendering" is the process of assembling
HTML on the server when loading a web page. Server-side rendering can use web
tech like JavaScript and even [headless
browsers](https://en.wikipedia.org/wiki/Headless_browser). Yet one more place
browsers are taking over!

[^self-hosted]: People actually did this! And when their website became popular,
it often ran out of bandwidth or computing power and became inaccessible.

With all that's changed, some things have stayed the same, the core building
blocks that are the essence of the web:

* The user uses a _User Agent_, called a _browser_, to navigate the web.
* The web is a _network of information_
  linked by _hyperlinks_.
* Information is requested with the _HTTP network protocol_
  and structured with the _HTML document format_.
* Documents are identified by URLs, _not_ by their content,
  and may be dynamically generated.
* Web pages can link to auxiliary assets in different formats,
  including images, videos, CSS, and JavaScript.
* All these building blocks are open, standardized, and free to use or re-use.

As a philosophical matter, perhaps one or another of these principles is
secondary. One could try to distinguish between the networking and rendering
aspects of the web. One could abstract linking and networking from the
particular choice of protocol and data format. One could ask whether the browser
is necessary in theory, or argue that HTTP, URLs, and hyperlinking are the only
truly essential parts of the web.

Perhaps.[^perhaps] The web is, after all, an experiment; the core technologies
evolve and grow. But the web is not an accident; its original design reflects
truths not just about computing, but about how human beings can connect and
interact. The web not only survived but thrived during the virtualization of
hosting and content, specifically due to the elegance and effectiveness of
this original design.

[^perhaps]: It is indeed true that one or more of the implementation choices
could be replaced, and perhaps that will happen over time. For example,
JavaScript might eventually be replaced by another language or technology, HTTP
by some other protocol, or HTML by a successor. Yet the web will stay the web,
because any successor format is sure to support a *superset* of functionality,
and have the same fundamental structure.

The key thing to understand is this grand experiment is not over.
The essence of the web will stay, but by building web browsers you have the
chance to shape its future.

Real browser codebases
======================

So let me tell you what it's like to contribute to a browser. Some time during
my first few months of working on Chrome, I came across the code implementing
the[`<br>`][br-tag] tag---look at that, the good-old `<br>` tag, which I’ve
used many times to insert newlines into web pages! And the implementation turns
out to be barely any code at all, both in Chrome and in this book's simple
browser.

[br-tag]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/br

But Chrome as a whole---its features, speed, security, reliability---_wow_.
_Thousands_ of person-years went into it. There is a constant pressure to do
more---to add more features, to improve performance, to keep up with the "web
ecosystem"---for the thousands of businesses, millions of
developers,[^developers] and billions of users on the web.

[^developers]: I usually prefer “engineer”---hence the title of this book---but
“developer” or “web developer” is much more common on the web. One important
reason is that anyone can build a web page---not just trained software engineers
and computer scientists. “Web developer” also is more inclusive of additional,
critical roles like designers, authors, editors, and photographers. A web
developer is anyone who makes web pages, regardless of how.

Working on such a codebase can feel daunting. I often find lines of code last
touched 15 years ago by someone I've never met; or even now discover files and
classes that I never knew existed; or see lines of code that don’t look necessary,
yet turn out to be important. What does that 15-year-old code do? What
is the purpose of these new-to-me files? Is that code there for a reason?

Every browser has thousands of unfixed bugs, from the smallest of mistakes to
myriad mix ups and mismatches. Every browser must be endlessly tuned and
optimized to squeeze out that last bit of performance. Every browser requires
painstaking work to continuously refactor the code to reduce its complexity,
often through the careful[^browsers-abstraction-hard] introduction of
modularization and abstraction.

[^browsers-abstraction-hard]: Browsers are so performance-sensitive that, in
many places, merely the introduction of an abstraction---the function call or
branching overhead---can have an unacceptable performance cost!

What makes a browser different from most massive code bases is their _urgency_.
Browsers are nearly as old as any “legacy” codebase, but are _not_ legacy, not
abandoned or half-deprecated, not slated for replacement. On the contrary, they
are vital to the world’s economy. Browser engineers must therefore fix and
improve rather than abandon and replace. And since the character of the web
itself is highly decentralized, the use cases met by browsers are to a
significant extent _not determined_ by the companies “owning” or “controlling” a
particular browser. Other people---includingyou---can and do contribute ideas,
proposals, and implementations.

What's amazing is that, despite the scale and the pace and the complexity, there
is still plenty of room to contribute. Every browser today is open-source, which
opens up its implementation to the whole community of web developers. Browsers
evolve like giant R&D projects, where new ideas are constantly being proposed
and tested out. As you would expect, some features fail and some succeed. The
ones that succeed end up in specifications and are implemented by other
browsers. Every web browser is open to contributions---whether
fixing bugs or proposing new features or implementing promising optimizations.

And it's worth contributing, because working on web browsers is a lot of fun.

Browser code concepts
=====================

HTML & CSS are meant to be black boxes---declarative APIs---where one
specifies _what_ outcome to achieve, and the _browser itself_ is
responsible for figuring out the _how_ to achieve it. Web developers
don't, and mostly can't, draw their web page's pixels on their own.

That can make the browser magical or frustrating---depending on
whether it is doing the right thing! But that also makes a browser a pretty
unusual piece of software, with unique challenges, interesting algorithms, and
clever optimizations. Browsers are worth studying for the pure pleasure of it.

[^loss-of-control]: Loss of control is not necessarily specific to the web---much
of computing these days relies on mountains of other peoples’ code.

What makes that all work is the web browser's implementations of [inversion of
control][inversion], [constraint programming][constraints], and
[declarative programming][declarative]. The web _inverts control_, with an
intermediary---the browser---handling most of the rendering, and the web
developer specifying rendering parameters and content to this intermediary.
[^forms] Further, these parameters usually take the form of _constraints_
between relative sizes and positions of on-screen elements instead of
specifying their values directly;[^constraints] the browser solves the
constraints to find those values. The same idea applies for actions: web pages
mostly require _that_ actions take place without specifying _when_ they do.
This _declarative_ style means that from the point of view of a developer,
changes "apply immediately," but under the hood, the browser can be
[lazy] and delay applying the changes until they become externally visible,
either due to subsequent API calls or because the page has to be displayed to
the user.[^style-calculation]

[inversion]: https://en.wikipedia.org/wiki/Inversion_of_control
[constraints]: https://en.wikipedia.org/wiki/Constraint_programming
[declarative]: https://en.wikipedia.org/wiki/Declarative_programming
[lazy]: https://en.wikipedia.org/wiki/Lazy_evaluation

There are practical reasons for the unusual design of a browser. Yes, developers
lose some control and agency---when pixels are wrong, developers cannot fix them
directly.[^loss-of-control] But they gain the ability to deploy content on the
web without worrying about the details, to make that content instantly available
on almost every computing device in existence, and to keep it accessible in the
future, mostly avoiding software's inevitable obsolescence.

[^forms]: For example, in HTML there are many built-in [form control
elements][forms] that take care of the various ways the user of a web page can
provide input. The developer need only specify parameters such as button names,
sizing, and look-and-feel, or JavaScript extension points to handle form
submission to the server. The rest of the implementation is taken care of by the
browser.

[forms]: https://developer.mozilla.org/en-US/docs/Learn/Forms/Basic_native_form_controls

[^constraints]: Constraint programming is clearest during web page layout, where
font and window sizes, desired positions and sizes, and the relative arrangement
of widgets is rarely specified directly.

[^style-calculation]: For example, when exactly does the browser
compute HTML element's styles? Any change to the styles is visible to
all subsequent API calls, so in that sense it applies "immediately."
But it is better for the browser to delay style re-calculation,
avoiding redundant work if styles change twice in quick succession.
Maximally exploiting the opportunities afforded by declarative
programming makes real-world browsers very complex.

To me, browsers are where algorithms _come to life_. A browser contains a
rendering engine more complex and powerful than any computer game; a full
networking stack; clever data structures and parallel programming techniques; a
virtual machine, an interpreted language, and a JIT; a world-class security
sandbox; and a uniquely dynamic system for storing data.

And the truth is---you use the browser all the time, maybe for reading this
book! That makes the algorithms more approachable in a browser than almost
anywhere else, because the web is already familiar.

The role of the browser
=======================

The web is at the center of modern computing.
Every year the web expands its reach to more and more of what we do with
computers. It now goes far beyond its original use for document-based
information sharing: many people now spend their entire day in a browser, not
using a single other application! Moreover, desktop applications are now often
built and delivered as _web apps_: web pages loaded by a browser but used like
installed applications.[^pwa] Even on mobile devices, apps often embed a browser
to render parts of the application UI.[^hybrid] Perhaps in the future both
desktop and mobile devices will largely be a container for web apps. Already,
browsers are a critical and indispensable part of computing.

[^pwa]: Related to the notion of a web app is a Progressive Web App, which is a
web app that becomes indistinguishable from a native app through [progressive
enhancement][prog-enhance-def].

[^hybrid]: The fraction of such "hybrid" apps that are shown via a "web view" is
    likely increasing over time. In some markets like China, "super-apps" act
    like a mobile web browser for web-view-based games and widgets.
    
So given this centrality, it's worth knowing how the web works. And in
particular, how the principles I listed earlier are put into practice by the
User Agent, i.e. *the web browser*.[^useragent] It's the browser that makes
these concepts real. The browser is the User Agent, but also the _mediator_ of
the web's interactions and the
_enforcer_ of its rules. The browser is the _implementer_ of the web: Its
sandbox keeps web browsing safe; its algorithms implement the declarative
document model; its UI navigates links. Web pages load fast and react smoothly
only when the browser is hyper-efficient.

[^useragent]: The User Agent concept views a computer, or software within the
    computer, as a trusted assistant and advocate of the human user.

Browsers and you
================

This book explains how to build a simple browser, one that can---despite its
simplicity---display interesting-looking web pages and support many interesting
behaviors. As you’ll see, it’s surprisingly easy, and it
demonstrates all the core concepts you need to understand a real-world browser.
The browser stops being a mystery when it becomes code.

[prog-enhance-def]:
https://en.wikipedia.org/wiki/Progressive_enhancement

The intention is for you to build your own browser as you work through the early
chapters. Once it is up and running, there are endless opportunities to improve
performance or add features. some of which are suggested as exercises. Many of
these exercises are features implemented in real browsers, and I encourage you
to try them---adding features is one of the best parts of browser development!

The book then moves on to details and advanced features that flesh out the
architecture of a real browser’s rendering engine, based on my experiences with
Chrome. After finishing the book, you should be able to dig into the source code
of Chromium, Gecko, or WebKit, and understand it without too much trouble.

I hope the book lets you appreciate a browser's depth, complexity, and power. I
hope the book passes along its beauty---its clever algorithms and data
structures, its co-evolution with the culture and history of computing, its
centrality in our world. But most of all, I hope the book lets you see in
yourself someone building the browser of the future.
