---
title: Preliminaries
cur: preliminaries
type: Preliminaries
prev: preface
next: http
...


Using Python
============

This book uses Python as its implementation language. Python supports
functional, imperative, and object-oriented programming. Plus, it is
cross-platform, beginner-friendly, and has many libraries you could
use for projects that build on this book. One downside is that Python
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
system might use something else, but probably doesn't.


Python Tips
===========

As you're following along with the text, or implementing exercises,
you'll frequently want to test or debug your web browser. Here are a
few tips on doing that.

**Test against browsers**: Except where explicitly noted, the web
browser developed in this book should match the behavior of real web
browsers. If you're unsure what the correct behavior in some situation
is, fire up your favorite web browser on an example page. On edge
cases, browser behavior is defined more by historical accident and
backwards compatibility than by logic. Looking at the real thing is
the best way to figure out what to do.

**Serving Web Pages**: You'll want to write test pages for your web
browser, and you'll need a web server to serve those pages. Luckily,
Python ships with a simple web server. Go to a directory and run:

    python3 -m http.server
    
This will start a web server at the address http://localhost:8000/
serving the contents of `index.html` in the current directory. You can
view other files in the directory by adding them to the URL, like
this:

    http://localhost:8000/my-test.html

**Printable Forms**: To use Python's `print` function for debugging,
you'll need to define printable forms for the classes you define.
Python uses the `__repr__` method for this:

``` {.python}
class Tag:
    def __repr__(self):
        return "Tag(" + self.tag + ")"
```

This book won't define these methods explicitly, but for your own
sanity and ease of debugging, implement them whenever you define a
class.

