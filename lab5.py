import socket
import tkinter
import tkinter.font

def parse_url(url):
    assert url.startswith("http://")
    url = url[len("http://"):]
    hostport, pathfragment = url.split("/", 1) if "/" in url else (url, "")
    host, port = hostport.rsplit(":", 1) if ":" in hostport else (hostport, "80")
    path, fragment = ("/" + pathfragment).rsplit("#", 1) if "#" in pathfragment else ("/" + pathfragment, None)
    return host, int(port), path, fragment

def request(host, port, path):
    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    s.connect((host, port))
    s.send("GET {} HTTP/1.0\r\nHost: {}\r\n\r\n".format(path, host).encode("utf8"))
    response = s.makefile("rb").read().decode("utf8")
    s.close()

    head, body = response.split("\r\n\r\n", 1)
    lines = head.split("\r\n")
    version, status, explanation = lines[0].split(" ", 2)
    assert status == "200", "Server error {}: {}".format(status, explanation)
    headers = {}
    for line in lines[1:]:
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()
    return headers, body

class Text:
    def __init__(self, text):
        self.text = text

class Tag:
    def __init__(self, tag):
        self.tag = tag

def lex(source):
    out = []
    text = ""
    in_angle = False
    for c in source:
        if c == "<":
            in_angle = True
            if text: out.append(Text(text))
            text = ""
        elif c == ">":
            in_angle = False
            out.append(Tag(text))
            text = ""
        else:
            text += c
    return out

class ElementNode:
    def __init__(self, parent, tagname):
        self.tag, *attrs = tagname.split(" ")
        self.children = []
        self.attributes = {}
        self.parent = parent

        for attr in attrs:
            out = attr.split("=", 1)
            name = out[0]
            val = out[1].strip("\"") if len(out) > 1 else ""
            self.attributes[name.lower()] = val

class TextNode:
    def __init__(self, parent, text):
        self.text = text
        self.parent = parent

def parse(tokens):
    current = None
    for tok in tokens:
        if isinstance(tok, Tag):
            if tok.tag.startswith("/"): # Close tag
                tag = tok.tag[1:]
                node = current
                while node is not None and node.tag != tag:
                    node = node.parent
                if not node and current.parent is not None:
                    current = current.parent
                elif node.parent is not None:
                    current = node.parent
            else: # Open tag
                new = ElementNode(current, tok.tag)
                if current is not None: current.children.append(new)
                if new.tag not in ["br", "link", "meta"]:
                    current = new
        else: # Text token
            new = TextNode(current, tok.text)
            current.children.append(new)
    return current

class Page:
    def __init__(self):
        self.x = 13
        self.y = 13
        self.w = 774
        self.children = []

    def content_left(self):
        return self.x
    def content_top(self):
        return self.y
    def content_width(self):
        return self.w

def is_inline(node):
    return isinstance(node, TextNode) and not node.text.isspace() or \
        isinstance(node, ElementNode) and node.tag in ["b", "i"]

class BlockLayout:
    def __init__(self, parent, y):
        self.parent = parent
        self.children = []
        parent.children.append(self)
        
        self.mt = self.mr = self.mb = self.ml = 0
        self.bt = self.br = self.bb = self.bl = 0
        self.pt = self.pr = self.pb = self.pl = 0

        self.x = parent.content_left()
        self.y = y
        self.w = parent.content_width()
        self.h = None

    def layout(self, node):
        self.x += self.ml
        self.y += self.mt
        self.w -= self.ml + self.mr
        if node.tag == "p":
            self.mb = 16
        elif node.tag == "ul":
            self.mt = self.mb = 16
            self.pl = 20
        elif node.tag == "li":
            self.mb = 8
        elif node.tag == "pre":
            self.ml = self.mr = 8
            self.bt = self.br = self.bb = self.bl = 1
            self.pt = self.pr = self.pb = self.pl = 8

        y = self.y + self.bt + self.pt
        if any(is_inline(child) for child in node.children):
            layout = InlineLayout(self)
            layout.layout(node)
            y += layout.height()
        else:
            for child in node.children:
                if isinstance(child, TextNode) and child.text.isspace(): continue
                layout = BlockLayout(self, y)
                layout.layout(child)
                y += layout.height() + layout.mt + layout.mb
        y += self.pb + self.bb
        self.h = y - self.y

    def height(self):
        return self.h

    def display_list(self):
        dl = []
        for child in self.children:
            dl.extend(child.display_list())
        if self.bl > 0: dl.append(DrawRect(self.x, self.y, self.x + self.bl, self.y + self.h))
        if self.br > 0: dl.append(DrawRect(self.x + self.w - self.br, self.y, self.x + self.w, self.y + self.h))
        if self.bt > 0: dl.append(DrawRect(self.x, self.y, self.x + self.w, self.y + self.bt))
        if self.bb > 0: dl.append(DrawRect(self.x, self.y + self.h - self.bb, self.x + self.w, self.y + self.h))
        return dl

    def content_left(self):
        return self.x + self.bl + self.pl
    def content_top(self):
        return self.y + self.bt + self.pt
    def content_width(self):
        return self.w - self.bl - self.br - self.pl - self.pr

