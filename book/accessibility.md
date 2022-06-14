---
title: Making Content Accessible
chapter: 14
prev: animations
next: skipped
...

It's important for everyone to be able to access content on the web, even if you
have a hard time using a mouse, can't read small fonts easily, are triggered by
very bright colors, or can't see a computer screen at all. It turns out that,
without too much more effort, our browser can address all of these problems,
through a variety of User Agent features that alonw the user to customize the
browser to meet their accessibilty needs.

Text zoom
=========

Let's start with the simplest, and perhaps most common accessibility problem:
reading words that have too small of a font. Almost all of us will face this
problem sooner or later, as our eyes become more weak with age. There are
multiple ways to do this, but the simplest and most effective is simply
increasing the size of fonts via a feature called zoom---like a camera zooming
in on a scene. Let's try that.

Let's bind the `ctrl-plus` keystroke combo to zooming in, `ctrl-minus` to
zooming out, and `ctrl-zero` to reset. The `zoom` of the browser wll start at
1. Zooming in and out will increase or decrease this number. Then we'll use the
number to multiply the sizes of all of the fonts on the page.

Binding these keystrokes in the browser main loop involves watching for when the
`ctrl` key is pressed and released:

``` {.python}
    ctrl_down = False
    while True:
		if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
			# ...
            elif event.type == sdl2.SDL_KEYDOWN:
            	# ...
                elif event.key.keysym.sym == sdl2.SDLK_RCTRL or \
                    event.key.keysym.sym == sdl2.SDLK_LCTRL:
                    ctrl_down = True            	
            elif event.type == sdl2.SDL_KEYUP:
                if event.key.keysym.sym == sdl2.SDLK_RCTRL or \
                    event.key.keysym.sym == sdl2.SDLK_LCTRL:
                    ctrl_down = False
           # ...
```

and then looking for plus, minus or zero pressed next and running code in the
browser:

``` {.python}
    while True:
		if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
			# ...
            elif event.type == sdl2.SDL_KEYDOWN:
                if ctrl_down:
                    if event.key.keysym.sym == sdl2.SDLK_EQUALS:
                        browser.increment_zoom(1)
                    elif event.key.keysym.sym == sdl2.SDLK_MINUS:
                        browser.increment_zoom(-1)
                    elif event.key.keysym.sym == sdl2.SDLK_0:
                        browser.reset_zoom()			
             	# ...
```

The `Browser` code just delegate to the `Tab`:

``` {.python}
class Browser:
	# ...
    def increment_zoom(self, increment):
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.zoom_by, increment)
        active_tab.task_runner.schedule_task(task)

    def reset_zoom(self):
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.reset_zoom)
        active_tab.task_runner.schedule_task(task)
```

which in turn changes `zoom` and re-renders:

``` {.python}
class Tab:
    def __init__(self, browser):
    	# ...
    	self.zoom = 1

	# ...
    def zoom_by(self, increment):
        if increment > 0:
            self.zoom *= 1.1;
        else:
            self.zoom *= 1/1.1;
        self.set_needs_render()

    def reset_zoom(self):
        self.zoom = 1
        self.set_needs_render()
```

Now we just need to pass `zoom` down into `layout`:

``` {.python replace=document/layout_tree}
class Tab:
	# ...
	def render(self):
			# ...
			self.document.layout(self.zoom)
```

And within each layout class type pass around `zoom` as well; whenever a font is
found, override the font size to account for zoom. To update that zoom let's
use a helper method that coverts from a *layout pixel* to a *device pixel* by
multiplying by zoom:

``` {.python}
def device_px(layout_px, zoom):
    return layout_px * zoom
```

Finally, there are a bunch of small changes to the `layout` methods. First
`BlockLayot`, `LineLayout` and `DocumentLayout`, which just pass on the zoom
to children:

``` {.python}
class BlockLayout:
	# ...
    def layout(self, zoom):
        for child in self.children:
            child.layout(zoom)

class LineLayout:
	# ...
    def layout(self, zoom):
        for word in self.children:
            word.layout(zoom)

class DocumentLayout:
	# ...
    def layout(self, zoom):
    	# ...
        child.layout(zoom)

```

`InlineLayout` is where it starts to get interesting. First some regular
plubming happens:

``` {.python}
class InlineLayout:
	# ...
    def layout(self, zoom):
    	# ...
        self.recurse(self.node, zoom)
        # ...
        for line in self.children:
            line.layout(zoom)

    def recurse(self, node, zoom):
        if isinstance(node, Text):
            self.text(node, zoom)
        else:
        	# ...
            elif node.tag == "input" or node.tag == "button":
                self.input(node, zoom)
            else:
                for child in node.children:
                    self.recurse(child, zoom)
```

But when we get to the `text` and `input` methods, the font sizes should be
adjusted:

``` {.python}
    def text(self, node, zoom):
    	# ...
        size = device_px(float(node.style["font-size"][:-2]), zoom)

    def input(self, node, zoom):
	    # ...
        size = device_px(float(node.style["font-size"][:-2]), zoom)
```
`


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
