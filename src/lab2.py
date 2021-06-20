"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 2 (Drawing to the Screen),
without exercises.
"""

import socket
import ssl
import tkinter

def request(socket, url):
    scheme, url = url.split("://", 1)
    assert scheme in ["http", "https"], \
        "Unknown scheme {}".format(scheme)

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

    s.send(("GET {} HTTP/1.0\r\n".format(path) +
            "Host: {}\r\n\r\n".format(host)).encode("utf8"))
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

    body = response.read()
    s.close()

    return headers, body

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

def set_width(width):
    WIDTH = width

def set_height(height):
    HEIGHT = height

def set_hstep(hstep):
    HSTEP = hstep

def set_vstep(vstep):
    VSTEP = vstep

WIDTH, HEIGHT = 0, 0
HSTEP, VSTEP = 0, 0

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
    def __init__(self, socket, window, canvas):
        self.socket = socket
        self.window = window
        self.canvas = canvas
        set_width(WIDTH)
        set_height(HEIGHT)
        set_hstep(HSTEP)
        set_vstep(VSTEP)

        self.canvas.pack()

        self.scroll = 0
        self.window.bind("<Down>", self.scrolldown)

    def load(self, url):
        headers, body = request(self.socket, url)
        text = lex(body)
        self.display_list = layout(text)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            breakpoint("draw")
            if y > self.scroll + HEIGHT: continue
            if y + VSTEP < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=c)

    def scrolldown(self, e):
        self.scroll += SCROLL_STEP
        self.draw()

if __name__ == "__main__":
    import sys

    set_width(800)
    set_height(600)
    set_hstep(13)
    set_vstep(18)

    window = tkinter.Tk();
    Browser(socket, window, tkinter.Canvas(
            window,
            width=WIDTH,
            height=HEIGHT
        )).load(sys.argv[1])
    tkinter.mainloop()
