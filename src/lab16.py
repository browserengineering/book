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
    InputLayout, LineLayout, TextLayout, ImageLayout, \
    IframeLayout, JSContext, style, AccessibilityNode, Frame, Tab, \
    CommitData, draw_line, Browser
import wbetools

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
            self.measure_layout.start()
            self.document.layout(self.frame_width, self.tab.zoom)
            self.measure_layout.stop()
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

        self.dirty_width = True
        self.dirty_height = True
        self.dirty_x = True
        self.dirty_y = True

    def mark_dirty(self):
        if isinstance(self.parent, BlockLayout) and \
            not self.parent.dirty_descendants:
            self.parent.dirty_descendants = True
            self.parent.mark_dirty()

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
            self.parent.dirty_height = True
            self.parent.mark_dirty()
            return

        max_ascent = max([-child.get_ascent(1.25) 
                          for child in self.children])
        baseline = self.y + max_ascent
        for child in self.children:
            child.y = baseline + child.get_ascent()
        max_descent = max([child.get_descent(1.25)
                           for child in self.children])
        self.height = max_ascent + max_descent
        self.parent.dirty_height = True
        self.parent.mark_dirty()

        self.dirty_width = False
        self.dirty_height = False
        self.dirty_x = False
        self.dirty_y = False

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

        self.dirty_children = True
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

    def layout(self):
        if self.dirty_zoom:
            self.zoom = self.parent.zoom
            for child in self.children:
                child.mark_dirty()
                child.dirty_zoom = True
            self.mark_dirty()
            self.dirty_width = True
            self.dirty_zoom = False

        if self.dirty_style:
            self.dirty_children = True
            self.dirty_width = True
            self.mark_dirty()
            self.dirty_style = False

        if self.dirty_width:
            assert not self.parent.dirty_width
            if "width" in self.node.style:
                self.width = device_px(float(self.node.style["width"][:-2]), zoom)
            else:
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

        mode = layout_mode(self.node)
        if self.dirty_children:
            if mode == "block":
                self.children = []
                previous = None
                for child in self.node.children:
                    next = BlockLayout(child, self, previous, self.frame)
                    self.children.append(next)
                    previous = next
                self.dirty_descendants = True
                self.mark_dirty()
            else:
                self.children = []
                self.new_line()
                self.recurse(self.node)
                self.dirty_descendants = True
                self.mark_dirty()
            self.dirty_children = False

        if self.dirty_descendants:
            assert not self.dirty_children
            assert not self.dirty_zoom
            for child in self.children:
                child.layout()
            self.dirty_descendants = False

        if self.dirty_height:
            assert not self.dirty_children
            for child in self.children:
                assert not child.dirty_height
            new_height = sum([child.height for child in self.children])
            if self.height != new_height:
                self.height = new_height
                self.parent.dirty_height = True
                self.parent.mark_dirty()
                if self.next:
                    self.next.dirty_y = True
                    self.next.mark_dirty()
            self.dirty_height = False

    def recurse(self, node):
        assert not self.dirty_style
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

    def paint(self, display_list):
        assert not self.dirty_children
        
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

@wbetools.patch(DocumentLayout)
class DocumentLayout:
    def __init__(self, node, frame):
        self.node = node
        self.frame = frame
        node.layout_object = self
        self.parent = None
        self.previous = None
        self.children = []

        self.zoom = None
        self.width = None
        self.height = None
        self.x = None
        self.y = None

        self.dirty_height = True
        self.dirty_width = True
        self.dirty_x = True
        self.dirty_y = True

    def mark_dirty(self):
        if isinstance(self.parent, BlockLayout) and \
            not self.parent.dirty_descendants:
            self.parent.dirty_descendants = True
            self.parent.mark_dirty()

    def layout(self, width, zoom):
        if not self.children:
            child = BlockLayout(self.node, self, None, self.frame)
        else:
            child = self.children[0]
        self.children = [child]

        if zoom != self.zoom:
            self.zoom = zoom
            child.dirty_zoom = True
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
        child.layout()
        assert not child.dirty_height
        self.height = child.height + 2* device_px(VSTEP, zoom)

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
