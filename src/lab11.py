"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 11 (Adding Visual Effects),
without exercises.
"""

import ctypes
import dukpy
import math
import sdl2
import skia
import socket
import ssl
import urllib.parse
from lab2 import WIDTH, HEIGHT, HSTEP, VSTEP, SCROLL_STEP
from lab4 import print_tree, HTMLParser
from lab5 import BLOCK_ELEMENTS, DrawRect, DocumentLayout
from lab6 import CSSParser, TagSelector, DescendantSelector
from lab6 import INHERITED_PROPERTIES, style, cascade_priority
from lab6 import DrawText, tree_to_list
from lab7 import DrawLine, DrawOutline, LineLayout, TextLayout, intersects
from lab7 import Chrome
from lab8 import Text, Element, BlockLayout, InputLayout, INPUT_WIDTH_PX
from lab8 import Browser
from lab9 import EVENT_DISPATCH_CODE
from lab10 import COOKIE_JAR, URL, JSContext, Tab
import wbetools

FONTS = {}

def get_font(size, weight, style):
    key = (weight, style)
    if key not in FONTS:
        if weight == "bold":
            skia_weight = skia.FontStyle.kBold_Weight
        else:
            skia_weight = skia.FontStyle.kNormal_Weight
        if style == "italic":
            skia_style = skia.FontStyle.kItalic_Slant
        else:
            skia_style = skia.FontStyle.kUpright_Slant
        skia_width = skia.FontStyle.kNormal_Width
        style_info = \
            skia.FontStyle(skia_weight, skia_width, skia_style)
        font = skia.Typeface('Arial', style_info)
        FONTS[key] = font
    return skia.Font(FONTS[key], size)

def parse_color(color):
    if color == "white":
        return skia.ColorWHITE
    elif color == "lightblue":
        return skia.ColorSetARGB(0xFF, 0xAD, 0xD8, 0xE6)
    elif color == "orange":
        return skia.ColorSetARGB(0xFF, 0xFF, 0xA5, 0x00)
    elif color == "red":
        return skia.ColorRED
    elif color == "green":
        return skia.ColorGREEN
    elif color == "blue":
        return skia.ColorBLUE
    elif color == "gray":
        return skia.ColorGRAY
    elif color == "lightgreen":
        return skia.ColorSetARGB(0xFF, 0x90, 0xEE, 0x90)
    else:
        return skia.ColorBLACK

def parse_blend_mode(blend_mode_str):
    if blend_mode_str == "multiply":
        return skia.BlendMode.kMultiply
    elif blend_mode_str == "difference":
        return skia.BlendMode.kDifference
    else:
        return skia.BlendMode.kSrcOver

def linespace(font):
    metrics = font.getMetrics()
    return metrics.fDescent - metrics.fAscent

class SaveLayer:
    def __init__(self, sk_paint, children,
            should_save=True, should_paint_cmds=True):
        self.should_save = should_save
        self.should_paint_cmds = should_paint_cmds
        self.sk_paint = sk_paint
        self.children = children
        self.rect = skia.Rect.MakeEmpty()
        for cmd in self.children:
            self.rect.join(cmd.rect)

    def execute(self, canvas):
        if self.should_save:
            canvas.saveLayer(paint=self.sk_paint)
        if self.should_paint_cmds:
            for cmd in self.children:
                cmd.execute(canvas)
        if self.should_save:
            canvas.restore()

@wbetools.patch(DrawRect)
class DrawRect:
    def __init__(self, x1, y1, x2, y2, color):
        self.rect = skia.Rect.MakeLTRB(x1, y1, x2, y2)
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color

    def execute(self, canvas):
        paint = skia.Paint()
        paint.setColor(parse_color(self.color))
        canvas.drawRect(self.rect, paint)

@wbetools.patch(DrawText)
class DrawText:
    def __init__(self, x1, y1, text, font, color):
        self.left = x1
        self.top = y1
        self.right = x1 + font.measureText(text)
        self.bottom = y1 - font.getMetrics().fAscent + font.getMetrics().fDescent
        self.rect = \
            skia.Rect.MakeLTRB(x1, y1, self.right, self.bottom)
        self.font = font
        self.text = text
        self.color = color

    def execute(self, canvas):
        paint = skia.Paint(
            AntiAlias=True, Color=parse_color(self.color))
        baseline = self.top - self.font.getMetrics().fAscent
        canvas.drawString(self.text, float(self.left), baseline,
            self.font, paint)

@wbetools.patch(DrawOutline)
class DrawOutline:
    def __init__(self, x1, y1, x2, y2, color, thickness):
        self.rect = skia.Rect.MakeLTRB(x1, y1, x2, y2)
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color
        self.thickness = thickness

    def execute(self, canvas):
        paint = skia.Paint()
        paint.setStyle(skia.Paint.kStroke_Style)
        paint.setStrokeWidth(self.thickness)
        paint.setColor(parse_color(self.color))
        canvas.drawRect(self.rect, paint)

@wbetools.patch(DrawLine)
class DrawLine:
    def __init__(self, x1, y1, x2, y2, color, thickness):
        self.rect = skia.Rect.MakeLTRB(x1, y1, x2, y2)
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.color = color
        self.thickness = thickness

    def execute(self, canvas):
        path = skia.Path().moveTo(self.x1, self.y1) \
                          .lineTo(self.x2, self.y2)
        paint = skia.Paint(Color=parse_color(self.color))
        paint.setStyle(skia.Paint.kStroke_Style)
        paint.setStrokeWidth(self.thickness)
        canvas.drawPath(path, paint)

class DrawRRect:
    def __init__(self, rect, radius, color):
        self.rect = rect
        self.rrect = skia.RRect.MakeRectXY(rect, radius, radius)
        self.color = color

    def execute(self, canvas):
        sk_color = parse_color(self.color)
        canvas.drawRRect(self.rrect,
            paint=skia.Paint(Color=sk_color))

class ClipRRect:
    def __init__(self, rect, radius, children, should_clip=True):
        self.rect = rect
        self.rrect = skia.RRect.MakeRectXY(rect, radius, radius)
        self.children = children
        self.should_clip = should_clip

    def execute(self, canvas):
        if self.should_clip:
            canvas.save()
            canvas.clipRRect(self.rrect)

        for cmd in self.children:
            cmd.execute(canvas)

        if self.should_clip:
            canvas.restore()

def paint_tree(layout_object, display_list):
    cmds = layout_object.paint(display_list)
    for child in layout_object.children:
        paint_tree(child, cmds)

#    cmds = layout_object.paint_effects(cmds)

    display_list.extend(cmds)

@wbetools.patch(BlockLayout)
class BlockLayout:
    def word(self, node, word):
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        size = float(node.style["font-size"][:-2])
        font = get_font(size, weight, style)
        w = font.measureText(word)
        if self.cursor_x + w > self.width:
            self.new_line()
        line = self.children[-1]
        text = TextLayout(node, word, line, self.previous_word)
        line.children.append(text)
        self.previous_word = text
        self.cursor_x += w + font.measureText(" ")

    def input(self, node):
        w = INPUT_WIDTH_PX
        if self.cursor_x + w > self.width:
            self.new_line()
        line = self.children[-1]
        input = InputLayout(node, line, self.previous_word)
        line.children.append(input)
        self.previous_word = input
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        size = float(node.style["font-size"][:-2])
        font = get_font(size, weight, style)
        self.cursor_x += w + font.measureText(" ")

    def paint(self, display_list):
        cmds = []

        rect = skia.Rect.MakeLTRB(
            self.x, self.y,
            self.x + self.width, self.y + self.height)

        bgcolor = self.node.style.get("background-color",
                                 "transparent")
        
        is_atomic = not isinstance(self.node, Text) and \
            (self.node.tag == "input" or self.node.tag == "button")

        if not is_atomic:
            if bgcolor != "transparent":
                radius = float(
                    self.node.style.get("border-radius", "0px")[:-2])
                cmds.append(DrawRRect(rect, radius, bgcolor))

        return cmds

    def paint_effects(self, cmds):
        is_atomic = not isinstance(self.node, Text) and \
            (self.node.tag == "input" or self.node.tag == "button")

        if not is_atomic:
            rect = skia.Rect.MakeLTRB(
                self.x, self.y,
                self.x + self.width, self.y + self.height)
            cmds = paint_visual_effects(self.node, cmds, rect)
        return cmds

@wbetools.patch(LineLayout)
class LineLayout:
    def layout(self):
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
            return

        max_ascent = max([-word.font.getMetrics().fAscent 
                          for word in self.children])
        baseline = self.y + 1.25 * max_ascent
        for word in self.children:
            word.y = baseline + word.font.getMetrics().fAscent
        max_descent = max([word.font.getMetrics().fDescent
                           for word in self.children])
        self.height = 1.25 * (max_ascent + max_descent)

    def paint(self, display_list):
        return display_list
    
    def paint_effects(self, display_list):
        return display_list

@wbetools.patch(TextLayout)
class TextLayout:
    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        size = float(self.node.style["font-size"][:-2])
        self.font = get_font(size, weight, style)

        # Do not set self.y!!!
        self.width = self.font.measureText(self.word)

        if self.previous:
            space = self.previous.font.measureText(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.height = linespace(self.font)

    def paint(self, display_list):
        cmds = []
        color = self.node.style["color"]
        cmds.append(
            DrawText(self.x, self.y, self.word, self.font, color))
        return cmds

    def paint_effects(self, cmds):
        return cmds

@wbetools.patch(InputLayout)
class InputLayout:
    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        size = float(self.node.style["font-size"][:-2])
        self.font = get_font(size, weight, style)

        self.width = INPUT_WIDTH_PX
        self.height = linespace(self.font)

        if self.previous:
            space = self.previous.font.measureText(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

    def paint(self, display_list):
        cmds = []

        rect = skia.Rect.MakeLTRB(
            self.x, self.y, self.x + self.width,
            self.y + self.height)

        bgcolor = self.node.style.get("background-color",
                                 "transparent")
        if bgcolor != "transparent":
            radius = float(self.node.style.get("border-radius", "0px")[:-2])
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

        if self.node.is_focused:
            cx = self.x + self.font.measureText(text)
            cmds.append(DrawLine(
                cx, self.y, cx, self.y + self.height, "black", 1))

        return cmds

    def paint_effects(self, cmds):
        rect = skia.Rect.MakeLTRB(
            self.x, self.y, self.x + self.width,
            self.y + self.height)

        return paint_visual_effects(self.node, cmds, rect)

def paint_visual_effects(node, cmds, rect):
    opacity = float(node.style.get("opacity", "1.0"))

    blend_mode = parse_blend_mode(node.style.get("mix-blend-mode"))

    border_radius = float(node.style.get("border-radius", "0px")[:-2])
    if node.style.get("overflow", "visible") == "clip":
        clip_radius = border_radius
    else:
        clip_radius = 0

    needs_clip = node.style.get("overflow", "visible") == "clip"
    needs_blend_isolation = blend_mode != skia.BlendMode.kSrcOver or \
        needs_clip or opacity != 1.0

    return [
        SaveLayer(skia.Paint(BlendMode=blend_mode, Alphaf=opacity), [
            ClipRRect(rect, clip_radius,
                cmds,
            should_clip=needs_clip),
        ], should_save=needs_blend_isolation),
    ]

@wbetools.patch(DocumentLayout)
class DocumentLayout:
    def paint(self, display_list):
        return display_list

    def paint_effects(self, display_list):
        return display_list

@wbetools.patch(Tab)
class Tab:
    def render(self):
        style(self.nodes, sorted(self.rules, key=cascade_priority))
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        paint_tree(self.document, self.display_list)

    def raster(self, canvas):
        for cmd in self.display_list:
            cmd.execute(canvas)

@wbetools.patch(Chrome)
class Chrome:
    def __init__(self, browser):
        self.browser = browser
        self.font = get_font(20, "normal", "roman")
        font_height = linespace(self.font)

        self.padding = 5
        self.tab_header_bottom = font_height + 2 * self.padding
        self.addressbar_top = self.tab_header_bottom + self.padding
        self.bottom = \
            math.ceil(
                self.addressbar_top + font_height + 2 * self.padding)

    def plus_bounds(self):
        plus_width = self.font.measureText("+")
        return (self.padding, self.padding,
            plus_width + self.padding, self.tab_header_bottom - self.padding)

    def tab_bounds(self, i):
        tab_start_x = self.font.measureText("+") + \
            self.padding + self.padding

        tab_width = self.font.measureText("Tab 1") + 2 * self.padding

        return (tab_start_x + tab_width * i, self.padding,
            tab_start_x + tab_width + tab_width * i, self.tab_header_bottom)

    def backbutton_bounds(self):
        backbutton_width = self.font.measureText("<")
        return (self.padding, self.addressbar_top,
            self.padding + backbutton_width, self.bottom - self.padding)

    def paint(self):
        cmds = []
        cmds.append(DrawRect(0, 0, WIDTH, self.bottom, "white"))

        (plus_left, plus_top, plus_right, plus_bottom) = self.plus_bounds()
        cmds.append(DrawOutline(
            plus_left, plus_top, plus_right, plus_bottom, "black", 1))
        cmds.append(DrawText(
            plus_left, plus_top, "+", self.font, "black"))

        for i, tab in enumerate(self.browser.tabs):
            name = "Tab {}".format(i)
            (tab_left, tab_top, tab_right, tab_bottom) = self.tab_bounds(i)

            cmds.append(DrawLine(
                tab_left, 0,tab_left, tab_bottom, "black", 1))
            cmds.append(DrawLine(
                tab_right, 0, tab_right, tab_bottom, "black", 1))
            cmds.append(DrawText(
                tab_left + self.padding, tab_top,
                name, self.font, "black"))
            if i == self.browser.active_tab:
                cmds.append(DrawLine(
                    0, tab_bottom, tab_left, tab_bottom, "black", 1))
                cmds.append(DrawLine(
                    tab_right, tab_bottom, WIDTH, tab_bottom, "black", 1))

        backbutton_width = self.font.measureText("<")
        (backbutton_left, backbutton_top, backbutton_right, backbutton_bottom) = \
            self.backbutton_bounds()
        cmds.append(DrawOutline(
            backbutton_left, backbutton_top,
            backbutton_right, backbutton_bottom,
            "black", 1))
        cmds.append(DrawText(
            backbutton_left, backbutton_top + self.padding,
            "<", self.font, "black"))

        (addressbar_left, addressbar_top, \
            addressbar_right, addressbar_bottom) = \
            self.addressbar_bounds()

        cmds.append(DrawOutline(
            addressbar_left, addressbar_top, addressbar_right,
            addressbar_bottom, "black", 1))
        left_bar = addressbar_left + self.padding
        top_bar = addressbar_top + self.padding
        if self.browser.focus == "address bar":
            cmds.append(DrawText(
                left_bar, top_bar,
                self.browser.address_bar, self.font, "black"))
            w = self.font.measureText(self.browser.address_bar)
            cmds.append(DrawLine(
                left_bar + w, top_bar,
                left_bar + w,
                self.bottom - self.padding, "red", 1))
        else:
            url = str(self.browser.tabs[self.browser.active_tab].url)
            cmds.append(DrawText(
                left_bar,
                top_bar,
                url, self.font, "black"))

        cmds.append(DrawLine(
            0, self.bottom + self.padding, WIDTH,
            self.bottom + self.padding, "black", 1))

        return cmds

    def click(self, x, y):
        if intersects(x, y, self.plus_bounds()):
            self.browser.load(URL("https://browser.engineering/"))
        elif intersects(x, y, self.backbutton_bounds()):
            self.browser.tabs[self.browser.active_tab].go_back()
        elif intersects(x, y, self.addressbar_bounds()):
            self.browser.focus = "address bar"
            self.browser.address_bar = ""
        else:
            for i, tab in enumerate(self.browser.tabs):
                if intersects(x, y, self.tab_bounds(i)):
                    self.browser.active_tab = i
                    break
            self.browser.raster_tab()


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

    def handle_down(self):
        self.tabs[self.active_tab].scrolldown()
        self.draw()

    def handle_click(self, e):
        if e.y < self.chrome.bottom:
            self.focus = None
            self.chrome.click(e.x, e.y)
            self.raster_chrome()
        else:
            if self.focus != "content":
                self.focus = "content"
                self.raster_chrome()
            else:
                self.focus = "content"
            self.tabs[self.active_tab].click(e.x, e.y - self.chrome.bottom)
            self.raster_tab()
        self.draw()

    def handle_key(self, char):
        if not (0x20 <= ord(char) < 0x7f): return
        if self.focus == "address bar":
            self.address_bar += char
            self.raster_chrome()
            self.draw()
        elif self.focus == "content":
            self.tabs[self.active_tab].keypress(char)
            self.raster_tab()
            self.draw()

    def handle_enter(self):
        if self.focus == "address bar":
            self.tabs[self.active_tab].load(URL(self.address_bar))
            self.focus = None
            self.raster_tab()
            self.draw()

    def load(self, url):
        new_tab = Tab(HEIGHT - self.chrome.bottom)
        new_tab.load(url)
        self.active_tab = len(self.tabs)
        self.tabs.append(new_tab)
        self.raster_chrome()
        self.raster_tab()
        self.draw()

    def raster_tab(self):
        print('raster_tab')
        active_tab = self.tabs[self.active_tab]
        tab_height = math.ceil(active_tab.document.height)

        if not self.tab_surface or \
                tab_height != self.tab_surface.height():
            self.tab_surface = skia.Surface(WIDTH, tab_height)

        canvas = self.tab_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        print('rastering')
        active_tab.raster(canvas)
        print('raster_tab done')

    def raster_chrome(self):
        canvas = self.chrome_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)

        for cmd in self.chrome.paint():
            cmd.execute(canvas)

    def draw(self):
        canvas = self.root_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        
        tab_rect = skia.Rect.MakeLTRB(0, self.chrome.bottom, WIDTH, HEIGHT)
        tab_offset = self.chrome.bottom - self.tabs[self.active_tab].scroll
        canvas.save()
        canvas.clipRect(tab_rect)
        canvas.translate(0, tab_offset)
        self.tab_surface.draw(canvas, 0, 0)
        canvas.restore()

        chrome_rect = skia.Rect.MakeLTRB(0, 0, WIDTH, self.chrome.bottom)
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
        sdl2.SDL_DestroyWindow(self.sdl_window)

if __name__ == "__main__":
    import sys
    sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS)
    browser = Browser()
    browser.load(URL(sys.argv[1]))

    event = sdl2.SDL_Event()
    while True:
        while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == sdl2.SDL_QUIT:
                browser.handle_quit()
                sdl2.SDL_Quit()
                sys.exit()
            elif event.type == sdl2.SDL_MOUSEBUTTONUP:
                browser.handle_click(event.button)
            elif event.type == sdl2.SDL_KEYDOWN:
                if event.key.keysym.sym == sdl2.SDLK_RETURN:
                    browser.handle_enter()
                elif event.key.keysym.sym == sdl2.SDLK_DOWN:
                    browser.handle_down()
            elif event.type == sdl2.SDL_TEXTINPUT:
                browser.handle_key(event.text.text.decode('utf8'))

