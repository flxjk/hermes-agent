from types import SimpleNamespace

from agent import relay_runtime
from hermes_cli import lifecycle, plugins


def test_invoke_hook_dispatches_to_plugins(monkeypatch):
    calls = []
    manager = SimpleNamespace(
        invoke_hook=lambda name, **kwargs: calls.append(("plugin", name, kwargs)) or ["ok"]
    )
    monkeypatch.setattr(plugins, "invoke_hook", manager.invoke_hook)

    result = lifecycle.invoke_hook("on_session_start", session_id="session-1")

    assert result == ["ok"]
    assert calls == [("plugin", "on_session_start", {"session_id": "session-1"})]


def test_finalize_session_closes_core_before_plugin_export(monkeypatch):
    calls = []
    manager = SimpleNamespace(
        invoke_hook=lambda name, **kwargs: calls.append(("plugin", name, kwargs)) or []
    )
    coordinator = SimpleNamespace(
        finalize_conversation=lambda **kwargs: calls.append(("core", kwargs))
    )
    monkeypatch.setattr(plugins, "invoke_hook", manager.invoke_hook)
    monkeypatch.setattr(relay_runtime, "SESSION_COORDINATOR", coordinator)
    monkeypatch.setattr(relay_runtime, "current_profile_key", lambda: "profile-1")

    lifecycle.finalize_session(session_id="session-1", platform="cli")

    assert [call[0] for call in calls] == ["core", "plugin"]
    assert calls[0][1] == {
        "profile_key": "profile-1",
        "session_id": "session-1",
    }


def test_has_hook_follows_the_plugin_manager(monkeypatch):
    monkeypatch.setattr(plugins, "has_hook", lambda name: name == "on_session_start")

    assert lifecycle.has_hook("on_session_start") is True
    assert lifecycle.has_hook("custom") is False
