---
title: Handling Buttons and Links
chapter: 7
prev: styles
next: forms
...

Our toy browser is still missing the key insight of *hypertext*:
documents linked together by hyperlinks. It lets us watch the
waves, but not surf the web. So in this chapter, we'll implement
hyperlinks, an address bar, and the rest of the browser
interface---the part of the browser that decides *which* page we are
looking at.

Where are the links?
====================

The core of the web is the link, so the most important part of the
browser interface is clicking on links. But before we can quite get to
_clicking_ on links, we first need to answer a more fundamental
question: where on the screen _are_ the links? Though paragraphs and
headings have their sizes and positions recorded in the layout tree,
formatted text (like links) does not. We need to fix that.

The big idea is to introduce two new types of layout objects:
`LineLayout` and `TextLayout`. `BlockLayout` will now have
`LineLayout` children for each line of text, which themselves will
contain a `TextLayout` for each word in that line. These new classes
can make the layout tree look different from the HTML tree. So to
avoid surprises, let's look at a simple example:

``` {.html}
<html>
  <body>
    Here is some text that is
    <br>
    spread across multiple lines
  </body>
</html>
```

The text in the `body` element wraps across two lines (because of the
`br` element), so the layout tree will have this structure:

    DocumentLayout
      BlockLayout[block] (html element)
        BlockLayout[inline] (body element)
          LineLayout (first line of text)
            TextLayout ("Here")
            TextLayout ("is")
            TextLayout ("some")
            TextLayout ("text")
            TextLayout ("that")
            TextLayout ("is")
          LineLayout (second line of text)
            TextLayout ("spread")
            TextLayout ("across")
            TextLayout ("multiple")
            TextLayout ("lines")

Note how one `body` element corresponds to two `LineLayout`s, and how
two text nodes turn into a total of ten `TextLayout`s!

Let's get started. Defining `LineLayout` is straightforward:

``` {.python}
class LineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
```

`TextLayout` is only a little more tricky. A single `TextLayout`
refers not to a whole HTML node but to a specific word. That means
`TextLayout` needs an extra argument to know which word that is:

``` {.python}
class TextLayout:
    def __init__(self, node, word, parent, previous):
        self.node = node
        self.word = word
        self.children = []
        self.parent = parent
        self.previous = previous
```

Like the other layout modes, `LineLayout` and `TextLayout` will need
their own `layout` and `paint` methods, but before we get to those we
need to think about how the `LineLayout` and `TextLayout` objects will
be created. That happens during word wrapping.

Let's review [how word wrapping works](text.md) right now.
`BlockLayout` is responsible for word wrapping, inside its `text`
method. That method updates a `line` field, which stores all the words
in the current line. When it's time to go to the next line, it calls
`flush`, which computes the location of the line and each word in it,
and adds all the words to a `display_list` field, which stores all the
words in the whole inline element.

Inside the `text` method, this key line adds a word to the current
line of text:

``` {.python file=lab6 indent=12}
self.line.append((self.cursor_x, word, font, color))
```

We now want to create a `TextLayout` object and add it to a
`LineLayout` object. The `LineLayout`s are children of the
`BlockLayout`, so the current line can be found at the end of the
`children` array:

``` {.python indent=12}
line = self.children[-1]
text = TextLayout(node, word, line, self.previous_word)
line.children.append(text)
self.previous_word = text
```

Note that I needed a new field here, `previous_word`, to keep track of
the previous word in the current line. So we'll need to initialize it
later.

Now let's think about what happens when we reach the end of the line.
The current code calls `flush`, which does stuff like positioning text
and clearing the `line` field. We don't want to do all that---we just
want to create a new `LineLayout` object. So let's use a different
method for that:

``` {.python indent=12}
if self.cursor_x + w > self.width:
    self.new_line()
```

This `new_line` method just creates a new line and resets some fields:

``` {.python indent=4}
def new_line(self):
    self.previous_word = None
    self.cursor_x = 0
    last_line = self.children[-1] if self.children else None
    new_line = LineLayout(self.node, self, last_line)
    self.children.append(new_line)
```

Now there's a lot of fields we're not using. Let's clean them up. In
the core `layout` method, we don't need to initialize the
`display_list` or `cursor_y` or `line` fields, since we won't be using
any of those any more. Instead, we just need to call `new_line` and
`recurse`:

