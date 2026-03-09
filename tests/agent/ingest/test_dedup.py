import unittest

from apps.agent.ingest.dedup import classify_duplicate


class DeduplicationTests(unittest.TestCase):
    def test_flags_duplicate_by_canonical_url(self):
        candidate = {
            "canonical_url": "https://example.com/story-1",
            "content_hash": "hash-new",
        }
        existing_documents = [
            {
                "doc_id": "doc_existing",
                "canonical_url": "https://example.com/story-1",
                "content_hash": "hash-old",
            }
        ]

        result = classify_duplicate(candidate=candidate, existing_documents=existing_documents)

        self.assertEqual(result["is_duplicate"], True)
        self.assertEqual(result["reason"], "canonical_url")
        self.assertEqual(result["matched_doc_id"], "doc_existing")

    def test_flags_duplicate_by_content_hash(self):
        candidate = {
            "canonical_url": "https://example.com/story-2",
            "content_hash": "hash-same",
        }
        existing_documents = [
            {
                "doc_id": "doc_existing",
                "canonical_url": "https://example.com/story-1",
                "content_hash": "hash-same",
            }
        ]

        result = classify_duplicate(candidate=candidate, existing_documents=existing_documents)

        self.assertEqual(result["is_duplicate"], True)
        self.assertEqual(result["reason"], "content_hash")
        self.assertEqual(result["matched_doc_id"], "doc_existing")

    def test_returns_non_duplicate_when_no_exact_match_exists(self):
        candidate = {
            "canonical_url": "https://example.com/story-2",
            "content_hash": "hash-two",
        }
        existing_documents = [
            {
                "doc_id": "doc_existing",
                "canonical_url": "https://example.com/story-1",
                "content_hash": "hash-one",
            }
        ]

        result = classify_duplicate(candidate=candidate, existing_documents=existing_documents)

        self.assertEqual(
            result,
            {
                "is_duplicate": False,
                "reason": None,
                "matched_doc_id": None,
            },
        )


if __name__ == "__main__":
    unittest.main()
