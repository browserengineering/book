#!/usr/bin/env python3

import ast, asttools
import json
import warnings
import outlines

INDENT = 2

class UnsupportedConstruct(AssertionError): pass

class MissingHint(Exception):
    def __init__(self, tree, key, hint, error=None):
        if not error:
            self.message = f"Could not find {key} key for `{asttools.unparse(tree)}`"
        else:
            self.message = error
        self.key = key
        self.tree = tree
        self.hint = hint

ISSUES = []

WRAP_DISABLED = False

def test_mode():
    global WRAP_DISABLED
    WRAP_DISABLED = True

def catch_issues(f):
    def wrapped(tree, *args, **kwargs):
        try:
            return find_hint(tree, "js")
        except MissingHint as e1:
            try:
                return f(tree, *args, **kwargs)
            except MissingHint as e:
                if WRAP_DISABLED: raise e
                ISSUES.append(e)
                return "/* " + asttools.unparse(tree) + " */"
            except AssertionError as e2:
                if str(e2):
                    e1.message = str(e2)
                if WRAP_DISABLED: raise e1
                ISSUES.append(e1)
                return "/* " + asttools.unparse(tree) + " */"
    return wrapped

HINTS = []

def read_hints(f):
    global HINTS
    hints = json.load(f)
    for h in hints:
        assert "line" not in h or isinstance(h["line"], int)
        assert "code" in h
        s = asttools.parse(h["code"])
        assert isinstance(s, ast.Module)
        assert len(s.body) == 1
        if isinstance(s.body[0], ast.Expr):
            h["ast"] = s.body[0].value
        else:
            h["ast"] = s.body[0]
        h["used"] = False
    HINTS = hints
    
def find_hint(t, key, error=None):
    for h in HINTS:
        if "line" in h and h["line"] != t.lineno: continue
        if ast.dump(h["ast"]) != ast.dump(t): continue
        if key not in h: continue
        break
    else:
        ln = t.lineno if hasattr(t, "lineno") else -1
        hint = {"line": ln, "code": asttools.unparse(t, explain=True), key: "???"}
        raise MissingHint(t, key, hint, error=error)
    h["used"] = True
    return h[key]

def check_args(args, ctx):
    assert not args.vararg, ast.dump(args)
    assert not args.kwonlyargs, ast.dump(args)
    assert not args.kw_defaults, ast.dump(args)
    assert not args.kwarg, ast.dump(args)
    out = []
    defaults = ([None] * len(args.args) + args.defaults)[-len(args.args):]
    for i, (arg, default) in enumerate(zip(args.args, defaults)):
        assert not arg.annotation
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
    "endswith": "endsWith",
    "find": "indexOf",
    "copy": "slice",
}

RENAME_FNS = {
    "int": "parseInt",
    "float": "parseFloat",
    "print": "console.log",
}

# These are filled in as import statements are read
RT_IMPORTS = []

RT_METHODS = [
    "makefile",
    "evaljs",
]

LIBRARY_METHODS = [
    # socket
    "connect",
    "wrap_socket",
    "send",
    "readline",
    "read",
    "close",

    # tkinter
    "pack",
    "bind",
    "delete",
    "create_text",
    "create_rectangle",
    "create_line",
    "create_polygon",

    # tkinter.font
    "metrics",
    "measure",

    # stuff the compiler needs
    "toString",
    "init",

    # urllib.parse
    "quote",
    "unquote_plus",

    # dukpy
    "evaljs",
]

OUR_FNS = []
OUR_CLASSES = []
OUR_CONSTANTS = []
OUR_METHODS = []

OUR_SYNC_METHODS = ["__repr__", "__init__"]

FILES = []

EXPORTS = []

