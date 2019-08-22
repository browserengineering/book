import socket
import tkinter

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
    assert version in ["HTTP/1.0", "HTTP/1.1"]
    assert status == "200", "Server error {}: {}".format(status, explanation)
    headers = {}
    for line in lines[1:]:
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()
    return headers, body

def lex(source):
    text = ""
    in_angle = False
    for c in source:
        if c == "<":
            in_angle = True
        elif c == ">":
            in_angle = False
        elif not in_angle:
            text += c
    return text

def layout(text, w, h):
    display_list = []
    x, y = 13, 13
    for c in text:
        if c == "\n":
            x = 13
            y += 24
        else:
            display_list.append((x, y, c))
            x += 13
            if x >= w - 13:
                y += 18
                x = 13
    return display_list

def show(text):
    SCROLL_STEP = 100
    scrolly = 0
    w, h = 800, 600

    window = tkinter.Tk()
    canvas = tkinter.Canvas(window, width=w, height=h, background="white",
                            highlightbackground="red", highlightcolor="red", highlightthickness=3)
    canvas.pack(fill="both", expand=True)

    display_list = []
    def relayout():
        nonlocal display_list
        display_list = layout(text, w - 6, h - 6)

    def render():
        canvas.delete("all")
        for x, y, c in display_list:
            if 0 <= x <= w and 0 <= y - scrolly <= h:
                canvas.create_text(x, y - scrolly, text=c)

    def scrolldown(e):
        nonlocal scrolly
        scrolly += SCROLL_STEP
        render()

    def scrollup(e):
        nonlocal scrolly
        scrolly -= SCROLL_STEP
        if scrolly < 0: scrolly = 0
        render()

    def resize(e):
        nonlocal w, h
        oldw = w
        w, h = e.width, e.height
        if oldw != w: relayout()
        render()

    window.bind("<Down>", scrolldown)
    window.bind("<Up>", scrollup)
    window.bind("<Configure>", resize)
    relayout()
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
