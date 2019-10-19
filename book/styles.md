---
title: Applying User Styles
chapter: 6
prev: layout
next: chrome
...

Our implementation of block layout required a lengthy list of
tag-specific styles to specify margins, borders, and padding (as well
as colors and sizes, if you did that exercise). This way, the
appearance of the various page elements is fixed: the web page cannot
override our style decisions. Let\'s fix that by implementing CSS.

The `style` attribute
=====================

Different elements have different styles: margins for paragraphs and
list items, padding for the body and for lists, and borders for code
blocks. But web pages are stuck with whatever styles our browser
chooses to assign them. That seems a little unfair though, not least
because I have no artistic sense and so my styles look ugly. Webpages
should be able to override my choices.

So let\'s start with the easiest way web pages can override browser
styles, which is the `style` attribute on elements. The style attribute
looks like this:

``` {.example}
<div style="border-left-width:1px;border-left-color:red;"></div>
```

Here the `<div>` element has the `style` attribute set, and that
attribute contains two key-value pairs: a `border-left-width` of 1 pixel
and a `border-left-color` of `red`.[^1] We want to gather these
key-value pairs from the `style` attribute, store them in a `style`
field on each `ElementNode`, and use them in our layout decisions.

You should already have some attribute parsing code in your
`ElementNode` class, which puts all the attributes into a dictionary. We
just need to take out the `style` attribute,[^2] split it on semicolon
and then colon, and stuff the results back into a dictionary:

``` {.python}
def __init__(self, parent, tagname):
    # ...
    self.style = self.compute_style()

def compute_style(self):
    style = {}
    style_value = self.attributes.get("style", "")
    for line in style_value.split(";"):
        prop, val = line.split(":")
        style[prop.lower().strip()] = val.strip()
    return style
```

That puts the style information into a handy place, but we also need to
pull it out and use it. To do that, we\'ll modify `BlockLayout` to pull
the style values out and use them for the margins, border, and padding:

``` {.python}
def __init__(self, parent, node):
    # ...
    self.mt = px(self.style.get("margin-top", "0px"))
    # ... repeat for the right, bottom, and left edges
    # ... and for padding and border as well
```

I\'m not writing out all 12 lines but they\'re basically the same (but
the border one is called `border-top-width`, not `border-top`!). Here
I\'m calling the `px` function. This is a very simple helper function
that strips off the `px` at the end of a pixel amount, and turns it into
a number.

Now border, padding, and margin sizes come from element `style`
attributes instead of just from hard-coded values. But we do want to put
the defaults back in, for pages that don\'t use `style`, so let\'s move
those defaults into `compute_style`:

``` {.python}
def compute_style(self):
    style = {}
    if self.tag == "p":
        style["margin-bottom"] = "16px"
    # ... other cases for ul, li, and pre
    # ...
```

We need to put these assignments in at the top of `compute_style`,
because we need them to be overridden, later, by the values from the
`style` attribute.

Parsing CSS
===========

We\'ve now got user-set styles, but those styles have to be specified on
an element-by-element basis. This makes it pretty tedious to change the
style of, say, every paragraph on the page, let alone to make multiple
web pages that share the same style---what if you forget the correct
`style` attribute? In the early days of the web,[^3] this
element-by-element approach was all there was.[^4] But then CSS was
invented, and it had a few goals:

-   CSS files must be reusable across multiple web pages, so that those
    pages can look similar
-   CSS files must be able to adjust styling of many elements at once
-   The design must be future-proof and handle browsers with different
    features

To achieve that, CSS took the simple key-value idea that we\'ve already
implemented and extended it with two interlinked ideas of *selectors*
and *cascading*. In CSS, you have blocks of key-value pairs, and those
blocks apply to *multiple elements*, specified using a selector. That
means multiple key-values pairs might apply to one element, so there may
be conflict, and *cascading* is the rule by which these conflicts are
resolved.

So overall, CSS is a sequence of rules that look like this:

``` {.css}
selector {
    property: value;
    property: value;
    property: value;
}
```

Let\'s start by parsing this syntax. I\'ll use a traditional
recursive-descent parser. A recursive-descent parser works like this: it
is a bunch of *parsing functions*, each of which takes two inputs (the
overall text and an index into it) and produces two outputs (some
element of the text it has parsed and a new index location). So here,
for example, is a parsing function for values:

``` {.python}
def css_value(s, i):
    j = i
    while s[j].isalnum() or s[j] == "-":
        j += 1
    return s[i:j], j
```

Then, here\'s how we parse property-value pairs:

``` {.python}
def css_pair(s, i):
    prop, i = css_value(s, i)
    _, i = css_whitespace(s, i)
    assert s[i] == ":"
    val, i = css_value(s, i + 1)
    return (prop, val), i
```

This calls `css_whitespace`, which increases `i` as long as `s[i]` is
whitespace, and also stops at the end of the document. I think you can
write that yourself. Now we can parse rule bodies:

``` {.python}
def css_body(s, i):
    pairs = {}
    assert s[i] == "{"
    _, i = css_whitespace(s, i+1)
    while True:
        if s[i] == "}": break

        try:
            (prop, val), i = css_pair(s, i)
            pairs[prop] = val
            _, i = css_whitespace(s, i)
            assert s[i] == ";"
            _, i = css_whitespace(s, i+1)
        except AssertionError:
            while s[i] not in [";", "}"]:
                i += 1
            if self.s[i] == ";":
                _, i = self.whitespace(i + 1)
    assert s[i] == "}"
    return pairs, i+1
```

Note that our `css_value` used an `assert` to handle error cases, like
values of `4` (no unit), `px` (no value), or `foobar` (neither). This
will trigger a lot in real web pages, since our browser won\'t support
all the different CSS features, so `css_body` catches those errors and
ignores those property-value pairs.

Finally, to parse a full CSS rule, we need to parse selectors. Selectors
come in multiple types. For example, there are tag selectors: `p`
selects all `<p>` elements, `ul` selects all `<ul>` elements, and so on.
Then, there are class selectors: HTML elements have a `class` attribute,
which is a space-separated list of arbitrary names, so the `.foo`
selector selects the elements that have `foo` in that list. And finally,
there are ID selectors: `#main` selects the element with an `id` value
of `main`. For now, let\'s handle just these three selector types in our
browser.

We\'ll start by defining some data structures for selectors:[^5]

``` {.python}
class TagSelector:
    def __init__(self, tag):
        self.tag = tag

class ClassSelector:
    def __init__(self, cls):
        self.cls = cls

class IdSelector:
    def __init__(self, id):
        self.id = id
```

We now want parsing functions for each of these data structures.
That\'ll look like this:

``` {.python}
def css_selector(s, i):
    if s[i] == "#":
        name, i = css_value(s, i+1)
        return IdSelector(name), i
    elif s[i] == ".":
        name, i = css_value(s, i+1)
        return ClassSelector(name), i
    else:
        name, i = css_value(s, i)
        return TagSelector(name), i
```

Here I\'m calling `css_property` for tag, class, and identifier names.
This is a hack, since in fact tag names, classes, and identifiers have
different allowed characters. Also tags are case-insensitive, as are
property values, while classes and identifiers are case-sensitive. I\'m
ignoring that but a real browser could not. Note the arithmetic with
`i`: we pass `i+1` to `css_name` in the class and ID cases (to skip the
hash or dot) but not in the tag case (since that first character is part
of the tag).

I\'ll leave it to you to stitch the selector and body parsing functions
together to parse a full CSS rule, and then run that function in a loop
to run multiple rules. Make sure to use a similar `try`-`except` pair to
handle the case of selectors that our engine cannot parse, since in fact
there are far more than these three selector types. The end result
should be a list of rule pairs, where the first element of the pair is a
selector object and the second element is the property/value dictionary.

Now that we\'ve parsed a CSS file, we need to apply it to the elements
on the page.

Selecting styled elements
=========================

Our goal is a function, let\'s call it `style`, which will take in the
tree of `ElementNode` objects and a list of rule pairs, and which will
update the elements\' `style` variables using those rules. The logic is
pretty simple:

-   Recursively operate on every `ElementNode` in the tree
-   For each rule, check if the rule matches
-   If it does, go through the property/value pairs and assign them

Here\'s what the code would look like:

