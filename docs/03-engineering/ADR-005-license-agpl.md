# ADR-005 · 项目许可证选用 AGPL-3.0

- 状态：已采纳
- 日期：2026-10-30

## 背景

开源前需要明确许可证。PDF 相关能力依赖 PyMuPDF，该库本身是 AGPL-3.0。

## 决定

仓库整体采用 **GNU Affero General Public License v3.0（AGPL-3.0）**。

## 原因

1. 与 PyMuPDF 的许可证一致，少一层「自己写 MIT、依赖却是 AGPL」的含糊。
2. 当前定位是本机工具、源码公开、不卖安装包；AGPL 不挡自用和 clone。
3. 以后若换成更宽松的 PDF 库，再评估是否把本仓库改成 MIT/Apache。

## 后果

- 根目录放 `LICENSE`（AGPL-3.0 全文）。
- README 写明许可证，并点出 PDF 能力依赖 PyMuPDF。
- 基于本仓库做闭源发行会受 AGPL 约束；接受这一点。
