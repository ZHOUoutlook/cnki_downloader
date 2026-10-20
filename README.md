# CNKI 论文助手

知网（CNKI）论文搜索、批量下载与文献管理工具，提供命令行（CLI）与 PyQt6 桌面版（GUI）两种使用方式。

## 功能特性

- **搜索**：按期刊名称或论文标题检索，支持分页、多页抓取，可指定起始页
- **详情补全**：自动访问详情页补充 DOI、摘要、关键词、作者单位、卷期页码等字段
- **批量下载**：PDF/CAJ 下载，自动重试、断点跳过、过期链接自动刷新
- **文献上传**：批量上传本地文献到文献管理 API，自动跳过缺失字段与重复文件
- **桌面 GUI**：网络状态检测、期刊/标题搜索、结果筛选与导出
- **免登录搜索**：匿名会话即可搜索，下载需校园网 IP 认证

## 项目结构

```
cnki_downloader/
├── main.py                 # CLI 入口（search / detail / download / upload）
├── gui_app.py              # GUI 入口（PyQt6 桌面版）
├── config.py               # 配置（API 端点、请求头、查询参数模板、超时）
├── __init__.py             # 包入口，导出公共 API
├── requirements.txt        # 依赖管理
├── GUI_PLAN.md             # GUI 开发规划文档
├── LICENSE                 # MIT 许可证
│
├── core/                   # 核心功能模块
│   ├── auth.py             # CNKIAuth - IP 登录 / 匿名会话认证
│   ├── search.py           # CNKISearcher - 论文搜索（期刊/标题/多页）
│   └── parser.py           # PaperParser - 检索结果与详情页 HTML 解析
│
├── models/                 # 数据模型
│   ├── __init__.py
│   └── paper.py            # Paper, Author - 论文数据类
│
├── downloaders/            # 下载器模块
│   ├── __init__.py
│   ├── base.py             # BaseDownloader - 下载器基类
│   └── pdf_downloader.py   # PDFDownloader - PDF/CAJ 下载（链接过期自动刷新）
│
├── gui/                    # PyQt6 图形界面模块
│   ├── main_window.py      # 主窗口（搜索、结果表格、下载面板）
│   ├── workers.py          # 后台线程（认证检测、搜索任务）
│   ├── result_model.py     # PaperTableModel - 结果表格模型
│   ├── styles.py           # QSS 样式
│   └── ...                 # 面板/对话框模块（部分为占位）
│
├── utils/                  # 工具函数
│   ├── __init__.py
│   └── file_utils.py       # JSON 读写、文件名清理等
│
└── output/                 # 输出目录
    ├── upload.py           # Uploader - 文献批量上传器
    ├── pdfs/               # 下载的 PDF/CAJ，按期刊分子目录
    └── *.json              # 搜索结果数据
```

## 安装

```bash
pip install -r requirements.txt
```

依赖：`requests`、`beautifulsoup4`（核心）、`PyQt6`（GUI）。

## 快速开始

```bash
# 命令行：搜索期刊论文
python main.py search --journal "财政研究"

# 从第 2 页开始搜索，直到第 5 页结束
python main.py search --journal "财政研究" --start-page 2 --pages 5

# 桌面版 GUI
python gui_app.py
```
## 使用方法（CLI）

### 搜索论文

```bash
# 按期刊搜索（匿名会话，无需登录）
python main.py search --journal "财政研究"

# 按标题精准搜索
python main.py search --title "预分配视角下的分配体系比较与协同"

# 获取多页结果
python main.py search --journal "财政研究" --pages 3

# 从第 2 页开始搜索，直到第 5 页结束
python main.py search --journal "财政研究" --start-page 2 --pages 5

# 指定起始页码与每页数量
python main.py search --journal "财政研究" --start-page 2 --page-size 50

# 指定输出文件（默认 papers.json，保存到 output/ 目录）
python main.py search --journal "经济学(季刊)" --output "经济学(季刊).json" --pages 50
```

> **增量合并说明**：`search` 会按「标题 + 发表时间」对输出文件做增量合并——**标题、发表时间两者都完全相同**的论文视为同一篇（不新增），仅刷新检索字段（详情链接、下载链接、HTML/AI 阅读链接、被引、下载次数、数据库类型、来源等），保留详情与下载字段（摘要、DOI、关键词、作者、作者单位、卷号、期号、页码范围、分类号、下载状态、本地PDF路径等，其中下载状态由 `download` 阶段维护，不会被检索结果重置）；任一不同的论文作为新论文自动追加，最后按发表时间降序重新编号（同一次运行内重复抓到的论文只追加一次）。
>
> 按期刊检索时，来源不等于该期刊的记录不会写入文件，也不会被计入"新增"。若服务端返回 `数据服务获取数据异常（feign 服务间调用异常）`，翻页会提前结束并给出提示——此时 `--pages` 并没有跑满，可稍后重试补齐。

