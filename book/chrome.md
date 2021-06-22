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


``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.window.bind("<Button-1>", self.handle_click)
```

Inside `handle_click`, we want to figure out what link the user has
clicked on. Luckily, the event handler is passed an "event object",
whose `x` and `y` fields refer to where the click happened:

Now, here, we have to be careful with coordinate systems. Those *x*
and *y* coordinates are relative to the browser window. Since the
canvas is in the top-left corner of the window, those are also the *x*
and *y* coordinates relative to the canvas. We want the coordinates
relative to the web page, so we need to account for scrolling:

``` {.python expected=False}
class Browser:
    def handle_click(self, e):
        x, y = e.x, e.y + self.scroll
```

The next step is to figure out what links or other elements are at
that location. To do that, we need search through the tree of layout
objects:

``` {.python}
def handle_click(self, e):
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

``` {.python}
def handle_click(self, e):
    # ...
    elt = objs[-1].node
```

Now `node` refers to the specific node in the HTML tree that you
clicked on. With a link, that's usually going to be a text node. But
since we want to know the actual URL the user clicked on, we need to
climb back up the HTML tree to find the link element:

``` {.python}
def handle_click(self, e):
    # ...
    while elt:
        if isinstance(elt, Text):
            pass
        elif elt.tag == "a" and "href" in elt.attributes:
            # ???
        elt = elt.parent
```

I wrote this in a kind of curious way because this way it's easier to
add other types of clickable things later---like text boxes and
buttons in the [next chapter](forms.md). Finally, now that we've found
the link element itself, we need to extract the URL and direct the
browser to it. This URL might be a relative URL:

``` {.python}
# ...
elif elt.tag == "a" and "href" in elt.attributes:
    url = relative_url(elt.attributes["href"], self.url)
    self.load(url)
```

Since this needs to know the browser's current URL, we need to store
it in `load`:

``` {.python}
class Browser:
    def load(self, url):
        self.url = url
        # ...
```

Try it! You should now be able to click on links and navigate to new
web pages.

Navigating between pages
========================

*Phew*. That was a lot of surgery to `InlineLayout`. But as a result,
`InlineLayout` should now look a lot like the other layout classes,
and we now have an individual layout object corresponding to each word in
the document. Test clicks in your browser again: when you click on a
link `find_layout` should now return the exact `TextNode` that you
clicked on, from which you could get a link:

``` {.python}
def is_link(node):
    return isinstance(node, ElementNode) \
        and node.tag == "a" and "href" in node.attributes

def handle_click(self, e):
    # ...
    while elt and not is_link(elt):
        elt = elt.parent
    if elt:
        # ...
```

Note the `while` loop. That's because the most specific thing the user
clicked on is a `TextNode`; we need to walk up the HTML tree to find
an `ElementNode` that is a link.

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

Note that relative URLs are relative to the page the browser is
currently looking at.

Try the code out, say on this page---you could use the links at the
top of the page, for example. Our toy browser now suffices to read
not just a chapter, but the whole book.

Browser chrome
==============

Now that we are navigating between pages all the time, it's easy to
get a little lost and forget what web page you're looking at.
Browsers solve this issue with an address bar that shows the URL.
Let's implement a little address bar ourselves.

The idea is to reserve the top 60 pixels of the canvas and then draw
the address bar there. That 60 pixels is called the browser
*chrome*.[^10]

[^10]: Yep, that predates and inspired the name of Google's Chrome
    browser.

To do that, we first have to move the page content itself further down.
I'm going to reserve 60 pixels for the browser chrome, which we need
to subtract in `draw`:

``` {.python}
def draw(self):
    self.canvas.delete("all")
    for cmd in self.display_list:
        if cmd.y1 > self.scroll + HEIGHT - 60: continue
        if cmd.y2 < self.scroll: continue
        cmd.draw(self.scroll - 60, self.canvas)
```

We need to make a similar change in `handle_click` to subtract that 60
pixels off when we convert back from screen to page coordinates. Next,
we need to cover up[^11] any actual page contents that got drawn to that top
60 pixels:

``` {.python}
def draw(self):
    # ...
    self.canvas.create_rectangle(0, 0, 800, 60, width=0, fill='light gray')
```

[^11]: Of course a real browser wouldn't draw that content in the
    first place, but in Tk that's a little tricky to do, and covering
    it up later is easier.

The browser chrome area is now our playbox. Let's add an address bar:

``` {.python replace=url/address_bar}
self.canvas.create_rectangle(50, 10, 790, 50)
font = tkinter.font.Font(family="Courier", size=30)
self.canvas.create_text(55, 15, anchor='nw', text=self.url, font=font)
```

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

``` {.python expected=False}
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
class Browser:
    def __init__(self):
        # ...
        self.history = []

    def load(self, url):
        self.url = url
        self.history.append(url)
        # ...
```

Now `self.go_back()` knows where to go:

``` {.python expected=False}
def go_back(self):
    if len(self.history) > 1:
        self.load(self.history[-2])
```

This is almost correct, but if you click the back button twice, you'll
go forward instead, because `load` has appended to the history.
Instead, we need to do something more like:

``` {.python}
def go_back(self):
    if len(self.history) > 1:
        self.history.pop()
        back = self.history.pop()
        self.load(back)
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
        # ...
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
            self.focus = "address bar"
            self.address_bar = ""
            self.draw()
    # ...
```

The click method now resets the text focus by default, and only
focuses on the address bar when it is clicked on. Note that I call
`draw()` to make sure the screen is redrawn with the new address bar
content. Make sure to modify `draw` to use `address_bar` as the text
in the address bar. If the address bar is focused let's also draw a
cursor:

``` {.python indent=4}
def draw(self):
    # ...
    if self.focus == "address bar":
        w = font.measure(self.address_bar)
        self.canvas.create_line(55 + w, 15, 55 + w, 45)
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
        if len(e.char) == 0: return
        if not (0x20 <= ord(e.char) < 0x7f): return

        if self.focus == "address bar":
            self.address_bar += e.char
            self.draw()
```

This `keypress` handler starts with some conditions: `<Key>` is Tk's
catchall event handler for keys, and fires for every key press, not
just regular letters. So the handler ignores cases where no character
is typed (a modifier key is pressed) or the character is outside the
ASCII range (the arrow keys and function keys correspond to larger key
codes).

Because we modify `address_bar`, we want the browser chrome redrawn,
so we need to call `draw()`. So now you can type into the address
bar. Our last step is to handle the "Enter" key, which Tk calls
`<Return>`, so that you can navigate to a new address:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.window.bind("<Return>", self.pressenter)

    def pressenter(self, e):
        if self.focus == "address bar":
            self.focus = None
            self.load(self.address_bar)
```

In this case, `load` calls `draw` so we don't need to do so directly.

Prettier pages
==============

Let's add support for *margins*, *borders*, and *padding*, which
change the position of block layout objects. Here's how those work. In
effect, every block has four rectangles associated with it: the
*margin rectangle*, the *border rectangle*, the *padding rectangle*,
and the *content rectangle*:

![](https://www.w3.org/TR/CSS2/images/boxdim.png)

So far, our block layout objects have had just one size and position;
these will refer to the border rectangle (so that the `x` and `y`
fields point to the top-left corner of the outside of the layout
object's border). To track the margin, border, and padding, we'll also
store the margin, border, and padding widths on each side of the
layout object in the variables `mt`, `mr`, `mb,` and `ml`; `bt`, `br`,
`bb`, and `bl`; and `pt`, `pr`, `pb`, and `pl`. The naming convention
here is that the first letter stands for margin, border, or padding,
while the second letter stands for top, right, bottom, or left.

Since each block layout object now has more variables, we'll need to
add code to `layout` to compute them:

``` {.python}
def px(s):
    if s.endswith("px"):
        return int(s[:-2])
    else:
        return 0

class BlockLayout:
    def layout(self):
        self.mt = px(self.node.style.get("margin-top", "0px"))
        self.bt = px(self.node.style.get("border-top-width", "0px"))
        self.pt = px(self.node.style.get("padding-top", "0px"))
        # ... repeat for the right, bottom, and left edges
```

Remember to write out the code to access the other 9 properties, and
don't forget that the border one is called `border-X-width`, not
`border-X`.[^because-colors]

[^because-colors]: Because borders have not only widths but also
    colors and styles, while paddings and margins are thought of as
    whitespace, not something you draw.

You'll also want to add these twelve variables to `DocumentLayout` and
`InlineLayout` objects. Set them all to zero.

With their values now loaded, we can use these fields to drive layout.
First of all, when we compute width, we need to account for the space
taken up by the parent's border and padding; and likewise we'll need
to adjust each layout object's `x` and `y` based on its margins:[^backslash-continue]

[^backslash-continue]: In Python, if you end a line with a backslash,
    the newline is ignored by the parser, letting you split a logical
    line of code across two actual lines in your file.

``` {.python}
def layout(self):
    # ...
    self.w = self.parent.w - self.parent.pl - self.parent.pr \
        - self.parent.bl - self.parent.br \
        - self.ml - self.mr
    self.y += self.mt
    self.x += self.ml
    # ...
```

Similarly, when we position child layout objects, we'll need to
account for our their parent's border and padding:

``` {.python indent=4}
def layout(self):
    # ...
    y = self.y
    for child in self.children:
        child.x = self.x + self.pl + self.bl
        child.y = y
        child.layout()
        y += child.mt + child.h + child.mb
    self.h = y - self.y
```

Likewise, in `InlineLayout` we'll need to account for the parent's
padding and border:

``` {.python}
class InlineLayout:
    def layout(self):
        self.w = self.parent.w - self.parent.pl - self.parent.pr \
            - self.parent.bl - self.parent.br
```

It's now possible to indent a single element by giving it a `style`
attribute that adds a `margin-left`. But while that's good for one-off
changes, it is a tedious way to change the style of, say, every
paragraph on the page. And if you have a site with many pages, you'll
need to remember to add the same `style` attributes to every web page
to achieve a measure of consistency. CSS provides a better way.


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
