import socket
import tkinter
import tkinter.font as tkFont
import collections
import dukpy

def request(domain, path, data={}, method="GET"):
    if ":" in domain:
        domain, port = domain.rsplit(":", 1)
    else:
        port = "80"
    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    s.connect((domain, int(port)))
    if method == "GET" and data:
        path += "?" + urlencode(data)
    s.send((method + " " + path + " HTTP/1.0\r\n").encode("latin1"))
    if method == "POST" and data:
        d = urlencode(data).encode("latin1")
        s.send(("Content-Length: " + str(len(d)) + "\r\n\r\n").encode("latin1"))
        s.send(d)
    else:
        s.send(b"\r\n")
    out = s.makefile("rb").read().decode("ascii")
    return out.split("\r\n", 3)[-1]

def urlencode(d):
    s = ""
    for k, v in d.items():
        if s: s += "&"
        s += k + "=" + v.replace(" ", "+").replace("\n", "%0A")
    return s

class Node(list):
    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = attrs
        self.style = HTML.parse_style(attrs.get("style", "")) if tag else {}
        self.parent = None

        self.x = None
        self.y = None
        self.w = None
        self.h = None
        self.tstyle = None

    def append(self, n):
        super(Node, self).append(n)
        n.parent = self

    def __repr__(self):
        if self.tag is None:
            return repr(self.attrs)
        else:
            return self.tag + " " + repr(self.attrs)

class HTML:
    Tag = collections.namedtuple("Tag", ["tag", "attrs"])

    @staticmethod
    def parse_attrs(tag):
        ts = tag.split(" ", 1)
        if len(ts) == 1:
            return tag, {}
        else:
            parts = ts[1].split("=")
            parts = [parts[0]] + sum([thing.rsplit(" ", 1) for thing in parts[1:-1]], []) + [parts[-1]]
            return ts[0], { a: b.strip("'").strip('"') for a, b in zip(parts[::2], parts[1::2]) }
    
    @staticmethod
    def parse_style(attr):
        return dict([x.strip() for x in y.split(":")] for y in attr.strip(";").split(";")) if ";" in attr or ":" in attr else {}
    
    @staticmethod
    def lex(source):
        source = " ".join(source.split())
        tag = None
        text = None
        for c in source:
            if c == "<":
                if text is not None: yield text
                text = None
                tag = ""
            elif c == ">":
                if tag is not None:
                    head, attrs = HTML.parse_attrs(tag.rstrip("/").strip())
                    yield HTML.Tag(head, attrs)
                    if tag.endswith("/"): yield HTML.Tag("/" + head, None)
                tag = None
            else:
                if tag is not None:
                    tag += c
                elif text is not None:
                    text += c
                else:
                    text = c
        if text is not None: yield text

    def parse(tokens):
        path = [[]]
        style = []
        scripts = []
        for tok in tokens:
            if isinstance(tok, HTML.Tag):
                if tok.tag.startswith("/"):
                    assert not tok.attrs
                    path.pop()
                    assert tok.tag == "/" + path[-1][-1].tag
                    if path[-1][-1].tag == "style":
                        assert len(path[-1][-1]) == 1
                        assert path[-1][-1][0].tag is None
                        style.append(path[-1][-1][0].attrs)
                        path[-1].pop()
                    elif path[-1][-1].tag == "script":
                        assert len(path[-1][-1]) == 1
                        assert path[-1][-1][0].tag is None
                        scripts.append(path[-1][-1][0].attrs)
                        path[-1].pop()
                elif tok.tag == '!DOCTYPE':
                    pass
                else:
                    n = Node(tok.tag, tok.attrs)
                    path[-1].append(n)
                    path.append(n)
            else:
                path[-1].append(Node(None, tok))
        return path[0], style, scripts

class CSS:
    @staticmethod
    def parse(source):
        i = 0
        while True:
            try:
                j = source.index("{", i)
            except ValueError as e:
                break
            
            sel = source[i:j].strip()
            i, j = j + 1, source.index("}", j)
            props = {}

            while i < j:
                try:
                    k = source.index(":", i)
                except ValueError as e:
                    break
                if k > j: break
                prop = source[i:k].strip()
                l = min(source.index(";", k + 1), j)
                val = source[k+1:l].strip()
                props[prop] = val
                if l == j: break
                i = l + 1
            yield sel, props
            i = j + 1
    
    @staticmethod
    def applies(sel, t):
        if t.tag is None:
            return False
        elif sel.startswith("."):
            return sel[1:] in t.attrs.get("class", "").split(" ")
        elif sel.startswith("#"):
            return sel[1:] == t.attrs.get("id", None)
        else:
            return sel == t.tag

    @staticmethod
    def px(val):
        return int(val.rstrip("px"))

