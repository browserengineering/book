import socket
import tkinter
import tkinter.font
import dukpy
import time

def parse_url(url):
    assert url.startswith("http://")
    url = url[len("http://"):]
    hostport, pathfragment = url.split("/", 1) if "/" in url else (url, "")
    host, port = hostport.rsplit(":", 1) if ":" in hostport else (hostport, "80")
    path, fragment = ("/" + pathfragment).rsplit("#", 1) if "#" in pathfragment else ("/" + pathfragment, None)
    return host, int(port), path, fragment

def request(method, host, port, path, headers={}, body=None):
    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    s.connect((host, port))
    s.send("{} {} HTTP/1.0\r\nHost: {}\r\n".format(method, path, host).encode("utf8"))
    if body:
        body = body.encode('utf8')
        s.send("Content-Length: {}\r\n\r\n".format(len(body)).encode('utf8'))
        s.send(body)
    else:
        s.send(b'\r\n')
    for header, value in headers.items():
        s.send("{}: {}\r\n".format(header, value).encode("utf8"))
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
        elif self.s[i] == ":":
            name, i = self.value(i + 1)
            return PseudoclassSelector(name), i
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

class PseudoclassSelector:
    def __init__(self, cls):
        self.cls = cls

    def matches(self, node):
        return self.cls in node.pseudoclasses

    def score(self):
        return 0

class IDSelector:
    def __init__(self, id):
        self.id = id

    def matches(self, node):
        return self.id == node.attributes.get("id", "")

    def score(self):
        return 256

INHERITED_PROPERTIES = { "font-style": "normal", "font-weight": "normal", "color": "black" }

def style(node, rules):
    if not isinstance(node, ElementNode):
        node.style = node.parent.style
        return
    node.style = {}
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

def find_scripts(node):
    if not isinstance(node, ElementNode): return
    if node.tag == "script" and \
       "src" in node.attributes:
        yield node.attributes["src"]
    for child in node.children:
        yield from find_scripts(child)

def find_selected(node, sel):
    if not isinstance(node, ElementNode): return
    if sel.matches(node):
        yield node
    for child in node.children:
        yield from find_selected(child, sel)

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
        self.pseudoclasses = set()
        self.parent = parent
        self.handle = 0

        for attr in attrs:
            out = attr.split("=", 1)
            name = out[0]
            val = out[1].strip("\"") if len(out) > 1 else ""
            self.attributes[name.lower()] = val

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
                elif node and node.parent is not None:
                    current = node.parent
            else: # Open tag
                new = ElementNode(current, tok.tag)
                if current is not None:
                    current.children.append(new)
                if new.tag not in ["br", "link", "meta", "input"]:
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
        parent.children.append(self)

        self.node = node

    def layout1(self):
        self.children = []
        self.mt = px(self.node.style.get("margin-top", "0px"))
        self.mr = px(self.node.style.get("margin-right", "0px"))
        self.mb = px(self.node.style.get("margin-bottom", "0px"))
        self.ml = px(self.node.style.get("margin-left", "0px"))

        self.bt = px(self.node.style.get("border-top-width", "0px"))
        self.br = px(self.node.style.get("border-right-width", "0px"))
        self.bb = px(self.node.style.get("border-bottom-width", "0px"))
        self.bl = px(self.node.style.get("border-left-width", "0px"))

        self.pt = px(self.node.style.get("padding-top", "0px"))
        self.pr = px(self.node.style.get("padding-right", "0px"))
        self.pb = px(self.node.style.get("padding-bottom", "0px"))
        self.pl = px(self.node.style.get("padding-left", "0px"))

        self.w = self.parent.content_width()
        self.w -= self.ml + self.mr

        h = self.bt + self.pt
        if any(is_inline(child) for child in self.node.children):
            layout = InlineLayout(self, self.node)
            layout.layout1()
            h += layout.h
        else:
            for child in self.node.children:
                if isinstance(child, TextNode) and child.text.isspace(): continue
                layout = BlockLayout(self, child)
                layout.layout1()
                h += layout.h + layout.mt + layout.mb
        h += self.pb + self.bb
        self.h = h

    def layout2(self, y):
        self.x = self.parent.content_left()
        self.y = y
        self.x += self.ml
        self.y += self.mt

        y = self.y
        for child in self.children:
            y += child.mt if isinstance(child, BlockLayout) else 0
            child.layout2(y)
            y += child.h + (child.mb if isinstance(child, BlockLayout) else 0)

    def display_list(self):
        for child in self.children:
            yield from child.display_list()
        if self.bl > 0: yield DrawRect(self.x, self.y, self.x + self.bl, self.y + self.h)
        if self.br > 0: yield DrawRect(self.x + self.w - self.br, self.y, self.x + self.w, self.y + self.h)
        if self.bt > 0: yield DrawRect(self.x, self.y, self.x + self.w, self.y + self.bt)
        if self.bb > 0: yield DrawRect(self.x, self.y + self.h - self.bb, self.x + self.w, self.y + self.h)

    def content_left(self):
        return self.x + self.bl + self.pl
    def content_top(self):
        return self.y + self.bt + self.pt
    def content_width(self):
        return self.w - self.bl - self.br - self.pl - self.pr

