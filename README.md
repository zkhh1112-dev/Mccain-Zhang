# 直播投流 Agent MVP

这是一个完全本地、只做模拟建议的最小版本。它不会连接真实广告账户，也不会执行真实预算操作。

## 已实现

- 输入 ROI、GMV、广告消耗、在线人数和当前预算
- 设置目标 ROI、止损 ROI、加/减预算比例和最大预算
- 输出加预算、减预算、暂停或保持
- 展示原因、原预算、建议预算和独立风控结果
- 独立的 `risk_control.py` 保证建议预算不超过最大预算且不小于 0
- 代码中明确禁止真实广告账户连接
- 当前会话内显示决策记录，不使用数据库

## 决策规则

1. 在线人数为 0：暂停。
2. ROI 触及或低于止损 ROI：暂停。
3. ROI 达到或高于目标 ROI：按比例加预算。
4. ROI 位于止损线与目标线的下半区：按比例减预算。
5. ROI 位于止损线与目标线的上半区：保持预算。
6. 所有结果最后都经过独立风控；超出最大预算会被截断，负预算会被截断为 0。

## 启动方法（Windows）

首次运行，在本目录打开终端，依次执行：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1
```

以后再次运行，只需进入本目录并执行：

```powershell
.venv\Scripts\Activate.ps1
python -m streamlit run app.py --server.address 127.0.0.1
```

也可以直接双击 `start.bat`。

## 运行测试

```powershell
python -m unittest -v
```
