"""
Tests the advanced type checking and automatic conversion capabilities
of the BogFolderBuilder's add_link method.
"""

from __future__ import annotations
from pathlib import Path
import pytest

from bog_builder import BogFolderBuilder


def test_add_link_applies_automatic_converter(tmp_path: Path) -> None:
    """
    Verify that the builder automatically applies a ConversionLink for a known
    type mismatch (StatusNumeric -> RelTime).
    """
    builder = BogFolderBuilder("AutoConversionTest", debug=True)

    # --- Components ---
    builder.add_numeric_writable("DelayTimeSeconds", default_value=60.0)
    builder.add_boolean_delay("MyDelay")
    builder.add_boolean_writable("Input")
    builder.add_boolean_writable("Output")

    # --- Wiring ---
    # This link is the focus of the test. The builder should detect the
    # StatusNumeric -> RelTime mismatch and apply the converter automatically.
    builder.add_link("DelayTimeSeconds", "out", "MyDelay", "onDelay")

    # Add other links to make it a functional wiresheet
    builder.add_link("Input", "out", "MyDelay", "in")
    builder.add_link("MyDelay", "out", "Output", "in16")

    # The test passes if the .bog file is created without raising an exception.
    out_path = tmp_path / "auto_conversion_success.bog"
    builder.save(str(out_path))
    assert out_path.exists()

    # Verify that the correct link data was stored internally
    link_info = next(l for l in builder._links if l["target_slot"] == "onDelay")
    assert link_info["link_type"] == "b:ConversionLink"
    assert link_info["converter_type"] == "conv:StatusNumericToRelTime"


def test_add_link_raises_type_error_for_invalid_conversion() -> None:
    """
    Verify that the builder raises a TypeError when linking two components
    with incompatible types for which no automatic converter is defined.
    """
    builder = BogFolderBuilder("InvalidConversionTest", debug=False)

    # --- Components ---
    # We will try to link a Numeric output to a Boolean input, which is an
    # invalid conversion with no entry in CONVERSION_MAP.
    builder.add_numeric_writable("NumericSource")
    builder.add_not("BooleanTarget")  # A 'Not' gate expects a boolean input.

    # --- Wiring ---
    # This should fail because there is no entry in CONVERSION_MAP for
    # ('StatusNumeric', 'StatusBoolean').
    with pytest.raises(TypeError) as excinfo:
        builder.add_link("NumericSource", "out", "BooleanTarget", "in")

    # Assert that the error message contains the expected information
    assert "Type mismatch" in str(excinfo.value)
    assert "NumericSource" in str(excinfo.value)
    assert "BooleanTarget" in str(excinfo.value)
    assert "StatusNumeric" in str(excinfo.value)
    assert "StatusBoolean" in str(excinfo.value)
    assert "No automatic converter found" in str(excinfo.value)
