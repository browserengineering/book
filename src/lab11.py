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
import skia
import PIL.Image
import socket
import ssl
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
from lab6 import TagSelector
from lab6 import DescendantSelector
from lab10 import url_origin
from lab10 import JSContext

COOKIE_JAR = {}

def request(url, top_level_url, payload=None):
    scheme, url = url.split("://", 1)
    assert scheme in ["http", "https"], \
        "Unknown scheme {}".format(scheme)

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

    if headers.get(
        'content-type',
        'application/octet-stream').startswith("text"):
        body = response.read().decode("utf8")
    else:
        body = response.read()

    s.close()

    return headers, body

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

def parse_blend_mode(blend_mode_str):
    if blend_mode_str == "multiply":
        return skia.BlendMode.kMultiply
    elif blend_mode_str == "difference":
        return skia.BlendMode.kDifference
    else:
        return skia.BlendMode.kSrcOver

def parse_clip_path(clip_path_str):
    if clip_path_str.find("circle") != 0:
        return None
    return int(clip_path_str[7:][:-2])

def linespace(font):
    metrics = font.getMetrics()
    return metrics.fDescent - metrics.fAscent

class SaveLayer:
    def __init__(self, sk_paint, rect):
        self.sk_paint = sk_paint
        self.rect = rect

    def execute(self, canvas):
        canvas.saveLayer(paint=self.sk_paint)

class Save:
    def __init__(self, rect):
        self.rect = rect

    def execute(self, canvas):
        canvas.save()

class Restore:
    def __init__(self, rect):
        self.rect = rect

    def execute(self, canvas):
        canvas.restore()

class CircleMask:
    def __init__(self, cx, cy, radius, rect):
        self.cx = cx
        self.cy = cy
        self.radius = radius
        self.rect = rect

    def execute(self, canvas):
        canvas.saveLayer(paint=skia.Paint(
            Alphaf=1.0, BlendMode=skia.kDstIn))
        canvas.drawCircle(
            self.cx, self.cy,
            self.radius, skia.Paint(Color=skia.ColorWHITE))
        canvas.restore()

def center_point(rect):
    return (rect.left() + (rect.right() - rect.left()) / 2,
        rect.top() + (rect.bottom() - rect.top()) / 2)

class Translate:
    def __init__(self, x, y, rect):
        self.x = x
        self.y = y
        self.rect = rect

    def execute(self, canvas):
        paint_rect = skia.Rect.MakeLTRB(
            self.rect.left(), self.rect.top(),
            self.rect.right(), self.rect.bottom())
        canvas.translate(self.x, self.y)

class DrawText:
    def __init__(self, x1, y1, text, font, color):
        self.top = y1
        self.left = x1
        self.right = x1 + font.measureText(text)
        self.bottom = self.top - font.getMetrics().fAscent + font.getMetrics().fDescent
        self.rect = skia.Rect.MakeLTRB(self.top, self.right, self.right, self.bottom)
        self.font = font
        self.text = text
        self.color = color

    def execute(self, canvas):
        draw_text(canvas, self.left, self.top,
            self.text, self.font)

    def __repr__(self):
        return "DrawText(text={})".format(self.text)

class DrawRect:
    def __init__(self, rect, color):
        self.rect = rect
        self.top = rect.top()
        self.left = rect.left()
        self.bottom = rect.bottom()
        self.right = rect.right()
        self.color = color

    def execute(self, canvas):
        draw_rect(canvas,
            self.left, self.top,
            self.right, self.bottom,
            fill=self.color, width=0)

    def __repr__(self):
        return "DrawRect(top={} left={} bottom={} right={} color={})".format(
            self.left, self.top, self.right, self.bottom, self.color)

def draw_line(canvas, x1, y1, x2, y2):
    path = skia.Path().moveTo(x1, y1).lineTo(x2, y2)
    paint = skia.Paint(Color=skia.ColorBLACK)
    paint.setStyle(skia.Paint.kStroke_Style)
    paint.setStrokeWidth(1);
    canvas.drawPath(path, paint)

def draw_text(canvas, x, y, text, font, color=None):
    sk_color = color_to_sk_color(color)
    paint = skia.Paint(AntiAlias=True, Color=sk_color)
    canvas.drawString(
        text, float(x), y - font.getMetrics().fAscent,
        font, paint)

