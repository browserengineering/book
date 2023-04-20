import dis

def record(type, *args):
    pass

def patch(existing_cls):
    def decorator(new_cls):
        for attr in dir(new_cls):
            obj = getattr(new_cls, attr)
            # Copies over all methods and all writable fields of functions
            # Uses a cute hack to get the `function` class.
            if isinstance(obj, type(decorator)) \
               or attr in ["__code__", "__module__", "__defaults__", "__annotations"]:
                try:
                    setattr(existing_cls, attr, obj)
                except Exception as e:
                    print(f"Trying to patch field {attr} of {existing_cls}")
                    raise e
            elif attr == "__closure__":
                assert obj is None, "Cannot patch using a closure"
                assert getattr(existing_cls, attr) is None, "Cannot patch a closure"
            elif attr == "__globals__":
                old_obj = getattr(existing_cls, attr)
                new_name = obj["__name__"]
                old_name = old_obj["__name__"]
                globs = set()
                for instr in dis.Bytecode(new_cls):
                    if instr.opname == "LOAD_GLOBAL":
                        globs.add(instr.argval)
                for field in globs:
                    if field in __builtins__:
                        continue
                    if field not in old_obj:
                        old_obj[field] = obj[field]
                    if obj[field] != old_obj[field]:
                        print()
                        print(f"Difference for {field} between {new_name} and {old_name}")
                        print(" ", obj[field], "vs", old_obj[field])
                        raise Exception(
                            f"{existing_cls.__qualname__}: patch uses global {field}, which differs")
        return existing_cls
    return decorator

def js_hide(f):
    return f

SHOW_COMPOSITED_LAYER_BORDERS = False
USE_COMPOSITING = True
USE_GPU = True
USE_BROWSER_THREAD = True
FORCE_CROSS_ORIGIN_IFRAMES = False
WINDOW_COUNT = 0
