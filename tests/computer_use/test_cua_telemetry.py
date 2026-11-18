"""cua-driver telemetry is always disabled in Hermes child environments.

cua-driver ships anonymous PostHog telemetry ENABLED by default upstream. Hermes forces
``CUA_DRIVER_RS_TELEMETRY_ENABLED=0`` into every cua-driver child env, and no setting turns it
back on.

These assert the behavior contract (always injected, overrides an inherited value, keeps the base
env), not specific config snapshots.
"""

from tools.computer_use import cua_backend


_VAR = "CUA_DRIVER_RS_TELEMETRY_ENABLED"


class TestChildEnv:

    def test_always_injects_var_zero(self):
        env = cua_backend.cua_driver_child_env({"PATH": "/usr/bin"})
        assert env[_VAR] == "0"
        # base env is preserved
        assert env["PATH"] == "/usr/bin"


    def test_overrides_inherited_enabled(self):
        # Even if the parent process had the driver's telemetry enabled, the child gets it off.
        env = cua_backend.cua_driver_child_env({_VAR: "1"})
        assert env[_VAR] == "0"


    def test_no_setting_turns_it_back_on(self, monkeypatch):
        monkeypatch.setattr(cua_backend, "_computer_use_cfg", lambda: {"cua_telemetry": True})
        assert cua_backend.cua_driver_child_env({})[_VAR] == "0"
