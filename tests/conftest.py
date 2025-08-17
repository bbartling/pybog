"""
Test configuration to make the ``bog_builder`` package importable from the ``src``
directory when running the tests without installing the package.  Pytest
automatically imports this file before collecting tests.

If you prefer to install the package in editable mode (``pip install -e .``)
before running the tests, this hook is unnecessary.  However, keeping it
ensures that contributors can run ``pytest`` in a freshly cloned repository
without needing to modify ``PYTHONPATH`` manually.
"""

import os
import sys


def pytest_sessionstart(session) -> None:  # type: ignore[override]
    """Ensure the package under ``src`` is on sys.path for test imports."""
    project_root = os.path.dirname(os.path.dirname(__file__))
    src_path = os.path.join(project_root, "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)