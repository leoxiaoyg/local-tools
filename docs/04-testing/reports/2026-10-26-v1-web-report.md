# v1 Web 测试报告

- 执行时间：2026-10-26 20:37:38
- 用例文档：`docs/04-testing/v1-web-cases.md`
- 被测服务：`http://127.0.0.1:8765`
- 工作目录：`_qa_workdir/`
- 合计：10 · 通过：10 · 失败：0

| 序号 | 测试模块 | 测试项 | 输入项 | 输出项 | 是否通过 |
|---|---|---|---|---|---|
| W01 | 首页 | 工具入口可见 | 无 | 首页 DOM 含分组与入口 | 通过 |
| W02 | 图片压缩 | 单张压缩并下载 | fixtures/a.jpg | _qa_workdir\outputs\web\w02_a_compressed.jpg | 通过 |
| W03 | 文字水印 | 右下单点水印 | a.jpg + 测试店 | _qa_workdir\outputs\web\w03_wm.jpg | 通过 |
| W04 | 文字水印 | 斜向平铺 | a.jpg + tile | _qa_workdir\outputs\web\w04_tile.jpg | 通过 |
| W05 | EXIF | 清除并下载 | a_exif.jpg | _qa_workdir\outputs\web\w05_clean.jpg | 通过 |
| W06 | PDF | 合并两个 PDF | one.pdf + two.pdf | _qa_workdir\outputs\web\w06_merged.pdf | 通过 |
| W07 | PDF | 加密 | one.pdf + secret | _qa_workdir\outputs\web\w07_locked.pdf | 通过 |
| W08 | CSV 清洗 | 去空行去重留列 | dirty.csv + sku,name | _qa_workdir\outputs\web\w08.csv | 通过 |
| W09 | 本地历史 | 处理后首页有记录 | 前置 W03 | historyList count=7 | 通过 |
| W10 | 边界 | 未选文件时按钮禁用 | 无文件 | submitBtn.disabled=True | 通过 |

## 明细

### W01 工具入口可见 — 通过
- 输入：无
- 输出：首页 DOM 含分组与入口
- 备注：中文 EN  本地优先  本地工具集  商品图与 PDF 在本机处理，文件不会上传。  本机记录  最近处理 清空  只在本机保存最近 20 条处理记录，不上传文件内容。  还没有历史记录，先处理一个文件试试。  图片 图片压缩  保持画质

### W02 单张压缩并下载 — 通过
- 输入：fixtures/a.jpg
- 输出：_qa_workdir\outputs\web\w02_a_compressed.jpg
- 备注：size=1047

### W03 右下单点水印 — 通过
- 输入：a.jpg + 测试店
- 输出：_qa_workdir\outputs\web\w03_wm.jpg
- 备注：已加水印（bottom-right，透明度 40%）

### W04 斜向平铺 — 通过
- 输入：a.jpg + tile
- 输出：_qa_workdir\outputs\web\w04_tile.jpg
- 备注：pos_hidden=True; meta=已加水印（平铺，透明度 40%）

### W05 清除并下载 — 通过
- 输入：a_exif.jpg
- 输出：_qa_workdir\outputs\web\w05_clean.jpg

### W06 合并两个 PDF — 通过
- 输入：one.pdf + two.pdf
- 输出：_qa_workdir\outputs\web\w06_merged.pdf
- 备注：pages=2

### W07 加密 — 通过
- 输入：one.pdf + secret
- 输出：_qa_workdir\outputs\web\w07_locked.pdf
- 备注：needs_pass=True

### W08 去空行去重留列 — 通过
- 输入：dirty.csv + sku,name
- 输出：_qa_workdir\outputs\web\w08.csv
- 备注：'sku,name\nA1,苹果\nB2,香蕉\n'

### W09 处理后首页有记录 — 通过
- 输入：前置 W03
- 输出：historyList count=7
- 备注：CSV 清洗 10/26 20:37  dirty.csv -> dirty_clean.csv  PDF 工具 10/26 20:37  one.pdf -> one_locked.pdf  PDF 工具 10/26 20:37  one

### W10 未选文件时按钮禁用 — 通过
- 输入：无文件
- 输出：submitBtn.disabled=True
