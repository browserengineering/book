import socket
import tkinter
import tkinter.font

def parse_url(url):
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

class ElementNode:
    def __init__(self, parent, tagname):
        self.tag, *attrs = tagname.split(" ")
        self.children = []
        self.attributes = {}
        self.parent = parent

        for attr in attrs:
            out = attr.split("=", 1)
            name = out[0]
            val = out[1].strip("\"") if len(out) > 1 else ""
            self.attributes[name.lower()] = val

class TextNode:
    def __init__(self, parent, text):
        self.text = text
        self.parent = parent

def parse(tokens):
    current = None
    for tok in tokens:
        if isinstance(tok, Tag):
            if tok.tag.startswith("/"): # Close tag
                tag = tok.tag[1:]
                node = current
                while node is not None and node.tag != tag:
                    node = node.parent
                if not node and current.parent is not None:
                    current = current.parent
                elif node.parent is not None:
                    current = node.parent
            else: # Open tag
                new = ElementNode(current, tok.tag)
                if current is not None: current.children.append(new)
                if new.tag not in ["br", "link", "meta"]:
                    current = new
        else: # Text token
            new = TextNode(current, tok.text)
            current.children.append(new)
    return current

def layout(node, state):
    if isinstance(node, ElementNode):
        state = layout_open(node, state)
        for child in node.children:
            state = layout(child, state)
        state = layout_close(node, state)
    else:
        state = layout_text(node, state)
    return state

def layout_open(node, state):
    x, y, bold, italic, terminal_space, display_list = state
    if node.tag == "b":
        bold = True
    elif node.tag == "i":
        italic = True
    else:
        pass
    return x, y, bold, italic, terminal_space, display_list

def layout_close(node, state):
    x, y, bold, italic, terminal_space, display_list = state
    font = tkinter.font.Font(
        family="Times", size=16,
        weight="bold" if bold else "normal",
        slant="italic" if italic else "roman"
    )
    if node.tag == "b":
        bold = False
    elif node.tag == "i":
        italic = False
    elif node.tag == "p" or node.tag == "br":
        terminal_space = True
        x = 13
        y += font.metrics('linespace') * 1.2 + 16
    else:
        pass
    return x, y, bold, italic, terminal_space, display_list

def layout_text(node, state):
    x, y, bold, italic, terminal_space, display_list = state

    font = tkinter.font.Font(
        family="Times", size=16,
        weight="bold" if bold else "normal",
        slant="italic" if italic else "roman"
    )

    if node.text[0].isspace() and not terminal_space:
        x += font.measure(" ")
    
    words = node.text.split()
    for i, word in enumerate(words):
        w = font.measure(word)
        if x + w > 787:
            x = 13
            y += font.metrics('linespace') * 1.2
        display_list.append((x, y, word, font))
        x += w + (0 if i == len(words) - 1 else font.measure(" "))
    
    terminal_space = node.text[-1].isspace()
    if terminal_space and words:
        x += font.measure(" ")
    return x, y, bold, italic, terminal_space, display_list

def show(nodes):
    window = tkinter.Tk()
    canvas = tkinter.Canvas(window, width=800, height=600)
    canvas.pack()

    SCROLL_STEP = 100
    scrolly = 0
    state = (13, 13, False, False, True, [])
    _, _, _, _, _, display_list = layout(nodes, state)

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
    host, port, path, fragment = parse_url(url)
    headers, body = request(host, port, path)
    text = lex(body)
    nodes = parse(text)
    show(nodes)

if __name__ == "__main__":
    import sys
    run(sys.argv[1])
