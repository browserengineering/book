---
title: Making Content Accessible
chapter: 14
prev: animations
next: embeds
...

So far, we've focused on making the browser an effective platform for
developing web applications. But ultimately, the browser is a [_user_
agent][ua]. That means it should assist the user in whatever way it
can to access and use web applications. Browsers therefore offer a
range of [*accessibility*][a11y] features that take advantage of
[declarative] UI and the flexibility of HTML and CSS to make it
possible to interact with the web page by touch, keyboard, or voice.

[ua]: intro.md#the-role-of-the-browser

[declarative]: intro.md#browser-code-concepts

[a11y]: https://developer.mozilla.org/en-US/docs/Learn/Accessibility/What_is_accessibility

What is accessibility?
======================

Accessibility means that the user can change or customize how they
interact with a web page in order to make it easier to
use.[^other-defs][^not-just-screen-reader] The web's uniquely-flexible
core technologies mean that browsers offer a lot of accessibility
features[^not-just-screen-reader] to allow a user to customize the
style, layout, and rendering of a web page, as well as interact with a
web page with their keyboard, by voice, or using some kind of helper
software.

[^other-defs]: Accessibility can also be defined from the developer's
    point of view, [in which case][mdn-def] it's something like: the
    ways you can make your web pages easy to use for as many people as
    possible.

[mdn-def]: https://developer.mozilla.org/en-US/docs/Learn/Accessibility/What_is_accessibility

[^not-just-screen-reader]: Too often, people take "accessibility" to
    mean "screen reader support", but this is just one way a user may
    want to interact with a web page.

The reasons for customizing, of course, are as diverse as the
customizations themselves. For example, when my son was born,[^pavel]
my wife and I alternated time taking care of the baby and I ended up
spending a lot of time working at night. To maximize precious sleep,
I wanted the screen to be less bright, and was thankful that many
websites offer a dark mode. Later, I found that taking notes by
voice was convenient when my hands were busy holding the baby. And
when I was trying to put the baby to sleep, muting the TV and reading
the closed captions turned out to be the best way of watching movies.

[^pavel]: This is Pavel speaking.

The underlying reasons for using these accessibility tools were
temporary; but other uses may last longer, or be permanent. I'm
ever-grateful, for example, for [curb cuts][curb-cut], which make it
much more convenient to go on walks with a stroller, something I'll be
doing for years to come.[^toddler-curb-cut] And there's a good chance
that, like many of my relatives, my eyesight will worsen as I age and
I'll need to set my computer to a permanently larger text size. For
more severe and permanent disabilities, there are advanced tools like
[screen readers][screen-reader].[^for-now] These take time to learn
and use effectively, but are transformative for those who need them.

[curb-cut]: https://en.wikipedia.org/wiki/Curb_cut

[^toddler-curb-cut]: And when my son grows a bit and starts walking on
    his own, he'll likely still be small enough that walking up a curb
    without a curb cut will be difficult for him.
    
[screen-reader]: https://www.afb.org/blindness-and-low-vision/using-technology/assistive-technology-products/screen-readers
    
[^for-now]: For now, that is---perhaps software assistants will become
more widespread as software improves, mediating between the user and
web pages. Password managers and form autofill agents are already
somewhat like this.

Accessibility covers the whole spectrum, from minor accommodations to
support for advanced accessibility tools like screen readers.[^moral]
But the common lesson of all kinds of accessibility work, physical and
digital, is that once an accessibility tool is built, creative people
find that it helps in all kinds of situations unforseen by the tool's
designers. Dark mode helps you tell your work and personal email
apart; web page zoom helps you print the whole web page on a single
sheet of paper; and keyboard shortcuts let you leverage muscle memory
to submit many similar orders to a web application that doesn't have a
batch mode.

[^moral]: We have an ethical responsibility to help all users. Plus,
    there is the practical matter that if you're making a web page,
    you want as many people as possible to benefit from
    it.

Moreover, accessibility derives from the same [principles](intro.md)
that birthed the web: user control, multi-modal content, and
interoperability. These principles allowed the web to be accessible to
all types of browsers and operating systems, and *these same
principles* likewise make the web accessible to people of all types
and abilities.

CSS zoom
========

Let's start with the simplest accessibility problem: text on the
screen that is too small to read. It's a problem many of us will face
sooner or later, and possibly the most common user disability issue.
The simplest and most effective way to address this is by increasing font
and element sizes. This approach is called *CSS zoom*.[^zoom]

[^zoom]: The word zoom evokes an analogy to a camera zooming in, but
it is not the same, because CSS zoom causes layout. *Pinch zoom*, on
the other hand is just like a camera and does not cause layout.

To implement it, we first need a way to trigger zooming. On most
browsers, that's done with the `Ctrl-+`, `Ctrl--`, and `Ctrl-0`
keys; using the `Ctrl` modifier key means you can type a `+`, `-`, or
`0` into a text entry without triggering the zoom function.

To handle modifier keys, we'll need to listen to both "key down" and
"key up" events, and store whether the `Ctrl` key is pressed:

``` {.python}
if __name__ == "__main__":
    # ...
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

Now we can have a case in the key handling code for "key down" events
while the `Ctrl` key is held:

``` {.python}
if __name__ == "__main__":
    # ...
    ctrl_down = False
    while True:
		if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
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

Finally, the `Tab` responds to these commands by adjusting a new
`zoom` property on `Browser`, which starts at `1` and acts as a
multiplier for all "CSS sizes" on the web page:[^browser-chrome]

[^browser-chrome]: CSS zoom typically does not change the size of
elements of the browser chrome. Browsers *can* do that too, but it's
usually triggered by a global OS setting.

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

Note that we need to set the `needs_render` flag when we zoom to
redraw the screen after zooming is complete. We also need to reset the
zoom level when we navigate to a new page:

``` {.python}
class Tab:
    def load(self, url, body=None):
        self.zoom = 1
        # ...
```

The `zoom` factor is supposed to multiply all CSS sizes, so we'll need
access to it during layout. There's a few ways to do this, but the
easiest is just to pass it in as an argument to `layout`:

``` {.python}
class Tab:
	# ...
	def render(self):
			# ...
			self.document.layout(self.zoom)
```

The `BlockLayout`, `LineLayout` and `DocumentLayout`, classes just
pass on the zoom to their children:

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

However, `InlineLayout`, `TextLayout`, and `InputLayout` have to
handle zoom specially, because the elements they represent have to be
scaled by the `zoom` multipler. First, pass the `zoom` argument into
the `recurse` method and from there into `text` and `input`:

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

These two methods now need to scale their font sizes to account for
`zoom`. Since scaling by `zoom` is a common operation, let's wrap it
in a helper method, `device_px`:

``` {.python}
def device_px(css_px, zoom):
    return css_px * zoom
```

