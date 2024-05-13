#!/usr/bin/env python3

import difflib
import subprocess
import json
import sys
import tempfile
import urllib.parse

class Span:
    def __init__(self, s):
        self.filename, pos = s.split("@", 1)
        self.start_line = None
        for piece in pos.split(";"):
            start, end = piece.split("-")
            if not self.start_line:
                self.start_line, self.start_char = start.split(":")
            self.end_line, self.end_char = end.split(":")

    def __add__(self, i):
        return Span(f"{self.filename}@{int(self.start_line) + i}:0-{int(self.start_line)}:60")

    def __str__(self):
        return f"{self.filename}:{self.start_line}"

class Block:
    def __init__(self, block):
        meta, self.content = block
        self.book_content = self.content
        assert meta[0] == ""
        self.classes = meta[1]

        self.errors = []
        if any(c.startswith("{.") for c in meta[1]):
            self.errors.append(f"Mis-parsed block metadata")

        attrs = dict(meta[2])
        self.loc = Span(attrs["data-pos"])
        self.file = attrs.get("file")
        self.ignore = attrs.get("ignore")
        self.expected = attrs.get("expected", "True") == "True"
        self.indent(int(attrs.get("indent", "0")))
        if "dropline" in attrs:
            self.dropline(attrs["dropline"])

        # There are several ways to specify text replacements
        cmds = [(key, val) for key, val in meta[2] if key in ["replace", "sub", "with"]]
        if cmds:
            self.replace(cmds)

        self.stop = "stop" in attrs

    def indent(self, n):
        indentation = " " * n
        self.content = indentation + self.content.strip().replace("\n", "\n" + indentation) + "\n"

    def dropline(self, pattern):
        self.content = "\n".join([
            line for line in self.content.split("\n")
            if urllib.parse.unquote(pattern) not in line
        ])

    def replace(self, cmds):
        replacements = []
        sub = None
        for key, value in cmds:
            if key == "replace":
                replacements.extend([item.split("/", 1) for item in value.split(",")])
        for find, replace in replacements:
            find = urllib.parse.unquote(find)
            replace = urllib.parse.unquote(replace)
            self.content = self.content.replace(find, replace)

BLOCK_CACHE = {}

def tangle(file):
    if file not in BLOCK_CACHE:
        cmd = ["pandoc", "--from", "commonmark_x+sourcepos", "--to", "json", file]
        out = subprocess.run(cmd, capture_output=True, check=True)
        data = json.loads(out.stdout)
        blocks = []
        for block in data['blocks']:
            if block['t'] == "CodeBlock":
                val = Block(block['c'])
                blocks.append(val)
                if val.stop: break
        BLOCK_CACHE[file] = blocks
    return BLOCK_CACHE[file]

def find_block(block, text):
    differ = difflib.Differ(charjunk=lambda c: c == " ", linejunk=str.isspace)
    block_lines = [
        i for i in block.content.splitlines(keepends=True)
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
        elif block.ignore and urllib.parse.unquote(block.ignore) in l:
            continue
        elif type == "+":
            # if the "+" immediately follows a "-", check for whitespace differences
            if same and last_type == "-" and n != block.content.count("\n"):
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
    long_lines = []
    for block in blocks:
        content = block.content
        if block.errors:
            for error in block.errors:
                print(f"{block.loc}:", error)
                failure += 1
            continue
        if "example" in block.classes and not block.file: continue
        if language and language not in block.classes: continue
        if block.file != file: continue
        cng = find_block(block, src)
        count += 1
        if any(l2 for l2, l in cng) == block.expected:
            # If expected to pass (True) and there are lines,
            # or if expected to fail (False) and there are no lines,
            # it is a failure
            failure += 1
            lines = block.content.count('\n')
            print()
            print(f"{block.loc}: Failed to match {lines} lines")
            for l2, l in cng:
                if l2:
                    print(">", l, end="")
                    if isinstance(l2, str):
                        print("~", l2, end="")
                else:
                    print(" ", l, end="")
            print()

        for i, line in enumerate(block.book_content.split("\n")):
            if len(line) > 60:
                long_lines.append((block.loc + i + 1, line))
    if long_lines:
        print()
        for loc, chars in long_lines:
            print(f"  {loc}: Line too long ({len(chars)} characters)")
    return failure, count
    
