WBE's Python-to-JS compiler
===========================

This file is mostly unit tests, but you could pretend it is
documentation if you were so inclined.

We need import the annotator:

    >>> import sys
    >>> sys.path.append("infra")
    >>> from annotate_code import *

That's all the helper code we need.

Annotating text
---------------

Raw, unannotated text just yields a `<pre>` tag:

    >>> print(parse("This is a test"))
    <pre class='highlight-region'>
    This is a test</pre>

However, square brackets introduce a highlight region:

    >>> print(parse("This is a [test][tl|Example]"))
    <pre class='highlight-region'>
    This is a <mark>test<label class='above left'>Example</label></mark></pre>

There are six "locations" where some text is allowed to appear:


    >>> print(parse("This is a [test][tl|Example]"))
    <pre class='highlight-region'>
    This is a <mark>test<label class='above left'>Example</label></mark></pre>
    >>> print(parse("This is a [test][tr|Example]"))
    <pre class='highlight-region'>
    This is a <mark>test<label class='above right'>Example</label></mark></pre>
    >>> print(parse("This is a [test][bl|Example]"))
    <pre class='highlight-region'>
    This is a <mark>test<label class='below left'>Example</label></mark></pre>
    >>> print(parse("This is a [test][br|Example]"))
    <pre class='highlight-region'>
    This is a <mark>test<label class='below right'>Example</label></mark></pre>
    >>> print(parse("This is a [test][sl|Example]"))
    <pre class='highlight-region'>
    This is a <mark>test<label class='side left'>Example</label></mark></pre>
    >>> print(parse("This is a [test][sr|Example]"))
    <pre class='highlight-region'>
    This is a <mark>test<label class='side right'>Example</label></mark></pre>
    
Multiple lines works fine:

    >>> print(parse("This is a [test][tl|Example]\nLine [two][br|2]"))
    <pre class='highlight-region'>
    This is a <mark>test<label class='above left'>Example</label></mark>
    Line <mark>two<label class='below right'>2</label></mark></pre>
