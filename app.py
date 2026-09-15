"""直播投流 Agent MVP 的 Streamlit 界面。"""

from datetime import datetime

import streamlit as st

from decision_engine import LiveData, StrategySettings, make_decision


st.set_page_config(page_title="直播投流 Agent MVP", page_icon="📊", layout="wide")

st.title("直播投流 Agent MVP")
st.caption("只提供模拟决策，不连接任何真实广告账户，也不会操作真实资金。")
st.warning("安全模式已开启：所有建议都必须经过独立风控检查。")

with st.form("decision_form"):
    st.subheader("当前直播数据")
    data_col1, data_col2, data_col3 = st.columns(3)
    with data_col1:
        roi = st.number_input("ROI", min_value=0.0, value=2.0, step=0.1)
        gmv = st.number_input("GMV（元）", min_value=0.0, value=10000.0, step=100.0)
    with data_col2:
        ad_spend = st.number_input("广告消耗（元）", min_value=0.0, value=5000.0, step=100.0)
        online_viewers = st.number_input("在线人数", min_value=0, value=100, step=1)
    with data_col3:
        current_budget = st.number_input("当前预算（元）", min_value=0.0, value=5000.0, step=100.0)

    st.subheader("策略设置")
    setting_col1, setting_col2, setting_col3 = st.columns(3)
    with setting_col1:
        target_roi = st.number_input("目标 ROI", min_value=0.0, value=2.0, step=0.1)
        stop_loss_roi = st.number_input("止损 ROI", min_value=0.0, value=1.2, step=0.1)
    with setting_col2:
        increase_percent = st.number_input("加预算比例（%）", min_value=0.0, max_value=100.0, value=20.0, step=1.0)
        decrease_percent = st.number_input("减预算比例（%）", min_value=0.0, max_value=100.0, value=20.0, step=1.0)
    with setting_col3:
        max_budget = st.number_input("最大预算（元）", min_value=0.0, value=10000.0, step=100.0)

    submitted = st.form_submit_button("生成决策建议", type="primary", width="stretch")


if submitted:
    try:
        decision = make_decision(
            LiveData(
                roi=roi,
                gmv=gmv,
                ad_spend=ad_spend,
                online_viewers=int(online_viewers),
                current_budget=current_budget,
            ),
            StrategySettings(
                target_roi=target_roi,
                stop_loss_roi=stop_loss_roi,
                increase_percent=increase_percent,
                decrease_percent=decrease_percent,
                max_budget=max_budget,
            ),
        )

        result = {
            "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "操作": decision.action.value,
            "原因": decision.reason,
            "原预算": f"¥{decision.original_budget:,.2f}",
            "建议预算": f"¥{decision.suggested_budget:,.2f}",
            "风控结果": decision.risk_control_note,
        }
        st.session_state.setdefault("decision_history", []).insert(0, result)

        st.divider()
        st.subheader("本次决策")
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric("操作", result["操作"])
        metric_col2.metric("原预算", result["原预算"])
        metric_col3.metric("建议预算", result["建议预算"])
        st.info(f"原因：{result['原因']}")
        st.success(f"风控：{result['风控结果']}")
    except ValueError as error:
        st.error(str(error))


if st.session_state.get("decision_history"):
    st.divider()
    st.subheader("本次会话的决策记录")
    st.caption("记录只保存在当前浏览器会话中，刷新或重启后可能清空。")
    st.dataframe(st.session_state["decision_history"], width="stretch", hide_index=True)
