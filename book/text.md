---
title: Formatting Text
chapter: 3
prev: graphics
next: html
...

In the last chapter, your web browser created a graphical window and
drew a grid of characters to it. That's OK for Chinese, but English
text features characters of different widths and words that you can't
break across lines.[^1] In this chapter, we'll add those capabilities.
You'll be able to read this page in your browser!

[^1]: There are lots of languages in the world, and lots of
    typographic conventions. A real web browser supports every
    language from Arabic to Zulu, but this book focuses on English.
    Text is near-infinitely complex, but this book cannot be
    infinitely long!

What is a font?
===============

So far, we've called `create_text` with a character and two
coordinates to write text to the screen. But we never specified the
font, the size, or the color. To talk about those things, we need to
create and use font objects.

What is a *font*, exactly? Well, in the olden days, printers arranged
little metal slugs on rails, covered them with ink, and pressed them
to a sheet of paper, creating a printed page. The metal shapes came in
boxes, one per letter, so you'd have a (large) box of e's, a (small)
box of x's, and so on. The boxes came in cases (one for upper*case*
and one for lower*case* letters). The set of cases was called a
font.[^2] Naturally, if you wanted to print larger text, you needed
different (bigger) shapes, so those were a different font; a
collection of fonts was called a *type*, which is why we call it
typing. Variations—like bold or italic letters—were called that type's
"faces".

[^2]: The word is related to *foundry*, which would create the little
    metal shapes.

This nomenclature reflects the world of the printing press: metal
shapes in boxes in cases of different types. Our modern world instead
has dropdown menus, and the old words no longer match it. "Font" can
now mean font, typeface, or type,[^3] and we say a font contains
several different *weights* (like "bold" and "normal"),[^4] several
different *styles* (like "italic" and "roman", which is what
not-italic is called),[^5] and arbitrary *sizes*.[^6] Welcome to the
world of magic ink.

[^3]: Let alone "font family", which can refer to larger or smaller
    collections of types.

[^4]: But sometimes other weights as well, like "light", "semibold",
    "black", and "condensed". Good fonts tend to come in many weights.

[^5]: Sometimes there are other options as well, like maybe there's a
    small-caps version; these are sometimes called *options* as well.
    And don't get me started on automatic versus manual italics.

[^6]: Font looks especially good at certain sizes where *hints* tell
    the computer how to best to align it to the pixel grid.

Yet Tk's *font objects* correspond to the older meaning of font: a
type at a fixed size, style, and weight. For example:

``` {.python expected=False}
import tkinter.font
bi_times = tkinter.font.Font(
    family="Times",
    size=16,
    weight="bold",
    slant="italic",
)
```

::: {.quirk}
Your computer might not have "Times" installed. The
`tkinter.font.families()` command lists the fonts available on your
machine; and pick something other than `Times` if you need to.
:::

Font objects can be passed to `create_text`'s `font` argument:

``` {.python expected=False}
canvas.create_text(200, 100, text="Hi!", font=bi_times)
```

::: {.further}
In the olden times, American type setters kept their boxes of metal
shapes arranged in a [California job case][california], which combined
lower- and upper-case letters side by side in one case, making type
setting easier. The upper-/lower-case nomenclature dates from
centuries earlier.
:::

[california]: http://www.alembicpress.co.uk/Typecases/CJCCASE.HTM 

Measuring text
==============

Text takes up space vertically and horizontally, and the font object's
`metrics` and `measure` methods measure that space:[^7]

``` {.python expected=False}
>>> bi_times.metrics()
{'ascent': 15, 'descent': 7, 'linespace': 22, 'fixed': 0}
>>> bi_times.measure("Hi!")
31
```

[^7]: On your computer, you might get different numbers. That's
    right---text rendering is OS-dependent, because it is complex
    enough that everyone uses one of a few libraries to do it, usually
    libraries that ship with the OS. That's why macOS fonts tend to be
    "blurrier" than the same font on Windows: different libraries make
    different trade-offs.

