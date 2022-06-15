---
title: Making Content Accessible
chapter: 14
prev: animations
next: skipped
...

It's important for everyone to be able to access content on the web, even if you
have a hard time using a mouse, can't read small fonts easily, are triggered by
very bright colors, or can't see a computer screen at all. Browsers have
features aimed at all of these use cases, taking advantage of the fact
that web pages declare the UI and allow the browser to manipulate it on behalf
of the user.

Text zoom
=========

Let's start with the simplest accessibility problem: words on the screen that
are too small to read. In fact, it's also probably the most common as well---
almost all of us will face this problem sooner or later, as our eyes become
weaker with age. There are multiple ways to address this problem, but the
simplest and most effective is simply increasing font sizes. This approach
is called text zoom---like a camera zooming in on a scene. Let's implement it.

ind the `ctrl-plus` keystroke combo to zooming in, `ctrl-minus` to zooming out,
and `ctrl-zero` to reset. A new `zoom` property on `Browser` wll start at `1`.
Zooming in and out will increase or decrease `zoom`. Then we'll use the
multiply the sizes of all of the fonts on the page by `zoom` as well.

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

The `Browser` code just delegates to the `Tab`:

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

which in turn changes `zoom`---let's increase or decrease by a
factor of 1.1, because that looks reasonable on the screen---and re-renders:

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
found, override the font size to account for zoom. To make that easier, add a
helper method that converts from a *layout pixel* (the units specified in a CSS
declaration) to a *device pixel* (what's actually drawn on the screen) by
multiplying by zoom:

``` {.python}
def device_px(layout_px, zoom):
    return layout_px * zoom
```

Finally, there are a bunch of small changes to the `layout` methods. First
`BlockLayout`, `LineLayout` and `DocumentLayout`, which just pass on the zoom
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
plumbing happens:

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
class InlineLayout:
	# ....
    def text(self, node, zoom):
    	# ...
        size = device_px(float(node.style["font-size"][:-2]), zoom)

    def input(self, node, zoom):
	    # ...
        size = device_px(float(node.style["font-size"][:-2]), zoom)
```

`TextLayout` also has some code to edit:

``` {.python}
class TextLayout:
	# ...
    def layout(self, zoom):
    	# ...
        size = device_px(
        	float(self.node.style["font-size"][:-2]), zoom)
```

Now try it out! All of the fonts should be get about 10% bigger each time you
press `ctrl-plus`, and the opposite with `ctrl-minus`. This is great for
reading text more easily.

But you'll quickly notice that there is a big problem with this approach: pretty
soon the text starts overflowing its container, and even worse gets cut off at
the edge of the screen. That's quite bad actually---we traded one accessibility
improvement in one area (you can read the text) for a loss in another(you can't
even see all the text!).

How can we fix this? Well, it turns out we shouldn't just increase the size
of fonts, but *also* the sizes of every other CSS pixel defined in `layout`.
We should essentially run the same layout algorithm we have, but with each
device pixel measurement larger by a a factor of `zoom`. This will automatically
cause inline text and content to wrap when it gets to the edge of the screen,
and not grow beyond.

For example, change `DocumentLayout` to adjust `HSTEP` and `VSTEP`---which are
in CSS pixels---to account for `zoom`:

``` {.python}
class DocumentLayout:
	# ...
    def layout(self, zoom):
    	# ...
        self.width = WIDTH - 2 * device_px(HSTEP, zoom)
        self.x = device_px(HSTEP, zoom)
        self.y = device_px(VSTEP, zoom)
        child.layout(zoom)
        self.height = child.height + 2* device_px(VSTEP, zoom)

```

Likewise, the `width` and `height` CSS properties need to be converted. In this
case, pass `zoom` to style_length as a new parameter for convenience:

``` {.python}
def style_length(node, style_name, default_value, zoom):
    style_val = node.style.get(style_name)
    return device_px(float(style_val[:-2]), zoom) if style_val \
        else default_value
```

Then use it:

``` {.python expected=False}
class BlockLayout:
	# ...
    def layout(self, zoom):
    	# ...
        self.width = style_length(
            self.node, "width", self.parent.width, zoom)
        # ...
        self.height = style_length(
            self.node, "height",
            sum([child.height for child in self.children]), zoom)
```

``` {.python}
class InlineLayout:
	# ...
    def layout(self, zoom):
        self.width = style_length(
            self.node, "width", self.parent.width, zoom)
        # ...
        self.height = style_length(
            self.node, "height",
            sum([line.height for line in self.children]), zoom)
```

``` {.python}
class InputLayout:
	# ...
    def layout(self, zoom):
		# ...
		self.width = style_length(
            self.node, "width", device_px(INPUT_WIDTH_PX, zoom), zoom)
        self.height = style_length(
            self.node, "height", linespace(self.font), zoom)
```

And `InlineLayout` also has a fixed `INPUT_WIDTH_PX` CSS pixels value that needs
to be adjusted:

``` {.python }
class InlineLayout:
	# ...
    def input(self, node, zoom):
        w = device_px(INPUT_WIDTH_PX, zoom)	
```

Now fire up the browser and try to zoom some pages. Everything should layout
quite well!

::: {.further}

TODO: `zoom` css property; device pixel scale and interpreting as zoom.

:::

Keyboard navigation
===================

Implement visual focus rings via the CSS outline property
Define ‘focusable’ elements
Implement the focus pseudoclass
Implement ‘tab’ to rotate among focusable elements
Implement tabindex to control tab order

Implement ‘enter’ to cause a button click.
Implement shortcut to focus the URL bar.
Implement keyboard back-button

Dark mode
=========

Voice navigation
================

Introduce accessibility tech
Implement the accessibility tree
Introduce the concept of implicit accessibility semantics, such as via form controls or links
Integrate with NVDA
Demonstrate how to run the browser and interact with web pages with the same tool

Section 7: aria labels, modifications of the accessibility tree
pIntroduce one or two
Introduce concept of alternate text, with anchor link text as an example
Augment the accessibility tree via them
Implement display: none
Implement inert

OS integrations:
https://www.w3.org/TR/accname-1.2/
https://www.w3.org/TR/core-aam-1.2/
https://www.w3.org/TR/html-aam-1.0/
https://www.w3.org/TR/svg-aam-1.0/

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




Section 6: visual modes for accessibility
Introduce media queries. Example: dark mode
Another example: prefers reduced motion
Third example: color contrast, forced colors mode


Other thoughts:
Introduce the role attribute? (needs a compelling example; maybe explain in the context of aria + the accessibility tree?)
