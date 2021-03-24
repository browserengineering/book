#!/usr/bin/env python3

# Issues:
#   Let or not
#   Using new on class constructors

import ast
import json

HINTS = []
IMPORTS = []

def read_hints(f):
    global HINTS
    hints = json.load(f)
    for h in hints:
        assert "line" in h
        assert isinstance(h["line"], int)
        assert "code" in h
        s = ast.parse(h["code"])
        assert isinstance(s, ast.Module)
        assert len(s.body) == 1
        assert isinstance(s.body[0], ast.Expr)
        h["ast"] = s.body[0].value
        h["used"] = False
    HINTS = hints
    
MISSING_HINTS = []
    
def find_hint(t):
    for h in HINTS:
        if h["line"] != t.lineno: continue
        if ast.dump(h["ast"]) != ast.dump(t): continue
        break
    else:
        MISSING_HINTS.append({"line": t.lineno, "code": ast.unparse(t)})
        return None
    assert not h["used"]
    h["used"] = True
    return h

def check_args(args, ctx):
    assert not args.posonlyargs, ast.dump(args)
    assert not args.vararg, ast.dump(args)
    assert not args.kwonlyargs, ast.dump(args)
    assert not args.kw_defaults, ast.dump(args)
    assert not args.kwarg, ast.dump(args)
    out = []
    defaults = ([None] * len(args.args) + args.defaults)[-len(args.args):]
    for i, (arg, default) in enumerate(zip(args.args, defaults)):
        assert not arg.annotation
        assert not arg.type_comment
        if ctx == "class" and i == 0:
            assert arg.arg == "self"
        else:
            if default:
                out.append(arg.arg + " = " + compile(default, ctx=ctx))
            else:
                out.append(arg.arg)
    return out

RENAME_METHODS = {
    "lower": "toLowerCase",
    "upper": "toUpperCase",
    "strip": "trim",
    "append": "push",
    "pop": "pop",
    "startswith": "startsWith",
}

LIBRARY_METHODS = [
    # socket
    "connect",
    "wrap_socket",
    "send",
    "makefile",
    "readline",
    "read",
    "close",

    # tkinter
    "pack",
    "bind",
    "delete",
    "create_text",
    "create_rectangle",

    # tkinter.font
    "metrics",
    "measure",
]

OUR_METHODS = [
    "parse",
    "layout",
    "draw",
    "execute",
]

assert not (set(LIBRARY_METHODS) | set(RENAME_METHODS)) & set(OUR_METHODS)

def compile_func(call, args):
    if isinstance(call.func, ast.Attribute) and \
       call.func.attr == "format" and \
       isinstance(call.func.value, ast.Constant):
        assert isinstance(call.func.value.value, str)
        parts = call.func.value.value.split("{}")
        out = ""
        assert len(parts) == len(args) + 1
        for part, arg in zip(parts, [None] + args):
            assert "{" not in part
            if arg: out += " + " + arg
            if part: out += " + " + repr(part)
        return "(" + out[3:] + ")"
    elif isinstance(call.func, ast.Attribute) and call.func.attr == "encode":
        assert args == ["'utf8'"]
        base = compile(call.func.value, ctx="fn")
        return base
    elif isinstance(call.func, ast.Attribute) and call.func.attr == "join":
        assert len(args) == 1
        base = compile(call.func.value, ctx="expr")
        return args[0] + ".join(" + base + ")"
    elif isinstance(call.func, ast.Attribute) and call.func.attr == "isspace":
        assert len(args) == 0
        base = compile(call.func.value, ctx="expr")
        return base + ".match(/^\s*$/)"
    elif isinstance(call.func, ast.Attribute) and \
         call.func.attr in LIBRARY_METHODS:
        base = compile(call.func.value, ctx="fn")
        return base + "." + call.func.attr + "(" + ", ".join(args) + ")"
    elif isinstance(call.func, ast.Attribute) and \
         call.func.attr in OUR_METHODS:
        base = compile(call.func.value, ctx="fn")
        return base + "." + call.func.attr + "(" + ", ".join(args) + ")"
    elif isinstance(call.func, ast.Attribute) and \
         call.func.attr == "split":
        assert 0 <= len(args) <= 2
        base = compile(call.func.value, ctx="fn")
        if len(args) == 0:
            return base + ".split(/\s+/)"
        elif len(args) == 1:
            return base + ".split(" + args[0] + ")"
        elif len(args) == 2:
            assert args[1].isdigit()
            return base + ".split(" + args[0] + ", " + str(int(args[1]) + 1) + ")"
    elif isinstance(call.func, ast.Attribute):
        base = compile(call.func.value, ctx="fn")
        if base == "this" or base in IMPORTS:
            return base + "." + call.func.attr + "(" + ", ".join(args) + ")"
        elif call.func.attr in RENAME_METHODS:
            fn = RENAME_METHODS[call.func.attr]
            return base + "." + fn + "(" + ", ".join(args) + ")"
        else:
            return "/* " + base + "." + call.func.attr + "(" + ", ".join(args) + ") */"
        if fn not in ["socket.socket", "s.makefile", "tkinter.Canvas"]:
            assert not tree.keywords, fn
    elif isinstance(call.func, ast.Name) and call.func.id == "len":
        assert len(args) == 1
        return args[0] + ".length"
    elif isinstance(call.func, ast.Name) and call.func.id == "isinstance":
        assert len(args) == 2
        return args[0] + " instanceof " + args[1]
    elif isinstance(call.func, ast.Name) and call.func.id == "sum":
        assert len(args) == 1
        return args[0] + ".reduce((a, v) => a + v, 0)"
    elif isinstance(call.func, ast.Name):
        return compile(call.func, ctx="fn") + "(" + ", ".join(args) + ")"
    else:
        raise ValueError(ast.dump(call))

