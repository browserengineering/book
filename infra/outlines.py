#!/usr/bin/env python3

import argparse
import ast, asttools
from dataclasses import dataclass
import sys
from typing import List

class Item: pass

@dataclass
class Function(Item):
    name: str
    args: List[str]
    
    def str(self):
        if len(self.args) > 0 and self.args[0] == "self":
            args = self.args[1:]
        else:
            args = self.args
        return "def {}({})".format(self.name, ", ".join(args))

    def html(self):
        return self.str().replace("def", "<span class=kw>def</span>")

    def sub(self):
        return None

@dataclass
class Class:
    name: str
    fns: List[Item]
    
    def str(self):
        return "class {}:".format(self.name)

    def html(self):
        return self.str().replace("class", "<span class=kw>class</span>")

    def sub(self):
        return self.fns

@dataclass
class Const(Item):
    names: List[str]
    
    def str(self):
        return "{}".format(", ".join(self.names))

    def html(self):
        return self.str()

    def sub(self):
        return None

@dataclass
class IfMain:
    pass
    
    def str(self):
        return "if __name__ == \"__main__\""

    def html(self):
        return self.str().replace("if", "<span class=cf>if</span>") \
            .replace("==", "<span class=op>==</span>") \
            .replace("\"__main__\"", "<span class=st>\"__main__\"</span>")

    def sub(self):
        return None

def write_str(objs, indent=0):
    for obj in objs:
        print(" " * indent, obj.str(), sep="")
        subs = obj.sub()
        if subs is None:
            pass
        elif len(subs) == 0:
            print(" " * (indent + 4), "pass", sep="")
        else:
            write_str(subs, indent=indent+4)

def write_html(objs, indent=0):
    for obj in objs:
        print("<code class=line>", " " * indent, obj.html(), sep="")
        subs = obj.sub()
        if subs is None:
            pass
        elif len(subs) == 0:
            print("<code class=line>", " " * (indent + 4), "pass", "</code>", sep="")
        else:
            write_html(subs, indent=indent+4)
        print("</code>")

def to_item(cmd):
    if is_sys_modules_hack(cmd): return
    elif is_if_main(cmd): return IfMain()
    elif is_doc_string(cmd): return
    elif isinstance(cmd, ast.ClassDef):
        return Class(cmd.name, [to_item(scmd) for scmd in cmd.body])
    elif isinstance(cmd, ast.FunctionDef):
        return Function(cmd.name, [arg.arg for arg in cmd.args.args])
    elif isinstance(cmd, ast.Assign) and len(cmd.targets) == 1:
        if isinstance(cmd.targets[0], ast.Name):
            names = [cmd.targets[0].id]
        elif isinstance(cmd.targets[0], ast.Tuple):
            names = [elt.id for elt in cmd.targets[0].elts]
        else:
            raise Exception(ast.dump(cmd))
        return Const(names)
    elif isinstance(cmd, ast.Import):
        return
    elif isinstance(cmd, ast.ImportFrom):
        return
    else:
        raise Exception(ast.dump(cmd))

def outline(tree):
    objs = []
    for name, item in asttools.iter_defs(tree):
        item = to_item(cmd)
        if item: objs.append(item)
    return objs

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Generates outlines for each chapter's code")
    parser.add_argument("file", type=argparse.FileType())
    parser.add_argument("--html", action="store_true", default=False)
    args = parser.parse_args()

    tree = asttools.inline(asttools.parse(args.file.read(), args.file.name))
    ol = outline(tree)
    if args.html:
        write_html(ol)
    else:
        write_str(ol)
