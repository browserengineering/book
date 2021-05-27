---
title: Applying User Styles
chapter: 6
prev: layout
next: chrome
...

So far, each HTML element's appearance has been hard-coded into our
browser. But web pages should be able to override our style decisions
and take on a unique character. This is done via _Cascading Style
Sheets_, a simple styling language for web authors (and, as we'll see,
browser developers) to define how a web page ought to look.

The style attribute
===================

In the [last chapter](layout.md), we gave each `pre` element a gray
background. It looks OK, and it *is* good to have some defaults, but
you can imagine a site wanting a say in how it looks.

The `style` attribute is the simplest way to override browser styles.
It looks like this:

``` {.example}
<div style="background-color:lightblue"></div>
```

This `<div>` element's `style` attribute contains a property/value
pair matching the property `background-color` to the value
`lightblue`.^[CSS allows spaces around the punctuation, but our
simplistic attribute parser does not support that.] Multiple
property/value pairs, separated by semicolons, are also allowed. The
browser looks at those property-value pairs when painting the element;
this way the `style` attribute allows web page authors to override the
default background for `pre` elements.

Let's implement that in our browser. We'll start with a recursive
function that creates a `style` field on each node to store this style
information:

``` {.python replace=(node)/(node%2C%20rules)}
def style(node):
    node.style = {}
    # ...
    for child in node.children:
        style(child, rules)
```

The `style` dictionary is filled in by parsing the element's `style`
attribute:[^python-get]

[^python-get]: The `get` method for dictionaries gets a value out of a
    dictionary, or uses a default value if it's not present.
    
``` {.python replace=(node)/(node%2C%20rules),val.strip()/computed_value}
def style(node):
    # ...
    if isinstance(node, Element):
        for pair in node.attributes.get("style", "").split(";"):
            if ":" not in pair: continue
            prop, val = pair.split(":")
            node.style[prop.strip().lower()] = val.strip()
    # ...
```

The browser can use the `style` information when it paints the
element:

``` {.python}
class BlockLayout:
    def paint(self, display_list):
        bgcolor = self.node.style.get("background-color",
                                      "transparent")
        if bgcolor != "transparent":
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, bgcolor)
            display_list.append(rect)
        # ...
```

