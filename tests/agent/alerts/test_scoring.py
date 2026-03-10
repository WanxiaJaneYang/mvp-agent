import unittest

from apps.agent.alerts.policy_gate import (
    AlertCandidate,
    AlertEvidenceSummary,
    AlertPolicyContext,
    evaluate_alert_policy,
)
from apps.agent.alerts.scoring import AlertScoreInputs, compute_alert_score


class AlertScoringTests(unittest.TestCase):
    def test_compute_alert_score_uses_modelled_weights(self):
        result = compute_alert_score(
            category="policy",
            inputs=AlertScoreInputs(
                importance=80,
                evidence_strength=70,
                confidence=60,
                portfolio_relevance=20,
                noise_risk=10,
            ),
        )

        self.assertEqual(result.total_score, 55.5)
        self.assertEqual(result.decision_band, "bundle")
        self.assertEqual(result.category_floor_met, True)

    def test_compute_alert_score_enforces_policy_floor(self):
        result = compute_alert_score(
            category="policy",
            inputs=AlertScoreInputs(
                importance=55,
                evidence_strength=95,
                confidence=90,
                portfolio_relevance=40,
                noise_risk=5,
            ),
        )

        self.assertEqual(result.total_score, 63.75)
        self.assertFalse(result.category_floor_met)
        self.assertEqual(result.decision_band, "suppress")

    def test_compute_alert_score_enforces_corporate_relevance_floor(self):
        result = compute_alert_score(
            category="corporate_event",
            inputs=AlertScoreInputs(
                importance=70,
                evidence_strength=80,
                confidence=75,
                portfolio_relevance=20,
                noise_risk=5,
            ),
        )

        self.assertFalse(result.category_floor_met)
        self.assertEqual(result.decision_band, "suppress")

    def test_compute_alert_score_clamps_total_within_bounds(self):
        result = compute_alert_score(
            category="macro_release",
            inputs=AlertScoreInputs(
                importance=120,
                evidence_strength=120,
                confidence=120,
                portfolio_relevance=120,
                noise_risk=-10,
            ),
        )

        self.assertEqual(result.total_score, 90.0)


