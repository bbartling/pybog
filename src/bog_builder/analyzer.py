# src/bog_builder/analyzer.py
"""
bog_builder.analyzer

Analyze or compare Niagara .bog/.dist archives or raw bajaObjectGraph XML.

Usage
-----
Analyze a single file:
    python -m bog_builder.analyzer analyze path/to/file.bog --format json

Compare two graphs (ideal for LLM agents):
    python -m bog_builder.analyzer compare path/to/Broken.xml path/to/Fixed.xml \
        --ignore handles --ignore ws-annotations --format table

Outputs
-------
- table  : human-readable console table
- json   : full machine-friendly JSON (recommended for agents)
- md     : markdown table (paste into READMEs)
- html   : self-contained HTML diff table (drop into a web app)

Notes
-----
- "Handles" (the `h=` attribute) are required for components/links to be fully
  resolvable in Workbench projects. Workbench usually injects them on save.
- `b:WsAnnotation` children are UI layout metadata; optional for logic but
  helpful for usability.
"""

from __future__ import annotations
import argparse
import json
import sys
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Iterable
import xml.etree.ElementTree as ET
from collections import defaultdict, Counter


# ----------------------------- Data structures ------------------------------


@dataclass(frozen=True)
class NodeKey:
    path: str
    type: str


@dataclass
class Node:
    key: NodeKey
    handle: Optional[str]
    attrs: Dict[str, str]
    # links recorded as tuples of (src, dst) using canonical "path.pin" form if resolvable
    outgoing_links: List[Tuple[str, str]]
    incoming_links: List[Tuple[str, str]]


@dataclass
class CompareOptions:
    ignore_handles: bool = False
    ignore_ws_annotations: bool = False
    ignore_attr_keys: Tuple[str, ...] = (
        "h",
    )  # always ignores "h" when ignore_handles=True


@dataclass
class CompareReport:
    added: List[NodeKey]
    removed: List[NodeKey]
    modified: List[Dict[str, object]]
    # structural/quality checks:
    problems_left: Dict[str, object]
    problems_right: Dict[str, object]
    summary: Dict[str, object]


# ----------------------------- Parsing helpers -----------------------------


def _is_ws_annotation(elem: ET.Element) -> bool:
    return elem.tag == "p" and elem.attrib.get("t", "").endswith("WsAnnotation")


def _iter_root_p_elems(root: ET.Element) -> Iterable[ET.Element]:
    for child in root:
        if child.tag == "p":
            yield child


def _read_xml_from_bog_or_xml(path: Path) -> ET.Element:
    if path.suffix.lower() in (".bog", ".dist"):
        with zipfile.ZipFile(path, "r") as zf:
            # heuristic: Niagara archives typically have a single file.xml at root
            xml_name = None
            for name in zf.namelist():
                if name.lower().endswith(".xml"):
                    xml_name = name
                    break
            if xml_name is None:
                raise ValueError(f"No XML found in archive: {path}")
            with zf.open(xml_name) as f:
                return ET.fromstring(f.read())
    else:
        return ET.parse(path).getroot()


def _walk_graph(
    p_elem: ET.Element, current_path: str = "/"
) -> Iterable[Tuple[str, ET.Element]]:
    """Yield (path, element) for every <p> component."""
    name = p_elem.attrib.get("n", "")
    path = current_path
    if name:
        path = (current_path.rstrip("/") + "/" + name).replace("//", "/")
    yield (path, p_elem)
    for c in p_elem:
        if c.tag == "p":
            yield from _walk_graph(c, path)


def _collect_links(root: ET.Element) -> List[ET.Element]:
    # Links can appear as <l ...> under the root or elsewhere
    # We'll gather all <l> elements in doc
    return list(root.iterfind(".//l"))


def _handle_map_by_handle(nodes: Dict[NodeKey, Node]) -> Dict[str, NodeKey]:
    m = {}
    for nk, node in nodes.items():
        if node.handle:
            m[node.handle] = nk
    return m


def _pin_to_canonical(handle_pin: str, handle_map: Dict[str, NodeKey]) -> Optional[str]:
    # formats are like "3.out" meaning handle 3, pin "out"
    if "." not in handle_pin:
        return None
    handle, pin = handle_pin.split(".", 1)
    nk = handle_map.get(handle)
    if not nk:
        return None
    return f"{nk.path}.{pin}"


# ----------------------------- Build Node index ----------------------------


