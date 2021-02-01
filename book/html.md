---
title: Constructing a Document Tree
chapter: 4
cur: html
prev: text
next: layout
...

So far, your web browser sees web pages as a stream of open tags,
close tags, and text. But HTML is actually a tree, and though the tree
structure hasn't been important yet, it will be once backgrounds,
margins, and CSS enter this picture. So this chapter adds a proper
HTML parser and converts the layout engine to use it.


A tree of nodes
===============

Right now, the browser sees web pages as a flat sequence of tags and
text, which is why the `Layout` object's `token` method includes code
for both open and close tags. But HTML is a tree, with one node for
each open and close tag pair and each span of text.[^1] Tokens need to
evolve into nodes.

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

``` {.python expected=False}
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

A parser builds a tree one element or text node at a time. But that
means the parser needs to store an *incomplete* tree. For example,
suppose the parser is has so far read this bit of HTML:

    <html><head></head><body><h1>This is my webpage

The parser has seen five tags (and one text node). The rest of the
HTML will contain more open tags, close tags, and text; but no matter
which tokens it sees, no new nodes will be added to the `<head>` tag,
which has already been closed. So that node is "finished". But the
other nodess are unfinished: more children can be added to the
`<html>`, `<body>`, and `<h1>` nodes. Since the parser reads the HTML
file from left to right, these unfinished tags have a certain
structure. The unfinished tags have always been *opened* but not yet
closed; they are always the *to the right* of the finished nodes; and
they are always *children of other unfinished tags*.

To leverage these facts, let's represent an incomplete tree by storing
a list of unfinished tags, ordered with parents before
children.[^touch-last] Let's store this list in a new `unfinished`
field:

[^touch-last]: In Python, and most other languages, it's faster to add
    and remove from the end of a list, instead of the beginning.

``` {.python}
class HTMLParser:
    def __init__(self, body):
        self.body = body
        self.unfinished = []
```

The first node in the list is the root of the HTML tree; the last node
in the list is the most recent unfinished tag. Before the parser
starts, it hasn't seen any tags at all, so the list is empty. But as
the parser reads tokens, that list fills up...

Constructing the tree
=====================

Let's start with the `lex` function we have now, but renamed,
aspirationally, to `parse`:

``` {.python}
class HTMLParser:
    def parse(self):
        # ...
```

Let's do a bit of surgery on `parse`. Right now `parse` creates `Tag`
and `Text` objects and appends them to the `out` array. We need it to
create `Element` and `Text` objects and add them to the `unfinished`
tree.

``` {.python indent=4}
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

A tree is a bit more complex than a list, so I moved the
adding-to-a-tree logic to `add_text` and `add_tag`. The `out` variable
is gone, and note that I've also moved the `return` statement to a new
`finish` method, which converts the incomplete tree to the final,
complete tree.

Let's start adding to the tree. To add a text node we add it as a
child of the last unfinished node:

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
    def add_tag(self, tag):
        if tag.startswith("/"):
            # ...
        else:
            # ...
```

A close tag removes the last element of `unfinished`, and adds to the
new last unfinished node:

``` {.python indent=4}
def add_tag(self, tag):
    if tag.startswith("/"):
        node = self.unfinished.pop()
        parent = self.unfinished[-1]
        parent.children.append(node)
    # ...
```

An open tag instead adds to `unfinished`:

``` {.python indent=4 expected=False}
def add_tag(self, tag):
    # ...
    else:
        parent = self.unfinished[-1]
        node = Element(tag, parent)
        self.unfinished.append(node)
```

Once the parser is done, it turns our incomplete tree into a complete
tree by just finishing any unfinished nodes:

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
beginning and end of the document. First, the very first tag is an
edge case that doesn't have a parent:

``` {.python}
def add_tag(self, tag):
    # ...
    else:
        parent = self.unfinished[-1] if self.unfinished else None
        # ...
```

And the very last tag is also an edge case, because there's no
unfinished node to add it to:

``` {.python indent=4}
def add_tag(self, tag):
    if tag.startswith("/"):
        if len(self.unfinished) == 1: return
        # ...
