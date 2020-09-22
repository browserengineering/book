import socket
import ssl
import tkinter
import tkinter.font

def request(url):
    scheme, url = url.split("://", 1)
    assert scheme in ["http", "https"], \
        "Unknown scheme {}".format(scheme)

    host, path = url.split("/", 1)
    path = "/" + path
    port = 80 if scheme == "http" else 443

    if ":" in host:
        host, port = host.split(":", 1)
        port = int(port)

    s = socket.socket(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
    )
    s.connect((host, port))

    if scheme == "https":
        ctx = ssl.create_default_context()
        s = ctx.wrap_socket(s, server_hostname=host)

    s.send(("GET {} HTTP/1.0\r\n".format(path) +
            "Host: {}\r\n\r\n".format(host)).encode("utf8"))
    response = s.makefile("r", encoding="utf8", newline="\r\n")

    statusline = response.readline()
    version, status, explanation = statusline.split(" ", 2)
    assert status == "200", "{}: {}".format(status, explanation)

    headers = {}
    while True:
        line = response.readline()
        if line == "\r\n": break
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()

    body = response.read()
    s.close()

    return headers, body

class Text:
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return "\"" + self.text.replace("\n", "\\n") + "\""

SELF_CLOSING_TAGS = [
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
]

class Tag:
    def __init__(self, parts):
        self.tag = parts[0]
        self.attributes = {}
        for i in range(1, len(parts), 2):
            self.attributes[parts[i]] = parts[i+1]

    def __repr__(self):
        return "<" + self.tag + ">"

def lex(body):
    out = []
    text = ""
    state = "text"
    tag_parts = []
    for c in body:
        if state == "text":
            if c == "<":
                if text: out.append(Text(text))
                text = ""
                tag_parts = []
                state = "tagname"
            else:
                text += c
        elif state == "tagname":
            if c == ">":
                tag_parts.append(text.lower())
                out.append(Tag(tag_parts))
                text = ""
                state = "text"
            elif c.isspace():
                if text:
                    tag_parts.append(text.lower())
                    text = ""
                    state = "attribute"
                else:
                    text = "<"
                    state = "text"
            else:
                text += c
        elif state == "attribute":
            if c == "=":
                tag_parts.append(text.lower())
                text = ""
                state = "value"
            elif c.isspace():
                if text:
                    tag_parts.append(text.lower())
                    tag_parts.append("")
                text = ""
            elif c == ">":
                if text:
                    tag_parts.append(text.lower())
                    tag_parts.append("")
                out.append(Tag(tag_parts))
                text = ""
                state = "text"
            else:
                text += c
        elif state == "value":
            if c == "\"":
                state = "quoted"
            elif c == ">":
                tag_parts.append(text)
                out.append(Tag(tag_parts))
                text = ""
                state = "text"
            elif c.isspace():
                tag_parts.append(text)
                text = ""
                state = "attribute"
            else:
                text += c
        elif state == "quoted":
            if c == "\"":
                state = "value"
            else:
                text += c
        else:
            raise Exception("Unknown state " + state)
    if state == "text" and text:
        out.append(Text(text))
    return out

class ElementNode:
    def __init__(self, tag):
        self.tag = tag
        self.children = []

    def __repr__(self):
        return "<" + self.tag + ">"

class TextNode:
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return self.text.replace("\n", "\\n")
        
def parse(tokens):
    currently_open = []
    for tok in tokens:
        if isinstance(tok, Text):
            node = TextNode(tok.text)
            if not currently_open: continue
            currently_open[-1].children.append(node)
        elif tok.tag.startswith("/"):
            node = currently_open.pop()
            if not currently_open: return node
            currently_open[-1].children.append(node)
        elif tok.tag in SELF_CLOSING_TAGS:
            node = ElementNode(tok.tag)
            currently_open[-1].children.append(node)
        elif tok.tag == "!doctype":
            continue
        else:
            node = ElementNode(tok.tag)
            currently_open.append(node)

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
LINEHEIGHT = 1.2

SCROLL_STEP = 100

class Layout:
    def __init__(self, tree):
        self.display_list = []

        self.x = HSTEP
        self.y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 16

        self.line = []
        self.layout(tree)

    def layout(self, tree):
        if isinstance(tree, TextNode):
            self.text(tree.text)
        else:
            self.open(tree.tag)
            for child in tree.children:
                self.layout(child)
            self.close(tree.tag)

    def open(self, tag):
        if tag == "i":
            self.style = "italic"
        elif tag == "b":
            self.weight = "bold"
        elif tag == "small":
            self.size -= 2
        elif tag == "big":
            self.size += 4
        elif tag == "br":
            self.flush()

    def close(self, tag):
        if tag == "i":
            self.style = "roman"
        elif tag == "b":
            self.weight = "normal"
        elif tag == "small":
            self.size += 2
        elif tag == "big":
            self.size -= 4
        elif tag == "p":
            self.flush()
            self.y += VSTEP
        
    def text(self, text):
        font = tkinter.font.Font(
            size=self.size,
            weight=self.weight,
            slant=self.style,
        )
        for word in text.split():
            w = font.measure(word)
            if self.x + w > WIDTH - HSTEP:
                self.flush()
            self.line.append((self.x, word, font))
            self.x += w + font.measure(" ")

    def flush(self):
        if not self.line: return
        metrics = [font.metrics() for x, word, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.y + 1.2 * max_ascent
        for x, word, font in self.line:
            y = baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))
        self.x = HSTEP
        self.line = []
        max_descent = max([metric["descent"] for metric in metrics])
        self.y = baseline + 1.2 * max_descent

class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT
        )
        self.canvas.pack()

        self.scroll = 0
        self.window.bind("<Down>", self.scrolldown)
        self.display_list = []

    def layout(self, tree):
        self.display_list = Layout(tree).display_list
        self.render()

    def render(self):
        self.canvas.delete("all")
        for x, y, word, font in self.display_list:
            if y > self.scroll + HEIGHT: continue
            if y + font.metrics("linespace") < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=word, font=font, anchor="nw")

    def scrolldown(self, e):
        self.scroll += SCROLL_STEP
        self.render()

if __name__ == "__main__":
    import sys
    headers, body = request(sys.argv[1])
    text = parse(lex(body))
    browser = Browser()
    browser.layout(text)
    tkinter.mainloop()
