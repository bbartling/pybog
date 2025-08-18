"""Tools for analysing Niagara .bog and .dist archives.

This module provides an ``Analyzer`` class that can extract the
component graph from Niagara BOG and DIST files, summarise the
components into a JSON structure, and produce high‑level statistics
about the usage of specific palettes such as ``kitControl``.  It also
includes optional plotting helpers to visualise these statistics.

The implementation is based on an original research tool.  It has
been refactored and expanded to support additional use cases such as
counting kitControl blocks and generating bar/pie charts showing
how many of each block type are present in a given file.
"""

from __future__ import annotations

import argparse
import collections
import io
import json
import os
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import xml.etree.ElementTree as ET

try:
    import matplotlib

    matplotlib.use("Agg")  # Use a non‑interactive backend for headless environments
    import matplotlib.pyplot as plt  # type: ignore
except Exception:
    plt = None  # Charting will be unavailable if matplotlib cannot be imported


class Analyzer:
    """Parse and analyse Niagara archive files.

    The class accepts a path to either a ``.bog`` or ``.dist`` file and
    extracts the underlying ``file.xml``.  It then walks the element
    tree to build a JSON representation of components, their types,
    properties and links.  Convenience methods are provided to count
    components by palette and to produce visualisations of these counts.
    """

    def __init__(self, file_path: str | Path, debug: bool = False) -> None:
        self.file_path: str = str(file_path)
        self.debug = debug
        self.xml_root: ET.Element | None = None
        self.analysis_title = "Niagara Analysis"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get_value_from_node(self, node: ET.Element) -> str | None:
        """Return the value for a property node.

        The value may be stored in the ``v`` attribute or as text content.
        If neither is present ``None`` is returned.
        """
        if "v" in node.attrib:
            return node.attrib["v"]
        text = node.text
        if text and text.strip():
            return text.strip()
        return None

    def list_archive_contents(self) -> List[str]:
        """Return the list of files contained in the archive without processing it."""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(
                f"The specified file does not exist: {self.file_path}"
            )
        if not zipfile.is_zipfile(self.file_path):
            raise ValueError(f"File is not a valid archive: {self.file_path}")
        with zipfile.ZipFile(self.file_path, "r") as archive:
            return archive.namelist()

    def _process_file(self) -> None:
        """Load and parse the file.xml from a .bog or .dist archive."""
        if self.xml_root is not None:
            return
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(
                f"The specified file does not exist: {self.file_path}"
            )
        if self.file_path.endswith(".bog"):
            self.analysis_title = "Niagara BOG File Analysis"
            self._parse_bog_file()
        elif self.file_path.endswith(".dist"):
            self.analysis_title = "Niagara Station Analysis"
            self._parse_dist_file()
        else:
            raise ValueError(
                "Unsupported file type. Please provide a .bog or .dist file."
            )

    def _get_xml_content_from_bytes(self, xml_bytes: bytes) -> str:
        """Decode raw XML bytes, trying UTF-8 first and falling back to Latin-1."""
        try:
            return xml_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            return xml_bytes.decode("latin-1")

    def _parse_bog_file(self) -> None:
        """Extract file.xml from a .bog archive and parse it into an ElementTree."""
        try:
            with zipfile.ZipFile(self.file_path, "r") as bog_zip:
                xml_bytes = bog_zip.read("file.xml")
                xml_content = self._get_xml_content_from_bytes(xml_bytes)
                self.xml_root = ET.fromstring(xml_content)
        except zipfile.BadZipFile:
            raise ValueError(f"File is not a valid .bog (ZIP) file: {self.file_path}")
        except KeyError:
            raise ValueError("The .bog file does not contain a 'file.xml' entry.")

    def _parse_dist_file(self) -> None:
        """Extract the embedded config.bog from a .dist archive and parse its file.xml."""
        if not zipfile.is_zipfile(self.file_path):
            raise ValueError(
                f"File is not a valid .dist (ZIP) file or may be corrupted: {self.file_path}"
            )
        pattern = re.compile(
            r"niagara_user_home/stations/[^/]+/config\.bog$", re.IGNORECASE
        )
        with zipfile.ZipFile(self.file_path, "r") as dist_zip:
            config_bog_path = None
            for path in dist_zip.namelist():
                if pattern.search(path):
                    config_bog_path = path
                    break
            if not config_bog_path:
                raise FileNotFoundError(
                    "Could not find a main config.bog inside the .dist archive."
                )
            with dist_zip.open(config_bog_path) as config_bog_file:
                config_bog_data = config_bog_file.read()
        with zipfile.ZipFile(io.BytesIO(config_bog_data), "r") as config_bog_zip:
            if "file.xml" not in config_bog_zip.namelist():
                raise FileNotFoundError("file.xml not found inside config.bog.")
            xml_bytes = config_bog_zip.read("file.xml")
            xml_content = self._get_xml_content_from_bytes(xml_bytes)
            self.xml_root = ET.fromstring(xml_content)
        self.analysis_title = "Niagara Station Analysis (config.bog)"

    def _extract_all_components(
        self, start_element: ET.Element
    ) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
        """Walk the XML tree and extract all component definitions.

        Each component is represented as a dictionary with keys:
        ``name``, ``type``, ``links`` and ``properties``.  Links are
        extracted as a list of dictionaries containing source ord, source
        slot and target slot.  A mapping from handle identifiers to
        component names is also returned.
        """
        components: List[Dict[str, Any]] = []
        handle_to_name_map: Dict[str, str] = {}
        for comp_element in start_element.findall(".//p[@h]"):
            comp_name = comp_element.get("n")
            comp_handle = comp_element.get("h")
            if comp_name and comp_handle:
                handle_to_name_map[f"h:{comp_handle}"] = comp_name
                component: Dict[str, Any] = {
                    "name": comp_name,
                    "type": comp_element.get("t"),
                    "links": [],
                    "properties": {},
                }
                for link_element in comp_element.findall('.//p[@t="b:Link"]'):
                    link_data = {
                        "source_ord": link_element.find('p[@n="sourceOrd"]').get("v"),
                        "source_slot": link_element.find('p[@n="sourceSlotName"]').get(
                            "v"
                        ),
                        "target_slot": link_element.find('p[@n="targetSlotName"]').get(
                            "v"
                        ),
                    }
                    component["links"].append(link_data)
                for prop in comp_element.findall("p"):
                    prop_name = prop.attrib.get("n")
                    if not prop_name:
                        continue
                    prop_val = self._get_value_from_node(prop)
                    component["properties"][prop_name] = prop_val
                components.append(component)
        return components, handle_to_name_map

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def generate_analysis_data(self) -> Dict[str, Any] | None:
        """Return a structured representation of the archive contents.

        The returned dictionary has keys ``title``, ``source``, ``components``
        and ``handle_map``.  Use this method if you need to inspect
        individual components or serialise the entire analysis to JSON.
        """
        self._process_file()
        if self.xml_root is None:
            return None
        components, handle_map = self._extract_all_components(self.xml_root)
        return {
            "title": self.analysis_title,
            "source": os.path.basename(self.file_path),
            "components": components,
            "handle_map": handle_map,
        }

    def save_analysis_to_file(
        self, analysis_data: Dict[str, Any], output_file: str | Path
    ) -> None:
        """Persist the analysis data to disk as JSON."""
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(analysis_data, f, indent=2)
        if self.debug:
            print(f"Analysis saved to {out_path}")

    # ------------------------------------------------------------------
    # Statistics and plotting
    # ------------------------------------------------------------------
    def count_kitcontrol_components(self) -> Dict[str, int]:
        """Return a case‑sensitive count of ``kitControl`` component types.

        Components whose ``type`` attribute begins with ``"kitControl:"``
        are grouped by their type name (the portion after the colon).
        For example ``"kitControl:Add"`` contributes to the ``"Add"``
        bucket.  The counts are returned as a normal dict sorted by
        descending frequency for convenience.
        """
        analysis = self.generate_analysis_data()
        if not analysis:
            return {}
        counts = collections.Counter()
        for comp in analysis["components"]:
            comp_type = comp.get("type")
            if not comp_type:
                continue
            if not comp_type.startswith("kitControl:"):
                continue
            _, type_name = comp_type.split(":", 1)
            counts[type_name] += 1
        return dict(counts.most_common())

    def plot_kitcontrol_counts(self, output_dir: str | Path) -> List[str]:
        """Generate bar and pie charts of kitControl usage.

        Two PNG files will be written into the provided ``output_dir``:
        ``kitcontrol_counts_bar.png`` and ``kitcontrol_counts_pie.png``.
        The function returns a list of the file paths created.  If
        matplotlib is not installed ``ValueError`` is raised.
        """
        if plt is None:
            raise ValueError("matplotlib is required for plotting but is not available")
        counts = self.count_kitcontrol_components()
        if not counts:
            raise ValueError("No kitControl components found to plot")
        names = list(counts.keys())
        values = list(counts.values())
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        created_files: List[str] = []

        # Bar chart
        fig_bar, ax_bar = plt.subplots(figsize=(max(6, len(names) * 0.4), 4))
        ax_bar.bar(range(len(names)), values, color="skyblue")
        ax_bar.set_title("kitControl Component Usage (Bar)")
        ax_bar.set_xlabel("Component Type")
        ax_bar.set_ylabel("Count")
        # Set ticks and labels separately to avoid FixedFormatter warnings
        ax_bar.set_xticks(range(len(names)))
        ax_bar.set_xticklabels(names, rotation=45, ha="right")
        fig_bar.tight_layout()
        bar_file = output_path / "kitcontrol_counts_bar.png"
        fig_bar.savefig(bar_file)
        created_files.append(str(bar_file))
        plt.close(fig_bar)

        # Pie chart
        fig_pie, ax_pie = plt.subplots(figsize=(5, 5))
        ax_pie.pie(values, labels=names, autopct="%1.1f%%", startangle=90)
        ax_pie.set_title("kitControl Component Usage (Pie)")
        pie_file = output_path / "kitcontrol_counts_pie.png"
        fig_pie.savefig(pie_file)
        created_files.append(str(pie_file))
        plt.close(fig_pie)

        if self.debug:
            print(f"Created plots: {created_files}")
        return created_files


