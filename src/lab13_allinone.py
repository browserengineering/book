"""
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
import wbetools
import OpenGL.GL as GL

def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)

class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent
        self.style = {}
        self.animations = {}

    def __repr__(self):
        return repr(self.text)

class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent
        self.style = {}
        self.animations = {}

    def __repr__(self):
        attrs = [" " + k + "=\"" + v + "\"" for k, v  in self.attributes.items()]
        return "<" + self.tag + "".join(attrs) + ">"

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
        parts = text.split()
        tag = parts[0].lower()
        attributes = {}
        for attrpair in parts[1:]:
            if "=" in attrpair:
                key, value = attrpair.split("=", 1)
                if len(value) > 2 and value[0] in ["'", "\""]:
                    value = value[1:-1]
                attributes[key.lower()] = value
            else:
                attributes[attrpair.lower()] = ""
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

def cascade_priority(rule):
    selector, body = rule
    return selector.priority

BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "pre", "blockquote",
    "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
    "figcaption", "main", "div", "table", "form", "fieldset",
    "legend", "details", "summary"
]

def layout_mode(node):
    if isinstance(node, Text):
        return "inline"
    elif node.children:
        for child in node.children:
            if isinstance(child, Text): continue
            if child.tag in BLOCK_ELEMENTS:
                return "block"
        return "inline"
    elif node.tag == "input":
        return "inline"
    else:
        return "block"

def resolve_url(url, current):
    if "://" in url:
        return url
    elif url.startswith("/"):
        scheme, hostpath = current.split("://", 1)
        host, oldpath = hostpath.split("/", 1)
        return scheme + "://" + host + url
    else:
        scheme, hostpath = current.split("://", 1)
        if "/" not in hostpath:
            current = current + "/"
        dir, _ = current.rsplit("/", 1)
        while url.startswith("../"):
            url = url[3:]
            if dir.count("/") == 2: continue
            dir, _ = dir.rsplit("/", 1)
        return dir + "/" + url

def tree_to_list(tree, list):
    list.append(tree)
    for child in tree.children:
        tree_to_list(child, list)
    return list

INHERITED_PROPERTIES = {
    "font-size": "16px",
    "font-style": "normal",
    "font-weight": "normal",
    "color": "black",
}

def compute_style(node, property, value):
    if property == "font-size":
        if value.endswith("px"):
            return value
        elif value.endswith("%"):
            if node.parent:
                parent_font_size = node.parent.style["font-size"]
            else:
                parent_font_size = INHERITED_PROPERTIES["font-size"]
            node_pct = float(value[:-1]) / 100
            parent_px = float(parent_font_size[:-2])
            return str(node_pct * parent_px) + "px"
        else:
            return None
    else:
        return value

class TagSelector:
    def __init__(self, tag):
        self.tag = tag
        self.priority = 1

    def matches(self, node):
        return isinstance(node, Element) and self.tag == node.tag

    def __repr__(self):
        return "TagSelector(tag={}, priority={})".format(
            self.tag, self.priority)

class DescendantSelector:
    def __init__(self, ancestor, descendant):
        self.ancestor = ancestor
        self.descendant = descendant
        self.priority = ancestor.priority + descendant.priority
            
    def matches(self, node):
        if not self.descendant.matches(node): return False
        while node.parent:
            if self.ancestor.matches(node.parent): return True
            node = node.parent
        return False

    def __repr__(self):
        return ("DescendantSelector(ancestor={}, descendant={}, priority={})") \
            .format(self.ancestor, self.descendant, self.priority)

EVENT_DISPATCH_CODE = \
    "new Node(dukpy.handle).dispatchEvent(new Event(dukpy.type))"

def url_origin(url):
    scheme_colon, _, host, _ = url.split("/", 3)
    return scheme_colon + "//" + host

COOKIE_JAR = {}

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
    body += "\r\n" + (payload if payload else "")
    s.send(body.encode("utf8"))
    response = s.makefile("r", encoding="utf8", newline="\r\n")

    statusline = response.readline()
    version, status, explanation = statusline.split(" ", 2)
    assert status == "200", "{}: {}".format(status, explanation)

    headers = {}
    while True:
        line = response.readline()
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

def draw_line(canvas, x1, y1, x2, y2):
    path = skia.Path().moveTo(x1, y1).lineTo(x2, y2)
    paint = skia.Paint(Color=skia.ColorBLACK)
    paint.setStyle(skia.Paint.kStroke_Style)
    paint.setStrokeWidth(1)
    canvas.drawPath(path, paint)

def draw_text(canvas, x, y, text, font, color=None):
    sk_color = parse_color(color)
    paint = skia.Paint(AntiAlias=True, Color=sk_color)
    canvas.drawString(
        text, float(x), y - font.getMetrics().fAscent,
        font, paint)

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

def linespace(font):
    metrics = font.getMetrics()
    return metrics.fDescent - metrics.fAscent

def parse_blend_mode(blend_mode_str):
    if blend_mode_str == "multiply":
        return skia.BlendMode.kMultiply
    elif blend_mode_str == "difference":
        return skia.BlendMode.kDifference
    else:
        return skia.BlendMode.kSrcOver

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
    elif color == "lightgreen":
        return skia.ColorSetARGB(0xFF, 0x90, 0xEE, 0x90)
    else:
        return skia.ColorBLACK


CHROME_PX = 100
SCROLL_STEP = 100

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

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18

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
            if len(self.tasks) == 0 or self.needs_quit:
                self.condition.wait()
            self.condition.release()


    def handle_quit(self):
        print(self.tab.measure_render.text())

class Task:
    def __init__(self, task_code, *args):
        self.task_code = task_code
        self.args = args
        self.__name__ = "task"

    def run(self):
        self.task_code(*self.args)
        self.task_code = None
        self.args = None

REFRESH_RATE_SEC = 0.016 # 16ms

def center_point(rect):
    return (rect.left() + (rect.right() - rect.left()) / 2,
        rect.top() + (rect.bottom() - rect.top()) / 2)

class DisplayItem:
    def __init__(self, rect, children=[], node=None):
        self.rect = rect
        self.children = children
        self.node = node

    def is_paint_command(self):
        return False

    def map(self, rect):
        return rect

    def add_composited_bounds(self, rect):
        rect.join(self.rect)
        for cmd in self.children:
            cmd.add_composited_bounds(rect)

    def needs_compositing(self):
        return any([child.needs_compositing() \
            for child in self.children])

def map_translation(rect, translation):
    if not translation:
        return rect
    else:
        (x, y) = translation
        matrix = skia.Matrix()
        matrix.setTranslate(x, y)
        return matrix.mapRect(rect)

class Transform(DisplayItem):
    def __init__(self, translation, rect, node, children):
        super().__init__(rect, children=children, node=node)
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

class DrawLine(DisplayItem):
    def __init__(self, x1, y1, x2, y2):
        super().__init__(skia.Rect.MakeLTRB(x1, y1, x2, y2))
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def is_paint_command(self):
        return True

    def execute(self, canvas):
        draw_line(canvas, self.x1, self.y1, self.x2, self.y2)

    def __repr__(self):
        return "DrawLine top={} left={} bottom={} right={}".format(
            self.y1, self.x1, self.y2, self.x2)

class DrawRRect(DisplayItem):
    def __init__(self, rect, radius, color):
        super().__init__(rect)
        self.rrect = skia.RRect.MakeRectXY(rect, radius, radius)
        self.color = color

    def is_paint_command(self):
        return True

    def execute(self, canvas):
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
        self.font = font
        self.text = text
        self.color = color
        super().__init__(skia.Rect.MakeLTRB(x1, y1,
            self.right, self.bottom))

    def is_paint_command(self):
        return True

    def execute(self, canvas):
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
        super().__init__(skia.Rect.MakeLTRB(x1, y1, x2, y2))
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color

    def is_paint_command(self):
        return True

    def execute(self, canvas):
        draw_rect(canvas,
            self.left, self.top,
            self.right, self.bottom,
            fill_color=self.color, width=0)

    def __repr__(self):
        return ("DrawRect(top={} left={} " +
            "bottom={} right={} color={})").format(
            self.top, self.left, self.bottom,
            self.right, self.color)

class ClipRRect(DisplayItem):
    def __init__(self, rect, radius, children, should_clip=True):
        super().__init__(rect, children=children)
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

    def clone(self, children):
        return ClipRRect(self.rect, self.radius, children, \
            self.should_clip)

    def __repr__(self):
        if self.should_clip:
            return "ClipRRect({})".format(str(self.rrect))
        else:
            return "ClipRRect(<no-op>)"

class SaveLayer(DisplayItem):
    def __init__(self, sk_paint, node, children, should_save=True):
        super().__init__(skia.Rect.MakeEmpty(), children=children, node=node)
        self.should_save = should_save
        self.sk_paint = sk_paint

    def execute(self, canvas):
        if self.should_save:
            canvas.saveLayer(paint=self.sk_paint)
        for cmd in self.children:
                cmd.execute(canvas)
        if self.should_save:
            canvas.restore()

    def needs_compositing(self):
        return USE_COMPOSITING and self.should_save or \
            any([child.needs_compositing() \
                for child in self.children])

    def clone(self, children):
        return SaveLayer(self.sk_paint, self.node, children, \
            self.should_save)

    def __repr__(self):
        if self.should_save:
            return "SaveLayer(alpha={})".format(self.sk_paint.getAlphaf())
        else:
            return "SaveLayer(<no-op>)"

class DrawCompositedLayer(DisplayItem):
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
        return "BlockLayout(x={}, y={}, width={}, height={}, node={})".format(
            self.x, self.x, self.width, self.height, self.node)

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

        is_atomic = not isinstance(self.node, Text) and \
            (self.node.tag == "input" or self.node.tag == "button")

        if not is_atomic:
            bgcolor = self.node.style.get("background-color",
                                     "transparent")
            if bgcolor != "transparent":
                radius = float(self.node.style.get("border-radius", "0px")[:-2])
                cmds.append(DrawRRect(rect, radius, bgcolor))
 
        for child in self.children:
            child.paint(cmds)

        if not is_atomic:
            cmds = paint_visual_effects(self.node, cmds, rect)
        display_list.extend(cmds)

    def __repr__(self):
        return "InlineLayout(x={}, y={}, width={}, height={}, node={})".format(
            self.x, self.y, self.width, self.height, self.node)

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
    return float(style_val[:-2]) if style_val else default_value

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

SHOW_COMPOSITED_LAYER_BORDERS = False

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
    rect = skia.Rect.MakeEmpty()
    display_item.add_composited_bounds(rect)
    effect = display_item.parent
    while effect:
        rect = effect.map(rect)
        effect = effect.parent
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
            item.add_composited_bounds(rect)
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
        for item in self.display_items:
            item.execute(canvas)
        canvas.restore()

        if SHOW_COMPOSITED_LAYER_BORDERS:
            draw_rect(
                canvas, 0, 0, irect.width() - 1,
                irect.height() - 1,
                border_color="red")

    def __repr__(self):
        composited_bounds = skia.Rect.MakeEmpty()
        self.add_composited_bounds(composited_bounds)
        absolute_bounds = skia.Rect.MakeEmpty()
        self.add_absolute_bounds(absolute_bounds)

        return ("layer: composited_bounds={} " +
            "absolute_bounds={} first_chunk={}").format(
            composited_bounds, absolute_bounds,
            self.display_items if len(self.display_items) > 0 else 'None')

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
        self.needs_style = False
        self.needs_layout = False
        self.needs_paint = False
        self.browser = browser
        if USE_BROWSER_THREAD:
            self.task_runner = TaskRunner(self)
        else:
            self.task_runner = SingleThreadedTaskRunner(self)
        self.task_runner.start()

        self.measure_render = MeasureTime("render")

        self.composited_updates = []

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
                    if USE_COMPOSITING and \
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
        self.composited_updates.clear()

        commit_data = CommitData(
            url=self.url,
            scroll=scroll,
            height=document_height,
            display_list=self.display_list,
            composited_updates=composited_updates,
        )
        self.display_list = None
        self.scroll_changed_in_tab = False

        self.browser.commit(self, commit_data)

    def render(self):
        self.measure_render.start()

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
            if self.focus:
                obj = [obj for obj in tree_to_list(self.document, [])
                   if obj.node == self.focus and \
                        isinstance(obj, InputLayout)][0]
                text = self.focus.attributes.get("value", "")
                x = obj.x + obj.font.measureText(text)
                y = obj.y
                self.display_list.append(
                    DrawLine(x, y, x, y + obj.height))
            self.needs_paint = False

        self.measure_render.stop()

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

USE_GPU = True

class Browser:
    def __init__(self):
        if USE_GPU:
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

        self.active_tab_height = 0
        self.active_tab_display_list = None

        self.composited_updates = {}
        self.composited_layers = []
        self.draw_list = []

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
        self.needs_animation_frame = True

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
            if not cmd.needs_compositing() and \
                (not cmd.parent or \
                 cmd.parent.needs_compositing())
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
            if USE_BROWSER_THREAD:
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
                active_tab = self.tabs[self.active_tab]
                task = Task(active_tab.set_needs_paint)
                active_tab.task_runner.schedule_task(task)
            elif 10 <= e.x < 30 and 10 <= e.y < 30:
                self.load_internal("https://browser.engineering/")
            elif 10 <= e.x < 35 and 40 <= e.y < 90:
                active_tab = self.tabs[self.active_tab]
                task = Task(active_tab.go_back)
                active_tab.task_runner.schedule_task(task)
                self.clear_data()
            elif 50 <= e.x < WIDTH - 10 and 40 <= e.y < 90:
                self.focus = "address bar"
                self.address_bar = ""
            self.set_needs_raster()
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
        self.lock.release()

    def load(self, url):
        self.lock.acquire(blocking=True)
        self.load_internal(url)
        self.lock.release()

    def load_internal(self, url):
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
