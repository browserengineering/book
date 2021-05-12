---
title: Applying User Styles
chapter: 6
cur: styles
prev: layout
next: chrome
...

So far, the appearance of an HTML element has been hard-coded into our
browser. But web pages should be able to override our style decisions
and take on a unique character. This is done via _Cascading Style
Sheets_, a simple styling language for web authors (and, as we'll see,
browser developers) to define how a web page out to look.

The style attribute
===================

In the [last chapter](layout.md), we gave each `pre` element a gray
background. It looks OK, and it *is* good to have some defaults, but
you can imagine a site wanting to have some say in how it looks.

The simplest mechanism for that is the `style` attribute on elements.
It looks like this:

``` {.example}
<div style="background-color:lightblue;"></div>
```

This is a `<div>` element with its `style` attribute set. That
attribute contains set of property/value pairs, in this case one pair
matching the property `background-color` to the value
`lightblue`.^[CSS allows spaces around the punctuation, but our
attribute parser does not support it.] Our browser should look at those
property-value pairs when drawing elements to allow web page authors
to override defaults like the gray background for `pre` elements.

To keep this style data easily accessible, let's parse it and store it
in a `style` field on each `ElementNode`:

``` {.python}
class Element:
    def __init__(self, tag, attributes, parent):
        # ...
        self.style = {}
        for pair in attributes.get("style", "").split(";"):
            if ":" not in pair: continue
            prop, val = pair.split(":")
            self.style[prop.strip().lower()] = val.strip()
```

[^python-get]: The `get` method for dictionaries gets a value out of a
    dictionary, or uses a default value if it's not present.

Here we're adding the `style` field in the `ElementNode` constructor,
based on the `style` attribute,[^python-get] and filling it by parsing
that attribute's value. Now we can use that information when we do
layout:

``` {.python style=background-color:white;}
class BlockLayout:
    def draw(self, display_list):
        bgcolor = self.node.style.get("background-color", "transparent")
        if bgcolor != "transparent":
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, bgcolor)
            display_list.append(rect)
        # ...
```

You can put exact same lines of code inside `InlineLayout` as well,
for giving paragraphs and list items and so on backgrounds as well.
Open up this web page in your browser; you should see that this code
block, unlike the others, has a white background.

So this works, and lets web pages define their appearance. But
honestly it's a bit of a pain---you need to set a `style` attribute on
each element, and if you decide to change the style there's a lot of
attributes to edit. In the early days of the web,^[I'm talking
Netscape 3. The late 90s.] the element-by-element approach was all
there was. CSS was invented to improve on this state of affairs:

- One CSS file can consistently style many web pages at once
- One line of CSS can consistently style many elements at once
- CSS is future-proof and supports browsers with different features

To achieve these goals, CSS extends the key-value `style` attribute
with two connected ideas: *selectors* and *cascading*. In CSS, a block
of style information can apply to multiple elements, across many pages,
consistently. Those elements are specified using a selector:

``` {.css}
selector { property-1: value-1; property-2: value-2; }
```

Once one block can apply to many elements, the possibility exists for
several blocks apply to a single element. So browsers have a
*cascading* mechanism to resolve conflicts in favor of the most
specific rule. Cascading also means browsers can ignore rules they
don't understand---the cascade will apply the next-most-specific rule
that it understands.

Let's add support for CSS to our browser. We'll need to parse CSS
files into selectors, blocks, property-values pairs; to figure out
which elements on the page match each selector; and then add the
block's property values to those elements' `style` fields.

::: {.further}
Actually, before CSS, you'd style pages with custom elements like
[`font`][font-elt] and [`center`][center-elt]. This was easy to
implement (we did it!) but hard to use consistently. There were also a
few properties on `<body>` like [`text` and `vlink`][body-attrs] that
could consistently set text colors, but only for links.
:::

[font-elt]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/font
[center-elt]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/center
[body-attrs]: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/body#attributes

Parsing with functions
======================