def draw_rect(canvas, l, t, r, b, fill=None, width=1):
    paint = skia.Paint()
    if fill:
        paint.setStrokeWidth(width);
        paint.setColor(color_to_sk_color(fill))
    else:
        paint.setStyle(skia.Paint.kStroke_Style)
        paint.setStrokeWidth(1);
        paint.setColor(skia.ColorBLACK)
    rect = skia.Rect.MakeLTRB(l, t, r, b)
    canvas.drawRect(rect, paint)

class ClipRect:
    def __init__(self, rect):
        self.rect = rect

    def execute(self, canvas):
        canvas.clipRect(skia.Rect.MakeLTRB(
            self.rect.left(), self.rect.top(),
            self.rect.right(), self.rect.bottom()))

class ClipRRect:
    def __init__(self, rect, radius):
        self.rect = rect
        self.radius = radius

    def execute(self, canvas):
        canvas.clipRRect(
            skia.RRect.MakeRectXY(
                skia.Rect.MakeLTRB(
                    self.rect.left(),
                    self.rect.top(),
                    self.rect.right(),
                    self.rect.bottom()),
                self.radius, self.radius))

class DrawImage:
    def __init__(self, image, rect):
        self.image = image
        self.rect = rect

    def execute(self, canvas):
        canvas.drawImage(
            self.image, self.rect.left(),
            self.rect.top())

class DrawImageRect:
    def __init__(self, image, rect):
        self.image = image
        self.rect = rect

    def execute(self, canvas):
        source_rect = skia.Rect.Make(self.image.bounds())
        dest_rect = skia.Rect.MakeLTRB(
            self.rect.left(),
            self.rect.top(),
            self.rect.right(),
            self.rect.bottom())
        canvas.drawImageRect(
            self.image, source_rect, dest_rect)

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

def font_style(weight, style):
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
        self.font = None

    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = float(self.node.style["font-size"][:-2])
        self.font = skia.Font(
            skia.Typeface('Arial', font_style(weight, style)), size)

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
        size = int(self.node.style["font-size"][:-2])
        self.font = skia.Font(
            skia.Typeface('Arial', font_style(weight, style)), size)

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
        paint_x = self.x
        paint_y = self.y

        rect = skia.Rect.MakeLTRB(
            paint_x, paint_y, paint_x + self.width,
            paint_y + self.height)

        restore_count = paint_visual_effects(self.node, display_list, rect)

        paint_background(self.node, display_list, rect)

        if self.node.tag == "input":
            text = self.node.attributes.get("value", "")
        elif self.node.tag == "button":
            text = self.node.children[0].text

        color = self.node.style["color"]
        display_list.append(
            DrawText(paint_x, paint_y, text, self.font, color))

        paint_clip_path(self.node, display_list, rect)

        for i in range(0, restore_count):
            display_list.append(Restore(rect))

    def __repr__(self):
        return "InputLayout(x={}, y={}, width={}, height={})".format(
            self.x, self.y, self.width, self.height)

def style_length(node, style_name, default_value):
    style_val = node.style.get(style_name)
    if style_val:
        return int(style_val[:-2])
    else:
        return default_value

def paint_clip_path(node, display_list, rect):
    clip_path = node.style.get("clip-path")
    if clip_path:
        percent = parse_clip_path(clip_path)
        if percent:
            width = rect.right() - rect.left()
            height = rect.bottom() - rect.top()
            reference_val = \
                math.sqrt(width * width + 
                    height * height) / math.sqrt(2)
            radius = reference_val * percent / 100
            (center_x, center_y) = center_point(rect)
            display_list.append(CircleMask(
                center_x, center_y, radius, rect))

def paint_visual_effects(node, display_list, rect):
    restore_count = 0
    
    blend_mode_str = node.style.get("mix-blend-mode")
    blend_mode = skia.BlendMode.kSrcOver
    if blend_mode_str:
        blend_mode = parse_blend_mode(blend_mode_str)

    opacity = float(node.style.get("opacity", "1.0"))
    if opacity != 1.0 or blend_mode_str:
        paint = skia.Paint(Alphaf=opacity, BlendMode=blend_mode)
        display_list.append(SaveLayer(paint, rect))
        restore_count = restore_count + 1

    clip_path = node.style.get("clip-path")
    if clip_path:
        display_list.append(SaveLayer(skia.Paint(), rect))
        restore_count = restore_count + 1

    border_radius = node.style.get("border-radius")
    if border_radius:
        radius = int(border_radius[:-2])
        display_list.append(Save(rect))
        display_list.append(ClipRRect(rect, radius))
        restore_count = restore_count + 1

    return restore_count

