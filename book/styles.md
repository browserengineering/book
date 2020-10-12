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
punctuation, but your attribute parser may not support it.] We want to
store these pairs in a `style` field on the `ElementNode` so we could
consult them during layout.

The first step is adding attributes to `ElementNode`s; attributes are
currently stored in `Tag`s but not `ElementNode`s:

``` {.python}
class ElementNode:
    def __init__(self, tag, attributes):
        self.tag = tag
        self.attributes = attributes
        self.children = []
```

These attributes need to be passed from the token to the `ElementNode`
it creates, both in `parse` and in `implicit_tags`. With the
attributes stored on the `ElementNode`, we can extract[^python-get]
and parse the `style` attribute in particular:

[^python-get]: The `get` method for dictionaries gets a value out of a
    dictionary, or uses a default value if it's not present.

``` {.python}
class ElementNode:
    def __init__(self, tag, attributes):
        # ...
        self.style = {}
        for pair in self.attributes.get("style", "").split(";"):
            if ":" not in pair: continue
            prop, val = pair.split(":")
            self.style[prop.lower().strip()] = val.strip()
```

With these changes, each `ElementNode` should now have a `style`
field with any stylistic choices made by the author.

The CSS box model
=================

It'd be nice to have some stylistic properties for authors to
manipulate with this `style` attribute. Let's add support for
*margins*, *borders*, and *padding*, which change the position of
block layout objects. Here's how those work. In effect, every block
has four rectangles associated with it: the *margin rectangle*, the
*border rectangle*, the *padding rectangle*, and the *content
rectangle*:

