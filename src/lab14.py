"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 14 (Making Content Accessible),
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
from lab4 import HTMLParser
from lab13 import Text, Element
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
import OpenGL.GL as GL
from lab12 import MeasureTime
from lab13 import USE_BROWSER_THREAD, CSSParser, JSContext, style, \
    clamp_scroll, CompositedLayer, absolute_bounds, \
    DrawCompositedLayer, Task, TaskRunner, SingleThreadedTaskRunner, \
    CommitData, add_parent_pointers, \
    DisplayItem, DrawRRect, DrawText, \
    DrawLine, paint_visual_effects, WIDTH, HEIGHT, INPUT_WIDTH_PX, \
    REFRESH_RATE_SEC, HSTEP, VSTEP

def parse_outline(outline_str):
    if not outline_str:
        return None
    values = outline_str.split(" ")
    if len(values) != 3:
        return None
    if values[1] != "solid":
        return None
    return (int(values[0][:-2]), values[2])

def draw_rect(
    canvas, rect, fill_color=None, border_color="black", width=1):
    paint = skia.Paint()
    if fill_color:
        paint.setStrokeWidth(width);
        paint.setColor(parse_color(fill_color))
    else:
        paint.setStyle(skia.Paint.kStroke_Style)
        paint.setStrokeWidth(width);
        paint.setColor(parse_color(border_color))
    canvas.drawRect(rect, paint)

class DrawRect(DisplayItem):
    def __init__(self, rect, border_color, fill_color=None, width=0):
        super().__init__(rect)
        self.border_color = border_color
        self.fill_color = fill_color
        self.width = width

    def is_paint_command(self):
        return True

    def execute(self, canvas):
        draw_rect(canvas, self.rect,
            fill_color=self.fill_color,
            border_color=self.border_color, width=self.width)

    def __repr__(self):
        return ("DrawRect(top={} left={} " +
            "bottom={} right={} border_color={} " +
            "width={} fill_color={})").format(
            self.rect.top(), self.rect.left(), self.rect.bottom(),
            self.rect.right(), self.border_color,
            self.width, self.fill_color)

def outline_cmd(rect, outline):
    (outline_width, outline_color) = outline
    return DrawRect(rect, border_color=outline_color,
            width=outline_width)

def is_focused(node):
    if isinstance(node, Text):
        node = node.parent
    return hasattr(node, "is_focused") and node.is_focused

def paint_outline(node, cmds, rect):
    outline = parse_outline(node.style.get("outline"))
    if outline:
        cmds.append(outline_cmd(rect, outline))
    elif hasattr(node, "is_focused") and node.is_focused:
        cmds.append(outline_cmd(rect, (2, "black")))

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

    def layout(self, zoom):
        previous = None
        for child in self.node.children:
            if layout_mode(child) == "inline":
                next = InlineLayout(child, self, previous)
            else:
                next = BlockLayout(child, self, previous)
            self.children.append(next)
            previous = next

        self.width = style_length(
            self.node, "width", self.parent.width, zoom)
        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        for child in self.children:
            child.layout(zoom)

        self.height = style_length(
            self.node, "height",
            sum([child.height for child in self.children]), zoom)

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

        paint_outline(self.node, cmds, rect)

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

    def layout(self, zoom):
        self.width = style_length(
            self.node, "width", self.parent.width, zoom)

        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        self.new_line()
        self.recurse(self.node, zoom)
        
        for line in self.children:
            line.layout(zoom)

        self.height = style_length(
            self.node, "height",
            sum([line.height for line in self.children]), zoom)

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
        self.cursor_x = self.x
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
            if self.cursor_x + w > self.x + self.width:
                self.new_line()
            line = self.children[-1]
            text = TextLayout(node, word, line, self.previous_word)
            line.children.append(text)
            self.previous_word = text
            self.cursor_x += w + font.measureText(" ")

    def input(self, node, zoom):
        w = device_px(INPUT_WIDTH_PX, zoom)
        if self.cursor_x + w > self.x + self.width:
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
        return "InlineLayout(x={}, y={}, width={}, height={}, node={})".format(
            self.x, self.y, self.width, self.height, self.node)

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

    def paint(self, display_list):
        outline_rect = skia.Rect.MakeEmpty()
        focused_node = None
        for child in self.children:
            node = child.node
            if isinstance(node, Text) and is_focused(node.parent):
                focused_node = node.parent
                outline_rect.join(child.rect())
            child.paint(display_list)

        if focused_node:
            paint_outline(focused_node, display_list, outline_rect)

    def role(self):
        return "none"

    def __repr__(self):
        return "LineLayout(x={}, y={}, width={}, height={}, node={})".format(
            self.x, self.y, self.width, self.height, self.node)

