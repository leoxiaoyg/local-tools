# CLI 冒烟清单（P0）

在项目根目录、已激活虚拟环境后执行。结果栏由 QA 勾。

| # | 步骤 | 输入 | 预期 | 结果 |
|---|---|---|---|---|
| 1 | `python -m app --help` | 无 | 列出 image / exif / pdf，退出 0 | |
| 2 | `python -m app --lang en image compress 不存在.jpg` | 无此文件 | stderr：`File not found`，退出非 0 | |
| 3 | `image compress a.jpg -o a_small.jpg` | 小 JPEG | 产出文件，stdout 含「已写入」 | |
| 4 | `image convert a.jpg --format webp -o a.webp` | 同上 | 产出 `.webp` | |
| 5 | `image compress a.jpg b.png -o imgs.zip` | 两张图 | 产出 zip，内含结果 | |
| 6 | `exif inspect a.jpg --json` | 任意静图 | JSON 含 width / height / has_gps | |
| 7 | `exif strip a.jpg -o clean.jpg` | 同上 | 产出文件；再 inspect 敏感项不增加 | |
| 8 | `pdf merge a.pdf b.pdf -o merged.pdf` | 两个小 PDF | 至少 2 页 | |
| 9 | `pdf compress a.pdf --preset light -o c.pdf` | 一个 PDF | 产出 PDF | |
| 10 | `pdf split merged.pdf --mode pages -o pages.zip` | 合并结果 | zip 内页数 = 源页数 | |
| 11 | `pdf split merged.pdf --mode range --pages 1 -o p1.pdf` | 同上 | 单页 PDF | |
| 12 | `pdf merge only-one.pdf` | 1 个文件 | 退出非 0（至少 2 个）或先报找不到 | |

## 不测（本里程碑）

视频、Office、加密 PDF、exe。

## 回归登记

新 CLI 子命令未进本表 = 未交付。Web 回归仍按各工具页手工/浏览器清单，不与本表混写。
