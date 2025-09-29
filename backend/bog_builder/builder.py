"""Main builder class for constructing Niagara .bog files.

This module exposes the :class:`BogFolderBuilder` which provides a high‑level API
for creating components, linking them together, organising them into sub‑folders
and saving the resulting graph as a `.bog` archive.  The builder delegates
validation of component definitions, link definitions and reduction blocks to
Pydantic models defined in :mod:`bog_builder.models`.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from xml.dom import minidom
import zipfile
from collections import defaultdict, deque
import os
import re
from typing import Any, Dict, List, Literal, Tuple

from pydantic import ValidationError

from .models import (
    COMPONENT_SLOT_MAP,
    COMPONENT_OUTPUT_TYPE,
    SLOT_TYPE_MAPPING,
    CONVERSION_MAP,
    _parse_time_to_ms,
    ComponentDefinition,
    LinkDefinition,
    ReductionBlockDefinition,
)


class BogFolderBuilder:
    """
    Builds a Niagara `.bog` file with an intelligent layout engine.  The builder
    supports automatic sub‑folder creation to manage complexity, rigorous input
    validation via Pydantic models, and a variety of helper methods for common
    component types.

    Parameters
    ----------
    folder_name : str
        The name of the root folder for the graph.  This becomes the top‑level
        folder name in the resulting `.bog` file.
    debug : bool, optional
        If ``True``, additional layout debug messages will be printed to stdout.
    """

    def __init__(self, folder_name: str, debug: bool = True):
        self.debug = debug
        self.folder_name = folder_name
        self._components: Dict[str, Dict] = {}
        self._links: List[Dict] = []
        self._next_handle = 1
        self._handle_map: Dict[str, str] = {}
        self._enum_ranges: Dict[str, Dict[str, int]] = {}
        self._sub_folders: Dict[Tuple[str, ...], List[str]] = defaultdict(list)
        self._component_to_folder: Dict[str, Tuple[str, ...]] = {}
        self._current_folder_path: Tuple[str, ...] = (folder_name,)
        self._folder_handles: Dict[Tuple[str, ...], str] = {}
        self.START_X = 10
        self.START_Y = 10
        self.X_COLUMN_WIDTH = 20  # DONT MODIFY HUMAN VERIFY VISUALLY GOOD
        self.Y_INCREMENT = 10  # DONT MODIFY HUMAN VERIFY VISUALLY GOOD

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    def log(self, message: str, is_layout_log: bool = False) -> None:
        """Print a debug message if debugging is enabled and the message
        relates to layout calculation."""
        if self.debug and is_layout_log:
            print(f"[BOG LAYOUT DEBUG] {message}")

    def _get_next_handle(self) -> str:
        handle = hex(self._next_handle)[2:]
        self._next_handle += 1
        return handle

    # ------------------------------------------------------------------
    # Folder management
    # ------------------------------------------------------------------
    def start_sub_folder(self, name: str) -> None:
        """Starts a new sub‑folder context with validation.

        Sub‑folder names follow the same naming rules as component names:
        they must start with a letter or underscore and contain only
        letters, digits or underscores.  Duplicate sub‑folder names at the
        same level are not allowed.

        Raises
        ------
        ValueError
            If the folder name is invalid or already exists at the current level.
        """
        if not isinstance(name, str) or not name:
            raise ValueError("Sub‑folder name must be a non‑empty string.")
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
            suggestion = f"Calc_{re.sub(r'[^A-Za-z0-9_]', '_', name)}"
            raise ValueError(
                f"Invalid sub‑folder name '{name}'. Folder names must start with a letter or "
                f"underscore and contain only letters, digits or underscores. Consider "
                f"renaming it to '{suggestion}'."
            )
        parent_path = self._current_folder_path
        if name in self._sub_folders.get(parent_path, []):
            raise ValueError(
                f"A sub‑folder named '{name}' already exists under '{self.get_current_path_str()}'. "
                f"Choose a unique sub‑folder name."
            )
        self._sub_folders[parent_path].append(name)
        new_path = parent_path + (name,)

        # Generate and store a unique handle for the new sub-folder path
        handle = self._get_next_handle()
        self._folder_handles[new_path] = handle

        self._current_folder_path = new_path

    def end_sub_folder(self) -> None:
        """Exits the current sub‑folder, returning to the parent.

        Raises
        ------
        ValueError
            If called when already at the root folder.
        """
        if len(self._current_folder_path) <= 1:
            raise ValueError(
                "Cannot end sub‑folder: already at the root folder. Ensure that "
                "start_sub_folder() was called before end_sub_folder()."
            )
        self._current_folder_path = self._current_folder_path[:-1]

    def get_current_path_str(self) -> str:
        """Returns the current folder path as a string separated by `/`."""
        return "/".join(self._current_folder_path)

    # ------------------------------------------------------------------
    # ENUM point handling
    # ------------------------------------------------------------------
    def define_enum_range(self, name: str, mapping: Dict[str, int]) -> None:
        """
        Registers a named enum range for reuse. This avoids having to
        re-create facets strings for multiple components.

        Parameters
        ----------
        name : str
            A unique name for this enum definition (e.g., "Mode", "DamperState").
        mapping : Dict[str, int]
            A dictionary mapping enum tags to their integer ordinals.
        """
        if name in self._enum_ranges:
            raise ValueError(f"An enum range named '{name}' has already been defined.")
        if not isinstance(mapping, dict) or not all(
            isinstance(k, str) and isinstance(v, int) for k, v in mapping.items()
        ):
            raise TypeError(
                "Enum mapping must be a dictionary of string keys to integer values."
            )
        self._enum_ranges[name] = mapping

    def add_enum_writable_by_name(
        self, component_name: str, enum_name: str, default_tag: str
    ) -> None:
        """
        Adds an EnumWritable using a pre-defined enum range.

        Parameters
        ----------
        component_name : str
            The name for the new EnumWritable component.
        enum_name : str
            The name of the enum range registered with define_enum_range().
        default_tag : str
            The string tag for the default value (e.g., "Startup").
        """
        if enum_name not in self._enum_ranges:
            raise ValueError(
                f"Enum range '{enum_name}' is not defined. Call define_enum_range() first."
            )

        mapping = self._enum_ranges[enum_name]
        if default_tag not in mapping:
            raise ValueError(
                f"Default tag '{default_tag}' not found in enum range '{enum_name}'."
            )

        facets_str = (
            "range=E:{" + ",".join(f"{k}={v}" for k, v in mapping.items()) + "}"
        )
        default_index = str(mapping[default_tag])

        self.add_enum_writable(
            component_name, facets=facets_str, default_value=default_index
        )

    def add_enum_const_by_name(
        self, component_name: str, enum_name: str, value_tag: str
    ) -> None:
        """
        Adds an EnumConst using a pre-defined enum range.

        Parameters
        ----------
        component_name : str
            The name for the new EnumConst component.
        enum_name : str
            The name of the enum range registered with define_enum_range().
        value_tag : str
            The string tag for the constant's value (e.g., "Startup").
        """
        if enum_name not in self._enum_ranges:
            raise ValueError(
                f"Enum range '{enum_name}' is not defined. Call define_enum_range() first."
            )

        mapping = self._enum_ranges[enum_name]
        if value_tag not in mapping:
            raise ValueError(
                f"Value tag '{value_tag}' not found in enum range '{enum_name}'."
            )

        facets_str = (
            "range=E:{" + ",".join(f"{k}={v}" for k, v in mapping.items()) + "}"
        )

        ord_ = mapping[value_tag]
        range_part = "{" + ",".join(f"{k}={v}" for k, v in mapping.items()) + "}"
        value_str = f"{ord_}@{range_part}"

        self._add_component(
            "kitControl:EnumConst",
            component_name,
            properties={"facets": facets_str, "value": value_str},
        )

    # ------------------------------------------------------------------
    # Internal component creation
    # ------------------------------------------------------------------
    def _add_component(
        self,
        comp_type: str,
        name: str,
        properties: dict | None = None,
        actions: dict | None = None,
    ) -> None:
        """Internal helper to register a component with validation.

        This method should not be called directly from user code.  It performs
        validation on the component type and name, converts time‑based
        properties into millisecond strings, and stores the component in the
        builder's internal state.
        """
        properties = properties or {}
        actions = actions or {}
        try:
            comp_def = ComponentDefinition(
                comp_type=comp_type,
                name=name,
                properties=properties,
                actions=actions,
            )
        except ValidationError as ve:
            raise ValueError(str(ve)) from ve
        if comp_def.name in self._components:
            raise ValueError(
                f"Component with name '{comp_def.name}' already exists. Each component must have a unique name."
            )
        normalized_props: dict = {}
        for prop_name, prop_value in comp_def.properties.items():
            if any(keyword in prop_name.lower() for keyword in ("delay", "period")):
                normalized_props[prop_name] = _parse_time_to_ms(prop_value)
            else:
                normalized_props[prop_name] = prop_value
        if comp_def.comp_type not in COMPONENT_SLOT_MAP and self.debug:
            print(
                f"[BOG VALIDATION WARNING] Component type '{comp_def.comp_type}' is not in the src on models.py in the COMPONENT_SLOT_MAP. "
                f"This should be reported on a gitissue and tested.",
            )
        handle = self._get_next_handle()
        self._handle_map[comp_def.name] = handle
        self._components[comp_def.name] = {
            "type": comp_def.comp_type,
            "properties": normalized_props,
            "actions": comp_def.actions,
            "handle": handle,
        }
        self._component_to_folder[comp_def.name] = self._current_folder_path

    def add_component(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Public API disabled. Use the typed wrapper methods instead."""
        raise RuntimeError(
            "add_component is internal; use the typed wrapper methods on BogFolderBuilder"
        )

    def add_numeric_writable(
        self,
        name: str,
        default_value: float = 0.0,
        precision: int = 2,
    ) -> None:
        """
        Adds a NumericWritable with sensible default facets.

        Note: Programmatically setting units is disabled to ensure stability across
        different Niagara versions. Please set units manually in Workbench.

        Parameters
        ----------
        name : str
            The unique name for the component.
        default_value : float, optional
            The initial fallback value for the point.
        precision : int, optional
            The number of decimal places for display.
        units : str, optional
            This parameter is disabled and must not be used.

        Raises
        ------
        ValueError
            If the 'units' argument is provided with a value other than the default.
        """

        # Construct a stable facets string. 'u:null' requires extra semicolons.
        facets_value = f"units=u:null;;;;|precision=i:{precision}|min=d:-inf|max=d:+inf"

        self._add_component(
            "control:NumericWritable",
            name,
            properties={
                "defaultValue": default_value,
                "facets": {"type": "b:Facets", "value": facets_value},
            },
            actions={"emergencyOverride": "h", "emergencyAuto": "h"},
        )

    def add_boolean_writable(self, name: str, default_value: bool = False) -> None:
        """Add a BooleanWritable with a default value."""
        self._add_component(
            "control:BooleanWritable",
            name,
            properties={"fallback": {"value": str(default_value).lower()}},
        )

    def add_enum_writable(
        self, name: str, facets: str, default_value: str = "0"
    ) -> None:
        """
        Add an EnumWritable with a facets mapping and an initial fallback value.

        Parameters
        ----------
        name : str
            The component name.
        facets : str
            The enumeration mapping string (e.g. ``"range=E:{duty1=1,duty2=2}"``) to
            define the set of allowed enum values.
        default_value : str, optional
            The initial fallback value as an ``"x@{...}"`` string or
            plain integer.  Defaults to ``"0"``.
        """
        dv = default_value if isinstance(default_value, str) else str(default_value)
        self._add_component(
            "control:EnumWritable",
            name,
            properties={
                "facets": facets,
                "fallback": {"value": dv},
            },
        )

    def add_numeric_switch(self, name: str) -> None:
        """Add a kitControl NumericSwitch component."""
        self._add_component("kitControl:NumericSwitch", name)

    def add_boolean_switch(self, name: str) -> None:
        """Add a kitControl BooleanSwitch component."""
        self._add_component("kitControl:BooleanSwitch", name)

    def add_numeric_select(self, name: str) -> None:
        """Adds a NumericSelect component with default 10 inputs (A‑J)."""
        self._add_component(
            "kitControl:NumericSelect", name, properties={"numberValues": "10"}
        )

    def add_multi_vibrator(self, name: str, period_ms: str | int = "10000") -> None:
        """Add a MultiVibrator component.

        Parameters
        ----------
        name : str
            The component name.
        period_ms : str or int, optional
            The period in milliseconds.  Accepts either an integer or a string; the
            value is converted to a string and emitted as a ``b:RelTime`` in the
            XML output.
        """
        self._add_component(
            "kitControl:MultiVibrator", name, properties={"period": str(period_ms)}
        )

    def add_counter(
        self,
        name: str,
        count_increment: float = 1.0,
        precision: int | None = None,
        properties: dict | None = None,
    ) -> None:
        """Add a Counter component.

        Parameters
        ----------
        name : str
            The component name.
        count_increment : float, optional
            The amount by which the counter increments on each tick.
        precision : int or None, optional
            Optional precision for display; if provided, it is rounded to an
            integer.
        properties : dict or None, optional
            Additional properties to set on the counter; keys in this dict will
            override default values for ``countIncrement`` and ``initialValue``.
        """
        props = dict(properties or {})
        props.setdefault("countIncrement", count_increment)
        if precision is not None:
            props["precision"] = int(precision)
        self._add_component("kitControl:Counter", name, properties=props) 
   # ------------------------------------------------------------------
    # New typed wrapper methods
    # ------------------------------------------------------------------
    def add_add(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:Add", name, properties=properties, actions=actions
        )

    def add_subtract(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:Subtract", name, properties=properties, actions=actions
        )

    def add_multiply(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:Multiply", name, properties=properties, actions=actions
        )

    def add_divide(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:Divide", name, properties=properties, actions=actions
        )

    def add_average(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:Average", name, properties=properties, actions=actions
        )

    def add_minimum(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:Minimum", name, properties=properties, actions=actions
        )

    def add_maximum(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:Maximum", name, properties=properties, actions=actions
        )

    def add_sine_wave(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:SineWave", name, properties=properties, actions=actions
        )

    def add_numeric_latch(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:NumericLatch", name, properties=properties, actions=actions
        )

    def add_boolean_latch(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:BooleanLatch", name, properties=properties, actions=actions
        )

    def add_numeric_delay(
        self,
        name: str,
        update_time: str | int | None = None,
        max_step_size: float | None = None,
        properties: dict | None = None,
    ) -> None:
        props = dict(properties or {})
        if update_time is not None:
            props["updateTime"] = update_time
        if max_step_size is not None:
            props["maxStepSize"] = max_step_size
        self._add_component("kitControl:NumericDelay", name, properties=props)

    def add_boolean_delay(
        self,
        name: str,
        on_delay: str | int | None = None,
        off_delay: str | int | None = None,
        properties: dict | None = None,
    ) -> None:
        props = dict(properties or {})
        if on_delay is not None:
            props["onDelay"] = on_delay
        if off_delay is not None:
            props["offDelay"] = off_delay
        self._add_component("kitControl:BooleanDelay", name, properties=props)

    def add_numeric_const(
        self, name: str, value: float | None = None, properties: dict | None = None
    ) -> None:
        props = dict(properties or {})
        if value is not None:
            props.setdefault("value", value)
        self._add_component("kitControl:NumericConst", name, properties=props)

    def add_boolean_const(
        self, name: str, value: bool | None = None, properties: dict | None = None
    ) -> None:
        props = dict(properties or {})
        if value is not None:
            props.setdefault("value", value)
        self._add_component("kitControl:BooleanConst", name, properties=props)

    def add_enum_const(
        self,
        name: str,
        facets: str | None = None,
        value: str | None = None,
        properties: dict | None = None,
    ) -> None:
        props = dict(properties or {})
        if facets is not None:
            props.setdefault("facets", facets)
        if value is not None:
            props.setdefault("value", value)
        self._add_component("kitControl:EnumConst", name, properties=props)

    def add_tstat(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:Tstat", name, properties=properties, actions=actions
        )

    def add_psychrometric(self, name: str) -> None:
        self._add_component("kitControl:Psychrometric", name)

    def add_reset(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:Reset", name, properties=properties, actions=actions
        )

    def add_one_shot(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:OneShot", name, properties=properties, actions=actions
        )

    def add_lead_lag_cycles(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:LeadLagCycles", name, properties=properties, actions=actions
        )

    def add_lead_lag_runtime(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:LeadLagRuntime", name, properties=properties, actions=actions
        )

    def add_loop_point(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:LoopPoint", name, properties=properties, actions=actions
        )

    def add_equal(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:Equal", name, properties=properties, actions=actions
        )

    def add_not_equal(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:NotEqual", name, properties=properties, actions=actions
        )

    def add_greater_than(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:GreaterThan", name, properties=properties, actions=actions
        )

    def add_greater_than_equal(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:GreaterThanEqual", name, properties=properties, actions=actions
        )

    def add_less_than(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:LessThan", name, properties=properties, actions=actions
        )

    def add_less_than_equal(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:LessThanEqual", name, properties=properties, actions=actions
        )

    def add_and(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:And", name, properties=properties, actions=actions
        )

    def add_or(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:Or", name, properties=properties, actions=actions
        )

    def add_xor(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:Xor", name, properties=properties, actions=actions
        )

    def add_not(
        self, name: str, properties: dict | None = None, actions: dict | None = None
    ) -> None:
        self._add_component(
            "kitControl:Not", name, properties=properties, actions=actions
        )

    # Schedule wrappers
    def add_boolean_schedule(self, name: str, properties: dict) -> None:
        self._add_component("sch:BooleanSchedule", name, properties=properties)

    def add_numeric_schedule(self, name: str, properties: dict) -> None:
        self._add_component("sch:NumericSchedule", name, properties=properties)

    def add_enum_schedule(self, name: str, properties: dict) -> None:
        self._add_component("sch:EnumSchedule", name, properties=properties)

    # ------------------------------------------------------------------
    # Linking
    # ------------------------------------------------------------------
    def add_link(
        self,
        source_comp_name: str,
        source_slot: str,
        target_comp_name: str,
        target_slot: str,
        *,
        link_type: str | None = None,  # Allow None to let the method decide
        converter_type: str | None = None,
    ) -> None:
        """
        Adds a validated link between two components, automatically handling
        required type conversions.
        """
        # --- 1. Basic Validation ---
        if source_comp_name not in self._components:
            raise ValueError(f"Source component '{source_comp_name}' not found.")
        if target_comp_name not in self._components:
            raise ValueError(f"Target component '{target_comp_name}' not found.")

        s_type = self._components[source_comp_name].get("type", "")
        t_type = self._components[target_comp_name].get("type", "")

        # --- 2. Determine Source and Target Data Types ---
        source_data_type = COMPONENT_OUTPUT_TYPE.get(s_type)
        target_data_type = SLOT_TYPE_MAPPING.get((t_type, target_slot))

        # If target isn't in our special map, infer its type.
        if not target_data_type:
            # If the target slot is a known boolean trigger, explicitly set its type
            if target_slot in ("countUp", "countDown", "clear", "preset"):
                target_data_type = "StatusBoolean"
            # Fallback for other unknown types remains numeric
            else:
                target_data_type = "StatusNumeric"

        # --- 3. Check for Mismatch and Find Converter ---
        # Set a default link_type if none was provided
        final_link_type = link_type if link_type is not None else "b:Link"
        final_converter_type = converter_type

        # If a manual converter was provided, use it.
        if final_converter_type:
            final_link_type = "b:ConversionLink"
        # Otherwise, if types are known and different, try to find an automatic converter.
        elif (
            source_data_type
            and target_data_type
            and source_data_type != target_data_type
        ):
            converter_key = (source_data_type, target_data_type)
            found_converter = CONVERSION_MAP.get(converter_key)

            if found_converter:
                final_link_type = "b:ConversionLink"
                final_converter_type = found_converter
                if self.debug:
                    print(
                        f"[BOG BUILDER DEBUG] Auto-applying '{final_converter_type}' for link "
                        f"{source_comp_name}.{source_slot} ({source_data_type}) -> "
                        f"{target_comp_name}.{target_slot} ({target_data_type})."
                    )
            else:
                # EXCEPTION HANDLING: If types mismatch and no converter is found, raise an error.
                raise TypeError(
                    (
                        f"Type mismatch: Cannot link '{source_comp_name}' (output: {source_data_type}) "
                        f"to '{target_comp_name}.{target_slot}' (expects: {target_data_type}). "
                        f"No automatic converter found in CONVERSION_MAP.",
                        "Check models.py for the CONVERSION_MAP and SLOT_TYPE_MAPPING.",
                    )
                )

        # --- 4. Store the Link ---
        link_data = {
            "source_name": source_comp_name,
            "source_slot": source_slot,
            "target_name": target_comp_name,
            "target_slot": target_slot,
            "link_type": final_link_type,
            "converter_type": final_converter_type,
        }
        self._links.append(link_data)

    # ------------------------------------------------------------------
    # Reduction blocks
    # ------------------------------------------------------------------
    def add_reduction_block(
        self,
        block_type: str,
        final_output_name: str,
        input_names: List[str],
    ) -> None:
        """Constructs a reduction tree (Average/Minimum/Maximum) from multiple inputs.

        The reduction logic splits the inputs into manageable chunks, creates
        tiers of comparison or aggregation blocks, and finally writes the result
        to a new writable component.  Input validation ensures the block type,
        final output name and input names are well‑formed and that all
        referenced inputs exist within the builder state.

        Raises
        ------
        ValueError
            If the block type or names are invalid, if inputs are missing, or
            if the output name already exists.
        """
        try:
            red_def = ReductionBlockDefinition(
                block_type=block_type,
                final_output_name=final_output_name,
                input_names=input_names,
            )
        except ValidationError as ve:
            raise ValueError(str(ve)) from ve
        for inp in red_def.input_names:
            if inp not in self._components:
                raise ValueError(
                    f"Reduction block input '{inp}' does not exist. All inputs must refer to existing components."
                )
        if red_def.final_output_name in self._components:
            raise ValueError(
                f"A component with the name '{red_def.final_output_name}' already exists. The final output name must be unique."
            )
        MAX_INPUTS = 4
        tier = 1
        current_inputs = list(red_def.input_names)
        self.start_sub_folder(f"{red_def.block_type}Calc")
        while len(current_inputs) > MAX_INPUTS:
            tier_outputs: List[str] = []
            for i in range(0, len(current_inputs), MAX_INPUTS):
                chunk = current_inputs[i : i + MAX_INPUTS]
                node_name = f"{red_def.block_type}_T{tier}_{i // MAX_INPUTS}"
                self._add_component(f"kitControl:{red_def.block_type}", node_name)
                for j, input_name in enumerate(chunk):
                    self.add_link(input_name, "out", node_name, f"in{chr(65 + j)}")
                tier_outputs.append(node_name)
            current_inputs = tier_outputs
            tier += 1
        final_block = f"{red_def.block_type}_T{tier}_final"
        self._add_component(f"kitControl:{red_def.block_type}", final_block)
        for j, input_name in enumerate(current_inputs):
            self.add_link(input_name, "out", final_block, f"in{chr(65 + j)}")
        self.end_sub_folder()
        self.add_numeric_writable(name=red_def.final_output_name)
        self.add_link(final_block, "out", red_def.final_output_name, "in16")

    # ------------------------------------------------------------------
    # Saving
    # ------------------------------------------------------------------
    def save(self, file_path: str) -> None:
        """Constructs the XML and saves it to a `.bog` file.

        A valid Niagara `.bog` file is essentially a zip archive containing a
        single XML file named ``file.xml``.  This method serialises the XML
        representation of the current graph and writes it into a zip file at
        the specified path.  A ``.bog`` extension is required to ensure
        compatibility with Niagara Workbench.

        Raises
        ------
        ValueError
            If the ``file_path`` does not end with '.bog'.
        OSError
            If there is an error writing the file.
        """
        if not isinstance(file_path, str) or not file_path.lower().endswith(".bog"):
            raise ValueError(
                f"Output file '{file_path}' must have a '.bog' extension to be recognised by Niagara. Try again with a .bog in the extension name."
            )
        final_xml_root = self._build_xml_recursive()
        rough_string = ET.tostring(final_xml_root, "utf-8")
        reparsed = minidom.parseString(rough_string)
        pretty_string = reparsed.toprettyxml(indent="  ", encoding="utf-8")
        try:
            with zipfile.ZipFile(file_path, "w") as bog_zip:
                bog_zip.writestr("file.xml", pretty_string)
        except Exception as exc:
            raise OSError(f"Failed to write .bog file '{file_path}': {exc}") from exc    # ---