``` {.python}
def style(node, rules):
    if not isinstance(node, ElementNode): return
    node.style = {}
    for selector, pairs in rules:
        if selector.matches(node):
            for property in pairs:
                node.style[property] = pairs[property]
    for child in node.children:
        style(child, rules)
```

Note that we\'re skipping `TextNode` objects; that\'s because only
elements can be selected in CSS.[^6] This calls out to a
currently-nonexistant `matches` function on the selector objects, but
it\'s pretty easy to define. For example, here\'s how it looks like for
`ClassSelector`, the hardest one:

``` {.python}
def matches(self, node):
    return self.cls == node.attributes.get("class", "").split()
```

You can imagine what it does for `IdSelector` and `ClassSelector`.

Cascade order
=============

This implementation of `style` just applies the rules in order, one
after another. And furthermore, it overwrites the existing styles, such
as the styles that come from attribute values. We need to fix that.

In CSS, this is solved by what is called the *cascade order*. The
cascade order gives a score to each selector, and rules with
higher-scoring selectors can overwrite rules with lower-scoring
selectors. Tag selectors get the lowest score; class selectors one
higher; and id selectors higher still. The `style` attribute has the
highest-possible score, so it overwrites everything. So let\'s add the
`score` method to the selector classes that return this score. Maybe tag
selectors have score 1, class selectors 16, id selectors 256.[^7] I
won\'t show code for that, since it\'s straightforward.

We\'ll use the score to the rules before passing them to `style`:

``` {.python}
rules.sort(key=lambda x: x[0].score())
```

Here `x[0]` refers to the selector half of a rule, and I\'m calling the
new `score` method. In Python, the `sort` function is *stable*, which
means that things keep their relative order if possible. This means that
in general, a later rule will override an earlier one, which is what CSS
does as well.

This works for rules with selectors; we also need to do this for inline
styles. We can just tack that on after the rules loop in `style`:[^8]

``` {.python}
def style(node, rules):
    # for selector, pair in rules ...
    for property, value in node.compute_style().items():
        node.style[property] = value
    # for child in node.children ...
```

We\'ve now implemented a toy CSS engine. The next step is go set it
loose on some CSS!

Downloading styles
==================

Browsers get CSS code from two sources. First, each browser ships with a
*browser style sheet*, which defines the default styles for all sorts of
elements. For our browser, this browser style sheet might look like
this:

``` {.css}
p { margin-bottom: 16px; }
ul { margin-top: 16px; margin-bottom: 16px; padding-left: 20px; }
/* ... */
```

Let\'s pull the default-element code out of `compute_style` and put it
in a file, let\'s say `default.css`. Then we can run our CSS parser on
it and apply it to the various elements:

``` {.python}
with open("default.css") as f:
    browser_style = f.read()
    browser_rules, _ = css_rules(browser_style, 0)
rules = browser_rules
rules.sort(key=lambda x: x[0].score())
style(nodes, rules)
```

This moves some code out of our browser into a plain CSS file, which is
nice. But our whole goal here is to go beyond just the browser styles;
to do that, we need to find website-specific CSS files, download them,
and use them as well. Browsers do this by searching for a particular
HTML element, called `link`. Link elements look like this:

``` {.example}
<link rel="stylesheet" href="/main.css">
```

The `rel` attribute here tells that browser that this is a link to a
stylesheet; web pages can also link to a home-page, or a
language-specific version, or so on. Browsers actually don\'t use those
links for anything useful, but search engines do, which is why the `rel`
attribute exists.

Then, the `href` attribute gives a location for the stylesheet in
question. The browser is expected to make a GET request to that
location, parse the stylesheet, and use it. Note that the location is
not a full URL; it is something called a *relative URL*, which can come
in three flavors:[^9]

-   A normal URL, which specifies a scheme, host, path, and so on
-   A host-relative URL, which starts with a slash but reuses the
    existing scheme and host
-   A path-relative URL, which doesn\'t start with a slash and is
    instead tacked onto the current URL (up but not past its last slash)

So to download CSS files, we\'re going to need to do three things:

-   Find the relevant `<link>` elements
-   Turn their relative URLs into real URLs
-   Download the CSS and parse it

For the first one, we\'ll need a recursive function that adds to a list:

``` {.python}
def find_links(node, lst):
    if not isinstance(node, ElementNode): return
    if node.tag == "link" and \
       node.attributes.get("rel", "") == "stylesheet" and \
       "href" in node.attributes:
        lst.append(node.attributes["href"])
    for child in node.children:
        find_links(child, lst)
    return lst
```

Then, to turn a relative URL into a full URL:

``` {.python}
def relative_url(url, current):
    if url.startswith("http://"):
        return url
    elif url.startswith("/"):
        return current.split("/")[0] + url
    else:
        return current.rsplit("/", 1)[0] + "/" + url
```

Now we just need to go through the links and download them:

``` {.python}
for link in find_links(nodes, []):
    lhost, lport, lpath = parse_url(relative_url(link, url))
    header, body = request(lhost, lport, lpath)
    lrules, _ = css_rules(body, 0)
    rules.extend(rules)
```

Put that block *after* you read the browser style, because later styles
override earlier ones and we want user styles to take priority.[^10]

Now our CSS engine should handle some real-world web pages, like this
one, properly, including changing some margins and paddings. If
you\'ve implemented the exercises on background and border colors, you
should also see a light-gray background for the page.

Styles for inline layout
========================

Right now, our CSS styles only affect the block layout mode. We\'d like
to extend CSS to affect inline layout mode as well, but there\'s a
catch: inline layout is mostly concerned with text, but text nodes
don\'t have any styles at all. How can that work?

The solution in CSS is *inheritance*. Inheritance means that if some
node doesn\'t have a value for a certain property, it uses its parent\'s
value instead. Some properties are inherited and some aren\'t; it
depends on the property. Let\'s implement two inherited properties:
`font-weight` (which can be `normal` or `bold`) and `font-style` (which
can be `normal` or `italic`[^11]). To inherit a property, we simple need
to check, after all the rules and inline styles have been applied,
whether the property is set and, if it isn\'t, to use the parent node\'s
style:

``` {.python}
INHERITED_PROPERTIES = [ "font-style", "font-weight" ]
def style(node, rules):
    # ...
    for prop in INHERITED_PROPERTIES:
        if prop not in node.style:
            if node.parent is None:
                node.style[prop] = "normal"
            else:
                node.style[prop] = node.parent.style[prop]
    # ...
```

There are a few \"accidents\" that make this work. First, getting the
parent\'s value of a property will only make sense if the parent has
already inherited the correct property value; that means that this
little loop has to come *before* the recursive calling of `style` on the
child nodes. And second, it just so happens that `"normal"` is the
default value for both `font-weight` and `font-style`; that\'s not
actually a rule, so in a real implementation you\'d need an extra
function that maps properties to their default values.

On `TextNode` objects we can do this even easier, since it always
inherits its styles for its parent:

``` {.python}
class TextNode:
    def __init__(self, parent, text):
        # ...
        self.style = self.parent.text
```

Now that we have `font-weight` and `font-style` set on every node, we
can use them in `InlineLayout` to set the font:

``` {.python}
self.bold = node.style["font-weight"] == "bold"
self.italic = node.style["font-style"] == "italic"
```

Because `font-weight` and `font-style` are always set, I\'m not using
`get` or anything similar here to handle default values.

Now that we have styles on both block and inline nodes, we can do a
final simplification of our code using CSS. There\'s an `is_inline`
function in our code, which specifically tests for the `<b>` and `<i>`
tags. Instead of hard-coding in these tags, we should instead use the
standard `display` property. This property can be either `block` or
`inline`, and it basically tells you which of the two layout modes to
use.[^12] So instead of...

``` {.python}
... or isinstance(node, ElementNode) and node.tag in ["i", "b"]
```

... do ...

``` {.python}
... or node.style.get("display", "block") == "inline"
```

To match the functionality of the original code, we\'ll need to add some
code like this to `default.css`:

``` {.css}
i { display: inline; font-style: italic; }
b { display: inline; font-weight: bold; }
```

Summary
=======

This chapter was quite a lot of work! We implemented a rudimentary but
complete layout engine, including a parser, selector matching,
cascading, and even downloading and applying CSS files. Not only that,
but the CSS engine should be relatively easy to extend, with new
properties and selectors; our engine ignores selectors and properties it
does not understand, so selectors and properties will immediately start
working as they are implemented.

