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

def px(s):
    return int(s[:-len("px")])

class CSSParser:
    def __init__(self, s):
        self.s = s

    def value(self, i):
        j = i
        while self.s[j].isalnum() or self.s[j] == "-":
            j += 1
        return self.s[i:j], j

    def whitespace(self, i):
        j = i
        while j < len(self.s) and self.s[j].isspace():
            j += 1
        return None, j

    def pair(self, i):
        prop, i = self.value(i)
        _, i = self.whitespace(i)
        assert self.s[i] == ":"
        _, i = self.whitespace(i+1)
        val, i = self.value(i)
        return (prop, val), i

    def body(self, i):
        pairs = {}
        assert self.s[i] == "{"
        _, i = self.whitespace(i+1)
        while True:
            if self.s[i] == "}": break

            try:
                (prop, val), i = self.pair(i)
                pairs[prop] = val
                _, i = self.whitespace(i)
                assert self.s[i] == ";"
                _, i = self.whitespace(i+1)
            except AssertionError:
                while self.s[i] not in ";}":
                    i += 1
                if self.s[i] == ";":
                    _, i = self.whitespace(i+1)
        assert self.s[i] == "}"
        return pairs, i + 1

    def selector(self, i):
        if self.s[i] == "#":
            name, i = self.value(i + 1)
            return IDSelector(name), i
        elif self.s[i] == ".":
            name, i = self.value(i + 1)
            return ClassSelector(name), i
        else:
            name, i = self.value(i)
            return TagSelector(name), i

    def rule(self, i):
        try:
            sel, i = self.selector(i)
            _, i = self.whitespace(i)
            body, i = self.body(i)
            return (sel, body), i
        except AssertionError:
            while self.s[i] != "}":
                i += 1
            i += 1
            return None, i

    def parse(self):
        rules = []
        i = 0
        while i < len(self.s):
            try:
                rule, i = self.rule(i)
                _, i = self.whitespace(i)
                if rule: rules.append(rule)
            except Exception as e:
                break
        return rules

class TagSelector:
    def __init__(self, tag):
        self.tag = tag

    def matches(self, node):
        return self.tag == node.tag

    def score(self):
        return 1

class ClassSelector:
    def __init__(self, cls):
        self.cls = cls

    def matches(self, node):
        return self.cls in node.attributes.get("class", "").split()

    def score(self):
        return 16

class IDSelector:
    def __init__(self, id):
        self.id = i

    def matches(self, node):
        return self.id == node.attributes.get("id", "")

    def score(self):
        return 256

INHERITED_PROPERTIES = { "font-style": "normal", "font-weight": "normal", "color": "black" }

def style(node, rules):
    if not isinstance(node, ElementNode): return
    for selector, pairs in rules:
        if selector.matches(node):
            for prop in pairs:
                node.style[prop] = pairs[prop]
    for prop, value in node.compute_style().items():
        node.style[prop] = value
    for prop in INHERITED_PROPERTIES:
        if prop not in node.style:
            if node.parent is None:
                node.style[prop] = INHERITED_PROPERTIES[prop]
            else:
                node.style[prop] = node.parent.style[prop]
    for child in node.children:
        style(child, rules)

def find_links(node):
    if not isinstance(node, ElementNode): return
    if node.tag == "link" and \
       node.attributes.get("rel", "") == "stylesheet" and \
       "href" in node.attributes:
        yield node.attributes["href"]
    for child in node.children:
        yield from find_links(child)

def relative_url(url, current):
    if url.startswith("http://"):
        return url
    if url.startswith("/"):
        return current.split("/")[0] + url
    else:
        return current.rsplit("/", 1)[0] + "/" + url

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

        self.style = self.compute_style()

    def compute_style(self):
        style = {}
        style_value = self.attributes.get("style", "")
        for line in style_value.split(";"):
            try:
                prop, val = line.split(":")
            except:
                break
            style[prop.lower().strip()] = val.strip()
        return style

