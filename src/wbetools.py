import dis

def record(type, *args):
    pass

def patch(existing_cls):
    def decorator(new_cls):
        if isinstance(new_cls, type): # Patching classes
            assert isinstance(existing_cls, type), f"Can't patch {existing_cls} with {new_cls}"
            for attr, obj in new_cls.__dict__.items():
                if attr in ["__module__", "__dict__", "__weakref__", "__doc__", "__firstlineno__", "__static_attributes__"]: continue
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

def patchable(f):
    return f;

def js_hide(f):
    return f

def outline_hide(f):
    return f

def delete(f):
    return f

def named_params(f):
    return f

SHOW_COMPOSITED_LAYER_BORDERS = False
USE_COMPOSITING = True
USE_GPU = True
USE_BROWSER_THREAD = True
FORCE_CROSS_ORIGIN_IFRAMES = False
ASSERT_LAYOUT_CLEAN = False
PRINT_INVALIDATION_DEPENDENCIES = False
OUTPUT_TRACE = False

def parse_flags():
    import argparse, sys
    global SHOW_COMPOSITED_LAYER_BORDERS, \
        USE_COMPOSITING, USE_GPU, USE_BROWSER_THREAD, \
        FORCE_CROSS_ORIGIN_IFRAMES, ASSERT_LAYOUT_CLEAN, \
        PRINT_INVALIDATION_DEPENDENCIES, OUTPUT_TRACE

    parser = argparse.ArgumentParser(description='Chapter 13 code')
    parser.add_argument("url", type=str, help="URL to load")
    parser.add_argument('--single_threaded', action="store_true", default=False,
        help='Whether to run the browser without a browser thread')
    parser.add_argument('--disable_compositing', action="store_true",
        default=False, help='Whether to composite some elements')
    parser.add_argument('--disable_gpu', action='store_true',
        default=False, help='Whether to disable use of the GPU')
    parser.add_argument('--show_composited_layer_borders', action="store_true",
        default=False, help='Whether to visually indicate composited layer borders')
    parser.add_argument("--force_cross_origin_iframes", action="store_true",
        default=False, help="Whether to treat all iframes as cross-origin")
    parser.add_argument("--assert_layout_clean", action="store_true",
        default=False, help="Assert layout is clean once complete")
    parser.add_argument("--print_invalidation_dependencies", action="store_true",
        default=False, help="Whether to print out all invalidation dependencies")
    parser.add_argument("--trace", action="store_true",
        default=False, help="Whether to output a browser.trace file")
    args = parser.parse_args()

    USE_BROWSER_THREAD = not args.single_threaded
    USE_GPU = not args.disable_gpu
    USE_COMPOSITING = not args.disable_compositing and not args.disable_gpu
    SHOW_COMPOSITED_LAYER_BORDERS = args.show_composited_layer_borders
    FORCE_CROSS_ORIGIN_IFRAMES = args.force_cross_origin_iframes
    ASSERT_LAYOUT_CLEAN = args.assert_layout_clean
    PRINT_INVALIDATION_DEPENDENCIES = args.print_invalidation_dependencies
    OUTPUT_TRACE = args.trace

    sys.argv = [sys.argv[0], args.url]
