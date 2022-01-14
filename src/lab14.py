"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 14 (Animations and Compositing),
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
from lab6 import compute_style
from lab6 import TagSelector, DescendantSelector
from lab9 import EVENT_DISPATCH_CODE
from lab10 import COOKIE_JAR, request, url_origin
from lab11 import get_font, linespace, parse_blend_mode, parse_color
from lab12 import raster

class Timer:
    def __init__(self):
        self.time = None

    def start(self):
        self.time = time.time()

    def stop(self):
        return time.time() - self.time
        self.time = None

FONTS = {}

def async_request(url, top_level_url, results):
    headers = None
    body = None
    def runner():
        headers, body = request(url, top_level_url)
        results[url] = {'headers': headers, 'body': body}
    thread = threading.Thread(target=runner)
    thread.start()
    return thread

def center_point(rect):
    return (rect.left() + (rect.right() - rect.left()) / 2,
        rect.top() + (rect.bottom() - rect.top()) / 2)

class DisplayItem:
    def __init__(self, rect, needs_compositing=False, cmds=None,
        is_noop=False):
        self.rect = rect if rect else skia.Rect.MakeEmpty()
        self.composited=needs_compositing
        self.cmds = cmds
        self.noop = is_noop

    def bounds(self):
        return self.rect

    def needs_compositing(self):
        if self.composited:
            return True
        return False

    def get_cmds(self):
        return self.cmds

    def is_noop(self):
        return self.noop

    def execute(self, canvas):
        if self.cmds:
            def op():
                for cmd in self.get_cmds():
                    cmd.execute(canvas, True, False)
            self.draw(canvas, op)
        else:
            self.draw(canvas)

    def draw(self, canvas, op):
        pass

    def transform(self, rect):
        return rect

    def repr_recursive(self, indent=0, include_noop=False):
        inner = ""
        if not include_noop and self.is_noop():
            if self.cmds:
                for cmd in self.cmds:
                   inner += cmd.repr_recursive(indent, include_noop)
                return inner
        else:
            if self.cmds:
                for cmd in self.cmds:
                    inner += cmd.repr_recursive(indent + 2, include_noop)
            return ("{indentation}{repr}: bounds={bounds}, " +
                "needs_compositing={needs_compositing}{noop}\n{inner} ").format(
                indentation=" " * indent,
                repr=self.__repr__(),
                bounds=self.bounds(),
                needs_compositing=self.needs_compositing(),
                inner=inner,
                noop=(" <no-op>" if self.is_noop() else ""))

class Transform(DisplayItem):
    def __init__(self, translation, rotation_degrees, rect, cmds,
        should_transform):
        self.rotation_degrees = rotation_degrees
        self.translation = translation
        (self.center_x, self.center_y) = center_point(rect)
        assert translation == None or rotation_degrees == None
        self.should_transform = should_transform
        my_bounds = self.compute_bounds(rect, cmds, should_transform)
        super().__init__(my_bounds, False, cmds, not should_transform)

    def draw(self, canvas, op):
        if self.is_noop():
            op()
        elif self.translation:
            (x, y) = self.translation
            canvas.save()
            canvas.translate(x, y)
            op()
            canvas.restore()
        else:
            print('center: x=' + str(self.center_x) + ' y=' + str(self.center_y))
            canvas.save()
            canvas.rotate(
                degrees=self.rotation_degrees, px=self.center_x, py=self.center_y)
            print('rotate: ' + str(self.rotation_degrees))
            op()
            canvas.restore()

    def transform(self, rect):
        return self.transform_internal(rect, not self.is_noop())

    def transform_internal(self, rect, should_transform):
        if not should_transform:
            return rect
        matrix = skia.Matrix()
        if self.translation:
            (x, y) = self.translation
            matrix.setTranslate(x, y)
        else:
            matrix.setRotate(
                self.rotation_degrees, self.center_x, self.center_y)
        return matrix.mapRect(rect)

    def compute_bounds(self, rect, cmds, should_transform):
        for cmd in cmds:
            rect.join(cmd.bounds())
        return self.transform_internal(rect, should_transform)

    def __repr__(self):
        if self.is_noop():
            return "Transform(<no-op>)"
        elif self.translation:
            return "Transform(translate({}, {}))".format(self.translation)
        else:
            return "Transform(rotate({}))".format(self.rotation_degrees)

