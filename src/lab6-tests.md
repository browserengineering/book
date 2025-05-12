Tests for WBE Chapter 6
=======================

Chapter 6 (Applying User Styles) introduces a CSS parser for the style attribute
and style sheets, and adds support for inherited properties, tag selectors, and
descendant selectors.

    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab6

    
6.1 Parsing with Functions
--------------------------

Let's test the `body` function, making sure it can parse CSS
property-value pairs.

    >>> lab6.CSSParser("background-color:lightblue;").body()
    {'background-color': 'lightblue'}

Whitespace should be allowed:

    >>> lab6.CSSParser("background-color : lightblue ;").body()
    {'background-color': 'lightblue'}

Multiple property-value pairs, with semicolons, should also work:

    >>> lab6.CSSParser("background-color: lightblue; margin: 1px;").body()
    {'background-color': 'lightblue', 'margin': '1px'}
    
The final semicolon should be optional:

    >>> lab6.CSSParser("background-color: lightblue").body()
    {'background-color': 'lightblue'}
    
Oddly, the book's parser doesn't allow the `style` value to start with
a space, probably because its HTML parser doesn't make that possible.

If there's junk or other garbage, the parser shouldn't crash


    >>> lab6.CSSParser("this isn't a CSS property : value pair ; ; ; lol").body()
    {}

6.2 The `style` Attribute
-------------------------

We need to make sure we didn't break layout with all of these changes:

    >>> sample_html = "<div></div><div>text</div><div><div></div>text</div><span></span><span>text</span>"
    >>> url = lab6.URL(test.socket.serve(sample_html))
    >>> browser = lab6.Browser()
    >>> browser.load(url)
    >>> lab6.print_tree(browser.document)
     DocumentLayout()
       BlockLayout[block](x=13, y=18, width=774, height=45.0, node=<html>)
         BlockLayout[block](x=13, y=18, width=774, height=45.0, node=<body>)
           BlockLayout[block](x=13, y=18, width=774, height=0, node=<div>)
           BlockLayout[inline](x=13, y=18, width=774, height=15.0, node=<div>)
           BlockLayout[block](x=13, y=33.0, width=774, height=15.0, node=<div>)
             BlockLayout[block](x=13, y=33.0, width=774, height=0, node=<div>)
             BlockLayout[inline](x=13, y=33.0, width=774, height=15.0, node='text')
           BlockLayout[block](x=13, y=48.0, width=774, height=0, node=<span>)
           BlockLayout[inline](x=13, y=48.0, width=774, height=15.0, node=<span>)

    >>> browser.display_list #doctest: +NORMALIZE_WHITESPACE
    [DrawText(top=20.25 left=13 bottom=32.25 text=text
              font=Font size=12 weight=normal slant=roman style=None),
     DrawText(top=35.25 left=13 bottom=47.25 text=text
              font=Font size=12 weight=normal slant=roman style=None),
     DrawText(top=50.25 left=13 bottom=62.25 text=text
              font=Font size=12 weight=normal slant=roman style=None)]
     
Here's a case with a paragraph split over multiple lines:

    >>> url = lab6.URL(test.socket.serve("""
    ... <p>Hello<br>World!</p>
    ... """))
    >>> browser = lab6.Browser()
    >>> browser.load(url)
    >>> browser.display_list #doctest: +NORMALIZE_WHITESPACE
    [DrawText(top=20.25 left=13 bottom=32.25 text=Hello
              font=Font size=12 weight=normal slant=roman style=None),
     DrawText(top=35.25 left=13 bottom=47.25 text=World!
              font=Font size=12 weight=normal slant=roman style=None)]

Let's test an element with a `style` attribute:

    >>> url = test.socket.serve("<div style='background-color:lightblue'></div>")
    >>> browser = lab6.Browser()
    >>> browser.load(lab6.URL(url))
    >>> browser.nodes.children[0].children[0].style['background-color']
    'lightblue'

This should in fact cause a background rectangle to be generated:

    >>> browser.display_list
    [DrawRect(top=18 left=13 bottom=18 right=787 color=lightblue)]

6.3 Selectors
-------------

A tag selector stores its tag, the key-value pair, and a priority of 1.

    >>> lab6.CSSParser("div { foo: bar }").parse()
    [(TagSelector(tag=div, priority=1), {'foo': 'bar'})]

A descendant selector stores its ancestor and descendant as TagSelectors,
with a priority that sums them.

    >>> lab6.CSSParser("div span { foo: bar }").parse()
    [(DescendantSelector(ancestor=TagSelector(tag=div, priority=1), descendant=TagSelector(tag=span, priority=1), priority=2), {'foo': 'bar'})]

    >>> lab6.CSSParser("div span h1 { foo: bar }").parse()
    [(DescendantSelector(ancestor=DescendantSelector(ancestor=TagSelector(tag=div, priority=1), descendant=TagSelector(tag=span, priority=1), priority=2), descendant=TagSelector(tag=h1, priority=1), priority=3), {'foo': 'bar'})]