The `metrics` call yields information about the vertical dimensions of
the text: the `linespace` is how tall the text is, which includes an
`ascent` which goes "above the line" and a `descent` that goes "below
the line".[^8] The `ascent` and `descent` matter when words in
different sizes sit on the same line: they ought to line up "along the
line", not along their tops or bottoms.

[^8]: The `fixed` parameter is actually a boolean and tells you whether
    all letters are the same *width*, so it doesn't really fit here.

Let's dig deeper. Remember that `bi_times` is size-16 Times: why does
`font.metrics` report that it is actually 22 pixels tall? Well, first
of all, size-16 meant sixteen *points*, which are defined as 72^nd^s
of an inch, not sixteen *pixels*, which your monitor probably has
around 100 of per inch.[^pt-for-fonts] Those sixteen points measure
not the individual letters but the metal blocks the letters were once
carved from, which by necessity were larger than the letters
themselves. In fact, different size-16 fonts have letters of varying
heights:

[^pt-for-fonts]: Tk doesn't use points anywhere else in its API. It's
    supposed to use pixels if you pass it a negative number, but that
    doesn't appear to work.

``` {.python expected=False}
>>> tkinter.font.Font(family="Courier", size=16).metrics()
{'fixed': 1, 'ascent': 13, 'descent': 4, 'linespace': 17}
>>> tkinter.font.Font(family="Times", size=16).metrics()
{'fixed': 0, 'ascent': 14, 'descent': 4, 'linespace': 18}
>>> tkinter.font.Font(family="Helvetica", size=16).metrics()
{'fixed': 0, 'ascent': 15, 'descent': 4, 'linespace': 19}
```

The `measure()` method is more direct: it tells you how much
*horizontal* space text takes up, in pixels. This depends on the text,
of course, since different letters have different width:[^9]

``` {.python expected=False}
>>> bi_times.measure("Hi!")
31
>>> bi_times.measure("H")
17
>>> bi_times.measure("i")
6
>>> bi_times.measure("!")
8
>>> 17 + 8 + 6
31
```

[^9]: The sum at the end of this snippet may not work on your machine:
    the width of a word is not always the sum of the widths of its
    letters. That's because Tk always returns whole pixels, but
    internally might do some rounding. Plus some fonts use something
    called *kerning* to shift letters a little bit when particular pairs
    of letters are next to one another, though I don't know if Tk
    supports this.


You can use this information to lay text out on the page. For example,
suppose you want to draw the text "Hello, world!" in two pieces, so that
"world!" is italic. Let's use two fonts:

``` {.python expected=False}
font1 = tkinter.font.Font(family="Times", size=16)
font2 = tkinter.font.Font(family="Times", size=16, slant='italic')
```

We can now lay out the text, starting at `(200, 200)`:

``` {.python expected=False}
x, y = 200, 200
canvas.create_text(x, y, text="Hello, ", font=font1)
x += font1.measure("Hello, ")
canvas.create_text(x, y, text="world!", font=font2)
```

You should see "Hello," and "world!", correctly aligned and with the
second word italicized.

Unfortunately, this code has a bug, though one masked by the choice of
example text: replace "world!" with "overlapping!" and the two words
will overlap. That's because the coordinates `x` and `y` that you pass
to `create_text` tell Tk where to put the *center* of the text. It
only worked for "Hello, world!" because "Hello," and "world!" are the
same length!

Luckily, the meaning of the coordinate you pass in is configurable. We
can instruct Tk to treat the coordinate we gave as the top-left corner
of the text by setting the `anchor` argument to `"nw"`, meaning the
"northwest" corner of the text:

``` {.python expected=False}
x, y = 200, 225
canvas.create_text(x, y, text="Hello, ", font=font1, anchor='nw')
x += font1.measure("Hello, ")
canvas.create_text(x, y, text="overlapping!", font=font2, anchor='nw')
```

Modify the `render` function to set `anchor` to `"nw"`; we didn't need
to do that in the previous chapter because all Chinese characters are
the same width.

::: {.further}
If you find font metrics confusing, you're not the only one! In 2012,
the Michigan Supreme Court heard [*Stand Up for Democracy v. Secretary
of State*][case], a case that centered on the definition of font size.
The court decided (correctly) that font size is the size of the metal
blocks that letters were carved from and not the size of the letters
themselves.
:::

