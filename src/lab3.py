import socket
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

def lex(source):
    out = []
    text = ""
    in_angle = False
    for c in source:
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
    return out

WIDTH = 800
HEIGHT = 600

HSTEP = 13
VSTEP = 18

TSIZE = 16

SCROLL_STEP = 100

def layout(tokens):
    display_list = []

    x, y = HSTEP, VSTEP
    bold, italic = False, False
    terminal_space = True
    for tok in tokens:
        if isinstance(tok, Text):
            font = tkinter.font.Font(
                family="Times",
                size=TSIZE,
                weight=("bold" if bold else "normal"),
                slant=("italic" if italic else "roman"),
            )

            if tok.text[0].isspace() and not terminal_space:
                x += font.measure(" ")
            
            for word in tok.text.split():
                w = font.measure(word)
                if x + w > WIDTH - HSTEP:
                    x = HSTEP
                    y += font.metrics('linespace') * 1.2
                display_list.append((x, y, word, font))
                x += w + font.measure(" ")
            
            terminal_space = tok.text[-1].isspace()
            if not terminal_space:
                x -= font.measure(" ")
        elif isinstance(tok, Tag):
            if tok.tag == "i":
                italic = True
            elif tok.tag == "/i":
                italic = False
            elif tok.tag == "b":
                bold = True
            elif tok.tag == "/b":
                bold = False
            elif tok.tag == "/p":
                terminal_space = True
                x = HSTEP
                y += font.metrics("linespace") * 1.2 + VSTEP
    return display_list

class Browser:
    def __init__(self, text):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(window, width=WIDTH, height=HEIGHT)
        self.canvas.pack()

        self.text = text
        self.layout()

        self.scrolly = 0
        window.bind("<Down>", self.scrolldown)

    def layout(self):
        self.display_list = layout(self.text)
        self.render()

    def render(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            self.canvas.create_text(x, y - self.scrolly, text=c)

    def scrolldown(self, e):
        self.scrolly += SCROLL_STEP
        self.render()


if __name__ == "__main__":
    import sys
    headers, body = request(sys.argv[1])
    show(lex(body))
