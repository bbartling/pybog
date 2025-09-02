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

            # Links (standard b:Link)
            for link_element in comp_element.findall('.//p[@t="b:Link"]'):
                # Some files may miss one child; be defensive
                def _getv(tag: str) -> str:
                    elem = link_element.find(f'p[@n="{tag}"]')
                    return (
                        elem.get("v") if elem is not None and "v" in elem.attrib else ""
                    )

                comp["links"].append(
                    {
                        "source_ord": _getv("sourceOrd"),
                        "source_slot": _getv("sourceSlotName"),
                        "target_slot": _getv("targetSlotName"),
                    }
                )

            # Shallow property snapshot (n/v or text)
            for prop in comp_element.findall("p"):
                prop_name = prop.attrib.get("n")
                if not prop_name:
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
        description="Analyze Niagara .bog or .dist files; emit JSON; count/plot kitControl usage."
    )
    parser.add_argument("file_path", help="Path to the .bog or .dist file.")
    parser.add_argument("-o", "--output_file", help="Write JSON analysis to this path.")
    parser.add_argument(
        "-l",
        "--list_contents",
        action="store_true",
        help="List archive contents and exit.",
    )
    parser.add_argument(
        "-c", "--count", action="store_true", help="Print kitControl component counts."
    )
    parser.add_argument(
        "-p", "--plots", help="Directory to write bar/pie charts of kitControl usage."
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Enable debug prints."
    )
    args = parser.parse_args()

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
    else:
        # If no JSON path and no other actions, print JSON to stdout
        if not (args.count or args.plots):
            print(json.dumps(analysis, indent=2))

    if args.count:
        counts = analyzer.count_kitcontrol_components()
        if counts:
            print("kitControl component counts:")
            for k, v in counts.items():
                print(f"{k}: {v}")
        else:
            print("No kitControl components found.")

    if args.plots:
        try:
            files = analyzer.plot_kitcontrol_counts(args.plots)
            print("Generated plot files:")
            for p in files:
                print(f"- {p}")
        except Exception as exc:
            print(f"Failed to generate plots: {exc}")


if __name__ == "__main__":
    main()
