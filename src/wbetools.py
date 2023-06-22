import dis

def record(type, *args):
    pass

def patch(existing_cls):
    def decorator(new_cls):
        if isinstance(new_cls, type): # Patching classes
            assert isinstance(existing_cls, type), f"Can't patch {existing_cls} with {new_cls}"
            for attr, obj in new_cls.__dict__.items():
                if attr in ["__module__", "__dict__", "__weakref__", "__doc__"]: continue
                assert isinstance(obj, type(record)), f"Can't patch attribute {attr} of {new_cls} to be {obj}"
                setattr(existing_cls, attr, obj)
        elif isinstance(new_cls, type(record)): # Patching functions
            assert isinstance(existing_cls, type(record)), f"Can't patch {existing_cls} with {new_cls}"
            for attr in dir(new_cls):
                obj = getattr(new_cls, attr)
                # Copies over all methods and all writable fields of functions
                if attr in ["__code__", "__module__", "__defaults__", "__annotations__"]:
                    setattr(existing_cls, attr, obj)
                elif attr == "__closure__":
                    assert obj is None, "Cannot patch using a closure"
                    assert getattr(existing_cls, attr) is None, "Cannot patch a closure"
                elif attr == "__globals__":
                    # if we are patching a function, the new function
                    # might use a global variable (normally, another
                    # function) that's defined in the new scope but not
                    # the old one. To prevent this, we copy the new
                    # function into the old scope, as long as it's not
                    # already defined. (If it's already defined, we throw
                    # an error.) We only do this for variables that are
                    # actually used; to get that, we walk the bytecode
                    # looking for LOAD_GLOBAL operations.
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
                            msg = f"{existing_cls.__qualname__}: patch uses global {field}, which differs\n"
                            msg += f"Difference for {field} between {new_name} and {old_name}\n"
                            msg += f"  {obj[field]} vs {old_obj[field]}"
                            raise Exception(msg)
        else:
            raise ValueError(f"Cannot patch {existing_cls}")
        return existing_cls
    return decorator

def js_hide(f):
    return f

SHOW_COMPOSITED_LAYER_BORDERS = False
USE_COMPOSITING = True
USE_GPU = True
USE_BROWSER_THREAD = True
FORCE_CROSS_ORIGIN_IFRAMES = False
ASSERT_LAYOUT_CLEAN = False
PRINT_INVALIDATION_DEPENDENCIES = False
WINDOW_COUNT = 0