``` {.python indent=4 replace=layout_inline/layout}
def layout(self):
    # ...
    else:
        self.new_line()
        self.recurse(self.node)
```

The `layout` method already recurses into its children to lay them
out, so that part doesn't need any change. And moreover, we can now
compute the height of a paragraph of text by summing the height of its
lines, so this part of the code no longer needs to be different
depending on the layout mode:

``` {.python indent=4}
def layout(self):
    # ...
    self.height = sum([child.height for child in self.children])
```

With the `display_list` gone, we can also remove the part of `paint`
that handles it. Painting all the lines in a paragraph is now just
automatically handled by recursing into the child layout objects. So
by adding `LineLayout` and `TextLayout` we made `BlockLayout` quite a
bit simpler and shared more code between block and inline layout modes.

You might also be tempted to delete the `flush` method, since it's no
longer called from anywhere. But keep it around for just a
moment---we'll need it to write the `layout` method for line and text
objects.

::: {.further}
The layout objects generated by a text node need not even be
consecutive. English containing a Farsi quotation, for example, can
flip from left-to-right to right-to-left in the middle of a line. The
text layout objects end up in a [surprising order][unicode-bidi].
And then there are languages laid out [vertically][mongolian]...
:::

[unicode-bidi]: https://www.w3.org/International/articles/inline-bidi-markup/uba-basics
[mongolian]: https://en.wikipedia.org/wiki/Mongolian_script


Line layout, redux
==================

We're now creating line and text objects, but we still need to lay
them out. Let's start with lines. Lines stack vertically and take up
their parent's full width, so computing `x` and `y` and `width` looks
the same as for our other boxes:[^mixins]

[^mixins]: You could reduce the duplication with some helper methods
    (or even something more elaborate, like mixin classes), but in a
    real browser different layout modes support different kinds of
    extra features (like text direction or margins) and the code looks
    quite different.

``` {.python}
class LineLayout:
    def layout(self):
        self.width = self.parent.width
        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y
        
        # ...
```

Computing height, though, is different---this is where all that logic
to compute maximum ascents, maximum descents, and so on from the old
comes in. We'll want to pilfer the code from the old `flush` method.
First, let's lay out each word:

``` {.python indent=8}
# ...
for word in self.children:
    word.layout()
```

Next, we need to compute the line's baseline based on the maximum
ascent and descent, using basically the same code as the old `flush`
method:

``` {.python indent=8}
# ...
max_ascent = max([word.font.metrics("ascent")
                  for word in self.children])
baseline = self.y + 1.25 * max_ascent
for word in self.children:
    word.y = baseline - word.font.metrics("ascent")
max_descent = max([word.font.metrics("descent")
                   for word in self.children])
```

Note that this code is reading from a `font` field on each word and
writing to each word's `y` field.[^why-no-y] That means that inside
`TextLayout`'s `layout` method, we need to compute `x`, `width`,
and `height`, but also `font`, and not `y`. Remember that for later.

[^why-no-y]: The `y` position could have been computed in
`TextLayout`'s `layout` method---but then that layout method would
have to come *after* the baseline computation, not *before*. Yet
`font` must be computed *before* the baseline computation. A real
browser might resolve this paradox with multi-phase layout, which
we'll [meet later](reflow.md). There are many considerations and
optimizations of this kind that are needed to make text layout super
fast.

Finally, since each line is now a standalone layout object, it needs
to have a height. We compute it from the maximum ascent and descent:

``` {.python indent=8}
# ...
self.height = 1.25 * (max_ascent + max_descent)
```

Ok, so that's line layout. Now let's think about laying out each word.
Recall that there's a few quirks here: we need to compute a `font`
field for each `TextLayout`, but we do not need to compute a `y`
field.

We can compute `font` using the same font-construction code as in
`BlockLayout`:

``` {.python}
class TextLayout:
    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(self.node.style["font-size"][:-2]) * .75)
        self.font = get_font(size, weight, style)
```

Next, we need to compute word's size and `x` position. We use the font
metrics to compute size, and stack words left to right to compute
position.

``` {.python}
class TextLayout:
    def layout(self):
        # ...

        # Do not set self.y!!!
        self.width = self.font.measure(self.word)

        if self.previous:
            space = self.previous.font.measure(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.height = self.font.metrics("linespace")
```

