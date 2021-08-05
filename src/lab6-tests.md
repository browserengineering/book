`Tests for WBE Chapter 6
=======================+

Chapter 6 (Applying User Styles) introduces a 

    >>> import test
    >>> _ = test.socket.patch().start()
    >>> _ = test.ssl.patch().start()
    >>> import lab6

    >>> url = 'http://test.test/example'
    >>> test.socket.respond(url, b"HTTP/1.0 200 OK\r\n" +
    ... b"Header1: Value1\r\n\r\n" +
    ... b"<div>Test</div>")

Testing resolve_url
===================

    >>> lab6.resolve_url("http://foo.com", "http://bar.com/")
    'http://foo.com'

    >>> lab6.resolve_url("/url", "http://bar.com/")
    'http://bar.com/url'

    >>> lab6.resolve_url("url2", "http://bar.com/url1")
    'http://bar.com/url2'

    >>> lab6.resolve_url("url2", "http://bar.com/url1/")
    'http://bar.com/url1/url2'

Testing tree_to_list
====================

    >>> browser = lab6.Browser()
    >>> browser.load(url)
    >>> list = []
    >>> retval = lab6.tree_to_list(browser.document, list)
    >>> retval
    [DocumentLayout(), BlockLayout(x=13, y=18, width=774, height=14.399999999999999), BlockLayout(x=13, y=18, width=774, height=14.399999999999999), InlineLayout(x=13, y=18, width=774, height=14.399999999999999)]
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
    [(DescendantSelector(ancestor=TagSelector(tag=div, priority=1), descendant=TagSelector(tag=span, priority=1), priority=2, {'foo': 'bar'})]

    >>> lab6.CSSParser("div span h1 { foo: bar }").parse()
    [(DescendantSelector(ancestor=DescendantSelector(ancestor=TagSelector(tag=div, priority=1), descendant=TagSelector(tag=span, priority=1), priority=2, descendant=TagSelector(tag=h1, priority=1), priority=3, {'foo': 'bar'})]

Multiple rules can be present.

    >>> lab6.CSSParser("div { foo: bar } span { baz : baz2 }").parse()
    [(TagSelector(tag=div, priority=1), {'foo': 'bar'}), (TagSelector(tag=span, priority=1), {'baz': 'baz2'})]

Unknown syntaxes are ignored.

    >>> lab6.CSSParser("foo { bar }").parse()
    [(TagSelector(tag=foo, priority=1), {})]


Testing compute_style
=====================

    >>> html = lab6.Element("html", {}, None)
    >>> body = lab6.Element("body", {}, html)
    >>> div = lab6.Element("div", {}, body)

Other than `font-size`, this just returns the value:

    >>> lab6.compute_style(body, "property", "value")
    'value'

Values for `font-size` ending in "px" return the value:

    >>> lab6.compute_style(body, "font-size", "12px")
    '12px'

Percentage values are computed against the parent

    >>> html.style = {"font-size": "30px"}
    >>> lab6.compute_style(body, "font-size", "100%")
    '30.0px'
    >>> lab6.compute_style(body, "font-size", "80%")
    '24.0px'

    >>> body.style = {"font-size": "10px"}
    >>> lab6.compute_style(div, "font-size", "100%")
    '10.0px'
    >>> lab6.compute_style(div, "font-size", "80%")
    '8.0px'

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

Priorities work (descendant selectors high higher priority than tag selectors):

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

    >>> url2 = 'http://test.test/example2'
    >>> test.socket.respond(url2, b"HTTP/1.0 200 OK\r\n" +
    ... b"Header1: Value1\r\n\r\n" +
    ... b"<div style=\"color:blue\">Test</div>")


Style attributes have the highest priority:

    >>> browser = lab6.Browser()
    >>> browser.load(url2)
    >>> browser.document.children[0].children[0].children[0].node.style['color']
    'blue'