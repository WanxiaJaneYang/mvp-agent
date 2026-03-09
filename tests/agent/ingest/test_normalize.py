import unittest

from apps.agent.ingest.normalize import build_document_record


class NormalizeDocumentTests(unittest.TestCase):
    def test_metadata_only_source_forces_body_text_to_none(self):
        source = {
            "id": "ft_markets",
            "name": "Financial Times - Markets",
            "paywall_policy": "metadata_only",
        }
        extracted = {
            "publisher": "Financial Times - Markets",
            "canonical_url": "https://example.com/ft/story-1",
            "title": "Rates shift",
            "author": "FT Staff",
            "language": "en",
            "doc_type": "news",
            "published_at": "2026-03-10T03:00:00Z",
            "fetched_at": "2026-03-10T03:05:00Z",
            "rss_snippet": "Markets react to central bank guidance.",
            "body_text": "This text must not survive normalization.",
        }

        document = build_document_record(source=source, extracted=extracted)

        self.assertEqual(document["source_id"], "ft_markets")
        self.assertEqual(document["paywall_policy"], "metadata_only")
        self.assertEqual(document["metadata_only"], 1)
        self.assertIsNone(document["body_text"])
        self.assertEqual(document["rss_snippet"], extracted["rss_snippet"])
        self.assertEqual(document["status"], "active")
        self.assertEqual(len(document["content_hash"]), 64)

    def test_full_source_preserves_body_text(self):
        source = {
            "id": "reuters_business",
            "name": "Reuters - Business News",
            "paywall_policy": "full",
        }
        extracted = {
            "publisher": "Reuters - Business News",
            "canonical_url": "https://example.com/reuters/story-1",
            "title": "Inflation cools",
            "author": "Reuters",
            "language": "en",
            "doc_type": "news",
            "published_at": "2026-03-10T01:00:00Z",
            "fetched_at": "2026-03-10T01:05:00Z",
            "rss_snippet": "Inflation slows for a second month.",
            "body_text": "Full article body.",
        }

        document = build_document_record(source=source, extracted=extracted)

        self.assertEqual(document["source_id"], "reuters_business")
        self.assertEqual(document["publisher"], source["name"])
        self.assertEqual(document["canonical_url"], extracted["canonical_url"])
        self.assertEqual(document["title"], extracted["title"])
        self.assertEqual(document["metadata_only"], 0)
        self.assertEqual(document["body_text"], extracted["body_text"])
        self.assertEqual(document["created_at"], extracted["fetched_at"])
        self.assertEqual(document["updated_at"], extracted["fetched_at"])


if __name__ == "__main__":
    unittest.main()