Think about `device_px` not as a simple helper method, but as a unit
coversion from *CSS pixel* (the units specified in a CSS declaration)
to a *device pixel* (what's actually drawn on the screen). In a real
browser, this method could also account for differences like high-DPI
displays.

We'll do this conversion to adjust the font sizes in the `text` and
`input` methods:

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

As well as the font size in `TextLayout`:[^min-font-size]

[^min-font-size]: Browsers also usually have a *minimum* font size
feature, but it's a lot trickier to use correctly. Since a minimum
font size only affects *some* of the text on the page, and doesn't
affect other CSS lengths, it can cause overflowing fonts and broken
layouts. Because of these problems, browsers often restrict the
feature to situations where the site seems to be using [relative font
sizes][relative-font-size].

[relative-font-size]: https://developer.mozilla.org/en-US/docs/Web/CSS/font-size

``` {.python}
class TextLayout:
	# ...
    def layout(self, zoom):
    	# ...
        size = device_px(
        	float(self.node.style["font-size"][:-2]), zoom)
```

And the fixed `INPUT_WIDTH_PX` for text boxes:

``` {.python }
class InlineLayout:
	# ...
    def input(self, node, zoom):
        w = device_px(INPUT_WIDTH_PX, zoom)	
```

This handles text and text boxes, but that's not the only thing that
needs to zoom in and out. CSS property values, like `width` and
`height`, are also specified in CSS pixels, not device pixels, so they
need to be scaled. The easiest way to do that is by passing the `zoom`
value to `style_length`, which we already use for reading CSS lengths:

``` {.python}
def style_length(node, style_name, default_value, zoom):
    style_val = node.style.get(style_name)
    return device_px(float(style_val[:-2]), zoom) if style_val \
        else default_value
```

Now just pass in the `zoom` parameter to `style_length` inside
`BlockLayout`, `InlineLayout`, and `InputLayout`.

Finally, one tricky place we need to adjust for zoom is inside
`DocumentLayout`. Here there are two sets of lengths: the overall
`WIDTH`, and the `HSTEP`/`VSTEP` padding around the edges of the page.
The `WIDTH` comes from the size of the application window itself, so
that's measured in device pixels and doesn't need to be converted. But
the `HSTEP`/`VSTEP` is part of the page's layout, so it's in CSS
pixels and *does* need to be converted:

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

Now try it out. All of the fonts should be get about 10% bigger each
time you press `+`, and shrink by 10% when you press `-`. The bigger
text should still wrap appropriately at the edge of the screen, and
CSS lengths should be scaled just like the text is. This is great for
reading text more easily.

::: {.further}

Another way that CSS pixels and device pixels can differ is on a high-resolution
screen. When CSS was first defined, the typical screen had about 96 pixels per
inch of screen. Since then, various devices (the original iPhone was an early
example) have screens with much higher pixel densities. This led to a problem
though---web sites designed for an assumed pixel density of 96 would look
tiny when displayed on those screens. This was solved with the
[`devicePixelRatio`][dpr] concept---each CSS pixel is by default multiplied by
the device pixel ratio to arrive at device pixels. The original iPhone, for
example, had 163 pixels per inch. 163/96 = 1.7, but since a multiplier like 1.7
leads to awkward rounding issues in layout, that device selected a
`devicePixelRatio` of 2.^[Since then, may different screens with different
pixel densities have appeared, and these days it's not uncommon to have a ratio
that is not an integer. For example, the Pixelbook Go I'm using to write this
book has a ratio of 1.25 (but with 166 pixels per inch; as you can see, the
choice of ratio for a given screen is somewhat arbitrary).]

On a device with a `devicePixelRatio` other than 1, `zoom` and
`devicePixelRatio` have to be multiplied together in the rendering code. In
addition, real browsers expose a global variable exposed to JavaScript called
`devicePixelRatio` that equal to the product of these two and updated whenever
the user zooms in or out.  Adn there is a (non-standard, please don't
use it!) [`zoom`][zoom-css] CSS property in WebKit and Chromium browsers that
allows developers to apply something similar to CSS zoom to specific element
subtrees.

[dpr]: https://developer.mozilla.org/en-US/docs/Web/API/Window/devicePixelRatio

[zoom-css]: https://developer.mozilla.org/en-US/docs/Web/CSS/zoom

On devices with touch screens,^[Originally just phones, but now many desktop
computers have touch screens.] many browsers also implement *pinch zoom*:
zooming in on the picture with a multi-touch pinch gesture. This kind of zoom
is just like a CSS scale transform though---it zooms in on the pixels but
doesn't update the main-thread rendering pipeline, and doesn't affect the
`devicePixelRatio` variable. The resulting view on the
screen is called the [visual viewport][visual-viewport].

[visual-viewport]: https://developer.mozilla.org/en-US/docs/Web/API/Visual_Viewport_API

:::

Dark mode
=========

Another useful visual change is using darker colors to help users who
are extra sensitive to light, use their device at night, or just
prefer a darker color scheme. This browser *dark mode* feature should
switch both the browser chrome and the web page itself to use white
text on a black background, and otherwise adjust background colors to
be darker.

We'll trigger dark mode with `Ctrl-d`:

``` {.python}
if __name__ == "__main__":
    while True:
        if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            # ...
                if ctrl_down:
                    # ...
                    elif event.key.keysym.sym == sdl2.SDLK_d:
                        browser.toggle_dark_mode()
```

When dark mode is active, we need to draw both the browser chrome and
the web page contents differently. The browser chrome is a bit easier,
so let's start with that. We'll start with a `dark_mode` field
indicating whether dark mode is active:

``` {.python}
class Browser:
    # ...
    def __init__(self):
        # ...
        self.dark_mode = False

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
```

Now we just need to flip all the colors in `raster_chrome` when
`dark_mode` is set. Let's store the foreground and background color in
variables we can reuse:

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

Likewise all of the other `draw_line`, `draw_text` and `draw_rect`
calls in `raster_chrome` (they're not all shown here) should use
`color` or `background_color`.[^more-colors]

[^more-colors]: Of course, a full-featured browser's chrome has many
    more buttons than our browser's, and probably uses many more
    buttons. Most browsers support a theming system that stores all
    the relevant colors and images, and dark mode switches the browser
    from one theme to another.
    
Now, we want the web page content to change from light mode to dark
mode as well. To start, let's inform the `Tab` when the user requests
dark mode:

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

Note that we need to rerender the page when the dark mode setting is
flipped, so that the user actually sees the new colors.

Now we need the page's colors to somehow depend on dark mode. The
easiest to change are the default text color and the background color
of the document, which are set by the browser. The default text color,
for example, comes from the `INHERITED_PROPERTIES` dictionary, which
we can just modify based on the dark mode:

``` {.python replace=))/)%2c%20self)}
class Tab:
    # ...
    def render(self):
        if self.needs_style:
            if self.dark_mode:
                INHERITED_PROPERTIES["color"] = "white"
            else:
                INHERITED_PROPERTIES["color"] = "black"
            style(self.nodes,
                sorted(self.rules, key=cascade_priority))
```

And the background for the page is drawn by the `Browser` in the
`draw` method, which we can make depend on dark mode:

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

Now if you open the browser and switch to dark mode, you should see
white text on a black background.

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
losing readability or failing to provide adequate dark mode styling.

[extension]: https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions
[user-style]: https://developer.mozilla.org/en-US/docs/Web/CSS/Cascade#user_stylesheets
[^no-user-styles]: Most browsers these days don't even support user style
sheets, and instead rely on extensions.

:::

Customizing dark mode
=====================

Our simple dark mode implementation works well for pages with just
text on a background. But for a good-looking dark mode, we probably
also want to adjust all the other colors on the page. For example,
buttons and input elements probably need a darker background color, as
do any colors that the web developer used on the page.

To support this, CSS uses [media queries][mediaquery]. This special
syntax that basically wraps some CSS rules in an `if` statement with
some kind of condition; if the condition is true, those CSS rules are
used, but if the condition is false, they are ignored. The
`prefers-color-scheme` condition checks for dark mode. For example,
this CSS will make `<div>`s have a white text on a black background
only in dark mode:


``` {.css expected=False}
@media (prefers-color-scheme:dark) {
  div { background-color: black; color: white; }
}
```

Web developers can use `prefers-color-scheme` queries in their own
stylesheets, adjusting their own choice of colors to fit user
requests, but we can also use a `prefers-color-scheme` media query in
the browser default stylesheet to adjust the default colors for links,
buttons, and text entries:

``` {.css}
@media (prefers-color-scheme: dark) {
  a { color: lightblue; }
  input { background-color: blue; }
  button { background-color: orangered; }
}
```

To implement media queries, we'll have to start with parsing this
syntax:

``` {.python replace=pair()/pair(%22)%22)}
class CSSParser:
    def media_query(self):
        self.literal("@")
        assert self.word() == "media"
        self.whitespace()
        self.literal("(")
        (prop, val) = self.pair()
        self.whitespace()
        self.literal(")")
        return prop, val
```

Then, in `parse`, we keep track of the current color scheme and adjust
it every time we enter or exit an `@media` rule:[^no-nested]

[^no-nested]: For simplicity, this code doesn't handle nested `@media`
    rules, because with just one type of media query there's no point
    in nesting them. To handle nested `@media` queries the `media`
    variable would have to store a stack of conditions.

``` {.python}
class CSSParser:
    def parse(self):
        # ...
        media = None
        self.whitespace()
        while self.i < len(self.s):
            try:
                if self.s[self.i] == "@" and not media:
                    prop, val = self.media_query()
                    if prop == "prefers-color-scheme" and val in ["dark", "light"]:
                        media = val
                    self.whitespace()
                    self.literal("{")
                    self.whitespace()
                elif self.s[self.i] == "}" and media:
                    self.literal("}")
                    media = None
                    self.whitespace()
                else:
                    # ...
                    rules.append((media, selector, body))
```

Note that I've modified the list of rules to store not just the
selector and the body, but also the color scheme for those
rules---`None` if it applies regardless of color scheme, `dark` for
dark-mode only, and `light` for light-mode only. This way, the `style`
function can ignore rules that don't apply:

``` {.python}
def style(node, rules, tab):
    # ...
    for media, selector, body in rules:
        if media:
            if (media == "dark") != tab.dark_mode: continue
        # ...
```

[mediaquery]: https://developer.mozilla.org/en-US/docs/Web/CSS/Media_Queries/Using_media_queries

Try your browser on a [web page](examples/example14-focus.html) with
lots of links, text entries, and buttons, and you should now see that
in dark mode they also change color to have a darker background and
lighter foreground.

::: {.further}

Fully customizable dark mode requires several additional features beyond
`prefers-color-scheme`. The most important is that web sites need a way
to declare whether they support dark mode or not (if they don't, the
browser should really not be flipping the colors on that page, because it'll
likely have terrible accessibility outcomes!) This feature is achieved with
the `color-scheme` [`meta` tag][meta-tag], which allows the web page to declare
whether it supports light mode, dark mode, or both.

[meta-tag]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/meta/name

The second is the [`color-scheme`][color-scheme] CSS property, indicating
whether that element and its subtree support dark, light or both modes.
(And with the `only` keyword, whether it should be forced into the ones
indicated.)


[color-scheme]: https://developer.mozilla.org/en-US/docs/Web/CSS/color-scheme
:::

Keyboard navigation
===================

Right now, most browser features are triggered using the
mouse,^[Except for scrolling, which is keyboard-only.] which is a
problem for users with injuries or disabilities in their hand---and
also a problem for power users that prefer their keyboards. So ideally
every browser feature should be accessible via the keyboard as well as
the mouse. That includes both browser chrome interactions like going
back, typing a URL, or quitting the browser, and also web page
interactions such as submitting forms, typing in text areas, and
navigating links.

Let's start with the browser chrome, since it's easiest. Here, we need
to allow the user to go back, to type in the address bar, and to
create and cycle through tabs, all with the keyboard. We'll also add a
keyboard shortcut for quitting the browser.[^one-more] Let's make all
these shortcuts use the `Ctrl` modifier key so they don't interfere
with normal typing: `Ctrl-Left` to go back, `Ctrl-L` to type in the
address bar, `Ctrl-T` to create a new tab, `Ctrl-Tab` to switch to the
next tab, and `Ctrl-Q` to exit the browser:

[^one-more]: Depending on the OS you might also need shortcuts for
minimizing or maximizing the browser window. Those require calling
specialized OS APIs, so I won't implement them.

``` {.python}
if __name__ == "__main__":
    while True:
        if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            elif event.type == sdl2.SDL_KEYDOWN:
                if ctrl_down:
                    # ...
                    elif event.key.keysym.sym == sdl2.SDLK_LEFT:
                        browser.go_back()
                    elif event.key.keysym.sym == sdl2.SDLK_l:
                        browser.focus_addressbar()
                    elif event.key.keysym.sym == sdl2.SDLK_t:
                        browser.load("https://browser.engineering/")
                    elif event.key.keysym.sym == sdl2.SDLK_TAB:
                        browser.cycle_tabs()
                    elif event.key.keysym.sym == sdl2.SDLK_q:
                        browser.handle_quit()
                        sdl2.SDL_Quit()
                        sys.exit()
                        break
```

Here the `focus_addressbar` and `cycle_tabs` methods are new, but
their contents are just copied from `handle_click`:

``` {.python}
class Browser:
    def focus_addressbar(self):
        self.lock.acquire(blocking=True)
        self.focus = "address bar"
        self.address_bar = ""
        self.set_needs_raster()
        self.lock.release()

    def cycle_tabs(self):
        new_active_tab = (self.active_tab + 1) % len(self.tabs)
        self.set_active_tab(new_active_tab)
```

Now any clicks in the browser chrome can be replaced with keyboard
actions. But what about clicks in the web page itself? This is
trickier, because web pages can have any number of links. So the
standard solution is letting the user `Tab` through all the clickable
things on the page, and press `Enter` to actually click on them.

We'll implement this by expanding our implementation of *focus*. We
already have a `focus` property on each `Tab` indicating which `input`
element is capturing keyboard input. Let's allow buttons and links to
be focused as well. Of course, they don't capture keyboard input, but
when the user pressed `Enter` we'll press the button or navigate to
the link. We'll start by binding those keys:

``` {.python}
if __name__ == "__main__":
    while True:
        if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            elif event.type == sdl2.SDL_KEYDOWN:
                # ...
                elif event.key.keysym.sym == sdl2.SDLK_RETURN:
                    browser.handle_enter()
                elif event.key.keysym.sym == sdl2.SDLK_TAB:
                    browser.handle_tab()
```

Note that these lines don't go inside the `if ctrl_down` block, since
we're binding `Tab` and `Enter`, not `Ctrl-Tab` and `Ctrl-Enter`. In
`Browser`, we just forward these keys to the active tab's `enter` and
`advance_tab` methods:

``` {.python}
class Browser:
    def handle_tab(self):
        self.focus = "content"
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.advance_tab)
        active_tab.task_runner.schedule_task(task)

    def handle_enter(self):
    	# ...
        elif self.focus == "content":
            active_tab = self.tabs[self.active_tab]
            task = Task(active_tab.enter)
            active_tab.task_runner.schedule_task(task)
        # ...
```

Let's start with the `advance_tab` method. Each time it's called, the
browser should advance focus to the next focusable thing. This will
first require a definition of which elements are focusable:

``` {.python replace=)]/)]%20 }
def is_focusable(node):
    return node.tag in ["input", "button", "a"]

class Tab:
    def advance_tab(self):
        focusable_nodes = [node
            for node in tree_to_list(self.nodes, [])
            if isinstance(node, Element) and is_focusable(node)
            and get_tabindex(node) >= 0]
```

Next, in `advance_tab`, we need to find out where the
currently-focused element is in this list so we can move focus to the
next one.

``` {.python}
class Tab:
    def advance_tab(self):
        # ...
        if self.focus in focusable_nodes:
            idx = focusable_nodes.index(self.focus) + 1
        else:
            idx = 0
```

Finally, we just need to focus on the chosen element. If we've reached
the last the focusable node (or if there weren't any focusable nodes
to begin with), we'll unfocus the page and move focus to the address
bar:

``` {.python replace=%20=%20focusable_nodes[idx]/_element(focusable_nodes[idx]),%20=%20None/_element(None)}
class Tab:
    def advance_tab(self):
        if idx < len(focusable_nodes):
            self.focus = focusable_nodes[idx]
        else:
            self.focus = None
            self.browser.focus_addressbar()
        self.set_needs_render()
```

Now that an element is focused, the user should be able to interact
with it by pressing `Enter`. Since the exact action they're doing
varies (navigating a link, pressing a button, clearning a text entry),
we'll call this "activating" the element:

``` {.python}
class Tab:
    def enter(self):
        if not self.focus: return
        self.activate_element(self.focus)
```

The `activate_element` method does different things for different
kinds of elements:

``` {.python}
class Tab:
    def activate_element(self, elt):
        if elt.tag == "input":
            elt.attributes["value"] = ""
        elif elt.tag == "a" and "href" in elt.attributes:
            url = resolve_url(elt.attributes["href"], self.url)
            self.load(url)
        elif elt.tag == "button":
            while elt:
                if elt.tag == "form" and "action" in elt.attributes:
                    self.submit_form(elt)
                elt = elt.parent
```

All of this activation code is copied from the `click` method on
`Tab`s, which can now be rewritten to call `activate_element`
directly:

``` {.python}
class Tab:
    def click(self, x, y):
        while elt:
            if isinstance(elt, Text):
                pass
            elif is_focusable(elt):
                self.focus_element(elt)
                self.activate_element(elt)
                self.set_needs_render()
                return
            elt = elt.parent
```

Note that hitting `Enter` when focused on a text entry clears the text
entry; in most browsers, it submits the containing form instead. That
quirk is because [our browser doesn't implement][clear-input] the
`Backspace` key.

[clear-input]: forms.html#interacting-with-widgets

Finally, note that sometimes activating an element submits a form or
navigates to a new page, which means the element we were focused on no
longer exists. We need to make sure to clear focus in this case:

``` {.python}
class Tab:
    def load(self, url, body=None):
        self.focus = None
        # ...
```

We now have the ability to focus on links, buttons, and text entries.
But as with any browser feature, it's worth asking whether web page
authors should be able to customize it. With keyboard navigation, the
author might want certain links not to be focusable (like "permalinks"
to a section heading, which would just be noise to most users), or
might want to change the order in which the user tabs through
focusable items.

Browsers support the `tabindex` HTML attribute to make this possible.
The `tabindex` attribute is a number. An element isn't focusable if
its `tabindex` is negative, and elements with smaller `tabindex`
values come before those with larger values and those without a
`tabindex` at all. To implement that, we need to sort the focusable
elements by tab index, so we need a function that returns the tab
index:

``` {.python}
def get_tabindex(node):
    return int(node.attributes.get("tabindex", "9999999"))
```

The default value, "9999999", makes sure that elements without a
`tabindex` attribute sort after ones with the attribute. Now we can
sort by `get_tabindex` in `advance_tab`:

``` {.python}
class Tab:
    def advance_tab(self):
        focusable_nodes = [node
            for node in tree_to_list(self.nodes, [])
            if isinstance(node, Element) and is_focusable(node)
            and get_tabindex(node) >= 0]
        focusable_nodes.sort(key=get_tabindex)
        # ...
```

Since Python's sort is "stable", two elements with the same `tabindex`
won't change their relative position in `focusable_nodes`.

Additionally, elements with `tabindex` are automatically focusable,
even if they aren't a link or a button or a text entry. That's useful,
because that element might listen to the `click` event. To support
this let's first extend `is_focusable` to consider `tabindex`:

``` {.python}
def is_focusable(node):
    if get_tabindex(node) <= 0:
        return False
    elif "tabindex" in node.attributes:
        return True
    else:
        return node.tag in ["input", "button", "a"]
```

Next, we need to make sure to send a `click` event when an element is
activated:

``` {.python}
class Tab:
    def enter(self):
        if not self.focus: return
        if self.js.dispatch_event("click", self.focus): return
        self.activate_element(self.focus)
```

Note that just like clicking on an element, activating an element can
be cancelled from JavaScript using `preventDefault`.

We now have configurable keyboard navigation for both the browser and
the web page content. And it involved writing barely any new code,
instead mostly moving code from existing methods into new stand-alone
ones. The fact that keyboard navigation simplified, not complicated,
our browser implementation is not a surprise: improving accessibility
often involves generalizing and refining existing concepts, leading to
more maintainable code overall.

::: {.further}
Why send the `click` event when an element is activated, instead of a
special `activate` event? Internet Explorer [did send][onactivate]
this event, and other browsers used to send a
[DOMActivate][domactivate] event, but it's been deprecated in favor of
sending the `click` event even if the element was activated via
keyboard, not via a click. This works better when the developers aren't
thinking much about accessibility and only register the `click` event
listener.
:::

[onactivate]: https://docs.microsoft.com/en-us/previous-versions/windows/internet-explorer/ie-developer/platform-apis/aa742710(v=vs.85)
[domactivate]: https://w3c.github.io/uievents/#event-type-DOMActivate

Indicating focus
================

Thanks to our keyboard shortcuts, users can now reach any link,
button, or text entry from the keyboard. But if you try to use this to
navigate a website, it's a little hard to know which element is
focused when. A visual indication---similar to the cursor we use on
text inputs---would help sighted users know if they've reached the
element they want or if they need to keep hitting `Tab`. In most
browsers, this visual indication is a *focus ring* that outlines the
focused element.

To implement focus rings, we're going to have to generalize how we
implement text cursors. Recall that, right now, text cursors are added
by drawing a verticle line in the `Tab`'s `render` method. We could
extend that code to draw a cursor or an outline, but before we make
that method more complicated let's move it into the `InputLayout` so
we have easier access to size and position information.[^effects] To
do that, we'll need each `InputLayout` to know whether or not it is
currently focused:

[^effects]: As a side effect, this change will also mean text cursors
    are now affected by visual effects, including blends, opacity, and
    translations. Translations in particular are important.

``` {.python}
class Element:
    def __init__(self, tag, attributes, parent):
        self.is_focused = False
```

We'll set this flag in a new `focus_element` method that we'll now use
to change the `focus` field in a `Tab`:

``` {.python}
class Tab:
    def focus_element(self, node):
        if self.focus:
            self.focus.is_focused = False
        self.focus = node
        if node:
            node.is_focused = True
```

To draw an outline, we'll need something like `DrawRect`, but which
draws the rectangle's border, not its inside. I'll call that command
`DrawOutline`:

``` {.python}
class DrawOutline(DisplayItem):
    def __init__(self, rect, color, thickness):
        super().__init__(rect)
        self.color = color
        self.thickness = thickness

    def is_paint_command(self):
        return True

    def execute(self, canvas):
        draw_rect(canvas,
            self.rect.left(), self.rect.top(),
            self.rect.right(), self.rect.bottom(),
            border_color=self.color, width=self.thickness)
```

Now we can paint a 2 pixel black outline around an element like this:

``` {.python expected=False}
def paint_outline(node, cmds, rect):
    if node.is_focused:
        cmds.append(DrawOutline(rect, "black", 2))
```

This is in a helper method so that we can call it in both
`InputLayout` (for text entries and buttons) and in `InlineLayout`
(for links). In `InputLayout` it looks like this:

``` {.python}
class InputLayout:
	def paint(self, display_list):
		# ...
        if self.node.is_focused and self.node.tag == "input":
            cx = rect.left() + self.font.measureText(text)
            cmds.append(DrawLine(cx, rect.top(), cx, rect.bottom()))

        paint_outline(self.node, cmds, rect)
        cmds = paint_visual_effects(self.node, cmds, rect)
        display_list.extend(cmds)
```

Note that this comes after painting the rest of the text entry's
content but before the visual effects.

Unfortunately, handling links is a little more complicated. That's
because one `<a>` element corresponds to multiple `TextLayout`
objects, so there's not just one layout object where we can stick the
code. Moreover, those `TextLayout`s could be split across several
lines, so we might want to draw more than one focus ring. To work
around this, let's draw the focus ring in `LineLayout`. Each
`LineLayout` finds all of its child `TextLayout`s that are focused,
and draws a rectangle around them all:

``` {.python expected=False}
class LineLayout:
    def paint(self, display_list):
        # ...
        outline_rect = skia.Rect.MakeEmpty()
        parent = None
        for child in self.children:
            parent = child.node.parent
            if has_outline(parent):
                outline_node = parent
                outline_rect.join(child.rect())
        if parent:
            paint_outline(parent, display_list, outline_rect)
```

You should also add a `paint_outline` call to `BlockLayout`, since
users can make any element focusable with `tabindex`.

Now when you `Tab` through a page, you should see the focused element
highlighted with a black outline. And if a link happens to cross
multiple lines, you will see our browser use multiple focus
rectangles to make crystal-clear what is being focused on.

Except for one problem: if the focused element is scrolled offscreen, there is
still no way to tell it's visible. To fix this we'll need to automatically
scroll it onto the screen.^[JavaScript methods like [`focus`][focus-el] also do
this (which is why you'll observe that it has an option to skip the scrolling
part).] Doing this is a bit tricky, because determining if the element is
offscreen requires layout. So we'll set a new `focus_changed` bit on `Tab`:

``` {.python}
class Tab:
    def focus_element(self, node):
        if node != self.focus:
            self.focus_changed = True
```

And use it at the end of `run_animation_frame` to set an appropriate scroll.
If the element is scrolled off the top of the screen, let's place it
`SCROLL_STEP` pixels from the top, and if it's scrolled off the bottom, place
it `SCROLL_STEP` pixels from the bottom.

``` {.python}
class Tab:
    def run_animation_frame(self, scroll):
        # ...
        if self.focus_changed and self.focus:
            if self.focus.layout_object:
                layout_object = self.focus.layout_object
                if layout_object.y - self.scroll < 0:
                    self.scroll = \
                        clamp_scroll(
                            layout_object.y - SCROLL_STEP,
                            document_height)
                    self.scroll_changed_in_tab = True
                elif layout_object.y - self.scroll > HEIGHT - CHROME_PX:
                    self.scroll = clamp_scroll(
                        layout_object.y + HEIGHT - \
                        CHROME_PX - SCROLL_STEP,
                        document_height)
                    self.scroll_changed_in_tab = True
        self.focus_changed = False
```

[focus-el]: https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/focus

Focus outlines now basically work, and will even scroll on-screen if you try
examples like [this](examples/example14-focus.html). But ideally, the focus
indicator should be customizable, so that the web page author can make sure the
focused element stands out. In CSS, that's done with what's called the
"`:focus` [pseudo-class][pseudoclass]". Basically, this means you can
write a selector like this:

[pseudoclass]: https://developer.mozilla.org/en-US/docs/Web/CSS/Pseudo-classes

    div:focus { ... }

And then that selector applies only to `<div>` elements that are
currently focused.[^why-pseudoclass]

[^why-pseudoclass]: It's called a pseudo-class because it's similar to how a
developer would indicate a [class] attribute on an element for the purpose
of targeting special elements with different styles. It's "pseudo" because
there is no actual class attribute set on the element while it's focused.

[class]: https://developer.mozilla.org/en-US/docs/Web/CSS/Class_selectors

To implement this, we need to first parse a new kind of selector. To
do that, let's change `selector` to call a new `simple_selector`
subroutine to parse a tag name and a possible pseudoclass:

``` {.python}
class CSSParser:
    def selector(self):
        out = self.simple_selector()
        # ...
        while self.i < len(self.s) and self.s[self.i] != "{":
            descendant = self.simple_selector()
            # ...
```

In `simple_selector`, the parser first parses a tag name and then
checks if that's followed by a colon and a pseudoclass name:

``` {.python}
class CSSParser:
    def simple_selector(self):
        out = TagSelector(self.word().lower())
        if self.i < len(self.s) and self.s[self.i] == ":":
            self.literal(":")
            pseudoclass = self.word().lower()
            out = PseudoclassSelector(pseudoclass, out)
        return out
```

A `PseudoclassSelector` wraps another selector; it checks that base
selector but also a pseudoclass.

``` {.python}
class PseudoclassSelector:
    def __init__(self, pseudoclass, base):
        self.pseudoclass = pseudoclass
        self.base = base
        self.priority = self.base.priority
```

Matching is straightforward; if the pseudoclass is unknown, the
selector fails to match anything:

``` {.python}
class PseudoclassSelector:
    def matches(self, node):
        if not self.base.matches(node):
            return False
        if self.pseudoclass == "focus":
            return is_focused(node)
        else:
            return False
```

We can now use `:focus` to customize our focus indicator; for example,
we can make the focused element a different color. But ideally we'd
also be able to customize the focus outline itself. That's normally
done with the CSS [`outline` property][outline], which looks like
this:[^outline-syntax]

[outline]: https://developer.mozilla.org/en-US/docs/Web/CSS/outline

[^outline-syntax]: Naturally, there are other forms this property can
    take; we'll only implement this syntax.

    outline: 3px solid red;

This asks for a three pixel red outline. To add support for this in
our browser, we'll again need to first generalize the parser.

First, annoyingly, our CSS parser right now doesn't recognize the line
above as a valid property/value pair, since it parses values as a
single word. Let's replace that with any string of characters except a
semicolon or a curly brace:

``` {.python}
class CSSParser:
    def until_char(self, chars):
        start = self.i
        while self.i < len(self.s) and self.s[self.i] not in chars:
            self.i += 1
        return self.s[start:self.i]

    def pair(self, until):
        # ...
        val = self.until_char(until)
        # ...

    def body(self):
        while self.i < len(self.s) and self.s[self.i] != "}":
            try:
                prop, val = self.pair([";", "}"])
                # ...

    def media_query(self):
        # ...
        (prop, val) = self.pair(")")
        # ...
```

Now we have `outline` value in the relevant element's `style`. We can
parse that into a thickness and a color, assuming that we only want to
support `solid` outlines:

``` {.python}
def parse_outline(outline_str):
    if not outline_str: return None
    values = outline_str.split(" ")
    if len(values) != 3: return None
    if values[1] != "solid": return None
    return (int(values[0][:-2]), values[2])
```

Now we can use this `parse_outline` method when drawing an outline, in
`paint_outline`:

``` {.python}
def has_outline(node):
    return parse_outline(node.style.get("outline"))

def paint_outline(node, cmds, rect):
    if has_outline(node):
        thickness, color = parse_outline(node.style.get("outline"))
        cmds.append(DrawOutline(rect, color, thickness))
```

The default two-pixel black outline can now be moved into the browser
default stylesheet, like this:

``` {.css}
input:focus { outline: 2px solid black; }
button:focus { outline: 2px solid black; }
div:focus { outline: 2px solid black; }
```

Moreover, we can now make the outline white when dark mode is
triggered, which is important for it to stand out against the black
background:

``` {.css}
@media (prefers-color-scheme: dark) {
input:focus { outline: 2px solid white; }
button:focus { outline: 2px solid white; }
div:focus { outline: 2px solid white; }
a:focus { outline: 2px solid white; }
}
```

Finally, what if someone sets `outline` on an element that isn't
focused? It's not really clear why you'd do that, but in a real
browser that draws the outline no matter what. We can implement that
by changing all of our `paint` methods to use `has_outline` instead of
`is_focused` to draw the outline; focused elements will have an
outline thanks to the browser stylesheet above:

``` {.python}
class LineLayout:
    def paint(self, display_list):
        for child in self.children:
            if has_outline(node.parent):
                # ...
```

As with dark mode, focus outlines are a case where adding an
accessibility feature meant generalizing existing browser features to
make them more powerful. And once they were generalized, this
generalized form can be made accessible to web page authors, who can
use it for all sorts of things.

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
The browser can do a lot, but ultimately [good contrast][contrast] between
colors is something that page authors also have to pay attention to.


[wcag]: https://www.w3.org/WAI/standards-guidelines/wcag/
[contrast]: https://www.w3.org/TR/WCAG21/#contrast-minimum

:::


The accessibility tree
======================

Zoom, dark mode, and focus indicators help users with difficulty
seeing fine details, but if the user can't see the screen at all,^[The
original motivation of screen readers was for blind users, but it's
also sometimes useful for situations where the user shouldn't be
looking at the screen (such as driving), or for devices with no
screen.] screen reader software is typically used instead. The name
kind of explains it all: this software reads the text on the screen
out loud, so that users know what it says without having to see it.

So: what should we say to the user? There are basically two big
challenges we must overcome.

First, web pages contain visual hints besides text that we need to
reproduce for screen reader users. For example, when focus is on an
`<input>` or `<button>` element, the screen reader needs to say so,
since these users won't see the light blue or orange background.

And second, when listening to a screen reader, the user must be able
to direct the browser to the part of the page that interests
them.[^fast] For example, the user might want to skip headers and
navigation menus, or even skip most of the page until they get to a
paragraph of interest. But once they've reached the part of the page
of interest to them, they may want it read to them, and if some
sentence or phrase is particularly complex, they may want the
screen reader to re-read it.

You can see an example[^imagine] of screen reader navigation in this
talk, specifically the segment from 2:36--3:54:[^whole-talk]

<iframe width="560" height="315" src="https://www.youtube-nocookie.com/embed/qi0tY60Hd6M?start=159" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

[^whole-talk]: The whole talk is recommended; it has great examples of
    using accessibility technology.

[^fast]: Though many people who rely on screen readers learn to listen
    to *much* faster speech, it's still a less informationally dense
    medium than vision.

[^imagine]: I encourage you to test out your operating system's
    built-in screen reader to get a feel for what screen reader
    navigation is like. On macOS, type Cmd-Fn-F5 to turn on Voice
    Over; on Windows, type Win-Ctrl-Enter or Win-Enter to start
    Narrator. Both are largely used via keyboard shortcuts that you
    can look up.
    
To support all this, browsers structure the page as a tree and use that
tree to interact with the screen reader. The higher levels of the tree
represent items like paragraphs, headings, or navigation menus, while
lower levels represent text, links, or buttons.

This probably sounds a lot like HTML---and it is quite similar! But,
just like the HTML tree does not exactly match the layout tree,
there's not an exact match with this tree either. For example, some
HTML elements (like `<div>`) group content for styling that is
meaningless to screen reader users. Alternatively, some HTML elements
may be invisible on the screen,[^invisible-example] but relevant to
screen reader users. The browser therefore builds a separate
[accessibility tree][at] to support screen reader navigation.

[at]: https://developer.mozilla.org/en-US/docs/Glossary/Accessibility_tree

[^invisible-example]: For example, using `opacity:0`. There are
several other ways in real browsers that elements can be made
invisible, such as with the `visibility` or `display` CSS properties.

Let's implement an accessibility tree in our browser. It is built in a
rendering phase just after layout:

``` {.python}
class Tab:
    def __init__(self, browser):
        # ...
        self.needs_accessibility = False
        self.accessibility_tree = None

    def render(self):
        # ...
        if self.needs_layout:
            # ...
            self.needs_accessibility = True
            self.needs_paint = True
            self.needs_layout = False

        if self.needs_accessibility:
            self.accessibility_tree = AccessibilityNode(self.nodes)
            self.accessibility_tree.build()
            self.needs_accessibility = False
            self.needs_paint = True
```

The accessibility tree is built out of `AccessibilityNode`s:

``` {.python}
class AccessibilityNode:
    def __init__(self, node):
        self.node = node
        self.children = []
        self.text = None
```

The `build` method on `AccessibilityNode` recursively creates the
accessibility tree. To do so, we traverse the HTML tree and, for each
node, determine what "role" it plays in the accessibility tree. Some
elements, like `<div>`, have no role, so don't appear in the
accessibility tree, while elements like `<input>`, `<a>` and
`<button>` have default roles.[^standard] We can compute the role of a
node based on its tag name, or from the special `role` attribute if
that exists:

[^standard]: Roles and default roles are are specified in the
[WAI ARIA standard][aria-roles].

[aria-roles]: https://www.w3.org/TR/wai-aria-1.2/#introroles

``` {.python}
class AccessibilityNode:
    def __init__(self, node):
        # ...
        if isinstance(node, Text):
            if node.parent.tag == "a":
                self.role = "link"
            elif is_focusable(node.parent):
                self.role = "focusable text"
            else:
                self.role = "StaticText"
        else:
            if "role" in node.attributes:
                self.role = node.attributes["role"]
            elif node.tag == "a":
                self.role = "link"
            elif node.tag == "input":
                self.role = "textbox"
            elif node.tag == "button":
                self.role = "button"
            elif node.tag == "html":
                self.role = "document"
            elif is_focusable(node):
                self.role = "focusable"
            else:
                self.role = "none"
```

To build the accessibility tree, we just recursively walk the HTML
tree. As we do so, we skip nodes with a `none` role, but not their children:

``` {.python}
class AccessibilityNode:
    def build(self):
        for child_node in self.node.children:
            self.build_internal(child_node)

    def build_internal(self, child_node):
        child = AccessibilityNode(child_node)
        if child.role != "none":
            self.children.append(child)
            child.build()
        else:
            for grandchild_node in child_node.children:
                self.build_internal(grandchild_node)
```

The user can now direct the screen reader to walk up or down this
accessibility tree and describe each node to the user. 

Screen readers
==============

Typically, the screen reader is a separate application from the
browser,[^why-diff] with which the browser communicates through
OS-specific APIs. To keep this book platform-independent, our
discussion of screen reader support will instead include a minimal
screen reader integrated directly into the browser.[^os-pain]

But should our built-in screen reader live in the `Browser` or each `Tab`? Real
browsers implement it in the `Browser`, so we'll do that too.^[And therefore
the browser thread in our multi-threaded browser.] This is sensible for a
couple of reasons. One is that screen readers need to describe not just the tab
contents but also browser chrome interactions, and doing it all in one place
makes it easier to present everything seamlessly to the user. But the most
critical reason is that since real-world screen readers tend to be in the
OS, *and their APIs are almost always synchronous*. So the browser
thread needs to interact with the screen reader without the main
thread's help.^[I suppose you could temporarily synchronize all
threads, but that's a really bad idea, not only because it's very
slow, but also is likely to cause deadlocks unless the browser is
extremely careful. Most browsers these days are also multi-process,
which makes it even harder.]

