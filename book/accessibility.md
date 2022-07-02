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

``` {.python}
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
tabs, and the button to quit the browser.[^one-more] Bind them to `ctrl-left`,
`ctrl-t`, `ctrl-tab` and `ctrl-q`, respectively. The code to implement these is
straightforward, so I've omitted it.

[^one-more]: Actually, there are sometimes more: buttons to minimize or
maximize the browser window. Those require calling specialized OS APIs, so I
won't implement them.

::: {.further}

Discuss the opposite of keyboard input: voice input. And how it can be mapped
to these same APIs, via speech-to-text assistants.

:::

Dark mode
=========

Next up is solving the issue of content being too bright for a user. The reasons
why might include extra sensitivity to light, or needing to use a device often
at night (especially in a shared space where others might be disturbed by too
much light). For this, browsers support a *dark mode*---a mode where the
browser---and therefore also web pages---by default have a black background and
a white foreground (as opposed to a white background and black foreground).

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
colors. For example plumb color to the `draw_line` function and pass `color`
as the color for rastering tabs:

``` {python}
def draw_line(canvas, x1, y1, x2, y2, color):
    sk_color = parse_color(color)
    # ...
    paint = skia.Paint(Color=sk_color)

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

Likewise all the rest of the `draw_line`, `draw_text` and `draw_rect` calls
in `raster_chrome` should be instrumented with the dark mode-dependent color.

``` {.python}
class Browser:
    # ...
    def toggle_dark_mode(self):
        # ...
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.toggle_dark_mode)
        active_tab.task_runner.schedule_task(task)
```

