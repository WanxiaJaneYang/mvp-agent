from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from html import escape
from pathlib import Path
from smtplib import SMTP
from typing import Any, Callable, Mapping, Sequence

from apps.agent.alerts.policy_gate import AlertPolicyContext, AlertPolicyDecision
from apps.agent.delivery.email_sender import EmailDeliveryConfig
from apps.agent.storage.sqlite_runtime import ensure_runtime_db, persist_alert_record, runtime_db_path


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class AlertCitation:
    citation_id: str
    title: str
    url: str
    published_at: str | None = None


@dataclass(frozen=True)
class AlertBullet:
    text: str
    citations: tuple[AlertCitation, ...]


@dataclass(frozen=True)
class AlertDeliveryContent:
    alert_id: str
    category: str
    triggered_at: str
    headline: str
    summary: str
    bullets: tuple[AlertBullet, ...]
    why_it_matters: str
    what_to_watch: str


@dataclass(frozen=True)
class AlertBundleItem:
    headline: str
    summary: str
    bullets: tuple[AlertBullet, ...]
    why_it_matters: str
    what_to_watch: str


@dataclass(frozen=True)
class AlertDeliveryChannels:
    send_email: Callable[..., Any] | None = None
    write_local_page: Callable[..., Any] | None = None


@dataclass(frozen=True)
class AlertDeliveryResult:
    alert_id: str
    action: str
    delivery_status: str
    delivery_mode: str
    delivered_channels: tuple[str, ...]
    retry_eligible: bool
    failure_reason: str | None
    suppression_reason: str | None
    bundle_item: AlertBundleItem | None
    email_delivery: Any = None
    html_path: str | None = None
    runtime_db_path: str | None = None


def deliver_alert(
    *,
    content: AlertDeliveryContent,
    policy_decision: AlertPolicyDecision,
    channels: AlertDeliveryChannels,
) -> AlertDeliveryResult:
    _validate_content(content)
    bundle_item = _build_bundle_item(content) if policy_decision.bundle_for_daily_brief else None

    if policy_decision.action == "bundle":
        return AlertDeliveryResult(
            alert_id=content.alert_id,
            action="bundle",
            delivery_status="bundled",
            delivery_mode="none",
            delivered_channels=(),
            retry_eligible=False,
            failure_reason=None,
            suppression_reason=None,
            bundle_item=bundle_item,
        )

    if policy_decision.action == "suppress":
        return AlertDeliveryResult(
            alert_id=content.alert_id,
            action="suppress",
            delivery_status="suppressed",
            delivery_mode="none",
            delivered_channels=(),
            retry_eligible=False,
            failure_reason=None,
            suppression_reason=policy_decision.suppression_reason,
            bundle_item=bundle_item,
        )

    subject = f"Major Event Alert: {content.headline}"
    plain_text_body = _render_alert_plain_text(content)
    html_body = _render_alert_html(content)

    delivered_channels: list[str] = []
    failures: list[str] = []
    email_delivery: Any = None
    html_path: str | None = None

    if channels.send_email is not None:
        try:
            email_delivery = channels.send_email(
                subject=subject,
                plain_text_body=plain_text_body,
                html_body=html_body,
            )
        except Exception as exc:
            failures.append(f"email: {exc}")
        else:
            delivered_channels.append("email")

    if channels.write_local_page is not None:
        try:
            html_path = str(
                channels.write_local_page(
                    alert_id=content.alert_id,
                    html_body=html_body,
                )
            )
        except Exception as exc:
            failures.append(f"local_page: {exc}")
        else:
            delivered_channels.append("local_page")

    delivery_mode = _delivery_mode_for_channels(tuple(delivered_channels))
    if failures and delivered_channels:
        delivery_status = "partial"
    elif failures:
        delivery_status = "failed"
    else:
        delivery_status = "delivered"

    return AlertDeliveryResult(
        alert_id=content.alert_id,
        action="send",
        delivery_status=delivery_status,
        delivery_mode=delivery_mode,
        delivered_channels=tuple(delivered_channels),
        retry_eligible=delivery_status in {"partial", "failed"},
        failure_reason="; ".join(failures) if failures else None,
        suppression_reason=None,
        bundle_item=None,
        email_delivery=email_delivery,
        html_path=html_path,
    )


