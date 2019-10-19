---
title: Saving Partial Layouts
chapter: 10
prev: scripts
next: security
...

Our little web browser now renders web pages that *change*. That means
our browser is now doing styling and layout multiple times per page.
Most of that styling and layout, however, is a waste: even when the
page changes, it usually doesn\'t change *much*, and layout is
expensive. In this chapter we\'ll put the breaks on new features and
implement some speed-ups instead.

Profiling our browser
=====================

Before we start working on speeding up our browser, let\'s find out
what\'s taking up so much time. Let\'s take a moment to list the stuff
our browser does. First, on the initial load:

-   It downloads a web page (including parsing the URL, opening a
    connection, sending a request, and getting a response);
-   Then it parses the HTML (including lexing and parsing)
-   Then it parses the CSS (including finding the page CSS files,
    downloading them, parsing them, and sorting them)
-   Then it runs the JavaScript (including finding the page JS files,
    downloading them, and running them)

And then every time it does layout:

-   It styles the page
-   It lays out the page
-   It computes the display list
-   It applies all of the drawing commands
-   And it draws the browser chrome

I\'d like to get timing measurements on both of these, so that we know
what to work on. To do that, I\'m basically going to check the wall
clock time at various points in the process and do some subtraction. To
keep it all well-contained, I\'m going to make a `Timer` class to store
that wall-clock time, with a method to report how long a phase took.

``` {.python}
import time

class Timer:
    def __init__(self):
        self.phase = None
        self.time = None

    def start(self, name):
        if self.phase: self.stop()
        self.phase = name
        self.time = time.time()

    def stop(self):
        print("[{:>10.6f}] {}".format(time.time() - self.time, self.phase))
        self.phase = None
```

That wacky string in the `print` statement is a Python \"format string\"
that will write out the time right-aligned, ten characters wide, and
with six digits after the decimal point. Using the timer is pretty easy.
First we define a `timer` field on browsers:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.timer = Timer()
```

Then we call `start` every time we start doing something useful. For
example, in `browse`, I start the `Downloading` phase:

``` {.python}
self.timer.start("Downloading")
```

I\'m just going to go ahead and insert one of these for each of the
bullet points above. Then, at the end of `render`, I stop the timer:

``` {.python}
self.timer.stop()
```

Your results may not match mine,[^1] but here\'s what I saw on my
console on a full page load for this web page.

    [  0.225331] Download
    [  0.028922] Parse HTML
    [  0.001835] Parse CSS
    [  0.003599] Run JS
    [  0.007073] Style
    [  0.517131] Layout
    [  0.022553] Display List
    [  0.275645] Rendering
    [  0.008225] Chrome

The overall process takes about one second (60 frames), with layout
consuming half and then rendering and network consuming the rest.
Moreover, the downloading only takes place on initial load, so it\'s
really layout and rendering that we\'re going to optimize. By the way,
keep in mind that while networking in a real web browser is similar
enough to our toy version,[^2] rendering is *more* complex in real web
browsers (since real browsers can apply many more stylistic effects)
and layout is *much more* complex in real browsers![^3][^4]

By the way, this might be the point in the book where you realize you
accidentally implemented something super-inefficiently. If you
something other than the network, layout, or rendering is taking a
long time, look into that.[^inexact] Whatever help it is your browser
needs, this chapter will only address layout and rendering.

[^inexact]: The exact speeds of each of these phases can vary quite a
    bit between implementations, and might depend (for example) on the
    exercises you ended up implementing, so don\'t sweat the details
    too much.

Adding `:hover` styles
======================

But to really drive home the need for faster layout and rendering,
let\'s implement a little browser feature that really taxes layout and
rendering: hover styles. CSS has a selector, called `:hover`, which
applies to whichever element you are currently hovering over. In real
browsers this is especially useful in combination with other selectors:
you might have the `a:hover` selector for links that you\'re hovering
over, or `section:hover h1` for headings inside the section you\'re
hoving over. We have a pretty limited set of selectors, but we can at
least try out the style

``` {.python}
:hover {
    border-top-width: 1px;
    border-right-width: 1px;
    border-bottom-width: 1px;
    border-left-width: 1px;
}
```

This should draw a box around the element we are currently hovering
over. Let\'s add this line to our browser stylesheet and try to
implement it. First, we need to parse the `:hover` selector. To do that,
we create a new kind of selector:

``` {.python}
class PseudoclassSelector:
    def __init__(self, cls):
        self.cls = cls

    def matches(self, node):
        return self.cls in node.pseudoclasses

    def score(self):
        return 0
