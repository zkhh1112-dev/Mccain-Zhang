# 直播投流决策助手（Windows 桌面版）

桌面版是原生 Windows 窗口，不需要打开浏览器。它复用项目已有的决策与独立风控逻辑，不连接真实广告账户，也不会执行真实预算操作。

## 直接运行

双击 `start_desktop.bat`，或在当前目录运行：

```powershell
.venv\Scripts\python.exe desktop_app.py
```

桌面版支持：

- 输入直播数据与策略参数
- 生成加预算、减预算、暂停或保持建议
- 展示建议原因和独立风控结果
- 保留本次运行的决策记录
- 将记录导出为 Excel 可直接打开的 UTF-8 CSV 文件

## 生成独立 EXE

双击 `build_exe.bat`，或运行：

```powershell
.\build_exe.ps1
```

脚本会安装 PyInstaller，并在下面的位置生成软件：

```text
dist\LiveStreamAgent.exe
```

生成的 EXE 可复制到其他 Windows 电脑直接运行，不要求目标电脑安装 Python。

## 快捷键

- `Ctrl + Enter`：生成决策建议
- `Ctrl + S`：导出决策记录

## 运行测试

```powershell
.venv\Scripts\python.exe -m unittest -v
```