def device_px(layout_px, zoom):
    return layout_px * zoom

def style_length(node, style_name, default_value, zoom):
    style_val = node.style.get(style_name)
    return device_px(float(style_val[:-2]), zoom) if style_val \
        else default_value

class DocumentLayout:
    def __init__(self, node):
        self.node = node
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

    def paint(self, display_list):
        display_list.append(
            DrawRect(skia.Rect.MakeLTRB(
                self.x, self.y, self.x + self.width, self.y + self.height),
                "white", "white"))
        self.children[0].paint(display_list)

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
        if style == "normal": style = "roman"
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
        if style == "normal": style = "roman"
        size = device_px(float(self.node.style["font-size"][:-2]), zoom)
        self.font = get_font(size, weight, style)

        self.width = style_length(
            self.node, "width", device_px(INPUT_WIDTH_PX, zoom), zoom)
        self.height = style_length(
            self.node, "height", linespace(self.font), zoom)

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

        paint_outline(self.node, cmds, rect)

        cmds = paint_visual_effects(self.node, cmds, rect)
        display_list.extend(cmds)

    def __repr__(self):
        return "InputLayout(x={}, y={}, width={}, height={})".format(
            self.x, self.y, self.width, self.height)

def compute_role(node):
    if isinstance(node, Text):
        if node.parent.tag == "a":
            return "link"
        else:
            return "StaticText"
    else:
        if node.tag == "a":
            return "link"
        elif node.tag == "input":
            return "textbox"
        elif node.tag == "html":
            return "document"
        else:
            return "none"

class AccessibilityNode:
    def __init__(self, node):
        self.node = node
        self.previous = None
        self.children = []

    def build(self):
        for child_node in self.node.children:
            AccessibilityNode.build_internal(child_node, self)
        pass

    def build_internal(node, parent):
        role = compute_role(node)
        if role != "none":
            child = AccessibilityNode(node)
            parent.children.append(child)
            parent = child
        for child_node in node.children:
            AccessibilityNode.build_internal(child_node, parent)

    def __repr__(self):
        return "AccessibilityNode(node={} role={}".format(
            str(self.node), compute_role(self.node))

