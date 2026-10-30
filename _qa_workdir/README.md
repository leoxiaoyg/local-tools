# QA 工作目录

本目录只放本次验收用的夹具、输出与报告草稿，**不要**在仓库其它路径散落测试文件。

```text
_qa_workdir/
├── fixtures/     # 生成的输入
├── outputs/
│   ├── cli/      # CLI 产出
│   └── web/      # Web 下载
├── reports/      # 执行报告（可复制到 docs/04-testing/reports/）
└── scripts/      # 生成夹具 / 跑用例
```

## 命令

```bat
.\.venv\Scripts\python.exe _qa_workdir\scripts\gen_fixtures.py
.\.venv\Scripts\python.exe _qa_workdir\scripts\run_cli_cases.py
.\.venv\Scripts\python.exe _qa_workdir\scripts\run_web_cases.py --base http://127.0.0.1:8765
```

Web 需要本机 Playwright Chromium：`pip install playwright` 后 `playwright install chromium`。

## 清理

删除整个 `_qa_workdir/fixtures`、`outputs`（可保留 `scripts` 与本 README）。或：

```bat
rmdir /s /q _qa_workdir\fixtures _qa_workdir\outputs
```

本目录已在 `.gitignore`，默认不入库。
