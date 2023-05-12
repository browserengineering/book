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
    CSSParser
from lab15 import request, DrawImage, DocumentLayout, BlockLayout, \
    EmbedLayout, InputLayout, LineLayout, TextLayout, ImageLayout, \
    IframeLayout, JSContext, style, AccessibilityNode, Frame, Tab, \
    CommitData, draw_line, Browser, BROKEN_IMAGE, font
import wbetools

def mark_dirty(node):
    if isinstance(node.parent, BlockLayout) and \
        not node.parent.dirty_descendants:
        node.parent.dirty_descendants = True
        mark_dirty(node.parent)

@wbetools.patch(Element)
class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.parent = parent

        self.animations = {}

        self.is_focused = False
        self.layout_object = None

        self.children_field = DependentField(self, "children")
        self.children = self.children_field.set([])
        self.style_field = DependentField(self, "style")
        self.style = {}

@wbetools.patch(Text)
class Text:
    def __init__(self, text, parent):
        self.text = text
        self.parent = parent

        self.animations = {}

        self.is_focused = False
        self.layout_object = None

        self.children_field = DependentField(self, "children")
        self.children = self.children_field.set([])
        self.style_field = DependentField(self, "style")
        self.style = {}

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


@wbetools.patch(Frame)
class Frame:
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
            task = Task(
                self.js.run, script_url, body,
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

        # Changed---create DocumentLayout here
        self.document = DocumentLayout(self.nodes, self)
        self.set_needs_render()

        # For testing only?
        self.measure_layout = MeasureTime("layout")

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
            self.tab.focus.children_field.notify()
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
            # Change here
            self.measure_layout.start_timing()
            self.document.layout(self.frame_width, self.tab.zoom)
            self.measure_layout.stop_timing()
            if self.tab.accessibility_is_on:
                self.tab.needs_accessibility = True
            else:
                self.needs_paint = True
            self.needs_layout = False

        clamped_scroll = self.clamp_scroll(self.scroll)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_frame = True
        self.scroll = clamped_scroll

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

        self.fields = FieldManager(self)
        self.zoom_field = self.fields.add("zoom")
        self.x_field = self.fields.add("x")
        self.y_field = self.fields.add("y")
        self.width_field = self.fields.add("width")
        self.height_field = self.fields.add("height")

    def layout(self):
        parent_zoom = self.zoom_field.read(self.parent.zoom_field)
        self.zoom = self.zoom_field.set(parent_zoom)

        parent_width = self.width_field.read(self.parent.width_field)
        self.width = self.width_field.set(parent_width)

        parent_x = self.x_field.read(self.parent.x_field)
        self.x = self.x_field.set(parent_x)

        if self.previous:
            prev_y = self.y_field.read(self.previous.y_field)
            prev_height = self.y_field.read(self.previous.height_field)
            self.y = self.y_field.set(prev_y + prev_height)
        else:
            parent_y = self.y_field.read(self.parent.y_field)
            self.y = self.y_field.set(parent_y)

        for word in self.children:
            word.layout()

        if not self.children:
            self.height = self.height_field.set(0)
            return

        max_ascent = max([-child.get_ascent(1.25) 
                          for child in self.children])
        baseline = self.y + max_ascent
        for child in self.children:
            child.y = baseline + child.get_ascent()
        max_descent = max([child.get_descent(1.25)
                           for child in self.children])

        self.height = self.height_field.set(max_ascent + max_descent)
        self.fields.check()
        
class DependentField:
    def __init__(self, base, name):
        self.base = base
        self.name = name
        self.value = None
        self.dirty = True
        self.depended_on = set()

    def depend(self, source):
        source.depended_on.add(self)
        self.dirty = True

    def read(self, field):
        assert not field.dirty
        self.depend(field)
        return field.value

    def set(self, value):
        if value != self.value:
            self.value = value
            self.notify()
        self.dirty = False
        return value

    def notify(self):
        for field in self.depended_on:
            field.dirty = True
            field.notify()

class FieldManager(DependentField):
    def __init__(self, base):
        super().__init__(base, "fields")
        self.fields = []

    def add(self, name):
        field = DependentField(self.base, name)
        field.depended_on.add(self)
        self.fields.append(field)
        return field

    def check(self):
        assert all([not field.dirty for field in self.fields])
        self.dirty = False
        
@wbetools.patch(BlockLayout)
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        self.node = node
        node.layout_object = self
        self.parent = parent
        self.previous = previous
        self.children = []
        self.frame = frame

        if previous: previous.next = self
        self.next = None

        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.zoom = None

        self.fields = FieldManager(self)
        self.children_field = self.fields.add("children")
        self.zoom_field = self.fields.add("zoom")
        self.width_field = self.fields.add("width")
        self.x_field = self.fields.add("x")
        self.y_field = self.fields.add("y")
        self.height_field = self.fields.add("height")
        self.descendants = self.fields.add("descendants")

    def layout(self):
        if self.zoom_field.dirty:
            parent_zoom = self.zoom_field.read(self.parent.zoom_field)
            self.zoom = self.zoom_field.set(parent_zoom)

        if self.width_field.dirty:
            node_style = self.width_field.read(self.node.style_field)
            if "width" in node_style:
                zoom = self.width_field.read(self.zoom_field)
                self.width = self.width_field.set(device_px(float(node_style["width"][:-2]), zoom))
            else:
                parent_width = self.width_field.read(self.parent.width_field)
                self.width = self.width_field.set(parent_width)

        if self.x_field.dirty:
            parent_x = self.x_field.read(self.parent.x_field)
            self.x = self.x_field.set(parent_x)

        if self.y_field.dirty:
            if self.previous: # Never changes
                prev_y = self.y_field.read(self.previous.y_field)
                prev_height = self.y_field.read(self.previous.height_field)
                self.y = self.y_field.set(prev_y + prev_height)
            else:
                parent_y = self.y_field.read(self.parent.y_field)
                self.y = self.y_field.set(parent_y)
            
        if self.children_field.dirty:
            node_children = self.children_field.read(self.node.children_field)
            mode = layout_mode(self.node)
            if mode == "block":
                self.children = []
                previous = None
                for child in node_children:
                    next = BlockLayout(child, self, previous, self.frame)
                    self.children.append(next)
                    previous = next
                    self.descendants.depend(next.fields)
                self.children_field.set(self.children)
            else:
                self.children_field.read(self.node.style_field)
                self.children_field.read(self.width_field)
                self.children = []
                self.new_line()
                self.recurse(self.node)
                self.children_field.set(self.children)

        if self.descendants.dirty:
            for child in self.children:
                child.layout()
            self.descendants.set(None) # Reset to clean but do not notify

        if self.height_field.dirty:
            children = self.height_field.read(self.children_field)
            new_height = sum([
                self.height_field.read(child.height_field)
                for child in self.children
            ])
            self.height = self.height_field.set(new_height)

        self.fields.check()

    def recurse(self, node):
        if isinstance(node, Text):
            self.text(node)
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
        self.descendants.depend(new_line.fields)

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
        self.cursor_x += w + font(node, self.zoom).measureText(" ")
        # TODO: don't currently depend on child.fields because it doesn't exist
        # but that is probably a bug (what if you change innerHTML on an inline element?)

    def paint(self, display_list):
        assert not self.children_field.dirty
        
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

@wbetools.patch(InputLayout)
class InputLayout(EmbedLayout):
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
            cmds.append(DrawCursor(self, self.font.measureText(text)))

        cmds = paint_visual_effects(self.node, cmds, rect)
        paint_outline(self.node, cmds, rect, self.zoom)
        display_list.extend(cmds)
        
def DrawCursor(elt, width):
    return DrawLine(elt.x + width, elt.y, elt.x + width, elt.y + elt.height)

@wbetools.patch(DocumentLayout)
class DocumentLayout:
    def __init__(self, node, frame):
        self.node = node
        self.frame = frame
        node.layout_object = self
        self.parent = None
        self.previous = None
        self.children = []

        self.fields = FieldManager(self)
        self.zoom_field = self.fields.add("zoom")
        self.width_field = self.fields.add("width")
        self.height_field = self.fields.add("height")
        self.x_field = self.fields.add("x")
        self.y_field = self.fields.add("y")

        self.width = None
        self.height = None
        self.x = None
        self.y = None

    def layout(self, width, zoom):
        if not self.children:
            child = BlockLayout(self.node, self, None, self.frame)
        else:
            child = self.children[0]
        self.children = [child]

        self.zoom = self.zoom_field.set(zoom)
        self.width = self.width_field.set(width - 2 * device_px(HSTEP, zoom))
        self.x = self.x_field.set(device_px(HSTEP, zoom))
        self.y = self.y_field.set(device_px(VSTEP, zoom))
        child.layout()
        child_height = self.height_field.read(child.height_field)
        self.height = self.height_field.set(child_height + 2*device_px(VSTEP, zoom))
        self.fields.check()

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
        frame.set_needs_render()

        elt.children_field.notify()

@wbetools.patch(style)
def style(node, rules, frame):
    if node.style_field.dirty:
        old_style = node.style
        new_style = {}
    
        for property, default_value in INHERITED_PROPERTIES.items():
            if node.parent:
                parent_style = node.style_field.read(node.parent.style_field)
                new_style[property] = parent_style[property]
            else:
                new_style[property] = default_value
        for media, selector, body in rules:
            if media:
                if (media == "dark") != frame.tab.dark_mode: continue
            if not selector.matches(node): continue
            for property, value in body.items():
                computed_value = compute_style(node, property, value)
                if not computed_value: continue
                if node.parent and property == "font-size" and value.endswith("%"):
                    node.style_field.read(node.parent.style_field)
                new_style[property] = computed_value
        if isinstance(node, Element) and "style" in node.attributes:
            pairs = CSSParser(node.attributes["style"]).body()
            for property, value in pairs.items():
                computed_value = compute_style(node, property, value)
                if not computed_value: continue
                if node.parent and property == "font-size" and value.endswith("%"):
                    node.style_field.read(node.parent.style_field)
                new_style[property] = computed_value
    
        if old_style:
            transitions = diff_styles(old_style, new_style)
            for property, (old_value, new_value, num_frames) \
                in transitions.items():
                if property in ANIMATED_PROPERTIES:
                    frame.set_needs_render()
                    AnimationClass = ANIMATED_PROPERTIES[property]
                    animation = AnimationClass(
                        old_value, new_value, num_frames)
                    node.animations[property] = animation
                    new_style[property] = animation.animate()
    
        node.style = node.style_field.set(new_style)

    for child in node.children:
        style(child, rules, frame)

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