```

Ok, that's all done. Let's test out parser out and see how well it
works!

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
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)
```

Here we're printing each node in the tree, and using indentation to
show the tree structure. Since we need to print each node, it's worth
taking the time to give them a nice printed form, which in Python
means defining the `__repr__` function:

``` {.python expected=False}
class Text:
    def __repr__(self):
        return repr(self.text)

class Element:
    def __repr__(self):
        return "<" + self.tag + ">"
```

Try this out on this web page, parsing the HTML source code and then
calling `print_tree` to visualize it:

``` {.python expected=False}
headers, body = request(sys.argv[1])
nodes = HTMLParser(body).parse()
print_tree(nodes)
```

Run it on this web page, and you'll see something like this:

``` {.example}
 <!DOCTYPE html>
   '\n'
   <html lang="en-US" xml:lang="en-US">
     '\n'
     <head>
       '\n  '
       <meta charset="utf-8" />
         '\n  '
         <meta name="generator" content="pandoc" />
           '\n  '
```

Immediately a couple of things stand out. Let's start at the top, with
the `<!DOCTYPE html>` tag.

This special tag is called a [doctype][html5-doctype] that's always
the very first thing in an HTML document. But it's not really an
element at all, nor is it supposed to have a close tag. Our toy
browser won't be using the doctype for anything, so it's best to throw
it away:[^quirks-mode]

[html5-doctype]: https://html.spec.whatwg.org/multipage/syntax.html#the-doctype

[^quirks-mode]: Real browsers use doctypes to switch between
    standards-compliant and legacy parsing and layout modes.

``` {.python indent=4}
def add_tag(self, tag):
    if tag.startswith("!"): return
    # ...
```

This ignores all tags that start with an exclamation mark, which not
only throws out doctype declarations but also most comments, which in
HTML are written `<!-- comment text -->`.

Just throwing out doctypes isn't quite enough though---if you run your
parser now, it will crash. That's because after the doctype comes a
newline, which our parser treats as text and tries to insert into the
tree. Except there isn't a tree, since the parser hasn't seen any open
tags. For simplicity, let's just have our browser skip whitespace-only
text nodes to side-step the problem:[^ignore-them]

[^ignore-them]: Real browsers retain whitespace, to correctly render
    `make<span></span>up` as one word and `make<span> </span>up` as
    two. Our browser won't. Plus, ignoring whitespace simplifies
    [later chapters](layout.md) by avoiding a special-case for
    whitespace-only text tags.

``` {.python indent=4}
def add_text(self, text):
    if text.isspace(): return
    # ...
```

The parsed HTML tree now looks like this:

``` {.example}
<html lang="en-US" xml:lang="en-US">
   <head>
     <meta charset="utf-8" />
       <meta name="generator" content="pandoc" />
         <meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=yes" />
           <meta name="author" content="Pavel Panchekha &amp; Chris Harrelson" />
             <link rel="stylesheet" href="book.css" />
               <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Vollkorn%7CLora&display=swap" />
                 <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Vollkorn:400i%7CLora:400i&display=swap" />
                   <title>
```

Why's everything so deeply indented? Why aren't these open elements
ever closed?

::: {.further}
In SGML, document type declarations had a URL to define the valid
tags. Browsers use the absense of a document type declaration to
[identify][quirks-mode] very old, pre-SGML versions of
HTML,[^almost-standards-mode] but don't use the URL, so `<!doctype
html>` is the best document type declaration for HTML.
:::

[quirks-mode]: https://developer.mozilla.org/en-US/docs/Web/HTML/Quirks_Mode_and_Standards_Mode

[^almost-standards-mode]: There's also this crazy thing called "[almost
    standards][limited-quirks]" or "limited quirks" mode, due to a
    backwards-incompatible change in table cell vertical layout. Yes.
    I don't need to make these up!

[limited-quirks]: https://hsivonen.fi/doctype/

Self-closing tags
=================

Elements like `<meta>` and `<link>` are what are called self-closing:
these tags don't surround content, so you don't ever write `</meta>`
or `</link>`. Our parser needs special support for them. In HTML,
there's a [specific list][html5-void-elements] of these self-closing
tags:[^void-elements]

[html5-void-elements]: https://html.spec.whatwg.org/multipage/syntax.html#void-elements

[^void-elements]: A lot of these tags are obscure or obsolete.

``` {.python}
SELF_CLOSING_TAGS = [
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
]
```

Our parser needs to auto-close tags from this list:

``` {.python indent=4 expected=False}
def add_tag(self, tag):
    # ...
    elif tag in self.SELF_CLOSING_TAGS:
        parent = self.unfinished[-1]
        node = Element(text, parent)
        parent.children.append(node)