Let's start with the parsing. I'll use recursive *parsing functions*,
where there's a function for each CSS construct like selectors,
blocks, and properties. Each parsing function take an index into the
input and return a new index, plus the data it parsed. We'll have a
lot of these functions, so let's organize them in a `CSSParser` class:

``` {.python}
class CSSParser:
    def __init__(self, s):
        self.s = s
```

The class wraps the string we're parsing. Parsing functions access the
string through `self.s`. Let's start small and build up. A parsing
function for whitespace would look like this:

``` {.python}
def whitespace(self, i):
    while i < len(self.s) and self.s[i].isspace():
        i += 1
    return None, i
```

This parsing function takes index `i`, pointing to the part of the
string we are currently parsing, and increments it through every
whitespace character. It then returns the new value of `i` that points
to a non-whitespace character. Whitespace is insignificant, so it
returns `None` for the parsed data.

Parsing functions can also fail. For example, it's often helpful to
check that there's a certain piece of text at the current location:

``` {.python}
def literal(self, i, literal):
    assert self.s[i:i+len(literal)] == literal
    return None, i + len(literal)
```

Here the check is done by `assert`, which raises an exception if the
condition is false.[^add-a-comma]

[^add-a-comma]: Add a comma after the condition, and you can add some
    error text to the assertion. I recommend doing that for all of
    your assertions to help in debugging.

Parsing functions can also return data. For example, to parse CSS
properties and values, we'll use this code:

``` {.python}
def word(self, i):
    start = i
    while i < len(self.s) and self.s[i].isalnum() or self.s[i] in "#-.":
        i += 1
    assert i > start
    return self.s[start:i], i
```

This function takes index `i` pointing to the start of the value and
increments it through any word characters,[^word-chars] much like
`literal`. But unlike `literal`, it also returns the word as parsed
data, and to do that it stores where it started and extracts the
substring it moved through. Also note the check: if `i` didn't
advance, that means `i` didn't point at a word to begin with.

[^word-chars]: I've chosen the set of word characters here to cover
    property names (which use letters and dash), length units (which
    use the minus sign, numbers, and periods), and colors (which use
    the hash sign). But the real CSS syntax is more complex.

Parsing functions can build upon one another. Property-value pairs,
for example, are a property, a colon, and
value,[^technically-different] with whitespace in between:

[^technically-different]: In reality properties and values have
    different syntaxes, so using `word` for both isn't quite right,
    but for our browser's limited CSS support this simplification will
    be alright.

``` {.python}
def pair(self, i):
    prop, i = self.word(i)
    _, i = self.whitespace(i)
    _, i = self.literal(i, ":")
    _, i = self.whitespace(i)
    val, i = self.word(i)
    return (prop.lower(), val), i
```

This builds upon `word`, `whitespace`, and `literal` to build a more
complicated parsing function. And note that if `i` does not actually
point to a property-value pair, one of the `word` calls or the
`literal` call will fail.

Sometimes we need to call these parsing functions in a loop. For
example, a rule body is an open brace, a sequence of property-value
pairs, and a close brace:

``` {.python indent=4}
def body(self, i):
    pairs = {}
    _, i = self.literal(i, "{")
    _, i = self.whitespace(i)
    while i < len(self.s) and self.s[i] != "}":
        (prop, val), i = self.pair(i)
        pairs[prop] = val
        _, i = self.whitespace(i)
        _, i = self.literal(i, ";")
        _, i = self.whitespace(i)
    _, i = self.literal(i, "}")
    return pairs, i
```

Another twist to parsing functions is handling errors. So for example,
sometimes our parser will see a malformed property-value pair, either
because the page author made a mistake or because they're using a CSS
feature that our parser doesn't support. We can catch this error to
skip property-value pairs that don't parse. We'll use this little
function to skips things:

``` {.python indent=4}
def ignore_until(self, i, chars):
    while i < len(self.s):
        if self.s[i] in chars:
            return self.s[i], i
        else:
            i += 1
    return None, i
```

