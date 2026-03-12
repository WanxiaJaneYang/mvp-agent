import sqlite3
import tempfile
import unittest
from pathlib import Path

from apps.agent.alerts.policy_gate import AlertPolicyDecision
from apps.agent.alerts.scoring import AlertScoreInputs, compute_alert_score
from apps.agent.delivery.alert_delivery import (
    AlertBullet,
    AlertCitation,
    AlertDeliveryChannels,
    AlertDeliveryContent,
    deliver_alert,
    deliver_runtime_alert,
    load_alert_policy_context,
)
from apps.agent.delivery.email_sender import EmailDeliveryConfig


class _FakeSMTP:
    last_instance = None

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.sent_messages = []
        _FakeSMTP.last_instance = self

    def __enter__(self) -> "_FakeSMTP":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def starttls(self) -> None:
        self.started_tls = True

    def send_message(self, message) -> None:
        self.sent_messages.append(message)


class _FailingSMTP(_FakeSMTP):
    def send_message(self, message) -> None:
        raise RuntimeError("smtp offline")


def _score():
    return compute_alert_score(
        category="policy",
        inputs=AlertScoreInputs(
            importance=90,
            evidence_strength=90,
            confidence=85,
            portfolio_relevance=50,
            noise_risk=5,
        ),
    )


def _content() -> AlertDeliveryContent:
    citation = AlertCitation(
        citation_id="cite_001",
        title="Fed Signals Cautious Patience",
        url="https://example.test/fed-signals",
        published_at="2026-03-12T08:00:00Z",
    )
    return AlertDeliveryContent(
        alert_id="alert_001",
        category="policy",
        triggered_at="2026-03-12T08:05:00Z",
        headline="Fed repricing stays event-driven",
        summary="Markets moved more than the official language changed.",
        bullets=(
            AlertBullet(text="The statement stayed cautious despite softer macro data.", citations=(citation,)),
            AlertBullet(text="Rate-sensitive assets rallied on a dovish read-through.", citations=(citation,)),
            AlertBullet(text="The next inflation print matters more than the headline reaction.", citations=(citation,)),
        ),
        why_it_matters="A wider market-policy gap can reverse quickly on the next official release.",
        what_to_watch="Next CPI and any Fedspeak that narrows the interpretation gap.",
    )


