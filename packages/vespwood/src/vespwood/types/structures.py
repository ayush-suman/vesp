from typing import TypeAlias

StructureObject = dict # TODO: Change to TypedDict

StructureInfo: TypeAlias = StructureObject | str

StructuresList = list[StructureInfo]