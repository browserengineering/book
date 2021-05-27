---
title: Applying User Styles
chapter: 6
prev: layout
next: chrome
...

So far, the appearance of each HTML element has been hard-coded into
our browser. But web pages should be able to override our style
decisions and take on a unique character. This is done via _Cascading
Style Sheets_, a simple styling language for web authors (and, as
we'll see, browser developers) to define how a web page ought to look.

The style attribute
===================

In the [last chapter](layout.md), we gave each `pre` element a gray
background. It looks OK, and it *is* good to have some defaults, but
you can imagine a site wanting to have some say in how it looks.

The simplest mechanism for that is the `style` attribute on elements.
It looks like this:

``` {.example}
<div style="background-color:lightblue"></div>
```

This `<div>` element has its `style` attribute set. That attribute
contains set of property/value pairs, in this case one pair with the
property `background-color` and the value `lightblue`.^[CSS allows
spaces around the punctuation, but our simplistic attribute parser
does not support that.] The browser looks at those property-value
pairs when drawing elements, so this `style` attribute allows web page
authors to override the default background for `pre` elements.

Let's implement that in our browser. We'll start wtih a recursive
function to traverse all the elements and create a `style` field to
store this style information:

``` {.python replace=(node)/(node%2C%20rules)}
def style(node):
    node.style = {}
    # ...
    for child in node.children:
        style(child, rules)
```

Then the `style` dictionary can be filled in by parsing the element's
`style` attribute into property/value pairs[^python-get].

[^python-get]: The `get` method for dictionaries gets a value out of a
    dictionary, or uses a default value if it's not present.
    
``` {.python replace=(node)/(node%2C%20rules)}
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

Put the exact same lines of code inside `InlineLayout` as well, so that
paragraphs and list items and so on can have backgrounds as well. For now, also
remove the default gray background from `pre` elements, but we'll put it back
soon.

Open up this web page in your browser; the code block right after this
paragraph should have a light blue background now:

``` {.example style=background-color:lightblue}
<div style="background-color:lightblue"> ... </div>
```

So this is one simple mechanism for web pages to change their appearance. But
honestly it's a pain---you need to set a `style` attribute on each element, and
if you decide to change the style that's a lot of attributes to edit. In the
early days of the web,^[I'm talking Netscape 3. The late 90s.] the
element-by-element approach was all there was. CSS was invented to improve on
this state of affairs, with these goals:

- One CSS file can consistently style many web pages at once
- One line of CSS can consistently style many elements at once
- CSS is future-proof and supports browsers with different features

To achieve these goals, CSS extends the key-value `style` attribute with two
related ideas: *selectors* and *cascading*. In CSS, style information can apply
to multiple elements, across many pages, specified using a selector: a syntax
for matching one or more elements. A selector plus a set of
property-value pairs is called a *rule*:

``` {.css}
selector { property-1: value-1; property-2: value-2; }
```

Once one block can apply to many elements, the possibility exists for
several blocks apply to a single element. So browsers have a
*cascading* mechanism to resolve conflicts in favor of the most
specific rule. Cascading also means a browser can ignore rules it
doesn't understand---the cascade chooses the next-most-specific rule
that the browser understands.

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

Let's start with the parsing. I'll use recursive *parsing functions*,
where there's a function for each CSS construct like selectors,
blocks, and properties. Each parsing function advances a pointer into
the text it's parsing, then returns any data it parsed. We'll
have a lot of these functions, so let's organize them in a `CSSParser`
class containing the string `s` and index `i`:

``` {.python}
class CSSParser:
    def __init__(self, s):
        self.s = s
        self.i = 0
```

Let's start small and build up. A parsing function for whitespace
looks like this:

``` {.python}
def whitespace(self):
    while self.i < len(self.s) and self.s[self.i].isspace():
        self.i += 1
```

This parsing function increments the index `i` past every whitespace
character. Whitespace is insignificant, so there's no data to return.

Parsing functions can fail. For example, it's often helpful to check
that there's a certain piece of text at the current location (and not
return it, as it is purely syntatic):

``` {.python}
def literal(self, literal):
    assert self.s[self.i:self.i+len(literal)] == literal
    self.i += len(literal)
```

Here the check is done by `assert`, which raises an exception if the
condition is false.[^add-a-comma]

[^add-a-comma]: Add a comma after the condition, and you can add error
    text to the assertion. I recommend doing that for all of your
    assertions to help in debugging. I also recommend making generous
    use of assertions in general.

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
much like `whitespace`. But unlike `whitespace`, it also returns the
word as parsed data, and to do that it stores where it started and
extracts the substring it moved through. Also note the assert: if `i`
didn't advance though any word characters, that means `i` didn't point
at a word to begin with.

[^word-chars]: I've chosen the set of word characters here to cover
    property names (which use letters and dash), length units (which
    use the minus sign, numbers, periods, and the percent sign), and
    colors (which use the hash sign). Real CSS values are more complex.

Parsing functions can built upon one another. Property-value pairs,
for example, are a property, a colon, and a
value,[^technically-different] with whitespace in between:

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

This builds upon `word`, `whitespace`, and `literal` to build a more
complicated parsing function. And note that if `i` does not actually
point to a property-value pair, one of the `word` calls or the
`literal` call will fail.

Sometimes we need to call these parsing functions in a loop. For
example, a rule body is an open brace, a sequence of property-value
pairs, and a close brace:

``` {.python indent=4}
def body(self):
    pairs = {}
    self.literal("{")
    self.whitespace()
    while self.i < len(self.s) and self.s[self.i] != "}":
        prop, val = self.pair()
        pairs[prop] = val
        self.whitespace()
        self.literal(";")
        self.whitespace()
    self.literal("}")
    return pairs
```

Another twist to parsing functions is handling errors. So for example,
sometimes our parser will see a malformed property-value pair, either
because the page author made a mistake or because they're using a CSS
feature that our parser doesn't support. We can catch this error to
skip property-value pairs that don't parse. We'll use this little
function to skip things:

``` {.python indent=4}
def ignore_until(self, chars):
    while self.i < len(self.s):
        if self.s[self.i] in chars:
            return self.s[self.i]
        else:
            self.i += 1
```

Note that this stops at any one of a list of characters, and returns
that character (or `None` if it was stopped by the end of the file).

Now let's think back to parsing rule bodies. When we fail to parse a
property-value pair, we need to go to either the next property-value
pair (skip to a semicolon) or the end of the block (skip to a close
brace).

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
messages, so debugging CSS files becomes more difficult, and it also
makes it harder to debug your parser.[^try-no-try] This makes
"catch-all" error handling like this a code smell in most cases.

[^try-no-try]: I suggest removing the `try` block when debugging.

On the web, however, there is an unusual benefit: it supports an
ecosystem of multiple implementations. For example, different browsers
support different kinds of property values,[^like-parens] so CSS that
parses in one browser might not parse in another. With silent parse
errors, browsers just ignore stuff they don't understand. The
principle (variously called "Postel's Law",[^for-jon] the "Digital
Principle",[^from-circuits] or the "Robustness Principle") is: produce
maximally conformant output but accept even minimally conformant
input.

[^like-parens]: Our browser does not support parentheses in property
    values, for example, which real browsers use for things like the
    `calc` and `url` functions.
    
[^for-jon]: After a line in the specification of TCP, written by Jon
    Postel

[^from-circuits]: After a similar idea in circuit design, where
    transistors must be nonlinear to reduce analog noise.

Selectors
=========

We've built a parser, using parsing functions, for CSS blocks. But
that's just half of CSS; the other half is the selectors. Selectors
come in lots of types but our browser will support the two simplest:

- Tag selectors: `p` selects all `<p>` elements, `ul` selects all
  `<ul>` elements, and so on.
- Descendant selectors: `article div` selects all elements matching
  `div` that have an ancestor matching `article`.[^how-associate]

[^how-associate]: The descendant selector associates to the left; in
    other words, `a b c` means something like `(a b) c`, which is a
    `c` that descends from a `b` that descends from an `a`. CSS
    doesn't have parentheses, so the parentheses are always implicit.

We'll start by defining some data structures for selectors:

``` {.python}
class TagSelector:
    def __init__(self, tag):
        self.tag = tag

class DescendantSelector:
    def __init__(self, ancestor, descendant):
        self.ancestor = ancestor
        self.descendant = descendant
```

We now want a parsing function for selectors, which is another loop:

``` {.python indent=4}
def selector(self):
    out = TagSelector(self.word().lower())
    self.whitespace()
    while self.i < len(self.s) and self.s[self.i] != "{":
        descendant = TagSelector(self.word().lower())
        out = DescendantSelector(out, descendant)
        self.whitespace()
    return out
```

Using `word` for tag names is again not quite right, but it's close
enough. Note that tag names, in HTML, are case-insensitive.

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
            body = self.body()
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

Make sure to test your parser, like you did the [HTML parser](html.md)
two chapters back. There are a couple of errors you might run into:

- If the output is missing some rules or properties, it's probably a bug
  being covered up by the error handling. Remove some `try` blocks and see
  if the error in question can be fixed.
- If you're seeing extra rules or properties that looked like mangled
  versions of the correct ones, you probably forgot to update `i`
  somewhere.
- If you're seeing an infinite loop, check the error-handling code.
  Make sure each parsing function (except `whitespace`) always makes
  progress and increments `i`.

Also try adding a `print` statement to the start and end[^add-parens]
of each parsing function. Print the name of the parsing
function,[^add-spaces] the index `i`, and the parsed data. It's a lot
of output, but step through it by hand and you will find your mistake.

[^add-parens]: If you print an open parenthesis at the start of the
function and a close parenthesis at the end, you can use your editor's
"jump to other parenthesis" feature to skip through output quickly.

[^add-spaces]: If you also add the right number of spaces to each line
it'll be a lot easier to read. Don't neglect debugging niceties like
this!

Anyway, once you've got your parser debugged, let's move on to the
next step: applying CSS to the page.

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

``` {.python indent=8}
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
`font-size` (a length or percentage). The `font-weight` and
`font-style` properties are inherited, but `font-size` won't
be.[^font-size] That way we could add a few more lines to the browser
style sheet:

[^font-size]: Check out [the docs][mdn-font-size], and you'll see that
    actually, `font-size` is defined to inherit. But percentages
    inherit in a weird way (they are first resolved to absolute units,
    then inherited) which for simplicity I'd rather skip; if you
    *only* use percentages for fonts, and never absolute `em` units,
    you won't notice a difference, and our browser won't support `em`
    anyway.

[mdn-font-size]: https://developer.mozilla.org/en-US/docs/Web/CSS/font-size

``` {.css}
a { color: blue; }
i { font-style: italic; }
b { font-weight: bold; }
small { font-size: 110%; }
big { font-size: 90%; }
```

To inherit a property, we need to check, after all the rules and
inline styles have been applied, whether the property is set and, if
it isn't, to use the parent node's style. To begin with, let's list
our inherited properties and their default values:

``` {.python}
INHERITED_PROPERTIES = {
    "font-style": "normal",
    "font-weight": "normal",
    "color": "black",
}
```

Let's add inherited properties to the `style` function. This should go
*before* the other loops, since explicit rules override inheritance:

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

Because the recursive call comes at the end of `style`, the parent has
already inherited the correct property value when the children try to
read it.

With all this in place, we can implement text color itself. First,
let's add a `color` parameter to `DrawText` and pass it to
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

Now we need to pass in the color when we create a `DrawText` command.
But this is a little tricky: one paragraph can have text of different
colors in it! This is going to require a couple of tricky changes to
`InlineLayout` to make it work.

Inside `InlineLayout`, font information for every word is looked up in
the `text` method. That's where color information should be looked up
too---and for that we'll need to change `text` to take a `Text` input,
not just a string:

``` {.python indent=4}
def text(self, node):
    color = node.style["color"]
    # ...
    for word in node.text.split():
        # ...
        self.line.append((self.cursor_x, word, font, color))
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

Phew! That was a lot of coordinated changes, so please test everything
and make sure it works. You should now see links on this page appear
in blue---and you'll also notice that the rest of the text has become
slightly lighter.[^book-css]

[^book-css]: Check out [the book's style sheet](book.css) to see the
    details.

Font Properties
===============

Since we're already mucking around with `InlineLayout`, let's also
modify it to look up the font size, weight, and style information via
CSS instead of using the `style`, `weight`, and `size` fields on
`InlineLayout`.

For `style` and `weight`, this is straightforward:

``` {.python indent=4}
def text(self, node):
    # ...
    weight = node.style["font-weight"]
    style = node.style["font-style"]
    if style == "normal": style = "roman"
    # ...
```

Note that for `font-style` we need to translate CSS "normal" to Tk
"roman". Font size is a little more complex, however: if the font
size is given as a percentage, we need to multiply the percentage by
the parent's font size.

To implement this, let's add a `font_size` field to each HTML element
in the `style` function:

``` {.python}
def style(node, rules):
    # ...
    if isinstance(node, Text):
        node.font_size = node.parent.font_size
    elif node.style["font-size"].endswith("px"):
        node.font_size = float(node.style["font-size"][:-2])
    elif node.style["font-size"].endswith("%"):
        parent_font_size = node.parent.font_size if node.parent else 16
        pct = float(node.style["font-size"][:-1])
        node.font_size = pct / 100 * parent_font_size
    else:
        node.font_size = node.parent.font_size if node.parent else 16
    # ...
```

Note the fallback options: if you set a percentage size on the `html`
element, that percentage is calculated from the default 16-pixel text.

Anyways, `InlineLayout` can now use the `font_size` field to choose
the font for each word:

``` {.python indent=4}
def text(self, node):
    # ...
    size = node.font_size * .75
    font = tkinter.font.Font(size=style, weight=weight, slant=style)
    # ...
```

I multiply the font size by 75% before passing it to Tk to convert
from pixel values (which CSS uses) to point values (which Tk
uses).[^72ppi]

[^72ppi]: Normally you think of points as a physical length unit (one 72^nd^ of
an inch) and pixels as a digital unit (dependent on the screen) but in CSS, the
conversion is fixed at exactly 75% (or 96 pixels per inch) because that was once
a common screen resolution. This might seem weird, but [OS internals][why-72]
are equally bizarre, let alone the fact that a traditional typesetters' point is
[one 72.27^th^ of an inch][why-7227].

[why-72]: https://tonsky.me/blog/font-size/
[why-7227]: https://tex.stackexchange.com/questions/200934/why-does-a-tex-point-differ-from-a-desktop-publishing-point

It may seem a little confusing to have so many places where a font
size is stored: in the style sheet, inside the `style` field on the
element, in the element's `font_size` field, and then finally in this
local `size` variable. In CSS, these different versions are referred
to as [specified, computed, used, and actual values][css-computed],
and it affects all CSS properties, not just the `font-size`. It's an
important wrinkle left out of this book's browser.

[css-computed]: https://www.w3.org/TR/CSS2/cascade.html#value-stages

So, thanks to all these changes, we now never need to read the
`style`, `weight`, and `size` properties on `InlineLayout`, so we can
delete all the code that sets those properties in the `layout`,
`open_tag`, and `close_tag` methods. Once you do that, you'll notice
that `close_tag` is totally empty, while `open_tag` just has code to
handle `br` tags. Let's refactor a bit to get rid of these methods:

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

So we made `InlineLayout` more complex in some ways, less complex in
others. But more importantly: we replaced some browser implementation
code with a browser style sheet. And that's a big improvement: The style
sheet is easier to edit, since it's independent of the rest of the
code. And while sometimes converting code to data means maintaining a
new format, here we get to reuse a format, CSS, that our browser needs
to support anyway.

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
