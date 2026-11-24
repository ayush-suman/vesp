from typing import TypeAlias

from .file import File
from .image import Image
from .tool_call import ToolCall
from .thinking import Thinking


Block: TypeAlias = str | ToolCall | Image | File | Thinking