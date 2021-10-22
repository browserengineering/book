"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 12 (Adding Visual Effects),
without exercises.
"""

import ctypes
import dukpy
import io
import math
from sdl2 import *
import skia
import socket
import ssl
import urllib.parse
from PIL import Image
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

def request(url, headers={}, payload=None):
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
    for header, value in headers.items():
        body += "{}: {}\r\n".format(header, value)
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

def parse_rotation_transform(transform_str):
    left_paren = transform_str.find('(')
    right_paren = transform_str.find('deg)')
    return float(transform_str[left_paren + 1:right_paren])

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

class Rasterizer:
    def __init__(self, surface):
        self.surface = surface

    def clear(self, color):
        with self.surface as canvas:
            canvas.clear(color)

    def draw_rect(self, rect,
        fill=None, width=1):
        paint = skia.Paint()
        if fill:
            paint.setStrokeWidth(width);
            paint.setColor(color_to_sk_color(fill))
        else:
            paint.setStyle(skia.Paint.kStroke_Style)
            paint.setStrokeWidth(1);
            paint.setColor(skia.ColorBLACK)
        with self.surface as canvas:
            canvas.drawRect(rect, paint)

    def draw_polyline(self, x1, y1, x2, y2, x3=None,
        y3=None, fill=False):
        path = skia.Path()
        path.moveTo(x1, y1)
        path.lineTo(x2, y2)
        if x3:
            path.lineTo(x3, y3)
        paint = skia.Paint()
        paint.setColor(skia.ColorBLACK)
        if fill:
            paint.setStyle(skia.Paint.kFill_Style)
        else:
            paint.setStyle(skia.Paint.kStroke_Style)
        paint.setStrokeWidth(1);
        with self.surface as canvas:
            canvas.drawPath(path, paint)

    def draw_text(self, x, y, text, font, color=None):
        paint = skia.Paint(
            AntiAlias=True, Color=color_to_sk_color(color))
        with self.surface as canvas:
            canvas.drawString(
                text, x, y - font.getMetrics().fAscent,
                font, paint)

def linespace(font):
    metrics = font.getMetrics()
    return metrics.fDescent - metrics.fAscent

class SaveLayer:
    def __init__(self, sk_paint, rect):
        self.sk_paint = sk_paint
        self.rect = rect

    def execute(self, scroll, rasterizer):
        with rasterizer.surface as canvas:
            canvas.saveLayer(paint=self.sk_paint)

class Save:
    def __init__(self, rect):
        self.rect = rect

    def execute(self, scroll, rasterizer):
        with rasterizer.surface as canvas:
            canvas.save()

class Restore:
    def __init__(self, rect):
        self.rect = rect

    def execute(self, scroll, rasterizer):
        with rasterizer.surface as canvas:
            canvas.restore()

class CircleMask:
    def __init__(self, cx, cy, radius, rect):
        self.cx = cx
        self.cy = cy
        self.radius = radius
        self.rect = rect

    def execute(self, scroll, rasterizer):
        with rasterizer.surface as canvas:
            canvas.saveLayer(paint=skia.Paint(
                Alphaf=1.0, BlendMode=skia.kDstIn))
            canvas.drawCircle(
                self.cx, self.cy - scroll,
                self.radius, skia.Paint(Color=skia.ColorWHITE))
            canvas.restore()

class Rotate:
    def __init__(self, degrees, rect):
        self.degrees = degrees
        self.rect = rect

    def execute(self, scroll, rasterizer):
        with rasterizer.surface as canvas:
            canvas.rotate(self.degrees)

class DrawText:
    def __init__(self, x1, y1, text, font, color):
        self.font = font
        self.rect = skia.Rect.MakeLTRB(x1, y1, x1, y1 + linespace(self.font))
        self.text = text
        self.color = color

    def execute(self, scroll, rasterizer):
        rasterizer.draw_text(
            self.rect.left(), self.rect.top() - scroll,
            self.text,
            self.font,
            self.color,
        )

    def __repr__(self):
        return "DrawText(text={})".format(self.text)

class DrawRect:
    def __init__(self, rect, color):
        self.rect = rect
        self.color = color

    def execute(self, scroll, rasterizer):
        rasterizer.draw_rect(
            skia.Rect.MakeLTRB(
                self.rect.left(), self.rect.top() - scroll,
                self.rect.right(), self.rect.bottom() - scroll),
            width=0,
            fill=self.color,
        )

    def __repr__(self):
        (left, top, right, bottom) = tuple(self.rect)
        return "DrawRect(top={} left={} bottom={} right={} color={})".format(
            left, top, right, bottom, self.color)

class ClipRect:
    def __init__(self, rect):
        self.rect = rect

    def execute(self, scroll, rasterizer):
        with rasterizer.surface as canvas:
            canvas.clipRect(skia.Rect.MakeLTRB(
                self.rect.left(), self.rect.top() - scroll,
                self.rect.right(), self.rect.bottom() - scroll))

class ClipRRect:
    def __init__(self, rect, radius):
        self.rect = rect
        self.radius = radius

    def execute(self, scroll, rasterizer):
        with rasterizer.surface as canvas:
            canvas.clipRRect(
                skia.RRect.MakeRectXY(
                    skia.Rect.MakeLTRB(
                        self.rect.left(), self.rect.top() - scroll,
                        self.rect.right(), self.rect.bottom() - scroll),
                    self.radius, self.radius))

class DrawImage:
    def __init__(self, image, rect):
        self.image = image
        self.rect = rect

    def execute(self, scroll, rasterizer):
        with rasterizer.surface as canvas:
            canvas.drawImage(
                self.image, self.rect.left(),
                self.rect.top() - scroll)

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
        size = int(self.node.style["font-size"][:-2])
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

        self.width = style_length(self.node, "width", INPUT_WIDTH_PX)
        self.height = style_length(
            self.node, "height", linespace(self.font))

        if self.previous:
            space = self.previous.font.measureText(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

    def paint(self, display_list):
        (paint_x, paint_y) = paint_coords(self.node, self.x, self.y)

        rect = skia.Rect.MakeLTRB(
            paint_x, paint_y, paint_x + self.width,
            paint_y + self.height)

        paint_background(self.node, display_list, rect)

        if self.node.tag == "input":
            text = self.node.attributes.get("value", "")
        elif self.node.tag == "button":
            text = self.node.children[0].text

        color = self.node.style["color"]
        display_list.append(
            DrawText(self.x, self.y, text, self.font, color))

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
            reference_val = math.sqrt(width * width + height * height) / math.sqrt(2)
            center_x = rect.left() + (rect.right() - rect.left()) / 2
            center_y = rect.top() + (rect.bottom() - rect.top()) / 2
            radius = reference_val * percent / 100
            display_list.append(CircleMask(
                center_x, center_y, radius, rect))

def paint_visual_effects(node, display_list, rect):
    restore_count = 0
    
    transform_str = node.style.get("transform", "")
    if transform_str:
        display_list.append(Save(rect))
        restore_count = restore_count + 1
        degrees = parse_rotation_transform(transform_str)
        display_list.append(Rotate(degrees, rect))

    blend_mode_str = node.style.get("mix-blend-mode")
    blend_mode = skia.BlendMode.kSrcOver
    if blend_mode_str:
        blend_mode = parse_blend_mode(blend_mode_str)

    opacity = float(node.style.get("opacity", "1.0"))
    if opacity != 1.0 or blend_mode_str:
        paint = skia.Paint(Alphaf=opacity, BlendMode=blend_mode)
#            ImageFilter=skia.DropShadowImageFilter.Make(5, 5, 3, 3, skia.ColorBLACK,
#                skia.DropShadowImageFilter.kDrawShadowAndForeground_ShadowMode))
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
        display_list.append(Save(rect))
        display_list.append(ClipRect(rect))
        print(rect)
        display_list.append(DrawImage(node.background_image,
            rect))
        display_list.append(Restore(rect))

def paint_coords(node, x, y):
    if not node.style.get("position") == "relative":
        return (x, y)

    paint_x = x
    paint_y = y

    left = node.style.get("left")
    if left:
        paint_x = paint_x + int(left[:-2])
    top = node.style.get("top")
    if top:
        paint_y = paint_y + int(top[:-2])

    return (paint_x, paint_y)

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
        (paint_x, paint_y) = paint_coords(self.node, self.x, self.y)
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
        size = int(node.style["font-size"][:-2])
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
        (paint_x, paint_y) = paint_coords(self.node, self.x, self.y)

        rect = skia.Rect.MakeLTRB(
            paint_x, paint_y, paint_x + self.width,
            paint_y + self.height)

        restore_count = paint_visual_effects(self.node, display_list, rect)

        paint_background(self.node, display_list, rect)

        for child in self.children:
            child.paint(display_list)

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
            if self.s[self.i].isalnum() or self.s[self.i] in "#-.%()\"'":
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

def get_images(image_url_strs, base_url, images):
    for image_url_str in image_url_strs:
        image_url = parse_style_url(image_url_str)
        header, body_bytes = request(
            resolve_url(image_url, base_url),
            headers={})
        picture_stream = io.BytesIO(body_bytes)

        pil_image = Image.open(picture_stream)
        if pil_image.mode == "RGBA":
            pil_image_bytes = pil_image.tobytes()
        else:
            pil_image_bytes = pil_image.convert("RGBA").tobytes()
        images[image_url] = skia.Image.frombytes(
            array=pil_image_bytes,
            dimensions=pil_image.size,
            colorType=skia.kRGBA_8888_ColorType)

def style(node, rules, url, images):
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
        image_url_strs = []
        for property, value in pairs.items():
            computed_value = compute_style(node, property, value)
            node.style[property] = computed_value
            if property == 'background-image':
                image_url_strs.append(value)
        get_images(image_url_strs, url, images)
    if node.style.get('background-image'):
        node.background_image = \
            images[parse_style_url(
                node.style.get('background-image'))]
    for child in node.children:
        style(child, rules, url, images)

SCROLL_STEP = 100
CHROME_PX = 100

class Tab:
    def __init__(self):
        self.history = []
        self.focus = None
        self.cookies = {}

        with open("browser8.css") as f:
            self.default_style_sheet = CSSParser(f.read()).parse()

    def cookie_string(self):
        origin = url_origin(self.history[-1])
        cookie_string = ""
        if not origin in self.cookies:
            return cookie_string
        for key, value in self.cookies[origin].items():
            cookie_string += "&" + key + "=" + value
        return cookie_string[1:]

    def load(self, url, body=None):
        self.scroll = 0
        self.url = url
        self.history.append(url)
        req_headers = { "Cookie": self.cookie_string() }        
        headers, body = request(url, headers=req_headers, payload=body)
        if "set-cookie" in headers:
            if ";" in headers["set-cookie"]:
                kv, params = headers["set-cookie"].split(";", 1)
            else:
                kv = headers["set-cookie"]
            key, value = kv.split("=", 1)
            origin = url_origin(self.history[-1])
            self.cookies.setdefault(origin, {})[key] = value

        self.nodes = HTMLParser(body).parse()

        self.js = JSContext(self)
        scripts = [node.attributes["src"] for node
                   in tree_to_list(self.nodes, [])
                   if isinstance(node, Element)
                   and node.tag == "script"
                   and "src" in node.attributes]
        for script in scripts:
            header, body = request(resolve_url(script, url),
                headers=req_headers)
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
            try:
                header, body = request(resolve_url(link, url),
                    headers=req_headers)
            except:
                continue
            self.rules.extend(CSSParser(body).parse())

        image_url_strs = [rule[1]['background-image']
                 for rule in self.rules
                 if 'background-image' in rule[1]]

        self.images = {}
        get_images(image_url_strs, url, self.images)

        self.render()

    def render(self):
        style(self.nodes, sorted(self.rules, key=cascade_priority),
            self.url, self.images)
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        self.document.paint(self.display_list)

    def draw(self, rasterizer):
        for cmd in self.display_list:
            if cmd.rect.top() > self.scroll + HEIGHT - CHROME_PX: continue
            if cmd.rect.bottom() < self.scroll: continue
            cmd.execute(self.scroll - CHROME_PX, rasterizer)

        if self.focus:
            obj = [obj for obj in tree_to_list(self.document, [])
                   if obj.node == self.focus][0]
            text = self.focus.attributes.get("value", "")
            x = obj.x + obj.font.measureText(text)
            y = obj.y - self.scroll + CHROME_PX
            rasterizer.draw_polyline(x, y, x, y + obj.height)

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
    def __init__(self, sdl_window):
        self.sdl_window = sdl_window
        self.window_surface = SDL_GetWindowSurface(
            self.sdl_window)
        self.skia_surface = skia.Surface(WIDTH, HEIGHT)

        self.tabs = []
        self.active_tab = None
        self.focus = None
        self.address_bar = ""

    def to_sdl_surface(skia_bytes):
        depth = 32 # 4 bytes per pixel
        pitch = 4 * WIDTH # 4 * WIDTH pixels per line on-screen
        # Skia uses an ARGB format - alpha first byte, then
        # through to blue as the last byte.
        alpha_mask = 0xff000000
        red_mask = 0x00ff0000
        green_mask = 0x0000ff00
        blue_mask = 0x000000ff
        return SDL_CreateRGBSurfaceFrom(
            skia_bytes, WIDTH, HEIGHT, depth, pitch,
            red_mask, green_mask, blue_mask, alpha_mask)

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
        self.draw()

    def draw(self):
        rasterizer = Rasterizer(self.skia_surface)
        rasterizer.clear(skia.ColorWHITE)

        self.tabs[self.active_tab].draw(rasterizer)
    
        # Draw the tabs UI:
        tabfont = skia.Font(skia.Typeface('Arial'), 20)
        for i, tab in enumerate(self.tabs):
            name = "Tab {}".format(i)
            x1, x2 = 40 + 80 * i, 120 + 80 * i
            rasterizer.draw_polyline(x1, 0, x1, 40)
            rasterizer.draw_polyline(x2, 0, x2, 40)
            rasterizer.draw_text(x1 + 10, 10, name, tabfont)
            if i == self.active_tab:
                rasterizer.draw_polyline(0, 40, x1, 40)
                rasterizer.draw_polyline(x2, 40, WIDTH, 40)

        # Draw the plus button to add a tab:
        buttonfont = skia.Font(skia.Typeface('Arial'), 30)
        rasterizer.draw_rect(skia.Rect.MakeLTRB(10, 10, 30, 30))
        rasterizer.draw_text(11, 0, "+", buttonfont)

        # Draw the URL address bar:
        rasterizer.draw_rect(
            skia.Rect.MakeLTRB(40, 50, WIDTH - 10, 90))
        if self.focus == "address bar":
            rasterizer.draw_text(55, 55, self.address_bar, buttonfont)
            w = buttonfont.measureText(self.address_bar)
            rasterizer.draw_polyline(55 + w, 55, 55 + w, 85)
        else:
            url = self.tabs[self.active_tab].url
            rasterizer.draw_text(55, 55, url, buttonfont)

        # Draw the back button:
        rasterizer.draw_rect(skia.Rect.MakeLTRB(10, 50, 35, 90))
        rasterizer.draw_polyline(
            15, 70, 30, 55, 30, 85, True)

        # Raster the results and copy to the SDL surface:
        skia_image = self.skia_surface.makeImageSnapshot()
        skia_bytes = skia_image.tobytes()
        rect = SDL_Rect(0, 0, WIDTH, HEIGHT)
        skia_surface = Browser.to_sdl_surface(skia_bytes)
        SDL_BlitSurface(
            skia_surface, rect, self.window_surface, rect)
        SDL_UpdateWindowSurface(self.sdl_window)

if __name__ == "__main__":
    import sys

    SDL_Init(SDL_INIT_VIDEO)
    sdl_window = SDL_CreateWindow(b"Browser",
        SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
        WIDTH, HEIGHT, SDL_WINDOW_SHOWN)

    browser = Browser(sdl_window)
    browser.load(sys.argv[1])

    running = True
    event = SDL_Event()
    while running:
        while SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == SDL_MOUSEMOTION or event.type == SDL_WINDOWEVENT:
                continue
            if event.type == SDL_MOUSEBUTTONUP:
                browser.handle_click(event.button)
            if event.type == SDL_KEYDOWN:
                if event.key.keysym.sym == SDLK_RETURN:
                    browser.handle_enter()
                if event.key.keysym.sym == SDLK_DOWN:
                    browser.handle_down()
            if event.type == SDL_TEXTINPUT:
                browser.handle_key(event.text.text.decode('utf8'))
            if event.type == SDL_QUIT:
                running = False
                break

    SDL_DestroyWindow(sdl_window)
    SDL_Quit()
