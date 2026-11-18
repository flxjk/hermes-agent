"""What an unverified ``/api/status`` caller may see of gateway diagnostics (#90700).

``/api/status`` is public; the router calls :func:`redact_status_for_unverified` on the body for
any caller the auth gate would not accept on a gated route.
"""
from __future__ import annotations

import re
from typing import Any, Callable, Optional

from gateway.status import normalize_updated_at


# What an unverified caller may read of a platform entry: lifecycle enum, the source-controlled
# error code, the attention flag and timestamps. ``error_message`` is adapter exception text (endpoint
# URLs, response bodies, credential names) and any other key is whatever an adapter chose to write,
# so the anonymous projection is an allowlist, never a denylist (#90700).
_PUBLIC_PLATFORM_STATES = frozenset({
    "connected", "connecting", "disabled", "disconnected", "fatal", "paused", "retrying", "running", "ok"})
# Source-controlled codes (``telegram_polling_conflict``, ``loop_liveness_watchdog``) are snake_case
# identifiers; anything else (spaces, URLs, quotes, ``=``) is prose and does not pass.
_PUBLIC_CODE_RE = re.compile(r"[a-z][a-z0-9_]{0,63}")


def _contains_any(*needles: str) -> Callable[[str], bool]:
    return lambda text: any(needle in text for needle in needles)


# Ordered (predicate, class) rules; first match wins, so auth outranks rate-limit etc. The bounded
# code an unverified caller reads in place of the raw shutdown text (#90700).
_GATEWAY_ERROR_RULES: tuple[tuple[Callable[[str], bool], str], ...] = (
    (_contains_any("auth", "token", "unauthorized", "forbidden", "401", "403"), "auth_failed"),
    (lambda s: "rate" in s and "limit" in s, "rate_limited"),
    (_contains_any("timeout", "timed out"), "timeout"),
    (_contains_any("network", "connection", "dns", "socket", "connect call failed", "failed to connect",
                   "cannot connect", "unreachable", "name resolution"), "network_error"),
    (_contains_any("config", "missing", "invalid"), "invalid_config"),
    (_contains_any("startup"), "startup_failed"),
    (_contains_any("fatal"), "platform_fatal"),
)


def _classify_gateway_error(raw: Any) -> str:
    s = str(raw or "").lower()
    return next((label for match, label in _GATEWAY_ERROR_RULES if match(s)), "unknown")


def _classify_exit_reason(raw: Any, *, state: Any) -> Optional[str]:
    """Reduce free-form shutdown text to a bounded operational class."""
    state_name = str(state or "").lower()
    if raw is None and state_name != "startup_failed":
        return None
    classified = _classify_gateway_error(raw)
    if state_name == "startup_failed":
        return classified if classified != "unknown" else "startup_failed"
    text = str(raw or "").lower()
    if "signal" in text or "sigterm" in text or "sigint" in text:
        return "signal"
    if state_name == "stopped" and any(word in text for word in ("shutdown", "stop")):
        return "planned_stop"
    return classified


def _anonymous_platform_entry(value: Any) -> dict[str, Any]:
    """Allowlisted, value-validated view of one platform entry for an unverified caller."""
    if not isinstance(value, dict):
        return {}
    entry: dict[str, Any] = {}
    state = value.get("state")
    if state is not None:
        entry["state"] = state if isinstance(state, str) and state in _PUBLIC_PLATFORM_STATES else "unknown"
    code = value.get("error_code")
    if isinstance(code, str) and _PUBLIC_CODE_RE.fullmatch(code):
        entry["error_code"] = code
    if isinstance(value.get("needs_attention"), bool):
        entry["needs_attention"] = value["needs_attention"]
    for key in ("retrying_since", "updated_at"):
        stamp = normalize_updated_at(value.get(key)) if isinstance(value.get(key), str) else None
        if stamp is not None:
            entry[key] = stamp
    return entry


def redact_status_for_unverified(status: dict[str, Any]) -> None:
    """Reduce the free-text diagnostics of a ``/api/status`` body to bounded codes in place.
    Full detail stays for a caller the auth gate would accept on a gated route."""
    status["gateway_platforms"] = {key: _anonymous_platform_entry(value)
                                   for key, value in (status.get("gateway_platforms") or {}).items()}
    reason = status.get("gateway_exit_reason")
    if reason is not None and not (isinstance(reason, str) and _PUBLIC_CODE_RE.fullmatch(reason)):
        status["gateway_exit_reason"] = _classify_exit_reason(reason, state=status.get("gateway_state"))
    # Remediation prose naming the colliding profiles and the credential's env var.
    status["multiplex_standalone_reason"] = None
