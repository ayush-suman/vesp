from __future__ import annotations
import copy
import uuid

from typing import Any, Self, TypeAlias

from vespwood_generator import Tag, Message

from vespwood.types import (
    Params,
    SchemaInfo, 
    ToolsList, 
    HooksList, 
    ValidatorsList, 
    Saves
)
from vespwood.parse_expr import parse_exprs, parse_dict
from vespwood.match import match
from vespwood.expression import Expression
from vespwood.logic import Logic
from vespwood.format_object import FormatKeys
from vespwood.message import Prompt



PromptStructureDataUnit: TypeAlias = "dict[str, PromptStructureData | str]"
PromptStructureData: TypeAlias = "list[PromptStructureDataUnit | str]"

PromptLike: TypeAlias = "Prompt | PromptStructure"


class PromptStructure(list[PromptLike]):

    def __init__(self, 
                prompt_list: list[Prompt | PromptStructure], 
                *,
                id: str | None = None,
                name: str | None = None,
                description: str | None = None,
                schemas: list[SchemaInfo] | None = None,
                tools: ToolsList | None = None,
                hooks: HooksList | None = None,
                validators: ValidatorsList | None = None,
                iterator: str | None = None, 
                iter_key: str | None = None,
                index_key: str | None = None,
                co_iterators: list[str] | None = None, 
                co_iter_keys: list[str | None] | None = None,
                default_co_iter_values: list[str | None] | None = None,
                initial: PromptStructure | None = None,
                whilekey: str | None = None,
                ifkey: str | None = None,
                match: str | int | bool | dict | Logic | Expression | None = None,
                then: PromptStructure | None = None,
                switch: str | None = None, 
                cases: list[PromptStructure] | None = None,
                params: Params | None = None):
        self.extend(prompt_list)
        self._id = id or uuid.uuid4().hex
        self._name = name,
        self._description = description,
        self._schemas = schemas
        self._tools = tools
        self._hooks = hooks
        self._validators = validators
        self._iterator = iterator
        self._iter_key = iter_key
        self._index_key = index_key
        self._co_iterators = co_iterators
        self._co_iter_keys = co_iter_keys
        self._default_co_iter_values = default_co_iter_values
        self._initial = initial
        self._while = whilekey
        self._if = ifkey
        if isinstance(match, str):
            match = parse_exprs(match)
        elif isinstance(match, dict):
            match = parse_dict(match)
        self._match: str | int | bool | Logic | Expression = match
        self._then = then
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
    

    @classmethod
    def __load_iterator__(cls, data: PromptStructureDataUnit):
        iterator = data.get("iterator") or data.get("in")
        iter_key: str = data.get("for") or data.get("iter_key", "it")
        index_key: str = data.get("index_key", "index")
        co_iterators: list[str] | None = data.get("co_iterators")
        co_iter_keys: list[str] | None = data.get("co_iter_keys", 
                                                              [f"co_iter_{idx}_value" for idx in range(len(co_iterators))] 
                                                              if co_iterators else None)
        default_co_iter_values: list[str | None] | None = data.get("default_co_iter_values")
        initial = data.get("initial")
        if initial is not None and not isinstance(initial, list): initial = [initial]
        structure = data["structure"]
        if not isinstance(structure, list): structure = [structure]
        params = data.get("params")
        return cls(
            PromptStructure.load_from_structure(structure), 
            iterator=iterator, 
            iter_key=iter_key, 
            index_key=index_key,
            co_iterators=co_iterators, 
            co_iter_keys=co_iter_keys, 
            default_co_iter_values=default_co_iter_values, 
            initial=PromptStructure.load_from_structure(initial),
            params=params
        )


    @classmethod
    def __load_case__(cls, data: PromptStructureDataUnit, params: list[str] | None = None):
        matchkey = data.get("match") or data.get("case")
        structure = data["structure"]
        if not isinstance(structure, list): structure = [structure]
        if p := data.get("params"):
            if params is None: params = {}
            params.extend(p)
        return cls(
            PromptStructure.load_from_structure(structure),
            match=matchkey,
            params=params
        )
        

    @classmethod
    def __load_switch__(cls, data: PromptStructureDataUnit):
        switch = data.get("switch") or data.get("when")
        params = data.get("params")
        cases = list(map(lambda case: PromptStructure.__load_case__(case, copy.copy(params)), data["cases"]))
        default = data.get("default", [])
        if not isinstance(default, list): default = [default]
        return cls(
            PromptStructure.load_from_structure(default), 
            switch=switch, cases=cases, params=params
        )
        

    @classmethod
    def __load_if__(cls, data: PromptStructureDataUnit):
        ifkey = data["if"]
        matchkey = data.get("match")
        structure = data.get("else", [])
        if not isinstance(structure, list):
            structure = [structure]
        then = data.get("then") or data.get("structure")
        if not isinstance(then, list): then = [then]
        params = data.get("params")
        return cls(
            PromptStructure.load_from_structure(structure), 
            ifkey=ifkey, 
            match=matchkey,
            then=PromptStructure.load_from_structure(then),
            params=params
        )


    @classmethod
    def __load_while__(cls, data: PromptStructureDataUnit):
        whilekey = data["while"]
        matchkey = data.get("match")
        initial = data.get("initial")
        index_key: str = data.get("index_key", "index")
        if initial:
            if not isinstance(initial, list):
                initial = [initial]
        structure = data["structure"]
        if not isinstance(structure, list): structure = [structure]
        params = data.get("params")
        return cls(
            PromptStructure.load_from_structure(structure),
            whilekey=whilekey,
            index_key=index_key,
            match=matchkey,
            initial=PromptStructure.load_from_structure(initial) if initial is not None else None,
            params=params
        )

    @classmethod
    def load_from_dict(cls, unit: PromptStructureDataUnit):
        if unit.get("iterator") or unit.get("in"):
            self = PromptStructure.__load_iterator__(unit)
        elif unit.get("when") or unit.get("switch"):
            self = PromptStructure.__load_switch__(unit)
        elif unit.get("if"):
            self = PromptStructure.__load_if__(unit)
        elif unit.get("while"):
            self = PromptStructure.__load_while__(unit)
        else:
            if not "structure" in unit:
                raise SyntaxError("No valid schema found in the dict to load PromptStrucutre. It should have either iterator, switch, if, while or structure key defined")
            self = PromptStructure.load_from_structure(unit["structure"])
        self._name = unit.get("name")
        self._description = unit.get("description")
        self._schemas = unit.get("schemas")
        self._tools = unit.get("tools")
        self._hooks = unit.get("hooks")
        self._validators = unit.get("validators")
        return self


    @classmethod
    def load_from_structure(
        cls, 
        data: PromptStructureData, 
        *, 
        name: str | None = None, 
        description: str | None = None,
        schemas: list[SchemaInfo] | None = None,
        tools: ToolsList | None = None
    ) -> Self:
        self = cls([], name=name, description=description, schemas=schemas, tools=tools)
        for prompt in data:
            if any(key in prompt for key in ("iterator", "in", "when", "switch", "if", "while", "structure")):
                self.append(PromptStructure.load_from_dict(prompt))
            else:
                self.append(Prompt.load_from_dict(prompt))
        return self


    @classmethod
    def load_from_file(cls, file_name: str) -> Self:
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
                return PromptStructure.load_from_dict(structure)
            elif isinstance(structure, list):
                return PromptStructure.load_from_structure(
                    structure, 
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
    def schemas(self) -> list[SchemaInfo] | None:
        return self._schemas
    
    
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
    def co_iterators(self):
        return self._co_iterators


    @property
    def co_iter_keys(self):
        return self._co_iter_keys


    @property
    def default_co_iter_values(self):
        return self._default_co_iter_values


    @property
    def initial(self):
        return self._initial


    @property
    def whilekey(self):
        return self._while


    @property
    def ifkey(self):
        return self._if


    @property
    def matchkey(self):
        return self._match


    @property
    def then(self):
        return self._then


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
        return self.is_iterator and self._initial is not None
    

    @property
    def is_switch(self) -> bool: 
        return self._switch
    

    @property
    def is_if(self) -> bool:
        return self._if is not None


    @property
    def normalised(self) -> PromptStructure:
        return PromptStructure(list(self))


    def copy(self) -> PromptStructure:
        new_co_iterators = self._co_iterators.copy() if self._co_iterators else None
        new_co_iter_keys = self._co_iter_keys.copy() if self._co_iter_keys else None
        new_default_co_iter_values = self._default_co_iter_values.copy() if self._default_co_iter_values else None
        new_initial = self._initial.copy() if self.has_initial else None
        new_then = self._then.copy() if self._then else None
        new_case = [] if self.is_switch else None
        new_params = self._params.copy() if self._params else None

        if self.is_switch:
            for prompt_structure in self._cases:
                new_case.append(prompt_structure.copy())
        
        return PromptStructure(
            [p.copy() for p in self],
            id=self._id, 
            name=self._name,
            description=self._description,
            schemas=self._schemas.copy() if self._schemas else None,
            tools=self._tools.copy() if self._tools else None,
            hooks=self._hooks.copy() if self._hooks else None,
            validators=self._validators.copy() if self._validators else None,
            iterator=copy.copy(self._iterator),
            iter_key=copy.copy(self._iter_key), 
            index_key=copy.copy(self._index_key),
            co_iterators=new_co_iterators,
            co_iter_keys=new_co_iter_keys,
            default_co_iter_values=new_default_co_iter_values,
            initial=new_initial,
            whilekey=copy.copy(self._while),
            ifkey=copy.copy(self._if),
            match=copy.copy(self._match),
            then=new_then,
            switch=copy.copy(self._switch), 
            cases=new_case,
            params=new_params
        )
    
    
    def __copy__(self):
        return self.copy()
    
    
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
    
    
    def indexed(self, idx: int) -> "PromptStructure":
        new_self = self.copy()
        new_self.clear()

        new_self._then = new_self._then.indexed(idx) if new_self._then else new_self._then
        new_self._cases = list(map(lambda case: case.indexed(idx), new_self._cases)) if new_self._cases else new_self._cases
        new_self._initial = new_self._initial.indexed(idx) if new_self._initial else new_self._initial

        for prompt in self:
            if isinstance(prompt, PromptStructure):
                new_self.append(prompt.indexed(idx))
            else:
                if prompt.is_tagged:
                    prompt @= prompt.tag.indexed(idx)
                    new_self.append(prompt.copy())
                else:
                    new_self.append(prompt.copy())
        return new_self
        
    # TODO: Change FormatKeys to CompletedArgs (alias of dict[str, Any])
    def get_usables(self, format_keys: FormatKeys, /, tagged_messages: dict[str, Message] = {}) -> tuple[list[Prompt], FormatKeys, Tag | None, SchemaInfo | None, ToolsList | None, HooksList | None, ValidatorsList | None, Saves | None]:
        prompt_structure = self.copy()
        msgs: list[Prompt] = []
        allNone = ([None] * 6)

        # Iterator
        if prompt_structure.is_iterator:
            if prompt_structure._params:
                mapping = format_keys.get_params(prompt_structure._params)
                prompt_structure._iterator = prompt_structure._iterator.format_map(mapping)
                prompt_structure._co_iterators = [co_iter.format_map(mapping) for co_iter in (prompt_structure._co_iterators or [])]
            iterator = format_keys[prompt_structure._iterator]
            iter_key = prompt_structure._iter_key
            index_key = prompt_structure._index_key
            co_iterators = [format_keys[co_iter] for co_iter in (prompt_structure._co_iterators or [])]
            co_iter_keys = prompt_structure._co_iter_keys
            default_co_iter_values = prompt_structure._default_co_iter_values
            for index, value in enumerate(iterator):
                structure = None
                if prompt_structure.has_initial and index == 0:
                    structure = prompt_structure._initial
                else:
                    structure = prompt_structure.normalised
                indexed_structure = structure.indexed(index)
                extra_keys = { iter_key : value, index_key: index }
                for idx, co_iterator in enumerate(co_iterators):
                    if len(co_iterator) <= index or co_iterator[index] is None:
                        extra_keys.update({co_iter_keys[idx]: default_co_iter_values[idx] if default_co_iter_values else None})
                    else:
                        extra_keys.update({co_iter_keys[idx]: co_iterator[index]})
                format_keys = format_keys.copy_with_extra(**extra_keys)
                prompts, format_keys, tag, *rest = indexed_structure.get_usables(format_keys, tagged_messages=tagged_messages)
                msgs.extend(prompts)
                if tag: return msgs, format_keys, tag, *rest
            return msgs, format_keys, *allNone
        
        # Switch
        elif prompt_structure.is_switch:
            if prompt_structure._params:
                mapping = format_keys.get_params(prompt_structure._params)
                prompt_structure._switch = prompt_structure._switch.format_map(mapping)
            case_data = format_keys[prompt_structure._switch]
            for case in prompt_structure._cases:
                if case.match(case_data, format_keys):
                    return case.get_usables(format_keys, tagged_messages=tagged_messages)
            normalised_structure = prompt_structure.normalised
            return normalised_structure.get_usables(format_keys, tagged_messages=tagged_messages)
            
        # If
        elif prompt_structure.is_if:
            if prompt_structure._params:
                mapping = format_keys.get_params(prompt_structure._params)
                prompt_structure._if = prompt_structure._if.format_map(mapping)
            case_data = format_keys[prompt_structure._if]
            if prompt_structure.match(case_data, format_keys):
                return prompt_structure._then.get_usables(format_keys, tagged_messages=tagged_messages)
            normalised_structure = prompt_structure.normalised
            return normalised_structure.get_usables(format_keys, tagged_messages=tagged_messages)
        
        # While
        elif prompt_structure.is_while:
            if prompt_structure._params:
                mapping = format_keys.get_params(prompt_structure._params)
                prompt_structure._while = prompt_structure._while.format_map(mapping)
            case_data = format_keys[prompt_structure._while]
            index_key = prompt_structure._index_key
            index = 0
            while prompt_structure.match(format_keys.get(f"{prompt_structure._while}?{self._id}#{index}", case_data), format_keys):
                structure = None
                if prompt_structure.has_initial and index == 0:
                    structure = prompt_structure._initial
                else:
                    structure = prompt_structure.normalised
                indexed_structure = structure.indexed(index)
                extra_keys = { index_key: index }
                format_keys = format_keys.copy_with_extra(**extra_keys)
                prompts, format_keys, tag, *rest = indexed_structure.get_usables(format_keys, tagged_messages=tagged_messages)
                msgs.extend(prompts)
                if not f"{prompt_structure._while}?{self._id}#{index}" in format_keys:
                    format_keys[f"{prompt_structure._while}?{self._id}#{index}"] = case_data
                if tag: return msgs, format_keys, tag, *rest
                index += 1
            return msgs, format_keys, *allNone

        # Normal
        for prompt in prompt_structure:
            if isinstance(prompt, PromptStructure):
                prompts, format_keys, tag, *rest = prompt.get_usables(format_keys, tagged_messages=tagged_messages)
                msgs.extend(prompts)
                if tag: return msgs, format_keys, tag, *rest
            else:
                if prompt.params:
                    mapping = format_keys.get_params(prompt._params)
                    prompt = prompt.format_map(mapping)
                if prompt.is_tagged:
                    tag = prompt.tag
                    if tag in tagged_messages:
                        message = tagged_messages[tag]
                        prompt.update_message(message)
                    if prompt.response_awaited:
                        return msgs, format_keys, tag, prompt.schema, prompt.tools, prompt.hooks, prompt.validators, prompt.saves    
                msgs.append(prompt)

        return msgs, format_keys, *allNone