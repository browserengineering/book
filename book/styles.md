---
title: Applying User Styles
chapter: 6
prev: layout
next: chrome
...

So far, the appearance of the various elements has been fixed. But web
pages should be able to override our style decisions and take on a
unique character. This is done via CSS.

The `style` attribute
=====================

Different elements have different styles, like margins for paragraphs
and borders for code blocks. Those styles are assigned by our browser,
and it *is* good to have some defaults. But webpages should be able to
override those choices.

The simplest mechanism for that is the `style` attribute on elements.
It looks like this:

``` {.example}
<div style="margin-left:10px;margin-right;10px;"></div>
```

It's a `<div>` element with its `style` attribute set. That attribute
contains two key-value pairs, which set `margin-left` and
`margin-right` to 10 pixels each.^[CSS allows spaces around the
punctuation, but your attribtue parser may support it.] We want store
these pairs in a `style` field on the `ElementNode` so we could
consult them during layout.

You should already have some attribute parsing code in your
`ElementNode` class to create the `attributes` field. We just need to
take out the `style` attribute, split it on semicolons and then on the
colon, and save the results:^[The `get` method for dictionaries gets a
value out of a dictionary, or uses a default value if it's not
present.]

``` {.python}
class ElementNode:
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

To use this information, we'll need to modify `BlockLayout`:

``` {.python}
def __init__(self, parent, node):
    # ...
    self.mt = px(self.style.get("margin-top", "0px"))
    # ... repeat for the right, bottom, and left edges
    # ... and for padding and border as well
```

where the `px` function is this little helper:

``` {.python}
def px(str):
    assert str.endswith("px")
    return int(str[:-2])
```

Remember the write out the code to access the other 11 properties; the
border one is called `border-top-width`, not `border-top`, but other
than that, they're very repetitive.

You'll notice that I set the default for each of the property values
to `0px`. For now, let's stick the per-element defaults at the top of
`compute_style`:

``` {.python}
def compute_style(self):
    style = {}
    if self.tag == "p":
        style["margin-bottom"] = "16px"
    # ... other cases for ul, li, and pre
    # ...
```

Make sure the defaults come first in `compute_style` so they can be
overridden by values from the `style` attribute.

Parsing CSS
===========

The `style` attribtue is set element by element. It's good for one-off
changes, but is a tedious way to change the style of, say, every
paragraph on the page. Plus, if multiple web pages are supposed to
share the same style, you're liable to forget the `style` attribute.
In the early days of the web,^[I\'m talking Netscape 3. The late 90s.]
this element-by-element approach was all there was.^[Though back then
it wasn't the `style` attribute, it was a custom elements like `font`
and `center`.] CSS was invented to improve on this state of affairs:

-   CSS files can to adjust styling of many elements at once
-   CSS files can style multiple pages from a single file
-   CSS is future-proof and supports browsers with different features

To achieve that, extended the key-value `style` attribute with two
connected ideas: *selectors* and *cascading*. In CSS, you have blocks
of key-value pairs, and those blocks apply to *multiple elements*,
specified using a selector. Since that allows multiple key-values
pairs to apply to one element, *cascading* resolves conflicts by using
the most specific rule.

Those blocks look like this:

``` {.css}
selector {
    property: value;
    property: value;
    property: value;
}
```

To support CSS in our browser, we'll need to parse this kind of code.
I\'ll use a traditional recursive-descent parser, which is is a bunch
of *parsing functions*, each of which advances along the input and
returns the parsed data as output.

Specifically, I'll implement a `CSSParser` class, which will store the
input string. Each parsing function will take an index into the input
and return a new index, plus it will return the parsed data.

Here's the class:

``` {.python}
class CSSParser:
    def __init__(self, s):
        self.s = s
```

So here, for example, is a parsing function for values:

``` {.python}
def value(self, i):
    j = i
    while self[j].isalnum() or self.s[j] in "#-":
        j += 1
    return s[i:j], j
```

Let's pick this apart. First of all, it takes index `i` pointing to
the start of the value and returns index `j` pointing to its end. It
also returns the string between them, which in this case is the parsed
data that we're interested in.

The point of recursive-descent parsing is that it's easy to build one
parsing function by calling others. So here's how to parse
property-value pairs:

``` {.python}
def pair(self, i):
    prop, i = self.value(i)
    _, i = self.whitespace(i)
    assert self.s[i] == ":"
    val, i = self.value(i + 1)
    return (prop, val), i
