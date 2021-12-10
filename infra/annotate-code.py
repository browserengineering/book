#!/bin/python3

DIRS = {
    "tl": "above left",
    "tr": "above right",
    "bl": "below left",
    "br": "below right",
    "sl": "side left",
    "sr": "side right",
}

def parse(s):
    state = "text" # "text" | "mark" | "post-mark" | "dir" | "label"
    out = ""
    buf = ""
    for c in s:
        if c == "[" and state == "text":
            state = "mark"
            out += "<mark>"
        elif c == "]" and state == "mark":
            state = "post-mark"
        elif c == "[" and state == "post-mark":
            state = "dir"
            buf = ""
            out += "<label"
        elif c != "|" and state == "dir":
            buf += c
        elif c == "|" and state == "dir":
            state = "label"
            out += " class='" + DIRS[buf] + "'>"
        elif c == "]" and state == "label":
            state = "text"
            out += "</label></mark>"
        else:
            out += c
    return "<pre class='highlight-region'>\n" + out + "</pre>"

if __name__ == "__main__":
    import sys
    print(parse(sys.stdin.read()))
