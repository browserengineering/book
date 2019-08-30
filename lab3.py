import socket
import tkinter
import tkinter.font

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

def layout(tokens):
    display_list = []

    fonts = { # (bold, italic) -> font
        (False, False): tkinter.font.Font(family="Times", size=16),
        (True, False): tkinter.font.Font(family="Times", size=16, weight="bold"),
        (False, True): tkinter.font.Font(family="Times", size=16, slant="italic"),
        (True, True): tkinter.font.Font(family="Times", size=16, weight="bold", slant="italic"),
    }

    x, y = 13, 13
    bold, italic = False, False
    terminal_space = True
    for tok in tokens:
        font = fonts[bold, italic]
        if isinstance(tok, Text):
            if tok.text[0].isspace() and not terminal_space:
                x += font.measure(" ")
            
            words = tok.text.split()
            for i, word in enumerate(words):
                w = font.measure(word)
                if x + w > 787:
                    x = 13
                    y += font.metrics('linespace') * 1.2
                display_list.append((x, y, word, font))
                x += w + (0 if i == len(words) - 1 else font.measure(" "))
            
            terminal_space = tok.text[-1].isspace()
            if terminal_space and words:
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
        for x, y, c, font in display_list:
            canvas.create_text(x, y - scrolly, text=c, font=font, anchor="nw")

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
