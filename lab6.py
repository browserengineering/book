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

class Node(list):
    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = attrs
        self.style = HTML.parse_style(attrs.get("style", "")) if tag else {}
        self.parent = None

        self.x = None
        self.y = None
        self.w = None
        self.h = None
        self.tstyle = None

    def append(self, n):
        super(Node, self).append(n)
        n.parent = self

class HTML:
    Tag = collections.namedtuple("Tag", ["tag", "attrs"])

    @staticmethod
    def parse_attrs(tag):
        ts = tag.split(" ", 1)
        if len(ts) == 1:
            return tag, {}
        else:
            parts = ts[1].split("=")
            parts = [parts[0]] + sum([thing.rsplit(" ", 1) for thing in parts[1:-1]], []) + [parts[-1]]
            return ts[0], { a: b.strip("'").strip('"') for a, b in zip(parts[::2], parts[1::2]) }
    
    @staticmethod
    def parse_style(attr):
        return dict([x.strip() for x in y.split(":")] for y in attr.strip(";").split(";")) if ";" in attr or ":" in attr else {}
    
    @staticmethod
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
                    head, attrs = HTML.parse_attrs(tag.rstrip("/").strip())
                    yield HTML.Tag(head, attrs)
                    if tag.endswith("/"): yield HTML.Tag("/" + head, None)
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
        style = []
        for tok in tokens:
            if isinstance(tok, HTML.Tag):
                if tok.tag.startswith("/"):
                    assert not tok.attrs
                    path.pop()
                    assert tok.tag == "/" + path[-1][-1].tag
                    if path[-1][-1].tag == "style":
                        assert len(path[-1][-1]) == 1
                        assert path[-1][-1][0].tag is None
                        style.append(path[-1][-1][0].attrs)
                        path[-1].pop()
                else:
                    n = Node(tok.tag, tok.attrs)
                    path[-1].append(n)
                    path.append(n)
            else:
                path[-1].append(Node(None, tok))
        assert len(path) == 1
        assert len(path[0]) == 1
        return path[0][0], style

class CSS:
    @staticmethod
    def parse(source):
        i = 0
        while True:
            try:
                j = source.index("{", i)
            except ValueError as e:
                break
            
            sel = source[i:j].strip()
            i, j = j + 1, source.index("}", j)
            props = {}

            while i < j:
                try:
                    k = source.index(":", i)
                except ValueError as e:
                    break
                if k > j: break
                prop = source[i:k].strip()
                l = min(source.index(";", k + 1), j)
                val = source[k+1:l].strip()
                props[prop] = val
                if l == j: break
                i = l + 1
            yield sel, props
            i = j + 1
    
    @staticmethod
    def applies(sel, t):
        if t.tag is None:
            return False
        elif sel.startswith("."):
            return sel[1:] in t.attrs.get("class", "").split(" ")
        elif sel.startswith("#"):
            return sel[1:] == t.attrs.get("id", None)
        else:
            return sel == t.tag

    @staticmethod
    def px(val):
        return int(val.rstrip("px"))

def style(rules, t):
    for sel, props in reversed(rules):
        if CSS.applies(sel, t):
            for prop, val in props.items():
                t.style.setdefault(prop, val)
    for subt in t:
        style(rules, subt)

def inherit(t, prop, default):
    if t is None:
        return default
    else:
        return t.style[prop] if prop in t.style else inherit(t.parent, prop, default)

def layout(t, x, y):
    if t.tag is None:
        t.x, t.y, t.tstyle = x, y, t.parent.tstyle

        fs, weight, slant, decoration, color = t.tstyle
        font = tkFont.Font(family="Times", size=fs, weight=weight,
                           slant=slant, underline=(decoration == "underline"))
        for word in t.attrs.split():
            w = font.measure(word)
            if x + w > 800 - 2*8:
                y += fs * 1.75
                x = 8
            x += font.measure(word) + 6
        t.h = y - t.y + fs * 1.75
        t.w = x - t.x
    else:
        if "font-size" in t.style: fs = CSS.px(t.style["font-size"])
        if "margin-left" in t.style: x += CSS.px(t.style["margin-left"])
        if "margin-top" in t.style: y += CSS.px(t.style["margin-top"])

        if t.tag == "hr": y += int(t.attrs.get("width", "2"))

        t.x = x
        t.y = y
        t.tstyle = (CSS.px(inherit(t, "font-size", "16px")),
                    inherit(t, "font-weight", "normal"),
                    inherit(t, "font-style", "roman"),
                    inherit(t, "text-decoration", "none"),
                    inherit(t, "color", "black"))
            
        x_ = x
        for c in t:
            x_, y = layout(c, x_, y)
        x = x_ if t.tag in "abi" else x

        if "margin-bottom" in t.style: y += CSS.px(t.style["margin-bottom"])
        if "margin-left" in t.style: x -= CSS.px(t.style["margin-left"])

        if t.tag in ["p", "h1", "h2", "h3", "li"]:
            y = t[-1].y + t[-1].h
        t.h = y - t.y

    return x, y

def render(canvas, t, scrolly):
    if t.tag is None:
        fs, weight, slant, decoration, color = t.tstyle
        font = tkFont.Font(family="Times", size=fs, weight=weight,
                           slant=slant, underline=(decoration == "underline"))

        x, y = t.x, t.y - scrolly
        for word in t.attrs.split():
            w = font.measure(word)
            if x + w > 800 - 2*8:
                y += 28
                x = 8
            canvas.create_text(x, y, text=word, font=font, anchor=tkinter.NW, fill=color)
            x += font.measure(word) + 6
    else:
        if t.tag == "li":
            x, y, fs, color = t.x - 16, t.y - scrolly, t.tstyle[0], t.tstyle[4]
            canvas.create_oval(x + 2, y + fs / 2 - 3, x + 7, y + fs / 2 + 2, fill=color, outline=color)
        elif t.tag == 'hr':
            x, y, color = t.x, t.y - scrolly, t.tstyle[4]
            width = int(t.attrs.get("width", "2"))
            canvas.create_line(x, y, 800 - x, y, width=width, fill=color)

        for subt in t:
            render(canvas, subt, scrolly=scrolly)

def show(source):
    with open("default.css") as f:
        rules = list(CSS.parse(f.read()))
    tree, styles = HTML.parse(HTML.lex(source))
    for s in styles:
        rules.extend(list(CSS.parse(s)))
    style(rules, tree)

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

    layout(tree, x=8, y=8)
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
