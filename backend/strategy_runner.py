from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from strategy_config import StrategyConfig


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parent
BASE_STRATEGY_FILE = BACKEND_DIR / "my_strategy.py"


def build_temp_strategy(config: StrategyConfig) -> Path:
    config_json = json.dumps(config.model_dump(), indent=4)
    strategy_source = BASE_STRATEGY_FILE.read_text(encoding="utf-8")

    strategy_source = strategy_source.replace(
        "class MyStrategy(BaseStrategy):",
        f"USER_CONFIG = {config_json}\n\nclass MyStrategy(BaseStrategy):",
        1,
    )
    strategy_source = strategy_source.replace(
        "def __init__(self, config: dict) -> None:",
        "def __init__(self) -> None:\n        config = USER_CONFIG",
        1,
    )

    temp_dir = Path(tempfile.mkdtemp())
    temp_file = temp_dir / "temp_strategy.py"
    temp_file.write_text(strategy_source, encoding="utf-8")
    return temp_file


def extract_chart_series(output: str) -> tuple[list[dict], str]:
    pattern = r"CHART_DATA_START\s*(.*?)\s*CHART_DATA_END"
    match = re.search(pattern, output, re.DOTALL)

    if not match:
        return [], output

    raw_json = match.group(1).strip()

    try:
        chart_points = json.loads(raw_json)
    except Exception:
        chart_points = []

    cleaned_output = re.sub(pattern, "", output, flags=re.DOTALL).strip()
    return chart_points, cleaned_output


def parse_backtest_output(output: str) -> dict:
    chart_points, cleaned_output = extract_chart_series(output)

    def extract_float(pattern: str, default: float = 0.0) -> float:
        match = re.search(pattern, cleaned_output, re.IGNORECASE)
        return float(match.group(1)) if match else default

    def extract_int(pattern: str, default: int = 0) -> int:
        match = re.search(pattern, cleaned_output, re.IGNORECASE)
        return int(float(match.group(1))) if match else default

    metrics = {
        "pnl": extract_float(r"P&L:\s+\$\s*([+-]?\d+\.?\d*)"),
        "sharpe": extract_float(r"Sharpe:\s+([+-]?\d+\.?\d*)"),
        "max_drawdown": extract_float(r"Max DD:\s+\$\s*([+-]?\d+\.?\d*)"),
        "trade_count": extract_int(r"Trades:\s+(\d+)"),
    }

    price_series = [
        {"time": point["time"], "price": point["btc_price"]}
        for point in chart_points
        if "time" in point and "btc_price" in point
    ]

    portfolio_series = [
        {"time": point["time"], "value": point["portfolio_value"]}
        for point in chart_points
        if "time" in point and "portfolio_value" in point
    ]

    return {
        "metrics": metrics,
        "raw_output": cleaned_output,
        "price_series": price_series,
        "portfolio_series": portfolio_series,
    }


def run_backtest(config: StrategyConfig) -> dict:
    temp_strategy = build_temp_strategy(config)

    cmd = [
        sys.executable,
        "run_backtest.py",
        str(temp_strategy),
        "--data",
        "data/train/",
        "--hours",
        "1",
        "--assets",
        "BTC",
        "--intervals",
        "5m",
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        return {
            "error": "Backtest timed out",
            "cmd": cmd,
            "project_root": str(PROJECT_ROOT),
            "config_used": config.model_dump(),
        }
    except Exception as e:
        return {
            "error": "Subprocess failed before backtest finished",
            "details": str(e),
            "cmd": cmd,
            "project_root": str(PROJECT_ROOT),
            "strategy_file": str(BASE_STRATEGY_FILE),
            "config_used": config.model_dump(),
        }

    if result.returncode != 0:
        return {
            "error": "Backtest failed",
            "stderr": result.stderr,
            "stdout": result.stdout,
            "cmd": cmd,
            "project_root": str(PROJECT_ROOT),
            "strategy_file": str(BASE_STRATEGY_FILE),
            "config_used": config.model_dump(),
        }

    parsed = parse_backtest_output(result.stdout)
    parsed["cmd"] = cmd
    parsed["config_used"] = config.model_dump()
    return parsed