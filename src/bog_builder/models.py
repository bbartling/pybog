"""Pydantic models and helper functions for validating components, links and reduction blocks.

This module centralises all validation logic used by the BogFolderBuilder.  Separating
the models from the builder itself makes the code easier to test and maintain, and
avoids repeated definitions when using the builder in different contexts.

python -m bog_builder.analyzer analyze \
  "/mnt/c/Users/ben/Niagara4.11/JENEsys/lead_lag_cycles_block_playground.bog" \
  --format json > analysis.json

python -m bog_builder.analyzer analyze \
  "/mnt/c/Users/ben/Niagara4.11/JENEsys/lead_lag_cycles_block_playground.bog" \
  --format table

python -m bog_builder.analyzer analyze "/mnt/c/Users/ben/Niagara4.11/JENEsys/lead_lag_cycles_block_playground.bog" \
  --ignore-ws-annotations --format table

"""

from __future__ import annotations

import re
from typing import List

try:

    from pydantic import (
        BaseModel,
        ValidationError,
        field_validator,
        model_validator,
    )
except ImportError as exc:
    raise ImportError(
        "pydantic is required for bog_builder models. Please install pydantic>=2."
    ) from exc


COMPONENT_SLOT_MAP: dict[str, dict[str, List[str]]] = {
    "kitControl:Add": {"inputs": ["inA", "inB", "inC", "inD"], "outputs": ["out"]},
    "kitControl:Subtract": {"inputs": ["inA", "inB", "inC", "inD"], "outputs": ["out"]},
    "kitControl:Average": {"inputs": ["inA", "inB", "inC", "inD"], "outputs": ["out"]},
    "kitControl:Minimum": {"inputs": ["inA", "inB", "inC", "inD"], "outputs": ["out"]},
    "kitControl:Maximum": {"inputs": ["inA", "inB", "inC", "inD"], "outputs": ["out"]},
    "kitControl:Divide": {"inputs": ["inA", "inB", "inC", "inD"], "outputs": ["out"]},
    "kitControl:Subract": {"inputs": ["inA", "inB", "inC", "inD"], "outputs": ["out"]},
    "kitControl:Multiply": {"inputs": ["inA", "inB", "inC", "inD"], "outputs": ["out"]},
    "kitControl:GreaterThan": {"inputs": ["inA", "inB"], "outputs": ["out"]},
    "kitControl:GreaterThanEqual": {"inputs": ["inA", "inB"], "outputs": ["out"]},
    "kitControl:LessThan": {"inputs": ["inA", "inB"], "outputs": ["out"]},
    "kitControl:LessThanEqual": {"inputs": ["inA", "inB"], "outputs": ["out"]},
    "kitControl:Or": {"inputs": ["inA", "inB", "inC", "inD"], "outputs": ["out"]},
    "kitControl:And": {"inputs": ["inA", "inB", "inC", "inD"], "outputs": ["out"]},
    "kitControl:Xor": {"inputs": ["inA", "inB", "inC", "inD"], "outputs": ["out"]},
    "kitControl:Not": {"inputs": ["in"], "outputs": ["out"]},
    "kitControl:Equal": {"inputs": ["inA", "inB"], "outputs": ["out"]},
    "kitControl:NumericSwitch": {
        "inputs": ["inSwitch", "inTrue", "inFalse"],
        "outputs": ["out"],
    },
    "kitControl:NumericSelect": {
        "inputs": ["select"] + [f"in{chr(65 + i)}" for i in range(10)],
        "outputs": ["out"],
    },
    "kitControl:BooleanLatch": {
        "inputs": ["in", "clock"],
        "outputs": ["out"],
    },
    "kitControl:NumericLatch": {
        "inputs": ["in", "clock"],
        "outputs": ["out"],
    },
    "kitControl:OneShot": {"inputs": ["in"], "outputs": ["out"]},
    "kitControl:BooleanDelay": {
        "inputs": ["in", "onDelay", "offDelay"],
        "outputs": ["out"],
    },
    "kitControl:NumericDelay": {
        "inputs": ["in", "updateTime", "maxStepSize"],
        "outputs": ["out"],
    },
    "kitControl:Counter": {
        "inputs": ["countUp", "countDown", "countIncrement", "clear", "presetValue"],
        "outputs": ["out"],
    },
    "kitControl:MultiVibrator": {"inputs": ["period", "enabled"], "outputs": ["out"]},
    "kitControl:SineWave": {"inputs": [], "outputs": ["out"]},
    "control:NumericWritable": {"outputs": ["out"]},
    "control:BooleanWritable": {"outputs": ["out"]},
    "control:EnumWritable": {"outputs": ["out"]},
    "kitControl:NumericConst": {"inputs": [], "outputs": ["out"]},
    "kitControl:BooleanConst": {"inputs": [], "outputs": ["out"]},
    "kitControl:EnumConst": {"inputs": [], "outputs": ["out"]},
    "kitControl:BooleanSwitch": {
        "inputs": ["inSwitch", "inTrue", "inFalse"],
        "outputs": ["out"],
    },
    "kitControl:Reset": {
        "inputs": [
            "inA",
            "inputLowLimit",
            "inputHighLimit",
            "outputLowLimit",
            "outputHighLimit",
        ],
        "outputs": ["out"],
    },
    "kitControl:LeadLagCycles": {
        "inputs": [
            "in",
            "feedback",
            "cycleCountA",
            "cycleCountB",
            "cycleCountC",
            "cycleCountD",
            "cycleCountE",
            "cycleCountF",
            "cycleCountG",
            "cycleCountH",
            "cycleCountI",
            "cycleCountJ",
        ],
        "outputs": [
            "outA",
            "outB",
            "outC",
            "outD",
            "outE",
            "outF",
            "outG",
            "outH",
            "outI",
            "outJ",
        ],
    },
    "kitControl:LeadLagRuntime": {
        "inputs": [
            "in",
            "maxRuntime",
            "feedback",
            "runtimeA",
            "runtimeB",
            "runtimeC",
            "runtimeD",
            "runtimeE",
            "runtimeF",
            "runtimeG",
            "runtimeH",
            "runtimeI",
            "runtimeJ",
        ],
        "outputs": [
            "outA",
            "outB",
            "outC",
            "outD",
            "outE",
            "outF",
            "outG",
            "outH",
            "outI",
            "outJ",
        ],
    },
    "kitControl:LoopPoint": {
        "inputs": [
            "loopEnable",
            "controlledVariable",
            "setpoint",
            "loopAction",
            "proportionalConstant",
            "integralConstant",
        ],
        "outputs": ["out"],
    },
    "kitControl:Tstat": {
        "inputs": [
            "cv",
            "diff",
            "sp",
            "action",
            "nullOnInControl",
            "nullOnInactive",
        ],
        "outputs": ["out"],
    },
    "sch:BooleanSchedule": {"outputs": ["out"]},
    "sch:NumericSchedule": {"outputs": ["out"]},
    "sch:EnumSchedule": {"outputs": ["out"]},
}


