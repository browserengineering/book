"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 7 (Handling Buttons and Links),
without exercises.
"""

import wbetools
import socket
import ssl
import tkinter
import tkinter.font
from lab2 import WIDTH, HEIGHT, HSTEP, VSTEP, SCROLL_STEP
from lab3 import FONTS, get_font
from lab4 import Text, Element, print_tree, HTMLParser
from lab5 import BLOCK_ELEMENTS, DrawRect, DocumentLayout
from lab6 import CSSParser, TagSelector, DescendantSelector
from lab6 import INHERITED_PROPERTIES, style, cascade_priority
from lab6 import DrawText, URL, tree_to_list, BlockLayout
import wbetools

@wbetools.patch(URL)
class URL:
    def __str__(self):
        port_part = ":" + str(self.port)
        if self.scheme == "https" and self.port == 443:
            port_part = ""
        if self.scheme == "http" and self.port == 80:
            port_part = ""
        return self.scheme + "://" + self.host + port_part + self.path

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

        max_ascent = max([word.font.metrics("ascent") 
                          for word in self.children])
        baseline = self.y + 1.25 * max_ascent
        for word in self.children:
            word.y = baseline - word.font.metrics("ascent")
        max_descent = max([word.font.metrics("descent")
                           for word in self.children])
        self.height = 1.25 * (max_ascent + max_descent)

    def paint(self, display_list):
        for child in self.children:
            child.paint(display_list)

    def __repr__(self):
        return "LineLayout(x={}, y={}, width={}, height={})".format(
            self.x, self.y, self.width, self.height)

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
        self.font = None

    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(self.node.style["font-size"][:-2]) * .75)
        self.font = get_font(size, weight, style)

        # Do not set self.y!!!
        self.width = self.font.measure(self.word)

        if self.previous:
            space = self.previous.font.measure(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.height = self.font.metrics("linespace")

    def paint(self, display_list):
        color = self.node.style["color"]
        display_list.append(
            DrawText(self.x, self.y, self.word, self.font, color))
    
    @wbetools.js_hide
    def __repr__(self):
        return ("TextLayout(x={}, y={}, width={}, height={}, " +
            "node={}, word={})").format(
            self.x, self.y, self.width, self.height, self.node, self.word)

@wbetools.patch(BlockLayout)
class BlockLayout:
    def layout(self):
        wbetools.record("layout_pre", self)

        self.width = self.parent.width
        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        mode = self.layout_mode()
        if mode == "block":
            previous = None
            for child in self.node.children:
                next = BlockLayout(child, self, previous)
                self.children.append(next)
                previous = next
        else:
            self.new_line()
            self.recurse(self.node)

        for child in self.children:
            child.layout()

        self.height = sum([child.height for child in self.children])

        wbetools.record("layout_post", self)

    def recurse(self, node):
        if isinstance(node, Text):
            for word in node.text.split():
                self.word(node, word)
        else:
            if node.tag == "br":
                self.new_line()
            for child in node.children:
                self.recurse(child)

    def new_line(self):
        self.previous_word = None
        self.cursor_x = 0
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line)
        self.children.append(new_line)

    def word(self, node, word):
        font = self.get_font(node)
        w = font.measure(word)
        if self.cursor_x + w > self.width:
            self.new_line()
        line = self.children[-1]
        text = TextLayout(node, word, line, self.previous_word)
        line.children.append(text)
        self.previous_word = text
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
        return "BlockLayout[{}](x={}, y={}, width={}, height={})".format(
            self.layout_mode(), self.x, self.y, self.width, self.height)

class DrawLine:
    def __init__(self, x1, y1, x2, y2, color, thickness):
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color
        self.thickness = thickness

    def execute(self, scroll, canvas):
        canvas.create_line(
            self.left, self.top - scroll,
            self.right, self.bottom - scroll,
            fill=self.color, width=self.thickness,
        )

    def __repr__(self):
        return "DrawLine({}, {}, {}, {}, color={}, thickness={})".format(
            self.left, self.top, self.right, self.bottom,
            self.color, self.thickness)

class DrawOutline:
    def __init__(self, x1, y1, x2, y2, color, thickness):
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color
        self.thickness = thickness

    def execute(self, scroll, canvas):
        canvas.create_rectangle(
            self.left, self.top - scroll,
            self.right, self.bottom - scroll,
            width=self.thickness,
            outline=self.color,
        )

    def __repr__(self):
        return "DrawOutline({}, {}, {}, {}, color={}, thickness={})".format(
            self.left, self.top, self.right, self.bottom,
            self.color, self.thickness)

class Tab:
    def __init__(self, tab_height):
        self.url = None
        self.history = []
        self.tab_height = tab_height

        with open("browser6.css") as f:
            self.default_style_sheet = CSSParser(f.read()).parse()

    def load(self, url):
        body = url.request()
        self.scroll = 0
        self.url = url
        self.history.append(url)
        self.nodes = HTMLParser(body).parse()

        rules = self.default_style_sheet.copy()
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
            rules.extend(CSSParser(body).parse())
        style(self.nodes, sorted(rules, key=cascade_priority))

        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        self.document.paint(self.display_list)

    def draw(self, canvas, offset):
        for cmd in self.display_list:
            if cmd.top > self.scroll + self.tab_height:
                continue
            if cmd.bottom < self.scroll: continue
            cmd.execute(self.scroll - offset, canvas)

    def scrolldown(self):
        max_y = max(
            self.document.height + 2*VSTEP - self.tab_height, 0)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)

    def click(self, x, y):
        y += self.scroll
        objs = [obj for obj in tree_to_list(self.document, [])
                if obj.x <= x < obj.x + obj.width
                and obj.y <= y < obj.y + obj.height]
        if not objs: return
        elt = objs[-1].node
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "a" and "href" in elt.attributes:
                url = self.url.resolve(elt.attributes["href"])
                return self.load(url)
            elt = elt.parent

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

    def __repr__(self):
        return "Tab(history={})".format(self.history)

def intersects(x, y, rect):
    (left, top, right, bottom) = rect
    return x >= left and x < right and y >= top and y < bottom

class Chrome:
    def __init__(self, browser):
        self.browser = browser
        self.font = get_font(20, "normal", "roman")
        font_height = self.font.metrics("linespace")

        self.padding = 5
        self.tab_header_bottom = font_height + 2 * self.padding
        self.addressbar_top = self.tab_header_bottom + self.padding
        self.bottom = \
            self.addressbar_top + font_height + \
            2 * self.padding

    def plus_bounds(self):
        plus_width = self.font.measure("+")
        return (self.padding, self.padding,
            self.padding + plus_width,
            self.tab_header_bottom - self.padding)

    def tab_bounds(self, i):
        tab_start_x = self.padding + self.font.measure("+") + \
            self.padding

        tab_width = self.padding + self.font.measure("Tab 1") + \
            self.padding

        return (tab_start_x + tab_width * i, self.padding,
            tab_start_x + tab_width + tab_width * i,
            self.tab_header_bottom)

    def backbutton_bounds(self):
        backbutton_width = self.font.measure("<")
        return (self.padding, self.addressbar_top,
            self.padding + backbutton_width,
            self.bottom - self.padding)

    def addressbar_bounds(self):
        (backbutton_left, backbutton_top, backbutton_right,
            backbutton_bottom) = \
            self.backbutton_bounds()

        return (backbutton_right + self.padding, self.addressbar_top,
            WIDTH - 10, self.bottom - self.padding)

    def paint(self):
        cmds = []
        cmds.append(
            DrawRect(0, 0, WIDTH, self.bottom, "white"))

        (plus_left, plus_top, plus_right, plus_bottom) = \
            self.plus_bounds()
        cmds.append(DrawOutline(
            plus_left, plus_top, plus_right, plus_bottom, "black", 1))
        cmds.append(DrawText(
            plus_left, plus_top, "+", self.font, "black"))

        for i, tab in enumerate(self.browser.tabs):
            name = "Tab {}".format(i)
            (tab_left, tab_top, tab_right, tab_bottom) = \
                self.tab_bounds(i)

            cmds.append(DrawLine(
                tab_left, 0, tab_left, tab_bottom, "black", 1))
            cmds.append(DrawLine(
                tab_right, 0, tab_right, tab_bottom, "black", 1))
            cmds.append(DrawText(
                tab_left + self.padding, tab_top,
                name, self.font, "black"))

            if i == self.browser.active_tab:
                cmds.append(DrawLine(
                    0, tab_bottom, tab_left, tab_bottom, "black", 1))
                cmds.append(DrawLine(
                    tab_right, tab_bottom, WIDTH, tab_bottom,
                    "black", 1))

        backbutton_width = self.font.measure("<")
        (backbutton_left, backbutton_top, backbutton_right,
            backbutton_bottom) = self.backbutton_bounds()
        cmds.append(DrawOutline(
            backbutton_left, backbutton_top,
            backbutton_right, backbutton_bottom,
            "black", 1))
        cmds.append(DrawText(
            backbutton_left, backbutton_top + self.padding,
            "<", self.font, "black"))

        (addressbar_left, addressbar_top, \
            addressbar_right, addressbar_bottom) = \
            self.addressbar_bounds()

        # Bounds around address bar
        cmds.append(DrawOutline(
            addressbar_left, addressbar_top, addressbar_right,
            addressbar_bottom, "black", 1))
        left_bar = addressbar_left + self.padding
        top_bar = addressbar_top + self.padding
        if self.browser.focus == "address bar":
            cmds.append(DrawText(
                left_bar, top_bar,
                self.browser.address_bar, self.font, "black"))
            w = self.font.measure(self.browser.address_bar)
            cmds.append(DrawLine(
                left_bar + w, top_bar,
                left_bar + w,
                self.bottom - self.padding, "red", 1))
        else:
            url = str(self.browser.tabs[self.browser.active_tab].url)
            cmds.append(DrawText(
                left_bar,
                top_bar,
                url, self.font, "black"))

        cmds.append(DrawLine(
            0, self.bottom, WIDTH,
            self.bottom, "black", 1))

        return cmds

    def click(self, x, y):
        if intersects(x, y, self.plus_bounds()):
            self.browser.load(URL("https://browser.engineering/"))
        elif intersects(x, y, self.backbutton_bounds()):
            self.browser.tabs[self.browser.active_tab].go_back()
        elif intersects(x, y, self.addressbar_bounds()):
            self.browser.focus = "address bar"
            self.browser.address_bar = ""
        else:
            for i, tab in enumerate(self.browser.tabs):
                if intersects(x, y, self.tab_bounds(i)):
                    self.browser.active_tab = i
                    break

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
        self.address_bar = ""
        self.chrome = Chrome(self)

    def handle_down(self, e):
        self.tabs[self.active_tab].scrolldown()
        self.draw()

    def handle_click(self, e):
        self.focus = None
        if e.y < self.chrome.bottom:
            self.chrome.click(e.x, e.y)
        else:
            self.tabs[self.active_tab].click(
                e.x, e.y - self.chrome.bottom)
        self.draw()

    def handle_key(self, e):
        if len(e.char) == 0: return
        if not (0x20 <= ord(e.char) < 0x7f): return
        if self.focus == "address bar":
            self.address_bar += e.char
            self.draw()

    def handle_enter(self, e):
        if self.focus == "address bar":
            self.tabs[self.active_tab].load(URL(self.address_bar))
            self.focus = None
            self.draw()

    def load(self, url):
        new_tab = Tab(HEIGHT - self.chrome.bottom)
        new_tab.load(url)
        self.active_tab = len(self.tabs)
        self.tabs.append(new_tab)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        self.tabs[self.active_tab].draw(self.canvas, self.chrome.bottom)
        for cmd in self.chrome.paint():
            cmd.execute(0, self.canvas)

if __name__ == "__main__":
    import sys
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()
