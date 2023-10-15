---
title: Handling Buttons and Links
chapter: 7
prev: styles
next: forms
...

Our toy browser is still missing the key insight of
*hypertext*\index{hypertext}: documents linked together by
hyperlinks\index{hyperlink}. It lets us watch the
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

``` {.python indent=8}
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

With the `display_list` gone, we can also remove the part of
`paint`\index{paint} that handles it. Painting all the lines in a paragraph
is now just automatically handled by recursing into the child layout objects.
So by adding `LineLayout` and `TextLayout` we made `BlockLayout` quite a
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
browser might resolve this paradox with multi-phase layout.
There are many considerations and optimizations of this kind that are
needed to make text layout super fast.

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
is painting. For `LineLayout` there is nothing to paint:

``` {.python}
class LineLayout:
    def paint(self):
        return []

```

And each `TextLayout` creates a single `DrawText` call:

``` {.python}
class TextLayout:
    def paint(self):
        cmds = []
        color = self.node.style["color"]
        cmds.append(
            DrawText(self.x, self.y, self.word, self.font, color))
        return cmds
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

``` {.python replace=Browser/Tab,self)/self%2c%20tab_height)}
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
should [use the area information][rect-based] for
"hit testing".\index{hit testing} This can happen even with a
[normal mouse click][hit-test] when the click is on a rotated or scaled
element.
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

Fundamentally, implementing tabbed browsing requires us to distinguish
between the browser itself and tabs that show individual web pages.
The canvas the browser draws to, for example, is shared by all web pages,
but the layout tree and display list are specific to one page. We need to
tease these two types of things apart.

Here's the plan: the `Browser` class will store the window and canvas,
plus a list of `Tab` objects, one per browser tab. Everything else
goes into a new `Tab` class. Since the `Browser` stores the window
and canvas, it handles all of the events, sometimes forwarding it to
the active tab.

Since the `Tab` class is responsible for layout, styling, and
painting, the default style sheet moves to the `Tab` constructor:

``` {.python replace=browser.css/browser6.css,self)/self%2c%20tab_height)}
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

``` {.python replace=canvas/canvas%2c%20offset}
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

``` {.python replace=e.y/e.y%20-%20self.chrome.bottom}
class Browser:
    def handle_down(self, e):
        self.tabs[self.active_tab].scrolldown()
        self.draw()

    def handle_click(self, e):
        self.tabs[self.active_tab].click(
            e.x, e.y)
        self.draw()
```

You'll need to tweak the `Tab`'s `scrolldown` and `click` methods:

- `scrolldown` now takes no arguments (instead of an event object)
- `click` now take two coordinates (instead of an event object)

Finally, the `Browser`'s `draw` call also calls into the active tab:

``` {.python replace=canvas)/canvas%2c%20self.chrome.bottom)}
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

``` {.python replace=Tab()/Tab(HEIGHT%20-%20self.chrome.bottom)}
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
"chrome"\index{browser chrome};[^chrome] all of this stuff is drawn by
the browser to the same window as the page contents, and it requires
information about the browser as a whole (like the list of all tabs),
so it has to happen at the browser level, not per-tab.

[^ohmy]: Oh my!

[^chrome]: Yep, that predates and inspired the name of Google's Chrome
    browser.

However, a browser's UI is quite complicated, so let's put that code in a new
`Chrome` helper class. It will have a `paint` method to paint the browser
chrome. The `paint` method constructs the display list for the browser chrome;
I'm just constructing and using it directly, instead of storing it somewhere,
because our browser will have pretty simple chrome, meaning `paint_chrome` will
be fast. In a real browser, it might be saved and only updated when the chrome
changes.

``` {.python}
class Chrome:
    def __init__(self, browser):
        self.browser = browser

    def paint(self):
        # ....
```

``` {.python}
class Browser:
    def __init__(self):
        ...
        self.chrome = Chrome(self)
```

The browser chrome generates a display list just like a tab. However, unlike
tabs, this display list will always be drawn at the top of the window and won't
be scrolled:

``` {.python}
class Browser:
    def draw(self):
        # ...
        for cmd in self.chrome.paint():
            cmd.execute(0, self.canvas)
```

First things first: we need to avoid drawing page contents to the part of the
browser window where the browser chrome is. Browser chrome is at the top of the
window, with tab contents below it. So we need to figure out how tall
the browser chrome is, to know how much to shrink the available tab area.
We don't know that yet without computing it as part of designing
the UI of the browser chrome, but we do know it will determien the `tab_height`
we can pass to each `Tab`:

``` {.python}
class Tab:
    def __init__(self, tab_height):
        ...
        self.tab_height = tab_height
