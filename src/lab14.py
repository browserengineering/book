"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 14 (Making Content Accessible),
without exercises.
"""

import ctypes
import dukpy
import math
import os
import gtts
import playsound
import sdl2
import skia
import socket
import ssl
import threading
import time
import urllib.parse
import wbetools
import OpenGL.GL as GL

from lab2 import WIDTH, HEIGHT, HSTEP, VSTEP, SCROLL_STEP
from lab4 import Text, Element, print_tree, HTMLParser
from lab5 import BLOCK_ELEMENTS
from lab6 import TagSelector, DescendantSelector
from lab6 import INHERITED_PROPERTIES, compute_style
from lab6 import resolve_url, tree_to_list
from lab7 import CHROME_PX
from lab8 import INPUT_WIDTH_PX, layout_mode
from lab9 import EVENT_DISPATCH_CODE
from lab10 import COOKIE_JAR, request, url_origin
from lab11 import FONTS, get_font, parse_blend_mode, linespace
from lab11 import draw_text
from lab12 import MeasureTime, SingleThreadedTaskRunner, TaskRunner
from lab12 import Task, REFRESH_RATE_SEC
from lab13 import JSContext, diff_styles, clamp_scroll, add_parent_pointers
from lab13 import absolute_bounds, absolute_bounds_for_obj
from lab13 import map_translation, parse_transform, ANIMATED_PROPERTIES
from lab13 import CompositedLayer, paint_visual_effects
from lab13 import DisplayItem, DrawText, DrawCompositedLayer, SaveLayer
from lab13 import ClipRRect, Transform, DrawLine, DrawRRect, draw_rect

@wbetools.patch(Element)
class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent

        self.style = {}
        self.animations = {}

        self.is_focused = False
        self.layout_object = None

@wbetools.patch(Text)
class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent

        self.style = {}
        self.animations = {}

        self.is_focused = False
        self.layout_object = None

def parse_color(color):
    if color == "white":
        return skia.ColorWHITE
    elif color == "lightblue":
        return skia.ColorSetARGB(0xFF, 0xAD, 0xD8, 0xE6)
    elif color == "orange":
        return skia.ColorSetARGB(0xFF, 0xFF, 0xA5, 0x00)
    elif color == "orangered":
        return skia.ColorSetARGB(0xFF, 0xFF, 0x45, 0x00)
    elif color == "red":
        return skia.ColorRED
    elif color == "green":
        return skia.ColorGREEN
    elif color == "blue":
        return skia.ColorBLUE
    elif color == "gray":
        return skia.ColorGRAY
    elif color == "lightgreen":
        return skia.ColorSetARGB(0xFF, 0x90, 0xEE, 0x90)
    else:
        return skia.ColorBLACK

def parse_outline(outline_str, zoom):
    if not outline_str: return None
    values = outline_str.split(" ")
    if len(values) != 3: return None
    if values[1] != "solid": return None
    return (device_px(int(values[0][:-2]), zoom), values[2])

class DrawOutline(DisplayItem):
    def __init__(self, rect, color, thickness):
        super().__init__(rect)
        self.color = color
        self.thickness = thickness

    def is_paint_command(self):
        return True

    def execute(self, canvas):
        draw_rect(canvas,
            self.rect.left(), self.rect.top(),
            self.rect.right(), self.rect.bottom(),
            border_color=self.color, width=self.thickness)

    def __repr__(self):
        return ("DrawOutline(top={} left={} " +
            "bottom={} right={} border_color={} " +
            "thickness={})").format(
            self.rect.top(), self.rect.left(), self.rect.bottom(),
            self.rect.right(), self.color,
            self.thickness)


def is_focused(node):
    if isinstance(node, Text):
        node = node.parent
    return node.is_focused

def has_outline(node):
    return parse_outline(node.style.get("outline"), 1)

def paint_outline(node, cmds, rect, zoom):
    if has_outline(node):
        thickness, color = parse_outline(node.style.get("outline"), zoom)
        cmds.append(DrawOutline(rect, color, thickness))

class BlockLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        node.layout_object = self
        self.parent = parent
        self.previous = previous
        self.children = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None

    def layout(self, zoom):
        self.width = self.parent.width
        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        mode = layout_mode(self.node)
        if mode == "block":
            previous = None
            for child in self.node.children:
                next = BlockLayout(child, self, previous)
                self.children.append(next)
                previous = next
        else:
            self.new_line()
            self.recurse(self.node, zoom)

        for child in self.children:
            child.layout(zoom)

        self.height = sum([child.height for child in self.children])

    def recurse(self, node, zoom):
        if isinstance(node, Text):
            self.text(node, zoom)
        else:
            if node.tag == "br":
                self.new_line()
            elif node.tag == "input" or node.tag == "button":
                self.input(node, zoom)
            else:
                for child in node.children:
                    self.recurse(child, zoom)

    def new_line(self):
        self.previous_word = None
        self.cursor_x = 0
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line)
        self.children.append(new_line)

    def text(self, node, zoom):
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        size = device_px(float(node.style["font-size"][:-2]), zoom)
        font = get_font(size, weight, size)
        for word in node.text.split():
            w = font.measureText(word)
            if self.cursor_x + w > self.width:
                self.new_line()
            line = self.children[-1]
            text = TextLayout(node, word, line, self.previous_word)
            line.children.append(text)
            self.previous_word = text
            self.cursor_x += w + font.measureText(" ")

    def input(self, node, zoom):
        w = device_px(INPUT_WIDTH_PX, zoom)
        if self.cursor_x + w > self.width:
            self.new_line()
        line = self.children[-1]
        input = InputLayout(node, line, self.previous_word)
        line.children.append(input)
        self.previous_word = input
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        size = device_px(float(node.style["font-size"][:-2]), zoom)
        font = get_font(size, weight, size)
        self.cursor_x += w + font.measureText(" ")

    def paint(self, display_list, zoom):
        cmds = []

        rect = skia.Rect.MakeLTRB(
            self.x, self.y, self.x + self.width,
            self.y + self.height)

        is_atomic = not isinstance(self.node, Text) and \
            (self.node.tag == "input" or self.node.tag == "button")

        if not is_atomic:
            bgcolor = self.node.style.get("background-color",
                                     "transparent")
            if bgcolor != "transparent":
                radius = device_px(
                    float(self.node.style.get("border-radius", "0px")[:-2]),
                        zoom)
                cmds.append(DrawRRect(rect, radius, bgcolor))
 
        for child in self.children:
            child.paint(cmds, zoom)

        if not is_atomic:
            cmds = paint_visual_effects(self.node, cmds, rect)
            paint_outline(
                self.node, cmds, rect, zoom)

        display_list.extend(cmds)

    def __repr__(self):
        return "BlockLayout[{}](x={}, y={}, width={}, height={}, node={})".format(
            layout_mode(self.node), self.x, self.y, self.width, self.height, self.node)

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

    def layout(self, zoom):
        self.width = self.parent.width
        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        for word in self.children:
            word.layout(zoom)

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

    def paint(self, display_list, zoom):
        for child in self.children:
            child.paint(display_list, zoom)

        outline_rect = skia.Rect.MakeEmpty()
        focused_node = None
        for child in self.children:
            node = child.node
            if has_outline(node.parent):
                focused_node = node.parent
                outline_rect.join(child.rect())

        if focused_node:
            paint_outline(
                focused_node, display_list, outline_rect, zoom)

    def role(self):
        return "none"

    def __repr__(self):
        return "LineLayout(x={}, y={}, width={}, height={}, node={})".format(
            self.x, self.y, self.width, self.height, self.node)

def device_px(css_px, zoom):
    return css_px * zoom

def get_tabindex(node):
    return int(node.attributes.get("tabindex", "9999999"))

def cascade_priority(rule):
    media, selector, body = rule
    return selector.priority

def style(node, rules, tab):
    old_style = node.style

    node.style = {}
    for property, default_value in INHERITED_PROPERTIES.items():
        if node.parent:
            node.style[property] = node.parent.style[property]
        else:
            node.style[property] = default_value
    for media, selector, body in rules:
        if media:
            if (media == "dark") != tab.dark_mode: continue
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

class DocumentLayout:
    def __init__(self, node):
        self.node = node
        node.layout_object = self
        self.parent = None
        self.previous = None
        self.children = []

    def layout(self, zoom):
        child = BlockLayout(self.node, self, None)
        self.children.append(child)

        self.width = WIDTH - 2 * device_px(HSTEP, zoom)
        self.x = device_px(HSTEP, zoom)
        self.y = device_px(VSTEP, zoom)
        child.layout(zoom)
        self.height = child.height + 2* device_px(VSTEP, zoom)

    def paint(self, display_list, zoom):
        self.children[0].paint(display_list, zoom)

    def __repr__(self):
        return "DocumentLayout()"

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

    def layout(self, zoom):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        size = device_px(
            float(self.node.style["font-size"][:-2]), zoom)
        self.font = get_font(size, weight, style)

        # Do not set self.y!!!
        self.width = self.font.measureText(self.word)

        if self.previous:
            space = self.previous.font.measureText(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.height = linespace(self.font)

    def paint(self, display_list, zoom):
        color = self.node.style["color"]
        display_list.append(
            DrawText(self.x, self.y, self.word, self.font, color))

    def rect(self):
        return skia.Rect.MakeLTRB(
            self.x, self.y, self.x + self.width,
            self.y + self.height)
    
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

    def layout(self, zoom):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        size = \
            device_px(float(self.node.style["font-size"][:-2]), zoom)
        self.font = get_font(size, weight, style)

        self.width = device_px(INPUT_WIDTH_PX, zoom)
        self.height = linespace(self.font)

        if self.previous:
            space = self.previous.font.measureText(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

    def paint(self, display_list, zoom):
        cmds = []

        rect = skia.Rect.MakeLTRB(
            self.x, self.y, self.x + self.width,
            self.y + self.height)

        bgcolor = self.node.style.get("background-color",
                                 "transparent")
        if bgcolor != "transparent":
            radius = device_px(
                float(self.node.style.get("border-radius", "0px")[:-2]),
                zoom)
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

        if self.node.is_focused and self.node.tag == "input":
            cx = rect.left() + self.font.measureText(text)
            cmds.append(DrawLine(cx, rect.top(), cx, rect.bottom()))

        cmds = paint_visual_effects(self.node, cmds, rect)
        paint_outline(self.node, cmds, rect, zoom)
        display_list.extend(cmds)

    def __repr__(self):
        return "InputLayout(x={}, y={}, width={}, height={})".format(
            self.x, self.y, self.width, self.height)

def is_focusable(node):
    if get_tabindex(node) <= 0:
        return False
    elif "tabindex" in node.attributes:
        return True
    else:
        return node.tag in ["input", "button", "a"]
    
def announce_text(node, role):
    text = ""
    if role == "StaticText":
        text = node.text
    elif role == "focusable text":
        text = "focusable text: " + node.text
    elif role == "textbox":
        if "value" in node.attributes:
            value = node.attributes["value"]
        elif node.tag != "input" and node.children and \
            isinstance(node.children[0], Text):
            value = node.children[0].text
        else:
            value = ""
        text = "Input box: " + value
    elif role == "button":
        text = "Button"
    elif role == "link":
        text = "Link"
    elif role == "alert":
        text = "Alert"
    if is_focused(node):
        text += " is focused"
    return text

class AccessibilityNode:
    def __init__(self, node):
        self.node = node
        self.children = []
        self.text = ""

        if node.layout_object:
            self.bounds = absolute_bounds_for_obj(node.layout_object)
        else:
            self.bounds = None

        if isinstance(node, Text):
            if is_focusable(node.parent):
                self.role = "focusable text"
            else:
                self.role = "StaticText"
        else:
            if "role" in node.attributes:
                self.role = node.attributes["role"]
            elif node.tag == "a":
                self.role = "link"
            elif node.tag == "input":
                self.role = "textbox"
            elif node.tag == "button":
                self.role = "button"
            elif node.tag == "html":
                self.role = "document"
            elif is_focusable(node):
                self.role = "focusable"
            else:
                self.role = "none"

    def build(self):
        for child_node in self.node.children:
            self.build_internal(child_node)

        if self.role == "StaticText":
            self.text = self.node.text
        elif self.role == "focusable text":
            self.text = "Focusable text: " + self.node.text
        elif self.role == "focusable":
            self.text = "Focusable"
        elif self.role == "textbox":
            if "value" in self.node.attributes:
                value = self.node.attributes["value"]
            elif self.node.tag != "input" and self.node.children and \
                 isinstance(self.node.children[0], Text):
                value = self.node.children[0].text
            else:
                value = ""
            self.text = "Input box: " + value
        elif self.role == "button":
            self.text = "Button"
        elif self.role == "link":
            self.text = "Link"
        elif self.role == "alert":
            self.text = "Alert"
        elif self.role == "document":
            self.text = "Document"

        if is_focused(self.node):
            self.text += " is focused"

    def build_internal(self, child_node):
        child = AccessibilityNode(child_node)
        if child.role != "none":
            self.children.append(child)
            child.build()
        else:
            for grandchild_node in child_node.children:
                self.build_internal(grandchild_node)

    def intersects(self, x, y):
        if self.bounds:
            return skia.Rect.Intersects(self.bounds,
                skia.Rect.MakeXYWH(x, y, 1, 1))
        return False

    def hit_test(self, x, y):
        nodes = [node for node in tree_to_list(self, [])
            if node.intersects(x, y)]
        if nodes:
            return nodes[-1]

    def __repr__(self):
        return "AccessibilityNode(node={} role={} text={}".format(
            str(self.node), self.role, self.text)

SPEECH_FILE = "/tmp/speech-fragment.mp3"

def speak_text(text):
    print("SPEAK:", text)
    tts = gtts.gTTS(text)
    tts.save(SPEECH_FILE)
    playsound.playsound(SPEECH_FILE)
    os.remove(SPEECH_FILE)
    
class PseudoclassSelector:
    def __init__(self, pseudoclass, base):
        self.pseudoclass = pseudoclass
        self.base = base
        self.priority = self.base.priority

    def matches(self, node):
        if not self.base.matches(node):
            return False
        if self.pseudoclass == "focus":
            return is_focused(node)
        else:
            return False

    def __repr__(self):
        return "PseudoclassSelector({}, {})".format(self.pseudoclass, self.base)

class CSSParser:
    def __init__(self, s, internal=False):
        self.s = s
        self.i = 0
        self.is_internal = internal

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
            if cur == "(":
                in_parens = True
            if cur.isalnum() or cur in ",/#-.%()\"'" \
                or (in_quote and cur == ':'):
                self.i += 1
            else:
                break
        assert self.i > start
        return self.s[start:self.i]

    def until_char(self, chars):
        start = self.i
        while self.i < len(self.s) and self.s[self.i] not in chars:
            self.i += 1
        return self.s[start:self.i]

    def pair(self, until):
        prop = self.word()
        self.whitespace()
        self.literal(":")
        self.whitespace()
        val = self.until_char(until)
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
                prop, val = self.pair([";", "}"])
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

    def simple_selector(self):
        out = TagSelector(self.word().lower())
        if self.i < len(self.s) and self.s[self.i] == ":":
            self.literal(":")
            pseudoclass = self.word().lower()
            out = PseudoclassSelector(pseudoclass, out)
        return out

    def selector(self):
        out = self.simple_selector()
        self.whitespace()
        while self.i < len(self.s) and self.s[self.i] != "{":
            descendant = self.simple_selector()
            out = DescendantSelector(out, descendant)
            self.whitespace()
        return out

    def media_query(self):
        self.literal("@")
        assert self.word() == "media"
        self.whitespace()
        self.literal("(")
        (prop, val) = self.pair(")")
        self.whitespace()
        self.literal(")")
        return prop, val

    def parse(self):
        rules = []
        media = None
        self.whitespace()
        while self.i < len(self.s):
            try:
                if self.s[self.i] == "@" and not media:
                    prop, val = self.media_query()
                    if prop == "prefers-color-scheme" and \
                        val in ["dark", "light"]:
                        media = val
                    self.whitespace()
                    self.literal("{")
                    self.whitespace()
                elif self.s[self.i] == "}" and media:
                    self.literal("}")
                    media = None
                    self.whitespace()
                else:
                    selector = self.selector()
                    self.literal("{")
                    self.whitespace()
                    body = self.body()
                    self.literal("}")
                    self.whitespace()
                    rules.append((media, selector, body))
            except AssertionError:
                why = self.ignore_until(["}"])
                if why == "}":
                    self.literal("}")
                    self.whitespace()
                else:
                    break
        return rules

class JSContext:
    def __init__(self, tab):
        self.tab = tab

        self.interp = dukpy.JSInterpreter()
        self.interp.export_function("log", print)
        self.interp.export_function("querySelectorAll",
            self.querySelectorAll)
        self.interp.export_function("getAttribute",
            self.getAttribute)
        self.interp.export_function("setAttribute",
            self.setAttribute)
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
        attr = elt.attributes.get(attr, None)
        return attr if attr else ""

    def setAttribute(self, handle, attr, value):
        elt = self.handle_to_node[handle]
        elt.attributes[attr] = value
        
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

class CommitData:
    def __init__(self, url, scroll, height, display_list,
                 composited_updates, accessibility_tree, focus):
        self.url = url
        self.scroll = scroll
        self.height = height
        self.display_list = display_list
        self.composited_updates = composited_updates
        self.accessibility_tree = accessibility_tree
        self.focus = focus

class Tab:
    def __init__(self, browser):
        self.history = []
        self.focus = None
        self.needs_focus_scroll = False
        self.url = None
        self.scroll = 0
        self.scroll_changed_in_tab = False
        self.needs_raf_callbacks = False
        self.needs_style = False
        self.needs_layout = False
        self.needs_accessibility = False
        self.needs_paint = False
        self.document = None
        self.dark_mode = browser.dark_mode

        self.accessibility_tree = None

        self.browser = browser
        if wbetools.USE_BROWSER_THREAD:
            self.task_runner = TaskRunner(self)
        else:
            self.task_runner = SingleThreadedTaskRunner(self)
        self.task_runner.start()

        self.measure_render = MeasureTime("render")
        self.composited_updates = []
        self.zoom = 1.0

        with open("browser14.css") as f:
            self.default_style_sheet = \
                CSSParser(f.read(), internal=True).parse()

    def allowed_request(self, url):
        return self.allowed_origins == None or \
            url_origin(url) in self.allowed_origins

    def script_run_wrapper(self, script, script_text):
        return Task(self.js.run, script, script_text)

    def load(self, url, body=None):
        self.focus_element(None)
        self.zoom = 1
        self.scroll = 0
        self.scroll_changed_in_tab = True
        self.task_runner.clear_pending_tasks()
        headers, body = request(url, self.url, payload=body)
        self.url = url
        self.accessibility_tree = None
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
        clamped_scroll = clamp_scroll(self.scroll, document_height)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_tab = True
        self.scroll = clamped_scroll

        if self.needs_focus_scroll and self.focus:
            self.scroll_to(self.focus)
        self.needs_focus_scroll = False

        scroll = None
        if self.scroll_changed_in_tab:
            scroll = self.scroll

        composited_updates = {}
        if not needs_composite:
            for node in self.composited_updates:
                composited_updates[node] = node.save_layer
        self.composited_updates.clear()

        commit_data = CommitData(
            url=self.url,
            scroll=scroll,
            height=document_height,
            display_list=self.display_list,
            composited_updates=composited_updates,
            accessibility_tree=self.accessibility_tree,
            focus=self.focus
        )
        self.display_list = None
        self.scroll_changed_in_tab = False
        self.accessibility_tree = None

        self.browser.commit(self, commit_data)

    def render(self):
        self.measure_render.start()

        if self.needs_style:
            if self.dark_mode:
                INHERITED_PROPERTIES["color"] = "white"
            else:
                INHERITED_PROPERTIES["color"] = "black"
            style(self.nodes,
                sorted(self.rules, key=cascade_priority), self)
            self.needs_layout = True
            self.needs_style = False

        if self.needs_layout:
            self.document = DocumentLayout(self.nodes)
            self.document.layout(self.zoom)
            self.needs_accessibility = True
            self.needs_paint = True
            self.needs_layout = False

        if self.needs_accessibility:
            self.accessibility_tree = AccessibilityNode(self.nodes)
            self.accessibility_tree.build()
            self.needs_accessibility = False
            self.needs_paint = True

        if self.needs_paint:
            self.display_list = []

            self.document.paint(self.display_list, self.zoom)
            self.needs_paint = False

        self.measure_render.stop()

    def focus_element(self, node):
        if node and node != self.focus:
            self.needs_focus_scroll = True
        if self.focus:
            self.focus.is_focused = False
        self.focus = node
        if node:
            node.is_focused = True
        self.set_needs_render()

    def activate_element(self, elt):
        if elt.tag == "input":
            elt.attributes["value"] = ""
            self.set_needs_render()
        elif elt.tag == "a" and "href" in elt.attributes:
            url = resolve_url(elt.attributes["href"], self.url)
            self.load(url)
        elif elt.tag == "button":
            while elt:
                if elt.tag == "form" and "action" in elt.attributes:
                    self.submit_form(elt)
                    return
                elt = elt.parent

    def scroll_to(self, elt):
        assert not (self.needs_style or self.needs_layout)
        objs = [
            obj for obj in tree_to_list(self.document, [])
            if obj.node == self.focus
        ]
        if not objs: return
        obj = objs[0]

        content_height = HEIGHT - CHROME_PX
        if self.scroll < obj.y < self.scroll + content_height:
            return

        document_height = math.ceil(self.document.height)
        new_scroll = obj.y - SCROLL_STEP
        self.scroll = clamp_scroll(new_scroll, document_height)
        self.scroll_changed_in_tab = True

    def click(self, x, y):
        self.render()
        self.focus_element(None)
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
            elif is_focusable(elt):
                self.focus_element(elt)
                self.activate_element(elt)
                self.set_needs_render()
                return
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
        if self.focus and self.focus.tag == "input":
            if not "value" in self.focus.attributes:
                self.activate_element(self.focus)
            if self.js.dispatch_event("keydown", self.focus): return
            self.focus.attributes["value"] += char
            self.set_needs_render()

    def enter(self):
        if not self.focus: return
        if self.js.dispatch_event("click", self.focus): return
        self.activate_element(self.focus)

    def advance_tab(self):
        focusable_nodes = [node
            for node in tree_to_list(self.nodes, [])
            if isinstance(node, Element) and is_focusable(node)                          
            and get_tabindex(node) >= 0]
        focusable_nodes.sort(key=get_tabindex)

        if self.focus in focusable_nodes:
            idx = focusable_nodes.index(self.focus) + 1
        else:
            idx = 0

        if idx < len(focusable_nodes):
            self.focus_element(focusable_nodes[idx])
        else:
            self.focus_element(None)
            self.browser.focus_addressbar()
        self.set_needs_render()

    def zoom_by(self, increment):
        if increment > 0:
            self.zoom *= 1.1
        else:
            self.zoom *= 1/1.1
        self.set_needs_render()

    def reset_zoom(self):
        self.zoom = 1
        self.set_needs_render()

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.set_needs_render()

def draw_line(canvas, x1, y1, x2, y2, color):
    sk_color = parse_color(color)
    path = skia.Path().moveTo(x1, y1).lineTo(x2, y2)
    paint = skia.Paint(Color=sk_color)
    paint.setStyle(skia.Paint.kStroke_Style)
    paint.setStrokeWidth(1)
    canvas.drawPath(path, paint)

class Browser:
    def __init__(self):
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
                GL.glGetString(GL.GL_VENDOR),
                GL.glGetString(GL.GL_RENDERER)))

            self.skia_context = skia.GrDirectContext.MakeGL()

            self.root_surface = \
                skia.Surface.MakeFromBackendRenderTarget(
                self.skia_context,
                skia.GrBackendRenderTarget(
                    WIDTH, HEIGHT, 0, 0, 
                    skia.GrGLFramebufferInfo(0, GL.GL_RGBA8)),
                    skia.kBottomLeft_GrSurfaceOrigin,
                    skia.kRGBA_8888_ColorType,
                    skia.ColorSpace.MakeSRGB())
            assert self.root_surface is not None

            self.chrome_surface = skia.Surface.MakeRenderTarget(
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
        self.needs_composite = False
        self.needs_raster = False
        self.needs_draw = False
        self.needs_accessibility = False

        self.active_tab_height = 0
        self.active_tab_display_list = None

        self.composited_updates = {}
        self.composited_layers = []
        self.draw_list = []
        self.muted = True
        self.dark_mode = False

        self.accessibility_is_on = False
        self.has_spoken_document = False
        self.pending_hover = None
        self.hovered_a11y_node = None
        self.focus_a11y_node = None
        self.needs_speak_hovered_node = False
        self.tab_focus = None
        self.last_tab_focus = None
        self.active_alerts = []
        self.spoken_alerts = []

    def render(self):
        assert not wbetools.USE_BROWSER_THREAD
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
            self.animation_timer = None
            self.composited_updates = data.composited_updates
            self.accessibility_tree = data.accessibility_tree
            if self.accessibility_tree:
                self.set_needs_accessibility()
            self.tab_focus = data.focus
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
        self.needs_animation_frame = True

    def set_needs_composite(self):
        self.needs_composite = True
        self.needs_raster = True
        self.needs_draw = True

    def set_needs_accessibility(self):
        if not self.accessibility_is_on:
            return
        self.needs_accessibility = True
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
            if not cmd.needs_compositing and \
                (not cmd.parent or \
                 cmd.parent.needs_compositing)
        ]
        for cmd in non_composited_commands:
            for layer in reversed(self.composited_layers):
                if layer.can_merge(cmd):
                    layer.add(cmd)
                    break
                elif skia.Rect.Intersects(
                    layer.absolute_bounds(),
                    absolute_bounds(cmd)):
                    layer = CompositedLayer(self.skia_context, cmd)
                    self.composited_layers.append(layer)
                    break
            else:
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

        if self.pending_hover:
            (x, y) = self.pending_hover
            y += self.scroll
            a11y_node = self.accessibility_tree.hit_test(x, y)
            if a11y_node:
                if not self.hovered_a11y_node or \
                    a11y_node.node != self.hovered_a11y_node.node:
                    self.needs_speak_hovered_node = True
                self.hovered_a11y_node = a11y_node
        self.pending_hover = None

        if self.hovered_a11y_node:
            self.draw_list.append(DrawOutline(
                self.hovered_a11y_node.bounds,
                "white" if self.dark_mode else "black", 2))

    def update_accessibility(self):
        if not self.accessibility_tree: return

        if not self.has_spoken_document:
            self.speak_document()
            self.has_spoken_document = True

        self.active_alerts = [
            node for node in tree_to_list(
                self.accessibility_tree, [])
            if node.role == "alert"
        ]

        for alert in self.active_alerts:
            if alert not in self.spoken_alerts:
                self.speak_node(alert, "New alert")
                self.spoken_alerts.append(alert)

        new_spoken_alerts = []
        for old_node in self.spoken_alerts:
            new_nodes = [
                node for node in tree_to_list(
                    self.accessibility_tree, [])
                if node.node == old_node.node
                and node.role == "alert"
            ]
            if new_nodes:
                new_spoken_alerts.append(new_nodes[0])
        self.spoken_alerts = new_spoken_alerts

        if self.tab_focus and \
            self.tab_focus != self.last_tab_focus:
            nodes = [node for node in tree_to_list(
                self.accessibility_tree, [])
                        if node.node == self.tab_focus]
            if nodes:
                self.focus_a11y_node = nodes[0]
                self.speak_node(
                    self.focus_a11y_node, "element focused ")
            self.last_tab_focus = self.tab_focus

        if self.needs_speak_hovered_node:
            self.speak_node(self.hovered_a11y_node, "Hit test ")
        self.needs_speak_hovered_node = False

    def composite_raster_and_draw(self):
        self.lock.acquire(blocking=True)
        if not self.needs_composite and \
            len(self.composited_updates) == 0 \
            and not self.needs_raster and not self.needs_draw and not \
            self.needs_accessibility:
            self.lock.release()
            return
        self.measure_composite_raster_and_draw.start()
        start_time = time.time()
        if self.needs_composite:
            self.composite()
        if self.needs_raster:
            self.raster_chrome()
            self.raster_tab()

        if self.needs_draw:
            self.paint_draw_list()
            self.draw()

        self.measure_composite_raster_and_draw.stop()

        if self.needs_accessibility:
            self.update_accessibility()

        self.needs_composite = False
        self.needs_raster = False
        self.needs_draw = False
        self.needs_accessibility = False

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
        self.lock.release()

    def handle_tab(self):
        self.focus = "content"
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.advance_tab)
        active_tab.task_runner.schedule_task(task)

    def focus_addressbar(self):
        self.lock.acquire(blocking=True)
        self.focus = "address bar"
        self.address_bar = ""
        text = "Address bar focused"
        if self.accessibility_is_on:
            print(text)
            if not self.muted:
                speak_text(text)
        self.set_needs_raster()
        self.lock.release()

    def clear_data(self):
        self.scroll = 0
        self.url = None
        self.display_list = []
        self.accessibility_tree = None
        self.composited_layers = []

    def set_active_tab(self, index):
        self.active_tab = index
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.set_needs_paint)
        active_tab.task_runner.schedule_task(task)

        self.clear_data()
        self.needs_animation_frame = True

    def go_back(self):
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.go_back)
        active_tab.task_runner.schedule_task(task)
        self.clear_data()

    def cycle_tabs(self):
        self.lock.acquire(blocking=True)
        new_active_tab = (self.active_tab + 1) % len(self.tabs)
        self.set_active_tab(new_active_tab)
        self.lock.release()

    def toggle_accessibility(self):
        self.lock.acquire(blocking=True)
        self.accessibility_is_on = not self.accessibility_is_on
        self.set_needs_accessibility()
        self.lock.release()

    def speak_node(self, node, text):
        text += node.text
        if text and node.children and \
            node.children[0].role == "StaticText":
            text += " " + \
            node.children[0].text

        if text:
            if not self.is_muted():
                speak_text(text)
            else:
                print(text)

    def speak_document(self):
        text = "Here are the document contents: "
        tree_list = tree_to_list(self.accessibility_tree, [])
        for accessibility_node in tree_list:
            new_text = accessibility_node.text
            if new_text:
                text += "\n"  + new_text

        if not self.is_muted():
            speak_text(text)
        else:
            print(text)

    def toggle_mute(self):
        self.lock.acquire(blocking=True)
        self.muted = not self.muted
        self.lock.release()

    def is_muted(self):
        return self.muted

    def toggle_dark_mode(self):
        self.lock.acquire(blocking=True)
        self.dark_mode = not self.dark_mode
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.toggle_dark_mode)
        active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def handle_click(self, e):
        self.lock.acquire(blocking=True)
        if e.y < CHROME_PX:
            self.focus = None
            if 40 <= e.x < 40 + 80 * len(self.tabs) and 0 <= e.y < 40:
                self.set_active_tab(int((e.x - 40) / 80))
            elif 10 <= e.x < 30 and 10 <= e.y < 30:
                self.load_internal("https://browser.engineering/")
            elif 10 <= e.x < 35 and 50 <= e.y < 90:
                self.go_back()
            elif 50 <= e.x < WIDTH - 10 and 50 <= e.y < 90:
                self.focus = "address bar"
                self.address_bar = ""
            self.set_needs_raster()
        else:
            self.focus = "content"
            active_tab = self.tabs[self.active_tab]
            task = Task(active_tab.click, e.x, e.y - CHROME_PX)
            active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def handle_hover(self, event):
        if not self.accessibility_is_on or \
            not self.accessibility_tree:
            return
        self.pending_hover = (event.x, event.y - CHROME_PX)
        self.set_needs_accessibility()

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
            self.schedule_load(active_tab, self.address_bar)
            self.url = self.address_bar
            self.focus = None
            self.set_needs_raster()
        elif self.focus == "content":
            active_tab = self.tabs[self.active_tab]
            task = Task(active_tab.enter)
            active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def increment_zoom(self, increment):
        self.lock.acquire(blocking=True)
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.zoom_by, increment)
        active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def reset_zoom(self):
        self.lock.acquire(blocking=True)
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.reset_zoom)
        active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def load(self, url):
        self.lock.acquire(blocking=True)
        self.load_internal(url)
        self.lock.release()

    def load_internal(self, url):
        new_tab = Tab(self)
        self.tabs.append(new_tab)
        self.set_active_tab(len(self.tabs) - 1)
        self.schedule_load(url)

    def raster_tab(self):
        for composited_layer in self.composited_layers:
            composited_layer.raster()

    def raster_chrome(self):
        canvas = self.chrome_surface.getCanvas()
        if self.dark_mode:
            color = "white"
            background_color = "black"
        else:
            color = "black"
            background_color = "white"
        canvas.clear(parse_color(background_color))
    
        # Draw the tabs UI:
        tabfont = skia.Font(skia.Typeface('Arial'), 20)
        for i, tab in enumerate(self.tabs):
            name = "Tab {}".format(i)
            x1, x2 = 40 + 80 * i, 120 + 80 * i
            draw_line(canvas, x1, 0, x1, 40, color)
            draw_line(canvas, x2, 0, x2, 40, color)
            draw_text(canvas, x1 + 10, 10, name, tabfont, color)
            if i == self.active_tab:
                draw_line(canvas, 0, 40, x1, 40, color)
                draw_line(canvas, x2, 40, WIDTH, 40, color)

        # Draw the plus button to add a tab:
        buttonfont = skia.Font(skia.Typeface('Arial'), 30)
        draw_rect(canvas, 10, 10, 30, 30,
            fill_color=background_color, border_color=color)
        draw_text(canvas, 11, 4, "+", buttonfont, color=color)

        # Draw the URL address bar:
        draw_rect(canvas, 40.0, 50.0, WIDTH - 10.0, 90.0,
            fill_color=background_color, border_color=color)

        if self.focus == "address bar":
            draw_text(canvas, 55, 55, self.address_bar, buttonfont,
                color=color)
            w = buttonfont.measureText(self.address_bar)
            draw_line(canvas, 55 + w, 55, 55 + w, 85, color)
        else:
            if self.url:
                draw_text(canvas, 55, 55, self.url, buttonfont,
                    color=color)

        # Draw the back button:
        draw_rect(canvas, 10, 50, 35, 90,
            fill_color=background_color, border_color=color)

        path = \
            skia.Path().moveTo(15, 70).lineTo(30, 55).lineTo(30, 85)
        paint = skia.Paint(
            Color=parse_color(color), Style=skia.Paint.kFill_Style)
        canvas.drawPath(path, paint)

    def draw(self):
        canvas = self.root_surface.getCanvas()
        if self.dark_mode:
            canvas.clear(skia.ColorBLACK)
        else:
            canvas.clear(skia.ColorWHITE)

        canvas.save()
        canvas.translate(0, CHROME_PX - self.scroll)
        for item in self.draw_list:
            item.execute(canvas)
        canvas.restore()

        chrome_rect = skia.Rect.MakeLTRB(0, 0, WIDTH, CHROME_PX)
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

    wbetools.USE_BROWSER_THREAD = not args.single_threaded
    wbetools.USE_GPU = not args.disable_gpu
    wbetools.USE_COMPOSITING = not args.disable_compositing and not args.disable_gpu
    wbetools.SHOW_COMPOSITED_LAYER_BORDERS = args.show_composited_layer_borders

    sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS)
    browser = Browser()
    browser.load(args.url)

    event = sdl2.SDL_Event()
    ctrl_down = False
    while True:
        if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == sdl2.SDL_QUIT:
                browser.handle_quit()
                sdl2.SDL_Quit()
                sys.exit()
                break
            elif event.type == sdl2.SDL_MOUSEBUTTONUP:
                browser.handle_click(event.button)
            elif event.type == sdl2.SDL_MOUSEMOTION:
                browser.handle_hover(event.motion)
            elif event.type == sdl2.SDL_KEYDOWN:
                if ctrl_down:
                    if event.key.keysym.sym == sdl2.SDLK_EQUALS:
                        browser.increment_zoom(1)
                    elif event.key.keysym.sym == sdl2.SDLK_MINUS:
                        browser.increment_zoom(-1)
                    elif event.key.keysym.sym == sdl2.SDLK_0:
                        browser.reset_zoom()
                    elif event.key.keysym.sym == sdl2.SDLK_LEFT:
                        browser.go_back()
                    elif event.key.keysym.sym == sdl2.SDLK_l:
                        browser.focus_addressbar()
                    elif event.key.keysym.sym == sdl2.SDLK_a:
                        browser.toggle_accessibility()
                    elif event.key.keysym.sym == sdl2.SDLK_d:
                        browser.toggle_dark_mode()
                    elif event.key.keysym.sym == sdl2.SDLK_m:
                        browser.toggle_mute()
                    elif event.key.keysym.sym == sdl2.SDLK_t:
                        browser.load("https://browser.engineering/")
                    elif event.key.keysym.sym == sdl2.SDLK_TAB:
                        browser.cycle_tabs()
                    elif event.key.keysym.sym == sdl2.SDLK_q:
                        browser.handle_quit()
                        sdl2.SDL_Quit()
                        sys.exit()
                        break
                elif event.key.keysym.sym == sdl2.SDLK_RETURN:
                    browser.handle_enter()
                elif event.key.keysym.sym == sdl2.SDLK_DOWN:
                    browser.handle_down()
                elif event.key.keysym.sym == sdl2.SDLK_TAB:
                    browser.handle_tab()
                elif event.key.keysym.sym == sdl2.SDLK_RCTRL or \
                    event.key.keysym.sym == sdl2.SDLK_LCTRL:
                    ctrl_down = True
            elif event.type == sdl2.SDL_KEYUP:
                if event.key.keysym.sym == sdl2.SDLK_RCTRL or \
                    event.key.keysym.sym == sdl2.SDLK_LCTRL:
                    ctrl_down = False
            elif event.type == sdl2.SDL_TEXTINPUT and not ctrl_down:
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
