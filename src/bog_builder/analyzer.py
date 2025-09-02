# src/bog_builder/analyzer.py
"""
Tools for analysing Niagara .bog and .dist archives.

- JSON analysis with components + handle_map (old tool behavior).
- Optional kitControl counts and bar/pie charts (new behavior).
- Can list archive contents.
- Robust .bog/.dist parsing (handles file.xml or baja.bog.xml).

Usage examples:
  python -m bog_builder.analyzer path/to/file.bog -o analysis.json
  python -m bog_builder.analyzer path/to/station.dist --count
  python -m bog_builder.analyzer path/to/file.bog --plots out/plots
  python -m bog_builder.analyzer path/to/file.bog -l
  python -m bog_builder.analyzer compare path/to/bool_delay_playground_Broken.bog path/to/BoolDelay_Playground_Fixed.bog
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

    matplotlib.use("Agg")  # headless-friendly
    import matplotlib.pyplot as plt  # type: ignore
except Exception:
    plt = None  # plotting optional



# ------------------------- Comparator -------------------------

class BogComparator:
    """Compares two BOG/DIST files using the Analyzer class."""

    def __init__(self, file_path_a: str, file_path_b: str, debug: bool = False):
        self.analyzer_a = Analyzer(file_path_a, debug=debug)
        self.analyzer_b = Analyzer(file_path_b, debug=debug)
        self.data_a = self.analyzer_a.generate_analysis_data()
        self.data_b = self.analyzer_b.generate_analysis_data()

        if not self.data_a or not self.data_b:
            raise ValueError("Failed to parse one or both files for comparison.")

        self.comps_a = {c["name"]: c for c in self.data_a["components"]}
        self.comps_b = {c["name"]: c for c in self.data_b["components"]}

    def compare(self) -> Dict[str, Any]:
        """Performs the comparison and returns a diff dictionary."""
        diff: Dict[str, Any] = {"added": [], "removed": [], "modified": []}

        names_a = set(self.comps_a.keys())
        names_b = set(self.comps_b.keys())

        diff["removed"] = sorted(list(names_a - names_b))
        diff["added"] = sorted(list(names_b - names_a))

        for name in sorted(list(names_a & names_b)):
            comp_a = self.comps_a[name]
            comp_b = self.comps_b[name]
            
            prop_changes = self._compare_properties(comp_a, comp_b)
            link_changes = self._compare_links(comp_a, comp_b)

            if prop_changes or link_changes:
                diff["modified"].append({
                    "name": name,
                    "property_changes": prop_changes,
                    "link_changes": link_changes,
                })
        
        return diff

    def _compare_properties(self, comp_a: Dict, comp_b: Dict) -> List[str]:
        changes = []
        props_a = comp_a.get("properties", {})
        props_b = comp_b.get("properties", {})
        all_prop_names = set(props_a.keys()) | set(props_b.keys())

        for prop in sorted(list(all_prop_names)):
            val_a = props_a.get(prop)
            val_b = props_b.get(prop)
            if val_a != val_b:
                changes.append(f"Property '{prop}': '{val_a}' -> '{val_b}'")
        return changes

    def _get_link_signature(self, link: Dict, handle_map: Dict) -> str:
        """Creates a comparable string representation of a link."""
        source_name = handle_map.get(link["source_ord"], link["source_ord"])
        sig = f"{source_name}:{link['source_slot']} -> :{link['target_slot']} (Type: {link['type']}"
        if link.get("converter"):
            sig += f", Converter: {link['converter']}"
        sig += ")"
        return sig

    def _compare_links(self, comp_a: Dict, comp_b: Dict) -> Dict[str, List[str]]:
        links_a = {self._get_link_signature(l, self.data_a["handle_map"]) for l in comp_a.get("links", [])}
        links_b = {self._get_link_signature(l, self.data_b["handle_map"]) for l in comp_b.get("links", [])}

        removed = sorted(list(links_a - links_b))
        added = sorted(list(links_b - links_a))

        if removed or added:
            return {"added": added, "removed": removed}
        return {}

def print_diff(file_a: str, file_b: str, diff: Dict[str, Any]) -> None:
    """Prints a formatted diff report."""
    print(f"--- Diff Report ---")
    print(f"File A: {os.path.basename(file_a)}")
    print(f"File B: {os.path.basename(file_b)}")
    print("-" * 20)

    if diff["removed"]:
        print("\n[REMOVED COMPONENTS]")
        for name in diff["removed"]:
            print(f"- {name}")

    if diff["added"]:
        print("\n[ADDED COMPONENTS]")
        for name in diff["added"]:
            print(f"+ {name}")

    if diff["modified"]:
        print("\n[MODIFIED COMPONENTS]")
        for mod in diff["modified"]:
            print(f"\nComponent: {mod['name']}")
            for change in mod.get("property_changes", []):
                print(f"  P: {change}")
            
            link_changes = mod.get("link_changes", {})
            for removed_link in link_changes.get("removed", []):
                print(f"  - Link: {removed_link}")
            for added_link in link_changes.get("added", []):
                print(f"  + Link: {added_link}")
    
    print("\n--- End of Report ---")


# ----------------------------- Analyzer -----------------------------


class Analyzer:
    """
    Parse and analyse Niagara .bog or .dist files and produce:
      - JSON tree (components, links, properties, handle_map)
      - kitControl component counts
      - optional plots (bar/pie) of kitControl usage
    """

    def __init__(self, file_path: str | Path, debug: bool = False) -> None:
        self.file_path: str = str(file_path)
        self.debug: bool = debug
        self.xml_root: ET.Element | None = None
        self.analysis_title: str = "Niagara Analysis"

    # ------------------------- internal helpers -------------------------

    @staticmethod
    def _get_value_from_node(node: ET.Element) -> str | None:
        """Value may be in 'v' attr or node text."""
        if "v" in node.attrib:
            return node.attrib["v"]
        text = node.text
        if text and text.strip():
            return text.strip()
        return None

    def list_archive_contents(self) -> List[str]:
        """List raw files in the archive."""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File not found: {self.file_path}")
        if not zipfile.is_zipfile(self.file_path):
            raise ValueError(f"Not a valid ZIP archive: {self.file_path}")
        with zipfile.ZipFile(self.file_path, "r") as zf:
            return zf.namelist()

    def _process_file(self) -> None:
        if self.xml_root is not None:
            return
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File not found: {self.file_path}")

        if self.file_path.endswith(".bog"):
            self.analysis_title = "Niagara BOG File Analysis"
            self._parse_bog_file()
        elif self.file_path.endswith(".dist"):
            self.analysis_title = "Niagara Station Analysis"
            self._parse_dist_file()
        else:
            raise ValueError("Unsupported file type (use .bog or .dist).")

    @staticmethod
    def _decode_bytes(xml_bytes: bytes) -> str:
        try:
            return xml_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            return xml_bytes.decode("latin-1")

    @staticmethod
    def _find_xml_member(members: Iterable[str]) -> str | None:
        """
        Return the likely XML entry name inside a .bog:
        prefer 'file.xml', otherwise 'baja.bog.xml', otherwise first .xml.
        """
        names = list(members)
        for preferred in ("file.xml", "baja.bog.xml"):
            if preferred in names:
                return preferred
        for n in names:
            if n.lower().endswith(".xml"):
                return n
        return None

    def _parse_bog_file(self) -> None:
        try:
            with zipfile.ZipFile(self.file_path, "r") as bog_zip:
                xml_entry = self._find_xml_member(bog_zip.namelist())
                if not xml_entry:
                    raise ValueError("Could not locate an XML entry in the .bog.")
                xml_bytes = bog_zip.read(xml_entry)
                xml_content = self._decode_bytes(xml_bytes)
                self.xml_root = ET.fromstring(xml_content)
                if self.debug:
                    print(f"[Analyzer] Parsed {xml_entry} from .bog")
        except zipfile.BadZipFile:
            raise ValueError(f"Invalid .bog (ZIP) file: {self.file_path}")

    def _parse_dist_file(self) -> None:
        if not zipfile.is_zipfile(self.file_path):
            raise ValueError(f"Invalid .dist (ZIP) file: {self.file_path}")

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
                raise FileNotFoundError("config.bog not found inside .dist")

            with dist_zip.open(config_bog_path) as config_bog_file:
                config_bog_data = config_bog_file.read()

        with zipfile.ZipFile(io.BytesIO(config_bog_data), "r") as config_bog_zip:
            xml_entry = self._find_xml_member(config_bog_zip.namelist())
            if not xml_entry:
                raise FileNotFoundError("No XML entry inside config.bog")
            xml_content = self._decode_bytes(config_bog_zip.read(xml_entry))
            self.xml_root = ET.fromstring(xml_content)
            if self.debug:
                print(f"[Analyzer] Parsed {xml_entry} from config.bog")

        self.analysis_title = "Niagara Station Analysis (config.bog)"

    def _extract_all_components(
        self, start_element: ET.Element
    ) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
        """
        Extract all <p h="..."> components, their links, and basic properties.
        Returns (components, handle_to_name_map).
        """
        components: List[Dict[str, Any]] = []
        handle_to_name_map: Dict[str, str] = {}

        for comp_element in start_element.findall(".//p[@h]"):
            comp_name = comp_element.get("n")
            comp_handle = comp_element.get("h")
            if not (comp_name and comp_handle):
                continue

            handle_to_name_map[f"h:{comp_handle}"] = comp_name
            comp: Dict[str, Any] = {
                "name": comp_name,
                "type": comp_element.get("t"),
                "links": [],
                "properties": {},
            }

            # Find potential links and filter them manually, as ElementTree has limited XPath support.
            for p_element in comp_element.findall('.//p[@t]'):
                link_type = p_element.get("t", "")
                if link_type.startswith("b:") and "Link" in link_type:
                    # This is a link element.
                    link_element = p_element

                    def _getv(tag: str) -> str:
                        elem = link_element.find(f'p[@n="{tag}"]')
                        return (
                            elem.get("v") if elem is not None and "v" in elem.attrib else ""
                        )
                    
                    link_data = {
                        "type": link_type,
                        "source_ord": _getv("sourceOrd"),
                        "source_slot": _getv("sourceSlotName"),
                        "target_slot": _getv("targetSlotName"),
                        "converter": None,
                    }
                    
                    # Check for a converter
                    converter_elem = link_element.find('p[@n="converter"]')
                    if converter_elem is not None:
                        link_data["converter"] = converter_elem.get("t")

                    comp["links"].append(link_data)

            # Shallow property snapshot (n/v or text)
            for prop in comp_element.findall("p"):
                prop_name = prop.attrib.get("n")
                if not prop_name:
                    continue
                # Avoid re-processing links as properties
                if prop.get("t", "").endswith("Link"):
                    continue
                prop_val = self._get_value_from_node(prop)
                comp["properties"][prop_name] = prop_val

            components.append(comp)

        return components, handle_to_name_map


    # ----------------------------- public API -----------------------------

    def generate_analysis_data(self) -> Dict[str, Any] | None:
        """Return dict with title, source, components, handle_map."""
        self._process_file()
        if self.xml_root is None:
            return None
        comps, handles = self._extract_all_components(self.xml_root)
        return {
            "title": self.analysis_title,
            "source": os.path.basename(self.file_path),
            "components": comps,
            "handle_map": handles,
        }

    def save_analysis_to_file(
        self, analysis_data: Dict[str, Any], output_file: str | Path
    ) -> None:
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(analysis_data, f, indent=2)
        if self.debug:
            print(f"[Analyzer] JSON saved to {out_path}")

    # ---------------------- stats & plotting helpers ----------------------

    def count_kitcontrol_components(self) -> Dict[str, int]:
        """Count kitControl:* types (bucketed by the type after the colon)."""
        analysis = self.generate_analysis_data()
        if not analysis:
            return {}
        counts = collections.Counter()
        for comp in analysis["components"]:
            t = comp.get("type") or ""
            if t.startswith("kitControl:"):
                _, name = t.split(":", 1)
                counts[name] += 1
        return dict(counts.most_common())

    def plot_kitcontrol_counts(self, output_dir: str | Path) -> List[str]:
        """Write bar and pie charts to output_dir; return list of file paths."""
        if plt is None:
            raise ValueError("matplotlib is required for plotting but is not available")
        counts = self.count_kitcontrol_components()
        if not counts:
            raise ValueError("No kitControl components found to plot")

        names = list(counts.keys())
        values = list(counts.values())

        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        created: List[str] = []

        # Bar
        fig_b, ax_b = plt.subplots(figsize=(max(6, len(names) * 0.45), 4))
        ax_b.bar(range(len(names)), values)
        ax_b.set_title("kitControl Component Usage (Bar)")
        ax_b.set_xlabel("Component Type")
        ax_b.set_ylabel("Count")
        ax_b.set_xticks(range(len(names)))
        ax_b.set_xticklabels(names, rotation=45, ha="right")
        fig_b.tight_layout()
        f_bar = out_dir / "kitcontrol_counts_bar.png"
        fig_b.savefig(f_bar)
        plt.close(fig_b)
        created.append(str(f_bar))

        # Pie
        fig_p, ax_p = plt.subplots(figsize=(5, 5))
        ax_p.pie(values, labels=names, autopct="%1.1f%%", startangle=90)
        ax_p.set_title("kitControl Component Usage (Pie)")
        f_pie = out_dir / "kitcontrol_counts_pie.png"
        fig_p.savefig(f_pie)
        plt.close(fig_p)
        created.append(str(f_pie))

        if self.debug:
            print(f"[Analyzer] Created plots: {created}")
        return created


# ----------------------------- CLI entry -----------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze and compare Niagara .bog or .dist files."
    )
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug prints.")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # --- Analyze Command ---
    parser_analyze = subparsers.add_parser("analyze", help="Analyze a single .bog or .dist file.")
    parser_analyze.add_argument("file_path", help="Path to the .bog or .dist file.")
    parser_analyze.add_argument("-o", "--output_file", help="Write JSON analysis to this path.")
    parser_analyze.add_argument("-l", "--list_contents", action="store_true", help="List archive contents and exit.")
    parser_analyze.add_argument("-c", "--count", action="store_true", help="Print kitControl component counts.")
    parser_analyze.add_argument("-p", "--plots", help="Directory to write bar/pie charts of kitControl usage.")
    
    # --- Compare Command ---
    parser_compare = subparsers.add_parser("compare", help="Compare two .bog or .dist files.")
    parser_compare.add_argument("file_a", help="Path to the first file (A).")
    parser_compare.add_argument("file_b", help="Path to the second file (B).")

    args = parser.parse_args()

    if args.command == "analyze":
        analyzer = Analyzer(args.file_path, debug=args.debug)

        if args.list_contents:
            for n in analyzer.list_archive_contents():
                print(n)
            return

        analysis = analyzer.generate_analysis_data()
        if analysis is None:
            print("No analysis data generated.")
            return

        if args.output_file:
            analyzer.save_analysis_to_file(analysis, args.output_file)
        elif not (args.count or args.plots):
            print(json.dumps(analysis, indent=2))

        if args.count:
            counts = analyzer.count_kitcontrol_components()
            print("kitControl component counts:")
            for k, v in (counts.items() if counts else {}):
                print(f"{k}: {v}")

        if args.plots:
            try:
                files = analyzer.plot_kitcontrol_counts(args.plots)
                print(f"Generated plot files in {args.plots}:")
                for p in files:
                    print(f"- {os.path.basename(p)}")
            except Exception as exc:
                print(f"Failed to generate plots: {exc}")

    elif args.command == "compare":
        try:
            comparator = BogComparator(args.file_a, args.file_b, debug=args.debug)
            diff = comparator.compare()
            print_diff(args.file_a, args.file_b, diff)
        except Exception as exc:
            print(f"An error occurred during comparison: {exc}")

if __name__ == "__main__":
    main()