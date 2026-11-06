# GitHub 发布检查单

以本仓 `local-tools` 为准。不要用 `knowledge-base/local-tools-release-prep` 那套 MIT 草稿覆盖这里。

## 发布前

- [ ] 许可证仍是根目录 `LICENSE`（AGPL-3.0），没有被改成 MIT
- [ ] README 里的启动命令是 `run.bat` / `run.sh` 或 `uvicorn app.main:app`，没有 `python main.py`
- [ ] 功能表和仓库里实际工具一致（含 EXIF、水印、PDF、CSV 清洗、CLI 等）
- [ ] 全文搜不到个人昵称；赞助区没有 `your-handle` 一类占位链接
- [ ] `python tests/cli_smoke.py` 能打出 `CLI_SMOKE_OK`
- [ ] 工作区干净，该提交的都已提交

## 建仓与推送

1. 在 GitHub 用账号（计划：`leoxiaoyg`）新建公开仓库 `local-tools`，不要勾选自动加 README/LICENSE（本地已有）。
2. 本机加远程并推送：

```bash
git remote add github https://github.com/leoxiaoyg/local-tools.git
git push -u github main
```

Gitee 的 `origin` 可以继续留着，两处各自 push。

3. 浏览器打开 GitHub 仓库，核对 README 渲染、LICENSE 显示为 AGPL-3.0。
4. 可选：About 里加 topics，例如 `local-first`、`fastapi`、`privacy`、`ffmpeg`、`offline`。
5. 可选：打 `v0.1.0` Release，说明「源码自跑，无安装包」。

## 发布后

- [ ] 爱发电 / GitHub Sponsors 真实链接有了，再改 README「赞助」一节
- [ ] 作品集或个人页链到这个仓库
- [ ] `knowledge-base/local-tools-release-prep` 标成废弃或删掉，避免以后又拿去发

## 不要做

- 不要把许可证改成 MIT（PyMuPDF 是 AGPL）
- 不要用 orphan 空历史丢掉已有提交，除非另有明确要求
- 不要把公司邮箱、真实业务文件、知识库商业文档推进公开仓
