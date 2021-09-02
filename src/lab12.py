"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 12 (Adding Visual Effects),
without exercises.
"""

import dukpy
import skia
import socket
import ssl
import tkinter
import tkinter.font
import urllib.parse
from lab4 import print_tree
from lab4 import Element
from lab4 import Text
from lab4 import HTMLParser
from lab6 import cascade_priority
from lab6 import layout_mode
from lab6 import resolve_url
from lab6 import style
from lab6 import tree_to_list
from lab6 import CSSParser
from lab10 import request
from lab10 import url_origin
from lab10 import JSContext

def color_to_sk_color(color):
    if color == "white":
        return skia.ColorWHITE
    elif color == "lightblue":
        return skia.ColorSetARGB(0xFF, 0xAD, 0xD8, 0xE6)
    elif color == "orange":
        return skia.ColorSetARGB(0xFF, 0xFF, 0xA5, 0x00)
    elif color == "blue":
        return skia.ColorBLUE
    else:
        return skia.ColorBLACK

class Rasterizer:
    def __init__(self, canvas, skia_surface):
        self.canvas = canvas
        self.skia_surface = skia_surface

    def draw_rect(self, x1, y1, x2, y2, fill=None, width=1):
        rect = skia.Rect.MakeLTRB(x1, y1, x2, y2)
        if fill:
            self.canvas.create_rectangle(
                x1, y1, x2, y2, fill=fill, width=width)

            paint = skia.Paint()
            paint.setStrokeWidth(width);
            paint.setColor(color_to_sk_color(fill))
            with self.skia_surface as canvas:
                canvas.drawRect(rect, paint)
        else:
            self.canvas.create_rectangle(
                x1, y1, x2, y2, width=width)

            paint = skia.Paint()
            paint.setStyle(skia.Paint.kStroke_Style)
            paint.setStrokeWidth(1);
            paint.setColor(skia.ColorBLACK)
            with self.skia_surface as canvas:
                canvas.drawRect(rect, paint)

    def draw_polyline(self, x1, y1, x2, y2, x3=None, y3=None, fill=False):
        if x3:
            if fill:
                self.canvas.create_polygon(x1, y1, x2, y2, x3, y3, fill='black')
            else:
                self.canvas.create_polygon(x1, y1, x2, y2, x3, y3)
        else:
            self.canvas.create_line(x1, y1, x2, y2)

        path = skia.Path()
        path.moveTo(x1, y1)
        path.lineTo(x2, y2)
        if x3:
            path.lineTo(x3, y3)
        paint = skia.Paint()
        paint.setColor(skia.ColorBLACK)
        if fill:
            paint.setStyle(skia.Paint.kFill_Style)
        else:
            paint.setStyle(skia.Paint.kStroke_Style)
        paint.setStrokeWidth(1);
        with self.skia_surface as canvas:
            canvas.drawPath(path, paint)

    def draw_text(self, x, y, text, tkinter_font, skia_font, color=None):
        self.canvas.create_text(
            x, y, anchor='nw', text=text, font=tkinter_font, fill=color)

        paint = skia.Paint(AntiAlias=True, Color=color_to_sk_color(color))
        with self.skia_surface as canvas:
            canvas.drawString(text, x, y - skia_font.getMetrics().fAscent,
                skia_font, paint)

class DrawText:
    def __init__(self, x1, y1, text, tkinter_font, skia_font, color):
        self.top = y1
        self.left = x1
        self.text = text
        self.tkinter_font = tkinter_font
        self.skia_font = skia_font
        self.color = color

        self.bottom = y1 + self.tkinter_font.metrics("linespace")

    def execute(self, scroll, rasterizer):
        rasterizer.draw_text(
            self.left, self.top - scroll,
            self.text,
            self.tkinter_font,
            self.skia_font,
            self.color,
        )

    def __repr__(self):
        return "DrawText(text={})".fpormat(self.text)

class DrawRect:
    def __init__(self, x1, y1, x2, y2, color):
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color

    def execute(self, scroll, rasterizer):
        print(self.color)
        rasterizer.draw_rect(
            self.left, self.top - scroll,
            self.right, self.bottom - scroll,
            width=0,
            fill=self.color,
        )

    def __repr__(self):
        return "DrawRect(top={} left={} bottom={} right={} color={})".format(
            self.top, self.left, self.bottom, self.right, self.color)

INPUT_WIDTH_PX = 200

class LineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None

    def layout(self):
        self.width = self.parent.width
        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        for word in self.children:
            word.layout()

        if not self.children:
            self.height = 0
            return

        max_ascent = max([word.tkinter_font.metrics("ascent") 
                          for word in self.children])
        baseline = self.y + 1.2 * max_ascent
        for word in self.children:
            word.y = baseline - word.tkinter_font.metrics("ascent")
        max_descent = max([word.tkinter_font.metrics("descent")
                           for word in self.children])
        self.height = 1.2 * (max_ascent + max_descent)

    def paint(self, display_list):
        for child in self.children:
            child.paint(display_list)

    def __repr__(self):
        return "LineLayout(x={}, y={}, width={}, height={})".format(
            self.x, self.y, self.width, self.height)

def skia_font_style(weight, style):
    skia_weight = skia.FontStyle.kNormal_Weight
    if weight == "bold":
        skia_weight = skia.FontStyle.kBold_Weight
    skia_style = skia.FontStyle.kUpright_Slant
    if style == "italic":
        skia_style = skia.FontStyle.kItalic_Slant
    return skia.FontStyle(skia_weight, skia.FontStyle.kNormal_Width, skia_style)

class TextLayout:
    def __init__(self, node, word, parent, previous):
        self.node = node
        self.word = word
        self.children = []
        self.parent = parent
        self.previous = previous
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.tkinter_font = None
        self.skia_font = None

    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(self.node.style["font-size"][:-2]) * .75)
        self.tkinter_font = tkinter.font.Font(
            size=size, weight=weight, slant=style)
        self.skia_font = skia.Font(
            skia.Typeface('Arial', skia_font_style(weight, style)), size)

        # Do not set self.y!!!
        self.width = self.tkinter_font.measure(self.word)

        if self.previous:
            space = self.previous.tkinter_font.measure(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.height = self.tkinter_font.metrics("linespace")

    def paint(self, display_list):
        color = self.node.style["color"]
        display_list.append(
            DrawText(self.x, self.y, self.word, self.tkinter_font,
                self.skia_font, color))
    
    def __repr__(self):
        return "TextLayout(x={}, y={}, width={}, height={}, font={}".format(
            self.x, self.y, self.width, self.height, self.tkinter_font)

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
        self.tkinter_font = None
        self.skia_font = None

    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(self.node.style["font-size"][:-2]) * .75)
        self.tkinter_font = tkinter.font.Font(
            size=size, weight=weight, slant=style)
        self.skia_font = skia.Font(
            skia.Typeface('Arial', skia_font_style(weight, style)), size)

        self.width = INPUT_WIDTH_PX

        if self.previous:
            space = self.previous.tkinter_font.measure(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.height = self.tkinter_font.metrics("linespace")

    def paint(self, display_list):
        bgcolor = self.node.style.get("background-color",
                                      "transparent")
        if bgcolor != "transparent":
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, bgcolor)
            display_list.append(rect)

        if self.node.tag == "input":
            text = self.node.attributes.get("value", "")
        elif self.node.tag == "button":
            text = self.node.children[0].text

        color = self.node.style["color"]
        display_list.append(
            DrawText(self.x, self.y, text, self.tkinter_font,
                self.skia_font, color))

    def __repr__(self):
        return "InputLayout(x={}, y={}, width={}, height={})".format(
            self.x, self.y, self.width, self.height)

class BlockLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None

    def layout(self):
        previous = None
        for child in self.node.children:
            if layout_mode(child) == "inline":
                next = InlineLayout(child, self, previous)
            else:
                next = BlockLayout(child, self, previous)
            self.children.append(next)
            previous = next

        self.width = self.parent.width
        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        for child in self.children:
            child.layout()

        self.height = sum([child.height for child in self.children])

    def paint(self, display_list):
        for child in self.children:
            child.paint(display_list)

    def __repr__(self):
        return "BlockLayout(x={}, y={}, width={}, height={})".format(
            self.x, self.y, self.width, self.height)

class InlineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.display_list = None

    def layout(self):
        self.width = self.parent.width
        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        self.new_line()
        self.recurse(self.node)
        
        for line in self.children:
            line.layout()

        self.height = sum([line.height for line in self.children])

    def recurse(self, node):
        if isinstance(node, Text):
            self.text(node)
        else:
            if node.tag == "br":
                self.new_line()
            elif node.tag == "input" or node.tag == "button":
                self.input(node)
            else:
                for child in node.children:
                    self.recurse(child)

    def new_line(self):
        self.previous_word = None
        self.cursor_x = self.x
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line)
        self.children.append(new_line)

    def get_font(self, node):
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(node.style["font-size"][:-2]) * .75)
        return tkinter.font.Font(size=size, weight=weight, slant=style)

    def text(self, node):
        font = self.get_font(node)
        for word in node.text.split():
            w = font.measure(word)
            if self.cursor_x + w > self.x + self.width:
                self.new_line()
            line = self.children[-1]
            text = TextLayout(node, word, line, self.previous_word)
            line.children.append(text)
            self.previous_word = text
            self.cursor_x += w + font.measure(" ")

    def input(self, node):
        w = INPUT_WIDTH_PX
        if self.cursor_x + w > self.x + self.width:
            self.new_line()
        line = self.children[-1]
        input = InputLayout(node, line, self.previous_word)
        line.children.append(input)
        self.previous_word = input
        size = int(float(node.style["font-size"][:-2]) * .75)
        font = self.get_font(node)
        self.cursor_x += w + font.measure(" ")

    def paint(self, display_list):
        bgcolor = self.node.style.get("background-color",
                                      "transparent")
        if bgcolor != "transparent":
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, bgcolor)
            display_list.append(rect)
        for child in self.children:
            child.paint(display_list)

    def __repr__(self):
        return "InlineLayout(x={}, y={}, width={}, height={})".format(
            self.x, self.y, self.width, self.height)

class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.previous = None
        self.children = []

    def layout(self):
        child = BlockLayout(self.node, self, None)
        self.children.append(child)

        self.width = WIDTH - 2*HSTEP
        self.x = HSTEP
        self.y = VSTEP
        child.layout()
        self.height = child.height + 2*VSTEP

    def paint(self, display_list):
        self.children[0].paint(display_list)

    def __repr__(self):
        return "DocumentLayout()"

SCROLL_STEP = 100
CHROME_PX = 100

class Tab:
    def __init__(self):
        self.history = []
        self.focus = None
        self.cookies = {}

        with open("browser8.css") as f:
            self.default_style_sheet = CSSParser(f.read()).parse()

    def cookie_string(self):
        origin = url_origin(self.history[-1])
        cookie_string = ""
        if not origin in self.cookies:
            return cookie_string
        for key, value in self.cookies[origin].items():
            cookie_string += "&" + key + "=" + value
        return cookie_string[1:]

    def load(self, url, body=None):
        self.scroll = 0
        self.url = url
        self.history.append(url)
        req_headers = { "Cookie": self.cookie_string() }        
        headers, body = request(url, headers=req_headers, payload=body)
        if "set-cookie" in headers:
            if ";" in headers["set-cookie"]:
                kv, params = headers["set-cookie"].split(";", 1)
            else:
                kv = headers["set-cookie"]
            key, value = kv.split("=", 1)
            origin = url_origin(self.history[-1])
            self.cookies.setdefault(origin, {})[key] = value

        self.nodes = HTMLParser(body).parse()

        self.js = JSContext(self)
        scripts = [node.attributes["src"] for node
                   in tree_to_list(self.nodes, [])
                   if isinstance(node, Element)
                   and node.tag == "script"
                   and "src" in node.attributes]
        for script in scripts:
            header, body = request(resolve_url(script, url),
                headers=req_headers)
            try:
                print("Script returned: ", self.js.run(body))
            except dukpy.JSRuntimeError as e:
                print("Script", script, "crashed", e)

        self.rules = self.default_style_sheet.copy()
        links = [node.attributes["href"]
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "link"
                 and "href" in node.attributes
                 and node.attributes.get("rel") == "stylesheet"]
        for link in links:
            try:
                header, body = request(resolve_url(link, url),
                    headers=req_headers)
            except:
                continue
            self.rules.extend(CSSParser(body).parse())
        self.render()

    def render(self):
        style(self.nodes, sorted(self.rules, key=cascade_priority))
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        self.document.paint(self.display_list)

    def draw(self, rasterizer):
        for cmd in self.display_list:
            if cmd.top > self.scroll + HEIGHT - CHROME_PX: continue
            if cmd.bottom < self.scroll: continue
            cmd.execute(self.scroll - CHROME_PX, rasterizer)

        if self.focus:
            obj = [obj for obj in tree_to_list(self.document, [])
                   if obj.node == self.focus][0]
            text = self.focus.attributes.get("value", "")
            x = obj.x + obj.font.measure(text)
            y = obj.y - self.scroll + CHROME_PX
            rasterizer.canvas.create_line(x, y, x, y + obj.height)

    def scrolldown(self):
        max_y = self.document.height - HEIGHT
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)

    def click(self, x, y):
        self.focus = None
        y += self.scroll
        objs = [obj for obj in tree_to_list(self.document, [])
                if obj.x <= x < obj.x + obj.width
                and obj.y <= y < obj.y + obj.height]
        if not objs: return
        elt = objs[-1].node
        if elt and self.js.dispatch_event("click", elt): return
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "a" and "href" in elt.attributes:
                url = resolve_url(elt.attributes["href"], self.url)
                return self.load(url)
            elif elt.tag == "input":
                elt.attributes["value"] = ""
                self.focus = elt
                return
            elif elt.tag == "button":
                while elt:
                    if elt.tag == "form" and "action" in elt.attributes:
                        return self.submit_form(elt)
                    elt = elt.parent
            elt = elt.parent

    def submit_form(self, elt):
        if self.js.dispatch_event("submit", elt): return
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
        body = body [1:]

        url = resolve_url(elt.attributes["action"], self.url)
        self.load(url, body)

    def keypress(self, char):
        if self.focus:
            if self.js.dispatch_event("keydown", self.focus): return
            self.focus.attributes["value"] += char
        self.document.paint(self.display_list) # TODO: is this necessary?

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18

class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT
        )
        self.canvas.pack()

        self.skia_surface = skia.Surface(WIDTH, HEIGHT)

        self.window.bind("<Down>", self.handle_down)
        self.window.bind("<Button-1>", self.handle_click)
        self.window.bind("<Key>", self.handle_key)
        self.window.bind("<Return>", self.handle_enter)

        self.tabs = []
        self.active_tab = None
        self.focus = None
        self.address_bar = ""

    def handle_down(self, e):
        self.tabs[self.active_tab].scrolldown()
        self.draw()

    def handle_click(self, e):
        if e.y < CHROME_PX:
            self.focus = None
            if 40 <= e.x < 40 + 80 * len(self.tabs) and 0 <= e.y < 40:
                self.active_tab = int((e.x - 40) / 80)
            elif 10 <= e.x < 30 and 10 <= e.y < 30:
                self.load("https://browser.engineering/")
            elif 10 <= e.x < 35 and 40 <= e.y < 90:
                self.tabs[self.active_tab].go_back()
            elif 50 <= e.x < WIDTH - 10 and 40 <= e.y < 90:
                self.focus = "address bar"
                self.address_bar = ""
        else:
            self.focus = "content"
            self.tabs[self.active_tab].click(e.x, e.y - CHROME_PX)
        self.draw()

    def handle_key(self, e):
        if len(e.char) == 0: return
        if not (0x20 <= ord(e.char) < 0x7f): return
        if self.focus == "address bar":
            self.address_bar += e.char
            self.draw()
        elif self.focus == "content":
            self.tabs[self.active_tab].keypress(e.char)
            self.draw()

    def handle_enter(self, e):
        if self.focus == "address bar":
            self.tabs[self.active_tab].load(self.address_bar)
            self.focus = None
            self.draw()

    def load(self, url):
        new_tab = Tab()
        new_tab.load(url)
        self.active_tab = len(self.tabs)
        self.tabs.append(new_tab)
        self.draw()

    def draw(self):
        with self.skia_surface as canvas:
            canvas.clear(skia.ColorWHITE)
            self.canvas.delete("all")

            rasterizer = Rasterizer(self.canvas, self.skia_surface)

            self.tabs[self.active_tab].draw(rasterizer)
        
            rasterizer.draw_rect(0, 0, WIDTH, CHROME_PX, "white")

            tabfont = tkinter.font.Font(size=20)
            skia_tabfont = skia.Font(skia.Typeface('Arial'), 20)
            for i, tab in enumerate(self.tabs):
                name = "Tab {}".format(i)
                x1, x2 = 40 + 80 * i, 120 + 80 * i
                rasterizer.draw_polyline(x1, 0, x1, 40)
                rasterizer.draw_polyline(x2, 0, x2, 40)
                rasterizer.draw_text(x1 + 10, 10, name, tabfont, skia_tabfont)
                if i == self.active_tab:
                    rasterizer.draw_polyline(0, 40, x1, 40)
                    rasterizer.draw_polyline(x2, 40, WIDTH, 40)

            buttonfont = tkinter.font.Font(size=30)
            skia_buttonfont = skia.Font(skia.Typeface('Arial'), 30)
            rasterizer.draw_rect(10, 10, 30, 30)
            rasterizer.draw_text(11, 0, "+", buttonfont, skia_buttonfont)

            rasterizer.draw_rect(40, 50, WIDTH - 10, 90)
            if self.focus == "address bar":
                rasterizer.draw_text(55, 55, self.address_bar, buttonfont, skia_buttonfont)
                w = buttonfont.measure(self.address_bar)
                rasterizer.draw_polyline(55 + w, 55, 55 + w, 85)
            else:
                url = self.tabs[self.active_tab].url
                rasterizer.draw_text(55, 55, url, buttonfont, skia_buttonfont)

            rasterizer.draw_rect(10, 50, 35, 90)
            rasterizer.draw_polyline(
                15, 70, 30, 55, 30, 85, True)
        skia_image = self.skia_surface.makeImageSnapshot()
        skia_image.save('output.png', skia.kPNG)


if __name__ == "__main__":
    import sys
    Browser().load(sys.argv[1])
    tkinter.mainloop()