Put the exact same lines of code inside `InlineLayout` as well, so
that paragraphs and list items and so on can have backgrounds as well.
For now, also remove the default gray background from `pre` elements
(we'll put it back soon).

Open up this web page in your browser, and the code block right after
this paragraph should now have a light blue background:

``` {.example style=background-color:lightblue}
<div style="background-color:lightblue"> ... </div>
```

So this is one way web pages change their appearance. But honestly,
it's a pain---you need to set a `style` attribute on each element, and
if you change the style that's a lot of attributes to edit. In the
early days of the web,^[I'm talking Netscape 3. The late 90s.] the
element-by-element approach was all there was. CSS was invented to
improve on this state of affairs:

- One CSS file can consistently style many web pages at once
- One line of CSS can consistently style many elements at once
- CSS is future-proof and supports browsers with different features

To achieve these goals, CSS extends the key-value `style` attribute
with two related ideas: *selectors* and *cascading*. Selectors
describe which HTML elements a list of property/value pairs apply
to:[^media-queries]

[^media-queries]: CSS rules can also be guarded by "media queries",
    which say that a rule should apply only in certain browsing
    environments (like only on mobile or only in landscape mode).
    Media queries are super-important for building sites that work
    across many devices (try this book on mobile!).

``` {.css}
selector { property-1: value-1; property-2: value-2; }
```

Since one of these *rules* can apply to many elements, it's possible
for several blocks to apply to the same element. So browsers have a
*cascading* mechanism to resolve conflicts in favor of the most
specific rule. Cascading also means a browser can ignore rules it
doesn't understand and choose the next-most-specific rule that it does
understand.

Let's add support for CSS to our browser. We'll need to parse CSS
files into selectors, blocks, and property-values pairs; figure out
which elements on the page match each selector; and then add the
block's property values to those elements' `style` fields.

::: {.further}
Actually, before CSS, you'd style pages with custom elements like
[`font`][font-elt] and [`center`][center-elt]. This was easy to
implement but made it hard to keep pages consistent. There
were also properties on `<body>` like [`text` and `vlink`][body-attrs]
that could consistently set text colors, mainly for links.
:::

[font-elt]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/font
[center-elt]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/center
[body-attrs]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/body#attributes

Parsing with functions
======================

Let's start with the parsing. I'll use recursive *parsing functions*.
Each CSS construct like selectors, blocks, and properties gets a
parsing function, which advances through the text as it parses and
returns any data it parsed. We'll have a lot of these functions, so
let's organize them in a `CSSParser` class. The class can store the
the string `s` and current index `i`:

``` {.python}
class CSSParser:
    def __init__(self, s):
        self.s = s
        self.i = 0
```

Let's start small and build up. A parsing function for whitespace
increments the index `i` past every whitespace character:

``` {.python}
def whitespace(self):
    while self.i < len(self.s) and self.s[self.i].isspace():
        self.i += 1
```

Whitespace is insignificant, so there's no data to return.

Parsing functions can fail. For example, to check for a literal colon
(or some other punctuation character) you'd do this:

``` {.python}
def literal(self, literal):
    assert self.s[self.i] == literal
    self.i += 1
```

Here `assert` will raise an exception if the condition is
false.[^add-a-comma]

[^add-a-comma]: Add a comma after the condition, and you can add error
    text to the assertion. I recommend doing that for all of your
    assertions to help in debugging. I also recommend using assertions
    generously.

Parsing functions can also return data. For example, to parse CSS
properties and values, we'll use this code:

``` {.python indent=4}
def word(self):
    start = self.i
    while self.i < len(self.s):
        if self.s[self.i].isalnum() or self.s[self.i] in "#-.%":
            self.i += 1
        else:
            break
    assert self.i > start
    return self.s[start:self.i]
```

This function increments `i` through any word characters,[^word-chars]
much like `whitespace`, but it also returns the parsed data. To do
that it stores where it started and extracts the substring it moved
through. Also note the assert: if `i` didn't advance though any word
characters, that means `i` didn't point at a word to begin with.

[^word-chars]: I've chosen the set of word characters here to cover
    property names (which use letters and dash), numbers (which use
    the minus sign, numbers, periods), units (the percent sign), and
    colors (which use the hash sign). Real CSS values have a complex
    syntax of their own.

Parsing functions built upon one another. Property-value pairs, for
example, are a property, a colon, and a value,[^technically-different]
with whitespace in between:

[^technically-different]: In reality properties and values have
    different syntaxes, so using `word` for both isn't quite right,
    but for our browser's limited CSS support this simplification will
    be alright.

``` {.python}
def pair(self):
    prop = self.word()
    self.whitespace()
    self.literal(":")
    self.whitespace()
    val = self.word()
    return prop.lower(), val
```

This combines `word`, `whitespace`, and `literal` into a more
complicated parsing function. And note that if `i` does not actually
point to a property-value pair, one of the `word` calls or the
`literal` call will fail.

Sometimes we need to call these parsing functions in a loop. For
example, a sequence of property-value pairs looks like this:

``` {.python indent=8}
def body(self):
    pairs = {}
    while self.i < len(self.s) and self.s[self.i] != "}":
        prop, val = self.pair()
        pairs[prop] = val
        self.whitespace()
        self.literal(";")
        self.whitespace()
    return pairs
```

One twist to parsing functions is handling errors. So for example,
sometimes our parser will see a malformed property-value pair, either
because the page author made a mistake or because they're using a CSS
feature that our parser doesn't support. We can catch this error to
skip property-value pairs that don't parse.

We'll use this little function to skip things; it stops at any one of
a list of characters, and returns that character (or `None` if it was
stopped by the end of the file):

``` {.python indent=4}
def ignore_until(self, chars):
    while self.i < len(self.s):
        if self.s[self.i] in chars:
            return self.s[self.i]
        else:
            self.i += 1
```

When we fail to parse a property-value pair, we need to go to either
the next property-value pair (skip to a semicolon) or the end of the
block (skip to a close brace).

``` {.python indent=4}
def body(self):
    # ...
    while self.i < len(self.s) and self.s[self.i] != "}":
        try:
            # ...
        except AssertionError:
            why = self.ignore_until([";", "}"])
            if why == ";":
                self.literal(";")
                self.whitespace()
            else:
                break
    # ...
```

Skipping parse errors is a double-edged sword. It hides error
messages, so debugging style sheets becomes more difficult; it also
makes it harder to debug your parser.[^try-no-try] So this "catch-all"
error handling is usually a code smell.

[^try-no-try]: I suggest removing the `try` block when debugging.

But on the web "catch-all" error handling has an unusual benefit. The
web is an ecosystem of many browsers, which (for example) support
different kinds of property values.[^like-parens] CSS that parses in
one browser might not parse in another. With silent parse errors,
browsers just ignore stuff they don't understand, and web pages mostly
work in all of them. The principle (variously called "Postel's
Law",[^for-jon] the "Digital Principle",[^from-circuits] or the
"Robustness Principle") is: produce maximally conformant output but
accept even minimally conformant input.

[^like-parens]: Our browser does not support parentheses in property
    values, for example, which real browsers use for things like the
    `calc` and `url` functions.
    
[^for-jon]: After a line in the specification of TCP, written by Jon
    Postel

[^from-circuits]: After a similar idea in circuit design, where
    transistors must be nonlinear to reduce analog noise.

Selectors
=========

So far our parser only handles property/value pairs. But the magic of
CSS is the selectors! Selectors come in lots of types but our browser
will support the two simplest:

- Tag selectors: `p` selects all `<p>` elements, `ul` selects all
  `<ul>` elements, and so on.

- Descendant selectors: `article div` selects all elements matching
  `div` that have an ancestor matching `article`.[^how-associate]

[^how-associate]: The descendant selector associates to the left; in
    other words, `a b c` means a `c` that descends from a `b` that
    descends from an `a`, which maybe you'd write `(a b) c` if CSS had
    parentheses.

We'll start by defining data structures for selectors:

``` {.python}
class TagSelector:
    def __init__(self, tag):
        self.tag = tag

class DescendantSelector:
    def __init__(self, ancestor, descendant):
        self.ancestor = ancestor
        self.descendant = descendant
```

A parsing function for selectors is just another loop:

``` {.python indent=4}
def selector(self):
    out = TagSelector(self.word().lower())
    self.whitespace()
    while self.i < len(self.s) and self.s[self.i] != "{":
        tag = self.word()
        descendant = TagSelector(tag.lower())
        out = DescendantSelector(out, descendant)
        self.whitespace()
    return out
```

Tag names, in HTML, are case-insensitive; using `word` is actually not
quite right but it is close enough.

Now that we have parsers for both selectors and blocks, we can build a
whole CSS parser. If a selector fails to parse, this combined parser
will skip both it and the associated block:

``` {.python indent=4}
def parse(self):
    rules = []
    self.whitespace()
    while self.i < len(self.s):
        try:
            selector = self.selector()
            self.literal("{")
            self.whitespace()
            body = self.body()
            self.literal("}")
            rules.append((selector, body))
        except AssertionError:
            why = self.ignore_until(["}"])
            if why == "}":
                self.literal("}")
                self.whitespace()
            else:
                break
    return rules
```

Make sure to test your parser, just like the HTML parser [two chapters
back](html.md). Here are some errors you might run into:

- If the output is missing some rules or properties, it's probably a
  bug being hidden by error handling. Remove some `try` blocks and see
  if the error in question can be fixed.
- If you're seeing extra rules or properties that are mangled versions
  of the correct ones, you probably forgot to update `i` somewhere.
- If you're seeing an infinite loop, check whether the error-handling
  code always increases `i`. Each parsing function (except
  `whitespace`) should always increment `i`.

You can also add a `print` statement to the start and end[^add-parens]
of each parsing function with the name of the parsing
function,[^add-spaces] the index `i`,[^show-context] and the parsed
data. It's a lot of output, but it's a sure-fire way to find really
complicated bugs.

[^add-parens]: If you print an open parenthesis at the start of the
function and a close parenthesis at the end, you can use your editor's
"jump to other parenthesis" feature to skip through output quickly.

[^add-spaces]: If you also add the right number of spaces to each line
it'll be a lot easier to read. Don't neglect debugging niceties like
this!

[^show-context]: It can be especially helpful to print, say, the 20
characters around index `i` from the string.

Once you've got your parser debugged, let's start applying the parsed
style sheet to the web page.

Applying style sheets
=====================

The goal isn't just parsing CSS: it's using it to style the web page.
First, the browser has to figure out which elements each rule applies
to. Let's start by adding a method to each selector that tells you if
it matches a given element:

``` {.python}
class TagSelector:
     def matches(self, node):
         return isinstance(node, Element) and self.tag == node.tag
```

Since descendant selectors wrap other selectors, their `match` method
is recursive:

``` {.python}
class DescendantSelector:
    def matches(self, node):
        if not self.descendant.matches(node): return False
        while node.parent:
            if self.ancestor.matches(node.parent): return True
            node = node.parent
        return False
```

If a rule applies to an element, the browser needs to add its
property-value pairs to the element's `style`. The logic is pretty
simple; first, we add a `rules` argument to the `style` function:

``` {.python}
def style(node, rules):
    # ...
```

Then, for each `Element` node we need to determine which CSS rules
apply to it and copy their property/value pairs over:

``` {.python replace==%20value/=%20computed_value}
def style(node, rules):
    # ...
    for selector, body in rules:
        if not selector.matches(node): continue
        for property, value in body.items():
            node.style[property] = value
```

The outer loop skips rules that don't match and the inner loop copies
over properties from matching rules. Put this loop before the one that
parses the `style` attribute: the attribute is supposed to take
priority over CSS style sheets.

Since two rules can apply to the same element, it matters what order
you apply the rules in. What's the correct order? In CSS, it's called
*cascade order*, and it is based on the selector used by the rule. Tag
selectors get the lowest priority; class selectors one higher; and id
selectors higher still. But since our CSS parser just has tag
selectors, you just count the number of tag selectors to put the rules
in order:

``` {.python}
class TagSelector:
    def __init__(self, tag):
        # ...
        self.priority = 1

class DescendantSelector:
    def __init__(self, ancestor, descendant):
        # ...
        self.priority = ancestor.priority + descendant.priority
```

To use Python's `sorted` function, we need a function that extracts
the priority of a rule's selector:

``` {.python}
def cascade_priority(rule):
    selector, body = rule
    return selector.priority
```

Then we can style web page using a list of parsed rules like this:

``` {.python indent=8}
def load(self, url):
    # ...
    nodes = HTMLParser(body).parse()

    rules = []
    style(nodes, sorted(rules, cascade_priority))

    self.document = DocumentLayout(nodes)
    # ...
```

In Python, the `sorted` function is *stable*, which means that things
keep their relative order if possible. This means that in general, a
rule that comes later in the CSS file has higher priority, unless the
selectors used force something different. That's how real browsers do
it, too. The `reversed` call is because we want higher-priority rules
to come first.

So our browser just needs to download some CSS files and it can start
styling web pages!

Downloading styles
==================

Browsers get CSS code from two sources. First, each browser ships with
a *browser style sheet*,[^technically-ua] which defines the default
styles for all sorts of elements; second, browsers download CSS code
from the web, as directed by web pages they browse to. Let's start
with the browser style sheet.

[^technically-ua]: Technically called a "User Agent" style sheet. User Agent,
 like the Memex.

Our browser's style sheet might look like this:

``` {.css}
pre { background-color: gray; }
```

Let's store that in a new file, `browser.css`, and have our browser
load and parse that file when it downloads a page:[^not-correct-browser-styles]

``` {.python replace=browser.css/browser6.css}
class Browser:
    def load(self, url):
        # ...
        rules = []
        with open("browser.css") as f:
            rules.extend(CSSParser(f.read()).parse())
        # ...
```

Beyond the browser styles, our browser needs to find website-specific
CSS files, download them, and use them as well. Web pages name their
CSS files using the `link` element, which looks like this:

``` {.example}
<link rel="stylesheet" href="/main.css">
```

The `rel` attribute here tells that browser that this is a link to a
style sheet. Browsers mostly don't care about any [other kinds of
links][link-types], but search engines do,[^like-canonical] so `rel`
is mandatory. And the `href` attribute describes the CSS file's URL.

[link-types]: https://developer.mozilla.org/en-US/docs/Web/HTML/Link_types

[^like-canonical]: For example, `rel=canonical` names the "true name"
    of a page and is used by search engines to track pages that appear
    at multiple URLs.

We could definitely write a little recursive function to find every
`link` element with those exact attributes. But we'll be doing similar
tasks a lot in the next few chapters, so let's instead write a more
general recursive function to turn a tree into a list:

``` {.python}
def tree_to_list(tree, list):
    list.append(tree)
    for child in tree.children:
        tree_to_list(child, list)
    return list
```

We can later use this function on the layout tree as well. Anyway, 
now we can grab the URLs for each CSS file with this line:

``` {.python indent=4}
def load(self, url):
    # ...
    links = [node.attributes["href"]
             for node in tree_to_list(nodes, [])
             if node.tag == "link"
             and "href" in node.attributes
             and node.attributes.get("rel") == "stylesheet"]
    # ...
```

It's kind of crazy, honestly, that Python lets you do this. Anyway,
now we have all the style sheet URLs. The browser is expected to make a
GET request to that location, parse the style sheet, and use it to
style the page.

Note that style sheet URLs we have are not full URLs; they are
something called *relative URLs*, which can come in three
flavors:^[There are even more flavors, including query-relative and
scheme-relative URLs, that I'm skipping.]

-   A normal URL, which specifies a scheme, host, path, and so on;
-   A host-relative URL, which starts with a slash but reuses the
    existing scheme and host; or
-   A path-relative URL, which doesn't start with a slash and is
    resolved like a file name would be.[^how-file]
    
[^how-file]: The "file name" after the last slash of the current URL
    is dropped; if the relative URL starts with "../", slash-separated
    "directories" are dropped from the current URL; and then the
    relative URL is put at the end.

To turn a relative URL into a full URL, then, we need to figure out
which case we're in:

``` {.python}
def relative_url(url, current):
    if "://" in url:
        return url
    elif url.startswith("/"):
        scheme, hostpath = current.split("://", 1)
        host, oldpath = hostpath.split("/", 1)
        return host + url
    else:
        dir, _ = current.rsplit("/", 1)
        while url.startswith("../"):
            dir, _ = dir.rsplit("/", 1)
            url = url[3:]
        return dir + "/" + url
```

Let's put it all together. We want to collect CSS rules from each of
the linked files, and the browser style sheet, into one big list so we
can apply each of them. So let's add them onto the end of the `rules`
list:

``` {.python indent=4}
def load(self, url):
    # ...
    for link in links:
        try:
            header, body = request(relative_url(link, url))
            rules.extend(CSSParser(body).parse())
        except:
            continue
```

The `try`/`except` here handles the case where downloading a style
sheet fails---in which case the browser just ignores it. But if you're
debugging `relative_url` try removing the `try`/`except` here, which
can hide errors.

Since the page's style sheets come *after* browser styles, user styles
take priority over the browser style sheet. With the rules loaded, we
need only sort and apply them and then do layout, the code for which
we've already added to `load`. Open this page up again, and you should
see both gray backgrounds on every code block (thanks to the browser
style sheet) and light-gold backgrounds on this book's mailing list
signup form (try the book's main page).

Alright: we've got background colors that can be configured by web
page authors. But there's more to web design than that! At the very
least, if you're changing background colors you might want to change
foreground colors as well---the CSS `color` property. For example,
usually links are blue. But there's a catch: `color` affects text, but
text nodes don't have any styles at all. How can that work?

::: {.further}
Each browser has its own browser style sheet ([Chromium][blink-css],
[Safari][webkit-css], [Firefox][gecko-css]). [Reset
style sheets][mdn-reset] are often used to overcome any differences.
This works because web page style sheets take precedence over the
browser style sheet, just like in our browser, though real browsers
[fiddle with priorities][cascade-order] to make that
happen.[^ours-works]
:::

[mdn-reset]: https://developer.mozilla.org/en-US/docs/Web/CSS/all
[cascade-order]: https://www.w3.org/TR/2011/REC-CSS2-20110607/cascade.html#cascading-order
[blink-css]: https://source.chromium.org/chromium/chromium/src/+/master:third_party/blink/renderer/core/html/resources/html.css
[gecko-css]: https://searchfox.org/mozilla-central/source/layout/style/res/html.css
[webkit-css]: https://github.com/WebKit/WebKit/blob/main/Source/WebCore/css/html.css

[^ours-works]: Our browser style sheet only has tag selectors in it,
so just putting them first works well enough. But if the browser style sheet
had any descendant selectors, we'd encounter bugs.

Inherited styles
================

The solution in CSS is *inheritance*. Inheritance means that if some
node doesn't have a value for a certain property, it uses its parent's
value instead. Some properties are inherited and some aren't; it
depends on the property. Background color isn't inherited, but text
color and other font properties are.

So let's implement text color and inheritance. And while we're at it,
let's also implement three other font properties: `font-weight`
(`normal` or `bold`), `font-style` (`normal` or `italic`), and
`font-size` (a length or percentage).

Let's start by listing our inherited properties and their default
values:

``` {.python}
INHERITED_PROPERTIES = {
    "font-size": "16px",
    "font-style": "normal",
    "font-weight": "normal",
    "color": "black",
}
```

The actual inheritance happens in the `style` function, *before* the
other loops, since explicit rules override inheritance:

``` {.python}
def style(node, rules):
    # ...
    for property, default in INHERITED_PROPERTIES.items():
        if node.parent:
            node.style[property] = node.parent.style[property]
        else:
            node.style[property] = default
    # ...
```

Inheriting font size comes with a twist. Web pages can use percentages
as font sizes: `h1 { font-size: 150% }` makes headings 50% bigger than
normal text. But what if you had, say, a `code` element inside an `h1`
tag---would that inherit the `150%` value for `font-size`? Would it be
another 50% bigger than the rest of the heading text? That seems
wrong. So in fact, browsers resolve percentages to absolute pixel
units before storing them in the `style`; it's called
["computing"][^css-computed] the style.

[^css-computed]: Full CSS is a bit more confusing: there are
[specified, computed, used, and actual values][css-computed], and they
affect lots of CSS properties besides `font-size`. We're just
implementing those other properties in this book.

[css-computed]: https://www.w3.org/TR/CSS2/cascade.html#value-stages

In our browser, only `font-size` needs to be computed in this way, so
the code looks like this:

``` {.python}
def compute_style(node, property, value):
    if property == "font-size":
        # ...
    else:
        return value
```

Compute `font-size` values works differently for pixel and percentages
values:

``` {.python indent=8}
if value.endswith("px"):
    return value
elif value.endswith("%"):
    if node.parent:
        parent_px = float(node.parent.style["font-size"][:-2])
    else:
        parent_px = 16
    return str(float(value[:-1]) / 100 * parent_font_size) + "px"
else:
    return None
```

Now `style` can call `computed_style` any time it reads a property
value out of a stylesheet:

``` {.python}
def style(node, rules):
    # ...
    for selector, body in rules:
        if not selector.matches(node): continue
        for property, value in body.items():
            computed_value = compute_style(node, property, value)
            if not computed_value: continue
            node.style[property] = computed_value
    # ...
```

You'll also need to call `computed_style` in the loop that handles
`style` attributes. Note that because `style` has the recursive call
at the end of the function, any time `computed_style` is called for a
node, that node's parent already has a `font-size` value stored.

So now with the `color` and font properties implemented, let's change
`InlineText` to use them!

Font Properties
===============

Inside `InlineLayout`, font information for every word is looked up in
the `text` method. Since we now want to use style information now,
we'll need to change `text` to take a `Text` input, not just a string:

``` {.python indent=4}
def text(self, node):
    # ...
    for word in node.text.split():
        # ...
```

We also need to change `recurse` to pass that node:

``` {.python indent=4}
def recurse(self, node):
    if isinstance(node, Text):
        self.text(node)
    else:
        # ...
```

Now we can look up font size, weight, and style information from
`node` instead of using the `style`, `weight`, and `size` fields on
`InlineLayout`:

``` {.python indent=4}
def text(self, node):
    # ...
    weight = node.style["font-weight"]
    style = node.style["font-style"]
    if style == "normal": style = "roman"
    size = float(node.style["font-size"][:-2]) * .75
    font = tkinter.font.Font(size=style, weight=weight, slant=style)
    # ...
```

Note that for `font-style` we need to translate CSS "normal" to Tk
"roman". Likewise, the `font-size` value is in pixels, but Tk uses
points, so you have to multiply by 75% to convert.[^72ppi]

[^72ppi]: Normally you think of points as a physical length unit (one 72^nd^ of
an inch) and pixels as a digital unit (dependent on the screen) but in CSS, the
conversion is fixed at exactly 75% (or 96 pixels per inch) because that was once
a common screen resolution. This might seem weird, but [OS internals][why-72]
are equally bizarre, let alone the fact that a traditional typesetters' point is
[one 72.27^th^ of an inch][why-7227].

[why-72]: https://tonsky.me/blog/font-size/
[why-7227]: https://tex.stackexchange.com/questions/200934/why-does-a-tex-point-differ-from-a-desktop-publishing-point

Text color is similar, but it requires a bit more plumbing. First, we
have to read the color and store it in the current `line`:

``` {.python indent=4}
def text(self, node):
    color = node.style["color"]
    # ...
    for word in node.text.split():
        # ...
        self.line.append((self.cursor_x, word, font, color))
        # ...
```

Since the `line` field now stores color, we need to modify `flush`,
which reads that variable:

``` {.python indent=4}
def flush(self):
    if not self.line: return
    metrics = [font.metrics() for x, word, font, color in self.line]
    # ...
    for x, word, font, color in self.line:
        # ...
        self.display_list.append((x, y, word, font, color))
    # ...
```

Finally, that `display_list` is written in `paint`:

``` {.python indent=4}
def paint(self, display_list):
    # ...
    for x, y, word, font, color in self.display_list:
        display_list.append(DrawText(x, y, word, font, color))
```

Now `DrawText` needs to store the `color` argument and pass it to
`create_text`'s `fill` parameter:

``` {.python}
class DrawText:
    def __init__(self, x1, y1, text, font, color):
        # ...
        self.color = color

    def execute(self, scroll, canvas):
        canvas.create_text(
            # ...
            color=self.color,
        )
```

Phew! That was a lot of coordinated changes, so please test everything
and make sure it works. You should now see links on this page appear
in blue---and you'll also notice that the rest of the text has become
slightly lighter.[^book-css]

[^book-css]: Check out [the book's style sheet](book.css) to see the
    details.

Now we can add a few more lines to the browser style sheet:

``` {.css}
a { color: blue; }
i { font-style: italic; }
b { font-weight: bold; }
small { font-size: 110%; }
big { font-size: 90%; }
```

That fully replaces all the code in `InlineLayout` that handles those
tags, including the `style`, `weight`, and `size` properties and the
`open_tag` and `close_tag` methods. Let's refactor a bit to get rid of
them:

``` {.python indent=4}
def recurse(self, node):
    if isinstance(node, Text):
        self.text(node)
    else:
        if self.tag == "br":
            self.flush()
        for child in node.children:
            self.recurse(child)
```

So these styling mechanisms we've implemented not only let web page
authors style their own web pages---they also replace browser code
with a simple style sheet. And that's a big improvement: the style
sheet is independent of the rest of the code and easier to edit. And
while sometimes converting code to data means maintaining a new
format, here we get to reuse a format, CSS, that our browser needs to
support anyway.

Summary
=======

This chapter implemented a rudimentary but complete styling engine,
including downloading, parsing, matching, sorting, and applying CSS
files. That means we:

- Added styling support in both `style` attributes and `link`ed CSS files;
- Refactored `InlineLayout` to move the font properties to CSS;
- Removed most tag-specific reasoning from our layout code.

Our styling engine is also relatively easy to extend with properties
and selectors.

Outline
=======

The complete set of functions, classes, and methods in our browser 
should now look something like this:

::: {.cmd .python .outline html=True}
    python3 infra/outlines.py --html src/lab6.py
:::

Exercises
=========

*Fonts*: Implement the `font-family` property, an inheritable
property that names which font should be used in an element. Make
`code` fonts use some nice monospaced font like `Courier`.

*Width/Height*: Add support to block layout objects for the `width`
and `height` properties. These can either be a pixel value, which
directly sets the width or height of the layout object, or the word
`auto`, in which case the existing layout algorithm is used.

*Class Selectors*: Any HTML element can have a `class` attribute,
whose value is a space-separated list of tags that apply to that
element. A CSS class selector, like `.main`, affects all elements
tagged `main`. Implement class selectors; give them priority 10.
If you've implemented them correctly, you should see code blocks in
this book being syntax-highlighted.

*Display*: Right now, the `layout_mode` function relies on a
hard-coded list of block elements. In a real browser, the `display`
property controls this. Implement `display` with a default value of
`inline`, and move the list of block elements to the browser style
sheet.

*Shorthand Properties*: CSS "shorthand properties" set multiple
related CSS properties at the same time; for example, `font: italic
bold 100% Times` sets the `font-style`, `font-weight`, `font-size`,
and `font-family` properties all at once. Add shorthand properties to
your parser. (If you haven't implemented `font-family`, just ignore
that part.)

*Fast Descendant Selectors*: Right now, matching a selector like `div
div div div div` can take a long time---it's *O(nd)* in the worst
case, where *n* is the length of the selector and *d* is the depth of
the layout tree. Modify the descendant-selector matching code to run
in *O(n)* time. It may help to have `DescendantSelector` store a list
of base selectors instead of just two.

*Selector Sequences*: Sometimes you want to select an element by tag *and*
class. You do this by concatenating the selectors without anything in
between.[^no-ws] For example, `span.announce` selects elements that match both
`span` and `.announce`. Implement a new `SelectorSequence` class to represent
these and modify the parser to parse them. Sum priorities.[^lexicographic]

[^no-ws]: Not even whitespace!

[^lexicographic]: Priorities for `SelectorSequence`s are supposed to
    compare the number of ID, class, and tag selectors in
    lexicographic order, but summing the priorities of the selectors
    in the sequence will work fine as long as no one strings more than
    16 selectors together.

*Important*: a CSS property-value pair can be marked "important" using
the `!important` syntax, like this:

    #banner a { color: black !important; }

This gives that property-value pair (but not other pairs in the same block!) a
higher priority than any other selector (except for other `!important`
selector). Parse and implement `!important`, giving any property-value pairs
marked this way a priority 10000 higher than normal property-value pairs.

*Ancestor Selectors*: An ancestor selector is the inverse of a
descendant selector---it styles an ancestor according to the presence
of a descendant. This feature is one of the benefits provided by the
[`:has` syntax](https://drafts.csswg.org/selectors-4/#relational). Try
to implement ancestor selectors. As I write this, no browser has
actually implemented `:has`; why do you think that is? Hint: analyze
the asymptotic speed of your implementation. There is a clever
implementation that is *O(1)* amortized per element---can you find
it?^[No, this clever implementation is still not fast enough for real
browsers to implement.]
