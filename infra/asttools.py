import ast
import copy

def is_doc_string(cmd):
    return isinstance(cmd, ast.Expr) and \
        isinstance(cmd.value, ast.Constant) and isinstance(cmd.value.value, str)

def is_sys_modules_hack(cmd):
    return isinstance(cmd, ast.Assign) and len(cmd.targets) == 1 and \
        isinstance(cmd.targets[0], ast.Attribute) and \
        isinstance(cmd.targets[0].value, ast.Subscript) and \
        isinstance(cmd.targets[0].value.value, ast.Attribute) and \
        isinstance(cmd.targets[0].value.value.value, ast.Name) and \
        cmd.targets[0].value.value.value.id == 'sys' and \
        cmd.targets[0].value.value.attr == 'modules'

def is_patch_decorator(cmd):
    return isinstance(cmd, ast.Call) and \
        isinstance(cmd.func, ast.Attribute) and \
        isinstance(cmd.func.value, ast.Name) and \
        cmd.func.value.id == "wbetools" and cmd.func.attr == "patch" and \
        not cmd.keywords and \
        len(cmd.args) == 1 and \
        isinstance(cmd.args[0], ast.Name)

def is_if_main(cmd):
    return isinstance(cmd, ast.If) and isinstance(cmd.test, ast.Compare) and \
        isinstance(cmd.test.left, ast.Name) and cmd.test.left.id == "__name__" and \
        len(cmd.test.comparators) == 1 and isinstance(cmd.test.comparators[0], ast.Constant) and \
        cmd.test.comparators[0].value == "__main__" and len(cmd.test.ops) == 1 and \
        isinstance(cmd.test.ops[0], ast.Eq)

def iter_defs(module):
    assert isinstance(module, ast.Module)
    for item in module.body:
        if isinstance(item, ast.Import): pass
        elif isinstance(item, ast.ImportFrom): pass
        elif is_doc_string(item): pass
        elif is_sys_modules_hack(item): pass
        elif is_if_main(item): pass
        elif isinstance(item, ast.ClassDef):
            yield item.name, item
        elif isinstance(item, ast.FunctionDef):
            yield item.name, item
        elif isinstance(item, ast.Assign) and len(item.targets) == 1:
            if isinstance(item.targets[0], ast.Name):
                yield item.targets[0].id, item
            elif isinstance(item.targets[0], ast.Tuple):
                assert isinstance(item.value, ast.Tuple)
                for var, val in zip(item.targets[0].elts, item.value.elts):
                    yield var.id, ast.Assign([var], val)
            else:
                raise Exception("Invalid module member: " + ast.dump(item))
        elif isinstance(item, ast.Try): pass
        else:
            raise Exception("Invalid module member: " + ast.dump(item))

def iter_methods(cls):
    assert isinstance(cls, ast.ClassDef)
    for item in cls.body:
        if is_doc_string(item): pass
        elif isinstance(item, ast.FunctionDef):
            yield item.name, item
        elif isinstance(item, ast.Assign) and len(item.targets) == 1:
            if isinstance(item.targets[0], ast.Name):
                yield item.targets[0].id, item
            elif isinstance(item.targets[0], ast.Tuple):
                assert isinstance(item.value, ast.Tuple)
                for var, val in zip(item.targets[0].elts, item.value.elts):
                    yield var.id, ast.Assign([var], val)
            else:
                raise Exception("Invalid class member: " + ast.dump(item))
        else:
            raise Exception("Invalid class member: " + ast.dump(item))

inline_cache = {}
def load(filename):
    if filename not in inline_cache:
        inline_cache[filename] = "in-progress"
        with open(filename) as f:
            ast = parse(f.read(), filename)
        ast = inline(ast)
        inline_cache[filename] = ast
        return ast
    elif inline_cache[filename] == "in-progress":
        raise ImportError(f"Detected a cycle when loading {filename}")
    else:
        return inline_cache[filename]