```

Each tab needs to make sure not to draw to those pixels. We need to pass an
extra `offset` parameter to account for the (still to be determined) browser
chrome height.

``` {.python}
class Tab:
    def draw(self, canvas, offset):
        for cmd in self.display_list:
            if cmd.top > self.scroll + self.tab_height:
                continue
            if cmd.bottom < self.scroll: continue
            cmd.execute(self.scroll - offset, canvas)
```

Now let's turn our attention to designing the UI.

First, there are still sometimes going to be halves of letters that stick out
into the browser chrome, but we can hide them by just drawing over
them. Here I'm assuming we've already computed `self.bottom`
(representing the bottom y coordinate of the browser chrome); that will
come in a moment:

``` {.python}
class Chrome:
    def paint(self):
        cmds = []
        cmds.append(
            DrawRect(0, 0, WIDTH, self.bottom, "white"))
        return cmds
```

You'll also need to adjust `scrolldown` to account for the height of
the page content now being `tab_height`:

``` {.python}
class Tab:
    def scrolldown(self):
        max_y = max(
            self.document.height + 2*VSTEP - self.tab_height, 0)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)
```

To better separate the chrome from the page, let's also add a border:

``` {.python}
class Chrome:
    def paint(self):
        # ...
        cmds.append(DrawLine(
            0, self.bottom, WIDTH,
            self.bottom, "black", 1))
        # ...
```

The `DrawLine` command draws a line of a given color and thickness.
It's defined like so:

``` {.python}
class DrawLine:
    def __init__(self, x1, y1, x2, y2, color, thickness):
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color
        self.thickness = thickness

    def execute(self, scroll, canvas):
        canvas.create_line(
            self.left, self.top - scroll,
            self.right, self.bottom - scroll,
            fill=self.color, width=self.thickness,
        )
```

Now let's design the browser chrome. I think it should have the following:

* At the top, a list of tab names, separated by vertical lines, and a "`+`"
  button to add a new tab.

* Underneath, the URL of of the current web page, and a "`<`" button to
  represent the browser back-button.

We'll need to reserve some space for all this at the top of the window. But how much?
One way could be to pick some arbitrary browser chrome height, then try to
squeeze the chrome into it (and making its font smaller as necessary). Another,
better way, is to pick a font size that is easy enough to read, then compute
the chrome height accordingly.

For our design, the chrome's height should be the vertical
height of those two lines plus some padding between and after them. For
convenience, and to use them later for processing mouse clicks, I'll store
these parameters on the `Chrome` object:^[I also chose `20px` as the
font size. Depending on your computer, this may end up looking smaller,
\index{device pixel ratio}
because of the device pixel ratio of the screen.]

``` {.python}
class Chrome:
    def __init__(self, browser):
        # ...
        self.font = get_font(20, "normal", "roman")
        font_height = self.font.metrics("linespace")

        self.padding = 5
        self.tab_header_bottom = font_height + 2 * self.padding
        self.addressbar_top = self.tab_header_bottom + self.padding
        self.bottom = \
            self.addressbar_top + font_height + \
            2 * self.padding    
```

In addition, it's convenient to define some methods that return the bounds of
the plus and each tab. Note how the size of each
elements' bounds is as wide as the font says it is. That way, if we change our
mind later, we can just change the font size, and everything else just draws
correctly.^[Also, we chose "Tab 1" as the fixed size of a tab, but in real
life many fonts draw different numbers (like "1" and "6") with different
widths, and this approximation also doesn't work for two-digit tab numbers.
Real browsers size their tabs to fit the [title], but we skipped that for
simplicity.]

[title]: https://developer.mozilla.org/en-US/docs/Web/API/Document/title

``` {.python}
class Chrome:
    def plus_bounds(self):
        plus_width = self.font.measure("+")
        return (self.padding, self.padding,
            self.padding + plus_width,
            self.tab_header_bottom - self.padding)

    def tab_bounds(self, i):
        tab_start_x = self.padding + self.font.measure("+") + \
            self.padding

        tab_width = self.padding + self.font.measure("Tab 1") + \
            self.padding

        return (tab_start_x + tab_width * i, self.padding,
            tab_start_x + tab_width + tab_width * i,
            self.tab_header_bottom)
```

Now for drawing the actual UI, starting with the tab bar at the top of the
browser window. Here's the plus icon:

``` {.python}
class Chrome:
    def paint(self):
        # ...
        (plus_left, plus_top, plus_right, plus_bottom) = \
            self.plus_bounds()
        cmds.append(DrawOutline(
            plus_left, plus_top, plus_right, plus_bottom, "black", 1))
        cmds.append(DrawText(
            plus_left, plus_top, "+", self.font, "black"))
        # ...