So the very first thing we need to do is send the tab's accessibility tree over
to the browser thread. That'll be a straightforward extension of the commit
concept introduced in [Chapter 12][ch12-commit]. First we'll add the tree
to `CommitData`: 

``` {.python expected=False}
class CommitData:
    def __init__(self, url, scroll, height,
        display_list, composited_updates, accessibility_tree):
        # ...
        self.accessibility_tree = accessibility_tree
```

Then we send it across in `run_animation_frame`:

``` {.python}
class Tab:
    def run_animation_frame(self, scroll):
        # ...
        commit_data = CommitData(
            accessibility_tree=self.accessibility_tree,
            # ...
        )
        # ...
        self.accessibility_tree = None

class Browser:
    def commit(self, tab, data):
        # ...
        self.accessibility_tree = data.accessibility_tree

    def clear_data(self):
        # ...
        self.accessibility_tree = None
```

Note that I clear the `Tab`'s reference to the accessibility tree once
it's sent over to the browser thread. This is the same thing we did
for the display list, and it makes sense, since the `Tab` has no use
for the accessibility tree other than to build it.

[ch12-commit]: scheduling.html#committing-a-display-list

Now that the tree is in the browser thread, let's implement the screen reader.
We'll use two Python libraries to actually read text
out loud: [`gtts`][gtts] (which wraps the Google [text-to-speech API][tts]) and
[`playsound`][playsound]. You can install them using `pip3`:

[^why-diff]: I think the reason is mainly historical, in that accessibility APIs
and screen readers evolved first with operating systems, and before/in parallel
with the development of browsers. These days, browsers are by far the
most important app many users interact with (especially on desktop computers),
so it makes more sense to consider such features core to a browser.

[^os-pain]: Another reason is that it's quite a lot of work to directly
integrate a browser with the accessibility APIs of each OS. Further, it's not
very easy to find Python bindings for these APIs, especially Linux. And as
you'll see, it really isn't very hard to get the basics working, though a big
reason is that these days there are high-quality text-to-speech libraries
available for non-commercial use.

[gtts]: https://pypi.org/project/gTTS/

[tts]: https://cloud.google.com/text-to-speech/docs/apis

[playsound]: https://pypi.org/project/playsound/

    pip3 install gtts
    pip3 install playsound

You can use these libraries to convert text to an audio file, and then
play it:

``` {.python}
import os
import gtts
import playsound

SPEECH_FILE = "/tmp/speech-fragment.mp3"

def speak_text(text):
    print("SPEAK:", text)
    tts = gtts.gTTS(text)
    tts.save(SPEECH_FILE)
    playsound.playsound(SPEECH_FILE)
    os.remove(SPEECH_FILE)
```

::: {.quirk}
You may need to adjust the `SPEECH_FILE` path to fit your system
better. If you have trouble importing any of the libraries, you may
need to consult the [`gtts`][gtts] or [`playsound`][playsound]
documentation. If you can't get these libraries working, just delete
everything in `speak_text` except the `print` statement. You won't
hear things being spoken, but you can at least debug by watching the
standard output.
:::

