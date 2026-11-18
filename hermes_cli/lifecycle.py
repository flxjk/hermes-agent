"""Hermes lifecycle dispatch for plugins."""

from __future__ import annotations

import logging
from typing import Any, List

logger = logging.getLogger(__name__)


def _plugin_hooks(hook_name: str, **kwargs: Any) -> list[Any]:
    from hermes_cli import plugins

    return plugins.invoke_hook(hook_name, **kwargs)


def invoke_hook(hook_name: str, **kwargs: Any) -> list[Any]:
    """Invoke compatibility plugin hooks."""
    from agent.safe_worker_policy import safe_worker_enabled

    if safe_worker_enabled():
        return []
    return _plugin_hooks(hook_name, **kwargs)


async def ainvoke_hook(hook_name: str, **kwargs: Any) -> list[Any]:
    """:func:`invoke_hook` for callers on an event loop, with ``async def`` plugin
    callbacks awaited on that loop."""
    from hermes_cli import plugins

    return await plugins.ainvoke_hook(hook_name, **kwargs)


def has_hook(hook_name: str) -> bool:
    """Return whether a plugin consumes a hook."""
    from agent.safe_worker_policy import safe_worker_enabled

    if safe_worker_enabled():
        return False
    from hermes_cli import plugins

    return plugins.has_hook(hook_name)


def hook_known_unused(hook_name: str) -> bool:
    """True when nothing in the active profile can consume *hook_name*, decided without loading
    plugins or reading config, so an event loop may ask before spending a thread on it: safe mode,
    or this profile's plugins already loaded with none registered for a hook. False means it may be
    consumed: ask :func:`has_hook` off the loop."""
    from agent.safe_worker_policy import safe_worker_enabled

    if safe_worker_enabled():
        return True
    from hermes_cli import plugins

    return plugins.hook_unused_nowait(hook_name)


def session_end_messages(results: Any) -> list[str]:
    """User-facing text from ``on_session_finalize`` results: a non-empty ``str`` or ``{"message": str}``.

    Surfaces show these out-of-band (CLI print, TUI system line, gateway chat send) — never as a model
    turn. ``on_session_end`` is per-turn and is never surfaced."""
    messages: list[str] = []
    for result in results or ():
        text = result.get("message") if isinstance(result, dict) else result
        if isinstance(text, str) and text.strip():
            messages.append(text.strip())
    return messages


def finalize_session(**kwargs: Any) -> list[Any]:
    """Hard-close one core-owned Relay conversation, then invoke plugin hooks."""
    session_id = str(kwargs.get("session_id") or "")
    if session_id:
        try:
            from agent import relay_runtime

            relay_runtime.SESSION_COORDINATOR.finalize_conversation(
                profile_key=relay_runtime.current_profile_key(),
                session_id=session_id,
            )
        except Exception:
            logger.warning("Core Relay session finalization failed", exc_info=True)

    return _plugin_hooks("on_session_finalize", **kwargs)