```

Note that this expects an `ElementNode.pseudoclasses` field, which I\'ll
initialize to an empty set:

``` {.python}
class ElementNode:
    def __init__(self, parent, tagname):
        # ...
        self.pseudoclasses = set()
```

Now that we have this class, we need to parse these pseudo-class
selectors. That just involves copying the bit of code we have for class
selectors and replacing the period with a colon:

``` {.python}
def css_selector(s, i):
    # ...
    elif s[i] == ":":
        name, i = css_value(s, i + 1)
        return PseudoclassSelector(name), i
    # ...
```

Finally we need to handle hover events. In Tk, you do that by binding
the `<Motion>` event:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.window.bind("<Motion>", self.handle_hover)
```

The `handle_hover` method is pretty simple; it calls `find_element`,
walks up the tree until it finds an `ElementNode`, and then sets its
`hover` pseudoclass. Also, it has to unset the `hover` pseudoclass on
the previously-hovered element. I store a reference to that element in
the `hovered_elt` field, initialized to `None` in the constructor.

``` {.python}
class Browser:
    def handle_hover(self, e):
        x, y = e.x, e.y - 60 + self.scrolly
        elt = find_element(x, y, self.nodes)
        while elt and not isinstance(elt, ElementNode):
            elt = elt.parent
        if self.hovered_elt:
            self.hovered_elt.pseudoclasses.remove("hover")
        if not elt:
            self.hovered_elt = None
            return
        elt.pseudoclasses.add("hover")
        self.hovered_elt = elt
        self.relayout()
```

Note that hover calls `relayout`, because by changing the pseudoclasses
it potentially changes which rules apply to which elements and thus
which borders are applied where.

Try this out! You should see black rectangles appear over every element
you hover over, except of course that it\'ll take about a second to do
so and the refresh rate will be really really bad. Now it\'s really
clear we need to speed up layout.

::: {.quirk}
Actually, this is not how `:hover` works, because in normal CSS if you
hover over an element you probably also hover over its parent, and both
get the `:hover` style. Because of how limited our selector language is,
there\'s no style change that incrementalizes well that I can apply on
hover. So I\'m instead bowdlerizing how `:hover` works. In other words,
this chapter is a good guide to incremental reflow but a bad guide to
hover selectors. My deepest apologies. Please learn how to *use* CSS
from some other source.
:::

Relative positions
==================

How can we make layout faster? In the intro to this chapter, I
mentioned that the layout doesn\'t change *much*, and that\'s going to
be the key here. But what exactly do I mean? When the page is
*reflowed*[^5] due to some change in JavaScript or CSS (like with
hovering), the sizes and positions of *most* elements on the page
change. For example, changing what element you\'re hovering over will
change the height of that element (due to the added border), and that
will move every later element further down the page. However,
intuitively, even if some part of the page moves down, the relative
positions of its innards won\'t change much.

My goal will be to leverage this intuition to skip as much work as
possible on reflow. The idea is going to be to split layout into two
phases. In the first, we\'ll compute *relative* positions for each
element; in the second, we\'ll compute the absolute positions by adding
the parent offset to the relative position. This will also involve
splitting the `layout` function into two, which I will call `layout1`
and `layout2`,[^6] for each of our five layout types (block, line, text,
input, and inline).

I\'ll start with block layout. In block layout, the *x* position is
computed from the parent\'s left content edge and then changed in
`layout` to account for the margin. Likewise, the *y* position is
initialized from the argument in `layout` and then changed once to
account for margins. In other words, neither changes much, so it\'s safe
to move these absolute position fields to `layout2`.:

``` {.python}
def layout1(self):
    y = 0
    # ...

def layout2(self, y):
    self.x = parent.content_left()
    self.y = y
    self.x += self.ml
    self.y += self.mt
```

