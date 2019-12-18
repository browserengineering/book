---
title: Preliminaries
type: Preliminaries
prev: preface
next: http
...

::: {.todo}
The debugging tips should move to their respective sections.
:::

Using Python
============

This book uses Python as its implementation language. Python supports
functional, imperative, and object-oriented programming. Plus, it is
cross-platform, beginner-friendly, and has many libraries you could
use in projects that build on this book. One downside is that Python
is quite slow, and for this reason every real web browser is written
in C++. For teaching, that isn't a problem.

::: {.todo}
This section will feature a quick discussion of installing Python and
point to some Python resources for students who aren't familiar with
the language.
:::

Python comes in two major versions: Python 2 and Python 3. All of the
examples in this book use Python 3, and if you try to follow along in
Python 2 you will get pretty confused. In a few places, I show Python
command lines, and when I do I call the Python binary `python3`. Your
system might be different (but probably won't be).

Debugging Tips
==============

As you're following along with the text, or implementing exercises,
you'll frequently want to test or debug your web browser. Here are a
few tips on doing that.

**Testing against browsers**: Except where explicitly noted, the web
browser developed in this book is intended to match the behavior of
real web browsers. That means you can always see the correct behavior
by firing up your favorite web browser on the same pages that you're
testing your web browser on. Use this any time you're unsure what the
correct behavior in some situation is. Often there's no rhyme or
reason to what browsers do in some edge case. Looking at the real
thing is the best way to find out.

**Simple HTTP Server**: You'll frequently want to test your web
browser by running it on custom web pages. To do so, you'll need to
start a web server that your browser could connect to. Luckily, Python
ships with one. Go to a directory and run:

    python3 -m http.server
    
This will start a web server at the address http://localhost:8000/
serving the contents of `index.html` in the current directory. You can
view other files in the directory as well.

**Printable Forms**: The Python `print` function is the most flexible
method of debugging, but it relies on things having a printable form.
For a custom object, that doesn't come for free. In Python, you can
define the printable form of an object by defining its `__repr__`
method, like this:

``` {.python}
class Tag:
    def __repr__(self):
        return "Tag(" + self.tag + ")"
```

The book doesn't show code for these methods, but for your own sanity
you should probably implement them for each custom object you define.

**Handling Crashes**: Crashes in the HTML and CSS parser can be
frustrating to debug. Luckily, I don't make many modifications to
either component once it's written. Still, if you find an error in
either component, the best way to proceed is to print the state of the
parser (the current element and current token for the HTML parser, and
the current parsing function and current input position for the CSS
parser) at every parsing step, and then walking through the output by
hand until you see the mistake. This is a slow but a sure process.

Crashes in the JavaScript component, on the other hand, are fairly
frustrating because backtraces that involve both JavaScript and Python
frames aren't supported by DukPy. I recommend wrapping Python
registered functions like so to print any backtraces they produce:

``` {.python}
try:
    # ...
except:
    import traceback
    traceback.print_exc()
    raise
```

For JavaScript functions called by Python, you can do the same like
this:

``` {.javascript}
try {
    # ...
} catch(e) {
    console.log(e.stack);
}
```

Naturally you'll need to implement `console.log` first.
