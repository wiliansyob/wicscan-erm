"""
Scanner registry — single source of truth for available scanner adapters.

To register a new scanner:
  1. Create a subpackage under scanners/ that implements ScannerAdapter.
  2. Import its class here and add it to SCANNER_REGISTRY.
  3. Add the scanner_type string to scan_sessions creation logic.
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
import logging

from app.modules.identification.scanners.base import ScannerAdapter
import app.modules.identification.scanners as scanners_pkg

log = logging.getLogger(__name__)

SCANNER_REGISTRY: dict[str, type[ScannerAdapter]] = {}

def _discover_scanners():
    """Dynamically discover and register all scanner adapters."""
    for module_info in pkgutil.walk_packages(scanners_pkg.__path__, scanners_pkg.__name__ + "."):
        try:
            mod = importlib.import_module(module_info.name)
            for _, obj in inspect.getmembers(mod):
                if inspect.isclass(obj) and issubclass(obj, ScannerAdapter) and obj is not ScannerAdapter:
                    scanner_type = getattr(obj, "scanner_type", None)
                    if scanner_type:
                        SCANNER_REGISTRY[scanner_type] = obj
        except Exception as exc:
            log.warning("Failed to load scanner adapter from %s: %s", module_info.name, exc)

# Execute discovery on module import
_discover_scanners()


def get_adapter(scanner_type: str) -> ScannerAdapter:
    """Return an instantiated adapter for the given scanner_type.

    Raises ValueError for unknown types so callers get a clear error
    instead of an AttributeError deep in the task.
    """
    cls = SCANNER_REGISTRY.get(scanner_type.lower())
    if cls is None:
        available = sorted(SCANNER_REGISTRY)
        raise ValueError(
            f"No adapter registered for scanner_type={scanner_type!r}. "
            f"Available: {available}"
        )
    return cls()