[case]: http://publicdocs.courts.mi.gov/opinions/final/sct/20120803_s145387_157_standup-op.pdf 

Word by word
============

In the last chapter, the `layout` function looped over the text
character-by-character and moved to the next line whenever we ran out
of space. That's appropriate in Chinese, where each character more or
less *is* a word. But in English you can't move to the next line in
the middle of a word. Instead, we need to lay out the text one word at
a time:[^10]

[^10]: This code splits words on whitespace. It'll thus break on
    Chinese, since there won't be whitespace between words. Real
    browsers use language-dependent rules for laying out text,
    including for identifying word boundaries.

``` {.python expected=False}
for word in text.split():
    w = font.measure(word)
    if x + w >= WIDTH - HSTEP:
        y += font.metrics("linespace") * 1.2
        x = HSTEP
    self.display_list.append((x, y, word))
    x += w + font.measure(" ")
```

There's a lot of moving parts to this code. First, we measure the width
of the text, and store it in `w`. We'd normally draw the text at `x`,
so its right end would be at `x + w`, so we check if that's past the
edge of the page. Now we have the location to *start* drawing the word,
so we add to the display list; and finally we update `x` to point to the
end of the word.

There are a few surprises in this code. One is that I call `metrics`
with an argument; that just returns the named metric directly. Also, I
increment `x` by `w + font.measure(" ")` instead of `w`. That's
because I want to have spaces between the words: the call to `split()`
removed all of the whitespace, and this adds it back. I don't add the
space to `w` on the second line, though, because you don't need a
space after the last word on a line.

Finally, note that I multiply the linespace by 1.2 when incrementing
`y`. Try removing the multiplier: you'll see that the text is harder
to read because the lines are too close together.[^11] Instead, it is
common to add "line spacing" or "leading"[^12] between lines. The 20%
line spacing is a normal amount.

[^11]: Designers say the text is too "tight".

[^12]: So named because in metal type days, thin pieces of lead that
    were placed between the lines to space them out. Lead is a softer
    metal than what the actual letter pieces were made of, so it could
    compress a little to keep pressure on the other pieces. Pronounce
    it "led-ing" not "leed-ing".

::: {.further}
Breaking lines in the middle of a word is called hyphenation, and can
be turned on via the [`hyphens` CSS property][hyphens]. Browsers
use the [Knuth-Liang hyphenation algorithm][liang], which uses a
dictionary of word fragments to prioritize possible hyphenation
points, to implement this.
:::

[liang]: http://www.tug.org/docs/liang/liang-thesis.pdf
[hyphens]: https://drafts.csswg.org/css-text-3/#hyphens-property

Styling text
============

Right now, all of the text on the page is drawn with one font. But web
pages sometimes **bold** or *italicise* text using the `<b>` and `<i>`
tags. It'd be nice to support that, but right now, the code resists
the change: the `layout` function only receives the text of the page
as input, and so has no idea where the bold and italics tags are.

Let's change `lex` to return a list of *tokens*, where a token is
either a `Text` object (for a run of characters outside a tag) or a
`Tag` object (for the contents of a tag). You'll need to write the
`Text` and `Tag` classes:[^13]
    
[^13]: If you're familiar with Python, you might want to use the
    `dataclass` library, which makes it easier to define these sorts
    of utility classes.

``` {.python}
class Text:
    def __init__(self, text):
        self.text = text

class Tag:
    def __init__(self, tag):
        self.tag = tag
```

`lex` must now gather text into `Text` and `Tag` objects:[^14]

[^14]: If you've done exercises in prior chapters, your code will look
    different. Code snippets in the book always assume you haven't
    done the exercises, so you'll need to port your modifications.


``` {.python}
def lex(body):
    out = []
    text = ""
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
            if text: out.append(Text(text))
            text = ""
        elif c == ">":
            in_tag = False
            out.append(Tag(text))
            text = ""
        else:
            text += c
    if not in_tag and text:
        out.append(Text(text))
    return out
```

