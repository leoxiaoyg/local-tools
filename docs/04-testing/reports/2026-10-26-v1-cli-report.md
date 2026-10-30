# v1 CLI 测试报告

- 执行时间：2026-10-26 20:31:30
- 用例文档：`docs/04-testing/v1-cli-cases.md`
- 工作目录：`_qa_workdir/`
- 合计：19 · 通过：19 · 失败：0

| 序号 | 测试模块 | 测试项 | 输入项 | 输出项 | 是否通过 |
|---|---|---|---|---|---|
| C01 | CLI 入口 | 帮助信息 | 无 | usage: python -m app [-h] [--lang {zh,en}] {image,exif,pdf,csv,video} ... | 通过 |
| C02 | 图片压缩 | 单张压缩 | fixtures/a.jpg | c02_small.jpg size=1047 | 通过 |
| C03 | 图片转换 | JPG→WebP | fixtures/a.jpg | c03.webp size=174 | 通过 |
| C04 | 图片压缩 | 批量 zip | a.jpg + b.png | zip entries=2 | 通过 |
| C05 | 文字水印 | 单点位置 | a.jpg + Shop | size=2163 | 通过 |
| C06 | 文字水印 | 斜向平铺 | a.jpg + --tile | size=5135 | 通过 |
| C07 | EXIF | 查看 | a_exif.jpg | {"filename": "a_exif.jpg", "format": "JPEG", "width": 320, "height": 240, "has_exif": true, "has_gps": false, "sensitive_count": 3, "fields": [{"key": "Model", "value": "FixtureCam", "sensitive": true | 通过 |
| C08 | EXIF | 清除 | a_exif.jpg | {"filename": "c08_clean.jpg", "format": "JPEG", "width": 320, "height": 240, "has_exif": false, "has_gps": false, "sensitive_count": 0, "fields": []} | 通过 |
| C09 | PDF | 合并 | one.pdf + two.pdf | pages=2 | 通过 |
| C10 | PDF | 压缩 | one.pdf | size=756 | 通过 |
| C11 | PDF | 按页拆分 | c09_merged.pdf | pdf_entries=2 | 通过 |
| C12 | PDF | 加密 | one.pdf + secret | needs_pass=True | 通过 |
| C13 | PDF | 解密 | c12_locked.pdf | needs_pass=False | 通过 |
| C14 | PDF | 错误密码 | locked + nope | Wrong password
 | 通过 |
| C15 | CSV 清洗 | 去空行/去重/留列 | dirty.csv | 'sku,name\nA1,苹果\nB2,香蕉\n' | 通过 |
| C16 | 视频 | 转音频 | clip.mp4 | size=6496; err= | 通过 |
| C17 | 视频 | 压缩 | clip.mp4 | size=20450; err= | 通过 |
| C18 | 边界 | 文件不存在 | fixtures/nope.jpg | File not found: C:\FileDir\Personal\local-tools\_qa_workdir\fixtures\nope.jpg
 | 通过 |
| C19 | 边界 | 批量部分失败 | a.jpg + not_image.txt | # Failed items

not_image.txt	Unsupported image format: .txt
 | 通过 |

## 明细

### C01 帮助信息 — 通过
- 预期：退出 0 且含主命令
- 实际输出：usage: python -m app [-h] [--lang {zh,en}] {image,exif,pdf,csv,video} ...

### C02 单张压缩 — 通过
- 预期：产出文件
- 实际输出：c02_small.jpg size=1047

### C03 JPG→WebP — 通过
- 预期：产出 webp
- 实际输出：c03.webp size=174

### C04 批量 zip — 通过
- 预期：zip 可解压
- 实际输出：zip entries=2

### C05 单点位置 — 通过
- 预期：产出 JPEG
- 实际输出：size=2163

### C06 斜向平铺 — 通过
- 预期：产出 JPEG
- 实际输出：size=5135

### C07 查看 — 通过
- 预期：JSON 含尺寸
- 实际输出：{"filename": "a_exif.jpg", "format": "JPEG", "width": 320, "height": 240, "has_exif": true, "has_gps": false, "sensitive_count": 3, "fields": [{"key": "Model", "value": "FixtureCam", "sensitive": true

### C08 清除 — 通过
- 预期：产出且无 GPS
- 实际输出：{"filename": "c08_clean.jpg", "format": "JPEG", "width": 320, "height": 240, "has_exif": false, "has_gps": false, "sensitive_count": 0, "fields": []}

### C09 合并 — 通过
- 预期：≥2 页
- 实际输出：pages=2

### C10 压缩 — 通过
- 预期：产出 PDF
- 实际输出：size=756

### C11 按页拆分 — 通过
- 预期：zip 页数=源
- 实际输出：pdf_entries=2

### C12 加密 — 通过
- 预期：需密码
- 实际输出：needs_pass=True

### C13 解密 — 通过
- 预期：无密码可开
- 实际输出：needs_pass=False

### C14 错误密码 — 通过
- 预期：退出非 0
- 实际输出：Wrong password


### C15 去空行/去重/留列 — 通过
- 预期：仅 sku,name 无重复
- 实际输出：'sku,name\nA1,苹果\nB2,香蕉\n'

### C16 转音频 — 通过
- 预期：产出 mp3
- 实际输出：size=6496; err=

### C17 压缩 — 通过
- 预期：产出 mp4
- 实际输出：size=20450; err=

### C18 文件不存在 — 通过
- 预期：File not found
- 实际输出：File not found: C:\FileDir\Personal\local-tools\_qa_workdir\fixtures\nope.jpg


### C19 批量部分失败 — 通过
- 预期：zip 含 errors.txt 英文
- 实际输出：# Failed items

not_image.txt	Unsupported image format: .txt