So that's `layout` for `LineLayout` and `TextLayout`. All that's left
is painting. For `LineLayout` we just recurse:

``` {.python}
class LineLayout:
    def paint(self, display_list):
        for child in self.children:
            child.paint(display_list)
```

And each `TextLayout` creates a single `DrawText` call:

``` {.python}
class TextLayout:
    def paint(self, display_list):
        color = self.node.style["color"]
        display_list.append(
            DrawText(self.x, self.y, self.word, self.font, color))
```

So, oof, well, this was quite a bit of refactoring. Take a moment to
test everything---it should look exactly identical to how it did
before we started this refactor. But while you can't see it, there's a
crucial difference: each blue link on the page now has an associated
layout object and its own size and position.

::: {.further}
Actually, text rendering is [*way* more complex][rendering-hates] than
this. [Letters][morx] can transform and overlap, and the user might
want to color certain letters---or parts of letters---a different
color. All of this is possible in HTML, and browsers implement support
for it.
:::

[rendering-hates]: https://gankra.github.io/blah/text-hates-you/
[morx]: https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6morx.html

Click handling
==============

Now that the browser knows where the links are, we start work on
clicking them. In Tk, clicks work just like key presses: you bind an
event handler to a certain event. For click handling that event is
`<Button-1>`, button number 1 being the left button on the mouse.[^1]

[^1]: Button 2 is the middle button; button 3 is the right-hand button.


``` {.python replace=self.click/self.handle_click}
class Browser:
    def __init__(self):
        # ...
        self.window.bind("<Button-1>", self.click)
```

Inside `click`, we want to figure out what link the user has clicked
on. Luckily, the event handler is passed an event object, whose `x`
and `y` fields refer to where the click happened:

``` {.python expected=False}
class Browser:
    def click(self, e):
        x, y = e.x, e.y
```

Now, here, we have to be careful with coordinate systems. Those *x*
and *y* coordinates are relative to the browser window. Since the
canvas is in the top-left corner of the window, those are also the *x*
and *y* coordinates relative to the canvas. We want the coordinates
relative to the web page, so we need to account for scrolling:

``` {.python replace=Browser/Tab,%20e/%20x%2c%20y}
class Browser:
    def click(self, e):
        # ...
        y += self.scroll
```

The next step is to figure out what links or other elements are at
that location. To do that, search through the tree of layout objects:

``` {.python indent=8}
# ...
objs = [obj for obj in tree_to_list(self.document, [])
        if obj.x <= x < obj.x + obj.width
        and obj.y <= y < obj.y + obj.height]
```

Now, normally when you click on some text, you're also clicking on the
paragraph it's in, and the section that that paragraph is in, and so
on. We want the one that's "on top", which is the last object in the
list:[^overlap]

[^overlap]: In a real browser, sibling elements can also overlap each
other, like a dialog that overlaps some text. Web pages can control
which sibling is on top using the `z-index` property. So real browsers
have to compute [stacking contexts][stack-ctx] to resolve what you
actually clicked on.

[stack-ctx]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Positioning/Understanding_z_index/The_stacking_context

``` {.python indent=8}
# ...
if not objs: return
elt = objs[-1].node
```

This `elt` node is the most specific node that was clicked. With a
link, that's usually going to be a text node. But since we want to
know the actual URL the user clicked on, we need to climb back up the
HTML tree to find the link element:

``` {.python indent=8}
# ...
while elt:
    if isinstance(elt, Text):
        pass
    elif elt.tag == "a" and "href" in elt.attributes:
        # ...
    elt = elt.parent
```

I wrote this in a kind of curious way so it's easy to add other types
of clickable things---like text boxes and buttons---in the [next
chapter](forms.md).

Once we find the link element itself, we need to extract the URL and
load it:

``` {.python indent=12}
# ...
elif elt.tag == "a" and "href" in elt.attributes:
    url = self.url.resolve(elt.attributes["href"])
    return self.load(url)
```

Note that when a link has a relative URL, that URL is resolved
relative to the current page, so store the current URL in `load`:

``` {.python replace=Browser/Tab}
class Browser:
    def __init__(self):
        # ...
        self.url = None

    def load(self, url):
        self.url = url
        # ...
```

Try it out! You should now be able to click on links and navigate to
new web pages.

