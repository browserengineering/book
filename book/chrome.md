---
title: Handling Buttons and Links
chapter: 7
prev: styles
next: forms
...

Our toy browser draws web pages, but it is is still missing the key
insight of *hypertext*: pages linked together into a web of
information. We can watch the waves, but cannot yet surf the web. We
need to implement hyperlinks, and we might as well add an address bar
and a back button while we're at it.

Click handling
==============

To implement links, the browser UI, and so on, we need to start
with clicks. We already handle key presses; clicks work similarly in
Tk: an event handler bound to a certain event. For scrolling, we
defined `scroll_down` and bound it to `<Down>`; for click handling we
will define `handle_click` and bind it to `<Button-1>`, button number
1 being the left button on the mouse.[^1]

[^1]: Button 2 is the middle button; button 3 is the right hand button.


``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.window.bind("<Button-1>", self.handle_click)
```

Inside `handle_click`, we want to figure out what link the user has
clicked on. We'll need to look at the `e` argument, which contains an
"event object". This object has `x` and `y` fields, which refer to
where the click happened, relative to the corner of the browser
window. Since the canvas is in the top-left corner of the window,
those are also the *x* and *y* coordinates relative to the canvas. To
get coordinates relative to the web page, we need to account for
scrolling:

``` {.python}
def handle_click(self, e):
    x, y = e.x, e.y + self.scroll
```

The next step is to figure out what links or other elements are at
that location. To do that, we need to keep the tree of layout objects
(which right now we create and then throw away) available as a field
on the `Browser` class:

``` {.python}
def layout(self, tree):
    self.document = DocumentLayout(tree)
    # ...
```

Now `handle_click` can walk this tree, checking each layout object's
size and position to find the element clicked on:

``` {.python}
def handle_click(self, e):
    # ...
    elt = find_element(x, y, self.document)
    print(elt.tag)
```

Here the `find_element` function is a straightforward variant of code
we've already written a few times:

``` {.python}
def find_element(x, y, layout):
    for child in reversed(layout.children):
        result = find_element(x, y, child)
        if result: return result
    if layout.x <= x < layout.x + layout.w and \
       layout.y <= y < layout.y + layout.h:
        return layout.node
```

In this code snippet, I am checking the children of a given node
before checking the node itself. That's because you want the most
specific element: if you click on a link, you want to click on the
link, not the page `<body>`. I search the children in reverse order in
case children overlap; the last one would be "on top".[^2]

[^2]: Real browsers use what are called *stacking contexts* to resolve
    the overlapping-elements question while allowing the order to be
    controlled with the `z-index` property.

Let's test it---but actually, first, let's handle a silly omission:
we don't have any special style for links! Let's quickly add support
for text color, which is controlled by the `color` property:

- First, add `color` to `INHERITED_PROPERTIES` with the default
  value `black`.
- Next, add `a { color: blue; }` to the browser style sheet so that
  links (`<a>` tags) are colored blue.
- Add a `color` field to `DrawText` and modify `DrawText.draw` to
  use it for the `fill` parameter of `create_text`.
- In `InlineLayout` pass the color from the `text` method, through the
  `line` field, then into the `display_list` in `flush`, and finally
  into the `DrawText` constructor.

Once links have colors, you can actually *find* them on the page. So
try clicking on them!

Adding line and text layout
===========================

Unfortunately, if you click on a link you won't see `a` printed in the
console. That's because there is no layout object corresponding to a
link. The link text is laid out by `InlineLayout`, but each
`InlineLayout` handles a whole paragraph of text, not a single link.
We'll need to do some surgery on `InlineLayout` to fix this.

Here's how I want inline layout to work, at a high level:

-   `InlineLayout`'s children are a list of `LineLayout` objects. This
    list replaces `InlineLayout` keeping track of a `y` cursor position.
-   `LineLayout`'s children are a list of `TextLayout` objects, one per
    word. Each `TextLayout` object has a `node`, which is always a
    `TextNode`. This replaces the `x` cursor position
-   Both `TextLayout` and `LineLayout` objects have a `w` and an `h` fields.
-   `InlineLayout` will create the `LineLayout` and `TextLayout`
    objects, then call `layout` on each `LineLayout`
-   `LineLayout.layout` will compute an `h` and an `x` and a `y`
    position and call `layout` on each `TextLayout`
-   `TextLayout.layout` will compute an `x` and a `y` position as well

To begin with, we'll need to create two new data structures:

``` {.python}
class LineLayout:
    def __init__(self, node, parent):
        self.node = node
        self.parent = parent
        self.children = []
        self.cx = 0

