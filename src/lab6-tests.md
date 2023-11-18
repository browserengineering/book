Tests for WBE Chapter 6
=======================

Chapter 6 (Applying User Styles) introduces a CSS parser for the style attribute
and style sheets, and adds support for inherited properties, tag selectors, and
descendant selectors.

    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab6

Testing resolve_url
===================

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

Testing tree_to_list
====================

    >>> url = lab6.URL(test.socket.serve("<div>Test</div>"))
    >>> browser = lab6.Browser()
    >>> browser.load(url)
    >>> lab6.print_tree(browser.document)
     DocumentLayout()
       BlockLayout[block](x=13, y=18, width=774, height=15.0)
         BlockLayout[block](x=13, y=18, width=774, height=15.0)
           BlockLayout[inline](x=13, y=18, width=774, height=15.0)
    >>> list = []
    >>> retval = lab6.tree_to_list(browser.document, list)
    >>> retval #doctest: +NORMALIZE_WHITESPACE
    [DocumentLayout(),
     BlockLayout[block](x=13, y=18, width=774, height=15.0),
     BlockLayout[block](x=13, y=18, width=774, height=15.0),
     BlockLayout[inline](x=13, y=18, width=774, height=15.0)]
    >>> retval == list
    True

Testing CSSParser
=================

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

    

Testing compute_style
=====================

Let's make a simple HTML tree:

    >>> html = lab6.Element("html", {}, None)
    >>> body = lab6.Element("body", {}, html)
    >>> div = lab6.Element("div", {}, body)
    >>> html.children.append(body)
    >>> body.children.append(div)
    
Let's give all of them a percentage font size:

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

Testing style
=============

    >>> html = lab6.Element("html", {}, None)
    >>> body = lab6.Element("body", {}, html)
    >>> div = lab6.Element("div", {}, body)

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