def build_index(path: Path, ignore_ws_annotations: bool) -> Dict[NodeKey, Node]:
    root = _read_xml_from_bog_or_xml(path)
    # find all top-level <p> under bajaObjectGraph
    nodes: Dict[NodeKey, Node] = {}
    for p in _iter_root_p_elems(root):
        for apath, elem in _walk_graph(p, "/"):
            if ignore_ws_annotations and _is_ws_annotation(elem):
                continue
            t = elem.attrib.get("t", "")
            nk = NodeKey(apath, t)
            n = Node(
                key=nk,
                handle=elem.attrib.get("h"),
                attrs=dict(elem.attrib),
                outgoing_links=[],
                incoming_links=[],
            )
            nodes[nk] = n

    # collect links and map to canonical "path.pin" where possible
    handle_map = _handle_map_by_handle(nodes)
    for l in _collect_links(root):
        s = l.attrib.get("s")  # source "handle.pin"
        d = l.attrib.get("d")  # dest "handle.pin"
        if not s or not d:
            continue
        s_canon = _pin_to_canonical(s, handle_map) or s
        d_canon = _pin_to_canonical(d, handle_map) or d
        # annotate on both ends if resolvable to nodes
        s_handle = s.split(".", 1)[0]
        d_handle = d.split(".", 1)[0]
        s_key = handle_map.get(s_handle)
        d_key = handle_map.get(d_handle)
        if s_key and s_key in nodes:
            nodes[s_key].outgoing_links.append((s_canon, d_canon))
        if d_key and d_key in nodes:
            nodes[d_key].incoming_links.append((s_canon, d_canon))

    return nodes


# ----------------------------- Quality checks ------------------------------


def diagnose(nodes: Dict[NodeKey, Node]) -> Dict[str, object]:
    # handle presence / uniqueness
    missing_handles = [asdict(n.key) for n in nodes.values() if not n.handle]
    dup_counter = Counter([n.handle for n in nodes.values() if n.handle])
    duplicate_handles = [h for h, c in dup_counter.items() if c > 1]

    # orphan link refs are detected during compare when the other side differs,
    # but we can still report counts here:
    link_count = sum(len(n.outgoing_links) for n in nodes.values())

    # specific helpful heuristics for folder playgrounds
    wsann_missing_under_folders = []
    for n in nodes.values():
        if n.key.type.endswith(":Folder"):
            # if *no* wsAnnotation child exists under this folder, note it
            # We can't see children directly here, but a cheap heuristic:
            # any node whose path startswith this folder + "/wsAnnotation" will exist in nodes
            expected = NodeKey(n.key.path + "/wsAnnotation", "b:WsAnnotation")
            # If user asked us to ignore ws annotations when building index, this won't exist;
            # so we only record a suggestion (not an error).
            # We'll still include a "suggestion" entry:
            wsann_missing_under_folders.append(asdict(n.key))

    return {
        "node_count": len(nodes),
        "link_count": link_count,
        "missing_handles": missing_handles,
        "duplicate_handles": duplicate_handles,
        "suggestions": {
            "ws_annotation_placeholders_for_folders": wsann_missing_under_folders
        },
    }


# ----------------------------- Comparison ----------------------------------


def _norm_attrs(attrs: Dict[str, str], opts: CompareOptions) -> Dict[str, str]:
    if not opts.ignore_handles:
        return dict(attrs)
    return {k: v for k, v in attrs.items() if k not in opts.ignore_attr_keys}


def compare(left_path: Path, right_path: Path, opts: CompareOptions) -> CompareReport:
    left_idx = build_index(left_path, ignore_ws_annotations=opts.ignore_ws_annotations)
    right_idx = build_index(
        right_path, ignore_ws_annotations=opts.ignore_ws_annotations
    )

    left_keys = set(left_idx.keys())
    right_keys = set(right_idx.keys())

    added = sorted(list(right_keys - left_keys), key=lambda k: (k.path, k.type))
    removed = sorted(list(left_keys - right_keys), key=lambda k: (k.path, k.type))

    modified: List[Dict[str, object]] = []
    for k in sorted(list(left_keys & right_keys), key=lambda k: (k.path, k.type)):
        ln = left_idx[k]
        rn = right_idx[k]
        lattrs = _norm_attrs(ln.attrs, opts)
        rattrs = _norm_attrs(rn.attrs, opts)
        if lattrs != rattrs or ln.outgoing_links != rn.outgoing_links:
            modified.append(
                {
                    "key": asdict(k),
                    "left_attrs": lattrs,
                    "right_attrs": rattrs,
                    "left_links": ln.outgoing_links,
                    "right_links": rn.outgoing_links,
                }
            )

    rep = CompareReport(
        added=added,
        removed=removed,
        modified=modified,
        problems_left=diagnose(left_idx),
        problems_right=diagnose(right_idx),
        summary={
            "left": {
                "file": str(left_path),
                "nodes": len(left_idx),
            },
            "right": {
                "file": str(right_path),
                "nodes": len(right_idx),
            },
            "options": vars(opts),
        },
    )
    return rep


