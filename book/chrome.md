---
title: Handling Buttons and Links
chapter: 7
prev: styles
next: forms
...

Our toy browser is still missing the key insight of *hypertext*:
documents linked together by hyperlinks. Our browser lets us watch the
waves, but not surf the web. So in this chapter, we'll implement
hyperlinks, an address bar, and the rest of the browser
interface---the part of the browser that decides *which* page we are
looking at.

<a name="hit-testing">

Where are the links?
====================

The core of the web is the link, so the most important part of the
browser interface is clicking on links. Before we can quite get to
_clicking_ on links, we first need to answer a more fundamental
question: where on the screen _are_ the links?

But even though paragraphs and headings have their sizes and positions
recorded in the layout tree, formatted text (like links) does not. We
need to fix that.

The big idea is to introduce two new types of layout objects:
`LineLayout`s represent a line of text, and `TextLayout`s represent
individual words in those lines. We'll have `InlineLayout` create
these objects.

These new classes can be surprising in practice because they make the
layout tree look different from the HTML tree. Before starting code
surgery, let's go through a simple example:

```
<html>
  <body>
    Here is some text that is
    <br>
    spread across multiple lines
  </body>
</html>
```

The layout tree will have this structure:

```
DocumentLayout
  BlockLayout (html element)
    InlineLayout (body element)
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
```

Note how one `body` element corresponds to two `LineLayout`s, and how
two text nodes turn into a total of ten `TextLayout`s!

Defining these layout modes is straightforward. `LineLayout` is
totally standard:

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

Let's review [how word wrapping works](text.md) right now. Word
wrapping happens inside `InlineLayout`'s `text` method. That method
updates a `line` field, which stores all the words in the current
line. When it's time to go to the next line, it calls `flush`, which
computes the location of the line and each word in it, and adds all
the words to a `display_list` field, which stores all the words in the
whole heading or paragraph or whatever.

We'll start our changes in the very middle of things, the `text`
method that lays out text into lines. This key line adds a word to the
current line of text:

``` {.python.lab6 indent=12}
self.line.append((self.cursor_x, word, font, color))
```

Now, we want this line to create a `TextLayout` object and add it to a
`LineLayout` object. The `LineLayout`s are children of the
`InlineLayout`, so the current line can be found at the end of the
`children` array:

``` {.python indent=12}
line = self.children[-1]
text = TextLayout(node, word, line, self.previous_word)
line.children.append(text)
self.previous_word = text
```

Note that I've added a new field here, `previous_word`, to keep track
of the previous word in the current line.

Now let's think about what happens when we reach the end of the line.
The current code calls `flush`, which does a lot of stuff, like
positioning text and clearing the `line` field. We don't want to do
all that---we just want to create a new `LineLayout` object. So let's
use a different method for that:

``` {.python indent=12}
if self.cursor_x + w > WIDTH - HSTEP:
    self.new_line()
```

This `new_line` method can be pretty simple, since it isn't doing any
layout stuff:

``` {.python indent=4}
def new_line(self):
    self.previous_word = None
    self.cursor_x = self.x
    last_line = self.children[-1] if self.children else None
    new_line = LineLayout(self.node, self, last_line)
    self.children.append(new_line)
```

We more or less have the code in place to create `LineLayout` and
`TextLayout` objects---there's just some cleanup to do. In the core
`layout` method, we don't need to initialize the `display_list` or
`cursor_y` or `line` fields, since we won't be using any of those any
more. But we do need to lay out each line:

``` {.python indent=4}
def layout(self):
    # ...
    self.new_line()
    self.recurse(self.node)
    for line in self.children:
        line.layout()
    self.height = sum([line.height for line in self.children])
```

With the `display_list` gone, we also need to change the `paint` method
to recursively paint each line:

``` {.python indent=4}
def paint(self, display_list):
    # ...
    for child in self.children:
        child.paint(display_list)
```

We can also delete the `flush` method, since it's no longer called
from anywhere, but keep a copy of it around for when write the
`layout` method for lines and text objects.

Line layout, redux
==================

Alright, we're now creating line and text objects, but we still need
to lay them out. Let's start with lines. Lines stack vertically and
take up their parent's full width, so computing `x` and `y` and
`width` looks the same as for our other boxes:[^mixins]

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
`flush` method comes in. First, let's lay out each word:

``` {.python}
class LineLayout:
    def layout(self):
        # ...
        for word in self.children:
            word.layout()
```

Next, we need to compute the line's baseline based on the maximum
ascent and descent, using basically the same code as the old `flush`
method:

``` {.python}
class LineLayout:
    def layout(self):
        # ...
        max_ascent = max([word.font.metrics("ascent")
                          for word in self.children])
        baseline = self.y + 1.2 * max_ascent
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
have to come *after* the baseline computation, not *before*. Yet the
font computation has to come *before* the baseline computation. A real
browser might resolve this paradox with multi-phase layout, which
we'll [meet later](reflow.md). There are many considerations and
optimizations of this kind that are needed to make text layout super
fast.

Finally, now that each line is a standalone layout object, we need to
compute the line's height. We can do that using the maximum ascent and
descent:

``` {.python}
class LineLayout:
    def layout(self):
        # ...
        self.height = 1.2 * (max_ascent + max_descent)
```

Ok, so that's line layout. Now let's think about laying out each word
in a line. Recall that there's a few quirks to `layout` for
`TextLayout` objects: it needs to compute a `font` field, and it does
not need to compute a `y` field.

Let's start with `font`, using code based on the font-construction
code in `InlineLayout`:

``` {.python}
class TextLayout:
    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(self.node.style["font-size"][:-2]) * .75)
        self.font = tkinter.font.Font(
            size=size, weight=weight, slant=style)
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

Alright---we have the `LineLayout` and `TextLayout` objects created
and laid out. All that's left is painting them. For `LineLayout` we
just recurse:

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
layout object, with its own width and height.

Click handling
==============

Now that the browser knows where the links are, we can start to work
on clicking them. In Tk, clicks work just like key presses: you bind
an event handler to a certain event. For click handling that event is
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

The next step is to figure out what links or other elements are at that
location. To do that, we need to search through the tree of layout objects:

``` {.python indent=8}
# ...
objs = [obj for obj in tree_to_list(self.document, [])
        if obj.x <= x < obj.x + obj.width
        and obj.y <= y < obj.y + obj.height]
if not objs: return
```

Now, normally you click on lots of layout objects at once: some text,
and also the paragraph it's in, and the section that that paragraph is
in, and so on. We want the one that's "on top", so the last object in
the list:[^overlap]

[^overlap]: In a real browser, sibling elements can also overlap each
other, like a dialog that overlaps some text. Web pages can control
which sibling is on top using the `z-index` property. So real browsers
have to compute [stacking contexts][stack-ctx] to resolve what you
actually clicked on.

[stack-ctx]: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Positioning/Understanding_z_index/The_stacking_context

``` {.python indent=8}
# ...
elt = objs[-1].node
```

This `elt` node is the specific node in the HTML tree that was
clicked. With a link, that's usually going to be a text node. But
since we want to know the actual URL the user clicked on, we need to
climb back up the HTML tree to find the link element:

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
    url = resolve_url(elt.attributes["href"], self.url)
    return self.load(url)
```

Note that links can have relative URLs, which are resolved relative to
the current page. That means we need to store the current URL in
`load`:

``` {.python replace=Browser/Tab}
class Browser:
    def load(self, url):
        self.url = url
        # ...
```

Try it out! You should now be able to click on links and navigate to
new web pages.

Multiple pages
==============

If you're anything like me, the next thing you tried after clicking on
links is middle-clicking them to open in a new tab. Every browser now
has tabbed browsing, and honestly it's a little embarrassing that our
little toy browser doesn't.[^ffx]

[^ffx]: Back in they day, browser tabs were how I'd convince friends
    and relatives to switch from IE 6 to Firefox. Though interestingly
    enough, browser tabs first appeared in [SimulBrowse][simulbrowse],
    which was based on the IE engine.
    
[simulbrowse]: https://en.wikipedia.org/wiki/NetCaptor

Fundamentally, tabbed browsing means distinguishing between the
browser itself and tabs that show individual web pages. Right now the
`Browser` class stores both information about the browser (like the
canvas it draws to) and information about a single tab (like the
layout tree and display list). We need to tease the two apart.

Here's the plan: the `Browser` class will store the window and canvas,
plus a list of `Tab` objects, one per browser tab. Everything else
goes into a new `Tab` class. Since the `Browser` stores the window
and canvas, it handles all of the events, sometimes forwarding it to
the active tab.

The `Tab` constructor looks like this:

``` {.python}
class Tab:
    def __init__(self):
        with open("browser6.css") as f:
            self.default_style_sheet = CSSParser(f.read()).parse()