def load_outline(module):
    for name, item in asttools.iter_defs(module):
        if isinstance(item, ast.Assign):
            OUR_CONSTANTS.append(name)
        elif isinstance(item, ast.FunctionDef):
            OUR_FNS.append(name)
        elif isinstance(item, ast.ClassDef):
            OUR_CLASSES.append(item.name)
            for subname, subitem in asttools.iter_methods(item):
                if isinstance(subitem, ast.Assign): continue
                elif isinstance(subitem, ast.ClassDef): continue
                elif isinstance(subitem, ast.FunctionDef):
                    OUR_METHODS.append(subname)
                else:
                    raise ValueError(subitem)
        else:
            raise ValueError(item)

    THEIR_STUFF = set(LIBRARY_METHODS) | set(RENAME_METHODS) | set(RENAME_FNS)
    OUR_STUFF = set(OUR_FNS) | set(OUR_METHODS) | set(OUR_CLASSES) | set(OUR_CONSTANTS)

    mixed_types = set(OUR_FNS) & set(OUR_CLASSES)
    assert not mixed_types, f"Names defined as both class and function: {mixed_types}"
    our_their = (set(LIBRARY_METHODS) | set(RENAME_METHODS)) & set(OUR_METHODS)
    assert not our_their, f"Methods defined by both our code and libraries: {our_their}"
    our_their = set(RENAME_FNS) & set(OUR_FNS)
    assert not our_their, f"Functions defined by our code shadow builtins: {our_their}"

def compile_method(base, name, args, ctx):
    base_js = compile_expr(base, ctx)
    args_js = [compile_expr(arg, ctx) for arg in args]
    if name == "bind": # Needs special handling due to "this"
        assert len(args) == 2
        return base_js + ".bind(" + args_js[0] + ", (e) => " + args_js[1] + "(e))"
    elif name == "export_function": # Needs special handling due to "this"
        assert len(args) == 2
        return base_js + ".export_function(" + args_js[0] + ", (...args) => " + args_js[1] + "(...args))"
    elif name in RT_METHODS:
        return "await " + base_js + "." + name + "(" + ", ".join(args_js) + ")"
    elif name in LIBRARY_METHODS:
        return base_js + "." + name + "(" + ", ".join(args_js) + ")"
    elif name in OUR_METHODS:
        if name in OUR_SYNC_METHODS:
            return base_js + "." + name + "(" + ", ".join(args_js) + ")"
        else:
            return "await " + base_js + "." + name + "(" + ", ".join(args_js) + ")"
    elif name in RENAME_METHODS:
        return base_js + "." + RENAME_METHODS[name] + "(" + ", ".join(args_js) + ")"
    elif isinstance(base, ast.Name) and base.id == "self":
        return base_js + "." + name + "(" + ", ".join(args_js) + ")"
    elif base_js in RT_IMPORTS:
        return base_js + "." + name + "(" + ", ".join(args_js) + ")"
    elif name == "keys":
        assert len(args) == 0
        return "Object.keys(" + base_js + ")"
    elif name == "format":
        assert isinstance(base, ast.Constant)
        assert isinstance(base.value, str)
        parts = base.value.split("{}")
        assert len(parts) == len(args) + 1
        out = ""
        for part, arg in zip(parts, [None] + args_js):
            assert "{" not in part
            if arg: out += " + " + arg
            if part: out += " + " + compile_expr(ast.Constant(part), ctx)
        return "(" + out[3:] + ")"
    elif name == "encode":
        assert len(args) == 1
        assert isinstance(args[0], ast.Constant)
        assert args[0].value == "utf8"
        return base_js
    elif name == "decode":
        assert len(args) == 1
        assert isinstance(args[0], ast.Constant)
        assert args[0].value == "utf8"
        return base_js
    elif name == "extend":
        assert len(args) == 1
        return "Array.prototype.push.apply(" + base_js + ", " + args_js[0] + ")"
    elif name == "join":
        assert len(args) == 1
        return args_js[0] + ".join(" + base_js + ")"
    elif name == "isspace":
        assert len(args) == 0
        return "/^\s*$/.test(" + base_js + ")"
    elif name == "isalnum":
        assert len(args) == 0
        return "/^[a-zA-Z0-9]+$/.test(" + base_js + ")"
    elif name == "items":
        assert len(args) == 0
        return "Object.entries(" + base_js + ")"
    elif name == "get":
        assert 1 <= len(args) <= 2
        default = args_js[1] if len(args) == 2 else "null"
        return "(" + base_js + "?.[" + args_js[0] + "] ?? " + default + ")"
    elif name == "split":
        assert 0 <= len(args) <= 2
        if len(args) == 0:
            return base_js + ".trim().split(/\s+/)"
        elif len(args) == 1:
            return base_js + ".split(" + args_js[0] + ")"
        else:
            return "pysplit(" + base_js + ", " + args_js[0] + ", " + args_js[1] + ")"
    elif name == "rsplit":
        assert len(args) == 2
        return "pyrsplit(" + base_js + ", " + args_js[0] + ", " + args_js[1] + ")"
    elif name == "count":
        assert len(args) == 1
        return base_js + ".split(" + args_js[0] + ").length - 1"
    else:
        raise UnsupportedConstruct()

