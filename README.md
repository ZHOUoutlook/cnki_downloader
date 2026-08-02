# CNKI 论文助手

知网论文搜索和下载工具

## 项目结构
```
cnki_downloader/
├── main.py                 # 程序入口，CLI 参数解析
├── config.py               # 配置文件（API 地址、请求头、查询参数模板）
├── __init__.py             # 包入口，导出公共 API
├── README.md               # 项目文档
├── requirements.txt        # 依赖管理
│
├── core/                   # 核心功能模块
│   ├── __init__.py
│   ├── auth.py             # CNKIAuth - IP 登录认证
│   ├── search.py           # CNKISearcher - 论文搜索（期刊/标题）
│   └── parser.py           # PaperParser - HTML 解析
│
├── models/                 # 数据模型
│   ├── __init__.py
│   └── paper.py            # Paper, Author - 论文数据类
│
├── downloaders/            # 下载器模块
│   ├── __init__.py
│   ├── base.py             # BaseDownloader - 下载器基类
│   └── pdf_downloader.py   # PDFDownloader - PDF 下载器（支持链接过期自动刷新）
│
├── utils/                  # 工具函数
│   ├── __init__.py
│   └── file_utils.py       # 文件操作工具
│
└── output/                 # 输出目录（PDF、JSON 等）
```

## 安装

```bash
pip install -r requirements.txt
```

## 使用方法

### 搜索论文

```bash
# 搜索指定期刊论文
python main.py search --journal "财政研究"

# 搜索指定标题论文（精准匹配）
python main.py search --title "预分配视角下的分配体系比较与协同"

# 搜索并保存到指定文件
python main.py search --journal "财政研究" --output papers.json

# 搜索多页结果
python main.py search --journal "财政研究" --pages 3

# 指定每页数量
python main.py search --journal "财政研究" --page-size 50

python main.py search --journal "经济学(季刊)" --output "经济学(季刊).json" --pages 50

```

### 获取详情

```bash
# 从 JSON 文件加载论文并获取详情页补充信息（摘要、关键词、作者单位等）
python main.py detail --input output/财政研究.json

# 指定输出文件（保存更新后的数据）
python main.py detail --input output/财政研究.json --output output/财政研究_详情.json

# 限制处理数量
python main.py detail --input output/财政研究.json --limit 10
```

> **说明**：detail 阶段会访问每篇论文的详情页面，补充搜索结果中缺失的信息，如 DOI、摘要、关键词、作者单位、ISSN、CN 号、页码、卷号、期号、页码范围、基金、专辑、专题、分类号等。

### 下载 PDF

```bash
# 下载论文 PDF（使用默认目录）
# PDF 会自动保存到 output/pdfs/<文件名>/ 目录
# 例如：--input output/财政研究.json → 保存到 output/pdfs/财政研究/
python main.py download --input output/财政研究.json

# 使用默认目录时，不同期刊的论文会自动分类存储
python main.py download --input output/经济研究.json  # → output/pdfs/经济研究/
python main.py download --input output/管理世界.json  # → output/pdfs/管理世界/

# 指定自定义目录（不使用自动分类）
python main.py download --input papers.json --output-dir my_pdfs

# 限制下载数量
python main.py download --input papers.json --limit 10

# 设置下载延迟（避免请求过快）
python main.py download --input papers.json --delay 20

# 不更新 JSON 文件中的下载状态
python main.py download --input papers.json --no-update-json
```

> **自动目录分类说明**：当使用默认的 `output/pdfs` 目录时，系统会根据输入 JSON 文件名自动创建子目录。例如下载 `财政研究.json` 中的论文，PDF 会保存到 `output/pdfs/财政研究/` 目录，便于按期刊分类管理。

## 作为库使用

