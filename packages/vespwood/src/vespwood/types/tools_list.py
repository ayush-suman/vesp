from typing import TypeAlias

ToolObject = dict # TODO: Change to TypedDict

ToolInfo: TypeAlias = ToolObject | str

ToolsList = list[ToolInfo]