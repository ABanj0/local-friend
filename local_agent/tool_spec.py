"""Immutable built-in tool contracts; registration is trusted host code only."""
import inspect
from collections.abc import Callable
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from .patches import MAX_FILES
from .safety import Denied

Category = Literal["coding", "browser", "desktop"]
PROFILES = MappingProxyType({
    "unified": frozenset({"coding", "browser", "desktop"}),
    "coding": frozenset({"coding"}), "browser": frozenset({"browser"}),
    "desktop": frozenset({"desktop"}),
})


def categories(profile):
    if not isinstance(profile, str) or profile not in PROFILES:
        raise ValueError("Unknown tool profile; choose unified, coding, browser or desktop")
    return PROFILES[profile]


@dataclass(frozen=True)
class ArgumentSpec:
    name: str
    kind: type
    required: bool
    default: object
    choices: tuple[str, ...] | None = None
    description: str = ""
    item_fields: tuple["ArgumentSpec", ...] = ()
    max_items: int = 0

    def schema(self):
        result = {"type": "integer" if self.kind is int else "array" if self.kind is list else "string"}
        if self.kind is list:
            result.update(minItems=1, maxItems=self.max_items, items={"type": "object",
                "properties": {field.name: field.schema() for field in self.item_fields},
                "required": [field.name for field in self.item_fields], "additionalProperties": False})
        if self.choices is not None:
            result["enum"] = list(self.choices)
        if self.description:
            result["description"] = self.description
        return result


@dataclass(frozen=True)
class ToolSpec:
    name: str
    version: int
    category: Category
    description: str
    handler: Callable
    signature: inspect.Signature
    arguments: tuple[ArgumentSpec, ...]

    @classmethod
    def create(cls, name, category, description, handler, commands):
        signature = inspect.signature(handler)
        arguments = []
        for key, parameter in signature.parameters.items():
            if parameter.kind not in {inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY}:
                raise ValueError("Tools require named parameters")
            default = parameter.default
            required = default is inspect.Parameter.empty
            kind = list if parameter.annotation is list else int if type(default) is int else str
            choices, detail = None, ""
            item_fields = ()
            if kind is list:
                if name != "apply_patch" or key != "changes":
                    raise ValueError("List tool arguments require an explicit trusted item contract")
                item_fields = tuple(ArgumentSpec(field, str, True, inspect.Parameter.empty, description=description)
                    for field, description in (("path", "Workspace-relative destination"),
                        ("expected_sha256", "Raw-byte lowercase SHA-256 from read_file/search_files, or 'missing'"),
                        ("text", "Complete proposed UTF-8 contents; empty string creates/replaces an empty file")))
            if name in {"command", "start_command", "command_status"} and key == "name":
                choices = tuple(commands)
                detail = ("Exact configured profile name, not a shell command. "
                          "Use 'test' to run unittest discovery.")
                if name == "command_status":
                    detail = "Exact configured profile previously started by this task; cannot inspect unrelated processes."
            if key == "cwd":
                detail = ("Workspace-relative directory, for example 'first-task'. "
                          "Do not use an absolute Windows path or prefix it with 'workspace/'.")
            arguments.append(ArgumentSpec(key, kind, required, default, choices, detail,
                                          item_fields, MAX_FILES if item_fields else 0))
        return cls(name, 1, category, description, handler, signature, tuple(arguments))

    def schema(self):
        return {"type": "function", "function": {
            "name": self.name, "description": self.description, "parameters": {
                "type": "object", "properties": {arg.name: arg.schema() for arg in self.arguments},
                "required": [arg.name for arg in self.arguments if arg.required],
                "additionalProperties": False}}}

    def validate(self, arguments):
        if not isinstance(arguments, dict):
            raise TypeError("Tool arguments must be an object")
        bound = self.signature.bind(**arguments)
        bound.apply_defaults()
        for argument in self.arguments:
            value = bound.arguments[argument.name]
            if type(value) is not argument.kind:
                raise TypeError(f"Invalid argument type: {argument.name}")
            if argument.item_fields:
                if not 1 <= len(value) <= argument.max_items:
                    raise TypeError("Invalid tool object-list length")
                for item in value:
                    if (type(item) is not dict or set(item) != {field.name for field in argument.item_fields}
                            or any(type(item[field.name]) is not field.kind for field in argument.item_fields)):
                        raise TypeError("Invalid tool object-list fields")
            if argument.choices is not None and value not in argument.choices:
                raise Denied("Unknown command profile. Allowed profiles: " + ", ".join(argument.choices)
                             + ". For unittest, use name='test' and a workspace-relative cwd.")
        return bound.arguments
