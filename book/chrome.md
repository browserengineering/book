---
title: Handling Buttons and Links
chapter: 7
prev: styles
next: forms
...

Our toy browser draws web pages, but it is still missing the key
insight of *hypertext*: pages linked together into a web of
information. We can watch the waves, but cannot yet surf the web. We
need to implement hyperlinks, an address bar, and the rest of the
browser interface.

<a name="hit-testing">

Where are the links?
====================

Before we can quite get to _clicking_ on links, we first need to
answer a more fundamental question: where on the screen are the links?
The reason this is tricky is that while paragraphs and headings
have corresponding objects in the layout tree with sizes and positions
attached, formatted text (like links) do not. We need to fix that.

The big idea is to introduce two new types of layout objects,
`LineLayout` and `TextLayout`, that go inside an `InlineLayout`
objects. `LineLayout`s represent a line of text and stack one after
another vertically. `TextLayout`s represent individual words and are
arranged on the line left to right. We'll need `InlineLayout` to
create both objects, and then we'll need to write layout methods for
them.

Let's start by defining our two new types of layout objects. A
`LineLayout` object is straightforward:

``` {.python}
class LineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
```

However, a `TextLayout` object needs to refer not just to a single
text node but also to a specific word in that text node. After all, a
single text node might be split over multiple lines, and so might need
multiple `TextLayout` objects:

``` {.python}
class TextLayout:
    def __init__(self, node, word, parent, previous):
        self.node = node
        self.word = word
        self.children = []
        self.parent = parent
        self.previous = previous
```

Right now, the `InlineLayout` object breaks text into lines using its
`line` field, computes the position of each line and each word in its
`flush` method, and stores the words in its `display_list` field. We
want to change this up.

It's going to be a lot of work to refactor this code, but the end
result will be cleaner and simpler, and more importantly it will
provide us with a layout object for every piece of text, which we'll
use to determine where links are and ultimately to enable clicking on
links.
 
Let's start in the very middle of things, the `text` method that lays
out text into lines. This one line corresponds to placing a word in a
line of text:

``` {.python.lab6 indent=12}
self.line.append((self.cursor_x, word, font, color))
```

An `InlineLayout` object will now have lots of lines in it, so there
won't be a `line` field. And each line will be a `LineLayout` object,
now an array. And each word in the line will be a `TextLayout` object,
not just an unweidly four-tuple. So it should look like this:

``` {.python indent=12}
line = self.children[-1]
text = TextLayout(node, word, line, self.previous_word)
line.children.append(text)
self.previous_word = text
```

Note that I've added a new field here, `previous_word`, for the
previous word in that same line. So let's think about when the code
starts a new line---it's when it calls `flush`. Now, `flush` does a
lot of stuff, like positioning text and clearing the `line` field. We
don't want to do all that---we just want to create a new `LineLayout`
object:

``` {.python indent=12}
if self.cursor_x + w > WIDTH - HSTEP:
    self.new_line()
```

This `new_line` method is pretty simple, since it isn't doing any
layout stuff:

``` {.python indent=4}
def new_line(self):
    self.previous_word = None
    self.cursor_x = self.x
    last_line = self.children[-1] if self.children else None
    new_line = LineLayout(self.node, self, last_line)
    self.children.append(new_line)
```

Now that we have the core `text` method updated, there are just a few
more cleanups to do. In the core `layout` method, we don't need to
initialize the `display_list` or `cursor_y` or `line` fields. But we
do need to lay out each line:

``` {.python indent=4}
def layout(self):
    # ...
    self.new_line()
    self.recurse(self.node)
    for line in self.children:
        line.layout()
    self.height = sum([line.height for line in self.children])
```

With the `display_list` gone, we do need to change the `paint` method.
instead of copying from the `display_list`, it just needs to
recursively paint each line:

``` {.python indent=4}
def paint(self, display_list):
    # ...
    for child in self.children:
        child.paint(display_list)
```

The `flush` method now isn't called from anywhere, but keep it around,
because we now need to write the `layout` method for lines and text
objects.

Let's start with lines. Lines stack vertically and take up their
parent's full width, so computing `x` and `y` and `width` looks the
same as for our other boxes:[^mixins]

[^mixins]: You could reduce the duplication with some helper methods
    (or even something more elaborate, like mixin classes), but in a
    real browser these code snippets would look more different, due to
    supporting all kinds of extra features.

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

When each word is laid out, it can compute its `font`, using code
basically identical to what's in `InlineLayout`:

``` {.python}
class TextLayout:
    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(self.node.style["font-size"][:-2]) * .75)
        self.font = tkinter.font.Font(size=size, weight=weight, slant=style)
```

Now when we're laying out a `LineLayout` object, we can use this
`font` field to compute maximum ascents and descents:

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
        self.height = 1.2 * (max_ascent + max_descent)
