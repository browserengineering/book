#!/bin/python3
import difflib
import subprocess
import json
import tempfile

def get_blocks(file):
    status = None
    accumulator = ""
    for line in file:
        if line.startswith("##</>"):
            yield status, accumulator
            status = None
            accumulator = ""
        elif line.startswith("##<"):
            metadata = line[len("##<"):-len(">")]
            try:
                status = json.loads(metadata)
            except json.decoder.JSONDecodeError:
                print("Count not decode " + metadata)
                status = {}
            accumulator = ""
        elif status is not None:
            if line:
                accumulator += line + "\n"
                
# Lua code to extract all code blocks from a Markdown file via Pandoc
FILTER = r'''
function CodeBlock(el)
  if el.classes:find("python") and not el.classes:find("example") then
     io.write("##<{")
     local written = nil
     for k, v in pairs(el.attributes) do
         if written then io.write(", ") end
         io.write("\"" .. k .. "\": \"" .. v .. "\"")
         written = true
     end
     io.write("}>\n")
     io.write(el.text .. "\n")
     io.write("##</>\n\n")
     io.flush()
  end
  return el
end
'''

def tangle(file):
    with tempfile.NamedTemporaryFile() as f:
        f.write(FILTER.encode("utf8"))
        f.close()
        cmd = ["pandoc", "--from", "markdown", "--to", "html", "--lua-filter", f.name, file]
        out = subprocess.run(cmd, capture_output=True)
    out.check_returncode()
    return list(get_blocks(out.stdout.decode("utf8").split("\n")))

def find_block(block, text):
    differ = difflib.Differ(charjunk=lambda c: c == " ", linejunk=lambda s: s.strip().startswith("#"))
    d = differ.compare(block.splitlines(keepends=True), text.splitlines(keepends=True))
    same = []
    last_type = None
    for n, l in enumerate(d):
        type = l[0]
        l = l[2:]
        if type == "?":
            continue
        elif type == "+":
            # if the "+" immediately follows a "-", check for whitespace differences
            if same and last_type == "-" and n != block.count("\n"):
                if same[-1][1].strip() == l.strip():
                    same[-1] = (False, same[-1][1])
                else:
                    same[-1] = (l, same[-1][1])
        elif type == " ":
            same.append((False, l))
        elif type == "-":
            if l.strip().startswith("# ..."):
                type = " "
            else:
                same.append((True, l))
        else:
            raise ValueError("Invalid diff type `" + type + "`")
        last_type = type
    return same

    
if __name__ == "__main__":
    import sys
    with open(sys.argv[2], "r") as f:
        src = f.read()
    
    blocks = tangle(sys.argv[1])
    count = 0
    for name, block in blocks:
        cng = find_block(block, src)
        expected = name.get("expected", "True") == "True"
        if any(l2 for l2, l in cng) == expected:
            count += 1
            print("Block <{}> ({} lines)".format(name, block.count("\n")))
            for l2, l in cng:
                if l2:
                    print(">", l, end="")
                    if isinstance(l2, str):
                        print("~", l2, end="")
                else:
                    print(" ", l, end="")
            print()
    print("Found differences in {} / {} blocks".format(count, len(blocks)))
    sys.exit(count)
