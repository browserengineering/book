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
possible to interact with web pages by touch, keyboard, or voice.

[ua]: intro.md#the-role-of-the-browser

[declarative]: intro.md#browser-code-concepts

[a11y]: https://developer.mozilla.org/en-US/docs/Learn/Accessibility/What_is_accessibility

What is Accessibility?
======================

Accessibility\index{accessibility} means that the user can change or
customize how they interact with a web page in order to make it easier to
use.[^other-defs] The web's uniquely flexible
core technologies mean that browsers offer a lot of accessibility
features[^not-just-screen-reader] that allow a user to customize the
rendering of a web page, as well as interact with a
web page with their keyboard, by voice, or using some kind of helper
software.

[^other-defs]: This definition takes the browser's point of view.
    Accessibility can also be defined from the developer's point of
    view, [in which case][mdn-def] it's about ways to make your web
    pages easy to use for as many people as possible.

[mdn-def]: https://developer.mozilla.org/en-US/docs/Learn/Accessibility/What_is_accessibility

[^not-just-screen-reader]: Too often, people take "accessibility" to
    mean "screen reader support", but this is just one way a user may
    want to interact with a web page.

The reasons for customizing, of course, are as diverse as the customizations
themselves. The World Health Organization
[found][who-fact-sheet] that as much as 15% of the world population have some
form of disability, and many of them are severe or permanent. Nearly all of
them can benefit greatly from the accessibility features described in this
chapter. The more severe the disability for a particular person, the more
critically important these features become for them.

[who-fact-sheet]: https://www.who.int/publications/i/item/9789241564182

Some needs for accessibility come and go over time. For example, when my son was
born,[^pavel] my wife and I alternated time taking care of the baby and I ended
up spending a lot of time working at night. To maximize precious sleep, I
wanted the screen to be less bright, and was thankful that many websites offer
a dark mode. Later, I found that taking notes by voice was convenient when my
hands were busy holding the baby. And when I was trying to put the baby to
sleep, muting the TV and reading the closed captions turned out to be the best
way of watching movies.

[^pavel]: This is Pavel speaking.

The underlying reasons for using these accessibility tools were
temporary; but other uses may last longer, or be permanent. I'm
ever-grateful, for example, for [curb cuts][curb-cut], which make it
much more convenient to go on walks with a
stroller.[^toddler-curb-cut] And there's a good chance that, like many
of my relatives, my eyesight will worsen as I age and I'll need to set
my computer to a permanently larger text size. For more severe and
permanent disabilities, there are advanced tools like [screen
readers][screen-reader].[^for-now] These take time to learn and use
effectively, but are transformative for those who need them.

[curb-cut]: https://en.wikipedia.org/wiki/Curb_cut

[^toddler-curb-cut]: And even though my son has now started walking on
    his own, he's still small enough that walking up a curb without a
    curb cut is difficult for him.
    
[screen-reader]: https://www.afb.org/blindness-and-low-vision/using-technology/assistive-technology-products/screen-readers
    
[^for-now]: Perhaps software assistants will become more widespread as
technology improves, mediating between the user and web pages, and
will one day no longer primarily be a screen reader accessibility
technology. Password managers and form autofill agents are already
somewhat like this, and in many cases use the same browser APIs as
screen readers.

Accessibility covers the whole spectrum, from minor accommodations to
advanced accessibility tools.[^moral]
But a key lesson of all kinds of accessibility work, physical and
digital, is that once an accessibility tool is built, creative people
find that it helps in all kinds of situations unforeseen by the tool's
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
that birthed the web: user control, multimodal content, and
interoperability. These principles allowed the web to be accessible to
all types of browsers and operating systems, and *these same
principles* likewise make the web accessible to people of all types
and abilities.

::: {.further}
In the United States, the United Kingdom, the European Union, and many other countries,
website accessibility is in many cases legally required. For example,
United States Government websites are required to be accessible under
[Section 508][sec508] of the [Rehabilitation Act Amendments of
1973 (with amendments added later)][rehab-act], and associated
[regulations][a11yreg]. Non-government websites
are also required to be accessible under the [Americans with
Disabilities Act][ada], though it's [not yet clear][ada-unclear]
exactly what that legal requirement means in practice, since it's
mostly being decided through the courts. In the UK, the [Equality Act
2010][uk-a11y] established similar rules for websites, with stricter
rules for government websites added in 2018. A similar law in the
European Union is the [European Accessibility Act][europe-a11y].
:::

[sec508]: https://www.access-board.gov/law/ra.html#section-508-federal-electronic-and-information-technology
[rehab-act]: https://www.access-board.gov/law/ra.html
[ada]: https://www.ada.gov/ada_intro.htm
[a11yreg]: https://www.access-board.gov/ict/
[ada-unclear]: https://www.americanbar.org/groups/law_practice/publications/law_practice_magazine/2022/jf22/vu-launey-egan/
[uk-a11y]: https://www.siteimprove.com/glossary/uk-accessibility-laws/
[europe-a11y]: https://ec.europa.eu/social/main.jsp?catId=1202

Zoom
====

Let's start with the simplest accessibility problem: text on the
screen that is too small to read. It's a problem many of us will face
sooner or later, and is possibly the most common user disability issue.
The simplest and most effective way to address this is by increasing font
and element sizes. This approach is called *zoom*,[^zoom]\index{zoom}
which means to lay out the page as if all of the CSS sizes were increased or
decreased by a specified factor.

[^zoom]: The word zoom evokes an analogy to a camera zooming in, but
it is not the same, because zoom causes layout. *Pinch zoom*, on
the other hand, is just like a camera and does not cause layout.

To implement it, we first need a way to trigger zooming. On most
browsers, that's done with the `Ctrl-+`, `Ctrl--`, and `Ctrl-0`
keys; using the `Ctrl` modifier key means you can type a `+`, `-`, or
`0` into a text entry without triggering the zoom function.

To handle modifier keys, we'll need to listen to both "key down" and
"key up" events in the event loop, and store whether the `Ctrl` key is pressed:

``` {.python}
def mainloop(browser):
    # ...
    ctrl_down = False
    while True:
		if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
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
def mainloop(browser):
    while True:
		if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            elif event.type == sdl2.SDL_KEYDOWN:
                if ctrl_down:
                     if event.key.keysym.sym == sdl2.SDLK_EQUALS:
                         browser.increment_zoom(True)
                     elif event.key.keysym.sym == sdl2.SDLK_MINUS:
                         browser.increment_zoom(False)
                     elif event.key.keysym.sym == sdl2.SDLK_0:
                         browser.reset_zoom()
                # ...
```

Here, the argument to `increment_zoom` is whether we should increment
(`True`) or decrement (`False`).

The `Browser` code just delegates to the `Tab`, via a main thread task:

``` {.python}
class Browser:
	# ...
    def increment_zoom(self, increment):
        task = Task(self.active_tab.zoom_by, increment)
        self.active_tab.task_runner.schedule_task(task)

    def reset_zoom(self):
        task = Task(self.active_tab.reset_zoom)
        self.active_tab.task_runner.schedule_task(task)
```

Finally, the `Tab` responds to these commands by adjusting a new
`zoom` property, which starts at `1` and acts as a
multiplier for all "CSS sizes" on the web page:[^browser-chrome]

[^browser-chrome]: Zoom typically does not change the size of
elements of the browser chrome. Browsers *can* do that too, but it's
usually triggered by a global OS setting.

``` {.python}
class Tab:
    def __init__(self, browser, tab_height):
    	# ...
    	self.zoom = 1

    def zoom_by(self, increment):
        if increment:
            self.zoom *= 1.1
            self.scroll *= 1.1
        else:
            self.zoom *= 1/1.1
            self.scroll *= 1/1.1
        self.scroll_changed_in_tab = True
        self.set_needs_render()

    def reset_zoom(self):
        self.scroll /= self.zoom
        self.zoom = 1
        self.scroll_changed_in_tab = True
        self.set_needs_render()
```

Note that we need to set the `needs_render` flag when we zoom to
redraw the screen after zooming is complete. Also note that when we
zoom the page we also need to adjust the scroll
position,[^zoom-scroll] and reset the zoom level when we
navigate to a new page:

