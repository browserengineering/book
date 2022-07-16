---
title: Making Content Accessible
chapter: 14
prev: animations
next: skipped
...

It's important for everyone to be able to access content on the web, even if you
have a hard time reading small text, can't or don't want to use a mouse, are
triggered by very bright colors, suffer from repetitive stress injury, or can't
see a computer screen at all. Browsers have features aimed at all of these use
cases, taking advantage of the fact that web pages [declare] UI and allow the
browser to manipulate it [on behalf][ua] of the user.[*Accessibility*][a11y] is
the name for the broad class of browser features for these use cases. They are
a critical part of a modern browser, and pretty much everyone benefits from one
or more of them.

[ua]: http://localhost:8001/intro.html#the-role-of-the-browser

[declare]: intro.md#browser-code-concepts

[a11y]: https://developer.mozilla.org/en-US/docs/Learn/Accessibility/What_is_accessibility

CSS zoom
========

Let's start with the simplest accessibility problem: words on the screen that
are too small to read. In fact, it's also probably the most common as
well---almost all of us will face this problem sooner or later, as our eyes
become weaker with age. There are multiple ways to address this problem, but
the simplest and most effective is simply increasing font and element sizes.
This approach is called *CSS zoom*.[^zoom]

[^zoom]: The word zoom evokes an analogy to a camera zooming in, but is not the
same, because CSS zoom causes layout. *Pinch zoom*, on the other hand is just
like a camera and does not cause layout (see the go-further block at the end
of this section).

To implement it, we first need a way to trigger zooming. Let's bind the
`ctrl-plus` keystroke combo to zooming in, `ctrl-minus` to zooming out, and
`ctrl-zero` to reset. A new `zoom` property on `Browser` wll start at `1`.
Zooming in and out will increase or decrease `zoom`. Then we'll multiply all of
the "CSS sizes" on the web page by `zoom` as well.[^browser-chrome]

[^browser-chrome]: This operation does not zoom in the browser chrome UI.
Browsers also have such a feature, and it's usually triggered by a global
OS setting.

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

and then looking for plus, minus or zero pressed next:

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

The `Browser` code just delegates to the `Tab`, via a main thread task:

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

The `Tab` in turn in turn changes `zoom`---let's increase or decrease by a
multiplicative factor of 1.1---and re-renders:

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

The `zoom` factor is supposed to multiply all CSS sizes, so
pass `zoom` down into `layout`:

``` {.python}
class Tab:
	# ...
	def render(self):
			# ...
			self.document.layout(self.zoom)
```

And within each layout class type, pass around `zoom` as well. But what do we do
with it? Let's start by resizing all fonts according to `zoom`.  To make that
easier, add a `device_px` helper method that converts from a *CSS pixel* (the units
specified in a CSS declaration) to a *device pixel* (what's actually drawn on
the screen) by multiplying by zoom.^[There will be a bunch of places to edit,
and this helper method lets us avoid mistakes.]

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

Also adjust the font size in `TextLayout`:

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

But you'll quickly notice that there is a big problem: pretty soon the text
starts overflowing the screen, and if the `width` or `height` CSS properties
are specified, it'll overflow elements as well. That's quite bad---we
traded an accessibility improvement in one area (you can read the text) for a
loss in another (you can't even see all the text!).

How can we fix this? We shouldn't just increase the size of
fonts, but also the size of every other CSS pixel. defined in `layout`. We
should essentially run the same layout algorithm we have, but with each device
pixel measurement larger by a a factor of `zoom`. But since the screen doesn't
magically get bigger when zooming, its width and height will remain fixed in
physical pixel width (and hence smaller in CSS pixels). This
will automatically cause inline text and content to wrap when they hit the
edge of the screen or container elements, and not grow beyond.[^min-font-size]
And the layout design of the website will tend to continue working, because
elements `width` and `height` will get larger in proportion to the font.

[^min-font-size]: Browsers also usually have a *minimum font size* feature. When
it's used, the browser will try to avoid rendering any fonts smaller than the
minimum. However, these features don't automatically use zoom, and therefore
suffer from problems like overflowing fonts and broken layouts. Because of
these problems, browsers also often restrict the feature to situations where
the site seems to be using [relative font sizes][relative-font-size], making
the feature even less useful. CSS zoom is a much better solution.

[relative-font-size]: https://developer.mozilla.org/en-US/docs/Web/CSS/font-size

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

Fire up the browser and try to zoom some pages. Everything should layout
quite well when zoomed, and text will naturally flow into multiple lines
as needed.

::: {.further}

Another way that CSS pixels and device pixels can differ is on a high-resolution
screen. When CSS was first defined, the typical screen had about 96 pixels per
inch of screen. Since then, various devices (the original iPhone was an early
example) have screens with much higher pixel density. This led to a problem
though---web sites displayed on those screens would look tiny if one CSS pixel
mapped to one device pixel. This was solved with the
[`devicePixelRatio`][dpr] concept---each CSS pixel is by default multiplied by
the device pixel ratio to arrive at device pixels. The original iPhone, for
example, had 163 pixels per inch. 163/96 = 1.7, but since a multiplier like
1.7 leads to awkward rounding issues in layout, that device selected a
`devicePixelRatio` of
2.^[Since then, may different screens with different pixel densities have
appeared, and these days it's not uncommon to have a ratio that is not an
integer. For example, the Pixelbook Go I'm using to write this book has a ratio
of 1.25 (but with 166 pixels per inch---As you can see, the choice of ratio
for a given screen is somewhat arbitrary).]

On a device with a `devicePixelRatio` other than 1, `zoom` and
`devicePixelRatio` have to be multiplied together in the rendering code. In
addition, real browsers expose a global variable exposed to JavaScript called
`devicePixelRatio` that equal to the product of these two and updated whenever
the user zooms in or out. In addition, there is a (non-standard, please don't
use it!) [`zoom`][zoom-css] CSS property in WebKit and Chromium browsers that
allows developers to apply something similar to CSS zoom to specific element
subtrees.

[dpr]: https://developer.mozilla.org/en-US/docs/Web/API/Window/devicePixelRatio

[zoom-css]: https://developer.mozilla.org/en-US/docs/Web/CSS/zoom

On devices with touch screens,^[Originally just phones, but now many desktop
computers have touch screens.] many browsers also implement *pinch zoom*:
zooming in on the picture with a multi-touch pinch gesture. This kind of zoom
is just like a CSS scale transform though---it zooms in on the pixels but
doesn't update the main-thread rendering pipeline. The resulting view on the
screen is called the [visual viewport][visual-viewport].

[visual-viewport]: https://developer.mozilla.org/en-US/docs/Web/API/Visual_Viewport_API

:::

Keyboard navigation
===================

Our browser is currently mouse-only.^[Except for scrolling, which is
keyboard-only.] This is problematic, because there are a number of reasons why
users might want to use the keyboard to interact instead. Reasons such as
physical inability, injury to the hand or arm from too much movement, or simply
being a power user that finds keyboards more efficient than mice.

Let's add keyboard equivalents to all of the mouse interactions. This includes
browser chrome interactions such as the back button, typing a URL, or quitting
the browser, as well as web page ones such as clicking on buttons, typing
input, and navigating links.

Most of these interactions will be built on top of an expanded implementation
of *focus*. We already have a `focus` property on each `Tab` indicating whether
an `input` element should be capturing keyboard input, and on the `Browser`
to indicate if the browser chrome is doing so instead. Let's expand on that
notion to allow buttons and links to capture input as well. When one of them
is focused and the user presses `enter`, then the button will be clicked
or the link navigated:

``` {.python}
    while True:
        if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            # ...
                elif event.key.keysym.sym == sdl2.SDLK_RETURN:
                    browser.handle_enter()
```

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
element. The `enter` method activates the currently focused element:

``` {.python}
class Tab:
    # ...
    def enter(self):
        if self.focus:
            self.activate_element(self.focus)   
```

Which performs a behavior depending on what it is:

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
```

With these methods, we can also avoid a bit of dulicated code in `click`, which
of course already handled the activation concept (but via the mouse):

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

Focus is also currently set only via a mouse click, so we also need introduce
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

Each time `tab` is pressed, the browser should advance focus to the next thing
in order. This will first require a definition of which elements are
focusable:

``` {.python expected=False}
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
            if isinstance(node, Element) and is_focusable(node)]
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
            self.focus.is_focused = False
        self.focus = node
        if node:
            if node.tag == "input":
                node.attributes["value"] = ""
            node.is_focused = True
