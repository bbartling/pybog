"""
Constant comparison test (Boolean, Numeric, Enum) — WORKS IN WB.

Wires:
- BooleanWritable + BooleanConst → Equal → BoolTrue
- NumericWritable + NumericConst → Equal → NumericTrue
- EnumWritable   + EnumConst     → Equal → EnumTrue
"""

from __future__ import annotations

import argparse, os
from bog_builder import BogFolderBuilder


ENUM_MAP = {
    "Occupied": 0,
    "Unoccupied": 1,
    "Startup": 3,
    "Shutdown": 4,
}

def enum_facets_str(mapping: dict[str, int]) -> str:
    return "range=E:{" + ",".join(f"{k}={v}" for k, v in mapping.items()) + "}"

def enum_value_str(tag: str, mapping: dict[str, int]) -> str:
    ord_ = mapping[tag]
    return f"{ord_}@{{" + ",".join(f"{k}={v}" for k, v in mapping.items()) + "}}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default="examples")
    args = ap.parse_args()

    b = BogFolderBuilder("ConstComparisonTest", debug=True)

    # -------- Boolean --------
    b.add_boolean_writable("BooleanWrit", default_value=True)
    b.add_component("kitControl:BooleanConst", "BooleanCons", properties={"value": True})
    b.add_component("kitControl:Equal", "Equal_Bool")
    b.add_boolean_writable("BoolTrue")
    b.add_link("BooleanWrit", "out", "Equal_Bool", "inA")
    b.add_link("BooleanCons", "out", "Equal_Bool", "inB")
    b.add_link("Equal_Bool", "out", "BoolTrue", "in16")

    # -------- Numeric --------
    b.add_numeric_writable("NumericWrit", default_value=1.0)
    b.add_component("kitControl:NumericConst", "NumericCons", properties={"value": 1.0})
    b.add_component("kitControl:Equal", "Equal_Num")
    b.add_boolean_writable("NumericTrue")
    b.add_link("NumericWrit", "out", "Equal_Num", "inA")
    b.add_link("NumericCons", "out", "Equal_Num", "inB")
    b.add_link("Equal_Num", "out", "NumericTrue", "in16")

    # -------- Enum --------
    facets = enum_facets_str(ENUM_MAP)                 # b:Facets string
    start_val = enum_value_str("Startup", ENUM_MAP)    # DynamicEnum string

    b.add_component(
        "control:EnumWritable",
        "EnumWrit",
        properties={
            "facets": facets,
            "fallback": {"value": start_val},   # default state
        },
    )
    b.add_component("kitControl:EnumConst", "EnumCons", properties={"value": start_val})
    b.add_component("kitControl:Equal", "Equal_Enum")
    b.add_boolean_writable("EnumTrue")

    b.add_link("EnumWrit", "out", "Equal_Enum", "inA")
    b.add_link("EnumCons", "out", "Equal_Enum", "inB")
    b.add_link("Equal_Enum", "out", "EnumTrue", "in16")

    os.makedirs(args.output, exist_ok=True)
    out_path = os.path.join(args.output, "ConstComparisonTest.bog")
    b.save(out_path)
    print(f"Created {out_path}")

if __name__ == "__main__":
    main()
