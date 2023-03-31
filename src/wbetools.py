
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
                continue
                old_obj = getattr(existing_cls, attr)
                for field in obj:
                    if field not in old_obj:
                        print(f"While patching {existing_cls}, __globals__.{field} not in old")
                        continue
                    if obj[field] != old_obj[field]:
                        print(f"While patching {existing_cls}, __globals__.{field} differs")
                for field in old_obj:
                    if field not in obj:
                        print(f"While patching {existing_cls}, __globals__.{field} not in new")
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