To start with, we'll want a key binding that turns the screen reader
on and off. While real operating systems typically use more obscure
shortcuts, I'll use `Ctrl-A` to turn on the screen reader:

``` {.python}
if __name__ == "__main__":
    while True:
        if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            # ...
                if ctrl_down:
                    # ...
                    elif event.key.keysym.sym == sdl2.SDLK_a:
                        browser.toggle_accessibility()            
```

The `toggle_accessibility` method tells the `Tab` that accessibility
is on:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.needs_accessibility = False
        self.accessibility_is_on = False

    def set_needs_accessibility(self):
        if not self.accessibility_is_on:
            return
        self.needs_accessibility = True
        self.needs_draw = True

    def toggle_accessibility(self):
        self.lock.acquire(blocking=True)
        self.accessibility_is_on = not self.accessibility_is_on
        self.set_needs_accessibility()
        self.lock.release()
```

When accessibility is on, the `Browser` calls `update_accessibility`, which
is what actually produces sound:

``` {.python}
class Browser:
    def composite_raster_and_draw(self):
        # ...
        if self.needs_accessibility:
            self.update_accessibility()

```

Now, what should the screen reader say? Well, that's not really up to
the browser---the screen reader is a stand-alone application, often
heavily configured by its user, and can decide on its own. But as a
simple debugging aid, let's write a screen reader that speaks the
whole web page once it's loaded; of course, a real screen reader is
much more flexible than that.

To speak the whole document, we need to know how to speak each
`AccessibilityNode`. This has to be decided back in the `Tab`, since
the text will include DOM content that is not accessible to the
browser thread. So let's add a `text` field to `AccessibilityNode` and
set it in `build` according to the node's role and surrounding DOM
context. For text nodes it's just the text, and otherwise it describes
the element tag, plus whether it's focused.

``` {.python}
class AccessibilityNode:
    def __init__(self, node):
        # ...
        self.text = None

    def build(self):
        for child_node in self.node.children:
            self.build_internal(child_node)

        if self.role == "StaticText":
            self.text = self.node.text
        elif self.role == "focusable text":
            self.text = "Focusable text: " + self.node.text
        elif self.role == "focusable":
            self.text = "Focusable"
        elif self.role == "textbox":
            if "value" in self.node.attributes:
                value = self.node.attributes["value"]
            elif self.node.tag != "input" and self.node.children and \
                 isinstance(self.node.children[0], Text):
                value = self.node.children[0].text
            else:
                value = ""
            self.text = "Input box: " + value
        elif self.role == "button":
            self.text = "Button"
        elif self.role == "link":
            self.text = "Link"
        elif self.role == "alert":
            self.text = "Alert"
        elif self.role == "document":
            self.text = "Document"

        if is_focused(self.node):
            self.text += " is focused"