class TextLayout:
    def __init__(self, node, word):
        self.node = node
        self.children = []
        self.word = word
```

`LineLayout` is pretty run-of-the-mill, but `TextLayout` is unusual.
First, its `children` field will always be an empty list; that's just
for convenience.[^4] Second, it has both a `node` and a `word`
argument. That's because a single `TextNode` contains multiple words,
and I want each `TextLayout` to be a single word.[^5] Finally,
`TextLayout` does not take a `parent` argument. That's because we'll
decide the parent later, in a separate `attach` method, which I'll
define below.

[^4]: You may want to use inheritance to group all the `Layout`
    classes into a hierarchy, but I'm trying to stick to some kind of
    easily-translatable subset of Python.

[^5]: Because of line breaking.

Next, since each `TextLayout` corresponds to a particular `TextNode`, we
can immediately compute its width and height:[^6]

[^6]: Make sure you measure `word`, not `node.text`, which contains
    multiple words! That's an easy and confusing bug.

``` {.python}
class TextLayout:
    def __init__(self, node, word):
        # ...
        bold = node.style["font-weight"] == "bold"
        italic = node.style["font-style"] == "italic"
        self.color = node.style["color"]
        self.font = tkinter.font.Font(
            family="Times", size=16,
            weight="bold" if bold else "normal",
            slant="italic" if italic else "roman"
        )
        self.w = self.font.measure(word)
        self.h = self.font.metrics('linespace')
```

We can compute all this immediately in the constructor; that's one of
the benefits of implementing styles and inheritance in the previous
chapter.

With `TextLayout` and `LineLayout` in place, we can start surgery on
`InlineLayout`. First, let's create that list of lines, and initialize
it with a blank line:

``` {.python}
class InlineLayout:
    def __init__(self, node, parent):
        # ...
        self.children = [LineLayout(self.node, self)]
```

We'll need to create `LineLayout` and `TextLayout` objects as we lay
out text in `InlineLayout`'s `text` and `flush` methods. Let's look at
them in turn.

The `text` function adds each word to the `line` field and then
increments `x`. It should add the word to the last open line instead.
At a high level, it should look something like this:

``` {.python}
def text(self, node, text):
    for word in text.split():
        child = TextLayout(node, word)
        line = self.children[-1]
        if line.cx + tl.w > self.w:
            self.flush()
        line.add(child)
```

Where the `add` call on `LineLayout`s is pretty simple:

``` {.python}
class LineLayout:
    def add(self, child):
        self.children.append(child)
        child.parent = self
        child.x = self.cx
        self.cx += child.w + child.font.measure(" ")
```

Note that the `text` method gained the `node` variable, which we need
to pass to `TextLayout` so that it styles itself correctly.

Meanwhile, `flush` now needs to do two things: lay out the current
line and then create a new one. Laying out the current line is what
all the existing code does; we'll move that to `LineLayout` as a new
`layout` method, so that `flush` is just:

``` {.python}
class InlineLayout:
    def flush(self):
        child = self.children[-1]
        child.x = self.x
        child.y = self.cy
        child.layout()
        self.cy += child.h
        self.children.append(LineLayout(self.node, self))
```

Meanwhile the new `layout` method for `LineLayout`s is nearly the same
as the old `flush` method, except:

1. Instead of adding things to a display list, it now just sets the
   `y` field on `TextNode` objects;
2. Instead of updating the `cx` and `cy` fields, it just computes an
   `h` field.

Now that words and lines lay themselves out, a lot of stuff disappears
from`InlineLayout`. The `style`, `size`, `weight` fields are no longer
needed. Neither is `line` or `cx`. And the display list is no longer
needed: instead of addings words to a display list, they can print
themselves in their draw call:

``` {.python}
class TextLayout:
    def draw(self):
        to.append(DrawText(self.x, self.y, self.word, self.font))