class InlineLayout:
    def __init__(self, parent, node):
        self.parent = parent
        parent.children.append(self)
        self.node = node

    def display_list(self):
        for child in self.children:
            yield from child.display_list()

    def layout1(self):
        self.children = []
        LineLayout(self)
        self.w = self.parent.content_width()
        self.recurse(self.node)
        h = 0
        for child in self.children:
            child.layout1()
            h += child.h
        self.h = h

    def layout2(self, y):
        self.x = self.parent.content_left()
        self.y = self.parent.content_top()
        y = self.y
        for child in self.children:
            child.layout2(y)
            y += child.h

    def recurse(self, node):
        if isinstance(node, TextNode):
            self.text(node)
        elif node.tag in ["input", "textarea", "button"]:
            self.input(node)
        else:
            for child in node.children:
                self.recurse(child)

    def text(self, node):
        if node.text[0].isspace() and len(self.children[-1].children) > 0:
            self.children[-1].children[-1].add_space()

        words = node.text.split()
        for i, word in enumerate(words):
            tl = TextLayout(node, word)
            tl.layout1()
            line = self.children[-1]
            if line.w + tl.w > self.w:
                line = LineLayout(self)
            tl.attach(line)
            if i != len(words) - 1 or node.text[-1].isspace():
                tl.add_space()

    def input(self, node):
        if node.tag == "input" and node.attributes.get("type") == "hidden":
            return
        tl = InputLayout(node, node.tag == "textarea")
        tl.layout1()
        line = self.children[-1]
        if line.w + tl.w > self.w:
            line = LineLayout(self)
        tl.attach(line)

class LineLayout:
    def __init__(self, parent):
        self.parent = parent
        parent.children.append(self)
        self.w = 0
        self.children = []

    def display_list(self):
        for child in self.children:
            yield from child.display_list()

    def layout1(self):
        self.h = 0
        leading = 2
        w = 0
        for child in self.children:
            w += child.w + child.space
            self.h = max(self.h, child.h + leading)
        self.w = w

    def layout2(self, y):
        self.y = y
        self.x = self.parent.x

        x = self.x
        leading = 2
        y += leading / 2
        for child in self.children:
            child.layout2(x, y)
            x += child.w + child.space

class TextLayout:
    def __init__(self, node, text):
        self.node = node
        self.text = text
        self.space = 0

    def layout1(self):
        self.children = []
        bold = self.node.style["font-weight"] == "bold"
        italic = self.node.style["font-style"] == "italic"
        self.color = self.node.style["color"]
        self.font = tkinter.font.Font(
            family="Times", size=16,
            weight="bold" if bold else "normal",
            slant="italic" if italic else "roman"
        )
        self.w = self.font.measure(self.text)
        self.h = self.font.metrics('linespace')

    def layout2(self, x, y):
        self.x = x
        self.y = y

    def attach(self, parent):
        self.parent = parent
        parent.children.append(self)
        parent.w += self.w

    def add_space(self):
        if self.space == 0:
            gap = self.font.measure(" ")
            self.space = gap
            self.parent.w += gap

    def display_list(self):
        yield DrawText(self.x, self.y, self.text, self.font, self.color)

class InputLayout:
    def __init__(self, node, multiline=False):
        self.node = node
        self.space = 0
        self.multiline = multiline

    def layout1(self):
        self.children = []
        self.w = 200
        self.h = 60 if self.multiline else 20
        if self.node.children:
            layout = InlineLayout(self, self.node.children[0])
            layout.layout()

    def layout2(self, x, y):
        self.x = x
        self.y = y
        if self.children:
            self.children[0].layout2(y)

    def content_left(self):
        return self.x + 1
    
    def content_top(self):
        return self.y + 1
    
    def content_width(self):
        return self.w - 2

    def attach(self, parent):
        self.parent = parent
        parent.children.append(self)
        parent.w += self.w

    def add_space(self):
        if self.space == 0:
            gap = 5
            self.space = gap
            self.parent.w += gap

    def display_list(self):
        yield DrawRect(self.x, self.y, self.x + self.w, self.y + self.h)
        if self.children:
            for child in self.children:
                yield from child.display_list()
        else:
            font = tkinter.font.Font(family="Times", size=16)
            yield DrawText(self.x + 1, self.y + 1, self.node.attributes.get("value", ""), font, "black")