class TextNode:
    def __init__(self, parent, text):
        self.text = text
        self.parent = parent
        self.style = self.parent.style

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
                if current is not None:
                    current.children.append(new)
                if new.tag not in ["br", "link", "meta"]:
                    current = new
        else: # Text token
            new = TextNode(current, tok.text)
            current.children.append(new)
    while current.parent is not None: current = current.parent
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
        isinstance(node, ElementNode) and node.style.get("display", "block") == "inline"

class BlockLayout:
    def __init__(self, parent, node):
        self.parent = parent
        self.children = []
        parent.children.append(self)

        self.node = node

        self.mt = px(node.style.get("margin-top", "0px"))
        self.mr = px(node.style.get("margin-right", "0px"))
        self.mb = px(node.style.get("margin-bottom", "0px"))
        self.ml = px(node.style.get("margin-left", "0px"))

        self.bt = px(node.style.get("border-top-width", "0px"))
        self.br = px(node.style.get("border-right-width", "0px"))
        self.bb = px(node.style.get("border-bottom-width", "0px"))
        self.bl = px(node.style.get("border-left-width", "0px"))

        self.pt = px(node.style.get("padding-top", "0px"))
        self.pr = px(node.style.get("padding-right", "0px"))
        self.pb = px(node.style.get("padding-bottom", "0px"))
        self.pl = px(node.style.get("padding-left", "0px"))

        self.x = parent.content_left()
        self.w = parent.content_width()
        self.h = None

    def layout(self, y):
        self.y = y
        self.x += self.ml
        self.y += self.mt
        self.w -= self.ml + self.mr

        y += self.bt + self.pt
        if any(is_inline(child) for child in self.node.children):
            layout = InlineLayout(self, self.node)
            layout.layout()
            y += layout.h
        else:
            for child in self.node.children:
                if isinstance(child, TextNode) and child.text.isspace(): continue
                layout = BlockLayout(self, child)
                layout.layout(y)
                y += layout.h + layout.mt + layout.mb
        y += self.pb + self.bb
        self.h = y - self.y

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

class LineLayout:
    def __init__(self, parent):
        self.parent = parent
        self.children = []
        parent.children.append(self)
        self.w = 0

    def display_list(self):
        dl = []
        for child in self.children:
            dl.extend(child.display_list())
        return dl

    def layout(self, y):
        self.y = y
        self.x = self.parent.x
        self.h = 0

        x = self.x
        leading = 2
        y += leading / 2
        for child in self.children:
            child.layout(x, y)
            x += child.w + child.space
            self.h = max(self.h, child.h + leading)
        self.w = x - self.x

class TextLayout:
    def __init__(self, node, text):
        self.children = []
        self.node = node
        self.text = text
        self.space = 0

        bold = node.style["font-weight"] == "bold"
        italic = node.style["font-style"] == "italic"
        self.color = node.style["color"]
        self.font = tkinter.font.Font(
            family="Times", size=16,
            weight="bold" if bold else "normal",
            slant="italic" if italic else "roman"
        )
        self.w = self.font.measure(text)
        self.h = self.font.metrics('linespace')

    def attach(self, parent):
        self.parent = parent
        parent.children.append(self)
        parent.w += self.w

    def add_space(self):
        if self.space == 0:
            gap = self.font.measure(" ")
            self.space = gap
            self.parent.w += gap

    def layout(self, x, y):
        self.x = x
        self.y = y

    def display_list(self):
        return [DrawText(self.x, self.y, self.text, self.font, self.color)]

