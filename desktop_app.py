"""直播投流决策助手的 Windows 桌面界面。

界面只调用本地决策与风控模块，不连接任何真实广告账户。
"""

from __future__ import annotations

import csv
import math
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Mapping

from decision_engine import Decision, LiveData, StrategySettings, make_decision


APP_NAME = "直播投流决策助手"
APP_VERSION = "1.0.0"

DEFAULT_VALUES = {
    "roi": "2.0",
    "gmv": "10000",
    "ad_spend": "5000",
    "online_viewers": "100",
    "current_budget": "5000",
    "target_roi": "2.0",
    "stop_loss_roi": "1.2",
    "increase_percent": "20",
    "decrease_percent": "20",
    "max_budget": "10000",
}

FIELD_LABELS = {
    "roi": "当前 ROI",
    "gmv": "GMV",
    "ad_spend": "广告消耗",
    "online_viewers": "在线人数",
    "current_budget": "当前预算",
    "target_roi": "目标 ROI",
    "stop_loss_roi": "止损 ROI",
    "increase_percent": "加预算比例",
    "decrease_percent": "减预算比例",
    "max_budget": "最大预算",
}

ACTION_COLORS = {
    "加预算": ("#DCFCE7", "#166534"),
    "减预算": ("#FFEDD5", "#9A3412"),
    "暂停": ("#FEE2E2", "#991B1B"),
    "保持": ("#DBEAFE", "#1E40AF"),
}


def _parse_number(values: Mapping[str, str], key: str) -> float:
    raw_value = str(values.get(key, "")).strip().replace(",", "")
    if not raw_value:
        raise ValueError(f"请填写{FIELD_LABELS[key]}")
    try:
        value = float(raw_value)
    except ValueError as error:
        raise ValueError(f"{FIELD_LABELS[key]}必须是数字") from error
    if not math.isfinite(value):
        raise ValueError(f"{FIELD_LABELS[key]}必须是有限数字")
    return value


def create_decision_from_strings(values: Mapping[str, str]) -> Decision:
    """把桌面表单内容转换为领域对象并生成建议，便于独立测试。"""
    online_viewers = _parse_number(values, "online_viewers")
    if not online_viewers.is_integer():
        raise ValueError("在线人数必须是整数")

    data = LiveData(
        roi=_parse_number(values, "roi"),
        gmv=_parse_number(values, "gmv"),
        ad_spend=_parse_number(values, "ad_spend"),
        online_viewers=int(online_viewers),
        current_budget=_parse_number(values, "current_budget"),
    )
    settings = StrategySettings(
        target_roi=_parse_number(values, "target_roi"),
        stop_loss_roi=_parse_number(values, "stop_loss_roi"),
        increase_percent=_parse_number(values, "increase_percent"),
        decrease_percent=_parse_number(values, "decrease_percent"),
        max_budget=_parse_number(values, "max_budget"),
    )
    return make_decision(data, settings)


def format_money(value: float) -> str:
    return f"¥{value:,.2f}"