class DrawText:
    def __init__(self, x, y, text, font, color):
        self.x1 = x
        self.y1 = y
        self.text = text
        self.font = font
        self.color = color
        self.y2 = y + 20
    
    def draw(self, scrolly, canvas):
        canvas.create_text(self.x1, self.y1 - scrolly, text=self.text, font=self.font, anchor='nw', fill=self.color)

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

class Timer:
    def __init__(self):
        self.phase = None
        self.time = None

    def start(self, name):
        if self.phase: self.stop()
        self.phase = name
        self.time = time.time()

    def stop(self):
        print("[{:>10.6f}] {}".format(time.time() - self.time, self.phase))
        self.phase = None

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

        self.hovered_elt = None
        self.window.bind("<Motion>", self.handle_hover)

        self.timer = Timer()
        self.jar = {}
        self.filter = True
        self.ref_policy = False

    def browse(self, url, method="GET", params={}):
        self.timer.start("Download")
        if params:
            body = ""
            for param, value in params.items():
                body += "&" + param + "="
                body += value.replace(" ", "%20")
            body = body[1:]
        else:
            body = None

        host, port, path, fragment = parse_url(url)

        req_headers = {}

        cookie_string = self.cookie_string(url)
        if cookie_string != "":
            req_headers["Cookie"] = cookie_string

        if len(self.history) >= 1:
            referer = self.history[-1]
            if not self.ref_policy:
                req_headers["Referer"] = referer
            elif self.ref_policy == "same-origin":
                rhost, rport, rpath, rfragment = parse_url(referer)
                if rhost == host and rport == port:
                    req_headers["Referer"] = referer

        headers, body = request(method, host, port, path, body,
                                headers={ "Cookie": cookie_string })

        if "set-cookie" in headers:
            kv, params = headers["set-cookie"].split(";")
            params = { param.split("=", 1)[0]: param.split("=", 1)[1]
                       for param in params }
            if "expires" in params:
                expiration = time.mktime(email.utils.parsedate(params["expiration"]))
            else:
                expiration = None
            if "origin" in params:
                origin = params["origin"]
                if ":" in origin:
                    ohost, oport = origin.split(":", 1)
                else:
                    ohost, oport = origin, "80"
                if oport == port and ("." + host).endswith(("." + ohost)):
                    origin = (ohost, oport)
                else:
                    origin = (host, port)
            else:
                origin = (host, port)
            key, value = kv.strip().split("=", 1)
            self.jar.setefault(origin, {})[key] = (value, expiration)

        if "content-security-policy" in headers:
            keyword, *hosts = headers["content-security-policy"].split(" ")
            if keyword == "default-src":
                self.filter = hosts
            else:
                self.filter = True
        else:
            self.filter = True

        if "referer-policy" in headers:
            self.ref_policy = headers["referer-policy"]
        else:
            self.ref_policy = None

        self.history.append(url)
        self.parse(body)

    def parse(self, body):
        self.timer.start("Parse HTML")
        text = lex(body)
        self.nodes = parse(text)

        self.timer.start("Parse CSS")
        self.rules = []
        with open("browser.css") as f:
            r = CSSParser(f.read()).parse()
            self.rules.extend(r)
        for link in find_links(self.nodes):
            lurl = relative_url(link, self.history[-1])
            if self.filter != True and \
               not any(lurl.startswith(furl) for furl in self.filter):
                continue
            lhost, lport, lpath, lfragment = parse_url(lurl)
            header, body = request('GET', lhost, lport, lpath)
            self.rules.extend(CSSParser(body).parse())
        self.rules.sort(key=lambda x: x[0].score())

        self.timer.start("Run JS")
        self.js = dukpy.JSInterpreter()
        self.js_handles = {}
        self.js.export_function("log", print)
        self.js.export_function("querySelectorAll", self.js_querySelectorAll)
        self.js.export_function("getAttribute", self.js_getAttribute)
        self.js.export_function("innerHTML", self.js_innerHTML)
        self.js.export_function("cookie", self.js_cookie)
        with open("runtime.js") as f:
            self.js.evaljs(f.read())
        for script in find_scripts(self.nodes):
            lurl = relative_url(script, self.history[-1])
            if self.filter != True and \
               not any(lurl.startswith(furl) for furl in self.filter):
                continue
            lhost, lport, lpath, lfragment = parse_url(lurl)
            header, body = request('GET', lhost, lport, lpath)
            self.js.evaljs(body)

        self.page = Page()
        self.layout = BlockLayout(self.page, self.nodes)
        self.reflow(self.nodes)
        self.relayout()
        
    def reflow(self, elt):
        self.timer.start("Style")
        style(elt, self.rules)
        self.timer.start("Layout1")
        layout = find_layout(self.layout, elt)
        if layout: layout.layout1()

    def relayout(self):
        self.timer.start("Layout2")
        self.layout.layout2(0)
        self.max_h = self.layout.h
        self.timer.start("Display List")
        self.display_list = list(self.layout.display_list())
        self.render()
        
    def render(self):
        self.timer.start("Rendering")
        self.canvas.delete("all")
        for cmd in self.display_list:
            if cmd.y2 - self.scrolly < 0: continue
            if cmd.y1 - self.scrolly > 600: continue
            cmd.draw(self.scrolly - 60, self.canvas)
        self.timer.start("Chrome")
        self.canvas.create_rectangle(0, 0, 800, 60, fill='white')
        self.canvas.create_rectangle(40, 10, 790, 50)
        self.canvas.create_text(45, 15, anchor='nw', text=self.history[-1])
        self.canvas.create_rectangle(10, 10, 35, 50)
        self.canvas.create_polygon(15, 30, 30, 15, 30, 45, fill='black')
        self.timer.stop()

    def event(self, type, elt):
        if isinstance(elt, ElementNode) and elt.handle:
            return self.js.evaljs("__runHandlers({}, \"{}\")".format(elt.handle, type))

    def js_cookie(self):
        host, port, path, fragment = parse_url(self.history[-1])

        cookie_string = ""
        for (ohost, oport), cookies in self.jar:
            if oport != port or not ("." + host).endswith("." + origin): continue
            for key, (value, expires) in cookies.items():
                if not expires or expires < time.time():
                    cookie_string += "&" + key + "=" + value
        return cookie_string[1:]

    def js_querySelectorAll(self, sel):
        p = CSSParser(sel + "{")
        selector, _ = p.selector(0)
        out = []
        for elt in find_selected(self.nodes, selector):
            if not elt.handle:
                handle = len(self.js_handles) + 1
                elt.handle = handle
                self.js_handles[handle] = elt
            out.append(handle)
        return out

    def js_getAttribute(self, handle, attr):
        elt = self.js_handles[handle]
        return elt.attributes.get(attr, None)

    def js_innerHTML(self, handle, s):
        elt = self.js_handles[handle]
        new_node = parse(lex("<new>" + s + "</new>"))
        elt.children = new_node.children
        for child in elt.children:
            child.parent = elt
        self.reflow(elt)
        self.relayout()
                
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
            if elt and self.event("click", elt): return
            while elt and not \
                  (isinstance(elt, ElementNode) and \
                   (elt.tag == "a" and "href" in elt.attributes or \
                    elt.tag in ["input", "textarea", "button"])):
                elt = elt.parent
            if not elt:
                pass
            elif elt.tag == "a":
                self.browse(relative_url(elt.attributes["href"], self.history[-1]))
            elif elt.tag == "button":
                self.submit_form(elt)
            else:
                new_text = input("Enter new text: ")
                if elt.tag == "input":
                    elt.attributes["value"] = new_text
                else:
                    elt.children = [TextNode(elt, new_text)]
                self.event("change", elt)
                self.reflow(elt)
                self.relayout()

    def handle_hover(self, e):
        x, y = e.x, e.y - 60 + self.scrolly
        elt = find_element(x, y, self.layout)
        while elt and not isinstance(elt, ElementNode):
            elt = elt.parent
        if self.hovered_elt:
            self.hovered_elt.pseudoclasses.remove("hover")
            self.reflow(self.hovered_elt)
        if not elt:
            self.hovered_elt = None
            return
        elt.pseudoclasses.add("hover")
        self.hovered_elt = elt
        self.reflow(elt)
        self.relayout()

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.browse(back)

    def submit_form(self, elt):
        while elt and elt.tag != 'form':
            print(elt, elt.tag)
            elt = elt.parent
        if not elt: return
        if self.event("submit", elt): return
        inputs = find_inputs(elt, [])
        params = {}
        for input in inputs:
            if input.tag == "input":
                params[input.attributes['name']] = input.attributes.get("value", "")
            else:
                params[input.attributes['name']] = input.children[0].text if input.children else ""
        self.browse(relative_url(elt.attributes['action'], self.history[-1]),
                    method="POST", params=params)

def find_inputs(elt, out):
    if not isinstance(elt, ElementNode): return
    if (elt.tag == "input" or elt.tag == "textarea") and "name" in elt.attributes:
        out.append(elt)
    for child in elt.children:
        find_inputs(child, out)
    return out

def find_layout(layout, elt):
    if not hasattr(layout, "children"):
        return layout
    if not isinstance(layout, LineLayout) and layout.node == elt:
        return layout
    for child in layout.children:
        out = find_layout(child, elt)
        if out: return out

if __name__ == "__main__":
    import sys
    browser = Browser()
    browser.browse(sys.argv[1])
    tkinter.mainloop()
