# CLI 冒烟清单（P0）

在项目根目录、已激活虚拟环境后执行。结果栏由 QA 勾。

| # | 步骤 | 输入 | 预期 | 结果 |
|---|---|---|---|---|
| 1 | `python -m app --help` | 无 | 列出 image / exif / pdf / csv / video，退出 0 | |
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
| 13 | `pdf encrypt a.pdf --user-pw secret -o locked.pdf` | 未加密 PDF | 产出文件；需要密码才能打开 | |
| 14 | `pdf decrypt locked.pdf --password secret -o opened.pdf` | 上一步结果 | 产出文件；无需密码可开 | |
| 15 | `pdf decrypt locked.pdf --password nope`（`--lang en`） | 上一步加密文件 | 退出非 0 | |
| 16 | `image watermark a.jpg --text Shop -o wm.jpg` | 小 JPEG | 产出文件 | |
| 16b | `image watermark a.jpg --text Shop --tile -o wm_tile.jpg` | 小 JPEG | 产出文件 | |
| 17 | `csv clean a.csv --keep sku,name -o out.csv` | 含空行/重复行/多余列 | 产出文件；去掉空行与重复行，只留 sku、name | |
| 18 | `video audio 片段.mp4 --format mp3 -o out.mp3` | 1 秒短片 | 产出 mp3 | |
| 19 | `video compress a.mp4 --crf 28 --resolution 480 -o out.mp4` | 同上 | 产出 mp4 | |
| 20 | `video audio nope.txt`（`--lang en`） | 非视频 | 退出非 0，stderr 含 `Unsupported video format` | |
| 21 | `video compress a.mp4 --crf 40` | 短片 | 退出非 0 | |
| 22 | `image compress a.jpg bad.txt -o out.zip`（`--lang en`） | 一张图 + 一个非图片 | zip 内 `errors.txt` 含 `# Failed items`，且失败原因是英文 | |

可复跑脚本（项目根目录）：`python tests/cli_smoke.py`，通过时打印 `CLI_SMOKE_OK`。

## 不测（本里程碑）

Office、exe、视频画质逐帧对比。加密权限位是否被所有阅读器严格执行，只做打开/解密验证。视频冒烟只用约 1 秒的短片。

## 回归登记

新 CLI 子命令未进本表 = 未交付。Web 回归仍按各工具页手工/浏览器清单，不与本表混写。