```

Just like activation, this also be used from `click`:

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

Now we have focus implemented on `<a>` and `<button>`, plus a way to cycle
through them with the keyboard. But how do you know which element is currently
focused? There needs to be some kind of visual indication. This is done with
a *focus ring*---a visual outline around an element that lets the user know
what is focused.

Draw the focus ring by painting a `2px` wide black rectangle around the element
that is focused. This requires some code in various `paint` methods plus this
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
first is that the painting of each inline element is potentially broken into
multiple lines of text. So it's not even just one rectangle; if an `<a>`
element's anchor text spans multiple lines, we should paint one rectangle for
each text run in each line.

The second complication is that there is not necessarily a layout object
corresponding exactly to an `<a>` element, if there is other text or an
`<input>` or `<button>` on the same line.

We'll solve both of these problems by painting the focus ring in `LineLayout`
(recall there is one of these for each line of an `InlineLayout`). Each line
will paint a rect that is the union of the rects of all children that are for a
`Text` node child of a focused parent.

``` {.python expected=False}
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
should be able to make the link cross multiple lines and use multiple
focus rectangles.

In addition to activation of input elements, there are four more mouse controls
in the browser: the back button, the add-tab button, iterating through the
tabs, and the button to quit the browser.[^one-more] Bind them to `ctrl-left`,
`ctrl-t`, `ctrl-tab` and `ctrl-q`, respectively. The code to implement these is
straightforward, so I've omitted it.

[^one-more]: Actually, there are sometimes more, depending on the OS you're
working with: buttons to minimize or maximize the browser window. Those require
calling specialized OS APIs, so I won't implement them.

::: {.further}

Keyboards, mice and touch screens are not the only way to interact with a
computer. There is also the possibility of voice input---talking to the
computer. Some operating systems have built-in support for voice commands and
dictation (speaking to type), plus there are software packages you can buy that
do it. These systems generally work very well with a keyboard-enabled
browser, because the voice input software can translate voice commands
directly into simulated keyboard events. This is one more reason that it's
important for browsers and web sites to provide keyboard input alternatives.

:::

Dark mode
=========

Next up is helping users who prefer darker screens. The reasons why might
include extra sensitivity to light, or using a device at night, or at night
near others without disturbing them. For these use cases, browsers these days
support a *dark mode* feature that darkens the browser and web pages,
such as having  a black background and a white foreground (as opposed to the
default white background and black foreground).

We'll bind the `ctrl-d` keystroke to toggle dark mode:

``` {.python}
    while True:
        if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            # ...
                if ctrl_down:
                    # ...
                    elif event.key.keysym.sym == sdl2.SDLK_d:
                        browser.toggle_dark_mode()
```

Which toggles in the browser:

``` {.python}
class Browser:
    # ...
    def __init__(self):
        # ...
        self.dark_mode = False

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
```

To make the browser chrome dark, we just need to flip all the colors in
`raster_chrome`. First set some variables to capture it, and set the canvas
default to `background_color`:

``` {.python}
class Browser:
    # ...
    def raster_chrome(self):
        if self.dark_mode:
            color = "white"
            background_color = "black"
        else:
            color = "black"
            background_color = "white"
        canvas.clear(parse_color(background_color))
```

Then we just need to use `color` or `background_color` in place of all of the
colors. For example, plumb `color` to the `draw_line` function:

``` {python}
def draw_line(canvas, x1, y1, x2, y2, color):
    sk_color = parse_color(color)
    # ...
    paint = skia.Paint(Color=sk_color)
```

And use it there and in `draw_text`:

``` {.python}
class Browser:
    # ...
    def raster_chrome(self):
        # ...

        # Draw the tabs UI:
        tabfont = skia.Font(skia.Typeface('Arial'), 20)
        for i, tab in enumerate(self.tabs):
            name = "Tab {}".format(i)
            x1, x2 = 40 + 80 * i, 120 + 80 * i
            draw_line(canvas, x1, 0, x1, 40, color)
            draw_line(canvas, x2, 0, x2, 40, color)
            draw_text(canvas, x1 + 10, 10, name, tabfont, color)
            if i == self.active_tab:
                draw_line(canvas, 0, 40, x1, 40, color)
                draw_line(canvas, x2, 40, WIDTH, 40, color)
```

Likewise all the rest of the `draw_line`, `draw_text` and `draw_rect` calls in
`raster_chrome` (not all are shown above) should be instrumented with the dark
mode-dependent color.

The `draw` method technically also needs to clear to a dark mode color
(though this color is generally not visible, it's just there to avoid any
accidental transparency in the window).

``` {.python}
class Browser:
    # ...
    def draw(self):
        # ...
        if self.dark_mode:
            canvas.clear(skia.ColorBLACK)
        else:
            canvas.clear(skia.ColorWHITE)
```

Next up is also informing the `Tab` to switch in or out of dark mode:

``` {.python}
class Browser:
    # ...
    def toggle_dark_mode(self):
        # ...
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.toggle_dark_mode)
        active_tab.task_runner.schedule_task(task)
```

And in `Tab`:

``` {.python}
class Tab:
    def __init__(self, browser):
        # ...
        self.dark_mode = browser.dark_mode

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.set_needs_render()
```

Now we need to flip the colors somehow. The easiest to change are the default
text color and background color of the document. The text color can just
be overridden by changing `INHERITED_PROPERTIES` before calling `style`:

``` {.python expected=False}
class Tab:
    # ...
    def render(self):
        # ...
        if self.dark_mode:
            INHERITED_PROPERTIES["color"] = "white"
        else:
            INHERITED_PROPERTIES["color"] = "black"
        style(self.nodes, sorted(
            self.rules, key=cascade_priority), self)
```

And the default background color of the document can be flipped by passing a
new `dark_mode` parameter:

``` {.python}
class Tab:
    # ...
    def render(self):
        self.document.paint(self.display_list, self.dark_mode)
```

``` {.python}
class DocumentLayout:
    # ...
    def paint(self, display_list, dark_mode):
        if dark_mode:
            background_color = "black"
        else:
            background_color = "white"
        display_list.append(
            DrawRect(skia.Rect.MakeLTRB(
                self.x, self.y, self.x + self.width,
                self.y + self.height),
                background_color, background_color))
```

If you load up a page, now you should see white text on a black background.
But if you try [this example](examples/example14-focus.html) it still won't
look very good, because buttons and input elements now have poor contrast
with the white foreground text. Let's fix that. Recall that the `lightblue` and
`orange` colors for `<input>` and `<button>` elements come from the
browser style sheet. We need to to make that style sheet depend on dark
mode.