def compile_function(name, args, ctx):
    args_js = [compile_expr(arg, ctx) for arg in args]
    if name in RENAME_FNS:
        return RENAME_FNS[name] + "(" + ", ".join(args_js) + ")"
    elif name in OUR_FNS:
        return "await " + name + "(" + ", ".join(args_js) + ")"
    elif name in OUR_CLASSES:
        return "await (new " + name + "()).init(" + ", ".join(args_js) + ")"
    elif name == "str":
        assert len(args) == 1
        return args_js[0] + ".toString()"
    elif name == "len":
        assert len(args) == 1
        return args_js[0] + ".length"
    elif name == "ord":
        assert len(args) == 1
        return args_js[0] + ".charCodeAt(0)"
    elif name == "isinstance":
        assert len(args) == 2
        return args_js[0] + " instanceof " + args_js[1]
    elif name == "sum":
        assert len(args) == 1
        return args_js[0] + ".reduce((a, v) => a + v, 0)"
    elif name == "max":
        assert 1 <= len(args) <= 2
        if len(args) == 1:
            return args_js[0] + ".reduce((a, v) => Math.max(a, v))"
        else:
            return "Math.max(" + args_js[0] + ", " + args_js[1] + ")"
    elif name == "breakpoint":
        assert isinstance(args[0], ast.Constant)
        assert isinstance(args[0].value, str)
        return "await breakpoint.event(" + ", ".join(args_js) + ")"
    elif name == "min":
        assert 1 <= len(args) <= 2
        if len(args) == 1:
            return args_js[0] + ".reduce((a, v) => Math.min(a, v))"
        else:
            return "Math.min(" + args_js[0] + ", " + args_js[1] + ")"
    elif name == "repr":
        assert len(args) == 1
        return args_js[0] + ".toString()"
    elif name == "open":
        assert len(args) == 1
        assert isinstance(args[0], ast.Str)
        FILES.append(args[0].s)
        return "filesystem.open(" + args_js[0] + ")"
    elif name == "enumerate":
        assert len(args) == 1
        return args_js[0] + ".entries()"
    elif name == "Exception":
        assert len(args) == 1
        return "(new Error(" + args_js[0] + "))"
    else:
        raise UnsupportedConstruct()

def compile_op(op):
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
    elif isinstance(op, ast.And): return "&&"
    elif isinstance(op, ast.Or): return "||"
    else:
        raise UnsupportedConstruct()
    
UNDERSCORES = 0

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
        raise UnsupportedConstruct()
    
