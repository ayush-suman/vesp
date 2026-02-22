import copy
import json
from typing import Any

from vespwood.schematic import Tool


class ToolCall:
    __slots__ = "_id", "_name", "_arguments", "_result"

    _id: str
    _name: str
    _arguments: dict[str, Any]
    _result: Any

    @property
    def id(self) -> str:
        return self._id or f"id_{hash(self)}"
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def arguments(self) -> dict[str, Any]:
        return self._arguments
    
    @property
    def result(self) -> Any:
        return self._result

    def __init__(self, *, id: str | None = None, name: str, arguments: dict[str, Any], result: Any = None):
        self._id = id
        self._name = name
        self._arguments = arguments
        self._result = result


    def add_result(self, result: Any):
        if self.result:
           raise ValueError("Result already set for tool", self._name) 
        self._result = result


    def load_with_result(self, *tools: Tool):
        for tool in tools:
            if tool.name == self._name:
                self._result = tool(**self._arguments)
                return
            
    @property
    def json(self):
        if self.result:
            return {"id": self.id, "name": self.name, "arguments": self.arguments, "result": self.result }
        return {"id": self.id, "name": self.name, "arguments": self.arguments }
    

    def __str__(self):
        return json.dumps(self.json, indent=2)
    
    
    def __repr__(self):
        return json.dumps(self.json, indent=2)
    

    def copy(self):
        return ToolCall(
            id=self.id,
            name=self.name,
            arguments=self._arguments.copy(),
            output=copy(self.result) if self.result is not None else None
        )
    
    def __copy__(self):
        return self.copy()