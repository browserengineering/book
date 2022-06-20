---
title: Making Content Accessible
chapter: 14
prev: animations
next: skipped
...

It's important for everyone to be able to access content on the web, even if you
have a hard time reading small text, can't or don't want ot use a mouse, are
triggered by very bright colors, or can't see a computer screen at all.
Browsers have features aimed at all of these use cases, taking advantage of the
fact that web pages declare the UI and allow the browser to manipulate it on
behalf of the user.

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

Our browser is currently mouse-only.^[Except for scrolling.] This is
problematic, because there are a number of reasons why users might want to use
the keyboard to interact instead, such as physical inability, injury to the
hand or arm from too much movement, or simply a power user that finds keyboards
more efficient than mice.

Let's add keyboard equivalents to all of the mouse interactions. This includes
browser chrome interactions such as the back button, typing a URL, or quitting
the browser, as well as web page ones such as clicking on buttons, typing
input, and navigating links.

Most of these interactions are built on top of an expanded implementation of
*focus*. We already have a `focus` property on each `Tab` (indicating whether
an `input` element should be capturing keyboard input, and on the `Browser`
to indicate if the browser chrome is doing so instead. Let's expand on that
notion to allow buttons and links to capture input as well. When one of them
is focused and the user presses `enter`, then the button will be clicked
or the link navigated.

``` {.python}
class Browser:
	# ...
    def handle_enter(self):
    	# ...
        elif self.focus == "content":
            active_tab = self.tabs[self.active_tab]
            task = Task(active_tab.enter)
            active_tab.task_runner.schedule_task(task)
        # ...
```

Let's call the act of pressing a button or navigating a link *activating* that
element:

``` {.python}
class Tab:
	# ...
    def activate_element(self, elt):
        if elt.tag == "a" and "href" in elt.attributes:
            url = resolve_url(elt.attributes["href"], self.url)
            self.load(url)
            return None
        elif elt.tag == "button":
            while elt:
                if elt.tag == "form" and "action" in elt.attributes:
                    self.submit_form(elt)
                    return None
                elt = elt.parent
        return elt

    def enter(self):
        if self.focus:
            self.activate_element(self.focus)	
```

With these methods, we can avoid a bit of dulicated code in `click`, which
of course also handles the activation concept (but via the mouse):

``` {.python}
class Tab:
	# ...
	def click(self, x, y):
		 # ...
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "input":
                elt.attributes["value"] = ""
                if elt != self.focus:
                    self.set_needs_render()
                self.focus = elt
                return
            elif not self.activate_element(elt):
                return
            elt = elt.parent
```

Focus is also currently set only via a mouse click, so we need to also introduce
a keyboard way to cycle through all of the focusable elements in the browser.
We'll implement this via the `tab` key:

``` {.python}
    while True:
        if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
        	# ...
            elif event.type == sdl2.SDL_KEYDOWN:
                elif event.key.keysym.sym == sdl2.SDLK_TAB:
                    browser.handle_tab()
```

``` {.python}
class Browser:
	# ...
    def handle_tab(self):
        self.focus = "content"
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.advance_tab)
        active_tab.task_runner.schedule_task(task)
        pass	
```

Each time `tab` is presseed, we'll advance focus to the next thing in order.
This will first require a definition of which elements are focusable:

``` {.python}
    def is_focusable(node):
        return node.tag == "input" or node.tag == "button" \
        	or node.tag == "a"
```

And then each iterating through them. When `tab` is pressed and we're at the
end of the focusable list, focus the addressbar:

``` {.python}
class Tab:
    def advance_tab(self):
        focusable_nodes = [node
            for node in tree_to_list(self.nodes, [])
            if isinstance(node, Element) and Tab.is_focusable(node)]
        if not focusable_nodes:
            self.apply_focus(None)
        elif not self.focus:
            self.apply_focus(focusable_nodes[0])
        else:
            i = focusable_nodes.index(self.focus)
            if i < len(focusable_nodes) - 1:
                self.apply_focus(focusable_nodes[i+1])
            else:
                self.apply_focus(None)
                self.browser.focus_addressbar()
        self.set_needs_render()
```

Setting focus works like this:

``` {.python}
    def apply_focus(self, node):
        if self.focus:
            self.focus.is_focused = None
        self.focus = node
        if node:
            if node.tag == "input":
                node.attributes["value"] = ""
            node.is_focused = True
```

which by the way should also be used from `click`:

``` {.python}
    def click(self, x, y):
        self.render()
        self.apply_focus(None)
```


And `focus_addressbar` is like this:

``` {.python}
class Browser:
	# ...
    def focus_addressbar(self):
        self.lock.acquire(blocking=True)
        self.focus = "address bar"
        self.address_bar = ""
        self.set_needs_raster()
        self.lock.release()
```

There is a third aspect though: if focus is caused by the keyboard, the user
needs to know what actually has focus. This is done with a *focus ring*---a
visual outline around an element that lets the user know what is focused.

We'll do this by painting a `2px` wide black rectangle around the element that
is focused. This requires some code in various `paint` methods plus this
helper:

``` {.python expected=False}
def paint_outline(node, cmds, rect):
    if hasattr(node, "is_focused") and node.is_focused:
        cmds.append(outline_cmd(rect, (2, "black")))
```

which is called in `BlockLayout` (note how it's after painting children, but
before visual effects):

``` {.python}
class BlockLayout:
	# ...
	def paint(self, display_list):
		# ...
        for child in self.children:
            child.paint(cmds)

        paint_outline(self.node, cmds, rect)

        cmds = paint_visual_effects(self.node, cmds, rect)
```

And `InputLayout` is similar:

``` {.python}
class InputLayout:
	# ...
	def paint(self, display_list):
		# ...
        paint_outline(self.node, cmds, rect)

        cmds = paint_visual_effects(self.node, cmds, rect)
```

But for inline layout, the situation is more complicated, for two reasons. The
first is that the painting of each inline element is broken into runs of
text, and can span multiple lines. So it's not even just one rectangle; if an
`<a>` element's anchor text spans multiple lines, we should paint one rectangle
for each text run in each line.

The second complication is that there is not necessarily a layout object
corresponding exactly to an `<a>` element, if there is other text or an
`<input>` on the same line.

We'll solve both of these problems `LineLayout` (recall there is one of these
for each line of an `InlineLayout`), and union the rects of all children
that are for `Text` node child of a focused parent.

``` {.python}
class LineLayout:
	# ...
    def paint(self, display_list):
    	# ...
        focused_node = None
        for child in self.children:
            node = child.node
            if isinstance(node, Text) and is_focused(node.parent):
                focused_node = node.parent
                outline_rect.join(child.rect())
        # ...
        if focused_node:
            paint_outline(focused_node, display_list, outline_rect)

```

Iterating through the focusable elements with the keyboard, and highlighting
them with a focus rect, should now work. Try it in
this [example](examples/example14-focus.html). And if you zoom in enough, you
should be able to make the link cross multiple lines.

In addition to activation of input elements, there are four more mouse controls
in the browser: the back button, the add-tab button, iterating through the
tabs, and the button to quit the browser.^[one-more] Bind them to `ctrl-left`,
`ctrl-t`, `ctrl-tab` (to cycle through tabs) and `ctrl-q`, respectively. The
code to implement these is straightforward, so I've omitted it.

^[one-more]: Actually, there are sometimes more: buttons to minimize or
maximize the browser window. Those require calling specialized OS APIs, so I
won't implement them.

Dark mode
=========

Implement dark mode.

Customizing accessibility features
==================================

1. Outline CSS property
2. tabindex

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
