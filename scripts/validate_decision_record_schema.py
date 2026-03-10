from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.agent.pipeline.decision_record_validation import (
    validate_decision_record,
    validate_example_file,
)


def main() -> None:
    errors = validate_example_file()
    if errors:
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("Decision record schema validation passed.")


if __name__ == "__main__":
    main()
