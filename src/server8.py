import socket
s = socket.socket(
    family=socket.AF_INET,
    type=socket.SOCK_STREAM,
    proto=socket.IPPROTO_TCP,
)
s.bind(('', 8000))
s.listen()

def handle_connection(conx):
    req = conx.makefile("rb")
    reqline = req.readline().decode('utf8')
    method, url, version = reqline.split(" ", 2)
    assert method in ["GET", "POST"]
    headers = {}
    for line in req:
        line = line.decode('utf8')
        if line == '\r\n': break
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()
    if 'content-length' in headers:
        length = int(headers['content-length'])
        body = req.read(length).decode('utf8')
    else:
        body = None

    body = handle_request(method, url, headers, body)
    response = "HTTP/1.0 200 OK\r\n"
    response += "Content-Length: {}\r\n".format(len(response))
    response += "\r\n" + body
    conx.send(response.encode('utf8'))
    conx.close()

ENTRIES = [ 'Pavel was here' ]

def handle_request(method, url, headers, body):
    if method == 'POST':
        params = form_decode(body)
        if url == '/add':
            return add_entry(params)
        else:
            return show_comments()
    else:
        return show_comments()

def show_comments():
    out = "<!doctype html>"
    out += "<form action=add method=post>"
    out +=   "<p><input name=guest></p>"
    out +=   "<p><button>Sign the book!</button></p>"
    out += "</form>"
    for entry in ENTRIES:
        out += "<p>" + entry + "</p>"
    return out

def add_entry(params):
    if 'guest' in params:
        ENTRIES.append(params['guest'])
    return show_comments()

def form_decode(body):
    params = {}
    for field in body.split("&"):
        name, value = field.split("=", 1)
        params[name] = value.replace("%20", " ")
    return params

while True:
    conx, addr = s.accept()
    print("Received connection from", addr)
    handle_connection(conx)
