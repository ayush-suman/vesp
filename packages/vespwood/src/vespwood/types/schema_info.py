from typing import TypeAlias

SchemaObject= dict # TODO: Change to TypedDict

SchemaInfo: TypeAlias = SchemaObject | str

SchemaList = list[SchemaInfo]