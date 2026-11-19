import json
from unittest.mock import MagicMock, patch

import yaml
from typer.testing import CliRunner

from holmes.core.tool_calling_llm import LLMResult
from holmes.main import app


@patch("holmes.checks.checks.CheckRunner._send_alerts")
@patch("holmes.config.Config.create_toolcalling_llm")
def test_per_check_alert_mode_from_checks_file_sends_alert(
    mock_create_toolcalling_llm, mock_send_alerts, tmp_path
):
    mock_ai = MagicMock()
    mock_ai.llm.model = "gpt-4"
    mock_ai.call.return_value = LLMResult(
        result=json.dumps({"passed": False, "rationale": "2 pods crashlooping"}),
        tool_calls=[],
    )
    mock_create_toolcalling_llm.return_value = mock_ai

    checks_file = tmp_path / "checks.yaml"
    checks_file.write_text(
        yaml.dump(
            {
                "version": 1,
                "destinations": {
                    "webhook": {"webhook_url": "http://example.invalid/hook"}
                },
                "checks": [
                    {
                        "name": "pods-healthy",
                        "query": "Are all pods healthy?",
                        "mode": "alert",
                        "destinations": ["webhook"],
                    }
                ],
            }
        )
    )

    # No --mode on the command line: the check's own `mode: alert` should apply.
    result = CliRunner().invoke(
        app, ["checks", "run", "--checks-file", str(checks_file)]
    )

    assert result.exit_code == 1, result.output
    assert "FAIL" in result.output
    mock_send_alerts.assert_called_once()
