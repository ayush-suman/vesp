from .image import Image
from .structured import Structured
from .tool_call import ToolCall
from .file import File


type Block = str | Structured | ToolCall | Image | File