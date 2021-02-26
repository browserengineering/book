---
title: Browsers and the Web
type: Intro
next: http
prev: preliminaries
...

The web browser, and the web[^theweb] more broadly, is a marvel. Every
year it expands its reach to more and more of what we do with
computers. It now goes far beyond its original use for document-based
information sharing; many people now spend their entire day in a
browser, not using a single other application!

[^theweb]: Broadly defined, the web is the interlinked network (“web”)
of [web pages](https://en.wikipedia.org/wiki/Web_page) on the
Internet. If you've never made a web page, I recommend MDN's [Learn
Web Development][learn-web] series, especially the [Getting
Started][learn-basics] guide. This book will be easier to read if
you're familiar with the core technologies.
    
[learn-web]: https://developer.mozilla.org/en-US/docs/Learn
[learn-basics]: https://developer.mozilla.org/en-US/docs/Learn/Getting_started_with_the_web

Nowadays, desktop applications are often built and delivered as _web
apps_: websites[^website] used in similar ways to installed
applications. And on mobile devices even native apps often use _web
views_ that embed a browser to render parts of the application UI.
Perhaps in the future mobile devices will, like desktop computers,
mostly be a container for web apps.

[^website]: You probably already know what a website is. This is one.
    If not, [see here](https://en.wikipedia.org/wiki/Website).

[^hybrid]: The fraction of these _hybrid apps_ that are web content is
    also likely increasing over time.

The basis of this critical piece of software is the web. And the web
itself is built on a few simple, yet revolutionary, concepts; concepts
that that together present a vision of the future of software and
information. Among them are open, decentralized and safe computing; a
declarative document model for describing UIs; hyperlinks; and the
User Agent[^useragent]. Since the browser makes the web real,
all these concepts form the core structure of the browser code itself.

[^useragent]: The User Agent is a way to view the computer, or
    software within the computer, as a trusted assistant and advocate.

This vision of the web is neither simple nor obvious; it is the result
of experimentation and research reaching back to nearly the beginning
of computing. And of course the web _also_ needs rich computer displays,
powerful UI-building libraries, fast consumer networks, and sufficient
CPU power and information storage capacity. As so often happens, the
web has many predecessors but only took its modern form in the late
1980s, once all those technologies were available.

The browser realizes the modern web. It is the User Agent, the
_mediator_ of web interactions and _enforcer_ of its rules. Not only
that, the browser is the _implementer_ of all of the ways information
is explored. The browser keeps web browsing safe; its algorithms
implement the declarative UI; it navigates links and represents you to
web pages. And of course, for websites to load fast and react
smoothly, the browser must be hyper-efficient as well.

Lofty goals! How does the browser deliver on them? It's a fascinating
and fun journey. That's what this book is about.

Explaining the black box
========================

HTML, CSS, HTTP, hyperlinks, and JavaScript---the core of the web---are
approachable enough, and if you've made a website before you've
approachable enough, and if you've made a website before you've
seen that programming ability is not required. But not many people---not even
professional software developers---know much about how a browser renders web
pages![^software-developers]

[^software-developers]: I usually prefer “engineer”---hence the title of this
book---but “developer” or “web developer” is much more common on the web. One
important reason is that anyone can build a website---not just trained software
engineers and computer scientists. “Web developer” also is more inclusive of
additional, critical roles like designers, authors, editors, or photographers.

As a black box, the browser is either magical or frustrating (depending on
whether it is working correctly or not!). And HTML & CSS are meant to be black
boxes---declarative APIs---that one specifies _what_ outcome to achieve, as
opposed to _how_ to achieve it. The _browser itself_ is responsible for figuring
out the "how". Web developers don't, and mostly can't, draw their website’s
pixels “on their own”.

There are philosophical reasons for this unusual design. Yes, developers lose
some control and agency---when those pixels are wrong, developers cannot fix
them directly.[^loss-of-control] But they gain the ability to deploy content on
the web without worrying about the details, to make that content instantly
available on almost every computing device in existence, and to keep it
accessible in the future, mostly avoiding the inevitable obsolescence of most
software.

[^loss-of-control]: Loss of control is not necessarily specific to the web---much
of computing these days involves relying on mountains of other peoples’ code.

Behind the philosophy lies a web browser's implementations of [inversion of
control][inversion], [constraint programming][contraints], and [declarative
programming][declarative]. The web _inverts control_, with an intermediary---the
browser---handling most of the rendering, and the web developer specifying
parameters and content to this intermediary. Further, these parameters usually
take the form of _constraints_ over relative sizes and positions instead of
specifying their values directly.[^constraints] It's the browser's job to solve
the constraints or to pick which ones to break. The same idea applies for
actions: web pages mostly require _that_ actions take place without specifying
_when_ they do. This _declarative_ style means that from the point of view of a
developer, changes "apply immediately", but under the hood, the browser can be
[lazy][lazy] and delay applying the changes until they become externally
visible, either due to subsequent API calls or because the page has to be
displayed to the user.[^style-calculation]

[inversion]: https://en.wikipedia.org/wiki/Inversion_of_control
[contraints]: https://en.wikipedia.org/wiki/Constraint_programming.
[declarative]: https://en.wikipedia.org/wiki/Declarative_programming
[lazy]: https://en.wikipedia.org/wiki/Lazy_evaluation

[^forms]: As just one example, in HTML there are many built-in [form control
elements][forms] that take care of the various ways the user of a website can
provide input. The developer need only specify parameters such as button names,
sizing, and look-and-feel, or JavaScript extension points to handle form
submission to the server. The rest of the implementation is taken care of by the
browser.

[forms]: https://developer.mozilla.org/en-US/docs/Learn/Forms/Basic_native_form_controls

[^constraints]: Constraint programming is clearest during web page layout, where
font and window sizes, desired positions and sizes, and the relative arrangement
of widgets is rarely specified directly. A fun question to consider: what does
the browser "optimize for" when computing a layout?

[^style-calculation]: For example, when exactly the browser compute which CSS
styles apply to which HTML element, for example after a web page changes those
styles? The change is visible to all subsequent API calls, so in that sense it
applies "immediately". But it is better for the browser to delay style
re-calculation, avoiding redundant work if styles change twice in quick
succession. Maximally exploiting the opportunities afforded by declarative
programming makes real-world browsers very complex.

The up shot of all this is that a browser is a pretty unusual piece of software,
with unique challenges, interesting algorithms, and clever optimizations
invented just for this domain. That makes browsers worth studying for the pure
pleasure of it---even leaving aside their importance!

The browser and me
==================

I[^chris] have known the web almost all of my adult life. Ever since I first
encountered the web, and its predecessors,[^bbs] in the early 90s, I was fascinated
by browsers and the concept of networked user interfaces. When I surfed the
web, even in its earliest form, I felt I was seeing the future of computing.
In some ways, the web and I grew together---for example, in 1995, the year the
web went commercial, was the same year I started college; while there I spent
a fair amount of time surfing it, and by the time I graduated in 1999, the
browser had fueled the famous dot-com speculation gold rush. The company for
which I now work, Google, is a child of the web and was founded during that
time. The web for me is something of a technological companion, and I’ve never
been far from it in my studies or work.

[^chris]: This is Chris speaking!

[^bbs]: For me, this was mostly using
[BBS](https://en.wikipedia.org/wiki/Bulletin_board_system) systems over a dialup
modem connection. A BBS is not all that different in concept from a browser if
you look at it from the point of view of “window into dynamic content created
somewhere else on the Internet”.

In my freshman year at college, I attended a presentation at the university by a
RedHat salesman. The presentation was of course aimed at selling RedHat Linux,
and probably included statements like Linux being the operating system of the
future, or the always-popular speculation about the “year of the Linux desktop.”
However, when asked about challenges RedHat faced, the salesman mentioned not
Linux but _the web_. He said something like “someone needs to make a good
browser for Linux. _It’s hard to be competitive without a good
browser”_[^netscape-linux]_._ Even back then, in the very first year or so of
the web, the browser was already becoming an absolutely necessary component of
every computer. He even threw out a challenge: “how hard could it be to build a
better browser?” Indeed, how hard could it be? What makes it so hard? That
question stuck with me for a long time.[^meantime-linux]

[^netscape-linux]: Netscape Navigator was available for Linux at that time, but
it wasn’t viewed as especially fast or featureful compared to its implementation
on other operating systems.


[^meantime-linux]: Meanwhile, the “better Linux browser than Netscape” seemed to
take quite a long time to appear....

How hard indeed! After seven years in the trenches working on a browser
(Chrome), I now know the answer to his question: building such a browser is
both easy and incredibly hard, intentional and accidental, planned and organic,
simple and unimaginably complex. And everywhere you look, you can see the
evolution and history of the web all wrapped up in one codebase.

As you’ll see when reading this book, it’s surprisingly easy to write a very
simple browser, one that can despite its simplicity display interesting-looking
web pages, and can even more-or-less correctly display many real ones, including
this book. This starting point---it’s easy enough to implement (and write) web
pages with the basics---encapsulates the (intentionally!) easy-to-implement core
of the web architecture, what you might call the _base level_ of [progressive
enhancement](https://en.wikipedia.org/wiki/Progressive_enhancement). I saw this
in the relative simplicity of individual features of Chrome---for example,
sometime during my first few months of working on Chrome, I came across the code
implementing the
[`<br>`](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/br) tag. Look
at that, the good-old `<br>` tag that I’ve used many times as a convenient hack
to insert newlines in the text of my web pages! And as it turns out, there
really isn’t much code at all to implement this tag, either in Chrome or the
simple browser you’ll build.

On the other hand, to make a browser that has all the features, performance,
security and reliability of today’s top browsers---well that is a whole lot of
work; _thousands_ of person-years of effort went into what you see today. On top
of that, but keeping a browser competitive is a lot of work: not only is there
an inherent cost to maintaining such large codebases, but there is constant
pressure to do more---add more features, continually improve performance to beat
the competition, and in general keep up with everything going on in what we now
call the “web ecosystem”---the millions of developers, billions of users, and
all the businesses and economies that build on the web. There are tens of
thousands of unfixed bugs in every browser, representing all the ways that bugs
can appear with the smallest of mistakes, through the myriad of ways to mix and
match features. There is the extreme complexity of trying to understand the
complicated set of optimizations deemed necessary to squeeze out the last bit of
performance from the system. And there is the painstaking, but necessary, work
to continuously refactor the code to reduce its complexity through the
careful[^browsers-abstraction-hard] introduction of modularization and
abstraction.

[^browsers-abstraction-hard]: Browsers are so performance-sensitive in many
places that merely the introduction of an abstraction - and the typical ensuing
function call or branching overhead---can cause an unacceptable performance
cost.

Working on such a codebase is often daunting. For one thing, there is an
immense history to each browser. It’s not uncommon to find lines of code last
touched 15 years ago by someone who you’ve never met; or even after years of
working discover files and code that you didn’t even know existed; or see 
lines of code that don’t look necessary, and all tests pass without them. If I
want to know what that 15-year-old code does, how can I do it? Does that code
I just discovered matter at all? Can I just delete those lines of code that
don’t seem necessary?

These kinds of quandaries come up all the time when working on a browser - in
fact they are common to all complex codebases. What makes a browser different is
that there is often an _urgency to fix them_. Browsers are nearly as old as any
“legacy” codebase, but are _not_ legacy (meaning deprecated or half-deprecated,
and scheduled to be replaced by some new codebase sometime soon) at all---on the
contrary, they are vital to the world’s economy. For this reason, and the
infeasibility of rewriting, browser engineers are forced[^forced-negative] to
fix and improve rather than replace.

[^forced-negative]: I say "forced", which has a negative connotation, but it’s
more of an iterative & continuous process of improvement.

It’s not just urgency though---understanding the cumulative answers to these
small questions yields true insights into how computing actually works, and
where future innovations may appear. In fact, browsers are where the fun of
algorithms _comes to life_. Where else can one explore the limits of so many
parts of computer science? Consider that a browser contains: a rendering engine
more complex and powerful than any computer game; a full networking stack; many
clever data structures and parallel programming techniques; a virtual machine,
interpreted language and JIT; world-class security sandboxes; and uniquely
dynamic systems for storing data. On top of this, the browser interacts in a
fascinating and symbiotic way with the huge number of websites deployed today.

The web in history
==================

The public Internet and the Web co-evolved, and in fact many peoples’ first
experiences of the Internet in the 1990s and onward were more or less
experiences with the web. However, it’s important to distinguish between them,
since the Internet and the web are in fact not synonymous.

In the early days, the similarity between the _physical structure_ of the web---
where the web servers were---and the _names_ of the websites was very strong.
The Internet was a world wide network of computers, those computers had domain
names, and many of them ran web servers. In this sense, the Internet and the web
really were closely related at that time. However, there is of course nothing
inherent about this: nothing forces you to host your own web server on your home
computer and Internet connection[^self-hosted], and the same goes for a
university or corporation. Likewise, there is nothing requiring everyone to have
their own web site rather than a social networking account. These days, almost
everyone uses a virtual machine or service purchased from one kind of cloud
computing service or another to run their websites, regardless of how small or
large, and there are many products available that can easily publish your web
content on your behalf on various social networking platforms.

[^self-hosted]: People actually did this! And when their web site became
popular, it often ran out of bandwidth or computing power and became
inaccessible.

This same *virtualization* concept also applies to the implementation of web
pages themselves. While it’s still possible to write HTML by hand, few of the
most popular web sites’ HTML payloads literally exist on a hard drive somewhere.
Instead, their component pieces and dependent databases exist, and the final
product is dynamically assembled on the fly by complex build and
“rendering”[^server-side-rendering] systems and sent over the Internet on-demand
to your browser. The reason for this is that their contents themselves are
dynamic---composed of data from news, blog posts, inbox contents,
advertisements, and algorithms adjusting to your particular tastes.

[^server-side-rendering]: "Server-side rendering" is the process of assembling
HTML on the server when loading a web page. Server-side rendering is sometimes
run in JavaScript, and sometimes even with a
[headless](https://en.wikipedia.org/wiki/Headless_browser) browser.

There is also aforementioned _web app_, which is a computer application written
entirely as a web page. These applications are widespread and are gradually
expanding to include nearly all types of computer tasks as the capabilities of
browsers to support those tasks expand. While these web apps  are part of the
web (e.g. they are loadable via URL), thinking of them as web pages is sometimes
confusing. To deal with this confusion, there is often a conceptual distinction
made (even if it is blurry in practice) between an “informational” _web page_
and a “task-based” _web app_, even though they use the same underlying
technology. Related to the notion of a web app is a _PWA_[^pwa], which is often
described as what may appear to the user as a regular “native” app, but is built
entirely as a website under the hood.

[^pwa]: PWA stands for Progressive Web App. In this case, progressive refers
to progressive enhancement.

For these reasons, it’s sometimes confusing to know what we should think of as
“the web”. Here is one definition[^key-web-properties] that gets at its essence:

*   The web is a _network of information_, built at its base on the _HTTP 
    network protocol_, the _HTML information format_, and the concept of a _
    hyperlink_.
*   Its unit of information is a _web page_, which is identified uniquely by
    its unique URL (_not_ by its content, which as mentioned above may be dynamic).
*   Web pages are _documents_ written in HTML.
*   Web pages can refer, via URL, to auxiliary assets such as images, video,
    CSS, and JavaScript, that are needed for their functionality.
*   Web pages _refer to each other_ other with hyperlinks.
*   The user views and navigates web pages through a _browser_, which is also
    sometimes called the _user agent_.
*   All APIs on the web are open, standardized and free to use or re-use.

[^key-web-properties]: It’s worth repeating here that this definition is not
[accidental and is part of the original design of the web. The fact that the
web not only survived but thrived during the process of "virtualization" of
hosting and content further demonstrates the elegance and effectiveness of
its original design.

One might try to argue that HTTP, URLs and hyperlinking are the only truly
essential parts of the Web, or  also argue that a browser is not strictly
necessary, since conceptually websites exist independently of the browser for
them, and could in principle self-render through dedicated
applications[^dedicated-applications]. In other words, one could try to separate
out the networking and rendering aspects of the web; likewise, one could
abstract the concept of linking and networking from the particular choice of
protocols and data formats. In theory it is indeed true that one or more of the
implementation choices could be replaced, and perhaps that will happen over
time. For example, JavaScript might eventually be replaced by another language
or technology, HTTP by some other protocol, or HTML by its successor.

[^dedicated-applications]: For example, if you're using an installed PWA, are
you using a browser?

In practice, it is not really the case that networking and rendering are
separated, and there are in fact important inter-dependencies---for example,
HTML plays a critical role in both rendering and hyperlinks. It’s best to just
consider browsers, HTML (and CSS and JavaScript) part of the core definition of
the web. In any case, as with all technology, the web continues to evolve. The
above definition may change over time, but for the purposes of this book, it’s a
pretty good one.

Technological precursors
========================

The web is at its core organized around _representing and displaying
information_, and how to provide a way for humans to effectively learn and
explore that information. The collective knowledge and wisdom of the species
long ago exceeded the capacity of a single mind, organization, library, country,
culture, group or language. However, while we as humans cannot possibly know
even a tiny fraction of what is possible to know, we can use technology to learn
more efficiently than before, and most importantly, to quickly access
information we need to learn or remember[^google-mission]. Computers, and the
Internet, allow us to _process and store_ as much information as we want. The
_web_, on the other hand, plays the role of _organizing and finding_ that
information and knowledge to make it useful.

[^google-mission]: The search engine Google’s [mission](https://about.google/)
statement to “organize the world’s information and make it universally
accessible and useful” is almost exactly the same as this. This is not a
coincidence - the search engine concept is inherently connected to the web.

The earliest exploration of how computers might revolutionize information is a
1945 essay[^memex-essay] entitled [As We May
Think](https://en.wikipedia.org/wiki/As_We_May_Think). This essay envisioned a
machine called a [Memex](https://en.wikipedia.org/wiki/Memex). The Memex was an
imagined machine that helps (think: User Agent) an individual human to see and
explore all the information in the world. It was described in terms of microfilm
screen technology of the time, but its purpose and concept has some clear
similarities to the web as we know it today, even if the user interface and
technology details differ.

[^memex-essay]: This brief prehistory of the web is by no means exhaustive.
Instead, you should view it as a brief view into a much larger - and quite
interesting in its own right - subject.

The concept of networked links of information began to appear in about
[1964-65](https://en.wikipedia.org/wiki/Hyperlink), when the term “link”
appeared (though connected to text rather than pages). Researchers then
began to  advocate for building a network of computers to realize the
concept.[^literary-criticism] Independently, the first hyperlink system appeared (though
apparently not using that word[^hyperlink-first]) for navigating within a single
document; it was later generalized to linking between multiple documents. This
work also formed one of the key parts of the [mother of all
demos](https://en.wikipedia.org/wiki/The_Mother_of_All_Demos), the most famous
technology demonstration in the history of computing.

[^hyperlink-first]: The word "hyperlink" may have fisrt appeared in 1987, in
connection with the HyperCard system on the Macintosh.)

[^literary-criticism]: These concepts are also the computer-based evolution of
the long tradition of citation in academics and literary criticism.

In 1983 the [HyperTIES](http://www.cs.umd.edu/hcil/hyperties/) system was
developed around highlighted hyperlinks. This was used to develop the world’s
first electronic journal, the 1988 issue of the [Communications of the
ACM](https://cacm.acm.org/). Tim Berners-Lee cites this 1988 event as the source
of the link concept in his World Wide Web concept[^world-wide-web-terminology],
in which he proposed to join the link concept with the availability of the
Internet, thus realizing many of the original goals of all the work from
previous decades.[^realize-web-decades]

[^world-wide-web-terminology]: Nowadays the World Wide Web is called just “the
web”, or “the web ecosystem”---ecosystem being another way to capture the same
concept as “World Wide”). The original wording lives on in the "www" in many
web site domain names.

[^realize-web-decades]: The web itself is, therefore, an example of the
realization of previous ambitions and dreams, just as today we strive to realize
the vision laid out by the web.

In 1989-1990, the first browser (named “WorldWideWeb”) and web server (named
“httpd”, for “HTTP Daemon” according to UNIX naming conventions) were born,
again written in their first version by Berners-Lee. Interestingly, the
browser’s capabilities were in some ways inferior to the browser you will
implement in this book[^no-css], and in some ways go beyond the capabilities
available even in modern browsers.[^more-less-powerful] On December 20, 1990 the
[first web page](http://info.cern.ch/hypertext/WWW/TheProject.html) was created.
The browser we will implement in this book is easily able to render this web
page, even today.[^original-aesthetics] In 1991, Berners-Lee advertised his
browser and the concept on the [alt.hypertext Usenet
group](https://www.w3.org/People/Berners-Lee/1991/08/art-6484.txt). [^gopher]

[^no-css]: No CSS!

[^more-less-powerful]: For example, it included the concept of an index page
meant for searching within a site (vestiges of which exist today in the
“index.html” convention when a URL path ends in /”), and had a WYSIWYG web page
editor (the “contenteditable” HTML attribute and “html()” method on DOM elements
has similar semantic behavior, but built-in file saving is gone). Today, the
index is replaced with a search engine, and web page editors as a concept are
somewhat obsolete due to the highly dynamic nature of today’s web site
rendering.

[^original-aesthetics]: Also, as you can see clearly, that web page has not been
updated in the meantime, and retains its original aesthetics!


[^gopher]: Another system that allowed linking across sites on the internet was
[Gopher](https://en.wikipedia.org/wiki/Gopher_(protocol)), which appeared around
1991, but was quickly supplanted by the web.

Berners-Lee has also written a [Brief History of the
Web](https://www.w3.org/DesignIssues/TimBook-old/History.html) that  highlights
a number of other interesting factors leading to the establishment of the web as
we know it. One key factor was its decentralized nature, which he describes as
arising from the culture of CERN, where he worked. The decentralized nature of
the web is a key feature that distinguishes it from many systems that came
before or after, and his explanation of it is worth quoting here (highlight is
mine):

> There was clearly a need for something like Enquire [ed: a predecessor
> software system] but accessible to everyone. I wanted it to scale so that if
> two people started to use it independently, and later started to work
> together, *they could start linking together their information without
> making any other changes*. This was the concept of the web.

This quote captures one of the key value propositions of the web. The web was
successful for several reasons, but I believe it’s primarily the following
three:

*   It provides a very low-friction way to publish information and applications.
There is no gatekeeper to doing anything, and it’s easy for novices to make a
simple web page and publish it.

*   Once bootstrapped, it builds quickly upon itself via [network
effects](https://en.wikipedia.org/wiki/Network_effect) made possible by
compatibility between sites and the power of the hyperlink to reinforce this
compatibility. Hyperlinks drive traffic between sites, but also into the web
_from the outside_, via email, social networking, and search engines.

*   It is outside the control of any one entity - and kept that way via
standards organizations - and therefore not subject to problems of monopoly
control or manipulation.

The browser ecosystem
=====================

Browsers have a unique character in that they are _not proprietary_ - no company
controls the APIs of the web and there are multiple independent implementations.
In addition, it turned out that over time almost all of the code became
open-source and developed by a very wide array of people and entities. As a
corollary, the software platform for web sites is also not proprietary, and the
information and capabilities contained within them are easy to make accessible 
to everyone[^unless-restricted].

[^unless-restricted]: Unless, of course, the web site chooses to restrict
availability for one reason or another. The point is that the _web platform_
does not restrict availability, and therefore the web site has the freedom to
choose.

I'll now give a brief overview of the evolution of browser implementations. The
first _widely distributed_ browser may have been
[ViolaWWW](https://en.wikipedia.org/wiki/ViolaWWW); this browser also pioneered
multiple interesting features such as applets and images. This browser was in
turn the inspiration for [NCSA
Mosaic](https://en.wikipedia.org/wiki/Mosaic_(web_browser)), which launched in
1993. One of the two original authors of Mosaic went on to co-found
[Netscape](https://en.wikipedia.org/wiki/Netscape_Navigator), the first
_commercial browser_[^commercial-browser], which launched in 1994. The era of
the [”first browser
war”](https://en.wikipedia.org/wiki/Browser_wars#First_Browser_War_(1995%E2%80%932001))
ensued, in a competition between Netscape and Internet Explorer. In addition,
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
codebase.

 During this time, essentially all of the features you will implement in your
browser were added, including CSS, DOM, and JavaScript. The second browser war, which
according to Wikipedia was
[2004-2017](https://en.wikipedia.org/wiki/Browser_wars#Second_Browser_War_(2004%E2%80%932017)),
was between a variety of browsers - Internet Explorer, Firefox, Safari and
Chrome in particular. Chrome split off its rendering engine subsystem into its
own code base called
[Blink](https://en.wikipedia.org/wiki/Blink_(browser_engine)) in 2013.

[^commercial-browser]: By commercial I mean built by a for-profit entity.
Netscape's early versions were also not free software---you had to buy them from
a store.

In parallel with these developments was another, equally important, one---the
standardization of Web APIs. In October 1994, the [World Wide Web
Consortium](https://www.w3.org/Consortium/facts) (W3C) was founded in order to
provide oversight and standards for web features. For a time after this point,
browsers would often introduce new HTML elements or APIs, and competing browsers
would copy them. Those elements and APIs were subsequently agreed upon and
documented in W3C specifications. (These days, an initial discussion,  design
and specification precedes any new feature.) Later on, the HTML specification
ended up moving to a different standards body called the
[WHATWG](https://whatwg.org/), but [CSS](https://drafts.csswg.org/) and other
features are still standardized at the W3C. JavaScript is standardized at
[TC39](https://tc39.es/) (“Technical Committee 39” at
[ECMA](https://www.ecma-international.org/memento/history.htm), yet another
standards body). [HTTP](https://tools.ietf.org/html/rfc2616) is standardized by
the [IETF](https://www.ietf.org/about/).

In the first years of the web, it was not so clear that browsers would remain
standard and that one browser might not end up “winning” and becoming another
proprietary software platform. There are multiple reasons this didn’t happen,
among them the egalitarian ethos of the computing community and the presence and
strength of the W3C.  Equally important was the networked nature of the web, and
therefore the desire of websites to make sure their site worked correctly in
most or all of the browsers (otherwise they would lose customers), leading them
to avoid any proprietary extensions.

Despite fears that this might happen, there never really was a point where any
browser openly attempted to break away from the standard. Instead, intense
competition for market share was channeled into very fast innovation and an
ever-expanding set of APIs and capabilities for the web, which we nowadays refer
to as _the Web Platform,_ not just the “World Wide Web”. This recognizes the
fact that the web is no longer a document viewing mechanism, but has evolved
into a fully realized computing platform and ecosystem.[^web-os] Given these
outcomes, in retrospect it is clear that it’s not so relevant to know which
browser “won” or “lost” each of the browser “wars”. In both cases _the web won_
and was preserved and enhanced for the benefit of the world. In economics terms,
enforcing a standard set of APIs across browsers made the web platform a
_commodity_; instead of competing based on lock-in, browsers compete on
_performance_ and _quality_, and also _browser features_ that are not part of
the web platform---for example, tabbed UIs and search engine integration.
Browser development is also primarily funded by revenue from search engine
advertisements; a secondary typical funding motivation is to improve the
competitive position of an operating system or device owned or controlled by the
company building the browser.[^compare-redhat]

[^web-os]: There have even been operating systems built around the web! Examples
include [webOS](https://en.wikipedia.org/wiki/WebOS), which powered some Palm
smartphones, [Firefox OS](https://en.wikipedia.org/wiki/Firefox_OS) (that today
lives on in [KaiOS](https://en.wikipedia.org/wiki/KaiOS)-based phones), and
[ChromeOS](https://en.wikipedia.org/wiki/Chrome_OS), which is a desktop
operating system. All of these OSes are based on using the Web as the UI layer
for all applications, with some JavaScript-exposed APIs on top for system
integration.

[^compare-redhat]: Compare this with the RedHat anecdote I related earlier!

An important and interesting outcome of the _second_ browser war was that all
mainstream browsers today (of which there are *many* more than
three[^examples-of-browsers-today]) are based on _three open-source web
rendering / JavaScript engines_: Chromium, Gecko and WebKit[^javascript-repo].
Since Chromium and WebKit have a common ancestral codebase, while Gecko is an
open-source descendant of Netscape, all three date back to the 1990s---almost to
the beginning of the web. That this occurred is not an accident, and in fact
tells us something quite interesting about the most cost-effective way to
implement a rendering engine based on a commodity set of platform APIs.

[^examples-of-browsers-today]: Examples of Chromium-based browsers include
Chrome, Edge, Opera (which switched to Chromium from the
[Presto](https://en.wikipedia.org/wiki/Presto_(browser_engine)) engine in 2013),
Samsung Internet, Yandex Browser, and UC Browser. In addition, there are many
"embedded" browsers, based on one or another of the three engines, for a wide
variety of automobiles, phones, TVs and other electronic devices.

[^javascript-repo]: The JavaScript engines are actually in different
repositories (as are various other sub-components that we won’t get into here),
and can and do exist outside of browsers as JavaScript virtual machines. One
important such application is the use of
[v8](https://en.wikipedia.org/wiki/V8_(JavaScript_engine)) to power
[node.js](https://en.wikipedia.org/wiki/Node.js). However, each of the three
rendering engines does have its own JavaScript implementation, so conflating the
two is reasonable.

How browsers evolve
===================

At the highest level, a browser has two major pieces of code: an implementation
of the web platform APIs (sometimes called a _web rendering engine_), and a
browsing UI and accompanying features, such as search engine integration,
bookmarks, navigation, tabs, translation, autofill, password managers, data sync
and so on.

Web rendering engines have a lot in common with any other very large software
project---they have a _very high total cost of development_, and a _significant
& increasing over time_ cost of maintenance (due to the ever-expanding feature
set). However, they also have a unique character in that they are just as much
community and ecosystem-driven as they are self-driven. In other words, since
the character of the web itself is highly decentralized, what use cases end up
getting met by browsers is to a significant extent _not determined_ by the
companies “owning” or “controlling” a particular browser. For example, there are
many other people, such as website developers, who contribute many good ideas
and proposals that end up implemented in browsers.

Due to the very high cost of building and maintaining an implementation of the
web platform, and the fact of being community-driven (and therefore having no
sustainable proprietary advantage over competitors), it makes sense that the
engine source code itself be open-source as well. This allows sharing the burden
(opportunity?) of maintenance and feature development across a larger community.
Another consequence of being driven collectively by the community is that a
browser often functions like an R&D project, where new ideas are constantly
being proposed and tested out in discussions and implementations. Like any R&D
project, this leads to the browser having an iterative and incremental planning
and shipping process---at any given time it’s not easy to lay out the exact
plans for the next year in great precision (let alone five years), because it’s
always unknown how well current projects will work or what new ideas might surface.

Browsers and you
================

This book explains how to build a simple web rendering engine plus browser
shell, as well as many details about advanced features and the architecture of
a real browser’s rendering engine. From this you will learn what is easy and 
what is hard in these engines: which algorithms are easy to understand, and
which are tricky and subtle to get right; what makes a browser fast, and what
makes it slow; and all the core concepts you need to understand to predict the
behavior of a real-world browser. After reading all of it, you should be able
to dig into the source code for a real browser’s rendering engine and
understand it without too much trouble.

The intention of the book is for you to build your own browser as you work
through the early chapters. Once your browser is up and running, there are
endless opportunities to improve performance or add features. Many of the
exercises at the ends of the chapters are suggested feature enhancements that
are similar to ones that come up in real browsers. We encourage you to try the
exercises---adding these features is one of the most fun parts of browser
development! It’s also a lot of fun (and very satisfying) to compare your
browser with a real one, or see how many websites you can successfully render. 

The browser is an essential part of computing, and this chapter gave evidence of
that fact, along with a flavor of the depth and history of the web and browsers.
However, I believe that only by really understanding how a browser works will
you really appreciate and understand its beauty, complexity and power fully. I
hope you come away from this book with a deeper sense of this beauty---how it
works, its relationship to the culture and history of computing and information,
what it’s like to be someone building a browser. But most of all, I hope you can
connect all of that to you, your career in software and computers, and the
future. After all, it’s up to you to invent and discover what comes next!
