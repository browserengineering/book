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

Tag = collections.namedtuple("Tag", ["tag", "attrs"])
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
            if tag is not None:
                parts = tag.rstrip("/").strip().split(" ")
                attrs = { part.split("=", 1)[0]: part.split("=", 1)[1].strip('"') for part in parts[1:] if "=" in part }
                yield Tag(parts[0], attrs)
                if tag.endswith("/"): yield Tag("/" + parts[0], "")
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

def render(canvas, tokens, yoffset=0):
    canvas.delete("all")
    x = 8
    y = -yoffset + 8

    fs = 16
    bold = False
    italic = False
    inlink = False

    for t in tokens:
        if isinstance(t, Tag):
            if t.tag == "b":
                bold = True
            elif t.tag == "i":
                italic = True
            elif t.tag == "/b":
                bold = False
            elif t.tag == "/i":
                italic = False
            elif t.tag == "a":
                inlink = True
            elif t.tag == "/a":
                inlink = False
            elif t.tag == "p":
                y += 16
            elif t.tag == "/p":
                y += 28
                x = 8
            elif t.tag == "h1":
                fs = 24
                bold = True
                y += 32
            elif t.tag == "h2":
                fs = 20
                bold = True
                y += 20
            elif t.tag == "h3":
                fs = 18
                italic = True
                y += 9
            elif t.tag in ["/h1", "/h2", "/h3"]:
                y += fs * 1.75
                x = 8
                fs = 16
                bold = italic = False
            elif t.tag == "ul":
                y += 16
            elif t.tag == "/ul":
                y += 16
            elif t.tag == "li":
                canvas.create_oval(x + 2, y + fs / 2 - 3, x + 7, y + fs / 2 + 2, fill="black")
                x += 16
            elif t.tag == "/li":
                y += 28
                x = 8
            elif t.tag in ["html", "body", "/html", "/body"]:
                pass
            elif t.tag == "hr":
                y += 8
                width = int(t.attrs.get("width", "2"))
                canvas.create_line(x, y, 800 - x, y, width=width)
                y += width + 8
            elif t.tag == "/hr":
                pass
            else:
                print("Unknown tag", t.tag)
        elif isinstance(t, Text):
            font = tkFont.Font(family="Times", size=fs, weight=(tkFont.BOLD if bold else tkFont.NORMAL),
                               slant=(tkFont.ITALIC if italic else tkFont.ROMAN),
                               underline=(1 if inlink else 0))

            for word in t.text.split():
                w = font.measure(word)
                if x + w > 800 - 2*8:
                    y += 28
                    x = 8
                canvas.create_text(x, y, text=word, font=font, anchor=tkinter.NW, fill=("blue" if inlink else "black"))
                x += font.measure(word) + 6

def show(source):
    tokens = list(lex(source))
    scrolly = 0

    def scroll(by):
        def handler(e):
            nonlocal scrolly
            scrolly += by
            if scrolly < 0: scrolly = 0
            render(canvas, tokens, yoffset=scrolly)
        return handler

    window = tkinter.Tk()
    frame = tkinter.Frame(window, width=800, height=1000)
    frame.bind("<Down>", scroll(100))
    frame.bind("<space>", scroll(400))
    frame.bind("<Up>", scroll(-100))
    frame.pack()
    frame.focus_set()
    canvas = tkinter.Canvas(frame, width=800, height=1000)
    canvas.pack()

    render(canvas, tokens, yoffset=scrolly)

    window.mainloop()

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
