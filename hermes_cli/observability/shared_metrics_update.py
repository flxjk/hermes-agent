"""Frozen old-updater compatibility stub (``tests/compat/old_updater_surface.json``, ``bare`` list).

An updater from an earlier release imports ``record_update_receipt`` from this module after the code
swap. The shared-metrics store it used to write to was removed, so the name stays importable and
inert.
"""

from __future__ import annotations

from typing import Any


def record_update_receipt(receipt: dict[str, Any], *, wait_saved: bool = False) -> bool:
    """Inert: records nothing and reports success — the answer the old store gave with collection
    off. ``wait_saved`` is accepted for signature compatibility."""
    return True


__all__ = ["record_update_receipt"]