# ----------------------------- Rendering -----------------------------------


def _render_table(rep: CompareReport) -> str:
    lines = []
    s = rep.summary
    lines.append(f"Left : {s['left']['file']} (nodes={s['left']['nodes']})")
    lines.append(f"Right: {s['right']['file']} (nodes={s['right']['nodes']})")
    lines.append(f"Options: {json.dumps(s['options'])}")
    lines.append("")

    def fmt_key(k: NodeKey) -> str:
        return f"{k.path} :: {k.type}"

    if rep.added:
        lines.append("=== Added in RIGHT (not in LEFT) ===")
        for k in rep.added:
            lines.append(f"+ {fmt_key(k)}")
        lines.append("")
    if rep.removed:
        lines.append("=== Removed from LEFT (not in RIGHT) ===")
        for k in rep.removed:
            lines.append(f"- {fmt_key(k)}")
        lines.append("")
    if rep.modified:
        lines.append("=== Modified (attrs or links) ===")
        for m in rep.modified:
            k = m["key"]
            lines.append(f"* {k['path']} :: {k['type']}")
            lines.append(f"  - left_attrs : {m['left_attrs']}")
            lines.append(f"  - right_attrs: {m['right_attrs']}")
            if m["left_links"] or m["right_links"]:
                lines.append(f"  - left_links : {m['left_links']}")
                lines.append(f"  - right_links: {m['right_links']}")
            lines.append("")
    lines.append("=== Diagnostics (LEFT) ===")
    lines.append(json.dumps(rep.problems_left, indent=2))
    lines.append("")
    lines.append("=== Diagnostics (RIGHT) ===")
    lines.append(json.dumps(rep.problems_right, indent=2))
    return "\n".join(lines)


def _render_md(rep: CompareReport) -> str:
    def fmt_key(k: NodeKey) -> str:
        return f"`{k.path}` — `{k.type}`"

    out = []
    out.append(
        f"**Left**: `{rep.summary['left']['file']}`  \n"
        f"**Right**: `{rep.summary['right']['file']}`  \n"
        f"**Options**: `{json.dumps(rep.summary['options'])}`"
    )
    out.append("")
    if rep.added:
        out.append("### Added (in Right only)")
        for k in rep.added:
            out.append(f"- {fmt_key(k)}")
        out.append("")
    if rep.removed:
        out.append("### Removed (missing in Right)")
        for k in rep.removed:
            out.append(f"- {fmt_key(k)}")
        out.append("")
    if rep.modified:
        out.append("### Modified")
        out.append("| Path | Type | Diff |")
        out.append("|---|---|---|")
        for m in rep.modified:
            k = m["key"]
            diff = f"<sub>left</sub> `{m['left_attrs']}` → <sub>right</sub> `{m['right_attrs']}`"
            out.append(f"| `{k['path']}` | `{k['type']}` | {diff} |")
        out.append("")
    out.append("### Diagnostics")
    out.append("**Left**")
    out.append("```json")
    out.append(json.dumps(rep.problems_left, indent=2))
    out.append("```")
    out.append("**Right**")
    out.append("```json")
    out.append(json.dumps(rep.problems_right, indent=2))
    out.append("```")
    return "\n".join(out)