```

The `load`, `scrolldown`, `click`, and `draw` methods all move to
`Tab`, since that's now where all web-page-specific data lives. But
since the `Browser` controls the canvas and handles events, it decides
when rendering happens and which tab does the drawing. After all, you
only want one tab drawing its contents at a time![^unless-windows]

[^unless-windows]: Unless the browser implements multiple windows, of course.

So let's remove the `draw` calls from the `load` and `scrolldown`
methods, and in `draw`, let's pass the canvas in as an argument:

``` {.python}
class Tab:
    def draw(self, canvas):
        # ...
```

Now let's turn to the `Browser` class. Let's store a list of tabs and
an index into it for the active tab:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.tabs = []
        self.active_tab = None
```

Each tab is "passive", and the job of the `Browser` is to call into it
as appropriate. So the `Browser` handles all of the events:

``` {.python}
class Browser:
    def __init__(self):
        self.window.bind("<Down>", self.handle_down)
        self.window.bind("<Button-1>", self.handle_click)
```

These methods just unpack the event and forward it to the active tab:

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

- `scrolldown` should take no arguments (instead of an event object)
- `click` should take two coordinates (instead of an event object)

Finally, the `Browser`'s `draw` call also just invokes the active tab:

``` {.python}
class Browser:
    def draw(self):
        self.tabs[self.active_tab].draw(self.canvas)
```

The `Browser`/`Tab` split is basically done now, so we need to
actually create some tabs! It looks like this:

``` {.python}
class Browser:
    def load(self, url):
        new_tab = Tab()
        new_tab.load(url)
        self.active_tab = len(self.tabs)
        self.tabs.append(new_tab)
        self.draw()
```

The core methods behind tabbed browsing are done. But we need a way
for *the user* to switch tabs, create new ones, and so on. Let's turn
to that next.

Browser chrome
==============

Real web browsers don't just show web page contents---they've got
labels and icons and buttons.[^ohmy] This is called the browser
"chrome";[^chrome] all of this stuff is drawn by the browser to the
same canvas as the page contents, and it requires information about
the browser as a whole (like the list of all tabs), so it has to
happen in the `Browser` class.

[^ohmy]: Oh my!

[^chrome]: Yep, that predates and inspired the name of Google's Chrome
    browser.

Since we're interested in multiple tabs, let's add some code to draw a
set of tabs at the top of the browser window---and let's keep it
simple, because this is going to require some tedious and mildly
tricky geometry.

We'll draw the tabs in the `draw` method, after the page contents are
drawn:

``` {.python}
class Browser:
    def draw(self):
        # ...
        tabfont = tkinter.font.Font(size=20)
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
    self.canvas.create_line(x1, 0, x1, 40)
    self.canvas.create_line(x2, 0, x2, 40)
    self.canvas.create_text(
        x1 + 10, 10, text=name, font=tabfont, anchor="nw")
```

Finally, to identify which tab is the active tab, we've got to make
that file folder shape with the current tab sticking up:

``` {.python}
for i, tab in enumerate(self.tabs):
    # ...
    if i == self.active_tab:
        self.canvas.create_line(0, 40, x1, 40)
        self.canvas.create_line(x2, 40, WIDTH, 40)
```

We need a button to create a new tab. Let's put that on the left, with
a big plus in the middle:

``` {.python}
class Browser:
    def draw(self):
        # ...
        buttonfont = tkinter.font.Font(size=30)
        self.canvas.create_rectangle(10, 10, 30, 30, width=1)
        self.canvas.create_text(
            11, 0, font=buttonfont, text="+", anchor="nw")
```

Run this code, and you'll see a small problem: the page contents and
the tab bar are drawn on top of each other. It's impossible to read!
We need the top of the browser window, where all the browser chrome
goes, to not have page contents rendered to it.

