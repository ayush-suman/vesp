from .file import File
from .image import Image
from .structured import Structured
from .tool_call import ToolCall

type Block = str | Structured | ToolCall | Image | File