::: {.further}
On mobile devices, a "click" happens over an area, not just at a
single point. Since mobile "taps" are often pretty inaccurate, click
should [use the area information][rect-based] for "hit testing". This
can happen even with a [normal mouse click][hit-test] when the click
is on a rotated or scaled element.
:::

[rect-based]: http://www.chromium.org/developers/design-documents/views-rect-based-targeting
[hit-test]: https://source.chromium.org/chromium/chromium/src/+/main:third_party/blink/renderer/core/layout/hit_test_location.h

Multiple pages
==============

If you're anything like me, the next thing you tried after clicking on
links is middle-clicking them to open in a new tab. Every browser now
has tabbed browsing, and honestly it's a little embarrassing that our
little toy browser doesn't.[^ffx]

[^ffx]: Back in the day, browser tabs were the feature that would
    convince friends and relatives to switch from IE 6 to Firefox.

Fundamentally, tabbed browsing means distinguishing between the
browser itself and tabs that show individual web pages. The canvas the
browser draws to, for example, is shared by all web pages, but the
layout tree and display list are specific to one page. We need to
tease these two types of things apart.

Here's the plan: the `Browser` class will store the window and canvas,
plus a list of `Tab` objects, one per browser tab. Everything else
goes into a new `Tab` class. Since the `Browser` stores the window
and canvas, it handles all of the events, sometimes forwarding it to
the active tab.

Since the `Tab` class is responsible for layout, styling, and
painting, the default style sheet moves to the `Tab` constructor:

``` {.python replace=browser.css/browser6.css}
class Tab:
    def __init__(self):
        with open("browser.css") as f:
            self.default_style_sheet = CSSParser(f.read()).parse()
```

The `load`, `scrolldown`, `click`, and `draw` methods also move to
`Tab`, since that's now where all web-page-specific data lives.

But since the `Browser` controls the canvas and handles events, it
decides when rendering happens and which tab does the drawing. After
all,[^unless-windows] you only want one tab drawing its contents at a
time! So let's remove the `draw` calls from the `load` and
`scrolldown` methods, and in `draw`, let's pass the canvas in as an
argument:

[^unless-windows]: Unless the browser implements multiple windows, of course.

``` {.python}
class Tab:
    def draw(self, canvas):
        # ...
```

Let's also make `draw` not clear the screen. That should be the
`Browser`'s job.

Now let's turn to the `Browser` class. It has to store a list of tabs
and an index into that list for the active tab:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.tabs = []
        self.active_tab = None
```

When it comes to user interaction, think of the `Browser` as "active"
and the `Tab` as "passive". It's the job of the `Browser` is to call
into the tabs as appropriate. So the `Browser` handles all events:

``` {.python}
class Browser:
    def __init__(self):
        self.window.bind("<Down>", self.handle_down)
        self.window.bind("<Button-1>", self.handle_click)
```

Since these events need page-specific information to resolve, these
handler methods just forward the event to the active tab:

``` {.python replace=e.y/e.y%20-%20CHROME_PX}
class Browser:
    def handle_down(self, e):
        self.tabs[self.active_tab].scrolldown()
        self.draw()

    def handle_click(self, e):
        self.tabs[self.active_tab].click(e.x, e.y)
        self.draw()
```

You'll need to tweak the `Tab`'s `scrolldown` and `click` methods:

- `scrolldown` now takes no arguments (instead of an event object)
- `click` now take two coordinates (instead of an event object)

Finally, the `Browser`'s `draw` call also calls into the active tab:

``` {.python}
class Browser:
    def draw(self):
        self.canvas.delete("all")
        self.tabs[self.active_tab].draw(self.canvas)
```

This only draws the active tab, which is how tabs are supposed to
work.

We're basically done splitting `Tab` from `Browser`, and after a
refactor like this we need to test things. To do that, we'll need to
create at least one tab, like this:

``` {.python}
class Browser:
    def load(self, url):
        new_tab = Tab()
        new_tab.load(url)
        self.active_tab = len(self.tabs)
        self.tabs.append(new_tab)
        self.draw()
