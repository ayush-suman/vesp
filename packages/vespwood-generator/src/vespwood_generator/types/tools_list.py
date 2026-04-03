from typing import TypeAlias

ToolObject: TypeAlias = dict # TODO: Change to TypedDict

ToolsList: TypeAlias = list[ToolObject | str]