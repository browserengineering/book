"""
This file contains unittests helpers for chapters 1-10
"""

import wbetools
import builtins
import io
import sys
import tkinter
import tkinter.font
import unittest
import sdl2
import skia
import threading
from unittest import mock

class socket:
    URLs = {}
    Requests = {}

    def __init__(self, *args, **kwargs):
        self.request = b""
        self.connected = False

    def connect(self, host_port):
        self.scheme = "http"
        self.host, self.port = host_port
        self.connected = True

    def send(self, text):
        self.request += text
        self.method, self.path, _ = self.request.decode("latin1").split(" ", 2)
        
        if self.method == "POST":
            beginning, self.body = self.request.decode("latin1").split("\r\n\r\n")
            headers = [item.split(": ") for item in beginning.split("\r\n")[1:]]
            assert any(name.casefold() == "content-length" for name, value in headers)
            assert all(int(value) == len(self.body) for name, value in headers
                       if name.casefold() == "content-length")

    def makefile(self, mode, encoding=None, newline=None):
        assert self.connected and self.host and self.port
        if self.port == 80 and self.scheme == "http":
            url = self.scheme + "://" + self.host + self.path
        elif self.port == 443 and self.scheme == "https":
            url = self.scheme + "://" + self.host + self.path
        else:
            url = self.scheme + "://" + self.host + ":" + str(self.port) + self.path
        self.Requests.setdefault(url, []).append(self.request)
        assert url in self.URLs, f"Unknown URL {url}, only know {', '.join(self.URLs.keys())}"
        assert self.method == self.URLs[url][0], f"Made a {self.method} request to {url}, should be {self.URLs[url][0]}"
        output = self.URLs[url][1]
        if self.URLs[url][2]:
            assert self.body == self.URLs[url][2], f"Request to {url} should have body {self.URLs[url][2]!r} but instead has body {self.body!r}"
        stream = io.BytesIO(output)
        if encoding:
            stream = io.TextIOWrapper(stream, encoding=encoding, newline=newline)
            stream.mode = mode
        else:
            assert mode == "b", "If no file encoding is passed, must pass 'b' mode"

        return stream

    def close(self):
        self.connected = False

    @classmethod
    def patch(cls):
        return mock.patch("socket.socket", wraps=cls)

    @classmethod
    def respond(cls, url, response, method="GET", body=None):
        cls.URLs[url] = [method, response, body]

    @classmethod
    def respond_ok(cls, url, response, method="GET", body=None):
        response = ("HTTP/1.0 200 OK\r\n\r\n" + response).encode("utf8")
        cls.URLs[url] = [method, response, body]

    @classmethod
    def serve(cls, html, headers={}):
        html = html.encode("utf8") if isinstance(html, str) else html
        response  = b"HTTP/1.0 200 OK\r\n"
        response += b"Content-Type: text/html\r\n"
        response += b"Content-Length: " + str(len(html)).encode("ascii") + b"\r\n"
        for header, value in headers.items():
            header_pretty = "-".join([name.title() for name in header.split("-")])
            response += header_pretty.encode("ascii") + b": " + value.encode("ascii") + b"\r\n"
        response += b"\r\n" + html
        prefix = "http://test/page"
        url = next(prefix + str(i) for i in range(1000) if prefix + str(i) not in cls.URLs)
        cls.respond(url, response)
        return url

    @classmethod
    def made_request(cls, url):
        return url in cls.Requests

    @classmethod
    def last_request(cls, url):
        return cls.Requests[url][-1]

    @classmethod
    def clear_history(cls):
        cls.Requests = {}

class ssl:
    def wrap_socket(self, s, server_hostname):
        assert s.host == server_hostname
        s.scheme = "https"
        return s

    @classmethod
    def patch(cls):
        return mock.patch("ssl.create_default_context", wraps=cls)

class SilentTk:
    def bind(self, event, callback):
        pass

tkinter.Tk = SilentTk

class SilentCanvas:
    def __init__(self, *args, **kwargs):
        self._parameters = kwargs

    def winfo_reqwidth(self):
        return self._parameters["width"]

    def winfo_reqheight(self):
        return self._parameters["height"]

    def create_text(self, x, y, text, **kwargs):
        pass

    def create_rectangle(self, x1, y1, x2, y2, **kwargs):
        pass

    def create_line(self, x1, y1, x2, y2, **kwargs):
        pass

    def create_line(self, x1, y1, x2, y2, **kwargs):
        pass

    def create_polygon(self, *args, **kwargs):
        pass

    def pack(self):
        pass

    def delete(self, v):
        pass