```

Of course, we need a way for *the user* to switch tabs, create new
ones, and so on. Let's turn to that next.

::: {.further}
Browser tabs first appeared in [SimulBrowse][simulbrowse], which was
a kind of custom UI for the Internet Explorer engine. SimulBrowse
(later renamed to NetCaptor) also had ad blocking and a private
browsing mode. The [old advertisements][netcaptor-ad] are a great
read!
:::

[simulbrowse]: https://en.wikipedia.org/wiki/NetCaptor
[netcaptor-ad]: https://web.archive.org/web/20050701001923/http://www.netcaptor.com/

Browser chrome
==============

Real web browsers don't just show web page contents---they've got
labels and icons and buttons.[^ohmy] This is called the browser
"chrome";[^chrome] all of this stuff is drawn by the browser to the
same window as the page contents, and it requires information about
the browser as a whole (like the list of all tabs), so it has to
happen in the `Browser` class.

[^ohmy]: Oh my!

[^chrome]: Yep, that predates and inspired the name of Google's Chrome
    browser.

Since we're interested in multiple tabs, let's add some code to draw a
tab bar at the top of the browser window---and let's keep it simple,
because this is going to require some tedious and mildly tricky
geometry.

We'll draw the tabs in the `draw` method, after the page contents are
drawn:

``` {.python}
class Browser:
    def draw(self):
        # ...
        tabfont = get_font(20, "normal", "roman")
        for i, tab in enumerate(self.tabs):
            # ...
```

Python's `enumerate` function lets you iterate over both the indices
and the contents of an array at the same time. Let's make each tab 80
pixels wide and 40 pixels tall. We'll label each tab something like
"Tab 4" so we don't have to deal with long tab titles overlapping. And
let's leave 40 pixels on the left for a button that adds a new tab.
Then, the `i`th tab starts at *x* position `40 + 80*i` and ends at
`120 + 80*i`:

``` {.python}
for i, tab in enumerate(self.tabs):
    name = "Tab {}".format(i)
    x1, x2 = 40 + 80 * i, 120 + 80 * i
```

For each tab, we need to create a border on the left and right and
then draw the tab name:

``` {.python}
for i, tab in enumerate(self.tabs):
    # ...
    self.canvas.create_line(x1, 0, x1, 40, fill="black")
    self.canvas.create_line(x2, 0, x2, 40, fill="black")
    self.canvas.create_text(x1 + 10, 10, anchor="nw", text=name,
        font=tabfont, fill="black")
```

Finally, to identify which tab is the active tab, we've got to make
that file folder shape with the current tab sticking up:

``` {.python}
for i, tab in enumerate(self.tabs):
    # ...
    if i == self.active_tab:
        self.canvas.create_line(0, 40, x1, 40, fill="black")
        self.canvas.create_line(x2, 40, WIDTH, 40, fill="black")
```

The whole point of tab support is to have more than one tab around,
and for that we we need a button that creates a new tab. Let's put
that on the left of the tab bar, with a big plus in the middle:

``` {.python}
class Browser:
    def draw(self):
        # ...
        buttonfont = get_font(30, "normal", "roman")
        self.canvas.create_rectangle(10, 10, 30, 30,
            outline="black", width=1)
        self.canvas.create_text(11, 0, anchor="nw", text="+",
            font=buttonfont, fill="black")
```

If you run this code, you'll see a small problem: the page contents
and the tab bar are drawn on top of each other. It's impossible to
read! We need to avoid drawing page contents to the part of the
browser window where the tab bar goes.

Let's reserve some space for the browser chrome---100 pixels, say,
leaving room for some more buttons later this chapter:

``` {.python}
CHROME_PX = 100
```

Each tab needs to make sure not to draw to those pixels:

``` {.python}
class Tab:
    def draw(self, canvas):
        for cmd in self.display_list:
            if cmd.top > self.scroll + HEIGHT - CHROME_PX: continue
            if cmd.bottom < self.scroll: continue
            cmd.execute(self.scroll - CHROME_PX, canvas)
```

There are still sometimes going to be halves of letters that stick out
into the browser chrome, but we can hide them by just drawing over
them:

``` {.python}
class Browser:
    def draw(self):
        self.tabs[self.active_tab].draw(self.canvas)
        self.canvas.create_rectangle(0, 0, WIDTH, CHROME_PX,
            fill="white", outline="black")
        # ...
