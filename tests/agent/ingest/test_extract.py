import unittest

from apps.agent.ingest.extract import extract_payload


def _build_pdf_bytes(text: str) -> bytes:
    escaped_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content_stream = f"BT\n/F1 18 Tf\n72 72 Td\n({escaped_text}) Tj\nET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
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
    trailer = f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF"
    return b"".join(parts) + xref.encode("latin-1") + trailer.encode("latin-1")


class ExtractPayloadTests(unittest.TestCase):
    def test_extracts_rss_payload_to_common_shape(self):
        source = {
            "id": "reuters_business",
            "name": "Reuters - Business News",
            "type": "rss",
            "paywall_policy": "full",
        }
        payload = {
            "url": "https://example.com/reuters/story-1",
            "title": "Inflation cools",
            "author": "Reuters",
            "language": "en",
            "published_at": "2026-03-10T01:00:00Z",
            "fetched_at": "2026-03-10T01:05:00Z",
            "summary": "Inflation slows for a second month.",
            "body_text": "Full article body.",
            "doc_type": "news",
        }

        extracted = extract_payload(source=source, payload=payload)

        self.assertEqual(extracted["publisher"], "Reuters - Business News")
        self.assertEqual(extracted["canonical_url"], payload["url"])
        self.assertEqual(extracted["rss_snippet"], payload["summary"])
        self.assertEqual(extracted["body_text"], payload["body_text"])

    def test_extracts_html_payload_to_common_shape(self):
        source = {
            "id": "boe_news",
            "name": "Bank of England - News",
            "type": "html",
            "paywall_policy": "full",
        }
        payload = {
            "canonical_url": "https://example.com/boe/news-1",
            "headline": "Policy statement",
            "byline": "BOE Staff",
            "language": "en",
            "published_at": "2026-03-10T02:00:00Z",
            "fetched_at": "2026-03-10T02:03:00Z",
            "snippet": "A short summary",
            "text": "HTML-derived article body",
            "doc_type": "policy_statement",
        }

        extracted = extract_payload(source=source, payload=payload)

        self.assertEqual(extracted["publisher"], "Bank of England - News")
        self.assertEqual(extracted["canonical_url"], payload["canonical_url"])
        self.assertEqual(extracted["title"], payload["headline"])
        self.assertEqual(extracted["author"], payload["byline"])
        self.assertEqual(extracted["rss_snippet"], payload["snippet"])
        self.assertEqual(extracted["body_text"], payload["text"])

    def test_extracts_pdf_payload_to_common_shape(self):
        source = {
            "id": "fomc_minutes_pdf",
            "name": "Federal Reserve - Minutes PDF",
            "type": "pdf",
            "paywall_policy": "full",
        }
        payload = {
            "url": "https://example.com/fed/minutes.pdf",
            "title": "FOMC Minutes",
            "author": "Federal Reserve",
            "language": "en",
            "published_at": "2026-03-10T03:00:00Z",
            "fetched_at": "2026-03-10T03:05:00Z",
            "summary": "Minutes for the latest FOMC meeting.",
            "pdf_bytes": _build_pdf_bytes("FOMC minutes note inflation progress."),
            "doc_type": "minutes",
        }

        extracted = extract_payload(source=source, payload=payload)

        self.assertEqual(extracted["publisher"], "Federal Reserve - Minutes PDF")
        self.assertEqual(extracted["canonical_url"], payload["url"])
        self.assertEqual(extracted["title"], payload["title"])
        self.assertEqual(extracted["rss_snippet"], payload["summary"])
        self.assertIn("FOMC minutes note inflation progress.", extracted["body_text"])
        self.assertEqual(extracted["doc_type"], "minutes")

    def test_pdf_payload_requires_text_or_bytes(self):
        source = {
            "id": "fomc_minutes_pdf",
            "name": "Federal Reserve - Minutes PDF",
            "type": "pdf",
            "paywall_policy": "full",
        }

        with self.assertRaisesRegex(ValueError, "PDF payload must include text, body_text, pdf_bytes, or pdf_base64"):
            extract_payload(
                source=source,
                payload={
                    "url": "https://example.com/fed/minutes.pdf",
                    "fetched_at": "2026-03-10T03:05:00Z",
                },
            )


if __name__ == "__main__":
    unittest.main()