class ResolveImports(ast.NodeTransformer):
    def visit_ImportFrom(self, cmd):
        assert cmd.level == 0
        assert cmd.module
        assert all(name.asname is None for name in cmd.names)
        names = [name.name for name in cmd.names]
        filename = "src/{}.py".format(cmd.module)
        objs = []

        subast = load(filename)

        for name in names:
            defns = [item for item_name, item in iter_defs(subast) if item_name == name]
            if len(defns) > 1:
                raise ValueError(f"Multiple definitions for {name} in {filename}\n" + 
                                 "\n".join("  " + unparse(defn) for defn in defns))
            elif len(defns) == 0:
                raise ValueError(f"No definition for {name} in {filename}")
            else:
                objs.append(defns[0])

        return objs
    
class ResolvePatches(ast.NodeTransformer):
    def __init__(self):
        self.patches = {}

    def visit_FunctionDef(self, cmd):
        if not cmd.decorator_list:
            patches = self.patches.get(cmd.name, [])
            if patches:
                args2 = patches[-1].args
                body2 = patches[-1].body
                return ast.FunctionDef(cmd.name, args2, body2, [])
            else:
                return cmd
        else:
            assert len(cmd.decorator_list) == 1
            assert is_patch_decorator(cmd.decorator_list[0])
            assert cmd.decorator_list[0].args[0].id == cmd.name
            self.patches.setdefault(cmd.name, []).append(cmd)
            return None

    def visit_ClassDef(self, cmd):
        if not cmd.decorator_list:
            patches = self.patches.get(cmd.name, [])
            if patches:
                body2 = {}
                for name, stmt in iter_methods(cmd):
                    body2[name] = stmt
                for patch in patches:
                    for repl_name, repl_stmt in iter_methods(patch):
                        body2[repl_name] = repl_stmt
                return ast.ClassDef(patch.name, cmd.bases, cmd.keywords, list(body2.values()), [])
            else:
                return cmd
        else:
            assert len(cmd.decorator_list) == 1
            assert is_patch_decorator(cmd.decorator_list[0])
            # Not just cmd.name because in Chapter 5 we rename Layout to BlockLayout
            self.patches.setdefault(cmd.decorator_list[0].args[0].id, []).append(cmd)
            return None

    def double_visit(self, tree):
        self.visit(tree)
        return self.visit(tree)
        
class ResolveJSHide(ast.NodeTransformer):
    def visit_FunctionDef(self, cmd):
        if any([
                isinstance(dec, ast.Attribute) and dec.attr == "js_hide"
                and isinstance(dec.value, ast.Name) and dec.value.id == "wbetools"
                for dec in cmd.decorator_list
        ]):
            return None
        else:
            return cmd

class AST39(ast.NodeTransformer):
    def visit_Num(self, node):
        return ast.Constant(node.n)
    def visit_Str(self, node):
        return ast.Constant(node.s)
    def visit_NameConstant(self, node):
        return ast.Constant(node.value)
    def visit_Ellipsis(self, node):
        return ast.Constant(node)
    def visit_ExtSlice(self, node):
        return ast.Tuple([self.generic_visit(d) for d in node.dims])
    def visit_Index(self, node):
        return node.value

    @classmethod
    def parse(cls, str, name='<unknown>'):
        tree = ast.parse(str, name)
        if hasattr(ast, "NameConstant"):
            return ast.fix_missing_locations(cls().visit(tree))
        else:
            return tree

    @staticmethod
    def unparse(tree, explain=False):
        if hasattr(ast, "unparse"):
            return ast.unparse(tree)
        elif explain:
            return "/* Please convert to Python: " + ast.dump(tree) + " */"
        else:
            return ast.dump(tree)

def parse(source, filename='<unknown>'):
    return AST39.parse(source, filename)

def inline(tree):
    tree2 = ResolveImports().visit(copy.deepcopy(tree))
    tree3 = ResolvePatches().double_visit(tree2)
    tree4 = ResolveJSHide().visit(tree3)
    return ast.fix_missing_locations(tree4)

def resolve_patches_and_return_them(tree):
    r = ResolvePatches()
    tree2 = r.double_visit(tree)
    return (ast.fix_missing_locations(tree2), r.patches)

def unparse(tree, explain=False):
    return AST39.unparse(tree, explain=explain)