```

Now you can see the tab bar fine.

You'll also need to adjust `scrolldown` to account for the height of
the page content now being `HEIGHT - CHROME_PX`:

``` {.python}
class Tab:
    def scrolldown(self):
        max_y = self.document.height - (HEIGHT - CHROME_PX)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)
```

The next step is clicking on tabs to switch between them. That has to
happen in the `Browser` class, since it's the `Browser` that stores
which tab is active. So let's go to the `handle_click` method and add
a branch for clicking on the browser chrome:

``` {.python}
class Browser:
    def handle_click(self, e):
        if e.y < CHROME_PX:
            # ...
        else:
            self.tabs[self.active_tab].click(e.x, e.y - CHROME_PX)
        self.draw()
```

When the user clicks on the browser chrome (the `if` branch), the
browser handles it directly, but clicks on the page content (the
`else` branch) are still forwarded to the active tab, subtracting
`CHROME_PX` to fix up the coordinates.

Within the browser chrome, the tab bar takes up the top 40 pixels,
starting 40 pixels from the left. Remember that the `i`th tab has `x1
= 40 + 80*i`; we need to solve that equation for `i` to figure out
which tab the user clicked on:

``` {.python}
if e.y < CHROME_PX:
    if 40 <= e.x < 40 + 80 * len(self.tabs) and 0 <= e.y < 40:
        self.active_tab = int((e.x - 40) / 80)
```

Note the first condition on the `if` statement: it makes sure that if
there are only two tabs, the user can't switch to the "third tab" by
clicking in the blank space where that tab would go. That would be
bad, because then later references to "the active tab" would error
out.

Let's also implement the button that adds a new tab. We need it to
test tab switching, anyway:

``` {.python}
if e.y < CHROME_PX:
    # ...
    elif 10 <= e.x < 30 and 10 <= e.y < 30:
        self.load(URL("https://browser.engineering/"))
```

That's an appropriate "new tab" page, don't you think? Anyway, you
should now be able to load multiple tabs, scroll and click around them
independently, and switch tabs by clicking on them.

::: {.further}
Google Chrome 1.0 was accompanied by a [comic book][chrome-comic] to
pitch its features. There's a whole [chapter][chrome-comic-tabs] about
its design ideas and user interface features, many of which stuck
around. Even this book's browser has tabs on top, for example!
:::

[chrome-comic]: https://www.google.com/googlebooks/chrome/
[chrome-comic-tabs]: https://www.google.com/googlebooks/chrome/big_18.html

Navigation history
==================

Now that we are navigating between pages all the time, it's easy to
get a little lost and forget what web page you're looking at. An
address bar that shows the current URL would help a lot.

``` {.python}
class Browser:
    def draw(self):
        # ...
        self.canvas.create_rectangle(40, 50, WIDTH - 10, 90,
            outline="black", width=1)
        url = str(self.tabs[self.active_tab].url)
        self.canvas.create_text(55, 55, anchor='nw', text=url,
            font=buttonfont, fill="black")
```

Here `str` is a built-in Python function that we can override to
correctly convert `URL` objects to strings:

``` {.python}
class URL:
    def __str__(self):
        port_part = ":" + str(self.port)
        if self.scheme == "https" and self.port == 443:
            port_part = ""
        if self.scheme == "http" and self.port == 80:
            port_part = ""
        return self.scheme + "://" + self.host + port_part + self.path
```

I think the extra logic to hide port numbers makes the URLs more tidy.

To keep up appearances, the address bar needs a "back" button nearby.
I'll start by drawing the back button itself:

``` {.python}
class Browser:
    def draw(self):
        # ...
        self.canvas.create_rectangle(10, 50, 35, 90,
            outline="black", width=1)
        self.canvas.create_polygon(
            15, 70, 30, 55, 30, 85, fill='black')
```

In Tk, `create_polygon` takes a list of coordinates and connects them
into a shape. Here I've got three points that form a simple triangle
evocative of a back button.

So what happens when that button is clicked on? Well, *that tab* goes
back. Other tabs are not affected. So the `Browser` has to invoke some
method on the current tab to go back:

``` {.python}
class Browser:
    def handle_click(self, e):
        if e.y < CHROME_PX:
            # ...
            elif 10 <= e.x < 35 and 50 <= e.y < 90:
                self.tabs[self.active_tab].go_back()
            # ...
```

For the active tab to "go back", it needs to store a "history" of
which pages it's visited before:

``` {.python}
class Tab:
    def __init__(self):
        # ...
        self.history = []
