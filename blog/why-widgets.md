---
title: Why Widgets?
author: Pavel Panchekha
date: 22 April 2020
prev: outlines
...

When Chris and I published [Chapter 5](../layout.md), we included two
interactive widgets that let you explore how the element tree and
layout tree interact. We plan to do more. So this post is a bit of our
thought process: why are we building these widgets, and what do we
hope to accomplish. I'll follow up with more posts later on the
technical details, which I think are quite subtle and interesting!

# An example widget

Consider the following widget, which steps you through how line height
is computed when different font sizes are mixed:

<iframe class="widget" src="widgets/lab3-baselines.html"
    height=160 data-big-height=160 data-small-height=320></iframe>

Please note that Chris and I haven't spent much time on the aesthetics
here. It won't stay a bland gray! But click "Next" a few times and see
the logic of baseline computation.

Just to refresh your memory, here's how baseline computation works:

+ Find the ascent and descent height of each individual word
+ Add the maximum ascent to the _y_-cursor to compute the baseline
+ Place each word by moving it its ascent above the baseline
+ Compute the new _y_-cursor by adding the maximumn descent to the baseline

The visualization in the widget shows each of these steps happen.
Specifically, pink and blue represent ascents and descents, with dark
red and dark blue showing the maximum ascent / descent, once that's
computed. The variable names (in typewriter font on the right)
correspond to the variables in [Chapter 3](../text.md)'s `flush`
method.

But the widget is a little more than just this list of steps.