tkinter.Canvas = SilentCanvas

class TkCanvas:
    def __init__(self, *args, **kwargs):
        self._parameters = kwargs

    def winfo_reqwidth(self):
        return self._parameters["width"]

    def winfo_reqheight(self):
        return self._parameters["height"]

    def create_text(self, x, y, text, font=None, anchor=None, **kwargs):
        if font or anchor:
            print("create_text: x={} y={} text={} font={} anchor={}".format(
                x, y, text, font, anchor))
        else:
            print("create_text: x={} y={} text={}".format(
                x, y, text))

    def pack(self):
        pass

    def delete(self, v):
        pass

original_tkinter_canvas = tkinter.Canvas

def patch_canvas():
    tkinter.Canvas = TkCanvas

def unpatch_canvas():
    tkinter.Canvas = original_tkinter_canvas

class TkFont:
    def __init__(self, size=12, weight='normal', slant='roman', style=None):
        self.size = size
        self.weight = weight
        self.slant = slant
        self.style = style

    def measure(self, word):
        return self.size * len(word)

    def metrics(self, name=None):
        all = {"ascent" : self.size * 0.75, "descent": self.size * 0.25,
            "linespace": self.size}
        if name:
            return all[name]
        return all

    def __repr__(self):
        return "Font size={} weight={} slant={} style={}".format(
            self.size, self.weight, self.slant, self.style)

tkinter.font.Font = TkFont

class TkLabel:
    def __init__(self, font):
        pass

tkinter.Label = TkLabel

def breakpoint(name, *args):
    args_str = (", " + ", ".join(["'{}'".format(arg) for arg in args]) if args else "")
    print("breakpoint(name='{}'{})".format(name, args_str))

def patch(cls):
        return mock.patch("socket.socket", wraps=cls)

builtin_breakpoint = wbetools.record

def patch_breakpoint():
    wbetools.record = breakpoint

def unpatch_breakpoint():
    wbetools.record = builtin_breakpoint

class Event:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class gtts:
    class gTTS:
        def __init__(self, text):
            pass
        def save(self, file):
            pass

    @classmethod
    def patch(cls):
        import sys
        sys.modules["gtts"] = cls()



def SDL_GetWindowSurfacePatched(window):
    return None

sdl2.SDL_GetWindowSurface = SDL_GetWindowSurfacePatched

def SDL_BlitSurfacePatched(surface, rect, window_surface, rect2):
    return None

sdl2.SDL_BlitSurface = SDL_BlitSurfacePatched


def SDL_UpdateWindowSurfacePatched(window):
    return None

sdl2.SDL_UpdateWindowSurface = SDL_UpdateWindowSurfacePatched

class MockSkiaImage:
    def __init__(self):
        pass

    def tobytes(self):
        return ""

class MockFont:
    def __init__(self, typeface, size):
        self.size = size
        self.typeface = typeface

    def measureText(self, word):
        return self.size * len(word)

    def getMetrics(self, name=None):
        m = skia.FontMetrics()
        m.fAscent = -self.size * .75
        m.fDescent = self.size * .25
        return m

    def __repr__(self):
        return "Font size={} weight={} slant={} style={}".format(
            self.size, self.weight, self.slant, self.style)