def deliver_runtime_alert(
    *,
    base_dir: Path,
    run_id: str,
    alert_id: str,
    category: str,
    triggered_at: str,
    title: str,
    summary: str,
    bullets: Sequence[Mapping[str, Any]],
    citation_store: Mapping[str, Mapping[str, Any]],
    policy_decision: AlertPolicyDecision,
    email_config: EmailDeliveryConfig | None = None,
    smtp_class: Any = SMTP,
) -> AlertDeliveryResult:
    ensure_runtime_db(base_dir=base_dir)
    created_at = _utc_now_iso()
    content = _build_content(
        alert_id=alert_id,
        category=category,
        triggered_at=triggered_at,
        title=title,
        summary=summary,
        bullets=bullets,
        citation_store=citation_store,
    )

    channels = AlertDeliveryChannels(
        send_email=(
            lambda *, subject, plain_text_body, html_body: _send_alert_email(
                config=email_config,
                subject=subject,
                plain_text_body=plain_text_body,
                html_body=html_body,
                smtp_class=smtp_class,
            )
            if email_config is not None
            else None
        )
        if email_config is not None
        else None,
        write_local_page=lambda *, alert_id, html_body: _write_local_page(
            base_dir=base_dir,
            alert_id=alert_id,
            triggered_at=triggered_at,
            html_body=html_body,
        ),
    )
    result = deliver_alert(
        content=content,
        policy_decision=policy_decision,
        channels=channels,
    )

    runtime_status = _runtime_delivery_status(result)
    delivered_email_at = created_at if "email" in result.delivered_channels else None
    delivered_local_page_at = created_at if "local_page" in result.delivered_channels else None
    db_path = persist_alert_record(
        base_dir=base_dir,
        row={
            "alert_id": alert_id,
            "run_id": run_id,
            "category": category,
            "title": title,
            "summary": summary,
            "action": policy_decision.action,
            "delivery_status": runtime_status,
            "score_total": policy_decision.score.total_score,
            "score_importance": policy_decision.score.inputs.importance,
            "score_evidence": policy_decision.score.inputs.evidence_strength,
            "score_confidence": policy_decision.score.inputs.confidence,
            "score_relevance": policy_decision.score.inputs.portfolio_relevance,
            "score_noise_risk": policy_decision.score.inputs.noise_risk,
            "triggered_at": triggered_at,
            "delivered_email_at": delivered_email_at,
            "delivered_local_page_at": delivered_local_page_at,
            "bundle_for_daily_brief": 1 if policy_decision.bundle_for_daily_brief else 0,
            "suppression_reason": policy_decision.suppression_reason,
            "failure_reason": result.failure_reason,
            "html_path": result.html_path,
            "created_at": created_at,
            "updated_at": created_at,
        },
    )

    return AlertDeliveryResult(
        alert_id=result.alert_id,
        action=result.action,
        delivery_status=runtime_status,
        delivery_mode=result.delivery_mode,
        delivered_channels=result.delivered_channels,
        retry_eligible=runtime_status == "failed",
        failure_reason=result.failure_reason,
        suppression_reason=result.suppression_reason,
        bundle_item=result.bundle_item,
        email_delivery=result.email_delivery,
        html_path=result.html_path,
        runtime_db_path=str(db_path),
    )


def load_alert_policy_context(
    *,
    base_dir: Path,
    triggered_at: str,
    budget_allowed: bool,
    max_alerts_per_day: int = 3,
    cooldown_minutes: int = 60,
) -> AlertPolicyContext:
    db_path = runtime_db_path(base_dir=base_dir)
    if not db_path.exists():
        return AlertPolicyContext(
            daily_alerts_sent=0,
            last_alert_sent_at=None,
            budget_allowed=budget_allowed,
            max_alerts_per_day=max_alerts_per_day,
            cooldown_minutes=cooldown_minutes,
        )

    delivered_statuses = ("delivered_html_only", "delivered_email_and_html")
    placeholders = ", ".join("?" for _ in delivered_statuses)
    day_partition = triggered_at[:10]
    connection = sqlite3.connect(db_path)
    try:
        daily_alerts_sent = int(
            connection.execute(
                f"""
                SELECT COUNT(*)
                FROM alerts
                WHERE delivery_status IN ({placeholders})
                  AND substr(triggered_at, 1, 10) = ?
                """,
                (*delivered_statuses, day_partition),
            ).fetchone()[0]
        )
        last_alert_sent_at = connection.execute(
            f"""
            SELECT triggered_at
            FROM alerts
            WHERE delivery_status IN ({placeholders})
              AND triggered_at <= ?
            ORDER BY triggered_at DESC
            LIMIT 1
            """,
            (*delivered_statuses, triggered_at),
        ).fetchone()
    finally:
        connection.close()

    return AlertPolicyContext(
        daily_alerts_sent=daily_alerts_sent,
        last_alert_sent_at=str(last_alert_sent_at[0]) if last_alert_sent_at else None,
        budget_allowed=budget_allowed,
        max_alerts_per_day=max_alerts_per_day,
        cooldown_minutes=cooldown_minutes,
    )


def _validate_content(content: AlertDeliveryContent) -> None:
    if not 3 <= len(content.bullets) <= 6:
        raise ValueError("Alert output must contain between 3 and 6 bullets.")
    for bullet in content.bullets:
        if not bullet.citations:
            raise ValueError("Each alert bullet must include at least one citation.")


def _build_bundle_item(content: AlertDeliveryContent) -> AlertBundleItem:
    return AlertBundleItem(
        headline=content.headline,
        summary=content.summary,
        bullets=content.bullets[:2],
        why_it_matters=content.why_it_matters,
        what_to_watch=content.what_to_watch,
    )


