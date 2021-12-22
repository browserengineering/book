"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 11 (Adding Visual Effects),
without exercises.
"""

import ctypes
import dukpy
import io
import math
import sdl2
import sdl2.ext as sdl2ext
import skia
import socket
import ssl
import threading
import time
import urllib.parse
from lab4 import print_tree
from lab4 import Element
from lab4 import Text
from lab4 import HTMLParser
from lab6 import cascade_priority
from lab6 import layout_mode
from lab6 import resolve_url
from lab6 import tree_to_list
from lab6 import INHERITED_PROPERTIES
from lab6 import CSSParser, compute_style, style
from lab6 import TagSelector, DescendantSelector
from lab9 import EVENT_DISPATCH_CODE
from lab10 import COOKIE_JAR, request, url_origin, JSContext

FONTS = {}

def get_font(size, weight, style):
    key = (weight, style)
    if key not in FONTS:
        if weight == "bold":
            skia_weight = skia.FontStyle.kBold_Weight
        else:
            skia_weight = skia.FontStyle.kNormal_Weight
        if style == "italic":
            skia_style = skia.FontStyle.kItalic_Slant
        else:
            skia_style = skia.FontStyle.kUpright_Slant
        skia_width = skia.FontStyle.kNormal_Width
        style_info = \
            skia.FontStyle(skia_weight, skia_width, skia_style)
        font = skia.Typeface('Arial', style_info)
        FONTS[key] = font
    return skia.Font(FONTS[key], size)

def parse_color(color):
    if color == "white":
        return skia.ColorWHITE
    elif color == "lightblue":
        return skia.ColorSetARGB(0xFF, 0xAD, 0xD8, 0xE6)
    elif color == "orange":
        return skia.ColorSetARGB(0xFF, 0xFF, 0xA5, 0x00)
    elif color == "red":
        return skia.ColorRED
    elif color == "green":
        return skia.ColorGREEN
    elif color == "blue":
        return skia.ColorBLUE
    elif color == "gray":
        return skia.ColorGRAY
    else:
        return skia.ColorBLACK

def parse_blend_mode(blend_mode_str):
    if blend_mode_str == "multiply":
        return skia.BlendMode.kMultiply
    elif blend_mode_str == "difference":
        return skia.BlendMode.kDifference
    else:
        return skia.BlendMode.kSrcOver

def linespace(font):
    metrics = font.getMetrics()
    return metrics.fDescent - metrics.fAscent

class SaveLayer:
    def __init__(self, sk_paint, cmds,
            should_save=True, should_paint_cmds=True):
        self.should_save = should_save
        self.should_paint_cmds = should_paint_cmds
        self.sk_paint = sk_paint
        self.cmds = cmds
        self.rect = skia.Rect.MakeEmpty()
        for cmd in self.cmds:
            self.rect.join(cmd.rect)

    def execute(self, canvas):
        if self.should_save:
            canvas.saveLayer(paint=self.sk_paint)
        if self.should_paint_cmds:
            for cmd in self.cmds:
                cmd.execute(canvas)
        if self.should_save:
            canvas.restore()

class DrawRRect:
    def __init__(self, rect, radius, color):
        self.rect = rect
        self.rrect = skia.RRect.MakeRectXY(rect, radius, radius)
        self.color = color

    def execute(self, canvas):
        sk_color = parse_color(self.color)
        canvas.drawRRect(self.rrect,
            paint=skia.Paint(Color=sk_color))

class DrawText:
    def __init__(self, x1, y1, text, font, color):
        self.left = x1
        self.top = y1
        self.right = x1 + font.measureText(text)
        self.bottom = y1 - font.getMetrics().fAscent + font.getMetrics().fDescent
        self.rect = \
            skia.Rect.MakeLTRB(x1, y1, self.right, self.bottom)
        self.font = font
        self.text = text
        self.color = color

    def execute(self, canvas):
        draw_text(canvas, self.left, self.top,
            self.text, self.font, self.color)

    def __repr__(self):
        return "DrawText(text={})".format(self.text)

class DrawRect:
    def __init__(self, x1, y1, x2, y2, color):
        self.rect = skia.Rect.MakeLTRB(x1, y1, x2, y2)
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color

    def execute(self, canvas):
        draw_rect(canvas,
            self.left, self.top,
            self.right, self.bottom,
            fill=self.color, width=0)

    def __repr__(self):
        return "DrawRect(top={} left={} bottom={} right={} color={})".format(
            self.left, self.top, self.right, self.bottom, self.color)

class ClipRRect:
    def __init__(self, rect, radius, cmds, should_clip=True):
        self.rect = rect
        self.rrect = skia.RRect.MakeRectXY(rect, radius, radius)
        self.cmds = cmds
        self.should_clip = should_clip

    def execute(self, canvas):
        if self.should_clip:
            canvas.save()
            canvas.clipRRect(self.rrect)

        for cmd in self.cmds:
            cmd.execute(canvas)

        if self.should_clip:
            canvas.restore()

def draw_line(canvas, x1, y1, x2, y2):
    path = skia.Path().moveTo(x1, y1).lineTo(x2, y2)
    paint = skia.Paint(Color=skia.ColorBLACK)
    paint.setStyle(skia.Paint.kStroke_Style)
    paint.setStrokeWidth(1);
    canvas.drawPath(path, paint)

def draw_text(canvas, x, y, text, font, color=None):
    sk_color = parse_color(color)
    paint = skia.Paint(AntiAlias=True, Color=sk_color)
    canvas.drawString(
        text, float(x), y - font.getMetrics().fAscent,
        font, paint)

def draw_rect(canvas, l, t, r, b, fill=None, width=1):
    paint = skia.Paint()
    if fill:
        paint.setStrokeWidth(width);
        paint.setColor(parse_color(fill))
    else:
        paint.setStyle(skia.Paint.kStroke_Style)
        paint.setStrokeWidth(1);
        paint.setColor(skia.ColorBLACK)
    rect = skia.Rect.MakeLTRB(l, t, r, b)
    canvas.drawRect(rect, paint)

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
        cmds = []

        rect = skia.Rect.MakeLTRB(
            self.x, self.y,
            self.x + self.width, self.y + self.height)
        bgcolor = self.node.style.get("background-color",
                                 "transparent")
        if bgcolor != "transparent":
            radius = float(
                self.node.style.get("border-radius", "0px")[:-2])
            cmds.append(DrawRRect(rect, radius, bgcolor))

        for child in self.children:
            child.paint(cmds)

        cmds = paint_visual_effects(self.node, cmds, rect)
        display_list.extend(cmds)

    def __repr__(self):
        return "BlockLayout(x={}, y={}, width={}, height={})".format(
            self.x, self.x, self.width, self.height)

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

    def text(self, node):
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        size = float(node.style["font-size"][:-2])
        font = get_font(size, weight, size)
        for word in node.text.split():
            w = font.measureText(word)
            if self.cursor_x + w > self.x + self.width:
                self.new_line()
            line = self.children[-1]
            text = TextLayout(node, word, line, self.previous_word)
            line.children.append(text)
            self.previous_word = text
            self.cursor_x += w + font.measureText(" ")

    def input(self, node):
        w = INPUT_WIDTH_PX
        if self.cursor_x + w > self.x + self.width:
            self.new_line()
        line = self.children[-1]
        input = InputLayout(node, line, self.previous_word)
        line.children.append(input)
        self.previous_word = input
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        size = float(node.style["font-size"][:-2])
        font = get_font(size, weight, size)
        self.cursor_x += w + font.measureText(" ")

    def paint(self, display_list):
        cmds = []

        rect = skia.Rect.MakeLTRB(
            self.x, self.y, self.x + self.width,
            self.y + self.height)

        bgcolor = self.node.style.get("background-color",
                                 "transparent")
        if bgcolor != "transparent":
            radius = float(self.node.style.get("border-radius", "0px")[:-2])
            cmds.append(DrawRRect(rect, radius, bgcolor))
 
        for child in self.children:
            child.paint(cmds)

        cmds = paint_visual_effects(self.node, cmds, rect)
        display_list.extend(cmds)

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

        max_ascent = max([-word.font.getMetrics().fAscent 
                          for word in self.children])
        baseline = self.y + 1.25 * max_ascent
        for word in self.children:
            word.y = baseline + word.font.getMetrics().fAscent
        max_descent = max([word.font.getMetrics().fDescent
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
        size = float(self.node.style["font-size"][:-2])
        self.font = get_font(size, weight, style)

        # Do not set self.y!!!
        self.width = self.font.measureText(self.word)

        if self.previous:
            space = self.previous.font.measureText(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.height = linespace(self.font)

    def paint(self, display_list):
        color = self.node.style["color"]
        display_list.append(
            DrawText(self.x, self.y, self.word, self.font, color))
    
    def __repr__(self):
        return "TextLayout(x={}, y={}, width={}, height={}".format(
            self.x, self.y, self.width, self.height)

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
        size = float(self.node.style["font-size"][:-2])
        self.font = get_font(size, weight, style)

        self.width = INPUT_WIDTH_PX
        self.height = linespace(self.font)

        if self.previous:
            space = self.previous.font.measureText(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

    def paint(self, display_list):
        cmds = []

        rect = skia.Rect.MakeLTRB(
            self.x, self.y, self.x + self.width,
            self.y + self.height)

        bgcolor = self.node.style.get("background-color",
                                 "transparent")
        if bgcolor != "transparent":
            radius = float(self.node.style.get("border-radius", "0px")[:-2])
            cmds.append(DrawRRect(rect, radius, bgcolor))

        if self.node.tag == "input":
            text = self.node.attributes.get("value", "")
        elif self.node.tag == "button":
            text = self.node.children[0].text

        color = self.node.style["color"]
        cmds.append(DrawText(self.x, self.y,
                             text, self.font, color))

        cmds = paint_visual_effects(self.node, cmds, rect)
        display_list.extend(cmds)

    def __repr__(self):
        return "InputLayout(x={}, y={}, width={}, height={})".format(
            self.x, self.y, self.width, self.height)

def paint_visual_effects(node, cmds, rect):
    opacity = float(node.style.get("opacity", "1.0"))

    blend_mode = parse_blend_mode(node.style.get("mix-blend-mode"))

    border_radius = float(node.style.get("border-radius", "0px")[:-2])
    if node.style.get("overflow", "visible") == "clip":
        clip_radius = border_radius
    else:
        clip_radius = 0

    needs_clip = node.style.get("overflow", "visible") == "clip"
    needs_blend_isolation = blend_mode != skia.BlendMode.kSrcOver or \
        needs_clip or opacity != 1.0

    return [
        SaveLayer(skia.Paint(BlendMode=blend_mode, Alphaf=opacity), [
            ClipRRect(rect, clip_radius,
                cmds,
            should_clip=needs_clip),
        ], should_save=needs_blend_isolation),
    ]

class JSContext:
    def __init__(self, tab):
        self.tab = tab

        self.interp = dukpy.JSInterpreter()
        self.interp.export_function("log", print)
        self.interp.export_function("querySelectorAll",
            self.querySelectorAll)
        self.interp.export_function("getAttribute",
            self.getAttribute)
        self.interp.export_function("innerHTML_set", self.innerHTML_set)
        self.interp.export_function("XMLHttpRequest_send",
            self.XMLHttpRequest_send)
        self.interp.export_function("now",
            self.now)
        self.interp.export_function("requestAnimationFrame",
            self.requestAnimationFrame)
        with open("runtime12.js") as f:
            self.interp.evaljs(f.read())

        self.node_to_handle = {}
        self.handle_to_node = {}

    def run(self, script, code):
        try:
            print("Script returned: ", self.interp.evaljs(code))
        except dukpy.JSRuntimeError as e:
            print("Script", script, "crashed", e)

    def dispatch_event(self, type, elt):
        handle = self.node_to_handle.get(elt, -1)
        do_default = self.interp.evaljs(
            EVENT_DISPATCH_CODE, type=type, handle=handle)
        return not do_default

    def get_handle(self, elt):
        if elt not in self.node_to_handle:
            handle = len(self.node_to_handle)
            self.node_to_handle[elt] = handle
            self.handle_to_node[handle] = elt
        else:
            handle = self.node_to_handle[elt]
        return handle

    def querySelectorAll(self, selector_text):
        selector = CSSParser(selector_text).selector()
        nodes = [node for node
                 in tree_to_list(self.tab.nodes, [])
                 if selector.matches(node)]
        return [self.get_handle(node) for node in nodes]

    def getAttribute(self, handle, attr):
        elt = self.handle_to_node[handle]
        return elt.attributes.get(attr, None)

    def innerHTML_set(self, handle, s):
#        print('innerhtml_set')
        doc = HTMLParser("<html><body>" + s + "</body></html>").parse()
        new_nodes = doc.children[0].children
        elt = self.handle_to_node[handle]
        elt.children = new_nodes
        for child in elt.children:
            child.parent = elt
        self.tab.run_rendering_pipeline()

    def XMLHttpRequest_send(self, method, url, body):
        full_url = resolve_url(url, self.tab.url)
        if not self.tab.allowed_request(full_url):
            raise Exception("Cross-origin XHR blocked by CSP")
        headers, out = request(full_url, self.tab.url, payload=body)
        if url_origin(full_url) != url_origin(self.tab.url):
            raise Exception("Cross-origin XHR request not allowed")
        return out

    def now(self):
        return int(time.time() * 1000)

    def requestAnimationFrame(self):
        self.tab.request_animation_frame_callback()

SCROLL_STEP = 100
CHROME_PX = 100

def set_timeout(func, sec):     
    t = None
    def func_wrapper():
#        print(threading.current_thread())
#        print(threading.main_thread())
        func()
        t.cancel()
    t = threading.Timer(sec, func_wrapper)
    t.start()


def raster(display_list, canvas):
    for cmd in display_list:
        cmd.execute(canvas)

class Tab:
    def __init__(self, browser):
        self.history = []
        self.focus = None
        self.url = None
        self.scroll = 0
        self.needs_raf_callbacks = False
        self.display_scheduled = False
        self.browser = browser
        self.main_thread_runner = MainThreadRunner(self)
        self.main_thread_runner.start()

        with open("browser8.css") as f:
            self.default_style_sheet = CSSParser(f.read()).parse()

    def allowed_request(self, url):
        return self.allowed_origins == None or \
            url_origin(url) in self.allowed_origins

    def cookie_string(self):
        origin = url_origin(self.history[-1])
        cookie_string = ""
        if not origin in self.cookies:
            return cookie_string
        for key, value in self.cookies[origin].items():
            cookie_string += "&" + key + "=" + value
        return cookie_string[1:]

    def script_run_wrapper(self, script, script_text):
        return Task(self.js.run, script, script_text)

    def handle_quit(self):
        self.main_thread_runner.set_needs_quit()

    def load(self, url, body=None):
        headers, body = request(url, self.url, payload=body)
        self.scroll = 0
        self.url = url
        self.history.append(url)

        self.allowed_origins = None
        if "content-security-policy" in headers:
           csp = headers["content-security-policy"].split()
           if len(csp) > 0 and csp[0] == "default-src":
               self.allowed_origins = csp[1:]

        self.nodes = HTMLParser(body).parse()

        self.js = JSContext(self)
        scripts = [node.attributes["src"] for node
                   in tree_to_list(self.nodes, [])
                   if isinstance(node, Element)
                   and node.tag == "script"
                   and "src" in node.attributes]
        for script in scripts:
            script_url = resolve_url(script, url)
            if not self.allowed_request(script_url):
                print("Blocked script", script, "due to CSP")
                continue
            header, body = request(script_url, url)
            self.main_thread_runner.schedule_script_task(
                self.script_run_wrapper(script, body))

        self.rules = self.default_style_sheet.copy()
        links = [node.attributes["href"]
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "link"
                 and "href" in node.attributes
                 and node.attributes.get("rel") == "stylesheet"]
        for link in links:
            style_url = resolve_url(link, url)
            if not self.allowed_request(style_url):
                print("Blocked style", link, "due to CSP")
                continue
            try:
                header, body = request(style_url, url)
            except:
                continue
            self.rules.extend(CSSParser(body).parse())
        self.set_needs_animation_frame()

    def set_needs_animation_frame(self):
#        print('set_needs_animation_frame')
        def callback():
            self.display_scheduled = False
            self.main_thread_runner.schedule_animation_frame()
        if not self.display_scheduled:
            set_timeout(callback, REFRESH_RATE_SEC)
            self.display_scheduled = True

    def request_animation_frame_callback(self):
        self.needs_raf_callbacks = True
        self.set_needs_animation_frame()

    def run_animation_frame(self):
#        print("run_animation_frame")
        self.needs_animation_frame = False

        if (self.needs_raf_callbacks):
            self.needs_raf_callbacks = False
            self.js.interp.evaljs("__runRAFHandlers()")

        self.run_rendering_pipeline()
        self.browser.commit()

    def run_rendering_pipeline(self):
#        print("run_rendering_pipeline")
        style(self.nodes, sorted(self.rules, key=cascade_priority))
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        self.document.paint(self.display_list)
#        print("rendering pipeline done")

#        if self.focus:
#            obj = [obj for obj in tree_to_list(self.document, [])
#                   if obj.node == self.focus][0]
#            text = self.focus.attributes.get("value", "")
#            x = obj.x + obj.font.measureText(text)
#            y = obj.y
#            draw_line(canvas, x, y, x, y + obj.height)

    def schedule_scroll(self):
        self.main_thread_runner.schedule_browser_task(
            Task(self.scrolldown))

    def schedule_click(self, x, y):
        self.main_thread_runner.schedule_browser_task(
            Task(self.click, x, y))

    def scrolldown(self):
        max_y = self.document.height - HEIGHT
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)
        self.set_needs_animation_frame()

    def click(self, x, y):
        self.run_rendering_pipeline()
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

class Task:
    def __init__(self, task_code, arg1=None, arg2=None):
        self.task_code = task_code
        self.arg1 = arg1
        self.arg2 = arg2
        self.__name__ = "task"

    def __call__(self):
        if self.arg2:
            self.task_code(self.arg1, self.arg2)
        elif self.arg1:
            self.task_code(self.arg1)
        else:
            self.task_code()
        # Prevent it accidentally running twice.
        self.task_code = None
        self.arg1 = None
        self.arg2 = None

class TaskQueue:
    def __init__(self, lock):
        self.tasks = []
        self.lock = lock

    def add_task(self, task_code):
        self.lock.acquire(blocking=True)
        self.tasks.append(task_code)
        self.lock.release()

    def has_tasks(self):
        self.lock.acquire(blocking=True)
        retval = len(self.tasks) > 0
        self.lock.release()
        return retval

    def get_next_task(self):
        self.lock.acquire(blocking=True)
        retval = self.tasks.pop(0)
        self.lock.release()
        return retval

class MainThreadRunner:
    def __init__(self, tab):
        self.lock = threading.Lock()
        self.tab = tab
        self.needs_animation_frame = False
        self.main_thread = threading.Thread(target=self.run, args=())
        self.script_tasks = TaskQueue(self.lock)
        self.browser_tasks = TaskQueue(self.lock)
        self.needs_quit = False

    def schedule_animation_frame(self):
        self.lock.acquire(blocking=True)
        self.needs_animation_frame = True
        self.lock.release()

    def schedule_script_task(self, script):
        self.script_tasks.add_task(script)

    def schedule_browser_task(self, callback):
        self.browser_tasks.add_task(callback)

    def schedule_event_handler():
        pass

    def set_needs_quit(self):
        self.needs_quit = True

    def start(self):
        self.main_thread.start()

    def run(self):
        while True:
            if self.needs_quit:
                return;
            self.lock.acquire(blocking=True)
            needs_animation_frame = self.needs_animation_frame
            self.lock.release()
            if needs_animation_frame:
                self.tab.run_animation_frame()

            browser_method = None
            if self.browser_tasks.has_tasks():
                browser_method = self.browser_tasks.get_next_task()
            if browser_method:
                browser_method()

            script = None
            if self.script_tasks.has_tasks():
                script = self.script_tasks.get_next_task()

            if script:
                script()

            time.sleep(0.001) # 1ms

REFRESH_RATE_SEC = 0.016 # 16ms

class Browser:
    def __init__(self):
        self.sdl_window = sdl2.SDL_CreateWindow(b"Browser",
            sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
            WIDTH, HEIGHT, sdl2.SDL_WINDOW_SHOWN)
        self.root_surface = skia.Surface.MakeRaster(
            skia.ImageInfo.Make(
            WIDTH, HEIGHT,
            ct=skia.kRGBA_8888_ColorType,
            at=skia.kUnpremul_AlphaType))
        self.chrome_surface = skia.Surface(WIDTH, CHROME_PX)
        self.tab_surface = None

        self.tabs = []
        self.active_tab = None
        self.focus = None
        self.address_bar = ""

        if sdl2.SDL_BYTEORDER == sdl2.SDL_BIG_ENDIAN:
            self.RED_MASK = 0xff000000
            self.GREEN_MASK = 0x00ff0000
            self.BLUE_MASK = 0x0000ff00
            self.ALPHA_MASK = 0x000000ff
        else:
            self.RED_MASK = 0x000000ff
            self.GREEN_MASK = 0x0000ff00
            self.BLUE_MASK = 0x00ff0000
            self.ALPHA_MASK = 0xff000000

        self.needs_tab_raster = False
        self.needs_chrome_raster = True
        self.needs_draw = True

        self.tab_height = None
        self.tab_display_list = None

    def set_needs_tab_raster(self):
        self.needs_tab_raster = True
        self.needs_draw = True

    def set_needs_chrome_raster(self):
        self.needs_chrome_raster = True
        self.need_draw = True

    def set_needs_draw(self):
        self.needs_draw = True

    def commit(self):
        active_tab = self.tabs[self.active_tab]
        self.tab_height = math.ceil(active_tab.document.height)
        self.tab_display_list = active_tab.display_list.copy()
        self.set_needs_tab_raster()

    def raster_and_draw(self):
        if self.needs_chrome_raster:
            self.raster_chrome()
        if self.needs_tab_raster:
            self.raster_tab()
        if self.needs_draw:
            self.draw()
        self.needs_tab_raster = False
        self.needs_chrome_raster = False
        self.needs_draw = False

    def handle_down(self):
        self.tabs[self.active_tab].schedule_scroll()
        self.set_needs_draw()

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
            self.set_needs_chrome_raster()
        else:
            self.focus = "content"
            self.tabs[self.active_tab].schedule_click(e.x, e.y - CHROME_PX)

    def handle_key(self, char):
        if not (0x20 <= ord(char) < 0x7f): return
        if self.focus == "address bar":
            self.address_bar += char
            self.set_needs_chrome_raster()
        elif self.focus == "content":
            self.tabs[self.active_tab].keypress(char)
            self.raster_tab()
#            self.draw()

    def handle_enter(self):
        if self.focus == "address bar":
            self.tabs[self.active_tab].load(self.address_bar)
            self.focus = None
            self.raster_tab()
#            self.draw()

    def load(self, url):
        new_tab = Tab(self)
        new_tab.load(url)
        self.active_tab = len(self.tabs)
        self.tabs.append(new_tab)

    def raster_tab(self):
#        print("raster tab")
        if not self.tab_surface or \
                self.tab_height != self.tab_surface.height():
            self.tab_surface = skia.Surface(WIDTH, self.tab_height)

        canvas = self.tab_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        raster(self.tab_display_list, canvas)

    def raster_chrome(self):
        canvas = self.chrome_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
    
        # Draw the tabs UI:
        tabfont = skia.Font(skia.Typeface('Arial'), 20)
        for i, tab in enumerate(self.tabs):
            name = "Tab {}".format(i)
            x1, x2 = 40 + 80 * i, 120 + 80 * i
            draw_line(canvas, x1, 0, x1, 40)
            draw_line(canvas, x2, 0, x2, 40)
            draw_text(canvas, x1 + 10, 10, name, tabfont)
            if i == self.active_tab:
                draw_line(canvas, 0, 40, x1, 40)
                draw_line(canvas, x2, 40, WIDTH, 40)

        # Draw the plus button to add a tab:
        buttonfont = skia.Font(skia.Typeface('Arial'), 30)
        draw_rect(canvas, 10, 10, 30, 30)
        draw_text(canvas, 11, 4, "+", buttonfont)

        # Draw the URL address bar:
        draw_rect(canvas, 40, 50, WIDTH - 10, 90)
        if self.focus == "address bar":
            draw_text(canvas, 55, 55, self.address_bar, buttonfont)
            w = buttonfont.measureText(self.address_bar)
            draw_line(canvas, 55 + w, 55, 55 + w, 85)
        else:
            url = self.tabs[self.active_tab].url
            draw_text(canvas, 55, 55, url, buttonfont)

        # Draw the back button:
        draw_rect(canvas, 10, 50, 35, 90)
        path = \
            skia.Path().moveTo(15, 70).lineTo(30, 55).lineTo(30, 85)
        paint = skia.Paint(
            Color=skia.ColorBLACK, Style=skia.Paint.kFill_Style)
        canvas.drawPath(path, paint)

    def draw(self):
        canvas = self.root_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        
        if self.tab_surface:
            tab_rect = skia.Rect.MakeLTRB(0, CHROME_PX, WIDTH, HEIGHT)
            tab_offset = CHROME_PX - self.tabs[self.active_tab].scroll
            canvas.save()
            canvas.clipRect(tab_rect)
            canvas.translate(0, tab_offset)
            self.tab_surface.draw(canvas, 0, 0)
            canvas.restore()

        chrome_rect = skia.Rect.MakeLTRB(0, 0, WIDTH, CHROME_PX)
        canvas.save()
        canvas.clipRect(chrome_rect)
        self.chrome_surface.draw(canvas, 0, 0)
        canvas.restore()

        # This makes an image interface to the Skia surface, but
        # doesn't actually copy anything yet.
        skia_image = self.root_surface.makeImageSnapshot()
        skia_bytes = skia_image.tobytes()

        depth = 32 # Bits per pixel
        pitch = 4 * WIDTH # Bytes per row
        sdl_surface = sdl2.SDL_CreateRGBSurfaceFrom(
            skia_bytes, WIDTH, HEIGHT, depth, pitch,
            self.RED_MASK, self.GREEN_MASK,
            self.BLUE_MASK, self.ALPHA_MASK)

        rect = sdl2.SDL_Rect(0, 0, WIDTH, HEIGHT)
        window_surface = sdl2.SDL_GetWindowSurface(self.sdl_window)
        # SDL_BlitSurface is what actually does the copy.
        sdl2.SDL_BlitSurface(sdl_surface, rect, window_surface, rect)
        sdl2.SDL_UpdateWindowSurface(self.sdl_window)

    def handle_quit(self):
        self.tabs[self.active_tab].handle_quit()
        sdl2.SDL_DestroyWindow(self.sdl_window)

if __name__ == "__main__":
    import sys

    sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS)
    browser = Browser()
    browser.load(sys.argv[1])

    event = sdl2.SDL_Event()
    while True:
        if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == sdl2.SDL_QUIT:
                browser.handle_quit()
                sdl2.SDL_Quit()
                sys.exit()
                break
            elif event.type == sdl2.SDL_MOUSEBUTTONUP:
                browser.handle_click(event.button)
            elif event.type == sdl2.SDL_KEYDOWN:
                if event.key.keysym.sym == sdl2.SDLK_RETURN:
                    browser.handle_enter()
                elif event.key.keysym.sym == sdl2.SDLK_DOWN:
                    browser.handle_down()
            elif event.type == sdl2.SDL_TEXTINPUT:
                browser.handle_key(event.text.text.decode('utf8'))
        browser.raster_and_draw()
        time.sleep(0.001) # 1ms
