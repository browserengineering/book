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

def parse_attrs(tag):
    ts = tag.split(" ", 1)
    if len(ts) == 1:
        return tag, {}
    else:
        parts = ts[1].split("=")
        parts = [parts[0]] + sum([thing.rsplit(" ", 1) for thing in parts[1:-1]], []) + [parts[-1]]
        return ts[0], { a: b.strip("'").strip('"') for a, b in zip(parts[::2], parts[1::2]) }

def parse_style(attr):
    return dict([x.strip() for x in y.split(":")] for y in attr.strip(";").split(";")) if ";" in attr or ":" in attr else {}

def lex(source):
    source = " ".join(source.split())
    tag = None
    text = None
    for c in source:
        if c == "<":
            if text is not None: yield text
            text = None
            tag = ""
        elif c == ">":
            if tag is not None:
                head, attrs = parse_attrs(tag.rstrip("/").strip())
                yield Tag(head, attrs)
                if tag.endswith("/"): yield Tag("/" + head, None)
            tag = None
        else:
            if tag is not None:
                tag += c
            elif text is not None:
                text += c
            else:
                text = c

def parse(tokens):
    path = [[]]
    for tok in tokens:
        if isinstance(tok, Tag):
            if tok.tag.startswith("/"):
                assert not tok.attrs
                path.pop()
                assert tok.tag == "/" + path[-1][-1].tag
            else:
                n = Node(tok.tag, tok.attrs)
                path[-1].append(n)
                path.append(n)
        else:
            path[-1].append(Node(None, tok))
    assert len(path) == 1
    assert len(path[0]) == 1
    return path[0][0]

class Node(list):
    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = attrs
        self.style = parse_style(attrs.get("style", "")) if tag else {}
        self.parent = None

        self.x = None
        self.y = None
        self.w = None
        self.h = None
        self.tstyle = None

    def append(self, n):
        super(Node, self).append(n)
        if isinstance(n, Node):
            n.parent = self

def layout(t, x, y, fs, bold, italic, inlink):
    if t.tag is None:
        font = tkFont.Font(family="Times", size=fs, weight=(tkFont.BOLD if bold else tkFont.NORMAL),
                           slant=(tkFont.ITALIC if italic else tkFont.ROMAN),
                           underline=(1 if inlink else 0))
        t.x = x
        t.y = y
        t.tstyle = (fs, 'bold' if bold else 'normal', 'italic' if italic else 'roman', inlink)

        for word in t.attrs.split():
            w = font.measure(word)
            if x + w > 800 - 2*8:
                y += 28
                x = 8
            x += font.measure(word) + 6
        t.h = y - t.y + 28
        t.w = x - t.x
    else:
        if "margin-left" in t.style:
            x += int(t.style["margin-left"].rstrip("px"))

        if t.tag == "b":
            bold = True
        elif t.tag == "i":
            italic = True
        elif t.tag == "a":
            inlink = True
        elif t.tag == "p":
            y += 16
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
        elif t.tag == "ul":
            y += 16
        elif t.tag == "li":
            x += 16
        elif t.tag in ["html", "body", "/html", "/body"]:
            pass
        elif t.tag == "hr":
            y += 8
            width = int(t.attrs.get("width", "2"))
            y += width + 8
        else:
            print("Unknown tag", t.tag)

        t.x = x
        t.y = y
        t.tstyle = (fs, "bold" if bold else "normal", "italic" if italic else "normal", inlink)
            
        x_, y_ = x, y
        for c in t:
            x_, y_ = layout(c, x_, y_, fs, bold, italic, inlink)
        y = y_
        if t.tag in "abi":
            x = x_

        t.h = y - t.y

        if "margin-left" in t.style:
            x -= int(t.style["margin-left"].rstrip("px"))

        if t.tag == "p":
            y += 28
            x = 8
        elif t.tag in ["h1", "h2", "h3"]:
            y += fs * 1.75
            x = 8
        elif t.tag == "ul":
            y += 16
        elif t.tag == "li":
            y += 28
            x -= 16

    return x, y

def render(canvas, t, scrolly):
    if t.tag is None:
        fs, weight, slant, inlink = t.tstyle
        font = tkFont.Font(family="Times", size=fs, weight=weight, slant=slant,
                           underline=(1 if inlink else 0))

        x, y = t.x, t.y - scrolly
        for word in t.attrs.split():
            w = font.measure(word)
            if x + w > 800 - 2*8:
                y += 28
                x = 8
            canvas.create_text(x, y, text=word, font=font, anchor=tkinter.NW, fill=("blue" if inlink else "black"))
            x += font.measure(word) + 6
    else:
        if t.tag == "li":
            x, y, fs = t.x - 16, t.y - scrolly, t.tstyle[0]
            canvas.create_oval(x + 2, y + fs / 2 - 3, x + 7, y + fs / 2 + 2, fill="black")
        elif t.tag == 'hr':
            x, y = t.x, t.y - scrolly
            width = int(t.attrs.get("width", "2"))
            canvas.create_line(x, y, 800 - x, y, width=width)

        for subt in t:
            render(canvas, subt, scrolly=scrolly)

def show(source):
    tree = parse(lex(source))
    scrolly = 0

    def scroll(by):
        def handler(e):
            nonlocal scrolly
            scrolly += by
            if scrolly < 0: scrolly = 0
            canvas.delete("all")
            render(canvas, tree, scrolly=scrolly)
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

    layout(tree, x=8, y=8, fs=16, bold=False, italic=False, inlink=False)
    scroll(0)(None)

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
