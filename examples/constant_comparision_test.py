"""
Constant comparison test (Boolean, Numeric, Enum) — WORKS IN WB.

Enum point handling example with an ENUM_MAP {} and src API handling.
"""

from __future__ import annotations
import argparse, os
from bog_builder import BogFolderBuilder

# The Enum map remains the source of truth
ENUM_MAP = {
    "Occupied": 0,
    "Unoccupied": 1,
    "Startup": 3,
    "Shutdown": 4,
}

# The old helper functions (enum_facets_str, enum_value_str) are NO LONGER NEEDED.


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default="examples")
    args = ap.parse_args()

    b = BogFolderBuilder("ConstComparisonTest", debug=True)

    # -------- Boolean (No Change) --------
    b.add_boolean_writable("BooleanWrit", default_value=True)
    b.add_component(
        "kitControl:BooleanConst", "BooleanCons", properties={"value": True}
    )
    b.add_component("kitControl:Equal", "Equal_Bool")
    b.add_boolean_writable("BoolTrue")
    b.add_link("BooleanWrit", "out", "Equal_Bool", "inA")
    b.add_link("BooleanCons", "out", "Equal_Bool", "inB")
    b.add_link("Equal_Bool", "out", "BoolTrue", "in16")

    # -------- Numeric (No Change) --------
    b.add_numeric_writable("NumericWrit", default_value=1.0)
    b.add_component("kitControl:NumericConst", "NumericCons", properties={"value": 1.0})
    b.add_component("kitControl:Equal", "Equal_Num")
    b.add_boolean_writable("NumericTrue")
    b.add_link("NumericWrit", "out", "Equal_Num", "inA")
    b.add_link("NumericCons", "out", "Equal_Num", "inB")
    b.add_link("Equal_Num", "out", "NumericTrue", "in16")

    # -------- Enum (Rewritten using the new API) --------

    # 1. Register the Enum definition with a name, "Mode"
    b.define_enum_range("Mode", ENUM_MAP)

    # 2. Create the EnumWritable using the new helper.
    #    Notice we use the human-readable tag "Startup", not the index 3.
    b.add_enum_writable_by_name("EnumWrit", enum_name="Mode", default_tag="Startup")

    # 3. Create the EnumConst using the other new helper.
    b.add_enum_const_by_name("EnumCons", enum_name="Mode", value_tag="Startup")

    # The rest of the logic is unchanged
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
