import json
import unittest
from datetime import datetime
from urllib.parse import parse_qs, urlparse

from qianchuan_client import (
    LIVE_REPORT_FIELDS,
    QianchuanApiError,
    QianchuanClient,
    QianchuanCredentials,
    parse_live_snapshot,
)


class QianchuanClientTests(unittest.TestCase):
    def test_builds_read_only_live_report_request(self):
        captured = {}

        def transport(url, headers, timeout):
            captured.update(url=url, headers=headers, timeout=timeout)
            return json.dumps(
                {
                    "code": 0,
                    "request_id": "request-123",
                    "data": {
                        "stat_cost": "125.50",
                        "live_pay_order_gmv_alias": 300,
                        "live_pay_order_gmv_roi": 2.39,
                        "ad_live_prepay_and_pay_order_gmv_roi": 2.1,
                        "total_live_watch_cnt": 1234,
                        "luban_live_pay_order_count": 20,
                    },
                }
            ).encode()

        client = QianchuanClient(
            QianchuanCredentials("secret-token", 123456, 987654),
            transport=transport,
        )
        snapshot = client.fetch_today_live(now=datetime(2026, 9, 3, 10, 30, 0))

        parsed = urlparse(captured["url"])
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.path, "/open_api/v1.0/qianchuan/report/live/get/")
        self.assertEqual(query["advertiser_id"], ["123456"])
        self.assertEqual(query["aweme_id"], ["987654"])
        self.assertEqual(query["start_time"], ["2026-09-03 00:00:00"])
        self.assertEqual(query["end_time"], ["2026-09-03 23:59:59"])
        self.assertEqual(tuple(json.loads(query["fields"][0])), LIVE_REPORT_FIELDS)
        self.assertEqual(captured["headers"]["Access-Token"], "secret-token")
        self.assertNotIn("secret-token", captured["url"])
        self.assertEqual(snapshot.stat_cost, 125.5)
        self.assertEqual(snapshot.total_gmv, 300)
        self.assertEqual(snapshot.watch_count, 1234)
        self.assertEqual(snapshot.request_id, "request-123")

    def test_parses_missing_metrics_as_zero(self):
        snapshot = parse_live_snapshot({"code": 0, "data": {}})

        self.assertEqual(snapshot.stat_cost, 0)
        self.assertEqual(snapshot.overall_roi, 0)
        self.assertEqual(snapshot.paid_order_count, 0)

    def test_surfaces_api_error_code_and_request_id(self):
        with self.assertRaisesRegex(QianchuanApiError, "40100"):
            parse_live_snapshot(
                {
                    "code": 40100,
                    "message": "Access Token 无效",
                    "request_id": "failed-request",
                }
            )

    def test_rejects_invalid_credentials_before_request(self):
        with self.assertRaisesRegex(ValueError, "Access Token"):
            QianchuanClient(QianchuanCredentials("", 123))

        with self.assertRaisesRegex(ValueError, "广告主 ID"):
            QianchuanClient(QianchuanCredentials("token", 0))

    def test_rejects_non_json_response(self):
        client = QianchuanClient(
            QianchuanCredentials("token", 123),
            transport=lambda _url, _headers, _timeout: b"not-json",
        )

        with self.assertRaisesRegex(QianchuanApiError, "无法解析"):
            client.fetch_today_live()


if __name__ == "__main__":
    unittest.main()
