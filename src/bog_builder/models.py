"""Pydantic models and helper functions for validating components, links and reduction blocks.

This module centralises all validation logic used by the BogFolderBuilder.  Separating
the models from the builder itself makes the code easier to test and maintain, and
avoids repeated definitions when using the builder in different contexts.
"""

from __future__ import annotations

import re
from typing import List

try:
    # Pydantic v2: we import both field_validator and model_validator for modern
    # validation hooks.  BaseModel and ValidationError are also used.
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


# Mapping of known component types to their valid input and output slot names.
# This mapping is not exhaustive, but covers all tested blocks from the examples.
# If a component type is not present, slot validation will be skipped for that type.
COMPONENT_SLOT_MAP: dict[str, dict[str, List[str]]] = {
    # Arithmetic / Math
    "kitControl:Add": {"inputs": ["inA", "inB", "inC", "inD"], "outputs": ["out"]},
    # Reduction blocks.  Average, Minimum and Maximum accept up to four inputs
    # (inA–inD) and produce a single out output.  Although the builder can
    # construct reductions using the `add_reduction_block` helper, users may
    # also add these blocks directly via `add_component`.
    "kitControl:Average": {"inputs": ["inA", "inB", "inC", "inD"], "outputs": ["out"]},
    "kitControl:Minimum": {"inputs": ["inA", "inB", "inC", "inD"], "outputs": ["out"]},
    "kitControl:Maximum": {"inputs": ["inA", "inB", "inC", "inD"], "outputs": ["out"]},
    # Comparison logic
    "kitControl:GreaterThan": {"inputs": ["inA", "inB"], "outputs": ["out"]},
    "kitControl:GreaterThanEqual": {"inputs": ["inA", "inB"], "outputs": ["out"]},
    "kitControl:LessThan": {"inputs": ["inA", "inB"], "outputs": ["out"]},
    "kitControl:LessThanEqual": {"inputs": ["inA", "inB"], "outputs": ["out"]},
    # Logical operators
    "kitControl:Or": {"inputs": ["inA", "inB"], "outputs": ["out"]},
    "kitControl:And": {"inputs": ["inA", "inB"], "outputs": ["out"]},
    "kitControl:Xor": {"inputs": ["inA", "inB"], "outputs": ["out"]},
    "kitControl:Not": {"inputs": ["in"], "outputs": ["out"]},
    # Switch/select
    "kitControl:NumericSwitch": {
        "inputs": ["inSwitch", "inTrue", "inFalse"],
        "outputs": ["out"],
    },
    "kitControl:NumericSelect": {
        "inputs": ["select"] + [f"in{chr(65 + i)}" for i in range(10)],
        "outputs": ["out"],
    },
    # Boolean latch: supports in, clock, set, reset inputs and an out output
    "kitControl:BooleanLatch": {
        "inputs": ["in", "clock", "set", "reset"],
        "outputs": ["out"],
    },
    # OneShot: pulse edge detector.  Single input and output.
    "kitControl:OneShot": {"inputs": ["in"], "outputs": ["out"]},
    # BooleanDelay and NumericDelay provide a delayed copy of their input.
    "kitControl:BooleanDelay": {"inputs": ["in"], "outputs": ["out"]},
    "kitControl:NumericDelay": {"inputs": ["in"], "outputs": ["out"]},
    # Counter: numeric counter block with countUp, countDown, countIncrement and clear inputs.
    "kitControl:Counter": {
        "inputs": ["countUp", "countDown", "countIncrement", "clear"],
        "outputs": ["out"],
    },
    # MultiVibrator: periodic pulse generator with no inputs and a single out output.
    "kitControl:MultiVibrator": {"inputs": [], "outputs": ["out"]},
    # Waveform generator
    "kitControl:SineWave": {"inputs": [], "outputs": ["out"]},
    # Writables (expose values to user)
    # For NumericWritable and BooleanWritable we only validate the output slot.  The
    # input slots (e.g. "in1", "in10", "in16") vary and are not exhaustively
    # mapped here, so we skip input validation by omitting the "inputs" key.
    "control:NumericWritable": {"outputs": ["out"]},
    "control:BooleanWritable": {"outputs": ["out"]},
    # Constants
    "kitControl:NumericConst": {"inputs": [], "outputs": ["out"]},
    # Reset block: linear interpolation between input and two limit pairs
    # The Reset block accepts five inputs (inA, inputLowLimit, inputHighLimit,
    # outputLowLimit, outputHighLimit) and produces a single out output.  This
    # slot map enables proper validation of links to and from a Reset block.
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
    # PID loop point: accepts a process variable, setpoint, enable, action and tuning constants
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
    # Boolean schedule: schedules from the schedule palette have a single
    # ``out`` slot which conveys the active boolean value.  We omit inputs since
    # schedules are configured via properties rather than links.
    "sch:BooleanSchedule": {"outputs": ["out"]},
    # Numeric schedules emit a numeric ``out`` value and do not define
    # input slots for linking.  The ``defaultOutput`` property sets the
    # baseline value when no schedule events are in effect.
    "sch:NumericSchedule": {"outputs": ["out"]},
    # Enum schedules emit an enumerated ``out`` value.  They do not have
    # defined input slots.  The ``facets`` property describes the
    # enumeration mapping (e.g. ``range=E:{duty1=1,duty2=2}``).
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
    # If a dictionary is passed (e.g., {"value": "1m"}), extract the value field
    if isinstance(value, dict) and "value" in value:
        value = value["value"]
    # If already a number, return as int string
    if isinstance(value, (int, float)):
        return str(int(float(value)))
    if isinstance(value, str):
        s = value.strip().lower()
        # Fully numeric string – treat as milliseconds directly
        if s.isdigit():
            return s
        # Pattern: number with optional decimal and a unit
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
        """
        Validate that component names start with a letter or underscore and consist
        only of alphanumeric characters and underscores.  Niagara 4 does not allow
        names to begin with a number.
        """
        if not isinstance(v, str) or not v:
            raise ValueError("Component name must be a non‑empty string.")
        # Names must start with a letter or underscore and may contain digits/underscores
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", v):
            suggestion = f"Calc_{re.sub(r'[^A-Za-z0-9_]', '_', v)}"
            raise ValueError(
                f"Invalid component name '{v}'. Names must start with a letter or underscore "
                f"and contain only letters, digits or underscores. Consider renaming it to '{suggestion}'."
            )
        return v

    @field_validator("comp_type")
    def comp_type_format(cls, v: str) -> str:
        """
        Validate that component types follow the 'palette:TypeName' format.
        """
        if not isinstance(v, str) or ":" not in v:
            raise ValueError(
                f"Invalid component type '{v}'. Component types must be of the form 'palette:TypeName', "
                f"e.g., 'kitControl:Add' or 'control:NumericWritable'."
            )
        return v

    @field_validator("properties")
    def properties_must_be_dict(cls, v):
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("The 'properties' field must be a dictionary.")
        return v

    @field_validator("actions")
    def actions_must_be_dict(cls, v):
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("The 'actions' field must be a dictionary.")
        return v


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
        # Use the same name rules as components
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