Note that `layout1` doesn\'t take any arguments any more, since it
doesn\'t need to know its position to figure out the *relative*
positions of its contents. Meanwhile, `layout2` still needs a `y`
parameter from its parent.

Now, `layout1` creates children and then makes a recursive calls to
`child.layout` to lay out its children. But since we\'ve split layout
into two phases, we need to change those recursive calls to call either
`layout1` or `layout2`. Actually we need to do both---but let\'s do a
recursive call to `layout1` in `layout1`, and add a loop to `layout2` to
do the recursive `layout2` call:

``` {.python}
y = self.y
for child in self.children:
    child.layout2(y)
    y += child.h + (child.mt + child.mb if isinstance(child, BlockLayout) else 0)
```

We also need to make sure that our layout objects don\'t do anything
interesting in the constructor. The hope, after all, is to keep layout
objects around between reflows, and that means we won\'t call the
constructor on reflow. If we do anything interesting in the constructor,
it won\'t get updated as the page changes. In block layout, the margin,
padding, and border values are computed in the constructor; let\'s move
that computation into `layout1`. Plus, the `children` array is
initialized in the constructor, but it\'s only modified in `layout1`.
Let\'s move that `children` array to `layout1`.

These few changes are complex, and we\'ll be doing the same thing again
for each of the other four layout types, so let\'s review what the code
we\'ve written guarantees:

`layout1`

:   This method is responsible for computing the twelve margin, padding,
    and border fields, *and* for creating the child layouts, *and* for
    assigning the `w` and `h` fields on the `BlockLayout`. Plus, it must
    call `layout1` on its children. It may not read the `x` or `y`
    fields on anything.

`layout2`

:   This method may read the `w` and `h` fields and is responsible for
    assigning the `x` and `y` fields on the `BlockLayout`. Plus, it must
    call `layout2` on its children.

Now that we\'ve got `BlockLayout` sorted, let\'s move on to text, input,
and line layout working. I\'ll save inline layout to the very end.

In `TextLayout`, the `layout` function does basically nothing, because
everything happens in the constructor. We\'ll rename `layout` to
`layout2` and move the computation of the `font`, `color`, `w`, and `h`
fields from the constructor into `layout1`.

