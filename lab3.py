import subprocess
import tkinter
import tkinter.font as tkFont
import collections

def get(domain, path):
    if ":" in domain:
        domain, port = domain.rsplit(":", 1)
    else:
        port = "80"
    s = subprocess.Popen(["telnet", domain, port], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    s.stdin.write(("GET " + path + " HTTP/1.0\n\n").encode("latin1"))
    s.stdin.flush()
    out = s.stdout.read().decode("latin1")
    return out.split("\r\n", 3)[-1]

Tag = collections.namedtuple("Tag", ["tag"])
Text = collections.namedtuple("Word", ["text"])

def lex(source):
    tag = None
    text = None
    last_space = False
    for c in source:
        if c == "<":
            if text is not None: yield Text(text)
            text = None
            tag = ""
        elif c == ">":
            if tag is not None: yield Tag(tag)
            tag = None
        else:
            if c.isspace():
                if last_space:
                    continue
                else:
                    last_space = True
            else:
                last_space = False

            if tag is not None:
                tag += c
            elif text is not None:
                text += c
            else:
                text = c

def layout(source):
    fonts = {
        (False, False): tkFont.Font(family="Times", size=16),
        (True, False): tkFont.Font(family="Times", size=16, weight="bold"),
        (False, True): tkFont.Font(family="Times", size=16, slant="italic"),
        (True, True): tkFont.Font(family="Times", size=16, weight="bold", slant="italic"),
    }

    x = 8
    y = 8

    bold = False
    italic = False
    terminal_space = True
    for t in lex(source):
        if isinstance(t, Tag):
            if t.tag == "b":
                bold = True
            elif t.tag == "i":
                italic = True
            elif t.tag == "/b":
                bold = False
            elif t.tag == "/i":
                italic = False
            elif t.tag == "/p":
                y += 28 + 14
                x = 8
                terminal_space = True
            else:
                pass
        elif isinstance(t, Text):
            font = fonts[bold, italic]
            spw = font.measure(" ")
            if t.text[0].isspace() and not terminal_space: x += spw
            words = t.text.split()
            for i, word in enumerate(words):
                w = font.measure(word)
                if x + w > 800 - 8:
                    y += 28
                    x = 8
                yield x, y, word, font
                x += font.measure(word) + (0 if i == len(words) - 1 else spw)
            terminal_space = t.text[-1].isspace()
            if terminal_space and len(words) > 0: x += spw

def show(source):
    window = tkinter.Tk()
    canvas = tkinter.Canvas(window, width=800, height=600)
    canvas.pack()

    dl = list(layout(source))

    def render():
        canvas.delete('all')
        for x, y, word, font in dl:
            if y - scrolly + 22 > 0 and y < 600:
                canvas.create_text(x, y - scrolly, text=word, font=font, anchor='nw')

    scrolly = 0
    def scroll(by):
        def handler(e):
            nonlocal scrolly
            scrolly += by
            if scrolly < 0: scrolly = 0
            render()
        return handler

    window.bind("<Down>", scroll(100))
    window.bind("<space>", scroll(400))
    window.bind("<Up>", scroll(-100))

    render()
    tkinter.mainloop()

def run(url):
    assert url.startswith("http://")
    url = url[len("http://"):]
    domain, path = url.split("/", 1)
    response = get(domain, "/" + path)
    headers, source = response.split("\n\n", 1)
    show(source)

if __name__ == "__main__":
    import sys
    run(sys.argv[1])