def compile_lhs(tree, ctx):
    targets = lhs_targets(tree)
    for target in targets:
        if target not in ctx:
            ctx[target] = {"is_class": False}
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
        args = tree.args[:]
        if tree.keywords:
            names = []
            vals = []
            for kwarg in tree.keywords:
                assert kwarg.arg
                names.append(ast.Constant(kwarg.arg))
                vals.append(kwarg.value)
            args += [ast.Dict(names, vals)]

        if isinstance(tree.func, ast.Attribute):
            return "(" + compile_method(tree.func.value, tree.func.attr, args, ctx) + ")"
        elif isinstance(tree.func, ast.Name) and tree.func.id == "sorted":
            assert len(tree.args) == 1
            assert len(tree.keywords) == 1
            assert tree.keywords[0].arg == 'key'
            assert isinstance(tree.keywords[0].value, ast.Name)
            base = compile_expr(args[0], ctx)
            return "(" + base + ".slice().sort(comparator(" + tree.keywords[0].value.id + ")))"
        elif isinstance(tree.func, ast.Name):
            return "(" + compile_function(tree.func.id, args, ctx) + ")"
        else:
            raise UnsupportedConstruct()
    elif isinstance(tree, ast.UnaryOp):
        rhs = compile_expr(tree.operand, ctx)
        if isinstance(tree.op, ast.Not): rhs = "truthy(" + rhs + ")"
        return "(" + compile_op(tree.op) + rhs + ")"
    elif isinstance(tree, ast.BinOp):
        lhs = compile_expr(tree.left, ctx)
        rhs = compile_expr(tree.right, ctx)
        if isinstance(tree.op, ast.FloorDiv):
            return "Math.trunc(" + lhs + " / " + rhs + ")"
        else:
            return "(" + lhs + " " + compile_op(tree.op) + " " + rhs + ")"
    elif isinstance(tree, ast.BoolOp):
        parts = ["truthy("+compile_expr(val, ctx)+")" for val in tree.values]
        return "(" + (" " + compile_op(tree.op) + " ").join(parts) + ")"
    elif isinstance(tree, ast.Compare):
        lhs = compile_expr(tree.left, ctx)
        conjuncts = []
        for op, comp in zip(tree.ops, tree.comparators):
            rhs = compile_expr(comp, ctx)
            if (isinstance(op, ast.In) or isinstance(op, ast.NotIn)):
                negate = isinstance(op, ast.NotIn)
                if isinstance(comp, ast.Str):
                    cmp = "===" if negate else "!=="
                    conjuncts.append("(" + rhs + ".indexOf(" + lhs + ") " + cmp + " -1)")
                elif isinstance(comp, ast.List):
                    assert isinstance(tree.left, ast.Name) or \
                        (isinstance(tree.left, ast.Subscript) and
                         isinstance(tree.left.value, ast.Name))
                    op = " !== " if negate else " === "
                    parts = [lhs + op + compile_expr(v, ctx) for v in comp.elts]
                    conjuncts.append("(" + (" && " if negate else " || ").join(parts) + ")")
                else:
                    t = find_hint(tree, "type")
                    assert t in ["str", "dict", "list"]
                    cmp = "===" if negate else "!=="
                    if t in ["str", "list"]:
                        conjuncts.append("(" + rhs + ".indexOf(" + lhs + ") " + cmp + " -1)")
                    elif t == "dict":
                        conjuncts.append("(typeof " + rhs + "[" + lhs + "] " + cmp + " \"undefined\")")
            elif isinstance(op, ast.Eq) and \
                 (isinstance(comp, ast.List) or isinstance(tree.left, ast.List)):
                conjuncts.append("(JSON.stringify(" + lhs + ") === JSON.stringify(" + rhs + "))")
            else:
                conjuncts.append("(" + lhs + " " + compile_op(op) + " " + rhs + ")")
            lhs = rhs
        if len(conjuncts) == 1:
            return conjuncts[0]
        else:
            return "(" + " && ".join(conjuncts) + ")"
    elif isinstance(tree, ast.IfExp):
        test = compile_expr(tree.test, ctx)
        ift = compile_expr(tree.body, ctx)
        iff = compile_expr(tree.orelse, ctx)
        return "(" + test + " ? " + ift + " : " + iff + ")"
    elif isinstance(tree, ast.ListComp):
        assert len(tree.generators) == 1
        gen = tree.generators[0]
        out = compile_expr(gen.iter, ctx)
        ctx2 = Context("expr", ctx)
        arg = compile_lhs(gen.target, ctx2)
        assert not gen.is_async
        for if_clause in gen.ifs:
            e = compile_expr(if_clause, ctx2)
            out = "(await asyncfilter(async (" + arg + ") => " + e + ", " + out + "))"
        e = compile_expr(tree.elt, ctx2)
        if e != arg:
            out = "(await Promise.all(" + out + ".map(async (" + arg + ") => " + e + ")))"
        return out
    elif isinstance(tree, ast.Attribute):
        base = compile_expr(tree.value, ctx)
        return base + "." + tree.attr
    elif isinstance(tree, ast.Dict):
        assert all(isinstance(k, ast.Str) for k in tree.keys)
        pairs = [compile_expr(k, ctx) + ": " + compile_expr(v, ctx) for k, v in zip(tree.keys, tree.values)]
        return "{" + ", ".join(pairs) + "}"
    elif isinstance(tree, ast.Tuple) or isinstance(tree, ast.List):
        return "[" + ", ".join([compile_expr(a, ctx) for a in tree.elts]) + "]"
    elif isinstance(tree, ast.Name):
        if tree.id == "self":
            return "this"
        elif tree.id in RT_IMPORTS or tree.id in OUR_CLASSES:
            return tree.id
        elif tree.id == "AssertionError":
            return "Error"
        elif tree.id in OUR_CONSTANTS:
            return "constants.{}".format(tree.id)
        elif tree.id == "_":
            global UNDERSCORES
            UNDERSCORES += 1
            return tree.id + str(UNDERSCORES)
        elif tree.id in ctx:
            return tree.id
        else:
            raise AssertionError(f"Could not find variable {tree.id}")
    elif isinstance(tree, ast.Constant):
        if isinstance(tree.value, str):
            return json.dumps(tree.value)
        elif isinstance(tree.value, bool):
            return "true" if tree.value else "false"
        elif isinstance(tree.value, int):
            return repr(tree.value)
        elif isinstance(tree.value, float):
            return repr(tree.value)
        elif tree.value is None:
            return "null"
        else:
            raise UnsupportedConstruct()
    else:
        raise UnsupportedConstruct()

