"""巨量千川 Marketing API 的只读直播数据客户端。

仅调用数据报表接口，不包含创建计划、修改预算等写操作。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_BASE_URL = "https://api.oceanengine.com"
LIVE_REPORT_PATH = "/open_api/v1.0/qianchuan/report/live/get/"

LIVE_REPORT_FIELDS = (
    "stat_cost",
    "live_pay_order_gmv_alias",
    "live_pay_order_gmv_roi",
    "ad_live_prepay_and_pay_order_gmv_roi",
    "total_live_watch_cnt",
    "luban_live_pay_order_count",
    "click_cnt",
    "ctr",
    "convert_cnt",
    "convert_rate",
    "total_live_follow_cnt",
    "total_live_comment",
    "live_click_product_count_alias",
)

Transport = Callable[[str, Mapping[str, str], float], bytes]


class QianchuanApiError(RuntimeError):
    """千川接口返回失败或网络调用失败。"""

    def __init__(self, message: str, *, code: int | str | None = None, request_id: str = "") -> None:
        self.code = code
        self.request_id = request_id
        details = message
        if code not in (None, ""):
            details = f"{details}（错误码：{code}）"
        if request_id:
            details = f"{details}（request_id：{request_id}）"
        super().__init__(details)


@dataclass(frozen=True)
class QianchuanCredentials:
    access_token: str
    advertiser_id: int
    aweme_id: int | None = None

    def validate(self) -> None:
        if not self.access_token.strip():
            raise ValueError("请填写 Access Token")
        if self.advertiser_id <= 0:
            raise ValueError("广告主 ID 必须是正整数")
        if self.aweme_id is not None and self.aweme_id <= 0:
            raise ValueError("抖音号 ID 必须是正整数")


@dataclass(frozen=True)
class LiveSnapshot:
    collected_at: datetime
    stat_cost: float
    total_gmv: float
    overall_roi: float
    ad_roi: float
    watch_count: int
    paid_order_count: int
    click_count: int
    ctr: float
    convert_count: int
    convert_rate: float
    follow_count: int
    comment_count: int
    product_click_count: int
    request_id: str = ""


def _number(data: Mapping[str, Any], key: str) -> float:
    value = data.get(key, 0)
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise QianchuanApiError(f"接口字段 {key} 不是有效数字") from error


def parse_live_snapshot(payload: Mapping[str, Any], *, collected_at: datetime | None = None) -> LiveSnapshot:
    code = payload.get("code", 0)
    request_id = str(payload.get("request_id", "") or "")
    try:
        success = int(code) == 0
    except (TypeError, ValueError):
        success = False
    if not success:
        message = str(payload.get("message") or payload.get("msg") or "千川接口调用失败")
        raise QianchuanApiError(message, code=code, request_id=request_id)

    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise QianchuanApiError("千川接口没有返回有效的直播数据", request_id=request_id)

    return LiveSnapshot(
        collected_at=collected_at or datetime.now(),
        stat_cost=_number(data, "stat_cost"),
        total_gmv=_number(data, "live_pay_order_gmv_alias"),
        overall_roi=_number(data, "live_pay_order_gmv_roi"),
        ad_roi=_number(data, "ad_live_prepay_and_pay_order_gmv_roi"),
        watch_count=int(_number(data, "total_live_watch_cnt")),
        paid_order_count=int(_number(data, "luban_live_pay_order_count")),
        click_count=int(_number(data, "click_cnt")),
        ctr=_number(data, "ctr"),
        convert_count=int(_number(data, "convert_cnt")),
        convert_rate=_number(data, "convert_rate"),
        follow_count=int(_number(data, "total_live_follow_cnt")),
        comment_count=int(_number(data, "total_live_comment")),
        product_click_count=int(_number(data, "live_click_product_count_alias")),
        request_id=request_id,
    )


def _default_transport(url: str, headers: Mapping[str, str], timeout: float) -> bytes:
    request = Request(url=url, headers=dict(headers), method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except HTTPError as error:
        try:
            response_text = error.read().decode("utf-8", errors="replace")
            payload = json.loads(response_text)
            message = str(payload.get("message") or payload.get("msg") or error.reason)
            code = payload.get("code", error.code)
            request_id = str(payload.get("request_id", "") or "")
        except (ValueError, AttributeError):
            message = str(error.reason)
            code = error.code
            request_id = ""
        raise QianchuanApiError(message, code=code, request_id=request_id) from error
    except URLError as error:
        raise QianchuanApiError(f"无法连接巨量千川服务器：{error.reason}") from error
    except TimeoutError as error:
        raise QianchuanApiError("连接巨量千川服务器超时") from error


class QianchuanClient:
    """只读千川客户端；Access Token 只随请求放入请求头。"""

    def __init__(
        self,
        credentials: QianchuanCredentials,
        *,
        transport: Transport | None = None,
        timeout: float = 15.0,
    ) -> None:
        credentials.validate()
        self._credentials = credentials
        self._transport = transport or _default_transport
        self._timeout = timeout

    def fetch_today_live(self, *, now: datetime | None = None) -> LiveSnapshot:
        current_time = now or datetime.now()
        date_text = current_time.strftime("%Y-%m-%d")
        params: dict[str, str | int] = {
            "advertiser_id": self._credentials.advertiser_id,
            "start_time": f"{date_text} 00:00:00",
            "end_time": f"{date_text} 23:59:59",
            "fields": json.dumps(LIVE_REPORT_FIELDS, ensure_ascii=False, separators=(",", ":")),
            "stats_authority": "CURRENT",
        }
        if self._credentials.aweme_id is not None:
            params["aweme_id"] = self._credentials.aweme_id

        url = f"{API_BASE_URL}{LIVE_REPORT_PATH}?{urlencode(params)}"
        headers = {
            "Access-Token": self._credentials.access_token.strip(),
            "Accept": "application/json",
            "User-Agent": "LiveStreamAgent/1.1",
        }
        response_body = self._transport(url, headers, self._timeout)
        try:
            payload = json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise QianchuanApiError("千川接口返回了无法解析的数据") from error
        if not isinstance(payload, Mapping):
            raise QianchuanApiError("千川接口返回格式不正确")
        return parse_live_snapshot(payload, collected_at=current_time)