class AlertPolicyGateTests(unittest.TestCase):
    def test_policy_gate_sends_immediate_alert_when_threshold_and_quality_pass(self):
        decision = evaluate_alert_policy(
            candidate=AlertCandidate(
                category="macro_release",
                triggered_at="2026-03-10T08:00:00Z",
                score_inputs=AlertScoreInputs(
                    importance=90,
                    evidence_strength=90,
                    confidence=85,
                    portfolio_relevance=60,
                    noise_risk=5,
                ),
                evidence=AlertEvidenceSummary(
                    source_ids=("fed_press_releases", "reuters_business"),
                    credibility_tiers=(1, 2),
                    citation_count=3,
                    max_publisher_pct=35.0,
                    tier_1_2_pct=100.0,
                    tier_4_pct=0.0,
                    paywall_safe=True,
                ),
            ),
            context=AlertPolicyContext(
                daily_alerts_sent=1,
                last_alert_sent_at="2026-03-10T05:00:00Z",
                budget_allowed=True,
            ),
        )

        self.assertEqual(decision.action, "send")
        self.assertIsNone(decision.suppression_reason)
        self.assertFalse(decision.bundle_for_daily_brief)
        self.assertGreaterEqual(decision.score.total_score, 70.0)

    def test_policy_gate_bundles_midrange_score(self):
        decision = evaluate_alert_policy(
            candidate=AlertCandidate(
                category="narrative_shift",
                triggered_at="2026-03-10T08:00:00Z",
                score_inputs=AlertScoreInputs(
                    importance=70,
                    evidence_strength=70,
                    confidence=65,
                    portfolio_relevance=40,
                    noise_risk=5,
                ),
                evidence=AlertEvidenceSummary(
                    source_ids=("reuters_business", "wsj_markets"),
                    credibility_tiers=(2, 2),
                    citation_count=2,
                    max_publisher_pct=40.0,
                    tier_1_2_pct=100.0,
                    tier_4_pct=0.0,
                    paywall_safe=True,
                ),
            ),
            context=AlertPolicyContext(
                daily_alerts_sent=0,
                last_alert_sent_at=None,
                budget_allowed=True,
            ),
        )

        self.assertEqual(decision.action, "bundle")
        self.assertIsNone(decision.suppression_reason)
        self.assertTrue(decision.bundle_for_daily_brief)

    def test_policy_gate_rejects_quality_gate_failures(self):
        decision = evaluate_alert_policy(
            candidate=AlertCandidate(
                category="policy",
                triggered_at="2026-03-10T08:00:00Z",
                score_inputs=AlertScoreInputs(
                    importance=85,
                    evidence_strength=90,
                    confidence=85,
                    portfolio_relevance=20,
                    noise_risk=5,
                ),
                evidence=AlertEvidenceSummary(
                    source_ids=("reuters_business",),
                    credibility_tiers=(2,),
                    citation_count=1,
                    max_publisher_pct=100.0,
                    tier_1_2_pct=100.0,
                    tier_4_pct=0.0,
                    paywall_safe=True,
                ),
            ),
            context=AlertPolicyContext(
                daily_alerts_sent=0,
                last_alert_sent_at=None,
                budget_allowed=True,
            ),
        )

        self.assertEqual(decision.action, "suppress")
        self.assertEqual(decision.suppression_reason, "failed_quality_gate")

    def test_policy_gate_rejects_when_cooldown_is_active(self):
        decision = evaluate_alert_policy(
            candidate=AlertCandidate(
                category="policy",
                triggered_at="2026-03-10T08:30:00Z",
                score_inputs=AlertScoreInputs(
                    importance=90,
                    evidence_strength=90,
                    confidence=85,
                    portfolio_relevance=60,
                    noise_risk=5,
                ),
                evidence=AlertEvidenceSummary(
                    source_ids=("fed_press_releases", "reuters_business"),
                    credibility_tiers=(1, 2),
                    citation_count=2,
                    max_publisher_pct=40.0,
                    tier_1_2_pct=100.0,
                    tier_4_pct=0.0,
                    paywall_safe=True,
                ),
            ),
            context=AlertPolicyContext(
                daily_alerts_sent=1,
                last_alert_sent_at="2026-03-10T08:00:00Z",
                budget_allowed=True,
            ),
        )

        self.assertEqual(decision.action, "suppress")
        self.assertEqual(decision.suppression_reason, "cooldown_active")
        self.assertTrue(decision.bundle_for_daily_brief)

    def test_policy_gate_rejects_when_daily_cap_is_reached(self):
        decision = evaluate_alert_policy(
            candidate=AlertCandidate(
                category="macro_release",
                triggered_at="2026-03-10T14:00:00Z",
                score_inputs=AlertScoreInputs(
                    importance=90,
                    evidence_strength=90,
                    confidence=85,
                    portfolio_relevance=60,
                    noise_risk=5,
                ),
                evidence=AlertEvidenceSummary(
                    source_ids=("us_bls_news", "reuters_business"),
                    credibility_tiers=(1, 2),
                    citation_count=2,
                    max_publisher_pct=40.0,
                    tier_1_2_pct=100.0,
                    tier_4_pct=0.0,
                    paywall_safe=True,
                ),
            ),
            context=AlertPolicyContext(
                daily_alerts_sent=3,
                last_alert_sent_at="2026-03-10T10:00:00Z",
                budget_allowed=True,
            ),
        )

        self.assertEqual(decision.action, "suppress")
        self.assertEqual(decision.suppression_reason, "daily_cap_reached")
        self.assertTrue(decision.bundle_for_daily_brief)

    def test_policy_gate_rejects_when_budget_has_stopped_runtime(self):
        decision = evaluate_alert_policy(
            candidate=AlertCandidate(
                category="policy",
                triggered_at="2026-03-10T14:00:00Z",
                score_inputs=AlertScoreInputs(
                    importance=90,
                    evidence_strength=90,
                    confidence=85,
                    portfolio_relevance=25,
                    noise_risk=5,
                ),
                evidence=AlertEvidenceSummary(
                    source_ids=("fed_press_releases", "reuters_business"),
                    credibility_tiers=(1, 2),
                    citation_count=2,
                    max_publisher_pct=40.0,
                    tier_1_2_pct=100.0,
                    tier_4_pct=0.0,
                    paywall_safe=True,
                ),
            ),
            context=AlertPolicyContext(
                daily_alerts_sent=0,
                last_alert_sent_at=None,
                budget_allowed=False,
            ),
        )

        self.assertEqual(decision.action, "suppress")
        self.assertEqual(decision.suppression_reason, "budget_stopped")


if __name__ == "__main__":
    unittest.main()