```

The history grows every time we go to a new page:

``` {.python}
class Tab:
    def load(self, url):
        self.history.append(url)
        # ...
```

Go back uses that history. You might think to write this:

``` {.python expected=False}
class Tab:
    def go_back(self):
        if len(self.history) > 1:
            self.load(self.history[-2])
```

That's almost correct, but it doesn't work if you click the back
button twice, because `load` adds to the history. Instead, we need to
do something more like this:

``` {.python indent=4}
class Tab:
    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)
```

Now, going back shrinks the history and clicking on links grows it, as
it should.

So we've now got a pretty good web browser for reading this very book:
you can click links, browse around, and even have multiple chapters
open simultaneously for cross-referencing things. But it's a little
hard to visit *any other website*...

::: {.further}
A browser's navigation history can contain sensitive information about
which websites a user likes visiting, so keeping it secure is
important. Surprisingly, this is pretty hard, because CSS features
like the [`:visited` selector][visited-selector] can be used to
[check][history-sniffing] whether a URL has been visited before.
:::

[visited-selector]: https://developer.mozilla.org/en-US/docs/Web/CSS/:visited
[history-sniffing]: https://blog.mozilla.org/security/2010/03/31/plugging-the-css-history-leak/

Editing the URL
===============

One way to go to another page is by clicking on a link. But most
browsers also allow you to type into the address bar to visit a new
URL, if you happen to know the URL off-hand.

Take a moment to notice the complex ritual of typing in an address:

- First, you have to click on the address bar to "focus" on it.
- That also selects the full address, so that it's all deleted when
  you start typing.
- Then, letters you type go into the address bar.
- The address bar updates as you type, but the browser doesn't yet
  navigate to the new page.
- Finally, you type the "Enter" key which navigates to a new page.

These steps suggest that the browser stores the contents of the
address bar separately from the `url` field, and also that there's
some state to say whether you're currently typing into the address
bar. Let's call the contents `address_bar` and the state `focus`:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.focus = None
        self.address_bar = ""
```

Clicking on the address bar should set `focus` and clicking outside it
should clear `focus`:

``` {.python}
class Browser:
    def handle_click(self, e):
        self.focus = None
        if e.y < CHROME_PX:
            # ...
            elif 50 <= e.x < WIDTH - 10 and 50 <= e.y < 90:
                self.focus = "address bar"
                self.address_bar = ""
        # ...
```

Note that clicking on the address bar also clears the address bar
contents. That's not quite what a browser does, but it's pretty close,
and lets us skip adding text selection.

Now, when we draw the address bar, we need to check whether to draw
the current URL or the currently-typed text:

``` {.python}
class Browser:
    def draw(self):
        # ...
        if self.focus == "address bar":
            self.canvas.create_text(
                55, 55, anchor='nw', text=self.address_bar,
                font=buttonfont, fill="black")
        else:
            url = str(self.tabs[self.active_tab].url)
            self.canvas.create_text(55, 55, anchor='nw', text=url,
                font=buttonfont, fill="black")
```

When the user is typing in the address bar, let's also draw a cursor.
Making states (like focus) visible on the screen (like with the
cursor) makes the software easier to use:

``` {.python indent=8}
if self.focus == "address bar":
    # ...
    w = buttonfont.measure(self.address_bar)
    self.canvas.create_line(55 + w, 55, 55 + w, 85, fill="black")
```

Next, when the address bar is focused, we need to support typing in a
URL. In Tk, you can bind to `<Key>` to capture all key presses. The
event object's `char` field contains the character the user typed:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.window.bind("<Key>", self.handle_key)

    def handle_key(self, e):
        if len(e.char) == 0: return
        if not (0x20 <= ord(e.char) < 0x7f): return

        if self.focus == "address bar":
            self.address_bar += e.char
            self.draw()
```

This `handle_key` handler starts with some conditions: `<Key>` fires
for every key press, not just regular letters, so we want to ignore
cases where no character is typed (a modifier key is pressed) or the
character is outside the ASCII range (which can represent the arrow
keys or function keys). After we modify `address_bar` we also need to
call `draw()` so that the new letters actually show up.

Finally, once the new URL is entered, we need to handle the "Enter"
key, which Tk calls `<Return>`, and actually send the browser to the
new address:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.window.bind("<Return>", self.handle_enter)

    def handle_enter(self, e):
        if self.focus == "address bar":
            self.tabs[self.active_tab].load(URL(self.address_bar))
            self.focus = None
            self.draw()
```

