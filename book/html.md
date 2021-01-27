---
title: Constructing a Document Tree
chapter: 4
cur: html
prev: text
next: layout
...

So far, your web browser sees web pages as a stream of open tags,
close tags, and text. But HTML is actually a tree, and though the tree
structure hasn't been important yet, you'll need it to draw
backgrounds, add margins, and implement CSS. So this chapter adds a
proper HTML parser and converts the layout engine to use it.


A tree of nodes
===============

Right now, the browser sees web pages as a flat sequence of tags and
text, which is why the `Layout` object's `token` method includes code
for both open and close tags. But HTML is a tree, and each open and
close tag pair are one node in the tree, as is each text token.[^1] We
need tokens to evolve into nodes.

[^1]: In reality there are other types of nodes too, like comments,
    doctypes, and `CDATA` sections, and processing instructions. There
    are even some deprecated types!

To make tokens into a tree, we need to add a list of children and a
parent pointer to each. For `Text` nodes that looks like this:

``` {.python}
class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent
```

We'll do the same for `Tag`. Since it takes two tags (the open and the
close tag) to make a node, let's rename the `Tag` class to `Element`:

``` {.python}
class Element:
    def __init__(self, tag, parent):
        self.tag = tag
        self.children = []
        self.parent = parent
```

Constructing a tree of nodes from source code is called parsing, and
it's a little more complex than `lex`, so we're going to want to break
the process into several functions. To store the tree, and to keep all
those functions organized, let's create a new `HTMLParser` class.

How should the parser store the tree? Specifically, a parser needs to
store an *incomplete* tree, since the tree is built bit by bit, one
element or text node at a time. For example, suppose our parser is
midway through an HTML file, having only read this bit so far:

    <html><head></head><body><h1>This is my webpage

The parser has seen five tags (and one text node), of which two are
"finished"---the parser has seen both the start and end tag for the
`<head>` element---but the others are unfinished---the parser has only
seen the open tag. And because the parser reads the HTML file from
left to right, the unfinished tags are always *open* tags, always the
*rightmost child* of their parent that the parser has currently seen,
and always *children of other unfinished tags*.

These facts representing an incomplete tree by storing a list of
unfinished tags, ordered with parents before children. Let's store
this list in a new `unfinished` field:

``` {.python}
class HTMLParser:
    def __init__(self, body):
        self.body = body
        self.unfinished = []
```

The first node in the list is the root of the HTML tree; the last
node in the list is the most recent unfinished tag. 

Constructing the tree
=====================

Let's start our parser with the `lex` function we have now, but
renamed (aspirationally) to `parse`:

``` {.python}
class HTMLParser:
    def __init__(self, body):
        self.body = body

    def parse(self):
        # ...
```

Of course just renaming the function doesn't make it output a tree of
nodes! So let's peek inside `parse`. Right now it creates `Tag` and
`Text` objects and appends them to an array it calls `out`. We need to
create `Element` and `Text` objects, and to add them somehow to a
tree. Since a tree is a bit more complex than a list, let's move the
adding-to-a-tree logic to two new functions: `add_text` and `add_tag`:

``` {.python}
def parse(self):
    text = ""
    in_tag = False
    for c in self.body:
        if c == "<":
            in_tag = True
            if text: self.add_text(text)
            text = ""
        elif c == ">":
            in_tag = False
            self.add_tag(text)
            text = ""
        else:
            text += c
    if not in_tag and text:
        self.add_text(text)
    return self.finish()
```

Note that the `out` variable is gone, and that I've also changed the
`return` statement to call a new `finish` method, which should convert
whatever incomplete tree we have to the final, complete tree.

To add a text node, which is never unfinished, we just add it to the
last node in the list:

``` {.python}
class HTMLParser:
    def add_text(self, text):
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)
```

On the other hand, tags are a little more complex since they might be
an open *or* a close tag:

``` {.python}
class HTMLParser:
    def add_tag(self, text):
        if text.startswith("/"):
            # ...
        else:
            # ...
```

A close tag finishes the last element of the `unfinished` list:

``` {.python}
def add_tag(self, text):
    if text.startswith("/"):
        node = self.unfinished.pop()
        parent = self.unfinished[-1]
        parent.children.append(node)
    # ...
```

An open tag instead adds a new unfinished tag:

``` {.python}
def add_tag(self, text):
    # ...
    else:
        parent = self.unfinished[-1]
        node = Element(text, parent)
        self.unfinished.append(node)
```

Then, once the parser is done, we can turn our incomplete tree into a
complete tree by just finishing any unfinished nodes:

``` {.python}
class HTMLParser:
    def finish(self):
        while self.unfinished:
            node = self.unfinished.pop()
            if not self.unfinished: return node
            parent = self.unfinished[-1]
            parent.children.append(node)
```

This is *almost* a complete parser, but it doesn't quite work at the
beginning and end of the document. First, the very first tag needs a
special case, since it doesn't have a parent:

``` {.python}
def add_tag(self, text):
    # ...
    else:
        parent = self.unfinished[-1] if self.unfinished else None
        # ...
```

And second, the very last tag needs a special case, since if we remove
*it* from the list of unfinished tags that list will be empty:

``` {.python}
def add_tag(self, text):
    if tag.startswith("/"):
        if len(self.unfinished) == 1: return
        # ...
```

With these tweaks, the parser will run. Let's test it out and see how
well it works.

::: {.further}
HTML derives from a long line of document processing systems. Its
predecessor, [SGML][sgml] traces back to [RUNOFF][runoff] and is a
sibling to [troff][troff], now used for Linux man pages. The
[committee][jtc1-sc34] that standardized SGML now works on the `.odf`,
`.docx`, and `.epub` formats.
:::

[sgml]: https://en.wikipedia.org/wiki/Standard_Generalized_Markup_Language
[runoff]: https://en.wikipedia.org/wiki/TYPSET_and_RUNOFF
[troff]: https://troff.org
[jtc1-sc34]: https://www.iso.org/committee/45374.html

Debugging a parser
==================

How do we know our parser does the right thing---that it builds the
right tree? Well the place to start is *seeing* the tree it produces.
We can do that with a quick, recursive pretty-printer:

``` {.python}
def print_tree(node, indent=0):
    print(" " * indent, elt)
    for child in elt.children:
        print_tree(child, indent + 2)
```

Here we're printing each node in the tree, and using indentation to
show the tree structure. Since we need to print each node, it's worth
taking the time to give them a nice printed form, which in Python
means defining the `__repr__` function:

``` {.python}
class Text:
    def __repr__(self):
        return repr(self.text)

class Element:
    def __repr__(self):
        return "<" + self.tag + ">"
```

Try this out on this web page, parsing the HTML source code and then
calling `print_tree` to visualize it:

``` {.python}
headers, body = request(sys.argv[1])
nodes = HTMLParser(body).parse()
print_tree(nodes)
```

Run it on this web page, and you'll see something like this:

``` {.example}
 <!DOCTYPE html >
   '\n'
   <html lang="en-US" xml:lang="en-US" >
     '\n'
     <head >
       '\n  '
       <meta charset="utf-8" / >
         '\n  '
         <meta name="generator" content="pandoc" / >
           '\n  '
```

Immediately a couple of things stand out. Let's start at the top, with the `<!DOCTYPE html>` tag.

This special tag is called a [doctype][html5-doctype] that's s always the very first thing in an HTML document. But it's not really an element at all, nor is it supposed to have close tag. Our toy browser won't be using the doctype for anything, so it's best to throw it away:[^quirks-mode]

[html5-doctype]: https://html.spec.whatwg.org/multipage/syntax.html#the-doctype

[^quirks-mode]: Real browsers use doctypes to switch between
    standards-compliant and legacy parsing and layout modes.

``` {.python}
def add_tag(self, text):
    if text.startswith("!"): return
    # ...
```

This ignores all tags that start with an exclamation mark, which not only throws out doctype declarations but also most comments, which in HTML are written `<!-- comment text -->`.