class AlertDeliveryTests(unittest.TestCase):
    def test_deliver_alert_sends_configured_channels_for_send_action(self):
        email_calls: list[tuple[str, str, str]] = []
        local_calls: list[tuple[str, str]] = []

        def send_email(*, subject: str, plain_text_body: str, html_body: str) -> str:
            email_calls.append((subject, plain_text_body, html_body))
            return "smtp://delivery/1"

        def write_local_page(*, alert_id: str, html_body: str) -> str:
            local_calls.append((alert_id, html_body))
            return "artifacts/runtime/alerts/alert_001.html"

        result = deliver_alert(
            content=_content(),
            policy_decision=AlertPolicyDecision(
                action="send",
                score=_score(),
                suppression_reason=None,
                bundle_for_daily_brief=False,
            ),
            channels=AlertDeliveryChannels(
                send_email=send_email,
                write_local_page=write_local_page,
            ),
        )

        self.assertEqual(result.delivery_status, "delivered")
        self.assertEqual(result.delivery_mode, "email_and_local")
        self.assertEqual(result.delivered_channels, ("email", "local_page"))
        self.assertFalse(result.retry_eligible)
        self.assertEqual(result.failure_reason, None)
        self.assertEqual(result.bundle_item, None)
        self.assertEqual(len(email_calls), 1)
        self.assertEqual(len(local_calls), 1)
        self.assertIn("Major Event Alert", email_calls[0][0])
        self.assertIn("why it matters", email_calls[0][1].lower())
        self.assertIn("What to watch next", local_calls[0][1])

    def test_deliver_alert_returns_bundle_without_dispatch_when_policy_bundles(self):
        result = deliver_alert(
            content=_content(),
            policy_decision=AlertPolicyDecision(
                action="bundle",
                score=_score(),
                suppression_reason=None,
                bundle_for_daily_brief=True,
            ),
            channels=AlertDeliveryChannels(),
        )

        self.assertEqual(result.delivery_status, "bundled")
        self.assertEqual(result.delivery_mode, "none")
        self.assertEqual(result.delivered_channels, ())
        self.assertFalse(result.retry_eligible)
        self.assertIsNotNone(result.bundle_item)
        self.assertEqual(len(result.bundle_item.bullets), 2)
        self.assertEqual(result.bundle_item.headline, "Fed repricing stays event-driven")

    def test_deliver_alert_returns_suppressed_bundle_for_cooldown_block(self):
        result = deliver_alert(
            content=_content(),
            policy_decision=AlertPolicyDecision(
                action="suppress",
                score=_score(),
                suppression_reason="cooldown_active",
                bundle_for_daily_brief=True,
            ),
            channels=AlertDeliveryChannels(),
        )

        self.assertEqual(result.delivery_status, "suppressed")
        self.assertEqual(result.delivery_mode, "none")
        self.assertEqual(result.suppression_reason, "cooldown_active")
        self.assertFalse(result.retry_eligible)
        self.assertIsNotNone(result.bundle_item)
        self.assertEqual(result.bundle_item.why_it_matters, _content().why_it_matters)

    def test_deliver_alert_marks_partial_failure_as_retry_eligible(self):
        def send_email(*, subject: str, plain_text_body: str, html_body: str) -> str:
            return "smtp://delivery/1"

        def write_local_page(*, alert_id: str, html_body: str) -> str:
            raise OSError("disk full")

        result = deliver_alert(
            content=_content(),
            policy_decision=AlertPolicyDecision(
                action="send",
                score=_score(),
                suppression_reason=None,
                bundle_for_daily_brief=False,
            ),
            channels=AlertDeliveryChannels(
                send_email=send_email,
                write_local_page=write_local_page,
            ),
        )

        self.assertEqual(result.delivery_status, "partial")
        self.assertEqual(result.delivered_channels, ("email",))
        self.assertTrue(result.retry_eligible)
        self.assertIn("local_page: disk full", result.failure_reason or "")

    def test_deliver_alert_rejects_invalid_alert_shape(self):
        citation = AlertCitation(
            citation_id="cite_001",
            title="Single Source",
            url="https://example.test/source",
            published_at="2026-03-12T08:00:00Z",
        )

        with self.assertRaises(ValueError):
            deliver_alert(
                content=AlertDeliveryContent(
                    alert_id="alert_bad",
                    category="policy",
                    triggered_at="2026-03-12T08:05:00Z",
                    headline="Too short",
                    summary="Invalid because it only has two bullets.",
                    bullets=(
                        AlertBullet(text="Bullet one", citations=(citation,)),
                        AlertBullet(text="Bullet two", citations=(citation,)),
                    ),
                    why_it_matters="Still matters.",
                    what_to_watch="Still watching.",
                ),
                policy_decision=AlertPolicyDecision(
                    action="send",
                    score=_score(),
                    suppression_reason=None,
                    bundle_for_daily_brief=False,
                ),
                channels=AlertDeliveryChannels(),
            )

    def test_deliver_runtime_alert_writes_html_sends_email_and_persists_delivery_row(self):
        content = _content()
        result = deliver_runtime_alert(
            base_dir=Path(tempfile.mkdtemp()),
            run_id="run_alert_send",
            alert_id=content.alert_id,
            category=content.category,
            triggered_at=content.triggered_at,
            title=content.headline,
            summary=content.summary,
            bullets=[
                {"text": bullet.text, "citation_ids": [citation.citation_id for citation in bullet.citations]}
                for bullet in content.bullets
            ],
            citation_store={
                "cite_001": {
                    "title": "Fed Signals Cautious Patience",
                    "url": "https://example.test/fed-signals",
                    "published_at": "2026-03-12T08:00:00Z",
                }
            },
            policy_decision=AlertPolicyDecision(
                action="send",
                score=_score(),
                suppression_reason=None,
                bundle_for_daily_brief=False,
            ),
            email_config=EmailDeliveryConfig(
                smtp_host="smtp.example.test",
                smtp_port=2525,
                sender_email="alerts@example.test",
                recipient_emails=("pm@example.test",),
                subject_prefix="Alert",
            ),
            smtp_class=_FakeSMTP,
        )

        self.assertEqual(result.delivery_status, "delivered_email_and_html")
        self.assertFalse(result.retry_eligible)
        self.assertIsNotNone(result.html_path)
        self.assertTrue(Path(result.html_path or "").exists())
        self.assertEqual(_FakeSMTP.last_instance.sent_messages[0]["Subject"], "Alert: Fed repricing stays event-driven")

        connection = sqlite3.connect(result.runtime_db_path)
        try:
            persisted = connection.execute(
                "SELECT action, delivery_status, suppression_reason, failure_reason FROM alerts WHERE alert_id = ?",
                (content.alert_id,),
            ).fetchone()
        finally:
            connection.close()

        self.assertEqual(persisted, ("send", "delivered_email_and_html", None, None))

    def test_deliver_runtime_alert_marks_email_failures_retryable_and_context_ignores_them(self):
        content = _content()
        with tempfile.TemporaryDirectory() as tmpdir:
            ok_result = deliver_runtime_alert(
                base_dir=Path(tmpdir),
                run_id="run_alert_ok",
                alert_id="alert_ok",
                category=content.category,
                triggered_at="2026-03-12T08:05:00Z",
                title=content.headline,
                summary=content.summary,
                bullets=[
                    {"text": bullet.text, "citation_ids": [citation.citation_id for citation in bullet.citations]}
                    for bullet in content.bullets
                ],
                citation_store={
                    "cite_001": {
                        "title": "Fed Signals Cautious Patience",
                        "url": "https://example.test/fed-signals",
                    }
                },
                policy_decision=AlertPolicyDecision(
                    action="send",
                    score=_score(),
                    suppression_reason=None,
                    bundle_for_daily_brief=False,
                ),
                email_config=None,
            )
            failed_result = deliver_runtime_alert(
                base_dir=Path(tmpdir),
                run_id="run_alert_fail",
                alert_id="alert_fail",
                category=content.category,
                triggered_at="2026-03-12T09:05:00Z",
                title=content.headline,
                summary=content.summary,
                bullets=[
                    {"text": bullet.text, "citation_ids": [citation.citation_id for citation in bullet.citations]}
                    for bullet in content.bullets
                ],
                citation_store={
                    "cite_001": {
                        "title": "Fed Signals Cautious Patience",
                        "url": "https://example.test/fed-signals",
                    }
                },
                policy_decision=AlertPolicyDecision(
                    action="send",
                    score=_score(),
                    suppression_reason=None,
                    bundle_for_daily_brief=False,
                ),
                email_config=EmailDeliveryConfig(
                    smtp_host="smtp.example.test",
                    smtp_port=2525,
                    sender_email="alerts@example.test",
                    recipient_emails=("pm@example.test",),
                    subject_prefix="Alert",
                ),
                smtp_class=_FailingSMTP,
            )

            context = load_alert_policy_context(
                base_dir=Path(tmpdir),
                triggered_at="2026-03-12T09:30:00Z",
                budget_allowed=True,
            )

        self.assertEqual(ok_result.delivery_status, "delivered_html_only")
        self.assertEqual(failed_result.delivery_status, "failed")
        self.assertTrue(failed_result.retry_eligible)
        self.assertEqual(context.daily_alerts_sent, 1)
        self.assertEqual(context.last_alert_sent_at, "2026-03-12T08:05:00Z")


if __name__ == "__main__":
    unittest.main()