def style(rules, t):
    for sel, props in reversed(rules):
        if CSS.applies(sel, t):
            for prop, val in props.items():
                t.style.setdefault(prop, val)
    for subt in t:
        style(rules, subt)

def inherit(t, prop, default):
    if t is None:
        return default
    else:
        return t.style[prop] if prop in t.style else inherit(t.parent, prop, default)

def layout(t, x, y):
    if t.tag is None:
        t.x, t.y, t.tstyle = x, y, t.parent.tstyle

        fs, weight, slant, decoration, color = t.tstyle
        font = tkFont.Font(family="Times", size=fs, weight=weight,
                           slant=slant, underline=(decoration == "underline"))
        for word in t.attrs.split():
            w = font.measure(word)
            if x + w > 800 - 2*8:
                y += fs * 1.75
                x = 8
            x += font.measure(word) + 6
        t.w = x - t.x
        t.h = y - t.y + fs * 1.75
    elif t.tag == "input":
        t.tstyle = (CSS.px(inherit(t, "font-size", "16px")),
                    inherit(t, "font-weight", "normal"),
                    inherit(t, "font-style", "roman"),
                    inherit(t, "text-decoration", "none"),
                    inherit(t, "color", "black"))
        fs, weight, slant, decoration, color = t.tstyle

        if t.attrs.get("type") == "submit":
            font = tkFont.Font(family="Times", size=fs, weight=weight,
                               slant=slant, underline=(decoration == "underline"))
            t.w = font.measure("Submit") + fs * .5 + 4
        else:
            t.w = 100
        t.h = fs * 1.5 + 4
        t.y = y - fs * .25 - 2
        t.x = x
        x += t.w
    else:
        if "font-size" in t.style: fs = CSS.px(t.style["font-size"])
        if "margin-left" in t.style: x += CSS.px(t.style["margin-left"])
        if "margin-top" in t.style: y += CSS.px(t.style["margin-top"])

        if t.tag == "hr": y += int(t.attrs.get("width", "2"))

        t.x = x
        t.y = y
        t.tstyle = (CSS.px(inherit(t, "font-size", "16px")),
                    inherit(t, "font-weight", "normal"),
                    inherit(t, "font-style", "roman"),
                    inherit(t, "text-decoration", "none"),
                    inherit(t, "color", "black"))
            
        x_ = x
        for c in t:
            x_, y = layout(c, x_, y)
        if t.tag in "abi":
            t.w = x_ - x
            x = x_
        else:
            t.w = 800 - x

        if "margin-bottom" in t.style: y += CSS.px(t.style["margin-bottom"])
        if "margin-left" in t.style: x -= CSS.px(t.style["margin-left"])

        if t.tag in ["p", "h1", "h2", "h3", "li"] and len(t):
            y = t[-1].y + t[-1].h

        if t.tag in "abi":
            t.h = t[-1].h
        elif t.tag == "textarea":
            t.w = t.h = 200
            y += 200
        else:
            t.h = y - t.y

    return x, y