Just throwing out doctypes isn't quite enough though---if you run your parser now, it will crash. That's because after the doctype comes a newline, which our parser treats as text and tries to insert into the tree. Except there isn't a tree, since there haven't been any open tags. For simplicity, let's just have our browser skip whitespace-only text nodes to side-step the problem:[^ignore-them]

[^ignore-them]: Real browsers retain whitespace nodes: whitespace is
    significant inside `<pre>` tags or in cases like the difference
    between `make<span>up</span>` and `make <span>up</span>`. Our
    browser won't support that, and ignoring all whitespace tags
    simplifies [later chapters](layout.md) by avoiding a special-case
    for whitespace-only text tags.

``` {.python}
def add_text(self, text):
    if text.isspace(): return
    # ...
```

The parsed HTML tree now looks like this:

``` {.example}
<html lang="en-US" xml:lang="en-US" >
   <head >
     <meta charset="utf-8" / >
       <meta name="generator" content="pandoc" / >
         <meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=yes" / >
           <meta name="author" content="Pavel Panchekha &amp; Chris Harrelson" / >
             <link rel="stylesheet" href="book.css" / >
               <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Vollkorn%7CLora&display=swap" / >
                 <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Vollkorn:400i%7CLora:400i&display=swap" / >
                   <title >
```

Why's everything so deeply indented? Why aren't these open elements ever closed?

::: {.further}
SGML document type declarations had a URL to define the valid tags.
Browsers use the absense of a document type declaration to
[identify][quirks-mode] very old, pre-SGML versions of
HTML,[^almost-standards-mode] but don't need the URL, so `<!doctype
html>` is the best document type declaration today.
:::

[quirks-mode]: https://developer.mozilla.org/en-US/docs/Web/HTML/Quirks_Mode_and_Standards_Mode

[^almost-standards-mode]: There's also a crazy thing called "[almost
    standards][limited-quirks]" or "limited quirks" mode, due to a
    backwards-incompatible change in table cell vertical layout. Yes.
    I don't need to make these up!

[limited-quirks]: https://hsivonen.fi/doctype/

Self-closing tags
=================

Elements like `<meta>` and `<link>` are what are called self-closing: you don't
ever write `</meta>` or `</link>`, because these tags don't surround content. To get a reasonable-looking tree out of our parser, we'll need special support for them. In HTML, there's a [fixed list][html-void-elements] of these self-closing tags:[^void-elements]

[html5-void-elements]: https://html.spec.whatwg.org/multipage/syntax.html#void-elements

[^void-elements]: A lot of these tags are obscure or obsolete, but
    it's nice that there's a complete list.

``` {.python}
SELF_CLOSING_TAGS = [
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
]
```

When our parser sees a tag from this list, it needs to treat it like a finished tag:

``` {.python}
def add_tag(self, text):
    # ...
    elif text in self.SELF_CLOSING_TAGS:
        parent = self.unfinished[-1]
        node = Element(text, parent)
        parent.children.append(node)
```

This code looks right, but if you test it out it won't seem to help. Why not? Because our parser doesn't yet understand attributes! It's looking for a tag named `meta`, but finding only a tag with the unweildy name

    meta name="generator" content="pandoc" /

We're going to need to add support for attributes if we want this parser to work right.

::: {.further}
Prior to the invention of CSS, some browsers supported web page
styling using attributes like `bgcolor` and `vlink` (the
color of visited links) and tags like `font`. These [are
obsolete][html5-obsolete], but browsers still support some of them.
:::

[html5-obsolete]: https://html.spec.whatwg.org/multipage/obsolete.html#obsolete

Attributes
==========

HTML attributes give
additional information about an element; an open tag can have any number
of attributes (though close tags can't have any). Attribute values can
be anything, and they can be written quoted, unquoted, or omitted entirely. Quoted attributes can even
contain whitespace. For simplicity, let's skip the case where attribute values contain whitespace, and extend our parser to understand attributes.

Since we're not handling attributes with whitespace, we can split the tag contents on whitespace to
get the tag name and the attribute-value pairs:

``` {.python}
def get_attributes(self, text):
    parts = text.split()
    tag = parts[0].lower()
    attributes = {}
    for attrpair in parts[1:]:
        # ...
    return tag, attributes
