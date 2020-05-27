import socket
import ssl
import tkinter
import tkinter.font

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

    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
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

class Text:
    def __init__(self, text):
        self.text = text

class Tag:
    def __init__(self, tag):
        self.tag = tag

def lex(body):
    out = []
    text = ""
    in_angle = False
    for c in body:
        if c == "<":
            in_angle = True
            if text: out.append(Text(text))
            text = ""
        elif c == ">":
            in_angle = False
            out.append(Tag(text))
            text = ""
        else:
            text += c
    if not in_angle and text:
        out.append(Text(text))
    return out

WIDTH = 800
HEIGHT = 600

HSTEP = 13
VSTEP = 18
LINEHEIGHT = 1.2

SCROLL_STEP = 100

class Line:
    def __init__(self, word, font):
       self.words = [(0, word, font)]
       self.width = font.measure(word + " ")

    def append(self, word, font):
        self.words.append((self.width, word, font))
        self.width += font.measure(word + " ")

class Layout:
    def __init__(self, tokens):
        self.tokens = tokens
        self.display_list = []

    def flush_line(self, y, line):
        if not line: return
        max_ascent = max([font.metrics("ascent") for x, word, font in line.words])
        baseline = y + max_ascent
        for x, word, font in line.words:
            self.display_list.append((x + HSTEP, baseline - font.metrics("ascent"), word, font))

    def layout(self):
        line = None
        y = VSTEP
        size, bold, italic = 16, False, False
        for tok in self.tokens:
            if isinstance(tok, Text):
                font = tkinter.font.Font(
                    family="Times",
                    size=size,
                    weight=("bold" if bold else "normal"),
                    slant=("italic" if italic else "roman"),
                )
                for word in tok.text.split():
                    w = font.measure(word)
                    if not line:
                        line = Line(word, font)
                    elif line.width + w >= WIDTH - HSTEP:
                        self.flush_line(y, line)
                        line = Line(word, font)
                        y += font.metrics("linespace") * LINEHEIGHT
                    else:
                        line.append(word, font)
            elif tok.tag == "i":
                italic = True
            elif tok.tag == "/i":
                italic = False
            elif tok.tag == "b":
                italic = True
            elif tok.tag == "/b":
                italic = False
            elif tok.tag == "small":
                size -= 2
            elif tok.tag == "/small":
                size += 2
            elif tok.tag == "big":
                size += 4
            elif tok.tag == "/big":
                size -= 4
            elif tok.tag == "br" or tok.tag == "br/":
                self.flush_line(y, line)
                line = None
                y += font.metrics("linespace") * LINEHEIGHT
            elif tok.tag == "/p":
                self.flush_line(y, line)
                line = None
                y += font.metrics("linespace") * LINEHEIGHT + VSTEP

class Browser:
    def __init__(self, tokens):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(self.window, width=WIDTH, height=HEIGHT)
        self.canvas.pack()

        self.scrolly = 0
        self.layout = Layout(tokens)
        self.layout.layout()
        self.render()

        self.window.bind("<Down>", self.scrolldown)

    def render(self):
        self.canvas.delete("all")
        for x, y, word, font in self.layout.display_list:
            self.canvas.create_text(x, y - self.scrolly, text=word, font=font, anchor="nw")

    def scrolldown(self, e):
        self.scrolly += SCROLL_STEP
        self.render()

if __name__ == "__main__":
    import sys
    headers, body = request(sys.argv[1])
    text = lex(body)
    browser = Browser(text)
    tkinter.mainloop()
