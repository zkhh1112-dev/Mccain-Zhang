"""独立预算风控层。

策略建议必须经过本模块后才能展示。真实广告账户连接被明确禁用。
"""

from dataclasses import dataclass


REAL_AD_CONNECTIONS_ALLOWED = False


@dataclass(frozen=True)
class RiskControlResult:
    action: str
    safe_budget: float
    note: str


def apply_budget_risk_control(
    action: str,
    proposed_budget: float,
    current_budget: float,
    max_budget: float,
) -> RiskControlResult:
    """限制预算上下界，并在必要时覆盖策略操作。"""
    safe_budget = max(0.0, min(proposed_budget, max_budget))
    notes: list[str] = []

    if proposed_budget > max_budget:
        notes.append(f"建议预算已限制为最大预算 ¥{max_budget:,.2f}")
    if proposed_budget < 0:
        notes.append("建议预算已限制为 ¥0.00")

    # 即使策略建议保持，当前预算超限时也必须主动降至上限。
    if current_budget > max_budget and action != "暂停":
        safe_budget = max_budget
        action = "减预算"
        notes.append("当前预算超过最大预算，风控已覆盖原策略")

    if action == "加预算" and safe_budget <= current_budget:
        if current_budget > max_budget:
            action = "减预算"
        else:
            action = "保持"
            if current_budget >= max_budget:
                notes.append("已达到最大预算，不能继续增加")
            else:
                notes.append("加预算比例为 0%，建议保持")

    note = "；".join(dict.fromkeys(notes)) if notes else "风控检查通过：预算未超上限且不为负数"
    return RiskControlResult(
        action=action,
        safe_budget=round(safe_budget, 2),
        note=note,
    )