```

Note that the tag name is converted to lower case,[^case-fold] because
HTML tag names are case-insensitive. Now, inside the loop, we need to split each attribute-value pair into the attribute name and its value.

[^case-fold]: This is [not the right way][case-hard] to do case
    insensitive comparisons; the Unicode case folding algorithm should
    be used if you want to handle languages other than English. But in
    HTML specifically, tag names only use the ASCII characters where
    this test is sufficient.
    
[case-hard]: https://www.b-list.org/weblog/2018/nov/26/case/

The easiest case is an unquoted attribute, where an equal sign separates the attribute's name and value:

``` {.python}
def get_attribute(self, text):
    # ...
    for attrpair in parts[1:]
        key, value = attrpair.split("=", 1)
        self.attributes[key.lower()] = value
    # ...
```

But actually, not all attributes have a value: the value
can be omitted, like in `<input disabled>`, in which case, the
attribute value defaults to the empty string:

``` {.python indent=8}
for attrpair in parts[1:]:
    if "=" in attrpair:
        # ...
    else:
        self.attributes[attrpair.lower()] = ""
```

And finally, when there is a value, it might also be quoted, in which case the quotes have to be stripped out:

``` {.python indent=12}
if "=" in attrpair:
    if len(value) > 2 and value[0] in ["'", "\""]:
        value = value[1:-1]
    # ...
```

This conditional checks the first character of the value to determine
if it's quoted, and if so strips off the first and last character,
leaving the contents of the quotes.

Let's modify `Element` to store these attributes: 

``` {.python}
class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        # ...
```

This means we'll need to call `get_attribute` at the top of `add_tag`:

``` {.python indent=4}
def add_tag(self, text):
    tag, attributes = self.get_attributes(text)
```

and then use the extracted `tag` and `attribute` values instead of `text` in the rest of `add_tag`.

Try your parser again:

``` {.example}
<html lang="en-US" xml:lang="en-US">
   <head>
     <meta charset="utf-8" /="">
     <meta name="generator" content="pandoc" /="">
     <meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=yes" /="">
     <meta name="author" content="Pave" panchekha="" &amp;="" chris="" harrelson"="" /="">
     <link rel="stylesheet" href="book.css" /="">
     <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Vollkorn%7CLora&display=swap" /="">
     <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Vollkorn:400i%7CLora:400i&display=swap" /="">
     <title>
```

Yeah, it's a little funky: attributes with whitespace (like `author` on the fourth `meta` tag) end up mis-parsed as multiple attributes, and the final slash on self-closing tags is treated as an attribute as well. But let's hit pause of refining our parser for now---these issues aren't going to be a problem for the toy browser we're building---and move on to integrating it with our browser.

::: {.further}
Putting a slash at the end of self-closing tags, like `<br/>`,
became fashionable when [XHTML][xhtml] looked like it might replace
HTML, and old-timers like me never broke the habit. But unlike in [XML][xml-self-closing], in HTML self-closing tags
are identified by name, not by some special syntax.
:::

[xml-self-closing]: https://www.w3.org/TR/xml/#sec-starttags
[xhtml]: https://www.w3.org/TR/xhtml1/

Using the node tree
===================

Right now, the `Layout` class lays out the page token-by-token; we now want it to go node-by-node instead.

So let's sepate the old `token` method into three parts: all the cases for open tags will go into a new `open` method; all the cases for close tags will to into a new `close` method; and instead of having a case for text tokens our browser can just call the existing `text` method directly:

``` {.python}
class Layout:
    def open(self, tag):
        if tag == "i":
            self.style = "italic"
        # ...

    def close(self, tag):
        if tag == "i":
            self.style = "roman"
        # ...
```

Now we need the `Layout` object to walk the node tree, calling `open`, `close`, and `text` in the right order:

``` {.python indent=4 expected=False}
def recurse(self, tree):
    if isinstance(tree, TextNode):
        self.text(tree.text)
    else:
        self.open(tree.tag))
        for child in tree.children:
            self.recurse(child)
        self.close(tree.tag)