At the end of the loop, `lex` dumps any accumulated text as a `Text`
object. Otherwise, if you never saw an angle bracket, you'd return an
empty list of tokens. But unfinished tags, like in `Hi!<hr`, are
thrown out.[^15]

[^15]: This may strike you as an odd decision: why not raise an error,
    or finish up the tag for the author? Good questions, but dropping
    the tag is what browsers do.

Note that `Text` and `Tag` are asymmetric: `lex` avoids empty
`Text` objects, but not empty `Tag` objects. That's because an empty
`Tag` object represents the HTML code `<>`, while an empty `Text`
object with empty text represents no content at all.

Now `layout` has access not just to the text of the page, but also the
tags in it. So `layout` must loop over tokens, not text:

``` {.python expected=False}
def layout(tokens):
    for tok in tokens:
        if isinstance(tok, Text):
            for word in tok.text.split():
                # ...
```

`layout` can also examine tag tokens to change font when directed by
the page. Let's start with support for weights and styles, with two
corresponding variables:

``` {.python replace=weight/self.weight,style/self.style}
weight = "normal"
style = "roman"
```

Those variables must change when the bold and italics open and close
tags are seen:

``` {.python replace=weight/self.weight,style/self.style indent=8}
if isinstance(tok, Text):
    # ...
elif tok.tag == "i":
    style = "italic"
elif tok.tag == "/i":
    style = "roman"
elif tok.tag == "b":
    weight = "bold"
elif tok.tag == "/b":
    weight = "normal"
```

Note that this code correctly handles not only `<b>bold</b>` and
`<i>italic</i>` text, but also `<b><i>bold italic</i></b>`
text.[^even-misnested]

[^even-misnested]: It even handles mis-nested tags like
    `<b>b<i>bi</b>i</i>`, but it does not handle
    `<b><b>twice</b>bolded</b>` text. We'll return to both in the
    [next chapter](html.md).

The `bold` and `italic` variables are used to select the font. Since
the font is computed in `layout` but used in `render`, we'll need to
add the font used to each entry in the display list.

``` {.python expected=False}
if instance(tok, Text):
    font = tkinter.font.Font(
        size=16,
        weight=weight,
        slant=style,
    )
    for word in tok.text.split():
        # ...
        display_list.append((x, y, word, font))
```

Make sure to update `render` to expect and use this extra font field
in display list entries.

::: {.further}
*Italic* fonts were developed in Italy (hence the name) to mimic a
cursive handwriting style called "[chancery hand][chancery]".
Non-italic fonts are called *roman* because they mimic text on Roman
monuments. There is an obscure third option: [*oblique*
fonts][oblique], which look like roman fonts but are slanted.
:::

[chancery]: https://en.wikipedia.org/wiki/Chancery_hand
[oblique]: https://en.wikipedia.org/wiki/Oblique_type

A layout object
===============

With all of these tags, `layout` has become quite large, with lots of
local variables and some complicated control flow. That is one sign
that something deserves to be a class, not a function:

``` {.python}
class Layout:
    def __init__(self, tokens):
        self.display_list = []
```

Every local variable in `layout` then becomes a field of `Layout`:

``` {.python}
self.x = HSTEP
self.y = VSTEP
self.weight = "normal"
self.style = "roman"
self.size = 16
```

The core of the old `layout` is a loop over tokens, and we can move
the body of that loop to a method on `Layout`:

``` {.python}
def __init__(self, tokens):
    # ...
    for tok in tokens:
        self.token(tok)

def token(self, tok):
    if isinstance(tok, Text):
        # ...
    elif tok.tag == "i":
        self.style = "italic"
    # ...
```

In fact, the body of the `isinstance(tok, Text)` branch can be moved
to its own method:

``` {.python replace=16/self.size indent=4}
def text(self, text):
    font = tkinter.font.Font(
        size=16,
        weight=self.weight,
        slant=self.style,
    )
    for word in text.split():
        # ...
```

Now that everything has moved out of `Browser`'s old `layout`
function, it can be replaced with calls into `Layout`:

``` {.python}
def layout(self, tokens):
    self.display_list = Layout(tokens).display_list
    self.render()
```

