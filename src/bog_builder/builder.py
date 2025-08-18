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
from typing import Dict, List, Tuple

from pydantic import ValidationError

from .models import (
    COMPONENT_SLOT_MAP,
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
        # Global registry of components: name -> data dict
        self._components: Dict[str, Dict] = {}
        # Global link list. Each element is a dict describing a link
        self._links: List[Dict] = []
        # Generate unique handles for each component
        self._next_handle = 1
        self._handle_map: Dict[str, str] = {}
        # Hierarchy of sub‑folders: parent_path -> [child_folder_names]
        self._sub_folders: Dict[Tuple[str, ...], List[str]] = defaultdict(list)
        # Map component_name -> folder_path tuple
        self._component_to_folder: Dict[str, Tuple[str, ...]] = {}
        # Current folder context
        self._current_folder_path: Tuple[str, ...] = (folder_name,)
        # Layout constants for positioning components in the workspace
        self.START_X = 10
        self.START_Y = 10
        self.X_COLUMN_WIDTH = 20  # Increased for better visual separation
        self.Y_INCREMENT = 15  # Increased for better visual separation

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
        # Validate the folder name format
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
        # Ensure the sub‑folder does not already exist at this level
        if name in self._sub_folders.get(parent_path, []):
            raise ValueError(
                f"A sub‑folder named '{name}' already exists under '{self.get_current_path_str()}'. "
                f"Choose a unique sub‑folder name."
            )
        # Append the folder and update the context
        self._sub_folders[parent_path].append(name)
        self._current_folder_path = parent_path + (name,)

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
        # Move back up one level
        self._current_folder_path = self._current_folder_path[:-1]

    def get_current_path_str(self) -> str:
        """Returns the current folder path as a string separated by `/`."""
        return "/".join(self._current_folder_path)

    # ------------------------------------------------------------------
    # Component creation
    # ------------------------------------------------------------------
    def add_component(
        self,
        comp_type: str,
        name: str,
        properties: dict | None = None,
        actions: dict | None = None,
    ) -> None:
        """Registers a component in the current folder context with strict validation.

        This method validates the component definition using a Pydantic model.  It
        enforces naming conventions (names cannot start with a number and must be
        composed of letters, digits and underscores) and ensures the component
        type follows the expected "palette:TypeName" format.  Time‑based
        properties (e.g. 'onDelay', 'offDelay', 'period') are automatically
        converted to millisecond strings if supplied in a human‑friendly format
        ("1m" -> "60000").

        Raises
        ------
        ValueError
            If the component definition is invalid or if the name already exists in
            the current builder state.
        """
        # Default values for optional dicts
        properties = properties or {}
        actions = actions or {}
        # Validate and normalise the component using Pydantic
        try:
            comp_def = ComponentDefinition(
                comp_type=comp_type,
                name=name,
                properties=properties,
                actions=actions,
            )
        except ValidationError as ve:
            # Propagate a human‑readable error message so an LLM can act upon it
            raise ValueError(str(ve)) from ve
        # Check for duplicate component names
        if comp_def.name in self._components:
            raise ValueError(
                f"Component with name '{comp_def.name}' already exists. Each component must have a unique name."
            )
        # Convert human‑friendly time values in properties to milliseconds
        normalized_props: dict = {}
        for prop_name, prop_value in comp_def.properties.items():
            # Only convert delay/period related properties; leave others untouched
            if any(keyword in prop_name.lower() for keyword in ("delay", "period")):
                normalized_props[prop_name] = _parse_time_to_ms(prop_value)
            else:
                normalized_props[prop_name] = prop_value
        # Warn if this component type is unknown (no slot map defined)
        if comp_def.comp_type not in COMPONENT_SLOT_MAP and self.debug:
            print(
                f"[BOG VALIDATION WARNING] Component type '{comp_def.comp_type}' is not in the known slot map. "
                f"Slot name validation will be skipped for this component."
            )
        # Assign a unique handle and register the component
        handle = self._get_next_handle()
        self._handle_map[comp_def.name] = handle
        self._components[comp_def.name] = {
            "type": comp_def.comp_type,
            "properties": normalized_props,
            "actions": comp_def.actions,
            "handle": handle,
        }
        self._component_to_folder[comp_def.name] = self._current_folder_path

    # Helper methods for common component types
    def add_numeric_writable(
        self,
        name: str,
        default_value: float = 0.0,
        precision: int = 2,
        units: str = "u:null",
    ) -> None:
        """Add a NumericWritable with sensible default facets."""
        facets_value = (
            f"units={units};;;;|precision=i:{precision}|min=d:-inf|max=d:+inf"
        )
        self.add_component(
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
        self.add_component(
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
        # Normalise the default value: allow either "3@{...}" strings or plain
        # integers (converted to string).  Do not wrap in a dict so the
        # ``control:EnumWritable`` property writer will interpret it as a
        # literal value string.
        dv = default_value if isinstance(default_value, str) else str(default_value)
        self.add_component(
            "control:EnumWritable",
            name,
            properties={
                "facets": facets,
                "fallback": {"value": dv},
            },
        )

    def add_numeric_switch(self, name: str) -> None:
        """Add a kitControl NumericSwitch component."""
        self.add_component("kitControl:NumericSwitch", name)

    def add_numeric_select(self, name: str) -> None:
        """Adds a NumericSelect component with default 10 inputs (A‑J)."""
        self.add_component(
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
        self.add_component(
            "kitControl:MultiVibrator", name, properties={"period": str(period_ms)}
        )

    def add_counter(
        self,
        name: str,
        count_increment: float = 1.0,
        initial_value: float = 0.0,
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
        initial_value : float, optional
            The initial value of the counter when created.
        precision : int or None, optional
            Optional precision for display; if provided, it is rounded to an
            integer.
        properties : dict or None, optional
            Additional properties to set on the counter; keys in this dict will
            override default values for ``countIncrement`` and ``initialValue``.
        """
        props = dict(properties or {})
        props.setdefault("countIncrement", count_increment)
        props.setdefault("initialValue", initial_value)
        if precision is not None:
            props["precision"] = int(precision)
        self.add_component("kitControl:Counter", name, properties=props)

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
        link_type: str = "b:Link",
        converter_type: str | None = None,
    ) -> None:
        """Adds a validated link between two components.

        This method checks that the source and target components exist, validates
        the format of the link via a Pydantic model, and ensures that slot names
        match the expected inputs/outputs for the respective component types when
        a slot map is available.  If the link crosses a folder boundary, a flag
        is stored on the link record for annotation.

        Raises
        ------
        ValueError
            If the link definition or slot names are invalid, or if either
            component cannot be found.
        """
        # Validate the structure of the link
        try:
            link_def = LinkDefinition(
                source_name=source_comp_name,
                source_slot=source_slot,
                target_name=target_comp_name,
                target_slot=target_slot,
            )
        except ValidationError as ve:
            raise ValueError(str(ve)) from ve
        # Ensure both components exist in the registry
        if link_def.source_name not in self._components:
            raise ValueError(
                f"Source component '{link_def.source_name}' not found. Make sure it is created before linking."
            )
        if link_def.target_name not in self._components:
            raise ValueError(
                f"Target component '{link_def.target_name}' not found. Make sure it is created before linking."
            )
        s_type = self._components[link_def.source_name]["type"]
        t_type = self._components[link_def.target_name]["type"]
        s_slots = COMPONENT_SLOT_MAP.get(s_type)
        t_slots = COMPONENT_SLOT_MAP.get(t_type)
        # Validate the source slot against known outputs, if mapping exists
        if s_slots and link_def.source_slot not in s_slots.get("outputs", []):
            raise ValueError(
                f"Invalid source slot '{link_def.source_slot}' for component '{link_def.source_name}' of type '{s_type}'. "
                f"Valid output slots: {s_slots['outputs']}"
            )
        # Validate the target slot against known inputs, if mapping exists
        if t_slots:
            # Only validate target slots if the component definition includes
            # an "inputs" list.  For components like NumericWritable and
            # BooleanWritable we omit the "inputs" key entirely, meaning any
            # input (in1, in10, etc.) is acceptable.  If an inputs list is
            # present but empty, skip validation as well since it signals
            # unbounded input names.
            if "inputs" in t_slots:
                valid_inputs = t_slots.get("inputs", [])
                # If no valid inputs are specified, don't perform validation
                if valid_inputs and link_def.target_slot not in valid_inputs:
                    raise ValueError(
                        f"Invalid target slot '{link_def.target_slot}' for component '{link_def.target_name}' of type '{t_type}'. "
                        f"Valid input slots: {valid_inputs}"
                    )
        # Determine whether the link crosses folder boundaries
        same_folder = (
            self._component_to_folder[link_def.source_name]
            == self._component_to_folder[link_def.target_name]
        )
        # Create the link using heuristics to determine conversion if no explicit converter
        self._add_direct_link(
            link_def.source_name,
            link_def.source_slot,
            link_def.target_name,
            link_def.target_slot,
        )
        # Override the link type or converter type if explicitly provided.  The
        # `_add_direct_link` helper always appends the new link to
        # ``self._links``, so we modify the last entry accordingly.  If the
        # caller specifies a conversion link explicitly, the heuristics are
        # superseded.
        if link_type != "b:Link" or converter_type is not None:
            self._links[-1]["link_type"] = link_type
            self._links[-1]["converter_type"] = converter_type
        # Attach a cross‑folder flag if necessary
        if not same_folder:
            self._links[-1]["cross_folder"] = True

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
        # Validate the reduction definition
        try:
            red_def = ReductionBlockDefinition(
                block_type=block_type,
                final_output_name=final_output_name,
                input_names=input_names,
            )
        except ValidationError as ve:
            raise ValueError(str(ve)) from ve
        # Check that all input names exist
        for inp in red_def.input_names:
            if inp not in self._components:
                raise ValueError(
                    f"Reduction block input '{inp}' does not exist. All inputs must refer to existing components."
                )
        # Ensure the final output name is unique
        if red_def.final_output_name in self._components:
            raise ValueError(
                f"A component with the name '{red_def.final_output_name}' already exists. The final output name must be unique."
            )
        # Build the reduction tree
        MAX_INPUTS = 4
        tier = 1
        current_inputs = list(red_def.input_names)
        # Create a dedicated subfolder for the reduction logic to avoid clutter
        self.start_sub_folder(f"{red_def.block_type}Calc")
        while len(current_inputs) > MAX_INPUTS:
            tier_outputs: List[str] = []
            for i in range(0, len(current_inputs), MAX_INPUTS):
                chunk = current_inputs[i : i + MAX_INPUTS]
                node_name = f"{red_def.block_type}_T{tier}_{i // MAX_INPUTS}"
                self.add_component(f"kitControl:{red_def.block_type}", node_name)
                for j, input_name in enumerate(chunk):
                    self.add_link(input_name, "out", node_name, f"in{chr(65 + j)}")
                tier_outputs.append(node_name)
            current_inputs = tier_outputs
            tier += 1
        # Build the final block in the last tier
        final_block = f"{red_def.block_type}_T{tier}_final"
        self.add_component(f"kitControl:{red_def.block_type}", final_block)
        for j, input_name in enumerate(current_inputs):
            self.add_link(input_name, "out", final_block, f"in{chr(65 + j)}")
        # Close the subfolder to return to the original context
        self.end_sub_folder()
        # Create the final output writable and wire the final reduction result to it
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
                f"Output file '{file_path}' must have a '.bog' extension to be recognised by Niagara."
            )
        # Build the XML structure
        final_xml_root = self._build_xml_recursive()
        rough_string = ET.tostring(final_xml_root, "utf-8")
        reparsed = minidom.parseString(rough_string)
        pretty_string = reparsed.toprettyxml(indent="  ", encoding="utf-8")
        # Write the XML into a zip archive
        try:
            with zipfile.ZipFile(file_path, "w") as bog_zip:
                bog_zip.writestr("file.xml", pretty_string)
        except Exception as exc:
            raise OSError(f"Failed to write .bog file '{file_path}': {exc}") from exc

    # ------------------------------------------------------------------
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
        """Builds the XML for a single folder, flattening only sub‑folder icons at the top level."""
        folder_name = folder_path_tuple[-1]
        self.log(
            f"--- Building folder: {'/'.join(folder_path_tuple)} ---",
            is_layout_log=True,
        )
        # Create XML <p> element for this folder
        folder_element = ET.SubElement(
            parent_xml_element, "p", {"n": folder_name, "t": "b:Folder"}
        )
        # Get all components assigned to this folder
        components_in_folder = {
            name: data
            for name, data in self._components.items()
            if self._component_to_folder.get(name) == folder_path_tuple
        }
        if len(folder_path_tuple) == 1:
            # TOP LEVEL: position inputs, outputs, and subfolder icons
            sub_folders_in_this_view = self._sub_folders.get(folder_path_tuple, [])
            comp_coords = self._position_top_level_interface(
                components_in_folder, sub_folders_in_this_view
            )
            # Flatten Y only for sub‑folder icons at top level
            for sf in sub_folders_in_this_view:
                if sf in comp_coords:
                    old_x, old_y = comp_coords[sf]
                    comp_coords[sf] = (old_x, self.START_Y)
        else:
            # LOGIC SUBFOLDER: normal tiered layout
            levels = self._calculate_levels(components_in_folder)
            comp_coords = self._position_components_normally(levels)
        # Add components with wsAnnotation tags
        self._add_component_xml_tags(folder_element, components_in_folder, comp_coords)
        # Add links targeting this folder
        links_targeting_this_folder = [
            l
            for l in self._links
            if self._component_to_folder.get(l["target_name"]) == folder_path_tuple
        ]
        self._add_link_xml_tags(folder_element, links_targeting_this_folder)
        # Recurse into subfolders
        for sub_folder_name in self._sub_folders.get(folder_path_tuple, []):
            self.log(
                f"About to recurse into sub‑folder: {sub_folder_name}",
                is_layout_log=True,
            )
            self._build_folder_contents(
                folder_element, folder_path_tuple + (sub_folder_name,)
            )

    def _position_top_level_interface(
        self, components: Dict[str, Dict], sub_folders: List[str]
    ) -> Dict[str, Tuple[int, int]]:
        """Special layout for the root folder: Inputs (left) | Folders (center) | Outputs (right)."""
        self.log("Using TOP‑LEVEL interface layout.", is_layout_log=True)
        coords: Dict[str, Tuple[int, int]] = {}
        inputs: List[str] = []
        outputs: List[str] = []
        all_links_sources = {l["source_name"] for l in self._links}
        all_links_targets = {l["target_name"] for l in self._links}
        # Categorise components
        for name, data in components.items():
            if (
                data["type"].endswith("Writable")
                and name in all_links_targets
                and name not in all_links_sources
            ):
                outputs.append(name)
            elif data["type"].endswith("Writable"):
                inputs.append(name)
        self.log(f"Categorised as INPUTS: {sorted(inputs)}", is_layout_log=True)
        self.log(f"Categorised as OUTPUTS: {sorted(outputs)}", is_layout_log=True)
        self.log(f"Found SUB‑FOLDERS: {sorted(sub_folders)}", is_layout_log=True)
        # Place INPUTS (left column)
        y = self.START_Y
        for name in sorted(inputs):
            coords[name] = (self.START_X, y)
            self.log(
                f"Positioned INPUT '{name}' at ({coords[name][0]}, {coords[name][1]})",
                is_layout_log=True,
            )
            y += self.Y_INCREMENT
        # Place SUB‑FOLDERS (middle column, flat at START_Y)
        folder_x = self.START_X + self.X_COLUMN_WIDTH * 3
        for folder_name in sorted(sub_folders):
            coords[folder_name] = (folder_x, self.START_Y)
            self.log(
                f"Positioned FOLDER '{folder_name}' flat at ({coords[folder_name][0]}, {coords[folder_name][1]})",
                is_layout_log=True,
            )
        # Place OUTPUTS (right column)
        y = self.START_Y
        output_x = self.START_X + self.X_COLUMN_WIDTH * 3
        for name in sorted(outputs):
            coords[name] = (output_x, y)
            self.log(
                f"Positioned OUTPUT '{name}' at ({coords[name][0]}, {coords[name][1]})",
                is_layout_log=True,
            )
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
        """Performs a topological sort to determine the layout tiers."""
        in_degree = {name: 0 for name in components_in_scope}
        adj: Dict[str, List[str]] = defaultdict(list)
        for link in self._links:
            source, target = link["source_name"], link["target_name"]
            if source in components_in_scope and target in components_in_scope:
                adj[source].append(target)
                in_degree[target] += 1
        queue: deque[str] = deque(
            [name for name in components_in_scope if in_degree[name] == 0]
        )
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
                for v in sorted(adj[u]):
                    in_degree[v] -= 1
                    if in_degree[v] == 0:
                        queue.append(v)
            if current_level:
                levels.append(current_level)
        return levels

    def _add_direct_link(
        self, source_name: str, source_slot: str, target_name: str, target_slot: str
    ) -> None:
        """Internal helper to register a link with optional type conversions."""
        s_type = self._components[source_name]["type"]
        t_type = self._components[target_name]["type"]
        link_type = "b:Link"
        converter_type = None

        # Helpers to determine whether a slot expects boolean or numeric values
        def target_is_boolean_like(t: str, slot: str) -> bool:
            # Boolean blocks / slots that expect boolean input
            if t in (
                "kitControl:And",
                "kitControl:Or",
                "kitControl:Xor",
                "kitControl:BooleanDelay",
                "kitControl:OneShot",
            ):
                return True
            # NumericSwitch inSwitch is boolean
            if t == "kitControl:NumericSwitch" and slot == "inSwitch":
                return True
            return False

        def target_is_numeric_like(t: str, slot: str) -> bool:
            # Numeric math / clamp blocks or numeric inputs
            if t.startswith("kitControl:") and t.split(":")[1] in (
                "Add",
                "Subtract",
                "Multiply",
                "Divide",
                "Average",
                "Minimum",
                "Maximum",
            ):
                return True
            # Generic heuristic: many kitControl numeric blocks use StatusNumeric on 'in*'
            return "Numeric" in t

        # 1) Enum case: NumericSelect.select expects enum (from numeric)
        if t_type == "kitControl:NumericSelect" and target_slot == "select":
            link_type = "b:ConversionLink"
            converter_type = "conv:StatusNumericToStatusEnum"
        # 2) Boolean → Numeric ONLY when target is numeric‑like (and not inSwitch)
        elif (
            "Boolean" in s_type
            and target_slot.startswith("in")
            and not target_is_boolean_like(t_type, target_slot)
            and target_is_numeric_like(t_type, target_slot)
        ):
            link_type = "b:ConversionLink"
            converter_type = "conv:StatusBooleanToStatusNumeric"
        # 3) Numeric (StatusNumeric) -> Counter.countIncrement needs Number
        elif t_type == "kitControl:Counter" and target_slot == "countIncrement":
            link_type = "b:ConversionLink"
            converter_type = "conv:StatusNumericToNumber"
        self._links.append(
            {
                "source_name": source_name,
                "source_slot": source_slot,
                "target_name": target_name,
                "target_slot": target_slot,
                "link_type": link_type,
                "converter_type": converter_type,
            }
        )

    def _add_component_xml_tags(
        self,
        folder_element: ET.Element,
        components: Dict[str, Dict],
        coords: Dict[str, Tuple[int, int]],
    ) -> None:
        """Adds the <p> tags for components to the XML tree."""
        for name, data in components.items():
            attrs = {"n": name, "t": data["type"], "h": data["handle"]}
            if ":" in data["type"]:
                prefix = data["type"].split(":")[0]
                # Override the module mapping for schedule components.  The Niagara
                # schedule palette uses the ``schedule`` module rather than a
                # module named ``sch``.  If we leave the default of
                # ``sch=sch`` then Workbench cannot resolve the schedule module
                # and fails to load the .bog.  Map the BooleanSchedule type
                # specifically to the ``schedule`` module; otherwise fall back
                # to the lowercase prefix mapping used for other palettes.
                if prefix == "sch":
                    # All schedule components live in the ``schedule`` module.  Use
                    # ``sch=schedule`` rather than ``sch=sch`` to ensure
                    # Workbench resolves the schedule module for Boolean,
                    # Numeric and other schedule variants.
                    attrs["m"] = "sch=schedule"
                else:
                    attrs["m"] = f"{prefix}={prefix}"
            element = ET.SubElement(folder_element, "p", attrs)
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
            # Special handling for certain component types
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
                # emit facets if provided
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
                const_val = data["properties"].get("out", 0.0)
                out_slot = ET.SubElement(
                    element, "p", {"n": "out", "t": "b:StatusNumeric"}
                )
                ET.SubElement(out_slot, "p", {"n": "value", "v": str(const_val)})
            # Revised logic for NumericSwitch
            elif data["type"] == "kitControl:NumericSwitch":
                # inSwitch slot
                in_switch_slot = ET.SubElement(
                    element, "p", {"n": "inSwitch", "f": "sL", "t": "b:StatusBoolean"}
                )
                ET.SubElement(in_switch_slot, "p", {"n": "value", "v": "false"})
                ET.SubElement(
                    in_switch_slot,
                    "p",
                    {"n": "status", "v": "0;activeLevel=e:17@control:PriorityLevel"},
                )
                # inTrue slot
                in_true_slot = ET.SubElement(
                    element, "p", {"n": "inTrue", "f": "sL", "t": "b:StatusNumeric"}
                )
                ET.SubElement(in_true_slot, "p", {"n": "value", "v": "0.0"})
                # inFalse slot
                in_false_slot = ET.SubElement(
                    element, "p", {"n": "inFalse", "f": "sL", "t": "b:StatusNumeric"}
                )
                ET.SubElement(in_false_slot, "p", {"n": "value", "v": "0.0"})
                # handle other simple properties passed in
                for prop_name, prop_value in data["properties"].items():
                    ET.SubElement(element, "p", {"n": prop_name, "v": str(prop_value)})
            elif data["type"] == "kitControl:BooleanDelay":
                # Input slot stub (so a link target exists even before wiring)
                ET.SubElement(element, "p", {"n": "in", "f": "sL"})
                on_d = data["properties"].get("onDelay", "0")
                off_d = data["properties"].get("offDelay", "0")
                if isinstance(on_d, dict):
                    on_d = on_d.get("value", "0")
                if isinstance(off_d, dict):
                    off_d = off_d.get("value", "0")
                ET.SubElement(
                    element,
                    "p",
                    {"n": "onDelay", "t": "b:RelTime", "v": str(on_d)},
                )
                ET.SubElement(
                    element,
                    "p",
                    {"n": "offDelay", "t": "b:RelTime", "v": str(off_d)},
                )
            elif data["type"] == "control:TimeTrigger":
                tm = data["properties"].get("triggerMode")
                if isinstance(tm, dict) and "value" in tm:
                    ET.SubElement(
                        element,
                        "p",
                        {
                            "n": "triggerMode",
                            "t": "control:IntervalTriggerMode",
                            "v": str(tm["value"]),
                        },
                    )
                elif isinstance(tm, str):
                    ET.SubElement(
                        element,
                        "p",
                        {
                            "n": "triggerMode",
                            "t": "control:IntervalTriggerMode",
                            "v": tm,
                        },
                    )
                for prop_name, prop_value in data["properties"].items():
                    if prop_name == "triggerMode":
                        continue
                    ET.SubElement(element, "p", {"n": prop_name, "v": str(prop_value)})
            elif data["type"] == "kitControl:MultiVibrator":
                per = data["properties"].get("period", "10000")
                if isinstance(per, dict):
                    per = per.get("value", "10000")
                ET.SubElement(
                    element,
                    "p",
                    {"n": "period", "t": "b:RelTime", "v": str(per)},
                )
            elif data["type"] == "kitControl:OneShot":
                ET.SubElement(element, "p", {"n": "in", "f": "sL"})
            elif data["type"] == "kitControl:Counter":
                props = data.get("properties", {})
                out_slot = ET.SubElement(
                    element, "p", {"n": "out", "f": "s", "t": "b:StatusNumeric"}
                )
                init_out = props.get("outValue")
                if init_out is not None:
                    prec = props.get("precision")
                    if prec is not None:
                        try:
                            init_out = round(float(init_out), int(prec))
                        except Exception:
                            pass
                    ET.SubElement(out_slot, "p", {"n": "value", "v": str(init_out)})
                precision = props.get("precision")
                if precision is not None:
                    ET.SubElement(
                        out_slot, "p", {"n": "precision", "v": str(int(precision))}
                    )
                ET.SubElement(
                    element, "p", {"n": "countUp", "f": "sL", "t": "b:StatusBoolean"}
                )
                ET.SubElement(
                    element, "p", {"n": "countDown", "f": "sL", "t": "b:StatusBoolean"}
                )
                inc = props.get("countIncrement")
                if inc is not None:
                    ET.SubElement(
                        element,
                        "p",
                        {
                            "n": "countIncrement",
                            "f": "L",
                            "t": "b:Float",
                            "v": str(inc),
                        },
                    )
                init_val = props.get("initialValue")
                if init_val is not None:
                    ET.SubElement(
                        element,
                        "p",
                        {
                            "n": "initialValue",
                            "f": "L",
                            "t": "b:Float",
                            "v": str(init_val),
                        },
                    )
                ET.SubElement(element, "a", {"n": "clear", "f": "aL"})
            elif data["type"] == "kitControl:BooleanLatch":
                ET.SubElement(element, "p", {"n": "clock", "f": "tsoL"})
                in_slot = ET.SubElement(
                    element, "p", {"n": "in", "f": "sL", "t": "b:StatusBoolean"}
                )
                ET.SubElement(in_slot, "p", {"n": "value", "v": "false"})
                ET.SubElement(
                    in_slot,
                    "p",
                    {"n": "status", "v": "0;activeLevel=e:17@control:PriorityLevel"},
                )
            elif data["type"] == "kitControl:Reset":
                # For Reset blocks, create StatusNumeric stubs for all reset slots so
                # links can attach.  The caller may provide default values in the
                # properties dict (e.g., {"inA": {"value": 11.0}}); otherwise
                # values default to 0.0.
                for slot_name in [
                    "inA",
                    "inputLowLimit",
                    "inputHighLimit",
                    "outputLowLimit",
                    "outputHighLimit",
                ]:
                    # Determine fallback value if specified in properties
                    prop_val = data["properties"].get(slot_name)
                    if isinstance(prop_val, dict):
                        val = prop_val.get("value", 0.0)
                    elif prop_val is not None:
                        val = prop_val
                    else:
                        val = 0.0
                    slot_el = ET.SubElement(
                        element,
                        "p",
                        {"n": slot_name, "f": "L", "t": "b:StatusNumeric"},
                    )
                    ET.SubElement(slot_el, "p", {"n": "value", "v": str(val)})
                    ET.SubElement(
                        slot_el,
                        "p",
                        {
                            "n": "status",
                            "v": "0;activeLevel=e:17@control:PriorityLevel",
                        },
                    )
            elif data["type"] == "kitControl:LoopPoint":
                # LoopPoint implements a PID control loop.  It exposes a
                # number of configuration slots that must exist to attach
                # links.  Use the provided properties dict to supply
                # initial values for these slots where available; otherwise
                # fall back to sensible defaults.
                props = data.get("properties", {})
                # loopEnable: StatusBoolean, default True unless overridden
                loop_enable_val: bool = True
                loop_prop = props.get("loopEnable")
                if isinstance(loop_prop, dict):
                    loop_enable_val = bool(loop_prop.get("value", loop_enable_val))
                elif loop_prop is not None:
                    loop_enable_val = bool(loop_prop)
                enable_slot = ET.SubElement(
                    element,
                    "p",
                    {"n": "loopEnable", "f": "L", "t": "b:StatusBoolean"},
                )
                ET.SubElement(
                    enable_slot, "p", {"n": "value", "v": str(loop_enable_val).lower()}
                )
                ET.SubElement(
                    enable_slot,
                    "p",
                    {"n": "status", "v": "0;activeLevel=e:17@control:PriorityLevel"},
                )
                # controlledVariable: StatusNumeric
                cv_val: float = 0.0
                cv_prop = props.get("controlledVariable")
                if isinstance(cv_prop, dict):
                    cv_val = float(cv_prop.get("value", cv_val))
                elif cv_prop is not None:
                    cv_val = float(cv_prop)
                cv_slot = ET.SubElement(
                    element,
                    "p",
                    {"n": "controlledVariable", "f": "L", "t": "b:StatusNumeric"},
                )
                ET.SubElement(cv_slot, "p", {"n": "value", "v": str(cv_val)})
                ET.SubElement(
                    cv_slot,
                    "p",
                    {"n": "status", "v": "0;activeLevel=e:17@control:PriorityLevel"},
                )
                # setpoint: StatusNumeric
                sp_val: float = 0.0
                sp_prop = props.get("setpoint")
                if isinstance(sp_prop, dict):
                    sp_val = float(sp_prop.get("value", sp_val))
                elif sp_prop is not None:
                    sp_val = float(sp_prop)
                sp_slot = ET.SubElement(
                    element,
                    "p",
                    {"n": "setpoint", "f": "L", "t": "b:StatusNumeric"},
                )
                ET.SubElement(sp_slot, "p", {"n": "value", "v": str(sp_val)})
                ET.SubElement(
                    sp_slot,
                    "p",
                    {"n": "status", "v": "0;activeLevel=e:17@control:PriorityLevel"},
                )
                # loopAction: expect an enum; stub out a locked slot with no initial value
                ET.SubElement(element, "p", {"n": "loopAction", "f": "L"})
                # proportionalConstant: Double
                pc_val: float = 0.0
                pc_prop = props.get("proportionalConstant")
                if isinstance(pc_prop, dict):
                    pc_val = float(pc_prop.get("value", pc_val))
                elif pc_prop is not None:
                    pc_val = float(pc_prop)
                ET.SubElement(
                    element,
                    "p",
                    {
                        "n": "proportionalConstant",
                        "f": "L",
                        "t": "b:Double",
                        "v": str(pc_val),
                    },
                )
                # integralConstant: Double
                ic_val: float = 0.0
                ic_prop = props.get("integralConstant")
                if isinstance(ic_prop, dict):
                    ic_val = float(ic_prop.get("value", ic_val))
                elif ic_prop is not None:
                    ic_val = float(ic_prop)
                ET.SubElement(
                    element,
                    "p",
                    {
                        "n": "integralConstant",
                        "f": "L",
                        "t": "b:Double",
                        "v": str(ic_val),
                    },
                )
                # derivativeConstant: Double (optional)
                dc_prop = props.get("derivativeConstant")
                if dc_prop is not None:
                    dc_val: float = 0.0
                    if isinstance(dc_prop, dict):
                        dc_val = float(dc_prop.get("value", 0.0))
                    else:
                        dc_val = float(dc_prop)
                    ET.SubElement(
                        element,
                        "p",
                        {
                            "n": "derivativeConstant",
                            "f": "L",
                            "t": "b:Double",
                            "v": str(dc_val),
                        },
                    )
            elif data["type"] == "sch:NumericSchedule":
                # NumericSchedule outputs a numeric status and typically has a
                # ``defaultOutput`` property to establish a baseline when no
                # schedule events are active.  Read the provided properties if
                # present, otherwise fall back to sensible defaults.
                props = data.get("properties", {})
                # Default output value
                default_val: float = 0.0
                default_prop = props.get("defaultOutput")
                if isinstance(default_prop, dict):
                    default_val = float(default_prop.get("value", default_val))
                elif default_prop is not None:
                    default_val = float(default_prop)
                def_slot = ET.SubElement(
                    element,
                    "p",
                    {"n": "defaultOutput", "t": "b:StatusNumeric"},
                )
                ET.SubElement(def_slot, "p", {"n": "value", "v": str(default_val)})
                # Current out value
                out_val: float = default_val
                out_prop = props.get("out")
                if isinstance(out_prop, dict):
                    out_val = float(out_prop.get("value", out_val))
                elif out_prop is not None:
                    out_val = float(out_prop)
                out_slot = ET.SubElement(
                    element,
                    "p",
                    {"n": "out", "t": "b:StatusNumeric"},
                )
                ET.SubElement(out_slot, "p", {"n": "value", "v": str(out_val)})
            elif data["type"] == "sch:EnumSchedule":
                # EnumSchedule outputs an enumerated value.  It may define a
                # ``facets`` property describing the enumeration mapping and
                # an ``out`` property providing the initial value.  Without
                # explicit properties, fall back to no facets and a zero
                # enumeration value ("0@{ }").
                props = data.get("properties", {})
                # Write facets mapping if provided.  When specifying facets
                # through the builder, the value should be the raw facets
                # string (e.g. "range=E:{duty1=1,duty2=2}").  If not provided,
                # facets are omitted and Niagara will default to an empty
                # enumeration.
                facets_val = props.get("facets")
                if facets_val is not None:
                    ET.SubElement(
                        element,
                        "p",
                        {"n": "facets", "t": "b:Facets", "v": str(facets_val)},
                    )
                # Determine the out value.  Accept either a dict with a
                # ``value`` key or a bare string.  Default to ``0``.
                out_val = "0"
                out_prop = props.get("out")
                if isinstance(out_prop, dict):
                    out_val = str(out_prop.get("value", out_val))
                elif out_prop is not None:
                    out_val = str(out_prop)
                out_slot = ET.SubElement(
                    element,
                    "p",
                    {"n": "out", "t": "b:StatusEnum"},
                )
                ET.SubElement(out_slot, "p", {"n": "value", "v": out_val})
            elif data["type"] == "sch:BooleanSchedule":
                # BooleanSchedule outputs a boolean status.  Use the provided
                # ``out`` property to initialise the default value if supplied.
                out_prop = (
                    data["properties"].get("out") if data.get("properties") else None
                )
                val = False
                if isinstance(out_prop, dict):
                    val = bool(out_prop.get("value", val))
                elif out_prop is not None:
                    val = bool(out_prop)
                out_slot = ET.SubElement(
                    element,
                    "p",
                    {"n": "out", "t": "b:StatusBoolean"},
                )
                ET.SubElement(out_slot, "p", {"n": "value", "v": str(val).lower()})
            else:
                # Generic logic for all other component types: simply emit properties
                for prop_name, prop_value in data["properties"].items():
                    ET.SubElement(element, "p", {"n": prop_name, "v": str(prop_value)})

    def _add_link_xml_tags(self, folder_element: ET.Element, links: List[Dict]) -> None:
        """Adds nested link tags for all links targeting components in this folder.

        Niagara Workbench expects links to be represented as child ``<p>`` elements
        underneath the target component rather than as top‑level ``<l>`` tags.  Each
        link element receives a sequential name (``Link``, ``Link1``, …) based on
        how many links already exist for the target component.  The link
        definition includes ``sourceOrd``, ``sourceSlotName`` and
        ``targetSlotName`` properties.  If a conversion type is present, a
        ``converter`` property is added with the appropriate module prefix.

        Parameters
        ----------
        folder_element : ET.Element
            The XML element representing the current folder.  Links are only
            added for components defined directly in this folder.
        links : List[Dict]
            A list of dictionaries describing the links that target components in
            this folder.  Each dictionary contains ``source_name``,
            ``source_slot``, ``target_name``, ``target_slot``, and optional
            ``converter_type`` and ``link_type`` (defaults to ``"b:Link"``).
        """
        from collections import defaultdict

        # Track how many links have been added per target so we can number them
        link_counters: Dict[str, int] = defaultdict(int)
        for link in links:
            target_name = link["target_name"]
            # Determine the handle for the target component.  If absent, skip.
            target_handle = self._handle_map.get(target_name)
            if not target_handle:
                continue
            # Find the XML element corresponding to this component in the current folder.
            # We look for a direct child of this folder with the matching handle.
            target_element = folder_element.find(f"./p[@h='{target_handle}']")
            if target_element is None:
                # If the target isn't in this folder, skip.  Cross‑folder links are
                # handled when processing the target's folder.
                continue
            # Determine the link name: first link is "Link", subsequent ones get a suffix
            count = link_counters[target_name]
            link_name = "Link" if count == 0 else f"Link{count}"
            link_counters[target_name] += 1
            # Create the link element.  Use the specified link_type if provided.
            link_type = link.get("link_type", "b:Link")
            link_element = ET.SubElement(
                target_element, "p", {"n": link_name, "t": link_type}
            )
            # Add required child properties.  relationTags is always empty and relationId
            # is "n:dataLink" for standard data links.
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
            # If a converter type is specified, include a converter definition with
            # the appropriate module prefix.  Niagara expects ``m="conv=converters"``.
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
