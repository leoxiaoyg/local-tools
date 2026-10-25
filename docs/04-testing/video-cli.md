# 视频 CLI 冒烟（P0）

网页视频功能不在这刀改动里。命令行在项目根目录跑 `python tests/cli_smoke.py`，其中第 18–21 条覆盖本刀。短片约 1 秒，不要用大文件当主路径。

| ID | 步骤 | 期望 | 结果 |
|---|---|---|---|
| P0-1 | `video audio 片段.mp4 --format mp3 -o out.mp3` | 产出 mp3 | |
| P0-2 | `video compress a.mp4 --crf 28 --resolution 480 -o out.mp4` | 产出 mp4 | |
| P0-3 | `video audio nope.txt`（`--lang en`） | 退出非 0，提示不支持的视频格式 | |
| P0-4 | `video compress a.mp4 --crf 40` | 退出非 0，CRF 必须在 18～28 | |

## 不测（本刀）

Office 转换、exe、画质逐帧对比、网页视频页面回归（页面未改）。
