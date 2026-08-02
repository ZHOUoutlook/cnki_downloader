#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CNKI 论文助手 - 程序入口

使用方法:
    python main.py search --journal "财政研究" --output papers.json
    python main.py search --journal "财政研究" --pages 3 --output papers.json
    python main.py download --input papers.json --output-dir output/pdfs
"""

import argparse
import sys
from pathlib import Path

# 支持从项目目录直接运行
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from cnki_downloader import CNKIAuth, CNKISearcher
# from cnki_downloader.config import JOURNAL_PAYLOAD,TITLE_PAYLOAD
from cnki_downloader.downloaders import PDFDownloader
from cnki_downloader.utils import load_json,save_json,update_json_entry,print_paper_summary,file_exists


def cmd_search(args):
    """搜索论文命令"""
    try:
        auth = CNKIAuth()
        # 直接匿名登录
        session = auth.anonymous_login()
        # 2. 搜索
        searcher = CNKISearcher(session)

        if args.journal:
            print(f"\n📚 搜索期刊: {args.journal}")
            if args.pages and args.pages > 1:
                papers = searcher.search_by_journal_all_pages(
                    journal_name=args.journal,
                    max_pages=args.pages,
                    page_size=args.page_size
                )
            else:
                papers = searcher.search_by_journal(
                    journal_name=args.journal,
                    page=args.page,
                    page_size=args.page_size
                )
        elif args.title:
            print(f"\n📚 搜索标题: {args.title}")
            papers = searcher.search_by_title(
                title=args.title,
                page=args.page,
                page_size=args.page_size
            )
        else:
            print("\n📚 使用默认搜索条件")
            papers = searcher.search(page=args.page, page_size=args.page_size)

        # 3. 打印结果
        print_paper_summary(papers)
        # 4. 保存结果（增量更新）
        output_file = args.output or "papers.json"
        output_path = Path(output_file)
        # 确保目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if file_exists(output_file):
            # 增量更新
            existing_papers = load_json(output_file)
            existing_by_title = {p['标题']: p for p in existing_papers}
            # search 只更新检索字段，不更新详情字段
            detail_fields = {'DOI', '摘要', '关键词', '作者','作者单位', 'ISSN', 'CN', '页码', '基金', '专辑', '专题', '分类号','下载状态','本地PDF路径'}

            updated_count = 0
            added_count = 0

            for paper in papers:
                paper_dict = paper.to_dict()
                if paper.title in existing_by_title:
                    # 论文已存在，只更新检索字段，保留详情信息
                    existing = existing_by_title[paper.title]
                    idx = existing_papers.index(existing)
                    for key ,value in paper_dict.items():
                        # 跳过详情字段，保留原有值
                        if key in detail_fields:
                            continue
                        # 只更新有值的检索字段
                        if isinstance(value, list):
                            if value:
                                existing_papers[idx][key] = value
                        elif value and str(value).strip():
                            existing_papers[idx][key] = value
                    
                    updated_count += 1
                else:
                    # 新论文，添加到列表
                    existing_papers.append(paper_dict)
                    added_count += 1

            # 重新编号，按照发表时间重新编号，然后再重新排序
            existing_papers.sort(key=lambda x: x['发表时间'], reverse=True)
            for i, p in enumerate(existing_papers):
                p['序号'] = i + 1
            existing_papers.sort(key=lambda x: x['序号'])
            # 保存整个文件（有新论文或已有更新）
            save_json(existing_papers, output_file)
            if added_count > 0:
                print(f"\n📝 增量更新：新增 {added_count} 篇论文，更新 {updated_count} 篇")
            else:
                print(f"\n📝 无新增论文，更新 {updated_count} 篇已存在论文")
        else:
            save_json(papers, output_file)

        return 0

    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        return 1


def cmd_detail(args):
    """显示论文详情命令"""
    try:
        from cnki_downloader.models import Paper
        from cnki_downloader.core.parser import PaperParser
        from cnki_downloader.config import REQUEST_TIMEOUT

        # 加载论文数据
        papers_data = load_json(args.input)
        papers = [Paper.from_dict(p) for p in papers_data]

        if not papers:
            print("❌ JSON 文件中没有论文数据")
            return 1

        # 使用 IP 登录（需要完整的认证 cookies 访问详情页）
        auth = CNKIAuth()
        session = auth.ip_login()
        if not auth.is_authenticated():
            print("❌ 登录失败")
            return 1

        print(f"\n📄 共 {len(papers)} 篇论文")

        for paper in papers:
            # 如果有详情链接,且摘要存在，获取详情页补充信息
            if paper.detail_url and paper.abstract == "":
                print(f"\n🌐 正在获取详情页: {paper.detail_url}")
                try:
                    # 处理相对 URL
                    url = paper.detail_url
                    if url.startswith('//'):
                        url = 'https:' + url
                    elif url.startswith('/'):
                        url = 'https://kns.cnki.net' + url
                    elif not url.startswith('http'):
                        url = 'https://kns.cnki.net/' + url

                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.7,en;q=0.6",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "same-site",
                        "Referer": "https://kns.cnki.net/kns8s/defaultresult/index",
                    }
                    resp = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
                    resp.encoding = 'utf-8'
                    print(f"HTTP 状态码: {resp.status_code}")
                    detail_info = PaperParser.parse_paper_detail(resp.text)
                    print(f"解析到的详情信息: {detail_info}")
                    if detail_info:
                        paper.doi = detail_info.get('doi', paper.doi)
                        paper.abstract = detail_info.get('abstract', paper.abstract)
                        paper.keywords = detail_info.get('keywords', paper.keywords)
                        paper.authors = detail_info.get('authors', paper.authors)
                        paper.author_org = detail_info.get('author_org', paper.author_org)
                        paper.issn = detail_info.get('issn', paper.issn)
                        paper.cn = detail_info.get('cn', paper.cn)
                        paper.pages = detail_info.get('pages', paper.pages)
                        paper.volume = detail_info.get('volume', paper.volume)
                        paper.issue = detail_info.get('issue', paper.issue)
                        paper.page_range = detail_info.get('page_range', paper.page_range)
                        paper.fund = detail_info.get('fund', paper.fund)
                        paper.album = detail_info.get('album', paper.album)
                        paper.topic = detail_info.get('topic', paper.topic)
                        paper.cls_no = detail_info.get('cls_no', paper.cls_no)
                        print(f"✅ 详情页获取成功")
                except Exception as e:
                    print(f"⚠️ 详情页获取失败: {e}")
                # 打印详情
                print(f"\n{'='*60}")
                print(f"📄 论文详情")
                print(f"{'='*60}")
                print(f"序号: {paper.seq}")
                print(f"标题: {paper.title}")
                print(f"作者: {' | '.join([a.name for a in paper.authors])}")
                print(f"来源: {paper.source}")
                print(f"发表时间: {paper.publish_date}")
                print(f"数据库类型: {paper.db_type}")
                print(f"被引次数: {paper.citation_count}")
                print(f"下载次数: {paper.download_count}")
                print(f"详情链接: {paper.detail_url}")
                print(f"下载链接: {paper.download_url}")
                print(f"HTML阅读链接: {paper.html_url}")
                print(f"AI阅读链接: {paper.ai_read_url}")
                print(f"DOI: {paper.doi}")
                print(f"摘要: {paper.abstract}")
                print(f"关键词: {', '.join(paper.keywords)}")
                print(f"作者单位: {paper.author_org}")
                print(f"ISSN: {paper.issn}")
                print(f"CN: {paper.cn}")
                print(f"页数: {paper.pages}")
                print(f"卷号: {paper.volume}")
                print(f"期号: {paper.issue}")
                print(f"页码范围: {paper.page_range}")
                print(f"基金: {paper.fund}")
                print(f"专辑: {paper.album}")
                print(f"专题: {paper.topic}")
                print(f"分类号: {paper.cls_no}")
                print(f"下载状态: {paper.download_status}")
                if paper.local_pdf_path:
                    print(f"本地PDF路径: {paper.local_pdf_path}")
                print(f"{'='*60}")

        # 保存更新后的数据到 JSON 文件
        updated_data = [p.to_dict() for p in papers]
        save_json(updated_data, args.input)
        print(f"\n💾 已保存详情到: {args.input}")

        return 0

    except Exception as e:
        print(f"❌ 获取详情失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


def cmd_download(args):
    """下载 PDF 命令"""
    try:
        from cnki_downloader.models import Paper

        # 加载论文数据
        papers_data = load_json(args.input)
        papers = [Paper.from_dict(p) for p in papers_data]

        print(f"\n📄 加载了 {len(papers)} 篇论文")

        # 检查有详情链接的论文（用于获取下载链接）
        downloadable = [p for p in papers if p.detail_url]
        print(f"📥 有详情链接的论文: {len(downloadable)} 篇")

        if not downloadable:
            print("❌ 没有可下载的论文（缺少详情链接）")
            return 1

        # 根据输入文件名确定输出目录
        input_path = Path(args.input)
        input_stem = input_path.stem  # 获取文件名（不含扩展名），如 "财政研究"
        if args.output_dir == 'output/pdfs':
            # 如果使用默认目录，则根据文件名创建子目录
            output_dir = f"output/pdfs/{input_stem}"
        else:
            # 如果用户指定了目录，则使用用户指定的目录
            output_dir = args.output_dir

        # 登录
        auth = CNKIAuth()
        session = auth.ip_login()

        if not auth.is_authenticated():
            print("❌ 登录失败")
            return 1

        # 创建下载器，传入 auth 对象以支持重新登录
        downloader = PDFDownloader(
            session,
            output_dir=output_dir,
            json_file=args.input,
            auth=auth
        )

        if args.limit:
            papers_to_download = downloadable[:args.limit]
            print(f"🔢 限制下载前 {args.limit} 篇")
        else:
            papers_to_download = downloadable

        results = downloader.download_batch(
            papers=papers_to_download,
            delay=args.delay,
            update_json=not args.no_update_json
        )

        return 0

    except Exception as e:
        print(f"❌ 下载失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description='CNKI 论文助手 - 知网论文搜索和下载工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 搜索期刊论文
  python main.py search --journal "财政研究"

  # 搜索多页结果
  python main.py search --journal "财政研究" --pages 3

  # 下载 PDF
  python main.py download --input papers.json --output-dir output/pdfs

  # 下载前 10 篇
  python main.py download --input papers.json --limit 10
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # search 子命令
    search_parser = subparsers.add_parser('search', help='搜索论文')
    search_parser.add_argument(
        '--journal', '-j',
        help='期刊名称'
    )
    search_parser.add_argument(
        '--title', '-t',
        help='论文标题'
    )
    search_parser.add_argument(
        '--page', '-p',
        type=int,
        default=1,
        help='页码，从 1 开始 (默认: 1)'
    )
    search_parser.add_argument(
        '--pages', '-P',
        type=int,
        help='获取的最大页数'
    )
    search_parser.add_argument(
        '--page-size', '-s',
        type=int,
        default=20,
        help='每页数量 (默认: 20)'
    )
    search_parser.add_argument(
        '--output', '-o',
        default='papers.json',
        help='输出文件名 (默认: papers.json)'
    )

    # detail 子命令
    detail_parser = subparsers.add_parser('detail', help='显示论文详情')
    detail_parser.add_argument(
        '--input', '-i',
        required=True,
        help='论文 JSON 文件'
    )

    # download 子命令
    download_parser = subparsers.add_parser('download', help='下载 PDF')
    download_parser.add_argument(
        '--input', '-i',
        required=True,
        help='论文 JSON 文件'
    )
    download_parser.add_argument(
        '--output-dir', '-o',
        default='output/pdfs',
        help='下载目录 (默认: output/pdfs)'
    )
    download_parser.add_argument(
        '--limit', '-l',
        type=int,
        help='限制下载数量'
    )
    download_parser.add_argument(
        '--delay', '-d',
        type=float,
        default=10.0,
        help='每次下载之间的延迟秒数 (默认: 10.0)'
    )
    download_parser.add_argument(
        '--no-update-json',
        action='store_true',
        help='不更新 JSON 文件中的下载状态'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if args.command == 'search':
        return cmd_search(args)
    elif args.command == 'download':
        return cmd_download(args)
    elif args.command == 'detail':
        return cmd_detail(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
