WBE's Python-to-JS compiler
===========================

This file is mostly unit tests, but you could pretend it is
documentation if you were so inclined.

```
This is some helper code for tests. First, import the compiler:

>>> import sys
>>> sys.path.append("infra")
>>> from compile import *
>>> test_mode()

Then, this pretends all variables are in scope:

>>> class FakeCtx(dict):
...    type = "module"
...    def __getitem__(self, i): return True
...    def __contains__(self, i): return True
...    def is_global_constant(self, i): return False

Finally, this has some helper methods:

>>> class Test:
...     @staticmethod
...     def expr(s):
...         mod = AST39.parse(s)
...         assert isinstance(mod, ast.Module) and len(mod.body) == 1
...         stmt = mod.body[0]
...         assert isinstance(stmt, ast.Expr)
...         print(compile_expr(stmt.value, ctx=FakeCtx()))
...     def stmt(s):
...         mod = AST39.parse(s)
...         assert isinstance(mod, ast.Module) and len(mod.body) == 1
...         print(compile(mod.body[0], ctx=FakeCtx()))

That's all the helper code we need.
```

Compiling methods 
-----------------

When compiling methods, the key distinction is between "our" and
"library" methods. Library methods are synchronous:

    >>> Test.expr("s.connect((host, port))")
    (s.connect([host, port]))
    >>> IMPORTS.append("socket")
    >>> Test.expr("socket.socket()")
    (socket.socket())

But "our" methods are async:

    >>> OUR_METHODS.append("layout")
    >>> Test.expr("self.document.layout()")
    (await this.document.layout())

One exception: `makefile` is async to allow for downloading external
pages:

     >>> Test.expr("s.makefile('r', encoding='utf8', newline='foo')")
     (await s.makefile("r", "utf8", "foo"))

Some library methods need to be renamed:

    >>> Test.expr("header.lower()")
    (header.toLowerCase())
    >>> Test.expr("value.strip()")
    (value.trim())
    >>> Test.expr("url.startswith('http://')")
    (url.startsWith("http://"))

There is some basic support for Python's `format`:

    >>> Test.expr("'a {} b {} c'.format(d, e)")
    (("a " + d + " b " + e + " c"))

And then there's a lot of special cases

    >>> Test.expr("body.encode('utf8')")
    (body)
    >>> Test.expr("', '.join(fields)")
    (fields.join(", "))
    >>> Test.expr("text.isspace()")
    (/^\s*$/.test(text))
    >>> Test.expr("text.isalnum()")
    (/^[a-zA-Z0-9]+$/.test(text))
    >>> Test.expr("node.attributes.items()")
    (Object.entries(node.attributes))
    >>> Test.expr("self.window.bind('<Down>', self.scrolldown)")
    (this.window.bind("<Down>", (e) => this.scrolldown(e)))
    >>> Test.expr("rules.extend(more_rules)")
    (Array.prototype.push.apply(rules, more_rules))
    >>> Test.expr("node.attributes.get('background', 'transparent')")
    ((node.attributes?.["background"] ?? "transparent"))
    >>> Test.expr("url.count('/')")
    (url.split("/").length - 1)

The Python `str.split` function is especially tricky, because its
cases don't map neatly to JavaScript. There's a `pysplit` function for
the hard case:

    >>> Test.expr("tag.split()")
    (tag.trim().split(/\s+/))
    >>> Test.expr("attrpair.split('=')")
    (attrpair.split("="))
    >>> Test.expr("hostpath.split('/', 1)")
    (pysplit(hostpath, "/", 1))
    >>> Test.expr("hostpath.rsplit('/', 1)")
    (pyrsplit(hostpath, "/", 1))

Compiling Functions
-------------------

Like for methods, library functions are synchronous but our functions
are async:

    >>> Test.expr("int(val)")
    (parseInt(val))
    >>> OUR_FNS.append("style")
    >>> Test.expr("style(nodes, rules)")
    (await style(nodes, rules))

Classes work a little differently in JS---they need the `new`
keyword---but that raises a problem because we want async constructors
but in JS constructors can only be synchronous. So we introduce a new
`init` method that is the real constructor:

    >>> OUR_CLASSES.append("Text")
    >>> Test.expr("Text(txt)")
    (await (new Text()).init(txt))

