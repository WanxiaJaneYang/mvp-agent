import unittest

from apps.agent.pipeline.stage8_validation import run_stage8_citation_validation


class Stage8ValidationTests(unittest.TestCase):
    def test_stage8_sets_partial_status_on_removals(self):
        synthesis = {
            "prevailing": [{"text": "Bad", "citation_ids": []}],
            "counter": [{"text": "ok", "citation_ids": ["c1"]}],
            "minority": [{"text": "ok", "citation_ids": ["c2"]}],
            "watch": [{"text": "ok", "citation_ids": ["c3"]}],
        }
        store = {
            "c1": {"id": "c1", "url": "u1", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
            "c2": {"id": "c2", "url": "u2", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
            "c3": {"id": "c3", "url": "u3", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
        }

        result = run_stage8_citation_validation(synthesis, store)

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["report"]["removed_bullets"], 1)


if __name__ == "__main__":
    unittest.main()
