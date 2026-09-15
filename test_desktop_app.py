import unittest

from decision_engine import Action
from desktop_app import DEFAULT_VALUES, create_decision_from_strings, format_money


class DesktopAppLogicTests(unittest.TestCase):
    def test_default_form_generates_increase_decision(self):
        decision = create_decision_from_strings(DEFAULT_VALUES)

        self.assertEqual(decision.action, Action.INCREASE)
        self.assertEqual(decision.suggested_budget, 6000)

    def test_accepts_thousands_separators(self):
        values = dict(DEFAULT_VALUES, current_budget="5,000", max_budget="10,000")
        decision = create_decision_from_strings(values)

        self.assertEqual(decision.suggested_budget, 6000)

    def test_rejects_non_numeric_input_with_field_name(self):
        values = dict(DEFAULT_VALUES, roi="abc")

        with self.assertRaisesRegex(ValueError, "当前 ROI"):
            create_decision_from_strings(values)

    def test_rejects_fractional_viewer_count(self):
        values = dict(DEFAULT_VALUES, online_viewers="1.5")

        with self.assertRaisesRegex(ValueError, "在线人数必须是整数"):
            create_decision_from_strings(values)

    def test_money_format_is_stable(self):
        self.assertEqual(format_money(12345.6), "¥12,345.60")


if __name__ == "__main__":
    unittest.main()
