"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 15 (Supporting Embedded Content),
without exercises.
"""

import sys
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
from lab4 import print_tree, HTMLParser
from lab5 import BLOCK_ELEMENTS
from lab14 import Text, Element
from lab6 import TagSelector, DescendantSelector
from lab6 import tree_to_list, INHERITED_PROPERTIES
from lab8 import INPUT_WIDTH_PX
from lab10 import COOKIE_JAR, URL
from lab11 import FONTS, NAMED_COLORS, get_font, linespace
from lab11 import parse_color, parse_blend_mode
from lab12 import MeasureTime, REFRESH_RATE_SEC, JSContext
from lab12 import Task, TaskRunner, SingleThreadedTaskRunner
from lab13 import diff_styles, parse_transition, add_parent_pointers
from lab13 import local_to_absolute, absolute_bounds_for_obj, absolute_to_local
from lab13 import NumericAnimation
from lab13 import map_translation, parse_transform
from lab13 import CompositedLayer, paint_visual_effects
from lab13 import PaintCommand, DrawText, DrawCompositedLayer, DrawOutline, \
    DrawLine, DrawRRect, DrawRect
from lab13 import VisualEffect, Blend, Transform
from lab14 import parse_outline, paint_outline, \
    dpx, cascade_priority, style, \
    is_focusable, get_tabindex, speak_text, \
    CSSParser, mainloop, Browser, Chrome, Tab, \
    AccessibilityNode, PseudoclassSelector, SPEECH_FILE
from lab14 import DocumentLayout, BlockLayout, LineLayout, TextLayout

@wbetools.patch(URL)
class URL:
    def request(self, referrer, payload=None):
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
            if referrer and params.get("samesite", "none") == "lax":
                if method != "GET":
                    allow_cookie = self.host == referrer.host
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
    
        response_headers = {}
        while True:
            line = response.readline().decode("utf8")
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
    
        if "set-cookie" in response_headers:
            cookie = response_headers["set-cookie"]
            params = {}
            if ";" in cookie:
                cookie, rest = cookie.split(";", 1)
                for param in rest.split(";"):
                    if '=' in param:
                        param, value = param.split("=", 1)
                    else:
                        value = "true"
                    params[param.strip().casefold()] = value.casefold()
            COOKIE_JAR[self.host] = (cookie, params)
    
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers
    
        body = response.read()
        s.close()
        return response_headers, body
      
DEFAULT_STYLE_SHEET = CSSParser(open("browser15.css").read()).parse()

def parse_image_rendering(quality):
    if int(skia.__version__.split(".")[0]) > 87:
        if quality == "high-quality":
            return skia.SamplingOptions(skia.CubicResampler.Mitchell())
        elif quality == "crisp-edges":
            return skia.SamplingOptions(
                skia.FilterMode.kNearest, skia.MipmapMode.kNone)
        else:
            return skia.SamplingOptions(
                skia.FilterMode.kLinear, skia.MipmapMode.kLinear)

    if quality == "high-quality":
        return skia.FilterQuality.kHigh_FilterQuality
    elif quality == "crisp-edges":
        return skia.FilterQuality.kLow_FilterQuality
    else:
        return skia.FilterQuality.kMedium_FilterQuality

class DrawImage(PaintCommand):
    def __init__(self, image, rect, quality):
        super().__init__(rect)
        self.image = image
        self.quality = parse_image_rendering(quality)

    def execute(self, canvas):
        if int(skia.__version__.split(".")[0]) > 87:
            canvas.drawImageRect(self.image, self.rect, self.quality)
            return

        paint = skia.Paint(
            FilterQuality=self.quality,
        )
        canvas.drawImageRect(self.image, self.rect, paint)

    @wbetools.js_hide
    def __repr__(self):
        return "DrawImage(rect={})".format(
            self.rect)

def paint_tree(layout_object, display_list):
    cmds = layout_object.paint()

    if isinstance(layout_object, IframeLayout) and \
        layout_object.node.frame and \
        layout_object.node.frame.loaded:
        paint_tree(layout_object.node.frame.document, cmds)
    else:
        for child in layout_object.children:
            paint_tree(child, cmds)

    cmds = layout_object.paint_effects(cmds)
    display_list.extend(cmds)

@wbetools.patch(DocumentLayout)
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

        self.width = width - 2 * dpx(HSTEP, self.zoom)
        self.x = dpx(HSTEP, self.zoom)
        self.y = dpx(VSTEP, self.zoom)
        child.layout()
        self.height = child.height

    def paint_effects(self, cmds):
        if self.frame != self.frame.tab.root_frame and self.frame.scroll != 0:
            rect = skia.Rect.MakeLTRB(
                self.x, self.y,
                self.x + self.width, self.y + self.height)
            cmds = [Transform((0, - self.frame.scroll), rect, self.node, cmds)]
        return cmds

@wbetools.patchable
def font(style, zoom):
    weight = style["font-weight"]
    variant = style["font-style"]
    size = None
    try:
        size = float(style["font-size"][:-2]) * 0.75
    except:
        size = 16
    font_size = dpx(size, zoom)
    return get_font(font_size, weight, variant)

@wbetools.patch(BlockLayout)
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
        elif self.node.tag in ["input", "img", "iframe"]:
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
        self.cursor_x = self.x
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line)
        self.children.append(new_line)

    def add_inline_child(self, node, w, child_class, frame, word=None):
        if self.cursor_x + w > self.x + self.width:
            self.new_line()
        line = self.children[-1]
        previous_word = line.children[-1] if line.children else None
        if word:
            child = child_class(node, word, line, previous_word)
        else:
            child = child_class(node, line, previous_word, frame)
        line.children.append(child)
        self.cursor_x += w + \
            font(node.style, self.zoom).measureText(" ")

    def word(self, node, word):
        node_font = font(node.style, self.zoom)
        w = node_font.measureText(word)
        self.add_inline_child(node, w, TextLayout, self.frame, word)

    def input(self, node):
        w = dpx(INPUT_WIDTH_PX, self.zoom)
        self.add_inline_child(node, w, InputLayout, self.frame) 

    def image(self, node):
        if "width" in node.attributes:
            w = dpx(int(node.attributes["width"]), self.zoom)
        else:
            w = dpx(node.image.width(), self.zoom)
        self.add_inline_child(node, w, ImageLayout, self.frame)

    def iframe(self, node):
        if "width" in self.node.attributes:
            w = dpx(int(self.node.attributes["width"]),
                    self.zoom)
        else:
            w = IFRAME_WIDTH_PX + dpx(2, self.zoom)
        self.add_inline_child(node, w, IframeLayout, self.frame)

    def should_paint(self):
        return isinstance(self.node, Text) or \
            (self.node.tag not in \
                ["input", "button", "img", "iframe"])

    def paint(self):
        cmds = []
        bgcolor = self.node.style.get(
            "background-color", "transparent")
        if bgcolor != "transparent":
            radius = dpx(
                float(self.node.style.get(
                    "border-radius", "0px")[:-2]),
                self.zoom)
            cmds.append(DrawRRect(self.self_rect(), radius, bgcolor))
        return cmds

    @wbetools.js_hide
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

    def layout(self):
        self.zoom = self.parent.zoom
        self.font = font(self.node.style, self.zoom)
        if self.previous:
            space = self.previous.font.measureText(" ")
            self.x = \
                self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

    def should_paint(self):
        return True

class InputLayout(EmbedLayout):
    def __init__(self, node, parent, previous, frame):
        super().__init__(node, parent, previous, frame)

    def layout(self):
        super().layout()

        self.width = dpx(INPUT_WIDTH_PX, self.zoom)
        self.height = linespace(self.font)

        self.ascent = -self.height
        self.descent = 0

    def self_rect(self):
        return skia.Rect.MakeLTRB(
            self.x, self.y, self.x + self.width,
            self.y + self.height)

    def paint(self):
        cmds = []

        bgcolor = self.node.style.get("background-color",
                                 "transparent")
        if bgcolor != "transparent":
            radius = dpx(
                float(self.node.style.get("border-radius", "0px")[:-2]),
                self.zoom)
            cmds.append(DrawRRect(self.self_rect(), radius, bgcolor))

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

        return cmds

    def paint_effects(self, cmds):
        cmds = paint_visual_effects(self.node, cmds, self.self_rect())
        paint_outline(self.node, cmds, self.self_rect(), self.zoom)
        return cmds

    @wbetools.js_hide
    def __repr__(self):
        return "InputLayout(x={}, y={}, width={}, height={})".format(
            self.x, self.y, self.width, self.height)

@wbetools.patch(LineLayout)
class LineLayout:
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

        max_ascent = max([-child.ascent 
                          for child in self.children])
        baseline = self.y + max_ascent

        for child in self.children:
            if isinstance(child, TextLayout):
                child.y = baseline + child.ascent / 1.25
            else:
                child.y = baseline + child.ascent
        max_descent = max([child.descent
                           for child in self.children])
        self.height = max_ascent + max_descent

@wbetools.patch(TextLayout)
class TextLayout:
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

        self.ascent = self.font.getMetrics().fAscent * 1.25
        self.descent = self.font.getMetrics().fDescent * 1.25

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
            self.width = dpx(int(width_attr), self.zoom)
            self.img_height = dpx(int(height_attr), self.zoom)
        elif width_attr:
            self.width = dpx(int(width_attr), self.zoom)
            self.img_height = self.width / aspect_ratio
        elif height_attr:
            self.img_height = dpx(int(height_attr), self.zoom)
            self.width = self.img_height * aspect_ratio
        else:
            self.width = dpx(image_width, self.zoom)
            self.img_height = dpx(image_height, self.zoom)

        self.height = max(self.img_height, linespace(self.font))

        self.ascent = -self.height
        self.descent = 0

    def paint(self):
        cmds = []
        rect = skia.Rect.MakeLTRB(
            self.x, self.y + self.height - self.img_height,
            self.x + self.width, self.y + self.height)
        quality = self.node.style.get("image-rendering", "auto")
        cmds.append(DrawImage(self.node.image, rect, quality))
        return cmds

    def paint_effects(self, cmds):
        return cmds

    @wbetools.js_hide
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
            self.width = dpx(int(width_attr) + 2, self.zoom)
        else:
            self.width = dpx(IFRAME_WIDTH_PX + 2, self.zoom)

        if height_attr:
            self.height = dpx(int(height_attr) + 2, self.zoom)
        else:
            self.height = dpx(IFRAME_HEIGHT_PX + 2, self.zoom)

        if self.node.frame and self.node.frame.loaded:
            self.node.frame.frame_height = \
                self.height - dpx(2, self.zoom)
            self.node.frame.frame_width = \
                self.width - dpx(2, self.zoom)

        self.ascent = -self.height
        self.descent = 0

    def paint(self):
        cmds = []

        rect = skia.Rect.MakeLTRB(
            self.x, self.y,
            self.x + self.width, self.y + self.height)
        bgcolor = self.node.style.get("background-color",
            "transparent")
        if bgcolor != "transparent":
            radius = dpx(float(
                self.node.style.get("border-radius", "0px")[:-2]),
                self.zoom)
            cmds.append(DrawRRect(rect, radius, bgcolor))
        return cmds

    def paint_effects(self, cmds):
        rect = skia.Rect.MakeLTRB(
            self.x, self.y,
            self.x + self.width, self.y + self.height)
        diff = dpx(1, self.zoom)
        offset = (self.x + diff, self.y + diff)
        cmds = [Transform(offset, rect, self.node, cmds)]
        inner_rect = skia.Rect.MakeLTRB(
            self.x + diff, self.y + diff,
            self.x + self.width - diff, self.y + self.height - diff)
        internal_cmds = cmds
        internal_cmds.append(Blend(1.0, "destination-in", None, [
                          DrawRRect(inner_rect, 0, "white")]))
        cmds = [Blend(1.0, "source-over", self.node, internal_cmds)]
        paint_outline(self.node, cmds, rect, self.zoom)
        cmds = paint_visual_effects(self.node, cmds, rect)
        return cmds

    @wbetools.js_hide
    def __repr__(self):
        return "IframeLayout(src={}, x={}, y={}, width={}, height={})".format(
            self.node.attributes["src"], self.x, self.y, self.width, self.height)

@wbetools.outline_hide
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
        if self.i == start:
            self.i = len(self.s)
            return ""
        if quoted:
            return self.s[start+1:self.i-1]
        return self.s[start:self.i]

    def parse(self):
        attributes = {}
        tag = None

        tag = self.word().casefold()
        while self.i < len(self.s):
            self.whitespace()
            key = self.word()
            if self.literal("="):
                value = self.word(allow_quotes=True) 
                attributes[key.casefold()] = value
            else:
                attributes[key.casefold()] = ""
        return (tag, attributes)

@wbetools.patch(HTMLParser)
class HTMLParser:
    def get_attributes(self, text):
        (tag, attributes) = AttributeParser(text).parse()
        return tag, attributes

EVENT_DISPATCH_JS = \
    "new window.Node(dukpy.handle)" + \
    ".dispatchEvent(new window.Event(dukpy.type))"

POST_MESSAGE_DISPATCH_JS = \
    "window.dispatchEvent(new window.MessageEvent(dukpy.data))"

SETTIMEOUT_JS = "window.__runSetTimeout(dukpy.handle)"
XHR_ONLOAD_JS = "window.__runXHROnload(dukpy.out, dukpy.handle)"
RUNTIME_JS = open("runtime15.js").read()

@wbetools.patch(JSContext)
class JSContext:
    def __init__(self, tab, url_origin):
        self.tab = tab
        self.url_origin = url_origin
        self.discarded = False

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

        self.tab.browser.measure.time('script-runtime')
        self.interp.evaljs(self.wrap(RUNTIME_JS, frame.window_id))
        self.tab.browser.measure.stop('script-runtime')

        self.interp.evaljs("WINDOWS[{}] = window_{};".format(
            frame.window_id, frame.window_id))

    def wrap(self, script, window_id):
        return "window = window_{}; {}".format(window_id, script)

    def run(self, script, code, window_id):
        try:
            code = self.wrap(code, window_id)
            self.tab.browser.measure.time('script-load')
            self.interp.evaljs(code)
            self.tab.browser.measure.stop('script-load')
        except dukpy.JSRuntimeError as e:
            self.tab.browser.measure.stop('script-load')
            print("Script", script, "crashed", e)

    def dispatch_event(self, type, elt, window_id):
        handle = self.node_to_handle.get(elt, -1)
        code = self.wrap(EVENT_DISPATCH_JS, window_id)
        do_default = self.interp.evaljs(code,
            type=type, handle=handle)
        return not do_default

    def querySelectorAll(self, selector_text, window_id):
        frame = self.tab.window_id_to_frame[window_id]
        self.throw_if_cross_origin(frame)
        selector = CSSParser(selector_text).selector()
        nodes = [node for node
                in tree_to_list(frame.nodes, [])
                 if selector.matches(node)]
        return [self.get_handle(node) for node in nodes]

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
            self.wrap(POST_MESSAGE_DISPATCH_JS, window_id),
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
        self.tab.browser.measure.time('script-settimeout')
        self.interp.evaljs(
            self.wrap(SETTIMEOUT_JS, window_id), handle=handle)
        self.tab.browser.measure.stop('script-settimeout')

    def setTimeout(self, handle, time, window_id):
        def run_callback():
            task = Task(self.dispatch_settimeout, handle, window_id)
            self.tab.task_runner.schedule_task(task)
        threading.Timer(time / 1000.0, run_callback).start()

    def dispatch_xhr_onload(self, out, handle, window_id):
        code = self.wrap(XHR_ONLOAD_JS, window_id)
        self.tab.browser.measure.time('script-xhr')
        do_default = self.interp.evaljs(code, out=out, handle=handle)
        self.tab.browser.measure.stop('script-xhr')

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
            response = response.decode("utf8", "replace")
            task = Task(
                self.dispatch_xhr_onload, response, handle, window_id)
            self.tab.task_runner.schedule_task(task)
            if not isasync:
                return response

        if not isasync:
            return run_load()
        else:
            threading.Thread(target=run_load).start()

    def dispatch_RAF(self, window_id):
        code = self.wrap("window.__runRAFHandlers()", window_id)
        self.interp.evaljs(code)

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
            if property == "opacity":
                frame.set_needs_render()
                animation = NumericAnimation(
                    old_value, new_value, num_frames)
                node.animations[property] = animation
                node.style[property] = animation.animate()

    for child in node.children:
        style(child, rules, frame)

@wbetools.patch(AccessibilityNode)
class AccessibilityNode:
    def __init__(self, node, parent=None):
        self.node = node
        self.children = []
        self.parent = parent
        self.text = ""
        self.bounds = self.compute_bounds()

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
            self.text = "Focusable element"
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

        if self.node.is_focused:
            self.text += " is focused"

    def build_internal(self, child_node):
        if isinstance(child_node, Element) \
            and child_node.tag == "iframe" and child_node.frame \
            and child_node.frame.loaded:
            child = FrameAccessibilityNode(child_node, self)
        else:
            child = AccessibilityNode(child_node, self)
        if child.role != "none":
            self.children.append(child)
            child.build()
        else:
            for grandchild_node in child_node.children:
                self.build_internal(grandchild_node)

    def map_to_parent(self, rect):
        pass

    def absolute_bounds(self):
        abs_bounds = []
        for bound in self.bounds:
            abs_bound = bound.makeOffset(0.0, 0.0)
            if isinstance(self, FrameAccessibilityNode):
                obj = self.parent
            else:
                obj = self
            while obj:
                obj.map_to_parent(abs_bound)
                obj = obj.parent
            abs_bounds.append(abs_bound)
        return abs_bounds

class FrameAccessibilityNode(AccessibilityNode):
    def __init__(self, node, parent=None):
        super().__init__(node, parent)
        self.scroll = self.node.frame.scroll
        self.zoom = self.node.layout_object.zoom

    def build(self):
        self.build_internal(self.node.frame.nodes)

    def hit_test(self, x, y):
        bounds = self.bounds[0]
        if not bounds.contains(x, y): return
        new_x = x - bounds.left() - dpx(1, self.zoom)
        new_y = y - bounds.top() - dpx(1, self.zoom) + self.scroll
        node = self
        for child in self.children:
            res = child.hit_test(new_x, new_y)
            if res: node = res
        return node

    def map_to_parent(self, rect):
        bounds = self.bounds[0]
        rect.offset(bounds.left(), bounds.top() - self.scroll)
        rect.intersect(bounds)

    @wbetools.js_hide
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
        self.loaded = False

        self.frame_width = 0
        self.frame_height = 0

        self.window_id = len(self.tab.window_id_to_frame)
        self.tab.window_id_to_frame[self.window_id] = self

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

    def load(self, url, payload=None):
        self.loaded = False
        self.zoom = 1
        self.scroll = 0
        self.scroll_changed_in_frame = True
        headers, body = url.request(self.url, payload)
        body = body.decode("utf8", "replace")
        self.url = url

        self.allowed_origins = None
        if "content-security-policy" in headers:
           csp = headers["content-security-policy"].split()
           if len(csp) > 0 and csp[0] == "default-src":
               self.allowed_origins = csp[1:]

        self.nodes = HTMLParser(body).parse()

        if self.js: self.js.discarded = True
        self.js = self.tab.get_js(url)
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

            try:
                header, body = script_url.request(url)
            except:
                continue
            body = body.decode("utf8", "replace")
            task = Task(self.js.run, script_url, body,
                self.window_id)
            self.tab.task_runner.schedule_task(task)

        self.rules = DEFAULT_STYLE_SHEET.copy()
        links = [node.attributes["href"]
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "link"
                 and node.attributes.get("rel") == "stylesheet"
                 and "href" in node.attributes]
        for link in links:  
            style_url = url.resolve(link)
            if not self.allowed_request(style_url):
                print("Blocked style", link, "due to CSP")
                continue
            try:
                header, body = style_url.request(url)
            except:
                continue
            self.rules.extend(CSSParser(body.decode("utf8", "replace")).parse())

        images = [node
            for node in tree_to_list(self.nodes, [])
            if isinstance(node, Element)
            and node.tag == "img"]
        for img in images:
            try:
                src = img.attributes.get("src", "")
                image_url = url.resolve(src)
                assert self.allowed_request(image_url), \
                    "Blocked load of " + str(image_url) + " due to CSP"
                header, body = image_url.request(url)
                img.encoded_data = body
                data = skia.Data.MakeWithoutCopy(body)
                img.image = skia.Image.MakeFromEncoded(data)
                assert img.image, \
                    "Failed to recognize image format for " + str(image_url)
            except Exception as e:
                print("Image", img.attributes.get("src", ""),
                    "crashed", e)
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
            task = Task(iframe.frame.load, document_url)
            self.tab.task_runner.schedule_task(task)

        self.set_needs_render()
        self.loaded = True

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
            self.tab.needs_accessibility = True
            self.needs_paint = True
            self.needs_layout = False

        clamped_scroll = self.clamp_scroll(self.scroll)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_frame = True
        self.scroll = clamped_scroll

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
            self.tab.browser.focus_content()
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
        self.tab.set_needs_paint()

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
                abs_bounds = \
                    absolute_bounds_for_obj(elt.layout_object)
                border = dpx(1, elt.layout_object.zoom)
                new_x = x - abs_bounds.left() - border
                new_y = y - abs_bounds.top() - border
                elt.frame.click(new_x, new_y)
                return
            elif is_focusable(elt):
                self.focus_element(elt)
                self.activate_element(elt)
                self.set_needs_render()
                return
            elt = elt.parent

    def clamp_scroll(self, scroll):
        height = math.ceil(self.document.height + 2*VSTEP)
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

@wbetools.patch(Tab)
class Tab:
    def __init__(self, browser, tab_height):
        self.url = ""
        self.tab_height = tab_height
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
        self.loaded = False

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

    def load(self, url, payload=None):
        self.loaded = False
        self.history.append(url)
        self.task_runner.clear_pending_tasks()
        self.root_frame = Frame(self, None, None)
        self.root_frame.load(url, payload)
        self.root_frame.frame_width = WIDTH
        self.root_frame.frame_height = self.tab_height
        self.loaded = True

    def get_js(self, url):
        origin = url.origin()
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

    def run_animation_frame(self, scroll):
        if not self.root_frame.scroll_changed_in_frame:
            self.root_frame.scroll = scroll

        needs_composite = False
        for (window_id, frame) in self.window_id_to_frame.items():
            if not frame.loaded:
                continue

            self.browser.measure.time('script-runRAFHandlers')
            frame.js.dispatch_RAF(frame.window_id)
            self.browser.measure.stop('script-runRAFHandlers')

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

        for (window_id, frame) in self.window_id_to_frame.items():
            if frame == self.root_frame: continue
            if frame.scroll_changed_in_frame:
                needs_composite = True
                frame.scroll_changed_in_frame = False

        scroll = None
        if self.root_frame.scroll_changed_in_frame:
            scroll = self.root_frame.scroll

        composited_updates = None
        if not needs_composite:
            composited_updates = {}
            for node in self.composited_updates:
                composited_updates[node] = node.blend_op
        self.composited_updates = []

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
            if frame.loaded:
                frame.render()

        if self.needs_accessibility:
            self.accessibility_tree = AccessibilityNode(self.root_frame.nodes)
            self.accessibility_tree.build()
            self.needs_accessibility = False
            self.needs_paint = True

        if self.needs_paint:
            self.display_list = []
            paint_tree(self.root_frame.document, self.display_list)
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

    def advance_tab(self):
        frame = self.focused_frame or self.root_frame
        frame.advance_tab()

    def zoom_by(self, increment):
        if increment > 0:
            self.zoom *= 1.1
            self.scroll *= 1.1
        else:
            self.zoom *= 1/1.1
            self.scroll *= 1/1.1
        self.scroll_changed_in_tab = True
        self.set_needs_render_all_frames()

    def reset_zoom(self):
        self.scroll_changed_in_tab = True
        self.scroll /= self.zoom
        self.zoom = 1
        self.set_needs_render_all_frames()

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

    def set_dark_mode(self, val):
        self.dark_mode = val
        self.set_needs_render_all_frames()

    def post_message(self, message, target_window_id):
        frame = self.window_id_to_frame[target_window_id]
        frame.js.dispatch_post_message(
            message, target_window_id)

@wbetools.patch(Browser)
class Browser:
    def __init__(self):
        self.chrome = Chrome(self)

        if wbetools.USE_GPU:
            self.sdl_window = sdl2.SDL_CreateWindow(b"Browser",
                sdl2.SDL_WINDOWPOS_CENTERED,
                sdl2.SDL_WINDOWPOS_CENTERED,
                WIDTH, HEIGHT,
                sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_OPENGL)

            sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_MAJOR_VERSION, 3)
            sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_MINOR_VERSION, 2)
            sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_FORWARD_COMPATIBLE_FLAG, True)
            sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_PROFILE_MASK,
                                     sdl2.SDL_GL_CONTEXT_PROFILE_CORE)

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
                    skia.ImageInfo.MakeN32Premul(WIDTH, math.ceil(self.chrome.bottom)))
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
            self.chrome_surface = skia.Surface(WIDTH, math.ceil(self.chrome.bottom))
            self.skia_context = None

        self.tabs = []
        self.active_tab = None
        self.focus = None
        self.address_bar = ""
        self.lock = threading.Lock()
        self.active_tab_url = None
        self.active_tab_scroll = 0

        self.measure = MeasureTime()
        threading.current_thread().name = "Browser thread"

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
        self.root_frame_focused = False

    def commit(self, tab, data):
        self.lock.acquire(blocking=True)
        if tab == self.active_tab:
            self.active_tab_url = data.url
            if data.scroll != None:
                self.active_tab_scroll = data.scroll
            self.root_frame_focused = data.root_frame_focused
            self.active_tab_height = data.height
            if data.display_list:
                self.active_tab_display_list = data.display_list
            self.animation_timer = None
            self.composited_updates = data.composited_updates
            self.accessibility_tree = data.accessibility_tree
            if self.accessibility_tree:
                self.set_needs_accessibility()
            if self.composited_updates == None:
                self.composited_updates = {}
                self.set_needs_composite()
            else:
                self.set_needs_draw()
        self.lock.release()

    def set_active_tab(self, tab):
        self.active_tab = tab
        task = Task(self.active_tab.set_dark_mode, self.dark_mode)
        self.active_tab.task_runner.schedule_task(task)
        task = Task(self.active_tab.set_needs_render_all_frames)
        self.active_tab.task_runner.schedule_task(task)

        self.clear_data()
        self.needs_animation_frame = True
        self.animation_timer = None

    def handle_down(self):
        self.lock.acquire(blocking=True)
        if self.root_frame_focused:
            if not self.active_tab_height:
                self.lock.release()
                return
            self.active_tab_scroll = \
                self.clamp_scroll(self.active_tab_scroll + SCROLL_STEP)
            self.set_needs_draw()
            self.needs_animation_frame = True
            self.lock.release()
            return
        task = Task(self.active_tab.scrolldown)
        self.active_tab.task_runner.schedule_task(task)
        self.needs_animation_frame = True
        self.lock.release()
     

if __name__ == "__main__":
    wbetools.parse_flags()
    sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS)
    browser = Browser()
    browser.new_tab(URL(sys.argv[1]))
    browser.draw()
    mainloop(browser)