def op2str(op):
    if isinstance(op, ast.Add): return "+"
    elif isinstance(op, ast.Sub): return "-"
    elif isinstance(op, ast.USub): return "-"
    elif isinstance(op, ast.Mult): return "*"
    elif isinstance(op, ast.Div): return "/"
    elif isinstance(op, ast.Not): return "!"
    elif isinstance(op, ast.Gt): return ">"
    elif isinstance(op, ast.Lt): return "<"
    elif isinstance(op, ast.GtE): return ">="
    elif isinstance(op, ast.LtE): return "<="
    elif isinstance(op, ast.Eq): return "==="
    elif isinstance(op, ast.NotEq): return "!=="
    elif isinstance(op, ast.And): return " && "
    elif isinstance(op, ast.Or): return " || "
    else:
        raise ValueError(ast.dump(op))

def compile(tree, indent=0, ctx=None):
    if isinstance(tree, ast.Module):
        assert not tree.type_ignores
        items = [compile(item, indent=0, ctx="module") for item in tree.body]
        return "\n\n".join(items)
    elif isinstance(tree, ast.Import):
        assert len(tree.names) == 1
        assert not tree.names[0].asname
        IMPORTS.append(tree.names[0].name)
        return " " * indent + "// " + "Requires access to `" + tree.names[0].name + "` API"
    elif isinstance(tree, ast.ClassDef):
        assert not tree.bases
        assert not tree.keywords
        assert not tree.decorator_list
        parts = [compile(part, indent=indent + 2, ctx="class") for part in tree.body]
        return " " * indent + "class " + tree.name + "{\n" + "\n\n".join(parts) + "\n}"
    elif isinstance(tree, ast.FunctionDef):
        assert not tree.decorator_list
        assert not tree.returns
        assert not tree.type_comment
        args = check_args(tree.args, ctx)
        name = {
            "__init__": "constructor",
            "__repr__": "toString",
        }.get(tree.name, tree.name)
        def_line = ("" if ctx == "class" else "function ") + name + "(" + ", ".join(args) + ")"
        body = "\n".join([compile(line, indent=indent + 2, ctx="function") for line in tree.body])
        return " " * indent + def_line + " {\n" + body + "\n" + " " * indent + "}"
    elif isinstance(tree, ast.Expr) and ctx == "module" and \
         isinstance(tree.value, ast.Constant) and isinstance(tree.value.value, str):
        cmt = " " * indent + "// "
        return cmt + tree.value.value.strip("\n").replace("\n", "\n" + cmt)
    elif isinstance(tree, ast.Expr):
        return " " * indent + compile(tree.value, indent=indent, ctx="expr") + ";"
    elif isinstance(tree, ast.Assign):
        assert not tree.type_comment
        assert len(tree.targets) == 1
        lhs = compile(tree.targets[0], indent=indent, ctx="lhs")
        rhs = compile(tree.value, indent=indent, ctx="expr")
        if ctx == "class": kw = ""
        elif isinstance(tree.targets[0], ast.Name): kw = "let "
        elif isinstance(tree.targets[0], ast.Tuple): kw = "let "
        else: kw = ""
        return " " * indent + kw + lhs + " = " + rhs + ";"
    elif isinstance(tree, ast.AugAssign):
        lhs = compile(tree.target, indent=indent, ctx="lhs")
        rhs = compile(tree.value, indent=indent, ctx="expr")
        return " " * indent + lhs + " " + op2str(tree.op) + "= " + rhs + ";"
    elif isinstance(tree, ast.Assert):
        test = compile(tree.test, indent=indent, ctx="expr")
        msg = compile(tree.msg, indent=indent, ctx="expr") if tree.msg else None
        return " " * indent + "console.assert(" + test + (", " + msg if msg else "") + ");"
    elif isinstance(tree, ast.Return):
        ret = compile(tree.value, indent=indent, ctx="expr") if tree.value else None
        return " " * indent + "return" + (" " + ret if ret else "") + ";"
    elif isinstance(tree, ast.While):
        assert not tree.orelse
        test = compile(tree.test, indent=indent, ctx="expr")
        out = " " * indent + "while (" + test + ") {\n"
        out += "\n".join([compile(line, indent=indent + 2, ctx="stmt") for line in tree.body])
        out += "\n" + " " * indent + "}"
        return out
    elif isinstance(tree, ast.For):
        assert not tree.orelse
        assert not tree.type_comment
        lhs = compile(tree.target, indent=indent, ctx="lhs")
        rhs = compile(tree.iter, indent=indent, ctx="expr")
        body = "\n".join([compile(line, indent=indent + 2, ctx="stmt") for line in tree.body])
        fstline = " " * indent + "for (let " + lhs + " of " + rhs + ") {\n"
        return fstline + body + "\n" + " " * indent + "}"
    elif isinstance(tree, ast.If) and ctx == "module":
        test = tree.test
        assert isinstance(test, ast.Compare)
        assert isinstance(test.left, ast.Name)
        assert test.left.id == "__name__"
        assert len(test.comparators) == 1
        assert isinstance(test.comparators[0], ast.Str)
        assert test.comparators[0].s == "__main__"
        assert len(test.ops) == 1
        assert isinstance(test.ops[0], ast.Eq)
        return " " * indent + "// Requires a test harness\n"
    elif isinstance(tree, ast.If):
        out = ""
        test = compile(tree.test, indent=indent, ctx="expr")
        out += " " * indent + "if (" + test + ") {\n"
        out += "\n".join([compile(line, indent=indent + 2, ctx="stmt") for line in tree.body])
        while len(tree.orelse) == 1 and isinstance(tree.orelse[0], ast.If):
            tree = tree.orelse[0]
            test = compile(tree.test, indent=indent, ctx="expr")
            out += "\n" + " " * indent + "} else if (" + test + ") {\n"
            out += "\n".join([compile(line, indent=indent + 2, ctx="stmt") for line in tree.body])
        if tree.orelse:
            out += "\n" + " " * indent + "} else {\n"
            out += "\n".join([compile(line, indent=indent + 2, ctx="stmt") for line in tree.orelse])
        out += "\n" + " " * indent + "}"
        return out
    elif isinstance(tree, ast.Continue):
        return " " * indent + "continue;"
    elif isinstance(tree, ast.Break):
        return " " * indent + "break;"
    elif isinstance(tree, ast.Subscript):
        lhs = compile(tree.value, indent=indent, ctx="expr")
        if isinstance(tree.slice, ast.Slice):
            assert not tree.slice.step
            lower = tree.slice.lower and compile(tree.slice.lower, indent=indent, ctx="expr")
            upper = tree.slice.upper and compile(tree.slice.upper, indent=indent, ctx="expr")
            if lower and upper:
                return lhs + ".slice(" + lower + ", " + upper + ")"
            elif upper:
                return lhs + ".slice(0, " + upper + ")"
            elif lower:
                return lhs + ".slice(" + lower + ")"
            else:
                return lhs + ".slice()"
        else:
            rhs = compile(tree.slice, indent=indent, ctx="expr")
            if rhs == "(-1)":
                return lhs + "[" + lhs + ".length - 1]"
            else:
                return lhs + "[" + rhs + "]"
    elif isinstance(tree, ast.Call):
        args = [compile(a, indent=indent, ctx="expr") for a in tree.args]
        return compile_func(tree, args)
    elif isinstance(tree, ast.UnaryOp):
        rhs = compile(tree.operand, indent=indent, ctx="expr")
        return "(" + op2str(tree.op) + rhs + ")"
    elif isinstance(tree, ast.BinOp):
        lhs = compile(tree.left, indent=indent, ctx="expr")
        rhs = compile(tree.right, indent=indent, ctx="expr")
        return "(" + lhs + " " + op2str(tree.op) + " " + rhs + ")"
    elif isinstance(tree, ast.BoolOp):
        parts = [compile(val, indent=indent, ctx="expr") for val in tree.values]
        return "(" + (" " + op2str(tree.op) + " ").join(parts) + ")"
    elif isinstance(tree, ast.Compare):
        assert len(tree.ops) == 1
        assert len(tree.comparators) == 1
        if (isinstance(tree.ops[0], ast.In) or isinstance(tree.ops[0], ast.NotIn)) and \
           isinstance(tree.comparators[0], ast.List):
            negate = isinstance(tree.ops[0], ast.NotIn)
            # pure expressions
            assert isinstance(tree.left, ast.Name) or \
                (isinstance(tree.left, ast.Subscript) and isinstance(tree.left.value, ast.Name)), \
                ast.dump(tree)
            op = " !== " if negate else " === "
            lhs = compile(tree.left, indent=indent, ctx="expr")
            parts = [lhs + op + compile(v, indent=indent, ctx="expr")
                     for v in tree.comparators[0].elts]
            return "(" + (" && " if negate else " || ").join(parts) + ")"
        if isinstance(tree.ops[0], ast.In) or isinstance(tree.ops[0], ast.NotIn):
            h = find_hint(tree)
            negate = isinstance(tree.ops[0], ast.NotIn)
            if not h:
                return "/* " + ast.dump(tree) + " */"
            elif "type" in h:
                t = h["type"]
                assert t in ["str", "dict", "list"]
                lhs = compile(tree.left, indent=indent, ctx="expr")
                rhs = compile(tree.comparators[0], indent=indent, ctx="expr")

                cmp = "===" if negate else "!=="
                if t in ["str", "list"]:
                    return "(" + rhs + ".indexOf(" + lhs + ") " + cmp + " -1)"
                elif t == "dict":
                    return "(" + rhs + "[" + lhs + "] " + cmp + " \"undefined\")"
            else:
                raise ValueError("Bad hint", h)
        else:
            lhs = compile(tree.left, indent=indent, ctx="expr")
            rhs = compile(tree.comparators[0], indent=indent, ctx="expr")
            return "(" + lhs + " " + op2str(tree.ops[0]) + " " + rhs + ")"
    elif isinstance(tree, ast.IfExp):
        test = compile(tree.test, indent=indent, ctx="expr")
        ift = compile(tree.body, indent=indent, ctx="expr")
        iff = compile(tree.orelse, indent=indent, ctx="expr")
        return "(" + test + " ? " + ift + " : " + iff + ")"
    elif isinstance(tree, ast.ListComp):
        assert len(tree.generators) == 1
        e = compile(tree.elt, indent=indent, ctx="expr")
        gen = tree.generators[0]
        assert not gen.is_async
        assert not gen.ifs
        iterator = compile(gen.iter, indent=indent, ctx="expr")
        arg = compile(gen.target, indent=indent, ctx="lhs")
        return iterator + ".map((" + arg + ") => " + e + ")"
    elif isinstance(tree, ast.Attribute):
        if ctx == "lhs":
            assert isinstance(tree.ctx, ast.Store)
        elif ctx == "expr" or ctx == "fn":
            assert isinstance(tree.ctx, ast.Load)
        base = compile(tree.value, indent=indent, ctx="expr")
        name = tree.attr
        return base + "." + name
    elif isinstance(tree, ast.Dict):
        return "{" + ", ".join([compile(k, indent=indent, ctx=ctx) + ": " + compile(v, indent=indent, ctx=ctx) for k, v in zip(tree.keys, tree.values)]) + "}"
    elif isinstance(tree, ast.Tuple) or isinstance(tree, ast.List):
        return "[" + ", ".join([compile(a, indent=indent, ctx=ctx) for a in tree.elts]) + "]"
    elif isinstance(tree, ast.Name):
        if ctx == "lhs":
            assert isinstance(tree.ctx, ast.Store)
        elif ctx == "expr":
            assert isinstance(tree.ctx, ast.Load)
        return {
            "self": "this",
            "False": "false",
            "True": "true",
        }.get(tree.id, tree.id)
    elif isinstance(tree, ast.Constant):
        if isinstance(tree.value, str):
            return repr(tree.value)
        elif isinstance(tree.value, int):
            return repr(tree.value)
        elif isinstance(tree.value, float):
            return repr(tree.value)
        elif tree.value == None:
            return "null"
        else:
            return "/* " + ast.dump(tree) + " */"
            raise ValueError(ast.dump(tree))
    else:
        return " " * indent + "/* " + ast.dump(tree) + " */"
        raise ValueError(ast.dump(tree))

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Compiles each chapter's Python code to JavaScript")
    parser.add_argument("--hints", default=None, type=argparse.FileType())
    parser.add_argument("python", type=argparse.FileType())
    parser.add_argument("javascript", type=argparse.FileType("w"))
    args = parser.parse_args()

    if args.hints: read_hints(args.hints)
    tree = ast.parse(args.python.read(), args.python.name)
    js = compile(tree)
    args.javascript.write(js)

    issues = 0

    if not all(h["used"] for h in HINTS):
        unused = [h for h in HINTS if not h["used"]]
        print(f"Unused hints: {unused}")
        issues = 1

    if "/*" in js:
        print("Compilation failed: Could not compile some expressions", file=sys.stderr)
        for hint in MISSING_HINTS:
            print("Consider hint:", json.dumps(hint))
        issues = 1

    sys.exit(issues)

