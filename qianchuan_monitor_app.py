"""巨量千川直播数据只读监测桌面软件。"""

from __future__ import annotations

import csv
import random
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from qianchuan_client import (
    LiveSnapshot,
    QianchuanApiError,
    QianchuanClient,
    QianchuanCredentials,
)


APP_NAME = "巨量千川直播监测"
APP_VERSION = "1.0.0"


def format_money(value: float) -> str:
    return f"¥{value:,.2f}"


def format_percent(value: float) -> str:
    return f"{value:.2f}%"


class MetricCard(tk.Frame):
    def __init__(self, parent: tk.Misc, title: str, initial: str = "--") -> None:
        super().__init__(
            parent,
            bg="#FFFFFF",
            highlightbackground="#DCE3EC",
            highlightthickness=1,
            padx=16,
            pady=12,
        )
        self.columnconfigure(0, weight=1)
        tk.Label(
            self,
            text=title,
            bg="#FFFFFF",
            fg="#64748B",
            font=("Microsoft YaHei UI", 9),
        ).grid(row=0, column=0, sticky="w")
        self.value_label = tk.Label(
            self,
            text=initial,
            bg="#FFFFFF",
            fg="#0F172A",
            font=("Microsoft YaHei UI", 17, "bold"),
        )
        self.value_label.grid(row=1, column=0, sticky="w", pady=(7, 0))

    def set_value(self, value: str) -> None:
        self.value_label.configure(text=value)


class QianchuanMonitorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.demo_mode = tk.BooleanVar(value=True)
        self.access_token = tk.StringVar()
        self.advertiser_id = tk.StringVar()
        self.aweme_id = tk.StringVar()
        self.interval_seconds = tk.StringVar(value="60")
        self.target_roi = tk.StringVar(value="2.0")
        self.stop_loss_roi = tk.StringVar(value="1.2")

        self.monitoring = False
        self.request_in_progress = False
        self.after_id: str | None = None
        self.history: list[LiveSnapshot] = []
        self.demo_values = {
            "cost": 1080.0,
            "gmv": 2280.0,
            "views": 12600,
            "orders": 68,
            "clicks": 1180,
            "converts": 92,
            "follows": 310,
            "comments": 680,
            "product_clicks": 1850,
        }

        self._configure_window()
        self._configure_styles()
        self._build_menu()
        self._build_layout()
        self._set_connection_fields_state()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _configure_window(self) -> None:
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1220x790")
        self.root.minsize(1050, 720)
        self.root.configure(bg="#F4F7FB")
        width, height = 1220, 790
        x = max((self.root.winfo_screenwidth() - width) // 2, 0)
        y = max((self.root.winfo_screenheight() - height) // 2, 0)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        self.root.option_add("*Font", ("Microsoft YaHei UI", 10))
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
        style.configure("Card.TLabel", background="#FFFFFF", foreground="#334155")
        style.configure("Hint.TLabel", background="#FFFFFF", foreground="#64748B")
        style.configure("Treeview", rowheight=29, font=("Microsoft YaHei UI", 9))
        style.configure("Treeview.Heading", font=("Microsoft YaHei UI", 9, "bold"))
        style.configure("Primary.TButton", padding=(16, 8), font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("Secondary.TButton", padding=(12, 7))

    def _build_menu(self) -> None:
        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="导出监测记录…", command=self.export_history, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.close)
        menu.add_cascade(label="文件", menu=file_menu)
        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="关于", command=self.show_about)
        menu.add_cascade(label="帮助", menu=help_menu)
        self.root.configure(menu=menu)
        self.root.bind("<Control-s>", lambda _event: self.export_history())
        self.root.bind("<F5>", lambda _event: self.refresh_now())

    def _build_layout(self) -> None:
        header = tk.Frame(self.root, bg="#13233A", height=100)
        header.pack(fill="x")
        header.pack_propagate(False)
        header_inner = tk.Frame(header, bg="#13233A")
        header_inner.pack(fill="both", expand=True, padx=30, pady=17)
        tk.Label(
            header_inner,
            text=APP_NAME,
            bg="#13233A",
            fg="#FFFFFF",
            font=("Microsoft YaHei UI", 21, "bold"),
        ).pack(anchor="w")
        tk.Label(
            header_inner,
            text="官方 Marketing API · 只读数据监测 · 不执行预算操作",
            bg="#13233A",
            fg="#B9C7DB",
            font=("Microsoft YaHei UI", 10),
        ).pack(anchor="w", pady=(4, 0))
        self.header_status = tk.Label(
            header_inner,
            text="● 演示模式",
            bg="#13233A",
            fg="#7DD3FC",
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        self.header_status.place(relx=1, rely=0.5, anchor="e")

        content = ttk.Frame(self.root, style="App.TFrame", padding=(24, 18, 24, 16))
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(4, weight=1)

        self._build_connection_panel(content)
        self._build_metric_cards(content)
        self._build_alert_panel(content)
        self._build_history_panel(content)

    def _build_connection_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.LabelFrame(
            parent, text="  数据连接  ", style="Card.TLabelframe", padding=(14, 11)
        )
        panel.grid(row=0, column=0, sticky="ew")
        panel.columnconfigure(2, weight=1)
        panel.columnconfigure(4, weight=1)

        ttk.Checkbutton(
            panel,
            text="演示模式",
            variable=self.demo_mode,
            command=self._set_connection_fields_state,
        ).grid(row=0, column=0, sticky="w", padx=(0, 18))

        ttk.Label(panel, text="Access Token", style="Card.TLabel").grid(row=0, column=1, sticky="e")
        self.token_entry = ttk.Entry(panel, textvariable=self.access_token, show="●")
        self.token_entry.grid(row=0, column=2, sticky="ew", padx=(8, 16))

        ttk.Label(panel, text="广告主 ID", style="Card.TLabel").grid(row=0, column=3, sticky="e")
        self.advertiser_entry = ttk.Entry(panel, textvariable=self.advertiser_id, width=18)
        self.advertiser_entry.grid(row=0, column=4, sticky="ew", padx=(8, 16))

        ttk.Label(panel, text="抖音号 ID", style="Card.TLabel").grid(row=0, column=5, sticky="e")
        self.aweme_entry = ttk.Entry(panel, textvariable=self.aweme_id, width=18)
        self.aweme_entry.grid(row=0, column=6, sticky="ew", padx=(8, 0))

        ttk.Label(panel, text="刷新间隔", style="Card.TLabel").grid(row=1, column=1, sticky="e", pady=(10, 0))
        self.interval_box = ttk.Combobox(
            panel,
            textvariable=self.interval_seconds,
            values=("30", "60", "120", "300"),
            state="readonly",
            width=10,
        )
        self.interval_box.grid(row=1, column=2, sticky="w", padx=(8, 16), pady=(10, 0))
        ttk.Label(panel, text="秒", style="Hint.TLabel").grid(row=1, column=2, sticky="w", padx=(82, 0), pady=(10, 0))

        ttk.Label(panel, text="目标 ROI", style="Card.TLabel").grid(row=1, column=3, sticky="e", pady=(10, 0))
        ttk.Entry(panel, textvariable=self.target_roi, width=10).grid(
            row=1, column=4, sticky="w", padx=(8, 16), pady=(10, 0)
        )
        ttk.Label(panel, text="止损 ROI", style="Card.TLabel").grid(row=1, column=5, sticky="e", pady=(10, 0))
        ttk.Entry(panel, textvariable=self.stop_loss_roi, width=10).grid(
            row=1, column=6, sticky="w", padx=(8, 0), pady=(10, 0)
        )

        button_row = ttk.Frame(panel, style="Card.TFrame")
        button_row.grid(row=2, column=0, columnspan=7, sticky="ew", pady=(12, 0))
        self.refresh_button = ttk.Button(
            button_row, text="立即刷新  F5", style="Secondary.TButton", command=self.refresh_now
        )
        self.refresh_button.pack(side="left")
        self.start_button = ttk.Button(
            button_row, text="开始监测", style="Primary.TButton", command=self.start_monitoring
        )
        self.start_button.pack(side="left", padx=(8, 0))
        self.stop_button = ttk.Button(
            button_row, text="停止", style="Secondary.TButton", command=self.stop_monitoring, state="disabled"
        )
        self.stop_button.pack(side="left", padx=(8, 0))
        self.connection_status = ttk.Label(
            button_row,
            text="演示模式可直接运行；真实模式需要官方数据报表权限。",
            style="Hint.TLabel",
        )
        self.connection_status.pack(side="right")

    def _build_metric_cards(self, parent: ttk.Frame) -> None:
        metrics = ttk.Frame(parent, style="App.TFrame")
        metrics.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        for column in range(6):
            metrics.columnconfigure(column, weight=1, uniform="metric")

        definitions = (
            ("cost", "今日广告消耗"),
            ("gmv", "累计成交金额"),
            ("roi", "整体 ROI"),
            ("ad_roi", "广告 ROI"),
            ("views", "观看人次"),
            ("orders", "广告成单数"),
        )
        self.metric_cards: dict[str, MetricCard] = {}
        for column, (key, title) in enumerate(definitions):
            card = MetricCard(metrics, title)
            card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 5, 0 if column == 5 else 5))
            self.metric_cards[key] = card

    def _build_alert_panel(self, parent: ttk.Frame) -> None:
        self.alert_frame = tk.Frame(
            parent,
            bg="#E2E8F0",
            highlightbackground="#CBD5E1",
            highlightthickness=1,
            padx=16,
            pady=11,
        )
        self.alert_frame.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        self.alert_label = tk.Label(
            self.alert_frame,
            text="等待第一条监测数据",
            bg="#E2E8F0",
            fg="#475569",
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        self.alert_label.pack(side="left")
        self.detail_label = tk.Label(
            self.alert_frame,
            text="软件只做监测与提示，不会自动修改千川账户。",
            bg="#E2E8F0",
            fg="#64748B",
            font=("Microsoft YaHei UI", 9),
        )
        self.detail_label.pack(side="right")

    def _build_history_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.LabelFrame(
            parent, text="  实时监测记录  ", style="Card.TLabelframe", padding=(12, 10)
        )
        panel.grid(row=4, column=0, sticky="nsew", pady=(14, 0))
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(0, weight=1)

        columns = ("time", "cost", "gmv", "roi", "ad_roi", "views", "orders", "ctr", "convert")
        self.table = ttk.Treeview(panel, columns=columns, show="headings", height=9)
        settings = {
            "time": ("采集时间", 150),
            "cost": ("广告消耗", 110),
            "gmv": ("成交金额", 110),
            "roi": ("整体 ROI", 90),
            "ad_roi": ("广告 ROI", 90),
            "views": ("观看人次", 100),
            "orders": ("成单数", 80),
            "ctr": ("点击率", 85),
            "convert": ("转化数", 80),
        }
        for name, (title, width) in settings.items():
            self.table.heading(name, text=title)
            self.table.column(name, width=width, minwidth=65, anchor="center", stretch=True)
        scrollbar = ttk.Scrollbar(panel, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        footer = ttk.Frame(panel, style="Card.TFrame")
        footer.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(9, 0))
        self.count_label = ttk.Label(footer, text="暂无记录", style="Hint.TLabel")
        self.count_label.pack(side="left")
        ttk.Button(footer, text="清空记录", command=self.clear_history).pack(side="right")
        ttk.Button(footer, text="导出 CSV", command=self.export_history).pack(side="right", padx=(0, 8))

    def _set_connection_fields_state(self) -> None:
        state = "disabled" if self.demo_mode.get() else "normal"
        self.token_entry.configure(state=state)
        self.advertiser_entry.configure(state=state)
        self.aweme_entry.configure(state=state)
        if self.demo_mode.get():
            self.header_status.configure(text="● 演示模式", fg="#7DD3FC")
            self.connection_status.configure(text="演示模式可直接运行；切换后可连接官方 API。")
        else:
            self.header_status.configure(text="● 尚未连接", fg="#FBBF24")
            self.connection_status.configure(text="Token 仅保存在本次软件运行的内存中。")

    def _read_thresholds(self) -> tuple[float, float]:
        try:
            target = float(self.target_roi.get().strip())
            stop_loss = float(self.stop_loss_roi.get().strip())
        except ValueError as error:
            raise ValueError("目标 ROI 和止损 ROI 必须是数字") from error
        if target < 0 or stop_loss < 0:
            raise ValueError("ROI 阈值不能为负数")
        if stop_loss > target:
            raise ValueError("止损 ROI 不能高于目标 ROI")
        return target, stop_loss

    def _read_interval(self) -> int:
        try:
            interval = int(self.interval_seconds.get())
        except ValueError as error:
            raise ValueError("刷新间隔必须是整数") from error
        if interval < 30:
            raise ValueError("为保护接口频控，刷新间隔不能少于 30 秒")
        return interval

    def _build_client(self) -> QianchuanClient:
        token = self.access_token.get().strip()
        advertiser_text = self.advertiser_id.get().strip()
        aweme_text = self.aweme_id.get().strip()
        try:
            advertiser_id = int(advertiser_text)
            aweme_id = int(aweme_text) if aweme_text else None
        except ValueError as error:
            raise ValueError("广告主 ID 和抖音号 ID 必须是整数") from error
        return QianchuanClient(
            QianchuanCredentials(
                access_token=token,
                advertiser_id=advertiser_id,
                aweme_id=aweme_id,
            )
        )

    def start_monitoring(self) -> None:
        try:
            self._read_interval()
            self._read_thresholds()
            if not self.demo_mode.get():
                self._build_client()
        except ValueError as error:
            messagebox.showerror("配置有误", str(error), parent=self.root)
            return
        self.monitoring = True
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.refresh_now()

    def stop_monitoring(self) -> None:
        self.monitoring = False
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.connection_status.configure(text="监测已停止。")

    def refresh_now(self) -> None:
        if self.request_in_progress:
            return
        try:
            self._read_thresholds()
            self._read_interval()
            client = None if self.demo_mode.get() else self._build_client()
        except ValueError as error:
            messagebox.showerror("配置有误", str(error), parent=self.root)
            return

        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.request_in_progress = True
        self.refresh_button.configure(state="disabled")
        self.connection_status.configure(text="正在获取最新直播数据…")

        if client is None:
            self.root.after(180, lambda: self._finish_refresh(self._create_demo_snapshot(), None))
            return

        thread = threading.Thread(target=self._fetch_worker, args=(client,), daemon=True)
        thread.start()

    def _fetch_worker(self, client: QianchuanClient) -> None:
        try:
            snapshot = client.fetch_today_live()
            failure: Exception | None = None
        except (QianchuanApiError, ValueError, OSError) as error:
            snapshot = None
            failure = error
        self.root.after(0, lambda: self._finish_refresh(snapshot, failure))

    def _finish_refresh(self, snapshot: LiveSnapshot | None, error: Exception | None) -> None:
        self.request_in_progress = False
        self.refresh_button.configure(state="normal")
        if error is not None:
            self.header_status.configure(text="● 连接失败", fg="#FCA5A5")
            self.connection_status.configure(text=f"获取失败：{error}")
        elif snapshot is not None:
            self._apply_snapshot(snapshot)
            mode_text = "演示数据" if self.demo_mode.get() else "官方 API"
            self.header_status.configure(text=f"● {mode_text}已连接", fg="#86EFAC")
            self.connection_status.configure(text=f"更新成功：{snapshot.collected_at:%H:%M:%S}")

        if self.monitoring:
            try:
                delay = self._read_interval() * 1000
            except ValueError:
                self.stop_monitoring()
                return
            self.after_id = self.root.after(delay, self.refresh_now)

    def _create_demo_snapshot(self) -> LiveSnapshot:
        values = self.demo_values
        values["cost"] += random.uniform(12, 42)
        values["gmv"] += random.uniform(25, 105)
        values["views"] += random.randint(80, 260)
        values["orders"] += random.randint(0, 4)
        values["clicks"] += random.randint(8, 35)
        values["converts"] += random.randint(0, 5)
        values["follows"] += random.randint(1, 8)
        values["comments"] += random.randint(2, 18)
        values["product_clicks"] += random.randint(10, 40)
        overall_roi = values["gmv"] / values["cost"] if values["cost"] else 0.0
        return LiveSnapshot(
            collected_at=datetime.now(),
            stat_cost=values["cost"],
            total_gmv=values["gmv"],
            overall_roi=overall_roi,
            ad_roi=max(0.0, overall_roi * random.uniform(0.82, 0.96)),
            watch_count=int(values["views"]),
            paid_order_count=int(values["orders"]),
            click_count=int(values["clicks"]),
            ctr=random.uniform(3.2, 4.8),
            convert_count=int(values["converts"]),
            convert_rate=random.uniform(5.5, 8.5),
            follow_count=int(values["follows"]),
            comment_count=int(values["comments"]),
            product_click_count=int(values["product_clicks"]),
            request_id="demo",
        )

    def _apply_snapshot(self, snapshot: LiveSnapshot) -> None:
        self.metric_cards["cost"].set_value(format_money(snapshot.stat_cost))
        self.metric_cards["gmv"].set_value(format_money(snapshot.total_gmv))
        self.metric_cards["roi"].set_value(f"{snapshot.overall_roi:.2f}")
        self.metric_cards["ad_roi"].set_value(f"{snapshot.ad_roi:.2f}")
        self.metric_cards["views"].set_value(f"{snapshot.watch_count:,}")
        self.metric_cards["orders"].set_value(f"{snapshot.paid_order_count:,}")

        target, stop_loss = self._read_thresholds()
        if snapshot.stat_cost <= 0:
            title, detail, background, foreground = (
                "暂无广告消耗",
                "继续观察直播间数据。",
                "#E2E8F0",
                "#475569",
            )
        elif snapshot.overall_roi <= stop_loss:
            title, detail, background, foreground = (
                "⚠ ROI 已触及止损线",
                f"当前 {snapshot.overall_roi:.2f}，止损 {stop_loss:.2f}；请人工核查投放。",
                "#FEE2E2",
                "#991B1B",
            )
        elif snapshot.overall_roi >= target:
            title, detail, background, foreground = (
                "✓ ROI 已达到目标",
                f"当前 {snapshot.overall_roi:.2f}，目标 {target:.2f}；表现处于目标区间。",
                "#DCFCE7",
                "#166534",
            )
        else:
            title, detail, background, foreground = (
                "ROI 处于观察区间",
                f"当前 {snapshot.overall_roi:.2f}，止损 {stop_loss:.2f}，目标 {target:.2f}。",
                "#FFEDD5",
                "#9A3412",
            )
        self.alert_frame.configure(bg=background, highlightbackground=foreground)
        self.alert_label.configure(text=title, bg=background, fg=foreground)
        self.detail_label.configure(text=detail, bg=background, fg=foreground)

        self.history.insert(0, snapshot)
        self.table.insert(
            "",
            0,
            values=(
                snapshot.collected_at.strftime("%Y-%m-%d %H:%M:%S"),
                format_money(snapshot.stat_cost),
                format_money(snapshot.total_gmv),
                f"{snapshot.overall_roi:.2f}",
                f"{snapshot.ad_roi:.2f}",
                f"{snapshot.watch_count:,}",
                f"{snapshot.paid_order_count:,}",
                format_percent(snapshot.ctr),
                f"{snapshot.convert_count:,}",
            ),
        )
        self.count_label.configure(text=f"共 {len(self.history)} 条记录")

    def clear_history(self) -> None:
        if not self.history:
            return
        if not messagebox.askyesno("清空记录", "确定清空本次运行的全部监测记录吗？", parent=self.root):
            return
        self.history.clear()
        for item in self.table.get_children():
            self.table.delete(item)
        self.count_label.configure(text="暂无记录")

    def export_history(self) -> None:
        if not self.history:
            messagebox.showinfo("暂无记录", "获取至少一条数据后才能导出。", parent=self.root)
            return
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="导出千川监测记录",
            initialfile=f"千川直播监测_{datetime.now():%Y%m%d_%H%M%S}.csv",
            defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")],
        )
        if not path:
            return
        fieldnames = [
            "采集时间",
            "广告消耗",
            "累计成交金额",
            "整体ROI",
            "广告ROI",
            "观看人次",
            "广告成单数",
            "广告点击次数",
            "点击率",
            "转化数",
            "转化率",
            "新增粉丝数",
            "评论次数",
            "商品点击次数",
            "request_id",
        ]
        try:
            with Path(path).open("w", encoding="utf-8-sig", newline="") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()
                for item in self.history:
                    writer.writerow(
                        {
                            "采集时间": item.collected_at.strftime("%Y-%m-%d %H:%M:%S"),
                            "广告消耗": item.stat_cost,
                            "累计成交金额": item.total_gmv,
                            "整体ROI": item.overall_roi,
                            "广告ROI": item.ad_roi,
                            "观看人次": item.watch_count,
                            "广告成单数": item.paid_order_count,
                            "广告点击次数": item.click_count,
                            "点击率": item.ctr,
                            "转化数": item.convert_count,
                            "转化率": item.convert_rate,
                            "新增粉丝数": item.follow_count,
                            "评论次数": item.comment_count,
                            "商品点击次数": item.product_click_count,
                            "request_id": item.request_id,
                        }
                    )
        except OSError as error:
            messagebox.showerror("导出失败", str(error), parent=self.root)
            return
        messagebox.showinfo("导出完成", f"监测记录已保存到：\n{path}", parent=self.root)

    def show_about(self) -> None:
        messagebox.showinfo(
            "关于",
            f"{APP_NAME} v{APP_VERSION}\n\n"
            "通过巨量引擎官方 Marketing API 读取直播报表。\n"
            "本软件仅做监测和提示，不包含任何账户写操作。",
            parent=self.root,
        )

    def close(self) -> None:
        self.monitoring = False
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
        self.root.destroy()


def _enable_windows_dpi_awareness() -> None:
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass


def main() -> None:
    _enable_windows_dpi_awareness()
    root = tk.Tk()
    QianchuanMonitorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