class DrawRRect(DisplayItem):
    def __init__(self, rect, radius, color):
        self.rrect = skia.RRect.MakeRectXY(rect, radius, radius)
        self.color = color
        super().__init__(rect)

    def draw(self, canvas):
        sk_color = parse_color(self.color)
        canvas.drawRRect(self.rrect,
            paint=skia.Paint(Color=sk_color))

    def print(self, indent=0):
        return " " * indent + self.__repr__()

    def __repr__(self):
        return "DrawRRect(rect={}, color={})".format(
            str(self.rrect), self.color)

class DrawText(DisplayItem):
    def __init__(self, x1, y1, text, font, color):
        self.left = x1
        self.top = y1
        self.right = x1 + font.measureText(text)
        self.bottom = y1 - font.getMetrics().fAscent + font.getMetrics().fDescent
        self.rect = \
        self.font = font
        self.text = text
        self.color = color
        super().__init__(skia.Rect.MakeLTRB(x1, y1, self.right, self.bottom))

    def draw(self, canvas, **args):
        draw_text(canvas, self.left, self.top,
            self.text, self.font, self.color)

    def __repr__(self):
        return "DrawText(text={})".format(self.text)

class DrawRect(DisplayItem):
    def __init__(self, x1, y1, x2, y2, color):
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color
        super().__init__(skia.Rect.MakeLTRB(x1, y1, x2, y2))

    def draw(self, canvas, *args):
        draw_rect(canvas,
            self.left, self.top,
            self.right, self.bottom,
            fill=self.color, width=0)

    def __repr__(self):
        return "DrawRect(top={} left={} bottom={} right={} color={})".format(
            self.left, self.top, self.right, self.bottom, self.color)

class ClipRRect(DisplayItem):
    def __init__(self, rect, radius, cmds, should_clip=True):
        self.rrect = skia.RRect.MakeRectXY(rect, radius, radius)
        super().__init__(
            ClipRRect.compute_bounds(rect, cmds), False, cmds, not should_clip)

    def draw(self, canvas, op):
        if not self.is_noop():
            canvas.save()
            canvas.clipRRect(self.rrect)
        op()
        if not self.is_noop():
            canvas.restore()

    def compute_bounds(rect, cmds):
        for cmd in cmds:
            rect.join(cmd.bounds())
        return rect

    def __repr__(self):
        if self.is_noop():
            return "ClipRRect(<no-op>)"
        else:
            return "ClipRRect({})".format(str(self.rrect))

class DrawLine(DisplayItem):
    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        super().__init__(skia.Rect.MakeLTRB(x1, y1, x2, y2))

    def execute(self, canvas, *args):
        draw_line(canvas, self.x1, self.y1, self.x2, self.y2)

class SaveLayer(DisplayItem):
    def __init__(self, sk_paint, cmds,
            should_save=True, should_paint_cmds=True, needs_animation=False):
        self.should_paint_cmds = should_paint_cmds
        self.sk_paint = sk_paint
        rect = skia.Rect.MakeEmpty()
        for cmd in cmds:
            rect.join(cmd.rect)
        super().__init__(rect, False, cmds, not should_save)

    def draw(self, canvas, op):
        if not self.is_noop():
            canvas.saveLayer(paint=self.sk_paint)
        if self.should_paint_cmds:
            op()
        if not self.is_noop():
            canvas.restore()

    def __repr__(self):
        if self.is_noop():
            return "SaveLayer(<no-op>)"
        else:
            return "SaveLayer(alpha={})".format(self.sk_paint.getAlphaf())

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

def parse_rotation_transform(transform_str):
    left_paren = transform_str.find('(')
    right_paren = transform_str.find('deg)')
    return float(transform_str[left_paren + 1:right_paren])

def parse_translate_transform(transform_str):
    left_paren = transform_str.find('(')
    right_paren = transform_str.find(')')
    (x_px, y_px) = \
        transform_str[left_paren + 1:right_paren].split(",")
    return (float(x_px[:-2]), float(y_px[:-2]))

def parse_transform(transform_str):
    if transform_str.find('translate') >= 0:
        return (parse_translate_transform(transform_str), None)
    elif transform_str.find('rotate') >= 0:
        return (None, parse_rotation_transform(transform_str))
    else:
        return (None, None)

