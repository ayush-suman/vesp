import importlib
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from vespwood_openai import OpenAIChatCompletionGenerator, OpenAIResponsesGenerator
    
def __getattr__(name):
    try:
        # We dynamically load the partner package only when needed
        module = importlib.import_module("vespwood_openai")
        return getattr(module, name)
    except ImportError:
        raise ImportError(
            "The 'vespwood-openai' package is required for this feature. "
            "Please install it using: pip install vesp[openai]"
        )