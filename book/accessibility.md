---
title: Making Content Accessible
chapter: 14
prev: animations
next: skipped
...


Section 1: what is accessibility (link to authoritative texts), what kinds of accessibility APIs exist. Keep it focused on what exists in browsers and how they work.

Types of accessibility to implement in this chapter:
Text zooming
Keyboard navigation
Voice interaction and navigation
Focus highlighting

Skipped:
High-contrast mode [Leave to an exercise]
Other kinds of input modalities, like:
Caret browsing [Just a simulated mouse, not that important to show how to implement] or other kinds of special input devices
Other mouse features like visual indications for mouse etc
Autofill [Leave to exercise]


Section 2: focus indicators; tab order

Implement visual focus rings via the CSS outline property
Define ‘focusable’ elements
Implement the focus pseudoclass
Implement ‘tab’ to rotate among focusable elements
Implement tabindex to control tab order

Section 3: keyboard interactions generally
Implement ‘enter’ to cause a button click.
Implement shortcut to focus the URL bar.
Implement keyboard back-button

Section 4: text zooming
Implement zooming of css pixels and how it affects layout
Add a keyboard shortcut for ctrl-+/-

Section 5: voice interaction
Introduce accessibility tech
Implement the accessibility tree
Introduce the concept of implicit accessibility semantics, such as via form controls or links
Integrate with NVDA
Demonstrate how to run the browser and interact with web pages with the same tool

Section 7: aria labels, modifications of the accessibility tree
Introduce one or two
Introduce concept of alternate text, with anchor link text as an example
Augment the accessibility tree via them
Implement display: none
Implement inert

OS integrations:
https://www.w3.org/TR/accname-1.2/
https://www.w3.org/TR/core-aam-1.2/
https://www.w3.org/TR/html-aam-1.0/
https://www.w3.org/TR/svg-aam-1.0/



Section 6: visual modes for accessibility
Introduce media queries. Example: dark mode
Another example: prefers reduced motion
Third example: color contrast, forced colors mode


Other thoughts:
Introduce the role attribute? (needs a compelling example; maybe explain in the context of aria + the accessibility tree?)