When you do big refactors like this, it's important to work
incrementally. It might seem more efficient to change everything at
once, that efficiency brings with it a risk of failure: trying to do
so much that you get confused and have to abandon the whole refactor.

Anyway, this refactor isolated all of the text-handling code into its
own method, with the main `token` function just branching on the tag
name. Let's take advantage of the new, cleaner organization to add
more tags. With font weights and styles working, size is the next
frontier in typographic sophistication. One simple way to change font
size is the `<small>` tag and its deprecated sister tag
`<big>`.[^why-obsolete]

[^why-obsolete]: In your web design projects, use the CSS `font-size`
    property to change text size instead of `<big>` and `<small>`. But
    since we haven't [implemented CSS](styles.html) for our browser,
    we're stuck using them here.

Our experience with font styles and weights suggests a simple
approach. First, a field in `Layout` to track font size:

``` {.python}
self.size = 16
```

That variable is used to create the font object:

``` {.python}
font = tkinter.font.Font(
    size=self.size,
    weight=self.weight,
    slant=self.style,
)
```

Finally, the `<big>` and `<small>` tags change the value of `size`:

``` {.python}
def token(self, tok):
    # ...
    elif tok.tag == "small":
        self.size -= 2
    elif tok.tag == "/small":
        self.size += 2
    elif tok.tag == "big":
        self.size += 4
    elif tok.tag == "/big":
        self.size -= 4
```

Try wrapping a whole paragraph in `<small>`, like you would a bit of
fine print, and enjoy your newfound typographical freedom.

::: {.further}
All of `<b>`, `<i>`, `<big>`, and `<small>` date from an earlier,
pre-CSS era of the web. Since CSS can now change how those tags
appear, `<b>`, `<i>`, and `<small>` have hair-splitting
[appearance-independent meanings][html5-text].
:::

[html5-text]: https://html.spec.whatwg.org/multipage/text-level-semantics.html#the-u-element

Text of different sizes
=======================

Start mixing font sizes, like `<small>a</small><big>A</big>`, and
you'll quickly notice a problem with the font size code: the text is
aligned along its top, not "along the line", as if it's hanging from a
clothes line.

Let's think through how to fix this. If the big text is moved up, it
would overlap with the previous line, so the smaller text has to be
moved down. That means its vertical position has to be computed later,
*after* the big text passes through `token`. But since the small text
comes through the loop first, we need a *two-pass* algorithm for lines
of text: the first pass identifies what words go in the line and
computes their `x` positions, while the second pass vertically aligns
the words and computes their `y` positions.

Let's start with phase one. Since one line contains text from many
tags, we need a a field on `Layout` to store the line-to-be. That
field, `line`, will be a list, and `text` will add words to it instead
of the display list. Entries in `line` will have `x` but not `y`
positions, since `y` positions aren't computed in the first phase:


``` {.python}
def __init__(self, tokens):
    # ...
    self.line = []
    # ...

def text(self, text):
    # ...
    for word in text.split():
        # ...
        self.line.append((self.x, word, font))
```

The second phase, meanwhile, needs to happen when we're finished with
a line; I'm calling that second phase `flush()`:

``` {.python}
if self.x + w > WIDTH - HSTEP:
    self.flush()
```

This new `flush` function has three main responsibilities:

1. It must align the words along the line;
2. It must add all those words to the display list; and
3. It must update the `x` and `y` fields

Since we want words to line up "on the line", let's start by computing
where that line should be. That depends on the metrics for all the
fonts involved:

``` {.python}
def flush(self):
    if not self.line: return
    metrics = [font.metrics() for x, word, font in self.line]
```

To line up the words up "along the line", let's start by computing
where that line should be. We need to locate the tallest word:

``` {.python}
max_ascent = max([metric["ascent"] for metric in metrics])
```

The line is then `max_ascent` below `self.y`—or actually a little more
to account for the leading:[^leading-half]

[^leading-half]: Actually actually, 20% leading doesn't add 20% of the
    ascender above the ascender and 20% of the descender below the
    descender. Instead, it adds [10% of the line height in both
    places][line-height-def].