def paint_background(node, display_list, rect):
    bgcolor = node.style.get("background-color",
                             "transparent")
    if bgcolor != "transparent":
        display_list.append(DrawRect(rect, bgcolor))

    background_image = node.style.get("background-image")
    if background_image:
        background_size = node.style.get("background-size")
        if background_size and background_size == "contain":
            display_list.append(DrawImageRect(node.background_image, rect))
        else:
            display_list.append(Save(rect))
            display_list.append(ClipRect(rect))
            display_list.append(DrawImage(node.background_image,
                rect))
            display_list.append(Restore(rect))

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
        paint_x = self.x
        paint_y = self.y

        rect = skia.Rect.MakeLTRB(
            paint_x, paint_y,
            paint_x + self.width, paint_y + self.height)

        restore_count = paint_visual_effects(
            self.node, display_list, rect)

        paint_background(self.node, display_list, rect)

        for child in self.children:
            child.paint(display_list)

        paint_clip_path(self.node, display_list, rect)

        for i in range(0, restore_count):
            display_list.append(Restore(rect))

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

    def get_font(self, node):
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        size = float(node.style["font-size"][:-2])
        return skia.Font(
            skia.Typeface('Arial', font_style(weight, style)), size)

    def text(self, node):
        font = self.get_font(node)
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
        size = int(float(node.style["font-size"][:-2]) * .75)
        font = self.get_font(node)
        self.cursor_x += w + font.measureText(" ")

    def paint(self, display_list):
        paint_x = self.x
        paint_y = self.y

        rect = skia.Rect.MakeLTRB(
            paint_x, paint_y, paint_x + self.width,
            paint_y + self.height)

        restore_count = paint_visual_effects(self.node, display_list, rect)

        paint_background(self.node, display_list, rect)

        for child in self.children:
            child.paint(display_list)

        paint_clip_path(self.node, display_list, rect)

        for i in range(0, restore_count):
            display_list.append(Restore(rect))

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
        while self.i < len(self.s):
            cur = self.s[self.i]
            if cur.isalnum() or cur in "/#-.%()\"'":
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

def parse_style_url(url_str):
    return url_str[5:][:-2]

def get_image(image_url, base_url):
    header, body_bytes = request(
        resolve_url(image_url, base_url), base_url)
    picture_stream = io.BytesIO(body_bytes)

    pil_image = PIL.Image.open(picture_stream)
    if pil_image.mode == "RGBA":
        pil_image_bytes = pil_image.tobytes()
    else:
        pil_image_bytes = pil_image.convert("RGBA").tobytes()
    return skia.Image.frombytes(
        array=pil_image_bytes,
        dimensions=pil_image.size,
        colorType=skia.kRGBA_8888_ColorType)

def style(node, rules, url):
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
    
    if node.style.get('background-image'):
        node.background_image = \
            get_image(parse_style_url(
                node.style.get('background-image')), url)
    for child in node.children:
        style(child, rules, url)

SCROLL_STEP = 100
CHROME_PX = 100