Exercises
=========

-   Right now, your browser is (probably) still displaying the page
    title as the first line of text on the page. Of course in a real
    browser, the `<title>` element is hidden, as is everything inside
    the `<head>` element (try adding a `<p>` to the head on a page!).
    The way this works is that `display` can have the value `none`, in
    which case the element is not displayed and neither are any of its
    children. Implement `display: none` and use that in your browser
    style sheet to hide the `<head>` element.
-   CSS allows a rule to have multiple selectors, which is basically the
    same as separate rules sharing a body. To do that, you list multiple
    selectors with a comma in between. Implement this feature, and use
    it to shorten and simplify the browser style sheet. (For example,
    both `<b>` and `<i>` have `display: inline`.)
-   CSS has some \"shortcut properties\". For example, you can write
    `margin: 1px` to set all four margins to the same width; the same
    applies to `padding` and `border-width`. You can also give multiple
    values to `margin`, which distributes those values to the various
    sides: if there is one value, it is for all four sides; if there are
    two values, the first is for top and bottom and the second for left
    and right; if there are four, they are the top, right, bottom, and
    left values, in that unusual order; and finally if there are three
    values the middle one is both left and right. Implement shortcut
    properties. The best place to do this is in the parsing function
    `css_body`, since that way it\'ll automatically happen whereever the
    rule is applied.
-   Sometimes it is helpful to select an element that matches *both* a
    tag and a class. In CSS, you do this by just concatenating the
    selectors together; for example `span.announce` selects elements
    that match both `span` and `.announce`. Implement those, both in the
    parser and with a new `AndSelector` class that combines multiple
    selectors into one. You\'re supposed to use lexicographic scoring
    for these `AndSelector` things, but the easy thing to do is to sum
    the scores of the selectors being combined in `AndSelector.score`.
    This will work fine as long as no strings more than 16 selectors
    together, if you used the scores suggested above.
-   Tags, class, and identifiers are not the only selectors! Another
    commonly-used selector is the *descendent* selector; the syntax is
    multiple space-separated selectors, like `ul strong`, which selects
    all `<strong>` elements[^13] with a `<ul>` ancestor. Implement
    descendent selectors, both in parsing and with a new
    `DescendentSelector` class. Scoring for descendent selectors works
    just like in `AndSelector`. Make sure that something like
    `section .warning` selects warnings inside sections, while
    `section.warning` selects warnings that *are* sections.

[^1]: In CSS you can put spaces around the semicolons or the colons,
    but you might not have implemented the exercise to support spaces
    in attribute. Also maybe you don\'t have border colors
    implemented.

[^2]: The `get` method for dictionaries gets a value out of a
    dictionary, or uses a default value if it's not present.

[^3]: I\'m talking Netscape 3. The late 90s.

[^4]: Though it wasn\'t the `style` attribute at the time, it was a mix
    of all these elements like `font` and `center` and so on.

[^5]: I\'m calling it `ClassSelector.cls` instead of
    `ClassSelector.class` because `class` is a reserved word in Python.

[^6]: Well, there are pseudo-elements, but we\'re not going to implement
    them...

[^7]: In this simplest implementation the exact numbers don\'t matter if
    they sort right, but choosing these numbers is a little easier for
    the exercises

[^8]: The `items()` call is a Python way to get the key and value out of
    a dictionary as you iterate over it.

[^9]: There are more flavors, including query-relative and
    scheme-relative URLs.

[^10]: In reality, browser styles get lower priority even if they have a
    higher score, but our browser styles are so simple---they\'re all
    tag styles---that that will happen anyway.

[^11]: Actually, it can also be `oblique`. No one knows that that is,
    though some browsers will use that value to display pseudo-italics,
    that is, roman text that\'s been algorithmically slanted.

[^12]: Modern CSS adds some funny new values, like `run-in` or
    `inline-block`, and it has layout modes set by other properties,
    like `float` and `position`.

[^13]: This is like a `<b>` tag but newer and with slightly different
    semantics. `<strong>` was an XHTML attempt to drop all visual
    aspects from element names.
