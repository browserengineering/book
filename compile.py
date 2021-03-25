#!/usr/bin/env python3

import ast
import json
import warnings

class CantCompile(Exception):
    def __init__(self, tree, hint=None):
        super().__init__(f"Could not compile `{ast.unparse(tree)}`")
        self.tree = tree
        self.hint = hint

ISSUES = []

def catch_issues(f):
    def wrapped(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except CantCompile as e:
            if not e.hint:
                try:
                    return find_hint(e.tree, "replace")
                except CantCompile as e2:
                    e = e2
            ISSUES.append(e)
            return "/* " + ast.unparse(e.tree) + " */"
    return wrapped

HINTS = []

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
    
def find_hint(t, key):
    for h in HINTS:
        if h["line"] != t.lineno: continue
        if ast.dump(h["ast"]) != ast.dump(t): continue
        if key not in h: continue
        break
    else:
        raise CantCompile(t, hint={"line": t.lineno, "code": ast.unparse(t), key: "???"})
    assert not h["used"]
    h["used"] = True
    return h[key]

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
        if ctx.type == "class" and i == 0:
            assert arg.arg == "self"
        else:
            if default:
                out.append(arg.arg + " = " + compile_expr(default, ctx))
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

RENAME_FNS = {
    "int": "Math.parseInt",
    "float": "Math.parseFloat",
    "print": "console.log",
}

IMPORTS = []

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

OUR_FNS = [
    "print_tree",
    "request",
    "layout_mode",
]

OUR_CLASSES = [
    "Text",
    "Element",
    "HTMLParser",
    "InlineLayout",
    "BlockLayout",
    "DocumentLayout",
    "DrawText",
    "DrawRect",
]

OUR_METHODS = [
    "parse",
    "layout",
    "draw",
    "execute",
]

THEIR_STUFF = set(LIBRARY_METHODS) | set(RENAME_METHODS) | set(RENAME_FNS)
OUR_STUFF = set(OUR_FNS) | set(OUR_METHODS) | set(OUR_CLASSES)
assert not set(OUR_FNS) & set(OUR_CLASSES)
assert not THEIR_STUFF & (set(OUR_FNS) | set(OUR_METHODS))

@catch_issues
def compile_func(call, args, ctx):
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
        base = compile_expr(call.func.value, ctx)
        return base
    elif isinstance(call.func, ast.Attribute) and call.func.attr == "join":
        assert len(args) == 1
        base = compile_expr(call.func.value, ctx)
        return args[0] + ".join(" + base + ")"
    elif isinstance(call.func, ast.Attribute) and call.func.attr == "isspace":
        assert len(args) == 0
        base = compile_expr(call.func.value, ctx)
        return base + ".match(/^\s*$/)"
    elif isinstance(call.func, ast.Attribute) and \
         call.func.attr in LIBRARY_METHODS:
        base = compile_expr(call.func.value, ctx)
        return base + "." + call.func.attr + "(" + ", ".join(args) + ")"
    elif isinstance(call.func, ast.Attribute) and \
         call.func.attr in OUR_METHODS:
        base = compile_expr(call.func.value, ctx)
        return base + "." + call.func.attr + "(" + ", ".join(args) + ")"
    elif isinstance(call.func, ast.Attribute) and \
         call.func.attr == "split":
        assert 0 <= len(args) <= 2
        base = compile_expr(call.func.value, ctx)
        if len(args) == 0:
            return base + ".split(/\s+/)"
        elif len(args) == 1:
            return base + ".split(" + args[0] + ")"
        elif len(args) == 2:
            assert args[1].isdigit()
            return base + ".split(" + args[0] + ", " + str(int(args[1]) + 1) + ")"
        else:
            raise CantCompile(call)
    elif isinstance(call.func, ast.Attribute):
        base = compile_expr(call.func.value, ctx)
        if base == "this" or base in IMPORTS:
            return base + "." + call.func.attr + "(" + ", ".join(args) + ")"
        elif call.func.attr == "items":
            assert len(args) == 0
            return "Object.entries(" + base + ")"
        elif call.func.attr in RENAME_METHODS:
            fn = RENAME_METHODS[call.func.attr]
            return base + "." + fn + "(" + ", ".join(args) + ")"
        else:
            raise CantCompile(call)
        if fn not in ["socket.socket", "s.makefile", "tkinter.Canvas"]:
            assert not tree.keywords, fn
    elif isinstance(call.func, ast.Name):
        if call.func.id in RENAME_FNS:
            return RENAME_FNS[call.func.id] + "(" + ", ".join(args) + ")"
        elif call.func.id in OUR_FNS:
            return call.func.id + "(" + ", ".join(args) + ")"
        elif call.func.id in OUR_CLASSES:
            return "new " + call.func.id + "(" + ", ".join(args) + ")"
        elif call.func.id == "len":
            assert len(args) == 1
            return args[0] + ".length"
        elif call.func.id == "isinstance":
            assert len(args) == 2
            return args[0] + " instanceof " + args[1]
        elif call.func.id == "sum":
            assert len(args) == 1
            return args[0] + ".reduce((a, v) => a + v, 0)"
        elif call.func.id == "max":
            if len(args) == 1:
                return args[0] + ".reduce((a, v) => Math.max(a, v))"
            else:
                assert len(args) == 2
                return "Math.max(" + args[0] + ", " + args[1] + ")"
        elif call.func.id == "min":
            if len(args) == 1:
                return args[0] + ".reduce((a, v) => Math.min(a, v))"
            else:
                assert len(args) == 2
                return "Math.min(" + args[0] + ", " + args[1] + ")"
        elif call.func.id == "repr":
            assert len(args) == 1
            return args[0] + ".toString()"
        else:
            raise CantCompile(call)
    else:
        raise CantCompile(call)

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
        raise CantCompile(op)

def deparen(s):
    if s[0] == "(" and s[-1] == ")":
        return s[1:-1]
    else:
        return s
    
def lhs_targets(tree):
    if isinstance(tree, ast.Name):
        return set([tree.id])
    elif isinstance(tree, ast.Tuple):
        return set().union(*[lhs_targets(t) for t in tree.elts])
    elif isinstance(tree, ast.Attribute):
        return set()
    elif isinstance(tree, ast.Subscript):
        return set()
    else:
        raise CantCompile(tree)
    
def compile_lhs(tree, ctx):
    targets = lhs_targets(tree)
    for target in targets:
        ctx[target] = True
    return compile_expr(tree, ctx)

class Context(dict):
    def __init__(self, type, parent):
        super().__init__(self)
        self.type = type
        self.parent = parent

    def __contains__(self, i):
        return (super().__contains__(i)) or (i in self.parent)

    def __getitem__(self, i):
        if super().__contains__(self, i):
            return super().__getitem__(i)
        else:
            return self.parent[i]
    
@catch_issues
def compile_expr(tree, ctx):
    if isinstance(tree, ast.Subscript):
        lhs = compile_expr(tree.value, ctx)
        if isinstance(tree.slice, ast.Slice):
            assert not tree.slice.step
            lower = tree.slice.lower and compile_expr(tree.slice.lower, ctx)
            upper = tree.slice.upper and compile_expr(tree.slice.upper, ctx)
            if lower and upper:
                return lhs + ".slice(" + lower + ", " + upper + ")"
            elif upper:
                return lhs + ".slice(0, " + upper + ")"
            elif lower:
                return lhs + ".slice(" + lower + ")"
            else:
                return lhs + ".slice()"
        else:
            rhs = compile_expr(tree.slice, ctx)
            if rhs == "(-1)":
                return lhs + "[" + lhs + ".length - 1]"
            else:
                return lhs + "[" + rhs + "]"
    elif isinstance(tree, ast.Call):
        args = [compile_expr(a, ctx) for a in tree.args]
        return compile_func(tree, args, ctx)
    elif isinstance(tree, ast.UnaryOp):
        rhs = compile_expr(tree.operand, ctx)
        return "(" + op2str(tree.op) + rhs + ")"
    elif isinstance(tree, ast.BinOp):
        lhs = compile_expr(tree.left, ctx)
        rhs = compile_expr(tree.right, ctx)
        return "(" + lhs + " " + op2str(tree.op) + " " + rhs + ")"
    elif isinstance(tree, ast.BoolOp):
        parts = [compile_expr(val, ctx) for val in tree.values]
        return "(" + (" " + op2str(tree.op) + " ").join(parts) + ")"
    elif isinstance(tree, ast.Compare):
        assert len(tree.ops) == 1
        assert len(tree.comparators) == 1
        lhs = compile_expr(tree.left, ctx)
        rhs = compile_expr(tree.comparators[0], ctx)
        if (isinstance(tree.ops[0], ast.In) or isinstance(tree.ops[0], ast.NotIn)) and \
           isinstance(tree.comparators[0], ast.List):
            negate = isinstance(tree.ops[0], ast.NotIn)
            # pure expressions
            assert isinstance(tree.left, ast.Name) or \
                (isinstance(tree.left, ast.Subscript) and isinstance(tree.left.value, ast.Name)), \
                ast.dump(tree)
            op = " !== " if negate else " === "
            parts = [lhs + op + compile_expr(v, ctx) for v in tree.comparators[0].elts]
            return "(" + (" && " if negate else " || ").join(parts) + ")"
        elif isinstance(tree.ops[0], ast.In) or isinstance(tree.ops[0], ast.NotIn):
            t = find_hint(tree, "type")
            negate = isinstance(tree.ops[0], ast.NotIn)
            assert t in ["str", "dict", "list"]

            cmp = "===" if negate else "!=="
            if t in ["str", "list"]:
                return "(" + rhs + ".indexOf(" + lhs + ") " + cmp + " -1)"
            elif t == "dict":
                return "(" + rhs + "[" + lhs + "] " + cmp + " \"undefined\")"
        elif isinstance(tree.ops[0], ast.Eq) and \
             (isinstance(tree.comparators[0], ast.List) or isinstance(tree.left, ast.List)):
            return "(JSON.stringify(" + lhs + ") === JSON.stringify(" + rhs + "))"
        else:
            return "(" + lhs + " " + op2str(tree.ops[0]) + " " + rhs + ")"
    elif isinstance(tree, ast.IfExp):
        test = compile_expr(tree.test, ctx)
        ift = compile_expr(tree.body, ctx)
        iff = compile_expr(tree.orelse, ctx)
        return "(" + test + " ? " + ift + " : " + iff + ")"
    elif isinstance(tree, ast.ListComp):
        assert len(tree.generators) == 1
        gen = tree.generators[0]
        iterator = compile_expr(gen.iter, ctx)
        ctx2 = Context("expr", ctx)
        arg = compile_lhs(gen.target, ctx2)
        assert not gen.is_async
        assert not gen.ifs
        e = compile_expr(tree.elt, ctx2)
        return iterator + ".map((" + arg + ") => " + e + ")"
    elif isinstance(tree, ast.Attribute):
        base = compile_expr(tree.value, ctx)
        return base + "." + tree.attr
    elif isinstance(tree, ast.Dict):
        pairs = [compile_expr(k, ctx) + ": " + compile_expr(v, ctx) for k, v in zip(tree.keys, tree.values)]
        return "{" + ", ".join(pairs) + "}"
    elif isinstance(tree, ast.Tuple) or isinstance(tree, ast.List):
        return "[" + ", ".join([compile_expr(a, ctx) for a in tree.elts]) + "]"
    elif isinstance(tree, ast.Name):
        if tree.id not in ctx:
            warnings.warn(f"{tree.id} not found in {ctx}")
        return "this" if tree.id == "self" else tree.id
    elif isinstance(tree, ast.Constant):
        if isinstance(tree.value, str):
            return repr(tree.value)
        elif isinstance(tree.value, bool):
            return "true" if tree.value else "false"
        elif isinstance(tree.value, int):
            return repr(tree.value)
        elif isinstance(tree.value, float):
            return repr(tree.value)
        elif tree.value is None:
            return "null"
        else:
            raise CantCompile(tree)
    else:
        raise CantCompile(call)

@catch_issues
def compile(tree, ctx, indent=0):
    if isinstance(tree, ast.Module):
        assert not tree.type_ignores
        items = [compile(item, indent=0, ctx=ctx) for item in tree.body]
        return "\n\n".join(items)
    elif isinstance(tree, ast.Import):
        assert len(tree.names) == 1
        assert not tree.names[0].asname
        ctx[tree.names[0].name] = True
        IMPORTS.append(tree.names[0].name)
        return " " * indent + "// " + "Requires access to `" + tree.names[0].name + "` API"
    elif isinstance(tree, ast.ClassDef):
        assert not tree.bases
        assert not tree.keywords
        assert not tree.decorator_list
        ctx[tree.name] = True
        ctx2 = Context("class", ctx)
        parts = [compile(part, indent=indent + 2, ctx=ctx2) for part in tree.body]
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
        def_line = ("" if ctx.type == "class" else "function ") + name + "(" + ", ".join(args) + ")"
        ctx2 = Context("function", ctx)
        for arg in tree.args.args:
            ctx2[arg.arg] = True
        body = "\n".join([compile(line, indent=indent + 2, ctx=ctx2) for line in tree.body])
        return " " * indent + def_line + " {\n" + body + "\n" + " " * indent + "}"
    elif isinstance(tree, ast.Expr) and ctx.type == "module" and \
         isinstance(tree.value, ast.Constant) and isinstance(tree.value.value, str):
        cmt = " " * indent + "// "
        return cmt + tree.value.value.strip("\n").replace("\n", "\n" + cmt)
    elif isinstance(tree, ast.Expr):
        return " " * indent + compile_expr(tree.value, ctx) + ";"
    elif isinstance(tree, ast.Assign):
        assert not tree.type_comment
        assert len(tree.targets) == 1

        targets = lhs_targets(tree.targets[0])
        ins = set([target in ctx for target in targets])
        if True in ins and False in ins:
            kw = "let " + ", ".join([target for target in targets if target not in ctx]) + "; "
        elif ctx.type in ["class"]: kw = ""
        elif False in ins: kw = "let "
        else: kw = ""

        lhs = compile_lhs(tree.targets[0], ctx)
        rhs = deparen(compile_expr(tree.value, ctx))
        return " " * indent + kw + lhs + " = " + rhs + ";"
    elif isinstance(tree, ast.AugAssign):
        targets = lhs_targets(tree.target)
        for target in targets:
            assert target in ctx
        lhs = compile_lhs(tree.target, ctx)
        rhs = deparen(compile_expr(tree.value, ctx))
        return " " * indent + lhs + " " + op2str(tree.op) + "= " + rhs + ";"
    elif isinstance(tree, ast.Assert):
        test = compile_expr(tree.test, ctx)
        msg = compile_expr(tree.msg, ctx) if tree.msg else None
        return " " * indent + "console.assert(" + test + (", " + msg if msg else "") + ");"
    elif isinstance(tree, ast.Return):
        ret = compile_expr(tree.value, ctx) if tree.value else None
        return " " * indent + "return" + (" " + ret if ret else "") + ";"
    elif isinstance(tree, ast.While):
        assert not tree.orelse
        test = deparen(compile_expr(tree.test, ctx))
        out = " " * indent + "while (" + test + ") {\n"
        out += "\n".join([compile(line, indent=indent + 2, ctx=ctx) for line in tree.body])
        out += "\n" + " " * indent + "}"
        return out
    elif isinstance(tree, ast.For):
        assert not tree.orelse
        assert not tree.type_comment
        ctx2 = Context(ctx.type, ctx)
        lhs = compile_lhs(tree.target, ctx2)
        rhs = compile_expr(tree.iter, ctx)
        body = "\n".join([compile(line, indent=indent + 2, ctx=ctx2) for line in tree.body])
        fstline = " " * indent + "for (let " + lhs + " of " + rhs + ") {\n"
        return fstline + body + "\n" + " " * indent + "}"
    elif isinstance(tree, ast.If) and ctx.type == "module":
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
        test = deparen(compile_expr(tree.test, ctx))
        out = " " * indent + "if (" + test + ") {\n"
        ctx2 = Context(ctx.type, ctx)
        ift = "\n".join([compile(line, indent=indent + 2, ctx=ctx2) for line in tree.body])
        if "\n" not in ift and not tree.orelse and tree.test.lineno == tree.body[0].lineno:
            return out[:-2] + ift.strip()
        else:
            out += ift
            while len(tree.orelse) == 1 and isinstance(tree.orelse[0], ast.If):
                ctx2 = Context(ctx.type, ctx)
                tree = tree.orelse[0]
                test = compile_expr(tree.test, ctx)
                out += "\n" + " " * indent + "} else if (" + test + ") {\n"
                out += "\n".join([compile(line, indent=indent + 2, ctx=ctx2) for line in tree.body])
            if tree.orelse:
                ctx2 = Context(ctx.type, ctx)
                out += "\n" + " " * indent + "} else {\n"
                out += "\n".join([compile(line, indent=indent + 2, ctx=ctx2) for line in tree.orelse])
            out += "\n" + " " * indent + "}"
            return out
    elif isinstance(tree, ast.Continue):
        return " " * indent + "continue;"
    elif isinstance(tree, ast.Break):
        return " " * indent + "break;"
    else:
        raise CantCompile(tree)

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
    js = compile(tree, ctx=Context("module", {}))
    args.javascript.write(js)

    issues = 0
    for h in HINTS:
        if h["used"]: continue
        print(f"Unused hints: {unused}", file=sys.stderr)
        issues += 1

    for i in ISSUES:
        print(str(i), file=sys.stderr)
        if i.hint:
            print("Consider hint:", json.dumps(i.hint), file=sys.stderr)
        issues += 1

    sys.exit(issues)

