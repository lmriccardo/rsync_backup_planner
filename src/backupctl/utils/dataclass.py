from __future__ import annotations

import types

from enum import Enum 
from dataclasses import asdict, is_dataclass, fields, MISSING
from typing import List, Union, Dict, Any, TypeVar, Type
from typing import get_args, get_origin, Callable, Iterable, Tuple, Optional
from typing import get_type_hints

T = TypeVar("T")

class DictConfiguration:
    def asdict(self) -> Dict[str,Any]:
        return asdict(self)

class PrintableConfiguration:
    INDENT = 2

    def _indent(self, level: int) -> str:
        return " " * ( self.INDENT * level )
    
    def pretty( self, level: int = 0 ) -> str:
        pad = self._indent( level )
        lines: List[str] = [ f"{self.__class__.__name__} {'{'}" ]

        for field in fields(self):
            name = field.name
            value = getattr(self, name)
            lines.extend(self._pretty_field(name, value, level + 1))
        
        lines.append("}")

        return "\n".join(lines)
    
    def _pretty_collection(
        self, name: str, value: Any, level: int, empty_repr: str, 
        open_token: str, close_token: str,
        iter_items: Callable[[Any], Iterable[Tuple[Optional[Any], Any]]]
    ) -> List[str]:
        pad = self._indent(level)
        if not value: return [f"{pad}{name}: {empty_repr}"]
        prefix = f"{name}: "
        if name is None: prefix=""
        out = [f"{pad}{prefix}{open_token}"]

        for key, item in iter_items( value ):
            item_to_str = f"{item!r}"
            apply_inner_padding = True
            use_field_name = True

            if is_dataclass(item) and hasattr(item, "pretty"):
                item_to_str = item.pretty(level + 1)
                item_to_str = item_to_str[:-1] + f"{self._indent(level + 1)}" + "}"
                apply_inner_padding = True
            
            if isinstance(item, (list, tuple, dict)):
                item_to_str = "\n".join( self._pretty_field(key, item, level+1) )
                apply_inner_padding = False
                use_field_name = key is None

            inner_pad = self._indent(level + 1)
            if not apply_inner_padding: inner_pad = ""

            if key is None or not use_field_name:
                out.append(f"{inner_pad}{item_to_str}")
                continue
            
            out.append(f"{inner_pad}{key}: {item_to_str}")

        out.append(f"{pad}{close_token}")
        return out

    def _pretty_field( self, name: str, value: Any, level: int ) -> List[str]:
        pad = self._indent( level )

        # If the value is None
        if value is None: return [f"{pad}{name}: None"]

        # If the value is a nested dataclass
        if is_dataclass(value):
            if not hasattr(value, "pretty"): return [f"{pad}{name}: {value}"]
            return [f"{pad}{name}: {value.pretty(level + 1)}"]
        
        # If the value is either a list or a tuple
        if isinstance(value, (list, tuple)):
            fn = lambda v: ((None, item) for item in v)
            return self._pretty_collection(name, value, level, "[]", "[", "]", fn)

        if isinstance(value, dict):
            fn = lambda v: ((k, item) for k, item in v.items())
            return self._pretty_collection(name, value, level, "{}", "{", "}", fn)

        # Otherwise the value is a scalar value
        return [f"{pad}{name}: {value!r}"]

    def __str__(self) -> str:
        return self.pretty()
    
    
def _is_list( t: Any ) -> bool:
    return get_origin(t) is list

def _is_union( t: Any ) -> bool:
    origin = get_origin(t)
    return origin in (Union, types.UnionType)
    
def dataclass_from_dict(cls: Type[T], data: Any, discriminator: Dict[str,Any] | None = None) -> T:
    """ Load a generic dict into a dataclass """
    def raise_type_error( _type: str ):
        raise TypeError(f"Expected {_type} for {cls.__name__}, got {type(data).__name__}")

    if data is None: return data

    # This if statement checks for Enum type
    if isinstance(cls, type) and issubclass(cls, Enum): return cls(data)

    # This if statement checks for list type. List fields can only be
    # constructed from list data, otherwise TypeError is raised
    if _is_list(cls):
        if not isinstance( data, list ): raise_type_error("list")
        (inner_tp, ) = get_args( cls )
        return [ dataclass_from_dict( inner_tp, e, discriminator ) for e in data ]
    
    # This if statement checks for Union Type. If multiple types
    # are selected, then it tries to discriminate using the type
    # field that must be present into the data if the data is a
    # dictionary type. If the type keyword is not found an error
    # is raised, since the program is not be able to create the data
    if _is_union(cls):
        if isinstance(data, dict) and "type" not in data:
            raise RuntimeError("For Union types the 'type' field must be present")
        
        if isinstance(data, dict) and discriminator is not None:
            disc_type = data["type"]
            target_t = discriminator.get(disc_type)
            if target_t is not None:
                return dataclass_from_dict( target_t, data, discriminator )
        
        # Fallback: try each branch
        last_err: Exception | None = None
        for branch_t in get_args( cls ):
            if branch_t is types.NoneType: continue
            try:
                return dataclass_from_dict( branch_t, data, discriminator )
            except Exception as e:
                last_err = e
        
        raise TypeError(f"Cannot parse {data!r} as {cls}. Error {last_err}")
        
    # This if statement checks for dataclass type and construct
    # the dataclass directly from the input data, which must be
    # a dict, otherwise TypeError will be raised
    if is_dataclass( cls ):
        if not isinstance( data, dict ): raise_type_error("dict")

        kwargs = {}
        hints = get_type_hints( cls )
        for dc_field in fields(cls):
            # Check for ALIAS name into the dictionary
            field_name = dc_field.name
            raw_data = data.get( field_name, MISSING )
            if field_name.endswith("_") and field_name[:-1] in data:
                raw_data = data.get( field_name[:-1] )

            # leave it out -> dataclass default/default_factory will apply
            if raw_data is MISSING: continue

            field_type = hints[field_name]
            kwargs[field_name] = dataclass_from_dict( field_type, 
                raw_data, discriminator )

        return cls(**kwargs)
    
    return data