def _render_html(rep: CompareReport) -> str:
    # simple self-contained HTML (no external CSS)
    def esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    rows = []
    for m in rep.modified:
        k = m["key"]
        rows.append(
            f"<tr><td>{esc(k['path'])}</td><td>{esc(k['type'])}</td>"
            f"<td><pre>{esc(json.dumps(m['left_attrs'], indent=2))}</pre></td>"
            f"<td><pre>{esc(json.dumps(m['right_attrs'], indent=2))}</pre></td></tr>"
        )
    html = f"""<!doctype html>
<html><head><meta charset="utf-8">
<title>BOG/XML Compare</title>
<style>
body{{font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Arial}}
table{{border-collapse:collapse;width:100%}} th,td{{border:1px solid #ddd;padding:8px;vertical-align:top}}
th{{background:#f5f5f5}} pre{{margin:0;white-space:pre-wrap}}
.code{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px}}
.kv{{display:grid;grid-template-columns:auto 1fr;gap:.5rem 1rem}}
.badge{{display:inline-block;padding:2px 6px;border:1px solid #ccc;border-radius:6px;background:#fafafa}}
</style></head>
<body>
<h2>BOG/XML Compare</h2>
<div class="kv">
<div>Left</div><div class="code">{esc(rep.summary['left']['file'])} <span class="badge">nodes={rep.summary['left']['nodes']}</span></div>
<div>Right</div><div class="code">{esc(rep.summary['right']['file'])} <span class="badge">nodes={rep.summary['right']['nodes']}</span></div>
<div>Options</div><div class="code">{esc(json.dumps(rep.summary['options']))}</div>
</div>
<h3>Added</h3>
<ul>
{"".join(f"<li>{esc(k.path)} — {esc(k.type)}</li>" for k in rep.added) or "<li><em>None</em></li>"}
</ul>
<h3>Removed</h3>
<ul>
{"".join(f"<li>{esc(k.path)} — {esc(k.type)}</li>" for k in rep.removed) or "<li><em>None</em></li>"}
</ul>
<h3>Modified</h3>
<table>
<tr><th>Path</th><th>Type</th><th>Left attrs</th><th>Right attrs</th></tr>
{"".join(rows) or "<tr><td colspan='4'><em>None</em></td></tr>"}
</table>
<h3>Diagnostics (Left)</h3>
<pre class="code">{esc(json.dumps(rep.problems_left, indent=2))}</pre>
<h3>Diagnostics (Right)</h3>
<pre class="code">{esc(json.dumps(rep.problems_right, indent=2))}</pre>
</body></html>"""
    return html


def render(rep: CompareReport, fmt: str) -> str:
    if fmt == "table":
        return _render_table(rep)
    if fmt == "json":
        return json.dumps(
            {
                "added": [asdict(k) for k in rep.added],
                "removed": [asdict(k) for k in rep.removed],
                "modified": rep.modified,
                "problems_left": rep.problems_left,
                "problems_right": rep.problems_right,
                "summary": rep.summary,
            },
            indent=2,
        )
    if fmt == "md":
        return _render_md(rep)
    if fmt == "html":
        return _render_html(rep)
    raise ValueError(f"Unknown format: {fmt}")


# ----------------------------- CLI -----------------------------------------


def _cmd_analyze(args: argparse.Namespace) -> int:
    idx = build_index(Path(args.file), ignore_ws_annotations=args.ignore_ws_annotations)
    diag = diagnose(idx)
    out = {
        "file": str(args.file),
        "nodes": len(idx),
        "diagnostics": diag,
        "options": {"ignore_ws_annotations": args.ignore_ws_annotations},
    }
    if args.format == "json":
        print(json.dumps(out, indent=2))
    elif args.format == "table":
        print(f"File: {out['file']} (nodes={out['nodes']})")
        print(json.dumps(diag, indent=2))
    elif args.format == "md":
        print(
            f"**File** `{out['file']}`  \n**Nodes** `{out['nodes']}`\n\n```json\n{json.dumps(diag, indent=2)}\n```"
        )
    else:
        raise ValueError("format must be one of: json, table, md")
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    rep = compare(
        Path(args.left),
        Path(args.right),
        CompareOptions(
            ignore_handles=args.ignore in ("handles", "all"),
            ignore_ws_annotations=args.ignore in ("ws-annotations", "all"),
        ),
    )
    print(render(rep, args.format))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="bog_builder.analyzer",
        description="Analyze or compare Niagara .bog/.dist or raw XML.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pa = sub.add_parser("analyze", help="Analyze one graph and print diagnostics.")
    pa.add_argument("file", help="Path to .bog/.dist or .xml")
    pa.add_argument(
        "--ignore-ws-annotations",
        action="store_true",
        help="Ignore b:WsAnnotation nodes",
    )
    pa.add_argument("--format", choices=["json", "table", "md"], default="table")
    pa.set_defaults(func=_cmd_analyze)

    pc = sub.add_parser("compare", help="Compare two graphs.")
    pc.add_argument("left", help="Left file (.bog/.dist or .xml)")
    pc.add_argument("right", help="Right file (.bog/.dist or .xml)")
    pc.add_argument(
        "--ignore",
        choices=["none", "handles", "ws-annotations", "all"],
        default="handles",
        help="Ignore sets when diffing.",
    )
    pc.add_argument(
        "--format", choices=["table", "json", "md", "html"], default="table"
    )
    pc.set_defaults(func=_cmd_compare)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
