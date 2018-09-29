import subprocess

def get(domain, path):
    s = subprocess.Popen(["telnet", domain, "80"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    s.stdin.write(("GET " + path + " HTTP/1.0\n\n").encode("latin1"))
    s.stdin.flush()
    out = s.stdout.read().decode("latin1")
    return out.split("\r\n", 3)[-1]

def show(source):
    in_angle = False
    for c in source:
        if c == "<":
            in_angle = True
        elif c == ">":
            in_angle = False
        else:
            if in_angle: continue
            print(c, end="")

def run(url):
    assert url.startswith("http://")
    url = url[len("http://"):]
    domain, path = url.split("/", 1)
    response = get(domain, "/" + path)
    headers, source = response.split("\n\n", 1)
    show(source)

if __name__ == "__main__":
    import sys
    run(sys.argv[1])
