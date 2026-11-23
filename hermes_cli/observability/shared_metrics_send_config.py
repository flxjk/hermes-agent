"""Resolve collection preferences with external transmission disabled."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_ENDPOINT = ""


@dataclass(frozen=True)
class SendConfig:
    enabled: bool
    send: bool
    endpoint: str


def resolve_send_config(config: dict | None) -> SendConfig:
    raw = config if isinstance(config, dict) else {}
    telemetry = raw.get("telemetry")
    shared = telemetry.get("shared_metrics") if isinstance(telemetry, dict) else None
    enabled = isinstance(shared, dict) and shared.get("enabled") is True
    return SendConfig(enabled=enabled, send=False, endpoint=DEFAULT_ENDPOINT)
