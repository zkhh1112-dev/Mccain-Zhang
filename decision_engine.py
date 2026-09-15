"""直播投流 MVP 的决策与风控逻辑。

本模块只计算建议，不连接广告平台，也不会执行任何真实操作。
"""

from dataclasses import dataclass
from enum import Enum

from risk_control import apply_budget_risk_control


class Action(str, Enum):
    INCREASE = "加预算"
    DECREASE = "减预算"
    PAUSE = "暂停"
    HOLD = "保持"


@dataclass(frozen=True)
class LiveData:
    roi: float
    gmv: float
    ad_spend: float
    online_viewers: int
    current_budget: float


@dataclass(frozen=True)
class StrategySettings:
    target_roi: float
    stop_loss_roi: float
    increase_percent: float
    decrease_percent: float
    max_budget: float


@dataclass(frozen=True)
class Decision:
    action: Action
    reason: str
    original_budget: float
    suggested_budget: float
    risk_control_note: str


def _validate(data: LiveData, settings: StrategySettings) -> None:
    numeric_values = {
        "ROI": data.roi,
        "GMV": data.gmv,
        "广告消耗": data.ad_spend,
        "在线人数": data.online_viewers,
        "当前预算": data.current_budget,
        "目标 ROI": settings.target_roi,
        "止损 ROI": settings.stop_loss_roi,
        "加预算比例": settings.increase_percent,
        "减预算比例": settings.decrease_percent,
        "最大预算": settings.max_budget,
    }
    for name, value in numeric_values.items():
        if value < 0:
            raise ValueError(f"{name}不能为负数")

    if settings.stop_loss_roi > settings.target_roi:
        raise ValueError("止损 ROI 不能高于目标 ROI")
    if settings.increase_percent > 100:
        raise ValueError("加预算比例不能超过 100%")
    if settings.decrease_percent > 100:
        raise ValueError("减预算比例不能超过 100%")


def _make_strategy_decision(
    data: LiveData, settings: StrategySettings
) -> tuple[Action, float, str]:
    """生成策略建议。这里不负责最终的预算边界校验。"""
    if data.online_viewers == 0:
        return Action.PAUSE, 0.0, "当前在线人数为 0，暂不继续消耗预算。"

    if data.roi <= settings.stop_loss_roi:
        return (
            Action.PAUSE,
            0.0,
            f"当前 ROI {data.roi:.2f} 已触及止损 ROI {settings.stop_loss_roi:.2f}。",
        )

    if data.current_budget == 0:
        return Action.HOLD, 0.0, "当前预算为 0，百分比调整没有可计算的预算基数。"

    if data.roi >= settings.target_roi:
        new_budget = data.current_budget * (1 + settings.increase_percent / 100)
        return (
            Action.INCREASE,
            new_budget,
            f"当前 ROI {data.roi:.2f} 达到目标 ROI {settings.target_roi:.2f}。",
        )

    observation_midpoint = (settings.target_roi + settings.stop_loss_roi) / 2
    if data.roi < observation_midpoint:
        new_budget = data.current_budget * (1 - settings.decrease_percent / 100)
        return (
            Action.DECREASE,
            new_budget,
            f"当前 ROI {data.roi:.2f} 低于观察区间中点 {observation_midpoint:.2f}，但尚未触及止损线。",
        )

    return (
        Action.HOLD,
        data.current_budget,
        f"当前 ROI {data.roi:.2f} 位于安全观察区间，暂时保持以继续观察。",
    )


def make_decision(data: LiveData, settings: StrategySettings) -> Decision:
    """生成一条经过独立风控的最终建议。"""
    _validate(data, settings)
    action, proposed_budget, reason = _make_strategy_decision(data, settings)
    risk_result = apply_budget_risk_control(
        action=action.value,
        proposed_budget=proposed_budget,
        current_budget=data.current_budget,
        max_budget=settings.max_budget,
    )
    safe_action = Action(risk_result.action)

    if safe_action != action:
        reason = f"{reason} 风控规则调整了最终操作。"

    return Decision(
        action=safe_action,
        reason=reason,
        original_budget=round(data.current_budget, 2),
        suggested_budget=risk_result.safe_budget,
        risk_control_note=risk_result.note,
    )