def flatten_ifs(tree):
    parts = [(tree.test, tree.body)]
    while len(tree.orelse) == 1 and isinstance(tree.orelse[0], ast.If):
        tree = tree.orelse[0]
        parts.append((tree.test, tree.body))
    if tree.orelse:
        parts.append((None, tree.orelse))
    return parts

@catch_issues
def compile(tree, ctx, indent=0):
    if isinstance(tree, ast.Import):
        assert len(tree.names) == 1
        assert not tree.names[0].asname
        name = tree.names[0].name
        ctx[name] = {"is_class": False}
        RT_IMPORTS.append(name.split(".")[0])
        RT_IMPORTS.append(name)
        return " " * indent + "// Please configure the '" + name + "' module"
    elif isinstance(tree, ast.ImportFrom):
        assert tree.level == 0
        assert tree.module
        assert all(name.asname is None for name in tree.names)
        names = [name.name for name in tree.names]

        to_import = []
        to_bind = []
        for name in names:
            if name.isupper(): # Global constant
                to_import.append("constants as {}_constants".format(tree.module))
                to_bind.append(name)
            elif name[0].isupper(): # Class
                to_import.append(name)
            else: # Function
                to_import.append(name)

        import_line = "import {{ {} }} from \"./{}.js\";".format(", ".join(sorted(set(to_import))), tree.module)
        out = " " * indent + import_line
        for const in to_bind:
            out += "\n" + " " * indent + "constants.{} = {}_constants.{};".format(const, tree.module, const)
        return out
    elif isinstance(tree, ast.ClassDef):
        assert not tree.bases
        assert not tree.keywords
        assert not tree.decorator_list
        ctx[tree.name] = {"is_class": True}
        ctx2 = Context("class", ctx)
        parts = [compile(part, indent=indent + INDENT, ctx=ctx2) for part in tree.body]
        EXPORTS.append(tree.name)
        return " " * indent + "class " + tree.name + " {\n" + "\n\n".join(parts) + "\n}"
    elif isinstance(tree, ast.FunctionDef):
        assert not tree.decorator_list
        assert not tree.returns
        args = check_args(tree.args, ctx)

        ctx2 = Context("function", ctx)
        for arg in tree.args.args:
            ctx2[arg.arg] = True
        body = "\n".join([compile(line, indent=indent + INDENT, ctx=ctx2) for line in tree.body])

        if tree.name == "__init__":
            # JS constructors cannot be async, so we move that to a builder method
            assert ctx.type == "class"
            def_line = " " * indent + "async init(" + ", ".join(args) + ") {\n"
            ret_line = "\n" + " " * (indent + INDENT) + "return this;"
            last_line = "\n" + " " * indent + "}"
            return def_line + body + ret_line + last_line
        elif tree.name == "__repr__":
            # This actually defines a 'toString' operator
            assert ctx.type == "class"
            def_line = " " * indent + "toString(" + ", ".join(args) + ") {\n"
            last_line = "\n" + " " * indent + "}"
            return def_line + body + last_line
        else:
            if ctx.type == "module":
                EXPORTS.append(tree.name)
            kw = "" if ctx.type == "class" else "function "
            def_line = kw + tree.name + "(" + ", ".join(args) + ") {\n"
            if ctx.type != "class" or tree.name not in OUR_SYNC_METHODS:
                def_line = "async " + def_line
            last_line = "\n" + " " * indent + "}"
            return " " * indent + def_line + body + last_line
    elif isinstance(tree, ast.Expr) and ctx.type == "module" and \
         isinstance(tree.value, ast.Constant) and isinstance(tree.value.value, str):
        cmt = " " * indent + "// "
        return cmt + tree.value.value.strip("\n").replace("\n", "\n" + cmt)
    elif isinstance(tree, ast.Expr):
        return " " * indent + compile_expr(tree.value, ctx) + ";"
    elif isinstance(tree, ast.Assign):
        assert len(tree.targets) == 1

        targets = lhs_targets(tree.targets[0])
        ins = set([target in ctx for target in targets])
        if True in ins and False in ins:
            kw = "let " + ", ".join([target for target in targets if target not in ctx]) + "; "
        elif ctx.type in ["class"]: kw = ""
        elif False in ins and ctx.type != "module":
            kw = "let "
        else: kw = ""

        lhs = compile_lhs(tree.targets[0], ctx)
        rhs = compile_expr(tree.value, ctx)
        return " " * indent + kw + lhs + " = " + rhs + ";"
    elif isinstance(tree, ast.AugAssign):
        targets = lhs_targets(tree.target)
        for target in targets:
            assert target in ctx
        lhs = compile_lhs(tree.target, ctx)
        rhs = compile_expr(tree.value, ctx)
        return " " * indent + lhs + " " + compile_op(tree.op) + "= " + rhs + ";"
    elif isinstance(tree, ast.Assert):
        test = compile_expr(tree.test, ctx)
        msg = compile_expr(tree.msg, ctx) if tree.msg else ""
        return " " * indent + "if (!truthy(" + test + ")) throw Error(" + msg + ");"
    elif isinstance(tree, ast.Return):
        ret = compile_expr(tree.value, ctx) if tree.value else None
        return " " * indent + "return" + (" " + ret if ret else "") + ";"
    elif isinstance(tree, ast.While):
        assert not tree.orelse
        ctx2 = Context("while", ctx)
        test = compile_expr(tree.test, ctx)
        out = " " * indent + "while (" + test + ") {\n"
        out += "\n".join([compile(line, indent=indent + INDENT, ctx=ctx2) for line in tree.body])
        out += "\n" + " " * indent + "}"
        return out
    elif isinstance(tree, ast.For):
        assert not tree.orelse
        ctx2 = Context("for", ctx)
        lhs = compile_lhs(tree.target, ctx2)
        rhs = compile_expr(tree.iter, ctx)
        body = "\n".join([compile(line, indent=indent + INDENT, ctx=ctx2) for line in tree.body])
        fstline = " " * indent + "for (let " + lhs + " of " + rhs + ") {\n"
        return fstline + body + "\n" + " " * indent + "}"
    elif isinstance(tree, ast.If) and ctx.type == "module":
        test = tree.test
        assert isinstance(test, ast.Compare)
        assert isinstance(test.left, ast.Name)
        assert test.left.id == "__name__"
        assert len(test.comparators) == 1
        if isinstance(test.comparators[0], ast.Str):
            s = test.comparators[0].s
        else:
            assert isinstance(test.comparators[0], ast.Constant)
            assert isinstance(test.comparators[0].value, str)
            s = test.comparators[0].value
        assert s == "__main__"
        assert len(test.ops) == 1
        assert isinstance(test.ops[0], ast.Eq)
        return " " * indent + "// Requires a test harness"
    elif isinstance(tree, ast.If):
        if not tree.orelse and tree.test.lineno == tree.body[0].lineno:
            assert len(tree.body) == 1
            ctx2 = Context(ctx.type, ctx)
            test = compile_expr(tree.test, ctx)
            body = compile(tree.body[0], indent=indent, ctx=ctx2)
            return " " * indent + "if (truthy(" + test + ")) " + body.strip()
        else:
            parts = flatten_ifs(tree)
            out = " " * indent

            # This block handles variables defined in all branches of an if statement
            ctxs = []
            for test, body in parts:
                ctx2 = Context(ctx.type, ctx)
                ctxs.append(ctx2)
                for line in body: compile(line, ctx=ctx2)

            intros = set.intersection(*[set(ctx2) for ctx2 in ctxs]) - set(ctx)
            if intros:
                for name in intros: ctx[name] =   {"is_class": False}
                out += "let " + ", ".join(sorted(intros)) + ";\n" + " " * indent

            for i, (test, body) in enumerate(parts):
                ctx2 = Context(ctx.type, ctx)
                body_js = "\n".join([compile(line, indent=indent + INDENT, ctx=ctx2) for line in body])
                if not i and test:
                    test_js = compile_expr(test, ctx)
                    out += "if (truthy(" + test_js + ")) {\n"
                elif i and test:
                    test_js = compile_expr(test, ctx)
                    out += " else if (truthy(" + test_js + ")) {\n"
                elif not test:
                    out += " else {\n"
                out += body_js + "\n"
                out += " " * indent + "}"

            return out
    elif isinstance(tree, ast.Raise):
        assert tree.exc
        assert not tree.cause
        exc = compile_expr(tree.exc, ctx=ctx)
        return " " * indent + "throw " + exc + ";"
    elif isinstance(tree, ast.Try):
        assert not tree.orelse
        assert not tree.finalbody
        assert len(tree.handlers) == 1
        out = " " * indent + "try {\n"
        ctx2 = Context(ctx.type, ctx)
        body_js = "\n".join([compile(line, indent=indent + INDENT, ctx=ctx2) for line in tree.body])
        out += body_js + "\n"
        handler = tree.handlers[0]
        ctx3 = Context(ctx.type, ctx)
        if handler.name:
            name = handler.name
            ctx3[handler.name] = {"is_class": False}
        else:
            name = "$err"
        out += " " * indent + "} catch (" + name + ") {\n"
        if handler.type:
            exc = compile_expr(handler.type, ctx)
            indent += INDENT
            out += " " * indent + "if (" + name + " instanceof " + exc + ") {\n"
        catch_js = "\n".join([compile(line, indent=indent + INDENT, ctx=ctx3) for line in handler.body])
        out += catch_js + "\n"
        if handler.type:
            out += " " * indent + "} else {\n"
            out += " " * (indent + INDENT) + "throw " + name + ";\n"
            out += " " * indent + "}\n"
        out += " " * indent + "}"
        return out
    elif isinstance(tree, ast.With):
        assert not tree.type_comment
        assert len(tree.items) == 1
        item = tree.items[0]
        if item.optional_vars:
            assert isinstance(item.optional_vars, ast.Name)
        var = compile_lhs(item.optional_vars if item.optional_vars else ast.Name("_ctx"), ctx)
        val = compile_expr(item.context_expr, ctx)
        out = " " * indent + "let " + var + " = " + val + ";\n"
        out += "\n".join([compile(line, indent=indent, ctx=ctx) for line in tree.body]) + "\n"
        out += " " * indent + var + ".close();"
        return out
    elif isinstance(tree, ast.Continue):
        return " " * indent + "continue;"
    elif isinstance(tree, ast.Break):
        return " " * indent + "break;"
    elif isinstance(tree, ast.Pass):
        return ""
    else:
        raise UnsupportedConstruct()
    