```

The screen reader can then read the whole document by speaking the
`text` field on each `AccessibilityNode`. While in a real screen
reader, this would happen via a browser API, I'll just put this code
in `Browser` to avoid discussing operating system accessibility APIs:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.has_spoken_document = False

    def update_accessibility(self):
        if not self.accessibility_tree: return

        if not self.has_spoken_document:
            self.speak_document()
            self.has_spoken_document = True

    def speak_document(self):
        text = "Here are the document contents: "
        tree_list = tree_to_list(self.accessibility_tree, [])
        for accessibility_node in tree_list:
            new_text = accessibility_node.text
            if new_text:
                text += "\n"  + new_text

        speak_text(text)
```

Speaking the whole document happens only once. But the user might need
feedback as they browse the page. For example, when the user tabs from
one element to another, they may want the new element spoken to them
so they know what they're interacting with.

To do that, the browser thread is going to need to know which element
is focused. Let's add that to the `CommitData`; I'm not going to show
the code, because it's repetitive, but the point is to store the
`Tab`'s `focus` field in the `Browser`'s `tab_focus` field.

Now we need to know when focus changes. The simplest way is to store a
`last_tab_focus` field on `Browser` with the last focused element we actually
spoke out loud:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.last_tab_focus = None
```

Then, if `tab_focus` isn't equal to `last_tab_focus`, we know focus
has moved and it's time to speak the focused node. The change looks like this:


``` {.python}
class Browser:
    def update_accessibility(self):
        # ...
        if self.tab_focus and \
            self.tab_focus != self.last_tab_focus:
            nodes = [node for node in tree_to_list(
                self.accessibility_tree, [])
                        if node.node == self.tab_focus]
            if nodes:
                self.focus_a11y_node = nodes[0]
                self.speak_node(
                    self.focus_a11y_node, "element focused ")
            self.last_tab_focus = self.tab_focus
```

The `speak_node` method is similar to `speak_document` but it only
speaks a single node:

``` {.python}
class Browser:
    def speak_node(self, node, text):
        text += node.text
        if text and node.children and \
            node.children[0].role == "StaticText":
            text += " " + \
            node.children[0].text

        if text:
            speak_text(text)
