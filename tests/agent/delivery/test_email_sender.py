import unittest

from apps.agent.delivery.email_sender import EmailDeliveryConfig, send_daily_brief_email


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


class DailyBriefEmailSenderTests(unittest.TestCase):
    def test_send_daily_brief_email_builds_and_sends_html_message(self):
        result = send_daily_brief_email(
            config=EmailDeliveryConfig(
                smtp_host="smtp.example.test",
                smtp_port=2525,
                sender_email="briefs@example.test",
                recipient_emails=("pm@example.test", "risk@example.test"),
            ),
            report_date="2026-03-10",
            run_id="run_delivery",
            html_body="<html><body><h1>Daily Brief</h1></body></html>",
            status_title="Validated",
            smtp_class=_FakeSMTP,
        )

        message = _FakeSMTP.last_instance.sent_messages[0]

        self.assertEqual(result["recipient_count"], 2)
        self.assertEqual(result["subject"], "Daily Brief: 2026-03-10")
        self.assertTrue(_FakeSMTP.last_instance.started_tls)
        self.assertEqual(message["To"], "pm@example.test, risk@example.test")
        self.assertEqual(message["Subject"], "Daily Brief: 2026-03-10")
        self.assertIn("Daily Brief", message.as_string())


if __name__ == "__main__":
    unittest.main()
