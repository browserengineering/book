
def record(type, *args):
    pass

def patch(existing_cls):
    def decorator(new_cls):
        for attr in dir(new_cls):
            obj = getattr(new_cls, attr)
            # Copies over all methods and all fields of a function object
            # Uses a cute hack to get the `function` class.
            if isinstance(obj, type(decorator)) \
               or attr in ["__code__", "__globals__", "__module__",
                           "__defaults__", "__closure__", "__annotations"]:
                setattr(existing_cls, attr, obj)
        return existing_cls
    return decorator

def js_hide(f):
    return f