```

There's a lot more in a real screen reader: landmarks, navigating text
at different granularities, repeating text when requested, and so on.
Those features make various uses of the accessibility tree and the
roles of the various nodes. But since the focus of this book is on the
browser, not the screen reader itself, let's focus for the rest of
this chapter on browser features that support accessibility.

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

Accessible alerts
=================

Scripts do not interact directly with the accessibility tree, much
like they do not interact directly with the display list. However,
sometimes scripts need to inform the screen reader about *why* they're
making certain changes to the page to give screen-reader users a
better experience. The most common example is an alert[^toast] telling
you that some action you just did failed. A screen reader user needs
the alert read to them immediately, no matter where in the document
it's inserted.

[^toast]: Also called a "toast", because it pops up.

The `alert` role addresses this need.[^other-live] A screen reader
will immediately[^alert-css] read an element with that role, no matter
where in the document the user currently is. Note that there aren't
any HTML elements whose default role is `alert`, so this requires
setting the `role` attribute.

[^other-live]: There are also other "live" roles like `status` for
less urgent information or `alertdialog` if the keyboard focus should
move to the alerted element.

[^alert-css]: The alert is only triggered if the element is added to
    the document, has the `alert` role (or the equivalent `aria-live`
    value, `assertive`), and is visible in the layout tree (meaning it
    doesn't have `display: none`), or if its contents change. In this
    chapter, I won't handle all of these cases and just focus on new
    elements with an `alert` role, not changes to contents or CSS.
    
Before we jump to implementation, we first need to make it possible
for scripts to change the `role` attribute. To do that, we'll need to
add support for the `setAttribute` method. On the JavaScript side,
this just calls a browser API:

``` {.javascript}
Node.prototype.setAttribute = function(attr, value) {
    return call_python("setAttribute", this.handle, attr, value);
}
```

The Python side is also quite simple:

``` {.python}
class JSContext:
    def __init__(self, tab):
        # ...
        self.interp.export_function("setAttribute",
            self.setAttribute)
    # ...

    def setAttribute(self, handle, attr, value):
        elt = self.handle_to_node[handle]
        elt.attributes[attr] = value
```

Now we can implement the `alert` role. To do so, we'll search the
accessiblity tree for elements with that role:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.active_alerts = []

    def update_accessibility(self):
        self.active_alerts = [
            node for node in tree_to_list(
                self.accessibility_tree, [])
            if node.role == "alert"
        ]
        # ...
```

Now, we can't just read out every `alert` at every frame; we need to
keep track of what elements have already been read, so we don't read
them twice:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.spoken_alerts = []

    def update_accessibility(self):
        # ...
        for alert in self.active_alerts:
            if alert not in self.spoken_alerts:
                self.speak_node(alert, "New alert")
                self.spoken_alerts.append(alert)
```

Since `spoken_alerts` points into the accessiblity tree, we'll need to
update it any time the accessibility tree is rebuilt, to point into
the new tree. Just like with compositing, we'll use the `node`
pointers in the accessibility tree to match accessibility nodes
between the old and new accessibility tree. Note that, while this
matching *could* be done inside `commit`, we want that method to be as
fast as possible since that method blocks both the browser and main
threads. So it's best to do it in `update_accessibility`:

``` {.python}
class Browser:
    def update_accessibility(self):
        # ...
        new_spoken_alerts = []
        for old_node in self.spoken_alerts:
            new_nodes = [
                node for node in tree_to_list(
                    self.accessibility_tree, [])
                if node.node == old_node.node
                and node.role == "alert"
            ]
            if new_nodes:
                new_spoken_alerts.append(new_nodes[0])
        self.spoken_alerts = new_spoken_alerts
        # ...
```

Note that if a node *loses* the `alert` role, we remove it from
`spoken_alerts`, so that if it later gains the `alert` role back, it
will be spoken again. This sounds like an edge case, but having a
single element for all of your alerts (and just changing its class,
say, from hidden to visible) is a common pattern.

You should now be able to load up [this example][alert-example] and
hear alert text once the button is clicked.

[alert-example]: examples/example14-alert-role.html

[role]: https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Roles

::: {.further}

The `role` attribute is part of the ARIA specification---ARIA stands for
Accessible Rich Internet Applications. You can see in the
name a direct reference to the custom-widget-with-good-accessibility goal
I've presented here. It defines [many]
different attributes; `role` is just one (though an important one). For
example, you can mark a whole subtree of the DOM as
hidden-to-the-accessibility-tree with the `aria-hidden`
attribute;^[This attribute is useful as a way of indicating parts of the DOM
that are not being currently presented to the user (but are still there for
performance or convenience-to-the-developer reasons).] the `aria-label`
attribute specifies the label for elements like buttons.

[many]: https://www.w3.org/TR/wai-aria-1.2/#accessibilityroleandproperties-correspondence

Some of the accessibility problems that ARIA tries to solve stem from a common
root problem: it's very difficult or sometimes impossible to apply a custom
style to the the built-in form control elements. If those were directly
stylable, then there would in these cases be no need for ARIA attributes,
because the built-in elements pre-define all of the necessary accessibility
semantics.

That root problem is in turn because these elements have somewhat magical layout
and paint behavior that is not defined by CSS or HTML (or any other web
specification), and so it's not clear *how* to style them. However, there are
several pseudo-classes available for input controls to
provide limited styling.^[One example is the [`checked`][checked]
pseudo-class.] And recently there has been progress towards defining
additional styles such as [`accent-color`][accent-color] (added in 2021), and
also defining new and fully stylable [form control elements][openui].

[checked]: https://developer.mozilla.org/en-US/docs/Web/CSS/:checked

[accent-color]: https://developer.mozilla.org/en-US/docs/Web/CSS/accent-color

[openui]: https://open-ui.org/#proposals

:::


Mixed voice / visual interaction
================================

Thanks to our work in this chapter, our rendering pipeline now
basically have two different outputs: a display list for visual
interaction, and an accessibility tree for screen-reader interaction.
Many users will use just one or the other. However, it can also be
valuable to use both together. For example, a user might have limited
vision, able to make out the general items on a web page but unable to
read the text. Such a user might use their mouse to navigate the page,
but need the items under the mouse to be read to them by a
screen-reader.

Implementing this feature will require each accessibility node to know
about its geometry on the page. The user could then instruct the
screen-reader to determine which object is under the mouse (this is
called [hit testing][hit-test]) and read it aloud.

[hit-test]: https://chromium.googlesource.com/chromium/src/+/HEAD/docs/accessibility/browser/how_a11y_works_3.md#Hit-testing

Getting access to the geometry is tricky, because the accessibility
tree is generated from the element tree, while the geometry is
accessible in the layout tree. Let's add a `layout_object` pointer to
each `Element` object:[^if-has]

[^if-has]: If it has a layout object, that is. Some `Element`s might
    not, and their `layout_object` pointers will stay `None`.

``` {.python}
class Element:
    def __init__(self, tag, attributes, parent):
        # ...
        self.layout_object = None

class Text:
    def __init__(self, text, parent):
        # ...
        self.layout_object = None
```

Now, when we construct a layout object, we can fill in the
`layout_object` field of its `Element`. In `BlockLayout`, it looks
like this:

``` {.python}
class Element:
    
class BlockLayout:
    def __init__(self, node, parent, previous):
        # ...
        node.layout_object = self
```

Make sure to add a similar line of code to the constructors for every
other type of layout object.

Now each `AccessibilityNode` can store the layout object's bounds:

``` {.python}
class AccessibilityNode:
    def __init__(self, node):
        # ...
        if node.layout_object:
            self.bounds = absolute_bounds_for_obj(node.layout_object)
        else:
            self.bounds = None
```

Note that I'm using `absolute_bounds_for_obj` here, because the bounds
we're interested in are the absolute coordinates on the screen, after
any transformations like `translate`.

So let's implement the read-on-hover feature. First we need to listen
for mouse move events, which in SDL are called `MOUSEMOTION`:

``` {.python}
if __name__ == "__main__":
    while True:
        if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            # ...
            elif event.type == sdl2.SDL_MOUSEMOTION:
                browser.handle_hover(event.motion)
```

Now the browser should listen to the hovered position, determine if
it's over an accessibility node, and highlight that node. We don't
want to disturb our normal rendering cadence, so in `handle_hover`
we'll save the hover event and then in `composite_raster_and_draw`
we'll react to the hover:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.pending_hover = None

    def handle_hover(self, event):
        if not self.accessibility_is_on:
            return
        self.pending_hover = (event.x, event.y - CHROME_PX)
        self.set_needs_accessibility()
```

When the user hovers over a node, we'll do two things. First, we'll
draw its bounds on the screen; this helps users see what they're
hovering over, plus it's also helpful for debugging. We'll do that in
`paint_draw_list`; we'll start by finding the accessibility node the
user is hovering over:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.hovered_a11y_node = None

    def paint_draw_list(self):
        # ...
        if self.pending_hover:
            (x, y) = self.pending_hover
            a11y_node = self.accessibility_tree.hit_test(x, y)
