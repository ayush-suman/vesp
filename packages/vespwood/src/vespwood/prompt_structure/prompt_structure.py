from __future__ import annotations
import copy
import uuid

from typing import Any, overload
from dataclasses import dataclass
from ._format_object import FormatInt, FormatList, FormatKeys, to_format_object
from vespwood_generator import Message

from vespwood.tag import (
    Tag
)
from vespwood.types import (
    Params,
    SchemaList, 
    ToolsList, 
    HooksList, 
    ValidatorsList, 
    Saves
)
from vespwood.parse_expr import parse_exprs, parse_dict
from vespwood.match import match
from vespwood.expression import Expression
from vespwood.logic import Logic
from vespwood.prompt import Prompt



PromptStructureDataUnit = dict["str, PromptStructureData | str"]
PromptStructureData = list["PromptStructureDataUnit | str"]


class PromptStructure:
    @overload
    def __init__(
        self,
        id: str,
        *,
        prompt_list: list[Prompt | PromptStructure | str],
        name: str | None = None,
        description: str | None = None,
        schemas: SchemaList | None = None,
        tools: ToolsList | None = None,
        hooks: HooksList | None = None,
        validators: ValidatorsList | None = None,
        
    ): ...
    @overload
    def __init__(
        self,
        id: str,
        *,
        iterator: str, 
        prompt_list: list[Prompt | PromptStructure | str],
        initial: list[Prompt | PromptStructure | str] | None = None,
        name: str | None = None,
        description: str | None = None,
        schemas: SchemaList | None = None,
        tools: ToolsList | None = None,
        hooks: HooksList | None = None,
        validators: ValidatorsList | None = None,
        iter_key: str | None = None,
        index_key: str | None = None,
        params: Params | None = None
    ): ...
    @overload
    def __init__(
        self,
        id: str,
        *,
        while_key: str,
        prompt_list: list[Prompt | PromptStructure | str],
        name: str | None = None,
        description: str | None = None,
        schemas: SchemaList | None = None,
        tools: ToolsList | None = None,
        hooks: HooksList | None = None,
        validators: ValidatorsList | None = None,
        initial: list[Prompt | PromptStructure | str] | None = None,
        match: str | int | bool | dict | Logic | Expression | None = None,
        index_key: str | None = None,
        params: Params | None = None
    ): ...
    @overload
    def __init__(
        self,
        id: str,
        *,
        if_key: str,
        prompt_list: list[Prompt | PromptStructure | str],
        else_list: list[Prompt | PromptStructure | str],
        name: str | None = None,
        description: str | None = None,
        schemas: SchemaList | None = None,
        tools: ToolsList | None = None,
        hooks: HooksList | None = None,
        validators: ValidatorsList | None = None,
        match: str | int | bool | dict | Logic | Expression | None = None,
        params: Params | None = None
    ): ...
    @overload
    def __init__(
        self,
        id: str,
        *,
        cases: list[PromptStructure | str],
        prompt_list: list[Prompt | PromptStructure | str],
        name: str | None = None,
        description: str | None = None,
        schemas: SchemaList | None = None,
        tools: ToolsList | None = None,
        hooks: HooksList | None = None,
        validators: ValidatorsList | None = None,
        switch: str | None = None, 
        params: Params | None = None
    ): ...
    @overload
    def __init__(
        self,
        id: str,
        *,
        match: str | int | bool | dict | Logic | Expression | None,
        prompt_list: list[Prompt | PromptStructure | str],
        name: str | None = None,
        description: str | None = None,
        schemas: SchemaList | None = None,
        tools: ToolsList | None = None,
        hooks: HooksList | None = None,
        validators: ValidatorsList | None = None,
        params: Params | None = None
    ): ...
    def __init__(
        self,
        id: str,
        *,
        prompt_list: list[Prompt | PromptStructure | str],
        iterator: str | None = None,
        while_key: str | None = None,
        if_key: str | None = None,
        cases: list[PromptStructure | str] | None = None,
        match: str | int | bool | dict | Logic | Expression | None = None,
        else_list: list[Prompt | PromptStructure | str] | None = None,
        initial: list[Prompt | PromptStructure | str] | None = None,
        iter_key: str | None = None,
        index_key: str | None = None,
        switch: str | None = None,
        name: str | None = None,
        description: str | None = None,
        schemas: SchemaList | None = None,
        tools: ToolsList | None = None,
        hooks: HooksList | None = None,
        validators: ValidatorsList | None = None,
        params: Params | None = None
        
    ):
        self._prompt_list = prompt_list
        self._id = id
        self._name = name
        self._description = description
        self._schemas = schemas
        self._tools = tools
        self._hooks = hooks
        self._validators = validators

        self._iterator = iterator
        self._iter_key = iter_key
        self._index_key = index_key
        
        self._while = while_key

        self._initial = initial
        
        self._if = if_key
        self._else = else_list

        if isinstance(match, str):
            match = parse_exprs(match)
        elif isinstance(match, dict):
            match = parse_dict(match)
        self._match: str | int | bool | Logic | Expression = match
        
        self._switch = switch
        self._cases = cases

        self._params = params


    def match(self, value: Any, format_keys: FormatKeys) -> bool:
        if isinstance(self._match, str) or isinstance(self._match, Expression) or isinstance(self._match, Logic):
            if self._params:
                mapping = format_keys.get_params(self._params)
                self._match = self._match.format_map(mapping)
        result = match(value, self._match)
        return result
    

    @staticmethod
    def to_prompt_list(data: PromptStructureData) -> list[Prompt | PromptStructure]:
        prompt_list = []
        for prompt in data:
            if any(key in prompt for key in ("iterator", "in", "when", "switch", "if", "while", "structure")):
                prompt_list.append(PromptStructure.load_from_dict(prompt))
            else:
                prompt_list.append(Prompt.load_from_dict(prompt))
        return prompt_list
    

    @staticmethod
    def _load_iterator(data: PromptStructureDataUnit) -> PromptStructure:
        name = data.get("name")
        description = data.get("description"), 
        schemas = data.get("schemas"), 
        tools = data.get("tools")
        iterator = data.get("iterator") or data.get("in")
        iter_key: str = data.get("for") or data.get("iter_key", "it")
        index_key: str = data.get("index_key", "index")

        initial = data.get("initial")
        if initial and not isinstance(initial, list): initial = [initial]

        structure = data["structure"]
        if not isinstance(structure, list): structure = [structure]

        params = data.get("params")

        return PromptStructure(
            uuid.uuid4().hex,
            iterator=iterator, 
            prompt_list=PromptStructure.to_prompt_list(structure), 
            initial=PromptStructure.to_prompt_list(initial) if initial else None,
            name=name, 
            description=description, 
            schemas=schemas, 
            tools=tools,
            iter_key=iter_key, 
            index_key=index_key,
            params=params
        )


    @staticmethod
    def _load_case(data: PromptStructureDataUnit) -> PromptStructure:
        name = data.get("name")
        description = data.get("description"), 
        schemas = data.get("schemas"), 
        tools = data.get("tools")
        matchkey = data.get("match") or data.get("case")

        structure = data["structure"]
        if not isinstance(structure, list): structure = [structure]

        params = data.get("params")

        return PromptStructure(
            uuid.uuid4().hex,
            match=matchkey,
            prompt_list=PromptStructure.to_prompt_list(structure),
            name=name,
            description=description,
            schemas=schemas,
            tools=tools,
            params=params
        )
        

    @staticmethod
    def _load_switch(data: PromptStructureDataUnit) -> PromptStructure:
        name = data.get("name")
        description = data.get("description"), 
        schemas = data.get("schemas"), 
        tools = data.get("tools")
        switch = data.get("switch") or data.get("when")
        params = data.get("params")
        cases = data["cases"]

        default = data.get("default", [])
        if not isinstance(default, list): default = [default]

        return PromptStructure(
            uuid.uuid4().hex,
            switch=switch, 
            prompt_list=PromptStructure.to_prompt_list(default), 
            cases=list(map(lambda case: PromptStructure._load_case(case), cases)), 
            name=name, 
            description=description, 
            schemas=schemas, 
            tools=tools,
            params=params
        )
        

    @staticmethod
    def _load_if(data: PromptStructureDataUnit) -> PromptStructure:
        name = data.get("name")
        description = data.get("description"), 
        schemas = data.get("schemas"), 
        tools = data.get("tools")
        ifkey = data["if"]
        matchkey = data.get("match")

        else_list = data.get("else", [])
        if not isinstance(else_list, list): else_list = [else_list]

        then = data.get("then") or data.get("structure")
        if not isinstance(then, list): then = [then]

        params = data.get("params")

        return PromptStructure(
            uuid.uuid4().hex,
            ifkey=ifkey, 
            structure=PromptStructure.to_prompt_list(then),
            else_list=PromptStructure.to_prompt_list(else_list), 
            match=matchkey,
            name=name,
            description=description,
            schemas=schemas,
            tools=tools,
            params=params,
        )


    @staticmethod
    def _load_while(data: PromptStructureDataUnit) -> PromptStructure:
        name = data.get("name")
        description = data.get("description"), 
        schemas = data.get("schemas"), 
        tools = data.get("tools")
        whilekey = data["while"]
        matchkey = data.get("match")
        index_key: str = data.get("index_key", "index")

        initial = data.get("initial")
        if initial and not isinstance(initial, list): initial = [initial]

        structure = data.get("then") or data["structure"]
        if not isinstance(structure, list): structure = [structure]

        params = data.get("params")

        return PromptStructure(
            uuid.uuid4().hex,
            whilekey=whilekey,
            prompt_list=PromptStructure.to_prompt_list(structure),
            initial=PromptStructure.to_prompt_list(initial) if initial is not None else None,
            index_key=index_key,
            match=matchkey,
            name=name,
            description=description,
            schemas=schemas,
            tools=tools,
            params=params,
        )

    @staticmethod
    def load_from_dict(unit: PromptStructureDataUnit) -> PromptStructure:
        if unit.get("iterator") or unit.get("in"):
            self = PromptStructure._load_iterator(unit)
        elif unit.get("when") or unit.get("switch"):
            self = PromptStructure._load_switch(unit)
        elif unit.get("if"):
            self = PromptStructure._load_if(unit)
        elif unit.get("while"):
            self = PromptStructure._load_while(unit)
        else:
            if not "structure" in unit:
                raise SyntaxError("No valid schema found in the dict to load PromptStructure. It should have either iterator, switch, if, while or structure key defined")
            self = PromptStructure.to_prompt_list(unit["structure"])
        self._name = unit.get("name")
        self._description = unit.get("description")
        self._schemas = unit.get("schemas")
        self._tools = unit.get("tools")
        self._hooks = unit.get("hooks")
        self._validators = unit.get("validators")
        return self


    @staticmethod
    def load_from_file(file_name: str) -> PromptStructure:
        with open(file_name, "r") as file:
            structure = None
            # Load from JSON file
            if file_name.endswith(".json"):
                import json
                structure = json.load(file)
            # Load from YAML file
            elif file_name.endswith(".yaml"):
                try:
                    import yaml # type: ignore
                except:
                    raise ImportError("To load from prompt structure from a yaml file, you need to install the optional dependency yaml. Try running 'pip install vespwood[yaml]'") from None
                structure = yaml.safe_load(file)

            if isinstance(structure, dict): 
                if "name" not in structure:
                    structure["name"] = file_name.split(".")[0]
                return PromptStructure.load_from_dict(structure)
            elif isinstance(structure, list):
                return PromptStructure(
                    PromptStructure.to_prompt_list(structure),
                    name=file_name.split(".")[0]
                )

    @property
    def id(self) -> str:
        return self._id


    @property
    def name(self) -> str | None:
        return self._name
    
    
    @property
    def description(self) -> str | None:
        return self._description
    
    
    @property
    def schemas(self) -> SchemaList | None:
        return self._schemas


    @property
    def prompt_list(self) -> list[Prompt | PromptStructure]:
        return self._prompt_list
    
    @property
    def tools(self) -> ToolsList | None:
        return self._tools
    
    
    @property
    def hooks(self) -> HooksList | None:
        return self._hooks
    

    @property
    def validators(self) -> ValidatorsList | None:
        return self._validators
    

    @property
    def params(self) -> Params | None:
        return self._params

    
    @property
    def iterator(self):
        return self._iterator


    @property
    def iter_key(self):
        return self._iter_key


    @property
    def index_key(self):
        return self._index_key


    @property
    def initial(self):
        return self._initial


    @property
    def while_key(self):
        return self._while


    @property
    def if_key(self):
        return self._if


    @property
    def match_key(self):
        return self._match


    @property
    def switch(self):
        return self._switch


    @property
    def cases(self):
        return self._cases


    @property
    def is_iterator(self) -> bool:
        return self._iterator is not None
    

    @property
    def is_while(self) -> bool:
        return self._while is not None
    

    @property
    def has_initial(self) -> bool:
        return self._initial is not None
    

    @property
    def is_switch(self) -> bool: 
        return self._switch is not None
    

    @property
    def is_if(self) -> bool:
        return self._if is not None


    @property
    def normalized(self) -> PromptStructure:
        return PromptStructure(prompt_list=list(self))


    def copy(self) -> PromptStructure:
        new_initial = self._initial.copy() if self.has_initial else None
        new_else = self._else.copy() if self._else else None
        new_case = [] if self.is_switch else None
        new_params = self._params.copy() if self._params else None

        if self.is_switch:
            for prompt_structure in self._cases:
                new_case.append(prompt_structure.copy())
        
        return PromptStructure(
            self._id,
            prompt_list=[p.copy() for p in self],
            name=self._name,
            description=self._description,
            schemas=self._schemas.copy() if self._schemas else None,
            tools=self._tools.copy() if self._tools else None,
            hooks=self._hooks.copy() if self._hooks else None,
            validators=self._validators.copy() if self._validators else None,
            iterator=copy.copy(self._iterator),
            iter_key=copy.copy(self._iter_key), 
            index_key=copy.copy(self._index_key),
            initial=new_initial,
            while_key=copy.copy(self._while),
            if_key=copy.copy(self._if),
            match=copy.copy(self._match),
            else_list=new_else,
            switch=copy.copy(self._switch), 
            cases=new_case,
            params=new_params
        )
    
    
    def __copy__(self):
        return self.copy()
    
    
    def indexed(self, idx: int) -> "PromptStructure":
        new_self = self.copy()
        new_self.prompt_list.clear()

        for prompt in self.prompt_list:
            if isinstance(prompt, PromptStructure):
                new_self.prompt_list.append(prompt.indexed(idx))
            else:
                prompt = prompt.indexed(idx)
                new_self.prompt_list.append(prompt.copy())
        return new_self

        
    # TODO: Change FormatKeys to CompletedArgs (alias of dict[str, Any])
    def get_usables(self, format_keys: FormatKeys, /, message_id_map: dict[str, Prompt] = {}) -> tuple[list[Message], FormatKeys, Prompt | None]:
        prompt_structure = self.copy()
        msgs: list[Message] = []

        def get_from_format_key(key: str):
            f = format_keys
            key_parts = key.split(".")
            for part in key_parts:
                f = f[part]
            return f

        # Iterator
        if prompt_structure.is_iterator:
            if prompt_structure._params:
                mapping = format_keys.get_params(prompt_structure._params)
                prompt_structure._iterator = prompt_structure._iterator.format_map(mapping)
           
            iterator: FormatList = get_from_format_key(prompt_structure._iterator)
            iter_key = prompt_structure._iter_key
            index_key = prompt_structure._index_key
            for index, value in enumerate(iterator):
                structure = None
                if prompt_structure.has_initial and index == 0:
                    structure = prompt_structure._initial
                else:
                    structure = prompt_structure.normalized
                indexed_structure = structure.indexed(index)
                extra_keys = { iter_key : value, index_key: FormatInt(index) }
                format_keys = format_keys.copy_with(extra_keys)
                prompts, format_keys, awaited_prompt = indexed_structure.get_usables(format_keys, message_id_map=message_id_map)
                msgs.extend(prompts)
                if awaited_prompt: return msgs, format_keys, awaited_prompt
            return msgs, format_keys, None

        # Switch
        elif prompt_structure.is_switch:
            if prompt_structure._params:
                mapping = format_keys.get_params(prompt_structure._params)
                prompt_structure._switch = prompt_structure._switch.format_map(mapping)
            case_data = get_from_format_key(prompt_structure._switch)
            for case in prompt_structure._cases:
                if case.match(case_data, format_keys):
                    return case.get_usables(format_keys, message_id_map=message_id_map)
            normalised_structure = prompt_structure.normalized
            return normalised_structure.get_usables(format_keys, message_id_map=message_id_map)
            
        # If
        elif prompt_structure.is_if:
            if prompt_structure._params:
                mapping = format_keys.get_params(prompt_structure._params)
                prompt_structure._if = prompt_structure._if.format_map(mapping)
            case_data = get_from_format_key(prompt_structure._if)
            if prompt_structure.match(case_data, format_keys):
                return prompt_structure._then.get_usables(format_keys, message_id_map=message_id_map)
            normalised_structure = prompt_structure.normalized
            return normalised_structure.get_usables(format_keys, message_id_map=message_id_map)
        
        # While
        elif prompt_structure.is_while:
            if prompt_structure._params:
                mapping = format_keys.get_params(prompt_structure._params)
                prompt_structure._while = prompt_structure._while.format_map(mapping)
            case_data = get_from_format_key(prompt_structure._while)
            index_key = prompt_structure._index_key
            index = 0
            while prompt_structure.match(case_data.extras.get(f"{self._id}#{index}") or case_data.normalized, format_keys):
                structure = None
                if prompt_structure.has_initial and index == 0:
                    structure = prompt_structure._initial
                else:
                    structure = prompt_structure.normalized
                indexed_structure = structure.indexed(index)
                extra_keys = { index_key: FormatInt(index) }
                format_keys = format_keys.copy_with(extra_keys)
                prompts, format_keys, awaited_prompt = indexed_structure.get_usables(format_keys, message_id_map=message_id_map)
                msgs.extend(prompts)

                if not f"{self._id}#{index}" in case_data.extras:
                    case_data.extras[f"{self._id}#{index}"] = case_data.normalized
                
                if awaited_prompt: return msgs, format_keys, awaited_prompt
                index += 1
            return msgs, format_keys, None

        # Normal
        for prompt in prompt_structure.prompt_list:
            if isinstance(prompt, PromptStructure):
                prompts, format_keys, awaited_prompt = prompt.get_usables(format_keys, message_id_map=message_id_map)
                msgs.extend(prompts)
                if awaited_prompt: return msgs, format_keys, awaited_prompt
            else:
                if prompt.params:
                    mapping = format_keys.get_params(prompt._params)
                    prompt = prompt.format_map(mapping)
                if prompt.id in message_id_map:
                    message = message_id_map[prompt.id]
                    prompt.update_content(message)
                if prompt.is_awaited:
                    return msgs, format_keys, prompt
                msgs.append(prompt)

        return msgs, format_keys, None

    @property
    def json(self) -> dict:
        data = {}
        for key in ("iterator", "in", "when", "switch", "if", "while", "structure"):
            if hasattr(self, key) and getattr(self, key) is not None:
                data[key] = getattr(self, key)
        if self.is_iterator: data["structure"] = list(map(lambda p: p.json, self))
        elif self.is_switch: data["default"] = list(map(lambda p: p.json, self)) 
        elif self.is_while: data["structure"] = list(map(lambda p: p.json, self))
        elif self.is_if:
            data["then"] = list(map(lambda p: p.json, self._then))
            data["else"] = list(map(lambda p: p.json, self))
        else: data["structure"] = list(map(lambda p: p.json, self))
        return data


    def __repr__(self) -> str:
        data = self.json
        import json
        return json.dumps(data, indent=2)
        
        
    def __str__(self) -> str:
        data = self.json
        import json
        return json.dumps(data, indent=2)