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
    synthesis: dict[str, Any] | None = None,
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
                *_build_plain_text_summary(synthesis=synthesis),
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


def _build_plain_text_summary(*, synthesis: dict[str, Any] | None) -> list[str]:
    if not isinstance(synthesis, dict):
        return []

    lines: list[str] = []
    brief = synthesis.get("brief")
    if isinstance(brief, dict):
        bottom_line = str(brief.get("bottom_line") or "").strip()
        if bottom_line:
            lines.append(f"Bottom line: {bottom_line}")

    issues = synthesis.get("issues", [])
    if not isinstance(issues, list):
        return lines

    for issue in issues[:1]:
        if not isinstance(issue, dict):
            continue
        issue_title = str(issue.get("title") or issue.get("issue_question") or "").strip()
        if issue_title:
            lines.append(f"Issue: {issue_title}")
        for section in ("prevailing", "counter", "minority", "watch"):
            bullets = issue.get(section, [])
            if not isinstance(bullets, list) or not bullets:
                continue
            bullet = bullets[0]
            if not isinstance(bullet, dict):
                continue
            novelty = str(bullet.get("novelty_vs_prior_brief") or "").strip()
            claim_text = str(bullet.get("text") or "").strip()
            why_it_matters = str(bullet.get("why_it_matters") or "").strip()
            if claim_text:
                prefix = f"{section}: "
                if novelty and novelty != "unknown":
                    prefix = f"{section} [{novelty}]: "
                lines.append(prefix + claim_text)
            if why_it_matters:
                lines.append(f"Why it matters: {why_it_matters}")
    return lines
