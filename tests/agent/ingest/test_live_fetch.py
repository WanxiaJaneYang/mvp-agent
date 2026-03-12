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

HTML_PAGE = """<!doctype html>
<html lang="en">
  <head>
    <title>Bank of England policy update</title>
    <link rel="canonical" href="https://example.test/boe/policy-update" />
    <meta name="description" content="A short HTML summary." />
    <meta name="author" content="BOE Staff" />
    <meta property="article:published_time" content="2026-03-10T14:00:00Z" />
  </head>
  <body>
    <main>
      <h1>Policy update</h1>
      <p>The committee left policy unchanged.</p>
      <p>Officials emphasized data dependence.</p>
    </main>
  </body>
</html>
"""


def _build_pdf_bytes(text: str) -> bytes:
    escaped_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content_stream = f"BT\n/F1 18 Tf\n72 72 Td\n({escaped_text}) Tj\nET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content_stream.encode('latin-1'))} >>\nstream\n{content_stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    parts: list[bytes] = [b"%PDF-1.4\n"]
    offsets: list[int] = [0]
    current_offset = len(parts[0])
    for index, body in enumerate(objects, start=1):
        object_bytes = f"{index} 0 obj\n{body}\nendobj\n".encode("latin-1")
        offsets.append(current_offset)
        parts.append(object_bytes)
        current_offset += len(object_bytes)

    xref_offset = current_offset
    xref_rows = ["0000000000 65535 f \n"]
    xref_rows.extend(f"{offset:010d} 00000 n \n" for offset in offsets[1:])
    xref = f"xref\n0 {len(objects) + 1}\n{''.join(xref_rows)}"
    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF"
    )
    return b"".join(parts) + xref.encode("latin-1") + trailer.encode("latin-1")


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

    def test_fetch_live_payloads_for_source_reads_html_page(self):
        source = {
            "id": "boe_news",
            "url": "https://example.test/boe/policy-update",
            "type": "html",
        }

        with patch(
            "apps.agent.ingest.live_fetch.urlopen",
            return_value=_FakeResponse(HTML_PAGE.encode("utf-8")),
        ):
            payloads = fetch_live_payloads_for_source(
                source=source,
                fetched_at_utc="2026-03-10T16:00:00Z",
            )

        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["canonical_url"], "https://example.test/boe/policy-update")
        self.assertEqual(payloads[0]["headline"], "Bank of England policy update")
        self.assertEqual(payloads[0]["byline"], "BOE Staff")
        self.assertEqual(payloads[0]["published_at"], "2026-03-10T14:00:00Z")
        self.assertEqual(payloads[0]["snippet"], "A short HTML summary.")
        self.assertIn("The committee left policy unchanged.", payloads[0]["text"])

    def test_fetch_live_payloads_for_source_reads_pdf_bytes(self):
        source = {
            "id": "fed_minutes_pdf",
            "url": "https://example.test/fed/minutes.pdf",
            "type": "pdf",
        }

        with patch(
            "apps.agent.ingest.live_fetch.urlopen",
            return_value=_FakeResponse(_build_pdf_bytes("FOMC minutes note inflation progress.")),
        ):
            payloads = fetch_live_payloads_for_source(
                source=source,
                fetched_at_utc="2026-03-10T16:00:00Z",
            )

        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["canonical_url"], "https://example.test/fed/minutes.pdf")
        self.assertEqual(payloads[0]["url"], "https://example.test/fed/minutes.pdf")
        self.assertEqual(payloads[0]["fetched_at"], "2026-03-10T16:00:00Z")
        self.assertEqual(payloads[0]["doc_type"], "pdf")
        self.assertIsInstance(payloads[0]["pdf_bytes"], bytes)

    def test_fetch_live_payloads_rejects_unknown_source_type(self):
        with self.assertRaises(ValueError):
            fetch_live_payloads_for_source(
                source={"id": "boe_news", "url": "https://example.test/news", "type": "api"},
                fetched_at_utc="2026-03-10T16:00:00Z",
            )


if __name__ == "__main__":
    unittest.main()
