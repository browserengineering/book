---
title: Code Outlines
author: Pavel Panchekha
date: 4 January 2020
prev: why-python
...

You may have noticed that [Web Browser Engineering](../)'s chapters
now have [outlines][ex-outline] listing all of the classes, constants,
and methods described in the book. That's a feature I've been working
on for a while, and I wanted to share how it works.

[ex-outline]: https://browser.engineering/text.html#outline


# Why outlines

One of the challenges both reading and writing Web Browser Engineering
is tracking how the code changes over time. The [eleven chapters](../)
of Parts 1–3 write about 2000 lines of code, which total to about 1000
when you net out edits and deletions. That's small by browser
standards (hah!) but still a sizable project, where how you organize
it starts to matter.

Besides, the point of Web Browser Engineering isn't just to build a
working browser from scratch. It's also to explain how browsers are
structured internally and what they spend all their time doing—the
sort of knowledge that could make you a better web developer even if
you never plan to touch a browser code base. Again, for this purpose,
a high-level overview of how a browser is structured helps a lot.

I saw both of these factors when teaching last year. Over the course
of a few months, students see many different parts of a browser. When
it comes time to edit and refactor (like in [Chapter 10][reflow]) it's
easy to have only a hazy recollection of how the code you're
refactoring actually works. And since I wanted my students to come
away with an understanding of a browser's high-level components, I
wanted to give them a quick way to view the completed browser at an
intermediate level of detail somewhere between the full code listing
and the book's table of contents.

[reflow]: ../reflow.html

# Outlining code

Code outlines are a way to get that intermediate level of detail
directly from the code. It's inspired by code-folding as implemented
in many text editors, reducing functions and classes to single lines.
Plus, in this book's coding style, individual functions directly refer
to specific browser concepts and are usually organized into classes
that refer to specific browser components.

As far as I know, code folding (like a lot of text editor tools) is
generally based on regular expressions. So my first attempt at code
outlines was literally to `grep` the code for lines beginning with
`def` or `class`. That worked fairly well to identify functions and
classes, but gave the function definition lines unchanged, like this
one from the current Chapter 11 draft:

    def load(self, url, body=None):

I don't really want to show all of this. Default values aren't
important when you're trying to get a birds-eye view of the code, and
the `self` parameter that Python requires might be pedagogically
useful when writing code, but it's redundant when you're looking at an
outline where methods and functions are clearly distinct.

I could fix some of these by further mangling the text with regular
expressions, but then I remembered that Python comes with an `ast`
library that exposes the Python parser itself as a Python library.
Using a parser means I don't need ugly regular expressions, and
guarantees that I don't have to keep the limitations of those regular
expressions in mind as I edit the text.

Using the `ast` library is also really easy: I call `ast.parse` and
then walk the tree looking for `ClassDef`, `FunctionDef`, and `Assign`
expressions, plus those unusual `if` statements that are Python's
version of `int main()`. For classes I walk the class body looking for
function definitions, and for function definitions I extract the
argument names but not their values with:

``` {.python}
args = [arg.arg for arg in stmt.args.args if arg.arg != "self"]
```

I put all this logic into a little program, which takes the Python
file it outlines as an argument. Because I've got a copy of the
browser code at the end of each chapter (as files named `lab1.py`,
`lab2.py`, and so on) I can use the outliner to get an outline for
each chapter.

# Displaying the outlines

I want code outlines at the end of every chapter. But the book itself
is written in Markdown and converted to static HTML with Pandoc, so I
need to somehow run my parser/outliner inside Pandoc. Luckily, Pandoc
is [scriptable in Lua][pandoc-lua][^1] and also supports [custom
blocks][pandoc-blocks], which can furthermore be adorned with classes.
That means I can write a Pandoc plugin that detects blocks with the
`cmd` class and acts on them specifically:

``` {.lua}
function Div(el)
  if el.classes[1] == "cmd" then
    -- ...
  else
    return el
  end
end
```

[pandoc-lua]: https://pandoc.org/lua-filters.html
[pandoc-blocks]: https://pandoc.org/MANUAL.html#divs-and-spans

