import os
import subprocess
import sys
from pathlib import Path


def test_smoke_main_flow_command_reports_expected_steps_without_sensitive_values() -> None:
    project_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")

    result = subprocess.run(
        [sys.executable, "scripts/smoke_main_flow.py"],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "health status=200" in result.stdout
    assert "unauthenticated status=401" in result.stdout
    assert "cache_miss status=200" in result.stdout
    assert "x-cache-status=MISS" in result.stdout
    assert "cache_hit status=200" in result.stdout
    assert "x-cache-status=HIT" in result.stdout
    assert "smoke_test=passed" in result.stdout
    assert "Authorization" not in result.stdout
    assert "smoke-local-token" not in result.stdout
    assert "local smoke prompt" not in result.stdout
