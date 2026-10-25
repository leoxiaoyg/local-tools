# 命令行说明书

面向要在本机脚本化处理商品图 / PDF 的人。文件只在这台电脑上读和写，不经过网站、也不上传。

完整帮助以 `python -m app --help` 为准。本文说明意图、范围和常见写法。

## 1. 能做什么 / 不能做什么

| 做 | 不做（首刀） |
|---|---|
| 图片压缩、格式/尺寸转换、文字水印 | 视频转音频、视频压缩 |
| 查看 / 清除 EXIF | Word / PPT 等 Office 转换 |
| PDF 合并、压缩、按页拆分或抽页、加密 / 解密 | 便携 exe |
| CSV 去空行、去重、留列 | 透视、公式、Excel 清洗 |

和网页是同一套处理函数。网页能压成什么样，命令行就是什么样。

## 2. 准备

在项目根目录、已安装依赖的环境里：

```bash
python -m app --help
```

语言：

- `--lang zh` 或 `--lang en`（写在子命令前或后均可）
- 或环境变量 `LT_LANG=en`
- 都不写则跟操作系统语言，中文环境默认中文

## 3. 输出规则（所有会写出文件的命令）

| 情况 | 结果 |
|---|---|
| 1 个输入，不写 `-o` | 写到**当前目录**，名字由程序定（如 `photo_compressed.jpg`） |
| 1 个输入，`-o file` | 写到这个文件 |
| 多个输入，不写 `-o` 或 `-o xxx.zip` | 打成 zip |
| `-o` 指向**已经存在的目录** | 每个结果单独放进该目录 |

失败时退出码非 0，说明打在 stderr。多文件 zip 里若有失败项，行为与网页批量一致（能出的仍打进包）。

## 4. 命令一览

### 4.1 图片压缩

```bash
python -m app image compress photo.jpg
python -m app image compress photo.jpg -o small.jpg --format webp
python -m app image compress a.jpg b.png --mode target --target-kb 200 -o out.zip
python -m app image compress *.jpg -o already-existing-dir/
```

| 参数 | 含义 | 默认 |
|---|---|---|
| `--format` | `auto` / `jpeg` / `png` / `webp` | `auto`（尽量保持原格式） |
| `--mode` | `smart` 保画质，`target` 卡体积 | `smart` |
| `--target-kb` | `mode=target` 时必填，整数 KB | 无 |

### 4.2 图片转换

```bash
python -m app image convert photo.png --format jpeg
python -m app image convert photo.jpg --format webp --width 800 --height 800 --resize fit
```

| 参数 | 含义 | 默认 |
|---|---|---|
| `--format` | `jpeg` / `png` / `webp` | `jpeg` |
| `--width` / `--height` | 像素，可只填一边 | 不缩放 |
| `--resize` | `fit` 等比不超出；`fill` 裁剪到精确宽高；`exact` 拉伸 | `fit` |

`fill` / `exact` 必须同时给宽和高。

### 4.2b 文字水印

```bash
python -m app image watermark photo.jpg --text 店铺名
python -m app image watermark a.jpg b.png --text Shop --position top-left --opacity 50 -o marked.zip
```

| 参数 | 含义 | 默认 |
|---|---|---|
| `--text` | 水印文字，最多 40 字 | 必填 |
| `--position` | `bottom-right` / `bottom-left` / `top-right` / `top-left` / `center` | `bottom-right` |
| `--opacity` | 10～100 | `40` |

不做铺满、不贴图。中文需要本机中文字体。

### 4.3 EXIF

```bash
python -m app exif inspect photo.jpg
python -m app exif inspect photo.jpg --json
python -m app exif strip photo.jpg -o clean.jpg
python -m app exif strip *.jpg -o clean.zip
```

`inspect` 只读，不改文件。`--json` 方便脚本解析。`strip` 去掉拍摄时间、机型、GPS 等，画面还在。这项能力免费，不打算做成付费锁。

### 4.4 PDF

```bash
python -m app pdf merge a.pdf b.pdf -o merged.pdf
python -m app pdf compress invoice.pdf --preset strong
python -m app pdf compress *.pdf -o compressed-pdfs.zip
python -m app pdf split doc.pdf --mode pages -o pages.zip
python -m app pdf split doc.pdf --mode range --pages 1-3,5 -o part.pdf
python -m app pdf encrypt invoice.pdf --user-pw secret --no-copy -o locked.pdf
python -m app pdf decrypt locked.pdf --password secret -o opened.pdf
```

| 参数 | 含义 |
|---|---|
| `--preset` | `light` / `standard` / `strong`，默认 `standard` |
| `--mode pages` | 一页一个 PDF，打成 zip |
| `--mode range` | 必须带 `--pages`，如 `1-3,5`，输出一个 PDF |
| `--user-pw` | 打开密码（加密必填） |
| `--owner-pw` | 权限密码，默认与打开密码相同 |
| `--no-print` / `--no-modify` / `--no-copy` / `--no-annotate` | 去掉对应权限；全加则只能打开查看 |
| `--password` | 解密密码 |

合并至少 2 个文件。合并 / 压缩 / 拆分遇到已加密文件时，请先 `pdf decrypt`。密码只在本机使用，不是法律或合规认证。

### 4.5 CSV 清洗

```bash
python -m app csv clean data.csv
python -m app csv clean data.csv --keep sku,name -o clean.csv
python -m app csv clean a.csv b.csv --keep 1,3 -o cleaned-csv.zip
python -m app csv clean data.csv --no-drop-empty --no-dedupe
```

| 参数 | 含义 | 默认 |
|---|---|---|
| `--keep` | 要保留的列名或 1 起的列序号，逗号分隔（中文逗号也可） | 全留 |
| `--no-drop-empty` | 保留整行空白 | 去掉空行 |
| `--no-dedupe` | 保留完全相同的行 | 去重，保留首次出现 |

第一行当表头。输出 UTF-8 BOM（`utf-8-sig`），方便 Excel 打开。不做透视或公式。

## 5. 上限（与网页相同）

| 类型 | 上限 |
|---|---|
| 图片 | 单文件 50MB；一批最多 50 个、合计 200MB |
| PDF | 单文件 80MB；合并最多 30 个、合计 200MB |
| 按页拆分 | 最多 400 页 |
| CSV 清洗 | 单文件 20MB / 最多 20 万行；一批最多 50 个、合计 200MB |

## 6. 和非目标相关的常见误解

- 这不是 HTTP 客户端。不要对 `127.0.0.1` 发请求来当 CLI。
- 通配符在 PowerShell / bash 里可能先被 shell 展开；`cmd.exe` 里由程序自己匹配 `*`。
- 视频和 Office 请继续用网页，或等后续里程碑。

## 7. 文档索引

- 决策：`docs/03-engineering/ADR-002-cli.md`
- 冒烟：`docs/04-testing/cli-smoke.md`
- 入口：`docs/00-governance/wiki.md`
