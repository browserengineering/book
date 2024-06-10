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
    flags : List[str] = ()
    
    def str(self):
        if "noargs" in self.flags:
            args = ["..."]
        elif len(self.args) > 0 and self.args[0] == "self":
            args = self.args[1:]
        else:
            args = self.args
        return "def {}({})".format(self.name, ", ".join(args))

    def html(self):
        if "noargs" in self.flags:
            args = ["..."]
        elif len(self.args) > 0 and self.args[0] == "self":
            args = self.args[1:]
        else:
            args = self.args
        return "<span class=kw>def</span> {}({})".format(self.name, ", ".join(args))

    def sub(self):
        return None

@dataclass
class Class:
    name: str
    fns: List[Item]
    flags : List[str] = ()
    
    def str(self):
        return "class {}:".format(self.name)

    def html(self):
        return "<span class=kw>class</span> {}:".format(self.name)

    def sub(self):
        return self.fns

@dataclass
class Const(Item):
    names: List[str]
    flags : List[str] = ()
    
    def str(self):
        return "{}".format(", ".join(self.names))

    def html(self):
        return self.str()

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
    if hasattr(cmd, "decorator_list") and any([
            asttools.is_outline_hide_decorator(dec)
            for dec in cmd.decorator_list
    ]):
        return None
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
    else:
        raise Exception(ast.dump(cmd))

def outline(tree):
    objs = []
    for name, cmd in asttools.iter_defs(tree):
        item = to_item(cmd)
        if item: objs.append(item)
    return objs

def read_template(f):
    items = []
    cur_item = []
    for i, line in enumerate(f):
        if line.isspace(): continue # Whitespace
        if line.strip()[0] == "#": continue # Comments

        if "#" in line:
            line, flags = line.split("#", 1)
            flags = [flag.strip() for flag in flags.split(",")]
        else:
            flags = []

        # Figure out what item is on this line
        if line.strip().startswith("def "):
            name = line.strip()[4:].split("(")[0]
            new_item = Function(name, [])
        elif line.strip().startswith("class "):
            name = line.strip()[6:].split("(")[0].strip().rstrip(":")
            new_item = Class(name, [])
        elif all(word.isupper() for word in line.strip().split(", ")):
            names = line.strip().split(", ")
            new_item = Const(names)
        else:
            raise Exception(f"{f.name}:{i+1}: Could not parse item in template")

        new_item.flags = flags

        # Add it to the template
        if line[0].isalpha():
            items.append(new_item)
            cur_item = None
        elif line.startswith("    "):
            assert cur_item, f"{f.name}:{i+1}: Indented template item does not follow a class block"
            cur_item.fns.append(new_item)
        else:
            raise Exception(f"{f.name}:{i+1}: Could not place item in template")

        if line.strip()[-1] == ":":
            assert isinstance(new_item, Class), f"{f.name}:{i+1}: Colon at the end of a non-class item"
            assert cur_item is None, f"{f.name}:{i+1}: Cannot place class inside class"
            cur_item = new_item

    return items

def sort_outline(ol, template, indent="", debug=False):
    new_ol = []
    for item in template:
        if debug: print(f"{indent}Looking for {item.str()}")
        if isinstance(item, Function):
            old_item = [
                (i, old) for i, old in enumerate(ol)
                if isinstance(old, Function) and old.name == item.name
            ]
            assert len(old_item) <= 1, f"Found {len(old_item)} matches for {item}"
            if old_item:
                if debug: print(f"{indent}Found {item.name}")
                new_ol.append(old_item[0][1])
                old_item[0][1].flags = item.flags
                del ol[old_item[0][0]]
            else:
                pass
        elif isinstance(item, Const):
            old_items = [
                (i, old) for i, old in enumerate(ol)
                if isinstance(old, Const) and set(old.names) & set(item.names)
            ]
            if not old_items: continue
            found_names = set().union(*[old.names for i, old in old_items])
            assert found_names <= set(item.names), \
                f"Looking for constants {item.names} but found {found_names}"
            # Sort found names in the right order
            found_names = sorted(found_names, key=lambda x: item.names.index(x))
            if debug: print(f"{indent}Found {', '.join(found_names)}")
            new_item = Const(found_names)
            new_item.flags = item.flags
            new_ol.append(new_item)
            # Sort in reverse order so indices don't change as we delete
            for i, old in sorted(old_items, key=lambda x: x[0], reverse=True):
                del ol[i]
        elif isinstance(item, Class):
            old_item = [
                (i, old) for i, old in enumerate(ol)
                if isinstance(old, Class) and old.name == item.name
            ]
            assert len(old_item) <= 1, f"Found {len(old_item)} matches for {item}"
            if old_item:
                if debug: print(f"{indent}Found {item.name}")
                cls = old_item[0][1]
                try:
                    new_fns = sort_outline(cls.fns, item.fns, indent=indent+"  ", debug=debug)
                except AssertionError:
                    print(f"Error while sorting {cls.name}:")
                    raise
                assert not cls.fns, f"Template for {cls.name} did not describe:\n" + \
                    "\n".join([f"  " + subitem.str() for subitem in cls.fns])
                cls.fns = new_fns
                new_ol.append(cls)
                cls.flags = item.flags
                del ol[old_item[0][0]]
            else:
                pass
        else:
            raise Exception(f"Found unknown item {item} in template")

    assert not ol, f"Template did not describe:\n" + \
        "\n".join(["  " + item.str() for item in ol])
    return new_ol

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generates outlines for each chapter's code")
    parser.add_argument("file", type=argparse.FileType())
    parser.add_argument("--html", action="store_true", default=False)
    parser.add_argument("--template", type=argparse.FileType(), default=None)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    tree = asttools.inline(asttools.parse(args.file.read(), args.file.name))
        
    ol = outline(tree)

    if args.template:
        template = read_template(args.template)
        ol = sort_outline(ol, template, debug=args.debug)

    if args.html:
        write_html(ol)
    else:
        write_str(ol)