[^1]: First time I've had to use the language, so this part was pretty
    slow-going.
    
Pandoc will run this `Div` function on every custom block in the file,
and replace the actual block `el` with whatever this function returns.
I'll be replacing these `cmd` blocks with the results of running a
command like my parser/outliner.

In Pandoc, `Div` objects contain other block-level objects like
paragraphs and code blocks. To avoid problems with punctuation and
inline markup, I decided that the actual command should be inside a
code block:

``` {.lua}
if #el.content ~= 1 or
   el.content[1].t ~= "CodeBlock" then
  error("`cmd` block does not contain a code block")
end
local cmd = el.content[1].text
```

Here `#el.content` gets the length of the `content` list and `~=` is
Lua's not equals operator. Once the command is extracted, the `popen`
function can be used to run the command:

``` {.lua}
local proc = io.popen(cmd)
local results = proc:read("*all")
```

I'm not a Lua expert, but I think the colon means calling a function as a
method, while the dot means calling it like a namespaced member. The
`*all` argument to `read` is a special argument that tells `read` to
read the whole contents of the file descriptor.

Finally, I want to insert the results back into the Pandoc document.
That means returning a new Pandoc object from `Div` with the outliner
results. Initially, I returned a Pandoc `CodeBlock` object, which is
its name for source code:

``` {.lua}
local pre = pandoc.CodeBlock(results)
pre.classes = el.classes
return pre
```

By copying classes from the original custom block to the new code
block, the new code block would have a `cmd` class that I could use to
add two columns, and I could also add a `python` class to add syntax
highlighting and other classes like `outline` to specify that this
specifically is an outline command.

# Styling the results

The outlines are fairly long. The current final copy of the code has
about 100 functions in 18 classes, and as I add more content that
might grow. But since I've only got argument names, each line is
pretty short; the longest one right now is 46 characters and it's an
outlier. So to make things more digestible I want to show the outline
in two columns, which is pretty easy in CSS:

``` {.css}
.outline { font-size: 60%; font-family: monospace; column-count: 2; }
```

The small font size works out to 15 pixels, small but still readable.
And remember, all the information in the outline is still available in
the other code blocks.

But two columns had a problem: the column break could happen in the
middle of a class, which would look ugly and also lead to confusion
about which function definitions are indented (because they are
methods) and which are not. The `break-inside` property in CSS
prevents that, but I didn't have any HTML element around individual
classes, since I was presenting the output as a source block.

The only way I could think of to fix this (other than rearranging my
code so that column breaks only occur between classes) was to
produce richer output than raw text. In Pandoc you can use the
`RawBlock` construct to do that:

``` {.lua}
pre = pandoc.Div({ pandoc.RawBlock("html", results) })
```

A `RawBlock` is ignored unless Pandoc is converting to the named
format, so if I ever want to publish this book as an EPUB or PDF file,
I'll need to continue working on this bit of the code, but for now
HTML is enough. Outputting HTML meant the output wouldn't be
syntax-highlighted any more, but luckily the outliner itself already
has access to a parsed AST, so I could add the syntax highlighting
myself:

``` {.python}
class IfMain:
    def html(self):
        str = "if __name__ == \"__main__\""
        return str.replace("if", "<span class=cf>if</span>") \
            .replace("==", "<span class=op>==</span>") \
            .replace("\"__main__\"", "<span class=st>\"__main__\"</span>")
```

Each top-level object in the outline is wrapped in a `code.line`
element, and I add the `break-inside` property to that. I also add a
little bit of whitespace between the top-level elements (which are
mostly classes) and indent class contents by two spaces:

``` {.css}
.outline code { break-inside: avoid; display: block; }
.outline > code { margin: .33em 0; }
.outline code > code { margin-left: 2ch; }
```

A benefit of producing my own HTML is that I can also stray a bit
further from Python syntax. I already don't output colons for function
definitions (to save space and since they don't have a body anyway),
but I've been thinking of merging constructors with the class header
too. Right now the final chapter's outline is about two screens of
text, and if by some tricks I can cut it down to one that would be
fantastic.
