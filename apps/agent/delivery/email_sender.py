from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
from smtplib import SMTP
from typing import Any


@dataclass(frozen=True)
class EmailDeliveryConfig:
    smtp_host: str
    smtp_port: int
    sender_email: str
    recipient_emails: tuple[str, ...]
    use_starttls: bool = True
    subject_prefix: str = "Daily Brief"
    timeout_seconds: float = 30.0


def send_daily_brief_email(
    *,
    config: EmailDeliveryConfig,
    report_date: str,
    run_id: str,
    html_body: str,
    status_title: str,
    smtp_class: Any = SMTP,
) -> dict[str, Any]:
    if not config.recipient_emails:
        raise ValueError("recipient_emails must include at least one address.")

    subject = f"{config.subject_prefix}: {report_date}"
    message = EmailMessage()
    message["From"] = config.sender_email
    message["To"] = ", ".join(config.recipient_emails)
    message["Subject"] = subject
    message.set_content(
        "\n".join(
            [
                f"Daily Brief status: {status_title}",
                f"Report date: {report_date}",
                f"Run: {run_id}",
            ]
        )
    )
    message.add_alternative(html_body, subtype="html")

    with smtp_class(config.smtp_host, config.smtp_port, timeout=config.timeout_seconds) as smtp_client:
        if config.use_starttls:
            smtp_client.starttls()
        smtp_client.send_message(message)

    return {
        "recipient_count": len(config.recipient_emails),
        "subject": subject,
        "smtp_host": config.smtp_host,
    }