def _parse_time_to_ms(value) -> str:
    """
    Convert various human‑friendly time strings into a millisecond string.  Accepts
    numeric values (assumed milliseconds), strings with units (ms, s, m, min, h),
    or floats.  If parsing fails, the original value is returned as a string.

    Examples:
        ``_parse_time_to_ms(1) -> "1"``
        ``_parse_time_to_ms("500ms") -> "500"``
        ``_parse_time_to_ms("2s") -> "2000"``
        ``_parse_time_to_ms("1m") -> "60000"``
    """
    if isinstance(value, dict) and "value" in value:
        value = value["value"]
    if isinstance(value, (int, float)):
        return str(int(float(value)))
    if isinstance(value, str):
        s = value.strip().lower()
        if s.isdigit():
            return s
        match = re.fullmatch(r"(\d+(?:\.\d+)?)(ms|s|m|min|h)", s)
        if match:
            num_str, unit = match.groups()
            num = float(num_str)
            # Convert based on unit
            if unit == "ms":
                return str(int(num))
            elif unit == "s":
                return str(int(num * 1000))
            elif unit in ("m", "min"):
                return str(int(num * 60000))
            elif unit == "h":
                return str(int(num * 3600000))
    # Fallback – return original value converted to string
    return str(value)


class ComponentDefinition(BaseModel):
    """Pydantic model to validate and normalise component definitions."""

    comp_type: str
    name: str
    properties: dict = {}
    actions: dict = {}

    @field_validator("name")
    def name_is_valid(cls, v: str) -> str:
        # ... (this validator remains the same)
        if not isinstance(v, str) or not v:
            raise ValueError("Component name must be a non‑empty string.")
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", v):
            suggestion = f"Calc_{re.sub(r'[^A-Za-z0-9_]', '_', v)}"
            raise ValueError(
                f"Invalid component name '{v}'. Names must start with a letter or underscore "
                f"and contain only letters, digits or underscores. Consider renaming it to '{suggestion}'."
            )
        return v

    @field_validator("comp_type")
    def comp_type_format(cls, v: str) -> str:
        # ... (this validator remains the same)
        if not isinstance(v, str) or ":" not in v:
            raise ValueError(
                f"Invalid component type '{v}'. Component types must be of the form 'palette:TypeName', "
                f"e.g., 'kitControl:Add' or 'control:NumericWritable'."
            )
        return v

    @field_validator("properties")
    def properties_must_be_dict(cls, v):
        # ... (this validator remains the same)
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("The 'properties' field must be a dictionary.")
        return v

    @field_validator("actions")
    def actions_must_be_dict(cls, v):
        # ... (this validator remains the same)
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("The 'actions' field must be a dictionary.")
        return v

    @model_validator(mode="after")
    def validate_enum_properties(
        cls, model: "ComponentDefinition"
    ) -> "ComponentDefinition":
        """
        Applies strict validation for EnumWritable and EnumConst components.
        """
        props = model.properties

        if model.comp_type == "control:EnumWritable":
            if "facets" not in props:
                raise ValueError(
                    "EnumWritable requires a 'facets' property (e.g., 'range=E:{...}')."
                )
            if "fallback" not in props or "value" not in props.get("fallback", {}):
                raise ValueError(
                    "EnumWritable requires a 'fallback' property with a 'value' key holding the default index."
                )

            fallback_val = props["fallback"]["value"]
            if "@" in str(fallback_val):
                raise ValueError(
                    f"EnumWritable fallback value must be a simple index (e.g., '3'), not a pre-formatted string ('{fallback_val}'). "
                    "Use the add_enum_writable() helper."
                )
            try:
                int(fallback_val)
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"EnumWritable fallback value must be a valid integer index, but got '{fallback_val}'."
                ) from e

        if model.comp_type == "kitControl:EnumConst":
            if "facets" not in props:
                raise ValueError(
                    "kitControl:EnumConst requires a 'facets' property (e.g., 'range=E:{...}')."
                )
            if "value" not in props:
                raise ValueError(
                    "kitControl:EnumConst requires a 'value' property holding the pre-formatted DynamicEnum string (e.g., '3@{...}')."
                )

            val = props["value"]
            if "@" not in str(val):
                raise ValueError(
                    f"kitControl:EnumConst 'value' property must be a pre-formatted DynamicEnum string containing '@' (e.g., '3@{{...}}'), but got '{val}'."
                )

        return model