### 获取详情

```bash
# 从 JSON 文件加载论文，补充摘要、关键词、作者单位、DOI 等详情字段
python main.py detail --input output/财政研究.json
```

> **说明**：`detail` 需要 IP 登录（校园网）访问详情页；仅当论文缺少摘要时才重新抓取；结果直接写回输入文件。

### 下载 PDF

```bash
# 下载论文 PDF（默认按输入文件名分类保存）
python main.py download --input output/财政研究.json   # → output/pdfs/财政研究/
python main.py download --input output/经济研究.json   # → output/pdfs/经济研究/

# 指定自定义目录（不自动分类）
python main.py download --input papers.json --output-dir my_pdfs

# 限制下载数量
python main.py download --input papers.json --limit 10

# 设置下载延迟（默认 10 秒）
python main.py download --input papers.json --delay 20

# 只更新下载状态，不实际下载文件
python main.py download --input papers.json --skip_download
```

> **下载说明**：
> - 使用默认 `output/pdfs` 目录时，会按输入 JSON 文件名自动创建子目录，便于按期刊分类管理
> - 自动跳过已下载的文件（断点续传）
> - 打乱下载顺序，并使用 50%~100% 的随机延迟，降低被反爬限制的风险
> - 每下载 30 篇自动清除 cookies 并重新登录
> - 详情链接过期时会通过标题重新搜索获取新链接，并更新 JSON 中的 `详情链接`
> - 部分论文只有 CAJ 格式，会自动下载 `.caj` 文件
> - 自动更新 JSON 中的 `下载状态` 与 `本地PDF路径`

### 上传文献

```bash
# 批量上传文献（JSON 中的多篇文献）
python main.py upload --input output/papers.json

# 指定文献管理 API 地址
python main.py upload --input output/papers.json --base-url http://localhost:8000
```

> **上传规则**：自动跳过缺少 `DOI`、`关键词` 或 `本地PDF路径` 的条目；上传前调用 `check_dois` 接口统计已存在的文献；重复文件由上传接口识别并跳过。

**JSON 示例**（与 `download` / `detail` 生成的字段一致）：

```json
[
  {
    "标题": "论文标题",
    "DOI": "10.1234/example",
    "本地PDF路径": "output/pdfs/论文.pdf",
    "作者": [{"name": "张三", "affiliation_indices": "1"}],
    "作者单位": ["XX大学"],
    "期刊": "期刊名称",
    "发表时间": "2024-01-01",
    "卷号": "1",
    "期号": "1",
    "页码": "1-10",
    "摘要": "摘要内容",
    "关键词": ["关键词1", "关键词2"],
    "专辑": "专辑",
    "专题": "专题",
    "分类号": "分类"
  }
]
```
## 使用方法（GUI）

```bash
python gui_app.py
```

- **网络状态检测**：启动后自动检测，校园网 IP 认证成功后可搜索和下载；失败时自动降级为匿名会话，可搜索（下载需连接校园网）
- **搜索**：支持期刊名 / 标题检索，可设置起始页、每页数量并获取多页结果，实时显示搜索进度
- **结果表格**：展示序号、标题、作者、来源、时间、被引、下载，支持关键词筛选、分页与清空
- **导出 JSON**：将搜索结果导出为 JSON 文件
- **下载面板**：已提供界面（导入 JSON、开始下载、停止、进度条与统计），下载流程当前以 CLI 为主，详细规划见 `GUI_PLAN.md`

## 作为库使用

```python
from cnki_downloader import CNKIAuth, CNKISearcher, save_json
from cnki_downloader.downloaders import PDFDownloader

# 认证：优先 IP 登录（校园网），否则匿名会话
auth = CNKIAuth()
session = auth.ip_login()
if not auth.is_authenticated():
    session = auth.anonymous_login()  # 匿名会话可搜索，不可下载

# 搜索
searcher = CNKISearcher(session)
papers = searcher.search_by_journal("财政研究")                       # 按期刊
papers = searcher.search_by_title("预分配视角下的分配体系比较与协同")   # 按标题
papers = searcher.search_by_journal_all_pages("财政研究", max_pages=5)  # 多页
papers = searcher.search_by_journal_all_pages("财政研究", max_pages=5, start_page=2)  # 从第 2 页开始

# 保存
save_json(papers, "papers.json")

# 获取详情（补充摘要、关键词、作者单位等）
from cnki_downloader.core.parser import PaperParser
for paper in papers:
    if paper.detail_url and paper.abstract == "":
        detail_info = PaperParser.parse_paper_detail(detail_html)
        if detail_info:
            paper.doi = detail_info.get('doi', paper.doi)
            paper.abstract = detail_info.get('abstract', paper.abstract)
            paper.keywords = detail_info.get('keywords', paper.keywords)
            paper.author_org = detail_info.get('author_org', paper.author_org)

# 下载 PDF（支持自动刷新过期链接）
downloader = PDFDownloader(
    session,
    output_dir="output/pdfs",
    json_file="papers.json",  # 用于更新下载状态
    auth=auth                # 用于重新登录
)
updated = downloader.download_batch(papers, delay=10.0)
print(f"已更新 {len(updated)} 篇论文的下载状态")
```

