from typing import TypeAlias

HookObject = dict # TODO: Change to TypedDict

HookInfo: TypeAlias = HookObject | str

HooksList = list[HookInfo]