```

Note that we're also setting the `y` field on each word in the line!
That means that inside `TextLayout`'s `layout` method, we only need to
compute `x`, `width`, and `height`:

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

Finally, now that we have all of the `LineLayout` and `TextLayout`
objects created and laid out, painting them is pretty easy. For
`LineLayout` we just recurse:

``` {.python}
class LineLayout:
    def paint(self, display_list):
        for child in self.children:
            child.paint(display_list)
```

For `TextLayout` we just create a single `DrawText` call:

``` {.python}
class TextLayout:
    def paint(self, display_list):
        color = self.node.style["color"]
        display_list.append(DrawText(self.x, self.y, self.word, self.font, color))
```

Oof, well, this was quite a bit of refactoring. It was tricky, and
probably exhausting. So take a moment to test everything---it should
look exactly identical to how it did before we started this refactor.
But while you can't see it, there's a crucial difference: each blue
link on the page now has an associated layout object, with its own
width and height.

Click handling
==============

So now let's start to implement links, the browser UI, and so on. We
need to start with clicks. In Tk, clicks work just like key presses:
you bind an event handler to a certain event. For click handling that
event is `<Button-1>`, button number 1 being the left button on the
mouse.[^1]

[^1]: Button 2 is the middle button; button 3 is the right hand button.


``` {.python replace=self.click/self.handle_click}
class Browser:
    def __init__(self):
        # ...
        self.window.bind("<Button-1>", self.click)
```

Inside `click`, we want to figure out what link the user has
clicked on. Luckily, the event handler is passed an "event object",
whose `x` and `y` fields refer to where the click happened:

Now, here, we have to be careful with coordinate systems. Those *x*
and *y* coordinates are relative to the browser window. Since the
canvas is in the top-left corner of the window, those are also the *x*
and *y* coordinates relative to the canvas. We want the coordinates
relative to the web page, so we need to account for scrolling:

``` {.python expected=False}
class Browser:
    def click(self, e):
        x, y = e.x, e.y
        y += self.scroll
        # ...
```

The next step is to figure out what links or other elements are at
that location. To do that, we need search through the tree of layout
objects:

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

[^overlap]: In a real browser you can also have a dialog that overlaps
some text, or something like that. And real browsers can control which
element is on top using the `z-index` property. So real browsers use
*stacking contexts* to resolve what exactly you actually clicked on.

``` {.python indent=8}
# ...
elt = objs[-1].node
```

Now `node` refers to the specific node in the HTML tree that you
clicked on. With a link, that's usually going to be a text node. But
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

I wrote this in a kind of curious way, but this way it's easier to add
other types of clickable things later---like text boxes and buttons in
the [next chapter](forms.md). Finally, now that we've found the link
element itself, we need to extract the URL and direct the browser to
it. This URL might be a relative URL:

``` {.python indent=12}
# ...
elif elt.tag == "a" and "href" in elt.attributes:
    url = relative_url(elt.attributes["href"], self.url)
    return self.load(url)
```

Since this needs to know the browser's current URL, we need to store
it in `load`:

``` {.python replace=Browser/Tab}
class Browser:
    def load(self, url):
        self.url = url
        # ...
```

Try it! You should now be able to click on links and navigate to new
web pages.

Multiple pages
==============

If you're anything like me, the next thing you tried after clicking on
links is middle-clicking them to open in a new tab. Every browser now
has tabbed browsing, and honestly it's a little embarrasing that our
little toy browser doesn't.

Fundamentally tabbed browsing means we need to distinguish between the
browser itself and individual tabs that browse some specific web page.
Right now the `Browser` class stores both information about the
browser (like the canvas it draws to) and information about a single
tab (like the layout tree and display list). We need to tease the two
apart.

Here's the plan: the `Browser` class will store the window and canvas,
plus the list of tabs. Everything else goes into a new `Page` class.
Since the `Browser` stores the window and canvas, it handles all of
the events, sometimes forwarding it to the active tab.

So the `Tab` constructor looks like this:

``` {.python}
class Tab:
    def __init__(self):
        with open("browser6.css") as f:
            self.default_style_sheet = CSSParser(f.read()).parse()
```

The `load`, `scrolldown`, `click`, and `draw` methods all move to
`Tab`, since that's now where all web-page-specific data lives. But
there's a change here too.

Since the `Browser` controls the canvas and handles events, it decides
when rendering happens and which tab does the drawing. After all, you
only want one tab drawing its contents at a time! So let's remove the
`draw` calls from the `load` and `scrolldown` methods.

Meanwhile, in `draw`, let's pass the canvas in as an argument:

``` {.python}
class Tab:
    def draw(self, canvas):
        # ...
