import socket

def parse(url):
    assert "://" in url
    scheme, url = url.split("://", 1)
    assert scheme in ["http", "file"]
    hostport, pathfragment = url.split("/", 1) if "/" in url else (url, "/")
    host, port = hostport.rsplit(":", 1) if ":" in hostport else (hostport, "80")
    path, fragment = ("/" + pathfragment).rsplit("#", 1) if "#" in pathfragment else ("/" + pathfragment, None)
    return scheme, host, int(port), path, fragment

def request(scheme, host, port, path):
    # Exercise 2
    if scheme == "http":
        return request_http(host, port, path)
    elif scheme == "file":
        return {}, request_file(path)
    else:
        raise ValueError("Invalid scheme " + scheme)

def request_file(path):
    with open(path) as f:
        return f.read()

def request_http(host, port, path):
    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    s.connect((host, port))

    # Request
    s.send("GET {} HTTP/1.1\r\n".format(path).encode("utf8"))
    # Exercise 1
    headers = {"Host": host, "User-Agent": "Emberfox 1.1", "Connection": "close"}
    for header, value in headers.items():
        s.send("{}: {}\r\n".format(header, value).encode("utf8"))
    s.send(b"\r\n")

    # Response
    response = s.makefile("rb").read().decode("utf8")
    s.close()
    head, body = response.split("\r\n\r\n", 1)
    lines = head.split("\r\n")
    status = lines[0]
    version, code, explanation = status.split(" ", 2)
    assert version == "HTTP/1.0" or version == "HTTP/1.1"
    headers = {}
    for line in lines[1:]:
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()

    # Exercise 3
    if code[0] == "3" and "location" in headers:
        location = headers["location"]
        if location.startswith("/"):
            return request_http(host, port, location)
        else:
            scheme, host, port, path, fragment = parse(location)
            return request(scheme, host, port, path)
    return headers, body

def show(ct, source):
    # Exercise 5
    if ct == "text/plain":
        show_text(source)
    elif ct == "text/html":
        show_html(source)
    else:
        raise ValueError("Invalid Content-Type " + ct)

def show_text(source):
    print(source)

def show_html(source):
    in_angle = False
    in_body = False
    tag = ""
    for c in source:
        if c == "<":
            in_angle = True
            tag = ""
        elif c == ">":
            # Exercise 4
            if tag == "body":
                in_body = True
            elif tag == "/body":
                in_body = False
            in_angle = False
        else:
            if in_angle:
                tag += c
            else:
                if in_body: print(c, end="")

def run(url):
    scheme, host, port, path, fragment = parse(url)
    headers, body = request(scheme, host, port, path)

    ct = headers.get("Content-Type", "text/plain" if scheme == "file" else "text/html")
    if ";" in ct:
        ct, params = ct.split(";", 1)
    assert ct in ["text/html", "text/plain"]
    show(ct, body)

if __name__ == "__main__":
    import sys
    run(sys.argv[1])