def compile_module(tree, use_js_modules):
    assert isinstance(tree, ast.Module)
    ctx = Context("module", {})

    items = [compile(item, indent=0, ctx=ctx) for item in tree.body]

    exports = ""
    rt_imports = ""
    render_imports = ""
    constants_export = "const constants = {};"
    if use_js_modules:
        if len(EXPORTS) > 0:
            exports = "export {{ {} }};".format(", ".join(EXPORTS))

        imports_str = "import {{ {} }} from \"./{}.js\";"

        rt_imports_arr = [ 'breakpoint', 'comparator', 'filesystem', 'asyncfilter', 'pysplit', 'pyrsplit', 'truthy' ]
        rt_imports_arr += set([ mod.split(".")[0] for mod in RT_IMPORTS])
        rt_imports = imports_str.format(", ".join(sorted(rt_imports_arr)), "rt")

        constants_export = "export " + constants_export

    return "{}\n{}\n{}\n\n{}".format(
        exports, rt_imports, constants_export, "\n\n".join(items))

if __name__ == "__main__":
    import sys, os
    import argparse

    MIN_PYTHON = (3, 7)
    if sys.version_info < MIN_PYTHON:
        sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)

    parser = argparse.ArgumentParser(description="Compiles each chapter's Python code to JavaScript")
    parser.add_argument("--hints", default=None, type=argparse.FileType())
    parser.add_argument("--indent", default=2, type=int)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--use-js-modules", action="store_true", default=False)
    parser.add_argument("python", type=argparse.FileType())
    parser.add_argument("javascript", type=argparse.FileType("w"))
    args = parser.parse_args()

    if args.debug:
        test_mode()

    name = os.path.basename(args.python.name)
    assert name.endswith(".py")
    if args.hints: read_hints(args.hints)
    INDENT = args.indent
    tree = asttools.parse(args.python.read(), args.python.name)
    load_outline(asttools.inline(tree))
    js = compile_module(tree, args.use_js_modules)

    for fn in FILES:
        path = os.path.join(os.path.dirname(args.python.name), fn)
        with open(path) as f:
            js += "\nfilesystem.register(" + repr(fn) + ", " + json.dumps(f.read()) + ");\n"
            
    args.javascript.write(js)

    issues = 0
    for i in ISSUES:
        print(i.message)
        if i.hint:
            print("  Hint:", json.dumps(i.hint), file=sys.stderr)
        issues += 1

    for h in HINTS:
        if h["used"]: continue
        h2 = h.copy()
        del h2["used"]
        del h2["ast"]
        print(f"Unused hint: {json.dumps(h2)}", file=sys.stderr)
        issues += 1

    sys.exit(issues)

