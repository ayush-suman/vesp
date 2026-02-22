import importlib

def __getattr__(name):
    try:
        module = importlib.import_module("vespwood_anthropic")
        return getattr(module, name)
    except ImportError:
        raise ImportError(
            "The 'vespwood-anthropic' package is required for this feature. "
            "Please install it using: pip install vesp[anthropic]"
        )