[^zoom-scroll]: In a real browser, adjusting the scroll position when
    zooming is more complex than just multiplying. That's because zoom
    not only changes the heights of individual lines of text, but also
    changes line breaking, meaning more or fewer lines of text. This
    means there's no easy correspondence between old and new scroll
    positions. Most real browsers implement a much more general algorithm called [scroll anchoring](https://drafts.csswg.org/css-scroll-anchoring-1/) that handles all kinds of changes beyond just zoom.

``` {.python}
class Tab:
    def load(self, url, payload=None):
        self.zoom = 1
        # ...
```

The `zoom` factor is supposed to multiply all CSS sizes, so we'll need
access to it during layout. There are a few ways to do this, but one easy way
is just to pass it as a parameter to `layout` for `DocumentLayout`:

``` {.python}
class DocumentLayout:
    def layout(self, zoom):
        self.zoom = zoom
        child = BlockLayout(self.node, self, None)
        # ...
```

``` {.python}
class Tab:
    def render(self):
        if self.needs_layout:
            # ...
            self.document.layout(self.zoom)
            # ...
```

Every other layout object can also have a `zoom` field, copied from
its parent in `layout`. Here's `BlockLayout`; the other layout classes
should do the same:

``` {.python}
class BlockLayout:
    def layout(self):
        self.zoom = self.parent.zoom
        # ...
```

Various methods now need to scale their font sizes to account for
`zoom`. Since scaling by `zoom` is a common operation, let's wrap it
in a helper method, `dpx`:[^dpx-name]

[^dpx-name]: Normally, `dpx` would be a terrible function name, being
    short and cryptic. But we'll be calling this function a lot, mixed
    in with mathematical operations, and it'll be convenient for it
    not to take up too much space.

``` {.python}
def dpx(css_px, zoom):
    return css_px * zoom
```

\index{device pixel ratio}
Think of `dpx` not as a simple helper method, but as a unit
conversion from a *CSS pixel* (the units specified in a CSS declaration)
to a *device pixel* (what's actually drawn on the screen). In a real
browser, this method could also account for differences like high-DPI
displays.

We'll do this conversion to adjust the font sizes in the `text` and
`input` methods for `BlockLayout`, and in `InputLayout`:

``` {.python}
class BlockLayout:
    def word(self, node, word):
    	# ...
        px_size = float(node.style["font-size"][:-2])
        size = dpx(px_size * 0.75, self.zoom)
    	# ...

    def input(self, node):
        # ...
        px_size = float(node.style["font-size"][:-2])
        size = dpx(px_size * 0.75, self.zoom)
    	# ...
```

``` {.python expected=False}
class InputLayout:
    def layout(self):
        # ...
        px_size = float(self.node.style["font-size"][:-2])
        size = dpx(px_size * 0.75, self.zoom)
    	# ...
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
    def layout(self):
    	# ...
        px_size = float(self.node.style["font-size"][:-2])
        size = dpx(px_size * 0.75, self.zoom)
```

And the fixed `INPUT_WIDTH_PX` for text boxes:

``` {.python }
class BlockLayout:
	# ...
    def input(self, node):
        w = dpx(INPUT_WIDTH_PX, self.zoom)	
```

Finally, one tricky place we need to adjust for zoom is inside
`DocumentLayout`. Here there are two sets of lengths: the overall
`WIDTH`, and the `HSTEP`/`VSTEP` padding around the edges of the page.
The `WIDTH` comes from the size of the application window itself, so
that's measured in device pixels and doesn't need to be converted. But
the `HSTEP`/`VSTEP` is part of the page's layout, so it's in CSS
pixels and *does* need to be converted:

``` {.python}
class DocumentLayout:
    def layout(self, zoom):
    	# ...
        self.width = WIDTH - 2 * dpx(HSTEP, self.zoom)
        self.x = dpx(HSTEP, self.zoom)
        self.y = dpx(VSTEP, self.zoom)
        child.layout()
        self.height = child.height
```

Now try it out. All of the fonts should get about 10% bigger each time
you press `Ctrl-+`, and shrink by 10% when you press `Ctrl--`. The
bigger text should still wrap appropriately at the edge of the screen,
and CSS lengths should be scaled just like the text is. This is great
for reading text more easily.

::: {.print-only}
Here is an example of some
text before zoom:^[No book on the web would be complete without some
good old [Lorem ipsum][lorem-ipsum]!] 
:::

::: {.transclude .html .print-only}
www/examples/example14-line-breaking.html
:::

::: {.web-only}

[Here is an example](examples/example14-line-breaking.html) of some
text before zoom.^[No book on the web would be complete without some
good old [Lorem ipsum][lorem-ipsum]!]

:::

This should render as shown in Figure 1, while Figure 2 shows how it should
look after a 2× zoom. Note how not only are the words twice
as big, but the lines wrap at different words, just as desired.

[lorem-ipsum]: https://en.wikipedia.org/wiki/Lorem_ipsum

::: {.center}
![Figure 1: Example of line breaking before zoom.](examples/example14-line-breaking-unzoomed.png)
:::

::: {.center}
![Figure 2: Example of line breaking after zoom.](examples/example14-line-breaking-zoomed.png)
:::

::: {.further}
On high-resolution screens, CSS pixels are scaled by both zoom and a
[`devicePixelRatio`][dpr] factor.[^js-dpr] This factor scales device
pixels so that there are approximately 96 CSS [pixels per inch][ppi]
(which a lot
of old-school desktop displays had). For example, the original iPhone
had 163 pixels per inch; the browser on that device used a
`devicePixelRatio` of 2, so that 96 CSS pixels corresponds to 192
device pixels or about 1.17 inches.[^non-pixel-dpr] This scaling is
especially tricky when a device is connected to multiple displays: a
window may switch from a low-resolution to a high-resolution display
(thus changing `devicePixelRatio`) or even be split across two
displays with different resolutions.
:::

[dpr]: https://developer.mozilla.org/en-US/docs/Web/API/Window/devicePixelRatio

[ppi]: https://en.wikipedia.org/wiki/Dots_per_inch

[zoom-css]: https://developer.mozilla.org/en-US/docs/Web/CSS/zoom

[^js-dpr]: Strictly speaking, the JavaScript variable called
`devicePixelRatio` is the product of the device-specific and
zoom-based scaling factors.

[^non-pixel-dpr]: Typically the `devicePixelRatio` is rounded to an
integer because that tends to make text and layout look crisper, but
this isn't required, and as pixel densities increase it becomes less
and less important. For example, the Pixelbook Go I'm using to write
this book, with a resolution of 166 pixels per inch, has a ratio of
1.25. The choice of ratio for a given screen is somewhat arbitrary.

Dark Mode
=========

Another useful visual change is using darker colors to help users who
are extra sensitive to light, use their device at night, or who just
prefer a darker color scheme. This browser *dark mode* feature should
switch both the browser chrome and the web page itself to use white
text on a black background, and otherwise adjust background colors to
be darker.[^dark-mode-a11y-origins]

[^dark-mode-a11y-origins]: These days, dark mode has hit the mainstream. It's
supported by pretty much all operating systems, browsers, and popular
apps, and many people enable it as a personal preference. But it was an
accessibility feature, often called high contrast or color filtering
mode, long before then.
Many other technologies, including text-to-speech, optical character
recognition, on-screen
keyboards, and voice control were also pioneered by accessibility engineers
before becoming widely used.

We'll trigger dark mode in the event loop with `Ctrl-d`:

``` {.python}
def mainloop(browser):
    while True:
        if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            elif event.type == sdl2.SDL_KEYDOWN:
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
    def __init__(self):
        # ...
        self.dark_mode = False

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
```

Now we just need to flip all the colors in `raster_chrome` when
`dark_mode` is set. Let's store the foreground and background colors in
variables we can reuse:

``` {.python}
class Browser:
    def raster_chrome(self):
        if self.dark_mode:
            background_color = skia.ColorBLACK
        else:
            background_color = skia.ColorWHITE
        canvas.clear(background_color)
        # ...
```

Similarly, in `paint` on `Chrome`, we need to use the right foreground
color:

``` {.python}
class Chrome:
    def paint(self):
        if self.browser.dark_mode:
            color = "white"
        else:
            color = "black"
```

Then we just need to use `color` instead of `black` everywhere. Make
that change in `paint`.[^more-colors]

[^more-colors]: Of course, a full-featured browser's chrome has many
    more buttons and colors to adjust than our browser's. Most
    browsers support a theming system that stores all the relevant
    colors and images, and dark mode switches the browser from one
    theme to another.
    
Now, we want the web page content to change from light mode to dark
mode as well. To start, let's inform the `Tab` when the user requests
dark mode:

``` {.python}
class Browser:
    # ...
    def toggle_dark_mode(self):
        # ...
        self.dark_mode = not self.dark_mode
        task = Task(self.active_tab.set_dark_mode, self.dark_mode)
        self.active_tab.task_runner.schedule_task(task)
```

And in `Tab`:

``` {.python}
class Tab:
    def __init__(self, browser, tab_height):
        # ...
        self.dark_mode = browser.dark_mode

    def set_dark_mode(self, val):
        self.dark_mode = val
        self.set_needs_render()
```

Note that we need to re-render the page when the dark mode setting is
flipped, so that the user actually sees the new colors. On that note,
we also need to set dark mode when changing tabs, since all tabs should
be either dark or light:

``` {.python}
class Browser:
   def set_active_tab(self, tab):
        # ...
        task = Task(self.active_tab.set_dark_mode, self.dark_mode)
        self.active_tab.task_runner.schedule_task(task)
```

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
white text on a black background, as in Figure 3.

::: {.center}
![Figure 3: Example of dark mode rendering of text.](examples/example14-dark-mode.png)
:::

::: {.further}

The browser really should  not be changing colors on unsuspecting pages; that
could have terrible readability outcomes if the page's theme conflicted!
Instead web pages [indicate support][dark-mode-post] for dark mode using the
`color-scheme` [`meta` tag][meta-tag] or [CSS property][css-prop]. Browsers use
the presence of the meta tag to determine whether it's safe to apply dark mode.
Before `color-scheme` was standardized, web pages could in principle offer
alternative color schemes using [alternative style sheets][alt-style], but few
browsers supported it (of the major ones, only Firefox) and it wasn't commonly
used.

[meta-tag]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/meta/name
[css-prop]: https://developer.mozilla.org/en-US/docs/Web/CSS/color-scheme
[alt-style]: https://developer.mozilla.org/en-US/docs/Web/CSS/Alternative_style_sheets
[dark-mode-post]: https://blogs.windows.com/msedgedev/2021/06/16/dark-mode-html-form-controls/

:::

Customizing Dark Mode
=====================

Our simple dark mode implementation works well for pages with just
text on a background. But for a good-looking dark mode, we
also need to adjust all the other colors on the page. For example,
buttons and input elements probably need a darker background color, as
do any colors that the web developer used on the page.

To support this, CSS uses [media queries][mediaquery]. This is a special
syntax that basically wraps some CSS rules in an `if` statement with
some kind of condition; if the condition is true, those CSS rules are
used, but if the condition is false, they are ignored. The
`prefers-color-scheme` condition checks for dark mode. For example,
this CSS will make `<div>`s have a white text on a black background
only in dark mode:


``` {.css .example}
@media (prefers-color-scheme: dark) {
  div { background-color: black; color: white; }
}
```

Web developers can use `prefers-color-scheme` queries in their own
style sheets, adjusting their own choice of colors to fit user
requests, but we can also use a `prefers-color-scheme` media query in
the browser default style sheet to adjust the default colors for links,
buttons, and text entries:

``` {.css}
@media (prefers-color-scheme: dark) {
  a { color: lightblue; }
  input { background-color: #2222FF; }
  button { background-color: #992500; }
}
```

Here I chose very specific hexadecimal colors that preserve the general color
scheme of blue and orange, but ensure maximum contrast with white foreground
text so they are easy to read. It's important to choose colors that ensure
maximum contrast (an ["AAA"][AAA] rating). [This tool][contrast-tool] is 
handy for checking the contrast of foreground and background colors.

[AAA]: https://accessibleweb.com/rating/aaa/

[contrast-tool]: https://webaim.org/resources/contrastchecker/

To implement media queries, we'll have to start with parsing this
syntax:

``` {.python replace=pair()/pair(%22)%22)}
class CSSParser:
    def media_query(self):
        self.literal("@")
        assert self.word() == "media"
        self.whitespace()
        self.literal("(")
        self.whitespace()
        prop, val = self.pair([")"])
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
                    if prop == "prefers-color-scheme" and \
                        val in ["dark", "light"]:
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
dark mode only, and `light` for light mode only. This way, the `style`
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

::: {.web-only}

Try your browser on this [web page](examples/example14-focus.html)^[I'll use it
throughout the chapter as the "focus example".] with lots
of links, text entries, and buttons,
and you should now see that in dark mode they also change
color to have a darker background and lighter foreground. It should look like
Figure 4 in dark mode.

:::

::: {.print-only}

Try your browser on [this](https://browser.engineering/examples/example14-focus.html)^[I'll use it throughout the chapter as the
"focus example".] example web page with lots of links, text entries and buttons:

::: {.transclude .html}
www/examples/example14-focus.html
:::

You should now see that in dark mode they also change color to have a darker
background and lighter foreground. It should look like Figure 4 in dark mode.

:::

::: {.center}
![Figure 4: Example of dark mode with forms. See the
`browser.engineering` website for full color.](examples/example14-dark-mode-forms.png)
:::

::: {.further}

Besides `prefers-color-scheme`, web pages can use media queries to
increase or decrease contrast when a user
[`prefers-contrast`][prefer-contrast] or disable unnecessary
animations when a user [`prefers-reduced-motion`][prefer-redmot], both
of which can help users with certain disabilities. Users can also
force the use of a specific, limited palette of colors through their
operating system; web pages can detect this with the
[`forced-colors`][forced-colors] media query or disable it for certain
elements (use with care!) with [`forced-color-adjust`][fc-adjust].

:::

[prefer-contrast]: https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-contrast
[prefer-redmot]: https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion
[forced-colors]: https://developer.mozilla.org/en-US/docs/Web/CSS/@media/forced-colors
[fc-adjust]: https://developer.mozilla.org/en-US/docs/Web/CSS/forced-color-adjust

Keyboard Navigation
===================

Right now, most of our browser's features are triggered using the
mouse,^[Except for scrolling, which is keyboard only.] which is a
problem for users with injuries or disabilities in their hand---and
also a problem for power users that prefer their keyboards. So ideally
every browser feature should be accessible via the keyboard as well as
the mouse. That includes browser chrome interactions like back
navigation, typing a URL, or quitting the browser, and also web page
interactions such as submitting forms, typing in text areas,
navigating links, and selecting items on the page.

Let's start with the browser chrome, since it's the easiest. Here, we need
to allow the user to back-navigate, to type in the address bar, and to
create and cycle through tabs, all with the keyboard. We'll also add a
keyboard shortcut for quitting the browser.[^one-more] Let's make all
these shortcuts in the event loop use the `Ctrl` modifier key so they don't
interfere with normal typing: `Ctrl-Left` to go back, `Ctrl-l` to type in the
address bar, `Ctrl-t` to create a new tab, `Ctrl-Tab` to switch to the
next tab, and `Ctrl-q` to exit the browser:

[^one-more]: Depending on the OS you might also need shortcuts for
minimizing or maximizing the browser window. Those require calling
specialized OS APIs, so I won't implement them.

``` {.python}
def mainloop(browser):
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
                        browser.new_tab(
                            "https://browser.engineering/")
                    elif event.key.keysym.sym == sdl2.SDLK_TAB:
                        browser.cycle_tabs()
                    elif event.key.keysym.sym == sdl2.SDLK_q:
                        browser.handle_quit()
                        sdl2.SDL_Quit()
                        sys.exit()
                        break
```

Here, the `focus_addressbar` and `cycle_tabs` methods are new, but
their contents are just copied from `handle_click`:

``` {.python}
class Chrome:
    def focus_addressbar(self):
        self.focus = "address bar"
        self.address_bar = ""

class Browser:
    def focus_addressbar(self):
        self.lock.acquire(blocking=True)
        self.chrome.focus_addressbar()
        self.set_needs_raster()
        self.lock.release()

    def cycle_tabs(self):
        self.lock.acquire(blocking=True)
        active_idx = self.tabs.index(self.active_tab)
        new_active_idx = (active_idx + 1) % len(self.tabs)
        self.set_active_tab(self.tabs[new_active_idx])
        self.lock.release()
```

Now any clicks in the browser chrome can be replaced with keyboard
actions. But what about clicks in the web page itself? This is
trickier, because web pages can have any number of links. So the
standard solution is letting the user `Tab` through all the clickable
things on the page, and press `Enter` to actually click on
them.[^vimperator]

[^vimperator]: Though it's not the only solution. The old
    [Vimperator][vimperator] browser extension for Firefox and its
    successors instead shows one- or two-letter codes next to each
    clickable element, and lets the user type those codes to activate
    that element.
    
[vimperator]: http://vimperator.org/

We'll implement this by expanding our implementation of *focus*.\index{focus}
We already have a `focus` property on each `Tab` indicating which `input`
element is capturing keyboard input. Let's allow buttons and links to
be focused as well. Of course, they don't capture keyboard input, but
when the user presses `Enter` we'll press the button or navigate to
the link.

We'll start by binding those keys in the event loop:

``` {.python}
def mainloop(browser):
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
`advance_tab` methods:^[Real browsers also support `Shift-Tab` to go
backwards in focus order.]

``` {.python}
class Browser:
    def handle_tab(self):
        self.focus = "content"
        task = Task(self.active_tab.advance_tab)
        self.active_tab.task_runner.schedule_task(task)

    def handle_enter(self):
    	# ...
        elif self.focus == "content":
            task = Task(self.active_tab.enter)
            self.active_tab.task_runner.schedule_task(task)
        # ...
```

Let's start with the `advance_tab` method. Each time it's called, the
browser should advance focus to the next focusable thing. This will
first require a definition of which elements are focusable:

``` {.python}
def is_focusable(node):
    return node.tag in ["input", "button", "a"]

class Tab:
    def advance_tab(self):
        focusable_nodes = [node
            for node in tree_to_list(self.nodes, [])
            if isinstance(node, Element) and is_focusable(node)]
```

Next, in `advance_tab`, we need to find out where the
currently focused element is in this list so we can move focus to the
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
the last focusable node (or if there weren't any focusable nodes
to begin with), we'll unfocus the page and move focus to the address
bar:

``` {.python replace=%20%3d%20focusable_nodes[idx]/_element(focusable_nodes[idx]),%20%3d%20None/_element(None)}
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
with it by pressing `Enter`. Since the exact action they're performing
varies (navigating a link, pressing a button, clearing a text entry),
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
            self.set_needs_render()
        elif elt.tag == "a" and "href" in elt.attributes:
            url = self.url.resolve(elt.attributes["href"])
            self.load(url)
        elif elt.tag == "button":
            while elt:
                if elt.tag == "form" and "action" in elt.attributes:
                    self.submit_form(elt)
                elt = elt.parent
```

All of this activation code is copied from the `click` method on
`Tab`s. Note that hitting `Enter` when focused on a text entry clears
the text entry; in most browsers, it submits the containing form
instead. That quirk is a workaround for our browser
[not implementing][clear-input] the `Backspace` key (Section 8.3).

[clear-input]: forms.md#interacting-with-widgets

The `click` method can now be rewritten to call `activate_element`
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
                return
            elt = elt.parent
```

Also, since now any element can be focused, we need `keypress` to
check that an `input` element is focused before typing into it:

``` {.python}
class Tab:
    def keypress(self, char):
        if self.focus and self.focus.tag == "input":
            if not "value" in self.focus.attributes:
                self.activate_element(self.focus)
            # ...
```

I've called `activate_element` to create an empty `value` attribute.

Similarly, `InputLayout` used to draw a cursor for any focused
element. Now that `button` elements can be focused, it needs to be
more careful:

``` {.python}
class InputLayout:
    def paint(self):
        # ...
        if self.node.is_focused and self.node.tag == "input":
            # ...
        # ...
```

Finally, note that sometimes activating an element submits a form or
navigates to a new page, which means the element we were focused on no
longer exists. We need to make sure to clear focus in this case:

``` {.python}
class Tab:
    def load(self, url, payload=None):
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
    tabindex = int(node.attributes.get("tabindex", "9999999"))
    return 9999999 if tabindex == 0 else tabindex
```

The default value, "9999999", is a hack to make sure that elements
without a `tabindex` attribute sort after ones with the attribute. Now
we can sort by `get_tabindex` in `advance_tab`:

``` {.python}
class Tab:
    def advance_tab(self):
        focusable_nodes = [node
            for node in tree_to_list(self.nodes, [])
            if isinstance(node, Element) and is_focusable(node)]
        focusable_nodes.sort(key=get_tabindex)
        # ...
```

Since Python's sort is "stable", two elements with the same `tabindex`
won't change their relative position in `focusable_nodes`.

Additionally, elements with non-negative `tabindex` are automatically
focusable, even if they aren't a link or a button or a text entry.
That's useful, because that element might listen to the `click` event.
To support this let's first extend `is_focusable` to consider
`tabindex`:

``` {.python}
def is_focusable(node):
    if get_tabindex(node) < 0:
        return False
    elif "tabindex" in node.attributes:
        return True
    else:
        return node.tag in ["input", "button", "a"]
```

If you print out `focusable_nodes` for the
[focus example](examples/example14-focus.html), you should
get this:

``` {.python .output}
[<a tabindex="1" href="/">,
 <button tabindex="2">,
 <div tabindex="3">,
 <div tabindex="12">,
 <input>,
 <a href="http://browser.engineering">]
```

We also need to make sure to send a `click` event when an element is
activated. Note that just like clicking on an element, activating an
element can be canceled from JavaScript using `preventDefault`.

``` {.python}
class Tab:
    def enter(self):
        if not self.focus: return
        if self.js.dispatch_event("click", self.focus): return
        self.activate_element(self.focus)
```

We now have configurable keyboard navigation for both the browser and
the web page content. And it involved writing barely any new code,
instead mostly moving code from existing methods into new standalone
ones. The fact that keyboard navigation simplified, not complicated,
our browser implementation is a common outcome: improving accessibility
often involves generalizing and refining existing concepts, leading to
more maintainable code overall.

::: {.further}

Why send the `click` event when an element is activated, instead of a
special `activate` event? Internet Explorer [did use][onactivate]
a special `activate` event, and other browsers used to send a
[DOMActivate][domactivate] event, but modern standards require
sending the `click` event even if the element was activated via
keyboard, not via a click. This works better when the developers aren't
thinking much about accessibility and only register the `click` event
listener.

:::

[onactivate]: https://docs.microsoft.com/en-us/previous-versions/windows/internet-explorer/ie-developer/platform-apis/aa742710(v=vs.85)
[domactivate]: https://w3c.github.io/uievents/#event-type-DOMActivate

Indicating Focus
================

Thanks to our keyboard shortcuts, users can now reach any link,
button, or text entry from the keyboard. But if you try to use this to
navigate a website, it's a little hard to know which element is
focused when. A visual indication---similar to the cursor we use on
text inputs---would help sighted users know if they've reached the
element they want or if they need to keep hitting `Tab`. In most
browsers, this visual indication is a *focus ring* that outlines the
focused element.

To implement focus rings, we'll use the same mechanism we use to draw
text cursors. Recall that, right now, text cursors are added by
drawing a vertical line in `InputLayout`'s `paint` method. We'll
add a call to `paint_outline` in that method, to draw a rectangle around
the focused element:

``` {.python replace=node.is_focused/outline,%22black%22/color,1/dpx(thickness%2c%20zoom)}
def paint_outline(node, cmds, rect, zoom):
    if not node.is_focused: return
    cmds.append(DrawOutline(rect, "black", 1))
```

Set this `is_focused` flag in a new `focus_element` method that we'll now use
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

Outline painting should happen in `paint_effects`, because it paints on top of
the subtree.

``` {.python}
class InputLayout:
	def paint_effects(self, cmds):
        cmds = paint_visual_effects(self.node, cmds, self.self_rect())
        paint_outline(self.node, cmds, self.self_rect(), self.zoom)
        return cmds
```

I also changed the cursor drawing to only happen if the node is
focused *and* it's an `input` element. Tabbing over to a `button`
element should not draw a cursor!

Unfortunately, handling links is a little more complicated. That's
because one `<a>` element corresponds to multiple `TextLayout`
objects, so there's not just one layout object where we can stick the
code. Moreover, those `TextLayout`s could be split across several
lines, so we might want to draw more than one focus ring. To work
around this, let's draw the focus ring in `LineLayout`. Each
`LineLayout` finds all of its child `TextLayout`s that are focused,
and draws a rectangle around them all.

``` {.python replace=child.node.parent.is_focused/parse_outline(outline_str)}
class LineLayout:
    def paint_effects(self, cmds):
        outline_rect = skia.Rect.MakeEmpty()
        outline_node = None
        for child in self.children:
            if child.node.parent.is_focused:
                outline_rect.join(child.self_rect())
                outline_node = child.node.parent
        if outline_node:
            paint_outline(
                outline_node, cmds, outline_rect, self.zoom)
        return cmds
```

You should also add a `paint_outline` call to `BlockLayout`, since
users can make any element focusable with
`tabindex`.[^wrong-for-nested]

[^wrong-for-nested]: This code does not correctly handle the case of
    text inside an inline element inside another inline element,
    with the outside one focused. You could fix this by walking from
    the `child` to the `LineLayout`'s `node`, checking the
    `is_focused` field along the way. I'm skipping that in the
    interest of expediency.

Now when you `Tab` through a page, you should see the focused element
highlighted with a black outline. And if a link happens to cross
multiple lines, you will see our browser use multiple focus
rectangles to make crystal clear what is being focused on.

Except for one problem: if the focused element is scrolled offscreen,
there is still no way to tell what's focused. To fix this we'll need
to automatically scroll it onto the screen when the user tabs to it.

Doing this is a bit tricky, because determining if the element is
offscreen requires layout. So, instead of scrolling to it immediately,
we'll set a new `needs_focus_scroll` bit on `Tab`:

``` {.python}
class Tab:
    def __init__(self, browser, tab_height):
        # ...
        self.needs_focus_scroll = False

    def focus_element(self, node):
        if node and node != self.focus:
            self.needs_focus_scroll = True
```

Then, `run_animation_frame` can scroll appropriately before resetting the
flag:

``` {.python}
class Tab:
    def run_animation_frame(self, scroll):
        # ...
        if self.needs_focus_scroll and self.focus:
            self.scroll_to(self.focus)
        self.needs_focus_scroll = False
        # ...
```

To actually do the scrolling, we need to find the layout object
corresponding to the focused node:

``` {.python}
class Tab:
    def scroll_to(self, elt):
        objs = [
            obj for obj in tree_to_list(self.document, [])
            if obj.node == self.focus
        ]
        if not objs: return
        obj = objs[0]
```

Then, we scroll to it:

``` {.python}
class Tab:
    def scroll_to(self, elt):
        # ...

        if self.scroll < obj.y < self.scroll + self.tab_height:
            return

        document_height = math.ceil(self.document.height + 2*VSTEP)
        new_scroll = obj.y - SCROLL_STEP
        self.scroll = self.clamp_scroll(new_scroll)
        self.scroll_changed_in_tab = True
```

Here, I'm shifting the scroll position to ensure that the object is
`SCROLL_STEP` pixels from the top of the screen, though a real browser
will likely use different logic for scrolling up versus down.

Focus outlines now basically work, and will even scroll on-screen if you try
it on the [focus example](examples/example14-focus.html). Figure 5 shows what
it looks like after I pressed tab to focus the "this is a link" element.

::: {.center}
![Figure 5: Example of focus outline.](examples/example14-focus-outline.png)
:::

But ideally, the focus indicator should be customizable, so that the web page
author can make sure the focused element stands out. In CSS, that's done with
the `:focus` [pseudo-class][pseudoclass]. Basically, this
means you can write a selector like this:

[pseudoclass]: https://developer.mozilla.org/en-US/docs/Web/CSS/Pseudo-classes

``` {.css .example}
div:focus { ... }
```

And then that selector applies only to `<div>` elements that are
currently focused.[^why-pseudoclass]

[^why-pseudoclass]: It's called a pseudo-class because the syntax is
similar to [class] selectors, except there's no actual `class`
attribute on the matched elements.

[class]: https://developer.mozilla.org/en-US/docs/Web/CSS/Class_selectors

To implement this, we need to parse this new kind of selector. Let's change
`selector` to call a new `simple_selector` subroutine to parse a tag name and a
possible pseudo-class:

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
checks if that's followed by a colon and a pseudo-class name:

``` {.python}
class CSSParser:
    def simple_selector(self):
        out = TagSelector(self.word().casefold())
        if self.i < len(self.s) and self.s[self.i] == ":":
            self.literal(":")
            pseudoclass = self.word().casefold()
            out = PseudoclassSelector(pseudoclass, out)
        return out
```

A `PseudoclassSelector` wraps another selector:

``` {.python}
class PseudoclassSelector:
    def __init__(self, pseudoclass, base):
        self.pseudoclass = pseudoclass
        self.base = base
        self.priority = self.base.priority
```

Matching is straightforward:

``` {.python}
class PseudoclassSelector:
    def matches(self, node):
        if not self.base.matches(node):
            return False
        if self.pseudoclass == "focus":
            return node.is_focused
        else:
            return False
```

Unknown pseudoclasses simply never match anything.

The focused element can now be styled. But ideally we'd also be able to
customize the focus outline itself and not just the element. That can be done
by adding support for the CSS [`outline` property][outline], which looks like
this (for a 3-pixel-thick red outline):[^outline-syntax]

``` {.css .example}
outline: 3px solid red;
```

[outline]: https://developer.mozilla.org/en-US/docs/Web/CSS/outline

[^outline-syntax]: We'll only implement this syntax, but `outline` can
    also take a few other forms.

We can parse that into a thickness and a color:

``` {.python}
def parse_outline(outline_str):
    if not outline_str: return None
    values = outline_str.split(" ")
    if len(values) != 3: return None
    if values[1] != "solid": return None
    return int(values[0][:-2]), values[2]
```

And then paint a parsed outline:

``` {.python}
def paint_outline(node, cmds, rect, zoom):
    outline = parse_outline(node.style.get("outline"))
    if not outline: return
    thickness, color = outline
    cmds.append(DrawOutline(rect, color, dpx(thickness, zoom)))
```

Even better, we can move the default two-pixel black outline
into the browser default style sheet, like this:

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

Finally, change all of our `paint` methods to use `parse_outline` instead of
`is_focused` to draw the outline. Here is `LineLayout`:

``` {.python}
class LineLayout:
    def paint_effects(self, cmds):
        # ...
        for child in self.children:
            outline_str = child.node.parent.style.get("outline")
            if parse_outline(outline_str):
                outline_rect.join(child.self_rect())
                outline_node = child.node.parent
```

For the [focus example](examples/example14-focus.html), the focus outline
of an `<a>` element becomes thicker and red, as in Figure 6.

::: {.center}
![Figure 6: Example of a customized focus outline.](examples/example14-focus-outline-custom.png)
:::

As with dark mode, focus outlines are a case where adding an
accessibility feature meant generalizing existing browser features to
make them more powerful. And once they were generalized, this
generalized form can be made accessible to web page authors, who can
use it for anything they like.

::: {.further}

It's essential that the focus indicator have [good contrast][contrast]
against the underlying web page, so the user can clearly see what
they've tabbed over to. This might [require some care][focus-blog] if
the default focus indicator looks like the page or element background.
For example, it might be best to draw [two outlines][ms-blog], white
and black, to guarantee a visible focus indicator on both dark and
light backgrounds. If you're designing your own, the [Web Content
Accessibility Guidelines][wcag] provides contrast guidance.

:::

[wcag]: https://www.w3.org/WAI/standards-guidelines/wcag/
[contrast]: https://www.w3.org/TR/WCAG21/#contrast-minimum
[focus-blog]: https://darekkay.com/blog/accessible-focus-indicator/
[ms-blog]: https://blogs.windows.com/msedgedev/2019/10/15/form-controls-microsoft-edge-chromium/

The Accessibility Tree
======================

Zoom, dark mode, and focus indicators help users with difficulty
seeing fine details, but if the user can't see the screen at all,^[The
original motivation for screen readers was for blind users, but it's
also sometimes useful for situations where the user shouldn't be
looking at the screen (such as driving), or for devices with no
screen.] they typically use a screen reader instead. The name
kind of explains it all: the screen reader reads the text on the screen
out loud, so that users know what it says without having to see it.

So: what should a screen reader say?
There are basically two big challenges we must overcome.

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

You can see an example[^imagine] of screen reader navigation in the
talk presented in the video shown in Figure 7, specifically the segment
from 2:36--3:54.[^whole-talk]

::: {.web-only .center}
<iframe width="560" height="315" src="https://www.youtube-nocookie.com/embed/qi0tY60Hd6M?start=159" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
:::

::: {.web-only .center}
Figure 7: Accessibility talk available [here].
:::

::: {.print-only .center}
![Figure 7: Accessibility talk available [here](https://www.youtube.com/watch?v=qi0tY60Hd6M&t=159s).](examples/example14-a11y-video-still.png)
:::

[^whole-talk]: The whole talk is recommended; it has great examples of
    using accessibility technology.

[^fast]: Though many people who rely on screen readers learn to listen
    to *much* faster speech, it's still a less informationally dense
    medium than vision.

[^imagine]: I encourage you to test out your operating system's
    built-in screen reader to get a feel for what screen reader
    navigation is like. On macOS, type Cmd-Fn-F5 to turn on Voice
    Over; on Windows, type Win-Ctrl-Enter or Win-Enter to start
    Narrator; on ChromeOS type Ctrl-Alt-z to start ChromeVox. All are
    largely used via keyboard shortcuts that you can look up.
    
To support all this, browsers structure the page as a tree and use that
tree to interact with the screen reader. The higher levels of the tree
represent items like paragraphs, headings, or navigation menus, while
lower levels represent text, links, or buttons.^[Generally speaking, the
OS APIs consume this tree like a data model, and the actual tree and data
model exposed to the OS APIs is platform-specific.]

This probably sounds a lot like HTML---and it is quite similar! But,
just as the HTML tree does not exactly match the layout tree,
there's not an exact match with this tree either. For example, some
HTML elements (like `<div>`) group content for styling that is
meaningless to screen reader users. Alternatively, some HTML elements
may be invisible on the screen,[^invisible-example] but relevant to
screen reader users. The browser therefore builds a separate
[accessibility tree][at]\index{accessibility tree} to support screen
reader navigation.

[at]: https://developer.mozilla.org/en-US/docs/Glossary/Accessibility_tree

[^invisible-example]: For example, using `opacity:0`. There are
several other ways in real browsers that elements can be made
invisible, such as with the `visibility` or `display` CSS properties.

Let's implement an accessibility tree in our browser. It's built in a
rendering phase just after layout:

``` {.python}
class Tab:
    def __init__(self, browser, tab_height):
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
```

The accessibility tree is built out of `AccessibilityNode`s:

``` {.python}
class AccessibilityNode:
    def __init__(self, node):
        self.node = node
        self.children = []
```

The `build` method on `AccessibilityNode` recursively creates the
accessibility tree. To do so, we traverse the HTML tree and, for each
node, determine what "role" it plays in the accessibility tree. Some
elements, like `<div>`, have no role, so don't appear in the
accessibility tree, while elements like `<input>`, `<a>` and
`<button>` have default roles.[^standard] We can compute the role of a
node based on its tag name, or from the special `role` attribute if
that exists:

[^standard]: Roles and default roles are specified in the
[WAI-ARIA standard][aria-roles].

[aria-roles]: https://www.w3.org/TR/wai-aria-1.2/#introroles

``` {.python}
class AccessibilityNode:
    def __init__(self, node):
        # ...
        if isinstance(node, Text):
            if is_focusable(node.parent):
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

To build the accessibility tree, just recursively walk the HTML
tree. Along the way, skip nodes with a `none` role, but still recurse into
their children:

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

Here is the accessibility tree for the
[focus example](examples/example14-focus.html):

``` {.output}
 role=document
   role=button
     role=focusable text
   role=StaticText
   role=textbox
   role=StaticText
   role=link
     role=focusable text
   role=StaticText
   role=textbox
     role=StaticText
   role=focusable
     role=focusable text
   role=StaticText
   role=StaticText
   role=StaticText
   role=StaticText
   role=StaticText
   role=StaticText
   role=StaticText
   role=StaticText
   role=StaticText
   role=StaticText
   role=StaticText
   role=StaticText
   role=StaticText
   role=StaticText
   role=StaticText
   role=StaticText
   role=StaticText
   role=StaticText
   role=focusable
     role=focusable text
   role=link
     role=focusable text
```

The user can now direct the screen reader to walk up or down this
accessibility tree and describe each node or trigger actions on it. Let's
implement that.

::: {.further}

In a multi-process\index{process} browser
([like Chromium][chrome-mp]), there is a browser process that interfaces with
the OS, and render processes for loading web pages. Since screen reader APIs
are synchronous, Chromium [stores two copies][chrome-mp-a11y] of the
accessibility tree, one in the browser and one in each renderer, and
only sends changes between the two. An alternative design, used by
pre-Chromium Microsoft Edge and some other browsers, connects each render
process to accessibility API requests from the operating system.
This removes the need to duplicate the accessibility tree, but exposing
the operating system to individual tabs can lead to security issues.

:::

[chrome-mp]: https://www.chromium.org/developers/design-documents/multi-process-architecture/

[chrome-mp-a11y]: https://chromium.googlesource.com/chromium/src/+/HEAD/docs/accessibility/browser/how_a11y_works_2.md

Screen Readers
==============

Typically, the screen reader is a separate application from the
browser;[^why-diff] the browser communicates with it through
OS-specific APIs. To keep this book platform-independent and demonstrate
more clearly how screen readers interact with the accessibility tree, our
discussion of screen reader support will instead include a minimal
screen reader integrated directly into the browser.

But should our built-in screen reader live in the `Browser` or each `Tab`?
Modern browsers generally talk to screen readers from  something like the
`Browser`, so we'll do that too.^[And therefore the browser thread in our
multithreaded browser.] So the very first thing we need to do is send the
tab's accessibility tree over to the browser thread. That'll be a
straightforward extension of the commit concept introduced in
[Chapter 12][ch12-commit]. First, we'll add the tree to `CommitData`: 

``` {.python replace=accessibility_tree)/accessibility_tree%2c%20focus)}
class CommitData:
    def __init__(self, url, scroll, height, display_list,
            composited_updates, accessibility_tree):
        # ...
        self.accessibility_tree = accessibility_tree
```

Then we send it across in `run_animation_frame`:

``` {.python}
class Tab:
    def run_animation_frame(self, scroll):
        # ...
        commit_data = CommitData(
            self.accessibility_tree,
            # ...
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

Note that I clear the `accessibility_tree` field once it's sent to the
browser thread, much like with the display list, to avoid a data race.

[ch12-commit]: scheduling.html#committing-a-display-list

Now that the tree is in the browser thread, let's implement the screen
reader. We'll use two Python libraries to actually read text out loud:
[`gtts`][gtts] (which wraps the Google [text-to-speech service][tts])
and [`playsound`][playsound]. You can install them using `pip`:

[^why-diff]: Screen readers need to help the user with operating
    system actions such as logging in, starting applications, and
    switching between them, so it makes sense for the screen reader to
    be outside any application and to integrate with them through the
    operating system.

[gtts]: https://pypi.org/project/gTTS/

[tts]: https://cloud.google.com/text-to-speech/docs/apis

[playsound]: https://pypi.org/project/playsound/

``` {.sh}
python3 -m pip install gtts
python3 -m pip install playsound
```

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
console output.
:::

To start with, we'll want a key binding that turns the screen reader
on and off. While real operating systems typically use more obscure
shortcuts, I'll use `Ctrl-a` to turn on the screen reader in the event loop:

``` {.python}
def mainloop(browser):
    while True:
        if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            elif event.type == sdl2.SDL_KEYDOWN:
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

When accessibility is on, the `Browser` should call a new `update_accessibility`
method, which we'll implement in a moment to actually produce sound:

``` {.python}
class Browser:
    def composite_raster_and_draw(self):
        # ...
        if self.needs_accessibility:
            self.update_accessibility()
```

Now, what should the screen reader say? That's not really up to
the browser---the screen reader is a standalone application, often
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
        self.text = ""

    def build(self):
        for child_node in self.node.children:
            self.build_internal(child_node)

        if self.role == "StaticText":
            self.text = repr(self.node.text)
        elif self.role == "focusable text":
            self.text = "Focusable text: " + self.node.text
        elif self.role == "focusable":
            self.text = "Focusable element"
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

        if self.node.is_focused:
            self.text += " is focused"
```

This text construction logic is, of course, pretty naive, but it's
enough to demonstrate the idea. Here is how it works out for the
[focus example](examples/example14-focus.html):

``` {.output}
 role=document text=Document
   role=button text=Button
     role=focusable text text=Focusable text: This is a button
   role=StaticText text='\nThis is an input element: '
   role=textbox text=Input box: 
   role=StaticText text=' and\n'
   role=link text=Link
     role=focusable text text=Focusable text: this is a link.
   role=StaticText text='Not focusable'
   role=textbox text=Input box: custom contents
     role=StaticText text='custom contents'
   role=focusable text=Focusable element
     role=focusable text text=Focusable text: Tabbable element
   role=StaticText text='\n.\n'
   role=StaticText text='\n.\n'
   role=StaticText text='\n.\n'
   role=StaticText text='\n.\n'
   role=StaticText text='\n.\n'
   role=StaticText text='\n.\n'
   role=StaticText text='\n.\n'
   role=StaticText text='\n.\n'
   role=StaticText text='\n.\n'
   role=StaticText text='\n.\n'
   role=StaticText text='\n.\n'
   role=StaticText text='\n.\n'
   role=StaticText text='\n.\n'
   role=StaticText text='\n.\n'
   role=StaticText text='\n.\n'
   role=StaticText text='\n.\n'
   role=StaticText text='\n.\n'
   role=StaticText text='\n.\n'
   role=focusable text=Focusable element
     role=focusable text text=Focusable text: Offscreen
   role=link text=Link
     role=focusable text text=Focusable text: browser.engineering
```

The screen reader can then read the whole document by speaking the
`text` field on each `AccessibilityNode`.

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
is focused. Let's add that to the `CommitData`:

``` {.python}
class CommitData:
    def __init__(self, url, scroll, height, display_list,
                 composited_updates, accessibility_tree, focus):
        # ...
        self.focus = focus
```

Make sure to pass this new argument in `run_animation_frame`. Then, in
`Browser`, we'll need to extract this field and save it to `tab_focus`:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.tab_focus = None

    def commit(self, tab, data):
        self.lock.acquire(blocking=True)
        if tab == self.active_tab:
            # ...
            self.tab_focus = data.focus
        self.lock.release()
```

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
this chapter on additional browser features that support accessibility.

::: {.further}

The accessibility tree isn't just for screen readers. For example,
some users prefer touch output such as a [braille
display][braille-display] instead of or in addition to speech output.
While the output device is quite different, the accessibility tree
would still contain all the information about what content is on the
page, whether it can be interacted with, its state, and so on.
Moreover, by using the same accessibility tree for all output devices,
users who use more than one *assistive technology*\index{assistive
technology} (like a braille display and a screen reader) are sure to
receive consistent information.

:::

[braille-display]: https://en.wikipedia.org/wiki/Refreshable_braille_display

Accessible Alerts
=================

Scripts do not interact directly with the accessibility tree, much
like they do not interact directly with the display list. However,
sometimes scripts need to inform the screen reader about *why* they're
making certain changes to the page to give screen reader users a
better experience. The most common example is an alert[^toast] telling
you that some action you just did failed. A screen reader user needs
the alert read to them immediately, no matter where in the document
it's inserted.

[^toast]: Also called a "toast", because it pops up.

The `alert` role addresses this need. A screen reader
will immediately[^alert-css] read an element with that role, no matter
where in the document the user currently is. Note that there aren't
any HTML elements whose default role is `alert`, so this requires
the page author to explicitly set the `role` attribute.

[^alert-css]: The alert is only triggered if the element is added to
    the document, has the `alert` role (or the equivalent `aria-live`
    value, `assertive`), and is visible in the layout tree (meaning it
    doesn't have `display: none`), or if its contents change. In this
    chapter, I won't handle all of these cases—I'll just focus on new
    elements with an `alert` role, not changes to contents or CSS.
    
On to implementation. We first need to make it possible
for scripts to change the `role` attribute, by
adding support for the `setAttribute` method. On the JavaScript side,
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
        self.tab.set_needs_render()
```

Now we can implement the `alert` role. Search the
accessibility tree for elements with that role:

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

Since `spoken_alerts` points into the accessibility tree, we need to
update it any time the accessibility tree is rebuilt, to point into
the new tree. Just like with compositing, use the `node`
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

::: {.web-only}

You should now be able to load up [this example][alert-example] and
hear alert text once the button is clicked.

[alert-example]: https://browser.engineering/examples/example14-alert-role.html

:::

::: {.print-only}

You should now be able to load up this example and
hear alert text once the button is clicked:^[See the `browser.engineering`
website for the JavaScript source.]

::: {.transclude .html}
www/examples/example14-alert-role.html
:::

:::

[role]: https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Roles

::: {.further}

The `alert` role is an example of what ARIA calls a "live region", a
region of the page which can change as a result of user actions. There
are other roles (like `status` or `alertdialog`), or live regions can
be configured on a more granular level by setting their "politeness"
via the `aria-live` attribute (assertive notifications interrupt the
user, but polite ones don't); what kinds of changes to announce, via
`aria-atomic` and `aria-relevant`; and whether the live region is in a
finished or intermediate state, via `aria-busy`. In addition, `aria-live`
is all that's necessary to create a live region; no role is necessary.

:::

Voice and Visual Interaction
============================

Thanks to our work in this chapter, our rendering pipeline now
basically has two different outputs: a display list for visual
interaction, and an accessibility tree for screen reader interaction.
Many users will use just one or the other. However, it can also be
valuable to use both together. For example, a user might have limited
vision---able to make out the general items on a web page but unable to
read the text. Such a user might use their mouse to navigate the page,
but need the items under the mouse to be read to them by a
screen reader.

Let's try that. Implementing this particular feature requires each
accessibility node to know about its geometry on the page. The user could then
instruct the screen reader to determine which object is under the mouse
(via [hit testing][hit-test]) and read it aloud.

[hit-test]: https://chromium.googlesource.com/chromium/src/+/HEAD/docs/accessibility/browser/how_a11y_works_3.md#Hit-testing

Getting access to the geometry is tricky, because the accessibility
tree is generated from the HTML tree, while the geometry is
accessible in the layout tree. Let's add a `layout_object` pointer to
each `Element` object to help with that:[^if-has]

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
class BlockLayout:
    def __init__(self, node, parent, previous):
        # ...
        node.layout_object = self
```

Make sure to add a similar line of code to the constructors for every other type
of layout object. Each `AccessibilityNode` can then store the layout object's
bounds:

``` {.python}
class AccessibilityNode:
    def __init__(self, node):
        # ...
        self.bounds = self.compute_bounds()

    def compute_bounds(self):
        if self.node.layout_object:
            return [absolute_bounds_for_obj(self.node.layout_object)]
        # ...
```

Note that I'm using `absolute_bounds_for_obj` here, because the bounds we're
interested in are the absolute coordinates on the screen, after any
transformations like `translate`.

However, there is another complication: it may be that `node.layout_object`
is not set; for example, text nodes do not have one.^[And that's OK, because I
chose not to set bounds at all for these nodes, as they are not focusable.]
Likewise, nodes with inline layout generally do not. So we need to walk up the
tree to find the parent with a `BlockLayout` and union all text nodes in all
`LineLayouts` that are children of the current `node`. And because there can be
multiple `LineLayouts` and text nodes, the bounds need to be in an array of
`skia.Rect` objects:

``` {.python}
class AccessibilityNode:
    def compute_bounds(self):
        # ...
        if isinstance(self.node, Text):
            return []
        inline = self.node.parent
        bounds = []
        while not inline.layout_object: inline = inline.parent
        for line in inline.layout_object.children:
            line_bounds = skia.Rect.MakeEmpty()
            for child in line.children:
                if child.node.parent == self.node:
                    line_bounds.join(skia.Rect.MakeXYWH(
                        child.x, child.y, child.width, child.height))
            bounds.append(line_bounds)
        return bounds
```

So let's implement the read-on-hover feature. First we need to listen for mouse
move events in the event loop, which in SDL are called `MOUSEMOTION`:

``` {.python}
def mainloop(browser):
    while True:
        if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            # ...
            elif event.type == sdl2.SDL_MOUSEMOTION:
                browser.handle_hover(event.motion)
```

The browser should listen to the hovered position, determine if
it's over an accessibility node, and highlight that node. We don't
want to disturb the normal rendering cadence, so in `handle_hover`
save the hover event and then in `composite_raster_and_draw`
react to the hover:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.pending_hover = None

    def handle_hover(self, event):
        if not self.accessibility_is_on or \
            not self.accessibility_tree:
            return
        self.pending_hover = (event.x, event.y - self.chrome.bottom)
        self.set_needs_accessibility()
```

When the user hovers over a node, we'll do two things. First,
draw its bounds on the screen; this helps users see what they're
hovering over, plus it's also helpful for debugging. Do that in
`paint_draw_list`; start by finding the accessibility node the
user is hovering over (note the need to take scroll into account):

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.hovered_a11y_node = None

    def paint_draw_list(self):
        # ...
        if self.pending_hover:
            (x, y) = self.pending_hover
            y += self.active_tab_scroll
            a11y_node = self.accessibility_tree.hit_test(x, y)
```

By the way, the acronym `a11y` in `a11y_node`, with an "a", the number 11, and
a "y", is a common shorthand for the word "accessibility".[^why-11] The
`hit_test` function recurses over the accessibility tree:

[^why-11]: The number "11" refers to the number of letters we're
    eliding from "accessibility".

``` {.python}
class AccessibilityNode:
    def contains_point(self, x, y):
        for bound in self.bounds:
            if bound.contains(x, y):
                return True
        return False

    def hit_test(self, x, y):
        node = None
        if self.contains_point(x, y):
            node = self
        for child in self.children:
            res = child.hit_test(x, y)
            if res: node = res
        return node
```

Once the hit test is done and the browser knows what node the user is
hovering over, save this information on the `Browser`---so that the outline
persists between frames---and draw an outline:

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
            for bound in self.hovered_a11y_node.bounds:
                self.draw_list.append(DrawOutline(
                    bound,
                    "white" if self.dark_mode else "black", 2))

```

Note that the color of the outline depends on whether or not dark mode
is on, to ensure high contrast.

So now we have an outline drawn. But we additionally want to speak
what the user is hovering over. To do that we'll need another flag,
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
over an object when nothing was previously hovered, or moving the
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

A common issue is web page authors making custom input
elements and not thinking much about their accessibility. The reason
for this is that built-in input elements are hard to style, so
authors roll their own better-looking ones.

Built-in input elements often involve
several separate pieces, like the path and button in a `file` input,
the check box in a `checkbox` element, or the pop-up menu in a
`select` dropdown, and CSS isn't (yet) good at styling such
"compound" elements, though [pseudo-elements][pseudoelts] such as
`::backdrop` or `::file-selector-button` help.
Perhaps the best solution is [standards][openui] for
new [fully styleable][selectmenu] input elements.

:::

[checked]: https://developer.mozilla.org/en-US/docs/Web/CSS/:checked
[pseudoelts]: https://developer.mozilla.org/en-US/docs/Web/CSS/Pseudo-elements
[accent-color]: https://developer.mozilla.org/en-US/docs/Web/CSS/accent-color
[openui]: https://open-ui.org/#proposals
[selectmenu]: https://blogs.windows.com/msedgedev/2022/05/05/styling-select-elements-for-real/

Summary
=======

This chapter introduces accessibility---features to ensure *all* users can
access and interact with websites---and shows how to solve several of
the most common accessibility problems in browsers. The key takeaways are:

- The semantic and declarative nature of HTML makes accessibility
  features natural extensions.
- Accessibility features often serve multiple needs, and almost
  everyone benefits from these features in one way or another.
- The accessibility tree is similar to the display list and drives
  the browser's interaction with screen readers and other assistive
  technologies.
- New features like dark mode, keyboard navigation, and outlines need
  to be customizable by web page authors to be maximally usable.

::: {.web-only}

Click [here](widgets/lab14-browser.html) to try this chapter's
browser.

:::

Outline
=======

The complete set of functions, classes, and methods in our browser 
should now look something like this:

::: {.web-only .cmd .python .outline html=True}
    python3 infra/outlines.py --html src/lab14.py --template book/outline.txt
:::

::: {.print-only .cmd .python .outline}
    python3 infra/outlines.py src/lab14.py --template book/outline.txt
:::


Exercises
=========

14-1 *Focus ring with good contrast*. Improve the contrast of the focus
indicator by using two outlines, a thicker white one and a thinner
black one, to ensure that there is contrast between the focus ring and
surrounding content.

14-2 *Focus method and events*. Add support for the JavaScript
[`focus()`][focus-method] method
and the corresponding [`focus`][focus-event] and
[`blur`][blur-event] events on DOM elements. Make sure that `focus()`
only has an effect on focusable elements. Be careful:
before reading an element's position, make sure that layout is up to date.

[focus-method]: https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/focus
[focus-event]: https://developer.mozilla.org/en-US/docs/Web/API/Element/focus_event
[blur-event]: https://developer.mozilla.org/en-US/docs/Web/API/Element/blur_event

14-3 *Highlighting elements during read*. The method to read the document
works, but it would be nice to also highlight the element being read as
it happens, in a similar way to how we did it for mouse hover.
Implement that. You may want to replace the `speak_document` method
with an `advance_accessibility` method that moves the accessibility
focus by one node and speaks it.

14-4 *Width media queries*. Zooming in or out causes the width of the page
in CSS pixels to change. That means that sometimes elements that used
to fit comfortably on the page no longer do, and if the page becomes
narrow enough, a different layout may be more appropriate. The
[`max-width` media query][width-mq] allows the developer to style
pages differently based on available width; it is active only if the
width of the page, in CSS pixels, is less than or equal to a given
length.[^responsive-width-size] Implement this media query. Test that
zooming in or out can trigger this media query.

[width-mq]: https://developer.mozilla.org/en-US/docs/Web/CSS/@media/width

[^responsive-width-size]: As you've seen, many accessibility features
also have non-accessibility uses. For example, the `max-width` media
query is indeed a way to customize behavior on zoom, but most
developers think of it instead as a way to customize their
website for different devices, like desktops, tablets, and mobile
devices. This is called [responsive design][responsive-design],
and can be viewed as a kind of accessibility.

[responsive-design]: https://developer.mozilla.org/en-US/docs/Learn/CSS/CSS_layout/Responsive_Design

::: {.web-only}
After completing the exercise,
[this example](examples/example14-maxwidth-media.html) should have green text
on narrow screens.
:::

::: {.print-only}

After completing the exercise, the
[following example](https://browser.engineering/examples/example14-maxwidth-media.html)
should have green text on narrow screens. HTML:

::: {.transclude .html}
www/examples/example14-maxwidth-media.html
:::

CSS:

::: {.transclude .css}
www/examples/example14-maxwidth-media.css
:::
:::

14-5 *Mixed inlines*. Make the focus ring work correctly on nested inline
elements. For example, in `<a>a <b>bold</b> link</a>`, the focus ring
should cover all three words together when the user is focused on the
link, and with multiple rectangles if the inline crosses lines.
However, if the user focuses on a block-level element, such as in
`<div tabindex=2>many<br>lines</div>`, there shouldn't be a focus ring
around each line, but instead the block as a whole.

14-6 *Threaded accessibility*. The accessibility code currently speaks text
on the browser thread, and blocks the browser thread while it speaks.
That's frustrating to use. Solve this by moving the speaking to a new
accessibility thread.

14-7 *High-contrast mode*. Implement high-contrast [forced-colors] mode.
This should replace all colors with one of a small set of
[high-contrast][contrast] colors.

[forced-colors]: https://developer.mozilla.org/en-US/docs/Web/CSS/@media/forced-colors

14-8 *`focus-visible`*. When the user tabs to a link, we probably want to
show a focus indicator, but if the user clicked on it, most browsers
don't---the user knows where the focused element is! And a redundant
focus indicator could be ugly, or distracting. Implement a similar
heuristic. Clicking on a button should focus it, but not show a focus
indicator. (Test this on the [focus example](examples/example14-focus.html)
with a button placed outside a form, so clicking the button doesn't
navigate to a new page.) But both clicking on and tabbing to an input
element should show a focus ring. Also add support for the
[`:focus-visible` pseudo-class][focus-visible]. This applies only if
the element is focused *and* the browser would have drawn a focus ring
(the focus ring would have been *visible*, hence the name). This lets
custom widgets change focus ring styling without losing the useful
browser heuristics I mentioned above.

[focus-visible]: https://developer.mozilla.org/en-US/docs/Web/CSS/:focus-visible

14-9 *OS integration*. Add the [`accessible_output`][os-integ] Python
library and use it to integrate directly with your OS's built-in
screen reader. Try out some of the examples in this chapter and
compare the behavior with a real browser.

[os-integ]: https://pypi.org/project/accessible_output/

14-10 *The `zoom` CSS property*. Add support for the [`zoom`][zoom-property] CSS
property. This exposes the same functionality as the zoom
accessibility feature to web developers, plus it allows applying it only
to designated HTML subtrees.

[zoom-property]: https://developer.mozilla.org/en-US/docs/Web/CSS/zoom
