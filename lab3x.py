import socket
import tkinter
import tkinter.font
import collections

def parse(url):
    assert url.startswith("http://")
    url = url[len("http://"):]
    hostport, pathfragment = url.split("/", 1) if "/" in url else (url, "")
    host, port = hostport.rsplit(":", 1) if ":" in hostport else (hostport, "80")
    path, fragment = ("/" + pathfragment).rsplit("#", 1) if "#" in pathfragment else ("/" + pathfragment, None)
    return host, int(port), path, fragment

def request(host, port, path):
    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    s.connect((host, port))
    s.send("GET {} HTTP/1.0\r\nHost: {}\r\n\r\n".format(path, host).encode("utf8"))
    response = s.makefile("rb").read().decode("utf8")
    s.close()

    head, body = response.split("\r\n\r\n", 1)
    lines = head.split("\r\n")
    version, status, explanation = lines[0].split(" ", 2)
    assert status == "200", "Server error {}: {}".format(status, explanation)
    headers = {}
    for line in lines[1:]:
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()
    return headers, body

class Text:
    def __init__(self, text):
        self.text = text.replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")

class Tag:
    def __init__(self, tag):
        if " " in tag:
            self.tag, attrs = tag.split(" ", 1)
            self.attrs = {}
            for entry in attrs.split(" "):
                if "=" in entry:
                    attr, val = entry.split("=", 1)
                else:
                    attr, val = entry, entry
                self.attrs[attr.lower()] = val.strip("\"")
        else:
            self.tag = tag
            self.attrs = {}

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

class DL:
    Text = collections.namedtuple("Text", ["string", "x", "y", "font", "color"])
    Line = collections.namedtuple("Line", ["x1", "y1", "x2", "y2", "color"])

def layout(tokens):
    display_list = []

    x, y = 13, 13
    bold, italic, uline = False, False, False
    family, size, color = "Times", 16, "black"
    pre = False

    terminal_space = True
    for tok in tokens:
        font = tkinter.font.Font(
            family=family, size=size,
            weight=("bold" if bold else "normal"),
            slant=("italic" if italic else "roman")
        )

        if isinstance(tok, Text):
            if tok.text[0].isspace() and not pre and not terminal_space:
                x += font.measure(" ")
            
            words = tok.text.split("\n") if pre else tok.text.split()
            for i, word in enumerate(words):
                w = font.measure(word)
                if x + w > 787 and not pre:
                    x = 13
                    y += font.metrics('linespace') * 1.2

                display_list.append(DL.Text(word, x, y, font, color))
                if uline:
                    yl = y + font.metrics("ascent") + 1
                    display_list.append(DL.Line(x, yl, x + w, yl, color))

                if pre:
                    if i == len(words) - 1:
                        x += w
                    else:
                        x = 13
                        y += font.metrics("linespace") * 1.2
                else:
                    x += w + (0 if i == len(words) - 1 else font.measure(" "))
            
            terminal_space = tok.text[-1].isspace()
            if terminal_space and words and not pre:
                x += font.measure(" ")
        elif isinstance(tok, Tag):
            if tok.tag == "i":
                italic = True
            elif tok.tag == "/i":
                italic = False
            elif tok.tag == "b":
                bold = True
            elif tok.tag == "/b":
                bold = False
            elif tok.tag == "pre":
                family = "Courier New"
                pre = True
            elif tok.tag == "/pre":
                family = "Times"
                pre = False
                terminal_space = True
                x = 13
                y += font.metrics("linespace") * 1.2 + 16
            elif tok.tag == "a":
                color = "blue"
                uline = True
            elif tok.tag == "/a":
                color = "black"
                uline = False
            elif tok.tag == "h1": # Exercise 1
                bold = True
            elif tok.tag == "/h1":
                bold = False
                terminal_space = True
                x = 13
                y += font.metrics("linespace") * 1.2 + 16
            elif tok.tag == "/p":
                terminal_space = True
                x = 13
                y += font.metrics("linespace") * 1.2 + 16
    return display_list

def show(text):
    window = tkinter.Tk()
    canvas = tkinter.Canvas(window, width=800, height=600)
    canvas.pack()

    SCROLL_STEP = 100
    scrolly = 0
    display_list = layout(text)

    def render():
        canvas.delete("all")
        for cmd in display_list:
            if isinstance(cmd, DL.Text):
                canvas.create_text(cmd.x, cmd.y - scrolly, text=cmd.string,
                                   font=cmd.font, fill=cmd.color, anchor="nw")
            elif isinstance(cmd, DL.Line):
                canvas.create_line(cmd.x1, cmd.y1 - scrolly, cmd.x2, cmd.y2 - scrolly, fill=cmd.color)

    def scrolldown(e):
        nonlocal scrolly
        scrolly += SCROLL_STEP
        render()

    window.bind("<Down>", scrolldown)
    render()

    tkinter.mainloop()

def run(url):
    host, port, path, fragment = parse(url)
    headers, body = request(host, port, path)
    text = lex(body)
    show(text)

if __name__ == "__main__":
    import sys
    run(sys.argv[1])