```

The `DrawOutline` command draws a rectangle's border instead of
its inside. It's defined like this:

``` {.python}
class DrawOutline:
    def __init__(self, x1, y1, x2, y2, color, thickness):
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color
        self.thickness = thickness

    def execute(self, scroll, canvas):
        canvas.create_rectangle(
            self.left, self.top - scroll,
            self.right, self.bottom - scroll,
            width=self.thickness,
            outline=self.color,
        )
```

Next up is drawing the tabs. Python's `enumerate` function lets you iterate over
both the indices and the contents of an array at the same time. For each tab,
we need to create a border on the left and right and then draw the tab name:

``` {.python}
class Chrome:
    def paint(self):
        # ...
        for i, tab in enumerate(self.browser.tabs):
            name = "Tab {}".format(i)
            (tab_left, tab_top, tab_right, tab_bottom) = \
                self.tab_bounds(i)

            cmds.append(DrawLine(
                tab_left, 0, tab_left, tab_bottom, "black", 1))
            cmds.append(DrawLine(
                tab_right, 0, tab_right, tab_bottom, "black", 1))
            cmds.append(DrawText(
                tab_left + self.padding, tab_top,
                name, self.font, "black"))
```

Finally, to identify which tab is the active tab, we've got to make
that file folder shape with the current tab sticking up:

``` {.python}
class Chrome:
    def paint(self):
        # ...
        for i, tab in enumerate(self.browser.tabs):
            # ...
            if i == self.browser.active_tab:
                cmds.append(DrawLine(
                    0, tab_bottom, tab_left, tab_bottom, "black", 1))
                cmds.append(DrawLine(
                    tab_right, tab_bottom, WIDTH, tab_bottom,
                    "black", 1))
```

The next step is clicking on tabs to switch between them. That has to
happen in the `Browser` class, since it's the `Browser` that stores
which tab is active. So let's go to the `handle_click` method and add
a branch for clicking on the browser chrome, which will delegate to a new
method on the `Chrome` object.

``` {.python}
class Browser:
    def handle_click(self, e):
        if e.y < self.chrome.bottom:
            self.chrome.click(e.x, e.y)
        else:
            self.tabs[self.active_tab].click(
                e.x, e.y - self.chrome.bottom)
        self.draw()
```

``` {.python}
class Chrome:
    def click(self, x, y):
        # ...
```

When the user clicks on the browser chrome (the `if` branch), the
browser handles it directly, but if the click is on the page content
(the `else` branch) it is still forwarded to the active tab,
subtracting `self.chrome.bottom` to fix up the coordinates.

If the `y` coordinate is as high as `self.chrome.bottom`, it's just a matter
of comparing it against each of the bounds methods we've already defined. To
that end, let's add a quick method to test whether a point intersects one
of them:

``` {.python}
def intersects(x, y, rect):
    (left, top, right, bottom) = rect
    return x >= left and x < right and y >= top and y < bottom
```

And then use it to choose between clicking to add a tab or select an open tab.

``` {.python}
class Chrome:
    def click(self, x, y):
        if intersects(x, y, self.plus_bounds()):
            self.browser.load(URL("https://browser.engineering/"))
        # ...
        else:
            for i, tab in enumerate(self.browser.tabs):
                if intersects(x, y, self.tab_bounds(i)):
                    self.browser.active_tab = i
                    break
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
class Chrome:
    def paint(self):
        # ...
        left_bar = addressbar_left + self.padding
        top_bar = addressbar_top + self.padding
        url = str(self.browser.tabs[self.browser.active_tab].url)
        cmds.append(DrawText(
            left_bar,
            top_bar,
            url, self.font, "black"))
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
class Chrome:
    def paint(self):
        # ...
        backbutton_width = self.font.measure("<")
        (backbutton_left, backbutton_top, backbutton_right,
            backbutton_bottom) = self.backbutton_bounds()
        cmds.append(DrawOutline(
            backbutton_left, backbutton_top,
            backbutton_right, backbutton_bottom,
            "black", 1))
        cmds.append(DrawText(
            backbutton_left, backbutton_top + self.padding,
            "<", self.font, "black"))
```

And of course add the `backbutton_bounds` method:

``` {.python}
class Chrome:
    def backbutton_bounds(self):
        backbutton_width = self.font.measure("<")
        return (self.padding, self.addressbar_top,
            self.padding + backbutton_width,
            self.bottom - self.padding)
```

So what happens when that button is clicked? Well, *that tab* goes
back. Other tabs are not affected. So the `Browser` has to invoke some
method on the current tab to go back:

``` {.python}
class Chrome:
    def click(self, x, y):
        # ...
        elif intersects(x, y, self.backbutton_bounds()):
                self.browser.tabs[self.browser.active_tab].go_back()