So there---after a long chapter, you can now unwind a bit by surfing
the web.

::: {.further}
Text editing is [surprisingly complex][editing-hates], and can be
pretty tricky to implement well, especially for languages other than
English. And nowadays URLs can be written in [any
language][i18n-urls], though modern browsers [restrict this
somewhat][idn-spoof] for security reasons.
:::

[editing-hates]: https://lord.io/text-editing-hates-you-too/
[i18n-urls]: https://en.wikipedia.org/wiki/Internationalized_domain_name
[idn-spoof]: https://en.wikipedia.org/wiki/IDN_homograph_attack

Summary
=======

It's been a lot of work just to handle links! We had to:

- Give each word an explicit size and position;
- Determine which piece of text a user clicked on;
- Split per-page from browser-wide information;
- Draw a tab bar, an address bar, and a back button;
- And even implement text editing!

Now just imagine all the features you can add to your browser!

::: {.signup}
:::

Outline
=======

The complete set of functions, classes, and methods in our browser 
should now look something like this:

::: {.cmd .python .outline html=True}
    python3 infra/outlines.py --html src/lab7.py
:::

If you run it, it should look something like this:

::: {.widget height=605}
    lab7-browser.html
:::

Exercises
=========

*Backspace*: Add support for the backspace key when typing in the
address bar. Honestly, do this exercise just for your sanity.

*Middle-click*: Add support for middle-clicking on a link (`Button-2`)
to open it in a new tab. You might need a mouse to test this easily.

*Forward*: Add a forward button, which should undo the back button. If
the most recent navigation action wasn't a back button, the forward
button shouldn't do anything. Draw it in gray in that case, so the
user isn't stuck wondering why it doesn't work. Also draw the back
button in gray if there's nowhere to go back to.

*Fragments*: URLs can contain a *fragment*, which comes at the end of
a URL and is separated from the path by a hash sign `#`. When the
browser navigates to a URL with a fragment, it should scroll the page
so that the element with that identifier is at the top of the screen.
Also, implement fragment links: relative URLs that begin with a `#`
don't load a new page, but instead scroll the element with that
identifier to the top of the screen. The table of contents on this
page uses fragment links.

*Search*: If the user types something that's *not* a URL into the
address bar, make your browser automatically search for it with a
search engine. This usually means going to a special URL. For example,
you can search Google by going to `https://google.com/search?q=QUERY`,
where `QUERY` is the search query with every space replaced by a `+`
sign.[^more-escapes]

[^more-escapes]: Actually, you need to escape [lots of punctuation
characters][query-escape] in these "query strings", but that's kind of
orthogonal to this address bar search feature.

[query-escape]: https://en.wikipedia.org/wiki/Query_string#URL_encoding

*Visited Links*: In real browsers, links you've visited before are
usually purple. Implement that feature. You'll need to store the set
of visited URLs, annotate the corresponding HTML elements, and check
those annotations when drawing the text.[^pseudo-class]

[^pseudo-class]: Real browsers support special [pseudo-class]
selectors that select all visited links, which you could implement if
you want.

[pseudo-class]: https://developer.mozilla.org/en-US/docs/Web/CSS/Pseudo-classes

*Bookmarks*: Implement basic *bookmarks*. Add a button to the browser
chrome; clicking it should bookmark the page. When you're looking at a
bookmarked page, that bookmark button should look different (maybe
yellow?) to remind the user that the page is bookmarked, and clicking
it should un-bookmark it. Add a special web page, `about:bookmarks`,
for viewing the list of bookmarks.

*Cursor*: Make the left and right arrow keys move the text cursor
around the address bar when it is focused. Pressing the backspace key
should delete the character before the cursor, and typing other keys
should add characters at the cursor. (Remember that the cursor can be
before the first character or after the last!)

*Multiple windows* Add support for multiple browser windows in
addition to tabs. This will require keeping track of multiple Tk
windows and canvases and grouping tabs by their containing window.
You'll also need some way to create a new window, perhaps with a
keypress such as `Ctrl+N`.
