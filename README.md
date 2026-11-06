# Local Tools · 本地工具集

本机跑的一套小工具：商品图、PDF、表格、视频等。文件留在这台电脑上，不传到别人的服务器。

源码按 **AGPL-3.0** 开源。要自己装 Python 再启动，目前没有免安装包。

Short English note: local web tools for images, PDFs, spreadsheets, and video. Processing stays on your machine. AGPL-3.0. Python required; no packaged installer yet.

## 功能

| 工具 | 路径 | 说明 |
|------|------|------|
| 视频转音频 | `/video.html` | 从视频提取 MP3、WAV、AAC、M4A、OGG、FLAC |
| 视频压缩 | `/video-compress.html` | 调整分辨率与 CRF，输出 MP4 / WebM |
| 图片压缩 | `/image.html` | 尽量保持画质的前提下缩小体积，可指定上限；支持批量 zip |
| 图片转换 | `/image-convert.html` | 格式转换（JPG / PNG / WebP）、等比缩放与裁剪；支持批量 zip |
| EXIF 清除 | `/exif.html` | 查看并去掉拍摄时间、机型、GPS |
| 文字水印 | `/watermark.html` | 店名/说明文字；位置或斜向平铺 + 透明度；支持批量 zip |
| JSON 格式化 | `/json.html` | 格式化、压缩、校验（纯浏览器） |
| Base64 编解码 | `/base64.html` | 文本本地处理；文件经本地 API 转换 |
| CSV ↔ Excel | `/csv-excel.html` | CSV 与 `.xlsx` 互转 |
| CSV 清洗 | `/csv-clean.html` | 去空行、去重、只留指定列；支持批量 zip |
| 文档转换 | `/doc-convert.html` | 图片/PDF/OFD/Word/PPT 互转 |
| PDF 工具 | `/pdf.html` | 合并、压缩、按页拆分 / 提取页、加密 / 解密 |
| 最近处理 | `/` | 首页保留最近 20 条本机处理记录，可清空 |

界面有中文 / English，右上角切换，记在本机。接口报错语言跟 `Accept-Language`。首页「最近处理」只存工具名、时间和结果摘要，不存文件内容。

## 环境要求

- Python 3.10+
- Windows 或 Linux
- FFmpeg 不用单独装（`imageio-ffmpeg` 自带）
- Word / PPT → PDF 需要本机有 **LibreOffice**（推荐）或 **Microsoft Office**（Windows）

## 快速开始

任选一个仓库地址（内容同一套）：

```text
https://github.com/leoxiaoyg/local-tools.git
https://gitee.com/xyg-dev/local-tools.git
```

### Windows

```bat
git clone https://github.com/leoxiaoyg/local-tools.git
cd local-tools
run.bat
```

