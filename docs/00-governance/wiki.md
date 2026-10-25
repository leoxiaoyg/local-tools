# local-tools 文档入口

先读本页，再按任务打开分册。不要把整棵 `docs/` 一次塞进上下文。

## 必读（按角色）

| 你要做的事 | 先读 | 可能还要读 | 先别读 |
|---|---|---|---|
| 问编制 / 谁拍板 | `team-charter.md` | 本页 | ADR、测试 |
| 问下一步做什么 | `docs/local-tools-roadmap.md` | `05-project/wrap-2026-10-24.md` | 实现细节 |
| 用 Web | `README.md` | `01-product/pdf.md`、`01-product/watermark.md`、`01-product/csv-clean.md`、各工具页 | CLI 说明书 |
| 改文字水印 | `01-product/watermark.md` | `04-testing/watermark.md` | 铺满/贴图（未做） |
| 改 CSV 清洗 | `01-product/csv-clean.md` | `04-testing/csv-clean.md` | 透视/公式（未做） |
| 用命令行 | `01-product/cli.md` | `03-engineering/ADR-002-cli.md` | Office 文档（未做） |
| 改视频 CLI | `01-product/cli.md` 第 4.6 节 | `04-testing/video-cli.md` | Office / exe |
| 改 PDF 加密 | `ADR-003-pdf-encrypt.md` + `01-product/pdf.md` | `04-testing/pdf-encrypt.md` | 视频/Office |
| 改批量 / zip | `03-engineering/ADR-001-batch-job.md` | `app/batch.py` | GTM |
| 改 CLI | `ADR-002-cli.md` + `01-product/cli.md` | `04-testing/cli-smoke.md` | 前端样式 |
| 验收里程碑 | 对应测试册 | wrap / roadmap 状态表 | 未进范围的二三梯队 |

## 文档树

```text
docs/
├── 00-governance/     编制、Wiki、路线图评审
├── 01-product/        说明书、功能点（用户怎么用）
├── 03-engineering/    ADR、实现边界
├── 04-testing/        冒烟 / 回归清单
├── 05-project/        收工纪要、接续
└── local-tools-roadmap.md
```

## 编制人数

虚拟团队 **9 人**（9 个角色，一人一岗）。产品所有者产品所有者不在编制表内，GM 向他汇报。详见 `team-charter.md`。

## 文档总责

**PM** 对「功能模块落地时文档是否跟上」总负责。谁改代码谁先改对应分册；QA / GM 把文档当验收门禁。细则：`team-charter.md` 第 6 节。全局技能：`docs-with-features`。

开发中多次沉淀员工 Agent：全局技能 `precipitate-role-skill`；本仓写 `.cursor/skills/lt-*`。
