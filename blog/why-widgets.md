---
title: Why Widgets?
author: Pavel Panchekha
date: 22 April 2020
prev: outlines
...

This is a different kind of blog post---perhaps you can call it a
manifesto. When Chris and I published [Chapter 5](../layout.md), we
included two interactive widgets that let you explore how the element
tree and layout tree interact. We plan to do more. This post is about
why we are building these widgets and what we hope to accomplish. I'll
follow up with more posts later on the technical details, which I
think are quite subtle and interesting!

# An example widget

Consider the following widget, which steps you through how line height
is computed when different font sizes are mixed:

::: {.widget height=204}
    lab3-baselines.html
:::

Click the buttons to start the simulations and go through the steps
one by one. You can see how baseline computation:

+ Finds the ascent and descent height of each individual word
+ Adds the maximum ascent to the _y_-cursor to compute the baseline
+ Places each word above the baseline by the size of its ascent
+ Computes the new _y_-cursor by adding the maximum descent to the baseline

In the widget, pink and blue represent ascents and descents, with dark
red and dark blue showing the maximum ascent / descent (once that's
computed). The variable names (in typewriter font on the right)
correspond to the variables in [Chapter 3](../text.md)'s `flush`
method.

Of course, we didn't invent this idea of interactive widgets. Perhaps
it all goes back to Logo and the work of Seymore Pappert. [Bret
Victor][explore-explain] is of course the modern intellectual source.
[Bartosz Ciechanowski][bartosz]'s visual explanations are a more
direct inspiration. [Pierre-Marie Dartus][shadow-dom-widgets]'s essay
on shadow DOM event propagation gave us a browser-related example to
study. In any case, I think widgets like this will help readers better
understand our book.

[explore-explain]: http://worrydream.com/ExplorableExplanations
[bartosz]: https://ciechanow.ski
[shadow-dom-widgets]: https://pm.dartus.fr/blog/a-complete-guide-on-shadow-dom-and-event-propagation/

# Goals for widgets 

So let me dissect this widget a bit---how is it better or worse than
the bulleted list above?

First off, of course, it is visual, and might be easier to pick up
that way. If you click through the widget you could probably figure
out the steps without reading anything. Some people prefer that, and
also if you already read the text the visual can reinforce things.

Second, the visual representation actually reinforces some key
concepts. For example, layout has two phases, you _first_ lay it out
horizontally, and only _later_ lay it out vertically. Putting two
things on the screen, labeled "Phase 1" and "Phase 2", reinforces that.

Third, the widget can actually reveal things that were hidden in the
description. For example, the bullet points in the previous section
didn't mention [leading], but it clearly shows up in the widget. In
fact, in a proper browser, the amount of leading above and below the
text should be the same---the widget shows that (for simplicity) this
book's toy browser doesn't do that.

[leading]: ../text.html#measuring-text

Finally, the widget can use color or shape to highlight relationships
and states. My widget above shows the maximum ascent and descent in a
different color, and uses those colors to hint that the line's height
is computed based on a maximum ascent and descent, but each word is
aligned relative to its own ascent and descent. That hints at the
correct algorithm without having to explain it.

To summarize: Just clicking through the widget should explain the
algorithm. The widget should make key concepts visual. It should
be real enough that it can surprise you. And it should use color,
alignment, and size to suggest real relationships in the code.

# Technical requirements

Ok---these are nice goals. But achieving them means surmounting some
real challenges:

For the widget to explain the algorithm, the user needs to execute the
code step by step. But you normally don't want the browser to pause
randomly, and adding code to support it would clutter up the browser
code and make it much harder to explain. A debugger could work, but
most debuggers, like the built-in `pdb`, can't step backwards, and
that's quite useful when learning.

To visually present key concepts each widget would need to be
custom-written. Each chapter means new concepts means new visuals!
That means any other overhead---coding up the widget, styling things,
adding step controls---needs to be minimized. If each widget is a
pain, Chris and I aren't going to write very many!

For the widget to be real, it should run the same code described in
the book. But the book is [written in Python](why-python.md), not
JavaScript, so it can't be run in the reader's browser. And neither I
nor Chris want to maintain the book in two languages. Anyway, bugs in
the translation would mean the confusing or deceptive widgets.

And for the widgets to use visual relationships to signify logical
ones, each widget would need custom styling and custom visuals. Yet
the widgets should also fit naturally into the book and have similar
styles and controls, so readers would know what to do when they saw
one.

These are pretty stringent requirements, so the solution Chris and I
have found is crazy and bizarre---I'll be explaining it over the next
few blog posts. Stay tuned!
