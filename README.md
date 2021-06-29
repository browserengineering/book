Web Browser Engineering
=======================

This is the source code to *Web Browser Engineering*, my book on how
web browsers work. The best way to read the book is
[online](https://browser.engineering/).

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

IWeam always happy to hear from readers and from educators who want to
use the book. Please [email us](mailto:author@browser.engineering)!
