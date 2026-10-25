# CSV 清洗 冒烟（P0）

网页打开用户正在用的那个 origin 上的 `/csv-clean.html`（先确认端口，勿另起一个自测过了就算）。CLI 也可跑 `python tests/cli_smoke.py`（含第 17 条）。

| ID | 步骤 | 期望 | 结果 |
|---|---|---|---|
| P0-1 | 上传含空行、重复行、多余列的 CSV，默认选项，开始 | 下载 `*_clean.csv`；空行和重复行去掉 | |
| P0-2 | 保留列填 `sku,name` 或 `1,3` | 只剩指定列 | |
| P0-3 | 填不存在的列名 | 400，提示找不到列 | |
| P0-4 | 多选 2 个，点其中一条删除后再处理 | 只处理剩下的；多文件为 zip | |
| P0-5 | 切换 EN | 按钮与提示为英文 | |
| P0-6 | CLI：`csv clean a.csv --keep sku,name -o out.csv` | 产出文件；与 `cli-smoke.md` 第 17 条一致 | |
| P0-7 | 对当前 origin `POST /api/csv/clean` | 不是 405 | |

## 不测（本里程碑）

透视、公式、按单列模糊去重、Excel 清洗。