class MockCanvas:
    def __init__(self):
        self.commands = []

    def clear(self, color):
        self.commands.append("clear(color={:x})".format(color))

    def format_paint(paint, include_leading_comma=True):
        format_str = ""
        if include_leading_comma:
            format_str = ", "
        format_str = format_str + "color={color:x}"
        if paint.getAlpha() != 255:
            format_str = format_str + ", alpha={alpha}"
        if paint.getBlendMode() != skia.BlendMode.kSrcOver:
            format_str = format_str + ", blend_mode={blend_mode}"
        return format_str

    def drawRect(self, rect, paint):
        format_str = "drawRect(rect={rect}" + MockCanvas.format_paint(paint)
        self.commands.append(
            (format_str + ")").format(
            rect=rect, color=paint.getColor(),
            alpha=paint.getAlpha(), blend_mode=paint.getBlendMode()))

    def drawPath(self, path, paint):
        format_str = "drawPath(<path>" + MockCanvas.format_paint(paint)
        self.commands.append(
            (format_str + ")").format(
            color=paint.getColor(),
            alpha=paint.getAlpha(), blend_mode=paint.getBlendMode()))

    def drawCircle(self, cx, cy, radius, paint):
        format_str = "drawCircle(cx={cx}, cy={cy}, radius={radius}" \
            + MockCanvas.format_paint(paint)
        self.commands.append(
            (format_str + ")").format(
                cx=cx, cy=cy, radius=radius,
                color=paint.getColor(),
                alpha=paint.getAlpha(), blend_mode=paint.getBlendMode()))

    def drawString(self, text, x, y, font, paint):
        format_str = "drawString(text={text}, x={x}, y={y}" \
            + MockCanvas.format_paint(paint)
        self.commands.append((format_str + ")").format(
            text=text, x=x, y=y,
            color=paint.getColor(),
            alpha=paint.getAlpha(), blend_mode=paint.getBlendMode()))

    def save(self):
        self.commands.append("save()")

    def saveLayer(self, ignored, paint):
        format_str = "saveLayer(" + MockCanvas.format_paint(paint, False)
        self.commands.append((format_str + ")").format(
            color=paint.getColor(),
            alpha=paint.getAlpha(), blend_mode=paint.getBlendMode()))

    def clipRect(self, rect):
        self.commands.append("clipRect(rect={rect})".format(rect=rect))

    def clipRRect(self, rrect):
        self.commands.append(
            "clipRRect(bounds={bounds}, radius={radius})".format(
                bounds=rrect.getBounds(), radius=rrect.getSimpleRadii()))

    def drawRRect(self, rrect, paint):
       format_str = "drawRRect(bounds={bounds}, radius={radius}, " + \
           MockCanvas.format_paint(paint, False)
       self.commands.append(
           (format_str + ")").format(
           bounds=rrect.getBounds(), radius=rrect.getSimpleRadii(),
           color=paint.getColor(),
          alpha=paint.getAlpha(), blend_mode=paint.getBlendMode()))


    def drawImage(self, image, left, top):
        self.commands.append("drawImage(<image>, left={left}, top={top}".format(
            left=left, top=top))

    def drawImageRect(self, image, src, dst):
        self.commands.append(
            "drawImageRect(<image>, src={src}, dst={dst}".format(
                src=src, dst=dst))

    def restore(self):
        self.commands.append("restore()")

    def translate(self, x, y):
        self.commands.append("translate(x={x}, y={y})".format(
            x=x, y=y))

    def rotate(self, degrees):
        self.commands.append("rotate(degrees={degrees})".format(
            degrees=degrees))

class MockSkiaSurface:
    def __init__(self, width, height):
        self.canvas = MockCanvas()
        pass

    @classmethod
    def MakeRaster(cls, info):
        return cls(info.width, info.height)

    def getCanvas(self):
        return self.canvas

    def makeImageSnapshot(self):
        return MockSkiaImage()

    def printTabCommands(self):
        count = 0
        total = len(self.canvas.commands)
        for command in self.canvas.commands:
            print(command)
            count = count + 1

    def draw(self, canvas, x, y):
        pass

skia.Surface = MockSkiaSurface
skia.Font = MockFont

class MockTimer:
	def __init__(self, sec, callback):
		self.sec = sec
		self.callback = callback

	def start(self):
		self.callback()

	def cancel(self):
		self.callback = None

threading.Timer = MockTimer

class MockTaskRunner:
	def __init__(self, tab):
		self.tab = tab

	def schedule_task(self, callback):
		callback()

	def clear_pending_tasks(self):
		pass

	def start(self):
		pass

	def run(self):
		pass

class MockNoOpTaskRunner:
	def __init__(self, tab):
		self.tab = tab

	def schedule_task(self, callback):
		pass

	def start(self):
		pass

	def run(self):
		pass

class MockLock:
	def acquire(self, blocking): pass
	def release(self): pass

	@classmethod
	def patch(cls):
		return mock.patch("threading.Lock", wraps=cls)


def print_display_list_skip_noops(display_list):
		for item in display_list:
				print_tree_skip_nooops(item)

def print_tree_skip_nooops(node, indent=0):
    if node.__repr__().find("no-op") >= 0:
        extra = 0
    else:
        print(" " * indent, node)
        extra = 2
    for child in node.children:
        print_tree_skip_nooops(child, indent + extra)
