import socket
import random

def handle_connection(conx):
    req = conx.makefile("b")
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

    status, body, headers = do_request(method, url, headers, body)
    response = "HTTP/1.0 {}\r\n".format(status)
    for header, value in headers.items():
        response += "{}: {}\r\n".format(header, value)
    response += "Content-Length: {}\r\n".format(len(body.encode("utf8")))
    response += "\r\n" + body
    conx.send(response.encode('utf8'))
    conx.close()

TOKENS = {}
NONCES = {}

ENTRIES = [
    ("No names. We are nameless!", "cerealkiller"),
    ("HACK THE PLANET!!!", "crashoverride"),
]

LOGINS = { "crashoverride": "0cool", "cerealkiller": "emmanuel" }

def check_login(username, pw):
    return username in LOGINS and LOGINS[username] == pw

def parse_cookies(s):
    out = {}
    if (len(s) == 0):
        return out
    for cookie in s.split(";"):
        k, v = cookie.strip().split("=", 1)
        out[k] = v
    return out

def do_request(method, url, headers, body):
    resp_headers = {}
   
    username = ""
    if method == 'POST' and url == "/":
        params = form_decode(body)
        if check_login(params.get("username"), params.get("password")):
            username = params["username"]
            token = str(random.random())[2:]
            TOKENS[token] = username
            resp_headers["Set-Cookie"] = "token=" + token
    elif "cookie" in headers:
        username = TOKENS.get(parse_cookies(headers["cookie"]).get("token"))

    if method == "GET":
        if url == "/":
            return "200 OK", show_comments(username), resp_headers
        elif url == "/login":
            return "200 OK", login_form(), resp_headers
        elif url == "/comment.js":
            with open("comment9.js") as f:
                return "200 OK", f.read(), resp_headers
        elif url == "/comment.css":
            with open("comment9.css") as f:
                return "200 OK", f.read(), resp_headers
    elif method == "POST":
        if url == "/add":
            params = form_decode(body)
            return "200 OK", add_entry(params, username), resp_headers
        else:
            return "200 OK", show_comments(username), resp_headers

    return "404 Not Found", not_found(url, method), resp_headers

def login_form():
    body = "<!doctype html>"
    body += "<form action=/ method=post>"
    body += "<p>Username: <input name=username></p>"
    body += "<p>Password: <input name=password type=password></p>"
    body += "<p><button>Log in</button></p>"
    body += "</form>"
    return body

def html_escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;")

def show_comments(username):
    out = "<!doctype html>"
    if username:
        nonce = str(random.random())[2:]
        NONCES[username] = nonce
        out += "<form action=add method=post>"
        out +=   "<p><input name=nonce type=hidden value=" + nonce + "></p>"
        out +=   "<p><input name=guest></p>"
        out +=   "<p><button>Sign the book!</button></p>"
        out += "</form>"
    else:
        out += "<p><a href=/login>Log in to add to the guest list</a></p>"

    for entry, who in ENTRIES:
        out += "<p>" + html_escape(entry)
        out += " <i>from " + who + "</i></p>"
    out += "<script src=/comment.js></script>"
    return out

def check_nonce(params, username):
    if 'nonce' not in params: return False
    if username not in NONCES: return False
    return params['nonce'] == NONCES[username]

def not_found(url, method):
    out = "<!doctype html>"
    out += "<h1>{} {} not found!</h1>".format(method, url)
    return out

def add_entry(params, username):
    if 'guest' in params and len(params["guest"]) <= 100 and username:
        ENTRIES.append((params['guest'], username))
    return show_comments(username)

def form_decode(body):
    params = {}
    for field in body.split("&"):
        name, value = field.split("=", 1)
        params[name] = value.replace("%20", " ")
    return params

if __name__ == "__main__":
    s = socket.socket(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
    )
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 8000))
    s.listen()

    while True:
        conx, addr = s.accept()
        print("Received connection from", addr)
        handle_connection(conx)
