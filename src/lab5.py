"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 5 (Laying out Pages),
without exercises.
"""

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
    def __init__(self, text):
        parts = text.split()
        self.tag = parts[0].lower()
        self.attributes = {}
        for attrpair in parts[1:]:
            if "=" in attrpair:
                key, value = attrpair.split("=", 1)
                if len(value) > 2 and value[0] in ["'", "\""]:
                    value = value[1:-1]
                self.attributes[key.lower()] = value
            else:
                self.attributes[attrpair.lower()] = ""

    def __repr__(self):
        return "<" + self.tag + ">"

def lex(body):
    out = []
    text = ""
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
            if text: out.append(Text(text))
            text = ""
        elif c == ">":
            in_tag = False
            out.append(Tag(text))
            text = ""
        else:
            text += c
    if not in_tag and text:
        out.append(Text(text))
    return out

class ElementNode:
    def __init__(self, tag, parent, attributes):
        self.tag = tag
        self.parent = parent
        self.attributes = attributes
        self.children = []

    def __repr__(self):
        return "<" + self.tag + ">"

class TextNode:
    def __init__(self, text, parent):
        self.text = text
        self.parent = parent
        self.children = []

    def __repr__(self):
        return self.text.replace("\n", "\\n")
        
def parse(tokens):
    currently_open = []
    for tok in tokens:
        parent = currently_open[-1] if currently_open else None

        implicit_tags(tok, currently_open)
        if isinstance(tok, Text):
            if tok.text.isspace(): continue
            node = TextNode(tok.text, parent)
            parent.children.append(node)
        elif tok.tag.startswith("/"):
            node = currently_open.pop()
            if not currently_open: return node
            currently_open[-1].children.append(node)
        elif tok.tag in SELF_CLOSING_TAGS:
            node = ElementNode(tok.tag, tok.attributes, parent)
            parent.children.append(node)
        elif tok.tag.startswith("!"):
            continue
        else:
            node = ElementNode(tok.tag, parent, tok.attributes)
            currently_open.append(node)
    while currently_open:
        node = currently_open.pop()
        if not currently_open: return node
        currently_open[-1].children.append(node)

HEAD_TAGS = [
    "base", "basefont", "bgsound", "noscript",
    "link", "meta", "title", "style", "script",
]
            
def implicit_tags(tok, currently_open):
    tag = tok.tag if isinstance(tok, Tag) else None
    while True:
        open_tags = [node.tag for node in currently_open]
        if open_tags == [] and tag != "html":
            currently_open.append(ElementNode("html", None, {}))
        elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
            if tag in HEAD_TAGS:
                implicit = "head"
            else:
                implicit = "body"
            parent = currently_open[-1]
            currently_open.append(ElementNode(implicit, parent, {}))
        elif open_tags == ["html", "head"] and tag not in ["/head"] + HEAD_TAGS:
            node = currently_open.pop()
            parent = currently_open[-1]
            parent.children.append(node)
        else:
            break

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
LINEHEIGHT = 1.2

SCROLL_STEP = 100

class InlineLayout:
    def __init__(self, node, parent):
        self.node = node
        self.parent = parent
        self.children = []

        self.x = -1
        self.y = -1
        self.w = -1
        self.h = -1

    def layout(self):
        self.w = self.parent.w
        self.display_list = []

        self.cx = self.x
        self.cy = self.y
        self.weight = "normal"
        self.style = "roman"
        self.size = 16

        self.line = []
        self.recurse(self.node)
        self.flush()

        self.h = self.cy - self.y

    def recurse(self, node):
        if isinstance(node, TextNode):
            self.text(node.text)
        else:
            self.open(node.tag)
            for child in node.children:
                self.recurse(child)
            self.close(node.tag)

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
            self.cy += VSTEP
        
    def text(self, text):
        font = tkinter.font.Font(
            size=self.size,
            weight=self.weight,
            slant=self.style,
        )
        for word in text.split():
            w = font.measure(word)
            if self.cx + w > WIDTH - HSTEP:
                self.flush()
            self.line.append((self.cx, word, font))
            self.cx += w + font.measure(" ")

    def flush(self):
        if not self.line: return
        metrics = [font.metrics() for x, word, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cy + 1.2 * max_ascent
        for x, word, font in self.line:
            y = baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))
        self.cx = self.x
        self.line = []
        max_descent = max([metric["descent"] for metric in metrics])
        self.cy = baseline + 1.2 * max_descent

    def draw(self, to):
        for x, y, word, font in self.display_list:
            to.append(DrawText(x, y, word, font))

INLINE_ELEMENTS = [
    "a", "em", "strong", "small", "s", "cite", "q", "dfn", "abbr",
    "ruby", "rt", "rp", "data", "time", "code", "var", "samp",
    "kbd", "sub", "sup", "i", "b", "u", "mark", "bdi", "bdo",
    "span", "br", "wbr", "big"
]

class BlockLayout:
    def __init__(self, node, parent):
        self.node = node
        self.parent = parent
        self.children = []

        self.x = -1
        self.y = -1
        self.w = -1
        self.h = -1

    def has_block_children(self):
        for child in self.node.children:
            if isinstance(child, TextNode):
                if not child.text.isspace():
                    return False
            elif child.tag in INLINE_ELEMENTS:
                return False
        return True

    def layout(self):
        # block layout here
        if self.has_block_children():
            for child in self.node.children:
                if isinstance(child, TextNode): continue
                self.children.append(BlockLayout(child, self))
        else:
            self.children.append(InlineLayout(self.node, self))

        self.w = self.parent.w
        y = self.y
        for child in self.children:
            child.x = self.x
            child.y = y
            child.layout()
            y += child.h
        self.h = y - self.y

    def draw(self, to):
        if self.node.tag == "pre":
            x2, y2 = self.x + self.w, self.y + self.h
            to.append(DrawRect(self.x, self.y, x2, y2, "gray"))
        for child in self.children:
            child.draw(to)

class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.children = []

        self.x = -1
        self.y = -1
        self.w = -1
        self.h = -1

    def layout(self):
        self.w = WIDTH
        child = BlockLayout(self.node, self)
        self.children.append(child)

        child.x = self.x = 0
        child.y = self.y = 0
        child.layout()
        self.h = child.h

    def draw(self, to):
        self.children[0].draw(to)

class DrawText:
    def __init__(self, x1, y1, text, font):
        self.x1 = x1
        self.y1 = y1
        self.text = text
        self.font = font

        self.y2 = y1 + font.metrics("linespace")

    def draw(self, scroll, canvas):
        canvas.create_text(
            self.x1, self.y1 - scroll,
            text=self.text,
            font=self.font,
            anchor='nw',
        )

class DrawRect:
    def __init__(self, x1, y1, x2, y2, color):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.color = color

    def draw(self, scroll, canvas):
        canvas.create_rectangle(
            self.x1, self.y1 - scroll,
            self.x2, self.y2 - scroll,
            width=0,
            fill=self.color,
        )

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
        document = DocumentLayout(tree)
        document.layout()
        self.display_list = []
        document.draw(self.display_list)
        self.render()
        self.max_y = document.h - HEIGHT

    def render(self):
        self.canvas.delete("all")
        for cmd in self.display_list:
            if cmd.y1 > self.scroll + HEIGHT: continue
            if cmd.y2 < self.scroll: continue
            cmd.draw(self.scroll, self.canvas)

    def scrolldown(self, e):
        self.scroll = self.scroll + SCROLL_STEP
        self.scroll = min(self.scroll, self.max_y)
        self.scroll = max(0, self.scroll))
        self.render()

if __name__ == "__main__":
    import sys
    headers, body = request(sys.argv[1])
    nodes = parse(lex(body))
    browser = Browser()
    browser.layout(nodes)
    tkinter.mainloop()