```

Make sure to update `recurse` to call these two new functions; now it
no longer has to construct `Tag` objects or add slashes to things to
indicate a close tag!

Update the browser entry point to use the node tree, and run it---you should see the browser again render web pages, this time with a proper understanding of the HTML tree.

::: {.further}
The ill-considered Javascript `document.write` method allows Javascript to modify the HTML source code while it's being parsed! Modern browsers use [speculative][speculative-parsing] parsing to avoid waiting on Javascript in the parser as long as that method isn't called.
:::

[seculative-parsing]: https://developer.mozilla.org/en-US/docs/Glossary/speculative_parsing

Handling author errors
======================

The parser now handles HTML pages correctly—at least, pages written by
the sorts of goody-two-shoes programmers who remember the HTML
boilerplate, close their open tags, and make their bed in the morning.
Since us mere mortals lack such discipline, browsers have to additionally
handle poorly-written, confusing, boilerplate-less HTML.

In fact, modern HTML parsers are capable of transforming *any* string
of characters into an HTML tree, no matter how confusing the markup.[^3]
The full algorithm is, as you might expect, complicated beyond belief,
with dozens of ever-more-special cases forming a taxonomy of human
error, but one of the nicer time-saving innovations is *implicit* tags.

[^3]: Yes, it's crazy, and for a few years in the early '00s the W3C
    tried to [do away with it](https://www.w3.org/TR/xhtml1/). They
    failed.

Normally, an HTML document starts with a familiar boilerplate:

``` {.html}
<!doctype html>
<html>
  <head>
  </head>
  <body>
  </body>
</html>
```

In reality, *all six* of these tags, except the doctype, are optional:
browsers insert them automatically. To do so, they compare the current
token's tag to the list of currently open elements; that reveals
whether any additional elements need to be created:

Let's add support for implicit tags to our browser via a new `implicit_tags` function that adds implicit tags when the web page omits them. We'll want to call it in both `add_text` and `add_tag`:

``` {.python indent=4}
class HTMLParser:
    def add_text(self, text):
        if text.isspace(): return
        self.implicit_tags(None)
        # ...

    def add_tag(self, text):
        tag, attributes = self.get_attributes(text)
        if tag.startswith("!"): return
        self.implicit_tags(tag)
        # ...
```

Note that the `implicit_tags` call comes after the lines that ignore whitespace and doctypes; this way those bits of the source code are truly ignored. The argument to `implicit_tags` is the tag name (or `None` for text nodes), which we'll compare to the list of unfinished tags to determine what's been omitted:

``` {.python}
class HTMLParser:
    def implicit_tags(self, tag):
        while True:
            open_tags = [node.tag for node in self.unfinished]
            # ...
```

`implicit_tags` has a loop because more than one tag could have been omitted in a row; every iteration around the loop will add just one. To determine which implicit tag to add, if any, requires examining the open tags and the tag being inserted.

Let's start with the easiest case, the implicit `<html>` tag. An implicit `<html>` tag is necessary if the first tag in the document is something other than `<html>`:

``` {.python indent=8}
while True:
    # ...
    if open_tags == [] and tag != "html":
        self.add_tag("html")
```

Both `<head>` and `<body>` can also be omitted, but to figure out which it is we need to look at which tag is being added:

``` {.python indent=8}
while True:
    # ...
    elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
        if tag in self.HEAD_TAGS:
            self.add_tag("head")
        else:
            self.add_tag("body")
```

Here `HEAD_TAGS` is just a list of all the tags that go into the `<head>` element by default:[^where-script]

[^where-script]: Note that some tags, like `<script>`, can go in
    either the head or body section of an HTML document. The code
    below places it inside a `<head>` tag by default, but doesn't
    prevent its being explicitly placed inside `<body>` by the page
    author.

``` {.python}
class HTMLParser:
    HEAD_TAGS = [
        "base", "basefont", "bgsound", "noscript",
        "link", "meta", "title", "style", "script",
    ]