class InlineLayout:
    def __init__(self, block):
        self.parent = block
        self.parent.children.append(self)
        self.x = block.content_left()
        self.y = block.content_top()
        self.bold = False
        self.italic = False
        self.terminal_space = True
        self.dl = []

    def font(self):
        return tkinter.font.Font(
            family="Times", size=16,
            weight="bold" if self.bold else "normal",
            slant="italic" if self.italic else "roman"
        )

    def height(self):
        font = self.font()
        return (self.y + font.metrics('linespace') * 1.2) - self.parent.y

    def display_list(self):
        return self.dl

    def layout(self, node):
        if isinstance(node, ElementNode):
            self.open(node)
            for child in node.children:
                self.layout(child)
            self.close(node)
        else:
            self.text(node)

    def open(self, node):
        if node.tag == "b":
            self.bold = True
        elif node.tag == "i":
            self.italic = True

    def close(self, node):
        if node.tag == "b":
            self.bold = False
        elif node.tag == "i":
            self.italic = False

    def text(self, node):
        font = self.font()

        if node.text[0].isspace() and not self.terminal_space:
            self.x += font.measure(" ")
        
        words = node.text.split()
        for i, word in enumerate(words):
            w = font.measure(word)
            if self.x + w > self.parent.content_left() + self.parent.content_width():
                self.x = self.parent.content_left()
                self.y += font.metrics('linespace') * 1.2
            self.dl.append(DrawText(self.x, self.y, word, font))
            self.x += w + (0 if i == len(words) - 1 else font.measure(" "))
        
        self.terminal_space = node.text[-1].isspace()
        if self.terminal_space and words:
            self.x += font.measure(" ")

class DrawText:
    def __init__(self, x, y, text, font):
        self.x = x
        self.y = y
        self.text = text
        self.font = font
    
    def draw(self, scrolly, canvas):
        canvas.create_text(self.x, self.y - scrolly, text=self.text, font=self.font, anchor='nw')

class DrawRect:
    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def draw(self, scrolly, canvas):
        canvas.create_rectangle(self.x1, self.y1 - scrolly, self.x2, self.y2 - scrolly)

def show(nodes):
    window = tkinter.Tk()
    canvas = tkinter.Canvas(window, width=800, height=600)
    canvas.pack()

    SCROLL_STEP = 100
    scrolly = 0
    page = Page()
    mode = BlockLayout(page, 0)
    mode.layout(nodes)
    maxh = mode.height()
    display_list = mode.display_list()

    def render():
        canvas.delete("all")
        for cmd in display_list:
            cmd.draw(scrolly, canvas)

    def scrolldown(e):
        nonlocal scrolly
        scrolly = min(scrolly + SCROLL_STEP, 13 + maxh - 600)
        render()

    window.bind("<Down>", scrolldown)
    render()

    tkinter.mainloop()

def run(url):
    host, port, path, fragment = parse_url(url)
    headers, body = request(host, port, path)
    text = lex(body)
    nodes = parse(text)
    show(nodes)

if __name__ == "__main__":
    import sys
    run(sys.argv[1])