```

The `InlineLayout` and `LineLayout` versions of the `draw` method
don't do anything but recurse on their children.


Navigating between pages
========================

*Phew*. That was a lot of surgery to `InlineLayout`. But as a result,
`InlineLayout` should now look a lot like the other layout classes,
and we now have individual layout object corresponding to each word in
the document. Test clicks in your browser again: when you click on a
link `find_element` should now return the exact `TextNode` that you
clicked on, from which you could get a link:

``` {.python}
def is_link(node):
    return isinstance(node, ElementNode) \
        and node.tag == "a" and "href" in node.attributes

def handle_click(self, e):
    # ...
    elt = find_element(x, y, self.document)
    while elt and not is_link(elt):
        elt = elt.parent
    if elt:
        print("Time to go to new page", elt.attributes["href"])
```

Once we've found the link, we need to navigate to that page. That
would mean:

-   Parsing the new URL
-   Requesting that page
-   Lexing and parsing it
-   Downloading its rules and styling the page nodes
-   Generating a display list
-   Drawing that display list to the canvas
-   Waiting for events like scrolling the page and clicking on links

We do all of that already, so it's just a matter of hooking it all up.
First, in `Browser.load`, let's store the current URL of the browser:

``` {.python}
def load(self, url):
    self.url = url
    # ...
```

Now, inside `handle_click`, we can convert the link we clicked on to a
new URL:

``` {.python}
def handle_click(self, e):
    # ...
    if elt:
        url = relative_url(elt.attributes["href"], self.url)
        self.load(url)
```

Note that because we we use the current URL to resolve relative URLs
in links.

Try the code out, say on this page---you could use the links at the
top of the page, for example. Our toy browser now sufficies to read
not just a chapter, but the whole book.

Browser chrome
==============

Now that we are navigating between pages all the time, it's easy to
get a little lost and forget what web page you're looking at.
Browsers solve this issue by with an address bar that shows the URL.
Let's implement a little address bar ourselves.

The idea is to reserve the top 60 pixels of the canvas and then draw
the address bar there. That 60 pixels is called the browser
*chrome*.[^10]

[^10]: Yep, that predates and inspired the name of Google's Chrome
    browser.

To do that, we first have to move the page content itself further down.
I'm going to reserve 60 pixels for the browser chrome, which we need
to subtract in `render`:

``` {.python}
def render(self):
    self.canvas.delete("all")
    for cmd in self.display_list:
        if cmd.y1 > self.scroll + (HEIGHT - 60): continue
        if cmd.y2 < self.scroll: continue
        cmd.draw(self.scroll - 60, self.canvas)
```

We need to make a similar change in `handle_click` to subtract that 60
pixels off when we convert back from screen to page coordinates. Next,
we need to cover up any actual page contents that got drawn to that top
60 pixels:

``` {.python}
def render(self):
    # ...
    self.canvas.create_rectangle(0, 0, 800, 60, fill='light gray')
```

Of course a real browser wouldn't draw that content in the first
place, but in Tk that's a little tricky to do,[^11] and covering it
up later is easier.

[^11]: Text that is partially covered by the browser chrome would be
    hard to handle.

The browser chrome area is now our playbox. Let's add an address bar:

``` {.python}
self.canvas.create_rectangle(50, 10, 790, 50)
self.canvas.create_text(15, 15, anchor='nw', text=self.url)
```

::: {.todo}
I'd like to tweak this a little to make the results look passable,
tweaking the font and the size of things.
:::

Browser history
===============

The back button is another classic browser feature our browser really
needs. I'll start by drawing the back button itself:

``` {.python}
self.canvas.create_rectangle(10, 10, 35, 50)
self.canvas.create_polygon(15, 30, 30, 15, 30, 45, fill='black')
```

In Tk, `create_polygon` takes a list of coordinates and connects them
into a shape. Here I've got three points that form a simple triangle
evocative of a back button. You'll need to shrink the address bar so
that it doesn't overlap this new back button.

Now we need to detect when that button is clicked on. This will go in
`handle_click`, which must now have two cases, for clicks in the chrome
and clicks in the page:

``` {.python}
def handle_click(self, e):
    if e.y < 60: # Browser chrome
        if 10 <= e.x < 35 and 10 <= e.y < 50:
            self.go_back()
    else: # Page content
        # ...
