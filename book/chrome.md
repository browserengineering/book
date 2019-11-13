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

To implement links, the browser chrome, and so on, we need to start
with clicks. We already handle key presses; clicks work similarly in
Tk: an event handler bound to a certain event. For scrolling, we
defined `scroll_down` and bound it to `<Down>`; for click handling we
will define `handle_click` and bind it to `<Button-1>`, button number
1 being the left button on the mouse.[^1]

[^1]: Button 2 is the middle button; button 3 is the right hand button.


``` {.python}
window.bind("<Button-1>", handle_click)

def handle_click(e):
    pass
```

Inside `handle_click`, we want to figure out what link the user has
clicked on. We'll need to look at the `e` argument, which contains an
\"event object\". This object has `x` and `y` fields, which refer to
where the click happened, relative to the corner of the browser
window. Since the canvas is in the top-left corner of the window,
those are also the *x* and *y* coordinates relative to the canvas. To
get coordinates relative to the web page, we need to account for
scrolling:

``` {.python}
x, y = e.x, e.y + scrolly
```

The next step is to figure out what links or other elements are at
that location. Naively, this seems like it should be easy. We already
have a tree of layout objects, each of which records size and
position. We could use those to find the element clicked on, something
like this:

``` {.python}
def handle_click(e):
    x, y = e.x, e.y + scrolly
    elt = find_element(x, y, mode)
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
before checking the node itself. That\'s because if you click on a
link, you want to click on the link, not the paragraph that it's in.
I search the children in reverse order in case children overlap; the
last one would be "on top".[^2]

[^2]: Real browsers use what are called *stacking contexts* to resolve
    the overlapping-elements question while allowing the order to be
    controlled with the `z-index` property.

Let\'s test it---but actually, first, let\'s handle a silly omission:
we don\'t have any special style for links! Let\'s quickly add support
for text color, which is controlled by the `color` property:

-   First, I add `color` to `INHERITED_PROPERTIES`, and changed `style`
    so that its default is `black`.
-   Next, I add the default style `a { color: blue; }` to our browser
    style sheet to color links blue.
-   Finally, I add a `color` field to `DrawText` and fill it out in
    `InlineLayout.text`.
-   Modified `DrawText.draw` to use the color for the `fill` parameter
    of `create_text`.

Once links have colors, you can actually *find* them on the page. So
try clicking on them!

... but it won\'t work. There is no layout object corresponding to a
link. The link text is laid out by `InlineLayout`, but each
`InlineLayout` handles a whole paragraph of text, not a single link.
We\'ll need to do some surgery on `InlineLayout` to fix this.

Adding line and text layout
===========================

Here\'s how I want inline layout to work, at a high level:

-   `InlineLayout`\'s children are a list of `LineLayout` objects. This
    list replaces `InlineLayout` keeping track of a `y` cursor position.
-   `LineLayout`\'s children are a list of `TextLayout` objects, one per
    word. Each `TextLayout` object has a `node`, which is always a
    `TextNode`. This replaces the `x` cursor position
-   Both `TextLayout` and `LineLayout` objects have a `w` and an `h` fields.
-   `InlineLayout` will create the `LineLayout` and `TextLayout`
    objects, then call `layout` on each `LineLayout`
-   `LineLayout.layout` will compute an `h` and an `x` and a `y`
    position and call `layout` on each `TextLayout`
-   `TextLayout.layout` will compute an `x` and a `y` position as well

To begin with, we\'ll need to create two new data structures:

``` {.python}
class LineLayout:
    def __init__(self, parent):
        self.parent = parent
        self.children = []
        self.w = 0

class TextLayout:
    def __init__(self, node, text):
        self.children = []
        self.node = node
        self.text = text
