from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the live daily brief on the active source subset."
    )
    parser.add_argument("--base-dir", default=str(ROOT), help="Base directory for artifact output.")
    parser.add_argument(
        "--run-id", default="run_daily_live", help="Stable run identifier for the slice."
    )
    parser.add_argument(
        "--generated-at-utc", help="Optional UTC timestamp override in ISO-8601 format."
    )
    return parser.parse_args()


def main() -> None:
    from apps.agent.daily_brief.runner import run_daily_brief

    args = parse_args()
    result = run_daily_brief(
        base_dir=Path(args.base_dir),
        run_id=args.run_id,
        generated_at_utc=args.generated_at_utc,
    )
    print(json.dumps(result, indent=2))
    if result["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