class AccessibilityAgent:
    def __init__(self, accessibility_tree):
        self.accessibility_tree = None

    def update(self):
        print('update')

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
        self.needs_accessibility = False
        self.needs_paint = False
        self.layout_tree = None
        self.accessibility_is_on = False
        self.accessibility_tree = None
        self.accessibility_agent = None

        self.browser = browser
        if USE_BROWSER_THREAD:
            self.task_runner = TaskRunner(self)
        else:
            self.task_runner = SingleThreadedTaskRunner(self)
        self.task_runner.start()

        self.measure_render = MeasureTime("render")

        self.composited_updates = []

        self.zoom = 1.0

        with open("browser8.css") as f:
            self.default_style_sheet = CSSParser(f.read()).parse()

    def allowed_request(self, url):
        return self.allowed_origins == None or \
            url_origin(url) in self.allowed_origins

    def script_run_wrapper(self, script, script_text):
        return Task(self.js.run, script, script_text)

    def load(self, url, body=None):
        self.zoom = 1
        self.focus = None
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

        document_height = math.ceil(self.layout_tree.height)
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
            self.layout_tree = DocumentLayout(self.nodes)
            self.layout_tree.layout(self.zoom)
            if self.accessibility_is_on:
                self.needs_accessibility = True
            else:
                self.needs_paint = True
            self.needs_layout = False

        if self.needs_accessibility:
            self.accessibility_tree = AccessibilityNode(self.nodes)
            self.accessibility_tree.build()
            print_tree(self.accessibility_tree)
            if not self.accessibility_agent:
                self.accessibility_agent = AccessibilityAgent(
                    self.accessibility_tree)
            self.needs_accessibility = False
            self.needs_paint = True

            task = Task(self.accessibility_agent.update)
            self.task_runner.schedule_task(task)

        if self.needs_paint:
            self.display_list = []

            self.layout_tree.paint(self.display_list)
            if self.focus and self.focus.tag == "input":
                obj = [obj for obj in tree_to_list(self.layout_tree, [])
                        if obj.node == self.focus][0]
                text = self.focus.attributes.get("value", "")
                x = obj.x + obj.font.measureText(text)
                y = obj.y
                self.display_list.append(
                    DrawLine(x, y, x, y + obj.height))
                self.needs_paint = False

        self.measure_render.stop()

    def apply_focus(self, node):
        if self.focus:
            self.focus.is_focused = None
        self.focus = node
        if node:
            if node.tag == "input":
                node.attributes["value"] = ""
            node.is_focused = True

    def activate_element(self, elt):
        if elt.tag == "a" and "href" in elt.attributes:
            url = resolve_url(elt.attributes["href"], self.url)
            self.load(url)
            return None
        elif elt.tag == "button":
            while elt:
                if elt.tag == "form" and "action" in elt.attributes:
                    self.submit_form(elt)
                    return None
                elt = elt.parent
        return elt

    def click(self, x, y):
        self.render()
        self.apply_focus(None)
        y += self.scroll
        objs = [obj for obj in tree_to_list(self.layout_tree, [])
                if obj.x <= x < obj.x + obj.width
                and obj.y <= y < obj.y + obj.height]
        if not objs: return
        elt = objs[-1].node
        if elt and self.js.dispatch_event("click", elt): return
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "input":
                elt.attributes["value"] = ""
                if elt != self.focus:
                    self.set_needs_render()
                self.focus = elt
                return
            elif not self.activate_element(elt):
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
        if self.focus:
            if self.js.dispatch_event("keydown", self.focus): return
            self.focus.attributes["value"] += char
            self.set_needs_render()

    def enter(self):
        if self.focus:
            self.activate_element(self.focus)

    def is_focusable(node):
        return node.tag == "input" or node.tag == "button" \
            or node.tag == "a"

    def get_tabindex(node):
        return int(node.attributes.get("tabindex", 9999999))

    def advance_tab(self):
        focusable_nodes = [node
            for node in tree_to_list(self.nodes, [])
            if isinstance(node, Element) and Tab.is_focusable(node)]
        focusable_nodes.sort(key=Tab.get_tabindex)
        if not focusable_nodes:
            self.apply_focus(None)
        elif not self.focus:
            self.apply_focus(focusable_nodes[0])
        else:
            i = focusable_nodes.index(self.focus)
            if i < len(focusable_nodes) - 1:
                self.apply_focus(focusable_nodes[i+1])
            else:
                self.apply_focus(None)
                self.browser.focus_addressbar()
        self.set_needs_render()

    def zoom_by(self, increment):
        if increment > 0:
            self.zoom *= 1.1;
        else:
            self.zoom *= 1/1.1;
        self.set_needs_render()

    def reset_zoom(self):
        self.zoom = 1
        self.set_needs_render()

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

    def toggle_accessibility(self):
        self.accessibility_is_on = not self.accessibility_is_on
        self.set_needs_render()

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
        active_tab = self.tabs[self.active_tab]
        task = Task(active_tab.toggle_accessibility)
        active_tab.task_runner.schedule_task(task)

    def handle_click(self, e):
        self.lock.acquire(blocking=True)
        if e.y < CHROME_PX:
            self.focus = None
            if 40 <= e.x < 40 + 80 * len(self.tabs) and 0 <= e.y < 40:
                self.set_active_tab(int((e.x - 40) / 80))
            elif 10 <= e.x < 30 and 10 <= e.y < 30:
                self.add_tab()
            elif 10 <= e.x < 35 and 40 <= e.y < 90:
                self.go_back()
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
        draw_rect(canvas, skia.Rect.MakeLTRB(10, 10, 30, 30))
        draw_text(canvas, 11, 4, "+", buttonfont)

        # Draw the URL address bar:
        draw_rect(canvas, skia.Rect.MakeLTRB(40.0, 50.0, WIDTH - 10.0, 90.0))
        if self.focus == "address bar":
            draw_text(canvas, 55, 55, self.address_bar, buttonfont)
            w = buttonfont.measureText(self.address_bar)
            draw_line(canvas, 55 + w, 55, 55 + w, 85)
        else:
            if self.url:
                draw_text(canvas, 55, 55, self.url, buttonfont)

        # Draw the back button:
        draw_rect(canvas, skia.Rect.MakeLTRB(10, 50, 35, 90))
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
        if not USE_BROWSER_THREAD:
            if active_tab.task_runner.needs_quit:
                break
            if browser.needs_animation_frame:
                browser.needs_animation_frame = False
                browser.render()
        browser.composite_raster_and_draw()
        browser.schedule_animation_frame()