```

This code is right, but if you test it out it won't seem to help. Why
not?

::: {.further}
Prior to the invention of CSS, some browsers supported web page
styling using attributes like `bgcolor` and `vlink` (the
color of visited links) and tags like `font`. These [are
obsolete][html5-obsolete], but browsers still support some of them.
:::

[html5-obsolete]: https://html.spec.whatwg.org/multipage/obsolete.html#obsolete

Attributes
==========

Our parser is looking for a tag named `meta`, but it's finding a tag
named "`meta name="generator" content="pandoc" /`". The self-closing
code isn't triggered. We're going to need to support attributes if we
want the parser to work right.

HTML attributes add information about an element; open tags can have
any number of attributes. Attribute values can be quoted, unquoted, or
omitted entirely. Let's have our parser ignore values that contain
whitespace---which are a little complicated---and just focus on the
simple case.

Since we're not handling whitespace in values, we can split on
whitespace to get the tag name and the attribute-value pairs:

``` {.python}
class HTMLParser:
    def get_attributes(self, text):
        parts = text.split()
        tag = parts[0].lower()
        attributes = {}
        for attrpair in parts[1:]:
            # ...
        return tag, attributes
```

HTML tag names are case-insensitive,[^case-fold] as by the way are
attribute values, so I convert them to lower case. Then, inside the
loop, I split each attribute-value pair into a name and a value.
The easiest case is an unquoted attribute, where an equal sign
separates the two:

[^case-fold]: This is [not the right way][case-hard] to do case
    insensitive comparisons; the Unicode case folding algorithm should
    be used if you want to handle languages other than English. But in
    HTML specifically, tag names only use the ASCII characters where
    this test is sufficient.
    
[case-hard]: https://www.b-list.org/weblog/2018/nov/26/case/


``` {.python indent=4}
def get_attributes(self, text):
    # ...
    for attrpair in parts[1:]:
        key, value = attrpair.split("=", 1)
        attributes[key.lower()] = value
    # ...
```

The value can also be omitted, like in `<input disabled>`, in which
case the attribute value defaults to the empty string:

``` {.python indent=8}
for attrpair in parts[1:]:
    if "=" in attrpair:
        # ...
    else:
        attributes[attrpair.lower()] = ""
```

Finally, the value can be quoted, in which case the quotes have to be
stripped out:

``` {.python indent=12}
if "=" in attrpair:
    if len(value) > 2 and value[0] in ["'", "\""]:
        value = value[1:-1]
    # ...
```

We'll store these attributes inside `Element`s:

``` {.python}
class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        # ...
```

That means we'll need to call `get_attributes` at the top of
`add_tag`, to get the `attributes` we need to construct an `Element`.

``` {.python indent=4}
def add_tag(self, tag):
    tag, attributes = self.get_attributes(tag)
