#!/usr/bin/env python3

import argparse
import ast
from dataclasses import dataclass
import sys
from typing import List

groups = [ "Node", "Layout", "Draw" ]

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
    if isinstance(cmd, ast.ClassDef):
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
    elif isinstance(cmd, ast.Expr) and \
         isinstance(cmd.value, ast.Constant) and isinstance(cmd.value.value, str):
        return
    elif isinstance(cmd, ast.Import):
        return
    elif isinstance(cmd, ast.ImportFrom):
        return
    elif isinstance(cmd, ast.If) and isinstance(cmd.test, ast.Compare) and \
         isinstance(cmd.test.left, ast.Name) and cmd.test.left.id == "__name__" and \
         len(cmd.test.comparators) == 1 and isinstance(cmd.test.comparators[0], ast.Constant) and \
         cmd.test.comparators[0].value == "__main__" and len(cmd.test.ops) == 1 and \
         isinstance(cmd.test.ops[0], ast.Eq):
        return IfMain()
    else:
        raise Exception(ast.dump(cmd))

def outline(tree):
    objs = []
    assert isinstance(tree, ast.Module)
    for cmd in tree.body:
        item = to_item(cmd)
        if item: objs.append(item)
    return objs

def get_imports(tree):
    objs = []
    assert isinstance(tree, ast.Module)
    for cmd in tree.body:
        if isinstance(cmd, ast.ImportFrom):
            assert cmd.level == 0
            assert cmd.module
            assert all(name.asname is None for name in cmd.names)
            names = [name.name for name in cmd.names]
            filename = "src/{}.py".format(cmd.module)

            with open(filename) as file:
                suboutline = outline(ast.parse(file.read(), filename))

            for item in suboutline:
                if isinstance(item, IfMain):
                    pass
                elif isinstance(item, Const):
                    if set(names) & set(item.names):
                        assert set(item.names).issubset(names)
                        objs.append(item)
                else:
                    if item.name in names:
                        objs.append(item)
    return objs

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Generates outlines for each chapter's code")
    parser.add_argument("file", type=argparse.FileType())
    parser.add_argument("--html", action="store_true", default=False)
    args = parser.parse_args()

    tree = ast.parse(args.file.read(), args.file.name)
    ol = get_imports(tree)
    ol.extend(outline(tree))
    if args.html:
        write_html(ol)
    else:
        write_str(ol)