class LinkDefinition(BaseModel):
    """Pydantic model to validate a link between two components."""

    source_name: str
    source_slot: str
    target_name: str
    target_slot: str

    @field_validator("source_name", "source_slot", "target_name", "target_slot")
    def non_empty(cls, v: str, info):  # type: ignore[override]
        """
        Ensure that each part of the link definition is a non‑empty string.  The
        `info` parameter (available in pydantic v2) provides the field name so we
        can craft meaningful error messages.
        """
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"The '{info.field_name}' must be a non‑empty string.")
        return v.strip()

    @model_validator(mode="after")
    def no_self_link(cls, model: "LinkDefinition") -> "LinkDefinition":
        """
        Prevent linking a component to the exact same slot on itself.  This
        validator triggers after all fields have been validated and constructed
        into a model instance.
        """
        if (
            model.source_name == model.target_name
            and model.source_slot == model.target_slot
        ):
            raise ValueError(
                f"Invalid link: source ({model.source_name}:{model.source_slot}) and target "
                f"({model.target_name}:{model.target_slot}) are identical."
            )
        return model


class ReductionBlockDefinition(BaseModel):
    """Validate inputs for reduction blocks (Average/Minimum/Maximum)."""

    block_type: str
    final_output_name: str
    input_names: List[str]

    @field_validator("block_type")
    def block_type_allowed(cls, v: str) -> str:
        allowed = {"Average", "Minimum", "Maximum"}
        if v not in allowed:
            raise ValueError(
                f"Invalid reduction block type '{v}'. Must be one of {sorted(allowed)}."
            )
        return v

    @field_validator("final_output_name")
    def output_name_valid(cls, v: str) -> str:
        if not isinstance(v, str) or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", v):
            suggestion = f"Calc_{re.sub(r'[^A-Za-z0-9_]', '_', v)}"
            raise ValueError(
                f"Invalid final output name '{v}'. Names must start with a letter or underscore "
                f"and contain only letters, digits or underscores. Consider renaming it to '{suggestion}'."
            )
        return v

    @field_validator("input_names")
    def inputs_must_be_nonempty(cls, v: List[str]) -> List[str]:
        if not isinstance(v, (list, tuple)) or len(v) < 2:
            raise ValueError("Input names must be a list with at least two entries.")
        for name in v:
            if not isinstance(name, str) or not name:
                raise ValueError(
                    "All input names must be non‑empty strings. Found an invalid entry."
                )
        return list(v)