```

Remember to use `tag` and `attribute` instead of `text` in `add_tag`,
and try your parser again:

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

It's... close? Yes, attributes with whitespace (like `author` on the
fourth `meta` tag) are mis-parsed as multiple attributes, and the
final slash on self-closing tags is treated as an attribute too. A
better parser would fix these issues. But let's instead leave our
parser as is---these issues aren't going to be a problem for the toy
browser we're building---and move on to integrating it with our
browser.

::: {.further}
Putting a slash at the end of self-closing tags, like `<br/>`, became
fashionable when [XHTML][xhtml] looked like it might replace HTML, and
old-timers like me never broke the habit. But unlike in
[XML][xml-self-closing], in HTML self-closing tags are identified by
name, not by some special syntax, and the slash is optional.
:::

[xml-self-closing]: https://www.w3.org/TR/xml/#sec-starttags
[xhtml]: https://www.w3.org/TR/xhtml1/

Using the node tree
===================

Right now, the `Layout` class works token-by-token; we now want it to
go node-by-node instead. So let's sepate the old `token` method into
three parts: all the cases for open tags will go into a new `open`
method; all the cases for close tags will to into a new `close`
method; and instead of having a case for text tokens our browser can
just call the existing `text` method directly:

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

Now we need the `Layout` object to walk the node tree, calling `open`,
`close`, and `text` in the right order:

``` {.python indent=4 expected=False}
def recurse(self, tree):
    if isinstance(tree, TextNode):
        self.text(tree.text)
    else:
        self.open(tree.tag)
        for child in tree.children:
            self.recurse(child)
        self.close(tree.tag)
```

We'll also need the browser to construct the node tree, like this:

```
class Browser:
    def layout(self, body):
        tree = HTMLParser(body).parse()
        self.display_list = Layout(tree).display_list
        self.render()
```

Run it---the browser should now render web pages, with a proper
understanding of the HTML tree.

::: {.further}
The ill-considered Javascript `document.write` method allows
Javascript to modify the HTML source code while it's being parsed!
Modern browsers use [speculative][speculative-parsing] parsing to avoid
evaluating Javascript while parsing.
:::

[speculative-parsing]: https://developer.mozilla.org/en-US/docs/Glossary/speculative_parsing

Handling author errors
======================

The parser now handles HTML pages correctly—at least when the HTML is
written by the sorts of goody-two-shoes programmers who remember the
HTML boilerplate, always close their open tags, and make their bed in
the morning. Mere mortals lack such discipline and so browsers also
have to handle broken, confusing, boilerplate-less HTML.

In fact, modern HTML parsers are capable of transforming *any* string
of characters into an HTML tree, no matter how confusing the
markup.[^3] The full algorithm is, as you might expect, complicated
beyond belief, with dozens of ever-more-special cases forming a
taxonomy of human error, but one its the nicer features is *implicit*
tags.

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
browsers insert them automatically. Let's add support for implicit
tags to our browser via a new `implicit_tags` function that adds
implicit tags when the web page omits them. We'll want to call it in
both `add_text` and `add_tag`:

``` {.python indent=4}
class HTMLParser:
    def add_text(self, text):
        if text.isspace(): return
        self.implicit_tags(None)
        # ...

    def add_tag(self, tag):
        tag, attributes = self.get_attributes(tag)
        if tag.startswith("!"): return
        self.implicit_tags(tag)
        # ...
```

Note that the `implicit_tags` call comes after the lines that ignore
whitespace and doctypes; this way those bits of the source code are
truly ignored. The argument to `implicit_tags` is the tag name (or
`None` for text nodes), which we'll compare to the list of unfinished
tags to determine what's been omitted:

``` {.python}
class HTMLParser:
    def implicit_tags(self, tag):
        while True:
            open_tags = [node.tag for node in self.unfinished]
            # ...
```

`implicit_tags` has a loop because more than one tag could have been
omitted in a row; every iteration around the loop will add just one.
To determine which implicit tag to add, if any, requires examining the
open tags and the tag being inserted.

Let's start with the easiest case, the implicit `<html>` tag. An
implicit `<html>` tag is necessary if the first tag in the document is
something other than `<html>`:

``` {.python indent=8}
while True:
    # ...
    if open_tags == [] and tag != "html":
        self.add_tag("html")
```

Both `<head>` and `<body>` can also be omitted, but to figure out
which it is we need to look at which tag is being added:

``` {.python indent=8}
while True:
    # ...
    elif open_tags == ["html"] \
      and tag not in ["head", "body", "/html"]:
        if tag in self.HEAD_TAGS:
            self.add_tag("head")
        else:
            self.add_tag("body")
