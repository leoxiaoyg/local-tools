# ADR-001：BatchJob（批量处理 + zip）

## Status

Accepted（2026-10-24 · GM/RD）

## Context

现有工具几乎全是单文件 `UploadFile` → 内存读入 → 单文件下载。路线图 P0 需要「多选 → 逐条处理 → 打包 zip」。若每个工具各写一套批量逻辑，会复制上限校验与清理代码。

## Decision

1. 新增 `app/batch.py`（名称可微调），提供：

```text
run_batch(
  files: list[tuple[bytes, str]],
  handler: Callable[[bytes, str], Path | bytes],  # 产出单文件路径或字节
  *,
  max_files: int = 50,
  max_total_bytes: int = 200 * 1024 * 1024,
  zip_name: str = "results.zip",
  fail_mode: "continue" | "fail_fast" = "continue",
) -> BatchResult  # zip_path, ok[], errors[{name, detail}]
```

2. Web：`POST /api/batch/{tool_id}` 或各工具增加 `files: list[UploadFile]` + `batch=1`；优先**按工具扩展多文件字段**，共享 `run_batch`，避免过早做万能调度器。
3. 串行调用 handler；单条失败写入 `errors.txt`（或 JSON）一并打进 zip；整批全失败则 400/500 不返回空 zip。
4. zip 条目名 = `Path(original).name` 消毒；同名自动 `stem_2.ext`。
5. CLI 直接调同一 `handler` + `run_batch`，不经 HTTP（已落地，见 ADR-002）。

## Consequences

- 图片压缩/转换、文档转换、PDF、EXIF 可渐进接入，不必一次改全站。
- 内存仍受「全量读入」限制；大视频批量需另议流式/落盘（本 ADR 不覆盖视频 500MB×N）。
- FE 需统一批量 UI 范式（见 UX AC）。

## 修订

2026-10-26：部分成功时，zip 内 `errors.txt` 的标题和失败原因跟随调用语言。Web 用 `Accept-Language`，CLI 用 `--lang` / `LT_LANG`。条目仍是「文件名 + 制表符 + 原因」。整批全失败时不产生 zip，行为不变。

## Rollback

删除 `batch` 模块与相关路由；单文件路径保持不变。
