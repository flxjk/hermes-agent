"""A module's log records keep their component when the module runs inside the ``hermes_agent`` package.

``gateway.log`` and ``hermes logs --component`` decide by logger
name. ``getLogger(__name__)`` in ``gateway/run.py`` names ``gateway.run`` today and
``hermes_agent.gateway.run`` once the module lives in the package; both must route the same way.
"""
from __future__ import annotations

import logging

import pytest

from hermes_cli.logs import _line_matches_component
from hermes_logging import COMPONENT_PREFIXES, _ComponentFilter

SAMPLES = {
    "gateway": ("gateway.run", "plugins.platforms.telegram.adapter", "agent.memory_caller_scope"),
    "agent": ("agent.conversation_loop", "run_agent"),
    "tools": ("tools.file_tools",),
    "cli": ("hermes_cli.update_cmd", "cli"),
    "cron": ("cron.scheduler",),
    "gui": ("hermes_cli.web_server", "tui_gateway.server"),
}


@pytest.mark.parametrize("component", sorted(COMPONENT_PREFIXES))
@pytest.mark.parametrize("package", ["", "hermes_agent."])
def test_component_routing_matches_top_level_and_package_logger_names(component, package):
    prefixes = COMPONENT_PREFIXES[component]
    for name in SAMPLES[component]:
        record = logging.LogRecord(f"{package}{name}", logging.WARNING, __file__, 1, "msg", (), None)
        assert _ComponentFilter(prefixes).filter(record), record.name
        assert _line_matches_component(f"2026-11-07 10:00:00 WARNING {package}{name}: msg", prefixes), record.name
    other = next(c for c in sorted(COMPONENT_PREFIXES) if not SAMPLES[c][0].startswith(prefixes))
    record = logging.LogRecord(f"{package}{SAMPLES[other][0]}", logging.WARNING, __file__, 1, "msg", (), None)
    assert not _ComponentFilter(prefixes).filter(record)


@pytest.mark.parametrize("package", ["", "hermes_agent."])
def test_formatted_lines_print_the_canonical_logger_name(package):
    from agent.redact import RedactingFormatter
    from hermes_logging import _LOG_FORMAT, DisplayNameFormatter

    record = logging.makeLogRecord({"name": f"{package}gateway.run", "levelname": "INFO", "msg": "started"})
    assert RedactingFormatter(_LOG_FORMAT).format(record).endswith(" INFO gateway.run: started")
    assert DisplayNameFormatter("%(name)s: %(message)s").format(record) == "gateway.run: started"
    assert record.name == f"{package}gateway.run"
    root = logging.makeLogRecord({"name": "hermes_agent", "msg": "x"})
    assert DisplayNameFormatter("%(name)s").format(root) == "hermes_agent"