```

`LineLayout` is pretty run-of-the-mill here,[^3] but `TextLayout` is
unusual. First, it\'s got a dummy `children` field. I added that just to
keep it uniform; it\'ll always be an empty list.[^4] But then, it\'s
also got both a `node` and a `text` argument. That\'s because a single
`TextNode` contains multiple words, and I want each `TextLayout` to be a
single word.[^5] Finally, I\'m not attaching the `TextLayout` to its
parents. I\'ll do that in a separate `attach` method, which I\'ll define
below.

[^3]: There\'s no dummy `node` field on `LineLayout` because there\'s no
    HTML node that corresponds to a line of text, and there couldn\'t
    be.

[^4]: You may want to use inheritance to group all the `Layout`
    classes into a hierarchy, but I\'m trying to stick to some kind of
    easily-translatable subset of Python.

[^5]: Because of line breaking.


Next, since each `TextLayout` corresponds to a particular `TextNode`, we
can immediately compute its width and height. I\'m going make the height
of a `TextNode` be just the line-space for its font, with the 0.2
linespace added in `LineLayout`.[^6]

[^6]: Make sure you measure `text`, not `node.text`, which contains
    multiple words! That\'s an easy and confusing bug.

``` {.python}
bold = node.style["font-weight"] == "bold"
italic = node.style["font-style"] == "italic"
self.color = node.style["color"]
self.font = tkinter.font.Font(
    family="Times", size=16,
    weight="bold" if bold else "normal",
    slant="italic" if italic else "roman"
)
self.w = self.font.measure(text)
self.h = self.font.metrics('linespace')
```

We can compute all this immediately in the constructor; that\'s one of
the benefits of implementing styles and inheritance in the previous
chapter.

With a basic `TextLayout` and `LineLayout` in place, we can start
changing `InlineLayout`. First, let\'s create that list of lines, and
initialize it with a blank line:

``` {.python}
class InlineLayout:
    def __init__(self, parent):
        # ...
        self.children = [LineLayout(self)]
```

We\'ll need to create `LineLayout` and `TextLayout` objects as we lay
out text in `InlineLayout.layout`. That function does little but
recurse and call `text` on each `TextNode`.[^7] In that `text`
function, there is a lot of control flow and then either an increment
to `x` or an increment to `y` and a reset of `x`. We\'ll
just replace the first case by creating a `TextLayout` and adding it
to the last child in `self.children`, while the second case will
create a new `LineLayout`.

[^7]: In the last lab, we stopped relying on `open` and `close` for
    changing the `bold` and `italic` variables, so you might as well
    delete those functions entirely.

If you ignore the `terminal_space` stuff, my version of `text` now looks
like this:

``` {.python}
def text(self, node):
    words = node.text.split()
    for i, word in enumerate(words):
        tl  = TextLayout(node, word)
        line = self.children[-1]
        if line.w + tl.w > self.w:
            line = LineLayout(self)
            self.children.append(line)
        tl.attach(line)
```

Note that I\'ve removed the `DrawText` command and the display list.
I\'m planning to do that in `TextLayout` now.

Here, `TextLayout.attach` just adds text to a line and increments the
line\'s width

``` {.python}
def attach(self, parent):
    self.parent = parent
    parent.children.append(self)
    parent.w += self.w
```

What about `terminal_space`? Well, remember that we only have
`TextLayout` objects for words of text, not the intermediate inline
style nodes. We just need to know which `TextLayout` objects have spaces
after them, and which do not. I\'m going to add a `space` field to
`TextLayout`, which is going to tell me whether a space goes *after*
that word, and set it like this:

``` {.python}
if node.text[0].isspace() and len(self.children[-1].children) > 0:
    self.children[-1].children[-1].add_space()

for i, word in enumerate(words):
    # ...
    if i != len(words) - 1 or node.text[-1].isspace():
        tl.add_space()
```

Here the `add_space` function sets the `space` field and also
increases the parent line\'s width:

``` {.python}
def add_space(self):
    if self.space == 0:
        gap = self.font.measure(" ")
        self.space = gap
        self.parent.w += gap
```

Now that we have created the `LineLayout` and `TextLayout` objects, we
need to compute their *x* and *y* positions. Let\'s start from the
simplest and work up to the hardest. `TextLayout` does barely anything;
it is told where to be and it goes there:

``` {.python}
class TextLayout:
    def layout(self, x, y):
        self.x = x
        self.y = y
```

Recall that for a `TextLayout` we compute the width and height in the
constructor. Now, for a line, we need to just lay out the words in the
line, one by one:

``` {.python}
class LineLayout:
    def layout(self, y):
        self.y = y
        self.x = self.parent.x
        self.h = 0

        x = self.x
        leading = 2
        y += leading / 2
        for child in self.children:
            child.layout(x, y)
            x += child.w + child.space
            self.h = max(self.h, child.h + leading)
        self.w = x - self.x
```

Note the height computation. It will be totally wrong if you mix fonts
of different sizes in one line. You should instead first compute the
largest ascenders and descenders, use that to compute a baseline, then
place all the boxes, and finally compute the line height. Leading
would be computed per-word and would factor into the placement of the
baseline. I\'m not doing any of that here because we don\'t have any
elements of different font sizes anyway.[^8]

Now that we have words and lines laying themselves out, we need only
modify `InlineLayout`. This involves the most surgery, but the end
result is much simpler now that we\'ve got proper line and text
layout.

First, we can delete the `bold`, `italic`, `terminal_space`, and `dl`
fields; pass `node` to the `InlineLayout` constructor; and rename the
`layout` method to `recurse`:

``` {.python}
class InlineLayout:
    def __init__(self, parent, node):
        # ...
        self.node = node

    def recurse(self, node):
        if isinstance(node, ElementNode):
            for child in node.children:
                self.recurse(child)
        else:
            self.text(node)
