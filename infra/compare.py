#!/usr/bin/env python3

import difflib
import subprocess
import json
import sys
import tempfile
import urllib.parse

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
                print("Could not decode " + metadata)
                status = {}
            accumulator = ""
        elif status is not None:
            if line:
                accumulator += line + "\n"
                
# Lua code to extract all code blocks from a Markdown file via Pandoc
FILTER = r'''
function CodeBlock(el)
  io.write("##<{")
  local written = nil
  io.write("\"classes\": [")
  for i, cls in pairs(el.classes) do
      if written then io.write(", ") end
      io.write("\"" .. cls .. "\"")
      written = true
  end
  io.write("]")
  for k, v in pairs(el.attributes) do
      io.write(", \"" .. k .. "\": \"" .. v:gsub("\"", "\\\"") .. "\"")
  end
  io.write("}>\n")
  io.write(el.text .. "\n")
  io.write("##</>\n\n")
  io.flush()
  return el
end
'''

def indent(block, n=0):
    n = int(n)
    if n == 0: return block
    indentation = " " * n
    block = indentation + block.replace("\n", "\n" + indentation)
    return block[:-n]

def replace(block, *cmds):
    for find, replace in cmds:
        find = urllib.parse.unquote(find)
        replace = urllib.parse.unquote(replace)
        block = block.replace(find, replace)
    return block

def dropline(block, pattern):
    return "\n".join([
        line for line in block.split("\n")
        if pattern not in line
    ])

def tangle(file):
    with open("/tmp/test", "wb") as f:
        f.write(FILTER.encode("utf8"))
        f.close()
        cmd = ["pandoc", "--from", "markdown", "--to", "html", "--lua-filter", f.name, file]
        out = subprocess.run(cmd, capture_output=True)
    out.check_returncode()
    return list(get_blocks(out.stdout.decode("utf8").split("\n")))

def find_block(block, text):
    differ = difflib.Differ(charjunk=lambda c: c == " ", linejunk=str.isspace)
    block_lines = [
        i for i in block.splitlines(keepends=True)
        if "..." not in i and not i.isspace()
    ]
    d = differ.compare(block_lines, text.splitlines(keepends=True))
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
            same.append((True, l))
        else:
            raise ValueError("Invalid diff type `" + type + "`")
        last_type = type
    return same

def compare_files(book, code, language, file):
    src = code.read()
    blocks = tangle(book.name)
    failure, count = 0, 0
    for name, block in blocks:
        if "example" in name.get("classes"): continue
        if language and language not in name.get("classes"): continue
        if name.get("file") != file: continue
        block = indent(block, name.get("indent", "0"))
        block = replace(block, *[item.split("/", 1) for item in name.get("replace", "/").split(",")])
        block = dropline(block, name["dropline"]) if "dropline" in name else block
        cng = find_block(block, src)
        expected = name.get("expected", "True") == "True"
        count += 1
        if any(l2 for l2, l in cng) == expected:
            # If expected to pass (True) and there are lines,
            # or if expected to fail (False) and there are no lines,
            # it is a failure
            failure += 1
            print("Block <{}> ({} lines)".format(name, block.count("\n")))
            if "hide" in name: continue
            for l2, l in cng:
                if l2:
                    print(">", l, end="")
                    if isinstance(l2, str):
                        print("~", l2, end="")
                else:
                    print(" ", l, end="")
            print()
        if name.get("last"): break
    return failure, count

def test_entry(chapter, chapter_metadata, key, language, file):
    if key in chapter_metadata:
        fname = chapter_metadata[key]
        print(f"Comparing chapter {chapter} with {key} {fname}")
        with open("book/" + chapter) as book, \
             open("src/" + fname) as code:
            failure, count = compare_files(book, code, language, file)
            if failure:
                print("  Found differences in {} / {} blocks".format(failure, count))
            else:
                print("  Found no differences {} blocks".format(count))
            return failure
    else:
        return 0
    

if __name__ == "__main__":
    import sys, argparse
    argparser = argparse.ArgumentParser(description="Compare book blocks to teacher's copy")
    argparser.add_argument("--config", type=str)
    argparser.add_argument("--chapter", type=str)
    argparser.add_argument("--book", metavar="book.md", type=argparse.FileType("r"))
    argparser.add_argument("--code", metavar="code.py", type=argparse.FileType("r"))
    argparser.add_argument("--file", dest="file", help="Only consider code blocks from this file")
    args = argparser.parse_args()

    failure = False
    if args.config:
        with open(args.config) as f:
            data = json.load(f)

            chapters = data["chapters"]
            for chapter, metadata in data["chapters"].items():
                if args.chapter and args.chapter != "all" and chapter != args.chapter: continue
                for key in metadata:
                    value = metadata[key]
                    if key == "disabled":
                        continue
                    elif key == "lab":
                        failure += test_entry(chapter, metadata, "lab", "python", None)
                    elif key == "stylesheet":
                        failure += test_entry(chapter, metadata, "stylesheet", "css", None)
                    elif key == "runtime":
                        failure += test_entry(chapter, metadata, "runtime", "javascript", None)
                    elif ".py" in value:
                        failure += test_entry(chapter, metadata, key, "python", key)
                    elif ".js" in value:
                        failure += test_entry(chapter, metadata, key, "javascript", key)
    else:
        failure = compare_files(args.book, args.code, "python", args.file)
    sys.exit(failure)
