
def record(type, *args):
    pass

def patch(existing_cls):
    def decorator(new_cls):
        for attr in dir(new_cls):
            obj = getattr(new_cls, attr)
            # This is a cute hack to get the `function` class
            if isinstance(obj, type(decorator)):
                setattr(existing_cls, attr, obj)
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