import socket
import urllib.parse
import random
import html
import time

SESSIONS = {}

def handle_connection(conx):
    req = conx.makefile("b")
    reqline = req.readline().decode('utf8')
    method, url, version = reqline.split(" ", 2)
    assert method in ["GET", "POST"]
    headers = {}
    while True:
        line = req.readline().decode('utf8')
        if line == '\r\n': break
        header, value = line.split(":", 1)
        headers[header.casefold()] = value.strip()
    if 'content-length' in headers:
        length = int(headers['content-length'])
        body = req.read(length).decode('utf8')
    else:
        body = None

    if "cookie" in headers:
        token = headers["cookie"][len("token="):]
    else:
        token = str(random.random())[2:]

    session = SESSIONS.setdefault(token, {})

    status, body = do_request(session, method, url, headers, body)
    response = "HTTP/1.0 {}\r\n".format(status)
    response += "Content-Length: {}\r\n".format(
        len(body.encode("utf8")))
    if 'cookie' not in headers:
        template = "Set-Cookie: token={}; SameSite=Lax\r\n"
        response += template.format(token)
    csp = "default-src http://localhost:8000"
    response += "Content-Security-Policy: {}\r\n".format(csp)
    response += "\r\n" + body
    conx.send(response.encode('utf8'))
    conx.close()
    
ENTRIES = [
    ("No names. We are nameless!", "cerealkiller"),
    ("HACK THE PLANET!!!", "crashoverride"),
]

LOGINS = {
    "crashoverride": "0cool",
    "cerealkiller": "emmanuel"
}

def do_request(session, method, url, headers, body):
    if method == "GET" and url == "/":
        return "200 OK", show_comments(session)
    elif method == "GET" and url == "/comment.js":
        with open("comment9.js") as f:
            return "200 OK", f.read()
    elif method == "GET" and url == "/comment.css":
        with open("comment9.css") as f:
            return "200 OK", f.read()
    elif method == "GET" and url == "/login":
        return "200 OK", login_form(session)
    elif method == "GET" and url == "/count":
        return "200 OK", show_count()
    elif method == "GET" and url == "/xhr":
        return "200 OK", show_xhr()
    elif url == "/eventloop12.js":
        with open("eventloop12.js") as f:
            return "200 OK", f.read()
    elif method == "POST" and url == "/add":
        params = form_decode(body)
        add_entry(session, params)
        return "200 OK", show_comments(session)
    elif method == "POST" and url == "/":
        params = form_decode(body)
        return do_login(session, params)
    else:
        return "404 Not Found", not_found(url, method)

def form_decode(body):
    params = {}
    for field in body.split("&"):
        name, value = field.split("=", 1)
        params[name] = urllib.parse.unquote_plus(value)
    return params

def show_count():
    out = "<!doctype html>"
    out += "<div>";
    out += "  Let's count up to 99!"
    out += "</div>";
    out += "<div>Output</div>"
    out += "<div>XHR</div>"
    out += "<script src=/eventloop12.js></script>"
    for i in range(1, 200):
        out += "Text {}<br>".format(i)
    out += "End of page"
    return out

def show_xhr():
    time.sleep(5)
    return "Slow XMLHttpRequest response!"

def show_comments(session):
    out = "<!doctype html>"
    if "user" in session:
        out += "<h1>Hello, " + session["user"] + "</h1>"
        nonce = str(random.random())[2:]
        session["nonce"] = nonce
        out += "<form action=add method=post>"
        out +=   "<p><input name=guest></p>"
        out +=   "<input name=nonce type=hidden value=" + nonce + ">"
        out +=   "<p><button>Sign the book!</button></p>"
        out += "</form>"
    else:
        out += "<a href=/login>Sign in to write in the guest book</a>"

    for entry, who in ENTRIES:
        out += "<p>" + html.escape(entry) + "\n"
        out += "<i>by " + html.escape(who) + "</i></p>"

    out += "<link rel=stylesheet src=/comment.css>"
    out += "<label></label>"
    out += "<script src=/comment.js></script>"
    out += "<script src=https://example.com/evil.js></script>"
    return out

def login_form(session):
    body = "<!doctype html>"
    body += "<form action=/ method=post>"
    body += "<p>Username: <input name=username></p>"
    body += "<p>Password: <input name=password type=password></p>"
    body += "<p><button>Log in</button></p>"
    body += "</form>"
    return body 

def do_login(session, params):
    username = params.get("username")
    password = params.get("password")
    if username in LOGINS and LOGINS[username] == password:
        session["user"] = username
        return "200 OK", show_comments(session)
    else:
        out = "<!doctype html>"
        out += "<h1>Invalid password for {}</h1>".format(username)
        return "401 Unauthorized", out

def not_found(url, method):
    out = "<!doctype html>"
    out += "<h1>{} {} not found!</h1>".format(method, url)
    return out

def add_entry(session, params):
    if "user" not in session: return
    if "nonce" not in session or "nonce" not in params: return
    if session["nonce"] != params["nonce"]: return
    if 'guest' in params and len(params['guest']) <= 100:
        ENTRIES.append((params['guest'], session["user"]))

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