```

Now let's turn our attention to the `Browser` class. Basically, the
`Tab` is now passive, just a collection of methods you can call to
manipulate the tab. The `Browser`'s job is to call those methods. In
the `Browser` class let's create a list of tabs and an index into it
for the active tab:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.tabs = []
        self.active_tab = None
```

As the "active party", the `Browser` needs to handle all of the
events. So let's bind the down key and the mouse click:

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

You'll need to modify the arguments `Tab`'s `scrolldown` and `click`
methods expect. Finally, that `draw` call also just forwards to the
active tab:

``` {.python}
class Browser:
    def draw(self):
        self.tabs[self.active_tab].draw(self.canvas)
```

This is all basically done now, with one small oversight: we need to
actually create some tabs! Let's start with a method that creates a
new tab:

``` {.python}
class Browser:
    def load(self, url):
        new_tab = Tab()
        new_tab.load(url)
        self.active_tab = len(self.tabs)
        self.tabs.append(new_tab)
        self.draw()
```

So this works---try it, debug it---but we're still missing a user
interface for the tabs feature. We need a way for the user to switch
tabs, create new ones, and so on. Let's turn to that next.

Browser chrome
==============

Real web browsers don't just show web page contents---they've got
labels and icons and buttons.[^ohmy] This is called the browser
"chrome";[^chrome] right now creating and listing and switching tabs
is most interesting. All of this stuff is drawn by the browser to the
same canvas as the page contents, and it requires information about
the browser as a whole (like the list of all tabs), so it has to
happen in the `Browser` class.

[^ohmy]: Oh my!

[^chrome]: Yep, that predates and inspired the name of Google's Chrome
    browser.

So let's add some code to draw a set of tabs at the top of the browser
window. Let's try to keep it simple, because this is going to require
some tedious and mildly tricky geometry. Let's have each tab be 80
pixels wide and 40 pixels tall. We'll label each tab something like
"Tab 4" so we don't have to deal with long tab titles overlapping. And
let's leave 40 pixels on the left for a button that adds a new tab.

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
and the contents of an array at the same time. Now, the `i`th tab
starts at *x* position `40 + 80*i` and ends at `120 + 80*i`:

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
    self.canvas.create_text(x1 + 10, 10, text=name, font=tabfont, anchor="nw")
```

Finally, we want to identify which tab is the active tab. To do that
let's draw a file folder shape with the current tab sticking up:

``` {.python}
for i, tab in enumerate(self.tabs):
    # ...
    if i == self.active_tab:
        self.canvas.create_line(0, 40, x1, 40)
        self.canvas.create_line(x2, 40, WIDTH, 40)
```

We'll also want a button to create a new tab. Let's put that on the
left, with a big plus in the middle:

``` {.python}
class Browser:
    def draw(self):
        # ...
        buttonfont = tkinter.font.Font(size=30)
        self.canvas.create_rectangle(10, 10, 30, 30, width=1)
        self.canvas.create_text(11, 0, font=buttonfont, text="+", anchor="nw")
```

If you run this code, you'll see a small problem: the page contents
and the tab bar are drawn on top of each other, and it's impossible to
read. We need the top of the browser window, where all the browser
chrome goes, to not have page contents rendered to it.

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

Now you can see the tab bar fine. The next step is clicking on tabs to
switch between them. That has to happen in the `Browser` class, since
it's the `Browser` that can change which tab is active. So let's go to
the `handle_click` method:

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
chrome; the `else` branch handles clicks on the web page content. Note
that when the user clicks on the content, we subtract `CHROME_PX` so
that the click coordinates are relative to the "page content" portion
of the browser.

When the user clicks on the browser chrome, the browser can react:

``` {.python}
if e.y < CHROME_PX:
    if 40 < e.x < 40 + 80 * len(self.tabs) and 10 <= e.y < 40:
        self.active_tab = (e.x - 40) // 80
```

In Python, the `//` operator divides two numbers and casts the result
to an integer---in this case, the index of the tab the user clicked
on. So this code switches tabs. To try it, we'll also need to handle
the button that adds new tabs:

``` {.python}
if e.y < CHROME_PX:
    # ...
    elif 10 <= e.x < 30 and 10 <= e.y < 30:
        self.load("https://browser.engineering/")
```

Now you should be able to load multiple tabs, scroll and click around
them independently, and switch tabs whenever you want.

Navigation history
==================

Now that we are navigating between pages all the time, it's easy to
get a little lost and forget what web page you're looking at.
Browsers solve this issue with an address bar that shows the URL.
Let's implement a little address bar ourselves. The URL it shows is
the URL for the currently-active tab:

``` {.python}
class Browser:
    def draw(self):
        # ...
        self.create_rectangle(40, 50, 790, 90, width=1)
        url = self.tabs[self.active_tab].url
        self.canvas.create_text(55, 55, anchor='nw', text=url, font=buttonfont)
```

If we've got an address bar, we need to have a "back" button too. I'll
start by drawing the back button itself:

``` {.python}
class Browser:
    def draw(self):
        # ...
        self.canvas.create_rectangle(10, 50, 35, 90, width=1)
        self.canvas.create_polygon(15, 70, 30, 55, 30, 85, fill='black')
```

In Tk, `create_polygon` takes a list of coordinates and connects them
into a shape. Here I've got three points that form a simple triangle
evocative of a back button.

So what happens when that button is clicked on? Well, before we jump
to the `handle_click` method, let's think this through. To go back, we
need to store a "history" of which pages we've visited before. And
different tabs have different histories, so the history has to be
stored on each tab:

``` {.python}
class Tab:
    def __init__(self):
        # ...
        self.history = []
```

We'll add to the history every time we go to a new page:

``` {.python}
class Tab:
    def load(self, url):
        self.history.append(url)
        # ...
```

Now a tab can go back just by looking in that history. You might write
that code like this:

``` {.python expected=False}
class Tab:
    def go_back(self):
        if len(self.history) > 1:
            self.load(self.history[-2])
```

That's almost correct, but if you click the back button twice, you'll
go forward instead, because `load` has appended to the history.
Instead, we need to do something more like:

``` {.python indent=4}
class Tab:
    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)
```

So now that an individual tab can go back, we can make pressing the
back button do the right thing:

``` {.python}
class Browser:
    def handle_click(self, e):
        if e.y < CHROME_PX:
            # ...
            elif 10 <= e.x < 35 and 40 <= e.y < 90:
                self.tabs[self.active_tab].go_back()
            # ...
```

So we've now got a pretty good web browser for reading this very book:
you can click links, browse around, and even have multiple chapters
open simultaneously for cross-referencing things. But it's a little
annoying that the only way to get to a new website is by following
links. Let's fix that.

Editing the URL
===============

One way to go to another page is by clicking on a link. But most
browsers also allow you to type into the address bar to visit a new
URL, if you happen to know the URL off-hand.

Take a moment to notice the complex ritual of typing in an address:

- First, you have to click on the address bar to "focus" on it
- That also selects the full address, so that it's all deleted when
  you start typing
- Then, letters you type go into the address bar
- The address bar updates as you type, but the browser doesn't yet
  navigate to the new page
- Finally, you type the "Enter" key which navigates to a new page.

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

Clicking outside the address bar should "unselect" the address bar by
clearing `focus`; clicking on the address bar should set instead set
`focus`:[^why-not-select]

[^why-not-select]: I'm not going to implement the selection bit,
    because it would add even more states to the system.

``` {.python}
class Browser:
    def handle_click(self, e):
        self.focus = None
        if e.y < CHROME_PX:
            # ...
            elif 50 <= e.x < 790 and 40 <= e.y < 90:
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
            self.canvas.create_text(55, 55, anchor='nw', text=self.address_bar, font=buttonfont)
        else:
            url = self.tabs[self.active_tab].url
            self.canvas.create_text(55, 55, anchor='nw', text=url, font=buttonfont)
```

Just to clearly show the user that they're now typing in the address
bar, let's also draw a cursor:

``` {.python indent=8}
if self.focus == "address bar":
    # ...
    w = font.measure(self.address_bar)
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
so we need to call `draw()`. Thus, when the user types into the
address bar, new letters appear in the browser.

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

So there---after a long day of prep work, you can now go surf the web.


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
identifier to the top of the screen.

*Visited Links*: In real browsers, links are a different color when
you've visited them before---usually purple. Implement that feature by
storing the set of all visited pages and checking them when you lay
out links. Link color is currently driven by CSS: you need to work
with that somehow. I recommend adding the `visited` class to all links
that have been visited, right after parsing and before styling. Then
you could add a browser style that uses that class. You could add a
[*pseudo*-class](https://developer.mozilla.org/en-US/docs/Web/CSS/Pseudo-classes)
feature to your CSS parser, which is what real browsers do.

*Bookmarks*: Implement basic *bookmarks*. Add a button to the browser
chrome; clicking it should bookmark the page. When you're looking at a
bookmarked page, that bookmark button should look different to remind
the user that the page is bookmarked, and clicking it should
un-bookmark it. Add a special web page, `about:bookmarks`, for viewing
the list of bookmarks, and make `Ctrl+B` navigate to that page.

*Cursor*: Make the left and right arrow keys move the text cursor
around the address bar when it is focused. Pressing the backspace key
should delete the character before the cursor, and typing other keys
should add characters at the cursor. Remember that the cursor can be
before the first character or after the last.
