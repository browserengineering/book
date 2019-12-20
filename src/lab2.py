import socket
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

def layout(text):
    display_list = []
    x, y = 13, 13
    for c in text:
        display_list.append((x, y, c))
        x += 13
        if x >= 787:
            y += 18
            x = 13
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
        for x, y, c in display_list:
            canvas.create_text(x, y - scrolly, text=c)

    def scrolldown(e):
        nonlocal scrolly
        scrolly += SCROLL_STEP
        render()

    window.bind("<Down>", scrolldown)
    render()

    tkinter.mainloop()

if __name__ == "__main__":
    import sys
    headers, body = request(sys.argv[1])
    show(lex(body))
