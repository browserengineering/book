"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 16 (Reusing Previous Computations),
without exercises.
"""

import sdl2
import skia
import ctypes
from lab4 import print_tree
from lab4 import HTMLParser
from lab13 import Text, Element
from lab6 import resolve_url
from lab6 import tree_to_list
from lab6 import INHERITED_PROPERTIES
from lab6 import compute_style
from lab8 import layout_mode
from lab9 import EVENT_DISPATCH_CODE
from lab10 import COOKIE_JAR, url_origin
from lab11 import draw_text, get_font, linespace, \
    ClipRRect, parse_blend_mode, CHROME_PX, SCROLL_STEP
import OpenGL.GL as GL
from lab12 import MeasureTime
from lab13 import diff_styles, \
    CompositedLayer, absolute_bounds, absolute_bounds_for_obj, \
    DrawCompositedLayer, Task, TaskRunner, SingleThreadedTaskRunner, \
    clamp_scroll, add_parent_pointers, map_translation, \
    DisplayItem, DrawText, ClipRRect, \
    DrawLine, paint_visual_effects, parse_transform, WIDTH, HEIGHT, \
    INPUT_WIDTH_PX, REFRESH_RATE_SEC, HSTEP, VSTEP, SETTIMEOUT_CODE, \
    XHR_ONLOAD_CODE, Transform, ANIMATED_PROPERTIES, SaveLayer
from lab14 import parse_color, parse_outline, draw_rect, DrawRRect, \
    is_focused, paint_outline, has_outline, \
    device_px, cascade_priority, \
    is_focusable, get_tabindex, announce_text, speak_text, \
    CSSParser, main_func, DrawOutline
from lab15 import request, DrawImage, DocumentLayout, BlockLayout, \
    EmbedLayout, InputLayout, LineLayout, TextLayout, ImageLayout, \
    IframeLayout, JSContext, style, AccessibilityNode, Frame, Tab, \
    CommitData, draw_line, Browser, BROKEN_IMAGE, font, add_main_args
import wbetools

@wbetools.patch(is_focusable)
def is_focusable(node):
    if get_tabindex(node) <= 0:
        return False
    elif "tabindex" in node.attributes:
        return True
    elif "contenteditable" in node.attributes:
        return True
    else:
        return node.tag in ["input", "button", "a"]

@wbetools.patch(print_tree)
def print_tree(node, indent=0):
    print(' ' * indent, node)
    children = node.children
    if not isinstance(children, list):
        children = children.get()
    for child in children:
        print_tree(child, indent + 2)

@wbetools.patch(tree_to_list)
def tree_to_list(tree, l):
    l.append(tree)
    children = tree.children
    if not isinstance(children, list):
        children = children.get()
    for child in children:
        tree_to_list(child, l)
    return l

@wbetools.patch(compute_style)
def compute_style(node, property, value):
    if property == 'font-size':
        if value.endswith('px'):
            return value
        elif value.endswith('%'):
            if node.parent:
                parent_font_size = node.parent.style.get()['font-size']
            else:
                parent_font_size = INHERITED_PROPERTIES['font-size']
            node_pct = float(value[:-1]) / 100
            parent_px = float(parent_font_size[:-2])
            return str(node_pct * parent_px) + 'px'
        else:
            return None
    else:
        return value

@wbetools.patch(paint_outline)
def paint_outline(node, cmds, rect, zoom):
    if has_outline(node):
        thickness, color = parse_outline(node.style.get().get('outline'), zoom)
        cmds.append(DrawOutline(rect, color, thickness))

@wbetools.patch(has_outline)
def has_outline(node):
    return parse_outline(node.style.get().get('outline'), 1)

@wbetools.patch(absolute_bounds_for_obj)
def absolute_bounds_for_obj(obj):
    w = obj.width
    if not isinstance(w, float): w = w.get()
    rect = skia.Rect.MakeXYWH(obj.x, obj.y, w, obj.height)
    cur = obj.node
    while cur:
        rect = map_translation(rect, parse_transform(cur.style.get().get('transform', '')))
        cur = cur.parent
    return rect

@wbetools.patch(paint_visual_effects)
def paint_visual_effects(node, cmds, rect):
    opacity = float(node.style.get().get('opacity', '1.0'))
    blend_mode = parse_blend_mode(node.style.get().get('mix-blend-mode'))
    translation = parse_transform(node.style.get().get('transform', ''))
    border_radius = float(node.style.get().get('border-radius', '0px')[:-2])
    if node.style.get().get('overflow', 'visible') == 'clip':
        clip_radius = border_radius
    else:
        clip_radius = 0
    needs_clip = node.style.get().get('overflow', 'visible') == 'clip'
    needs_blend_isolation = blend_mode != skia.BlendMode.kSrcOver or needs_clip or opacity != 1.0
    save_layer = SaveLayer(skia.Paint(BlendMode=blend_mode, Alphaf=opacity), node, [ClipRRect(rect, clip_radius, cmds, should_clip=needs_clip)], should_save=needs_blend_isolation)
    transform = Transform(translation, rect, node, [save_layer])
    node.save_layer = save_layer
    return [transform]

class ProtectedField:
    def __init__(self):
        self.value = None
        self.dirty = True
        self.depended_on = set()

    def mark(self):
        if self.dirty: return
        self.dirty = True

    def notify(self):
        for field in self.depended_on:
            field.mark()

    def set(self, value):
        self.notify()
        self.value = value
        self.dirty = False

    def get(self):
        assert not self.dirty
        return self.value

    def read(self, field):
        field.depended_on.add(self)
        return field.get()

    def copy(self, field):
        self.set(self.read(field))

@wbetools.patch(Element)
class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent

        self.style = ProtectedField()
        self.animations = {}

        self.is_focused = False
        self.layout_object = None

@wbetools.patch(Text)
class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent

        self.style = ProtectedField()
        self.animations = {}

        self.is_focused = False
        self.layout_object = None

@wbetools.patch(DocumentLayout)
class DocumentLayout:
    def __init__(self, node, frame):
        self.node = node
        self.frame = frame
        node.layout_object = self
        self.parent = None
        self.previous = None
        self.children = []

        self.zoom = ProtectedField()
        self.width = ProtectedField()
        self.height = None
        self.x = None
        self.y = None

    def layout(self, width, zoom):
        self.zoom.set(zoom)
        if not self.children:
            child = BlockLayout(self.node, self, None, self.frame)
        else:
            child = self.children[0]
        self.children = [child]

        self.width.set(width - 2 * device_px(HSTEP, zoom))
        self.x = device_px(HSTEP, zoom)
        self.y = device_px(VSTEP, zoom)
        child.layout()
        self.height = child.height + 2 * device_px(VSTEP, zoom)

    def paint(self, display_list, dark_mode, scroll):
        cmds = []
        self.children[0].paint(cmds)
        if scroll != None and scroll != 0:
            rect = skia.Rect.MakeLTRB(
                self.x, self.y,
                self.x + self.width, self.y + self.height)
            cmds = [Transform((0, -scroll), rect, self.node, cmds)]

        display_list.extend(cmds)

@wbetools.patch(BlockLayout)
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        self.node = node
        node.layout_object = self
        self.parent = parent
        self.previous = previous
        self.frame = frame

        self.children = ProtectedField()
        self.zoom = ProtectedField()
        self.width = ProtectedField()
        self.height = None
        self.x = None
        self.y = None

    def layout(self):
        if self.zoom.dirty:
            self.zoom.copy(self.parent.zoom)

        if self.width.dirty:
            self.width.copy(self.parent.width)
        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        mode = layout_mode(self.node)
        if mode == "block":
            if self.children.dirty:
                children = []
                previous = None
                for child in self.node.children:
                    next = BlockLayout(child, self, previous, self.frame)
                    children.append(next)
                    previous = next
                self.children.set(children)
        else:
            if self.children.dirty:
                self.temp_children = []
                self.new_line()
                self.recurse(self.node)
                self.children.set(self.temp_children)
                self.temp_children = None

        for child in self.children.get():
            child.layout()

        self.height = sum([child.height for child in self.children.get()])

    def input(self, node):
        zoom = self.children.read(self.zoom)
        w = device_px(INPUT_WIDTH_PX, zoom)
        self.add_inline_child(node, w, InputLayout, self.frame)

    def image(self, node):
        zoom = self.children.read(self.zoom)
        if 'width' in node.attributes:
            w = device_px(int(node.attributes['width']), zoom)
        else:
            w = device_px(node.image.width(), zoom)
        self.add_inline_child(node, w, ImageLayout, self.frame)

    def iframe(self, node):
        zoom = self.children.read(self.zoom)
        if 'width' in self.node.attributes:
            w = device_px(int(self.node.attributes['width']), zoom)
        else:
            w = IFRAME_WIDTH_PX + device_px(2, zoom)
        self.add_inline_child(node, w, IframeLayout, self.frame)

    def text(self, node):
        zoom = self.children.read(self.zoom)
        style = self.children.read(node.style)
        node_font = font(style, zoom)
        for word in node.text.split():
            w = node_font.measureText(word)
            self.add_inline_child(node, w, TextLayout, self.frame, word)

    def new_line(self):
        self.previous_word = None
        self.cursor_x = 0
        last_line = self.temp_children[-1] if self.temp_children else None
        new_line = LineLayout(self.node, self, last_line)
        self.temp_children.append(new_line)

    def add_inline_child(self, node, w, child_class, frame, word=None):
        width = self.children.read(self.width)
        if self.cursor_x + w > width:
            self.new_line()
        line = self.temp_children[-1]
        if word:
            child = child_class(node, line, self.previous_word, word)
        else:
            child = child_class(node, line, self.previous_word, frame)
        line.children.append(child)
        self.previous_word = child
        style = self.children.read(node.style)
        zoom = self.children.read(self.zoom)
        self.cursor_x += w + font(style, zoom).measureText(' ')

    def paint(self, display_list):
        cmds = []

        rect = skia.Rect.MakeLTRB(
            self.x, self.y, self.x + self.width.get(),
            self.y + self.height)

        is_atomic = not isinstance(self.node, Text) and \
            (self.node.tag == "input" or self.node.tag == "button")

        if not is_atomic:
            bgcolor = self.node.style.get().get(
                "background-color", "transparent")
            if bgcolor != "transparent":
                radius = device_px(
                    float(self.node.style.get().get(
                        "border-radius", "0px")[:-2]),
                    self.zoom.get())
                cmds.append(DrawRRect(rect, radius, bgcolor))
 
        for child in self.children.get():
            child.paint(cmds)

        if self.node.is_focused and "contenteditable" in self.node.attributes:
            text_nodes = [
                t for t in tree_to_list(self, [])
                if isinstance(t, TextLayout)
            ]
            if text_nodes:
                cmds.append(DrawCursor(text_nodes[-1], text_nodes[-1].width))
            else:
                cmds.append(DrawCursor(self, 0))

        if not is_atomic:
            cmds = paint_visual_effects(self.node, cmds, rect)
        display_list.extend(cmds)

def DrawCursor(elt, width):
    return DrawLine(elt.x + width, elt.y, elt.x + width, elt.y + elt.height)

@wbetools.patch(LineLayout)
class LineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.zoom = ProtectedField()
        self.x = None
        self.y = None
        self.width = None
        self.height = None

    def layout(self):
        if self.zoom.dirty:
            self.zoom.copy(self.parent.zoom)
        self.width = self.parent.width.get()
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
        max_ascent = max([-child.get_ascent(1.25) for child in self.children])
        baseline = self.y + max_ascent
        for child in self.children:
            child.y = baseline + child.get_ascent()
        max_descent = max([child.get_descent(1.25) for child in self.children])
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
            paint_outline(outline_node, display_list, outline_rect, self.zoom.get())

@wbetools.patch(TextLayout)
class TextLayout:
    def __init__(self, node, parent, previous, word):
        self.node = node
        self.word = word
        self.children = []
        self.parent = parent
        self.previous = previous
        self.zoom = ProtectedField()
        self.width = None
        self.height = None
        self.x = None
        self.y = None
        self.font = None

    def get_ascent(self, font_multiplier=1.0):
        return self.font.getMetrics().fAscent * font_multiplier

    def get_descent(self, font_multiplier=1.0):
        return self.font.getMetrics().fDescent * font_multiplier

    def layout(self):
        if self.zoom.dirty:
            self.zoom.copy(self.parent.zoom)

        self.font = font(self.node.style.get(), self.zoom.get())
        self.width = self.font.measureText(self.word)

        if self.previous:
            space = self.previous.font.measureText(' ')
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x
        self.height = linespace(self.font)

    def paint(self, display_list):
        color = self.node.style.get()['color']
        display_list.append(DrawText(self.x, self.y, self.word, self.font, color))

@wbetools.patch(EmbedLayout)
class EmbedLayout:
    def __init__(self, node, parent, previous, frame):
        self.node = node
        self.frame = frame
        node.layout_object = self
        self.parent = parent
        self.previous = previous

        self.children = []
        self.zoom = ProtectedField()
        self.width = None
        self.height = None
        self.x = None
        self.y = None
        self.font = None

    def get_ascent(self, font_multiplier=1.0):
        return -self.height

    def get_descent(self, font_multiplier=1.0):
        return 0

    def layout(self):
        self.zoom.copy(self.parent.zoom)
        self.font = font(self.node.style.get(), self.zoom.get())
        if self.previous:
            space = self.previous.font.measureText(' ')
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

@wbetools.patch(InputLayout)
class InputLayout(EmbedLayout):
    def layout(self):
        EmbedLayout.layout(self)
        self.width = device_px(INPUT_WIDTH_PX, self.zoom.get())
        self.height = linespace(self.font)

    def paint(self, display_list):
        cmds = []
        rect = skia.Rect.MakeLTRB(self.x, self.y, self.x + self.width, self.y + self.height)
        bgcolor = self.node.style.get().get('background-color', 'transparent')
        if bgcolor != 'transparent':
            radius = device_px(float(self.node.style.get().get('border-radius', '0px')[:-2]), self.zoom.get())
            cmds.append(DrawRRect(rect, radius, bgcolor))
        if self.node.tag == 'input':
            text = self.node.attributes.get('value', '')
        elif self.node.tag == 'button':
            if len(self.node.children) == 1 and isinstance(self.node.children[0], Text):
                text = self.node.children[0].text
            else:
                print('Ignoring HTML contents inside button')
                text = ''
        color = self.node.style.get()['color']
        cmds.append(DrawText(self.x, self.y, text, self.font, color))
        if self.node.is_focused and self.node.tag == 'input':
            cx = rect.left() + self.font.measureText(text)
            cmds.append(DrawLine(cx, rect.top(), cx, rect.bottom()))
        cmds = paint_visual_effects(self.node, cmds, rect)
        paint_outline(self.node, cmds, rect, self.zoom.get())
        display_list.extend(cmds)

    def paint(self, display_list):
        cmds = []

        rect = skia.Rect.MakeLTRB(
            self.x, self.y, self.x + self.width,
            self.y + self.height)

        bgcolor = self.node.style.get().get("background-color",
                                 "transparent")
        if bgcolor != "transparent":
            radius = device_px(
                float(self.node.style.get().get("border-radius", "0px")[:-2]),
                self.zoom.get())
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

        color = self.node.style.get()["color"]
        cmds.append(DrawText(self.x, self.y,
                             text, self.font, color))

        if self.node.is_focused and self.node.tag == "input":
            cmds.append(DrawCursor(self, self.font.measureText(text)))

        cmds = paint_visual_effects(self.node, cmds, rect)
        paint_outline(self.node, cmds, rect, self.zoom.get())
        display_list.extend(cmds)

@wbetools.patch(ImageLayout)
class ImageLayout(EmbedLayout):
    def layout(self):
        EmbedLayout.layout(self)
        width_attr = self.node.attributes.get('width')
        height_attr = self.node.attributes.get('height')
        image_width = self.node.image.width()
        image_height = self.node.image.height()
        aspect_ratio = image_width / image_height

        if width_attr and height_attr:
            self.width = device_px(int(width_attr), self.zoom.get())
            self.img_height = device_px(int(height_attr), self.zoom.get())
        elif width_attr:
            self.width = device_px(int(width_attr), self.zoom.get())
            self.img_height = self.width / aspect_ratio
        elif height_attr:
            self.img_height = device_px(int(height_attr), self.zoom.get())
            self.width.set(self.img_height * aspect_ratio)
        else:
            self.width = device_px(image_width, self.zoom.get())
            self.img_height = device_px(image_height, self.zoom.get())
        self.height = max(self.img_height, linespace(self.font))

    def paint(self, display_list):
        cmds = []
        rect = skia.Rect.MakeLTRB(self.x, self.y + self.height - self.img_height, self.x + self.width, self.y + self.height)
        quality = self.node.style.get().get('image-rendering', 'auto')
        cmds.append(DrawImage(self.node.image, rect, quality))
        display_list.extend(cmds)

@wbetools.patch(IframeLayout)
class IframeLayout(EmbedLayout):
    def layout(self):
        EmbedLayout.layout(self)
        width_attr = self.node.attributes.get('width')
        height_attr = self.node.attributes.get('height')
        if width_attr:
            self.width = device_px(int(width_attr) + 2, self.zoom.get())
        else:
            self.width = device_px(IFRAME_WIDTH_PX + 2, self.zoom.get())
        if height_attr:
            self.height = device_px(int(height_attr) + 2, self.zoom.get())
        else:
            self.height = device_px(IFRAME_HEIGHT_PX + 2, self.zoom.get())
        if self.node.frame:
            self.node.frame.frame_height = self.height - device_px(2, self.zoom.get())
            self.node.frame.frame_width = self.width - device_px(2, self.zoom.get())

    def paint(self, display_list):
        frame_cmds = []
        rect = skia.Rect.MakeLTRB(self.x, self.y, self.x + self.width, self.y + self.height)
        bgcolor = self.node.style.get().get('background-color', 'transparent')
        if bgcolor != 'transparent':
            radius = device_px(float(self.node.style.get().get('border-radius', '0px')[:-2]), self.zoom.get())
            frame_cmds.append(DrawRRect(rect, radius, bgcolor))
        if self.node.frame:
            self.node.frame.paint(frame_cmds)
        diff = device_px(1, self.zoom.get())
        offset = (self.x + diff, self.y + diff)
        cmds = [Transform(offset, rect, self.node, frame_cmds)]
        inner_rect = skia.Rect.MakeLTRB(self.x + diff, self.y + diff, self.x + self.width - diff, self.y + self.height - diff)
        cmds = paint_visual_effects(self.node, cmds, inner_rect)
        paint_outline(self.node, cmds, rect, self.zoom.get())
        display_list.extend(cmds)

def style(node, rules, frame):
    old_style = node.style.value
    new_style = {}
    for property, default_value in INHERITED_PROPERTIES.items():
        if node.parent:
            parent_style = node.style.read(node.parent.style)
            new_style[property] = parent_style[property]
        else:
            new_style[property] = default_value
    for media, selector, body in rules:
        if media:
            if (media == 'dark') != frame.tab.dark_mode: continue
        if not selector.matches(node): continue
        for property, value in body.items():
            computed_value = compute_style(node, property, value)
            if not computed_value: continue
            new_style[property] = computed_value
    if isinstance(node, Element) and 'style' in node.attributes:
        pairs = CSSParser(node.attributes['style']).body()
        for property, value in pairs.items():
            computed_value = compute_style(node, property, value)
            new_style[property] = computed_value
    if old_style:
        transitions = diff_styles(old_style, new_style)
        for property, (old_value, new_value, num_frames) in transitions.items():
            if property in ANIMATED_PROPERTIES:
                tab.set_needs_render()
                AnimationClass = ANIMATED_PROPERTIES[property]
                animation = AnimationClass(old_value, new_value, num_frames)
                node.animations[property] = animation
                new_style[property] = animation.animate()
    node.style.set(new_style)
    for child in node.children:
        style(child, rules, frame)

@wbetools.patch(JSContext)
class JSContext:
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
        elt.layout_object.children.mark()
        frame.set_needs_render()

    def style_set(self, handle, s, window_id):
        frame = self.tab.window_id_to_frame[window_id]
        self.throw_if_cross_origin(frame)
        elt = self.handle_to_node[handle]
        elt.attributes['style'] = s
        elt.style.notify()
        frame.set_needs_render()

@wbetools.patch(Frame)
class Frame:
    def load(self, url, body=None):
        self.zoom = 1
        self.scroll = 0
        self.scroll_changed_in_frame = True
        headers, body = request(url, self.url, body)
        body = body.decode("utf8")
        self.url = url

        self.allowed_origins = None
        if "content-security-policy" in headers:
           csp = headers["content-security-policy"].split()
           if len(csp) > 0 and csp[0] == "default-src":
               self.allowed_origins = csp[1:]

        self.nodes = HTMLParser(body).parse()

        self.js = self.tab.get_js(url_origin(url))
        self.js.add_window(self)

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
            and node.tag == "img"]
        for img in images:
            try:
                src = img.attributes.get("src", "")
                image_url = resolve_url(src, self.url)
                assert self.allowed_request(image_url), \
                    "Blocked load of " + image_url + " due to CSP"
                header, body = request(image_url, self.url)
                img.encoded_data = body
                data = skia.Data.MakeWithoutCopy(body)
                img.image = skia.Image.MakeFromEncoded(data)
                assert img.image, "Failed to recognize image format for " + image_url
            except Exception as e:
                print("Exception loading image: url="
                    + image_url + " exception=" + str(e))
                img.image = BROKEN_IMAGE

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

        self.document = DocumentLayout(self.nodes, self)
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

    def keypress(self, char):
        if self.tab.focus and self.tab.focus.tag == "input":
            if not "value" in self.tab.focus.attributes:
                self.activate_element(self.tab.focus)
            if self.js.dispatch_event(
                "keydown", self.tab.focus, self.window_id): return
            self.tab.focus.attributes["value"] += char
            self.set_needs_render()
        elif self.tab.focus and "contenteditable" in self.tab.focus.attributes:
            text_nodes = [
               t for t in tree_to_list(self.tab.focus, [])
               if isinstance(t, Text)
            ]
            if text_nodes:
                last_text = text_nodes[-1]
            else:
                last_text = Text("", self.tab.focus)
                self.tab.focus.children.append(last_text)
            last_text.text += char
            self.tab.focus.layout_object.children.mark()
            self.set_needs_render()

if __name__ == "__main__":
    args = add_main_args()
    main_func(args)
