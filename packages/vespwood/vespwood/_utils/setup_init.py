import inspect
from typing import get_type_hints


def setup_init(cls):
        for c in cls.__mro__:
            if c is not object:
                if "__init__" in c.__dict__:
                    return cls
        hints = get_type_hints(cls, include_extras=True)
        names = list(hints.keys())

        def __init__(self, **kwargs):
            for n in names:
                if n in kwargs:
                    setattr(self, n, kwargs.pop(n))
                else:
                    raise TypeError(f"Missing required argument: {n}")
            if kwargs:
                raise TypeError(f"Unexpected argument(s): {', '.join(kwargs)}")
            
        params = [inspect.Parameter("self", inspect.Parameter.POSITIONAL_ONLY)]
        for n in names:
            ann = hints.get(n, inspect._empty)
            params.append(inspect.Parameter(n, inspect.Parameter.KEYWORD_ONLY, annotation=ann))
        __init__.__signature__ = inspect.Signature(params)
        
        cls.__init__ = __init__
        return cls