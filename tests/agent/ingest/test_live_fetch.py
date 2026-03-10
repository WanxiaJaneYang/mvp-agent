import unittest
from unittest.mock import patch

from apps.agent.ingest.live_fetch import fetch_live_payloads_for_source, parse_rss_feed

RSS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example Feed</title>
    <item>
      <title>Fed keeps policy steady</title>
      <link>https://example.test/fed</link>
      <pubDate>Tue, 10 Mar 2026 14:00:00 GMT</pubDate>
      <description>Fed officials kept policy steady.</description>
    </item>
    <item>
      <title>BLS releases CPI update</title>
      <link>https://example.test/bls</link>
      <pubDate>2026-03-10T13:30:00Z</pubDate>
      <description>CPI update for February.</description>
    </item>
  </channel>
</rss>
"""


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class LiveFetchTests(unittest.TestCase):
    def test_parse_rss_feed_returns_runtime_payload_shape(self):
        payloads = parse_rss_feed(
            feed_text=RSS_FEED,
            fetched_at_utc="2026-03-10T16:00:00Z",
        )

        self.assertEqual(len(payloads), 2)
        self.assertEqual(payloads[0]["url"], "https://example.test/fed")
        self.assertEqual(payloads[0]["title"], "Fed keeps policy steady")
        self.assertEqual(payloads[0]["published_at"], "2026-03-10T14:00:00Z")
        self.assertEqual(payloads[1]["published_at"], "2026-03-10T13:30:00Z")
        self.assertEqual(payloads[0]["doc_type"], "rss")

    def test_fetch_live_payloads_for_source_reads_rss_feed(self):
        source = {
            "id": "fed_press_releases",
            "url": "https://example.test/feed.xml",
            "type": "rss",
        }

        with patch(
            "apps.agent.ingest.live_fetch.urlopen",
            return_value=_FakeResponse(RSS_FEED.encode("utf-8")),
        ):
            payloads = fetch_live_payloads_for_source(
                source=source,
                fetched_at_utc="2026-03-10T16:00:00Z",
            )

        self.assertEqual(len(payloads), 2)
        self.assertEqual(payloads[0]["fetched_at"], "2026-03-10T16:00:00Z")

    def test_fetch_live_payloads_rejects_non_rss_source_type_for_current_slice(self):
        with self.assertRaises(ValueError):
            fetch_live_payloads_for_source(
                source={"id": "boe_news", "url": "https://example.test/news", "type": "html"},
                fetched_at_utc="2026-03-10T16:00:00Z",
            )


if __name__ == "__main__":
    unittest.main()
