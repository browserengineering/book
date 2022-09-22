
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