浏览器打开终端里打印的地址，一般是 [http://127.0.0.1:8000](http://127.0.0.1:8000)。端口被占用时脚本会试 8080、8765。

### Linux / macOS

```bash
git clone https://github.com/leoxiaoyg/local-tools.git
cd local-tools
chmod +x run.sh
./run.sh
```

### 手动启动

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux:    source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

没有 `main.py`。入口是 `app.main:app`，或直接用上面的 `run.bat` / `run.sh`。

### pip 代理（可选）

启动脚本默认直连 PyPI。本机访问 PyPI 很慢、又有本地代理时再设：

```bat
set LT_PIP_PROXY=http://127.0.0.1:7897
run.bat
```

```bash
export LT_PIP_PROXY=http://127.0.0.1:7897
./run.sh
```

## 命令行

和网页共用同一套处理函数，不走 HTTP。覆盖图片压缩 / 转换 / 文字水印、视频转音频 / 压缩、EXIF、PDF 合并压缩拆分与加密解密、CSV 清洗。Office 转换暂不提供。

```bash
python -m app --help
python -m app --lang en image compress photo.jpg -o small.jpg
python -m app image convert a.png b.png --format webp -o converted.zip
python -m app image watermark photo.jpg --text 店铺名
python -m app exif inspect photo.jpg
python -m app exif strip *.jpg -o clean.zip
python -m app pdf merge a.pdf b.pdf -o merged.pdf
python -m app pdf compress invoice.pdf --preset strong
python -m app pdf split doc.pdf --mode range --pages 1-3,5
python -m app pdf encrypt invoice.pdf --user-pw secret -o locked.pdf
python -m app pdf decrypt locked.pdf --password secret -o opened.pdf
python -m app csv clean data.csv --keep sku,name
python -m app video audio clip.mp4 --format mp3
python -m app video compress clip.mp4 --crf 28 --resolution 720
```

`--lang zh|en` 控制提示语言，也可设 `LT_LANG`。多文件默认打 zip；`-o` 指到已有目录就逐个写出。

命令说明见 [docs/01-product/cli.md](docs/01-product/cli.md)。文档入口：[docs/00-governance/wiki.md](docs/00-governance/wiki.md)。

## 已知限制

- 没有 Windows 安装包 / 单文件 exe（见 ADR-004）
- Office 相关转换依赖本机已装的办公软件，不打进本仓库
- PDF 能力用了 PyMuPDF（AGPL）；加密、清 EXIF 都不是合规认证
- `.cursor/skills/` 是给 Cursor Agent 用的角色说明，用不用随你

## 赞助

现有工具都能直接用，不靠赞助解锁。若你愿意支持维护，爱发电 / GitHub Sponsors 链接有了再挂到这里；占位地址先不写。

## 许可证

本仓库以 [AGPL-3.0](LICENSE) 发布。PDF 路径依赖的 PyMuPDF 也是 AGPL，两边对齐比较省事。第三方库各自遵守其原许可证。

参与方式见 [CONTRIBUTING.md](CONTRIBUTING.md)。安全相关见 [SECURITY.md](SECURITY.md)。

## 项目结构

```
local-tools/
├── app/                  # FastAPI 后端
├── static/               # 前端页面
├── tests/                # CLI 冒烟：python tests/cli_smoke.py
├── docs/                 # 说明书、ADR、测试（入口 wiki.md）
├── _qa_workdir/          # QA 脚本；夹具与产出默认不入库
├── requirements.txt
├── run.bat / run.sh
├── LICENSE
├── CONTRIBUTING.md
└── SECURITY.md
```

## 文件大小限制

| 类型 | 上限 |
|------|------|
| 视频 | 单文件 500 MB；命令行一批最多 10 个 |
| 图片 | 单文件 50 MB；批量合计 200 MB / 最多 50 张 |
| CSV / Excel | 单文件 20 MB；清洗批量合计 200 MB / 最多 50 个 |
| 文档转换 | 80 MB |
| PDF | 单文件 80 MB；合并合计 200 MB / 最多 30 个 |
| Base64 文件编码 | 10 MB |

## 文档转换说明

| 转换 | 实现方式 | 说明 |
|------|----------|------|
| 图片 → PDF | Pillow | 纯 Python，支持多图合并 |
| 图片 → OFD | easyofd | 纯 Python |
| PDF → OFD | easyofd | 纯 Python；复杂版式可能有差异 |
| PDF → Word | pdf2docx | 纯 Python；扫描件无 OCR |
| Word → PDF | LibreOffice / MS Word | 需本机 Office 引擎 |
| PPT → PDF | LibreOffice / MS PowerPoint | 需本机 Office 引擎 |

## 常见问题

**端口被占用：** 启动脚本会接着试 8080、8765。

**图片压缩后格式变了：** 「保持原格式」只在原格式里压；PNG 想明显变小，可改成 WebP。

**视频压缩慢：** 和时长、分辨率有关，等一会儿。

## 仓库

- GitHub：https://github.com/leoxiaoyg/local-tools  
- Gitee：https://gitee.com/xyg-dev/local-tools  

GitHub 发布步骤见 [docs/05-project/github-publish-checklist.md](docs/05-project/github-publish-checklist.md)。
