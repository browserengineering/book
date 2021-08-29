"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 2 (Drawing to the Screen),
without exercises.
"""

from lab1 import request
from PIL import Image, ImageTk
import skia
import socket
import ssl
import tkinter
import io

def lex(body):
    text = ""
    in_angle = False
    for c in body:
        if c == "<":
            in_angle = True
        elif c == ">":
            in_angle = False
        elif not in_angle:
            text += c
        breakpoint("lex", text)
    return text

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18

SCROLL_STEP = 100

def layout(text):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP
        if cursor_x >= WIDTH - HSTEP:
            cursor_y += VSTEP
            cursor_x = HSTEP
        breakpoint("layout", display_list)
    return display_list

class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT
        )
        self.canvas.pack()

        self.scroll = 0
        self.window.bind("<Down>", self.scrolldown)

    def load(self, url):
        headers, body = request(url)
        text = lex(body)
        self.display_list = layout(text)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        surface = skia.Surface(WIDTH, HEIGHT)

        use_skia = True

        if use_skia:
            with surface as canvas:
                skia_paint = skia.Paint(AntiAlias=True, Color=skia.ColorBLACK)
                skia_font = skia.Font(skia.Typeface('Arial'), 20)
                for x, y, c in self.display_list:
                    if c == '\n': continue
                    breakpoint("draw")
                    if y > self.scroll + HEIGHT: continue
                    if y + VSTEP < self.scroll: continue
                    canvas.drawString(c, x, y - self.scroll, skia_font,
                        skia_paint)
            skia_image = surface.makeImageSnapshot()
            # This is supposed to work, but gets the color channels messed up
            # for some reason
            pil_image = Image.fromarray(skia_image.convert(alphaType=skia.kUnpremul_AlphaType))
            # ... whereas this does not:
            with io.BytesIO(skia_image.encodeToData()) as f:
               pil_image = Image.open(f)
               pil_image.load()
            tk_image = ImageTk.PhotoImage(image=pil_image)
            self.canvas.create_image(0, 0, image=tk_image, anchor="nw")

            # Don't konw why this is required, but it is in my demo.
            tkinter.mainloop()
        else:
            for x, y, c in self.display_list:
                if y > self.scroll + HEIGHT: continue
                if y + VSTEP < self.scroll: continue
                self.canvas.create_text(x, y - self.scroll, text=c)

    def scrolldown(self, e):
        self.scroll += SCROLL_STEP
        self.draw()

if __name__ == "__main__":
    import sys

    Browser().load(sys.argv[1])
    tkinter.mainloop(1,2,3)
