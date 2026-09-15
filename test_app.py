import unittest

from streamlit.testing.v1 import AppTest


class StreamlitAppTests(unittest.TestCase):
    def test_page_loads_without_errors(self):
        app = AppTest.from_file("app.py").run(timeout=10)

        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "直播投流 Agent MVP")

    def test_submit_displays_a_complete_decision(self):
        app = AppTest.from_file("app.py").run(timeout=10)
        app.button[0].click().run(timeout=10)

        self.assertFalse(app.exception)
        self.assertTrue(any("原因：" in item.value for item in app.info))
        self.assertTrue(any("风控：" in item.value for item in app.success))
        self.assertGreaterEqual(len(app.metric), 3)


if __name__ == "__main__":
    unittest.main()
