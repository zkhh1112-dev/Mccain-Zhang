import unittest

from decision_engine import Action, LiveData, StrategySettings, make_decision
from risk_control import REAL_AD_CONNECTIONS_ALLOWED


class DecisionEngineTests(unittest.TestCase):
    def setUp(self):
        self.settings = StrategySettings(
            target_roi=2.0,
            stop_loss_roi=1.0,
            increase_percent=20,
            decrease_percent=25,
            max_budget=10000,
        )

    def data(self, roi=2.0, viewers=100, budget=5000):
        return LiveData(
            roi=roi,
            gmv=10000,
            ad_spend=5000,
            online_viewers=viewers,
            current_budget=budget,
        )

    def test_increases_budget_when_target_is_reached(self):
        decision = make_decision(self.data(roi=2.2), self.settings)
        self.assertEqual(decision.action, Action.INCREASE)
        self.assertEqual(decision.suggested_budget, 6000)

    def test_decreases_budget_in_lower_observation_range(self):
        decision = make_decision(self.data(roi=1.2), self.settings)
        self.assertEqual(decision.action, Action.DECREASE)
        self.assertEqual(decision.suggested_budget, 3750)

    def test_holds_budget_in_upper_observation_range(self):
        decision = make_decision(self.data(roi=1.8), self.settings)
        self.assertEqual(decision.action, Action.HOLD)
        self.assertEqual(decision.suggested_budget, 5000)

    def test_pauses_at_stop_loss(self):
        decision = make_decision(self.data(roi=1.0), self.settings)
        self.assertEqual(decision.action, Action.PAUSE)
        self.assertEqual(decision.suggested_budget, 0)

    def test_pauses_when_no_viewers_are_online(self):
        decision = make_decision(self.data(roi=3.0, viewers=0), self.settings)
        self.assertEqual(decision.action, Action.PAUSE)
        self.assertEqual(decision.suggested_budget, 0)

    def test_risk_control_caps_budget_at_maximum(self):
        decision = make_decision(self.data(roi=3.0, budget=9000), self.settings)
        self.assertEqual(decision.action, Action.INCREASE)
        self.assertEqual(decision.suggested_budget, 10000)
        self.assertIn("最大预算", decision.risk_control_note)

    def test_risk_control_reduces_an_existing_over_limit_budget(self):
        decision = make_decision(self.data(roi=1.8, budget=12000), self.settings)
        self.assertEqual(decision.action, Action.DECREASE)
        self.assertEqual(decision.suggested_budget, 10000)

    def test_risk_control_can_reduce_over_limit_budget_to_zero(self):
        settings = StrategySettings(2.0, 1.0, 20, 20, 0)
        decision = make_decision(self.data(roi=1.8, budget=100), settings)
        self.assertEqual(decision.action, Action.DECREASE)
        self.assertEqual(decision.suggested_budget, 0)

    def test_zero_increase_percent_becomes_hold(self):
        settings = StrategySettings(2.0, 1.0, 0, 20, 10000)
        decision = make_decision(self.data(roi=2.2), settings)
        self.assertEqual(decision.action, Action.HOLD)
        self.assertEqual(decision.suggested_budget, 5000)
        self.assertIn("0%", decision.risk_control_note)

    def test_decrease_can_reach_zero_but_never_negative(self):
        settings = StrategySettings(2.0, 1.0, 20, 100, 10000)
        decision = make_decision(self.data(roi=1.2), settings)
        self.assertEqual(decision.suggested_budget, 0)
        self.assertGreaterEqual(decision.suggested_budget, 0)

    def test_rejects_invalid_stop_loss(self):
        settings = StrategySettings(1.0, 2.0, 20, 20, 10000)
        with self.assertRaisesRegex(ValueError, "止损 ROI"):
            make_decision(self.data(), settings)

    def test_rejects_negative_inputs(self):
        with self.assertRaisesRegex(ValueError, "当前预算"):
            make_decision(self.data(budget=-1), self.settings)

    def test_real_ad_connections_are_disabled(self):
        self.assertFalse(REAL_AD_CONNECTIONS_ALLOWED)


if __name__ == "__main__":
    unittest.main()