class InlineLayout:
    def __init__(self, parent, node):
        self.parent = parent
        parent.children.append(self)
        self.node = node
        self.children = []
        LineLayout(self)

    def display_list(self):
        dl = []
        for child in self.children:
            dl.extend(child.display_list())
        return dl

    def layout(self):
        self.x = self.parent.content_left()
        self.y = self.parent.content_top()
        self.w = self.parent.content_width()
        self.recurse(self.node)
        y = self.y
        for child in self.children:
            child.layout(y)
            y += child.h
        self.h = y - self.y

    def recurse(self, node):
        if isinstance(node, ElementNode):
            for child in node.children:
                self.recurse(child)
        else:
            self.text(node)

    def text(self, node):
        if node.text[0].isspace() and len(self.children[-1].children) > 0:
            self.children[-1].children[-1].add_space()

        words = node.text.split()
        for i, word in enumerate(words):
            tl = TextLayout(node, word)
            line = self.children[-1]
            if line.w + tl.w > self.w:
                line = LineLayout(self)
            tl.attach(line)
            if i != len(words) - 1 or node.text[-1].isspace():
                tl.add_space()

class DrawText:
    def __init__(self, x, y, text, font, color):
        self.x = x
        self.y = y
        self.text = text
        self.font = font
        self.color = color
    
    def draw(self, scrolly, canvas):
        canvas.create_text(self.x, self.y - scrolly, text=self.text, font=self.font, anchor='nw', fill=self.color)

class DrawRect:
    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def draw(self, scrolly, canvas):
        canvas.create_rectangle(self.x1, self.y1 - scrolly, self.x2, self.y2 - scrolly)

def find_element(x, y, layout):
    for child in layout.children:
        result = find_element(x, y, child)
        if result: return result
    if hasattr(layout, "node") and \
       layout.x <= x < layout.x + layout.w and \
       layout.y <= y < layout.y + layout.h:
        return layout.node

class Browser:
    SCROLL_STEP = 100

    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(self.window, width=800, height=600)
        self.canvas.pack()
        
        self.history = []
        self.scrolly = 0
        self.max_h = 0
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Button-1>", self.handle_click)


    def browse(self, url):
        self.history.append(url)
        host, port, path, fragment = parse_url(url)
        headers, body = request(host, port, path)
        text = lex(body)
        self.nodes = parse(text)
        self.rules = []
        with open("browser.css") as f:
            r = CSSParser(f.read()).parse()
            self.rules.extend(r)
        for link in find_links(self.nodes):
            lhost, lport, lpath, lfragment = parse_url(relative_url(link, url))
            header, body = request(lhost, lport, lpath)
            self.rules.extend(CSSParser(body)).parse()
        self.rules.sort(key=lambda x: x[0].score())
        style(self.nodes, self.rules)
        
        self.page = Page()
        self.layout = BlockLayout(self.page, self.nodes)
        self.layout.layout(0)
        self.max_h = self.layout.h
        self.display_list = self.layout.display_list()
        self.render()
        
    def render(self):
        self.canvas.delete("all")
        for cmd in self.display_list:
            cmd.draw(self.scrolly - 60, self.canvas)
        self.canvas.create_rectangle(0, 0, 800, 60, fill='white')
        self.canvas.create_rectangle(40, 10, 790, 50)
        self.canvas.create_text(45, 15, anchor='nw', text=self.history[-1])
        self.canvas.create_rectangle(10, 10, 35, 50)
        self.canvas.create_polygon(15, 30, 30, 15, 30, 45, fill='black')
                
    def scrolldown(self, e):
        self.scrolly = min(self.scrolly + self.SCROLL_STEP, 13 + self.max_h - 600)
        self.render()
                    
    def handle_click(self, e):
        if e.y < 60:
            if 10 <= e.x < 35 and 10 <= e.y < 50:
                self.go_back()
        else:
            x, y = e.x, e.y - 60 + self.scrolly
            elt = find_element(x, y, self.layout)
            while elt and not \
                  (isinstance(elt, ElementNode) and elt.tag == "a" and "href" in elt.attributes):
                elt = elt.parent
            if elt:
                self.browse(relative_url(elt.attributes["href"], self.history[-1]))

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.browse(back)

if __name__ == "__main__":
    import sys
    browser = Browser()
    browser.browse(sys.argv[1])
    tkinter.mainloop()
