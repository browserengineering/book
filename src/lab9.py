"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 9 (Running Interactive Scripts),
without exercises.
"""

import socket
import ssl
import tkinter
import tkinter.font
import dukpy
from lab8 import request

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
    def __init__(self, tag, attributes):
        self.tag = tag
        self.attributes = attributes
        self.children = []

        self.style = {}
        for pair in self.attributes.get("style", "").split(";"):
            if ":" not in pair: continue
            prop, val = pair.split(":")
            self.style[prop.strip().lower()] = val.strip()

    def __repr__(self):
        return "<" + self.tag + ">"

class TextNode:
    def __init__(self, text):
        self.text = text
        self.tag = None
        self.children = []

    def __repr__(self):
        return self.text.replace("\n", "\\n")
        
def parse(tokens):
    currently_open = []
    for tok in tokens:
        implicit_tags(tok, currently_open)
        if isinstance(tok, Text):
            node = TextNode(tok.text)
            if not currently_open: continue
            node.parent = currently_open[-1]
            currently_open[-1].children.append(node)
        elif tok.tag.startswith("/"):
            node = currently_open.pop()
            if not currently_open: return node
            currently_open[-1].children.append(node)
        elif tok.tag in SELF_CLOSING_TAGS:
            node = ElementNode(tok.tag, tok.attributes)
            node.parent = currently_open[-1]
            currently_open[-1].children.append(node)
        elif tok.tag.startswith("!"):
            continue
        else:
            node = ElementNode(tok.tag, tok.attributes)
            if len(currently_open) > 0:
                node.parent = currently_open[-1]
            else:
                node.parent = None
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
    while True:4
        open_tags = [node.tag for node in currently_open]
        if open_tags == [] and tag != "html":
            node = ElementNode("html", {})
            node.parent = None
            currently_open.append(node)
        elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
            if tag in HEAD_TAGS:
                implicit = "head"
            else:
                implicit = "body"
            node = ElementNode(implicit, {})
            node.parent = currently_open[-1]
            currently_open.append(node)
        elif open_tags == ["html", "head"] and tag not in ["/head"] + HEAD_TAGS:
            node = currently_open.pop()
            currently_open[-1].children.append(node)
        else:
            break

class CSSParser:
    def __init__(self, s):
        self.s = s

    def whitespace(self, i):
        while i < len(self.s) and self.s[i].isspace():
            i += 1
        return None, i

    def literal(self, i, literal):
        l = len(literal)
        assert self.s[i:i+l] == literal
        return None, i + l

    def word(self, i):
        j = i
        while j < len(self.s) and self.s[j].isalnum() or self.s[j] in "-.":
            j += 1
        assert j > i
        return self.s[i:j], j

    def pair(self, i):
        prop, i = self.word(i)
        _, i = self.whitespace(i)
        _, i = self.literal(i, ":")
        _, i = self.whitespace(i)
        val, i = self.word(i)
        return (prop.lower(), val), i

    def ignore_until(self, i, chars):
        while i < len(self.s) and self.s[i] not in chars:
            i += 1
        return None, i

    def body(self, i):
        pairs = {}
        _, i = self.literal(i, "{")
        _, i = self.whitespace(i)
        while i < len(self.s) and self.s[i] != "}":
            try:
                (prop, val), i = self.pair(i)
                pairs[prop] = val
                _, i = self.whitespace(i)
                _, i = self.literal(i, ";")
            except AssertionError:
                _, i = self.ignore_until(i, [";", "}"])
                if i < len(self.s) and self.s[i] == ";":
                    _, i = self.literal(i, ";")
            _, i = self.whitespace(i)
        _, i = self.literal(i, "}")
        return pairs, i

    def selector(self, i):
        if self.s[i] == "#":
            _, i = self.literal(i, "#")
            name, i = self.word(i)
            return IdSelector(name), i
        elif self.s[i] == ".":
            _, i = self.literal(i, ".")
            name, i = self.word(i)
            return ClassSelector(name), i
        else:
            name, i = self.word(i)
            return TagSelector(name.lower()), i

    def rule(self, i):
        selector, i = self.selector(i)
        _, i = self.whitespace(i)
        body, i = self.body(i)
        return (selector, body), i

    def file(self, i):
        rules = []
        _, i = self.whitespace(i)
        while i < len(self.s):
            try:
                rule, i = self.rule(i)
                rules.append(rule)
            except AssertionError:
                _, i = self.ignore_until(i, "}")
                _, i = self.literal(i, "}")
            _, i = self.whitespace(i)
        return rules, i

    def parse(self):
        rules, _ = self.file(0)
        return rules
    
class TagSelector:
    def __init__(self, tag):
        self.tag = tag

    def matches(self, node):
        return self.tag == node.tag

    def priority(self):
        return 1

class ClassSelector:
    def __init__(self, cls):
        self.cls = cls

    def matches(self, node):
        return self.cls in node.attributes.get("class", "").split()

    def priority(self):
        return 16

class IdSelector:
    def __init__(self, id):
        self.id = id

    def matches(self, node):
        return self.id == node.attributes.get("id", "")

    def priority(self):
        return 256

INHERITED_PROPERTIES = {
    "font-style": "normal",
    "font-weight": "normal",
    "font-size": "16px",
    "color": "black",
}

def style(node, parent, rules):
    if isinstance(node, TextNode):
        node.style = parent.style
    else:
        for selector, pairs in rules:
            if selector.matches(node):
                for property in pairs:
                    if property not in node.style:
                        node.style[property] = pairs[property]
        for property, default in INHERITED_PROPERTIES.items():
            if property not in node.style:
                if parent:
                    node.style[property] = parent.style[property]
                else:
                    node.style[property] = default
    for child in node.children:
        style(child, node, rules)

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18

SCROLL_STEP = 100

class LineLayout:
    def __init__(self, node, parent):
        self.node = node
        self.parent = parent
        self.children = []
        self.cx = 0
        self.laid_out = False

    def append(self, child):
        self.children.append(child)
        child.parent = self
        self.cx += child.w + child.font.measure(" ")

    def layout(self):
        self.w = self.parent.w
        if not self.children:
            self.h = 0
            return
        metrics = [child.font.metrics() for child in self.children]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.y + 1.2 * max_ascent
        self.cx = 0
        for child, metric in zip(self.children, metrics):
            child.x = self.x + self.cx
            child.y = baseline - metric["ascent"]
            self.cx += child.w + child.font.measure(" ")
        max_descent = max([metric["descent"] for metric in metrics])
        self.h = 1.2 * (max_descent + max_ascent)

    def paint(self, to):
        for child in self.children:
            child.paint(to)

class TextLayout:
    def __init__(self, node, word):
        self.node = node
        self.children = []
        self.word = word

    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(px(self.node.style["font-size"]) * .75)
        self.font = tkinter.font.Font(size=size, weight=weight, slant=style)
        
        self.w = self.font.measure(self.word)
        self.h = self.font.metrics('linespace')

    def paint(self, to):
        color = self.node.style["color"]
        to.append(DrawText(self.x, self.y, self.word, self.font, color))

class InputLayout:
    def __init__(self, node):
        self.node = node
        self.children = []

    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(px(self.node.style["font-size"]) * .75)
        self.font = tkinter.font.Font(size=size, weight=weight, slant=style)
        self.w = 200
        self.h = 20

    def paint(self, to):
        x1, x2 = self.x, self.x + self.w
        y1, y2 = self.y, self.y + self.h
        bgcolor = "light gray" if self.node.tag == "input" else "yellow"
        to.append(DrawRect(x1, y1, x2, y2, bgcolor))

        if self.node.tag == "input":
            text = self.node.attributes.get("value", "")
        else:
            text = self.node.children[0].text
        color = self.node.style["color"]
        to.append(DrawText(self.x, self.y, text, self.font, color))

class InlineLayout:
    def __init__(self, node, parent):
        self.node = node
        self.parent = parent
        self.children = [LineLayout(self.node, self)]

    def layout(self):
        self.mt = self.bt = self.pt = 0
        self.mr = self.br = self.pr = 0
        self.mb = self.bb = self.pb = 0
        self.ml = self.bl = self.pl = 0

        self.w = self.parent.w - self.parent.pl - self.parent.pr \
            - self.parent.bl - self.parent.br

        self.cy = self.y
        self.recurse(self.node)
        self.flush()
        self.children.pop()

        self.h = self.cy - self.y

    def recurse(self, node):
        if isinstance(node, TextNode):
            self.text(node)
        elif node.tag == "br":
            self.flush()
        elif node.tag == "input":
            self.input(node)
        else:
            for child in node.children:
                self.recurse(child)

    def text(self, node):
        for word in node.text.split():
            child = TextLayout(node, word)
            child.layout()
            if self.children[-1].cx + child.w > self.w:
                self.flush()
            self.children[-1].append(child)

    def input(self, node):
        child = InputLayout(node)
        child.layout()
        if self.children[-1].cx + child.w > self.w:
            self.flush()
        self.children[-1].append(child)

    def flush(self):
        child = self.children[-1]
        child.x = self.x
        child.y = self.cy
        child.layout()
        self.cy += child.h
        self.children.append(LineLayout(self.node, self))

    def paint(self, to):
        for child in self.children:
            child.paint(to)

def px(s):
    if s.endswith("px"):
        return int(s[:-2])
    else:
        return 0

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
            elif child.style.get("display", "block") == "inline":
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

        self.mt = px(self.node.style.get("margin-top", "0px"))
        self.bt = px(self.node.style.get("border-top-width", "0px"))
        self.pt = px(self.node.style.get("padding-top", "0px"))
        self.mr = px(self.node.style.get("margin-right", "0px"))
        self.br = px(self.node.style.get("border-right-width", "0px"))
        self.pr = px(self.node.style.get("padding-right", "0px"))
        self.mb = px(self.node.style.get("margin-bottom", "0px"))
        self.bb = px(self.node.style.get("border-bottom-width", "0px"))
        self.pb = px(self.node.style.get("padding-bottom", "0px"))
        self.ml = px(self.node.style.get("margin-left", "0px"))
        self.bl = px(self.node.style.get("border-left-width", "0px"))
        self.pl = px(self.node.style.get("padding-left", "0px"))

        self.w = self.parent.w - self.parent.pl - self.parent.pr \
            - self.parent.bl - self.parent.br \
            - self.ml - self.mr

        self.y += self.mt
        self.x += self.ml

        y = self.y
        for child in self.children:
            child.x = self.x + self.pl + self.bl
            child.y = y
            child.layout()
            y += child.mt + child.h + child.mb
        self.h = y - self.y

    def paint(self, to):
        if self.node.tag == "pre":
            x2, y2 = self.x + self.w, self.y + self.h
            to.append(DrawRect(self.x, self.y, x2, y2, "gray"))
        for child in self.children:
            child.paint(to)

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
        child = BlockLayout(self.node, self)
        self.children.append(child)

        self.w = WIDTH
        self.mt = self.bt = self.pt = 0
        self.mr = self.br = self.pr = 0
        self.mb = self.bb = self.pb = 0
        self.ml = self.bl = self.pl = 0

        child.x = self.x = 0
        child.y = self.y = 0
        child.layout()
        self.h = child.h

    def paint(self, to):
        self.children[0].paint(to)

class DrawText:
    def __init__(self, x1, y1, text, font, color):
        self.x1 = x1
        self.y1 = y1
        self.text = text
        self.font = font
        self.color = color

        self.y2 = y1 + font.metrics("linespace")

    def draw(self, scroll, canvas):
        canvas.create_text(
            self.x1, self.y1 - scroll,
            text=self.text,
            font=self.font,
            fill=self.color,
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

def find_links(node, lst):
    if not isinstance(node, ElementNode): return
    if node.tag == "link" and \
       node.attributes.get("rel", "") == "stylesheet" and \
       "href" in node.attributes:
        lst.append(node.attributes["href"])
    for child in node.children:
        find_links(child, lst)
    return lst

def resolve_url(url, current):
    if "://" in url:
        return url
    elif url.startswith("/"):
        return "/".join(current.split("/")[:3]) + url
    else:
        return current.rsplit("/", 1)[0] + "/" + url

def find_layout(x, y, tree):
    for child in reversed(tree.children):
        result = find_layout(x, y, child)
        if result: return result
    if tree.x <= x < tree.x + tree.w and \
       tree.y <= y < tree.y + tree.h:
        return tree

def find_inputs(elt, out):
    if not isinstance(elt, ElementNode): return
    if elt.tag == "input" and "name" in elt.attributes:
        out.append(elt)
    for child in elt.children:
        find_inputs(child, out)
    return out

def find_scripts(node, out):
    if not isinstance(node, ElementNode): return
    if node.tag == "script" and \
       "src" in node.attributes:
        out.append(node.attributes["src"])
    for child in node.children:
        find_scripts(child, out)
    return out

def find_selected(node, sel, out):
    if not isinstance(node, ElementNode): return
    if sel.matches(node):
        out.append(node)
    for child in node.children:
        find_selected(child, sel, out)
    return out

def is_link(node):
    return isinstance(node, ElementNode) \
        and node.tag == "a" and "href" in node.attributes

class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT
        )
        self.canvas.pack()

        self.history = []
        self.focus = None
        self.address_bar = ""
        self.scroll = 0

        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Button-1>", self.handle_click)
        self.window.bind("<Key>", self.keypress)
        self.window.bind("<Return>", self.pressenter)
        self.display_list = []

    def handle_click(self, e):
        self.focus = None
        if e.y < 60: # Browser chrome
            if 10 <= e.x < 35 and 10 <= e.y < 50:
                self.go_back()
            elif 50 <= e.x < 790 and 10 <= e.y < 50:
                self.focus = "address bar"
                self.address_bar = ""
                self.render()
        else:
            x, y = e.x, e.y + self.scroll - 60
            obj = find_layout(x, y, self.document)
            if not obj: return
            elt = obj.node
            if elt and self.dispatch_event("click", elt): return
            while elt:
                if isinstance(elt, TextNode):
                    pass
                elif is_link(elt):
                    url = resolve_url(elt.attributes["href"], self.url)
                    return self.load(url)
                elif elt.tag == "input":
                    elt.attributes["value"] = ""
                    self.focus = obj
                    return self.layout(self.document.node)
                elif elt.tag == "button":
                    self.submit_form(elt)
                elt = elt.parent

    def keypress(self, e):
        if not (len(e.char) == 1 and 0x20 <= ord(e.char) < 0x7f):
            return

        if not self.focus:
            return
        elif self.focus == "address bar":
            self.address_bar += e.char
            self.render()
        else:
            self.focus.node.attributes["value"] += e.char
            self.dispatch_event("change", self.focus.node)
            self.layout(self.document.node)

    def submit_form(self, elt):
        while elt and elt.tag != "form":
            elt = elt.parent
        if not elt: return
        if self.dispatch_event("submit", elt): return
        inputs = find_inputs(elt, [])
        body = ""
        for input in inputs:
            name = input.attributes["name"]
            value = input.attributes.get("value", "")
            body += "&" + name + "=" + value.replace(" ", "%20")
        body = body[1:]
        url = resolve_url(elt.attributes["action"], self.url)
        self.load(url, body)

    def pressenter(self, e):
        if self.focus == "address bar":
            self.focus = None
            self.load(self.address_bar)

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

    def load(self, url, body=None):
        self.address_bar = url
        self.url = url
        self.history.append(url)
        header, body = request(url, body)
        self.nodes = parse(lex(body))
        
        with open("browser8.css") as f:
            self.rules = CSSParser(f.read()).parse()

        for link in find_links(self.nodes, []):
            header, body = request(resolve_url(link, url))
            self4.rules.extend(CSSParser(body).parse())

        self.rules.sort(key=lambda x: x[0].priority())
        self.rules.reverse()

        self.setup_js()
        for script in find_scripts(self.nodes, []):
            header, body = request(resolve_url(script, self.history[-1]))
            try:
                print("Script returned: ", self.js.evaljs(body))
            except dukpy.JSRuntimeError as e:
                print("Script", script, "crashed", e)
        self.layout(self.nodes)

    def setup_js(self):
        self.js = dukpy.JSInterpreter()
        self.node_to_handle = {}
        self.handle_to_node = {}
        self.js.export_function("log", print)
        self.js.export_function("querySelectorAll",
            self.js_querySelectorAll)
        self.js.export_function("getAttribute", self.js_getAttribute)
        self.js.export_function("innerHTML", self.js_innerHTML)
        with open("runtime9.js") as f:
            self.js.evaljs(f.read())

    def js_querySelectorAll(self, sel):
        selector, _ = CSSParser(sel + "{").selector(0)
        elts = find_selected(self.nodes, selector, [])
        return [self.make_handle(elt) for elt in elts]
    
    def js_getAttribute(self, handle, attr):
        elt = self.handle_to_node[handle]
        return elt.attributes.get(attr, None)

    def js_innerHTML(self, handle, s):
        doc = parse(lex("<html><body>" + s + "</body></html>"))
        new_nodes = doc.children[0].children
        elt = self.handle_to_node[handle]
        elt.children = new_nodes
        for child in elt.children:
            child.parent = elt
        self.layout(self.document.node)

    def dispatch_event(self, type, elt):
        handle = self.node_to_handle.get(elt, -1)
        do_default = self.js.evaljs(
            "__runHandlers({}, \"{}\")".format(handle, type))
        return not do_default

    def make_handle(self, elt):
        if elt not in self.node_to_handle:
            handle = len(self.node_to_handle)
            self.node_to_handle[elt] = handle
            self.handle_to_node[handle] = elt
        else:
            handle = self.node_to_handle[elt]
        return handle

    def layout(self, tree):
        style(tree, None, self.rules)
        self.document = DocumentLayout(tree)
        self.document.layout()
        self.display_list = []
        self.document.paint(self.display_list)
        self.render()
        self.max_y = self.document.h - HEIGHT

    def render(self):
        self.canvas.delete("all")
        for cmd in self.display_list:
            if cmd.y1 > self.scroll + HEIGHT - 60: continue
            if cmd.y2 < self.scroll: continue
            cmd.draw(self.scroll - 60, self.canvas)
        self.canvas.create_rectangle(0, 0, 800, 60, width=0, fill='light gray')
        self.canvas.create_rectangle(50, 10, 790, 50)
        font = tkinter.font.Font(family="Courier", size=30)
        self.canvas.create_text(55, 15, anchor='nw', text=self.address_bar, font=font)
        self.canvas.create_rectangle(10, 10, 35, 50)
        self.canvas.create_polygon(15, 30, 30, 15, 30, 45, fill='black')
        if self.focus == "address bar":
            w = font.measure(self.address_bar)
            self.canvas.create_line(55 + w, 15, 55 + w, 45)
        elif isinstance(self.focus, InputLayout):
            text = self.focus.node.attributes.get("value", "")
            x = self.focus.x + self.focus.font.measure(text)
            y = self.focus.y - self.scroll + 60
            self.canvas.create_line(x, y, x, y + self.focus.h)

    def scrolldown(self, e):
        self.scroll = self.scroll + SCROLL_STEP
        self.scroll = min(self.scroll, self.max_y)
        self.scroll = max(0, self.scroll)
        self.render()

if __name__ == "__main__":
    import sys
    browser = Browser()
    browser.load(sys.argv[1])
    tkinter.mainloop()
