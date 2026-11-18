"""Caller identity for requests to the first-party gateways: who is calling, and which turn asked.

``user_agent()`` goes on every request. The gateway strips every ``x-nous-`` header before it calls
a vendor.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Mapping, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "CallRef",
    "connector_headers",
    "log_connector_outcome",
    "response_request_id",
    "user_agent",
]

REQUEST_ID_HEADER = "x-request-id"

# sys.platform -> the OS family named in the User-Agent.
_OS_FAMILY = {"darwin": "macos", "linux": "linux", "win32": "windows"}

# The surfaces a first-party gateway request can come from, and the platform names that alias onto
# them (a platform the registry knows is a gateway; anything else is ``other``).
_SURFACES = frozenset({
    "acp", "api", "batch", "cli", "desktop", "gateway", "python", "scheduled_task", "tui",
    "other", "unknown",
})
_SURFACE_ALIASES = {
    "api_server": "api",
    "relay": "gateway",
    **dict.fromkeys(("cron", "scheduler", "scheduled"), "scheduled_task"),
}
_KNOWN_GATEWAY_PLATFORMS = frozenset({"discord", "email", "slack", "telegram", "teams", "whatsapp"})

# The account route answers 404 with this code until the vendor has created the account.
_EXPECTED_MISSES = frozenset({"connection_not_found"})


@dataclass(frozen=True)
class CallRef:
    """The model's ids for the call a request serves. Used for local connector logging."""

    turn_id: Optional[str] = None
    tool_call_id: Optional[str] = None


def _platform_name() -> str:
    """The session's platform: the running turn's agent platform, else the bound session vars.

    Off a turn (a desktop page action, an account operation thread) only the session vars exist.
    The classic CLI and one-shot runs bind neither, so they read as ``cli``."""
    from agent.relay_runtime import current_turn
    from gateway.session_context import get_session_env
    from tools.connectors.gateway.config import session_platform
    from utils import is_truthy_value

    turn = current_turn()
    if turn is not None and turn.lease.platform:
        return turn.lease.platform
    if platform := session_platform():
        return platform
    return "cron" if is_truthy_value(get_session_env("HERMES_CRON_SESSION", "")) else "cli"


def _surface() -> str:
    """The session's surface for the ``User-Agent``: the platform, bucketed to the surfaces a gateway
    request can come from. Off a turn (a desktop page action, an account operation thread) only the
    session vars exist; the classic CLI and one-shot runs bind neither, so they read as ``cli``."""
    from hermes_cli.platforms import get_all_platforms

    value = _platform_name().strip().lower()
    if value in _SURFACES:
        return value
    if value in _SURFACE_ALIASES:
        return _SURFACE_ALIASES[value]
    try:
        if value in get_all_platforms():
            return "gateway"
    except Exception:
        pass
    return "gateway" if value in _KNOWN_GATEWAY_PLATFORMS else "other"


def user_agent() -> str:
    from hermes_cli.version_info import get_version_info
    from hermes_platform.host.facts import os_family

    os_name = _OS_FAMILY.get(os_family(), "unknown")
    return f"hermes-agent/{get_version_info().base_version} ({_surface()}; {os_name})"


def connector_headers() -> dict[str, str]:
    """Every identity header for one connector HTTP attempt. Call it once per attempt."""
    return {"User-Agent": user_agent()}


def response_request_id(response: object) -> Optional[str]:
    headers = getattr(response, "headers", None)
    if not isinstance(headers, Mapping):
        return None
    value = headers.get(REQUEST_ID_HEADER) or headers.get("X-Request-Id")
    return str(value) if value else None


def log_connector_outcome(
    route: str, status: Optional[int], *, code: Optional[str] = None, request_id: Optional[str] = None,
    call: Optional[CallRef] = None,
) -> None:
    """One line per connector HTTP outcome: failures at WARNING, success and expected misses at DEBUG.

    The ``code`` makes a line a failure, not the status: a 200 whose body failed carries one, and a
    304 that refreshed a cached list does not."""
    level = logging.WARNING if code is not None and code not in _EXPECTED_MISSES else logging.DEBUG
    logger.log(
        level, "connector %s %s %s request_id=%s dispatch=%s",
        route, status if status is not None else "transport", code or "-", request_id or "-",
        (call.tool_call_id if call else None) or "-",
    )