class LiveStreamAgentApp:
    """原生 Tk 桌面应用。"""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.values = {key: tk.StringVar(value=value) for key, value in DEFAULT_VALUES.items()}
        self.history: list[dict[str, str]] = []

        self._configure_window()
        self._configure_styles()
        self._build_menu()
        self._build_layout()
        self._bind_shortcuts()

    def _configure_window(self) -> None:
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1180x780")
        self.root.minsize(1000, 700)
        self.root.configure(bg="#F4F7FB")

        width, height = 1180, 780
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")

        self.root.option_add("*Font", ("Microsoft YaHei UI", 10))
        self.title_font = ("Microsoft YaHei UI", 22, "bold")

        style.configure("App.TFrame", background="#F4F7FB")
        style.configure("Card.TFrame", background="#FFFFFF")
        style.configure(
            "Card.TLabelframe",
            background="#FFFFFF",
            bordercolor="#DCE3EC",
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "Card.TLabelframe.Label",
            background="#FFFFFF",
            foreground="#152238",
            font=("Microsoft YaHei UI", 11, "bold"),
        )
        style.configure("Field.TLabel", background="#FFFFFF", foreground="#334155")
        style.configure("Hint.TLabel", background="#FFFFFF", foreground="#64748B")
        style.configure("Result.TLabel", background="#FFFFFF", foreground="#0F172A")
        style.configure(
            "Primary.TButton",
            font=("Microsoft YaHei UI", 10, "bold"),
            padding=(18, 9),
        )
        style.configure("Secondary.TButton", padding=(14, 8))
        style.configure("Treeview", rowheight=30, font=("Microsoft YaHei UI", 9))
        style.configure(
            "Treeview.Heading",
            font=("Microsoft YaHei UI", 9, "bold"),
            foreground="#334155",
        )

    def _build_menu(self) -> None:
        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="导出决策记录…", command=self.export_history, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.destroy, accelerator="Alt+F4")
        menu.add_cascade(label="文件", menu=file_menu)

        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="关于", command=self.show_about)
        menu.add_cascade(label="帮助", menu=help_menu)
        self.root.configure(menu=menu)

    def _build_layout(self) -> None:
        header = tk.Frame(self.root, bg="#13233A", height=112)
        header.pack(fill="x")
        header.pack_propagate(False)

        header_inner = tk.Frame(header, bg="#13233A")
        header_inner.pack(fill="both", expand=True, padx=34, pady=20)
        tk.Label(
            header_inner,
            text=APP_NAME,
            font=self.title_font,
            bg="#13233A",
            fg="#FFFFFF",
        ).pack(anchor="w")
        tk.Label(
            header_inner,
            text="本地模拟决策 · 独立预算风控 · 不连接真实广告账户",
            font=("Microsoft YaHei UI", 10),
            bg="#13233A",
            fg="#B9C7DB",
        ).pack(anchor="w", pady=(5, 0))
        tk.Label(
            header_inner,
            text="安全模式",
            font=("Microsoft YaHei UI", 9, "bold"),
            bg="#D1FAE5",
            fg="#065F46",
            padx=12,
            pady=6,
        ).place(relx=1.0, rely=0.5, anchor="e")

        content = ttk.Frame(self.root, style="App.TFrame", padding=(28, 22, 28, 18))
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(3, weight=1)

        live_frame = ttk.LabelFrame(
            content, text="  当前直播数据  ", style="Card.TLabelframe", padding=16
        )
        strategy_frame = ttk.LabelFrame(
            content, text="  策略与风控设置  ", style="Card.TLabelframe", padding=16
        )
        live_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        strategy_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self._build_form_group(
            live_frame,
            [
                ("roi", "当前 ROI", ""),
                ("gmv", "GMV", "元"),
                ("ad_spend", "广告消耗", "元"),
                ("online_viewers", "在线人数", "人"),
                ("current_budget", "当前预算", "元"),
            ],
        )
        self._build_form_group(
            strategy_frame,
            [
                ("target_roi", "目标 ROI", ""),
                ("stop_loss_roi", "止损 ROI", ""),
                ("increase_percent", "加预算比例", "%"),
                ("decrease_percent", "减预算比例", "%"),
                ("max_budget", "最大预算", "元"),
            ],
        )

        actions = ttk.Frame(content, style="App.TFrame")
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=16)
        ttk.Button(
            actions,
            text="生成决策建议",
            style="Primary.TButton",
            command=self.generate_decision,
        ).pack(side="left")
        ttk.Button(
            actions,
            text="恢复默认值",
            style="Secondary.TButton",
            command=self.reset_form,
        ).pack(side="left", padx=(10, 0))
        ttk.Label(
            actions,
            text="快捷键：Ctrl + Enter",
            background="#F4F7FB",
            foreground="#64748B",
        ).pack(side="right")

        result_frame = ttk.LabelFrame(
            content, text="  决策结果  ", style="Card.TLabelframe", padding=16
        )
        result_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        result_frame.columnconfigure(2, weight=1)

        self.action_badge = tk.Label(
            result_frame,
            text="等待计算",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg="#E2E8F0",
            fg="#475569",
            padx=18,
            pady=10,
        )
        self.action_badge.grid(row=0, column=0, rowspan=2, sticky="nsw", padx=(0, 22))

        self.budget_label = ttk.Label(
            result_frame,
            text="填写数据后生成建议",
            style="Result.TLabel",
            font=("Microsoft YaHei UI", 14, "bold"),
        )
        self.budget_label.grid(row=0, column=1, columnspan=2, sticky="w")
        self.reason_label = ttk.Label(
            result_frame,
            text="所有输出都会先经过独立风控检查。",
            style="Hint.TLabel",
            wraplength=780,
        )
        self.reason_label.grid(row=1, column=1, columnspan=2, sticky="w", pady=(5, 0))
        self.risk_label = ttk.Label(
            result_frame,
            text="风控状态：待检查",
            style="Hint.TLabel",
            wraplength=1000,
        )
        self.risk_label.grid(row=2, column=0, columnspan=3, sticky="w", pady=(13, 0))

        history_frame = ttk.LabelFrame(
            content, text="  本次运行的决策记录  ", style="Card.TLabelframe", padding=(12, 10)
        )
        history_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(16, 0))
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)

        columns = ("time", "action", "original", "suggested", "reason", "risk")
        self.history_table = ttk.Treeview(
            history_frame,
            columns=columns,
            show="headings",
            height=6,
            selectmode="browse",
        )
        headings = {
            "time": "时间",
            "action": "操作",
            "original": "原预算",
            "suggested": "建议预算",
            "reason": "原因",
            "risk": "风控结果",
        }
        widths = {
            "time": 140,
            "action": 74,
            "original": 94,
            "suggested": 94,
            "reason": 330,
            "risk": 300,
        }
        for column in columns:
            self.history_table.heading(column, text=headings[column])
            self.history_table.column(
                column,
                width=widths[column],
                minwidth=60,
                stretch=column in {"reason", "risk"},
                anchor="w" if column in {"reason", "risk"} else "center",
            )

        scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.history_table.yview)
        self.history_table.configure(yscrollcommand=scrollbar.set)
        self.history_table.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        footer = ttk.Frame(history_frame, style="Card.TFrame")
        footer.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(9, 0))
        self.history_count = ttk.Label(footer, text="暂无记录", style="Hint.TLabel")
        self.history_count.pack(side="left")
        ttk.Button(footer, text="清空记录", command=self.clear_history).pack(side="right")
        ttk.Button(footer, text="导出 CSV", command=self.export_history).pack(side="right", padx=(0, 8))

    def _build_form_group(
        self,
        parent: ttk.LabelFrame,
        fields: list[tuple[str, str, str]],
    ) -> None:
        parent.columnconfigure(1, weight=1)
        for row, (key, label, unit) in enumerate(fields):
            ttk.Label(parent, text=label, style="Field.TLabel").grid(
                row=row, column=0, sticky="w", pady=5, padx=(0, 12)
            )
            entry = ttk.Entry(parent, textvariable=self.values[key], justify="right")
            entry.grid(row=row, column=1, sticky="ew", pady=5)
            ttk.Label(parent, text=unit, style="Hint.TLabel", width=3).grid(
                row=row, column=2, sticky="w", pady=5, padx=(8, 0)
            )

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-Return>", lambda _event: self.generate_decision())
        self.root.bind("<Control-s>", lambda _event: self.export_history())

    def generate_decision(self) -> None:
        try:
            decision = create_decision_from_strings(
                {key: value.get() for key, value in self.values.items()}
            )
        except ValueError as error:
            messagebox.showerror("输入有误", str(error), parent=self.root)
            return

        background, foreground = ACTION_COLORS[decision.action.value]
        self.action_badge.configure(
            text=decision.action.value,
            bg=background,
            fg=foreground,
        )
        self.budget_label.configure(
            text=f"{format_money(decision.original_budget)}  →  {format_money(decision.suggested_budget)}"
        )
        self.reason_label.configure(text=decision.reason)
        self.risk_label.configure(text=f"风控状态：{decision.risk_control_note}")

        record = {
            "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "操作": decision.action.value,
            "原预算": format_money(decision.original_budget),
            "建议预算": format_money(decision.suggested_budget),
            "原因": decision.reason,
            "风控结果": decision.risk_control_note,
        }
        self.history.insert(0, record)
        self.history_table.insert(
            "",
            0,
            values=(
                record["时间"],
                record["操作"],
                record["原预算"],
                record["建议预算"],
                record["原因"],
                record["风控结果"],
            ),
        )
        self.history_count.configure(text=f"共 {len(self.history)} 条记录")

    def reset_form(self) -> None:
        for key, default_value in DEFAULT_VALUES.items():
            self.values[key].set(default_value)

    def clear_history(self) -> None:
        if not self.history:
            return
        if not messagebox.askyesno("清空记录", "确定清空本次运行的全部决策记录吗？", parent=self.root):
            return
        self.history.clear()
        for item in self.history_table.get_children():
            self.history_table.delete(item)
        self.history_count.configure(text="暂无记录")

    def export_history(self) -> None:
        if not self.history:
            messagebox.showinfo("暂无记录", "生成至少一条决策后才能导出。", parent=self.root)
            return
        filename = f"直播投流决策记录_{datetime.now():%Y%m%d_%H%M%S}.csv"
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="导出决策记录",
            initialfile=filename,
            defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")],
        )
        if not path:
            return
        try:
            with Path(path).open("w", newline="", encoding="utf-8-sig") as csv_file:
                writer = csv.DictWriter(
                    csv_file,
                    fieldnames=["时间", "操作", "原预算", "建议预算", "原因", "风控结果"],
                )
                writer.writeheader()
                writer.writerows(self.history)
        except OSError as error:
            messagebox.showerror("导出失败", f"无法保存文件：{error}", parent=self.root)
            return
        messagebox.showinfo("导出完成", f"决策记录已保存到：\n{path}", parent=self.root)

    def show_about(self) -> None:
        messagebox.showinfo(
            "关于",
            f"{APP_NAME} v{APP_VERSION}\n\n"
            "本软件仅生成本地模拟建议，不连接广告平台，"
            "不会执行真实预算操作。",
            parent=self.root,
        )


def _enable_windows_dpi_awareness() -> None:
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass


def main() -> None:
    _enable_windows_dpi_awareness()
    root = tk.Tk()
    LiveStreamAgentApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