def _build_content(
    *,
    alert_id: str,
    category: str,
    triggered_at: str,
    title: str,
    summary: str,
    bullets: Sequence[Mapping[str, Any]],
    citation_store: Mapping[str, Mapping[str, Any]],
) -> AlertDeliveryContent:
    rendered_bullets: list[AlertBullet] = []
    for bullet in bullets:
        citations: list[AlertCitation] = []
        for citation_id in bullet.get("citation_ids", []):
            citation = citation_store.get(str(citation_id), {})
            citations.append(
                AlertCitation(
                    citation_id=str(citation_id),
                    title=str(citation.get("title") or citation_id),
                    url=str(citation.get("url") or "#"),
                    published_at=str(citation.get("published_at")) if citation.get("published_at") else None,
                )
            )
        rendered_bullets.append(
            AlertBullet(
                text=str(bullet.get("text") or ""),
                citations=tuple(citations),
            )
        )
    return AlertDeliveryContent(
        alert_id=alert_id,
        category=category,
        triggered_at=triggered_at,
        headline=title,
        summary=summary,
        bullets=tuple(rendered_bullets),
        why_it_matters=str(bullets[0].get("why_it_matters") or summary if bullets else summary),
        what_to_watch=str(bullets[-1].get("text") or summary if bullets else summary),
    )


def _delivery_mode_for_channels(channels: tuple[str, ...]) -> str:
    if channels == ("email", "local_page") or channels == ("local_page", "email"):
        return "email_and_local"
    if channels == ("email",):
        return "email_only"
    if channels == ("local_page",):
        return "local_only"
    return "none"


def _runtime_delivery_status(result: AlertDeliveryResult) -> str:
    if result.delivery_status == "bundled":
        return "bundled"
    if result.delivery_status == "suppressed":
        return "suppressed"
    if result.delivery_status in {"partial", "failed"}:
        return "failed"
    if "email" in result.delivered_channels:
        return "delivered_email_and_html"
    return "delivered_html_only"


def _render_alert_plain_text(content: AlertDeliveryContent) -> str:
    lines = [
        f"Alert category: {content.category}",
        f"Triggered at: {content.triggered_at}",
        f"Headline: {content.headline}",
        f"Summary: {content.summary}",
        "Why it matters:",
        content.why_it_matters,
        "What to watch next:",
        content.what_to_watch,
    ]
    for bullet in content.bullets:
        lines.append(f"- {bullet.text}")
    return "\n".join(lines)


def _render_alert_html(content: AlertDeliveryContent) -> str:
    bullet_html = []
    for bullet in content.bullets:
        citations = "".join(
            f'<li><a href="{escape(citation.url)}">{escape(citation.title)}</a></li>'
            for citation in bullet.citations
        )
        bullet_html.append(
            "<li>"
            f"<p>{escape(bullet.text)}</p>"
            f"<ul>{citations}</ul>"
            "</li>"
        )
    return (
        "<!doctype html>"
        "<html><head><meta charset=\"utf-8\">"
        f"<title>{escape(content.headline)}</title>"
        "</head><body>"
        f"<h1>{escape(content.headline)}</h1>"
        f"<p><strong>Category:</strong> {escape(content.category)}</p>"
        f"<p><strong>Triggered:</strong> {escape(content.triggered_at)}</p>"
        f"<p>{escape(content.summary)}</p>"
        "<h2>Why it matters</h2>"
        f"<p>{escape(content.why_it_matters)}</p>"
        "<h2>What to watch next</h2>"
        f"<p>{escape(content.what_to_watch)}</p>"
        f"<ol>{''.join(bullet_html)}</ol>"
        "</body></html>"
    )


def _write_local_page(*, base_dir: Path, alert_id: str, triggered_at: str, html_body: str) -> str:
    artifact_dir = base_dir / "artifacts" / "alerts" / triggered_at[:10]
    artifact_dir.mkdir(parents=True, exist_ok=True)
    html_path = artifact_dir / f"{alert_id}.html"
    html_path.write_text(html_body, encoding="utf-8")
    return str(html_path)


def _send_alert_email(
    *,
    config: EmailDeliveryConfig,
    subject: str,
    plain_text_body: str,
    html_body: str,
    smtp_class: Any,
) -> dict[str, Any]:
    if not config.recipient_emails:
        raise ValueError("recipient_emails must include at least one address.")

    message = EmailMessage()
    message["From"] = config.sender_email
    message["To"] = ", ".join(config.recipient_emails)
    message["Subject"] = subject.replace("Major Event Alert", config.subject_prefix, 1)
    message.set_content(plain_text_body)
    message.add_alternative(html_body, subtype="html")

    with smtp_class(config.smtp_host, config.smtp_port, timeout=config.timeout_seconds) as smtp_client:
        if config.use_starttls:
            smtp_client.starttls()
        smtp_client.send_message(message)

    return {
        "recipient_count": len(config.recipient_emails),
        "subject": str(message["Subject"]),
        "smtp_host": config.smtp_host,
    }
