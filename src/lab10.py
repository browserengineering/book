"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 10 (Keeping Data Private),
without exercises.
"""

import socket
import ssl
import tkinter
import tkinter.font
import urllib.parse
import dukpy
from lab2 import WIDTH, HEIGHT, HSTEP, VSTEP, SCROLL_STEP
from lab3 import FONTS, get_font
from lab4 import Text, Element, print_tree, HTMLParser
from lab5 import BLOCK_ELEMENTS, DrawRect
from lab6 import CSSParser, TagSelector, DescendantSelector
from lab6 import INHERITED_PROPERTIES, style, cascade_priority, compute_style
from lab6 import DrawText, resolve_url, tree_to_list
from lab7 import LineLayout, TextLayout, CHROME_PX
from lab8 import DocumentLayout, BlockLayout, InputLayout, INPUT_WIDTH_PX, layout_mode
from lab9 import EVENT_DISPATCH_CODE

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
        with open("runtime10.js") as f:
            self.interp.evaljs(f.read())

        self.node_to_handle = {}
        self.handle_to_node = {}

    def run(self, code):
        self.interp.evaljs(code)

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
        doc = HTMLParser("<html><body>" + s + "</body></html>").parse()
        new_nodes = doc.children[0].children
        elt = self.handle_to_node[handle]
        elt.children = new_nodes
        for child in elt.children:
            child.parent = elt
        self.tab.render()

    def XMLHttpRequest_send(self, method, url, body):
        full_url = resolve_url(url, self.tab.url)
        if not self.tab.allowed_request(full_url):
            raise Exception("Cross-origin XHR blocked by CSP")
        headers, out = request(full_url, self.tab.url, body)
        if url_origin(full_url) != url_origin(self.tab.url):
            raise Exception("Cross-origin XHR request not allowed")
        return out

class Tab:
    def __init__(self):
        self.history = []
        self.focus = None
        self.url = None

        with open("browser8.css") as f:
            self.default_style_sheet = CSSParser(f.read()).parse()

    def allowed_request(self, url):
        return self.allowed_origins == None or \
            url_origin(url) in self.allowed_origins

    def load(self, url, body=None):
        headers, body = request(url, self.url, body)
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
        style(self.nodes, sorted(self.rules, key=cascade_priority))
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        self.document.paint(self.display_list)

    def draw(self, canvas):
        for cmd in self.display_list:
            if cmd.top > self.scroll + HEIGHT - CHROME_PX: continue
            if cmd.bottom < self.scroll: continue
            cmd.execute(self.scroll - CHROME_PX, canvas)

        if self.focus:
            obj = [obj for obj in tree_to_list(self.document, [])
               if obj.node == self.focus and \
                    isinstance(obj, InputLayout)][0]
            text = self.focus.attributes.get("value", "")
            x = obj.x + obj.font.measure(text)
            y = obj.y - self.scroll + CHROME_PX
            canvas.create_line(x, y, x, y + obj.height)

    def scrolldown(self):
        max_y = self.document.height - (HEIGHT - CHROME_PX)
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
            self.render()

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT,
            bg="white",
        )
        self.canvas.pack()

        self.window.bind("<Down>", self.handle_down)
        self.window.bind("<Button-1>", self.handle_click)
        self.window.bind("<Key>", self.handle_key)
        self.window.bind("<Return>", self.handle_enter)

        self.tabs = []
        self.active_tab = None
        self.focus = None
        self.address_bar = ""

    def handle_down(self, e):
        self.tabs[self.active_tab].scrolldown()
        self.draw()

    def handle_click(self, e):
        if e.y < CHROME_PX:
            self.focus = None
            if 40 <= e.x < 40 + 80 * len(self.tabs) and 0 <= e.y < 40:
                self.active_tab = int((e.x - 40) / 80)
            elif 10 <= e.x < 30 and 10 <= e.y < 30:
                self.load("https://browser.engineering/")
            elif 10 <= e.x < 35 and 50 <= e.y < 90:
                self.tabs[self.active_tab].go_back()
            elif 50 <= e.x < WIDTH - 10 and 50 <= e.y < 90:
                self.focus = "address bar"
                self.address_bar = ""
        else:
            self.focus = "content"
            self.tabs[self.active_tab].click(e.x, e.y - CHROME_PX)
        self.draw()

    def handle_key(self, e):
        if len(e.char) == 0: return
        if not (0x20 <= ord(e.char) < 0x7f): return
        if self.focus == "address bar":
            self.address_bar += e.char
            self.draw()
        elif self.focus == "content":
            self.tabs[self.active_tab].keypress(e.char)
            self.draw()

    def handle_enter(self, e):
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
        self.canvas.delete("all")
        self.tabs[self.active_tab].draw(self.canvas)
        self.canvas.create_rectangle(0, 0, WIDTH, CHROME_PX,
            fill="white", outline="black")

        tabfont = get_font(20, "normal", "roman")
        for i, tab in enumerate(self.tabs):
            name = "Tab {}".format(i)
            x1, x2 = 40 + 80 * i, 120 + 80 * i
            self.canvas.create_line(x1, 0, x1, 40, fill="black")
            self.canvas.create_line(x2, 0, x2, 40, fill="black")
            self.canvas.create_text(x1 + 10, 10, anchor="nw", text=name,
                font=tabfont, fill="black")
            if i == self.active_tab:
                self.canvas.create_line(0, 40, x1, 40, fill="black")
                self.canvas.create_line(x2, 40, WIDTH, 40, fill="black")

        buttonfont = get_font(30, "normal", "roman")
        self.canvas.create_rectangle(10, 10, 30, 30,
            outline="black", width=1)
        self.canvas.create_text(11, 0, anchor="nw", text="+",
            font=buttonfont, fill="black")

        self.canvas.create_rectangle(40, 50, WIDTH - 10, 90,
            outline="black", width=1)
        if self.focus == "address bar":
            self.canvas.create_text(
                55, 55, anchor='nw', text=self.address_bar,
                font=buttonfont, fill="black")
            w = buttonfont.measure(self.address_bar)
            self.canvas.create_line(55 + w, 55, 55 + w, 85, fill="black")
        else:
            url = self.tabs[self.active_tab].url
            self.canvas.create_text(55, 55, anchor='nw', text=url,
                font=buttonfont, fill="black")

        self.canvas.create_rectangle(10, 50, 35, 90,
            outline="black", width=1)
        self.canvas.create_polygon(
            15, 70, 30, 55, 30, 85, fill='black')

if __name__ == "__main__":
    import sys
    Browser().load(sys.argv[1])
    tkinter.mainloop()