```

This makes room for a new `layout` function, which calls `recurse` to
create children and then lays them out:

``` {.python}
def layout(self):
    self.x = self.parent.content_left()
    self.y = self.parent.content_top()
    self.w = self.parent.content_width()
    self.recurse(self.node)
    y = self.y
    for child in self.children:
        child.layout(y)
        y += child.h
    self.h = y - self.y
```

All that\'s left is generating a display list; let\'s just copy the
recursive `display_list` method from `BlockLayout` to `InlineLayout`
and `LineLayout` (skipping the borders and background color stuff),
and add a simple `display_list` to `TextLayout`, which just issues a
single `DrawText` call:

``` {.python}
def display_list(self):
    return [DrawText(
        self.x, self.y,
        self.text, self.font, self.color)]
```

*Phew*. That was a lot of surgery to `InlineLayout`. But as a result,
`InlineLayout` should now look a lot like the other layout classes.
And, we now have individual layout object corresponding to each word
in the document. The `handle_click` function should now working
correctly: when you click on a link `find_element` should return the
exact `TextNode` that you clicked on, from which you could get a link:

``` {.python}
elt = find_element(x, y, nodes)
while elt and not \
      (isinstance(elt, ElementNode) and \
       elt.tag == "a" and "href" in elt.attributes):
    elt = elt.parent
if elt:
    print(elt.attributes["href"])
```

Once we've found the link, we need to navigate to that page.

Navigating between pages
========================

I\'d like clicking a link to cause the browser to navigate to that page.
That would mean:

-   Parsing the new URL
-   Requesting that page
-   Lexing and parsing it
-   Downloading its rules and styling the page nodes
-   Generating a display list
-   Drawing that display list to the canvas
-   Waiting for events like scrolling the page and clicking on links

None of that is impossible, since we do all of it already, but right now
it\'s split between two functions: `show`, which executes the last three
bullet points, and the browser entry point that does the first few. I\'m
going to rejigger this architecture by introducing a new `Browser`
object, which will both manage the canvas and do the page-related stuff.
The GUI will be set up in the constructor:

``` {.python}
class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(self.window,
            width=800, height=600)
        self.canvas.pack()

        self.url = None
        self.scrolly = 0
        self.max_h = 0
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Button-1>", self.handle_click)
```

Then, we\'ll have a method to browse to a given web page:

``` {.python}
def browse(self, url):
    self.url = url
    host, port, path = parse_url(url)
    headers, body = request(host, port, path)
    text = lex(body)
    self.nodes = parse(text)
    self.rules = []
    with open("browser.css") as f:
        r = CSSParser(f.read()).parse()
        self.rules.extend(r)
    for link in find_links(self.nodes):
        lhost, lport, lpath = parse_url(relative_url(link, self.url))
        header, body = request(lhost, lport, lpath)
        self.rules.extend(CSSParser(body)).parse()
    self.rules.sort(key=lambda x: x[0].score())
    style(self.nodes, self.rules)
    self.page = Page()
    self.layout = BlockLayout(self.page, self.nodes)
    self.layout.layout(0)
    self.max_h = self.layout.height()
    self.display_list = self.layout.display_list()
    self.render()
```

Here the methods like `self.scrolldown`, `self.handle_click`, and
`self.render` are the functions we used to have of that name, but now
with an additional `self` argument.

Running the browser is straight-forward:

``` {.python}
browser = Browser()
browser.browse(sys.argv[1])
tkinter.mainloop()
```

In `handle_click`, that `print` statement can now call `browse`:

``` {.python}
def handle_click(self, e):
    # ...
    if elt:
        self.browse(relative_url(elt.attributes["href"], self.url))
```

Try the code out, say on this page---you could use the links at the
top of the page, for example. Our toy browser now sufficies to read
not just a chapter, but the whole book.

Browser chrome
==============

Now that we are navigating between pages all the time, it\'s easy to
get a little lost and forget what web page you\'re looking at.
Browsers solve this issue by with an address bar that shows the URL.
Let\'s implement a little address bar ourselves.

The idea is to reserve the top 60 pixels of the canvas and then draw
the address bar there. That 60 pixels is called the browser
*chrome*.[^10]

[^10]: Yep, that predates and inspired the name of the Chrome browser.

To do that, we first have to move the page content itself further down.
We can do that in `render`:

``` {.python}
def render(self):
    self.canvas.delete("all")
    for cmd in self.display_list:
        cmd.draw(scrolly - 60, canvas)