```

where `HEAD_TAGS` list the tags that you're supposed to put into the
`<head>` element:[^where-script]

[^where-script]: The `<script>`, can go in either the head or the body
    section, but it goes into the head by default.

``` {.python}
class HTMLParser:
    HEAD_TAGS = [
        "base", "basefont", "bgsound", "noscript",
        "link", "meta", "title", "style", "script",
    ]
```

Note that if both the `<html>` and `<head>` tags are omitted,
`implicit_tags` is going to insert both of them by going around the
loop twice. The first iteration add the `<html>` tag, and then in the
second iteration `open_tags` is `["html"]` and a `<head>` tag is
added.

Finally, the `</head>` tag can also be implicit, if the parser is
inside the `<head>` and sees an element that's supposed to go in the
`<body>`:

``` {.python indent=8}
while True:
    # ...
    elif open_tags == ["html", "head"] and tag not in ["/head"] + self.HEAD_TAGS:
        self.add_tag("/head")
```

Technically, the `</body>` and `</html>` tags can also be implicit.
But since our `finish` function already closes any unfinished tags,
that doesn't need any extra code. So all that's left for
`implicit_tags` tags is to exit out of the loop:

``` {.python indent=8}
while True:
    # ...
    else:
        break
```

These rules for malformed HTML may seem arbitrary, and they are: they
evolved over years of trying to guess what people "meant" when they
wrote that HTML, and are now codified in the [HTML parsing
standard][html5-parsing]. Of course, sometimes these rules "guess"
wrong---but as so often happens on the web, it's often more important
that every browser does the *same* thing, rather than each trying to
guess what the *right* thing is.

[html5-parsing]: https://html.spec.whatwg.org/multipage/parsing.html

::: {.further}
Thanks to implicit tags, you can usually skip the `<html>`, `<body>`,
and `<head>` elements, and they'll be implicitly added back for you.
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
- Code to recognize and handle attributes on elements
- Automatic fixes for some malformed HTML documents
- A recursive layout algorithm to lay out an HTML tree

The tree structure of HTML is essential to display visually complex
web pages, as we will see in the [next chapter](layout.md).

::: {.signup}
:::

Outline
=======

The complete set of functions, classes, and methods in our browser 
should look something like this:

::: {.cmd .python .outline html=True}
    python3 outlines.py --html src/lab4.py
:::

Exercises
=========

*Comments:* Update the HTML lexer to support comments. Comments in
HTML begin with `<!--` and end with `-->`. However, comments aren't
the same as tags: they can contain any text, including left and right
angle brackets. The lexer should skip comments, not generating any
token at all. Check: is `<!-->` a comment, or does it just start one?

*Paragraphs:* It's not clear what it would mean for one paragraph to
contain another. Change the parser so that a document like
`<p>hello<p>world</p>` results in two sibling paragraphs instead of
one paragraph inside another; real browsers do this too.

*Scripts:* JavaScript code embedded in a `<script>` tag uses the left
angle bracket to mean less-than. Modify your lexer so that the
contents of `<script>` tags are treated specially: no tags are allowed
inside `<script>`, except the `</script>` close tag.[^or-space]

[^or-space]: Technically it's just `</script` followed by a [space,
    tab, `\v`, `\r`, slash, or greater than sign][script-end-state].
    If you need to talk about `</script>` tags inside JavaScript code,
    you have to split it into multiple strings.

[script-end-state]: https://html.spec.whatwg.org/multipage/parsing.html#script-data-end-tag-name-state

*Quoted attributes:* Quoted attributes can contain spaces and right
angle brackets. Fix the lexer so that this is supported properly.
Hint: the current lexer is a finite state machine, with two states
(determined by `in_tag`). You'll need more states.

*Syntax Highlighting:* Implement the `view-source:` protocol as in
[Chapter 1](http.md#exercises), but make it syntax-highlight the
source code of HTML pages. Keep source code for HTML tags in a normal
font, but make text contents bold. If you've implemented it, wrap text
in `<pre>` tags as well to preserve line breaks. Hint: subclass the
HTML parser and use it to implement your syntax highlighter.
