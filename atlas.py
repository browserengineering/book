#!/usr/bin/env python3

import ast
from dataclasses import dataclass
from typing import List

groups = [ "Node", "Layout", "Draw" ]

@dataclass
class Function:
    name: str
    args: List[str]
    
    def str(self):
        return "def {}({}): ...".format(self.name, ", ".join(self.args))

    def sub(self):
        return None

@dataclass
class Class:
    name: str
    fns: List[Function]
    
    def str(self):
        return "class {}:".format(self.name)

    def sub(self):
        return self.fns

@dataclass
class Const:
    names: List[str]
    
    def str(self):
        return "{} = ...".format(", ".join(self.names))

    def sub(self):
        return None

@dataclass
class IfMain:
    pass
    
    def str(self):
        return "if __name__ == \"__main__\": ..."

    def sub(self):
        return None

def write_outline(objs, indent=0):
    prev = None
    for obj in objs:
        if prev and type(prev) != type(obj): print()
        if isinstance(prev, Class) and isinstance(obj, Class) and \
           any((group in prev.name) != (group in obj.name) for group in groups):
            print()
        prev = obj

        print(" " * indent, obj.str(), sep="")
        subs = obj.sub()
        if subs is None:
            pass
        elif len(subs) == 0:
            print(" " * (indent + 4), "pass", sep="")
        else:
            write_outline(subs, indent=indent+4)

def outline(tree):
    objs = []
    assert isinstance(tree, ast.Module)
    for cmd in tree.body:
        if isinstance(cmd, ast.ClassDef):
            fns = []
            objs.append(Class(cmd.name, fns))
            for subcmd in cmd.body:
                if isinstance(subcmd, ast.FunctionDef):
                    fns.append(Function(subcmd.name, [arg.arg for arg in subcmd.args.args]))
                else:
                    raise Exception(ast.dump(cmd))
        elif isinstance(cmd, ast.FunctionDef):
            objs.append(Function(cmd.name, [arg.arg for arg in cmd.args.args]))
        elif isinstance(cmd, ast.Assign) and len(cmd.targets) == 1:
            if isinstance(cmd.targets[0], ast.Name):
                names = [cmd.targets[0].id]
            elif isinstance(cmd.targets[0], ast.Tuple):
                names = [elt.id for elt in cmd.targets[0].elts]
            else:
                raise Exception(ast.dump(cmd))
            objs.append(Const(names))
        elif isinstance(cmd, ast.Expr) and isinstance(cmd.value, ast.Str):
            pass
        elif isinstance(cmd, ast.Import):
            pass
        elif isinstance(cmd, ast.If) and isinstance(cmd.test, ast.Compare) and \
             isinstance(cmd.test.left, ast.Name) and cmd.test.left.id == "__name__" and \
             len(cmd.test.comparators) == 1 and isinstance(cmd.test.comparators[0], ast.Str) and \
             cmd.test.comparators[0].s == "__main__" and len(cmd.test.ops) == 1 and \
             isinstance(cmd.test.ops[0], ast.Eq):
            objs.append(IfMain())
        else:
            raise Exception(ast.dump(cmd))
    return objs

if __name__ == "__main__":
    import sys
    for fname in sys.argv[1:]:
        with open(fname) as f:
            tree = ast.parse(f.read(), fname)
            print("{}:".format(fname))
            write_outline(outline(tree), indent=2)
            print()
