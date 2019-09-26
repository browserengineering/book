import socket

def handle_connection(conx):
    req = conx.makefile('rb')
    method, url, version = req.readline().decode('utf8').split(" ", 2)
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

    response = handle_request(method, url, headers, body).encode('utf8')
    conx.send('HTTP/1.0 200 OK\r\n'.encode('utf8'))
    conx.send('Content-Length: {}\r\n\r\n'.format(len(response)).encode('utf8'))
    conx.send(response)
    conx.close()

ENTRIES = ['Pavel was here']
def handle_request(method, url, headers, body):
    if method == 'POST':
        params = {}
        for field in body.split("&"):
            id, value = field.split("=", 1)
            params[id] = value.replace("%20", " ")
        if 'guest' in params:
            ENTRIES.append(params['guest'])

    out = '<!doctype html>'
    out += "<body>"
    out += "<form action=/add method=post><p><input name=guest /></p><p><button>Sign the book!</button></p></form>"
    for entry in ENTRIES.get(url, []):
        out += '<p>' + entry + '</p>'
    out += '</body>'
    return out

s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
s.bind(("", 8000))
s.listen()

while True:
    conx, addr = s.accept()
    handle_connection(conx)
