import socket
import email
import random
import time

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

    response, headers = handle_request(method, url, headers, body).encode('utf8')
    conx.send('HTTP/1.0 200 OK\r\n'.encode('utf8'))
    conx.send('Content-Length: {}\r\n\r\n'.format(len(response)).encode('utf8'))
    for header, value in headers.items():
        conx.send("{}: {}\r\n".format(header, value).encode("utf8"))
    conx.send(response)
    conx.close()

    to_del = []
    for t, (v, e) in TOKENS:
        if e < time.time():
            to_del.append(t)
    for t in to_del:
        del TOKENS[t]

ENTRIES = [
    ("Mess with the best, die like the rest", "crashoverride"),
    ("HACK THE PLANET!!!", "nameless")
]

LOGINS = {"crashoverride": "0cool", "nameless": "cerealkiller"}

TOKENS = {}
NONCES = {}

def form_decode(body):
    params = {}
    for field in body.split("&"):
        id, value = field.split("=", 1)
        params[id] = value.replace("%20", " ")
    return params

def parse_cookies(s):
    out = {}
    for cookie in s.split(";"):
        k, v = cookie.strip().split("=", 1)
        out[k] = v
    return out

def check_login(username, pw):
    return username in LOGINS and LOGINS[username] == pw

def handle_request(method, url, headers, body):
    if url == "/comment.js":
        with open("comment.js") as f:
            return f.read(), {}
    elif url == "/comment.css":
        with open("comment.css") as f:
            return f.read(), {}
    elif url == "/login":
        body = "<!doctype html>"
        body += "<form action=/ method=post>"
        body += "<p>Username: <input name=username></p>"
        body += "<p>Password: <input name=password type=password></p>"
        body += "<p><button>Log in</button></p>"
        body += "</form>"
        return body, {}

    resp_headers = {}
    if method == 'POST' and url == "/add":
        params = form_decode(body)
        if 'guest' in params and len(params) <= 100 and username and \
           'nonce' in params and params['nonce'] == NONCE.get(username):
            ENTRIES.setdefault(url, []).append((params['guest'], username))
    elif method == "POST" and url == "/":
        params = form_decode(body)
        if check_login(params.get("username"), params.get("password")):
            username = params["username"]
            out += "<p class=success>Logged in as {}</p>".format(username)
            token = str(random.random())[2:]
            expiration = time.time() + 60 * 60 * 24 * 7
            TOKENS[token] = (username, expiration)
            resp_headers["Set-Cookie"] = "token=" + token + "; expires=" + email.utils.formatdate(expiration)
        else:
            out += "<p class=errors>Login failed!</p>"

    if "cookie" in headers:
        tok = TOKENS.get(parse_cookies(headers["cookie"]).get("token"))

    out = '<!doctype html>'
    out += "<script src=comment.js></script>"
    out += "<link rel=stylesheet href=comment.css />"
    out += "<body>"
    if username:
        nonce = str(random.random())[2:]
        NONCES[username] = nonce
        out += "<form action=/add method=post>"
        out += "<p><input name=guest /></p>"
        out += "<input name=nonce type=hidden value={}>".format(nonce)
        out += "<p id=errors></p>"
        out += "<p><button>Sign the book!</button></p>"
        out += "</form>"
    else:
        out += "<p><a href=/login>Log in to add to the guest book</a></p>"
        
    for entry, who in ENTRIES.get(url, []):
        entry = entry.replace("&", "&amp;").replace("<", "&lt;")
        out += '<p>' + entry + " <i>from " + who + '</i></p>'
    out += '</body>'

    return out, resp_headers

s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
s.bind(("", 8000))
s.listen()

while True:
    conx, addr = s.accept()
    handle_connection(conx)