Then there are a lot of builtin functions that have idiosyncratic
translations:

    >>> Test.expr("len(x)")
    (x.length)
    >>> Test.expr("isinstance(node, Element)")
    (node instanceof Element)
    >>> Test.expr("sum(lengths)")
    (lengths.reduce((a, v) => a + v, 0))
    >>> Test.expr("max(a, b)")
    (Math.max(a, b))
    >>> Test.expr("min(ascents)")
    (ascents.reduce((a, v) => Math.min(a, v)))
    >>> Test.expr("repr(node)")
    (node.toString())
    >>> Test.expr("str(node)")
    (node.toString())

The `open` function works in a weird way---it has to record all read
files, which must be constants:

    >>> Test.expr("open('browser.css')")
    (filesystem.open("browser.css"))
    >>> assert 'browser.css' in FILES

The `sorted` function is similarly weird because we need to convert
key functions to a comparator:

    >>> Test.expr("sorted(rules, key=cascade_priority)")
    (rules.slice().sort(comparator(cascade_priority)))

Finally there is the special `breakpoint` builtin, which we use for
pausing widgets. It compiles to a `breakpoint.event` function, which
has to use `await` in order to capture the continuation.

    >>> Test.expr("breakpoint('layout_pre', self)")
    (await breakpoint.event("layout_pre", this))

Compiling Expressions
---------------------

Subscripts in Python are tricky because they can be indices or slices:

    >>> Test.expr("a[i]")
    a[i]
    >>> Test.expr("a[i:j]")
    a.slice(i, j)

There special support for index `-1`:

    >>> Test.expr("a[-1]")
    a[a.length - 1]

Functions calls are described above, so I won't repeat it here.

Math operations work as expected:

    >>> Test.expr("a + b")
    (a + b)
    >>> Test.expr("a / b")
    (a / b)

But some boolean operations use the `truthy` wrapper to handle
truthiness of arrays (in JS, empty arrays are true):

    >>> Test.expr("not x")
    (!truthy(x))
    >>> Test.expr("a or b")
    (truthy(a) || truthy(b))

Comparisons in Python can chain, but we don't support that:

    >>> Test.expr("a < b")
    (a < b)
    >>> Test.expr("a < b < c")
    Traceback (most recent call last):
        ...
    AssertionError

The `in` operator is handled unusually, since there's no equivalent in
JS. For a fixed list or for a fixed string we can express it directly:

    >>> Test.expr("x in ['a', 'b']")
    (x === "a" || x === "b")
    >>> Test.expr("x in 'asdf'")
    ("asdf".indexOf(x) !== -1)

But otherwise you need a hint. Also, there's a special case for
comparing to an array (arrays in JS compare by identity):

    >>> Test.expr("x == ['a', 'b']")
    (JSON.stringify(x) === JSON.stringify(["a", "b"]))
    
Conditional expressions are also supported:

    >>> Test.expr("x if y else z")
    (y ? x : z)

One weird case is list comprehensions. We compile those to `map` and `filter`:

    >>> Test.expr("[x for x, y in v.items()]")
    (Object.entries(v)).map(([x, y]) => x)
    >>> Test.expr("[x for x, y in v.items() if y > 0]")
    (Object.entries(v)).filter(([x, y]) => (y > 0)).map(([x, y]) => x)

The remaining expressions are pretty much direct translations:

    >>> Test.expr("(a, b)")
    [a, b]
    >>> Test.expr("[a, b]")
    [a, b]
    >>> Test.expr("{'a': 'b', 'c': 'd'}")
    {"a": "b", "c": "d"}
    >>> Test.expr("self")
    this
    >>> Test.expr("foo")
    foo
    >>> Test.expr("foo.bar")
    foo.bar
    >>> Test.expr("'asdf'")
    "asdf"
    >>> Test.expr("12")
    12
    >>> Test.expr("None")
    null
    >>> Test.expr("True")
    true

Compiling Statements
--------------------

Compiling statements is more complex than expressions. For example,
imports don't turn into anything at all, but they do affect the
compiler state:

    >>> Test.stmt("import ssl")
    // Please configure the 'ssl' module
    >>> assert "ssl" in IMPORTS

