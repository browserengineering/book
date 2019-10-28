---
title: Formatting Text
chapter: 3
prev: graphics
next: html
...

In the last chapter, our web browser gained a graphical window and
began to display web pages with a grid of characters. That\'s OK for
Chinese text (and some other East Asian languages), but in this
chapter we\'ll better support English text, which features characters
of different widths and words that you can\'t break across lines.[^1]
A great English-language web page to try out is this page!

What is a font?
===============

So far, we\'ve written text to the canvas by calling the `create_text`
function with a character and two coordinates. That works if you don\'t
care much about the font, or the size, or the color, or the exact
position of the text. When you do care about those things, you need to
create and use font objects.

What is a *font*, exactly? Well, in the olden days, printers arranged
little metal shapes on rails, covered them with ink, and pressed them to
a sheet of paper, creating a printed page. The metal shapes came in
boxes, one per letter, so you\'d have a (large) box of e's, a (small)
box of x's, and so on. The set of all of the boxes was called a
font.[^2] Naturally, if you wanted to print larger text, you needed
different (bigger) shapes, so those were a different font. Fonts came in
different *types*: big, small, italic, bold, fraktur, and so on.
Generally, fonts with different sizes but the same general shape were
collectively called a *typeface*: one of the possible "faces" of the
"type".

