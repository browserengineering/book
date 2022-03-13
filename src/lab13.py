f"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 13 (Animations and Compositing),
without exercises.
"""

import ctypes
import dukpy
import io
import math
import sdl2
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
from lab11 import draw_line, draw_text, get_font, linespace, \
    parse_blend_mode, parse_color, request, CHROME_PX, SCROLL_STEP
from OpenGL import GL

class MeasureTime:
    def __init__(self, name):
        self.name = name
        self.start_time = None
        self.total_s = 0
        self.count = 0

    def start(self):
        self.start_time = time.time()

    def stop(self):
        self.total_s += time.time() - self.start_time
        self.count += 1
        self.start_time = None

    def text(self):
        if self.count == 0: return ""
        avg = self.total_s / self.count
        return "Time in {} on average: {:>.0f}ms".format(
            self.name, avg * 1000)

def center_point(rect):
    return (rect.left() + (rect.right() - rect.left()) / 2,
        rect.top() + (rect.bottom() - rect.top()) / 2)

class DisplayItem:
    def __init__(self, rect, needs_compositing=False, cmds=None,
        is_noop=False, node=None, item_type=None):
        self.rect = rect if rect else skia.Rect.MakeEmpty()
        self.composited=needs_compositing
        self.cmds = cmds
        self.noop = is_noop
        self.item_type = item_type
        self.node = node

    def bounds(self):
        return self.rect

    def needs_compositing(self):
        return USE_COMPOSITING and self.composited

    def get_cmds(self):
        return self.cmds

    def is_noop(self):
        return self.noop

    def execute(self, canvas):
        if self.cmds:
            def op():
                for cmd in self.get_cmds():
                    cmd.execute(canvas, True, False)
            self.draw(canvas, op, True)
        else:
            self.draw(canvas)

    def draw(self, canvas, op):
        pass

    def transform(self, rect):
        return rect

    def copy(self, display_item):
        assert False

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
    def __init__(self, translation,
        rect, node, cmds):
        self.translation = translation
        should_transform = translation != None
        self.self_rect = rect
        my_bounds = self.compute_bounds(rect, cmds, should_transform)

        super().__init__(
            rect=my_bounds, needs_compositing=should_transform, cmds=cmds,
            is_noop=not should_transform, node=node, item_type="transform")

    def draw(self, canvas, op):
        if self.is_noop():
            op()
        else:
            assert self.translation
            (x, y) = self.translation
            canvas.save()
            canvas.translate(x, y)
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
        return matrix.mapRect(rect)

    def compute_bounds(self, rect, cmds, should_transform):
        for cmd in cmds:
            rect.join(cmd.bounds())
        return self.transform_internal(rect, should_transform)

    def copy(self, other):
        assert other.item_type == self.item_type
        self.translation = other.translation
        should_transform = self.translation != None
        self.rect = self.compute_bounds(self.rect, self.get_cmds(), should_transform)

    def __repr__(self):
        if self.is_noop():
            return "Transform(<no-op>)"
        else:
            return "Transform(translate({}, {}))".format(self.translation)

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

def draw_rect(
    canvas, l, t, r, b, fill_color=None, border_color="black", width=1):
    paint = skia.Paint()
    if fill_color:
        paint.setStrokeWidth(width);
        paint.setColor(parse_color(fill_color))
    else:
        paint.setStyle(skia.Paint.kStroke_Style)
        paint.setStrokeWidth(1);
        paint.setColor(parse_color(border_color))
    rect = skia.Rect.MakeLTRB(l, t, r, b)
    canvas.drawRect(rect, paint)

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
            fill_color=self.color, width=0)

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
    def __init__(self, sk_paint, node, cmds,
            should_save=True, should_paint_cmds=True, needs_animation=False):
        self.should_paint_cmds = should_paint_cmds
        self.sk_paint = sk_paint
        rect = skia.Rect.MakeEmpty()
        for cmd in cmds:
            rect.join(cmd.rect)
        super().__init__(
            rect=rect, needs_compositing=should_save, cmds=cmds,
            is_noop=not should_save, node=node, item_type="save_layer")

    def draw(self, canvas, op):
        if not self.is_noop():
            canvas.saveLayer(paint=self.sk_paint)
        if self.should_paint_cmds:
            op()
        if not self.is_noop():
            canvas.restore()

    def copy(self, other):
        assert other.item_type == self.item_type
        self.sk_paint = other.sk_paint

    def __repr__(self):
        if self.is_noop():
            return "SaveLayer(<no-op>)"
        else:
            return "SaveLayer(alpha={})".format(self.sk_paint.getAlphaf())

def parse_transform(transform_str):
    if transform_str.find('translate') < 0:
        return None
    left_paren = transform_str.find('(')
    right_paren = transform_str.find(')')
    (x_px, y_px) = \
        transform_str[left_paren + 1:right_paren].split(",")
    return (float(x_px[:-2]), float(y_px[:-2]))

USE_COMPOSITING = True

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
        display_list.append(
            DrawRect(self.x, self.y, self.x + self.width, self.y + self.height,
                "white"))
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
        return int(math.floor(float(style_val[:-2])))
    else:
        return default_value

def paint_visual_effects(node, cmds, rect):
    opacity = float(node.style.get("opacity", "1.0"))
    blend_mode = parse_blend_mode(node.style.get("mix-blend-mode"))
    translation = parse_transform(node.style.get("transform", ""))

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

    if transform.needs_compositing() or save_layer.needs_compositing:
        node.transform = transform
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
        full_url = resolve_url(url, self.tab.url)
        if not self.tab.allowed_request(full_url):
            raise Exception("Cross-origin XHR blocked by CSP")
        if url_origin(full_url) != url_origin(self.tab.url):
            raise Exception(
                "Cross-origin XHR request not allowed")

        def run_load():
            headers, response = request(
                full_url, self.tab.url, payload=body)
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

USE_BROWSER_THREAD = True

def animate_style(node, old_style, new_style, tab):
    if not old_style:
        return

    try_numeric_animation(node, "opacity",
        old_style, new_style, tab, is_px=False)
    try_numeric_animation(node, "width",
        old_style, new_style, tab, is_px=True)
    try_transform_animation(node, old_style, new_style, tab)

def get_transition(property_value, style):
    if not "transition" in style:
        return None
    transition_items = style["transition"].split(",")
    found = False
    for item in transition_items:
        if property_value == item.split(" ")[0]:
            found = True
            break
    if not found:
        return None   
    duration_secs = float(item.split(" ")[1][:-1])
    return duration_secs / REFRESH_RATE_SEC 

def try_transition(name, node, old_style, new_style):
    if not get_transition(name, old_style):
        return None

    num_frames = get_transition(name, new_style)
    if num_frames == None:
        return None

    if name not in old_style or name not in new_style:
        return None

    if old_style[name] == new_style[name]:
        return None

    return num_frames

def try_transform_animation(node, old_style, new_style, tab):
    num_frames = try_transition("transform", node,
        old_style, new_style)
    if num_frames == None:
        return None;

    old_translation = parse_transform(old_style["transform"])
    new_translation = parse_transform(new_style["transform"])

    if old_translation == None or new_translation == None:
        return None

    if not node in tab.animations:
        tab.animations[node] = {}
    tab.animations[node]["transform"] = TranslateAnimation(
        node, old_translation, new_translation, num_frames, tab)

def try_numeric_animation(node, name,
    old_style, new_style, tab, is_px):
    num_frames = try_transition(name, node, old_style, new_style)
    if num_frames == None:
        return None;

    if is_px:
        old_value = float(old_style[name][:-2])
        new_value = float(new_style[name][:-2])
    else:
        old_value = float(old_style[name])
        new_value = float(new_style[name])

    if not node in tab.animations:
        tab.animations[node] = {}
    tab.animations[node][name] = NumericAnimation(
        node, name, is_px, old_value, new_value,
        num_frames, tab)

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

class TranslateAnimation:
    def __init__(
        self, node, old_translation, new_translation,
        num_frames, tab):
        self.node = node
        (self.old_x, self.old_y) = old_translation
        (new_x, new_y) = new_translation
        self.change_per_frame_x = (new_x - self.old_x) / num_frames
        self.change_per_frame_y = (new_y - self.old_y) / num_frames
        self.num_frames = num_frames
        self.tab = tab
        self.frame_count = 0
        self.animate()

    def animate(self):
        self.frame_count += 1
        if self.frame_count >= self.num_frames: return False
        self.node.style["transform"] = \
            "translate({}px,{}px)".format(
                self.old_x +
                self.change_per_frame_x * self.frame_count,
                self.old_y +
                self.change_per_frame_y * self.frame_count)
        self.tab.set_needs_animation(self.node, "transform", True)
        return True

class NumericAnimation:
    def __init__(
        self, node, property_name, is_px,
        old_value, new_value, num_frames, tab):
        self.node = node
        self.property_name = property_name
        self.is_px = is_px
        self.old_value = old_value
        self.num_frames = num_frames
        self.change_per_frame = (new_value - old_value) / num_frames
        self.tab = tab
        self.frame_count = 0
        self.animate()

    def animate(self):
        self.frame_count += 1
        if self.frame_count >= self.num_frames: return False
        updated_value = self.old_value + \
            self.change_per_frame * self.frame_count
        if self.is_px:
            self.node.style[self.property_name] = \
                "{}px".format(updated_value)
        else:
            self.node.style[self.property_name] = \
                "{}".format(updated_value)
        self.tab.set_needs_animation(self.node, self.property_name,
            self.property_name == "opacity" and USE_COMPOSITING)
        return True

SHOW_COMPOSITED_LAYER_BORDERS = False

class CompositedLayer:
    def __init__(self, first_chunk, skia_context):
        self.surface = None
        self.skia_context = skia_context
        self.chunks = []

    def init(self, first_chunk):
        self.chunks = []
        self.chunks.append(first_chunk)

    def can_merge(self, chunk):
        if len(self.chunks) == 0:
            return not chunk.needs_compositing()
        return  \
            self.chunks[0].composited_item() == chunk.composited_item()

    def composited_bounds(self):
        retval = skia.Rect.MakeEmpty()
        for chunk in self.chunks:
            retval.join(chunk.composited_bounds())
        return retval

    def absolute_bounds(self):
        retval = skia.Rect.MakeEmpty()
        for chunk in self.chunks:
            retval.join(chunk.absolute_bounds())
        return retval

    def composited_item(self):
        return self.chunks[0].composited_item()

    def composited_items(self):
        return self.chunks[0].composited_items()

    def append(self, chunk):
        assert self.can_merge(chunk)
        self.chunks.append(chunk)

    def overlaps(self, rect):
        return skia.Rect.Intersects(self.absolute_bounds(), rect)

    def draw(self, canvas, draw_offset):
        if not self.surface:
            return

        assert len(self.chunks) > 0

        def op():
            bounds = self.composited_bounds()
            surface_offset_x = bounds.left()
            surface_offset_y = bounds.top()
            self.surface.draw(canvas, surface_offset_x, surface_offset_y)

        (draw_offset_x, draw_offset_y) = draw_offset

        canvas.save()
        canvas.translate(draw_offset_x, draw_offset_y)
        self.chunks[0].draw(canvas, op)
        canvas.restore()

    def raster(self):
        bounds = self.composited_bounds()
        if bounds.isEmpty():
            return
        irect = bounds.roundOut()
        if not self.surface:
            if USE_GPU:
                self.surface = skia.Surface.MakeRenderTarget(
                    self.skia_context, skia.Budgeted.kNo,
                    skia.ImageInfo.MakeN32Premul(
                        irect.width(), irect.height()))
                assert self.surface is not None
            else:
                self.surface = skia.Surface(irect.width(), irect.height())

        canvas = self.surface.getCanvas()

        canvas.clear(skia.ColorTRANSPARENT)
        canvas.save()
        canvas.translate(-bounds.left(), -bounds.top())
        for chunk in self.chunks:
            chunk.raster(canvas)
        canvas.restore()

        if SHOW_COMPOSITED_LAYER_BORDERS:
            draw_rect(
                canvas, 0, 0, irect.width() - 1, irect.height() - 1,
                border_color="red")

    def __repr__(self):
        return ("layer: composited_bounds={} " +
            "absolute_bounds={} first_chunk={}").format(
            self.composited_bounds(), self.absolute_bounds(),
            self.chunks[0] if len(self.chunks) > 0 else 'None')

def raster(display_list, canvas):
    for cmd in display_list:
        cmd.execute(canvas)

def clamp_scroll(scroll, tab_height):
    return max(0, min(scroll, tab_height - (HEIGHT - CHROME_PX)))

class Tab:
    def __init__(self, browser):
        self.history = []
        self.focus = None
        self.url = None
        self.scroll = 0
        self.scroll_changed_in_tab = False
        self.needs_raf_callbacks = False
        self.needs_render = False
        self.needs_layout = False
        self.needs_paint = False
        self.browser = browser
        if USE_BROWSER_THREAD:
            self.task_runner = TaskRunner(self)
        else:
            self.task_runner = SingleThreadedTaskRunner(self)
        self.task_runner.start()

        self.measure_render = MeasureTime("render")

        self.animations = {}
        self.composited_animation_updates = []

        with open("browser8.css") as f:
            self.default_style_sheet = CSSParser(f.read()).parse()

    def allowed_request(self, url):
        return self.allowed_origins == None or \
            url_origin(url) in self.allowed_origins

    def script_run_wrapper(self, script, script_text):
        return Task(self.js.run, script, script_text)

    def load(self, url, body=None):
        self.scroll = 0
        self.scroll_changed_in_tab = True
        self.task_runner.clear_pending_tasks()
        headers, body = request(url, self.url, payload=body)
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
            style_url = resolve_url(link, url)
            if not self.allowed_request(style_url):
                print("Blocked style", link, "due to CSP")
                continue
            try:
                header, body = request(style_url, url)
            except:
                continue
            self.rules.extend(CSSParser(body).parse())
        self.set_needs_render()

    def set_needs_render(self):
        self.needs_render = True
        self.needs_layout = True
        self.needs_paint = True
        self.browser.set_needs_animation_frame(self)

    def set_needs_layout(self):
        self.needs_layout = True
        self.needs_paint = True
        self.browser.set_needs_animation_frame(self)

    def request_animation_frame_callback(self):
        self.needs_raf_callbacks = True
        self.browser.set_needs_animation_frame(self)

    def set_needs_animation(self, node, property_name, is_composited):
        if is_composited:
            self.needs_paint = True
            self.composited_animation_updates.append(node)
            self.browser.set_needs_animation_frame(self)
        else:
            self.set_needs_layout()

    def run_animation_frame(self, scroll):
        if not self.scroll_changed_in_tab:
            self.scroll = scroll
        self.js.interp.evaljs("__runRAFHandlers()")

        to_delete = []
        for node in self.animations:
            for (property_name, animation) in \
                self.animations[node].items():
                if not animation.animate():
                    to_delete.append((node, property_name))

        for (node, property_name) in to_delete:
            del self.animations[node][property_name]

        needs_composite = self.needs_render or self.needs_layout

        self.render()

        document_height = math.ceil(self.document.height)
        clamped_scroll = clamp_scroll(self.scroll, document_height)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_tab = True
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_tab = True
        self.scroll = clamped_scroll

        scroll = None
        if self.scroll_changed_in_tab:
            scroll = self.scroll

        composited_updates = []
        if not needs_composite:
            for node in self.composited_animation_updates:
                composited_updates.append(
                    (node, node.transform, node.save_layer))
        self.composited_animation_updates.clear()

        commit_data = CommitForRaster(
            url=self.url,
            scroll=scroll,
            height=document_height,
            display_list=self.display_list,
            composited_updates=composited_updates,
            needs_composite=needs_composite
        )
        self.display_list = None
        self.scroll_changed_in_tab = False

        self.browser.commit(self, commit_data)

    def render(self):
        if not self.needs_render \
            and not self.needs_layout \
            and not self.needs_paint:
            return

        self.measure_render.start()

        if self.needs_render:
            style(self.nodes, sorted(self.rules,
                key=cascade_priority), self)

        if self.needs_layout:
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
        self.needs_render = False
        self.needs_layout = False
        self.needs_paint = False

        self.measure_render.stop()

    def click(self, x, y):
        self.render()
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
                    self.set_needs_render()
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
            self.set_needs_render()

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

    def run(self):
        self.task_code(*self.args)
        self.task_code = None
        self.args = None

class SingleThreadedTaskRunner:
    def __init__(self, tab):
        self.tab = tab
        self.needs_quit = False
        self.lock = threading.Lock()

    def schedule_task(self, callback):
        callback.run()

    def clear_pending_tasks(self):
        pass

    def start(self):    
        pass

    def set_needs_quit(self):
        self.needs_quit = True
        pass

    def run(self):
        pass

class CommitForRaster:
    def __init__(self, url, scroll, height, display_list, composited_updates,
        needs_composite):
        self.url = url
        self.scroll = scroll
        self.height = height
        self.display_list = display_list
        self.composited_updates = composited_updates
        self.needs_composite = needs_composite

class TaskRunner:
    def __init__(self, tab):
        self.condition = threading.Condition()
        self.tab = tab
        self.tasks = []
        self.main_thread = threading.Thread(target=self.run)
        self.needs_quit = False

    def schedule_task(self, task):
        self.condition.acquire(blocking=True)
        self.tasks.append(task)
        self.condition.notify_all()
        self.condition.release()

    def set_needs_quit(self):
        self.condition.acquire(blocking=True)
        self.needs_quit = True
        self.condition.notify_all()
        self.condition.release()

    def clear_pending_tasks(self):
        self.tasks.clear()
        self.pending_scroll = None

    def start(self):
        self.main_thread.start()

    def run(self):
        while True:
            self.condition.acquire(blocking=True)
            needs_quit = self.needs_quit
            self.condition.release()
            if needs_quit:
                self.handle_quit()
                return

            task = None
            self.condition.acquire(blocking=True)
            if len(self.tasks) > 0:
                task = self.tasks.pop(0)
            self.condition.release()
            if task:
                task.run()

            self.condition.acquire(blocking=True)
            if len(self.tasks) == 0:
                self.condition.wait()
            self.condition.release()


    def handle_quit(self):
        print(self.tab.measure_render.text())

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

    def equals(self, other_chunk):
        return self.chunk_items[0].node == other_chunk.chunk_items[0].node

    def absolute_bounds(self):
        return self.bounds_internal(True)

    def composited_bounds(self):
        return self.bounds_internal(False)

    def bounds_internal(self, include_composited):
        retval = skia.Rect.MakeEmpty()
        for item in self.chunk_items:
            retval.join(item.bounds())
        for display_item in reversed(self.ancestor_effects):
            if display_item.needs_compositing() and not include_composited:
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

    def composited_items(self):
        items = []
        for item in reversed(self.ancestor_effects):
            if item.needs_compositing():
                items.append(item)
        return items

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
        if self.composited_ancestor_index >= 0:
            self.draw_internal(canvas, op, 0)
        else:
            op()

    def __repr__(self):
        composited_item = None
        if self.composited_ancestor_index >= 0:
            composited_item = \
                self.ancestor_effects[self.composited_ancestor_index]
        return "Chunk: first_item={} composited_item=".format(
            self.chunk_items[0], composited_item)

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
        print('chunks:')
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
    print("Composited layers:")
    for layer in composited_layers:
        print("  " * 4 + str(layer))

def get_composited_layer(
    chunk, current_composited_layers, current_index, skia_context):
    layer = None
    if current_index < len(current_composited_layers):
        if current_composited_layers[current_index].chunks[0].equals(chunk):
            layer = current_composited_layers[current_index]
            current_index += 1

    if not layer:
        layer = CompositedLayer(chunk, skia_context)
        current_index = len(current_composited_layers)

    layer.init(chunk)
    return (layer, current_index)

def do_compositing(display_list, skia_context,
    current_composited_layers):
    chunks = display_list_to_paint_chunks(display_list)
    composited_layers = []
    current_index = 0
    for chunk in chunks:
        placed = False
        for layer in reversed(composited_layers):
            if layer.can_merge(chunk):
                layer.append(chunk)
                placed = True
                break
            elif layer.overlaps(chunk.absolute_bounds()):
                (layer, current_index) = get_composited_layer(
                    chunk, current_composited_layers, current_index,
                    skia_context)
                composited_layers.append(layer)
                placed = True
                break
        if not placed:
            (layer, current_index) = get_composited_layer(
                chunk, current_composited_layers, current_index,
                skia_context)
            composited_layers.append(layer)

    return composited_layers

USE_GPU = True

class Browser:
    def __init__(self):
        if USE_GPU:
            self.sdl_window = sdl2.SDL_CreateWindow(b"Browser",
                sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
                WIDTH, HEIGHT,
                sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_OPENGL)
            self.gl_context = sdl2.SDL_GL_CreateContext(self.sdl_window)
            print("OpenGL initialized: vendor={}, renderer={}".format(
                GL.glGetString(GL.GL_VENDOR),
                GL.glGetString(GL.GL_RENDERER)))

            self.skia_context = skia.GrDirectContext.MakeGL()

            self.root_surface = skia.Surface.MakeFromBackendRenderTarget(
                self.skia_context,
                skia.GrBackendRenderTarget(
                    WIDTH, HEIGHT,
                    0,  # sampleCnt
                    0,  # stencilBits
                    skia.GrGLFramebufferInfo(0, GL.GL_RGBA8)),
                    skia.kBottomLeft_GrSurfaceOrigin,
                    skia.kRGBA_8888_ColorType, skia.ColorSpace.MakeSRGB())
            assert self.root_surface is not None

            self.chrome_surface =  skia.Surface.MakeRenderTarget(
                    self.skia_context, skia.Budgeted.kNo,
                    skia.ImageInfo.MakeN32Premul(WIDTH, CHROME_PX))
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
            self.chrome_surface = skia.Surface(WIDTH, CHROME_PX)
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
        self.needs_raster = False
        self.needs_draw = False
        self.needs_composite = False

        self.active_tab_height = 0
        self.active_tab_display_list = None

        self.composited_updates = []
        self.composited_layers = []

    def render(self):
        assert not USE_BROWSER_THREAD
        tab = self.tabs[self.active_tab]
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
            self.composited_updates = data.composited_updates

            self.animation_timer = None
            if data.needs_composite or len(self.composited_layers) == 0:
                self.set_needs_composite()
            else:
                self.set_needs_draw()
        self.lock.release()

    def set_needs_animation_frame(self, tab):
        self.lock.acquire(blocking=True)
        if tab == self.tabs[self.active_tab]:
            self.needs_animation_frame = True
        self.lock.release()

    def set_needs_raster_and_draw(self):
        self.needs_raster = True
        self.needs_draw = True
        self.needs_animation_frame = True

    def set_needs_composite(self):
        self.needs_composite = True
        self.needs_raster = True
        self.needs_draw = True

    def set_needs_draw(self):
        self.needs_draw = True

    def composite(self):
        if self.needs_composite:
            self.composited_layers = do_compositing(
                self.active_tab_display_list, self.skia_context,
                self.composited_layers)

            self.active_tab_height = 0
            for layer in self.composited_layers:
                self.active_tab_height = \
                    max(self.active_tab_height, layer.absolute_bounds().bottom())
        else:
            for (node, transform, save_layer) in self.composited_updates:
                success = False
                for layer in self.composited_layers:
                    composited_items = layer.composited_items()
                    for composited_item in composited_items:
                        if composited_item.item_type == "transform":
                            composited_item.copy(transform)
                            success = True
                        elif composited_item.item_type == "save_layer":
                            composited_item.copy(save_layer)
                            success = True
                assert success

    def composite_raster_and_draw(self):
        self.lock.acquire(blocking=True)
        if not self.needs_composite and len(self.composited_updates) == 0 \
            and not self.needs_raster and not self.needs_draw:
            self.lock.release()
            return

        self.measure_composite_raster_and_draw.start()
        start_time = time.time()
        if self.needs_composite or len(self.composited_updates) > 0:
            self.composite()
        if self.needs_raster:
            self.raster_chrome()
            self.raster_tab()
        if self.needs_draw:
            self.draw()
        self.measure_composite_raster_and_draw.stop()
        self.needs_composite = False
        self.needs_raster = False
        self.needs_draw = False
        self.composited_updates.clear()
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
            if USE_BROWSER_THREAD:
                self.animation_timer = \
                    threading.Timer(REFRESH_RATE_SEC, callback)
                self.animation_timer.start()
        self.lock.release()

    def handle_down(self):
        self.lock.acquire(blocking=True)
        if not self.active_tab_height: return
        active_tab = self.tabs[self.active_tab]
        scroll = clamp_scroll(
            self.scroll + SCROLL_STEP,
            self.active_tab_height)
        self.scroll = scroll
        self.set_needs_raster_and_draw()
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
        if e.y < CHROME_PX:
            self.focus = None
            if 40 <= e.x < 40 + 80 * len(self.tabs) and 0 <= e.y < 40:
                self.set_active_tab(int((e.x - 40) / 80))
            elif 10 <= e.x < 30 and 10 <= e.y < 30:
                self.load("https://browser.engineering/")
            elif 10 <= e.x < 35 and 40 <= e.y < 90:
                active_tab = self.tabs[self.active_tab]
                task = Task(active_tab.go_back)
                active_tab.task_runner.schedule_task(task)
                self.clear_data()
            elif 50 <= e.x < WIDTH - 10 and 40 <= e.y < 90:
                self.focus = "address bar"
                self.address_bar = ""
            self.set_needs_raster_and_draw()
        else:
            self.focus = "content"
            active_tab = self.tabs[self.active_tab]
            task = Task(active_tab.click, e.x, e.y - CHROME_PX)
            active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def handle_key(self, char):
        self.lock.acquire(blocking=True)
        if not (0x20 <= ord(char) < 0x7f): return
        if self.focus == "address bar":
            self.address_bar += char
            self.set_needs_raster_and_draw()
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
            self.schedule_load(self.address_bar)
            self.url = self.address_bar
            self.focus = None
            self.set_needs_raster_and_draw()
        self.lock.release()

    def load(self, url):
        new_tab = Tab(self)
        self.set_active_tab(len(self.tabs))
        self.tabs.append(new_tab)
        self.schedule_load(url)

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
            if self.url:
                draw_text(canvas, 55, 55, self.url, buttonfont)

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
        canvas.clipRect(chrome_rect)
        self.chrome_surface.draw(canvas, 0, 0)
        canvas.restore()

        if USE_GPU:
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
        if USE_GPU:
            sdl2.SDL_GL_DeleteContext(self.gl_context)
        sdl2.SDL_DestroyWindow(self.sdl_window)

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Chapter 13 code')
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

    USE_BROWSER_THREAD = not args.single_threaded
    USE_GPU = not args.disable_gpu
    USE_COMPOSITING = not args.disable_compositing and not args.disable_gpu
    SHOW_COMPOSITED_LAYER_BORDERS = args.show_composited_layer_borders

    sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS)
    browser = Browser()
    browser.load(args.url)

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
        if not USE_BROWSER_THREAD:
            if active_tab.task_runner.needs_quit:
                break
            if browser.needs_animation_frame:
                browser.needs_animation_frame = False
                browser.render()
        browser.composite_raster_and_draw()
        browser.schedule_animation_frame()
