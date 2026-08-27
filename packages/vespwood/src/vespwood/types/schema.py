from typing import TypeAlias

SchemaObject= dict # TODO: Change to TypedDict

SchemaInfo: TypeAlias = SchemaObject | str

SchemasList = list[SchemaInfo]