Let's reserve some space for the browser chrome---100 pixels of space,
to leave room for some more buttons later this chapter:

``` {.python}
CHROME_PX = 100
```

Each tab needs to make sure not to draw to those pixels:

``` {.python}
class Tab:
    def draw(self, canvas):
        canvas.delete("all")
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
        self.canvas.create_rectangle(0, 0, WIDTH, CHROME_PX, fill="white")
        # ...
```

Now you can see the tab bar fine.

The next step is clicking on tabs to switch between them. That has to
happen in the `Browser` class, since it's the `Browser` that stores
which tab is active. So let's go to the `handle_click` method:

``` {.python}
class Browser:
    def handle_click(self, e):
        if e.y < CHROME_PX:
            # ...
        else:
            self.tabs[self.active_tab].click(e.x, e.y - CHROME_PX)
        self.draw()
```

The `if` branch of the conditional handles clicks in the browser
chrome; the `else` branch handles clicks on the web page content. When
the user clicks in the browser chrome, it doesn't go to the active
tab---the browser handles it directly. Also note that we subtract
`CHROME_PX` before forwarding a click to the active tab.

When the user clicks to switch tabs, we need to figure out what tab
they clicked on. Remember that the `i`th tab has `x1 = 40 + 80*i`; we
need to solve that equation for `i`:

``` {.python}
if e.y < CHROME_PX:
    if 40 <= e.x < 40 + 80 * len(self.tabs) and 10 <= e.y < 40:
        self.active_tab = int((e.x - 40) / 80)
```

Note the condition on the `if` statement: it makes sure that if there
are only two active tabs, the user can't switch to the "third tab" by
clicking in the blank space where that tab would go. That would be
bad, because later references to "the active tab" would error out.

We need multiple tabs to test this out, so let's implement the button
that adds new tabs:

``` {.python}
if e.y < CHROME_PX:
    # ...
    elif 10 <= e.x < 30 and 10 <= e.y < 30:
        self.load("https://browser.engineering/")
```

That's an appropriate "new tab" page, don't you think? Anyway, you
should now be able to load multiple tabs, scroll and click around them
independently, and switch tabs by clicking on them.

Navigation history
==================

Now that we are navigating between pages all the time, it's easy to
get a little lost and forget what web page you're looking at. Browsers
solve this issue with an address bar that shows the current URL. Let's
implement a little address bar ourselves:

``` {.python}
class Browser:
    def draw(self):
        # ...
        self.canvas.create_rectangle(40, 50, WIDTH - 10, 90, width=1)
        url = self.tabs[self.active_tab].url
        self.canvas.create_text(
            55, 55, anchor='nw', text=url, font=buttonfont)
```

To keep up appearances, the address bar needs a "back" button nearby.
I'll start by drawing the back button itself:

``` {.python}
class Browser:
    def draw(self):
        # ...
        self.canvas.create_rectangle(10, 50, 35, 90, width=1)
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
            elif 10 <= e.x < 35 and 40 <= e.y < 90:
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

To go back we just look at that history. You might write that code
like this:

``` {.python expected=False}
class Tab:
    def go_back(self):
        if len(self.history) > 1:
            self.load(self.history[-2])
```

That's almost correct, but if you click the back button twice, you'll
go forward instead, because `load` has appended to the history.
Instead, we need to do something more like this:

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

Editing the URL
===============

One way to go to another page is by clicking on a link. But most
browsers also allow you to type into the address bar to visit a new
URL, if you happen to know the URL off-hand.

Take a moment to notice the complex ritual of typing in an address:

- First, you have to click on the address bar to "focus" on it.
- That also selects the full address, so that it's all deleted when
  you start typing.[^why-not-select]
- Then, letters you type go into the address bar.
- The address bar updates as you type, but the browser doesn't yet
  navigate to the new page.
- Finally, you type the "Enter" key which navigates to a new page.

[^why-not-select]: I'm not going to implement the selection bit,
    because it would add even more states to the system.

This ritual suggests that the browser stores a string with the
contents of the address bar, separate from the `url` field, and also a
boolean to know if you're currently typing into the address bar. Let's
call that string `address_bar` and that boolean `focus`:

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
            elif 50 <= e.x < WIDTH - 10 and 40 <= e.y < 90:
                self.focus = "address bar"
                self.address_bar = ""
        # ...
```

