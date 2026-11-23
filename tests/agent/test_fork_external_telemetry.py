"""Privacy contracts shared by the fork default and dev."""

import importlib.util

import pytest

from agent.relay_runtime import NoopRelayRuntime, RelayHostRegistry, resolve_plugin_sources
from hermes_cli.relay_plugin_cutover import RELAY_PLUGINS_CONFIG_ENV


def test_legacy_relay_configuration_keeps_a_noop_host(monkeypatch, tmp_path):
    config = tmp_path / "plugins.toml"
    config.write_text("[plugins.exporter]\nenabled = true\n", encoding="utf-8")
    monkeypatch.setenv(RELAY_PLUGINS_CONFIG_ENV, str(config))
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://collector.example.invalid")

    registry = RelayHostRegistry()
    host = registry.for_profile(str(tmp_path))
    assert isinstance(host, NoopRelayRuntime)
    assert registry.for_profile(str(tmp_path)) is host
    assert not resolve_plugin_sources().enabled
    registry.shutdown_all()


def test_shared_metrics_sender_is_inert_with_legacy_profile_settings():
    name = "hermes_cli.observability.shared_metrics_sender"
    if importlib.util.find_spec(name) is None:
        return

    from hermes_cli.observability.shared_metrics_send_config import resolve_send_config
    from hermes_cli.observability.shared_metrics_sender import _post

    endpoint = "https://collector.example.invalid"
    config = {"telemetry": {"shared_metrics": {"enabled": True, "send": True, "endpoint": endpoint}}}
    assert not resolve_send_config(config).send
    with pytest.raises(RuntimeError, match="transmission is disabled"):
        _post(endpoint, b"fixture", timeout=1)


def test_legacy_otlp_configuration_cannot_start_exporters(monkeypatch):
    if importlib.util.find_spec("agent.monitoring") is None:
        return

    from agent.monitoring.gateway_health_export import start_gateway_health_export
    from agent.monitoring.otlp_exporter import OTLPUnavailable, build_exporter, is_available, start_streaming

    endpoint = "https://collector.example.invalid"
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", endpoint)
    config = {
        "monitoring": {
            "export": {"otlp": {"enabled": True, "endpoint": endpoint}},
            "gateway_health_export": {"enabled": True, "metrics_enabled": True},
        },
    }
    assert not is_available()
    assert start_streaming(config) is None
    runtime = start_gateway_health_export(config)
    assert not runtime.enabled
    with pytest.raises(OTLPUnavailable, match="disabled"):
        build_exporter(config)
