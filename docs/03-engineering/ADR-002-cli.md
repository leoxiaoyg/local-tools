# ADR-002：CLI 与 Web 共用 handler

## Status

Accepted（2026-10-25 · RD / GM）

## Context

Web 已能批量处理图片、EXIF、PDF。脚本用户和跨境卖家批量场景需要不打开浏览器。若 CLI 再写一套压缩 / 拆分逻辑，会和 `app/*.py` 分叉。ADR-001 已约定 CLI 直接调 `handler` + `run_batch`，不经 HTTP。

## Decision

1. 入口：`python -m app`（`app/__main__.py` → `app/cli.py`）。`argparse` 子命令，不加 Click / Typer。
2. 首刀命令：`image compress|convert`、`exif inspect|strip`、`pdf merge|compress|split`。加密 / 解密后补，仍走同一入口：`pdf encrypt|decrypt`（见 ADR-003）。
3. 处理函数只调用现有 `compress_image` / `transform_image` / `inspect_exif` / `strip_exif` / `merge_pdfs` / `compress_pdf` / `split_pdf` / `encrypt_pdf` / `decrypt_pdf` 与 `run_batch`。禁止复制算法。
4. 读本地路径，写本地路径。不启动 uvicorn，不发 HTTP。
5. 输出约定：
   - 1 个输入：写出单个结果文件（`-o` 为文件；省略则写到当前目录，文件名跟 handler）。
   - 多个输入：默认 zip；`-o` 指向**已存在目录**时逐个落盘。
6. 语言：`--lang zh|en`，或环境变量 `LT_LANG`，默认跟系统 locale。错误文案走 `app/i18n.py` 的 `translate_text`。
7. 上限与 Web 相同（图片 50 个 / 200MB，PDF 单文件 80MB、合并 30 个 / 200MB）。不在 CLI 另开一套限额。

## 非目标（本 ADR）

- 视频转音频 / 视频压缩
- 文档 Office 转换（Word / PPT）
- PDF 加密（2026-10-25 已按本 ADR 接入，细节见 ADR-003）
- 便携 exe
- 守护进程、监听目录、云同步

## Consequences

- Web 改 handler 行为，CLI 自动跟上；修 bug 只改一处。
- CLI 用户必须有本机 Python 与依赖。分发仍靠「先证 CLI、exe 推迟」。
- Windows 控制台需 UTF-8 输出（`cli.py` 启动时 `reconfigure`），避免中文帮助乱码。

## Rollback

删除 `app/cli.py`、`app/__main__.py`；Web 不受影响。
