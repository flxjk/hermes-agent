"""Shared leaf helpers for the ``hermes update`` modules (no Hermes imports; no cycle)."""

import logging
import sys
from contextlib import contextmanager

# Log-record parity with the origin module.
logger = logging.getLogger("hermes_cli.update_cmd")


def _record_stop(reason: str) -> None:
    """Name the exit about to stop this update as one closed token (see update_receipt.record_stop_reason).

    The receipt module is read from ``sys.modules``, never imported: an older updater can load this
    tree after the swap while its own, older ``update_receipt`` stays loaded.
    """
    receipt = sys.modules.get("hermes_cli.update_receipt")
    record = getattr(receipt, "record_stop_reason", None)
    if record is not None:
        record(reason)


@contextmanager
def _best_effort(message: str):
    """Run a non-critical update step; swallow ``Exception`` and log it at debug.

    The updater must never die on bookkeeping (receipt, notices, cache seeds):
    ``message`` is the ``%s``-style debug line the inline ``try/except`` used.
    """
    try:
        yield
    except Exception as exc:
        logger.debug(message, exc)
