# Local Tools · 本地工具集

在本地运行的 Web 工具集合，处理过程不依赖第三方云服务。上传的文件由本机 FastAPI 服务处理，适合日常媒体转换、图片处理与文本/表格工具。

## 功能

| 工具 | 路径 | 说明 |
|------|------|------|
| 视频转音频 | `/video.html` | 从视频提取 MP3、WAV、AAC、M4A、OGG、FLAC |
| 视频压缩 | `/video-compress.html` | 调整分辨率与 CRF，输出 MP4 / WebM |
| 图片压缩 | `/image.html` | 尽量保持画质的前提下缩小体积，可指定上限 |
| 图片转换 | `/image-convert.html` | 格式转换（JPG / PNG / WebP）、等比缩放与裁剪 |
| JSON 格式化 | `/json.html` | 格式化、压缩、校验（纯浏览器，不上传服务器） |
| Base64 编解码 | `/base64.html` | 文本本地处理；文件经本地 API 转换 |
| CSV ↔ Excel | `/csv-excel.html` | CSV 与 `.xlsx` 互转 |

## 环境要求

- Python 3.10+
- Windows 或 Linux
- 无需单独安装 FFmpeg（通过 `imageio-ffmpeg` 内置）

## 快速开始

### Windows

```bat
git clone https://gitee.com/xyg-dev/local-tools.git
cd local-tools
run.bat
```

浏览器打开终端显示的地址，一般为 [http://127.0.0.1:8000](http://127.0.0.1:8000)。

### Linux / macOS

```bash
git clone https://gitee.com/xyg-dev/local-tools.git
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

## 依赖安装说明

`run.bat` / `run.sh` 在执行 `pip install` 时会临时使用代理 `http://127.0.0.1:7897`（便于访问 PyPI），安装完成后自动清除，不影响服务运行。若你不需要代理，可自行修改脚本中的 `HTTP_PROXY` / `HTTPS_PROXY`。

## 项目结构

```
local-tools/
├── app/                  # FastAPI 后端
│   ├── main.py           # 路由入口
│   ├── converter.py      # 视频转音频
│   ├── video_compressor.py
│   ├── image_compressor.py
│   ├── image_transform.py
│   └── csv_excel.py
├── static/               # 前端页面与静态资源
├── requirements.txt
├── run.bat               # Windows 启动脚本
└── run.sh                # Linux 启动脚本
```

## 文件大小限制

| 类型 | 上限 |
|------|------|
| 视频 | 500 MB |
| 图片 | 50 MB |
| CSV / Excel | 20 MB |
| Base64 文件编码 | 10 MB |

## 常见问题

**端口被占用：** 启动脚本会自动尝试 8080、8765。

**图片压缩后格式变了：** 选择「保持原格式」时只会在原格式内优化；若需明显缩小 PNG 体积，可手动选择 WebP。

**视频压缩较慢：** 与视频时长和分辨率有关，请耐心等待。

## 仓库

https://gitee.com/xyg-dev/local-tools