Multiple rules can be present.

    >>> lab6.CSSParser("div { foo: bar } span { baz : baz2 }").parse()
    [(TagSelector(tag=div, priority=1), {'foo': 'bar'}), (TagSelector(tag=span, priority=1), {'baz': 'baz2'})]

Unknown syntaxes are ignored.

    >>> lab6.CSSParser("a;").parse()
    []
    >>> lab6.CSSParser("a {;}").parse()
    [(TagSelector(tag=a, priority=1), {})]
    >>> lab6.CSSParser("{} a;").parse()
    []
    >>> lab6.CSSParser("a { p }").parse()
    [(TagSelector(tag=a, priority=1), {})]
    >>> lab6.CSSParser("a { p: v }").parse()
    [(TagSelector(tag=a, priority=1), {'p': 'v'})]
    >>> lab6.CSSParser("a { p: ^ }").parse()
    [(TagSelector(tag=a, priority=1), {})]
    >>> lab6.CSSParser("a { p: ; }").parse()
    [(TagSelector(tag=a, priority=1), {})]
    >>> lab6.CSSParser("a { p: v; q }").parse()
    [(TagSelector(tag=a, priority=1), {'p': 'v'})]
    >>> lab6.CSSParser("a { p: v; ; q: u }").parse()
    [(TagSelector(tag=a, priority=1), {'p': 'v', 'q': 'u'})]
    >>> lab6.CSSParser("a { p: v; q:: u }").parse()
    [(TagSelector(tag=a, priority=1), {'p': 'v'})]

Whitespace can be present anywhere. This is an easy mistake to make
with a scannerless parser like used here:

    >>> lab6.CSSParser("a {}").parse()
    [(TagSelector(tag=a, priority=1), {})]
    >>> lab6.CSSParser("a{}").parse()
    [(TagSelector(tag=a, priority=1), {})]
    >>> lab6.CSSParser("a{ }").parse()
    [(TagSelector(tag=a, priority=1), {})]
    >>> lab6.CSSParser("a {} ").parse()
    [(TagSelector(tag=a, priority=1), {})]
    >>> lab6.CSSParser("a {p:v} ").parse()
    [(TagSelector(tag=a, priority=1), {'p': 'v'})]
    >>> lab6.CSSParser("a {p :v} ").parse()
    [(TagSelector(tag=a, priority=1), {'p': 'v'})]
    >>> lab6.CSSParser("a { p:v} ").parse()
    [(TagSelector(tag=a, priority=1), {'p': 'v'})]
    >>> lab6.CSSParser("a {p: v} ").parse()
    [(TagSelector(tag=a, priority=1), {'p': 'v'})]
    >>> lab6.CSSParser("a {p:v } ").parse()
    [(TagSelector(tag=a, priority=1), {'p': 'v'})]

6.4 Applying Style Sheets
-------------------------

Let's also test the `tree_to_list` helper function:

    >>> url = lab6.URL(test.socket.serve("<div>Test</div>"))
    >>> browser = lab6.Browser()
    >>> browser.load(url)
    >>> lab6.print_tree(browser.document)
     DocumentLayout()
       BlockLayout[block](x=13, y=18, width=774, height=15.0, node=<html>)
         BlockLayout[block](x=13, y=18, width=774, height=15.0, node=<body>)
           BlockLayout[inline](x=13, y=18, width=774, height=15.0, node=<div>)
    >>> list = []
    >>> retval = lab6.tree_to_list(browser.document, list)
    >>> retval #doctest: +NORMALIZE_WHITESPACE
    [DocumentLayout(),
     BlockLayout[block](x=13, y=18, width=774, height=15.0, node=<html>),
     BlockLayout[block](x=13, y=18, width=774, height=15.0, node=<body>),
     BlockLayout[inline](x=13, y=18, width=774, height=15.0, node=<div>)]
    >>> retval == list
    True

To test that our browser actually loads style sheets, we create a CSS
file and load a page linking to it:

    >>> cssurl = test.socket.serve("div { background-color: blue; }")
    >>> htmlurl = test.socket.serve("""
    ...    <link rel=stylesheet href='""" + cssurl + """'>
    ...    <div>test</div>
    ... """)
    >>> browser = lab6.Browser()
    >>> browser.load(lab6.URL(htmlurl))

Now we make sure that the `div` is blue:

    >>> browser.nodes.children[1].children[0].style["background-color"]
    'blue'
    
If the page doesn't exist, the browser doesn't crash:

    >>> htmlurl = test.socket.serve("""
    ...    <link rel=stylesheet href='/does/not/exist'>
    ... """)
    >>> browser.load(lab6.URL(htmlurl))

