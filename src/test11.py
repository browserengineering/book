"""
This file contains unittests helpers for chapters 11 and onward
"""

import builtins
import io
import sdl2
import skia
import sys
import unittest
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
            assert any(name.lower() == "content-length" for name, value in headers)
            assert all(int(value) == len(self.body) for name, value in headers
                       if name.lower() == "content-length")

    def makefile(self, mode, encoding=None, newline=None):
        assert self.connected and self.host and self.port
        if self.port == 80 and self.scheme == "http":
            url = self.scheme + "://" + self.host + self.path
        elif self.port == 443 and self.scheme == "https":
            url = self.scheme + "://" + self.host + self.path
        else:
            url = self.scheme + "://" + self.host + ":" + str(self.port) + self.path
        self.Requests.setdefault(url, []).append(self.request)
        assert self.method == self.URLs[url][0], f"Made a {self.method} request to a {self.URLs[url][0]} URL"
        output = self.URLs[url][1]
        if self.URLs[url][2]:
            assert self.body == self.URLs[url][2], (self.body, self.URLs[url][2])
        if encoding:
            return io.StringIO(output.decode(encoding).replace(newline, "\n"), newline)
        else:
            assert mode == "b"
            return io.BytesIO(output)

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

class MockCanvas:
    def __init__(self):
        self.commands = []

    def clear(self, color):
        self.commands.append("clear(color={:x})".format(color))

    def format_paint(paint):
        format_str = ", color={color:x}"
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

    def drawString(self, text, x, y, font, paint):
        format_str = "drawString(text={text}, x={x}, y={y}" \
            + MockCanvas.format_paint(paint)
        self.commands.append((format_str + ")").format(
            text=text, x=x, y=y,
            color=paint.getColor(),
            alpha=paint.getAlpha(), blend_mode=paint.getBlendMode()))

class MockSkiaSurface:
    def __init__(self, width, height):
        self.canvas = MockCanvas()
        pass

    def __enter__(self):
        return self.canvas

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def makeImageSnapshot(self):
        return MockSkiaImage();

    def printTabCommands(self):
        count = 0
        total = len(self.canvas.commands)
        for command in self.canvas.commands:
            if count == total - 12:
                break
            if count > 0:
                print(command)
            count = count + 1

skia.Surface = MockSkiaSurface