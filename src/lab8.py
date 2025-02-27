"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 8 (Sending Information to Servers),
without exercises.
"""

import wbetools
import socket
import ssl
import tkinter
import tkinter.font
import urllib.parse
from lab2 import WIDTH, HEIGHT, HSTEP, VSTEP, SCROLL_STEP
from lab3 import FONTS, get_font
from lab4 import Text, Element, print_tree, HTMLParser
from lab5 import BLOCK_ELEMENTS, DocumentLayout
from lab6 import CSSParser, TagSelector, DescendantSelector
from lab6 import INHERITED_PROPERTIES, style, cascade_priority, tree_to_list
from lab7 import DrawText, DrawLine, DrawOutline, BlockLayout, LineLayout, TextLayout
from lab7 import URL, Tab, Browser, Chrome, DrawRect, Rect

@wbetools.patch(Element)
class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent
        self.style = {}
        self.is_focused = False

@wbetools.patch(Text)
class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent
        self.style = {}
        self.is_focused = False

@wbetools.patch(URL)
class URL:
    def request(self, payload=None):
        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
        s.connect((self.host, self.port))
    
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
    
        method = "POST" if payload else "GET"
        request = "{} {} HTTP/1.0\r\n".format(method, self.path)
        if payload:
            length = len(payload.encode("utf8"))
            request += "Content-Length: {}\r\n".format(length)
        request += "Host: {}\r\n".format(self.host)
        request += "\r\n"
        if payload: request += payload
        s.send(request.encode("utf8"))
        response = s.makefile("r", encoding="utf8", newline="\r\n")
    
        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)
    
        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
    
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers
    
        content = response.read()
        s.close()
        return content

DEFAULT_STYLE_SHEET = CSSParser(open("browser8.css").read()).parse()

INPUT_WIDTH_PX = 200

class InputLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.children = []
        self.parent = parent
        self.previous = previous
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.font = None

    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(self.node.style["font-size"][:-2]) * .75)
        self.font = get_font(size, weight, style)

        self.width = INPUT_WIDTH_PX

        if self.previous:
            space = self.previous.font.measure(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.height = self.font.metrics("linespace")

    def should_paint(self):
        return True

    def self_rect(self):
        return Rect(self.x, self.y,
            self.x + self.width, self.y + self.height)

    def paint(self):
        cmds = []
        bgcolor = self.node.style.get("background-color",
                                      "transparent")
        if bgcolor != "transparent":
            rect = DrawRect(self.self_rect(), bgcolor)
            cmds.append(rect)

        if self.node.tag == "input":
            text = self.node.attributes.get("value", "")
        elif self.node.tag == "button":
            if len(self.node.children) == 1 and \
               isinstance(self.node.children[0], Text):
                text = self.node.children[0].text
            else:
                print("Ignoring HTML contents inside button")
                text = ""

        color = self.node.style["color"]
        cmds.append(
            DrawText(self.x, self.y, text, self.font, color))

        if self.node.is_focused:
            cx = self.x + self.font.measure(text)
            cmds.append(DrawLine(
                cx, self.y, cx, self.y + self.height, "black", 1))
        return cmds

    @wbetools.js_hide
    def __repr__(self):
        if self.node.tag == "input":
            extra = "type=input"
        else:
            extra = "type=button text={}".format(self.node.children[0].text)
        return "InputLayout(x={}, y={}, width={}, height={}, {})".format(
            self.x, self.y, self.width, self.height, extra)

@wbetools.patch(DocumentLayout)
class DocumentLayout:
    def should_paint(self):
        return True

@wbetools.patch(LineLayout)
class LineLayout:
    def should_paint(self):
        return True

@wbetools.patch(TextLayout)
class TextLayout:
    def should_paint(self):
        return True

@wbetools.patch(BlockLayout)
class BlockLayout:
    def layout_mode(self):
        if isinstance(self.node, Text):
            return "inline"
        elif any([isinstance(child, Element) and \
                  child.tag in BLOCK_ELEMENTS
                  for child in self.node.children]):
            return "block"
        elif self.node.children or self.node.tag == "input":
            return "inline"
        else:
            return "block"

    def recurse(self, node):
        if isinstance(node, Text):
            for word in node.text.split():
                self.word(node, word)
        else:
            if node.tag == "br":
                self.new_line()
            elif node.tag == "input" or node.tag == "button":
                self.input(node)
            else:
                for child in node.children:
                    self.recurse(child)

    def input(self, node):
        w = INPUT_WIDTH_PX
        if self.cursor_x + w > self.width:
            self.new_line()
        line = self.children[-1]
        previous_word = line.children[-1] if line.children else None
        input = InputLayout(node, line, previous_word)
        line.children.append(input)

        weight = node.style["font-weight"]
        style = node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(node.style["font-size"][:-2]) * .75)
        font = get_font(size, weight, style)

        self.cursor_x += w + font.measure(" ")

    def should_paint(self):
        return isinstance(self.node, Text) or \
            (self.node.tag != "input" and self.node.tag !=  "button")

    def paint(self):
        cmds = []
        bgcolor = self.node.style.get("background-color",
                                      "transparent")
        if bgcolor != "transparent":
            draw_rect = DrawRect(self.self_rect(), bgcolor)
            cmds.append(draw_rect)
        return cmds

    @wbetools.js_hide
    def __repr__(self):
        return "BlockLayout[{}](x={}, y={}, width={}, height={}, node={})".format(
            self.layout_mode(), self.x, self.y, self.width, self.height, self.node)

def paint_tree(layout_object, display_list):
    if layout_object.should_paint():
        display_list.extend(layout_object.paint())

    for child in layout_object.children:
        paint_tree(child, display_list)

@wbetools.patch(Tab)
class Tab:
    def __init__(self, tab_height):
        self.url = None
        self.history = []
        self.tab_height = tab_height
        self.focus = None

    def load(self, url, payload=None):
        self.scroll = 0
        self.url = url
        self.history.append(url)
        body = url.request(payload)
        self.nodes = HTMLParser(body).parse()

        self.rules = DEFAULT_STYLE_SHEET.copy()
        links = [node.attributes["href"]
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "link"
                 and node.attributes.get("rel") == "stylesheet"
                 and "href" in node.attributes]
        for link in links:
            try:
                body = url.resolve(link).request()
            except:
                continue
            self.rules.extend(CSSParser(body).parse())
        self.render()

    def render(self):
        style(self.nodes, sorted(self.rules, key=cascade_priority))
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        paint_tree(self.document, self.display_list)

    def click(self, x, y):
        if self.focus:
            self.focus.is_focused = False
        self.focus = None
        y += self.scroll
        objs = [obj for obj in tree_to_list(self.document, [])
                if obj.x <= x < obj.x + obj.width
                and obj.y <= y < obj.y + obj.height]
        if not objs: return self.render()
        elt = objs[-1].node
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "a" and "href" in elt.attributes:
                url = self.url.resolve(elt.attributes["href"])
                return self.load(url)
            elif elt.tag == "input":
                elt.attributes["value"] = ""
                self.focus = elt
                elt.is_focused = True
                return self.render()
            elif elt.tag == "button":
                while elt:
                    if elt.tag == "form" and "action" in elt.attributes:
                        return self.submit_form(elt)
                    elt = elt.parent
            elt = elt.parent
        self.render()

    def submit_form(self, elt):
        inputs = [node for node in tree_to_list(elt, [])
                  if isinstance(node, Element)
                  and node.tag == "input"
                  and "name" in node.attributes]

        body = ""
        for input in inputs:
            name = input.attributes["name"]
            value = input.attributes.get("value", "")
            name = urllib.parse.quote(name)
            value = urllib.parse.quote(value)
            body += "&" + name + "=" + value
        body = body[1:]

        url = self.url.resolve(elt.attributes["action"])
        self.load(url, body)

    def keypress(self, char):
        if self.focus:
            self.focus.attributes["value"] += char
            self.render()

@wbetools.patch(Chrome)
class Chrome:
    def keypress(self, char):
        if self.focus == "address bar":
            self.address_bar += char
            return True
        return False

    def blur(self):
        self.focus = None

@wbetools.patch(Browser)
class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT,
            bg="white",
        )
        self.canvas.pack()

        self.window.bind("<Down>", self.handle_down)
        self.window.bind("<Button-1>", self.handle_click)
        self.window.bind("<Key>", self.handle_key)
        self.window.bind("<Return>", self.handle_enter)

        self.tabs = []
        self.active_tab = None
        self.focus = None
        self.chrome = Chrome(self)

    def handle_click(self, e):
        if e.y < self.chrome.bottom:
            self.focus = None
            self.chrome.click(e.x, e.y)
        else:
            self.focus = "content"
            self.chrome.blur()
            tab_y = e.y - self.chrome.bottom
            self.active_tab.click(e.x, tab_y)
        self.draw()

    def handle_key(self, e):
        if len(e.char) == 0: return
        if not (0x20 <= ord(e.char) < 0x7f): return
        if self.chrome.keypress(e.char):
            self.draw()
        elif self.focus == "content":
            self.active_tab.keypress(e.char)
            self.draw()

if __name__ == "__main__":
    import sys
    Browser().new_tab(URL(sys.argv[1]))
    tkinter.mainloop()