In `InputLayout`, the width and height are computed in the constructor
(so let\'s move them to `layout1`), while `layout` computes `x` and `y`
but also creates a child `InlineLayout` for textareas. Let\'s put the
child layout creation in `layout1` and leave the `x` and `y` computation
in `layout2`. Plus, `layout2` will need to call `layout2` on the child
layout, if there is one.

Now let\'s get to `LineLayout`. Like in `BlockLayout`, we\'ll need to
split `layout` into two functions. But one quirk of `LineLayout` is that
it does not create its own children (`InlineLayout` is in charge of
that) and it also does not compute its own width (its children do that
in their `attach` methods). So unlike the other layout modes,
`LineLayout` will initialize the `children` and `w` fields in its
constructor, and its `layout1` won\'t recursively call `layout1` on its
children or compute the `w` field:

``` {.python}
class LineLayout:
    def __init__(self, parent):
        self.parent = parent
        parent.children.append(self)
        self.w = 0
        self.children = []

    def layout1(self):
        self.h = 0
        leading = 2
        for child in self.children:
            self.h = max(self.h, child.h + leading)
```

The `layout2` method looks more normal, however:

``` {.python}
class LineLayout:
    def layout2(self, y):
        self.y = y
        self.x = self.parent.x

        x = self.x
        leading = 2
        y += leading / 2
        for child in self.children:
            child.layout2(x, y)
            x += child.w + child.space
```

Finally, inline layout. For inline layout we want to accomplish the same
split as above. The current `layout` function computes the `x`, `y`, and
`w` fields, then creates its children with the `recurse` method, and
then calls `layout` on each child. If we peek inside `recurse` and its
helper methods `text` and `input`, we\'ll find that it only reads the
`w` field, which is allowed in `layout1`. So all of `recurse` can happen
in `layout1`. Hooray!

``` {.python}
class InlineLayout:
    def layout1(self):
        self.children = []
        LineLayout(self)
        self.w = self.parent.content_width()
        self.recurse(self.node)
        h = 0
        for child in self.children:
            child.layout1()
            h += child.h
        self.h = h
```

As mentioned above, there\'s a quirk with inline layout, which is that
it is responsible not only for its children (line layouts) but their
children (text and input layouts) as well. So, we need update the `text`
and `input` helpers to call `layout1` on the new layout objects they
create.

Meanwhile, `layout2` compute `x` and `y` and will need a new loop that
calls `layout2` on the children:

``` {.python}
class InlineLayout:
    def layout2(self, y):
        self.x = self.parent.content_left()
        self.y = self.parent.content_top()
        y = self.y
        for child in self.children:
            child.layout2(y)
            y += child.h
```

Note that I\'m accepting a `y` argument in `layout2`, even though I
don\'t use it. That\'s because `BlockLayout` passes one. Probably it
would be good to accept both `x` and `y` in every `layout2` method,
though that\'s not how I\'ve written my code. Also don\'t forget to
update `InputLayout` to pass a `y` argument in `layout2` when it handles
its child layout.

I want to emphasize that `recurse` is by far the slowest part of our
browser\'s layout algorithm,[^7] and since it happens in `layout1` we
will be able to mostly skip it. This will be our the big performance
win.

Finally, we need to update our browser to actually call all of these
functions. In `Browser.relayout`, where we used to call `layout`, let\'s
call `layout1` followed by `layout2`:

``` {.python}
self.layout = BlockLayout(self.page, self.nodes)
self.layout.layout1()
self.layout.layout2(0)
```

::: {.warning}
I cannot overemphasize how it important it is right now to *stop and
debug*. If you\'re anything like me, you will have a long list of very
minor bugs, including forgetting to add `self` to stuff when moving it
out of constructors, not moving the `children` array, and passing the
wrong number of arguments to one of the two layout phases. If you don\'t
get things working bug-free now, you\'ll spend three times as long
debugging the next phase, where we make things yet more complicated by
only calling `layout1` sometimes. Read through all of the constructors
for the layout classes to make sure they\'re not doing anything
interesting.
:::

Incrementalizing layout
=======================

If you time the browser, now that we\'ve split layout into two phases,
you\'ll find that not much has changed; for me, layout got about five
percent slower. To find out more, I made `layout1` and `layout2`
separate phases in the timer. Here\'s what it looks like:

    [  0.498251] Layout1
    [  0.006418] Layout2

So really `layout1` is taking all of the time and `layout2` is
near-instantaneous.[^8] That validates our next step: avoiding `layout1`
whenever we can.

The idea is simple, but the implementation will be tricky, because
sometimes you *do* need to lay an element out again; for example, the
element you hover over gains a border, and that changes its width and
therefore potentially its line breaking behavior. So you may need to run
`layout1` on *that* element. But you won\'t need to do so on its
siblings. The guide to this nonsense will be the responsibilities of
`layout1` and `layout2` outlined above. Because `layout1` reads the node
style, it only needs to be called when the node or its style changes.

Let\'s start by making a plan. Look over your browser and make a list of
all of the places where `relayout` is called. For me, these are:

-   In `parse`, on initial page load.
-   In `js_innerHTML`, when new elements are added to the page (and old
    ones removed).
-   In `edit_input`, when the contents of an input element is changed.
-   In `handle_hover`, when an element is hovered over.

Each of these needs a different approach:

-   In `parse`, we are doing the initial page load so we don\'t even
    have an existing layout. We need to create one, and that involves
    calling `layout1` on everything.
-   In `js_innerHTML`, the new elements and their parent are the only
    elements that have had their nodes or style changed.
-   In `edit_input`, only the input element itself has had a change to
    node or style.
-   In `handle_hover`, only the newly-hovered and newly-not-hovered
    elements have had a change to node or style.

Let\'s split `relayout` into pieces to reflect the above. First, let\'s
move the construction of `self.page` and `self.layout` into `parse`.
Then let\'s create a new `reflow` function that calls `style` and
`layout1` on an element of your choice. And finally, `relayout` will
just contain the call to `layout2` and the computation of the display
list. Here\'s `parse` and `relayout`:

``` {.python}
class Browser:
    def parse(self, body):
        # ...
        self.page = Page()
        self.layout = BlockLayout(self.page, self.nodes)
        self.reflow(self.nodes)
        self.relayout()

    def relayout(self):
        self.start("Layout2")
        self.layout.layout2(0)
        self.max_h = self.layout.h
        self.timer.start("Display List")
        self.display_list = self.layout.display_list()
        self.render()
```

The new `reflow` method is a little more complex. Here\'s what it looks
like after a simple reorganization:

``` {.python}
class Browser:
    def reflow(self, elt):
        self.timer.start("Style")
        style(self.nodes, self.rules)
        self.timer.start("Layout1")
        self.layout.layout1()
```

Note that while `reflow` takes an element as an argument, it ignores it,
and restyles and re-lays-out the whole page. That\'s clearly silly, so
let\'s fix that. First, the `style` call only needs to be passed
`elt`:

``` {.python}
style(elt, self.rules)
```

Second, instead of calling `layout1` on `self.layout`, we only want to
call it on the layout object corresponding to `elt`. The easiest way to
find that is with a big loop:[^10]

``` {.python}
def find_layout(layout, elt):
    if not isinstance(layout, LineLayout) and layout.node == elt:
        return layout
    for child in layout.children:
        out = find_layout(child, elt)
        if out: return out
```

This is definitely inefficient, because we could store the
element-layout correspondence on the node itself, but let\'s run with it
for the sake of simplicity. We can now change the
`self.layout.layout1()` line to:

``` {.python}
layout = find_layout(self.layout, elt)
if layout: layout.layout1()
```

This mostly works, but `find_layout` won\'t be happy on initial page
load because at that point some of the layout objects don\'t have
children yet. Let\'s add a line for that:[^11]

``` {.python}
def find_layout(layout, elt):
    if not hasattr(layout, "children"):
        return layout
    # ...
```

The logic of returning any layout object without a `children` field is
that if some layout object does not have such a field, it definitely
hasn\'t had `layout1` called on it and therefore we should, which we do
by returning it from `find_layout`.

Finally, let\'s go back to place where we call `relayout` and add a call
to `reflow`. The only complicated case is `handle_hover`, where you need
to call `reflow` both on the old `hovered_elt` and on the new one. (You
only need to call `layout` once, though.)

With this tweak, you should see `layout1` taking up almost no time,
except on initial page load, and hovering should be much more
responsible. For me the timings now look like this:

``` {.python}
[  0.009246] Layout1
[  0.003590] Layout2
```

So now rendering takes up roughly 89% of the runtime when hovering, and
everything else takes up 32 milliseconds total. That\'s not one frame,
but it\'s not bad for a Python application!

Faster rendering
================

Let\'s put a bow on this lab by speeding up `render`. It\'s actually
super easy: we just need to avoid drawing stuff outside the browser
window; in the graphics world this is called *clipping*. Now, we need to
make sure to draw text that *starts* outside the browser window but has
a part inside the window, so I\'m going to update the `DrawText`
constructor to compute where the text ends:

``` {.python}
self.y1 = y
self.y2 = y + 50
```

Ok, wait, that\'s not the code you expected. Why 50? Why not use
`font.measure` and `font.metrics`? Because `font.measure` and
`font.metrics` are quite slow: they actually execute text layout, and
that takes a long time! So I\'ll be using only *y* position for
clipping, and I\'ll be using an overapproximation to `font.metrics`. The
50 is not a magic value; it just needs to be *bigger* than any actual
line height. If it\'s too big, we render a few too many `DrawText`
objects, but it won\'t change the resulting page.

Now both `DrawText` and `DrawRect` objects have top-left and
bottom-right coordinates and we can check those in `render`:

``` {.python}
for cmd in self.display_list:
    if cmd.y2 - self.scrolly < 0: continue
    if cmd.y2 - self.scrolly > 600: continue
    cmd.draw(self.scrolly - 60, self.canvas)
```

That takes rendering down from a quarter-second to a hundredth of a
second for me, and makes the hover animation fairly smooth. A hover
reflow now takes roughly 25 milliseconds, with the display list
computation 44% of that, rendering 39%, and `layout2` 13%. We could
continue optimizing (for example, tracking invalidation rectangles in
rendering), but I\'m going to call this a success. We\'ve made
interacting with our browser more than 30 times faster, and in the
process made the `:hover` selector perfectly usable.

Summary
=======

With the changes in this chapter, my toy browser became roughly 30×
faster, to the point that it is now reacts to changes fast enough to
make simple animations. The cost of that is a more complex, two-pass
layout algorithm.

Exercises
=========

-   When you create a `DrawText` command in `TextLayout.display_list`,
    you already know the width and height of the text to be laid out.
    Use that to compute `y2` and `x2` in `DrawText`, and update the
    clipping implementation to clip horizontally as well as vertically.
-   Turns out, the `font.measure` function is quite slow! Change
    `TextLayout.add_space` to use a cache for the size of a space in a
    given font.
-   Count the time to lay out each type of layout object. That
    is---compute how much time is spent laying out `BlockLayout`
    objects, how much in `InlineLayout`, and so on. What percentage of
    the `layout1` time is spent handling inline layouts? If you did the
    first exercise, measure its effect.
-   Add support for the `setAttribute` method in JavaScript. Note that
    this method can be used to change the `id`, `class`, or `style`
    attribute, which can change which styles apply to the affected
    element; make sure to handle that with reflow. Furthermore, you can
    use `setAttribute` to update the `href` attribute of a `<link>`
    element, which means you must download a new CSS file and recompute
    the set of CSS rules. Make sure to handle that edge case as well. If
    you change the `src` attribute of a `<script>` tag, oddly enough,
    the new JavaScript file is not downloaded or executed.
-   Add support for `setTimeout` command in JavaScript;
    `setTimeout(ms, f)` should run the function `f` in `ms`
    milliseconds. In Python, you can use the `Timer` class from the
    `threading` library, but be careful---the callback on the timer is
    called in a separate thread, so you need to make sure no other
    JavaScript is running when calling the timeout handler. Use
    `setTimeout` to implement a simple animation; for example, you might
    implement a \"typewriter effect\" where a paragraph is typed out
    letter-by-letter. Check that your browser handles the animation
    relatively smoothly.

[^1]: These results were recorded on a 2019 13-inch MacBook Pro with a
    2.4GHz i5, 8 GB of LPDDR3 memory, and an Intel Iris Plus graphics
    655 with 1.5 GB of video memory, running macOS 10.14.6.

[^2]: Granted with caching, keep-alive, parallel connections, and
    incremental parsing to hide the delay...

[^3]: Of course they\'re also not written in Python...

[^4]: Now is a good time to mention that benchmarking a real browser is
    a lot harder than benchmarking ours. A real browser will run most of
    these phases simultaneously, and may also split the work over
    multiple CPU and GPU processes. Counting how much time everything
    takes is a chore. Real browsers are also memory hogs, so optimizing
    memory usage is just as important for them, which is a real pain to
    measure in Python. Luckily our browser doesn\'t have tabs so it\'s
    unlikely to strain for memory!

[^5]: That is, laid out but excluding initial layout.

[^6]: Look, I\'ve got a bit of a cold, I\'m not feeling very creative.

[^7]: Because it calls `font.measure`, which has to do a slow and
    expensive text rendering to get the right size. Text is crazy.

[^8]: Heh heh, near-instantaneous. Anyone that\'s worked on a
    high-performance application would like you to know that 6.418
    milliseconds is almost 40% of your one-frame time budget! But, this
    is a toy web browser written in Python. Cut me some slack.

[^10]: There is a subtlety in the code below. It\'s important to check
    the current node before recursing, because some nodes have two
    layout objects, in particular block layout elements that contain
    text and thus have both a `BlockLayout` and an `InlineLayout`. We
    want the parent, and doing the check before recursing guarantees us
    that.

[^11]: I recognize that in many languages, unlike in Python, you can\'t
    just add fields in some method without declaring them earlier on. I
    assume that in all of those cases you\'ve been initializing the
    fields with dummy values, and then you\'d check for that dummy value
    instead of using `hasattr`. Just make sure your dummy value for
    `children` isn\'t the empty list, since that is also a valid value.
    Better to use a null pointer or something like that, whatever your
    language provides.