def render(canvas, t, scrolly):
    if t.tag is None:
        fs, weight, slant, decoration, color = t.tstyle
        font = tkFont.Font(family="Times", size=fs, weight=weight,
                           slant=slant, underline=(decoration == "underline"))

        x, y = t.x, t.y - scrolly
        for word in t.attrs.split():
            w = font.measure(word)
            if x + w > 800 - 2*8:
                y += 28
                x = 8
            canvas.create_text(x, y, text=word, font=font, anchor=tkinter.NW, fill=color)
            x += font.measure(word) + 6
    else:
        if t.tag == "li":
            x, y, fs, color = t.x - 16, t.y - scrolly, t.tstyle[0], t.tstyle[4]
            canvas.create_oval(x + 2, y + fs / 2 - 3, x + 7, y + fs / 2 + 2, fill=color, outline=color)
        elif t.tag in ["input", "textarea"]:
            canvas.create_rectangle(t.x, t.y - scrolly, t.x + t.w - 2, t.y + t.h - 2 - scrolly, width=2, outline=t.tstyle[4])

            text = t.attrs.get("value", "submit" if t.attrs.get("type") == "submit" else "")
            fs, weight, slant, decoration, color = t.tstyle
            font = tkFont.Font(family="Times", size=fs, weight=weight,
                               slant=slant, underline=(decoration == "underline"))
            canvas.create_text(t.x + fs * .25 + 2, t.y + fs * .25 + 2 - scrolly, text=text, fill=color, anchor=tkinter.NW)
        elif t.tag == 'hr':
            x, y, color = t.x, t.y - scrolly, t.tstyle[4]
            width = int(t.attrs.get("width", "2"))
            canvas.create_line(x, y, 800 - x, y, width=width, fill=color)

        for subt in t:
            render(canvas, subt, scrolly=scrolly)
            

def chrome(canvas, url):
    canvas.create_rectangle(0, 0, 800, 60, fill='white')
    canvas.create_rectangle(10, 10, 35, 50)
    canvas.create_polygon(15, 30, 30, 15, 30, 45, fill='black')
    canvas.create_rectangle(40, 10, 65, 50)
    canvas.create_polygon(60, 30, 45, 15, 45, 45, fill='black')
    canvas.create_rectangle(70, 10, 110, 50)
    canvas.create_polygon(80, 30, 75, 30, 90, 15, 105, 30, 100, 30, 100, 45, 80, 45, 80, 30, fill='black')
    canvas.create_rectangle(115, 10, 795, 50)
    font = tkFont.Font(family="Courier New", size=25)
    canvas.create_text(120, 15, anchor=tkinter.NW, text=url, font=font)

def find_elt(t, x, y):
    for i in t:
        e = find_elt(i, x, y)
        if e is not None: return e
    if t.x <= x <= t.x + t.w and t.y <= y <= t.y + t.h:
        return t

def collect_form_vars(elt, d):
    if elt.tag in {"input", "textarea"} and "name" in elt.attrs:
        d[elt.attrs["name"]] = elt.attrs.get("value", "")
    for sube in elt:
        collect_form_vars(sube, d)
    return d

def query_selector(elt, sel):
    if elt.tag is None: return
    if CSS.applies(sel, elt):
        return elt
    for i in elt:
        s = query_selector(i, sel)
        if s is not None:
            return s

def resolve_relative(url, base):
    if url.startswith("http://"):
        return url
    elif url.startswith("/"):
        return base.split("/", 1)[0] + url
    else:
        return base.rsplit("/", 1)[0] + "/" + url