class CSSParser:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def whitespace(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    def literal(self, literal):
        assert self.i < len(self.s) and self.s[self.i] == literal
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
        assert self.i > start
        return self.s[start:self.i]

    def pair(self):
        prop = self.word()
        self.whitespace()
        self.literal(":")
        self.whitespace()
        val = self.word()
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
            except AssertionError:
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
            except AssertionError:
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
        previous = None
        for child in self.node.children:
            if layout_mode(child) == "inline":
                next = InlineLayout(child, self, previous)
            else:
                next = BlockLayout(child, self, previous)
            self.children.append(next)
            previous = next

        self.width = style_length(
            self.node, "width", self.parent.width)
        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        for child in self.children:
            child.layout()

        self.height = style_length(
            self.node, "height",
            sum([child.height for child in self.children]))

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
        self.width = style_length(
            self.node, "width", self.parent.width)

        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        self.new_line()
        self.recurse(self.node)
        
        for line in self.children:
            line.layout()

        self.height = style_length(
            self.node, "height",
            sum([line.height for line in self.children]))

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

        self.width = style_length(
            self.node, "width", INPUT_WIDTH_PX)
        self.height = style_length(
            self.node, "height", linespace(self.font))

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

def style_length(node, style_name, default_value):
    style_val = node.style.get(style_name)
    if style_val:
        return int(style_val[:-2])
    else:
        return default_value

def paint_visual_effects(node, cmds, rect):
    opacity = float(node.style.get("opacity", "1.0"))
    blend_mode = parse_blend_mode(node.style.get("mix-blend-mode"))
    (translation, rotation) = parse_transform(node.style.get("transform", ""))

    border_radius = float(node.style.get("border-radius", "0px")[:-2])
    if node.style.get("overflow", "visible") == "clip":
        clip_radius = border_radius
    else:
        clip_radius = 0

    needs_clip = node.style.get("overflow", "visible") == "clip"
    needs_blend_isolation = blend_mode != skia.BlendMode.kSrcOver or \
        needs_clip or opacity != 1.0

    return [
        Transform(translation, rotation, rect, [
            SaveLayer(skia.Paint(BlendMode=blend_mode, Alphaf=opacity), [
                ClipRRect(rect, clip_radius,
                    cmds,
                should_clip=needs_clip),
            ], should_save=needs_blend_isolation),
        ],
        should_transform=translation != None or rotation != None)
    ]

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
        self.interp.export_function("now",
            self.now)
        self.interp.export_function("requestAnimationFrame",
            self.requestAnimationFrame)
        with open("runtime14.js") as f:
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
        doc = HTMLParser(
            "<html><body>" + s + "</body></html>").parse()
        new_nodes = doc.children[0].children
        elt = self.handle_to_node[handle]
        elt.children = new_nodes
        for child in elt.children:
            child.parent = elt
        self.tab.set_needs_pipeline_update()

    def style_set(self, handle, s):
        elt = self.handle_to_node[handle]
        elt.attributes["style"] = s;
        self.tab.set_needs_pipeline_update()

    def xhr_onload(self, out, handle):
        do_default = self.interp.evaljs(
            XHR_ONLOAD_CODE, out=out, handle=handle)

    def XMLHttpRequest_send(
        self, method, url, body, is_async, handle):
        full_url = resolve_url(url, self.tab.url)
        if not self.tab.allowed_request(full_url):
            raise Exception("Cross-origin XHR blocked by CSP")

        def run_load():
            headers, out = request(
                full_url, self.tab.url, payload=body)
            handle_local = handle
            if url_origin(full_url) != url_origin(self.tab.url):
                raise Exception(
                    "Cross-origin XHR request not allowed")
            self.tab.main_thread_runner.schedule_script_task(
                Task(self.xhr_onload, out, handle_local))
            return out

        if not is_async:
            run_load(is_async)
        else:
            load_thread = threading.Thread(target=run_load, args=())
            load_thread.start()

    def now(self):
        return int(time.time() * 1000)

    def requestAnimationFrame(self):
        self.tab.request_animation_frame_callback()

SCROLL_STEP = 100
CHROME_PX = 100

USE_BROWSER_THREAD = True

def set_timeout(func, sec):
    t = threading.Timer(sec, func)
    t.start()

def clamp_scroll(scroll, tab_height):
    return max(0, min(scroll, tab_height - (HEIGHT - CHROME_PX)))

def animate_style(node, old_style, new_style, tab):
    if not old_style:
        return
    if not "transition" in old_style or not "transition" in new_style:
        return
    if not old_style["transition"] == "opacity" or not new_style["transition"] == "opacity":
        return
    if old_style["opacity"] == new_style["opacity"]:
        return
    tab.animations[node] = start_opacity_animation(float(old_style["opacity"]), new_style, tab)

ANIMATION_FRAME_COUNT = 60

def start_opacity_animation(old_opacity, new_style, tab):
    new_opacity = float(new_style["opacity"])
    change_per_frame = (new_opacity - old_opacity) / ANIMATION_FRAME_COUNT
    return Animation("opacity", old_opacity, change_per_frame, new_style, tab)

def style(node, rules, tab):
    old_style = None
    if hasattr(node, 'style'):
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
            computed_value = compute_style(node, property, value)
            if not computed_value: continue
            node.style[property] = computed_value
    if isinstance(node, Element) and "style" in node.attributes:
        pairs = CSSParser(node.attributes["style"]).body()
        for property, value in pairs.items():
            computed_value = compute_style(node, property, value)
            node.style[property] = computed_value
    animate_style(node, old_style, node.style, tab)
    for child in node.children:
        style(child, rules, tab)

class Animation:
    def __init__(
        self, property_name, old_value, change_per_frame, computed_style, tab):
        self.property_name = property_name
        self.old_value = old_value
        self.change_per_frame = change_per_frame
        self.computed_style = computed_style
        self.tab = tab
        self.frame_count = 0
        tab.set_needs_animation_frame()

    def animate(self):
        self.frame_count += 1
        self.computed_style[self.property_name] = \
            self.old_value + self.change_per_frame * self.frame_count
        needs_another_frame = self.frame_count < ANIMATION_FRAME_COUNT
        if needs_another_frame:
            self.tab.set_needs_paint()
            self.tab.set_needs_animation_frame()
        return needs_another_frame

class CompositedLayer:
    def __init__(self, bounds=None, first_chunk=None):
#        print('new composited layer: bounds=' + str(bounds) + ' ' + str(first_chunk))
        self.surface = None
        self.chunks = []
        self.first_chunk = first_chunk
        if first_chunk:
            self.append(first_chunk)

    def can_merge(self, chunk):
        if len(self.chunks) == 0:
            return not chunk.needs_compositing()
        return  \
            self.chunks[0].composited_item() == chunk.composited_item()

    def bounds(self):
        retval = skia.Rect.MakeEmpty()
        for chunk in self.chunks:
            retval.join(chunk.bounds())
        return retval

    def append(self, chunk):
        assert self.can_merge(chunk)
        self.chunks.append(chunk)

    def overlaps(self, rect):
        return skia.Rect.Intersects(self.bounds(), rect)

    def draw(self, canvas, draw_offset):
        def op():
            canvas.save()
            (offset_x, offset_y) = draw_offset
            bounds = self.bounds()
            offset_x += bounds.left()
            offset_y += bounds.top()
            canvas.translate(offset_x, offset_y)
            self.surface.draw(canvas, 0, 0)
            canvas.restore()
        if not self.surface:
            return
        if self.first_chunk:
            self.first_chunk.draw(canvas, op)
        else:
            op()

    def raster(self):
        bounds = self.bounds()
        if bounds.isEmpty():
            return
        irect = bounds.roundOut()
        if not self.surface:
#            print('make surface: bounds=' + str(irect))
            self.surface = skia.Surface(irect.width(), irect.height())
#        print('surface width: ' + str(irect.width()))
        canvas = self.surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        canvas.save()
#        print(bounds.left())
        canvas.translate(-bounds.left(), -bounds.top())
        for chunk in self.chunks:
 #           print("  raster regular cmd: " + str(cmd))
            chunk.raster(canvas)
        canvas.restore()
  #      print('raster done')

class Tab:
    def __init__(self, commit_func):
        self.history = []
        self.focus = None
        self.url = None
        self.scroll = 0
        self.scroll_changed_in_tab = False
        self.needs_raf_callbacks = False
        self.display_scheduled = False
        self.needs_pipeline_update = False
        self.needs_paint = False
        self.commit_func = commit_func
        if USE_BROWSER_THREAD:
            self.main_thread_runner = MainThreadRunner(self)
        else:
            self.main_thread_runner = SingleThreadedTaskRunner(self)
        self.main_thread_runner.start()

        self.time_in_style_layout_and_paint = 0.0
        self.animations = {}
        self.display_list = []

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

    def load(self, url, body=None):
        self.main_thread_runner.clear_pending_tasks()
        headers, body = request(url, self.url, payload=body)
        self.scroll = 0
        self.scroll_changed_in_tab = True
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

        async_requests = []
        script_results = {}
        for script in scripts:
            script_url = resolve_url(script, url)
            if not self.allowed_request(script_url):
                print("Blocked script", script, "due to CSP")
                continue
            async_requests.append({
                "url": script_url,
                "type": "script",
                "thread": async_request(
                    script_url, url, script_results)
            })
 
        self.rules = self.default_style_sheet.copy()
        links = [node.attributes["href"]
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "link"
                 and "href" in node.attributes
                 and node.attributes.get("rel") == "stylesheet"]

        style_results = {}
        for link in links:
            style_url = resolve_url(link, url)
            if not self.allowed_request(style_url):
                print("Blocked style", link, "due to CSP")
                continue
            async_requests.append({
                "url": style_url,
                "type": "style sheet",
                "thread": async_request(style_url, url, style_results)
            })

        for async_req in async_requests:
            async_req["thread"].join()
            req_url = async_req["url"]
            if async_req["type"] == "script":
                self.main_thread_runner.schedule_script_task(
                    Task(self.js.run, req_url,
                        script_results[req_url]['body']))
            else:
                self.rules.extend(
                    CSSParser(
                        style_results[req_url]['body']).parse())

        self.set_needs_pipeline_update()

    def apply_scroll(self, scroll):
        self.scroll = scroll

    def set_needs_paint(self):
        self.needs_paint = True

    def set_needs_pipeline_update(self):
        self.needs_pipeline_update = True
        self.needs_paint = True
        self.set_needs_animation_frame()

    def set_needs_animation_frame(self):
        def callback():
            self.display_scheduled = False
            self.main_thread_runner.schedule_animation_frame()
        if not self.display_scheduled:
            if USE_BROWSER_THREAD:
                set_timeout(callback, REFRESH_RATE_SEC)
            self.display_scheduled = True

    def request_animation_frame_callback(self):
        self.needs_raf_callbacks = True
        self.set_needs_animation_frame()

    def compute_document_bounds(self):
#        print('compute_document_bounds')
        rect = skia.Rect.MakeEmpty()
        for display_item in self.display_list:
#            print("   " + str(display_item) + " " + str(display_item.bounds()))
            rect.join(display_item.bounds())
        return rect

    def print_display_list(self):
        print("Display list:")
        out = ""
        for display_item in self.display_list:
            out += display_item.repr_recursive(indent=2, include_noop=True)
        print(out)

    def run_animation_frame(self):
        if self.needs_raf_callbacks:
            self.needs_raf_callbacks = False
            self.js.interp.evaljs("__runRAFHandlers()")

        self.run_rendering_pipeline()

#        self.print_display_list()
        document_bounds = self.compute_document_bounds()
        clamped_scroll = clamp_scroll(self.scroll,
            document_bounds.height())
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_tab = True
        self.scroll = clamped_scroll

        self.commit_func(
            self.url, clamped_scroll if self.scroll_changed_in_tab \
                else None, 
            document_bounds,
            self.display_list)
        self.scroll_changed_in_tab = False

    def run_rendering_pipeline(self):
        timer = None

        to_delete = []
        for animation_key in self.animations:
            if not self.animations[animation_key].animate():
                to_delete.append(animation_key)

        for key in to_delete:
            del self.animations[key]

        if self.needs_pipeline_update:
            timer = Timer()
            timer.start()

            style(self.nodes, sorted(self.rules,
                key=cascade_priority), self)
            self.document = DocumentLayout(self.nodes)
            self.document.layout()

        if self.needs_paint:
            self.display_list = []
            self.document.paint(self.display_list)
            if self.focus:
                obj = [obj for obj in tree_to_list(self.document, [])
                       if obj.node == self.focus][0]
                text = self.focus.attributes.get("value", "")
                x = obj.x + obj.font.measureText(text)
                y = obj.y
                self.display_list.append(
                    DrawLine(x, y, x, y + obj.height))
            self.needs_paint = False

        self.needs_pipeline_update = False

        if timer:
            self.time_in_style_layout_and_paint += timer.stop()

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
                self.load(url)
                return
            elif elt.tag == "input":
                elt.attributes["value"] = ""
                if elt != self.focus:
                    self.set_needs_pipeline_update()
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
            self.set_needs_pipeline_update()

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18

class Task:
    def __init__(self, task_code, *args):
        self.task_code = task_code
        self.args = args
        self.__name__ = "task"

    def __call__(self):
        self.task_code(*self.args)
        self.task_code = None
        self.args = None

class TaskQueue:
    def __init__(self):
        self.tasks = []

    def add_task(self, task_code):
        self.tasks.append(task_code)

    def has_tasks(self):
        retval = len(self.tasks) > 0
        return retval

    def get_next_task(self):
        retval = self.tasks.pop(0)
        return retval

    def clear(self):
        self.tasks = []

class SingleThreadedTaskRunner:
    def __init__(self, tab):
        self.tab = tab

    def schedule_scroll(self, scroll):
        self.tab.apply_scroll(scroll)

    def schedule_animation_frame(self):
        self.tab.run_animation_frame()

    def schedule_script_task(self, script):
        script()

    def schedule_browser_task(self, callback):
        callback()

    def schedule_scroll(self, scroll):
        self.tab.scroll = scroll

    def clear_pending_tasks(self):
        pass

    def start(self):    
        pass

    def set_needs_quit(self):
        pass

    def run(self):
        pass

class MainThreadRunner:
    def __init__(self, tab):
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.tab = tab
        self.needs_animation_frame = False
        self.main_thread = threading.Thread(target=self.run, args=())
        self.script_tasks = TaskQueue()
        self.browser_tasks = TaskQueue()
        self.needs_quit = False
        self.pending_scroll = None

    def schedule_animation_frame(self):
        self.lock.acquire(blocking=True)
        self.needs_animation_frame = True
        self.condition.notify_all()
        self.lock.release()

    def schedule_script_task(self, script):
        self.lock.acquire(blocking=True)
        self.script_tasks.add_task(script)
        self.condition.notify_all()
        self.lock.release()

    def schedule_browser_task(self, callback):
        self.lock.acquire(blocking=True)
        self.browser_tasks.add_task(callback)
        self.condition.notify_all()
        self.lock.release()

    def set_needs_quit(self):
        self.lock.acquire(blocking=True)
        self.needs_quit = True
        self.condition.notify_all()
        self.lock.release()

    def schedule_scroll(self, scroll):
        self.lock.acquire(blocking=True)
        self.pending_scroll = scroll
        self.condition.notify_all()
        self.lock.release()

    def clear_pending_tasks(self):
        self.needs_animation_frame = False
        self.script_tasks.clear()
        self.browser_tasks.clear()
        self.pending_scroll = None

    def start(self):
        self.main_thread.start()

    def run(self):
        while True:
            if self.needs_quit:
                return;

            self.lock.acquire(blocking=True)
            needs_animation_frame = self.needs_animation_frame
            self.needs_animation_frame = False
            pending_scroll = self.pending_scroll
            self.pending_scroll = None
            self.lock.release()
            if pending_scroll:
                self.tab.apply_scroll(pending_scroll)
            if needs_animation_frame:
                self.tab.run_animation_frame()

            browser_method = None
            self.lock.acquire(blocking=True)
            if self.browser_tasks.has_tasks():
                browser_method = self.browser_tasks.get_next_task()
            self.lock.release()
            if browser_method:
                browser_method()

            script = None
            self.lock.acquire(blocking=True)
            if self.script_tasks.has_tasks():
                script = self.script_tasks.get_next_task()
            self.lock.release()
            if script:
                script()

            self.lock.acquire(blocking=True)
            if not self.script_tasks.has_tasks() and \
                not self.browser_tasks.has_tasks() and not \
                self.needs_animation_frame and not \
                self.pending_scroll and not \
                self.needs_quit:
                self.condition.wait()
            self.lock.release()

class TabWrapper:
    def __init__(self, browser):
        self.tab = Tab(self.commit)
        self.browser = browser
        self.url = None
        self.scroll = 0

    def schedule_load(self, url, body=None):
        self.tab.main_thread_runner.schedule_browser_task(
            Task(self.tab.load, url, body))
        self.browser.set_needs_chrome_raster()

    def commit(self, url, scroll, tab_bounds, display_list):
        self.browser.compositor_lock.acquire(blocking=True)
        if url != self.url or scroll != self.scroll:
            self.browser.set_needs_chrome_raster()
        self.url = url
        if scroll != None:
            self.scroll = scroll
        self.browser.active_tab_bounds = tab_bounds
        self.browser.active_tab_display_list = display_list.copy()
        self.browser.set_needs_tab_raster()
        self.browser.compositor_lock.release()

    def schedule_click(self, x, y):
        self.tab.main_thread_runner.schedule_browser_task(
            Task(self.tab.click, x, y))

    def schedule_keypress(self, char):
        self.tab.main_thread_runner.schedule_browser_task(
            Task(self.tab.keypress, char))

    def schedule_go_back(self):
        self.tab.main_thread_runner.schedule_browser_task(
            Task(self.tab.go_back))

    def schedule_scroll(self, scroll):
        self.scroll = scroll
        self.tab.main_thread_runner.schedule_scroll(scroll)

    def handle_quit(self):
        print("Time in style, layout and paint: {:>.6f}s".format(
            self.tab.time_in_style_layout_and_paint))
        self.tab.main_thread_runner.set_needs_quit()

REFRESH_RATE_SEC = 0.016 # 16ms

class PaintChunk:
    def __init__(self, ancestor_effects):
        self.ancestor_effects = ancestor_effects
        self.chunk_items = []

        self.composited_ancestor_index = -1
        count = len(ancestor_effects) - 1
        for display_item in reversed(ancestor_effects):
            if display_item.needs_compositing():
                self.composited_ancestor_index = count
                break
            count -= 1

    def bounds(self):
        retval = skia.Rect.MakeEmpty()
        for item in self.chunk_items:
            retval.join(item.bounds())
        for display_item in reversed(self.ancestor_effects):
            if display_item.needs_compositing():
                break
            retval = display_item.transform(retval)
        return retval

    def append(self, display_item):
        self.chunk_items.append(display_item)

    def needs_compositing(self):
        return self.composited_ancestor_index >= 0

    def composited_item(self):
        if not self.needs_compositing():
            return None
        return self.ancestor_effects[self.composited_ancestor_index]

    def display_list(self):
        return self.chunk_items

    def raster(self, canvas):
        def op():
            for display_item in self.chunk_items:
                display_item.execute(canvas)
        self.draw_internal(canvas, op, self.composited_ancestor_index + 1)

    def draw_internal(self, canvas, op, index):
        if index == len(self.ancestor_effects):
            op()
        else:
            display_item = self.ancestor_effects[index]
            def recurse_op():
                self.draw_internal(canvas, op, index + 1)
            display_item.draw(canvas, recurse_op)

    def draw(self, canvas, op):
        self.draw_internal(canvas, op, 0)


def display_list_to_paint_chunks_internal(
    display_list, chunks, ancestor_effects):
    current_chunk = None
    for display_item in display_list:
        if display_item.get_cmds() != None:
            display_list_to_paint_chunks_internal(display_item.get_cmds(), chunks,
                ancestor_effects + [display_item])
        else:
            if not current_chunk:
                current_chunk = PaintChunk(ancestor_effects)
                chunks.append(current_chunk)
            current_chunk.append(display_item)

def print_chunks(chunks):
    for chunk in chunks:
        print('chunk:')
        print("  chunk display items:")
        for display_item in chunk.chunk_items:
            print(" " * 4 + str(display_item))
        print("  chunk ancestor visual effect (skipping no-ops):")
        count = 4
        for display_item in chunk.ancestor_effects:
            if not display_item.is_noop():
                print(" " * count + str(display_item))
                count += 2

def display_list_to_paint_chunks(display_list):
    chunks = []
    display_list_to_paint_chunks_internal(display_list, chunks, [])
    return chunks

def print_composited_layers(composited_layers):
    for layer in composited_layers:
        print("layer: bounds=" + str(layer.bounds()))

def do_composite(display_list, initial_layer):
    chunks = display_list_to_paint_chunks(display_list)
    composited_layers = [initial_layer]
    for chunk in chunks:
#        print('compositing chunk: ' + str(chunk.display_list()[0]))
#        print(chunk.needs_compositing())
        placed = False
        for layer in reversed(composited_layers):
            if layer.can_merge(chunk):
                layer.append(chunk)
                placed = True
                break
            elif layer.overlaps(chunk.bounds()):
                composited_layers.append(
                    CompositedLayer(first_chunk=chunk))
                placed = True
                break
        if not placed:
#            print('placing..')
            composited_layers.append(
                CompositedLayer(first_chunk=chunk))
    print_composited_layers(composited_layers)
    return composited_layers

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
        self.composited_layers = None

        self.tabs = []
        self.active_tab = None
        self.focus = None
        self.address_bar = ""
        self.compositor_lock = threading.Lock()

        self.time_in_raster_and_draw = 0
        self.time_in_draw = 0

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

        self.active_tab_bound = None
        self.active_tab_display_list = None
        self.composited_layers = []
        self.tab_surface = None

    def render(self):
        assert not USE_BROWSER_THREAD
        tab = self.tabs[self.active_tab].tab
        tab.run_animation_frame()

    def set_needs_tab_raster(self):
        self.needs_tab_raster = True
        self.needs_draw = True

    def set_needs_chrome_raster(self):
        self.needs_chrome_raster = True
        self.needs_draw = True

    def set_needs_draw(self):
        self.needs_draw = True

    def composite(self):
        print('\n\ncompositing...')
        initial_layer = CompositedLayer(bounds=self.active_tab_bounds)

#        print_chunks(display_list_to_paint_chunks(self.active_tab_display_list))

        self.composited_layers = do_composite(
            self.active_tab_display_list, initial_layer)

    def composite_raster_draw(self):
        self.compositor_lock.acquire(blocking=True)
        timer = None
        draw_timer = None
        if self.needs_draw:
            timer = Timer()
            timer.start()
        if self.needs_chrome_raster:
            self.raster_chrome()
        if self.needs_tab_raster:
            self.composite()
            self.raster_tab()
        if self.needs_draw:
            draw_timer = Timer()
            draw_timer.start()
            self.draw()
            self.time_in_draw += draw_timer.stop()
        self.needs_tab_raster = False
        self.needs_chrome_raster = False
        self.needs_draw = False
        self.compositor_lock.release()
        if timer:
            self.time_in_raster_and_draw += timer.stop()

    def handle_down(self):
        self.compositor_lock.acquire(blocking=True)
        if not self.active_tab_bounds:
            return
        active_tab = self.tabs[self.active_tab]
        active_tab.schedule_scroll(
            clamp_scroll(
                active_tab.scroll + SCROLL_STEP,
                self.active_tab_bounds.height()))
        self.set_needs_draw()
        self.compositor_lock.release()

    def handle_click(self, e):
        self.compositor_lock.acquire(blocking=True)
        if e.y < CHROME_PX:
            self.focus = None
            if 40 <= e.x < 40 + 80 * len(self.tabs) and 0 <= e.y < 40:
                self.active_tab = int((e.x - 40) / 80)
            elif 10 <= e.x < 30 and 10 <= e.y < 30:
                self.load("https://browser.engineering/")
            elif 10 <= e.x < 35 and 40 <= e.y < 90:
                self.tabs[self.active_tab].schedule_go_back()
            elif 50 <= e.x < WIDTH - 10 and 40 <= e.y < 90:
                self.focus = "address bar"
                self.address_bar = ""
            self.set_needs_chrome_raster()
        else:
            self.focus = "content"
            self.tabs[self.active_tab].schedule_click(
                e.x, e.y - CHROME_PX)
        self.compositor_lock.release()

    def handle_key(self, char):
        self.compositor_lock.acquire(blocking=True)
        if not (0x20 <= ord(char) < 0x7f): return
        if self.focus == "address bar":
            self.address_bar += char
            self.set_needs_chrome_raster()
        elif self.focus == "content":
            self.tabs[self.active_tab].schedule_keypress(char)
        self.compositor_lock.release()

    def handle_enter(self):
        self.compositor_lock.acquire(blocking=True)
        if self.focus == "address bar`":
            self.tabs[self.active_tab].schedule_load(self.address_bar)
            self.tabs[self.active_tab].url = self.address_bar
            self.focus = None
            self.set_needs_chrome_raster()
        self.compositor_lock.release()

    def load(self, url):
        new_tab = TabWrapper(self)
        new_tab.schedule_load(url)
        self.active_tab = len(self.tabs)
        self.tabs.append(new_tab)

    def raster_tab(self):
        for composited_layer in self.composited_layers:
            composited_layer.raster()

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
            if url:
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
        
        draw_offset=(0, CHROME_PX - self.tabs[self.active_tab].scroll)
        if self.composited_layers:
            for composited_layer in self.composited_layers:
                composited_layer.draw(canvas, draw_offset)

        chrome_rect = skia.Rect.MakeLTRB(0, 0, WIDTH, CHROME_PX)
        canvas.save()
#        canvas.clipRect(chrome_rect)
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
        print("Time in raster and draw: {:>.6f}s".format(
            self.time_in_raster_and_draw))
        print("Time in draw: {:>.6f}s".format(
            self.time_in_draw))

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
        if not USE_BROWSER_THREAD and \
            browser.tabs[browser.active_tab].tab.display_scheduled:
            browser.render()
        browser.composite_raster_draw()