```

The `whitespace` function increases `i` until it sees a non-whitespace
character (or the end of the document); you can write it yourself.


Note the `assert`: that raises an error if you are trying to parse a
pair but there isn't one there. When we parse rule bodies, we can
catch this error to skip property-value pairs that don't parse:

``` {.python}
def body(self, i):
    pairs = {}
    assert self.s[i] == "{"
    _, i = self.whitespace(i+1)
    while True:
        if self.s[i] == "}": break

        try:
            (prop, val), i = self.pair(i)
            pairs[prop] = val
            _, i = self.whitespace(i)
            assert self.s[i] == ";"
            _, i = self.whitespace(i+1)
        except AssertionError:
            while self.s[i] not in [";", "}"]:
                i += 1
            if self.s[i] == ";":
                _, i = self.whitespace(i + 1)
    assert self.s[i] == "}"
    return pairs, i+1
```

I should stop and mention the importance of skipping code that causes
parse errors. This is a double-edged sword. It hides error messages,
making debugging CSS files more difficult, and also makes it harder to
debug your parser.^[Try debugging without the `try` block first.] This
makes "catch-all" error handling like this a code smell in most cases.

However, on the web there is an unusual benefit: it supports an
ecosystem of multiple implementations. For example, different browsers
may support different syntax for property values.^[Our browser does
not support parentheses in property values, which are valid in real
browsers, for example.] Crashing on a parse error would mean web pages
can't use a feature until all browsers support it, while skipping
parse errors means a feature is useful once a single browser supports
it. This is variously called "Postel's Law",^[After a line in the
specification of TCP, written by Jon Postel] the "Digital
Principle",^[After a similar idea in circuit design.] or the
"Robustness Principle": produce maximally supported output but accept
unsupported input.

Finally, to parse a full CSS rule, we need to parse selectors. Selectors
come in multiple types; for now, our browser will support three:

- Tag selectors: `p` selects all `<p>` elements, `ul` selects all
  `<ul>` elements, and so on.
- Class selectors: HTML elements have a `class` attribute, which is a
  space-separated list of arbitrary names, so the `.foo` selector
  selects the elements that have `foo` in that list.
- ID selectors: `#main` selects the element with an `id` value of
  `main`.

We\'ll start by defining some data structures for selectors:^[I\'m
calling the `ClassSelector` field `cls` instead of `class` because
`class` is a reserved word in Python.]

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
That'll look like:

``` {.python}
def selector(self, i):
    if self.s[i] == "#":
        name, i = self.value(i+1)
        return IdSelector(name), i
    elif self.s[i] == ".":
        name, i = self.value(i+1)
        return ClassSelector(name), i
    else:
        name, i = self.value(i)
        return TagSelector(name), i
```

Here I'm using `property` for tag, class, and identifier names. This
is a hack, since in fact tag names, classes, and identifiers have
different allowed characters. Also tags are case-insensitive (as by
the way are property names), while classes and identifiers are
case-sensitive. I'm ignoring that but a real browser would not. Note
the arithmetic with `i`: we pass `i+1` to `value` in the class and ID
cases (to skip the hash or dot) but not in the tag case (since that
first character is part of the tag).

I'll leave it to you to finish up the parser, writing the `whitespace`
helper, the `rule` function for parsing a selector followed by a body
(making sure to skip rules with unknown selectors), and the `parse`
function, which unlike the others should not take an index input (it
should start at 0) or produce an index output and should return a list
of parsed selector/body pairs.

Now that we've parsed a CSS file, we need to apply it to the elements
on the page.

Selecting styled elements
=========================

Browsers get CSS code from two sources. First, each browser ships with a
*browser style sheet*, which defines the default styles for all sorts of
elements; second, browsers download CSS code from the web, as directed
by web pages they browse to. Let's start with the browser style sheet.

Our browser's style sheet might look like this:

``` {.css}
p { margin-bottom: 16px; }
ul { margin-top: 16px; margin-bottom: 16px; padding-left: 20px; }
li { margin-bottom: 8px; }
pre {
    margin-top: 8px; margin-bottom: 8px;
    padding-top: 8px; padding-right: 8px;
    padding-bottom: 8px; padding-left: 8px;
    border-top-width: 1px; border-bottom-width: 1px;
    border-left-width: 1px; border-right-width: 1px;
}
```

That moves code from `compute_style` to a data file, let\'s call it
`browser.css`. Then we can run our CSS parser on it to extract the rules:

``` {.python}
with open("default.css") as f:
    browser_style = f.read()
    rules = CSSParser(browser_style).parse()
```

