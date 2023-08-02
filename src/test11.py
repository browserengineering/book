"""
This file contains unittests helpers for chapters 11 and onward
"""

import builtins
import io
import sdl2
import skia
import sys
import unittest
import threading
from unittest import mock
from test import socket, ssl

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

    def saveLayer(self, paint):
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