This first test used an absolute URL, but let's also test relative URLs.

    >>> lab6.URL("http://bar.com/").resolve("http://foo.com/")
    URL(scheme=http, host=foo.com, port=80, path='/')

    >>> lab6.URL("http://bar.com/").resolve("/url")
    URL(scheme=http, host=bar.com, port=80, path='/url')

    >>> lab6.URL("http://bar.com/url1").resolve("url2")
    URL(scheme=http, host=bar.com, port=80, path='/url2')

    >>> lab6.URL("http://bar.com/url1/").resolve("url2")
    URL(scheme=http, host=bar.com, port=80, path='/url1/url2')

    >>> lab6.URL("http://bar.com/url1/").resolve("//baz.com/url2")
    URL(scheme=http, host=baz.com, port=80, path='/url2')

A trailing slash is automatically added if omitted:

    >>> lab6.URL("http://bar.com").resolve("url2")
    URL(scheme=http, host=bar.com, port=80, path='/url2')

You can use `..` to go up:

    >>> lab6.URL("http://bar.com/a/b/c").resolve("d")
    URL(scheme=http, host=bar.com, port=80, path='/a/b/d')
    >>> lab6.URL("http://bar.com/a/b/c").resolve("../d")
    URL(scheme=http, host=bar.com, port=80, path='/a/d')
    >>> lab6.URL("http://bar.com/a/b/c").resolve("../../d")
    URL(scheme=http, host=bar.com, port=80, path='/d')
    >>> lab6.URL("http://bar.com/a/b/c").resolve("../../../d")
    URL(scheme=http, host=bar.com, port=80, path='/d')

6.5 Cascading
-------------

To test cascading, let's make a tiny HTML page and test styling it.

    >>> html = lab6.Element("html", {}, None)
    >>> body = lab6.Element("body", {}, html)
    >>> div = lab6.Element("div", {}, body)
    >>> html.children.append(body)
    >>> body.children.append(div)
    
Now we can style these elements with various rules to make sure
cascading works. First, a test with no cascading:

    >>> rules = lab6.CSSParser("html { background-color: green }").parse()
    >>> lab6.style(html, sorted(rules, key=lab6.cascade_priority))
    >>> html.style['background-color']
    'green'
    
Rules apply in order by default:

    >>> rules = lab6.CSSParser("html { background-color: green }" + \
    ...    "html { background-color: red }").parse()
    >>> lab6.style(html, sorted(rules, key=lab6.cascade_priority))
    >>> html.style['background-color']
    'red'

More descendant selectors means higher priority

    >>> rules = lab6.CSSParser("html div { background-color: green }" + \
    ...    "div { background-color: red }").parse()
    >>> lab6.style(html, sorted(rules, key=lab6.cascade_priority))
    >>> div.style['background-color']
    'green'

6.6 Inherited Styles
--------------------

Let's re-make the tree to clear any styles on it:

    >>> html = lab6.Element("html", {}, None)
    >>> body = lab6.Element("body", {}, html)
    >>> div = lab6.Element("div", {}, body)
    >>> html.children.append(body)
    >>> body.children.append(div)
    
Let's give all of the elements a percentage font size:

    >>> html.attributes["style"] = "font-size:150%"
    >>> body.attributes["style"] = "font-size:150%"
    >>> div.attributes["style"] = "font-size:150%"
    >>> lab6.style(html, [])

The font size of the `<div>` is computed relatively:

    >>> lab6.INHERITED_PROPERTIES["font-size"]
    '16px'
    >>> 16 * 1.5 * 1.5 * 1.5
    54.0
    >>> div.style["font-size"]
    '54.0px'
    
If we change the `<body>` to be absolute, then the `<div>` is relative
to that:

    >>> body.attributes["style"] = "font-size:10px"
    >>> lab6.style(html, [])
    >>> div.style["font-size"]
    '15.0px'

Let's reset again and test that all of the necessary inherited
properties are assigned to each element:

    >>> html = lab6.Element("html", {}, None)
    >>> body = lab6.Element("body", {}, html)
    >>> div = lab6.Element("div", {}, body)
    >>> html.children.append(body)
    >>> body.children.append(div)

The default styles for many elements are the same:

    >>> lab6.style(html, [])
    >>> html.style
    {'font-size': '16px', 'font-style': 'normal', 'font-weight': 'normal', 'color': 'black'}
    >>> lab6.style(body, [])
    >>> body.style
    {'font-size': '16px', 'font-style': 'normal', 'font-weight': 'normal', 'color': 'black'}
    >>> lab6.style(div, [])
    >>> div.style
    {'font-size': '16px', 'font-style': 'normal', 'font-weight': 'normal', 'color': 'black'}

    >>> rules = lab6.CSSParser(
    ... "html { font-size: 10px} body { font-size: 90% } \
    ... div { font-size: 90% } ").parse()

