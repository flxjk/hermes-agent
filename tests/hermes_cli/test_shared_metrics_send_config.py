"""The fork preserves local consent and ignores every outbound setting."""

import pytest

from hermes_cli.observability.shared_metrics_send_config import SendConfig, resolve_send_config


@pytest.mark.parametrize("enabled", [False, True])
def test_legacy_outbound_settings_cannot_enable_transmission(enabled):
    config = {"telemetry": {"shared_metrics": {
        "enabled": enabled, "send": True, "endpoint": "https://collector.example.invalid",
    }}}
    assert resolve_send_config(config) == SendConfig(enabled=enabled, send=False, endpoint="")


def test_missing_configuration_disables_collection_and_transmission():
    assert resolve_send_config(None) == SendConfig(enabled=False, send=False, endpoint="")
