"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 2 (Drawing to the Screen),
without exercises.
"""

import socket
import ssl
import tkinter

def request(url):
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

SCROLL_STEP = 100

def layout(text, width, hstep, vstep):
    display_list = []
    cursor_x, cursor_y = hstep, vstep
    for c in text:
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += hstep
        if cursor_x >= width - hstep:
            cursor_y += vstep
            cursor_x = hstep
        breakpoint("layout", display_list)
    return display_list

class Browser:
    def __init__(self, width, height, hstep, vstep):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=width,
            height=height)
        self.width = width
        self.height = height
        self.hstep = hstep
        self.vstep = vstep

        self.canvas.pack()

        self.scroll = 0
        self.window.bind("<Down>", self.scrolldown)

    def load(self, url):
        headers, body = request(url)
        text = lex(body)
        self.display_list = layout(text, self.width, self.hstep, self.vstep)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            breakpoint("draw")
            if y > self.scroll + self.height: continue
            if y + self.vstep < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=c)

    def scrolldown(self, e):
        self.scroll += SCROLL_STEP
        self.draw()

if __name__ == "__main__":
    import sys

    width = 800
    height = 600
    hstep = 13
    vstep = 18
    Browser(width, height, hstep, vstep).load(sys.argv[1])
    tkinter.mainloop()