We now want to apply the rules to change the `style` field of the
`ElementNode` objects on the page; let's call the function that does
that `style(tree, rules)`. Its logic is pretty simple:

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
elements can be selected in CSS.^[Well, there are also
pseudo-elements, but we\'re not going to implement them...] We're also
calling a currently-nonexistant `matches` method on selectors. Here\'s
how it looks like for `ClassSelector`:

``` {.python}
def matches(self, node):
    return self.cls == node.attributes.get("class", "").split()
```

You can write `matches` for `TagSelector` and `IdSelector` on your
own. You can then call `style`:

``` {.python}
style(rules, nodes)
```

Once you're done, you should be able to delete the default
element styles from `compute_style` and still see elements property
styled.

Downloading styles
==================

This moves some code out of our browser into a plain CSS file, which
is nice. But the goal is to go beyond just the browser styles; to do
that, our browser needs to find website-specific CSS files, download
them, and use them as well. Web pages call out their CSS files using
the `link` element, which looks like this:

``` {.example}
<link rel="stylesheet" href="/main.css">
```

The `rel` attribute here tells that browser that this is a link to a
stylesheet; web pages can also link to a home-page, or a translation,
or similar. Browsers mostly don\'t do anything with those other kinds
of links, but search engines do, so `rel` is widely used.

The `href` attribute gives a location for the stylesheet in question.
The browser is expected to make a GET request to that location, parse
the stylesheet, and use it. Note that the location is not a full URL;
it is something called a *relative URL*, which can come in three
flavors:^[There are more flavors, including query-relative and
scheme-relative URLs, which I'm skipping.]

-   A normal URL, which specifies a scheme, host, path, and so on
-   A host-relative URL, which starts with a slash but reuses the
    existing scheme and host
-   A path-relative URL, which doesn\'t start with a slash and is
    instead tacked onto the current URL (up but not past its last slash)

So to download CSS files, we\'re going to need to do three things:

-   Find the relevant `<link>` elements
-   Turn the relative URLs into real URLs
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
        return "/".join(current.split("/")[:3]) + url
    else:
        return current.rsplit("/", 1)[0] + "/" + url
```

In the first case, the `[:3]` and the `"/".join` handle the two
slashes that come after `http:` in the URL, while in the last case,
the logic ensures that a link to `foo.html` on `http://a.com/bar.html`
goes to `http://a.com/foo.html`, not `http://a.com/bar.html/foo.html`.

We want to collect CSS rules from each of the linked files, and the
browser style sheet, into one big list so we can apply each of them.
So let's add them onto the end of the `rules` list:

``` {.python}
for link in find_links(nodes, []):
    header, body = request(relative_url(link, url))
    rules.extend(CSSParser(body).parse())
```

Put that block *after* you read the browser style, because user styles
should to take priority over the browser style sheet,^[In reality this
is handled by browser styles having a lower score than user styles in
the cascade order, but our browser style sheet only has tag selectors
in it, so every rule already has the lowest possible score.] but
before the call to `style`, so you actually use the newly downloaded
rules.

Our CSS engine should now change some margins and paddings as
specified by the web page in question. For example, on this web page,
you should see that the title of the page has moved down
significantly.

Cascade order
=============

So far, `style` applies the rules in order, one after another. And
furthermore, it overwrites existing styles, such as the styles
that come from attribute values. We need to fix that.

In CSS, this is governed by the *cascade order*, which assigns a score
to each selector; rules with higher-scoring selectors overwrite rules
with lower-scoring selectors. Tag selectors get the lowest score;
class selectors one higher; and id selectors higher still. The `style`
attribute has the highest-possible score, so it overwrites everything.
So let\'s add the `score` method to the selector classes that return
this score. Maybe tag selectors have score 1, class selectors 16, id
selectors 256.^[In this simplest implementation the exact numbers
don\'t matter if they sort right, but choosing these numbers makes the
exercises a little easier.]

``` {.python}
class TagSelector:
    def score(self):
        return 1
```

You can write the code for the other selector types.

We\'ll use the score to the rules before passing them to `style`:

``` {.python}
rules.sort(key=lambda x: x[0].score())
```

Here `x[0]` refers to the selector half of a rule, and I\'m calling
the new `score` method. In Python, the `sort` function is *stable*,
which means that things keep their relative order if possible. This
means that in general, a later rule, from a later `<link>` or just
later in a file, will override an earlier one, which is what CSS does
as well.

This works for rules with selectors. We also need inline styles to
override linked stylesheets. We can just tack that on after the rules
loop in `style`:^[The `items()` call is a Python way to get the key
and value out of a dictionary as you iterate over it.]

``` {.python}
def style(node, rules):
    # for selector, pair in rules ...
    for property, value in node.compute_style().items():
        node.style[property] = value
    # for child in node.children ...
```

Our CSS engine now correctly handles conflicts between different rules.

Inherited styles
================

Right now, our CSS styles only affect the block layout mode. We\'d like
to extend CSS to affect inline layout mode as well, but there\'s a
catch: inline layout is mostly concerned with text, but text nodes
don\'t have any styles at all. How can that work?

The solution in CSS is *inheritance*. Inheritance means that if some
node doesn\'t have a value for a certain property, it uses its
parent\'s value instead. Some properties are inherited and some
aren\'t; it depends on the property. Let\'s implement two inherited
properties: `font-weight` (which can be `normal` or `bold`) and
`font-style` (which can be `normal` or `italic`^[Actually, it can also
be `oblique`. No one knows that that is, though some browsers will use
that value to display pseudo-italics, that is, roman text that\'s been
algorithmically slanted.]). To inherit a property, we simple need to
check, after all the rules and inline styles have been applied,
whether the property is set and, if it isn\'t, to use the parent
node\'s style:

``` {.python}
INHERITED_PROPERTIES = [ "font-style", "font-weight" ]
def style(node, rules):
    # handle inline styles
    for prop in INHERITED_PROPERTIES:
        if prop not in node.style and node.parent is None:
            node.style[prop] = "normal"
    # recurse into child nodes
```

This little loop has to come *before* the recursive calling of `style`
on the child nodes because getting the parent\'s value only makes
sense if the parent has already inherited the correct property value.

On `TextNode` objects we can do an even simpler trick, since it always
inherits its styles from its parent:

``` {.python}
def style(node, rules):
    if isinstance(node, TextNode):
        node.style = node.parent.style
    else:
        # ...
```

Now that we have `font-weight` and `font-style` set on every node, we
can use them in `InlineLayout` to set the font:

``` {.python}
self.bold = node.style.get("font-weight", "normal") == "bold"
self.italic = node.style.get("font-style", "normal") == "italic"
```

Now that we have styles on both block and inline nodes, we can
refactor `is_inline`. Instead of testing directly for the `<b>` and
`<i>`, we could test for a CSS property both share. The standard
property is `display`, which can be either `block` or `inline`; it
basically tells you which of the two layout modes to use.^[Modern CSS
adds some funny new values, like `run-in` or `inline-block`, and it
has layout modes set by other properties, like `float` and
`position`. Nothing gold can stay.] So instead of...

``` {.python}
return node.tag in ["i", "b"]
```

... do ...

``` {.python}
return node.style.get("display", "block") == "inline"
```

With inheritance and the `display` property, we can move some more
code into the CSS file.

``` {.css}
i { display: inline; font-style: italic; }
b { display: inline; font-weight: bold; }
```

By the way---why move code to a data file? The advantage is that that
the data file may be easier to write, especially independently of the
rest of the code. So here, you could experiment with new browser
default styles more quickly. But as a software design decision, it is
not always a winner, since you have to maintain a new format (for the
data file) and also code to parse the data and then to apply it as
code. That's true in general, but here in particular, we need a CSS
parser and applier anyway, so the downsides do not apply, and the
refactoring is very much worth it.

::: {.todo}
I think I'd like nodes to have a `font()` method that returns the font
to use.
:::

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
    the `<head>` element (try adding a `<p>` to the head in a real
    browser!). The way this works is that `display` can have the value
    `none`, in which case the element is not displayed and neither are
    any of its children. Implement `display: none` and use that in
    your browser style sheet to hide the `<head>` element.
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
-   CSS allows a rule to have multiple selectors, which is basically the
    same as separate rules sharing a body. To do that, you list multiple
    selectors with a comma in between. Implement this feature, and use
    it to shorten and simplify the browser style sheet. (For example,
    both `<b>` and `<i>` have `display: inline`.)
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
    multiple space-separated selectors, like `ul strong`, which
    selects all `<strong>` elements^[This is basically a `<b>` tag but
    with a hipper name. The idea was to drop all visual aspects from
    element names.] with a `<ul>` ancestor. Implement descendent
    selectors, both in parsing and with a new `DescendentSelector`
    class. Scoring for descendent selectors works just like in
    `AndSelector`. Make sure that something like `section .warning`
    selects warnings inside sections, while `section.warning` selects
    warnings that *are* sections.

