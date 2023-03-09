"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 15 (Supporting Embedded Content),
without exercises.
"""

import ctypes
import dukpy
import io
import gtts
import math
import os
import playsound
import sdl2
import skia
import socket
import ssl
import threading
import time
import urllib.parse
import wbetools

from lab4 import print_tree
from lab13 import Text, Element
from lab6 import resolve_url
from lab6 import tree_to_list
from lab6 import INHERITED_PROPERTIES
from lab6 import compute_style
from lab8 import layout_mode
from lab9 import EVENT_DISPATCH_CODE
from lab10 import COOKIE_JAR, url_origin
from lab11 import draw_text, get_font, linespace, \
    parse_blend_mode, CHROME_PX, SCROLL_STEP
import OpenGL.GL as GL
from lab12 import MeasureTime
from lab13 import diff_styles, \
    CompositedLayer, absolute_bounds, absolute_bounds_for_obj, \
    DrawCompositedLayer, Task, TaskRunner, SingleThreadedTaskRunner, \
    clamp_scroll, add_parent_pointers, \
    DisplayItem, DrawText, \
    DrawLine, paint_visual_effects, WIDTH, HEIGHT, INPUT_WIDTH_PX, \
    REFRESH_RATE_SEC, HSTEP, VSTEP, SETTIMEOUT_CODE, XHR_ONLOAD_CODE, \
    Transform, ANIMATED_PROPERTIES, SaveLayer

from lab14 import parse_color, parse_outline, draw_rect, DrawRRect, \
    is_focused, paint_outline, has_outline, \
    device_px, cascade_priority, style, \
    is_focusable, get_tabindex, announce_text, speak_text, \
    CSSParser, DrawOutline

def request(url, top_level_url, payload=None):
    scheme, url = url.split("://", 1)
    assert scheme in ["http", "https"], \
        "Unknown scheme {}".format(scheme)

    if "/" not in url:
        url = url + "/"
    host, path = url.split("/", 1)

    path = "/" + path
    port = 80 if scheme == "http" else 443

    if ":" in host:
        host, port = host.split(":", 1)
        port = int(port)

    s = socket.socket(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
    )
    s.connect((host, port))

    if scheme == "https":
        ctx = ssl.create_default_context()
        s = ctx.wrap_socket(s, server_hostname=host)

    method = "POST" if payload else "GET"
    body = "{} {} HTTP/1.0\r\n".format(method, path)
    body += "Host: {}\r\n".format(host)
    if host in COOKIE_JAR:
        cookie, params = COOKIE_JAR[host]
        allow_cookie = True
        if top_level_url and params.get("samesite", "none") == "lax":
            _, _, top_level_host, _ = top_level_url.split("/", 3)
            if ":" in top_level_host:
                top_level_host, _ = top_level_host.split(":", 1)
            allow_cookie = (host == top_level_host or method == "GET")
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
        COOKIE_JAR[host] = (cookie, params)

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

class LayoutObject:
    def __init__(self):
        pass

    def dispatch(self, x, y):
        return False

class DocumentLayout(LayoutObject):
    def __init__(self, node, frame):
        super().__init__()
        self.node = node
        self.frame = frame
        node.layout_object = self
        self.parent = None
        self.previous = None
        self.children = []

    def layout(self, zoom, width):
        child = BlockLayout(self.node, self, None, self.frame)
        self.children.append(child)

        self.width = width - 2 * device_px(HSTEP, zoom)
        self.x = device_px(HSTEP, zoom)
        self.y = device_px(VSTEP, zoom)
        child.layout(zoom)
        self.height = child.height + 2* device_px(VSTEP, zoom)

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

def font(node, zoom):
    weight = node.style["font-weight"]
    style = node.style["font-style"]
    font_size = device_px(float(node.style["font-size"][:-2]), zoom)
    return get_font(font_size, weight, font_size)

class BlockLayout(LayoutObject):
    def __init__(self, node, parent, previous, frame):
        super().__init__()
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
                next = BlockLayout(child, self, previous, self.frame)
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
            elif node.tag == "img":
                self.image(node, zoom)
            elif node.tag == "iframe":
                self.iframe(node, zoom)
            else:
                for child in node.children:
                    self.recurse(child, zoom)

    def new_line(self):
        self.previous_word = None
        self.cursor_x = self.x
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line)
        self.children.append(new_line)

    def add_inline_child(self, node, zoom, w, child_class, frame, word=None):
        if self.cursor_x + w > self.x + self.width:
            self.new_line()
        line = self.children[-1]
        if word:
            child = child_class(node, line, self.previous_word, word)
        else:
            child = child_class(node, line, self.previous_word, frame)
        line.children.append(child)
        self.previous_word = child
        self.cursor_x += w + font(node, zoom).measureText(" ")

    def text(self, node, zoom):
        node_font = font(node, zoom)
        for word in node.text.split():
            w = node_font.measureText(word)
            self.add_inline_child(node, zoom, w, TextLayout, self.frame, word)

    def input(self, node, zoom):
        w = device_px(INPUT_WIDTH_PX, zoom)
        self.add_inline_child(node, zoom, w, InputLayout, self.frame) 

    def image(self, node, zoom):
        if "width" in node.attributes:
            w = device_px(int(node.attributes["width"]), zoom)
        else:
            w = device_px(node.image.width(), zoom)
        self.add_inline_child(node, zoom, w, ImageLayout, self.frame)

    def iframe(self, node, zoom):
        if "width" in self.node.attributes:
            w = device_px(int(self.node.attributes["width"]), zoom)
        else:
            w = IFRAME_WIDTH_PX + 2
        self.add_inline_child(node, zoom, w, IframeLayout, self.frame)

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
                radius = float(self.node.style.get(
                    "border-radius", "0px")[:-2])
                cmds.append(DrawRRect(rect, radius, bgcolor))
 
        for child in self.children:
            child.paint(cmds)

        if not is_atomic:
            paint_outline(self.node, cmds, rect)
            cmds = paint_visual_effects(self.node, cmds, rect)
        display_list.extend(cmds)

    def dispatch(self, x, y):
        if isinstance(self.node, Element) and is_focusable(self.node):
            self.frame.focus_element(self.node)
            self.frame.activate_element(self.node)
            self.frame.set_needs_render()
            return True
        return False

    def __repr__(self):
        return "BlockLayout(x={}, y={}, width={}, height={}, node={})".format(
            self.x, self.x, self.width, self.height, self.node)

class EmbedLayout(LayoutObject):
    def __init__(self, node, frame, parent, previous):
        super().__init__()
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

    def layout(self, zoom):
        self.font = font(self.node, zoom)
        if self.previous:
            space = self.previous.font.measureText(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

class InputLayout(EmbedLayout):
    def __init__(self, node, parent, previous, frame):
        super().__init__(node, frame, parent, previous)

    def layout(self, zoom):
        super().layout(zoom)

        self.width = device_px(INPUT_WIDTH_PX, zoom)
        self.height = linespace(self.font)

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

        if self.node.is_focused and self.node.tag == "input":
            cx = rect.left() + self.font.measureText(text)
            cmds.append(DrawLine(cx, rect.top(), cx, rect.bottom()))

        paint_outline(self.node, cmds, rect)
        cmds = paint_visual_effects(self.node, cmds, rect)
        display_list.extend(cmds)

    def dispatch(self, x, y):
        self.frame.focus_element(self.node)
        self.frame.activate_element(self.node)
        self.frame.set_needs_render()
        return True

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
            paint_outline(outline_node, display_list, outline_rect)

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

    def layout(self, zoom):
        self.font = font(self.node, zoom)

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
        super().__init__(node, frame, parent, previous)

    def layout(self, zoom):
        super().layout(zoom)

        aspect_ratio = self.node.image.width() / self.node.image.height()
        has_width = "width" in self.node.attributes
        has_height = "height" in self.node.attributes

        if has_width:
            self.width = \
                device_px(int(self.node.attributes["width"]), zoom)
        elif has_height:
            self.width = aspect_ratio * \
                device_px(int(self.node.attributes["height"]), zoom)
        else:
            self.width = device_px(self.node.image.width(), zoom)
    
        if has_height:
            self.img_height = \
                device_px(int(self.node.attributes["height"]), zoom)
        elif has_width:
            self.img_height = (1 / aspect_ratio) * \
                device_px(int(self.node.attributes["width"]), zoom)
        else:
            self.img_height = device_px(self.node.image.height(), zoom)

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
        super().__init__(node, parent_frame, parent, previous)

    def layout(self, zoom):
        super().layout(zoom)

        width_attr = self.node.attributes.get("width")
        height_attr = self.node.attributes.get("height")

        if width_attr:
            self.width = device_px(int(width_attr), zoom)
        else:
            self.width = device_px(IFRAME_WIDTH_PX + 2, zoom)

        if height_attr:
            self.height = device_px(int(height_attr), zoom)
        else:
            self.height = device_px(IFRAME_HEIGHT_PX + 2, zoom)

        self.node.frame.frame_height = self.height - 2
        self.node.frame.frame_width = self.width - 2

    def paint(self, display_list):
        frame_cmds = []

        rect = skia.Rect.MakeLTRB(
            self.x, self.y,
            self.x + self.width, self.y + self.height)
        bgcolor = self.node.style.get("background-color",
                                 "transparent")
        if bgcolor != "transparent":
            radius = float(
                self.node.style.get("border-radius", "0px")[:-2])
            frame_cmds.append(DrawRRect(rect, radius, bgcolor))

        if self.node.frame:
            self.node.frame.paint(frame_cmds)

        offset = (self.x + 1, self.y + 1)
        cmds = [Transform(offset, rect, self.node, frame_cmds)]
        paint_outline(self.node, cmds, rect)
        cmds = paint_visual_effects(self.node, cmds, rect)
        display_list.extend(cmds)

    def dispatch(self, x, y):
        self.node.frame.click(x - self.x, y - self.y)
        return True

    def __repr__(self):
        return "IframeLayout(src={}, x={}, y={}, width={}, height={})".format(
            self.node.attributes["src"], self.x, self.y, self.width, self.height)

def download_image(image_src, frame):
    image_url = resolve_url(image_src, frame.url)
    assert frame.allowed_request(image_url), \
        "Blocked load of " + image_url + " due to CSP"
    try:
        header, body = request(image_url, frame.url)
        data = skia.Data.MakeWithoutCopy(body)
    except:
        data = skia.Data.MakeFromFileName("Broken_Image.png")
        body = ""
    img = skia.Image.MakeFromEncoded(data)
    assert img, "Failed to recognize image format for " + image_url
    return body, img

class AttributeParser:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def whitespace(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    def literal(self, literal):
        if self.s[self.i] == literal:
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
            elif in_quote and cur.isspace():
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
                attriubutes[key.lower()] = ""
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

def wrap_in_window(js, window_id):
    return ("window = window_{window_id}; " + \
    "with (window) {{ {js} }}").format(js=js, window_id=window_id)

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
        self.interp.export_function("parent", self.parent)
        self.interp.export_function("postMessage", self.postMessage)

        self.node_to_handle = {}
        self.handle_to_node = {}

    def add_window(self, frame):
        self.interp.evaljs(
            "var window_{window_id} = \
                new Window({window_id});".format(
                window_id=frame.window_id))

    def run(self, script, code, window_id):
        try:
            print("Script returned: ", self.interp.evaljs(
               wrap_in_window(code, window_id)))
        except dukpy.JSRuntimeError as e:
            print("Script", script, "crashed", e)
        self.current_window = None

    def dispatch_event(self, type, elt, window_id):
        handle = self.node_to_handle.get(elt, -1)
        do_default = self.interp.evaljs(
            wrap_in_window(EVENT_DISPATCH_CODE, window_id),
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
        selector = CSSParser(selector_text).selector()
        nodes = [node for node
                 in tree_to_list(frame.nodes, [])
                 if selector.matches(node)]
        return [self.get_handle(node) for node in nodes]

    def getAttribute(self, handle, attr):
        elt = self.handle_to_node[handle]
        return elt.attributes.get(attr, None)

    def parent(self, window_id):
        parent_frame = \
            self.tab.window_id_to_frame[window_id].parent_frame
        if not parent_frame:
            return None
        return parent_frame.window_id

    def dispatch_post_message(self, message, window_id):
        self.interp.evaljs(
            wrap_in_window(
                "dispatchEvent(new PostMessageEvent(dukpy.data))",
                window_id),
            data=message)

    def postMessage(self, target_window_id, message, origin):
        task = Task(self.tab.post_message, message, target_window_id)
        self.tab.task_runner.schedule_task(task)

    def innerHTML_set(self, handle, s, window_id):
        doc = HTMLParser(
            "<html><body>" + s + "</body></html>").parse()
        new_nodes = doc.children[0].children
        elt = self.handle_to_node[handle]
        elt.children = new_nodes
        for child in elt.children:
            child.parent = elt
        frame = self.tab.window_id_to_frame[window_id]        
        frame.set_needs_render()

    def style_set(self, handle, s, window_id):
        elt = self.handle_to_node[handle]
        elt.attributes["style"] = s;
        frame = self.tab.window_id_to_frame[window_id]        
        frame.set_needs_render()

    def dispatch_settimeout(self, handle, window_id):
        self.interp.evaljs(
            wrap_in_window(SETTIMEOUT_CODE, window_id), handle=handle)

    def setTimeout(self, handle, time, window_id):
        def run_callback():
            task = Task(self.dispatch_settimeout, handle, window_id)
            self.tab.task_runner.schedule_task(task)
        threading.Timer(time / 1000.0, run_callback).start()

    def dispatch_xhr_onload(self, out, handle, window_id):
        do_default = self.interp.evaljs(
            XHR_ONLOAD_CODE, out=out, handle=handle)

    def XMLHttpRequest_send(
        self, method, url, body, isasync, handle, window_id):
        full_url = resolve_url(url, self.tab.url)
        frame = self.tab.window_id_to_frame[window_id]        
        if not frame.allowed_request(full_url):
            raise Exception("Cross-origin XHR blocked by CSP")
        if url_origin(full_url) != url_origin(self.tab.url):
            raise Exception(
                "Cross-origin XHR request not allowed")

        def run_load():
            headers, response = request(
                full_url, self.tab.url, payload=body)
            response = response.decode("utf8")
            task = Task(self.dispatch_xhr_onload, response, handle, window_id)
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
                frame.set_needs_render()
                AnimationClass = ANIMATED_PROPERTIES[property]
                animation = AnimationClass(
                    old_value, new_value, num_frames)
                node.animations[property] = animation
                node.style[property] = animation.animate()

    for child in node.children:
        style(child, rules, frame)

class AccessibilityTree:
    def __init__(self, frame):
        self.root_node = AccessibilityNode(frame.nodes)
        self.width = frame.frame_width
        self.height = frame.frame_height
        self.scroll = frame.scroll

    def build(self):
        self.root_node.build()

    def to_list(self, list):
        return self.root_node.to_list(list)

    def hit_test(self, x, y):
        if x > self.width or y > self.height:
            return None
        y += self.scroll
        nodes = []
        self.root_node.hit_test(x, y, nodes)
        if nodes:
            return nodes[-1]

class AccessibilityNode:
    def __init__(self, node):
        self.node = node
        self.children = []
        self.text = None
        self.child_tree = None

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
        if isinstance(self.node, Element) \
            and self.node.tag == "iframe":
            self.child_tree = AccessibilityTree(self.node.frame)
            self.child_tree.build()
            return

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

    def hit_test(self, x, y, nodes):
        if self.intersects(x, y):
            nodes.append(self)
        if self.child_tree:
            child_node = self.child_tree.hit_test(
                x - self.bounds.x(), y - self.bounds.y())
            if child_node:
                nodes.append(child_node)
        for child in self.children:
            child.hit_test(x, y, nodes)

    def to_list(self, list):
        list.append(self)
        if self.child_tree:
            self.child_tree.to_list(list)
            return list
        for child in self.children:
            child.to_list(list)
        return list

    def __repr__(self):
        return "AccessibilityNode(node={} role={} text={}".format(
            str(self.node), self.role, self.text)


WINDOW_COUNT = 0

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

        global WINDOW_COUNT
        self.window_id = WINDOW_COUNT
        WINDOW_COUNT += 1
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
            url_origin(url) in self.allowed_origins

    def get_js(self):
        if self.js:
            return self.js
        else:
            return self.parent_frame.get_js()

    def load(self, url, body=None):
        self.zoom = 1
        self.scroll = 0
        self.scroll_changed_in_frame = True
        headers, body = request(url, self.url, payload=body)
        body = body.decode("utf8")
        self.url = url

        self.allowed_origins = None
        if "content-security-policy" in headers:
           csp = headers["content-security-policy"].split()
           if len(csp) > 0 and csp[0] == "default-src":
               self.allowed_origins = csp[1:]

        self.nodes = HTMLParser(body).parse()

        if not self.parent_frame or wbetools.FORCE_CROSS_ORIGIN_IFRAMES or \
            url_origin(self.url) != url_origin(self.parent_frame.url):
            self.js = JSContext(self.tab)
            self.js.interp.evaljs(\
                "function Window(id) { this._id = id };")
        js = self.get_js()
        js.add_window(self)

        with open("runtime15.js") as f:
            wrapped = wrap_in_window(f.read(), self.window_id)
            js.interp.evaljs(wrapped)

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
            body = body.decode("utf8")
            task = Task(\
                self.get_js().run, script_url, body,
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
            style_url = resolve_url(link, url)
            if not self.allowed_request(style_url):
                print("Blocked style", link, "due to CSP")
                continue
            try:
                header, body = request(style_url, url)
            except:
                continue
            self.rules.extend(CSSParser(body.decode("utf8")).parse())

        images = [node
                   for node in tree_to_list(self.nodes, [])
                   if isinstance(node, Element)
                   and node.tag == "img"
                   and "src" in node.attributes]
        for img in images:
            img.image = None
            image_url = resolve_url(img.attributes["src"], self.url)
            assert self.allowed_request(image_url), \
                "Blocked load of " + image_url + " due to CSP"
            try:
                header, body = request(image_url, self.url)
                data = skia.Data.MakeWithoutCopy(body)
            except:
                data = skia.Data.MakeFromFileName("Broken_Image.png")
                body = ""
            image = skia.Image.MakeFromEncoded(data)
            assert image, "Failed to recognize image format for " + image_url
            img.encoded_data = body
            img.image = image

        iframes = [node
                   for node in tree_to_list(self.nodes, [])
                   if isinstance(node, Element)
                   and node.tag == "iframe"
                   and "src" in node.attributes]
        for iframe in iframes:
            document_url = resolve_url(iframe.attributes["src"],
                self.tab.root_frame.url)
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
            self.style()
            self.needs_layout = True
            self.needs_style = False

        if self.needs_layout:
            self.layout(
                self.tab.zoom)
            if self.tab.accessibility_is_on:
                self.tab.needs_accessibility = True
            else:
                self.needs_paint = True
            self.needs_layout = False

    def style(self):
        style(self.nodes,
            sorted(self.rules,
                key=cascade_priority), self)

    def layout(self, zoom):
        self.document = DocumentLayout(self.nodes, self)
        self.document.layout(zoom, self.frame_width)

        clamped_scroll = self.clamp_scroll(self.scroll)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_frame = True

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
            url = resolve_url(elt.attributes["href"], self.url)
            self.load(url)
        elif elt.tag == "button":
            while elt:
                if elt.tag == "form" and "action" in elt.attributes:
                    self.submit_form(elt)
                    return
                elt = elt.parent

    def clamp_scroll(self, scroll):
        return max(0, min(
            scroll,
            math.ceil(
                self.document.height) - self.frame_height))

    def submit_form(self, elt):
        if self.get_js().dispatch_event(
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

        url = resolve_url(elt.attributes["action"], self.url)
        self.load(url, body)

    def keypress(self, char):
        if self.tab.focus and self.tab.focus.tag == "input":
            if not "value" in self.tab.focus.attributes:
                self.activate_element(self.tab.focus)
            if self.get_js().dispatch_event(
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
        if elt and self.get_js().dispatch_event(
            "click", elt, self.window_id): return
        while elt:
            if elt.layout_object and elt.layout_object.dispatch(x, y):
                return
            elt = elt.parent

class Tab:
    def __init__(self, browser):
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
        self.task_runner.start()

        self.measure_render = MeasureTime("render")
        self.composited_updates = []
        self.zoom = 1.0

        self.window_id_to_frame = {}

    def load(self, url, body=None):
        self.history.append(url)
        self.task_runner.clear_pending_tasks()
        self.root_frame = Frame(self, None, None)
        self.root_frame.load(url, body)
        self.root_frame.frame_width = WIDTH
        self.root_frame.frame_height = HEIGHT - CHROME_PX

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
            frame.get_js().interp.evaljs(
                wrap_in_window("__runRAFHandlers()", window_id))
    
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

        commit_data = CommitData(
            url=self.root_frame.url,
            scroll=scroll,
            root_frame_focused=not self.focused_frame or \
                (self.focused_frame == self.root_frame),
            height=math.ceil(self.root_frame.document.height),
            display_list=self.display_list,
            composited_updates=composited_updates,
            accessibility_tree=self.accessibility_tree,
            focus=self.focus
        )
        self.display_list = None
        self.root_frame.scroll_changed_in_frame = False

        self.browser.commit(self, commit_data)

    def render(self):
        self.measure_render.start()

        for id, frame in self.window_id_to_frame.items():
            frame.render()

        if self.needs_accessibility:
            self.accessibility_tree = AccessibilityTree(self.root_frame)
            self.accessibility_tree.build()
            self.needs_accessibility = False
            self.needs_paint = True

        if self.needs_paint:
            self.display_list = []
            self.root_frame.paint(self.display_list)
            self.needs_paint = False

        self.measure_render.stop()

    def click(self, x, y):
        self.render()
        self.root_frame.click(x, y)

    def keypress(self, char):
        frame = self.focused_frame
        if not frame: frame = self.root_frame
        frame.keypress(char)

    def scrolldown(self):
        frame = self.focused_frame
        if not frame: frame = self.root_frame
        frame.scrolldown()
        self.set_needs_accessibility()
        self.set_needs_paint()

    def enter(self):
        if self.focus:
            self.activate_element(self.focus)

    def get_tabindex(node):
        return int(node.attributes.get("tabindex", 9999999))

    def advance_tab(self):
        frame = self.focused_frame
        if not frame:
            frame = self.root_frame
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
        frame.get_js().dispatch_post_message(
            message, target_window_id)

def draw_line(canvas, x1, y1, x2, y2, color):
    sk_color = parse_color(color)
    path = skia.Path().moveTo(x1, y1).lineTo(x2, y2)
    paint = skia.Paint(Color=sk_color)
    paint.setStyle(skia.Paint.kStroke_Style)
    paint.setStrokeWidth(1)
    canvas.drawPath(path, paint)

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
            node for node in self.accessibility_tree.to_list([])
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
                    self.accessibility_tree.to_list([])
                if node.node == old_node.node
                and node.role == "alert"
            ]
            if new_nodes:
                new_spoken_alerts.append(new_nodes[0])
        self.spoken_alerts = new_spoken_alerts

        if self.tab_focus and \
            self.tab_focus != self.last_tab_focus:
            nodes = [node for node in \
                self.accessibility_tree.to_list([])
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
            self.lock.release()
            return
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.scrolldown)
        active_tab.task_runner.schedule_task(task)
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
        self.clear_data()
        self.needs_animation_frame = True

    def go_back(self):
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.go_back)
        active_tab.task_runner.schedule_task(task)
        self.clear_data()

    def add_tab(self):
        self.load("https://browser.engineering/")

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
        tree_list = self.accessibility_tree.to_list([])
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
                self.add_tab()
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
            self.schedule_load(self.address_bar)
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
        new_tab = Tab(self)
        self.set_active_tab(len(self.tabs))
        self.tabs.append(new_tab)
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
    parser.add_argument("--force_cross_origin_iframes", action="store_true",
        default=False, help="Whether to treat all iframes as cross-origin")
    args = parser.parse_args()

    wbetools.USE_BROWSER_THREAD = not args.single_threaded
    wbetools.USE_GPU = not args.disable_gpu
    wbetools.USE_COMPOSITING = not args.disable_compositing and not args.disable_gpu
    wbetools.SHOW_COMPOSITED_LAYER_BORDERS = args.show_composited_layer_borders
    wbetools.FORCE_CROSS_ORIGIN_IFRAMES = args.force_cross_origin_iframes

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
                    elif event.key.keysym.sym == sdl2.SDLK_TAB:
                        browser.cycle_tabs()
                    elif event.key.keysym.sym == sdl2.SDLK_a:
                        browser.toggle_accessibility()
                    elif event.key.keysym.sym == sdl2.SDLK_d:
                        browser.toggle_dark_mode()
                    elif event.key.keysym.sym == sdl2.SDLK_m:
                        browser.toggle_mute()
                    elif event.key.keysym.sym == sdl2.SDLK_t:
                        browser.add_tab()
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
