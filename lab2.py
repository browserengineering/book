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

            if tag is not None:
                tag += c
            elif text is not None:
                text += c
            else:
                text = c

def show(source):
    window = tkinter.Tk()
    canvas = tkinter.Canvas(window, width=800, height=600)
    canvas.pack()

    fonts = {
        "roman": tkFont.Font(family="Times", size=16),
        "bold": tkFont.Font(family="Times", size=16, weight=tkFont.BOLD),
        "italic": tkFont.Font(family="Times", size=16, slant=tkFont.ITALIC),
        "bolditalic": tkFont.Font(family="Times", size=16, weight=tkFont.BOLD, slant=tkFont.ITALIC),
    }

    x = 30
    y = 16

    bold = False
    italic = False
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
            else:
                pass
        elif isinstance(t, Text):
            for word in t.text.split():
                font = fonts["roman" if not bold and not italic else "bold" if not italic else "italic" if not bold else "bolditalic"]
                canvas.create_text(x, y, text=word, font=font)
                x += font.measure(word) + 10
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
