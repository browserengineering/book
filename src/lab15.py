"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 15 (Supporting Embedded Content),
without exercises.
"""

import ctypes
import dukpy
import gtts
import math
import os
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
from lab4 import print_tree
from lab5 import BLOCK_ELEMENTS
from lab14 import Text, Element
from lab6 import TagSelector, DescendantSelector
from lab6 import tree_to_list, INHERITED_PROPERTIES
from lab7 import CHROME_PX
from lab8 import INPUT_WIDTH_PX
from lab9 import EVENT_DISPATCH_CODE
from lab10 import COOKIE_JAR, URL
from lab11 import FONTS, get_font, linespace, parse_blend_mode
from lab12 import MeasureTime, REFRESH_RATE_SEC
from lab12 import Task, TaskRunner, SingleThreadedTaskRunner
from lab13 import diff_styles, parse_transition, clamp_scroll, add_parent_pointers
from lab13 import absolute_bounds, absolute_bounds_for_obj
from lab13 import NumericAnimation, TranslateAnimation
from lab13 import map_translation, parse_transform, ANIMATED_PROPERTIES
from lab13 import CompositedLayer, paint_visual_effects
from lab13 import DisplayItem, DrawText, DrawCompositedLayer, SaveLayer
from lab13 import ClipRRect, Transform, DrawLine, DrawRRect, add_main_args
from lab14 import parse_color, DrawRRect, \
    is_focused, parse_outline, paint_outline, has_outline, \
    device_px, cascade_priority, style, \
    is_focusable, get_tabindex, announce_text, speak_text, \
    CSSParser, DrawOutline, main_func, Browser

@wbetools.patch(URL)
class URL:
    def request(self, top_level_url, payload=None):
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
        body = "{} {} HTTP/1.0\r\n".format(method, self.path)
        body += "Host: {}\r\n".format(self.host)
        if self.host in COOKIE_JAR:
            cookie, params = COOKIE_JAR[self.host]
            allow_cookie = True
            if top_level_url and params.get("samesite", "none") == "lax":
                if method != "GET":
                    allow_cookie = self.host == top_level_url.host
            if allow_cookie:
                body += "Cookie: {}\r\n".format(cookie)
        if payload:
            content_length = len(payload.encode("utf8"))
            body += "Content-Length: {}\r\n".format(content_length)
        body += "\r\n" + (payload or "")
        s.send(body.encode("utf8"))
    
        response = s.makefile("b")
    
        statusline = response.readline().decode("utf8")
        version, status, explanation = statusline.split(" ", 2)
        assert status == "200", "{}: {}".format(status, explanation)
    
        headers = {}
        while True:
            line = response.readline().decode("utf8")
            if line == "\r\n": break
            header, value = line.split(":", 1)
            headers[header.lower()] = value.strip()
    
        if "set-cookie" in headers:
            params = {}
            if ";" in headers["set-cookie"]:
                cookie, rest = headers["set-cookie"].split(";", 1)
                for param_pair in rest.split(";"):
                    if '=' in param_pair:
                        name, value = param_pair.strip().split("=", 1)
                        params[name.lower()] = value.lower()
            else:
                cookie = headers["set-cookie"]
            COOKIE_JAR[self.host] = (cookie, params)
    
        assert "transfer-encoding" not in headers
        assert "content-encoding" not in headers
    
        body = response.read()
        s.close()
        return headers, body

class DrawImage(DisplayItem):
    def __init__(self, image, rect, quality):
        super().__init__(rect)
        self.image = image
        if quality == "high-quality":
            self.quality = skia.FilterQuality.kHigh_FilterQuality
        elif quality == "crisp-edges":
            self.quality = skia.FilterQuality.kLow_FilterQuality
        else:
            self.quality = skia.FilterQuality.kMedium_FilterQuality

    def execute(self, canvas):
        paint = skia.Paint(FilterQuality=self.quality)
        canvas.drawImageRect(self.image, self.rect, paint)

    def __repr__(self):
        return "DrawImage(rect={})".format(
            self.rect)

class DocumentLayout:
    def __init__(self, node, frame):
        self.node = node
        self.frame = frame
        node.layout_object = self
        self.parent = None
        self.previous = None
        self.children = []

    def layout(self, width, zoom):
        self.zoom = zoom
        child = BlockLayout(self.node, self, None, self.frame)
        self.children.append(child)

        self.width = width - 2 * device_px(HSTEP, self.zoom)
        self.x = device_px(HSTEP, self.zoom)
        self.y = device_px(VSTEP, self.zoom)
        child.layout()
        self.height = child.height + 2 * device_px(VSTEP, self.zoom)

    def paint(self, display_list, dark_mode, scroll):
        cmds = []
        self.children[0].paint(cmds)
        if scroll != None and scroll != 0:
            rect = skia.Rect.MakeLTRB(
                self.x, self.y,
                self.x + self.width, self.y + self.height)
            cmds = [Transform((0, -scroll), rect, self.node, cmds)]

        display_list.extend(cmds)

    def __repr__(self):
        return "DocumentLayout()"

def font(style, zoom):
    weight = style["font-weight"]
    variant = style["font-style"]
    try:
        size = float(style["font-size"][:-2])
    except ValueError:
        size = 16
    font_size = device_px(size, zoom)
    return get_font(font_size, weight, variant)

class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        self.node = node
        node.layout_object = self
        self.parent = parent
        self.previous = previous
        self.children = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.frame = frame

    def layout(self):
        self.zoom = self.parent.zoom
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
                next = BlockLayout(child, self, previous, self.frame)
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
            elif node.tag == "img":
                self.image(node)
            elif node.tag == "iframe" and \
                 "src" in node.attributes:
                self.iframe(node)
            else:
                for child in node.children:
                    self.recurse(child)

    def new_line(self):
        self.previous_word = None
        self.cursor_x = self.x
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line)
        self.children.append(new_line)

    def add_inline_child(self, node, w, child_class, frame, word=None):
        if self.cursor_x + w > self.x + self.width:
            self.new_line()
        line = self.children[-1]
        if word:
            child = child_class(node, line, self.previous_word, word)
        else:
            child = child_class(node, line, self.previous_word, frame)
        line.children.append(child)
        self.previous_word = child
        self.cursor_x += w + font(node.style, self.zoom).measureText(" ")

    def word(self, node, word):
        node_font = font(node.style, self.zoom)
        w = node_font.measureText(word)
        self.add_inline_child(node, w, TextLayout, self.frame, word)

    def input(self, node):
        w = device_px(INPUT_WIDTH_PX, self.zoom)
        self.add_inline_child(node, w, InputLayout, self.frame) 

    def image(self, node):
        if "width" in node.attributes:
            w = device_px(int(node.attributes["width"]), self.zoom)
        else:
            w = device_px(node.image.width(), self.zoom)
        self.add_inline_child(node, w, ImageLayout, self.frame)

    def iframe(self, node):
        if "width" in self.node.attributes:
            w = device_px(int(self.node.attributes["width"]),
                self.zoom)
        else:
            w = IFRAME_WIDTH_PX + device_px(2, self.zoom)
        self.add_inline_child(node, w, IframeLayout, self.frame)

    def paint(self, display_list):
        cmds = []

        rect = skia.Rect.MakeLTRB(
            self.x, self.y, self.x + self.width,
            self.y + self.height)

        is_atomic = not isinstance(self.node, Text) and \
            (self.node.tag == "input" or self.node.tag == "button")

        if not is_atomic:
            bgcolor = self.node.style.get(
                "background-color", "transparent")
            if bgcolor != "transparent":
                radius = device_px(
                    float(self.node.style.get(
                        "border-radius", "0px")[:-2]),
                    self.zoom)
                cmds.append(DrawRRect(rect, radius, bgcolor))
 
        for child in self.children:
            child.paint(cmds)

        if not is_atomic:
            cmds = paint_visual_effects(self.node, cmds, rect)
        display_list.extend(cmds)

    def __repr__(self):
        return "BlockLayout(x={}, y={}, width={}, height={}, node={})".format(
            self.x, self.x, self.width, self.height, self.node)

class EmbedLayout:
    def __init__(self, node, parent, previous, frame):
        self.node = node
        self.frame = frame
        node.layout_object = self
        self.children = []
        self.parent = parent
        self.previous = previous
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.font = None

    def get_ascent(self, font_multiplier=1.0):
        return -self.height

    def get_descent(self, font_multiplier=1.0):
        return 0

    def layout(self):
        self.zoom = self.parent.zoom
        self.font = font(self.node.style, self.zoom)
        if self.previous:
            space = self.previous.font.measureText(" ")
            self.x = \
                self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

class InputLayout(EmbedLayout):
    def __init__(self, node, parent, previous, frame):
        super().__init__(node, parent, previous, frame)

    def layout(self):
        super().layout()

        self.width = device_px(INPUT_WIDTH_PX, self.zoom)
        self.height = linespace(self.font)

    def paint(self, display_list):
        cmds = []

        rect = skia.Rect.MakeLTRB(
            self.x, self.y, self.x + self.width,
            self.y + self.height)

        bgcolor = self.node.style.get("background-color",
                                 "transparent")
        if bgcolor != "transparent":
            radius = device_px(
                float(self.node.style.get("border-radius", "0px")[:-2]),
                self.zoom)
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
            cx = self.x + self.font.measureText(text)
            cmds.append(DrawLine(cx, self.y, cx, self.y + self.height, color, 1))

        cmds = paint_visual_effects(self.node, cmds, rect)
        paint_outline(self.node, cmds, rect, self.zoom)
        display_list.extend(cmds)

    def __repr__(self):
        return "InputLayout(x={}, y={}, width={}, height={})".format(
            self.x, self.y, self.width, self.height)

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
        self.zoom = self.parent.zoom
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

        max_ascent = max([-child.get_ascent(1.25) 
                          for child in self.children])
        baseline = self.y + max_ascent
        for child in self.children:
            child.y = baseline + child.get_ascent()
        max_descent = max([child.get_descent(1.25)
                           for child in self.children])
        self.height = max_ascent + max_descent

    def paint(self, display_list):
        outline_rect = skia.Rect.MakeEmpty()
        outline_node = None
        for child in self.children:
            node = child.node
            if isinstance(node, Text) and has_outline(node.parent):
                outline_node = node.parent
                outline_rect.join(child.rect())
            child.paint(display_list)

        if outline_node:
            paint_outline(outline_node, display_list, outline_rect, self.zoom)

    def role(self):
        return "none"

    def __repr__(self):
        return "LineLayout(x={}, y={}, width={}, height={}, node={})".format(
            self.x, self.y, self.width, self.height, self.node)

class TextLayout:
    def __init__(self, node, parent, previous, word):
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

    def get_ascent(self, font_multiplier=1.0):
        return self.font.getMetrics().fAscent * font_multiplier

    def get_descent(self, font_multiplier=1.0):
        return self.font.getMetrics().fDescent * font_multiplier

    def layout(self):
        self.zoom = self.parent.zoom
        self.font = font(self.node.style, self.zoom)

        # Do not set self.y!!!
        self.width = self.font.measureText(self.word)

        if self.previous:
            space = self.previous.font.measureText(" ")
            self.x =self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.height = linespace(self.font)

    def paint(self, display_list):
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

def filter_quality(node):
    attr = node.style.get("image-rendering", "auto")
    if attr == "high-quality":
        return skia.FilterQuality.kHigh_FilterQuality
    elif attr == "crisp-edges":
        return skia.FilterQuality.kLow_FilterQuality
    else:
        return skia.FilterQuality.kMedium_FilterQuality

class ImageLayout(EmbedLayout):
    def __init__(self, node, parent, previous, frame):
        super().__init__(node, parent, previous, frame)

    def layout(self):
        super().layout()

        width_attr = self.node.attributes.get("width")
        height_attr = self.node.attributes.get("height")
        image_width = self.node.image.width()
        image_height = self.node.image.height()
        aspect_ratio = image_width / image_height

        if width_attr and height_attr:
            self.width = device_px(int(width_attr), self.zoom)
            self.img_height = device_px(int(height_attr), self.zoom)
        elif width_attr:
            self.width = device_px(int(width_attr), self.zoom)
            self.img_height = self.width / aspect_ratio
        elif height_attr:
            self.img_height = device_px(int(height_attr), self.zoom)
            self.width = self.img_height * aspect_ratio
        else:
            self.width = device_px(image_width, self.zoom)
            self.img_height = device_px(image_height, self.zoom)

        self.height = max(self.img_height, linespace(self.font))

    def paint(self, display_list):
        cmds = []
        rect = skia.Rect.MakeLTRB(
            self.x, self.y + self.height - self.img_height,
            self.x + self.width, self.y + self.height)
        quality = self.node.style.get("image-rendering", "auto")
        cmds.append(DrawImage(self.node.image, rect, quality))
        display_list.extend(cmds)

    def __repr__(self):
        return ("ImageLayout(src={}, x={}, y={}, width={}," +
            "height={})").format(self.node.attributes["src"],
                self.x, self.y, self.width, self.height)

IFRAME_WIDTH_PX = 300
IFRAME_HEIGHT_PX = 150

class IframeLayout(EmbedLayout):
    def __init__(self, node, parent, previous, parent_frame):
        super().__init__(node, parent, previous, parent_frame)

    def layout(self):
        super().layout()

        width_attr = self.node.attributes.get("width")
        height_attr = self.node.attributes.get("height")

        if width_attr:
            self.width = device_px(int(width_attr) + 2, self.zoom)
        else:
            self.width = device_px(IFRAME_WIDTH_PX + 2, self.zoom)

        if height_attr:
            self.height = device_px(int(height_attr) + 2, self.zoom)
        else:
            self.height = device_px(IFRAME_HEIGHT_PX + 2, self.zoom)

        if self.node.frame:
            self.node.frame.frame_height = \
                self.height - device_px(2, self.zoom)
            self.node.frame.frame_width = \
                self.width - device_px(2, self.zoom)

    def paint(self, display_list):
        frame_cmds = []

        rect = skia.Rect.MakeLTRB(
            self.x, self.y,
            self.x + self.width, self.y + self.height)
        bgcolor = self.node.style.get("background-color",
                                 "transparent")
        if bgcolor != "transparent":
            radius = device_px(float(
                self.node.style.get("border-radius", "0px")[:-2]),
                self.zoom)
            frame_cmds.append(DrawRRect(rect, radius, bgcolor))

        if self.node.frame:
            self.node.frame.paint(frame_cmds)

        diff = device_px(1, self.zoom)
        offset = (self.x + diff, self.y + diff)
        cmds = [Transform(offset, rect, self.node, frame_cmds)]
        inner_rect = skia.Rect.MakeLTRB(
            self.x + diff, self.y + diff,
            self.x + self.width - diff, self.y + self.height - diff)
        cmds = paint_visual_effects(self.node, cmds, inner_rect)
        paint_outline(self.node, cmds, rect, self.zoom)
        display_list.extend(cmds)

    def __repr__(self):
        return "IframeLayout(src={}, x={}, y={}, width={}, height={})".format(
            self.node.attributes["src"], self.x, self.y, self.width, self.height)

class AttributeParser:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def whitespace(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    def literal(self, literal):
        if self.i < len(self.s) and self.s[self.i] == literal:
            self.i += 1
            return True
        return False

    def word(self, allow_quotes=False):
        start = self.i
        in_quote = False
        quoted = False
        while self.i < len(self.s):
            cur = self.s[self.i]
            if not cur.isspace() and cur not in "=\"\'":
                self.i += 1
            elif allow_quotes and cur in "\"\'":
                in_quote = not in_quote
                quoted = True
                self.i += 1
            elif in_quote and (cur.isspace() or cur == "="):
                self.i += 1
            else:
                break
        assert self.i > start
        if quoted:
            return self.s[start+1:self.i-1]
        return self.s[start:self.i]

    def parse(self):
        attributes = {}
        tag = None

        tag = self.word()
        while self.i < len(self.s):
            self.whitespace()
            key = self.word()
            if self.literal("="):
                value = self.word(allow_quotes=True) 
                attributes[key.lower()] = value
            else:
                attributes[key.lower()] = ""
        return (tag, attributes)

class HTMLParser:
    def __init__(self, body):
        self.body = body
        self.unfinished = []

    def parse(self):
        text = ""
        in_tag = False
        for c in self.body:
            if c == "<":
                in_tag = True
                if text: self.add_text(text)
                text = ""
            elif c == ">":
                in_tag = False
                self.add_tag(text)
                text = ""
            else:
                text += c
        if not in_tag and text:
            self.add_text(text)
        return self.finish()

    def get_attributes(self, text):
        (tag, attributes) = AttributeParser(text).parse()
        return tag, attributes

    def add_text(self, text):
        if text.isspace(): return
        self.implicit_tags(None)
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    SELF_CLOSING_TAGS = [
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    ]

    def add_tag(self, tag):
        tag, attributes = self.get_attributes(tag)
        if tag.startswith("!"): return
        self.implicit_tags(tag)

        if tag.startswith("/"):
            if len(self.unfinished) == 1: return
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        elif tag in self.SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            parent.children.append(node)
        else:
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, attributes, parent)
            self.unfinished.append(node)

    HEAD_TAGS = [
        "base", "basefont", "bgsound", "noscript",
        "link", "meta", "title", "style", "script",
    ]

    def implicit_tags(self, tag):
        while True:
            open_tags = [node.tag for node in self.unfinished]
            if open_tags == [] and tag != "html":
                self.add_tag("html")
            elif open_tags == ["html"] \
                 and tag not in ["head", "body", "/html"]:
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            elif open_tags == ["html", "head"] and \
                 tag not in ["/head"] + self.HEAD_TAGS:
                self.add_tag("/head")
            else:
                break

    def finish(self):
        if len(self.unfinished) == 0:
            self.add_tag("html")
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()


INTERNAL_ACCESSIBILITY_HOVER = "-internal-accessibility-hover"

EVENT_DISPATCH_CODE = \
    "new window.Node(dukpy.handle)" + \
    ".dispatchEvent(new window.Event(dukpy.type))"

POST_MESSAGE_DISPATCH_CODE = \
    "window.dispatchEvent(new window.MessageEvent(dukpy.data))"

SETTIMEOUT_CODE = "window.__runSetTimeout(dukpy.handle)"
XHR_ONLOAD_CODE = "window.__runXHROnload(dukpy.out, dukpy.handle)"

class JSContext:
    def __init__(self, tab, url_origin):
        self.tab = tab
        self.url_origin = url_origin

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
        self.interp.export_function("parent", self.parent)
        self.interp.export_function("postMessage", self.postMessage)

        self.node_to_handle = {}
        self.handle_to_node = {}

        self.interp.evaljs("function Window(id) { this._id = id };")
        self.interp.evaljs("WINDOWS = {}")

    def throw_if_cross_origin(self, frame):
        if frame.url.origin() != self.url_origin:
            raise Exception(
                "Cross-origin access disallowed from script")

    def add_window(self, frame):
        code = "var window_{} = new Window({});".format(
            frame.window_id, frame.window_id)
        self.interp.evaljs(code)

        with open("runtime15.js") as f:
            self.interp.evaljs(self.wrap(f.read(), frame.window_id))

        self.interp.evaljs("WINDOWS[{}] = window_{};".format(
            frame.window_id, frame.window_id))

    def wrap(self, script, window_id):
        return "window = window_{}; {}".format(window_id, script)

    def run(self, script, code, window_id):
        try:
            code = self.wrap(code, window_id)
            self.interp.evaljs(code)
        except dukpy.JSRuntimeError as e:
            print("Script", script, "crashed", e)

    def dispatch_event(self, type, elt, window_id):
        handle = self.node_to_handle.get(elt, -1)
        code = self.wrap(EVENT_DISPATCH_CODE, window_id)
        do_default = self.interp.evaljs(code,
            type=type, handle=handle)
        return not do_default

    def get_handle(self, elt):
        if elt not in self.node_to_handle:
            handle = len(self.node_to_handle)
            self.node_to_handle[elt] = handle
            self.handle_to_node[handle] = elt
        else:
            handle = self.node_to_handle[elt]
        return handle

    def querySelectorAll(self, selector_text, window_id):
        frame = self.tab.window_id_to_frame[window_id]
        self.throw_if_cross_origin(frame)
        selector = CSSParser(selector_text).selector()
        nodes = [node for node
                in tree_to_list(frame.nodes, [])
                 if selector.matches(node)]
        return [self.get_handle(node) for node in nodes]

    def getAttribute(self, handle, attr):
        elt = self.handle_to_node[handle]
        return elt.attributes.get(attr, None)

    def setAttribute(self, handle, attr, value, window_id):
        frame = self.tab.window_id_to_frame[window_id]        
        self.throw_if_cross_origin(frame)
        elt = self.handle_to_node[handle]
        elt.attributes[attr] = value
        self.tab.set_needs_render_all_frames()

    def parent(self, window_id):
        parent_frame = \
            self.tab.window_id_to_frame[window_id].parent_frame
        if not parent_frame:
            return None
        return parent_frame.window_id

    def dispatch_post_message(self, message, window_id):
        self.interp.evaljs(
            self.wrap(POST_MESSAGE_DISPATCH_CODE, window_id),
            data=message)

    def postMessage(self, target_window_id, message, origin):
        task = Task(self.tab.post_message,
            message, target_window_id)
        self.tab.task_runner.schedule_task(task)

    def innerHTML_set(self, handle, s, window_id):
        frame = self.tab.window_id_to_frame[window_id]        
        self.throw_if_cross_origin(frame)
        doc = HTMLParser(
            "<html><body>" + s + "</body></html>").parse()
        new_nodes = doc.children[0].children
        elt = self.handle_to_node[handle]
        elt.children = new_nodes
        for child in elt.children:
            child.parent = elt
        frame.set_needs_render()

    def style_set(self, handle, s, window_id):
        frame = self.tab.window_id_to_frame[window_id]        
        self.throw_if_cross_origin(frame)
        elt = self.handle_to_node[handle]
        elt.attributes["style"] = s;
        frame.set_needs_render()

    def dispatch_settimeout(self, handle, window_id):
        self.interp.evaljs(
            self.wrap(SETTIMEOUT_CODE, window_id), handle=handle)

    def setTimeout(self, handle, time, window_id):
        def run_callback():
            task = Task(self.dispatch_settimeout, handle, window_id)
            self.tab.task_runner.schedule_task(task)
        threading.Timer(time / 1000.0, run_callback).start()

    def dispatch_xhr_onload(self, out, handle, window_id):
        code = self.wrap(XHR_ONLOAD_CODE, window_id)
        do_default = self.interp.evaljs(code, out=out, handle=handle)

    def XMLHttpRequest_send(
        self, method, url, body, isasync, handle, window_id):
        frame = self.tab.window_id_to_frame[window_id]        
        full_url = frame.url.resolve(url)
        if not frame.allowed_request(full_url):
            raise Exception("Cross-origin XHR blocked by CSP")
        if full_url.origin() != frame.url.origin():
            raise Exception(
                "Cross-origin XHR request not allowed")

        def run_load():
            headers, response = full_url.request(frame.url, body)
            response = response.decode("utf8")
            task = Task(
                self.dispatch_xhr_onload, response, handle, window_id)
            self.tab.task_runner.schedule_task(task)
            if not isasync:
                return response

        if not isasync:
            return run_load()
        else:
            threading.Thread(target=run_load).start()

    def now(self):
        return int(time.time() * 1000)

    def dispatch_RAF(self, window_id):
        code = self.wrap("window.__runRAFHandlers()", window_id)
        self.interp.evaljs(code)

    def requestAnimationFrame(self):
        self.tab.browser.set_needs_animation_frame(self.tab)

@wbetools.patch(style)
def style(node, rules, frame):
    old_style = node.style

    node.style = {}
    for property, default_value in INHERITED_PROPERTIES.items():
        if node.parent:
            node.style[property] = node.parent.style[property]
        else:
            node.style[property] = default_value
    for media, selector, body in rules:
        if media:
            if (media == "dark") != frame.tab.dark_mode: continue
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
                frame.set_needs_render()
                AnimationClass = ANIMATED_PROPERTIES[property]
                animation = AnimationClass(
                    old_value, new_value, num_frames)
                node.animations[property] = animation
                node.style[property] = animation.animate()

    for child in node.children:
        style(child, rules, frame)

class AccessibilityNode:
    def __init__(self, node, parent = None):
        self.node = node
        self.children = []
        self.parent = parent
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
            elif node.tag == "img":
                self.role = "image"
            elif node.tag == "iframe":
                self.role = "iframe"
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
        elif self.role == "image":
            if "alt" in self.node.attributes:
                self.text = "Image: " + self.node.attributes["alt"]
            else:
                self.text = "Image"
        elif self.role == "iframe":
            self.text = "Child document"

        if is_focused(self.node):
            self.text += " is focused"

    def build_internal(self, child_node):
        if isinstance(child_node, Element) \
            and child_node.tag == "iframe" and child_node.frame:
            child = FrameAccessibilityNode(child_node, self)
        else:
            child = AccessibilityNode(child_node, self)
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
        node = None
        if self.intersects(x, y):
            node = self
        for child in self.children:
            res = child.hit_test(x, y)
            if res: node = res
        return node

    def map_to_parent(self, rect):
        pass

    def absolute_bounds(self):
        rect = skia.Rect.MakeXYWH(
            self.bounds.x(), self.bounds.y(),
            self.bounds.width(), self.bounds.height())
        obj = self
        while obj:
            obj.map_to_parent(rect)
            obj = obj.parent
        return rect

    def __repr__(self):
        return "AccessibilityNode(node={} role={} text={}".format(
            str(self.node), self.role, self.text)

class FrameAccessibilityNode(AccessibilityNode):
    def __init__(self, node, parent = None):
        super().__init__(node, parent)
        self.scroll = self.node.frame.scroll

    def build(self):
        self.build_internal(self.node.frame.nodes)

    def hit_test(self, x, y):
        if not self.intersects(x, y): return
        new_x = x - self.bounds.x()
        new_y = y - self.bounds.y() + self.scroll
        node = self
        for child in self.children:
            res = child.hit_test(new_x, new_y)
            if res: node = res
        return node

    def map_to_parent(self, rect):
        rect.offset(self.bounds.x(), self.bounds.y() - self.scroll)

    def __repr__(self):
        return "FrameAccessibilityNode(node={} role={} text={}".format(
            str(self.node), self.role, self.text)


BROKEN_IMAGE = skia.Image.open("Broken_Image.png")

class Frame:
    def __init__(self, tab, parent_frame, frame_element):
        self.tab = tab
        self.parent_frame = parent_frame
        self.frame_element = frame_element
        self.needs_style = False
        self.needs_layout = False

        self.document = None
        self.scroll = 0
        self.scroll_changed_in_frame = True
        self.needs_focus_scroll = False
        self.nodes = None
        self.url = None
        self.js = None

        self.frame_width = 0
        self.frame_height = 0

        self.window_id = len(self.tab.window_id_to_frame)
        self.tab.window_id_to_frame[self.window_id] = self

        with open("browser15.css") as f:
            self.default_style_sheet = \
                CSSParser(f.read(), internal=True).parse()

    def set_needs_render(self):
        self.needs_style = True
        self.tab.set_needs_accessibility()
        self.tab.set_needs_paint()

    def set_needs_layout(self):
        self.needs_layout = True
        self.tab.set_needs_accessibility()
        self.tab.set_needs_paint()

    def allowed_request(self, url):
        return self.allowed_origins == None or \
            url.origin() in self.allowed_origins

    def load(self, url, body=None):
        self.zoom = 1
        self.scroll = 0
        self.scroll_changed_in_frame = True
        headers, body = url.request(self.url, body)
        body = body.decode("utf8")
        self.url = url

        self.allowed_origins = None
        if "content-security-policy" in headers:
           csp = headers["content-security-policy"].split()
           if len(csp) > 0 and csp[0] == "default-src":
               self.allowed_origins = csp[1:]

        self.nodes = HTMLParser(body).parse()

        self.js = self.tab.get_js(url.origin())
        self.js.add_window(self)

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
            body = body.decode("utf8")
            task = Task(self.js.run, script_url, body,
                self.window_id)
            self.tab.task_runner.schedule_task(task)

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
            self.rules.extend(CSSParser(body.decode("utf8")).parse())

        images = [node
            for node in tree_to_list(self.nodes, [])
            if isinstance(node, Element)
            and node.tag == "img"]
        for img in images:
            try:
                src = img.attributes.get("src", "")
                image_url = url.resolve(src)
                assert self.allowed_request(image_url), \
                    "Blocked load of " + image_url + " due to CSP"
                header, body = image_url.request(url)
                img.encoded_data = body
                data = skia.Data.MakeWithoutCopy(body)
                img.image = skia.Image.MakeFromEncoded(data)
                assert img.image, "Failed to recognize image format for " + image_url
            except Exception as e:
                print("Exception loading image: url="
                    + str(image_url) + " exception=" + str(e))
                img.image = BROKEN_IMAGE

        iframes = [node
                   for node in tree_to_list(self.nodes, [])
                   if isinstance(node, Element)
                   and node.tag == "iframe"
                   and "src" in node.attributes]
        for iframe in iframes:
            document_url = url.resolve(iframe.attributes["src"])
            if not self.allowed_request(document_url):
                print("Blocked iframe", document_url, "due to CSP")
                iframe.frame = None
                continue
            iframe.frame = Frame(self.tab, self, iframe)
            iframe.frame.load(document_url)

        self.set_needs_render()

    def render(self):
        if self.needs_style:
            if self.tab.dark_mode:
                INHERITED_PROPERTIES["color"] = "white"
            else:
                INHERITED_PROPERTIES["color"] = "black"
            style(self.nodes,
                  sorted(self.rules,
                         key=cascade_priority), self)
            self.needs_layout = True
            self.needs_style = False

        if self.needs_layout:
            self.document = DocumentLayout(self.nodes, self)
            self.document.layout(self.frame_width, self.tab.zoom)
            if self.tab.accessibility_is_on:
                self.tab.needs_accessibility = True
            else:
                self.needs_paint = True
            self.needs_layout = False

        clamped_scroll = self.clamp_scroll(self.scroll)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_frame = True
        self.scroll = clamped_scroll

    def paint(self, display_list):
        self.document.paint(display_list, self.tab.dark_mode,
            self.scroll if self != self.tab.root_frame else None)

    def advance_tab(self):
        focusable_nodes = [node
            for node in tree_to_list(self.nodes, [])
            if isinstance(node, Element) and is_focusable(node)                          
            and get_tabindex(node) >= 0]
        focusable_nodes.sort(key=get_tabindex)

        if self.tab.focus in focusable_nodes:
            idx = focusable_nodes.index(self.tab.focus) + 1
        else:
            idx = 0

        if idx < len(focusable_nodes):
            self.focus_element(focusable_nodes[idx])
        else:
            self.focus_element(None)
            self.tab.browser.focus_addressbar()
        self.set_needs_render()

    def focus_element(self, node):
        if node and node != self.tab.focus:
            self.needs_focus_scroll = True
        if self.tab.focus:
            self.tab.focus.is_focused = False
        if self.tab.focused_frame and self.tab.focused_frame != self:
            self.tab.focused_frame.set_needs_render()
        self.tab.focus = node
        self.tab.focused_frame = self
        if node:
            node.is_focused = True
        self.set_needs_render()

    def activate_element(self, elt):
        if elt.tag == "input":
            elt.attributes["value"] = ""
            self.set_needs_render()
        elif elt.tag == "a" and "href" in elt.attributes:
            url = self.url.resolve(elt.attributes["href"])
            self.load(url)
        elif elt.tag == "button":
            while elt:
                if elt.tag == "form" and "action" in elt.attributes:
                    self.submit_form(elt)
                    return
                elt = elt.parent

    def submit_form(self, elt):
        if self.js.dispatch_event(
            "submit", elt, self.window_id): return
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
        if self.tab.focus and self.tab.focus.tag == "input":
            if not "value" in self.tab.focus.attributes:
                self.activate_element(self.tab.focus)
            if self.js.dispatch_event(
                "keydown", self.tab.focus, self.window_id): return
            self.tab.focus.attributes["value"] += char
            self.set_needs_render()

    def scrolldown(self):
        self.scroll = self.clamp_scroll(self.scroll + SCROLL_STEP)
        self.scroll_changed_in_frame = True

    def scroll_to(self, elt):
        assert not (self.needs_style or self.needs_layout)
        objs = [
            obj for obj in tree_to_list(self.document, [])
            if obj.node == self.tab.focus
        ]
        if not objs: return
        obj = objs[0]

        if self.scroll < obj.y < self.scroll + self.frame_height:
            return
        new_scroll = obj.y - SCROLL_STEP
        self.scroll = self.clamp_scroll(new_scroll)
        self.scroll_changed_in_frame = True
        self.set_needs_render()

    def click(self, x, y):
        self.focus_element(None)
        y += self.scroll
        loc_rect = skia.Rect.MakeXYWH(x, y, 1, 1)
        objs = [obj for obj in tree_to_list(self.document, [])
                if absolute_bounds_for_obj(obj).intersects(
                    loc_rect)]
        if not objs: return
        elt = objs[-1].node
        if elt and self.js.dispatch_event(
            "click", elt, self.window_id): return
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "iframe":
                new_x = x - elt.layout_object.x
                new_y = y - elt.layout_object.y
                elt.frame.click(new_x, new_y)
                return
            elif is_focusable(elt):
                self.focus_element(elt)
                self.activate_element(elt)
                self.set_needs_render()
                return
            elt = elt.parent

    def clamp_scroll(self, scroll):
        height = math.ceil(self.document.height)
        maxscroll = height - self.frame_height
        return max(0, min(scroll, maxscroll))

class CommitData:
    def __init__(self, url, scroll, root_frame_focused, height,
        display_list, composited_updates, accessibility_tree, focus):
        self.url = url
        self.scroll = scroll
        self.root_frame_focused = root_frame_focused
        self.height = height
        self.display_list = display_list
        self.composited_updates = composited_updates
        self.accessibility_tree = accessibility_tree
        self.focus = focus


class Tab:
    def __init__(self, browser):
        self.url = ""
        self.history = []
        self.focus = None
        self.focused_frame = None
        self.needs_raf_callbacks = False
        self.needs_accessibility = False
        self.needs_paint = False
        self.root_frame = None
        self.dark_mode = browser.dark_mode

        self.accessibility_is_on = False
        self.accessibility_tree = None
        self.has_spoken_document = False
        self.accessibility_focus = None

        self.browser = browser
        if wbetools.USE_BROWSER_THREAD:
            self.task_runner = TaskRunner(self)
        else:
            self.task_runner = SingleThreadedTaskRunner(self)
        self.task_runner.start_thread()

        self.composited_updates = []
        self.zoom = 1.0

        self.window_id_to_frame = {}
        self.origin_to_js = {}

    def load(self, url, body=None):
        self.history.append(url)
        self.task_runner.clear_pending_tasks()
        self.root_frame = Frame(self, None, None)
        self.root_frame.load(url, body)
        self.root_frame.frame_width = WIDTH
        self.root_frame.frame_height = HEIGHT - CHROME_PX

    def get_js(self, origin):
        if wbetools.FORCE_CROSS_ORIGIN_IFRAMES:
            return JSContext(self, origin)
        if origin not in self.origin_to_js:
            self.origin_to_js[origin] = JSContext(self, origin)
        return self.origin_to_js[origin]

    def set_needs_render_all_frames(self):
        for id, frame in self.window_id_to_frame.items():
            frame.set_needs_render()

    def set_needs_accessibility(self):
        if not self.accessibility_is_on:
            return
        self.needs_accessibility = True
        self.browser.set_needs_animation_frame(self)

    def set_needs_paint(self):
        self.needs_paint = True
        self.browser.set_needs_animation_frame(self)

    def request_animation_frame_callback(self):
        self.needs_raf_callbacks = True
        self.browser.set_needs_animation_frame(self)

    def run_animation_frame(self, scroll):
        if not self.root_frame.scroll_changed_in_frame:
            self.root_frame.scroll = scroll

        needs_composite = False
        for (window_id, frame) in self.window_id_to_frame.items():
            frame.js.dispatch_RAF(frame.window_id)
    
            for node in tree_to_list(frame.nodes, []):
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
                            frame.set_needs_layout()
            if frame.needs_style or frame.needs_layout:
                needs_composite = True

        self.render()

        if self.focus and self.focused_frame.needs_focus_scroll:
            self.focused_frame.scroll_to(self.focus)
            self.focused_frame.needs_focus_scroll = False

        scroll = None
        if self.root_frame.scroll_changed_in_frame:
            scroll = self.root_frame.scroll

        composited_updates = {}
        if not needs_composite:
            for node in self.composited_updates:
                composited_updates[node] = node.save_layer
        self.composited_updates.clear()

        root_frame_focused = not self.focused_frame or \
                self.focused_frame == self.root_frame
        commit_data = CommitData(
            self.root_frame.url, scroll,
            root_frame_focused,
            math.ceil(self.root_frame.document.height),
            self.display_list, composited_updates,
            self.accessibility_tree,
            self.focus
        )
        self.display_list = None
        self.root_frame.scroll_changed_in_frame = False

        self.browser.commit(self, commit_data)

    def render(self):
        self.browser.measure.time('render')

        for id, frame in self.window_id_to_frame.items():
            frame.render()

        if self.needs_accessibility:
            self.accessibility_tree = AccessibilityNode(self.root_frame.nodes)
            self.accessibility_tree.build()
            self.needs_accessibility = False
            self.needs_paint = True

        if self.needs_paint:
            self.display_list = []
            self.root_frame.paint(self.display_list)
            self.needs_paint = False

        self.browser.measure.stop('render')

    def click(self, x, y):
        self.render()
        self.root_frame.click(x, y)

    def keypress(self, char):
        frame = self.focused_frame
        if not frame: frame = self.root_frame
        frame.keypress(char)

    def scrolldown(self):
        frame = self.focused_frame or self.root_frame
        frame.scrolldown()
        self.set_needs_accessibility()
        self.set_needs_paint()

    def enter(self):
        if self.focus:
            frame = self.focused_frame or self.root_frame
            frame.activate_element(self.focus)

    def get_tabindex(node):
        return int(node.attributes.get("tabindex", 9999999))

    def advance_tab(self):
        frame = self.focused_frame or self.root_frame
        frame.advance_tab()

    def zoom_by(self, increment):
        if increment > 0:
            self.zoom *= 1.1
        else:
            self.zoom *= 1/1.1
        self.set_needs_render_all_frames()

    def reset_zoom(self):
        self.zoom = 1
        self.set_needs_render_all_frames()

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

    def toggle_accessibility(self):
        self.accessibility_is_on = not self.accessibility_is_on
        self.set_needs_accessibility()

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.set_needs_render_all_frames()

    def post_message(self, message, target_window_id):
        frame = self.window_id_to_frame[target_window_id]
        frame.js.dispatch_post_message(
            message, target_window_id)

@wbetools.patch(Browser)
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
                OpenGL.GL.glGetString(OpenGL.GL.GL_VENDOR),
                OpenGL.GL.glGetString(OpenGL.GL.GL_RENDERER)))

            self.skia_context = skia.GrDirectContext.MakeGL()

            self.root_surface = \
                skia.Surface.MakeFromBackendRenderTarget(
                self.skia_context,
                skia.GrBackendRenderTarget(
                    WIDTH, HEIGHT, 0, 0, 
                    skia.GrGLFramebufferInfo(0, OpenGL.GL.GL_RGBA8)),
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

        self.measure = MeasureTime()

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
        self.accessibility_is_on = False
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
        tab.task_runner.run_tasks()
        tab.run_animation_frame(self.scroll)

    def commit(self, tab, data):
        self.lock.acquire(blocking=True)
        if tab == self.tabs[self.active_tab]:
            self.url = data.url
            if data.scroll != None:
                self.scroll = data.scroll
            self.root_frame_focused = data.root_frame_focused
            self.active_tab_height = data.height
            if data.display_list:
                self.active_tab_display_list = data.display_list
            self.animation_timer = None
            self.composited_updates = data.composited_updates
            self.accessibility_tree = data.accessibility_tree
            if self.accessibility_tree:
                self.set_needs_accessibility()
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
                self.hovered_a11y_node.absolute_bounds(),
                "white" if self.dark_mode else "black", 2))

    def update_accessibility(self):
        if not self.accessibility_tree: return

        if not self.has_spoken_document:
            self.speak_document()
            self.has_spoken_document = True

        self.active_alerts = [
            node for node in tree_to_list(self.accessibility_tree, [])
            if node.role == "alert"
        ]

        for alert in self.active_alerts:
            if alert not in self.spoken_alerts:
                self.speak_node(alert, "New alert")
                self.spoken_alerts.append(alert)

        new_spoken_alerts = []
        for old_node in self.spoken_alerts:
            new_nodes = [
                node for node in \
                    tree_to_list(self.accessibility_tree, [])
                if node.node == old_node.node
                and node.role == "alert"
            ]
            if new_nodes:
                new_spoken_alerts.append(new_nodes[0])
        self.spoken_alerts = new_spoken_alerts

        if self.tab_focus and \
            self.tab_focus != self.last_tab_focus:
            nodes = [node for node in \
                tree_to_list(self.accessibility_tree, [])
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
            and not self.needs_raster and not self.needs_draw:
            self.lock.release()
            return
        self.measure.time('raster/draw')
        start_time = time.time()
        if self.needs_composite:
            self.composite()
        if self.needs_raster:
            self.raster_chrome()
            self.raster_tab()
        if self.needs_draw:
            self.paint_draw_list()
            self.draw()

        self.measure.stop('raster/draw')

        if self.needs_accessibility:
            self.update_accessibility()

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
        if self.root_frame_focused:
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
            return
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.scrolldown)
        active_tab.task_runner.schedule_task(task)
        self.needs_animation_frame = True
        self.lock.release()        

    def handle_tab(self):
        self.focus = "content"
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.advance_tab)
        active_tab.task_runner.schedule_task(task)
        pass

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
        new_active_tab = (self.active_tab + 1) % len(self.tabs)
        self.set_active_tab(new_active_tab)

    def toggle_accessibility(self):
        self.accessibility_is_on = not self.accessibility_is_on
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.toggle_accessibility)
        active_tab.task_runner.schedule_task(task)

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
        self.muted = not self.muted

    def is_muted(self):
        muted = self.muted
        return muted

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.toggle_dark_mode)
        active_tab.task_runner.schedule_task(task)

    def handle_click(self, e):
        self.lock.acquire(blocking=True)
        if e.y < CHROME_PX:
            self.focus = None
            if 40 <= e.x < 40 + 80 * len(self.tabs) and 0 <= e.y < 40:
                self.set_active_tab(int((e.x - 40) / 80))
            elif 10 <= e.x < 30 and 10 <= e.y < 30:
                self.load_internal(URL("https://browser.engineering/"))
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
            self.schedule_load(URL(self.address_bar))
            self.url = self.address_bar
            self.focus = None
            self.set_needs_raster()
        elif self.focus == "content":
            active_tab = self.tabs[self.active_tab]
            task = Task(active_tab.enter)
            active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def increment_zoom(self, increment):
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.zoom_by, increment)
        active_tab.task_runner.schedule_task(task)

    def reset_zoom(self):
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.reset_zoom)
        active_tab.task_runner.schedule_task(task)

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

    def paint_chrome(self):
        if self.dark_mode:
            color = "white"
        else:
            color = "black"

        cmds = []
        cmds.append(DrawLine(0, CHROME_PX - 1, WIDTH, CHROME_PX - 1, color, 1))

        tabfont = get_font(20, "normal", "roman")
        for i, tab in enumerate(self.tabs):
            name = "Tab {}".format(i)
            x1, x2 = 40 + 80 * i, 120 + 80 * i
            cmds.append(DrawLine(x1, 0, x1, 40, color, 1))
            cmds.append(DrawLine(x2, 0, x2, 40, color, 1))
            cmds.append(DrawText(x1 + 10, 10, name, tabfont, color))
            if i == self.active_tab:
                cmds.append(DrawLine(0, 40, x1, 40, color, 1))
                cmds.append(DrawLine(x2, 40, WIDTH, 40, color, 1))

        buttonfont = get_font(30, "normal", "roman")
        cmds.append(DrawOutline(10, 10, 30, 30, color, 1))
        cmds.append(DrawText(11, 5, "+", buttonfont, color))

        cmds.append(DrawOutline(40, 50, WIDTH - 10, 90, color, 1))
        if self.focus == "address bar":
            cmds.append(DrawText(55, 55, self.address_bar, buttonfont, color))
            w = buttonfont.measureText(self.address_bar)
            cmds.append(DrawLine(55 + w, 55, 55 + w, 85, color, 1))
        else:
            url = ""
            if self.tabs[self.active_tab].root_frame:
                url = str(self.tabs[self.active_tab].root_frame.url)
            cmds.append(DrawText(55, 55, url, buttonfont, color))

        cmds.append(DrawOutline(10, 50, 35, 90, color, 1))
        cmds.append(DrawText(15, 55, "<", buttonfont, color))
        return cmds

    def raster_chrome(self):
        canvas = self.chrome_surface.getCanvas()
        if self.dark_mode:
            background_color = skia.ColorBLACK
        else:
            background_color = skia.ColorWHITE
        canvas.clear(background_color)
    
        for cmd in self.paint_chrome():
            cmd.execute(canvas)

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
        self.measure.finish()
        self.tabs[self.active_tab].task_runner.set_needs_quit()
        if wbetools.USE_GPU:
            sdl2.SDL_GL_DeleteContext(self.gl_context)
        sdl2.SDL_DestroyWindow(self.sdl_window)

def add_main_args():
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
    parser.add_argument("--force_cross_origin_iframes", action="store_true",
        default=False, help="Whether to treat all iframes as cross-origin")
    args = parser.parse_args()

    wbetools.USE_BROWSER_THREAD = not args.single_threaded
    wbetools.USE_GPU = not args.disable_gpu
    wbetools.USE_COMPOSITING = not args.disable_compositing and not args.disable_gpu
    wbetools.SHOW_COMPOSITED_LAYER_BORDERS = args.show_composited_layer_borders
    wbetools.FORCE_CROSS_ORIGIN_IFRAMES = args.force_cross_origin_iframes

    return args

if __name__ == "__main__":
    args = add_main_args()
    main_func(args)