```

For the active tab to "go back", it needs to store a "history" of
which pages it's visited before:

``` {.python}
class Tab:
    def __init__(self, tab_height):
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

Going back uses that history. You might think to write this:

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
[check][history-sniffing] whether a URL has been visited before. For
this reason, there are [efforts] to restrict `:visited`.
:::

[visited-selector]: https://developer.mozilla.org/en-US/docs/Web/CSS/:visited
[history-sniffing]: https://blog.mozilla.org/security/2010/03/31/plugging-the-css-history-leak/
[efforts]: https://github.com/kyraseevers/Partitioning-visited-links-history

Editing the URL
===============

One way to go to another page is by clicking on a link. But most
browsers also allow you to type into the address bar to visit a new
URL, if you happen to know the URL off-hand.

Take a moment to notice the complex ritual of typing in an address:

- First, you have to click on the address bar to "focus"\index{focus} on it.
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
class Chrome:
    def click(self, x, y):
        # ...
        elif intersects(x, y, self.addressbar_bounds()):
            self.browser.focus = "address bar"
            self.browser.address_bar = ""
```

With this definition of the bounds:

``` {.python}
class Chrome:
    def addressbar_bounds(self):
        (backbutton_left, backbutton_top, backbutton_right,
            backbutton_bottom) = \
            self.backbutton_bounds()

        return (backbutton_right + self.padding, self.addressbar_top,
            WIDTH - 10, self.bottom - self.padding)
```

Note that clicking on the address bar also clears the address bar
contents. That's not quite what a browser does, but it's pretty close,
and lets us skip adding text selection.

Now, when we draw the address bar, we need to check whether to draw
the current URL or the currently-typed text:

``` {.python}
class Chrome:
    def paint(self):
        # ...
        if self.browser.focus == "address bar":
            cmds.append(DrawText(
                left_bar, top_bar,
                self.browser.address_bar, self.font, "black"))
        else:
            url = str(self.browser.tabs[self.browser.active_tab].url)
            cmds.append(DrawText(
                left_bar,
                top_bar,
                url, self.font, "black"))
```

When the user is typing in the address bar, let's also draw a cursor.
Making states (like focus) visible on the screen (like with the
cursor) makes the software easier to use:

``` {.python}
class Chrome:
    def paint(self):
        # ...
        if self.browser.focus == "address bar":
            # ...
            w = self.font.measure(self.browser.address_bar)
            cmds.append(DrawLine(
                left_bar + w, top_bar,
                left_bar + w,
                self.bottom - self.padding, "red", 1))
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

*Multiple windows*: Add support for multiple browser windows in
addition to tabs. This will require keeping track of multiple Tk
windows and canvases and grouping tabs by their containing window.
You'll also need some way to create a new window, perhaps with a
keypress such as `Ctrl+N`.

*Hit testing in layout*: The `click` method we implemented is on the `Tab`
object. While it doesn't have a whole lot of logic in it, there is special
logic for `Text` objects and `a` tags. Real browsers have many more special
kinds of nodes, plus more complicated layout, so they tend to implement this
logic directly on the layout tree.^[Real browsers call this logic *hit testing*,
because it's used for more than just clicking. The name comes from thinking
whether an arrow shot at that location would "hit" the object.] Implement
`click` on the layout tree.

*Hit testing on the display list*: Hit testing can be thought of as a "reversed"
version of `paint`: `paint` turns elements into pixels,
while hit testing turns pixels into elements. Plus, it looks
at the elements front-to-back in paint order,
as opposed to back-to-front. Building on this observation, we could build all
of the necessary information for hit testing directly into the display list
instead of the layout tree. Implement one of these.^[You might want to implement
hit testing in this way in a browser because display lists are pure data
structurs and therefore easier to optimize or execute in different
threads.]

*Reusing HTML*: Browser chrome is quite complicated in real browsers,
with tricky details such as font sizes, padding, outlines,
shadows, icons and so on. This makes it tempting to try to reuse our
implementation of those features for web pages---imagine replacing the
contents of `paint_chrome` with a call to paint some HTML instead that
represents the UI of the browser chrome. Implement this, including support for
the [`padding`][padding] CSS property (even if you can't implement the
whole UI faithfully---outline will have to wait for [Chapter
14](accessibility.md), for example).[^real-browser-reuse]

[padding]: https://developer.mozilla.org/en-US/docs/Web/CSS/padding

[^real-browser-reuse]: Real browsers have in fact gone down this implementation
path multiple times. Firefox [has one](https://en.wikipedia.org/wiki/XUL),
and [so does Chrome](https://www.chromium.org/developers/webui/). However,
because it's so important for the browser chrome to be very fast and responsive
to draw, such approaches have had mixed success.
