# 参与贡献

先能在自己电脑上跑起来，再提改动。

## 本地跑

```bat
git clone https://github.com/leoxiaoyg/local-tools.git
cd local-tools
run.bat
```

也可以 clone Gitee：`https://gitee.com/xyg-dev/local-tools.git`。

Linux / macOS 用 `./run.sh`。浏览器打开终端里打印的地址（常见是 `http://127.0.0.1:8000`，端口被占用时会试 8080、8765）。

pip 默认直连。必须走代理时再设：

```bat
set LT_PIP_PROXY=http://127.0.0.1:7897
run.bat
```

## 改代码时请带上文档

用户能感知的改动，同一次提交里改 README 或 `docs/01-product/` 里对应说明书。有架构分叉就写 `docs/03-engineering/ADR-*`。主路径变更在 `docs/04-testing/` 加一条能复测的步骤。细节见 `docs/00-governance/team-charter.md` 第 6 节。

## 自测

```bash
python tests/cli_smoke.py
```

通过会打印 `CLI_SMOKE_OK`。更完整的用例在 `docs/04-testing/v1-cli-cases.md`、`v1-web-cases.md`，脚本在 `_qa_workdir/scripts/`。

## 范围

眼下不接：便携 exe、Office 进 CLI、没证据的新小工具。有真实使用摩擦再开议题。

## 许可证

贡献默认按仓库的 AGPL-3.0 授权。
