"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 12 (Scheduling and Threading),
without exercises.
"""

import ctypes
import dukpy
import math
import sdl2
import skia
import socket
import ssl
import threading
import time
import urllib.parse
import wbetools

from lab2 import WIDTH, HEIGHT, HSTEP, VSTEP, SCROLL_STEP
from lab4 import print_tree, HTMLParser
from lab5 import BLOCK_ELEMENTS, DocumentLayout
from lab6 import CSSParser, TagSelector, DescendantSelector
from lab6 import INHERITED_PROPERTIES, style, cascade_priority
from lab6 import tree_to_list
from lab7 import intersects
from lab8 import Text, Element, INPUT_WIDTH_PX
from lab9 import EVENT_DISPATCH_CODE
from lab10 import COOKIE_JAR, JSContext, URL
from lab11 import get_font, FONTS, DrawLine, DrawRect, DrawOutline, linespace, DrawText, SaveLayer, ClipRRect
from lab11 import BlockLayout, LineLayout, TextLayout, InputLayout, Chrome
from lab11 import paint_visual_effects, parse_blend_mode, parse_color, Tab, Browser

class MeasureTime:
    def __init__(self, name):
        self.name = name
        self.start_time = None
        self.total_s = 0
        self.count = 0

    def start_timing(self):
        self.start_time = time.time()

    def text_current(self, name):
        print("Time after {}: {}ms".format(
            name, (time.time() - self.start_time) * 1000))

    def stop_timing(self):
        self.total_s += time.time() - self.start_time
        self.count += 1
        self.start_time = None

    def text(self):
        if self.count == 0: return ""
        avg = self.total_s / self.count
        self.count = 0
        self.total_s = 0
        return "Time in {} on average: {:>.0f}ms".format(
            self.name, avg * 1000)

SETTIMEOUT_CODE = "__runSetTimeout(dukpy.handle)"
XHR_ONLOAD_CODE = "__runXHROnload(dukpy.out, dukpy.handle)"

@wbetools.patch(JSContext)
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
        self.interp.export_function("XMLHttpRequest_send",
            self.XMLHttpRequest_send)
        self.interp.export_function("setTimeout",
            self.setTimeout)
        self.interp.export_function("requestAnimationFrame",
            self.requestAnimationFrame)
        with open("runtime12.js") as f:
            self.interp.evaljs(f.read())

        self.node_to_handle = {}
        self.handle_to_node = {}

    def run(self, script, code):
        try:
            self.interp.evaljs(code)
        except dukpy.JSRuntimeError as e:
            print("Script", script, "crashed", e)

    def innerHTML_set(self, handle, s):
        doc = HTMLParser(
            "<html><body>" + s + "</body></html>").parse()
        new_nodes = doc.children[0].children
        elt = self.handle_to_node[handle]
        elt.children = new_nodes
        for child in elt.children:
            child.parent = elt
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

    def XMLHttpRequest_send(
        self, method, url, body, isasync, handle):
        full_url = self.tab.url.resolve(url)
        if not self.tab.allowed_request(full_url):
            raise Exception("Cross-origin XHR blocked by CSP")
        if full_url.origin() != self.tab.url.origin():
            raise Exception(
                "Cross-origin XHR request not allowed")

        def run_load():
            headers, response = full_url.request(self.tab.url, body)
            task = Task(self.dispatch_xhr_onload, response, handle)
            self.tab.task_runner.schedule_task(task)
            if not isasync:
                return response

        if not isasync:
            return run_load()
        else:
            threading.Thread(target=run_load).start()

    def requestAnimationFrame(self):
        self.tab.browser.set_needs_animation_frame(self.tab)

def clamp_scroll(scroll, document_height, tab_height):
    return max(0, min(
        scroll, document_height - tab_height))

@wbetools.patch(Tab)
class Tab:
    def __init__(self, browser, tab_height):
        self.history = []
        self.tab_height = tab_height
        self.focus = None
        self.url = None
        self.scroll = 0
        self.scroll_changed_in_tab = False
        self.needs_raf_callbacks = False
        self.needs_render = False
        self.browser = browser
        if wbetools.USE_BROWSER_THREAD:
            self.task_runner = TaskRunner(self)
        else:
            self.task_runner = SingleThreadedTaskRunner(self)
        self.task_runner.start_thread()

        self.measure_render = MeasureTime("render")

        with open("browser8.css") as f:
            self.default_style_sheet = CSSParser(f.read()).parse()

    def load(self, url, body=None):
        self.scroll = 0
        self.scroll_changed_in_tab = True
        self.task_runner.clear_pending_tasks()
        headers, body = url.request(self.url, body)
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
            script_url = url.resolve(script)
            if not self.allowed_request(script_url):
                print("Blocked script", script, "due to CSP")
                continue

            header, body = script_url.request(url)
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
            style_url = url.resolve(link)
            if not self.allowed_request(style_url):
                print("Blocked style", link, "due to CSP")
                continue
            try:
                header, body = style_url.request(url)
            except:
                continue
            self.rules.extend(CSSParser(body).parse())
        self.set_needs_render()

    def set_needs_render(self):
        self.needs_render = True
        self.browser.set_needs_animation_frame(self)

    def run_animation_frame(self, scroll):
        if not self.scroll_changed_in_tab:
            self.scroll = scroll
        self.js.interp.evaljs("__runRAFHandlers()")

        self.render()

        document_height = math.ceil(self.document.height + 2*VSTEP)
        clamped_scroll = clamp_scroll(
            self.scroll, document_height, self.tab_height)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_tab = True
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_tab = True
        self.scroll = clamped_scroll

        scroll = None
        if self.scroll_changed_in_tab:
            scroll = self.scroll
        commit_data = CommitData(
            self.url, scroll, document_height, self.display_list)
        self.display_list = None
        self.browser.commit(self, commit_data)
        self.scroll_changed_in_tab = False

    def render(self):
        if not self.needs_render: return
        self.measure_render.start_timing()
        style(self.nodes, sorted(self.rules,
            key=cascade_priority))
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        self.document.paint(self.display_list)
        self.measure_render.stop_timing()
        self.needs_render = False

    def click(self, x, y):
        self.render()
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
                url = self.url.resolve(elt.attributes["href"])
                self.load(url)
                return
            elif elt.tag == "input":
                elt.attributes["value"] = ""
                if self.focus:
                    self.focus.is_focused = False
                self.focus = elt
                elt.is_focused = True
                self.set_needs_render()
                return
            elif elt.tag == "button":
                while elt.parent:
                    if elt.tag == "form" and "action" in elt.attributes:
                        return self.submit_form(elt)
                    elt = elt.parent
            elt = elt.parent

class Task:
    def __init__(self, task_code, *args):
        self.task_code = task_code
        self.args = args
        self.__name__ = "task"

    def run(self):
        self.task_code(*self.args)
        self.task_code = None
        self.args = None

class SingleThreadedTaskRunner:
    def __init__(self, tab):
        self.tab = tab
        self.needs_quit = False
        self.tasks = []

    def schedule_task(self, callback):
        self.tasks.append(callback)

    def run_tasks(self):
        while self.tasks:
            task = self.tasks.pop(0)
            task.run()

    def clear_pending_tasks(self):
        self.tasks = []

    def start_thread(self):    
        pass

    def set_needs_quit(self):
        self.needs_quit = True
        pass

    def run(self):
        pass

class CommitData:
    def __init__(self, url, scroll, height, display_list):
        self.url = url
        self.scroll = scroll
        self.height = height
        self.display_list = display_list

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

    def start_thread(self):
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

REFRESH_RATE_SEC = 0.016 # 16ms

@wbetools.patch(Chrome)
class Chrome:
    def click(self, x, y):
        if intersects(x, y, self.plus_bounds()):
            self.browser.load_internal(URL("https://browser.engineering/"))
        elif intersects(x, y, self.backbutton_bounds()):
            active_tab = self.browser.tabs[self.browser.active_tab]
            task = Task(active_tab.go_back)
            active_tab.task_runner.schedule_task(task)
        elif intersects(x, y, self.addressbar_bounds()):
            self.browser.focus = "address bar"
            self.browser.raddress_bar = ""
        else:
            for i, tab in enumerate(self.browser.tabs):
                if intersects(x, y, self.tab_bounds(i)):
                    self.browser.set_active_tab(i)
                    active_tab = self.browser.tabs[self.browser.active_tab]
                    task = Task(active_tab.set_needs_render)
                    active_tab.task_runner.schedule_task(task)
                    break

@wbetools.patch(Browser)
class Browser:
    def __init__(self):
        self.chrome = Chrome(self)

        self.sdl_window = sdl2.SDL_CreateWindow(b"Browser",
            sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
            WIDTH, HEIGHT, sdl2.SDL_WINDOW_SHOWN)
        self.root_surface = skia.Surface.MakeRaster(
            skia.ImageInfo.Make(
            WIDTH, HEIGHT,
            ct=skia.kRGBA_8888_ColorType,
            at=skia.kUnpremul_AlphaType))
        self.chrome_surface = skia.Surface(WIDTH, self.chrome.bottom)
        self.tab_surface = None

        self.tabs = []
        self.active_tab = None
        self.focus = None
        self.address_bar = ""
        self.lock = threading.Lock()
        self.url = None
        self.scroll = 0

        self.measure_raster_and_draw = MeasureTime("raster-and-draw")

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
        self.needs_raster_and_draw = False

        self.active_tab_height = 0
        self.active_tab_display_list = None

    def render(self):
        assert not wbetools.USE_BROWSER_THREAD
        tab = self.tabs[self.active_tab]
        tab.task_runner.run_tasks()
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
            self.set_needs_raster_and_draw()
        self.lock.release()

    def set_needs_animation_frame(self, tab):
        self.lock.acquire(blocking=True)
        if tab == self.tabs[self.active_tab]:
            self.needs_animation_frame = True
        self.lock.release()

    def set_needs_raster_and_draw(self):
        self.needs_raster_and_draw = True

    def raster_and_draw(self):
        self.lock.acquire(blocking=True)
        if not self.needs_raster_and_draw:
            self.lock.release()
            return
        self.measure_raster_and_draw.start_timing()
        self.raster_chrome()
        self.raster_tab()
        self.draw()
        self.measure_raster_and_draw.stop_timing()
        self.needs_raster_and_draw = False
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
        if not self.active_tab_height:
            self.lock.release()
            return
        scroll = clamp_scroll(
            self.scroll + SCROLL_STEP,
            self.active_tab_height,
            HEIGHT - self.chrome.bottom)
        self.scroll = scroll
        self.set_needs_raster_and_draw()
        self.needs_animation_frame = True
        self.lock.release()

    def set_active_tab(self, index):
        self.active_tab = index
        self.scroll = 0
        self.url = None
        self.needs_animation_frame = True

    def handle_click(self, e):
        self.lock.acquire(blocking=True)
        if e.y < self.chrome.bottom:
            self.focus = None
            self.chrome.click(e.x, e.y)
            self.set_needs_raster_and_draw()
        else:
            if self.focus != "content":
                self.focus = "content"
                self.set_needs_raster_and_draw()
            else:
                self.focus = "content"
            active_tab = self.tabs[self.active_tab]
            task = Task(active_tab.click, e.x, e.y - self.chrome.bottom)
            active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def handle_key(self, char):
        self.lock.acquire(blocking=True)
        if not (0x20 <= ord(char) < 0x7f): return
        if self.focus == "address bar":
            self.address_bar += char
            self.set_needs_raster_and_draw()
        elif self.focus == "content":
            active_tab = self.tabs[self.active_tab]
            task = Task(active_tab.keypress, char)
            active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def schedule_load(self, url, body=None):
        active_tab = self.tabs[self.active_tab]
        active_tab.task_runner.clear_pending_tasks()
        task = Task(active_tab.load, url, body)
        active_tab.task_runner.schedule_task(task)

    def handle_enter(self):
        self.lock.acquire(blocking=True)
        if self.focus == "address bar":
            self.schedule_load(URL(self.address_bar))
            self.url = self.address_bar
            self.focus = None
            self.set_needs_raster_and_draw()
        self.lock.release()

    def load(self, url):
        self.lock.acquire(blocking=True)
        self.load_internal(url)
        self.lock.release()

    def load_internal(self, url):
        new_tab = Tab(self, HEIGHT - self.chrome.bottom)
        self.set_active_tab(len(self.tabs))
        self.tabs.append(new_tab)
        self.schedule_load(url)

    def raster_tab(self):
        if self.active_tab_height == None:
            return
        if not self.tab_surface or \
                self.active_tab_height != self.tab_surface.height():
            self.tab_surface = skia.Surface(WIDTH, self.active_tab_height)

        canvas = self.tab_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        for cmd in self.active_tab_display_list:
            cmd.execute(canvas)

    def handle_quit(self):
        print(self.measure_raster_and_draw.text())
        self.tabs[self.active_tab].task_runner.set_needs_quit()
        sdl2.SDL_DestroyWindow(self.sdl_window)

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Toy browser')
    parser.add_argument("url", type=str, help="URL to load")
    parser.add_argument('--single_threaded', action="store_true", default=False,
        help='Whether to run the browser without a browser thread')
    args = parser.parse_args()

    wbetools.USE_BROWSER_THREAD = not args.single_threaded

    sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS)
    browser = Browser()
    browser.load(URL(args.url))
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
        if not wbetools.USE_BROWSER_THREAD:
            if active_tab.task_runner.needs_quit:
                break
            if browser.needs_animation_frame:
                browser.needs_animation_frame = False
                browser.render()
        browser.raster_and_draw()
        browser.schedule_animation_frame()