```

How should `self.go_back()` work? Well, to begin with, we'll need to
store the *history* of the browser got to the current page. I'll add
a `history` field to `Browser`, and have `browse` append to it when
navigating to a page:

``` {.python}
def browse(self, url):
    self.url = url
    self.history.append(url)
    # ...
```

Now `self.go_back()` knows where to go:

``` {.python}
def go_back(self):
    if len(self.history) > 1:
        self.browse(self.history[-2])
```

This is almost correct, but if you click the back button twice, you'll
go forward instead, because `browse` has appended to the history.
Instead, we need to do something more like:

``` {.python}
def go_back(self):
    if len(self.history) > 1:
        self.history.pop()
        back = self.history.pop()
        self.browse(back)
```

Editing the URL
===============

One way to go to another page is by clicking on a link. But most
browsers also allow you to type into the address bar to visit a new
URL, if you happen to know the URL off-hand.

But take a moment to notice the complex ritual involved in typing in a
new address:

- First, you have to click on the address bar to "focus" on it
- That also selects the full address, so that it's all deleted when
  you start typing
- Then, letters you type go into the address bar
- The address bar updates itself, but the browser doesn't yet navigate
  to the new page
- Finally, you type the "Enter" key which navigates to a new page.

This ritual suggests that the browser stores a boolean for whether or
not you've clicked on the address bar and a string with the contents
of the address bar, separate from the `url` field. Let's call that
boolean `focus` and the string `address_bar`:

``` {.python}
class Browser:
    def __init__(self):
        self.focus = None
        self.address_bar = ""

    def load(self, url):
        self.address_bar = url
        # ...
```

Clicking on the address bar should set `focus` and clear the
`address_bar` variable:[^why-not-select]

[^why-not-select]: I'm not going to implement the selection bit, since
    text selection is actually quite hard.

``` {.python}
def handle_click(self, e):
    self.focus = None
    if e.y < 60: # Browser chrome
        # ...
        elif 50 <= e.x < 790 and 10 <= e.y < 50:
            self.focus = "address_bar"
            self.address_bar = ""
            self.render()
    # ...
```

The click method now resets the text focus by default, and only
focuses on the address bar when it is clicked on. Note that I call
`render()` to make sure the screen is redrawn with the new address bar
content. Make sure to modify `render` to use `address_bar` as the text
in the address bar. If the address bar is focused let's also draw a
cursor:

``` {.python}
def render(self):
    # ...
    font = tkinter.font.Font(family="Courier", size=20)
    self.canvas.create_text(15, 15, anchor="nw", text=self.address_bar)
    if self.focus == "address_bar":
        w = font.measure(self.address_bar)
        self.canvas.create_line(15 + w, 15, 15 + w, 45)
```

Next, when the address bar is focused, typing letters should add them
to the address bar. In Tk, you can bind to `<Key>` and access the
letter typed with the event object's `char` field:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.window.bind("<Key>", self.keypress)

    def keypress(self, e):
        if self.focus == "address_bar" and \
            len(e.char) == 1 and 0x20 <= ord(e.char) < 0x7f \
            and e.state ^ 4 == 0:
            self.address_bar += e.char
            self.render()
```

Again, because we modified `address_bar` and want the browser chrome
to be redrawn, we need to call `render()`. Note the conditions in that
`if` statement: `<Key>` is Tk's catchall event handler for keys, and
fires for every key press, not just regular letters. So, I make that
sure a character was typed (instead of just a modifier key being
pressed), that it is in the ASCII range between "space" and "tilde"
(as opposed to the arrow keys), and that no modifier keys were held
(such as Control or Alt) except Shift (that's what "4" means).

Now you can type into the address bar, but it doesn't do anything. So
our last step is to handle the "Enter" key, which Tk calls `<Return>`:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.window.bind("<Return>", self.pressenter)

    def pressenter(self, e):
        if self.focus == "address_bar":
            self.focus = None
            self.load(self.address_bar)
```

In this case, `load` calls `render` so we don't need to do so directly.

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
you could add a browser style that uses that class. You could add
*pseudo*-class, like in [Chapter 10](reflow.md), which is what real
browsers do.

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