```

Note that if both the `<html>` and `<head>` tags are omitted, `implicit_tags` is going to insert both of them by going around the loop twice. The first iteration add the `<html>` tag, and then in the second iteration `open_tags` is `["html"]` and a `<head>` tag is added.

Finally, the `</head>` tag can also be implicit, if the parser is inside the `<head>` and sees an element that's supposed to go in the `<body>`:

``` {.python indent=8}
while True:
    # ...
    elif open_tags == ["html", "head"] and tag not in ["/head"] + self.HEAD_TAGS:
        self.add_tag("/head")
```

In HTML the `</body>` and `</html>` tags can also be implicit. Luckily, our `finish` function already handles this case, closing any unfinished tags. So all that's left for `implicit` tags is to exit out of the loop:

``` {.python indent=8}
while True:
    # ...
    else:
        break
```

These rules for malformed HTML may seem arbitrary, and they are: they
evolved over years of trying to guess what people "meant" when they
wrote that HTML, and are now codified in the [HTML parsing
standard][html5-parsing]. Of course, sometimes these rules "guess" wrong---but as so often happens on the web, it's often more important that every browser does the *same* thing, rather than each trying to guess what the *right* thing is.

[html5-parsing]: https://html.spec.whatwg.org/multipage/parsing.html

::: {.further}
Thanks to implicit tags, you can often skip the `<html>`, `<body>`,
and `<head>` elements. They'll be implicitly added back for you.
Nor does writing them explicitly let you do anything weird; the HTML
parser's [many states][after-after-body] guarantee that there's only
one `<head>` and one `<body>`.[^except-templates]
:::

[^except-templates]: At least, per document. An HTML file that uses
    frames or templates can have more than one `<head>` and `<body>`,
    but they correspond to different documents.

[after-after-body]: https://html.spec.whatwg.org/multipage/parsing.html#parsing-main-afterbody

Summary
=======

This chapter taught our browser that HTML is a tree, not just a flat
list of tokens. We added:

- A parser to transform HTML tokens to a tree
- Layout operating recursively on the tree
- Code to recognize and handle attributes on elements
- Automatic fixes for some malformed HTML documents

The tree structure of HTML is essential to display visually complex
web pages, as we will see in the [next chapter](layout.md).

::: {.signup}
:::


Exercises
=========

*Comments:* Update the HTML lexer to support comments. Comments in
HTML begin with `<!--` and end with `-->`. However, comments aren't
the same as tags: they can contain any text, including left and right
angle brackets. The lexer should skip comments, not generating any
token at all. Test: is `<!-->` a comment, or does it just start one?

*Paragraphs:* Since it's not clear what it would mean for one
paragraph to contain another, the most common reason for this to
happen in a web page is that someone forgot a close tag. Change the
parser so that a document like `<p>hello<p>world</p>` results in two
sibling paragraphs instead of one paragraph inside another.

*Scripts:* JavaScript code embedded in a `<script>` tag uses the left
angle bracket to mean less-than. Modify your lexer so that the
contents of `<script>` tags are treated specially: no tags are allowed
inside `<script>`, except the `</script>` close tag.[^or-space]

[^or-space]: Technically it's just `</script` followed by a [space,
    tab, `\v`, `\r`, slash, or greater than sign][script-end-state].
    If you need to talk about `</script>` tags inside your JavaScript
    code, split it across multiple strings. I talk about it in a
    video.

[script-end-state]: https://html.spec.whatwg.org/multipage/parsing.html#script-data-end-tag-name-state

*Quoted attributes:* Quoted attributes can contain spaces and right
angle brackets. Fix the lexer so that this is supported properly.
Hint: the current lexer is a finite state machine, with two states
(determined by `in_tag`). You'll need more states.

*Syntax Highlighting:* Implement the `view-source:` protocol as in
[Chapter 1](http.md#exercises), but make it syntax-highlight the
source code of HTML pages. Keep source code for HTML tags in a normal
font, but make text contents bold. If you've implemented it, wrap text
in `<pre>` tags as well to preserve line breaks. Use your browser's
HTML lexer to implement the syntax highlighter.
