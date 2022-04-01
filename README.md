Web Browser Engineering
=======================

This is the source code to *Web Browser Engineering*, my book on how
web browsers work. The best way to read the book is
[online](https://browser.engineering/).

# Building the book

If you want to build from source, run:

    make book draft blog

The source code contains:

- The Markdown source for the book text, in `book/`
- A template and code for converting the book to HTML, in `infra/`
- Chapter-by-chapter implementations of the browser, in `src/`
- Styling for the book's website, in `www/`
- The book's built-in feedback system, in `www/`, including JavaScript
  and the Python backend.

We prefer to receive typos and small comments on the text using the
book's built-in feedback tools, which you can enable with `Ctrl+E`.

You can run the book's built-in checks with:

    make lint

We're always happy to hear from readers and from educators who want to
use the book. Please [email us](mailto:author@browser.engineering)!

# Running the browser

Code for the browser developed in the book can be found in `src/`, in
files named `lab1.py`, `lab2.py`, and so on, corresponding to each
chapter.

To run it, you'll need to install:

- A recent Python 3; version 3.9.10is known to work, but older
  versions probably will too.
- The `tkinter` package, part of the Python standard library but often
  isn't included in pre-installed Pythons on macOS and Linux.
  You can check by running `python3 -m tkinter`, which should open a test window.
- For Chapter 9+, the `dukpy` package. Consult that chapter for installation instructions.
- For Chapter 11+, the `skia` and `pysdl2` packages. Consult that chapter for installation instructions.

Once you have the above, you can run, say, the browser as of the end
of Chapter 3 like so:

```
cd src/
PYTHONBREAKPOINT=0 python3 lab3.py https://browser.engineering
```

Every chapter can be run in a similar fashion.

For chapters 8 onward, there's also a "guest book" web application,
which you can run with:

```
cd src/
PYTHONBREAKPOINT=0 python3 server8.py
```

Like the browser, there are different versions of the server for
different chapters, named `server8.py`, `server9.py`, and so on.

You can also run the book's unit tests with:

    make test