This nomenclature reflects the what working with little pieces of metal
was like: there were lots of boxes, the boxes were in cases (hence
lower- and uppercase letter), the cases were on shelves, they came in
different types, and so on. In the shiny modern world, none of these
things exist, so the words have become more vague and confused: you can
use the word font to refer to fonts, typefaces, or types.[^3] Nowadays,
we say a font contains several different *weights* (like "bold" and
"normal"),[^4] several different *styles* (like \"italic\" and
\"roman\", which is what not-italic is called),[^5] and can be rendered
at an arbitrary *size*.[^6]

In Tk, you work with *font objects*, which correspond to what an
old-timey designer would call a font: a type at a fixed size, style, and
weight. For example:

``` {.python}
import tkinter.font
font_bi = tkinter.font.Font(
    family="Times",
    size=16,
    weight="bold",
    slant="italic",
)
```

Once you have a font, you can use it with `create_text` using the `font`
keyword argument:

``` {.python}
canvas.create_text(200, 100, text="Hi!", font=font_bi)
```

Measuring text
==============

Text takes up space vertically and horizontally. In Tk, there are two
functions that measure this space, `metrics` and `measure`:[^7]

``` {.python}
>>> font_bi.metrics()
{'ascent': 15, 'descent': 7, 'linespace': 22, 'fixed': 0}
>>> font_bi.measure("Hi!")
31
```

The `metrics()` call gives information about the vertical spacing of the
text: the `linespace` is how tall the text is, which includes an
`ascent` which goes "above the line" and a `descent` that goes "below
the line".[^8] You end up caring about the `ascent` and `descent` if you
have text of different sizes on the same line: you want them to line up
"on the line", not along their tops or bottoms.

Let\'s dig deeper. Remember that in this code, `font_bi` is a 16-pixel
Times. But `font.metrics` tells us that this "16 pixel" font is actually
22 pixels tall. This kind of misdirection is pretty common. The
advertised pixel size describes the font\'s ascent, not its full size.
Which for this font is 15 pixels; 16 pixels is how big the font "feels".
It\'s like dress sizes.

On the other hand, the `measure()` call tells you about the horizontal
space the text takes up. This obviously depends on *what* text you\'re
rendering, since different letters have different width:[^9]

``` {.python}
>>> font_bi.measure("Hi!")
31
>>> font_bi.measure("H")
17
>>> font_bi.measure("i")
6
>>> font_bi.measure("!")
8
>>> 17 + 8 + 6
31
```

You can use this information to lay text out on the page. For example,
suppose you want to draw the text "Hello, world!" in two pieces, so that
"world!" is italic. Let\'s use two fonts:

``` {.python}
font1 = tkinter.font.Font(family="Times", size=16)
font2 = tkinter.font.Font(family="Times", size=16, slant='italic')
```

We can now lay out the text, starting at `(200, 200)`:

``` {.python}
x = 200
y = 200
canvas.create_text(x, y, text="Hello, ", font=font1)
x += font1.measure("Hello, ")
canvas.create_text(x, y, text="world!", font=font2)
```

This should work, giving you nicely aligned "Hello," and "world!", with
the second italicized.

This actually only works by chance: there is a hidden bug in this code
that happens not to occur for "Hello, world!". For example, replace
"world!" with "overlapping!": that the two words will overlap. That\'s
because the coordinates `x` and `y` that you pass to `create_text` tell
Tk where to put the *center* of the text. So, instead of incrementing
`x` by the length of "Hello,", you need to increment it by half the
length of "Hello," and half the length of "overlapping!". It only worked
for "Hello, world!" because \"Hello,\" and \"world!\" are the same
length!

Luckily, the meaning of the coordinate you pass in is configurable. We
can instruct Tk to treat the coordinate we gave as the top-left corner
of the text by setting the `anchor` argument to `nw`, meaning the
\"northwest\" corner of the text:

``` {.python}
x = 200
y = 225
canvas.create_text(x, y, text="Hello, ", font=font1, anchor='nw')
x += font1.measure("Hello, ")
canvas.create_text(x, y, text="overlapping!", font=font2, anchor='nw')
```

Make this change in your `render` function; we didn\'t need it in the
previous chapter because all Chinese characters are the same width.

Word by word
============

In the last chapter, the `layout` function looped over the text
character-by-character and moved to the next line whenever we ran out of
space. That\'s appropriate in Chinese, where each character more or less
*is* a word. But it doesn\'t work for English, where you can\'t move to
the next line in the middle of a word. Instead, we need to loop word by
word, where words are whitespace-separated:[^10]

``` {.python}
for word in text.split():
    w = font.measure(word)
    if x + w >= 787:
        y += font.metrics("linespace") *1.2
        x = 13
    display_list.append((x, y, word))
    x += w + font.measure(" ")
```

There\'s a lot of moving parts to this code. First, we measure the width
of the text, and store it in `w`. We\'d normally draw the text at `x`,
so its right end would be at `x + w`, so we check if that\'s past the
edge of the page. Now we have the location to *start* drawing the word,
so we add to the display list; and finally we update `x` to point to the
end of the word.

There are a few surprises in this code. One is that I call `metrics`
with an argument; that just returns that metric directly. Also, instead
of incrementing `x` by `w`, we increment it by `w + font.measure(" ")`.
That\'s because we want to have spaces between our words. When we called
`split()` we removed all of the whitespace, and this adds it back. We
don\'t add the space to `w` on the second line, though, because we
don\'t need a space after the last word on a line. Finally, note that I
multiply the linespace by 1.2 when incrementing `y`. Try removing the
multiplier: you\'ll see that the text is harder to read because the
lines are too close together.[^11] Instead, it is common to add "line
spacing" or "leading"[^12] between lines. Here, It\'s 20% line spacing,
which is a normal amount.

Separate lexing
===============

Right now, all of the text on the page is drawn with one font. But web
pages sometimes **bold** or *italicise* text using the `<b>` and `<i>`
tags. It\'d be nice to implement that, but right now, the code resists
the change: the `lex` function only receives the text of the page as
input, and so has no idea where the bold and italics tags are.

Let\'s change `lex` to return a list of *tokens*, where a token is
either a `Text` object (for a run of characters outside a tag) or a
`Tag` object (for the contents of a tag). You\'ll need to write the
`Text` and `Tag` classes:[^13]

``` {.python}
class Text:
    def __init__(self, text):
        self.text = text

class Tag:
    def __init__(self, tag):
        self.tag = tag
```

Now, `lex` will store a list of `Text` and `Tag` objects instead of a
string:[^14]

``` {.python}
def lex(source):
    out = []
    text = ""
    in_angle = False
    for c in source:
        if c == "<":
            in_angle = True
            if text: out.append(Text(text))
            text = ""
        elif c == ">":
            in_angle = False
            out.append(Tag(text))
            text = ""
        else:
            text += c
    if not in_angle and text:
        out.append(Text(text))
    return out
```

There are a few changes here. First, instead of accumulating characters
into `text`, we accumulate into `text` only until we transition between
text and tags; and the chunks in `text` are then accumulated into `out`.
`Text` and `Tag` are asymmetric: we avoid empty `Text` objects, but not
empty `Tag` objects. That\'s because an empty `Tag` object represents
the HTML code `<>`, while an empty `Text` object with empty text
represents no content at all. Finally, note that at the end of the loop,
we need to create a text token with any text we\'ve accumulated.
Otherwise, if you never saw an angle bracket, you\'d return an empty
list of tokens. If you end with an unfinished tag, like if you\'re
lexing `"Hi!<hr"`, that unfinished tag is thrown out.[^15]

Our `layout` function must now loop over tokens, not text:

``` {.python}
def layout(tokens):
    for tok in tokens:
        if isinstance(tok, Text):
            for word in tok.text.split():
                # ...
```

Styling text
============

Now that we have access to the tags in the `layout` function, we can use
them to change fonts when directed by the user. Let\'s have four
different styles, corresponding to bold/normal and italic/roman choices,
and add two variables to track which style to use:

``` {.python}
bold, italic = False, False
```

We\'ll need to change those variables as we go through the tokens,
responding to bold and italics open and close tags:

``` {.python}
for tok in tokens:
    if isinstance(tok, Text):
        # ...
    elif isinstance(tok, Tag):
        if tok.tag == "i":
            italic = True
        elif tok.tag == "/i":
            italic = False
        elif tok.tag == "b":
            bold = True
        elif tok.tag == "/b":
            bold = False
```

Note that this code correctly handles not only `<b>bold</b>` and
`<i>italic</i>` text, but also `<b><i>bold italic</i></b>` text. It even
handles what you might call mis-nested tags like
`<b>bold <i>both</b> italic</i>`. It doesn\'t handle
`<b>accidentally <b>double</b> bolded</b>` text, which we\'ll leave for
[later](html.md).

Finally, use `bold` and `italic` to choose the font for rendering text.
Since `bold` and `italic` are computed in `layout` but the canvas
methods themselves are called `render`, we\'ll need to add the font used
to each entry in the display list.

``` {.python}
if instance(tok, Text):
    font = tkinter.font.Font(
        family="Times",
        size=16,
        weight=("bold" if bold else "normal"),
        slant=("italic" if italic else "roman"),
    )
    for word in tok.text.split():
        # ...
        display_list.append((x, y, word, font))
```

Make sure to update `render` to expect and use that font entry.

Word boundaries
===============

This section handles spaces between words. That seems like a nitpick,
but it gets to the whitespace-insensitivity of HTML.

Right now, the code assumes that there\'s a space after *every* word, so
for HTML code like \"`I'm so <i>excited</i>!`\", it\'ll put a space
after `excited`, making the exclamation mark look weird. Sometimes, like
after \"`so`\", we need a space after the last word in a text token, but
other times, like after \"`excited`\", we don\'t. And for HTML code like
\"`I'm so<i> excited</i>!`\", spaces before the first word are
important. We need to check whether text token starts or ends with a
space:[^16]

``` {.python}
if tok.text[0].isspace():
    x += font.measure(" ")

for word in tok.text.split():
    # ...

if not tok.text[-1].isspace():
    x -= font.measure(" ")
```

The code first checks for the initial space, and increments `x` if it
finds one; then it loops through each word as normal, adding a space
after each; and finally, it checks whether we were supposed to add that
final space and, if not, subtracts it back off of `x`.[^17]

This code handles the two cases above, but not odd input like
\"`I'm <i> so </i> excited!`\": it draws two spaces in a row, while HTML
dictates that two pieces of whitespace one after another should
merge.[^18] We need extra state to track when we had a space at the end
of the previous token, and only insert an initial space if we didn\'t:

``` {.python}
if tok.text[0].isspace() and not terminal_space:
    x += font.measure(" ")

for word in tok.text.split():
    # ...

terminal_space = tok.text[-1].isspace()
if not terminal_space:
    x -= font.measure(" ")
```

The state variable `terminal_space` is set at the end of every text
token, and read at the beginning of the next text token. So, you need to
define `terminal_space` somewhere; put it right next to `bold` and
`italic`. It should start off start `True`, because if the first thing
in a line is a space, you don\'t print that space.

I bet you\'ve never thought this much about the spaces between words.

Separating paragraphs
=====================

The browser now lays out English text properly, with characters nicely
arranged into words that aren\'t split across lines. But it\'s a bit
hard to read that text without paragraph breaks.

In HTML, text is grouped into paragraphs by wrapping each paragraph with
the `<p>` tag. Just like our browser looks for the `<b>` and `<i>` tags
to change which font it uses, it needs to look for `<p>` tags to
implement paragraphs.

``` {.python}
elif tok.tag == "/p":
    terminal_space = True
    x = 13
    y += font.metrics('linespace') * 1.2 + 16
```

The end of a paragraph is the end of a line, so we reset `x` and
increment `y`. I increment `y` by 16 pixels more than normal, to add a
little gap between paragraphs. I also reset `terminal_space`; remember
that spaces at the start of a line aren\'t printed.

Compared to how complicated text is, paragraphs are easy!

Summary
=======

The last chapter introduced a browser that laid out Chinese text. Now it
does English, too:

-   Text is laid out word-by-word
-   Lines are split at word boundaries
-   Text can be bold or italic
-   Spacing rules are obeyed
-   Paragraphs are separated from one another

The browser is now good enough to read an essay or a blog!

Exercises
=========

-   Right now, if you have a heading (`<h1>` or `<h2>`) followed by a
    paragraph, the heading just becomes part of the first line of the
    paragraph. Put headings on their own line, and make headings bold.
-   Make heading text larger, perhaps size-24 for `h1` and size-20 for
    `h2`. Check that multi-line headings don\'t cause overlapping text.
-   Add support for the `<small>` tag: text in this tag should be
    smaller, maybe size-12. Make sure that when small text is mixed with
    normal-sized text, all of the text is aligned. For example, in
    \"`A <small>little</small> bit`\", the bottoms of each word should
    match up. If the text has descenders, like in
    \"`An <small>example</small> for you`\", it should look like all the
    letters sit on a line, with the descenders in \"`p`\" and \"`y`\"
    hanging below that line.
-   Add support for the `<pre>` tag. Unlike normal paragraphs, text
    inside `<pre>` tags doesn\'t automatically break lines, while
    whitespace like spaces and newlines are preserved. Use a fixed-width
    font like `Courier New` or `SFMono` as well. Make sure tags work
    normally inside `<pre>` tags: it should be possible to bold part
    `<pre>` text. You shouldn\'t need to modify `lex`.
-   **Hard**: Add support for the `<big>` tag. Text surrounded by this
    tag should be bigger, maybe size-20. Make sure that when text sizes
    are mixed, like in \"`A <big>huge</big> deal`\", all of the text is
    aligned. This is much harder than implementing `<small>`: `<big>`
    text should not overlap with the previous line, even if half of the
    line is normal sized and half is `<big>`.

[^1]: There are lots of languages in the world, and lots of
    typographic conventions. A real web browser supports every
    language from Arabic to Zulu, but this book focuses on English.
    Text is near-infinitely complex, but this book cannot be
    infinitely long!

[^2]: The word is related to *foundry*, which would create the little
    metal shapes.

[^3]: The term "font family" was invented to specifically refer to
    types, and now has also become confusing and blurry.

[^4]: But sometimes other weights as well, like "light", "semibold",
    "black", and "condensed". Good fonts tend to come in many weights.

[^5]: Sometimes there are other options as well, like maybe there\'s a
    small-caps version; these are sometimes called *options* as well.
    And don\'t get me started on automatic versus manual italics.

[^6]: But usually the font looks especially good at certain sizes where
    *hints* tell the computer how to best resize the font to a
    particular pixel size.

[^7]: On your computer, you might get different numbers. That\'s
    right---text rendering is OS-dependent, because it is complex enough
    that everyone uses one of a few libraries to do it, usually
    libraries that ship with the OS. That\'s why macOS fonts tend to be
    \"blurrier\" than the same font on Windows.

[^8]: The `fixed` parameter is actually a boolean and tells you whether
    all letters are the same *width*, so it doesn\'t really fit here.

[^9]: The sum at the end of this snippet may not work on your machine:
    the width of a word is not always the sum of the widths of its
    letters. That\'s because Tk always returns whole pixels, but
    internally might do some rounding. Plus some fonts use something
    called *kerning* to shift letters a little bit when particular pairs
    of letters are next to one another, though I don\'t know if Tk
    supports this.

[^10]: Note that this code will now break on Chinese, since Chinese
    won\'t have whitespace between words/characters. Real browsers use
    language-dependent rules for laying out text.

[^11]: Designers say the text is too "tight".

[^12]: So named because in metal type days, little pieces of metal that
    were placed between lines to space them out, and those metal pieces
    were made of lead. Lead is a softer metal than what the actual
    letter pieces were made of, so it could compress a little to keep
    pressure on the other pieces. Pronounce it "led-ing" not "leed-ing".

[^13]: If you\'re familiar with Python, you might want to use the
    `dataclass` library, which makes it easier to define these sorts of
    utility classes.

[^14]: If you\'ve done exercises in prior chapters, your code will look
    different. The code in these chapters always assumes you haven\'t
    done the exercises, so you\'re on your own to port any
    modifications.

[^15]: This may strike you as an odd decision: perhaps you should raise
    an error, or finish up the tag for the author. There\'s no right
    answer, but dropping the tag is what browsers do.

[^16]: Note that tokens never contain an empty string of text, so the
    `[0]` and `[-1]` accesses are valid.

[^17]: We could never have broken a line *after* the final word, so
    subtracting off of `x` is correct. And because `font.measure` always
    returns an integer, so there\'s no possibility of rounding error.

[^18]: Try it in a web browser!