Note that this stops at any one of a list of characters, and returns
that character (or `None` if it was stopped by the end of the file).
That's because when we fail to parse a property-value pair, we need to
go to either the next property-value pair (skip to a semicolon) or to
the end of the block (skip to a close brace).

``` {.python indent=4}
def body(self, i):
    # ...
    while i < len(self.s) and self.s[i] != "}":
        try:
            # ...
        except AssertionError:
            why, i = self.ignore_until(i, [";", "}"])
            if why == ";":
                _, i = self.literal(i, ";")
                _, i = self.whitespace(i)
            else:
                break
    # ...
```

Skipping parse errors is a double-edged sword. It hides error
messages, so debugging CSS files becomes more difficult, and it also
makes it harder to debug your parser.[^try-no-try] This makes
"catch-all" error handling like this a code smell in most cases.

[^try-no-try]: Try removing the `try` block when debugging.

However, on the web there is an unusual benefit: it supports an
ecosystem of multiple implementations. For example, different browsers
may support different syntaxes for property values.[^like-parens]
Thanks to silent parse errors, web pages can use features that only
some browsers support, with other browsers just ignoring it. This
principle variously called "Postel's Law",[^for-jon] the "Digital
Principle",[^from-circuits] or the "Robustness Principle": produce
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
come in multiple types; for now, our browser will support three:

- Tag selectors: `p` selects all `<p>` elements, `ul` selects all
  `<ul>` elements, and so on.
- ID selectors: `#main` selects the element with an `id` attribute 
  set to `main`.
- Descendant selectors: `#main div` selects all elements matching
  `div` that have an ancestor matching `#main`.

We'll start by defining some data structures for selectors:

``` {.python}
class TagSelector:
    def __init__(self, tag):
        self.tag = tag

class IdSelector:
    def __init__(self, id):
        self.id = id

class DescendantSelector:
    def __init__(self, ancestor, descendant):
        self.ancestor = ancestor
        self.descendant = descendant
```

We now want a parsing function for selectors. In fact, we'll have two:
one selector function for tag and ID selectors ("base selectors") and
another for descendant selectors, which can chain[^how-associate]. Tag
and ID selectors are pretty simple:

[^how-associate]: The descendant selector associates to the left; in
    other words, `a b c` means something like `(a b) c`, which is a
    `c` that descends from a `b` that descends from an `a`. CSS
    doesn't have parentheses, so the parentheses are always implicit.

``` {.python indent=4}
def base_selector(self, i):
    assert i < len(self.s)
    if self.s[i] == "#":
        _, i = self.literal(i, "#")
        name, i = self.word(i)
        return IdSelector(name), i
    else:
        name, i = self.word(i)
        return TagSelector(name.lower()), i
```

Using `word` for tag and ID names isn't quite right, but at least I'm
being careful to treat tag names case-insensitively. These base
selectors can then be strung together into descendant selectors:

``` {.python indent=4}
def selector(self, i):
    out, i = self.base_selector(i)
    _, i = self.whitespace(i)
    while i < len(self.s) and self.s[i] != "{":
        descendent, i = self.base_selector(i)
        out = DescendantSelector(out, descendant)
        _, i = self.whitespace(i)
    return out, i
```

We can now combine the selector and block parsers into a single parser
for CSS files. If a selector fails to parse, this combined parser
skips both it and the associated block:

``` {.python indent=4}
def file(self, i):
    rules = []
    _, i = self.whitespace(i)
    while i < len(self.s):
        try:
            selector, i = self.selector(i)
            _, i = self.whitespace(i)
            body, i = self.body(i)
            rules.append((selector, body))
        except AssertionError:
            why, i = self.ignore_until(i, "}")
            if why == "}":
                _, i = self.literal(i, "}")
                _, i = self.whitespace(i)
            else:
                break
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
two chapters back. There are a couple of different kinds of errors you
might run into:

- If you aren't seeing some rules or properties you think should be
  there, it's probably an error covered up by the error handling.
  Remove some `try` blocks and see if the error in question can be
  fixed.
- If you're seeing extra rules or properties that looked like mangled
  versions of the correct ones, you probably forgot to update `i`
  somewhere.
- If you're seeing a tuple like `("background-color", 12)` where you
  expect to see just the string, you probably wrote `x = ...` instead
  of `x, i = ...` or some similar idiom.
- If you're seeing an infinite loop, check the error-handling code. In
  general, it's very important that each parsing function (except
  `whitespace`) always makes progress and increments `i`.

More broadly, the best way to debug a little bit is to add a line to
each parsing function to print the index at the beginning, and both
the index and the parsed value at the end. You'll get a lot of output,
but if you step through it by hand, you will find your mistake.

Also, if you add the right number of spaces to each line it'll be a
lot easier to read. Don't neglect these debugging tools. And if you
also add an open parenthesis to the print at the start and a close
parenthesis to the print at the end, you can use your editor's "jump
to other parenthesis" feature to go through the output quickly.

Anyway, once you've got your parser debugged, let's move on to the
next step: applying CSS to the elements on the page.

Selecting styled elements
=========================

Our next step, after parsing CSS, is to figure out which elements each
rule applies to. The easiest way to do that is to add a method to each
selector, which tells you if the selector matches an element. Here's
what it looks like for `TagSelector` and `IdSelector`:

``` {.python}
class TagSelector:
     def matches(self, node):
         return self.tag == node.tag

class IdSelector:
    def matches(self, node):
        return self.id == node.attributes.get("id")
```

Descendant selectors wrap other selectors, so their `match` method is
recursive:

``` {.python}
class DescendantSelector:
    def matches(self, node):
        if not self.descendant.matches(node): return False
        parent = node.parent
        while parent:
            if self.ancestor.matches(parent): return True
            parent = parent.parent
        return False
```

So we know which rules apply to an element, and now we need to add
those rules' property-value pairs to the element's `style`. The logic
is pretty simple:

-   Recurse over the tree of `ElementNode`s;
-   For each rule, check if the rule matches;
-   If it does, go through the property/value pairs and assign them.

Here's what the code would look like:

``` {.python replace=return/node.style%20=%20node.parent.style}
def style(node, rules):
    if isinstance(node, TextNode):
        return
    else:
        for selector, pairs in rules:
            if selector.matches(node):
                for property in pairs:
                    if property not in node.style:
                        node.style[property] = pairs[property]
        for child in node.children:
            style(child, rules)
```

Note that this code skips properties that already have a value. That's
because `style` attributes should take priority, and they're loaded in
first. But that also means that it matters what order you apply the
rules in.

What's the correct order? In CSS, it's called *cascade order*, and it
is based on the selector used by the rule. Tag selectors get the
lowest priority; class selectors one higher; and id selectors higher
still. Just like how the `style` attribute comes first, we need to
sort the rules in priority order, with higher-priority rules first.

So let's add a `priority` method to the selector classes that return
this priority. In this simplest implementation the exact numbers don't
matter if they sort right so let's assign tag selectors priority `1`
and ID selectors priority `100`, and have descendant selectors add the
priority of their two halves. This means `#a b` takes priority over
`#a` which takes priority over `b`.

``` {.python}
class TagSelector:
    def __init__(self, tag):
        # ...
        self.priority = 1
        
class IdSelector:
    def __init__(self, id):
        # ...
        self.priority = 100

class DescendantSelector:
    def __init__(self, ancestor, descendant):
        # ...
        self.priority = ancestor.priority + descendant + priority
```

Before we call `style` we need to put our rules in the right order;
that would look something like this:

``` {.python expected=False}
rules.sort(key=lambda x: x[0].priority)
rules.reverse()
```

Here the `sort` function is given an inline function as an argument.
That function takes a rule, extracts its selector, and returns its
priority; in other words we sort by selector priority. Note the
`reverse` call: we want higher-priority rules to come first.

