# v1 CLI 测试用例

**版本**：v1 使用期验收  
**环境**：项目根目录，已激活 `.venv`，工作数据仅在 `_qa_workdir/`  
**执行**：`python _qa_workdir/scripts/run_cli_cases.py`  
**对应报告**：`_qa_workdir/reports/v1-cli-report.md`（跑完生成）

「是否通过」栏在执行前为空，由报告回填。

| 序号 | 测试模块 | 测试项 | 操作步骤 | 预期结果 | 输入项 | 输出项 | 是否通过 |
|---|---|---|---|---|---|---|---|
| C01 | CLI 入口 | 帮助信息 | 1. 在项目根执行 `python -m app --help` | 退出码 0；stdout 含 image / exif / pdf / csv / video | 无 | 帮助文本 | 通过 |
| C02 | 图片压缩 | 单张压缩 | 1. `python -m app image compress fixtures/a.jpg -o outputs/cli/c02_small.jpg` | 退出码 0；产出文件存在且体积 > 0 | `fixtures/a.jpg` | `outputs/cli/c02_small.jpg` | 通过 |
| C03 | 图片转换 | JPG→WebP | 1. `python -m app image convert fixtures/a.jpg --format webp -o outputs/cli/c03.webp` | 退出码 0；产出为 WebP | `fixtures/a.jpg` | `outputs/cli/c03.webp` | 通过 |
| C04 | 图片压缩 | 批量 zip | 1. `python -m app image compress fixtures/a.jpg fixtures/b.png -o outputs/cli/c04.zip` | 退出码 0；zip 可解压且含结果 | `a.jpg` + `b.png` | `outputs/cli/c04.zip` | 通过 |
| C05 | 文字水印 | 单点位置 | 1. `python -m app image watermark fixtures/a.jpg --text Shop -o outputs/cli/c05_wm.jpg` | 退出码 0；产出 JPEG | `a.jpg`，文字 Shop | `outputs/cli/c05_wm.jpg` | 通过 |
| C06 | 文字水印 | 斜向平铺 | 1. `python -m app image watermark fixtures/a.jpg --text Shop --tile -o outputs/cli/c06_tile.jpg` | 退出码 0；产出 JPEG | `a.jpg`，`--tile` | `outputs/cli/c06_tile.jpg` | 通过 |
| C07 | EXIF | 查看 | 1. `python -m app exif inspect fixtures/a_exif.jpg --json` | 退出码 0；JSON 含 width/height | `fixtures/a_exif.jpg` | JSON stdout | 通过 |
| C08 | EXIF | 清除 | 1. `python -m app exif strip fixtures/a_exif.jpg -o outputs/cli/c08_clean.jpg` 2. 再 inspect 输出文件 | 退出码 0；清除后 has_gps 不为 true（或敏感项不增加） | `a_exif.jpg` | `outputs/cli/c08_clean.jpg` | 通过 |
| C09 | PDF | 合并 | 1. `python -m app pdf merge fixtures/one.pdf fixtures/two.pdf -o outputs/cli/c09_merged.pdf` | 退出码 0；合并 PDF 至少 2 页 | `one.pdf` + `two.pdf` | `outputs/cli/c09_merged.pdf` | 通过 |
| C10 | PDF | 压缩 | 1. `python -m app pdf compress fixtures/one.pdf --preset light -o outputs/cli/c10.pdf` | 退出码 0；产出 PDF | `one.pdf` | `outputs/cli/c10.pdf` | 通过 |
| C11 | PDF | 按页拆分 | 1. 对 C09 结果：`pdf split … --mode pages -o outputs/cli/c11_pages.zip` | 退出码 0；zip 内页数 = 源页数 | `c09_merged.pdf` | `outputs/cli/c11_pages.zip` | 通过 |
| C12 | PDF | 加密 | 1. `python -m app pdf encrypt fixtures/one.pdf --user-pw secret -o outputs/cli/c12_locked.pdf` | 退出码 0；文件需密码才能打开 | `one.pdf`，密码 secret | `outputs/cli/c12_locked.pdf` | 通过 |
| C13 | PDF | 解密 | 1. `python -m app pdf decrypt outputs/cli/c12_locked.pdf --password secret -o outputs/cli/c13_opened.pdf` | 退出码 0；产出可无密码打开 | 加密 PDF + 正确密码 | `outputs/cli/c13_opened.pdf` | 通过 |
| C14 | PDF | 错误密码 | 1. `python -m app --lang en pdf decrypt outputs/cli/c12_locked.pdf --password nope` | 退出码非 0 | 加密 PDF + 错误密码 | stderr 错误信息 | 通过 |
| C15 | CSV 清洗 | 去空行/去重/留列 | 1. `python -m app csv clean fixtures/dirty.csv --keep sku,name -o outputs/cli/c15.csv` | 退出码 0；仅留 sku,name；无空行与重复行 | `dirty.csv` | `outputs/cli/c15.csv` | 通过 |
| C16 | 视频 | 转音频 | 1. `python -m app video audio fixtures/clip.mp4 --format mp3 -o outputs/cli/c16.mp3` | 退出码 0；产出 mp3 | `clip.mp4` | `outputs/cli/c16.mp3` | 通过 |
| C17 | 视频 | 压缩 | 1. `python -m app video compress fixtures/clip.mp4 --crf 28 --resolution 480 -o outputs/cli/c17.mp4` | 退出码 0；产出 mp4 | `clip.mp4` | `outputs/cli/c17.mp4` | 通过 |
| C18 | 边界 | 文件不存在 | 1. `python -m app --lang en image compress fixtures/nope.jpg` | 退出码非 0；含 `File not found` | 不存在的路径 | stderr | 通过 |
| C19 | 边界 | 批量部分失败 | 1. `python -m app --lang en image compress fixtures/a.jpg fixtures/not_image.txt -o outputs/cli/c19.zip` | 退出码 0 或按实现约定；zip 内 `errors.txt` 含英文失败原因 | 图 + 非图 | `outputs/cli/c19.zip` | 通过 |

## 不在本表范围

Office 转换、便携 exe、真实店主大文件、画质主观对比。
