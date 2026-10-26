# ADR-004：便携 exe 继续推迟，形态先定死

## Status

Accepted（2026-10-26 · RD / GM）

本刀只做评估。没有安装包，没有 PyInstaller 配置，也没有新增运行依赖。

## Context

CLI 已经覆盖图片、EXIF、PDF、CSV 和视频转音频 / 压缩，路线图里「先证明 CLI」已经满足。分发仍要本机有 Python，并用 `run.bat` / `run.sh` 拉起 `uvicorn app.main:app`。

若现在把站点打成 exe，要带上当前 `requirements.txt` 里的 FastAPI、PyMuPDF、pdf2docx、easyofd、Pillow，以及 `imageio-ffmpeg` 自带的 ffmpeg。Word / PPT 转 PDF 仍依赖本机 LibreOffice 或 Microsoft Office，打不进包。未签名的 Windows 可执行文件还有被杀毒软件拦截的风险。仓库里没有「没有 Python 就没法用」的使用记录。2026-10-24 的路线图评审写过：近两个月不把 exe 当焦点。

## Decision

**继续推迟打包。** 在重新开工之前，不添加打包工具，不提交 spec，不在 README 里写「下载即用」。

重新开工要同时满足下面两条：

1. 所有者点名打包。
2. 已有一位不写代码的使用者，对方机器上没有本仓库的 Python 环境，`run.bat` 走不通。或日期到了 2026-12-24（「近两月不作为焦点」到期）且所有者仍点名打包。

再次开工时按下表做，不再重新选型：

| 项 | 定死的做法 |
|---|---|
| 形态 | 一个 Windows 程序。启动后只监听 `127.0.0.1`，端口沿用 `run.bat` 的 8000 → 8080 → 8765，然后打开系统浏览器 |
| 逻辑 | 进程内跑现有 `app.main:app`。不复制压缩、转换、加密算法 |
| 命令行 | `python -m app` 继续给脚本用。exe 不取代 CLI，也不去调 CLI |
| 依赖 | 打进当前 Web 运行所需的 Python 包和 ffmpeg。不打 LibreOffice，不打 Microsoft Office |
| Office | 没有本机 Office 时，沿用现在的错误说明，不能闪退 |
| 网络 | 不上传文件，不做遥测。冻结包里不要 `--reload` |
| 签名 | 第一包可以不签名。杀毒误报记成已知风险，不靠加壳掩盖 |
| 平台 | 只做 Windows。macOS / Linux 仍用 `run.sh` |

铺满水印、Office 进命令行、透视和公式不在这次评估里，也不因本 ADR 打开。

## Consequences

- 今天的分发方式仍是克隆仓库后运行 `run.bat` / `run.sh`，或在已安装依赖的环境里执行 `python -m app`。
- 对外不能把产品说成免安装。加密和 EXIF 继续不叫合规认证。
- 下次真的打包时，P0 只有两条：双击后浏览器打开本机页面；在没有 Office 的机器上做 Word 转 PDF，出现现有的缺引擎说明。

## Rollback

删除本文件，并把路线图里 exe 一行改回「先证 CLI」。不影响已落地的 Web 和 CLI。