Now, when we draw the address bar, we need to check whether to draw
the current URL or the currently-typed text:

``` {.python}
class Browser:
    def draw(self):
        # ...
        if self.focus == "address bar":
            self.canvas.create_text(
                55, 55, anchor='nw', text=self.address_bar,
                font=buttonfont)
        else:
            url = self.tabs[self.active_tab].url
            self.canvas.create_text(
                55, 55, anchor='nw', text=url, font=buttonfont)
```

When the user is typing in the address bar, let's draw a cursor:

``` {.python indent=8}
if self.focus == "address bar":
    # ...
    w = buttonfont.measure(self.address_bar)
    self.canvas.create_line(55 + w, 55, 55 + w, 85)
```

Next, when the address bar is focused, you should be able to type in a
URL. In Tk, you can bind to `<Key>` and access the letter typed with
the event object's `char` field:

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

This `handle_key` handler starts with some conditions: `<Key>` is Tk's
catchall event handler for keys, and fires for every key press, not
just regular letters. So the handler ignores cases where no character
is typed (a modifier key is pressed) or the character is outside the
ASCII range (the arrow keys and function keys correspond to larger key
codes).

Because we modify `address_bar`, we want the browser chrome redrawn,
so we need to call `draw()`. Thus, when the user types, new letters
appear in the address bar.

The last step is to handle the "Enter" key, which Tk calls `<Return>`,
to actually direct the browser to the new address:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.window.bind("<Return>", self.handle_enter)

    def handle_enter(self, e):
        if self.focus == "address bar":
            self.tabs[self.active_tab].load(self.address_bar)
            self.focus = None
            self.draw()
```

So there---after a long day of work, unwind a bit by surfing the web.

Summary
=======

It's been a lot of work just to handle links! We have totally re-done
line and text layout. That's allowed us to determine which piece of
text a user clicked on, which allows us to determine what link they've
clicked on and where that links goes. And as a cherry on top, we've
implemented a simple browser chrome, which displays the URL of the
current page and allows the user to navigate back and forth.

Exercises
=========

*Middle-click*: Add support for middle-clicking on a link (`Button-2`)
to open it in a new tab. You might need a mouse to test this easily.

*Backspace*: Add support for the backspace key when typing in the
address bar.

*Forward*: Add a forward button, which should "undo" the back button.
If the most recent navigation action wasn't a back button, the forward
button shouldn't do anything. Draw it in gray in that case, so the
user isn't stuck wondering why it doesn't work.

*Fragments*: URLs can contain a *fragment*, which comes at the end of
a URL and is separated from the path by a hash sign `#`. When the
browser navigates to a URL with a fragment, it should scroll the page
so that the element with that identifier is at the top of the screen.
Also, implement fragment links: relative URLs that begin with a `#`
don't load a new page, but instead scroll the element with that
identifier to the top of the screen. The table of contents on this
page uses fragment links.

*Search*: If the user types something that's *not* a URL into the
address bar, make your browser automatically search for that query in
a search engine. For example, you can search Google by going to

    https://google.com/search?q=QUERY

where `QUERY` is the search query with every space replaced by a `+`
sign.[^more-escapes]

[^more-escapes]: Actually you need to escape many different
    punctuation characters, but don't worry about it for now.

*Visited Links*: In real browsers, links are a different color when
you've visited them before---usually purple. Implement that feature by
storing the set of all visited pages and checking them when you lay
out links. Link color is currently driven by CSS: you need to work
with that somehow. I recommend adding the `visited` class to all links
that have been visited, right after parsing and before styling. Then
you could add a browser style that uses that class. (Or you could add a
[*pseudo*-class](https://developer.mozilla.org/en-US/docs/Web/CSS/Pseudo-classes)
feature to your CSS parser, which is what real browsers do.)

*Bookmarks*: Implement basic *bookmarks*. Add a button to the browser
chrome; clicking it should bookmark the page. When you're looking at a
bookmarked page, that bookmark button should look different to remind
the user that the page is bookmarked, and clicking it should
un-bookmark it. Add a special web page, `about:bookmarks`, for viewing
the list of bookmarks, and make `Ctrl+B` navigate to that page.

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