In Python, the `sort` function is *stable*, which means that things
keep their relative order if possible. This means that in general, a
rule that comes later in the CSS file has higher priority, unless the
selectors used force something different. That's how real browsers do
it, too.

Downloading styles
==================

Browsers get CSS code from two sources. First, each browser ships with
a *browser style sheet*,[^technically-ua] which defines the default
styles for all sorts of elements; second, browsers download CSS code
from the web, as directed by web pages they browse to. Let's start
with the browser style sheet.

[^technically-ua]: Technically called a "user agent" style sheet,
    because the browser acts as an agent of the user.

Our browser's style sheet might look like this:

``` {.css}
pre { background-color: gray; }
```

Let's store that in a new file, `browser.css`, and have our browser
load and parse that file when it downloads a page:

``` {.python replace=browser.css/browser6.css}
class Browser:
    def load(self, url):
        headers, body = request(url)
        nodes = HTMLParser(body).parse()

        with open("browser.css") as f:
            rules = CSSParser(f.read()).parse()
```

Beyond the browser styles, our browser needs to find website-specific
CSS files, download them, and use them as well. Web pages name their
CSS files using the `link` element, which looks like this:

``` {.example}
<link rel="stylesheet" href="/main.css">
```

The `rel` attribute here tells that browser that this is a link to a
stylesheet. Browsers mostly don't care about any [other kinds of
links][link-types], but search engines do[^like-canonical], so `rel`
is mandatory. And the `href` attribute describes the CSS file's URL.

[link-types]: https://developer.mozilla.org/en-US/docs/Web/HTML/Link_types

[^like-canonical]: For example, `rel=canonical` names the "true name"
    of a page and is used by search engines to track pages that appear
    at multiple URLs.

We could definitely write a little recursive function to find ever
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
now we have all the stylesheet URLs. The browser is expected to make a
GET request to that location, parse the stylesheet, and use it to
style the page.

Note that stylesheet URLs we have are not full URLs; they are
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
        header, body = request(relative_url(link, url))
        rules.extend(CSSParser(body).parse())
```

Since the page's stylesheets come *after* browser style, user styles
take priority over the browser style sheet.^[They do that in real
browsers too, but real browsers accomplish this goal by fiddling with
priorities. Our browser style sheet only has tag selectors in it, so
just putting them first works well enough.] With the rules loaded, we
need only sort and apply them and then do layout:

``` {.python indent=4}
def load(self, url):
    # ...
    rules.sort(key=lambda x: x[0].priority())
    rules.reverse()
    style(nodes, rules)
    # ...
```

Now every element is styled and ready to be laid out and drawn to the
screen. Open this page up again, and you should see both gray
backgrounds on every code block (thanks to the browser style sheet)
and light-gold backgrounds on this book's mailing list signup form
(try the book's main page).

Inherited styles
================

Alright: we've got background colors that can be configured by web
page authors. But there's more to web design than that! At the very
least, if you're changing background colors you might want to change
foreground colors as well---the CSS `color` property. But there's a
catch: color is mostly concerned with text, but text nodes don't have
any styles at all. How can that work?

The solution in CSS is *inheritance*. Inheritance means that if some
node doesn't have a value for a certain property, it uses its parent's
value instead. Some properties are inherited and some aren't; it
depends on the property. Background color isn't inherited, but text
color and other font properties are.

So let's implement text color and inheritance. And while we're at it,
let's also implement three other font properties: `font-weight`
(`normal` or `bold`), `font-style` (`normal` or `italic`), and
`font-size` (a percentage). The `font-weight` and `font-style`
properties are inherited, but `font-size` won't be.[^font-size] That
way we could add a few more lines to the browser style sheet:

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

Now let's add another loop to `style`, *after* the handling of rules
but *before* the recursive calls, to inherit properties:

``` {.python}
def style(node, rules):
    if isinstance(node, TextNode):
        node.style = node.parent.style
    else:
        # ...
        for property, default in INHERITED_PROPERTIES.items():
            if property not in node.style:
                if node.parent:
                    node.style[property] = node.parent.style[property]
                else:
                    node.style[property] = default
        # ...
