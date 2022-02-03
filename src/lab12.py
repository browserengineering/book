"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 12 (Scheduling and Threading),
without exercises.
"""

import ctypes
import dukpy
import io
import math
import sdl2
import sdl2.ext as sdl2ext
import skia
import socket
import ssl
import threading
import time
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
from lab6 import CSSParser, compute_style, style
from lab6 import TagSelector, DescendantSelector
from lab9 import EVENT_DISPATCH_CODE
from lab10 import COOKIE_JAR, request, url_origin
from lab11 import DocumentLayout, DrawLine, parse_color

class Timer:
    def __init__(self):
        self.time = None

    def start(self):
        self.time = time.time()

    def stop(self):
        result = time.time() - self.time
        self.time = None
        return result

FONTS = {}

def request(url, top_level_url, payload=None, lock=None):
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

    if lock:
        lock.acquire(blocking=True)
    has_cookie = host in COOKIE_JAR
    if has_cookie:
        cookie, params = COOKIE_JAR[host]
    if lock:
        lock.release()

    if has_cookie:
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

        if lock:
            lock.acquire(blocking=True)
        COOKIE_JAR[host] = (cookie, params)
        if lock:
            lock.release()

    body = response.read()
    s.close()

    return headers, body

def async_request(url, top_level_url, results, lock):
    headers = None
    body = None
    def runner():
        headers, body = request(url, top_level_url, None, lock)
        results[url] = {'headers': headers, 'body': body}
    thread = threading.Thread(target=runner)
    thread.start()
    return thread

def draw_line(canvas, x1, y1, x2, y2):
    path = skia.Path().moveTo(x1, y1).lineTo(x2, y2)
    paint = skia.Paint(Color=skia.ColorBLACK)
    paint.setStyle(skia.Paint.kStroke_Style)
    paint.setStrokeWidth(1);
    canvas.drawPath(path, paint)

def draw_text(canvas, x, y, text, font, color=None):
    sk_color = parse_color(color)
    paint = skia.Paint(AntiAlias=True, Color=sk_color)
    canvas.drawString(
        text, float(x), y - font.getMetrics().fAscent,
        font, paint)

def draw_rect(canvas, l, t, r, b, fill=None, width=1):
    paint = skia.Paint()
    if fill:
        paint.setStrokeWidth(width);
        paint.setColor(parse_color(fill))
    else:
        paint.setStyle(skia.Paint.kStroke_Style)
        paint.setStrokeWidth(1);
        paint.setColor(skia.ColorBLACK)
    rect = skia.Rect.MakeLTRB(l, t, r, b)
    canvas.drawRect(rect, paint)


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
        self.interp.export_function("XMLHttpRequest_send",
            self.XMLHttpRequest_send)
        self.interp.export_function("setTimeout",
            self.setTimeout)
        self.interp.export_function("now",
            self.now)
        self.interp.export_function("requestAnimationFrame",
            self.requestAnimationFrame)
        with open("runtime12.js") as f:
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

    def setTimeout(self, handle, time):
        def run_callback():
            self.tab.task_runner.schedule_task(
                Task(self.interp.evaljs,
                    "__runSetTimeout({})".format(handle)))

        threading.Timer(time / 1000.0, run_callback).start()

    def xhr_onload(self, out, handle):
        do_default = self.interp.evaljs(
            XHR_ONLOAD_CODE, out=out, handle=handle)

    def XMLHttpRequest_send(
        self, method, url, body, is_async, handle):
        full_url = resolve_url(url, self.tab.url)
        if not self.tab.allowed_request(full_url):
            raise Exception("Cross-origin XHR blocked by CSP")
        if url_origin(full_url) != url_origin(self.tab.url):
            raise Exception(
                "Cross-origin XHR request not allowed")

        def run_load():
            headers, out = request(
                full_url, self.tab.url, payload=body)
            handle_local = handle
            self.tab.task_runner.schedule_task(
                Task(self.xhr_onload, out, handle_local))
            return out

        if not is_async:
            return run_load(is_async)
        else:
            load_thread = threading.Thread(target=run_load)
            load_thread.start()

    def now(self):
        return int(time.time() * 1000)

    def requestAnimationFrame(self):
        self.tab.request_animation_frame_callback()

SCROLL_STEP = 100
CHROME_PX = 100

USE_BROWSER_THREAD = True

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
        self.needs_render = False
        self.browser = browser
        if USE_BROWSER_THREAD:
            self.task_runner = TaskRunner(self)
        else:
            self.task_runner = SingleThreadedTaskRunner(self)
        self.task_runner.start()

        self.time_in_style_layout_and_paint = 0.0
        self.num_renders = 0

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

        async_requests = []
        script_results = {}
        for script in scripts:
            script_url = resolve_url(script, url)
            if not self.allowed_request(script_url):
                print("Blocked script", script, "due to CSP")
                continue
            async_requests.append({
                "url": script_url,
                "type": "script",
                "thread": async_request(
                    script_url, url, script_results, self.task_runner.lock)
            })
 
        self.rules = self.default_style_sheet.copy()
        links = [node.attributes["href"]
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "link"
                 and "href" in node.attributes
                 and node.attributes.get("rel") == "stylesheet"]

        style_results = {}
        for link in links:
            style_url = resolve_url(link, url)
            if not self.allowed_request(style_url):
                print("Blocked style", link, "due to CSP")
                continue
            async_requests.append({
                "url": style_url,
                "type": "style sheet",
                "thread": async_request(
                    style_url, url, style_results, self.task_runner.lock)
            })

        for async_req in async_requests:
            async_req["thread"].join()
            req_url = async_req["url"]
            if async_req["type"] == "script":
                self.task_runner.schedule_task(
                    Task(self.js.run, req_url,
                        script_results[req_url]['body']))
            else:
                self.rules.extend(
                    CSSParser(
                        style_results[req_url]['body']).parse())

        self.set_needs_render()

    def set_needs_render(self):
        self.needs_render = True
        self.browser.set_needs_animation_frame()

    def request_animation_frame_callback(self):
        self.needs_raf_callbacks = True
        self.browser.set_needs_animation_frame()

    def run_animation_frame(self, scroll):
        self.scroll = scroll
        if self.needs_raf_callbacks:
            self.needs_raf_callbacks = False
            self.js.interp.evaljs("__runRAFHandlers()")

        self.render()

        document_height = math.ceil(self.document.height)
        clamped_scroll = clamp_scroll(self.scroll, document_height)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_tab = True
        self.scroll = clamped_scroll

        self.browser.commit(
            self.url,
            clamped_scroll if self.scroll_changed_in_tab \
                else None, 
            document_height, self.display_list)
        self.scroll_changed_in_tab = False

    def render(self):
        if not self.needs_render:
            return
        timer = Timer()
        timer.start()
        style(self.nodes, sorted(self.rules,
            key=cascade_priority))
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []

        self.document.paint(self.display_list)
        if self.focus:
            obj = [obj for obj in tree_to_list(self.document, [])
                   if obj.node == self.focus][0]
            text = self.focus.attributes.get("value", "")
            x = obj.x + obj.font.measureText(text)
            y = obj.y
            self.display_list.append(
                DrawLine(x, y, x, y + obj.height))
        self.time_in_style_layout_and_paint += timer.stop()
        self.num_renders += 1
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

    def handle_quit(self):
        print("""Time in style, layout and paint: {:>.6f}s
    ({:>.6f}ms per render on average;
    {} total renders)""".format(
            self.time_in_style_layout_and_paint,
            self.time_in_style_layout_and_paint / \
                self.num_renders * 1000,
            self.num_renders))


WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18

class Task:
    def __init__(self, task_code, *args):
        self.task_code = task_code
        self.args = args
        self.__name__ = "task"

    def __call__(self):
        self.task_code(*self.args)
        self.task_code = None
        self.args = None

class SingleThreadedTaskRunner:
    def __init__(self, tab):
        self.tab = tab
        self.needs_quit = False

    def schedule_task(self, callback):
        callback()

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
        self.lock = threading.Lock()
        self.tab = tab
        self.tasks = []
        self.main_thread = threading.Thread(target=self.run)
        self.needs_quit = False

    def schedule_task(self, callback):
        self.lock.acquire(blocking=True)
        self.tasks.append(callback)
        self.lock.release()

    def set_needs_quit(self):
        self.lock.acquire(blocking=True)
        self.needs_quit = True
        self.lock.release()

    def clear_pending_tasks(self):
        self.tasks.clear()
        self.pending_scroll = None

    def start(self):
        self.main_thread.start()

    def run(self):
        while True:
            self.lock.acquire(blocking=True)
            needs_quit = self.needs_quit
            self.lock.release()
            if needs_quit:
                self.tab.handle_quit()
                return

            task = None
            self.lock.acquire(blocking=True)
            if len(self.tasks) > 0:
                task = self.tasks.pop(0)
            self.lock.release()
            if task:
                task()

REFRESH_RATE_SEC = 0.016 # 16ms

class Browser:
    def __init__(self):
        self.sdl_window = sdl2.SDL_CreateWindow(b"Browser",
            sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
            WIDTH, HEIGHT, sdl2.SDL_WINDOW_SHOWN)
        self.root_surface = skia.Surface.MakeRaster(
            skia.ImageInfo.Make(
            WIDTH, HEIGHT,
            ct=skia.kRGBA_8888_ColorType,
            at=skia.kUnpremul_AlphaType))
        self.chrome_surface = skia.Surface(WIDTH, CHROME_PX)
        self.tab_surface = None

        self.tabs = []
        self.active_tab = None
        self.focus = None
        self.address_bar = ""
        self.lock = threading.Lock()
        self.display_scheduled = False
        self.url = None
        self.scroll = 0

        self.time_in_raster = 0
        self.time_in_draw = 0
        self.num_raster_and_draws = 0

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

        self.needs_animation_frame = False
        self.needs_raster_and_draw = False

        self.active_tab_height = None
        self.active_tab_display_list = None

    def render(self):
        assert not USE_BROWSER_THREAD
        tab = self.tabs[self.active_tab]
        tab.run_animation_frame(self.scroll)

    def commit(self, url, scroll, tab_height, display_list):
        self.lock.acquire(blocking=True)
        if url != self.url or scroll != self.scroll:
            self.set_needs_raster_and_draw()
        self.url = url
        if scroll != None:
            self.scroll = scroll
        self.active_tab_height = tab_height
        self.active_tab_display_list = display_list.copy()
        self.set_needs_raster_and_draw()
        self.lock.release()

    def set_needs_animation_frame(self):
        self.needs_animation_frame = True

    def set_needs_raster_and_draw(self):
        self.needs_raster_and_draw = True
        self.set_needs_animation_frame()

    def raster_and_draw(self):
        if not self.needs_raster_and_draw:
            return
        self.lock.acquire(blocking=True)
        self.num_raster_and_draws += 1

        raster_timer = Timer()
        raster_timer.start()
        self.raster_chrome()
        self.raster_tab()
        self.time_in_raster += raster_timer.stop()

        draw_timer = Timer()
        draw_timer.start()
        self.draw()
        self.time_in_draw += draw_timer.stop()
        self.needs_raster_and_draw = False
        self.lock.release()

    def schedule_animation_frame(self):
        def callback():
            self.lock.acquire(blocking=True)
            self.display_scheduled = False
            scroll = self.scroll
            active_tab = self.tabs[self.active_tab]
            self.lock.release()
            active_tab.task_runner.schedule_task(
                Task(active_tab.run_animation_frame, scroll))
        self.lock.acquire(blocking=True)
        if not self.display_scheduled:
            if USE_BROWSER_THREAD:
                threading.Timer(REFRESH_RATE_SEC, callback).start()
            self.display_scheduled = True
        self.lock.release()

    def handle_down(self):
        self.lock.acquire(blocking=True)
        if not self.active_tab_height:
            return
        active_tab = self.tabs[self.active_tab]
        scroll = clamp_scroll(
            self.scroll + SCROLL_STEP,
            self.active_tab_height)
        self.scroll = scroll
        self.set_needs_raster_and_draw()
        self.lock.release()

    def set_active_tab(self, index):
        self.active_tab = index
        self.scroll = 0
        self.url = None
        self.set_needs_animation_frame()

    def handle_click(self, e):
        self.lock.acquire(blocking=True)
        if e.y < CHROME_PX:
            self.focus = None
            if 40 <= e.x < 40 + 80 * len(self.tabs) and 0 <= e.y < 40:
                self.set_active_tab(int((e.x - 40) / 80))
            elif 10 <= e.x < 30 and 10 <= e.y < 30:
                self.load("https://browser.engineering/")
            elif 10 <= e.x < 35 and 40 <= e.y < 90:
                active_tab = self.tabs[self.active_tab]
                active_tab.task_runner.schedule_task(
                    Task(active_tab.go_back))
            elif 50 <= e.x < WIDTH - 10 and 40 <= e.y < 90:
                self.focus = "address bar"
                self.address_bar = ""
            self.set_needs_raster_and_draw()
        else:
            self.focus = "content"
            active_tab = self.tabs[self.active_tab]
            active_tab.task_runner.schedule_task(
                Task(active_tab.click, e.x, e.y - CHROME_PX))
        self.lock.release()

    def handle_key(self, char):
        self.lock.acquire(blocking=True)
        if not (0x20 <= ord(char) < 0x7f): return
        if self.focus == "address bar":
            self.address_bar += char
            self.set_needs_raster_and_draw()
        elif self.focus == "content":
            active_tab = self.tabs[self.active_tab]
            active_tab.task_runner.schedule_task(
                Task(active_tab.keypress, char))
        self.lock.release()

    def schedule_load(self, url, body=None):
        active_tab = self.tabs[self.active_tab]
        active_tab.task_runner.schedule_task(
            Task(active_tab.load, url, body))
        self.set_needs_raster_and_draw()

    def handle_enter(self):
        self.lock.acquire(blocking=True)
        if self.focus == "address bar":
            self.schedule_load(self.address_bar)
            self.url = self.address_bar
            self.focus = None
            self.set_needs_raster_and_draw()
        self.lock.release()

    def load(self, url):
        new_tab = Tab(self)
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
        raster(self.active_tab_display_list, canvas)

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
        
        if self.tab_surface:
            tab_rect = skia.Rect.MakeLTRB(0, CHROME_PX, WIDTH, HEIGHT)
            tab_offset = CHROME_PX - self.scroll
            canvas.save()
            canvas.clipRect(tab_rect)
            canvas.translate(0, tab_offset)
            self.tab_surface.draw(canvas, 0, 0)
            canvas.restore()

        chrome_rect = skia.Rect.MakeLTRB(0, 0, WIDTH, CHROME_PX)
        canvas.save()
        canvas.clipRect(chrome_rect)
        self.chrome_surface.draw(canvas, 0, 0)
        canvas.restore()

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
        print("""Time in raster: {:>.6f}s
    ({:>.6f}ms per raster run on average;
    {} total rasters)""".format(
            self.time_in_raster,
            self.time_in_raster / \
                self.num_raster_and_draws * 1000,
            self.num_raster_and_draws))
        print("""Time in draw: {:>.6f}s
    ({:>.6f}ms per draw run on average;
    {} total draw updates)""".format(
            self.time_in_draw,
            self.time_in_draw / self.num_raster_and_draws * 1000,
            self.num_raster_and_draws))

        self.tabs[self.active_tab].task_runner.set_needs_quit()
        sdl2.SDL_DestroyWindow(self.sdl_window)

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Chapter 12 code')
    parser.add_argument("url", type=str, help="URL to load")
    parser.add_argument('--single_threaded', action="store_true", default=False,
        help='Whether to run the browser without a browser thread')
    args = parser.parse_args()

    USE_BROWSER_THREAD = not args.single_threaded

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
            if active_tab.display_scheduled:
                active_tab.display_scheduled = False
                browser.render()
        browser.raster_and_draw()
        if browser.needs_animation_frame:
            browser.schedule_animation_frame()
        browser.needs_animation_frame = False