[line-height-def]: https://www.w3.org/TR/CSS2/visudet.html#leading
    
``` {.python}
baseline = self.y + 1.2 * max_ascent
```

Now that we know where the line is, we can place each word relative to
that line and add it to the display list:

``` {.python}
for x, word, font in self.line:
    y = baseline - font.metrics("ascent")
    self.display_list.append((x, y, word, font))
```

Note how `y` starts at the baseline, and moves *up* by just enough to
accomodate that word's ascender.

Finally, `flush` must update the `Layout`'s `x`, `y`, and `line`
fields. `x` and `line` are easy:

``` {.python}
self.x = HSTEP
self.line = []
```

Meanwhile, `y` must be far enough below `baseline` to account for the
deepest descender:

``` {.python}
max_descent = max([metric["descent"] for metric in metrics])
self.y = baseline + 1.2 * max_descent
```

Now all the text is aligned along the line, even when text sizes are
mixed. Plus, this new `flush` function is convenient for other line
breaking jobs. For example, in HTML the `<br>` tag[^self-closing] ends
the current line and starts a new one:

[^self-closing]: Which is a self-closing tag, so there's no `</br>`.
    Many tags that *are* content, instead of annotating it, are like
    this. Some people like adding a final slash to self-closing tags,
    like `<br/>`, but this is not required in HTML.

``` {.python}
def token(self, tok):
    # ...
    elif tok.tag == "br":
        self.flush()
```

Likewise, paragraphs are defined by the `<p>` and `</p>` tags, so
`</p>` also ends the current line:

``` {.python indent=4}
def token(self, tok):
    # ...
    elif tok.tag == "/p":
        self.flush()
        self.y += VSTEP
```

I add a bit extra to `y` here to create a little gap between
paragraphs.

::: {.further}
Actually, browsers support not only *horizontal* but also [*vertical*
writing systems][vertical], like some traditional East Asian writing
styles. A particular challenge is [Mongolian script][mongolian].
:::

[vertical]: https://www.smashingmagazine.com/2019/08/writing-modes-layout/
[mongolian]: https://www.w3.org/TR/mlreq/

Summary
=======

The last chapter introduced a browser that laid out Chinese text. Now it
does English, too:

- Text is laid out word-by-word
- Lines are split at word boundaries
- Text can be bold or italic
- Text of different sizes can be mixed

You can now use your browser to read an essay, a blog post, or a book!

::: {.signup}
:::

Exercises
=========

*Links:* The `<a>` tag[^a-for-anchor] defines links. Color them in
blue with an underline; there's an `underline` argument to the `Font`
constructor. Note that links normally have attributes, as in `<a
href="...">`.

[^a-for-anchor]: The `<a>` tag is short for "anchor". I don't think it
    makes sense, but (despite an attempt to get rid of the tag in
    XHTML 2) we're stuck with it.

*Centered Text:* This book's page titles are centered: find them
between `<h1 class="title">` and `</h1>`. Make your browser center the
text in these titles. Each line has to be centered individually,
because different lines will have different lengths.

*Superscripts:* Add support for the `<sup>` tag: text in this tag
should be smaller (perhaps half the normal text size) and be placed so
that the top of a superscript lines up with the top of a normal
letter.

*Soft hyphens:* The soft hyphen character, written `\N{soft hyphen}`
in Python, represents a place where the text renderer can, but doesn't
have to, insert a hyphen and break the word across lines. Add support
for it. If a word doesn't fit at the end of a line, check if it has
soft hyphens, and if so break the word across lines. Remember that a
word can have multiple soft hyphens in it, and make sure to draw a
hyphen when you break a word. The word
"super­cala­fraga­listic­expi­ala­do­shus" is a good test case.

*Preformatted text:* Add support for the `<pre>` tag. Unlike normal
paragraphs, text inside `<pre>` tags doesn't automatically break
lines, and whitespace like spaces and newlines are preserved. Use a
fixed-width font like `Courier New` or `SFMono` as well. Make sure
tags work normally inside `<pre>` tags: it should be possible to bold
some text inside a `<pre>`.
