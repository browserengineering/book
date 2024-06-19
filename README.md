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
python3 lab3.py https://browser.engineering
```

Every chapter can be run in a similar fashion.

For chapters 8 onward, there's also a "guest book" web application,
which you can run with:

```
cd src/
python3 server8.py
```

Like the browser, there are different versions of the server for
different chapters, named `server8.py`, `server9.py`, and so on.

You can also run the book's unit tests with:

    make test

## Rebuilding the quiz JavaScript

The source for the interactive multiple-choice quizzes is taken from [mdbook-quiz](https://github.com/cognitive-engineering-lab/mdbook-quiz). To rebuild the JS blob that we include on the quiz pages (located in `www/quiz-embed.iife.js`) do the following:

 - Install [depot](https://github.com/cognitive-engineering-lab/depot) (made by the same people who made `mdbook-quiz`; tldr: `cargo install depot-js --locked`).
 - Ensure you have [`cargo-make`](https://github.com/sagiegurari/cargo‐make) installed.
 - `git clone https://github.com/cognitive-engineering-lab/mdbook-quiz && cd mdbook-quiz`
 - `cargo make init-bindings`
 - `cd js`
 - `depot build`

The `quiz-embed.iife.js` file should be in `packages/quiz-embed/dist/`.

These instructions are taken from the `README.md` and `CONTRIBUTING.md` files in the `mdbook-quiz` project.
