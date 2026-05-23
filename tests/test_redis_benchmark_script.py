import os
import subprocess
import sys
from pathlib import Path


def test_redis_benchmark_skips_without_redis_url() -> None:
    project_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.pop("REDIS_URL", None)
    env["PYTHONPATH"] = str(project_root / "src")

    result = subprocess.run(
        [sys.executable, "scripts/benchmark_redis_cache_hit.py"],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "REDIS_URL is not configured" in result.stdout
