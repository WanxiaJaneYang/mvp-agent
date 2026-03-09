import unittest

from apps.agent.ingest.extract import extract_payload


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


if __name__ == "__main__":
    unittest.main()