Percentage font sizes work as expected:

    >>> lab6.style(html, rules)
    >>> html.style
    {'font-size': '10px', 'font-style': 'normal', 'font-weight': 'normal', 'color': 'black'}

    >>> lab6.style(body, rules)
    >>> body.style
    {'font-size': '9.0px', 'font-style': 'normal', 'font-weight': 'normal', 'color': 'black'}

    >>> lab6.style(div, rules)
    >>> div.style
    {'font-size': '8.1px', 'font-style': 'normal', 'font-weight': 'normal', 'color': 'black'}

Inherited properties work (`font-weight` is an inherited property):

    >>> rules = lab6.CSSParser("html { font-weight: bold}").parse()
    >>> lab6.style(html, rules)
    >>> html.style
    {'font-size': '16px', 'font-style': 'normal', 'font-weight': 'bold', 'color': 'black'}
    >>> lab6.style(body, rules)
    >>> body.style
    {'font-size': '16px', 'font-style': 'normal', 'font-weight': 'bold', 'color': 'black'}
    >>> lab6.style(div, rules)
    >>> div.style
    {'font-size': '16px', 'font-style': 'normal', 'font-weight': 'bold', 'color': 'black'}

Other properties do not:

    >>> rules = lab6.CSSParser("html { background-color: green}").parse()
    >>> lab6.style(html, rules)
    >>> html.style
    {'font-size': '16px', 'font-style': 'normal', 'font-weight': 'normal', 'color': 'black', 'background-color': 'green'}
    >>> lab6.style(body, rules)
    >>> body.style
    {'font-size': '16px', 'font-style': 'normal', 'font-weight': 'normal', 'color': 'black'}
    >>> lab6.style(div, rules)
    >>> div.style
    {'font-size': '16px', 'font-style': 'normal', 'font-weight': 'normal', 'color': 'black'}

Descendant selectors work:

    >>> rules = lab6.CSSParser("html div { background-color: green}").parse()
    >>> lab6.style(html, rules)
    >>> html.style
    {'font-size': '16px', 'font-style': 'normal', 'font-weight': 'normal', 'color': 'black'}
    >>> lab6.style(body, rules)
    >>> body.style
    {'font-size': '16px', 'font-style': 'normal', 'font-weight': 'normal', 'color': 'black'}
    >>> lab6.style(div, rules)
    >>> div.style
    {'font-size': '16px', 'font-style': 'normal', 'font-weight': 'normal', 'color': 'black', 'background-color': 'green'}

Priorities work (descendant selectors higher priority than tag selectors):

    >>> rules = lab6.CSSParser(
    ... "html div { background-color: green} div { background-color: blue").parse()
    >>> lab6.style(html, rules)
    >>> html.style
    {'font-size': '16px', 'font-style': 'normal', 'font-weight': 'normal', 'color': 'black'}
    >>> lab6.style(body, rules)
    >>> body.style
    {'font-size': '16px', 'font-style': 'normal', 'font-weight': 'normal', 'color': 'black'}
    >>> lab6.style(div, rules)
    >>> div.style
    {'font-size': '16px', 'font-style': 'normal', 'font-weight': 'normal', 'color': 'black', 'background-color': 'green'}

Style attributes have the highest priority:

    >>> url2 = lab6.URL(test.socket.serve("<div style=\"color:blue\">Test</div>"))
    >>> browser = lab6.Browser()
    >>> browser.load(url2)
    >>> browser.document.children[0].children[0].children[0].node.style['color']
    'blue'

6.7 Font Properties
-------------------

Finally, let's test that the default style sheet gives appropriate
sizes to things, all the way down to the display list:

    >>> url = test.socket.serve("<a>blue</a><i>italic</i><b>bold</b><small>small</small><big>big")
    >>> browser = lab6.Browser()
    >>> browser.load(lab6.URL(url))
    >>> browser.display_list #doctest: +NORMALIZE_WHITESPACE
    [DrawText(top=21.1875 left=13 bottom=33.1875 text=blue font=Font size=12 weight=normal slant=roman style=None),
     DrawText(top=21.1875 left=73 bottom=33.1875 text=italic font=Font size=12 weight=normal slant=italic style=None),
     DrawText(top=21.1875 left=157 bottom=33.1875 text=bold font=Font size=12 weight=bold slant=roman style=None),
     DrawText(top=22.6875 left=217 bottom=32.6875 text=small font=Font size=10 weight=normal slant=roman style=None),
     DrawText(top=20.4375 left=277 bottom=33.4375 text=big font=Font size=13 weight=normal slant=roman style=None)]
