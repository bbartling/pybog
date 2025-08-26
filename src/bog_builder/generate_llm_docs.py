from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable


def iter_example_files(examples_dir: Path) -> Iterable[Path]:
    """Yield all Python files under the given examples directory.

    Files are yielded in sorted order for deterministic output.  Only
    files ending with ``.py`` are included, and hidden files are
    ignored.  Traversal is recursive.

    :param examples_dir: Directory containing example scripts.
    :return: An iterable of Path objects.
    """
    for root, _, filenames in os.walk(examples_dir):
        for filename in sorted(filenames):
            if filename.startswith("."):
                continue

            if not filename.endswith(".py"):
                continue

            if filename.startswith("UNVERIFIED_"):
                print(f"[LLM DOC MAKER] Skipping {filename}")
                continue

            yield Path(root) / filename


def generate_docs(examples_dir: Path, output_dir: Path) -> None:
    """Generate LLM‑friendly documentation files from example scripts.

    :param examples_dir: Path to the directory containing example scripts.
    :param output_dir: Path to the directory where documentation will be written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    llms_path = output_dir / "llms.txt"
    full_path = output_dir / "llms-full.txt"

    with llms_path.open("w", encoding="utf-8") as llms_f, full_path.open(
        "w", encoding="utf-8"
    ) as full_f:
        for file_path in iter_example_files(examples_dir):
            rel_dir = file_path.parent.relative_to(examples_dir)
            file_name = file_path.name
            # Write entry to sitemap
            llms_f.write(f"{file_name}\t{rel_dir.as_posix()}\n")

            # Read file contents safely
            try:
                code = file_path.read_text(encoding="utf-8")
            except Exception as exc:  # pragma: no cover - file reading errors
                code = f"<<Error reading {file_path}: {exc}>>"

            # Write full code with delimiters
            full_f.write(f"=== FILE: {file_name} ===\n")
            full_f.write(f"DIR: {rel_dir.as_posix()}\n")
            full_f.write("=== CODE START ===\n")
            full_f.write(code)
            if not code.endswith("\n"):
                full_f.write("\n")
            full_f.write("=== CODE END ===\n\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__ or "Generate LLM docs")
    parser.add_argument(
        "--examples",
        type=str,
        default=str(Path(__file__).resolve().parents[1] / "examples"),
        help="Path to the examples directory. Defaults to the 'examples' folder of the package.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(Path(__file__).resolve().parents[1] / "context"),
        help="Directory where the llms.txt and llms-full.txt files will be created. Defaults to a 'context' folder alongside this script.",
    )
    args = parser.parse_args()
    examples_dir = Path(args.examples).resolve()
    output_dir = Path(args.output).resolve()

    if not examples_dir.is_dir():
        raise SystemExit(f"Examples directory not found: {examples_dir}")

    generate_docs(examples_dir, output_dir)
    print(f"Generated LLM docs in {output_dir}")


if __name__ == "__main__":  # pragma: no cover
    main()
