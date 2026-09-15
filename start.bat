@echo off
if exist ".venv\Scripts\python.exe" (
  .venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
) else (
  echo 未找到虚拟环境，请先按照 README.md 完成首次安装。
  pause
)
