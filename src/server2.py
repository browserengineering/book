import socket
import importlib
from urllib.parse import urlparse

lab1 = importlib.import_module("lab1")

s = socket.socket(
    family=socket.AF_INET,
    type=socket.SOCK_STREAM,
    proto=socket.IPPROTO_TCP,
)
s.bind(('', 8001))
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
    response += "Content-Length: {}\r\n".format(len(body.encode("utf8")))
    response += "Access-Control-Allow-Origin: *\r\n"
    response += "\r\n" + body
    conx.send(response.encode('utf8'))
    conx.close()

# Handles GET requests to /proxy?url as a proxy to load
# url. For example, a request to /proxy?https://browser.engineering
# will respond with the contents of https://browser.engineering in the body
def handle_request(method, url, headers, body):
    print('handle_request: ' + url)
    if method != 'GET':
        return ''
    parsed_url = urlparse(url)

    if (not parsed_url.query):
        return ''

    if (parsed_url.path != '/proxy'):
        return ''

    headers, body = lab1.request(parsed_url.query)
    print(body)
    return body

while True:
    conx, addr = s.accept()
    print("Received connection from", addr)
    handle_connection(conx)
