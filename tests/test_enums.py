"""
Tests the high-level Enum handling API of the BogFolderBuilder.
"""

from __future__ import annotations
from pathlib import Path

from bog_builder import BogFolderBuilder

# Define the Enum map for the test
MODE_ENUM = {
    "Occupied": 0,
    "Unoccupied": 1,
    "Startup": 3,
    "Shutdown": 4,
}


def test_enum_comparison_with_new_api(tmp_path: Path) -> None:
    """
    Validates the entire Enum workflow: defining a range, creating writable
    and const components by name, and automatically creating conversion links.
    """
    # 1. Setup the builder
    builder = BogFolderBuilder("EnumApiTest", debug=False)

    # 2. Exercise the new API
    # Define the enum range once
    builder.define_enum_range("Mode", MODE_ENUM)

    # Create components using the new, simple helpers
    # We use different tags to ensure the comparison is meaningful
    builder.add_enum_writable_by_name(
        "EnumWrit", enum_name="Mode", default_tag="Startup"
    )
    builder.add_enum_const_by_name("EnumCons", enum_name="Mode", value_tag="Occupied")

    # 3. Add the rest of the logic
    builder.add_equal("Equal_Enum")
    builder.add_boolean_writable("ComparisonResult")

    # 4. Wire the components
    # The builder should now automatically create ConversionLinks here
    builder.add_link("EnumWrit", "out", "Equal_Enum", "inA")
    builder.add_link("EnumCons", "out", "Equal_Enum", "inB")
    builder.add_link("Equal_Enum", "out", "ComparisonResult", "in16")

    # 5. Save and assert success
    out_path = tmp_path / "enum_api_test.bog"
    builder.save(str(out_path))

    # The test passes if no exceptions were raised and the file was created.
    assert out_path.exists()
