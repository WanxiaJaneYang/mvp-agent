from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the deterministic daily-brief fixture slice.")
    parser.add_argument("--base-dir", default=str(ROOT), help="Base directory for artifact output.")
    parser.add_argument("--fixture-path", help="Optional override for the fixture payload JSON file.")
    parser.add_argument("--run-id", default="run_daily_fixture", help="Stable run identifier for the slice.")
    parser.add_argument("--generated-at-utc", help="Optional UTC timestamp override in ISO-8601 format.")
    parser.add_argument("--timezone", default="Asia/Singapore", help="IANA timezone for daily scheduling metadata.")
    parser.add_argument("--delivery-hour", type=int, default=7, help="Scheduled local delivery hour.")
    parser.add_argument("--delivery-minute", type=int, default=5, help="Scheduled local delivery minute.")
    parser.add_argument("--smtp-host", help="Optional SMTP host for email delivery.")
    parser.add_argument("--smtp-port", type=int, default=587, help="SMTP port for email delivery.")
    parser.add_argument("--sender-email", help="Sender address for email delivery.")
    parser.add_argument(
        "--recipient-email",
        action="append",
        default=[],
        help="Recipient address for email delivery. Repeat for multiple recipients.",
    )
    return parser.parse_args()


def main() -> None:
    from apps.agent.daily_brief.runner import run_fixture_daily_brief
    from apps.agent.delivery.email_sender import EmailDeliveryConfig
    from apps.agent.delivery.scheduler import DailyBriefSchedule

    args = parse_args()
    email_config = None
    if args.smtp_host or args.sender_email or args.recipient_email:
        if not args.smtp_host or not args.sender_email or not args.recipient_email:
            raise SystemExit("--smtp-host, --sender-email, and at least one --recipient-email are required together.")
        email_config = EmailDeliveryConfig(
            smtp_host=args.smtp_host,
            smtp_port=args.smtp_port,
            sender_email=args.sender_email,
            recipient_emails=tuple(args.recipient_email),
        )
    result = run_fixture_daily_brief(
        base_dir=Path(args.base_dir),
        fixture_path=Path(args.fixture_path) if args.fixture_path else None,
        run_id=args.run_id,
        generated_at_utc=args.generated_at_utc,
        delivery_schedule=DailyBriefSchedule(
            timezone_name=args.timezone,
            delivery_hour=args.delivery_hour,
            delivery_minute=args.delivery_minute,
        ),
        email_config=email_config,
    )
    print(json.dumps(result, indent=2))
    if result["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
