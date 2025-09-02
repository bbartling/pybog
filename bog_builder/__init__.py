"""Bog Builder package.

This package provides a :class:`BogFolderBuilder` class for constructing Niagara
`.bog` files programmatically, along with Pydantic models for validating
inputs.  To use it, simply import :class:`BogFolderBuilder` from the package:

```
from bog_builder import BogFolderBuilder

builder = BogFolderBuilder("MyFolder")
builder.add_numeric_writable("Input1", 42.0)
...
builder.save("my_logic.bog")
```
"""

from .builder import BogFolderBuilder
from .models import (
    ComponentDefinition,
    LinkDefinition,
    ReductionBlockDefinition,
    COMPONENT_SLOT_MAP,
    _parse_time_to_ms,
)

# Optionally expose the Analyzer for users who want to inspect existing
# Niagara archives.  The import is done lazily so that environments
# without matplotlib can still import bog_builder without pulling in
# heavy dependencies.  If the analyzer cannot be imported it will
# simply be absent from __all__.
try:
    from .analyzer import Analyzer  # type: ignore
except Exception:
    Analyzer = None

__all__ = [
    "BogFolderBuilder",
    "ComponentDefinition",
    "LinkDefinition",
    "ReductionBlockDefinition",
    "COMPONENT_SLOT_MAP",
    "_parse_time_to_ms",
    "Analyzer",
]