```python
from cnki_downloader import CNKIAuth, CNKISearcher, save_json
from cnki_downloader.downloaders import PDFDownloader

# 登录
auth = CNKIAuth()
session = auth.ip_login()

# 搜索
searcher = CNKISearcher(session)

# 按期刊搜索
papers = searcher.search_by_journal("财政研究")

# 按标题精准搜索
papers = searcher.search_by_title("预分配视角下的分配体系比较与协同")

# 搜索所有页面
papers = searcher.search_by_journal_all_pages("财政研究", max_pages=5)

# 保存
save_json(papers, "papers.json")

# 获取详情（补充摘要、关键词、作者单位等信息）
from cnki_downloader.core.parser import PaperParser
for paper in papers:
    if paper.detail_url and paper.abstract == "":
        # 访问详情页并解析
        detail_info = PaperParser.parse_paper_detail(detail_html)
        if detail_info:
            paper.doi = detail_info.get('doi', paper.doi)
            paper.abstract = detail_info.get('abstract', paper.abstract)
            paper.keywords = detail_info.get('keywords', paper.keywords)
            paper.author_org = detail_info.get('author_org', paper.author_org)
            # ... 其他字段

# 下载 PDF（支持自动刷新过期链接）
downloader = PDFDownloader(
    session,
    output_dir="output/pdfs",
    json_file="papers.json",  # 用于更新下载状态
    auth=auth  # 用于重新登录
)
results = downloader.download_batch(papers, delay=10.0)
print(f"下载完成: 成功 {results['success']}, 失败 {results['failed']}")
```

## 核心功能

### 搜索功能

| 方法 | 说明 |
|------|------|
| `search_by_journal(name)` | 按期刊名称搜索论文 |
| `search_by_journal_all_pages(name, max_pages)` | 搜索期刊所有页面论文 |
| `search_by_title(title)` | 按论文标题精准搜索 |

### 数据字段

#### Paper 模型字段

| 字段 | 说明 |
|------|------|
| `seq` | 序号 |
| `title` | 标题 |
| `detail_url` | 详情链接 |
| `authors` | 作者列表 `List[Author]` |
| `source` | 来源期刊 |
| `publish_date` | 发表时间 |
| `db_type` | 数据库类型 |
| `citation_count` | 被引次数 |
| `download_count` | 下载次数 |
| `download_url` | PDF下载链接 |
| `html_url` | HTML阅读链接 |
| `ai_read_url` | AI阅读链接 |
| `doi` | DOI |
| `abstract` | 摘要 |
| `keywords` | 关键词列表 |
| `author_org` | 作者单位列表 `List[str]` |
| `volume` | 卷号 |
| `issue` | 期号 |
| `page_range` | 页码范围 |
| `pages` | 页数 |
| `fund` | 基金 |
| `album` | 专辑 |
| `topic` | 专题 |
| `cls_no` | 分类号 |
| `issn` | ISSN |
| `cn` | CN号 |

#### Author 模型字段

| 字段 | 说明 |
|------|------|
| `name` | 作者名 |
| `profile_url` | 作者主页链接 |
| `affiliation_indices` | 作者所属单位的序号，如 "1,2" |

### 下载功能

- **自动重试**：下载失败时自动重试
- **链接过期刷新**：当详情链接过期触发验证机制时，自动通过标题重新搜索获取新的详情链接
- **断点续传**：跳过已下载的文件
- **状态更新**：自动更新 JSON 文件中的下载状态和刷新后的详情链接
- **文件命名**：下载文件以 `论文标题_发表日期` 格式命名

## 配置说明

`config.py` 中包含两种搜索模板：

```python
# 基于期刊来源检索
JOURNAL_PAYLOAD = {...}

# 基于文献标题精准检索
TITLE_PAYLOAD = {...}
```

## 功能状态

- [x] IP 登录认证
- [x] 论文搜索（期刊/标题）
- [x] HTML 解析
- [x] JSON 导出
- [x] PDF 下载
- [x] 过期链接自动刷新
- [x] 下载状态更新
- [x] 详情页信息补充（卷号、期号、页码范围、作者单位等）
- [ ] 断点续传
- [ ] 并发下载

## 注意事项

1. **IP 登录**：需要在知网授权的 IP 范围内（如校园网）才能使用 IP 登录功能
2. **下载延迟**：建议设置 9-11 秒的延迟，避免请求过于频繁被限制
3. **文件格式**：部分论文可能只提供 CAJ 格式，下载器会自动下载 CAJ 文件
4. **链接过期**：当详情链接过期时，下载器会自动通过论文标题重新搜索获取新的链接，并更新 JSON 文件中的 `详情链接` 字段