The `draw` method technically also needs to clear to a dark mode color
(though this color is generally not available, it's just there to avoid any
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

Dark mode also needs to make tabs dark by default. So first plumb the bit:

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
be overridden by changing `INHERITED_PROPERTIES`:

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
browser style sheet. What we need is to make that style sheet depend on dark
mode.

This won't be *too* hard. One way to do it would be to programmatically modify
styles in `style`. Instead let's just define two browser style sheets,
and load both:^[Yes, this is quite inefficient because the style sheets of the
document are stored twice. See the go-further event at the end of this section.]


``` {.python}
class Tab:
    def __init__(self, browser):
        # ...
        with open("browser14-light.css") as f:
            self.default_light_style_sheet = \
                CSSParser(f.read()).parse()
        with open("browser14-dark.css") as f:
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

``` {.python}
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
Describe media queries and prefers-color-scheme in particular.
:::


Voice navigation
================

Now let's consider a challenge even harder than too-small/too-bright contrent or
keyboard navigation: what if the user can't see the web page at
all? For these users, a whole lot of the work our browser does is about
rendering content visually, which for them is simply not useful at all. So
what do we do instead?

Well, there is still the DOM itself, and that has inherent *semantics* in it.
For example, an `<a>` element has a clear meaning and purpose, irrespedctive
of how it's displayed on the screen. The same goes for `<input` and `<button>`.
And of course the text in the document has meaning even without display.

So what we need to do is bundle up the semantics of the DOM and present them to
the user in some way they can visualize. For a user that can't see the screen,
the simplest approach will be to read the content out loud. This functionality
is called a *screen reader*. Screen readers are in practice generally
[^why-diff] a different application than the browser. But it's actually
not so hard to build one directly *into* our browser, and doing so will give
you a lot of insights into how accessibility actually works in a browser.
So let's do it![^os-pain]

[^why-diff]: I think the reason is mainly historical, in that accessibilty APIs
and screen readers evolved first with operating systems, and before/in paralell
with the development of browsers. These days, though, browsers are by far the
most important app many users interact with (especially on desktop OSes),
so it makes more sense to consier such features core to a browser with each
year that passes

[^os-pain]: Another reason is that it's actually quite a lot of work to
directly integrate a browser with the accessibility APIs of each OS. Further,
it's not very easy to find Python bindings for these APIs, especially Linux.]

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
by `gtts`:

``` {.python}
import gtts
# ...
import os
import playsound
```
Using these librares is very easy. To speak text out loud you just convert it
to an audio file, then play the file:

``` {.python}
SPEECH_FILE = "/tmp/speech-fragment.mp3"

def speak_text(text):
    tts = gtts.gTTS(text)
    tts.save(SPEECH_FILE)
    playsound.playsound(SPEECH_FILE)
    os.remove(SPEECH_FILE)
```

Let's use this to speak to the user the focused element. A new method,
`speak_update`, will check if the focused element changed and say it out loud,
via a `speak_node` method. Saying it out loud will require knowing what text to
say, which will be decided in `announce_text`.

Here is `announce_text`. For text nodes it's just the text, and otherwise it
describes the element tag, plus whether it's focused.

``` {.python}
def announce_text(node):
    if isinstance(node, Text):
        return node.text

    elif node.tag == "input":
        return "Input box"
    elif node.tag == "button":
        return "Button"
    elif node.tag == "a":
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
    def speak_node(self, node):
        text = "Element focused. "
        text = announce_text(node)
        if text and node.children and \
            isinstance(node.children[0], Text):
            text += " " + announce_text(node.children[0])
        print(text)
        if text:
            if not self.browser.is_muted():
                speak_text(text)
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
            self.speak_node(self.focus)
```

The update can then be called after layout is done:

``` {.python expected=False}
class Tab:
    # ...
    def render(self):
        # ...
            self.document.layout(self.zoom)
            self.speak_update()     
```

::: {.further}

Describe connection bewteen blind users and assistant experiences, search engine
crawlers and other machine-reading use cases.

:::

The accessibility tree
======================

Reading out focus is great, but there are a number of other things such users
want to do, such as reading the whole document and interacting with it in
various ways. And the semantics of how this work ends up being a lot like
rendering. For example, DOM nodes that are invisible[^invisible-example] to the
user, or are purely *presentational*[^presentational] in nature, should not be
read out to users, and is not important for interaction.

[^invisible-example]: For example, `opacity:0`. There are several other
ways in real browsers that elements can be made invisible, such as with the
`visibility` or `display` CSS properties.

[^presentational]: A node that is presentational is one whose purpose is only
to create something visual on the screen, and has no semantic meaning to a user
who is not looking at a screen. An example is a `<div>` that is present only
to create space or a background color.

Further, the semantics are sometimes a bit different than layout and paint.
So we'll need to create a new *accessibility* tree in rendering to implement
it. Add a new rendering pipeline phase after layout and before paint to
build this tree.

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

And building it recursively creates the tree. But not all nodes in the
document tree are present in the accessibility tree. For example, a `<div>` by
itself is by default considered presentational or otherwise having no
accessibilty semantics, but `<input>`, `<a>` and `<button` do have semantics.
The semantics are called the *role* of the element---the role it plays in the
meaning of the document.

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
                text += " "  + new_text
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
            self.speak_node(self.focus)
```

Customizing accessibility features
==================================

Our browser now has all these cool features to help accessibility: zoom,
keyboard navigation and dark mode. But what if the website wants to *extend*
that work to new use cases not built into the browser? For example, what if
a web developer wants to add their own different kind of input element, or
a fancier kind of hyperlink? These kinds of *custom widgets* are very common
on the web, in fact much more common than the built-in ones.

You can make a custom widget with event listeners for keyboard and mouse events,
and your own styling and layout. But it immediately loses important features
like becoming focusable, participating in tab index order, and responding to
dark mode. This means that as a site wants to customize the experience to
make it nicer for some users, it becomes worse for others---the ones who
really depend on tab order, dark mode and the accessibility tree.

Let's add features to our browser to allow custom widgets to get back that
functionality, and start with focus and tab order. This is easily solved
with the `tabindex` attribute on HTML elements. When this attribute is present,
the element automatically becomes focusable. The value of this property is
a number, indicating the order of focus. For example, an element with
`tabindex=1` on it will be focused before `tabindex=2`.^[Elements like
input that are by default focusable can have `tabindex` set, but if it isn't
set they will be last in the order after `tabidex` elements.]

First, `is_focusable` needs to be extended accordingly:

``` {.python}
def is_focusable(node):
    return node.tag == "input" or node.tag == "button" \
        or node.tag == "a" or "tabindex" in node.attributes
```

Define a new method to get the tab index. It defaults to 9999999, which is
an approximation to "higher tabindex than anything specified".

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

Next up is customizing the focus rectangle via the `outline` CSS property.
As usual, we'll implement only the subset of it that looks like this:

    outline: 3px solid red;

Which means "make the outline 3px and red". First parse it:

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

And use it, The outline will be present if the element is focused or has
the outline generally.

``` {.python}
def paint_outline(node, cmds, rect):
    outline = parse_outline(node.style.get("outline"))
    if outline:
        cmds.append(outline_cmd(rect, outline))
    elif hasattr(node, "is_focused") and node.is_focused:
        cmds.append(outline_cmd(rect, (2, "black")))
```

Which is a problem. Implement pseudoclass syntax?


TODO: Implement media queries dark mode.


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



Exercises
=========

* Implement `prefers-color-scheme`