```

Because this loop comes *before* the recursive call, the parent has
already inherited the correct property value when the children try to
read it.

On `TextNode` objects we can do an even simpler trick, since a text
node never has styles of its own and only inherits from its parent:

``` {.python}
def style(node, rules):
    if isinstance(node, TextNode):
        node.style = node.parent.style
    else:
        # ...
```

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

Finally, that `display_list` is read in `draw`:

``` {.python indent=4}
def draw(self, display_list):
    # ...
    for x, y, word, font, color in self.display_list:
        display_list.append(DrawText(x, y, word, font, color))
```

Phew! That was a lot of coordinated changes, so please test everything
and make sure it works. You should now see links on this page appear
in blue---and you'll also notice that the rest of the text has become
slightly lighter.^[Check out [the book's stylesheet](book.css) to see
the details.]

Well---since we're already mucking around with `InlineLayout`, let's
also modify it to look up the font size, weight, and style information
via CSS instead of using the `style`, `weigth`, and `size` fields on
`InlineLayout`:

::: {.todo}
How do we resolve percentage values for nodes? And the `font-size`
needs to be converted from pixels to points.[^72ppi]

[^72ppi]: Normally you think of points as a physical length unit (one
    72^nd^ of an inch) and pixels as a digital unit (dependent on the
    screen) but in CSS, the conversion is fixed at exactly 75% (or 96
    pixels per inch) because that was once a common screen resolution.
:::

``` {.python indent=4}
def text(self, node):
    # ...
    weight = node.style["font-weight"]
    style = node.style["font-style"]
    if style == "normal": style = "roman"
    size = node.style["font-size"] * .75 # ???
    font = tkinter.font.Font(size=style, weight=weight, slant=style)
    # ...
```

Note that for `font-style` we needs to translate CSS "normal" to Tk
"roman". Thanks to these changes, we now never need to read the
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
code with browser stylesheet. And that's a big improvement: The style
sheet is easier to edit, since it's independent of the rest of the
code. And while sometimes converting code to data means maintaining a
new format, here we get to reuse a format, CSS, that our browser needs
to support anyway.

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

Outline
=======

The complete set of functions, classes, and methods in our browser 
should look something like this:

::: {.cmd .python .outline html=True}
    python3 outlines.py --html src/lab6.py
:::

Exercises
=========

*Fonts*: Implement the `font-family` property, and inheritable
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

*Fast Descendants*: Right now, matching a selector like `div div div
div div` against a `div` element with only three `div` ancestors takes
a long time---more precisely, it's *O(n^2^)* in the length of the
selector. Modify the descendant-selector matching code to run in
*O(n)* time. It may help to have `DescendantSelector` store a list of
base selectors instead of just two.

*Selector Sequences*: Sometimes you want to select an element by tag
*and* class. You do this by concatenating the selectors without
anything in between:[^no-ws] `span.announce` selects elements that
match both `span` and `.announce`. Implement a new `SelectorSequence`
class to represent these and modify the parser to parse them. Sum
priorities.[^lexicographic]

[^no-ws]: Not even whitespace!

[^lexicographic]: Priorities for `SelectorSequence`s are supposed to
    compare the number of ID, class, and tag selectors in
    lexicographic order, but summing the priorities of the selectors
    in the sequence will work fine as long as no one strings more than
    16 selectors together.

*Ancestor Selectors*: an ancestor selector is the inverse of a
descendant selector - it styles an ancestor according to the presence
of a descendant. This feature is one of the benefits provided by the
[`:has` syntax](https://drafts.csswg.org/selectors-4/#relational). Try
to implement ancestor selectors. As I write this, no browser has
actually implemented `:has`; why? Hint: analyze the asymptotic speed
of your implementation. There is a clever implementation that is
*O(1)* amortized per element---can you find it?