![](https://www.w3.org/TR/CSS2/images/boxdim.png)

So far, our block layout objects have had just one size and position;
these will refer to the border rectangle (so that the `x` and `y`
fields point to the top-left corner of the outside of the layout
object's border). To track the margin, border, and padding, we'll also
store the margin, border, and padding widths on each side of the
layout object. That makes for a lot of variables:

``` {.python}
class BlockLayout:
    def __init__(self, parent, node):
        # ....
        self.mt = self.mr = self.mb = self.ml = -1
        self.bt = self.br = self.bb = self.bl = -1
        self.pt = self.pr = self.pb = self.pl = -1
```

The naming convention here is that the first letter stands for margin,
border, or padding, while the second letter stands for top, right,
bottom, or left.

Since each block layout object now has more variables, we'll need to
add code to `layout` to compute them:

``` {.python}
def px(s):
    if str.endswith("px"):
        return int(str[:-2])
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
    colors and styles, while paddings are margins are thought of as
    whitespace, not something you draw.

With their values now loaded, we can use these fields to drive layout.
First of all, when we compute width, we need to account for the space
taken up by the parent's border and padding:[^backslash-continue]

[^backslash-continue]: In Python, if you end a line with a backslash,
    the newline is ignored by the parser, letting you split a logical
    line of code across two actual lines in your file.

``` {.python}
def layout(self):
    # ...
    self.w = self.parent.w - self.parent.pl - self.parent.pr \
        - self.parent.bl - self.parent.br \
        - self.ml - self.mr
    # ...
```

Similarly, when we position boxes, we'll need to account for our own
border and padding:

``` {.python}
def layout(self):
    # ...
    self.y += self.mt
    self.x += self.ml
    y = self.y
    for child in self.children:
        child.x = self.x + self.pl + self.pr + self.bl + self.br
        child.y = y
        child.layout()
        y += child.h + child.mt + child.mb
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
changes, but is a tedious way to change the style of, say, every
paragraph on the page. And if you have a site with many pages, you'll
need to remember to add the same `style` attributes to every web page
to achieve a measure of consistency. CSS provides a better way.

Parsing CSS
===========

In the early days of the web,^[I'm talking Netscape 3. The late 90s.]
the element-by-element approach was all there was.^[Though back then
it wasn't the `style` attribute, it was a custom elements like `font`
and `center`.] CSS was invented to improve on this state of affairs:

-   CSS files can adjust styling of many elements at once
-   CSS files can style multiple pages from a single file
-   CSS is future-proof and supports browsers with different features

To achieve these goals, CSS extends the key-value `style` attribute
with two connected ideas: *selectors* and *cascading*. In CSS, you
have blocks of style information, but those blocks apply to *multiple
elements*, specified using a selector:

``` {.css}
selector {
    property: value;
    property: value;
    property: value;
    ...
}
```

To account for the possibility that allows blocks apply to a single
element, there's a *cascading* mechanism to resolve conflicts in favor
of the most specific rule.

To support CSS in our browser, we'll need to:

- Parse CSS files to understand the selector for each block and also
  the property values that block sets;
- Run each selector to figure out which elements on the page each
  block selects;
- Add the block's property values to those elements' `style` fields.

Let's start with the parsing. I'll use recursive *parsing functions*,
each parsing a certain type of CSS element like selectors, properties,
or blocks. Parsing function will take an index into the input and
return a new index, plus the data it parsed. Since we'll have a lot of
parsing functions, let's organize them in a `CSSParser` class:

``` {.python}
class CSSParser:
    def __init__(self, s):
        self.s = s
```

The class wraps the string we're parsing. Parsing functions access the
string through `self.s`; for example, to parse values:

``` {.python}
def value(self, i):
    j = i
    while self[j].isalnum() or self.s[j] in "-.":
        j += 1
    return s[i:j], j
```

This function takes index `i` pointing to the start of the value and
returns index `j` pointing to its end. It comuputes `j` by
advancing through letters, numbers, and minus and period characters
(which might be present in numbers).

This parsing function the string between `i` and `j`, which will be
the value it just read. In another parsing function, we might
transform or change the returned data; for example, whitespace is
insignificant in CSS, so when we parse whitespace we just return
`None` instead of the whitespace parsed:

``` {.python}
def whitespace(self, i):
    j = i
    while j < len(self.s) and self.s[j].isspace():
        j += 1
    return None, j
```

Parsing functions can also build upon one another. Here's how to parse
property-value pairs:

``` {.python}
def pair(self, i):
    prop, i = self.value(i)
    _, i = self.whitespace(i)
    assert self.s[i] == ":"
    _, i = self.whitespace(i + 1)
    val, i = self.value(i)
    return (prop.lower(), val), i
```

I'm using `value` here for both properties and values. In reality they
have different syntaxes, but we'll support few enough values in our
parser that this simplification will be alright. And note the
`assert`: that raises an error if what you're parsing isn't a valid
pair. When we parse rule bodies, we can catch this error to skip
property-value pairs that don't parse:

``` {.python}
def body(self, i):
    pairs = {}
    assert self.s[i] == "{"
    _, i = self.whitespace(i+1)
    while True:
        if i > len(self.s): break
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

Skipping parse errors is a double-edged sword. It hides error
messages, making debugging CSS files more difficult, and also makes it
harder to debug your parser.^[Try debugging without the `try` block
first.] This makes "catch-all" error handling like this a code smell
in most cases.

However, on the web there is an unusual benefit: it supports an
ecosystem of multiple implementations. For example, different browsers
may support different syntaxes for property values.^[Our browser does
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

We'll start by defining some data structures for selectors:^[I'm
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
        return TagSelector(name.lower()), i
```

Note the arithmetic with `i`: we pass `i+1` to `value` in the class
and ID cases (to skip the hash or dot) but not in the tag case (since
that first character is part of the tag). Like with property names,
I'm using `value` for tag, class, and identifier names, a
simplification a real browser couldn't do.

Finally, selectors and bodies can be combined:

``` {.python}
def rule(self, i):
    selector, i = self.selector(i)
    _, i = self.whitespace(i)
    body, i = self.body(i)
    return (selector, body), i
```

Finally, a CSS file itself is just a sequence of rules:

``` {.python}
def file(self, i):
    rules = []
    _, i = self.whitespace(i)
    while i < len(self.s):
        try:
            rule, i = self.rule(i)
        except AssertionError:
            while i < len(self.s) and self.s[i] != "}":
                i += 1
        else:
            rules.append(rule)
        _, i = self.whitespace(i)
    return rules, i

```

With all our parsing functions written, we can give the `CSSParser`
function a simple entry point:

``` {.python}
class CSSParser:
    def parse(self):
        rules, _ = self.file(0)
        return rules
```

Make sure to test your parser, like you did the [HTML parser](html.md)
two chapters back. If you find an error, the best way to proceed is to
print the index at the beginning of every parsing function, and print
both the index and parsed value at the end. You'll get a lot of
output, but if you step through it by hand, you will find your mistake.

Now that we've parsed a CSS file, we need to apply it to the elements
on the page.

Selecting styled elements
=========================

Our next step, after parsing CSS, is to figure out which elements each
rule applies to. The easiest way to do that is to add a method to the
selector classes, which tells you if the selector matches. Here's how
it looks like for `ClassSelector`:

``` {.python}
def matches(self, node):
    return self.cls == node.attributes.get("class", "").split()
```

You can write `matches` for `TagSelector` and `IdSelector` on your
own.

Now that we know which rules applies to an element, we need use their
property-value pairs to change its `style`. The logic is pretty
simple:

-   Recursive over the tree of `ElementNode`s;
-   For each rule, check if the rule matches;
-   If it does, go through the property/value pairs and assign them.

Here's what the code would look like:

``` {.python}
def style(node, rules):
    if not isinstance(node, ElementNode): return
    for selector, pairs in rules:
        if selector.matches(node):
            for property in pairs:
                if property not in node.style:
                    node.style[property] = pairs[property]
    for child in node.children:
        style(child, rules)
```

We're skipping `TextNode` objects because text doesn't have styles in
CSS (just the elements that wrap the text).

Note that we skip properties that already have a value. That's because
`style` attributes are loaded into the `style` field first, and should
take priority. But it means that it matters what order you apply the
rules in.

What's the correct order? In CSS, it's called *cascade order*, and it
is based on the selector used by the rule. Tag selectors get the
lowest priority; class selectors one higher; and id selectors higher
still. Just like how the `style` attribute comes first, we need to
sort the rules in priority order, with higher-priority rules first.

So let's add a `priority` method to the selector classes that return
this priority. In this simplest implementation the exact numbers don't
matter if they sort right, but with an eye toward the future let's
assign tag selectors priority `1`, class selectors priority `16`, and
id selectors priority `256`:

``` {.python}
class TagSelector:
    def priority(self):
        return 1
        
class ClassSelector:
    def priority(self):
        return 16
        
class IdSelector:
    def priority(self):
        return 256
```

Now, before you call `style`, you should sort your list of rules:

``` {.python}
rules.sort(key=lambda (selector, body): selector.priority(), reverse=True)
```

Note the `reverse` flag: we want higher-priority rules to come first.
In Python, the `sort` function is *stable*, which means that things
keep their relative order if possible. This means that in general, a
later rule has higher priority, unless the selectors used force
something different.

Downloading styles
==================

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
}
```

Our CSS parser can convert this CSS source code to text:

``` {.python}
class Browser:
    def load(self, url):
        header, body = request(url)
        nodes = parse(lex(body))

        with open("browser.css") as f:
            browser_style = f.read()
            rules = CSSParser(browser_style).parse()
```

Beyond the browser styles, our browser needs to find website-specific
CSS files, download them, and use them as well. Web pages call out
their CSS files using the `link` element, which looks like this:

``` {.example}
<link rel="stylesheet" href="/main.css">
```

The `rel` attribute here tells that browser that this is a link to a
stylesheet. Browsers mostly don't care about any [other kinds of
links][link-types], but search engines do[^like-canonical], so `rel`
is mandatory.

[^like-canonical]: For example, `rel=canonical` names the "master
    copy" of a page and is used by search engines to track pages that
    appear at multiple URLs.

[link-types]: https://developer.mozilla.org/en-US/docs/Web/HTML/Link_types

To find these links, we'll need another recursive function:

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

For each link, the `href` attribute gives a location for the
stylesheet in question. The browser is expected to make a GET request
to that location, parse the stylesheet, and use it. Note that the
location is not a full URL; it is something called a *relative URL*,
which can come in three flavors:^[There are more flavors, including
query-relative and scheme-relative URLs, which I'm skipping.]

-   A normal URL, which specifies a scheme, host, path, and so on
-   A host-relative URL, which starts with a slash but reuses the
    existing scheme and host
-   A path-relative URL, which doesn't start with a slash and is
    instead tacked onto the current URL (up but not past its last slash)

To turn a relative URL into a full URL, then, we need to figure out
which case we're in:

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

Let's put it all together. We want to collect CSS rules from each of
the linked files, and the browser style sheet, into one big list so we
can apply each of them. So let's add them onto the end of the `rules`
list:

``` {.python}
def load(self, url):
    # ...
    for link in find_links(nodes, []):
        header, body = request(relative_url(link, url))
        rules.extend(CSSParser(body).parse())
```

Since the page's stylesheets come *after* browser style, user styles
take priority over the browser style sheet.^[In reality this is
handled by browser styles having a lower score than user styles in the
cascade order, but our browser style sheet only has tag selectors in
it, so every rule already has the lowest possible score.] With the
rules loaded, we need only sort and apply them and then do layout:

``` {.python}
def load(self, url):
    # ...
    rules.sort(key=lambda (selector, body): selector.priority(),
        reverse=True)
    style(nodes, rules)
    self.layout(nodes)
```

With this done, each page should now automatically apply the margins
and paddings specified in the browser stylesheet, making it possible
to delete some of `InlineLayout`'s tag handlers in its `close` method.

Inherited styles
================

Our implementation of margins, borders, and padding styles only affect
the block layout mode.[^inline-margins] We'd like to extend CSS to
affect inline layout mode as well, for example to change text styling.
But there's a catch: inline layout is mostly concerned with text, but
text nodes don't have any styles at all. How can that work?

[^inline-margins]: Margins, borders, and padding can be applied to
    inline layout objects in a real browser, but they work kind of a
    funky way.

The solution in CSS is *inheritance*. Inheritance means that if some
node doesn't have a value for a certain property, it uses its
parent's value instead. Some properties are inherited and some
aren't; it depends on the property: the margin, border, and padding
properties aren't inherited, but the font properties are.

Let's implement three inherited properties: `font-weight` (which can
be `normal` or `bold`), `font-style` (which can be `normal` or
`italic`), and `font-size` (which can be any pixel value). To inherit
a property, we need to check, after all the rules and inline styles
have been applied, whether the property is set and, if it isn't, to
use the parent node's style. To begin with, let's list our inherited
properties and their default values:

``` {.python}
INHERITED_PROPERTIES = {
    "font-style": "normal",
    "font-weight": "normal",
    "font-size": "16px",
]
```

Now, in our `style` loop we'll need access to the parent node, so
let's pass that along recursively:

``` {.python}
def style(node, parent, rules):
    # ...
    for child in node.children:
        style(child, node, rules)
```

Now let's add another loop to `style`, *after* the handling of rules
but *before* the recursive calls, to inherit properties:

``` {.python}
def style(node, parent, rules):
    # ...
    for property, default in INHERITED_PROPERTIES.items():
        if property not in node.style:
            if parent:
                node.style[property] = parent.style[property]
            else:
                node.style[property] = default
    # ...
```

Because this loop comes *before* the recursive call, the parent has
already inherited the correct property value when the children try to
read it.

On `TextNode` objects we can do an even simpler trick, since never has
styles of its own and only inherits from its parent:

``` {.python}
def style(node, rules):
    if isinstance(node, TextNode):
        node.style = node.parent.style
    else:
        # ...
```

With `font-weight` and `font-style` set on every node, `InlineLayout`
no longer needs `style`, `weight`, and `size` fields; they were only
there to track when text was inside or outside `<i>` and `<b>` tags,
and now styles and inheritance are doing that job:

``` {.python}
class InlineLayout:
    def font(self):
        bold = node.style["font-weight"]
        italic = node.style["font-style"]
        if italic == "normal": italic = "roman"
        size = int(px(node.style.get("font-size")) * .75)
        return tkinter.font.Font(size=size, weight=weight, slant=slant)
    
    def text(self, text):
        font = self.font()
        for word in text.split():
            # ...
```

Note that the `font-style` needs to replace the CSS default of
"normal" with the Tk value "roman", and the `font-size` needs to be
converted from points to pixels.[^72ppi]

[^72ppi]: Normally you think of points as a physical length unit (one
    72^nd^ of an inch) and pixels as a digital unit (dependent on the
    screen) but in CSS, the conversion is fixed at exactly 75% (or 96
    pixels per inch). I'm not sure why, it seems weird and it does
    cause problems.

Now support for the `i`, `b`, `small`, and `big` tags can all be moved
to CSS:

``` {.css}
i { font-style: italic; }
b { font-weight: bold; }
small { font-size: 12px; }
big { font-size: 20px; }
```

Another place where the code depends on specific tag names is
`has_block_children`, which relies on a list of inline elements. The
CSS `display`, which can be either `block` or `inline`, replaces that
mechanism.^[Modern CSS adds way more values, like `run-in` or
`inline-block` or `flex` or `grid`, and it has layout modes set by
other properties, like `float` and `position`. Design matters.]
So we can add all the inline elements to our browser style sheet:

``` {.css}
a { display: inline; }
em { display: inline; }
/* ... */
```

And then read that in `has_block_children`:

``` {.python}
def has_block_children(self):
    for child in self.node.children:
        # ...
        elif child.style.get("display", "inline") == "inline":
            return False
    return True
```

With these changes, `InlineLayout` can lose its `open` and `close`
methods, becoming a small, self-contained engine for line layout while
most of its domain-specific knowledge of tags is moved to the browser
style sheet.

That style sheet is easier to edit, since it's independent of the rest
of the code. And while sometimes moving things to a data file means
maintaining a new format. Here we get to reuse a format, CSS, that our
browser needs to support anyway.

Summary
=======

This chapter implemented a rudimentary but complete styling engine,
including downloading, parser, matching, sorting, and applying CSS
files. That means we:

- Added styling support in both `style` attributes and `link`ed CSS files;
- Implemented for margins, borders, and padding to block layout objects;
- Refactored `InlineLayout` to move the font properties to CSS;
- Removed most tag-specific reasoning from our layout code.

Our styling engine is also relatively easy to extend with properties
and selectors.

Exercises
=========

*Shortcuts*: CSS "shortcut properties" set multiple related CSS
properties at the same time; `margin`, `padding`, `border-width`, and
`font` are all popular shortcuts. Implement these four shortcut
properties. If you do it in the `body` parsing function, you won't
need to change the rest of the code. Start with the case where all of
the subproperties are specified, then add default values.

*Comma*: CSS allows a rule to have multiple, comma-separated
selectors, which is basically the same as multiple rules with the same
body. Implement this and use it to shorten and shorten the browser
style sheet.

*Width/Height*: Add support to block layout objects for the `width`
and `height` properties. These can either be a pixel value, which
directly sets the width or height of the layout object, or the word
`auto`, in which case the existing layout algorithm is used.

*Percentages*: Most places where you can specify a pixel value in CSS,
you can also write a percentage value like `50%`. When you do that for
`margin`, `border`, or `padding` properties, it's relative to the
layout object's width, while when you do it for `font-weight` it's
relative to the parent's font size. Implement percentage values for
all of these properties.

*Combinations*: Sometimes you want to select an element by tag *and*
class. You do this by concatenating the selectors without anything in
between: `span.announce` selects elements that match both `span` and
`.announce`. Implement a new `AndSelector` class to represent these
and modify the parser to parse them. Sum priorities.[^lexicographic]

[^lexicographic]: You're supposed to use lexicographic scoring for
    these `AndSelector` things, but sums will work fine as long as no
    one strings more than 16 selectors together.

*Descendants*: When multiple selectors are separated with spaces, like
`ul b`, that selects all `<b>` elements with a `<ul>` ancestor.
Implement descendent selectors; scoring for descendent selectors works
just like for comnbination selectors. Make sure that something like `section
.warning` selects warnings inside sections, while `section.warning`
selects warnings that *are* sections.