---------------------------------------------------------------
    # XML construction helpers
    # ------------------------------------------------------------------
    def _build_xml_recursive(self) -> ET.Element:
        """Builds the entire XML structure, starting from the root."""
        root = ET.Element(
            "bajaObjectGraph",
            {
                "version": "4.0",
                "reversibleEncodingKeySource": "none",
                "FIPSEnabled": "false",
                "reversibleEncodingValidator": "[null.1]",
            },
        )
        unrestricted_folder = ET.SubElement(
            root, "p", {"t": "b:UnrestrictedFolder", "m": "b=baja"}
        )
        self._build_folder_contents(unrestricted_folder, (self.folder_name,))
        return root

    def _build_folder_contents(
        self, parent_xml_element: ET.Element, folder_path_tuple: Tuple[str, ...]
    ) -> None:
        """Build XML for a single folder. Top-level:
        - no subfolders  -> tiered layout (place all logic)
        - has subfolders -> Inputs | Folders | Outputs layout
        Subfolders: always tiered.
        """
        folder_name = folder_path_tuple[-1]
        self.log(
            f"--- Building folder: {'/'.join(folder_path_tuple)} ---",
            is_layout_log=True,
        )
        folder_element = ET.SubElement(
            parent_xml_element, "p", {"n": folder_name, "t": "b:Folder"}
        )

        components_in_folder = {
            name: data
            for name, data in self._components.items()
            if self._component_to_folder.get(name) == folder_path_tuple
        }

        if len(folder_path_tuple) == 1:
            sub_folders_in_this_view = self._sub_folders.get(folder_path_tuple, [])
            if not sub_folders_in_this_view:
                levels = self._calculate_levels(components_in_folder)
                comp_coords = self._position_components_normally(levels)
            else:
                comp_coords = self._position_top_level_interface(
                    components_in_folder, sub_folders_in_this_view
                )
                for sf in sub_folders_in_this_view:
                    if sf in comp_coords:
                        x, _y = comp_coords[sf]
                        comp_coords[sf] = (x, self.START_Y)
        else:
            levels = self._calculate_levels(components_in_folder)
            comp_coords = self._position_components_normally(levels)

        self._add_component_xml_tags(folder_element, components_in_folder, comp_coords)

        links_targeting_this_folder = [
            l
            for l in self._links
            if self._component_to_folder.get(l["target_name"]) == folder_path_tuple
        ]
        self._add_link_xml_tags(folder_element, links_targeting_this_folder)

        # Recurse into subfolders
        for sub_folder_name in self._sub_folders.get(folder_path_tuple, []):
            self.log(
                f"About to recurse into sub-folder: {sub_folder_name}",
                is_layout_log=True,
            )
            self._build_folder_contents(
                folder_element, folder_path_tuple + (sub_folder_name,)
            )

    def _position_top_level_interface(
        self, components: Dict[str, Dict], sub_folders: List[str]
    ) -> Dict[str, Tuple[int, int]]:
        """
        Special layout for the root folder with column wrapping.
        Layout: Outputs (left, wraps) | Folders (center) | Inputs (right, wraps).
        """
        self.log("Using TOP-LEVEL interface layout.", is_layout_log=True)
        coords: Dict[str, Tuple[int, int]] = {}
        inputs: List[str] = []
        outputs: List[str] = []
        MAX_ITEMS_PER_COLUMN = 150

        all_links_sources = {l["source_name"] for l in self._links}
        all_links_targets = {l["target_name"] for l in self._links}
        for name, data in components.items():
            if data.get("type") == "folder":
                continue
            is_target = name in all_links_targets
            is_source = name in all_links_sources
            if is_target and not is_source:
                inputs.append(name)
            elif is_source and not is_target:
                outputs.append(name)
            else:
                outputs.append(name)

        self.log(f"Categorised as INPUTS: {sorted(inputs)}", is_layout_log=True)
        self.log(f"Categorisd as OUTPUTS: {sorted(outputs)}", is_layout_log=True)
        self.log(f"Found SUB-FOLDERS: {sorted(sub_folders)}", is_layout_log=True)

        # --- Position Outputs with wrapping ---
        x = self.START_X
        y = self.START_Y
        for i, name in enumerate(sorted(outputs)):
            if i > 0 and i % MAX_ITEMS_PER_COLUMN == 0:
                x += self.X_COLUMN_WIDTH
                y = self.START_Y
            coords[name] = (x, y)
            self.log(
                f"Positioned OUTPUT '{name}' at {coords[name]}", is_layout_log=True
            )
            y += self.Y_INCREMENT

        num_output_cols = (len(outputs) - 1) // MAX_ITEMS_PER_COLUMN + 1
        folder_x_start = self.START_X + (num_output_cols * self.X_COLUMN_WIDTH)

        # Position folders horizontally
        x = folder_x_start
        y = self.START_Y
        for name in sorted(sub_folders):
            coords[name] = (x, y)
            self.log(
                f"Positioned FOLDER '{name}' at {coords[name]}", is_layout_log=True
            )
            x += self.X_COLUMN_WIDTH  # Correctly increment X for horizontal layout

        # Calculate input start position after all folder columns
        num_folder_cols = len(sub_folders)
        input_x_start = folder_x_start + (num_folder_cols * self.X_COLUMN_WIDTH)

        # Position Inputs with wrapping
        x = input_x_start
        y = self.START_Y
        for i, name in enumerate(sorted(inputs)):
            if i > 0 and i % MAX_ITEMS_PER_COLUMN == 0:
                x += self.X_COLUMN_WIDTH
                y = self.START_Y
            coords[name] = (x, y)
            self.log(f"Positioned INPUT '{name}' at {coords[name]}", is_layout_log=True)
            y += self.Y_INCREMENT

        return coords

    def _position_components_normally(
        self, levels: List[List[str]]
    ) -> Dict[str, Tuple[int, int]]:
        """Calculates X,Y coordinates for components inside a logic folder."""
        self.log(
            f"Using NORMAL component layout across {len(levels)} tiers.",
            is_layout_log=True,
        )
        comp_coords: Dict[str, Tuple[int, int]] = {}
        current_x = self.START_X
        for i, level in enumerate(levels):
            y_pos = self.START_Y
            self.log(
                f"  Positioning Tier {i + 1} with {len(level)} components.",
                is_layout_log=True,
            )
            for name in level:
                comp_coords[name] = (current_x, y_pos)
                y_pos += self.Y_INCREMENT
            current_x += self.X_COLUMN_WIDTH
        return comp_coords

    def _calculate_levels(
        self, components_in_scope: Dict[str, Dict]
    ) -> List[List[str]]:
        """
        Perform a rudimentary topological sort to group components into tiers.

        Components are assigned to tiers based on their data‑flow dependencies.
        If a complete DAG cannot be obtained (e.g. cycles exist), any components
        that are not visited by the topological pass are collected into an
        additional tier.  This prevents components involved in feedback loops
        from all being placed at the same coordinates (0,0) and at least
        separates them vertically.
        """
        in_degree: Dict[str, int] = {name: 0 for name in components_in_scope}
        adj: Dict[str, List[str]] = defaultdict(list)
        # Build adjacency and in‑degree counts for links internal to this scope
        for link in self._links:
            source, target = link["source_name"], link["target_name"]
            if source in components_in_scope and target in components_in_scope:
                adj[source].append(target)
                in_degree[target] += 1
        # Initialise queue with nodes that have no inbound edges
        queue: deque[str] = deque([name for name, deg in in_degree.items() if deg == 0])
        levels: List[List[str]] = []
        visited: set[str] = set()
        while queue:
            level_size = len(queue)
            current_level: List[str] = []
            for _ in range(level_size):
                u = queue.popleft()
                if u in visited:
                    continue
                visited.add(u)
                current_level.append(u)
                for v in sorted(adj.get(u, [])):
                    in_degree[v] -= 1
                    if in_degree[v] == 0:
                        queue.append(v)
            if current_level:
                levels.append(current_level)
        # If cycles exist, some components won't be visited; group them into the last tier
        remaining = [name for name in components_in_scope if name not in visited]
        if remaining:
            # Sort remaining for deterministic placement
            levels.append(sorted(remaining))
        return levels

    def _add_component_xml_tags(
        self,
        folder_element: ET.Element,
        components: Dict[str, Dict],
        coords: Dict[str, Tuple[int, int]],
    ) -> None:

        def _write_facets_if_enum(element, enum_range):
            # enum_range may be dict {"Occupied":0, ...} or already a "E:{...}" string
            if isinstance(enum_range, dict):
                pairs = ",".join(f"{k}={v}" for k, v in enum_range.items())
                v = f"range=E:{{{pairs}}}"
            else:
                s = str(enum_range)
                v = (
                    s
                    if s.startswith("range=E:{") and s.endswith("}")
                    else f"range=E:{s if s.startswith('{') else '{'+s+'}'}"
                )
            ET.SubElement(element, "p", {"n": "facets", "t": "b:Facets", "v": v})

        def _encode_dynamic_enum(value_index, enum_range):
            # enum_range may be dict or "{A=0,B=1}" string
            if isinstance(enum_range, dict):
                pairs = ",".join(f"{k}={v}" for k, v in enum_range.items())
                range_str = f"{{{pairs}}}"
            else:
                s = str(enum_range)
                # normalize: ensure single enclosing braces only
                range_str = (
                    s
                    if (s.startswith("{") and s.endswith("}"))
                    else "{" + s.strip("{}") + "}"
                )
            return f"{int(value_index)}@{range_str}"  # <-- no extra brace!

        """Adds the <p> tags for components to the XML tree."""
        for name, data in components.items():
            attrs = {"n": name, "t": data["type"], "h": data["handle"]}
            if ":" in data["type"]:
                prefix = data["type"].split(":")[0]
                if prefix == "sch":
                    attrs["m"] = "sch=schedule"
                else:
                    attrs["m"] = f"{prefix}={prefix}"
            element = ET.SubElement(folder_element, "p", attrs)

            if data["type"] == "control:NumericWritable":
                default_val = data["properties"].get("defaultValue", 0.0)
                out_slot = ET.SubElement(
                    element, "p", {"n": "out", "f": "s", "t": "b:StatusNumeric"}
                )
                ET.SubElement(out_slot, "p", {"n": "value", "v": str(default_val)})
                ET.SubElement(
                    out_slot,
                    "p",
                    {"n": "status", "v": "0;activeLevel=e:17@control:PriorityLevel"},
                )
                fallback_slot = ET.SubElement(
                    element, "p", {"n": "fallback", "t": "b:StatusNumeric"}
                )
                ET.SubElement(fallback_slot, "p", {"n": "value", "v": str(default_val)})
                facets_prop = data["properties"].get("facets")
                if (
                    isinstance(facets_prop, dict)
                    and facets_prop.get("type") == "b:Facets"
                ):
                    ET.SubElement(
                        element,
                        "p",
                        {
                            "n": "facets",
                            "t": "b:Facets",
                            "v": str(facets_prop.get("value", "")),
                        },
                    )
                elif isinstance(facets_prop, str):
                    ET.SubElement(
                        element,
                        "p",
                        {"n": "facets", "t": "b:Facets", "v": facets_prop},
                    )
                ET.SubElement(element, "p", {"n": "in16", "f": "tsL"})
            elif data["type"] == "control:BooleanWritable":
                fallback_prop = data["properties"].get("fallback", {})
                fallback_val = fallback_prop.get("value", "false")
                fallback_slot = ET.SubElement(
                    element, "p", {"n": "fallback", "t": "b:StatusBoolean"}
                )
                ET.SubElement(
                    fallback_slot, "p", {"n": "value", "v": str(fallback_val).lower()}
                )

            elif data["type"] == "kitControl:NumericConst":
                out = ET.SubElement(element, "p", {"n": "out", "t": "b:StatusNumeric"})
                props = data.get("properties", {})
                val = props.get("value")
                if val is None:
                    out_prop = props.get("out")
                    if isinstance(out_prop, dict):
                        val = out_prop.get("value", 0.0)
                    elif out_prop is not None:
                        val = out_prop
                    else:
                        val = 0.0
                ET.SubElement(out, "p", {"n": "value", "v": str(val)})

            elif data["type"] == "kitControl:BooleanConst":
                out = ET.SubElement(element, "p", {"n": "out", "t": "b:StatusBoolean"})
                val = data["properties"].get(
                    "value", data["properties"].get("out", {}).get("value", False)
                )
                ET.SubElement(out, "p", {"n": "value", "v": str(bool(val)).lower()})

            else:
                for prop_name, prop_value in data["properties"].items():
                    ET.SubElement(element, "p", {"n": prop_name, "v": str(prop_value)})

            x, y = coords.get(name, (self.START_X, self.START_Y))
            ET.SubElement(
                element,
                "p",
                {
                    "n": "wsAnnotation",
                    "t": "b:WsAnnotation",
                    "v": f"{int(x)},{int(y)},8",
                },
            )

    def _add_link_xml_tags(self, folder_element: ET.Element, links: List[Dict]) -> None:
        """Adds nested link tags for all links targeting components in this folder."""
        from collections import defaultdict

        link_counters: Dict[str, int] = defaultdict(int)
        for link in links:
            target_name = link["target_name"]
            target_handle = self._handle_map.get(target_name)
            if not target_handle:
                continue
            target_element = folder_element.find(f"./p[@h='{target_handle}']")
            if target_element is None:
                continue
            count = link_counters[target_name]
            link_name = "Link" if count == 0 else f"Link{count}"
            link_counters[target_name] += 1
            link_type = link.get("link_type", "b:Link")
            link_element = ET.SubElement(
                target_element, "p", {"n": link_name, "t": link_type}
            )
            ET.SubElement(
                link_element,
                "p",
                {"n": "sourceOrd", "v": f"h:{self._handle_map[link['source_name']]}"},
            )
            ET.SubElement(link_element, "p", {"n": "relationTags", "v": ""})
            ET.SubElement(link_element, "p", {"n": "relationId", "v": "n:dataLink"})
            ET.SubElement(
                link_element, "p", {"n": "sourceSlotName", "v": link["source_slot"]}
            )
            ET.SubElement(
                link_element, "p", {"n": "targetSlotName", "v": link["target_slot"]}
            )
            conv_type = link.get("converter_type")
            if conv_type:
                ET.SubElement(
                    link_element,
                    "p",
                    {
                        "n": "converter",
                        "m": "conv=converters",
                        "t": conv_type,
                    },
                )