This won't be *too* hard. One way to do it would be to programmatically modify
styles in `style`. Instead let's just define two browser style sheets,
and load both:^[Yes, this is quite inefficient because the style sheets of the
document are stored twice. We'll optimize it later on.]


``` {.python expected=False}
class Tab:
    def __init__(self, browser):
        # ...
        with open("browser-light.css") as f:
            self.default_light_style_sheet = \
                CSSParser(f.read()).parse()
        with open("browser-dark.css") as f:
            self.default_dark_style_sheet = \
                CSSParser(f.read()).parse()
    # ...
    def load(self, url, body=None):
        # ...
        self.light_rules = self.default_light_style_sheet.copy()
        self.dark_rules = self.default_dark_style_sheet.copy()
        # ...
        for link in links:
            self.light_rules.extend(CSSParser(body).parse())
            self.dark_rules.extend(CSSParser(body).parse())
```

Then we can just use them when calling `style`:

``` {.python expected=False}
class Tab:
    # ...
    def render(self):
        if self.needs_style:
            if self.dark_mode:
                INHERITED_PROPERTIES["color"] = "white"
                style(self.nodes,
                    sorted(self.dark_rules,
                        key=cascade_priority), self)
            else:
                INHERITED_PROPERTIES["color"] = "black"
                style(self.nodes,
                    sorted(self.light_rules,
                        key=cascade_priority), self)
```

::: {.further}

Dark mode is a relatively recent browser feature. In the original design of CSS,
the [cascade](https://developer.mozilla.org/en-US/docs/Web/CSS/Cascade) defined
not just browser and author style sheets, but also [*user*][user-style] style
sheets. These are style sheets defined by the person using the browser, as a
kind of custom theme. Another approach is to add a
[browser extension][extension] (or equivalent browser built-in feature) that
injects additional style sheets applying dark styles.[^no-user-styles]

With one of these mechanisms, users might be able to add their
own dark mode. While it's relatively easy for this to work well overriding the
browser's default style sheet and a few common sites, it's very hard to come up
with styles that work well alongside the style sheets of many sites without
losing readability or failing to provide adequate dark mode stying.

[extension]: https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions
[user-style]: https://developer.mozilla.org/en-US/docs/Web/CSS/Cascade#user_stylesheets
[^no-user-styles]: Most browsers these days don't even support user style
sheets, and instead rely on extensions.

:::


Screen readers
==============

Consider a challenge even more fundamental than too-small/too-bright
content or keyboard navigation: what if the user can't see the web page at
all?^[The original motivation of screen readers was for blind users, but it's
also sometimes useful for situations where the user shouldn't be looking
at the screen, such as driving.]
For these users, a whole lot of the work our browser does to render content
visually is simply not useful at all. So what do we do instead?

Well, there is still the DOM itself, and that has inherent *semantics*
(meaning) in it. For example, an `<a>` element has a clear meaning and purpose,
irrespective of how it's displayed on the screen. The same goes for `<input`
and `<button>`. And of course the text in the document has meaning.

So what we need to do is bundle up the semantics of the DOM and present them to
the user in some way they can access. For a user that can't see the screen,
the simplest approach will be to read the content out loud. This functionality
is called a *screen reader*. Screen readers are typically[^why-diff] a different
application than the browser. But it's actually not so hard to build one
directly into our browser, and doing so will give you a lot of insights into
how accessibility actually works in a browser.
So let's do it![^os-pain] 

[^why-diff]: I think the reason is mainly historical, in that accessibilty APIs
and screen readers evolved first with operating systems, and before/in parallel
with the development of browsers. These days, browsers are by far the
most important app many users interact with (especially on desktop computers),
so it makes more sense to consider such features core to a browser.

[^os-pain]: Another reason is that it's actually quite a lot of work to directly
integrate a browser with the accessibility APIs of each OS. Further, it's not
very easy to find Python bindings for these APIs, especially Linux. And as
you'll see, it really isn't very hard to get the basics working, though a big
reason is that these days there are high-quality text-to-speeh libraries
available for non-commerical use.

The first step is to install something that can read text out loud. For this
we'll use two libraries: one that converts text to audio files, and one that
plays the audio files. For the first we'll use [`gtts`][gtts], a Python library
that wraps the Google [text-to-speech API][tts]. For the latter we'll
use the [`playsound`][playsound] library.

[gtts]: https://pypi.org/project/gTTS/

[tts]: https://cloud.google.com/text-to-speech/docs/apis

[playsound]: https://pypi.org/project/playsound/

First install them:

    pip3 install gtts
    pip3 install playsound

And then import them (we need the `os` module also, for managing files created
by `gtts`):

``` {.python}
import gtts
# ...
import os
import playsound
```
Using these libraries is very easy. To speak text out loud you just convert it
to an audio file, then play the file:

``` {.python}
SPEECH_FILE = "/tmp/speech-fragment.mp3"

def speak_text(text):
    tts = gtts.gTTS(text)
    tts.save(SPEECH_FILE)
    playsound.playsound(SPEECH_FILE)
    os.remove(SPEECH_FILE)
```

Let's use this to speak the focused element to the user. A new method,
`speak_update`, will check if the focused element changed and say it out loud,
via a `speak_node` method. Saying it out loud will require knowing what text to
say, which will be decided in `announce_text`.

Here is `announce_text`. For text nodes it's just the text, and otherwise it
describes the element tag, plus whether it's focused.

``` {.python expected=False}
def announce_text(node):
    role = compute_role(node)
    if role == "StaticText":
        return node.text
    elif role == "focusable text":
        return "focusable text: " + node.text
    elif role == "textbox":
        value = node.attributes["value"] \
            if "value" in node.attributes else ""
        return "Input box: " + value
    elif role == "button":
        return "Button"
    elif role == "link":
        return "Link"
    elif is_focusable(node):
        return "focused element"
    else:
        return None
```

The `speak_node` method calls `announce_text` and also adds in any text
children. It then prints it to the screen (most useful for our own debugging),
and then speaks the text.

``` {.python}
class Tab:
    # ...
    def speak_node(self, node, text):
        text += announce_text(node)
        if text and node.children and \
            isinstance(node.children[0], Text):
            text += " " + announce_text(node.children[0])
        print(text)
        if text:
            if not self.browser.is_muted():
                speak_text(text)

    def speak_focus(self, node):
        self.speak_node(node, "element focused ")
```

And finally there is `speak_update`:

``` {.python}
class Tab:
    def __init__(self, browser):
        # ...
        self.accessibility_focus = None

    def speak_update(self):
        if self.focus and \
            self.focus != self.accessibility_focus:
            self.accessibility_focus = self.focus
            self.speak_focus(self.focus)
```

The `speak_update` method can then be called after layout is done:

``` {.python expected=False}
class Tab:
    # ...
    def render(self):
        # ...
            self.document.layout(self.zoom)
            self.speak_update()     
```

::: {.further}

In addition to speech output, sometimes users prefer output via touch
instead of speech, such as with a [braille display][braille-display]. Making
our browser work with such a device is just a matter of replacing
`speak_text` with the equivalent APIs calls that connect to a braille display
and programming its output.^[I haven't checked in detail, but there may be
easy-to-use Python libraries for it. If you're interested and have a braille
display (or even an emulated one on the computer screen), it would be a fun
project to implement this functionality.]

And of course, the opposite of a braille display is a braille keyboard that
allows typing in a more optimized way than memorizing the locations of each key
on a non-braille keyboard. Or you can buy keyboards with raised braille dots on
each key. Each of these options should work out of the box with our browser,
since these keyboards generate the same OS events as other keyboards.

:::

[braille-display]: https://en.wikipedia.org/wiki/Refreshable_braille_display

The accessibility tree
======================

Reading out focus is great, but there are a number of other things such users
want to do, such as reading the whole document and interacting with it in
various ways. And the semantics of how this works ends up being a lot like
rendering. For example, DOM nodes that are invisible[^invisible-example] to the
user, or are purely *presentational* in nature (i.e only
for the purpose of changing visual apperance[^presentational]) should not be
read out to users, because they are not important.

[^invisible-example]: For example, `opacity:0`. There are several other
ways in real browsers that elements can be made invisible, such as with the
`visibility` or `display` CSS properties.

[^presentational]: A `<div>` element, for example, is by default
presentational (or more precisely, has no semantic role).

First, not everyone wants the accessibility tree to be on, so let's bind it
to the `ctrl-a` keystroke:

``` {.python}
    while True:
        if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            # ...
                if ctrl_down:
                    # ...
                    elif event.key.keysym.sym == sdl2.SDLK_a:
                        browser.toggle_accessibility()            
```

``` {.python}
class Browser:
    def __init__(self):
        self.accessibility_is_on = False

    def toggle_accessibility(self):
        self.accessibility_is_on = not self.accessibility_is_on
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.toggle_accessibility)
        active_tab.task_runner.schedule_task(task)
```

``` {.python}
class Tab:
    def __init__(self, browser):
        self.accessibility_is_on = False
    # ...

    def toggle_accessibility(self):
        self.accessibility_is_on = not self.accessibility_is_on
        self.set_needs_render()
```

Further, the semantics are sometimes a bit different than layout and paint. So
instead of shoehorning something into the layout tree or the DOM, we'll need to
create a new [*accessibility tree*][at] in rendering to implement it. Add a new
rendering pipeline phase after layout and before paint to build this tree.

[at]: https://developer.mozilla.org/en-US/docs/Glossary/Accessibility_tree

``` {.python expected=False}
class Tab:
    def __init__(self, browser):
        # ...
        self.accessibility_tree = None

    def render(self):
        # ...
        if self.needs_layout:
            self.document = DocumentLayout(self.nodes)
            self.document.layout(self.zoom)
            if self.accessibility_is_on:
                self.needs_accessibility = True
            else:
                self.needs_paint = True
            self.needs_layout = False

        if self.needs_accessibility:
            self.accessibility_tree = AccessibilityNode(self.nodes)
            self.accessibility_tree.build()
            self.needs_accessibility = False
            self.needs_paint = True
            self.speak_task()
```

The `build` method on `AccessibilityNode` recursively creates the tree. Whether
a node is represented in the accessibilty tree depends on its tag and style,
which in turn determine not only whether the element is presentational, but if
not what its semantics are. For example, a `<div>` by itself is by default
considered presentational or otherwise having no accessibilty semantics, but
`<input>`, `<a>` and `<button>` have them by default. The semantics are called
the *role* of the element---the role it plays in the meaning of the document.
And these roles arenot arbitrary text; they are specified in a
[standard][aria-roles] just like rendering.[^not-exposed]

[^not-exposed]: However, the role computed by the browser is not exposed to
any JavaScript API.

[aria-roles]: https://www.w3.org/TR/wai-aria-1.2/#introroles

``` {.python}
def compute_role(node):
    if isinstance(node, Text):
        if node.parent.tag == "a":
            return "link"
        elif is_focusable(node.parent):
            return "focusable text"
        else:
            return "StaticText"
    else:
        if node.tag == "a":
            return "link"
        elif node.tag == "input":
            return "textbox"
        elif node.tag == "button":
            return "button"
        elif node.tag == "html":
            return "document"
        elif is_focusable(node):
            return "focusable"
        else:
            return "none"
```

An `AccessibilityNode` forms a tree just like the other ones:

``` {.python}
class AccessibilityNode:
    def __init__(self, node):
        self.node = node
        self.previous = None
        self.children = []

    def __repr__(self):
        return "AccessibilityNode(node={} role={}".format(
            str(self.node), compute_role(self.node))        
```

Building the tree requires recursingly walking the document tree and adding
nodes if their role is not `None`:

``` {.python}
    def build(self):
        for child_node in self.node.children:
            AccessibilityNode.build_internal(child_node, self)
        pass

    def build_internal(node, parent):
        role = compute_role(node)
        if role != "none":
            child = AccessibilityNode(node)
            parent.children.append(child)
            parent = child
        for child_node in node.children:
            AccessibilityNode.build_internal(child_node, parent)
```

Let's now use this code to speak the whole document once after it's been loaded:

``` {.python}
class Tab:
    def __init__(self, browser):
        # ...
        self.has_spoken_document = False

    # ...
    def speak_document(self):
        text = "Here are the document contents: "
        tree_list = tree_to_list(self.accessibility_tree, [])
        for accessibility_node in tree_list:
            new_text = announce_text(accessibility_node.node)
            if new_text:
                text += "\n"  + new_text
        print(text)
        if not self.browser.is_muted():
            speak_text(text)

    def speak_update(self):
        if not self.has_spoken_document:
            self.speak_document()
            self.has_spoken_document = True

        if self.focus and \
            self.focus != self.accessibility_focus:
            self.accessibility_focus = self.focus
            self.speak_focus(self.focus)
```

The accessiblity tree also needs access to geometry of each object. This allows
accessibility technology to know where things are on the screen in case
the user wants to [hit test][hit-test] a place on the screen to see what is
there. A user who can't see the screen still might want to do things like
touch exploration of the screen, or being notified what is under the mouse
as they move it around.

To get access to the geometry, let's add a `layout_object` pointer to each
`Node` object if it has one. That's easy to do in the constructor of each layout
object type. Here are two examples (don't forget to handle all of them):

``` {.python}
class DocumentLayout:
    def __init__(self, node):
        # ...
        node.layout_object = self
```

``` {.python}
class BlockLayout:
    def __init__(self, node, parent, previous):
        # ...
        node.layout_object = self
```

[hit-test]: https://chromium.googlesource.com/chromium/src/+/HEAD/docs/accessibility/browser/how_a11y_works_3.md#Hit-testing

Let's implement the second use case I mentioned above (being notified what
is under the mouse). We'll store the size and location of
each `AccessibilityNode`, and the hit testing algorithm will be exactly the
same as we've already implemented when handling mouse clicks (except on 
a different tree, of course).

First we need to listen for mouse move events:

``` {.python}

    while True:
        if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            # ...
            elif event.type == sdl2.SDL_MOUSEMOTION:
                browser.handle_hover(event.motion)
```

In `Browser`:

``` {.python}
class Browser:
    # ...
    def handle_hover(self, event):
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.hover, event.x, event.y - CHROME_PX)
        active_tab.task_runner.schedule_task(task)
```

Now the tab should listen to the hovered position, determine if it's over an
accessibility node, and higlight that node. But as I explained in
[chapter 11][forced-layout-hit-test], a hit test is one way that forced layouts
can occur. So we could first call `render` inside `hover` before running the
hit test. And this is exactly what `click` does. But there is something
different about hover: when a click happens, the tab needs[^why-needs] to
respond synchronously to it. But a hover is arguably much less urgent than a
click, and so the hit test can be delayed until after the next time the
rendering pipeline runs. By delaying it, we can avoid any forced renders for
hit testing.

[forced-layout-hit-test]: https://browser.engineering/scheduling.html#threaded-style-and-layout

[^why-needs]: It may not be immediately obvious why clicks can't be
asynchronous and happen after a scheduled render. If all that was happening
was browser clicks, and the browser was always responsive and fast, then
maybe that's a good idea. But the browser can't always guarantee that
scripts or other work won't slow down the page, and it's quite important to
respond quickly clicks because the user is waiting on the result.

So `hover` should just note down that a hover is desired, and schedule a render:

``` {.python}
class Tab:
    # ...
    def hover(self, x, y):
        self.pending_hover = (x, y)
        self.set_needs_render()
```

Then, after the accessibility tree is built, process the pending hover:

``` {.python}
class Tab:
    def __init__(self, browser):
        # ...
        self.pending_hover = None
        self.hovered_node = None

        if self.pending_hover:
            if self.accessibility_tree:
                (x, y) = self.pending_hover
                a11y_node = self.accessibility_tree.hit_test(x, y)
                if self.hovered_node:
                    self.hovered_node.is_hovered = False

                if a11y_node:
                    if a11y_node.node != self.hovered_node:
                        self.speak_hit_test(a11y_node.node)
                    self.hovered_node = a11y_node.node
            self.pending_hover = None
```

The last bit is implementing `hit_test` on `AccessibilityNode`. It's
basically the same as regular hit testing:

``` {.python}
class AccessibilityNode:
    # ...
    def hit_test(self, x, y):
        nodes = [node for node in tree_to_list(self, [])
                if node.intersects(x, y)]
        if not nodes:
            return None
        else:
            node = nodes[-1] 
            if isinstance(node, Text):
                return node.parent
            else:
                return node
```

::: {.further}

The accessiblity tree typically plays a key role in the interface between
browsers and accessibility technology like screen readers. The screen reader
registers itself with accessibility OS APIs that promise to call it when
interaction events happen, and the browser does the same on the other end.
Users can express intent by interacting with the accessibility tech, and
then this is forwarded on by way of the OS to an event triggered on the
corresponding accessibility object in the tree.

Generally speaking, the OS does not enforce that the browser build such a tree,
but it's convenient enough that browsers generally do it. However, in the era of
multi-process browser engines (of which [Chromium][chrome-mp] was the first), an
accessibility tree in the browser process that mirrors content state from each
visible browser tab hash become necessary. That's because OS accessibility
APIs are generally synchronous, and it's not possible to synchronously stop
the browser and tab at the same time to figure out how to respond. See
[here][chrome-mp-a11y] for a more
detailed description of the challenge and how Chromium deals with it.

[chrome-mp]: https://www.chromium.org/developers/design-documents/multi-process-architecture/

[chrome-mp-a11y]: https://chromium.googlesource.com/chromium/src/+/HEAD/docs/accessibility/browser/how_a11y_works_2.md

In addition, defining this tree in a specification is a means to encourage
interoperability between browsers. This is critically important---imagine
how frustrating it would be if a web site doesn't work in your chosen browser
just because it happens to interpret accessibility slightly differently than
another one! This is made worse since web sites unfortunately vary greatly
in accessibility quality, and so a user might be forced to constantly
switch browsers in the hope of finding one that works well. Interoperability
is also important for web site authors who would otherwise have to constantly
test everything in every browser.

:::

Tab-index
=========

Our browser now has all these cool features to help accessibility: zoom,
keyboard navigation and dark mode. But what if the website wants to *extend*
that work to new use cases not built into the browser? For example, what if
a web developer wants to add their own different kind of input element, or
a fancier kind of hyperlink? These kinds of *custom widgets* are very common
on the web---in fact much more common than the built-in ones, because they
look nicer and have extra features.

You can make a custom widget with event listeners for keyboard and mouse events,
and your own styling and layout. But it immediately loses important features
like becoming focusable, participating in tab index order, responding to
dark mode, and expressing semantics. This means that as a site wants to
customize the experience to make it nicer for some users, it becomes worse for
others---the ones who really depend on these accessibility features.

Let's add features to our browser to allow custom widgets to get back that
functionality, and start with focus and tab order. This is easily solved
with the `tabindex` attribute on HTML elements. When this attribute is present,
the element automatically becomes focusable. The value of this property is
a number, indicating the order of focus. For example, an element with
`tabindex=1` on it will be focused before `tabindex=2`.^[Elements like
input that are by default focusable can have `tabindex` set, but if it isn't
set they will be last in the order after `tabidex` elements, and will be
ordered according to to their position in the DOM.]

First, `is_focusable` needs to be extended accordingly:

``` {.python}
def is_focusable(node):
    return node.tag == "input" or node.tag == "button" \
        or node.tag == "a" or "tabindex" in node.attributes
```

Define a new method to get the tab index. It defaults to a very large number,
which is an approximation to "higher `tabindex` than anything specified".

``` {.python}
class Tab:
    # ...
    def get_tabindex(node):
        return int(node.attributes.get("tabindex", 9999999))
```

Then it can be used in the sorting order for `advance_tab`:

``` {.python}
class Tab:
    def advance_tab(self):
        focusable_nodes = [node
            for node in tree_to_list(self.nodes, [])
            if isinstance(node, Element) and is_focusable(node)]
        focusable_nodes.sort(key=Tab.get_tabindex)
        # ...
```

That's it! Now tabindex works. Tabbing through the
[focus example](examples/example14-focus.html) should now
change its order according to the `tabindex` attributes in it.

Outline
=======

Next up is customizing the focus rectangle via the [`outline`][outline] CSS
property. As usual, we'll implement only a subset of the full definition; in
particular, syntax that looks like this:

[outline]: https://developer.mozilla.org/en-US/docs/Web/CSS/outline

    outline: 3px solid red;

Which means "make the outline red 3px thick". First parse it:

``` {.python}
def parse_outline(outline_str):
    if not outline_str:
        return None
    values = outline_str.split(" ")
    if len(values) != 3:
        return None
    if values[1] != "solid":
        return None
    return (int(values[0][:-2]), values[2])
```

Now to use it. The outline will be present if the element is focused or has the
`outline` CSS property generally. While we could finish implementing that via
some extra logic in `paint_outline`, the feature has a fundamental problem that
has to be fixed. Specifying an outline is a fine feature to offer to web
developers, but it doesn't actually solve the problem of customizing the focus
outline. That's because `outline`, if specified by the developer,
would *always* apply, but instead we want it to only apply to an element when
it's focused!

To do this we need some way to let developers
express *outline-only-while-focused* in CSS. This is done with a
[*pseudo-class*][pseudoclass], which is a way to target internal state of the
browser (in this case internal state of a specific element).
[^why-pseudoclass] Pseudo-classes are notated with a suffix applied to a tag or
other selector, separated by a single colon character. For the case of focus,
the syntax looks like this:

    div:focus { outline: 2px solid black; }

[pseudoclass]: https://developer.mozilla.org/en-US/docs/Web/CSS/Pseudo-classes

[^why-pseudoclass]: It's called a pseudo-class because it's similar to how a
developoer would indicate a [class] attribute on an element for the purpose
of targeting special elements with different styles. It's "pseudo" because
there is no actual class attribute set on the element while it's focused.

[class]: https://developer.mozilla.org/en-US/docs/Web/CSS/Class_selectors

Let's implement the `focus` pseuo-class. Then we can change focus outlines to
use a browser style sheet with `:focus` instead of special code in
`paint_outline`. The style sheet lines will look like this:

``` {.css}
input:focus { outline: 2px solid black; }

button:focus { outline: 2px solid black; }

div:focus { outline: 2px solid black; }
```

And then we can change `paint_outline` to just look at the `outline` CSS
property:

``` {.python}
def paint_outline(node, cmds, rect):
    outline = parse_outline(node.style.get("outline"))
    if outline:
        cmds.append(outline_cmd(rect, outline))
```

``` {.python expected=False}
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

Now for adding support for `:focus`. The first step will be teaching
`CSSParser` how to parse it.  Let's start by providing a way to mark a
`TagSelector` as needing a pseudoclass to also be set in order to apply:

``` {.python}
class TagSelector:
    def __init__(self, tag):
        # ...
        self.pseudoclass = None

    def set_pseudoclass(self, pseudoclass):
        self.pseudoclass = pseudoclass

    def matches(self, node):
        tag_match = isinstance(node, Element) and self.tag == node.tag
        if not tag_match: return False
        if not self.pseudoclass: return True
        if self.pseudoclass == "focus":
            return is_focused(node)

    def __repr__(self):
        return ("TagSelector(tag={}, priority={} " +
            "pseudoclass={})").format(
            self.tag, self.priority, self.pseudoclass)
```

In `CSSParser`, we first need to write a method that consumes a pseudoclass
string if the `:` separator was found:

``` {.python expected=False}
class CSSParser:
    def try_pseudoclass(self):
        if self.i == len(self.s):
            return None
        if self.s[self.i] != ":":
            return None
        self.i += 1
        return self.word().lower()
```

And then call it in `selector`:

``` {.python expected=False}
class CSSParser:
    def selector(self):
        out = TagSelector(self.word().lower())
        out.set_pseudoclass(self.try_pseudoclass())
        # ...
        while self.i < len(self.s) and self.s[self.i] != "{":
            descendant = TagSelector(self.word().lower())
            descendant.set_pseudoclass(self.try_pseudoclass())
            # ...
```

And that's it! Elegant, right?

::: {.further}

In addition to focus rings being present for focus, another very important part
of accessibility is ensuring *contrast*. I alluded to it in the section on dark
mode, in the context of ensuring that the dark mode style sheet provides good
default contrast. But in fact, the focus ring we've implemented here does not
necessarily have great contrast, for example if it's next to an element with a
black background provided in a page style sheet. This is not too hard to
fix, and there is an exercise at the end of this chapter about it.

Contrast is one part of the [Web Content Accessibility Guidelines][wcag], a
standard set of recommendations to page authors on how to ensure accessibility.
The browser can do a lot, but ultimately things like
[good contrast][contrast] between colors is something that page authors also
have to pay attention to.


[wcag]: https://www.w3.org/WAI/standards-guidelines/wcag/
[contrast]: https://www.w3.org/TR/WCAG21/#contrast-minimum

:::

Hover CSS
=========

Let's come back to the mouse-hover-for-accessibility use case. Our browser
can read the hovered element to the user, but it'd be even better to
highlight it visually, in a way similar to focus outlines. Let's implement
that with a new pseudo-class for accessibility highlighting.

However, in this case it's not so clear that it's a good idea to expose this
pseudo-class to scripts as well. After all, it's really important that
accessibility features actually help users access a web page---more
important, in fact, than the ability of web developers to style it.

Nevertheless, it would be super convenient to re-use the pseudo-class machinery
we just built. Browsers achieve this with *browser-internal*
pseudo-classes---ones that can only be used from with the default
browser style sheet. In this case we'll define a new 
`-internal-accessibility-hover` pseudo-class, and put rules like this in
`browser.css`:

``` {.css}
input:-internal-accessibility-hover {
    outline: 4px solid red;
}
```

Making it work is very easy, just set `is_hovered` on the right node:

``` {.python}
class Tab:
    # ...
    def render(self):
        # ...
                a11y_node = self.accessibility_tree.hit_test(x, y)
                if self.hovered_node:
                    self.hovered_node.is_hovered = False
                if a11y_node:
                    # ...
                    self.hovered_node.is_hovered = True
```

And match it in `TagSelector`:

``` {.python}
INTERNAL_ACCESSIBILITY_HOVER = "-internal-accessibility-hover"
# ...
class TagSelector:
    # ...
    def matches(self, node):
        # ...
        elif self.pseudoclass == INTERNAL_ACCESSIBILITY_HOVER:
            return hasattr(node, "is_hovered") and node.is_hovered
```

The only step remaining is to restrict to the browser style sheet. That
requires passing around an `is_internal` flag in `CSSParser`. If it's not
true then internal pseudo-classes are ignored:

``` {.python}
class CSSParser:
    # ...
    def try_pseudoclass(self, is_internal):
        # ...
        word = self.word().lower()
        if word == INTERNAL_ACCESSIBILITY_HOVER and not is_internal:
            return "IGNORED"
        else:
            return word

    def selector(self, is_internal):
        # ...
        out.set_pseudoclass(self.try_pseudoclass(is_internal))
        # ...
            descendant.set_pseudoclass(
                self.try_pseudoclass(is_internal))

    def parse(self, is_internal=False):
        # ...
                selector = self.selector(is_internal)
```

And then parsing the browser style sheet:

``` {.python}
class Tab:
    def __init__(self, browser):
        # ...
        with open("browser14.css") as f:
            self.default_style_sheet = \
                CSSParser(f.read()).parse(is_internal=True)
```


::: {.further}

Browsers have a number of internal pseudo-classes and other CSS features to
ease their implementation. For example, check out the
[internal features][internal-chromium] in Chromium's HTML style sheet
(everything with the `-internal` prefix).[^vendor-prefix]

[internal-chromium]: https://source.chromium.org/chromium/chromium/src/+/main:third_party/blink/renderer/core/html/resources/html.css

[^vendor-prefix]: You'll also see various features in there that start with
`-webkit`. These are not internal, but instead
[vendor-specific prefixes][vendor-prefix]. A
decade or so ago, browsers shipped "experimental" features based on these
prefixes with the intention of standardizing them later. However,
everyone eventually decided this was a bad idea, because once web sites
start depending on a feature, even if it's "experimental", you can't remove
it from browsers or it will break the web. Even worse, browsers that never
shipped such a feature might be forced to ship it for compatibility reasons.

These features are also sometimes a way to *incubate* new web platform features.
For example, because it's convenient, browsers sometimes use CSS to style their
own browser chrome UI, and at times the needs of the UI exceed what is
expressible in a web page, but could be solved with a simple CSS
extension.^[Browser-internal accessibility state is a good example.]
But in some of these cases, it may make sense to later on expose the CSS
feature to developers, and trying it out on internal UI can inform the
motivation and design of a corresponding new standardized feature. (Plus,
knowing that it was implemented by a browser is a good sign that it's not
*too* hard to do it.)

[vendor-prefix]: https://developer.mozilla.org/en-US/docs/Glossary/Vendor_Prefix

:::

Color scheme
============

Dark mode has a similar problem to focus: when it's on, a web developer will
want to adjust all of the styles of their page, not just the ones provided by
the browser.^[But they'll also want to be able to customize those built-ins!]
Now dark mode is a browser state just like focus, so it would technically be
possible to introduce a pseudo-class for it. But since dark mode is a global
state that applies to all elements, and it's unlikely to change often, the
pseudo-class syntax is too repetitive and clunky. 

So instead, dark mode uses a [*media query*][mediaquery] syntax. This a lot like
wrapping some lines of CSS in an if statement. This syntax will make a `<div>`
tag have a white text color only in dark mode:


``` {.css expected=False}
    @media (prefers-color-scheme:dark) {
    div { color: white; }
    }
```

And just like `:focus`, once we've implemented a dark mode media query, we can
specify dark colors directly in the browser style sheet:

``` {.css}
@media (prefers-color-scheme: dark) {

a { color: lightblue; }
input { background-color: blue; }
button { background-color: orangered; }

input:focus { outline: 2px solid white; }

button:focus { outline: 2px solid white; }

div:focus { outline: 2px solid white; }

a:focus { outline: 2px solid white; }

}
```

This also lets us get rid of the second style sheet
(`default_dark_style_sheet`); instead there can just be a single default style
sheet on a `Tab` object, just like before this chapter (but with the additional
rules listed above).

Parsing requires looking for media query syntax:

``` {.python}
class CSSParser:
    def try_media_query(self):
        if self.i == len(self.s):
            return

        if self.s[self.i] == "@":
            self.literal("@")
            media = self.word()
            assert media == "media"
            self.whitespace()
            self.literal("(")
            (prop, val) = self.pair(")")
            assert prop == "prefers-color-scheme"
            assert val == "dark" or val == "light"
            self.whitespace()
            self.literal(")")
            self.whitespace()
            self.literal("{")
            self.preferred_color_scheme = val
            return True

    def try_end_media_query(self):
        if self.i == len(self.s):
            return

        if not self.preferred_color_scheme:
            return
        if self.s[self.i] == "}":
            self.literal("}")
            self.preferred_color_scheme = None
            return True
```

Here I made a modification to `pair` to accept an end character other than
a semicolon:

``` {.python}
class CSSParser:
    def pair(self, end_char):
        prop = self.word()
        self.whitespace()
        self.literal(":")
        self.whitespace()
        val = self.until_char(end_char)
        return prop.lower(), val

    def body(self):
        # ...
                prop, val = self.pair(";")            
```

And then looking for it in each loop of `parse`:

``` {.python expected=False}
class CSSParser:
    def parse(self):
        # ...
        while self.i < len(self.s):
            try:
                self.whitespace()
                if self.try_media_query(): continue
                if self.try_end_media_query(): continue
                # ...
                rules.append(
                    (selector, body, self.preferred_color_scheme))
```

The `style` method also needs to understand dark mode rules:

``` {.python}
def style(node, rules, tab):
    # ...
    for selector, body, preferred_color_scheme in rules:
        if preferred_color_scheme:
            if (preferred_color_scheme == "dark") != \
                tab.dark_mode: continue
        # ...
```

[mediaquery]: https://developer.mozilla.org/en-US/docs/Web/CSS/Media_Queries/Using_media_queries


::: {.further}

Fully customizable dark mode requires several additional features beyond
`prefers-color-scheme`. The most important is that web sites need a way
to declare whether they support dark mode or not (if they don't, the
browser should really not be flipping the colors on that page, because it'll
likely have terrible accessibility outcomes!) This feature is achieved with
the `color-scheme` [`meta` tag][meta-tag], and allows the web page to declare
whether it supports light mode, dark mode, or both.

[meta-tag]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/meta/name

The second is the [`color-scheme`][color-scheme] CSS, indicating whether that
element and its subtree support dark, light or both modes. (And with the `only`
keyword, whether it should be forced into the ones indicated.)


[color-scheme]: https://developer.mozilla.org/en-US/docs/Web/CSS/color-scheme
:::

ARIA
====

The accessibility tree can also be customized. For one thing, various CSS
properties influence whether elements are in the accessibility tree at all. For
example, making elements invisible^[Via `display:none` or `visibility:hidden`,
for example.] causes them to lose their accessibility tree node. But there
what about changing the role of an element? For example, tab-index allows a
`<div>` to participage in focus, but can it also be made to behave like an
input element? That's what the [`role`][role] attribute is for: overriding the 
semantic role of an element from its default.

This markup gives a `<div>` a role of [`textbox`][textbox-role]:

    <div role=textbox>contents</div>

Its role  in the accessibility tree now becomes equivalent to an `<input>`
element. The first text child is also reused as the *value* of the input field
(a representation of what the user has typed), and pressing `<enter>` submits
any containing `<form>` element. But more importantly, the element is
advertised to users of accessibility features as an textbox. For example, when
the element is read to a person using a screen reader, it is identified as a
textbox, and the user is therefore encouraged to treat it as such---expecting
to have all the usual behaviors of an `<input>` element.

However, the `role` CSS property does not affect the element in any other way.
in particular:

* It is not by default focusable.
* Keyboard events do not modify the text child.
* Visual rendering is unchanged from a regular `<div>`.

That means that the web page is now responsible for implementing all of this
correctly, and providing all the right keyboard event handlers via JavaScript
that the user expects. And if the page doesn't do it, the user is left
confused and sad. That's why it's better for a web page author to simply
[use `<input>` elements when possible][use-input]---it's all too easy to
accidentally forget to implement something important for those users.

[use-input]: https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Roles/textbox_role

But the `role` attribute exists nevertheless, as a way for a page author to not
lose accessibility when building custom widgets. Implementing the `role`
attribute is very easy, so let's do that for the `textbox` roles. It's as
simple as modifying `compute_role`:

``` {.python}
def compute_role(node):
    # ...
        elif "role" in node.attributes:
            return node.attributes["role"]
```
And then a small modification to `announce_text` to get the text contents
from the child text node:

``` {.python}
def announce_text(node):
    # ...
    elif role == "textbox":
        if "value" in node.attributes:
            value = node.attributes["value"]
        elif node.tag != "input" and node.children and \
            isinstance(node.children[0], Text):
            value = node.children[0].text
        else:
            value = ""
        return "Input box: " + value
```


[role]: https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Roles
[textbox-role]: https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Roles/textbox_role

::: {.further}

https://www.w3.org/TR/accname-1.2/
https://www.w3.org/TR/core-aam-1.2/
https://www.w3.org/TR/html-aam-1.0/
https://www.w3.org/TR/svg-aam-1.0/


:::

Summary
=======

This chapter introduces accessibility---features to ensure *all* users can
access and interact with web sites---then showed how to solve several of
the most common accessibility problems in browsers. The key takeaways are:

* Built-in accessibility is possible because of the semantic and deeclarative
nature of HTML.

* Accessibility features are a natural extension to the technology we've already
introduced in earlier chapters.

* It's important to design additional browser features so that page authors
can customize their widgets without losing accessibility.

Outline
=======

The complete set of functions, classes, and methods in our browser 
should now look something like this:

::: {.cmd .python .outline html=True}
    python3 infra/outlines.py --html src/lab14.py
:::

Exercises
=========

* *Focus ring with good contrast*: Add a second white color to the outside of
the 2px black one, and likewise on the inside, to ensure that there is contrast
between the focus ring and surrounding content.

* *Button role*: Add support for the `button` value of the `role` attribute.

* *Visited links*: Implement the [`:visited`][visited] pseudo-class. This
shows `<a>` links pointing to destination URLs have been loaded in the past
by the user in a different color.

[visited]: https://developer.mozilla.org/en-US/docs/Web/CSS/:visited

* *High-contrast mode*: Implement high-contrast [forced-colors] mode. As part
of this, draw a rectangular *backplate* behind all lines of text in order to
ensure that there is sufficientcontrast (as [defined][contrast] by the WCAG
specification) between  foreground and background colors. Also check the
contrast of the default style sheets I provied in this chapter---do they meet
the requirements?

[forced-colors]: https://developer.mozilla.org/en-US/docs/Web/CSS/@media/forced-colors

* *Custom inputs*: Implement an `<input>` element with a `<div>` completely in
JavaScript. Make sure that it's represented correctly in the accessibility tree
and participates correctly in form submission.

* *Threaded accessibility*: The accessibility code currently speaks on the
main thread, which creates a lot of slowdown because the playback doesn't
happen in parallel with other work. Solve this by adding a new accessibility
thread that is in charge of speaking the document. (You don't want to use
the compositor thread, because then that thread will become slow also.) To
achieve this you will need to copy the accessibility tree from one thread
to another.

* *Highlighting elements during read*: The method to read the document works,
but it'd be nice to also highlight the elements being read as it happens,
in a similar way to how we did it for mouse hover. Implement that.

* *`:hover` pseudoclass*: There is in fact a pseudoclass for generic mouse
[hover][hover-pseudo] events (it's unrelated to accessibility). It works the
same way as `-internal-accessibility-hover ` but hit tests the layout tree
instead. Implement it.

[hover-pseudo]: https://developer.mozilla.org/en-US/docs/Web/CSS/:hover

* *Find-in-page*: Yet another accessibility feature is searching for
text within a web page. Implement this feature. A simple approach might be to
binding it to `ctrl-f` and then interpreting subsequent keyboard input
as the text to search for, and ended by pressing `esc`. Add an internal
pseudo-class for the selected element. You don't need
to implement matching text across multiple `InlineLayout` elements (in general,
find-in-page and other [selection] APIs are quite complicated.

[selection]: https://developer.mozilla.org/en-US/docs/Web/API/Selection