Functions become function definitions:

    >>> Test.stmt("def foo(): return 1")
    async function foo() {
      return 1;
    }
    >>> Test.stmt("def foo(a, b): return a")
    async function foo(a, b) {
      return a;
    }


Classes become class definitions. But inside a class there's a special
cases for the names `__init__` and `__repr__`. The `__init__` function
becomes a special `init` function:

    >>> Test.stmt("class foo:\n def __init__(self):\n  self.x = 1")
    class foo {
      async init() {
        this.x = 1;
        return this;
      }
    }

Meanwhile `__repr__` becomes `toString` and it cannot be async---so
basically don't call any functions for a `__repr__` function:

    >>> Test.stmt("class foo:\n def __repr__(self):\n  return 'foo'")
    class foo {
      toString() {
        return "foo";
      }
    }

There's a pretty weird special case for string constants at the top
level, which we take to be multiline comments:

    >>> Test.stmt("'''\nThis is a test comment\nfor testing\n'''")
    // This is a test comment
    // for testing

Assignment statements work of course:

    >>> Test.stmt("x = 1")
    x = 1;
    >>> Test.stmt("x += 1")
    x += 1;
    >>> Test.stmt("x, y = z")
    [x, y] = z;

What's missing from these tests is a system for tracking which
variables are new and which aren't, so that we can insert `let`
appropriately. Just gotta assume it works, I guess!

Return, continue, and break all do the obvious:

    >>> Test.stmt("return x")
    return x;
    >>> Test.stmt("continue")
    continue;
    >>> Test.stmt("break")
    break;

Assertions raise a generic `Error`; we need this for parsing CSS:

    >>> Test.stmt("assert len(x) > 0")
    if (!truthy(((x.length) > 0))) throw Error();
    >>> Test.stmt("assert len(x) > 0, 'asdf'")
    if (!truthy(((x.length) > 0))) throw Error("asdf");

The `while` and `for` loops translate pretty directly:

    >>> OUR_FNS.append("foo")
    >>> OUR_FNS.append("bar")
    >>> Test.stmt("while foo():\n bar()")
    while ((await foo())) {
      (await bar());
    }
    >>> Test.stmt("for x in foo():\n bar(x)")
    for (let x of (await foo())) {
      (await bar(x));
    }

The `try` statement is different in Python because you can catch
specific types of exceptions. That's just not supported in JS:

    >>> Test.stmt("try:\n assert False\nexcept AssertionError:\n foo()")
    try {
      if (!truthy(false)) throw Error();
    } catch {
      (await foo());
    }

The `with` statement in Python has no analog in JS (which also has a
`with` statement but one that does something unrelated) so we just
compile it into `open` and `close` statements:

    >>> Test.stmt("with open('browser.css') as f:\n f.read()")
    f = (filesystem.open("browser.css"));
    (f.read());
    (f.close());

But `if` statements are weird. First, there's the top-level `if`
statement, which we elide. But then also there are one-line `if`
statements and also some complex handling of `if` chains:

    >>> Test.stmt("if __name__ == '__main__': pass")
    // Requires a test harness
    >>> Test.stmt("def foo():\n if foo(): bar()")
    async function foo() {
      if (truthy((await foo()))) (await bar());
    }
    >>> Test.stmt("def foo():\n if foo():\n  bar()")
    async function foo() {
      if (truthy((await foo()))) {
        (await bar());
      }
    }
    >>> OUR_FNS.append("baz")
    >>> Test.stmt("def foo():\n if foo():\n  bar()\n else:\n  baz()")
    async function foo() {
      if (truthy((await foo()))) {
        (await bar());
      } else {
        (await baz());
      }
    }
    >>> Test.stmt('''
    ... def foo():
    ...  if foo():
    ...    bar()
    ...  elif bar():
    ...    foo()
    ...  else:
    ...   baz()
    ... ''')
    async function foo() {
      if (truthy((await foo()))) {
        (await bar());
      } else if (truthy((await bar()))) {
        (await foo());
      } else {
        (await baz());
      }
    }

With `if` statements there's also some real complex logic for defining
variables assigned in both branches of an `if`, but I can't easily
test that here.
