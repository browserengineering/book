"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 16 (Reusing Previous Computations),
without exercises.
"""

import skia
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
    parse_blend_mode, CHROME_PX, SCROLL_STEP
import OpenGL.GL as GL
from lab12 import MeasureTime
from lab13 import USE_BROWSER_THREAD, diff_styles, \
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
    CSSParser
from lab15 import request, DrawImage, DocumentLayout, BlockLayout, \
    InputLayout, LineLayout, TextLayout, ImageLayout, \
    IframeLayout, JSContext, style, AccessibilityNode, Frame, Tab, \
    CommitData, draw_line, Browser, main, wrap_in_window, CROSS_ORIGIN_IFRAMES, \
    WINDOW_COUNT
import wbetools

@wbetools.patch(Frame)
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
        global WINDOW_COUNT
        self.window_id = WINDOW_COUNT
        WINDOW_COUNT += 1
        self.frame_width = 0
        self.frame_height = 0

        self.tab.window_id_to_frame[self.window_id] = self

        with open("browser15.css") as f:
            self.default_style_sheet = \
                CSSParser(f.read(), internal=True).parse()

        self.measure_layout = MeasureTime("layout")

    def load(self, url, body=None):
        self.zoom = 1
        self.scroll = 0
        self.scroll_changed_in_frame = True
        headers, body = request(url, self.url, payload=body)
        self.url = url
        self.accessibility_tree = None

        self.allowed_origins = None
        if "content-security-policy" in headers:
           csp = headers["content-security-policy"].split()
           if len(csp) > 0 and csp[0] == "default-src":
               self.allowed_origins = csp[1:]

        self.nodes = HTMLParser(body).parse()

        if not self.parent_frame or CROSS_ORIGIN_IFRAMES or \
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
            self.rules.extend(CSSParser(body).parse())

        iframes = [node
                   for node in tree_to_list(self.nodes, [])
                   if isinstance(node, Element)
                   and node.tag == "iframe"
                   and "src" in node.attributes]
        for iframe in iframes:
            document_url = resolve_url(iframe.attributes["src"],
                self.tab.root_frame.url)
            iframe.frame = Frame(self.tab, self, iframe)
            iframe.frame.load(document_url)

        self.document = DocumentLayout(self.nodes, self)
        self.set_needs_render()

    def style(self):
        style(self.nodes,
            sorted(self.rules,
                key=cascade_priority), self)

    def layout(self, zoom):
        self.measure_layout.start()
        self.document.layout(zoom, self.frame_width)
        self.measure_layout.stop()
        print(self.measure_layout.text())

        clamped_scroll = self.clamp_scroll(self.scroll)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_frame = True

@wbetools.patch(DocumentLayout)
class DocumentLayout:
    def __init__(self, node, frame):
        self.node = node
        node.layout_object = self
        self.parent = None
        self.previous = None
        self.children = []
        self.frame = frame

        self.dirty_height = True
        self.dirty_width = True
        self.dirty_x = True
        self.dirty_y = True

        self.width = None
        self.height = None
        self.x = None
        self.y = None

    def mark_dirty(self):
        if isinstance(self.parent, BlockLayout) and \
            not self.parent.dirty_descendants:
            self.parent.dirty_descendants = True
            self.parent.mark_dirty()

    def layout(self, zoom, width):
        if not self.children:
            child = BlockLayout(self.node, self, None, self.frame)
        else:
            child = self.children[0]
        self.children = [child]

        if width - 2 * device_px(HSTEP, zoom) != self.width:
            self.width = width - 2 * device_px(HSTEP, zoom)
            child.dirty_width = True
            child.mark_dirty()
            self.dirty_width = False
        if device_px(HSTEP, zoom) != self.x:
            self.x = device_px(HSTEP, zoom)
            child.dirty_x = True
            child.mark_dirty()
            self.dirty_x = False
        if device_px(VSTEP, zoom) != self.y:
            self.y = device_px(VSTEP, zoom)
            child.dirty_y = True
            child.mark_dirty()
            self.dirty_y = False
        child.layout(zoom)
        self.height = child.height + 2* device_px(VSTEP, zoom)

@wbetools.patch(BlockLayout)
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        self.node = node
        node.layout_object = self
        self.parent = parent
        self.previous = previous
        self.next = None
        if previous: previous.next = self
        self.children = []
        self.frame = frame

        self.x = None
        self.y = None
        self.width = None
        self.height = None

        self.dirty_children = True
        self.dirty_inline_children = True
        self.dirty_zoom = True
        self.zoom = None
        self.dirty_style = True
        self.dirty_width = True
        self.dirty_height = True
        self.dirty_x = True
        self.dirty_y = True
        self.dirty_descendants = True

    def mark_dirty(self):
        if isinstance(self.parent, BlockLayout) and \
            not self.parent.dirty_descendants:
            self.parent.dirty_descendants = True
            self.parent.mark_dirty()

    def layout(self, zoom):
        self.dirty_zoom = (zoom != self.zoom)
        if self.dirty_zoom:
            self.zoom = zoom
            self.mark_dirty()
            self.dirty_inline_children = True
            self.dirty_zoom = False

        if self.dirty_style:
            self.dirty_inline_children = True
            self.mark_dirty()
            self.dirty_style = False

        if self.dirty_width:
            assert not self.parent.dirty_width
            self.width = self.parent.width
            self.dirty_children = True
            for child in self.children:
                child.dirty_width = True
                child.mark_dirty()
            self.dirty_width = False

        if self.dirty_x:
            assert not self.parent.dirty_x
            self.x = self.parent.x
            for child in self.children:
                child.dirty_x = True
                child.mark_dirty()
            self.dirty_x = False

        if self.dirty_y:
            assert not self.previous or not self.previous.dirty_y
            assert not self.previous or not self.previous.dirty_height
            assert not self.parent.dirty_y
            if self.previous:
                self.y = self.previous.y + self.previous.height
            else:
                self.y = self.parent.y
            for child in self.children:
                child.dirty_y = True
                child.mark_dirty()
            if self.next:
                self.next.dirty_y = True
                self.next.mark_dirty()
            self.dirty_y = False

        previous = None
        if layout_mode(self.node) == "block":
            if self.dirty_children:
                self.children = []
                previous = None
                for child in self.node.children:
                    next = BlockLayout(child, self, previous, self.frame)
                    self.children.append(next)
                    previous = next
        else:
            if self.dirty_inline_children or self.dirty_children:
                self.children = []
                self.new_line()
                assert not self.dirty_zoom
                self.recurse(self.node, zoom)
            self.dirty_inline_children = False
        self.dirty_children = False

        assert not self.dirty_children
        assert not self.dirty_zoom
        if self.dirty_descendants:
            for child in self.children:
                child.layout(zoom)

        if self.dirty_height:
            assert not self.dirty_children
            for child in self.children:
                assert not child.dirty_height
            new_height = sum([child.height for child in self.children])
            if self.height != new_height:
                self.height = new_height
                self.parent.dirty_height = True
                self.parent.mark_dirty()
                self.dirty_height = False
                if self.next:
                    self.next.dirty_y = True
                    self.next.mark_dirty()

    def paint(self, display_list):
        assert not self.dirty_children
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

@wbetools.patch(JSContext)
class JSContext:
    def innerHTML_set(self, handle, s):
        doc = HTMLParser(
            "<html><body>" + s + "</body></html>").parse()
        new_nodes = doc.children[0].children
        elt = self.handle_to_node[handle]
        elt.children = new_nodes
        for child in elt.children:
            child.parent = elt
        self.tab.set_needs_render()
        elt.layout_object.dirty_children = True
        elt.layout_object.mark_dirty()

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

    if node.style != old_style and node.layout_object:
        node.layout_object.dirty_style = True
        node.layout_object.mark_dirty()

    for child in node.children:
        style(child, rules, frame)

@wbetools.patch(LineLayout)
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

        self.dirty_height = False
        self.dirty_width = False
        self.dirty_x = False
        self.dirty_y = False

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

        self.dirty_width = False
        self.dirty_height = False
        self.dirty_x = False
        self.dirty_y = False

if __name__ == "__main__":
    main()
