"""Run the examination-only Phase 2.5 reliability package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.phase2_5_reliability.dataset_schema_profiler import (
    load_reliability_config,
    with_execution_overrides,
)
from src.phase2_5_reliability.reliability_runner_controller import ReliabilityRunnerController


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/phase2_5_reliability.json")
    parser.add_argument("--mode", choices=["smoke", "sample", "full"], default=None)
    parser.add_argument("--seed", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = (PROJECT_ROOT / args.config).resolve()
    config = with_execution_overrides(load_reliability_config(config_path), args.mode, args.seed)
    manifest = ReliabilityRunnerController(PROJECT_ROOT, config).run()
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