class Tab:
    def __init__(self):
        self.history = []
        self.focus = None
        self.url = None
        self.scroll = 0

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
            style_url = resolve_url(link, url)
            if not self.allowed_request(style_url):
                print("Blocked style", link, "due to CSP")
                continue
            try:
                header, body = request(style_url, url)
            except:
                continue
            self.rules.extend(CSSParser(body).parse())

        self.render()

    def render(self):
        style(self.nodes, sorted(self.rules, key=cascade_priority),
            self.url)
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        self.document.paint(self.display_list)

    def raster(self, canvas):
        for cmd in self.display_list:
            cmd.execute(canvas)

        if self.focus:
            obj = [obj for obj in tree_to_list(self.document, [])
                   if obj.node == self.focus][0]
            text = self.focus.attributes.get("value", "")
            x = obj.x + obj.font.measureText(text)
            y = obj.y
            draw_line(canvas, x, y, x, y + obj.height)

    def display_list_bounds(self):
        bounds = skia.Rect()
        for cmd in self.display_list:
            bounds.join(cmd.rect)
        return bounds

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
        self.sdl_window = sdl2.SDL_CreateWindow(b"Browser",
            sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
            WIDTH, HEIGHT, sdl2.SDL_WINDOW_SHOWN)
        self.root_surface = skia.Surface(WIDTH, HEIGHT)
        self.chrome_surface = skia.Surface(WIDTH, HEIGHT)
        self.tab_surface = None

        self.tabs = []
        self.active_tab = None
        self.focus = None
        self.address_bar = ""

    def handle_down(self):
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

    def handle_key(self, char):
        if not (0x20 <= ord(char) < 0x7f): return
        if self.focus == "address bar":
            self.address_bar += char
            self.draw()
        elif self.focus == "content":
            self.tabs[self.active_tab].keypress(char)
            self.draw()

    def handle_enter(self):
        if self.focus == "address bar":
            self.tabs[self.active_tab].load(self.address_bar)
            self.focus = None
            self.draw()

    def load(self, url):
        new_tab = Tab()
        new_tab.load(url)
        self.active_tab = len(self.tabs)
        self.tabs.append(new_tab)
        self.raster()
        self.draw()

    def raster(self):
        active_tab = self.tabs[self.active_tab]

        # Re-allocate the tab surface if its size changes.
        tab_bounds = active_tab.display_list_bounds()
        assert tab_bounds.top() >= 0
        assert tab_bounds.left() >= 0
        if not self.tab_surface or \
                tab_bounds.bottom() != self.tab_surface.height() or \
                tab_bounds.right() != self.tab_surface.width():
            self.tab_surface = skia.Surface(
                math.ceil(tab_bounds.right()),
                math.ceil(tab_bounds.bottom()))

        tab_canvas = self.tab_surface.getCanvas()
        tab_canvas.clear(skia.ColorWHITE)
        active_tab.raster(tab_canvas)

        self.raster_browser_chrome()

    def raster_browser_chrome(self):
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
        path = skia.Path().moveTo(15, 70).lineTo(30, 55).lineTo(30, 85)
        paint = skia.Paint(Color=skia.ColorBLACK, Style=skia.Paint.kFill_Style)
        canvas.drawPath(path, paint)

    def draw(self):
        root_canvas = self.root_surface.getCanvas()
        root_canvas = self.root_surface.getCanvas()
        root_canvas.clear(skia.ColorWHITE)
        
        root_canvas.save()
        root_canvas.clipRect(skia.Rect.MakeLTRB(
            0, CHROME_PX, WIDTH, HEIGHT))
        root_canvas.translate(
            0, CHROME_PX- self.tabs[self.active_tab].scroll)
        self.tab_surface.draw(root_canvas, 0, 0)
        root_canvas.restore()

        root_canvas.save()
        root_canvas.clipRect(skia.Rect.MakeLTRB(
            0, 0, WIDTH, CHROME_PX))
        self.chrome_surface.draw(root_canvas, 0, 0)
        root_canvas.restore()

        # Copy the results to the SDL surface:
        skia_image = self.root_surface.makeImageSnapshot()
        skia_bytes = skia_image.tobytes()
        rect = sdl2.SDL_Rect(0, 0, WIDTH, HEIGHT)

        depth = 32 # 4 bytes per pixel
        pitch = 4 * WIDTH # 4 * WIDTH pixels per line on-screen
        # Skia uses an ARGB format - alpha first byte, then
        # through to blue as the last byte.
        alpha_mask = 0xff000000
        red_mask = 0x00ff0000
        green_mask = 0x0000ff00
        blue_mask = 0x000000ff
        sdl_surface = sdl2.SDL_CreateRGBSurfaceFrom(
            skia_bytes, WIDTH, HEIGHT, depth, pitch,
            red_mask, green_mask, blue_mask, alpha_mask)


        window_surface = sdl2.SDL_GetWindowSurface(self.sdl_window)
        sdl2.SDL_BlitSurface(sdl_surface, rect, window_surface, rect)
        sdl2.SDL_UpdateWindowSurface(self.sdl_window)

    def handle_quit(self):
        sdl2.SDL_DestroyWindow(self.sdl_window)

if __name__ == "__main__":
    import sys

    sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
    browser = Browser()
    browser.load(sys.argv[1])

    event = sdl2.SDL_Event()
    while True:
        while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == sdl2.SDL_QUIT:
                browser.handle_quit()
                sdl2.SDL_Quit()
                sys.exit()
            elif event.type == sdl2.SDL_MOUSEBUTTONUP:
                browser.handle_click(event.button)
            elif event.type == sdl2.SDL_KEYDOWN:
                if event.key.keysym.sym == sdl2.SDLK_RETURN:
                    browser.handle_enter()
                elif event.key.keysym.sym == sdl2.SDLK_DOWN:
                    browser.handle_down()
            elif event.type == sdl2.SDL_TEXTINPUT:
                browser.handle_key(event.text.text.decode('utf8'))