## 核心功能

### 认证

| 方法 | 说明 |
| --- | --- |
| `CNKIAuth().ip_login()` | IP 登录（需校园网授权 IP），返回完整认证会话 |
| `CNKIAuth().anonymous_login()` | 匿名会话，免登录搜索 |
| `auth.is_authenticated()` | 检查当前是否已认证 |

### 搜索

| 方法 | 说明 |
| --- | --- |
| `search_by_journal(name, page, page_size)` | 按期刊名称搜索论文 |
| `search_by_journal_all_pages(name, max_pages, page_size, start_page=1)` | 从 `start_page` 开始搜索期刊论文，直到 `max_pages` 结束（默认从第 1 页开始） |
| `search_by_title(title, page, page_size)` | 按论文标题精准搜索 |
### 数据字段

#### Paper 模型字段

| 字段 | 说明 |
| --- | --- |
| `seq` | 序号 |
| `title` | 标题 |
| `detail_url` | 详情链接 |
| `authors` | 作者列表 `List[Author]` |
| `source` | 来源期刊 |
| `publish_date` | 发表时间 |
| `db_type` | 数据库类型 |
| `citation_count` | 被引次数 |
| `download_count` | 下载次数 |
| `download_url` | PDF 下载链接 |
| `html_url` | HTML 阅读链接 |
| `ai_read_url` | CNKI AI 阅读链接 |
| `doi` | DOI |
| `abstract` | 摘要 |
| `keywords` | 关键词列表 |
| `author_org` | 作者单位（详情页补充） |
| `volume` | 卷号 |
| `issue` | 期号 |
| `page_range` | 页码范围 |
| `pages` | 页数 |
| `fund` | 基金 |
| `album` | 专辑 |
| `topic` | 专题 |
| `cls_no` | 分类号 |
| `issn` | ISSN |
| `cn` | CN 号 |
| `local_pdf_path` | 本地 PDF 路径（下载后） |
| `download_status` | 下载状态：`pending` / `downloading` / `completed` / `failed` |

#### Author 模型字段

| 字段 | 说明 |
| --- | --- |
| `name` | 作者名 |
| `profile_url` | 作者主页链接 |
| `affiliation_indices` | 作者所属单位的序号，如 `"1,2"` |

## 配置说明

`config.py` 集中管理：

- **API 端点**：IP 登录、搜索、详情页、PDF 下载接口地址
- **请求头**：默认请求头与搜索请求头
- **查询模板**：`JOURNAL_PAYLOAD`（期刊检索）、`TITLE_PAYLOAD`（标题检索）等
- **超时设置**：登录、请求、下载超时时间
- **输出目录**：`OUTPUT_DIR = "output"`

## 功能状态

- [X] IP 登录认证
- [X] 匿名会话（免登录搜索）
- [X] 论文搜索（期刊 / 标题 / 多页）
- [X] HTML 解析（检索结果 + 详情页）
- [X] JSON 导出与增量合并
- [X] PDF / CAJ 下载
- [X] 过期链接自动刷新（重新搜索 + 重新登录）
- [X] 下载状态更新
- [X] 详情页信息补充
- [X] 文献批量上传
- [X] 断点续传（跳过已下载文件）
- [X] 防反爬（打乱顺序、随机延迟、定期重新登录）
- [X] GUI 桌面版（网络检测 / 搜索 / 导出）
- [ ] GUI 下载流程
- [ ] 并发下载

## 注意事项

1. **网络环境**：IP 登录与下载需要在知网授权 IP 范围内（如校园网）；匿名会话可以搜索，但无法下载
2. **下载延迟**：默认 10 秒（建议 9-11 秒），避免请求过于频繁被限制
3. **文件格式**：部分论文只提供 CAJ 格式，下载器会自动下载 `.caj` 文件
4. **链接过期**：详情链接过期时，下载器会自动通过论文标题重新搜索获取新链接，并更新 JSON 中的 `详情链接` 字段