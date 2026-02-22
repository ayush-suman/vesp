from __future__ import annotations
import uuid

from typing import Any, List, Dict, Self, TextIO

from vespwood._utils import parse_dict, parse_exprs, match
from vespwood.expression import Expression
from vespwood.logic import Logic
from vespwood.format_object import FormatKeys
from vespwood.message import Message, Prompt
from vespwood.tag import Tag
from vespwood.types.schema_info import SchemaInfo
from vespwood.types.tools_list import ToolsList
from vespwood.types.hooks_list import HooksList
from vespwood.types.validators_list import ValidatorsList
from vespwood.types.saves import Saves

type PromptStructureDataUnit = Dict[str, "PromptStructureData" | str]
type PromptStructureData = List[PromptStructureDataUnit | str] | PromptStructureDataUnit

type PromptLike = Prompt | PromptStructure

type Msgs = list[Prompt]

class PromptStructure(list[PromptLike]):
    def keys(self):
        return ["iterator", "iter_key", "co_iterators", "co_iter_keys", "default_co_iter_values", "initial", "while", "if", "match", "then", "switch", "cases"]
    
    
    def __getitem__(self, key):
        if key is int:
            return self[key]
        return getattr(self, f"_{key}")
    

    def __contains__(self, key):
        return key in self.keys()


    def __init__(self, 
                prompt_list: list[Prompt | PromptStructure], 
                *,
                id: str | None = None,
                iterator: str | None = None, 
                iter_key: str | None = None,
                co_iterators: list[str] | None = None, 
                co_iter_keys: list[str | None] | None = None,
                default_co_iter_values: list[str | None] | None = None,
                initial: PromptStructure | None = None,
                whilekey: str | None = None,
                ifkey: str | None = None,
                match: str | int | bool | dict | Logic | Expression | None = None,
                then: PromptStructure | None = None,
                switch: str | None = None, 
                cases: list[PromptStructure] | None = None):
        self.extend(prompt_list)
        self._id = id or uuid.uuid4().hex
        self._iterator = iterator
        self._iter_key = iter_key
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


    def match(self, value: Any, **format_keys) -> bool:
        match_val = self._match
        if isinstance(match_val, str) or isinstance(match_val, Expression) or isinstance(match_val, Logic):
            print(match_val, format_keys)
            match_val = match_val.format(**format_keys)
        result = match(value, match_val)
        return result
    

    @classmethod
    def load_iterator(cls, data: PromptStructureData):
        iterator = data.get("iterator") or data.get("in")
        iter_key: str = data.get("for") or data.get("iter_key", "it")
        co_iterators: list[str] | None = data.get("co_iterators")
        co_iter_keys: list[str] | None = data.get("co_iter_keys", 
                                                              [f"co_iter_{idx}_value" for idx in range(len(co_iterators))] 
                                                              if co_iterators else None)
        default_co_iter_values: list[str | None] | None = data.get("default_co_iter_values")
        initial = PromptStructure.load_from_dict(data["initial"]) if data.get("initial") else None
        structure = data["structure"]
        if not isinstance(structure, list):
            structure = [structure]
        return cls(
            PromptStructure.load_from_dict(structure), 
            iterator=iterator, 
            iter_key=iter_key, 
            co_iterators=co_iterators, 
            co_iter_keys=co_iter_keys, 
            default_co_iter_values=default_co_iter_values, 
            initial=initial
        )


    @classmethod
    def load_case(cls, data: PromptStructureData):
        matchkey = data.get("match") or data.get("case")
        structure = data["structure"]
        if not isinstance(structure, list):
            structure = [structure]
        return cls(
            PromptStructure.load_from_dict(structure),
            match=matchkey
        )
        

    @classmethod
    def load_switch(cls, data: PromptStructureData):
        switch = data.get("switch") or data.get("when")
        cases = list(map(PromptStructure.load_case, data["cases"]))
        default = data.get("default", [])
        if not isinstance(default, list):
            default = [default]
        return cls(
            PromptStructure.load_from_dict(default), 
            switch=switch, cases=cases
        )
        

    @classmethod
    def load_if(cls, data: PromptStructureData):
        ifkey = data["if"]
        matchkey = data.get("match")
        structure = data.get("else", [])
        if not isinstance(structure, list):
            structure = [structure]
        then = data.get("then") or data.get("structure")
        if not isinstance(then, list):
            then = [then]
        return cls(
            PromptStructure.load_from_dict(structure), 
            ifkey=ifkey, 
            match=matchkey,
            then=PromptStructure.load_from_dict(then)
        )


    @classmethod
    def load_while(cls, data: PromptStructureData):
        whilekey = data["while"]
        matchkey = data.get("match")
        initial = data.get("initial")
        if initial:
            if not isinstance(initial, list):
                initial = [initial]
        structure = data["structure"]
        if not isinstance(structure, list):
            structure = [structure]
        return cls(
            PromptStructure.load_from_dict(structure),
            whilekey=whilekey,
            match=matchkey,
            initial=PromptStructure.load_from_dict(initial) if initial is not None else None
        )


    @classmethod
    def load_from_dict(cls, data: PromptStructureData) -> Self:
        if isinstance(data, Dict):
            if data.get("iterator") or data.get("in"):
                return PromptStructure.load_iterator(data)
            elif data.get("when") or data.get("switch"):
                return PromptStructure.load_switch(data)
            elif data.get("if"):
                return PromptStructure.load_if(data)
            elif data.get("while"):
                return PromptStructure.load_while(data)
            else:
                return cls(Prompt.load_from_dict([data]))
        elif isinstance(data, List):
            self = cls([])
            for prompt in data:
                if any(key in prompt for key in self.keys()):
                    self.append(PromptStructure.load_from_dict(prompt))
                else:
                    self.append(Prompt.load_from_dict(prompt))
            return self
    
    
    @property
    def as_dict(self):
        data = {}
        for key in self.keys():
            if self[key] is not None:
                if key == "while":
                    data["whilekey"] = self[key]
                elif key == "if":
                    data["ifkey"] = self[key]
                else:
                    data[key] = self[key]
        return data

    @property
    def json(self) -> dict:
        data = {}
        if self.is_iterator:
            data = { **self.as_dict, "structure": list(map(lambda p: p.json, self)) }
        elif self.is_switch:
            data = { **self.as_dict, "default": list(map(lambda p: p.json, self)) }
        elif self.is_while:
            data = { **self.as_dict, "structure": list(map(lambda p: p.json, self)) }
        elif self.is_if:
            data = { **self.as_dict, "then": list(map(lambda p: p.json, self._then)), "else": list(map(lambda p: p.json, self)) }
        else:
            data = list(map(lambda p: p.json, self))
        return data


    def __repr__(self) -> str:
        data = self.json
        import json
        return json.dumps(data, indent=2)
        
        
    def __str__(self) -> str:
        data = self.json
        import json
        return json.dumps(data, indent=2)


    @classmethod
    def load(cls, file_name: str) -> Self:
        file: TextIO = open(file_name, "r")
        structure = None
        # Load from JSON file
        if file_name.endswith(".json"):
            import json
            structure = json.load(file)
        # Load from YAML file
        elif file_name.endswith(".yaml"):
            try:
                import yaml
                structure = yaml.safe_load(file)
            except ImportError as e:
                raise ImportError(
                    "Importing from yaml requires vespwood[yaml]. "
                    "Install it with: pip install vespwood[yaml]"
                ) from e
        self = None
        if isinstance(structure, dict):
            self = PromptStructure.load_from_dict(structure)  
        else:
            self = PromptStructure.load_from_dict(structure["structure"])
        file.close()
        return self
    

    @property
    def is_iterator(self) -> bool:
        return self._iterator is not None
    

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
    def is_while(self) -> bool:
        return self._while is not None
    

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
        if self.is_switch:
            for prompt_structure in self._cases:
                new_case.append(prompt_structure.copy())
        
        return PromptStructure(
            [p.copy() for p in self],
            id=self._id, 
            iterator=self._iterator,
            iter_key=self._iter_key, 
            co_iterators=new_co_iterators,
            co_iter_keys=new_co_iter_keys,
            default_co_iter_values=new_default_co_iter_values,
            initial=new_initial,
            whilekey=self._while,
            ifkey=self._if,
            match=self._match,
            then=new_then,
            switch=self._switch, 
            cases=new_case
        )
    
    
    def __copy__(self):
        return self.copy()
    
    
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
        

    def get_usables(self, format_keys: FormatKeys, /, tagged_messages: dict[str, Message] = {}) -> tuple[Msgs, Tag | None, SchemaInfo | None, ToolsList | None, HooksList | None, ValidatorsList | None, Saves | None]:
        prompt_structure = self.copy()
        msgs: list[Prompt] = []
        allNone = ([None] * 6)

        # Iterator
        if prompt_structure.is_iterator:
            _iterator = prompt_structure._iterator.format(**format_keys)
            iterator = format_keys[_iterator]
            iter_key = prompt_structure._iter_key
            co_iterators = [format_keys[co_iter] for co_iter in (prompt_structure._co_iterators or [])]
            co_iter_keys = prompt_structure._co_iter_keys
            default_co_iter_values = prompt_structure._default_co_iter_values
            for index, value in enumerate(iterator):
                print("Inside iterator", type(value))
                structure = None
                if prompt_structure.has_initial and index == 0:
                    structure = prompt_structure._initial
                else:
                    structure = prompt_structure.normalised
                indexed_structure = structure.indexed(index)
                extra_keys = { iter_key : value, "index": index }
                for idx, co_iterator in enumerate(co_iterators):
                    if len(co_iterator) <= index or co_iterator[index] is None:
                        extra_keys.update({co_iter_keys[idx]: default_co_iter_values[idx] if default_co_iter_values else None})
                    else:
                        extra_keys.update({co_iter_keys[idx]: co_iterator[index]})
                prompts, tag, *rest = indexed_structure.get_usables(format_keys.copy_with_extra(**extra_keys), tagged_messages=tagged_messages)
                msgs.extend(prompts)
                if tag: return msgs, tag, *rest
            return msgs, *allNone
        
        # Switch
        elif prompt_structure.is_switch:
            case_data = format_keys[prompt_structure._switch]
            for case in prompt_structure._cases:
                if case.match(case_data, **format_keys):
                    return case.get_usables(format_keys, tagged_messages=tagged_messages)
            normalised_structure = prompt_structure.normalised
            return normalised_structure.get_usables(format_keys, tagged_messages=tagged_messages)
            
        # If
        elif prompt_structure.is_if:
            case_data = format_keys[prompt_structure._if]
            if prompt_structure.match(case_data, **format_keys):
                return prompt_structure._then.get_usables(format_keys, tagged_messages=tagged_messages)
            normalised_structure = prompt_structure.normalised
            return normalised_structure.get_usables(format_keys, tagged_messages=tagged_messages)
        
        # While
        elif prompt_structure.is_while:
            case_data = format_keys[prompt_structure._while]
            index = 0
            while prompt_structure.match(format_keys.get(f"{prompt_structure._while}_{self._id}#{index}", case_data), **format_keys):
                print(f"{prompt_structure._while}_{self._id}#{index}")
                print(format_keys.get(f"{prompt_structure._while}_{self._id}#{index}"))
                structure = None
                if prompt_structure.has_initial and index == 0:
                    structure = prompt_structure._initial
                else:
                    structure = prompt_structure.normalised
                indexed_structure = structure.indexed(index)
                extra_keys = { "index": index }
                prompts, tag, *rest = indexed_structure.get_usables(format_keys.copy_with_extra(**extra_keys), tagged_messages=tagged_messages)
                msgs.extend(prompts)
                if not f"{prompt_structure._while}_{self._id}#{index}" in format_keys:
                    format_keys[f"{prompt_structure._while}_{self._id}#{index}"] = case_data
                if tag: return msgs, tag, *rest
                index += 1
            return msgs, *allNone

        # Normal
        for prompt in prompt_structure:
            if isinstance(prompt, PromptStructure):
                prompts, tag, *rest = prompt.get_usables(format_keys, tagged_messages=tagged_messages)
                msgs.extend(prompts)
                if tag: return msgs, tag, *rest
            else:
                if prompt.params:
                    params = format_keys.get_params(prompt._params)
                    prompt = prompt.format(params)
                if prompt.is_tagged:
                    tag = prompt.tag
                    if tag in tagged_messages:
                        message = tagged_messages[tag]
                        prompt.update_message(message)
                    if prompt.response_awaited:
                        if len(msgs) == 0:
                            raise ValueError("What the fuck do you want the LLM to respond to?")
                        return msgs, tag, prompt.schema, prompt.tools, prompt.hooks, prompt.validators, prompt.saves    
                msgs.append(prompt)
        
        return msgs, *allNone