```

We need to make a similar change in `handle_click` to subtract that 60
pixels off when we convert back from screen to page coordinates. Next,
we need to cover up any actual page contents that got drawn to that top
60 pixels:

``` {.python}
def render(self):
    # ...
    self.canvas.create_rectangle(0, 0, 800, 60, fill='white')
```

Of course a real browser wouldn't draw that content in the first
place, but in Tk that\'s a little tricky to do,[^11] and covering it
up later is easier.

[^11]: Text that is partially covered by the browser chrome would be
    hard to handle.

The browser chrome area is now our playbox. Let's add an address bar:

``` {.python}
self.canvas.create_rectangle(10, 10, 790, 50)
self.canvas.create_text(15, 15, anchor='nw', text=self.url)
```

::: {.todo}
I'd like to tweak this a little to make the results look passable,
tweaking the font and the size of things.
:::

Browser history
===============

The back button is another classic browser feature our browser really
needs. I\'ll start by drawing the back button itself:

``` {.python}
self.canvas.create_rectangle(10, 10, 35, 50)
self.canvas.create_polygon(15, 30, 30, 15, 30, 45, fill='black')
```

In Tk, `create_polygon` takes a list of coordinates and connects them
into a shape. Here I\'ve got three points that form a simple triangle
evocative of a back button. You\'ll need to shrink the address bar so
that it doesn\'t overlap this new back button.

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

How should `self.go_back()` work? Well, to begin with, we\'ll need to
store the *history* of the browser got to the current page. I\'ll add
a `history` field to `Browser`, and have `browse` append to it when
navigating to a page. The `self.url` field now becomes the last
element of `self.history`:

``` {.python}
def browse(self, url):
    self.history.append(url)
    # ...
```

Now `self.go_back()` knows where to go:

``` {.python}
def go_back(self):
    if len(self.history) > 1:
        self.browse(self.history[-2])
```

This is almost correct, but if you click the back button twice, you\'ll
go forward instead, because `browse` has appended to the history.
Instead, we need to do something more like:

``` {.python}
def go_back(self):
    if len(self.history) > 1:
        self.history.pop()
        back = self.history.pop()
        self.browse(back)
```

::: {.todo}
I'd like to add a forward button too, which requires the history list
to contain a cursor.
:::

Summary
=======

It\'s been a lot of work just to handle links! We have totally re-done
line and text layout. That\'s allowed us to determine which piece of
text a user clicked on, which allows us to determine what link they\'ve
clicked on and where that links goes. And as a cherry on top, we\'ve
implemented a simple browser chrome, which displays the URL of the
current page and allows the user to go back.

Exercises
=========

-   Clicking the address bar should allow the user to enter a new URL.
    Text entry is actually very complex, so I recommend taking input
    on the command line.

-   URLs can contain a *fragment*, which comes at the end of a URL and
    is separated from the path by a hash sign `#`. When the browser
    navigates to a URL with a fragment, it should scroll the page so
    that the element with that identifier is at the top of the screen.
    Also, implement fragment links: relative URLs that begin with a `#`
    don\'t load a new page, but instead scroll the element with that
    identifier to the top of the screen.

-   Implement basic *bookmarks*. Add a button to the browser chrome;
    clicking it should bookmark the page. When you\'re looking at a
    bookmarked page, that bookmark button should look different to
    remind the user that the page is bookmarked, and clicking it
    should un-bookmark it. Also, add a keyboard shortcut, like
    `Ctrl-b`, for printing the list of bookmarks to the console.[^12]

[^12]: You can respond to `Ctrl-b` directly by binding `<Control-b>` in
    Tk.

-   In real browsers, links are a different color when you\'ve visited
    them before---usually purple. Implement that feature by storing
    the set of all visited pages and checking them when you lay out
    links. Link color is currently driven by CSS: you need to work
    with that somehow. I recommend adding the `visited` class to all
    links that have been visited, right after parsing and before
    styling. Then you could add a browser style that uses that class.
    You could add *pseudo*-class, like in [Chapter 10](reflow.md),
    which is what real browsers do.

-   Right now, line layout looks super weird if some text is bigger
    than other text. Let\'s fix that. You\'ll need to add the
    `font-size` attribute (it\'s inheritable!) and use it to draw
    text; then, in `LineLayout`, first collect the ascender and
    descender size of each word in the line, use that to compute the
    line height and the position of the baseline, and place text
    relative to that baseline.