```

The acronym `a11y`, with an "a", the number 11, and a "y", is a common
shorthand for the word "accessibility".[^why-11] The `hit_test`
function I'm calling is similar to code we wrote [many chapters
ago](chrome.md#click-handling) to handle clicks, except of course that
it is searching a different tree:

[^why-11]: The number "11" refers to the number of letters we're
    eliding from "accessibility".

``` {.python}
class AccessibilityNode:
    def hit_test(self, x, y):
        for node in tree_to_list(self, []):
            if node.bounds.intersects(x, y):
                return node
```

Once we've done the hit test and we know what node the user is
hovering over, we can save that on the `Browser` (so that the outline
persists between frames) and draw an outline:

``` {.python}
class Browser:
    def paint_draw_list(self):
        if self.pending_hover:
            # ...
            if a11y_node:
                self.hovered_a11y_node = a11y_node
            self.pending_hover = None
```

Finally, we can draw the outline at the end of `paint_draw_list`:

``` {.python}
class Browser:
    def paint_draw_list(self):
        # ...
        if self.hovered_a11y_node:
            self.draw_list.append(DrawOutline(
                self.hovered_a11y_node.bounds,
                "white" if self.dark_mode else "black", 2))
```

Note that the color of the outline depends on whether or not dark mode
is on, to try to ensure high contrast.

So now we have an outline drawn. But we additionally want to speak
whether the user is hovering over. To do that we'll need another flag,
`needs_speak_hovered_node`, which we'll set whenever hover moves from
one element to another:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.needs_speak_hovered_node = False

    def paint_draw_list(self):
        if self.pending_hover:
            if a11y_node:
                if not self.hovered_a11y_node or \
                    a11y_node.node != self.hovered_a11y_node.node:
                    self.needs_speak_hovered_node = True
                # ...
```

The ugly conditional is necessary to handle two cases: either hovering
over an object when nothing was previously hovered over, or moving the
mouse from one object onto another. We set the flag in either case,
and then use that flag in `update_accessibility`:

``` {.python}
class Browser:
    def update_accessibility(self):
        # ...
        if self.needs_speak_hovered_node:
            self.speak_node(self.hovered_a11y_node, "Hit test ")
        self.needs_speak_hovered_node = False
```

You should now be able to turn on accessibility mode and move your
mouse over the page to get both visual and auditory feedback about
what you're hovering on!

::: {.further}

The accessibility tree plays a key role in the interface between
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
visible browser tab has become necessary. That's because OS accessibility
APIs are generally synchronous, and it's not possible to synchronously stop
the browser and tab at the same time to figure out how to respond. See
[here][chrome-mp-a11y] for a more
detailed description of the challenge and how Chromium deals with it.

[chrome-mp]: https://www.chromium.org/developers/design-documents/multi-process-architecture/

[chrome-mp-a11y]: https://chromium.googlesource.com/chromium/src/+/HEAD/docs/accessibility/browser/how_a11y_works_2.md

In addition, defining this tree in a specification is a means to encourage
interoperability between browsers. This is critically important---imagine how
frustrating it would be if a web site doesn't work in your chosen browser just
because it happens to interpret accessibility slightly differently than another
one! This might force a user to constantly switch browsers in the hope of
finding one that works well on any particular site, and which one does
may be unpredictable. Interoperability is also important for web site
authors who would otherwise have to constantly test everything in every
browser.

:::


Summary
=======

This chapter introduces accessibility---features to ensure *all* users can
access and interact with web sites---then showed how to solve several of
the most common accessibility problems in browsers. The key takeaways are:

* Built-in accessibility is possible because of the semantic and declarative
nature of HTML.

* There are many accessibility use cases, accessibility features
often serve multiple needs, and almost everyone benefits from these features
in one way or another.

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

* *High-contrast mode*: Implement high-contrast [forced-colors] mode. As part
of this, draw a rectangular *backplate* behind all lines of text in order to
ensure that there is sufficient contrast (as [defined][contrast] by the WCAG
specification) between  foreground and background colors. Also check the
contrast of the default style sheets I provided in this chapter---do they meet
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

* *`:hover` pseudoclass*: There is a pseudoclass for generic mouse
[hover][hover-pseudo] events (it's unrelated to accessibility). Implement it
by sending along mouse hover events to the active `Tab` and hit testing
to find out which element is hovered. Try to do so by avoiding a [forced
layout][forced-layout-hit-test]; one way to do that is to store a
`pending_hover` on the `Tab` and running the hit test at the right time during
`render` (which will be after layout), and then doing *another* render to
invalidate the hovered element's style.

[forced-layout-hit-test]: https://browser.engineering/scheduling.html#threaded-style-and-layout

[hover-pseudo]: https://developer.mozilla.org/en-US/docs/Web/CSS/:hover

* *Find-in-page*: Yet another accessibility feature is searching for
text within a web page. Implement this feature. A simple approach might be to
binding it to `ctrl-f` and then interpreting subsequent keyboard input
as the text to search for, and ended by pressing `esc`. Add an internal
pseudo-class for the selected element so that it can be highlighted
visually. You don't need to implement matching text across multiple
`InlineLayout` elements (in general, find-in-page and other [selection]
APIs are quite complicated).

[selection]: https://developer.mozilla.org/en-US/docs/Web/API/Selection

*  *focus-visible*: In some cases, showing a focus ring around an element makes
    sense only with some input modes. For example if an `<a>` element has focus
    and the user achieved that focus with keyboard tabbing, it makes sense to
    show a focus ring around it, because otherwise the user cannot know that it
    was focused. But if the user causes the focus by clicking on it, then
    arguably there is no reason to show the focus ring, because if the user
    could click with a mouse, they probably know which element it was already.
    Because of this, many users also find a focus ring created by mouse click
    distracting, redundant or ugly.

    For this reason, real browsers by default do not create a focus ring for
    such elements on mouse click. On the other hand, they do show one if
    focus was caused by keyboard input. Further, whether the mouse click causes
    a focus ring may depend on the element---an `<input>` element still receives
    a focus ring on a mouse click, because it's still useful for the user to
    know that subsequent keyboard typing will go into that element.

    As you can see, there are a number of heuristics and rules that go into the
    choice of focus ring. For this reason, browsers have in recent years added
    the [`:focus-visible`][focus-visible] pseudo-class, which applies only if
    the element is focused *and* the browser would have drawn a focus ring
    (the focus ring would have been *visible*, hence the name). This lets
    custom widgets change focus ring styling without losing the useful browser
    heuristics I mentioned above.

    Implement browser heuristics to not show a focus ring on an `<a>` element if
    focus occured due to a mouse click, and add the `:focus-visible`
    pseudo-class. <a href="examples/example14-focus.html">This example</a>
    should show the difference between mouse and keyboard interaction.

[focus-visible]: https://developer.mozilla.org/en-US/docs/Web/CSS/:focus-visible

*   *Width media queries*: Zooming in or out causes the width of the page in CSS
    pixels to change. That means that sometimes elements that used to fit
    comfortably on the page no longer do so, because they become too large. The
    browser tries to flow those elements onto new lines, but sometimes that is
    not possible because of the structure of the content, such as with a table
    or grid that can't automatically be broken into multiple lines.

    Just like the other accessibility features can be customized, so can
    zoom.[^responsive-width-size]
    For example, a media query such as `max-width` can be used to change the
    default number of columns in these tables or grids.[^table-grid] A simple
    example that demonstrates `max-width` media queries is below; in this
    example, the text becomes green if the width of the viewport in CSS pixels
    is `700px` or less:

        @media (max-width:700px) {
        * { color: green }
        }

    Implement this media query. Our browser starts out with a default width of
    `800px`, so zooming in a few times should trigger this media query; <a
    href="examples/example14-maxwidth-media.html">click here</a> to see the
    example in action.

[^table-grid]: Note that [tables][table-css] and [grids][grid-css] are real
browser features we have not implemented. To test out such examples you'll have
to try on a real browser.

[table-css]: https://developer.mozilla.org/en-US/docs/Learn/CSS/Building_blocks/Styling_tables
[grid-css]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Grid_Layout

[^responsive-width-size]: The `max-width` media query is indeed a way to
customize behavior on zoom, but most developers think of it instead as a way to
customize according to the width and height of the browser viewport pre-zoom,
which it's also useful for. After all, users can resize a desktop browser
window to any size they like, and mobile and tablet devices have a wide variety
of sizes. Developers often use such media queries to create a "mobile"
or "tablet" layout of web sites; this general technique is called
[responsive design][responsive-design], which is about designing websites to
work well on any kind of browser screens and contexts. Responsive design can be
viewed as a kind of accessibility.

[responsive-design]: https://developer.mozilla.org/en-US/docs/Learn/CSS/CSS_layout/Responsive_Design

* `Element.focus`: Implement the JavaScript [`focus`][focus-el] method on DOM
  elements, including the option to prevent scrolling.]