# ----------------------------------------------------------------------
# CLI entry point
# ----------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze Niagara .bog or .dist files and optionally plot kitControl usage statistics."
    )
    parser.add_argument("file_path", help="Path to the .bog or .dist file to analyse.")
    parser.add_argument(
        "-o", "--output_file", help="Path to save the JSON analysis file."
    )
    parser.add_argument(
        "-l",
        "--list_contents",
        action="store_true",
        help="List contents of the archive and exit.",
    )
    parser.add_argument(
        "-c",
        "--count",
        action="store_true",
        help="Print a count of kitControl component types.",
    )
    parser.add_argument(
        "-p",
        "--plots",
        help="Directory where bar and pie charts of kitControl usage should be saved.",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug logging during analysis.",
    )
    args = parser.parse_args()

    analyzer = Analyzer(args.file_path, debug=args.debug)
    if args.list_contents:
        for name in analyzer.list_archive_contents():
            print(name)
        return
    # Always generate analysis data
    analysis_data = analyzer.generate_analysis_data()
    if analysis_data is None:
        print("No analysis data generated.")
        return
    if args.output_file:
        analyzer.save_analysis_to_file(analysis_data, args.output_file)
    else:
        # If an output file is not specified and no other action requested, print to stdout
        if not (args.count or args.plots):
            print(json.dumps(analysis_data, indent=2))
    if args.count:
        counts = analyzer.count_kitcontrol_components()
        if counts:
            print("kitControl component counts:")
            for comp_type, count in counts.items():
                print(f"{comp_type}: {count}")
        else:
            print("No kitControl components found.")
    if args.plots:
        try:
            files = analyzer.plot_kitcontrol_counts(args.plots)
            print("Generated plot files:")
            for f in files:
                print(f"- {f}")
        except Exception as exc:
            print(f"Failed to generate plots: {exc}")


if __name__ == "__main__":
    main()
