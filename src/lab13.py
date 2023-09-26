"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 13 (Animations and Compositing),
without exercises.
"""

import ctypes
import dukpy
import math
import sdl2
import skia
import socket
import ssl
import threading
import time
import urllib.parse
import wbetools
import OpenGL.GL

from lab2 import WIDTH, HEIGHT, HSTEP, VSTEP, SCROLL_STEP
from lab4 import print_tree, HTMLParser
from lab5 import BLOCK_ELEMENTS
from lab6 import TagSelector, DescendantSelector
from lab6 import INHERITED_PROPERTIES, cascade_priority
from lab6 import tree_to_list
from lab7 import intersects
from lab8 import Text, Element, INPUT_WIDTH_PX
from lab9 import EVENT_DISPATCH_CODE
from lab10 import COOKIE_JAR, URL
from lab11 import FONTS, get_font, parse_color, parse_blend_mode, linespace
from lab12 import MeasureTime, SingleThreadedTaskRunner, TaskRunner
from lab12 import Task, REFRESH_RATE_SEC, clamp_scroll

@wbetools.patch(Text)
class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent
        self.style = {}
        self.is_focused = False
        self.animations = {}

@wbetools.patch(Element)
class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent
        self.style = {}
        self.is_focused = False
        self.animations = {}

class DrawCommand:
    def __init__(self, rect):
        self.rect = rect
        self.children = []

class VisualEffect:
    def __init__(self, rect, children, node=None):
        self.rect = rect.makeOffset(0.0, 0.0)
        self.children = children
        for child in self.children:
            self.rect.join(child.rect)
        self.node = node
        self.needs_compositing = any([
            child.needs_compositing for child in self.children
            if isinstance(child, VisualEffect)
        ])

def map_translation(rect, translation):
    if not translation:
        return rect
    else:
        (x, y) = translation
        matrix = skia.Matrix()
        matrix.setTranslate(x, y)
        return matrix.mapRect(rect)

class Transform(VisualEffect):
    def __init__(self, translation, rect, node, children):
        super().__init__(rect, children, node)
        self.translation = translation

    def execute(self, canvas):
        if self.translation:
            (x, y) = self.translation
            canvas.save()
            canvas.translate(x, y)
        for cmd in self.children:
            cmd.execute(canvas)
        if self.translation:
            canvas.restore()

    def map(self, rect):
        return map_translation(rect, self.translation)

    def clone(self, children):
        return Transform(self.translation, self.rect,
            self.node, children)

    def __repr__(self):
        if self.translation:
            (x, y) = self.translation
            return "Transform(translate({}, {}))".format(x, y)
        else:
            return "Transform(<no-op>)"

class DrawLine(DrawCommand):
    def __init__(self, x1, y1, x2, y2, color, thickness):
        super().__init__(skia.Rect.MakeLTRB(x1, y1, x2, y2))
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.color = color
        self.thickness = thickness

    def execute(self, canvas):
        path = skia.Path().moveTo(self.x1, self.y1).lineTo(self.x2, self.y2)
        paint = skia.Paint(Color=parse_color(self.color))
        paint.setStyle(skia.Paint.kStroke_Style)
        paint.setStrokeWidth(self.thickness)
        canvas.drawPath(path, paint)

    def __repr__(self):
        return "DrawLine top={} left={} bottom={} right={}".format(
            self.y1, self.x1, self.y2, self.x2)

class DrawRRect(DrawCommand):
    def __init__(self, rect, radius, color):
        super().__init__(rect)
        self.rrect = skia.RRect.MakeRectXY(rect, radius, radius)
        self.color = color

    def execute(self, canvas):
        sk_color = parse_color(self.color)
        canvas.drawRRect(self.rrect,
            paint=skia.Paint(Color=sk_color))

    def print(self, indent=0):
        return " " * indent + self.__repr__()

    def __repr__(self):
        return "DrawRRect(rect={}, color={})".format(
            str(self.rrect), self.color)

class DrawText(DrawCommand):
    def __init__(self, x1, y1, text, font, color):
        self.left = x1
        self.top = y1
        self.right = x1 + font.measureText(text)
        self.bottom = y1 - font.getMetrics().fAscent + font.getMetrics().fDescent
        self.font = font
        self.text = text
        self.color = color
        super().__init__(skia.Rect.MakeLTRB(x1, y1,
            self.right, self.bottom))

    def execute(self, canvas):
        paint = skia.Paint(AntiAlias=True, Color=parse_color(self.color))
        baseline = self.top - self.font.getMetrics().fAscent
        canvas.drawString(self.text, float(self.left), baseline,
            self.font, paint)

    def __repr__(self):
        return "DrawText(text={})".format(self.text)

class DrawRect(DrawCommand):
    def __init__(self, x1, y1, x2, y2, color):
        super().__init__(skia.Rect.MakeLTRB(x1, y1, x2, y2))
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color

    def execute(self, canvas):
        paint = skia.Paint()
        paint.setColor(parse_color(self.color))
        canvas.drawRect(self.rect, paint)

    def __repr__(self):
        return ("DrawRect(top={} left={} " +
            "bottom={} right={} color={})").format(
            self.top, self.left, self.bottom,
            self.right, self.color)

class DrawOutline(DrawCommand):
    def __init__(self, x1, y1, x2, y2, color, thickness):
        super().__init__(skia.Rect.MakeLTRB(x1, y1, x2, y2))
        self.color = color
        self.thickness = thickness

    def execute(self, canvas):
        paint = skia.Paint()
        paint.setStyle(skia.Paint.kStroke_Style)
        paint.setStrokeWidth(self.thickness)
        paint.setColor(parse_color(self.color))
        canvas.drawRect(self.rect, paint)

    @wbetools.js_hide
    def __repr__(self):
        return ("DrawOutline(top={} left={} " +
            "bottom={} right={} border_color={} " +
            "thickness={})").format(
            self.rect.top(), self.rect.left(), self.rect.bottom(),
            self.rect.right(), self.color,
            self.thickness)


class ClipRRect(VisualEffect):
    def __init__(self, rect, radius, children, should_clip=True):
        super().__init__(rect, children)
        self.should_clip = should_clip
        self.radius = radius
        self.rrect = skia.RRect.MakeRectXY(rect, radius, radius)

    def execute(self, canvas):
        if self.should_clip:
            canvas.save()
            canvas.clipRRect(self.rrect)
        for cmd in self.children:
            cmd.execute(canvas)
        if self.should_clip:
            canvas.restore()

    def map(self, rect):
        bounds = self.rrect.rect()
        bounds.intersect(rect)
        return bounds

    def clone(self, children):
        return ClipRRect(self.rect, self.radius, children, \
            self.should_clip)

    def __repr__(self):
        if self.should_clip:
            return "ClipRRect({})".format(str(self.rrect))
        else:
            return "ClipRRect(<no-op>)"

class SaveLayer(VisualEffect):
    def __init__(self, sk_paint, node, children, should_save=True):
        super().__init__(skia.Rect.MakeEmpty(), children, node)
        self.should_save = should_save
        self.sk_paint = sk_paint

        if wbetools.USE_COMPOSITING and self.should_save:
            self.needs_compositing = True

    def execute(self, canvas):
        if self.should_save:
            canvas.saveLayer(paint=self.sk_paint)
        for cmd in self.children:
                cmd.execute(canvas)
        if self.should_save:
            canvas.restore()

    def map(self, rect):
        return rect

    def clone(self, children):
        return SaveLayer(self.sk_paint, self.node, children, \
            self.should_save)

    def __repr__(self):
        if self.should_save:
            return "SaveLayer(alpha={})".format(self.sk_paint.getAlphaf())
        else:
            return "SaveLayer(<no-op>)"

class DrawCompositedLayer(DrawCommand):
    def __init__(self, composited_layer):
        self.composited_layer = composited_layer
        super().__init__(
            self.composited_layer.composited_bounds())

    def execute(self, canvas):
        layer = self.composited_layer
        if not layer.surface: return
        bounds = layer.composited_bounds()
        layer.surface.draw(canvas, bounds.left(), bounds.top())

    def __repr__(self):
        return "DrawCompositedLayer()"

def parse_transform(transform_str):
    if transform_str.find('translate(') < 0:
        return None
    left_paren = transform_str.find('(')
    right_paren = transform_str.find(')')
    (x_px, y_px) = \
        transform_str[left_paren + 1:right_paren].split(",")
    return (float(x_px[:-2]), float(y_px[:-2]))

class CSSParser:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def whitespace(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    def literal(self, literal):
        if not (self.i < len(self.s) and self.s[self.i] == literal):
            raise Exception("Parsing error")
        self.i += 1

    def word(self):
        start = self.i
        in_quote = False
        while self.i < len(self.s):
            cur = self.s[self.i]
            if cur == "'":
                in_quote = not in_quote
            if cur.isalnum() or cur in ",/#-.%()\"'" \
                or (in_quote and cur == ':'):
                self.i += 1
            else:
                break
        if not (self.i > start):
            raise Exception("Parsing error")
        return self.s[start:self.i]

    def until_semicolon(self):
        start = self.i
        while self.i < len(self.s):
            cur = self.s[self.i]
            if cur == ";":
                break
            self.i += 1
        return self.s[start:self.i]

    def pair(self):
        prop = self.word()
        self.whitespace()
        self.literal(":")
        self.whitespace()
        val = self.until_semicolon()
        return prop.lower(), val

    def ignore_until(self, chars):
        while self.i < len(self.s):
            if self.s[self.i] in chars:
                return self.s[self.i]
            else:
                self.i += 1

    def body(self):
        pairs = {}
        while self.i < len(self.s) and self.s[self.i] != "}":
            try:
                prop, val = self.pair()
                pairs[prop.lower()] = val
                self.whitespace()
                self.literal(";")
                self.whitespace()
            except Exception:
                why = self.ignore_until([";", "}"])
                if why == ";":
                    self.literal(";")
                    self.whitespace()
                else:
                    break
        return pairs

    def selector(self):
        out = TagSelector(self.word().lower())
        self.whitespace()
        while self.i < len(self.s) and self.s[self.i] != "{":
            tag = self.word()
            descendant = TagSelector(tag.lower())
            out = DescendantSelector(out, descendant)
            self.whitespace()
        return out

    def parse(self):
        rules = []
        while self.i < len(self.s):
            try:
                self.whitespace()
                selector = self.selector()
                self.literal("{")
                self.whitespace()
                body = self.body()
                self.literal("}")
                rules.append((selector, body))
            except Exception:
                why = self.ignore_until(["}"])
                if why == "}":
                    self.literal("}")
                    self.whitespace()
                else:
                    break
        return rules

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

    def layout_mode(self):
        if isinstance(self.node, Text):
            return "inline"
        elif self.node.children:
            for child in self.node.children:
                if isinstance(child, Text): continue
                if child.tag in BLOCK_ELEMENTS:
                    return "block"
            return "inline"
        elif self.node.tag == "input":
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

    def new_line(self):
        self.previous_word = None
        self.cursor_x = 0
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line)
        self.children.append(new_line)

    def word(self, node, word):
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        size = float(node.style["font-size"][:-2])
        font = get_font(size, weight, size)
        w = font.measureText(word)
        if self.cursor_x + w > self.width:
            self.new_line()
        line = self.children[-1]
        text = TextLayout(node, word, line, self.previous_word)
        line.children.append(text)
        self.previous_word = text
        self.cursor_x += w + font.measureText(" ")

    def input(self, node):
        w = INPUT_WIDTH_PX
        if self.cursor_x + w > self.width:
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
            self.x, self.y,
            self.x + self.width, self.y + self.height)

        bgcolor = self.node.style.get("background-color",
                                 "transparent")
        
        is_atomic = not isinstance(self.node, Text) and \
            (self.node.tag == "input" or self.node.tag == "button")

        if not is_atomic:
            if bgcolor != "transparent":
                radius = float(
                    self.node.style.get("border-radius", "0px")[:-2])
                cmds.append(DrawRRect(rect, radius, bgcolor))

        for child in self.children:
            child.paint(cmds)

        if not is_atomic:
            cmds = paint_visual_effects(self.node, cmds, rect)
        display_list.extend(cmds)

    def __repr__(self):
        return "BlockLayout[{}](x={}, y={}, width={}, height={}, node={})".format(
            self.layout_mode(), self.x, self.y, self.width, self.height, self.node)

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
        return "LineLayout(x={}, y={}, width={}, height={}, node={})".format(
            self.x, self.y, self.width, self.height, self.node)

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
        return ("TextLayout(x={}, y={}, width={}, height={}, " +
            "node={}, word={})").format(
            self.x, self.y, self.width, self.height, self.node, self.word)

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
            if len(self.node.children) == 1 and \
               isinstance(self.node.children[0], Text):
                text = self.node.children[0].text
            else:
                print("Ignoring HTML contents inside button")
                text = ""

        color = self.node.style["color"]
        cmds.append(DrawText(self.x, self.y,
                             text, self.font, color))

        if self.node.is_focused:
            cx = self.x + self.font.measureText(text)
            cmds.append(DrawLine(
                cx, self.y, cx, self.y + self.height, "black", 1))

        cmds = paint_visual_effects(self.node, cmds, rect)
        display_list.extend(cmds)

    def __repr__(self):
        if self.node.tag == "input":
            extra = "type=input"
        else:
            extra = "type=button text={}".format(self.node.children[0].text)
        return "InputLayout(x={}, y={}, width={}, height={} {})".format(
            self.x, self.y, self.width, self.height, extra)

def paint_visual_effects(node, cmds, rect):
    opacity = float(node.style.get("opacity", "1.0"))
    blend_mode = parse_blend_mode(node.style.get("mix-blend-mode"))
    translation = parse_transform(
        node.style.get("transform", ""))

    border_radius = float(node.style.get("border-radius", "0px")[:-2])
    if node.style.get("overflow", "visible") == "clip":
        clip_radius = border_radius
    else:
        clip_radius = 0

    needs_clip = node.style.get("overflow", "visible") == "clip"
    needs_blend_isolation = blend_mode != skia.BlendMode.kSrcOver or \
        needs_clip or opacity != 1.0

    save_layer = \
        SaveLayer(skia.Paint(BlendMode=blend_mode, Alphaf=opacity), node, [
            ClipRRect(rect, clip_radius, cmds,
                should_clip=needs_clip),
        ], should_save=needs_blend_isolation)

    transform = Transform(translation, rect, node, [save_layer])

    node.save_layer = save_layer

    return [transform]

SETTIMEOUT_CODE = "__runSetTimeout(dukpy.handle)"
XHR_ONLOAD_CODE = "__runXHROnload(dukpy.out, dukpy.handle)"

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
        self.interp.export_function("style_set", self.style_set)
        self.interp.export_function("XMLHttpRequest_send",
            self.XMLHttpRequest_send)
        self.interp.export_function("setTimeout",
            self.setTimeout)
        self.interp.export_function("now",
            self.now)
        self.interp.export_function("requestAnimationFrame",
            self.requestAnimationFrame)
        with open("runtime13.js") as f:
            self.interp.evaljs(f.read())

        self.node_to_handle = {}
        self.handle_to_node = {}

    def run(self, script, code):
        try:
            self.interp.evaljs(code)
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
        doc = HTMLParser(
            "<html><body>" + s + "</body></html>").parse()
        new_nodes = doc.children[0].children
        elt = self.handle_to_node[handle]
        elt.children = new_nodes
        for child in elt.children:
            child.parent = elt
        self.tab.set_needs_render()

    def style_set(self, handle, s):
        elt = self.handle_to_node[handle]
        elt.attributes["style"] = s;
        self.tab.set_needs_render()

    def dispatch_settimeout(self, handle):
        self.interp.evaljs(SETTIMEOUT_CODE, handle=handle)

    def setTimeout(self, handle, time):
        def run_callback():
            task = Task(self.dispatch_settimeout, handle)
            self.tab.task_runner.schedule_task(task)
        threading.Timer(time / 1000.0, run_callback).start()

    def dispatch_xhr_onload(self, out, handle):
        do_default = self.interp.evaljs(
            XHR_ONLOAD_CODE, out=out, handle=handle)

    def XMLHttpRequest_send(self, method, url, body, isasync, handle):
        full_url = self.tab.url.resolve(url)
        if not self.tab.allowed_request(full_url):
            raise Exception("Cross-origin XHR blocked by CSP")
        if full_url.origin() != self.tab.url.origin():
            raise Exception(
                "Cross-origin XHR request not allowed")

        def run_load():
            headers, response = full_url.request(self.tab.url, body)
            task = Task(self.dispatch_xhr_onload, response, handle)
            self.tab.task_runner.schedule_task(task)
            if not isasync:
                return response

        if not isasync:
            return run_load()
        else:
            threading.Thread(target=run_load).start()

    def now(self):
        return int(time.time() * 1000)

    def requestAnimationFrame(self):
        self.tab.browser.set_needs_animation_frame(self.tab)

def parse_transition(value):
    properties = {}
    if not value: return properties
    for item in value.split(","):
        property, duration = item.split(" ", 1)
        frames = float(duration[:-1]) / REFRESH_RATE_SEC
        properties[property] = frames
    return properties

def diff_styles(old_style, new_style):
    old_transitions = \
        parse_transition(old_style.get("transition"))
    new_transitions = \
        parse_transition(new_style.get("transition"))

    transitions = {}
    for property in old_transitions:
        if property not in new_transitions: continue
        num_frames = new_transitions[property]
        if property not in old_style: continue
        if property not in new_style: continue
        old_value = old_style[property]
        new_value = new_style[property]
        if old_value == new_value: continue
        transitions[property] = \
            (old_value, new_value, num_frames)

    return transitions

class NumericAnimation:
    def __init__(self, old_value, new_value, num_frames):
        self.old_value = float(old_value)
        self.new_value = float(new_value)
        self.num_frames = num_frames

        self.frame_count = 1
        total_change = self.new_value - self.old_value
        self.change_per_frame = total_change / num_frames

    def animate(self):
        self.frame_count += 1
        if self.frame_count >= self.num_frames: return
        current_value = self.old_value + \
            self.change_per_frame * self.frame_count
        return str(current_value)

    def __repr__(self):
        return ("NumericAnimation(" + \
            "old_value={old_value}, change_per_frame={change_per_frame}, " + \
            "num_frames={num_frames})").format(
            old_value=self.old_value,
            change_per_frame=self.change_per_frame,
            num_frames=self.num_frames)

class TranslateAnimation:
    def __init__(self, old_value, new_value, num_frames):
        (self.old_x, self.old_y) = parse_transform(old_value)
        (new_x, new_y) = parse_transform(new_value)
        self.num_frames = num_frames

        self.frame_count = 1
        self.change_per_frame_x = \
            (new_x - self.old_x) / num_frames
        self.change_per_frame_y = \
            (new_y - self.old_y) / num_frames

    def __repr__(self):
        return ("TranslateAnimation(" + \
            "old_value=({old_x},{old_y}), " + \
            "change_per_frame=({change_x},{change_y}), " + \
            "num_frames={num_frames})").format(
            old_x=self.old_x,
            old_y = self.old_y,
            change_x=self.change_per_frame_x,
            change_y=self.change_per_frame_y,
            num_frames=self.num_frames)

    def animate(self):
        self.frame_count += 1
        if self.frame_count >= self.num_frames: return
        new_x = self.old_x + \
            self.change_per_frame_x * self.frame_count
        new_y = self.old_y + \
            self.change_per_frame_y * self.frame_count
        return "translate({}px,{}px)".format(new_x, new_y)

ANIMATED_PROPERTIES = {
    "opacity": NumericAnimation,
    "transform": TranslateAnimation,
}
    
def style(node, rules, tab):
    old_style = node.style

    node.style = {}
    for property, default_value in INHERITED_PROPERTIES.items():
        if node.parent:
            node.style[property] = node.parent.style[property]
        else:
            node.style[property] = default_value
    for selector, body in rules:
        if not selector.matches(node): continue
        for property, value in body.items():
            node.style[property] = value
    if isinstance(node, Element) and "style" in node.attributes:
        pairs = CSSParser(node.attributes["style"]).body()
        for property, value in pairs.items():
            node.style[property] = value
    if node.style["font-size"].endswith("%"):
        if node.parent:
            parent_font_size = node.parent.style["font-size"]
        else:
            parent_font_size = INHERITED_PROPERTIES["font-size"]
        node_pct = float(node.style["font-size"][:-1]) / 100
        parent_px = float(parent_font_size[:-2])
        node.style["font-size"] = str(node_pct * parent_px) + "px"

    if old_style:
        transitions = diff_styles(old_style, node.style)
        for property, (old_value, new_value, num_frames) \
            in transitions.items():
            if property in ANIMATED_PROPERTIES:
                tab.set_needs_render()
                AnimationClass = ANIMATED_PROPERTIES[property]
                animation = AnimationClass(
                    old_value, new_value, num_frames)
                node.animations[property] = animation
                node.style[property] = animation.animate()

    for child in node.children:
        style(child, rules, tab)

def absolute_bounds_for_obj(obj):
    rect = skia.Rect.MakeXYWH(
        obj.x, obj.y, obj.width, obj.height)
    cur = obj.node
    while cur:
        rect = map_translation(rect,
            parse_transform(
                cur.style.get("transform", "")))
        cur = cur.parent
    return rect

def absolute_bounds(display_item):
    rect = display_item.rect
    while display_item.parent:
        rect = display_item.parent.map(rect)
        display_item = display_item.parent
    return rect

class CompositedLayer:
    def __init__(self, skia_context, display_item):
        self.skia_context = skia_context
        self.surface = None
        self.display_items = [display_item]
        self.parent = display_item.parent

    def can_merge(self, display_item):
        return display_item.parent == \
            self.display_items[0].parent

    def add(self, display_item):
        assert self.can_merge(display_item)
        self.display_items.append(display_item)

    def composited_bounds(self):
        rect = skia.Rect.MakeEmpty()
        for item in self.display_items:
            rect.join(item.rect)
        rect.outset(1, 1)
        return rect

    def absolute_bounds(self):
        rect = skia.Rect.MakeEmpty()
        for item in self.display_items:
            rect.join(absolute_bounds(item))
        return rect

    def raster(self):
        bounds = self.composited_bounds()
        if bounds.isEmpty(): return
        irect = bounds.roundOut()

        if not self.surface:
            if wbetools.USE_GPU:
                self.surface = skia.Surface.MakeRenderTarget(
                    self.skia_context, skia.Budgeted.kNo,
                    skia.ImageInfo.MakeN32Premul(
                        irect.width(), irect.height()))
                if not self.surface:
                    self.surface = skia.Surface(irect.width(), irect.height())
                assert self.surface
            else:
                self.surface = skia.Surface(irect.width(), irect.height())

        canvas = self.surface.getCanvas()

        canvas.clear(skia.ColorTRANSPARENT)
        canvas.save()
        canvas.translate(-bounds.left(), -bounds.top())
        for item in self.display_items:
            item.execute(canvas)
        canvas.restore()

        if wbetools.SHOW_COMPOSITED_LAYER_BORDERS:
            DrawOutline(0, 0, irect.width() - 1, irect.height() - 1, "red", 1).execute(canvas)

    def __repr__(self):
        return ("layer: composited_bounds={} " +
            "absolute_bounds={} first_chunk={}").format(
            self.composited_bounds(), self.absolute_bounds(),
            self.display_items if len(self.display_items) > 0 else 'None')

def raster(display_list, canvas):
    for cmd in display_list:
        cmd.execute(canvas)

class Tab:
    def __init__(self, browser, chrome_bottom):
        self.history = []
        self.chrome_bottom = chrome_bottom
        self.focus = None
        self.url = None
        self.scroll = 0
        self.scroll_changed_in_tab = False
        self.needs_raf_callbacks = False
        self.needs_style = False
        self.needs_layout = False
        self.needs_paint = False
        self.browser = browser
        if wbetools.USE_BROWSER_THREAD:
            self.task_runner = TaskRunner(self)
        else:
            self.task_runner = SingleThreadedTaskRunner(self)
        self.task_runner.start_thread()

        self.measure_render = MeasureTime("render")

        self.composited_updates = []

        with open("browser8.css") as f:
            self.default_style_sheet = CSSParser(f.read()).parse()

    def allowed_request(self, url):
        return self.allowed_origins == None or \
            url.origin() in self.allowed_origins

    def script_run_wrapper(self, script, script_text):
        return Task(self.js.run, script, script_text)

    def load(self, url, body=None):
        self.scroll = 0
        self.scroll_changed_in_tab = True
        self.task_runner.clear_pending_tasks()
        headers, body = url.request(self.url, body)
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
            script_url = url.resolve(script)
            if not self.allowed_request(script_url):
                print("Blocked script", script, "due to CSP")
                continue

            header, body = script_url.request(url)
            task = Task(self.js.run, script_url, body)
            self.task_runner.schedule_task(task)

        self.rules = self.default_style_sheet.copy()
        links = [node.attributes["href"]
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "link"
                 and "href" in node.attributes
                 and node.attributes.get("rel") == "stylesheet"]
        for link in links:
            style_url = url.resolve(link)
            if not self.allowed_request(style_url):
                print("Blocked style", link, "due to CSP")
                continue
            try:
                header, body = style_url.request(url)
            except:
                continue
            self.rules.extend(CSSParser(body).parse())
        self.set_needs_render()

    def set_needs_render(self):
        self.needs_style = True
        self.browser.set_needs_animation_frame(self)

    def set_needs_layout(self):
        self.needs_layout = True
        self.browser.set_needs_animation_frame(self)

    def set_needs_paint(self):
        self.needs_paint = True
        self.browser.set_needs_animation_frame(self)

    def request_animation_frame_callback(self):
        self.needs_raf_callbacks = True
        self.browser.set_needs_animation_frame(self)

    def run_animation_frame(self, scroll):
        if not self.scroll_changed_in_tab:
            self.scroll = scroll
        self.js.interp.evaljs("__runRAFHandlers()")

        for node in tree_to_list(self.nodes, []):
            for (property_name, animation) in \
                node.animations.items():
                value = animation.animate()
                if value:
                    node.style[property_name] = value
                    if wbetools.USE_COMPOSITING and \
                        property_name == "opacity":
                        self.composited_updates.append(node)
                        self.set_needs_paint()
                    else:
                        self.set_needs_layout()

        needs_composite = self.needs_style or self.needs_layout
        self.render()

        document_height = math.ceil(self.document.height)
        clamped_scroll = clamp_scroll(
            self.scroll, document_height, self.chrome_bottom)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_tab = True
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_tab = True
        self.scroll = clamped_scroll

        scroll = None
        if self.scroll_changed_in_tab:
            scroll = self.scroll

        composited_updates = {}
        if not needs_composite:
            for node in self.composited_updates:
                composited_updates[node] = node.save_layer
        self.composited_updates = []

        commit_data = CommitData(
            self.url, scroll, document_height,
            self.display_list, composited_updates,
        )
        self.display_list = None
        self.scroll_changed_in_tab = False

        self.browser.commit(self, commit_data)

    def render(self):
        self.measure_render.start_timing()

        if self.needs_style:
            style(self.nodes, sorted(self.rules, key=cascade_priority), self)
            self.needs_layout = True
            self.needs_style = False

        if self.needs_layout:
            self.document = DocumentLayout(self.nodes)
            self.document.layout()
            self.needs_paint = True
            self.needs_layout = False
        
        if self.needs_paint:
            self.display_list = []
            self.document.paint(self.display_list)
            self.needs_paint = False

        self.measure_render.stop_timing()

    def click(self, x, y):
        self.render()
        self.focus = None
        y += self.scroll
        loc_rect = skia.Rect.MakeXYWH(x, y, 1, 1)
        objs = [obj for obj in tree_to_list(self.document, [])
                if absolute_bounds_for_obj(obj).intersects(
                    loc_rect)]
        if not objs: return
        elt = objs[-1].node
        if elt and self.js.dispatch_event("click", elt): return
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "a" and "href" in elt.attributes:
                url = self.url.resolve(elt.attributes["href"])
                self.load(url)
                return
            elif elt.tag == "input":
                elt.attributes["value"] = ""
                if self.focus:
                    self.focus.is_focused = False
                self.focus = elt
                elt.is_focused = True
                self.set_needs_render()
                return
            elif elt.tag == "button":
                while elt.parent:
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

        url = self.url.resolve(elt.attributes["action"])
        self.load(url, body)

    def keypress(self, char):
        if self.focus:
            if self.js.dispatch_event("keydown", self.focus): return
            self.focus.attributes["value"] += char
            self.set_needs_render()

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

class CommitData:
    def __init__(self, url, scroll, height,
        display_list, composited_updates):
        self.url = url
        self.scroll = scroll
        self.height = height
        self.display_list = display_list
        self.composited_updates = composited_updates

def print_composited_layers(composited_layers):
    print("Composited layers:")
    for layer in composited_layers:
        print("  " * 4 + str(layer))

def add_parent_pointers(nodes, parent=None):
    for node in nodes:
        node.parent = parent
        add_parent_pointers(node.children, node)

class Browser:
    def __init__(self):
        self.init_chrome()

        if wbetools.USE_GPU:
            self.sdl_window = sdl2.SDL_CreateWindow(b"Browser",
                sdl2.SDL_WINDOWPOS_CENTERED,
                sdl2.SDL_WINDOWPOS_CENTERED,
                WIDTH, HEIGHT,
                sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_OPENGL)
            self.gl_context = sdl2.SDL_GL_CreateContext(
                self.sdl_window)
            print(("OpenGL initialized: vendor={}," + \
                "renderer={}").format(
                OpenGL.GL.glGetString(OpenGL.GL.GL_VENDOR),
                OpenGL.GL.glGetString(OpenGL.GL.GL_RENDERER)))

            self.skia_context = skia.GrDirectContext.MakeGL()

            self.root_surface = \
                skia.Surface.MakeFromBackendRenderTarget(
                self.skia_context,
                skia.GrBackendRenderTarget(
                    WIDTH, HEIGHT, 0, 0, 
                    skia.GrGLFramebufferInfo(
                        0, OpenGL.GL.GL_RGBA8)),
                    skia.kBottomLeft_GrSurfaceOrigin,
                    skia.kRGBA_8888_ColorType,
                    skia.ColorSpace.MakeSRGB())
            assert self.root_surface is not None

            self.chrome_surface = skia.Surface.MakeRenderTarget(
                    self.skia_context, skia.Budgeted.kNo,
                    skia.ImageInfo.MakeN32Premul(WIDTH, self.chrome_bottom))
            assert self.chrome_surface is not None
        else:
            self.sdl_window = sdl2.SDL_CreateWindow(b"Browser",
            sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
            WIDTH, HEIGHT, sdl2.SDL_WINDOW_SHOWN)
            self.root_surface = skia.Surface.MakeRaster(
                skia.ImageInfo.Make(
                WIDTH, HEIGHT,
                ct=skia.kRGBA_8888_ColorType,
                at=skia.kUnpremul_AlphaType))
            self.chrome_surface = skia.Surface(WIDTH, self.chrome_bottom)
            self.skia_context = None

        self.tabs = []
        self.active_tab = None
        self.focus = None
        self.address_bar = ""
        self.lock = threading.Lock()
        self.url = None
        self.scroll = 0

        self.measure_composite_raster_and_draw = MeasureTime("raster-and-draw")

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

        self.animation_timer = None

        self.needs_animation_frame = False
        self.needs_composite = False
        self.needs_raster = False
        self.needs_draw = False

        self.active_tab_height = 0
        self.active_tab_display_list = None

        self.composited_updates = {}
        self.composited_layers = []
        self.draw_list = []

    def init_chrome(self):
        self.chrome_font = get_font(20, "normal", "roman")
        chrome_font_height = linespace(self.chrome_font)

        self.padding = 5
        self.tab_header_bottom = chrome_font_height + 2 * self.padding
        self.addressbar_top = self.tab_header_bottom + self.padding
        self.chrome_bottom = \
            self.addressbar_top + chrome_font_height + 2 * self.padding

    def render(self):
        assert not wbetools.USE_BROWSER_THREAD
        tab = self.tabs[self.active_tab]
        tab.task_runner.run_tasks()
        tab.run_animation_frame(self.scroll)

    def commit(self, tab, data):
        self.lock.acquire(blocking=True)
        if tab == self.tabs[self.active_tab]:
            self.url = data.url
            if data.scroll != None:
                self.scroll = data.scroll
            self.active_tab_height = data.height
            if data.display_list:
                self.active_tab_display_list = data.display_list
            self.animation_timer = None
            self.composited_updates = data.composited_updates
            if not self.composited_updates:
                self.composited_updates = {}
                self.set_needs_composite()
            else:
                self.set_needs_draw()
        self.lock.release()

    def set_needs_animation_frame(self, tab):
        self.lock.acquire(blocking=True)
        if tab == self.tabs[self.active_tab]:
            self.needs_animation_frame = True
        self.lock.release()

    def set_needs_raster(self):
        self.needs_raster = True
        self.needs_draw = True

    def set_needs_composite(self):
        self.needs_composite = True
        self.needs_raster = True
        self.needs_draw = True

    def set_needs_draw(self):
        self.needs_draw = True

    def composite(self):
        self.composited_layers = []
        add_parent_pointers(self.active_tab_display_list)
        all_commands = []
        for cmd in self.active_tab_display_list:
            all_commands = \
                tree_to_list(cmd, all_commands)
        non_composited_commands = [cmd
            for cmd in all_commands
            if isinstance(cmd, DrawCommand) or not cmd.needs_compositing
            if not cmd.parent or cmd.parent.needs_compositing
        ]
        for cmd in non_composited_commands:
            did_break = False
            for layer in reversed(self.composited_layers):
                if layer.can_merge(cmd):
                    layer.add(cmd)
                    did_break = True
                    break
                elif skia.Rect.Intersects(
                    layer.absolute_bounds(),
                    absolute_bounds(cmd)):
                    layer = CompositedLayer(self.skia_context, cmd)
                    self.composited_layers.append(layer)
                    did_break = True
                    break
            if not did_break:
                layer = CompositedLayer(self.skia_context, cmd)
                self.composited_layers.append(layer)

        self.active_tab_height = 0
        for layer in self.composited_layers:
            self.active_tab_height = \
                max(self.active_tab_height,
                    layer.absolute_bounds().bottom())

    def clone_latest(self, visual_effect, current_effect):
        node = visual_effect.node
        if not node in self.composited_updates:
            return visual_effect.clone(current_effect)
        save_layer = self.composited_updates[node]
        if type(visual_effect) is SaveLayer:
            return save_layer.clone(current_effect)
        return visual_effect.clone(current_effect)

    def paint_draw_list(self):
        self.draw_list = []
        for composited_layer in self.composited_layers:
            current_effect = \
                DrawCompositedLayer(composited_layer)
            if not composited_layer.display_items: continue
            parent = composited_layer.display_items[0].parent
            while parent:
                current_effect = \
                    self.clone_latest(parent, [current_effect])
                parent = parent.parent
            self.draw_list.append(current_effect)

    def composite_raster_and_draw(self):
        self.lock.acquire(blocking=True)
        if not self.needs_composite and \
            len(self.composited_updates) == 0 \
            and not self.needs_raster and not self.needs_draw:
            self.lock.release()
            return

        self.measure_composite_raster_and_draw.start_timing()
        start_time = time.time()
        if self.needs_composite:
            self.composite()
        if self.needs_raster:
            self.raster_chrome()
            self.raster_tab()
        if self.needs_draw:
            self.paint_draw_list()
            self.draw()
        self.measure_composite_raster_and_draw.stop_timing()
        self.needs_composite = False
        self.needs_raster = False
        self.needs_draw = False
        self.lock.release()

    def schedule_animation_frame(self):
        def callback():
            self.lock.acquire(blocking=True)
            scroll = self.scroll
            active_tab = self.tabs[self.active_tab]
            self.needs_animation_frame = False
            self.lock.release()
            task = Task(active_tab.run_animation_frame, scroll)
            active_tab.task_runner.schedule_task(task)
        self.lock.acquire(blocking=True)
        if self.needs_animation_frame and not self.animation_timer:
            if wbetools.USE_BROWSER_THREAD:
                self.animation_timer = \
                    threading.Timer(REFRESH_RATE_SEC, callback)
                self.animation_timer.start()
        self.lock.release()

    def handle_down(self):
        self.lock.acquire(blocking=True)
        if not self.active_tab_height:
            self.lock.release()
            return
        scroll = clamp_scroll(
            self.scroll + SCROLL_STEP,
            self.active_tab_height)
        self.scroll = scroll
        self.set_needs_draw()
        self.needs_animation_frame = True
        self.lock.release()

    def clear_data(self):
        self.scroll = 0
        self.url = None
        self.display_list = []
        self.composited_layers = []

    def set_active_tab(self, index):
        self.active_tab = index
        self.clear_data()
        self.needs_animation_frame = True

    def handle_click(self, e):
        self.lock.acquire(blocking=True)
        if e.y < self.chrome_bottom:
            self.focus = None
            if intersects(e.x, e.y, self.plus_bounds()):
                self.load_internal(URL("https://browser.engineering/"))
            elif intersects(e.x, e.y, self.backbutton_bounds()):
                active_tab = self.tabs[self.active_tab]
                task = Task(active_tab.go_back)
                active_tab.task_runner.schedule_task(task)
            elif intersects(e.x, e.y, self.addressbar_bounds()):
                self.focus = "address bar"
                self.address_bar = ""
            else:
                for i in range(0, len(self.tabs)):
                    if intersects(e.x, e.y, self.tab_bounds(i)):
                        self.set_active_tab(int((e.x - 40) / 80))
                        active_tab = self.tabs[self.active_tab]
                        task = Task(active_tab.set_needs_render)
                        active_tab.task_runner.schedule_task(task)
                        break
            self.set_needs_raster()
        else:
            self.focus = "content"
            active_tab = self.tabs[self.active_tab]
            task = Task(active_tab.click, e.x, e.y - self.chrome_bottom)
            active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def handle_key(self, char):
        self.lock.acquire(blocking=True)
        if not (0x20 <= ord(char) < 0x7f): return
        if self.focus == "address bar":
            self.address_bar += char
            self.set_needs_raster()
        elif self.focus == "content":
            active_tab = self.tabs[self.active_tab]
            task = Task(active_tab.keypress, char)
            active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def schedule_load(self, url, body=None):
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.load, url, body)
        active_tab.task_runner.schedule_task(task)

    def handle_enter(self):
        self.lock.acquire(blocking=True)
        if self.focus == "address bar":
            self.schedule_load(URL(self.address_bar))
            self.url = self.address_bar
            self.focus = None
            self.set_needs_raster()
            self.needs_animation_frame = True
        self.lock.release()

    def load(self, url):
        self.lock.acquire(blocking=True)
        self.load_internal(url)
        self.lock.release()

    def load_internal(self, url):
        new_tab = Tab(self, self.chrome_bottom)
        self.set_active_tab(len(self.tabs))
        self.tabs.append(new_tab)
        self.schedule_load(url)

    def raster_tab(self):
        for composited_layer in self.composited_layers:
            composited_layer.raster()

    def plus_bounds(self):
        plus_width = self.chrome_font.measureText("+")
        return (self.padding, self.padding,
            plus_width + self.padding, self.tab_header_bottom - self.padding)

    def tab_bounds(self, i):
        (plus_left, plus_top, plus_right, plus_bottom) = self.plus_bounds()
        tab_start_x = plus_right + self.padding

        tab_width = self.chrome_font.measureText("Tab 1") + 2 * self.padding

        return (tab_start_x + tab_width * i, self.padding,
            tab_start_x + tab_width + tab_width * i, self.tab_header_bottom)

    def backbutton_bounds(self):
        backbutton_width = self.chrome_font.measureText("<")
        return (self.padding, self.addressbar_top,
            self.padding + backbutton_width, self.chrome_bottom - self.padding)

    def addressbar_bounds(self):
        (backbutton_left, backbutton_top, backbutton_right, backbutton_bottom) = \
            self.backbutton_bounds()

        return (backbutton_right + self.padding, self.addressbar_top,
            WIDTH - 10, self.chrome_bottom - self.padding)

    def paint_chrome(self):
        cmds = []
        # Background of page
        cmds.append(DrawRect(0, 0, WIDTH, self.chrome_bottom, "white"))

        # Box around plus icon
        (plus_left, plus_top, plus_right, plus_bottom) = self.plus_bounds()
        cmds.append(DrawOutline(
            plus_left, plus_top, plus_right, plus_bottom, "black", 1))
        # Plus icon
        cmds.append(DrawText(
            plus_left, plus_top, "+", self.chrome_font, "black"))

        # List of tabs
        for i, tab in enumerate(self.tabs):
            name = "Tab {}".format(i)
            (tab_left, tab_top, tab_right, tab_bottom) = self.tab_bounds(i)

            # Vertical line on LHS of tab
            cmds.append(DrawLine(
                tab_left, 0,tab_left, tab_bottom, "black", 1))
            # Vertical line on RHS of TAB
            cmds.append(DrawLine(
                tab_right, 0, tab_right, tab_bottom, "black", 1))
            # Tab name
            cmds.append(DrawText(
                tab_left + self.padding, tab_top,
                name, self.chrome_font, "black"))
            # Active tab indication lines
            if i == self.active_tab:
                cmds.append(DrawLine(
                    0, tab_bottom, tab_left, tab_bottom, "black", 1))
                cmds.append(DrawLine(
                    tab_right, tab_bottom, WIDTH, tab_bottom, "black", 1))

        # Back button
        backbutton_width = self.chrome_font.measureText("<")
        (backbutton_left, backbutton_top, backbutton_right, backbutton_bottom) = \
            self.backbutton_bounds()
        cmds.append(DrawOutline(
            backbutton_left, backbutton_top,
            backbutton_right, backbutton_bottom,
            "black", 1))
        cmds.append(DrawText(
            backbutton_left, backbutton_top + self.padding,
            "<", self.chrome_font, "black"))

        (addressbar_left, addressbar_top, \
            addressbar_right, addressbar_bottom) = \
            self.addressbar_bounds()

        # Bounds around address bar
        cmds.append(DrawOutline(
            addressbar_left, addressbar_top, addressbar_right,
            addressbar_bottom, "black", 1))
        left_bar = addressbar_left + self.padding
        top_bar = addressbar_top + self.padding
        if self.focus == "address bar":
            # Address user is editing
            cmds.append(DrawText(
                left_bar, top_bar,
                self.address_bar, self.chrome_font, "black"))
            w = self.chrome_font.measure(self.address_bar)
            # Caret
            cmds.append(DrawLine(
                left_bar + w, top_bar,
                left_bar + w,
                self.chrome_bottom - self.padding, "red", 1))
        else:
            url = str(self.tabs[self.active_tab].url)
            cmds.append(DrawText(
                left_bar,
                top_bar,
                url, self.chrome_font, "black"))

        # Line between chrome and content
        cmds.append(DrawLine(
            0, self.chrome_bottom + self.padding, WIDTH,
            self.chrome_bottom + self.padding, "black", 1))

        return cmds

    def raster_chrome(self):
        canvas = self.chrome_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)

        for cmd in self.paint_chrome():
            cmd.execute(canvas)

    def draw(self):
        canvas = self.root_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)

        canvas.save()
        canvas.translate(0, self.chrome_bottom - self.scroll)
        for item in self.draw_list:
            item.execute(canvas)
        canvas.restore()

        chrome_rect = skia.Rect.MakeLTRB(0, 0, WIDTH, self.chrome_bottom)
        canvas.save()
        canvas.clipRect(chrome_rect)
        self.chrome_surface.draw(canvas, 0, 0)
        canvas.restore()

        if wbetools.USE_GPU:
            self.root_surface.flushAndSubmit()
            sdl2.SDL_GL_SwapWindow(self.sdl_window)
        else:
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
        print(self.measure_composite_raster_and_draw.text())
        self.tabs[self.active_tab].task_runner.set_needs_quit()
        if wbetools.USE_GPU:
            sdl2.SDL_GL_DeleteContext(self.gl_context)
        sdl2.SDL_DestroyWindow(self.sdl_window)

def add_main_args():
    import argparse
    parser = argparse.ArgumentParser(description='Toy browser')
    parser.add_argument("url", type=str, help="URL to load")
    parser.add_argument('--single_threaded', action="store_true", default=False,
        help='Whether to run the browser without a browser thread')
    parser.add_argument('--disable_compositing', action="store_true",
        default=False, help='Whether to composite some elements')
    parser.add_argument('--disable_gpu', action='store_true',
        default=False, help='Whether to disable use of the GPU')
    parser.add_argument('--show_composited_layer_borders', action="store_true",
        default=False, help='Whether to visually indicate composited layer borders')
    args = parser.parse_args()

    wbetools.USE_BROWSER_THREAD = not args.single_threaded
    wbetools.USE_GPU = not args.disable_gpu
    wbetools.USE_COMPOSITING = not args.disable_compositing and not args.disable_gpu
    wbetools.SHOW_COMPOSITED_LAYER_BORDERS = args.show_composited_layer_borders
    return args

if __name__ == "__main__":
    import sys

    args = add_main_args()

    sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS)
    browser = Browser()
    browser.load(URL(args.url))

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
        active_tab = browser.tabs[browser.active_tab]
        if not wbetools.USE_BROWSER_THREAD:
            if active_tab.task_runner.needs_quit:
                break
            if browser.needs_animation_frame:
                browser.needs_animation_frame = False
                browser.render()
        browser.composite_raster_and_draw()
        browser.schedule_animation_frame()
