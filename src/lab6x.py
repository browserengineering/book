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
        print(repr(s))

    def word(self, i):
        j = i
        while self.s[j].isalnum() or self.s[j] in "-":
            j += 1
        return self.s[i:j], j

    def value(self, i):
        j = i
        while self.s[j].isalnum() or self.s[j] in "- ":
            j += 1
        return self.s[i:j], j

    def whitespace(self, i):
        j = i
        while j < len(self.s) and self.s[j].isspace():
            j += 1
        return None, j

    def pair(self, i):
        prop, i = self.word(i)
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
        pairs2 = {}
        for p, v in pairs.items():
            for q, u in self.expand_shorthand(p, v).items():
                pairs2[q] = u
        return pairs2, i + 1

    def single_selector(self, i):
        sel = []
        while not self.s[i].isspace() and self.s[i] not in ",{":
            if self.s[i] == "#":
                name, i = self.word(i + 1)
                sel.append(IDSelector(name))
            elif self.s[i] == ".":
                name, i = self.word(i + 1)
                sel.append(ClassSelector(name))
            else:
                name, i = self.word(i)
                sel.append(TagSelector(name))
        if len(sel) == 1:
            return sel[0], i
        else:
            return AndSelector(*sel), i

    def selector(self, i):
        sels = []
        while True:
            sel, i = self.single_selector(i)
            _, i = self.whitespace(i)
            sels.append(sel)
            if self.s[i] in ",{":
                break
        if len(sels) == 1:
            return sels[0], i
        else:
            return DescendantSelector(*sels), i

    def selectors(self, i):
        sels = []

        while True:
            try:
                sel, i = self.selector(i)
                _, i = self.whitespace(i)
                sels.append(sel)
            except AssertionError:
                while self.s[i] not in ",{":
                    i += 1
            if self.s[i] == "{":
                break
            assert self.s[i] == ","
            _, i = self.whitespace(i+1)
        return sels, i

    def rule(self, i):
        try:
            sels, i = self.selectors(i)
            _, i = self.whitespace(i)
            body, i = self.body(i)
            return (sels, body), i
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
                if rule:
                    sels, body = rule
                    for sel in sels:
                        rules.append((sel, body))
            except AssertionError as e:
                break
        return rules

    def expand_shorthand(self, prop, value):
        result = {}
        if prop in ["margin", "padding", "border-width"]:
            vals = value.split()
            if len(vals) == 1:
                vals = [vals[0]] * 4
            elif len(vals) == 2:
                v, h = vals
                vals = [v, h, v, h]
            elif len(vals) == 3:
                t, h, b = vals
                vals = [t, h, b, h]
            else:
                pass
            for dir, val in zip(["top", "right", "bottom", "left"], vals):
                p = prop.split("-")
                prop2 = "-".join(p[:1] + [dir] + p[1:])
                result[prop2] = val
        else:
            result[prop] = value
        return result

class AndSelector:
    def __init__(self, *sels):
        self.sels = sels

    def matches(self, node):
        return all(sel.matches(node) for sel in self.sels)

    def score(self):
        return sum(sel.score() for sel in self.sels)

class DescendantSelector:
    def __init__(self, *sels):
        self.sels = sels

    def matches(self, node):
        if not self.sels[-1].matches(node):
            return False
        node = node.parent

        for sel in reversed(self.sels[:-1]):
            while node and not sel.matches(node):
                node = node.parent
            if not node:
                return False

        return True

    def score(self):
        return sum(sel.score() for sel in self.sels)

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

INHERITED_PROPERTIES = [ "font-style", "font-weight" ]

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
                node.style[prop] = "normal"
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
        return parse_url(url)
    host, port, path, fragment = parse_url(current)
    if url.startswith("/"):
        path, fragment = url.split("#", 1) if "#" in url else (url, None)
        return host, port, path, fragment
    else:
        path, fragment = url.split("#", 1) if "#" in url else (url, None)
        curdir, curfile = current.rsplit("/", 1)
        return host, port, curdir + "/" + path, fragment

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
            layout = InlineLayout(self)
            layout.layout(self.node)
            y += layout.height()
        else:
            for child in self.node.children:
                if isinstance(child, TextNode) and child.text.isspace(): continue
                if child.style.get("display", "block") == "none": continue
                layout = BlockLayout(self, child)
                layout.layout(y)
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
            for child in node.children:
                self.layout(child)
        else:
            self.text(node)

    def text(self, node):
        self.bold = node.style["font-weight"] == "bold"
        self.italic = node.style["font-style"] == "italic"
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
    mode = BlockLayout(page, nodes)
    mode.layout(0)
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
    rules = []
    with open("browserx.css") as f:
        r = CSSParser(f.read()).parse()
        rules.extend(r)
    for link in find_links(nodes):
        lhost, lport, lpath, lfragment = relative_url(link, url)
        header, body = request(lhost, lport, lpath)
        rules.extend(CSSParser(body)).parse()
    rules.sort(key=lambda x: x[0].score())
    style(nodes, rules)
    show(nodes)

if __name__ == "__main__":
    import sys
    run(sys.argv[1])
