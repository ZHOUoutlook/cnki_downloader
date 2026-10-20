# CNKI 论文助手

知网（CNKI）论文搜索、批量下载与文献管理工具，支持命令行（CLI）与桌面 GUI（开发中）两种使用方式。

## 目录

- [功能特性](#功能特性)
- [环境要求](#环境要求)
- [安装](#安装)
- [快速开始](#快速开始)
- [使用流程](#使用流程)
- [命令行参考](#命令行参考)
- [作为 Python 库使用](#作为-python-库使用)
- [API 参考](#api-参考)
- [JSON 数据格式](#json-数据格式)
- [配置说明](#配置说明)
- [常见问题](#常见问题)
- [注意事项](#注意事项)
- [项目结构](#项目结构)
- [开发指南](#开发指南)
- [功能状态](#功能状态)
- [许可证](#许可证)

---

## 功能特性

| 功能 | 说明 | 状态 |
|------|------|------|
| 搜索 | 按期刊名称或论文标题检索，支持分页、多页抓取，可指定起始页 | ✅ |
| 详情补全 | 自动访问详情页补充 DOI、摘要、关键词、作者单位、卷期页码等字段 | ✅ |
| 批量下载 | PDF/CAJ 下载，自动重试、断点跳过、过期链接自动刷新 | ✅ |
| 文献上传 | 批量上传本地文献到文献管理 API（内部工具） | ✅ |
| 免登录搜索 | 匿名会话即可搜索，下载需校园网 IP 认证 | ✅ |
| 桌面 GUI | 网络状态检测、期刊/标题搜索、结果筛选与导出 | 🔧 开发中 |

---

## 环境要求

- **Python** ≥ 3.9
- **网络**：
  - 搜索：任意网络（匿名会话即可）
  - 详情获取 / PDF 下载：知网授权 IP（如校园网）
- **依赖**：`requests`、`beautifulsoup4`（核心）；`PyQt6`（仅 GUI 需要，可选）

---

## 安装

### 方式一：从 Git 仓库安装（推荐开发者使用）

```bash
git clone https://github.com/ZHOUoutlook/cnki_downloader.git
cd cnki_downloader

# 正式安装
pip install .

# 开发模式（可编辑安装，修改代码即时生效，无需重装）
pip install -e .
```

### 方式二：安装 whl 文件（推荐普通用户使用）

从本仓库 [Releases](https://github.com/ZHOUoutlook/cnki_downloader/releases) 页面下载对应版本的 `.whl` 文件：

```bash
# 核心功能
pip install cnki_downloader-<version>-py3-none-any.whl

# 含 GUI（需 PyQt6，GUI 功能开发中）
pip install "cnki_downloader-<version>-py3-none-any.whl[gui]"
```

> `<version>` 替换为实际版本号，如 `0.1.0`。

### 可选组件

```bash
pip install ".[gui]"     # 安装 PyQt6，启用桌面 GUI（开发中）
pip install ".[dev]"     # 安装开发依赖（pytest 等）
```

### 验证安装

```bash
# 查看版本
python -c "import cnki_downloader; print(cnki_downloader.__version__)"

# 查看帮助
cnki --help
```

---

## 快速开始

安装后即可使用 `cnki` 命令完成「搜索 → 补全详情 → 下载 PDF」的完整流程：

```bash
# 第 1 步：搜索期刊论文（匿名会话，无需登录）
cnki search --journal "金融研究" --pages 5 --output output/金融研究.json

# 第 2 步：补全详情（需校园网 IP）
cnki detail --input output/金融研究.json

# 第 3 步：批量下载 PDF（需校园网 IP）
cnki download --input output/金融研究.json
```

> 💡 **提示**：搜索结果自动增量合并到输出文件，重复运行不会重复添加论文。

---

## 使用流程

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  cnki search │ ──→  │ cnki detail │ ──→  │ cnki download│
│  搜索论文    │      │ 补全详情    │      │ 下载 PDF    │
└─────────────┘      └─────────────┘      └─────────────┘
     匿名会话可              需校园网               需校园网
     生成 JSON ──→ JSON 写回详情 ──→ JSON 更新下载状态
```

---

## 命令行参考

### `cnki search` — 搜索论文

```bash
# 按期刊搜索
cnki search --journal "财政研究"

# 按标题精准搜索
cnki search --title "预分配视角下的分配体系比较与协同"

# 获取多页结果（从第 1 页到第 3 页）
cnki search --journal "财政研究" --pages 3

# 从第 2 页开始搜索，到第 5 页结束
cnki search --journal "财政研究" --start-page 2 --pages 5

# 指定每页数量（默认 20）
cnki search --journal "财政研究" --start-page 2 --page-size 50

# 指定输出文件（默认 output/papers.json）
cnki search --journal "经济学(季刊)" --output "经济学(季刊).json" --pages 50
```

**参数说明：**

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--journal, -j` | 期刊名称 | — |
| `--title, -t` | 论文标题（精准搜索） | — |
| `--pages, -P` | 结束页码（绝对页码） | — |
| `--start-page` | 起始页码 | 1 |
| `--page-size, -s` | 每页数量 | 20 |
| `--output, -o` | 输出文件名 | `papers.json` |

> **增量合并**：`search` 按「标题 + 发表时间」对输出文件做增量合并——两者都完全相同的论文视为同一篇（只更新检索字段，不新增），其余论文作为新论文追加，最后按发表时间降序重新编号。
>
> 按期刊检索时，来源不等于该期刊的记录不会写入文件。若服务端返回异常，翻页会提前结束并提示，可稍后重试补齐。

---

### `cnki detail` — 补全详情

```bash
cnki detail --input output/财政研究.json
```

**参数说明：**

| 参数 | 说明 |
|------|------|
| `--input, -i` | 论文 JSON 文件（必填） |

> 需校园网 IP 认证；仅当论文缺少摘要时才重新抓取；结果直接写回输入文件。

---

### `cnki download` — 下载 PDF

```bash
# 下载论文 PDF（默认按输入文件名分类保存到 output/pdfs/<期刊名>/）
cnki download --input output/财政研究.json

# 指定自定义输出目录（不自动分类）
cnki download --input papers.json --output-dir my_pdfs

# 限制下载数量
cnki download --input papers.json --limit 10

# 设置下载延迟（默认 10 秒）
cnki download --input papers.json --delay 20

# 只更新下载状态，不实际下载文件
cnki download --input papers.json --skip_download
```

**参数说明：**

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--input, -i` | 论文 JSON 文件（必填） | — |
| `--output-dir, -o` | 下载目录 | `output/pdfs` |
| `--limit, -l` | 限制下载数量 | 不限制 |
| `--delay, -d` | 下载间隔（秒） | 10.0 |
| `--skip_download` | 跳过下载，仅更新状态 | False |

> **自动行为**：
> - 按输入 JSON 文件名自动创建子目录（如 `output/pdfs/财政研究/`）
> - 跳过已下载的文件（断点续传）
> - 打乱下载顺序 + 随机延迟，降低被限制风险
> - 每 30 篇自动重新登录
> - 详情链接过期时自动通过标题重新搜索获取新链接
> - 部分论文只有 CAJ 格式，自动下载 `.caj`
> - 自动更新 JSON 中的 `下载状态` 与 `本地PDF路径`

---

### `cnki upload` — 上传文献（内部工具）

```bash
cnki upload --input output/papers.json
cnki upload --input output/papers.json --base-url http://localhost:8000
```

> 自动跳过缺少 `DOI`、`关键词` 或 `本地PDF路径` 的条目；上传前检查已存在的 DOI；重复文件自动跳过。

---

## 作为 Python 库使用

```python
from cnki_downloader import CNKIAuth, CNKISearcher, save_json
from cnki_downloader.downloaders import PDFDownloader

# 1. 认证（优先 IP 登录，失败则降级为匿名会话）
auth = CNKIAuth()
session = auth.ip_login()
if not auth.is_authenticated():
    session = auth.anonymous_login()  # 匿名可搜索，不可下载

# 2. 搜索
searcher = CNKISearcher(session)
papers = searcher.search_by_journal("财政研究")                          # 按期刊，第 1 页
papers = searcher.search_by_title("预分配视角下的分配体系比较与协同")    # 按标题
papers = searcher.search_by_journal_all_pages(
    "财政研究", max_pages=5, start_page=2   # 从第 2 页到第 5 页
)

# 3. 保存
save_json(papers, "papers.json")

# 4. 下载 PDF
downloader = PDFDownloader(
    session,
    output_dir="output/pdfs",
    json_file="papers.json",  # 用于更新下载状态
    auth=auth                 # 用于链接过期时重新登录
)
updated = downloader.download_batch(papers, delay=10.0)
print(f"已更新 {len(updated)} 篇论文的下载状态")
```

---

## API 参考

### CNKIAuth — 认证

| 方法 | 说明 | 网络要求 |
|------|------|----------|
| `ip_login()` | IP 登录，返回完整认证会话 | 校园网 |
| `anonymous_login()` | 匿名会话，免登录 | 任意 |
| `is_authenticated()` | 检查当前是否已认证 | — |

### CNKISearcher — 搜索

| 方法 | 说明 |
|------|------|
| `search_by_journal(name, page=1, page_size=20)` | 按期刊名称搜索单页 |
| `search_by_journal_all_pages(name, max_pages=None, page_size=20, start_page=1)` | 多页搜索（从 `start_page` 到 `max_pages`） |
| `search_by_title(title, page=1, page_size=20)` | 按论文标题精准搜索 |

### Paper — 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `seq` | int | 序号 |
| `title` | str | 标题 |
| `detail_url` | str | 详情链接 |
| `authors` | List[Author] | 作者列表 |
| `source` | str | 来源期刊 |
| `publish_date` | str | 发表时间 |
| `db_type` | str | 数据库类型 |
| `citation_count` | int | 被引次数 |
| `download_count` | int | 下载次数 |
| `download_url` | str | PDF 下载链接 |
| `html_url` | str | HTML 阅读链接 |
| `doi` | str | DOI（详情页补充） |
| `abstract` | str | 摘要（详情页补充） |
| `keywords` | List[str] | 关键词（详情页补充） |
| `author_org` | str | 作者单位（详情页补充） |
| `volume` / `issue` | str | 卷号 / 期号（详情页补充） |
| `page_range` / `pages` | str | 页码范围 / 页数（详情页补充） |
| `fund` | str | 基金（详情页补充） |
| `cls_no` | str | 分类号（详情页补充） |
| `issn` / `cn` | str | ISSN / CN 号（详情页补充） |
| `local_pdf_path` | str \| None | 本地 PDF 路径（下载后） |
| `download_status` | str | `pending` / `downloading` / `completed` / `failed` |

### Author — 作者模型

| 字段 | 说明 |
|------|------|
| `name` | 作者名 |
| `profile_url` | 作者主页链接 |
| `affiliation_indices` | 所属单位序号，如 `"1,2"` |

---

## JSON 数据格式

`search` 输出 / `detail` 写回 / `download` 更新的 JSON 文件示例：

```json
[
  {
    "序号": 1,
    "标题": "论文标题",
    "来源": "期刊名称",
    "发表时间": "2024-01-01",
    "详情链接": "https://...",
    "作者": [{"name": "张三", "affiliation_indices": "1"}],
    "作者单位": ["XX大学"],
    "DOI": "10.1234/example",
    "摘要": "摘要内容",
    "关键词": ["关键词1", "关键词2"],
    "卷号": "1",
    "期号": "1",
    "页码范围": "1-10",
    "分类号": "F830",
    "下载状态": "completed",
    "本地PDF路径": "output/pdfs/论文.pdf"
  }
]
```

---

## 配置说明

所有配置集中在 `src/cnki_downloader/config.py`：

| 配置项 | 说明 |
|--------|------|
| API 端点 | IP 登录、搜索、详情页、PDF 下载接口地址 |
| 请求头 | 默认请求头与搜索请求头（模拟浏览器） |
| 查询模板 | `JOURNAL_PAYLOAD`（期刊检索）、`TITLE_PAYLOAD`（标题检索） |
| 超时设置 | 登录 15s、请求 20s、下载 60s |
| 输出目录 | `OUTPUT_DIR = "output"` |

---

## 常见问题

### Q: 搜索报错或返回空结果？

- 确认网络连通性（匿名会话需能访问 `kns.cnki.net`）
- 期刊名称需尽量精确（支持精确匹配）
- 若服务端返回「数据服务获取数据异常」，稍后重试即可

### Q: 下载失败 / 链接过期？

- 工具会自动通过标题重新搜索获取新链接并重试
- 若持续失败，尝试重新登录：`cnki download --input papers.json`（会自动清除 cookies 重新认证）
- 确认当前 IP 在知网授权范围内

### Q: 从第 N 页开始搜索时翻页失败？

- 工具会自动从第 1 页预热获取翻页令牌（策略：1→9→13→17→...→N），无需手动干预
- 若预热过程中某页无数据，说明该期刊总页数不足，属正常现象

### Q: 如何断点续传？

- 直接重新运行 `cnki download --input papers.json`，已下载的文件会自动跳过

### Q: 部分论文下载的是 .caj 而不是 .pdf？

- 知网部分论文只提供 CAJ 格式，工具会自动下载 `.caj` 文件
- 可使用 CAJ 阅读器或 Adobe Acrobat 打开

### Q: GUI 什么时候可用？

- 当前 GUI 处于开发中（已支持搜索与导出），下载流程仍在完善
- 建议现阶段使用 CLI 方式

---

## 注意事项

1. **网络环境**：IP 登录与下载需在知网授权 IP 范围内（如校园网）；匿名会话可搜索但无法下载
2. **下载延迟**：默认 10 秒（建议 9-11 秒），请勿设得过短以避免被限制
3. **文件格式**：部分论文只有 CAJ 格式，会自动下载 `.caj`
4. **链接过期**：详情链接有时效性，过期时工具会自动刷新，无需手动处理
5. **合理使用**：请遵守知网使用条款，控制下载频率

---

## 项目结构

```
cnki_downloader/
├── pyproject.toml          # 打包配置
├── README.md               # 本文件
├── LICENSE                 # MIT 许可证
├── requirements.txt        # 核心依赖
├── requirements-gui.txt    # GUI 依赖（可选）
├── requirements-dev.txt    # 开发依赖（可选）
│
├── src/cnki_downloader/    # 可安装包
│   ├── __init__.py         # 包入口，导出公共 API
│   ├── main.py             # CLI 入口
│   ├── gui_app.py          # GUI 入口
│   ├── config.py           # 配置
│   ├── core/
│   │   ├── auth.py         # IP 登录 / 匿名会话
│   │   ├── search.py       # 期刊/标题搜索、多页翻页
│   │   ├── parser.py       # HTML 解析
│   │   └── pagination.py   # 翻页预热序列
│   ├── models/paper.py     # Paper / Author 数据类
│   ├── downloaders/        # PDF/CAJ 下载
│   ├── gui/                # PyQt6 桌面界面（开发中）
│   └── utils/              # 工具函数
│
├── tests/                  # 单元测试
└── output/                 # 运行时输出（PDF、JSON）
```

---

## 开发指南

```bash
# 1. 克隆仓库
git clone https://github.com/ZHOUoutlook/cnki_downloader.git
cd cnki_downloader

# 2. 安装开发依赖
pip install -e ".[dev]"

# 3. 运行测试
python -m pytest tests/ -v

# 4. 开发（修改 src/ 下代码即时生效，无需重装）

# 5. 构建发布包
pip install build
python -m build
# 产物在 dist/ 目录，上传到 GitHub Releases
```

---

## 功能状态

- [x] IP 登录认证
- [x] 匿名会话（免登录搜索）
- [x] 论文搜索（期刊 / 标题 / 多页）
- [x] HTML 解析（检索结果 + 详情页）
- [x] JSON 导出与增量合并
- [x] PDF / CAJ 下载
- [x] 过期链接自动刷新
- [x] 下载状态更新
- [x] 详情页信息补充
- [x] 文献批量上传
- [x] 断点续传
- [x] 防反爬（随机延迟、定期重新登录）
- [ ] GUI 桌面版（开发中）
- [ ] 并发下载

---

## 许可证

[MIT License](LICENSE)
