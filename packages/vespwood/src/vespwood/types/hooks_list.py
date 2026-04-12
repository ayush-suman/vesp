from typing import TypeAlias

HookObject: TypeAlias = dict # TODO: Change to TypedDict

HooksList: TypeAlias = list[HookObject | str]