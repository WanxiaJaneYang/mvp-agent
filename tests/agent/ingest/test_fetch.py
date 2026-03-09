import unittest

from apps.agent.ingest.fetch import plan_fetch_items


class FetchPlannerTests(unittest.TestCase):
    def test_applies_per_source_cap_before_combining_results(self):
        sources = [
            {"id": "src_alpha", "per_fetch_cap": 2},
            {"id": "src_beta", "per_fetch_cap": 1},
        ]
        candidate_payloads = {
            "src_alpha": [{"item": 1}, {"item": 2}, {"item": 3}],
            "src_beta": [{"item": "a"}, {"item": "b"}],
        }

        planned = plan_fetch_items(
            sources=sources,
            candidate_payloads=candidate_payloads,
            global_cap=10,
        )

        self.assertEqual(
            planned,
            [
                {"source_id": "src_alpha", "payload": {"item": 1}},
                {"source_id": "src_alpha", "payload": {"item": 2}},
                {"source_id": "src_beta", "payload": {"item": "a"}},
            ],
        )

    def test_applies_global_cap_across_sources_in_order(self):
        sources = [
            {"id": "src_alpha"},
            {"id": "src_beta"},
        ]
        candidate_payloads = {
            "src_alpha": [{"item": 1}, {"item": 2}],
            "src_beta": [{"item": "a"}, {"item": "b"}],
        }

        planned = plan_fetch_items(
            sources=sources,
            candidate_payloads=candidate_payloads,
            default_per_source_cap=10,
            global_cap=3,
        )

        self.assertEqual(
            planned,
            [
                {"source_id": "src_alpha", "payload": {"item": 1}},
                {"source_id": "src_alpha", "payload": {"item": 2}},
                {"source_id": "src_beta", "payload": {"item": "a"}},
            ],
        )


if __name__ == "__main__":
    unittest.main()