class Browser:
    def __init__(self, url):
        self.source = None
        self.tree = None
        self.scrolly = 0
        self.home = url
        self.history = [url]
        self.index = 0
        with open("default.css") as f:
            self.default_style = list(CSS.parse(f.read()))
        
        window = tkinter.Tk()
        window.bind("<Down>", self.scroll(100))
        window.bind("<space>", self.scroll(400))
        window.bind("<Up>", self.scroll(-100))
        window.bind("<Button-1>", self.handle_click)
        window.focus_set()
        canvas = tkinter.Canvas(window, width=800, height=1000)
        canvas.pack(side=tkinter.LEFT)
        self.window = window
        self.canvas = canvas

        self.js = dukpy.JSInterpreter()
        self.js.export_function("querySelector", self.js_querySelector)
        self.js.export_function("innerHTML", self.js_innerHTML)
        self.js.export_function("get_attr", self.js_getattr)
        self.js.export_function("log", self.js_log)
        self.js_handles = []

        with open("default.js") as f:
            self.js.evaljs(f.read())

    def fetch(self):
        url = self.history[self.index]
        assert url.startswith("http://")
        url = url[len("http://"):]
        domain, path = url.split("/", 1)
        response = request(domain, "/" + path)
        headers, source = response.split("\r\n\r\n", 1)
        self.source = source

    def js_querySelector(self, sel):
        elt = query_selector(self.tree, sel)
        assert elt is not None, "No element found for selector " + sel
        id = len(self.js_handles)
        self.js_handles.append(elt)
        return id

    def js_getattr(self, handle, attr):
        try:
            elt = self.js_handles[handle]
            return elt.attrs.get(attr, None)
        except:
            import traceback
            traceback.print_exc()
            return

    def js_log(self, s):
        print(s)

    def js_innerHTML(self, handle, html_source):
        try:
            elt = self.js_handles[handle]
            html_tree, styles, scripts = HTML.parse(HTML.lex(html_source))
            for i in elt:
                i.parent = None # Gotta kick them out
            elt[:] = html_tree
            for i in elt:
                i.parent = elt # Gotta make them at home
            for s in styles:
                self.rules.append(list(CSS.parse(s)))
            style(sum(self.rules, []), elt)
            layout(self.tree, x=8, y=8)
        except:
            import traceback
            traceback.print_exc()
            return

    def js_event(self, elt, data):
        if elt is None: return
        if elt in self.js_handles:
            handle = self.js_handles.index(elt)
            self.js.evaljs("_handle_event(dukpy['handle'], dukpy['data'])",
                           handle=handle, data=data)
        self.js_event(elt.parent, data)

    def js_eval(self, s):
        self.js.evaljs(s)

    def parse(self):
        assert self.source
        trees, styles, scripts = HTML.parse(HTML.lex(self.source))
        tree = [t for t in trees if t.tag][0]
        self.rules = [self.default_style]
        for s in styles:
            self.rules.append(list(CSS.parse(s)))
        style(sum(self.rules, []), tree)
        layout(tree, x=8, y=8)
        self.tree = tree
        for s in scripts:
            self.js_eval(s)

    def scroll(self, by):
        def handler(e):
            self.scrolly = max(self.scrolly + by, 0)
            self.render()
        return handler

    def render(self):
        assert self.tree
        self.canvas.delete('all')
        render(self.canvas, self.tree, scrolly=self.scrolly - 60)
        chrome(self.canvas, self.history[self.index])

    def handle_click(self, e):
        if 10 <= e.x <= 35 and 10 <= e.y <= 50:
            self.index -= 1
            self.go()
        elif 40 <= e.x <= 65 and 10 <= e.y <= 50:
            self.index += 1
            self.go()
        elif 70 <= e.x <= 110 and 10 <= e.y <= 50:
            self.index = 0
            self.go()
        elif 115 <= e.x <= 795 and 10 <= e.y <= 50:
            new_url = input("Where to? ")
            self.navigate(new_url)
        else:
            e = find_elt(self.tree, e.x, e.y + self.scrolly - 60)
            self.js_event(e, {"type": "click"})
            while e is not None and e.tag not in {"a", "input", "textarea"}:
                e = e.parent
            if e is None:
                pass
            elif e.tag == "a":
                url = e.attrs["href"]
                self.navigate(url)
            elif e.tag == "input" and e.attrs.get("type") != "submit":
                e.attrs["value"] = input("> ")
                self.js_event(e, {"type": "change"})
            elif e.tag == "textarea":
                s = ""
                while True:
                    l = input("> ")
                    if not l: break
                    s += l + "\n"
                e.attrs["value"] = s
                self.js_event(e, {"type": "change"})
            elif e.tag == "input" and e.attrs.get("type") == "submit":
                while e is not None and e.tag != "form":
                    e = e.parent
                self.js_event(e, {"type": "submit"})
                self.scrolly = 0
                self.submit(e)
                self.parse()
            self.render()

    def submit(self, elt):
        method = elt.attrs.get("method", "GET").upper()
        action = elt.attrs.get("action", self.history[-1])
        attrs = collect_form_vars(elt, {})

        url = resolve_relative(action, self.history[self.index])
        assert url.startswith("http://")
        url = url[len("http://"):]
        self.history[self.index+1:] = [url]
        self.index += 1
        domain, path = url.split("/", 1)
        response = request(domain, "/" + path, method=method, data=attrs)
        headers, source = response.split("\r\n\r\n", 1)
        self.source = source

    def navigate(self, url):
        self.history[self.index+1:] = [url]
        self.index += 1
        self.go()

    def go(self):
        self.scrolly = 0
        self.fetch()
        self.parse()
        self.render()

    def mainloop(self):
        self.window.mainloop()

if __name__ == "__main__":
    import sys
    b = Browser(sys.argv[1])
    b.go()
    b.mainloop()
