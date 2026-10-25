# ADR-003：PDF 加密用 AES-256，与 Web / CLI 共用 handler

## Status

Accepted（2026-10-25 · RD / SEC / GM）

## Context

合同与发票需要本机加锁。PyMuPDF 已在合并 / 压缩 / 拆分路径中。若另选加密库，会多依赖、两套打开逻辑。产品不得把「加了密码」说成合规认证。

## Decision

1. 只用 PyMuPDF：`PDF_ENCRYPT_AES_256`。打开密码必填；权限密码默认同打开密码。
2. 权限项：`print` / `modify` / `copy` / `annotate`。无障碍阅读始终打开。全不选则只能打开查看。
3. `encrypt_pdf` / `decrypt_pdf` 是唯一实现。Web `POST /api/pdf/encrypt|decrypt`（及 batch）和 CLI `pdf encrypt|decrypt` 都调它们。
4. 合并 / 压缩 / 拆分遇到已加密文件：未给密码则拒绝，提示先解密。不在这些路径里再开一套口令参数。
5. 对外话术：有助于控制谁能打开；密码只在本机；**不是法律或合规认证**。禁止「跨境合规」口径。

## 非目标

- 证书、DRM、时间戳、水印与加密捆绑
- 云端存密码或找回密码
- 便携 exe

## Consequences

- 不新增依赖。读者软件对权限位的执行程度不一，页面必须写明这一点。
- 已加密文件要先走解密，再合并或压缩。

## Rollback

删除 `encrypt_pdf` / `decrypt_pdf`、对应路由与 CLI 子命令；合并压缩拆分不受影响。
