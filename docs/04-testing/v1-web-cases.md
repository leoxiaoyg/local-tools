# v1 Web 测试用例

**版本**：v1 使用期验收  
**服务**：必须打用户正在用的源，默认 `http://127.0.0.1:8765`（以地址栏为准）  
**工作数据**：仅 `_qa_workdir/`  
**执行**：`python _qa_workdir/scripts/run_web_cases.py --base http://127.0.0.1:8765`  
**对应报告**：`_qa_workdir/reports/v1-web-report.md`

浏览器用 Playwright Chromium 模拟：打开页面 → 选文件 → 填参数 → 点提交 → 校验结果区 / 下载文件。  
「是否通过」栏在执行前为空，由报告回填。

| 序号 | 测试模块 | 测试项 | 操作步骤 | 预期结果 | 输入项 | 输出项 | 是否通过 |
|---|---|---|---|---|---|---|---|
| W01 | 首页 | 工具入口可见 | 1. 打开 `/` 2. 检查分组与关键卡片 | 页面标题/工具分组含图片、文档、视频、文本；可见水印、EXIF、PDF、CSV 清洗入口 | 无 | 首页 DOM | 通过 |
| W02 | 图片压缩 | 单张压缩并下载 | 1. 打开 `/image.html` 2. 选择 `fixtures/a.jpg` 3. 点击开始压缩 4. 等待结果并下载 | 结果区出现；下载文件体积 > 0 | `a.jpg` | `outputs/web/w02_*.jpg`（或同扩展名） | 通过 |
| W03 | 文字水印 | 右下单点水印 | 1. 打开 `/watermark.html` 2. 选 `a.jpg` 3. 文字填 `测试店` 4. 不勾平铺，位置右下 5. 提交并下载 | 结果区显示成功；下载 JPEG 存在 | 图 + 文字「测试店」 | `outputs/web/w03_wm.jpg` | 通过 |
| W04 | 文字水印 | 斜向平铺 | 1. 打开 `/watermark.html` 2. 选 `a.jpg` 3. 文字 `铺满` 4. 勾选「铺满整张」5. 提交并下载 | 位置下拉隐藏或忽略；下载成功；结果文案含平铺相关提示（若页面展示） | 图 + tile | `outputs/web/w04_tile.jpg` | 通过 |
| W05 | EXIF | 清除并下载 | 1. 打开 `/exif.html` 2. 选 `a_exif.jpg` 3. 等待摘要出现 4. 点击清除下载 | 摘要可见；下载文件存在 | `a_exif.jpg` | `outputs/web/w05_clean.jpg` | 通过 |
| W06 | PDF | 合并两个 PDF | 1. 打开 `/pdf.html` 2. 操作选「合并」3. 选 `one.pdf`、`two.pdf` 4. 提交并下载 | 结果成功；下载 PDF 页数 ≥ 2 | `one.pdf` + `two.pdf` | `outputs/web/w06_merged.pdf` | 通过 |
| W07 | PDF | 加密 | 1. 操作选「加密」2. 选 `one.pdf` 3. 填打开密码 `secret` 4. 提交并下载 | 下载 PDF 存在且需密码打开 | PDF + 密码 secret | `outputs/web/w07_locked.pdf` | 通过 |
| W08 | CSV 清洗 | 去空行去重留列 | 1. 打开 `/csv-clean.html` 2. 选 `dirty.csv` 3. 勾去空行/去重 4. 保留列填 `sku,name` 5. 提交并下载 | 结果成功；下载 CSV 仅含预期列且无空行 | `dirty.csv` | `outputs/web/w08.csv` | 通过 |
| W09 | 本地历史 | 处理后首页有记录 | 1. 先完成 W03 2. 打开 `/` 3. 查看「最近处理」 | 列表非空，或至少出现水印相关摘要 | 前置 W03 | 首页历史列表文案 | 通过 |
| W10 | 边界 | 未选文件时按钮禁用 | 1. 打开 `/watermark.html` 2. 不选文件 | 「开始加水印」按钮为 disabled | 无文件 | 按钮状态 | 通过 |

## 不在本表范围

视频页长耗时压缩主观画质、Office 转换、暗色模式像素级对比、英文全站逐句对照。
