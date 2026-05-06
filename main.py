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

from cnki_downloader import CNKIAuth, CNKISearcher, save_json, print_paper_summary
from cnki_downloader.config import JOURNAL_PAYLOAD,TITLE_PAYLOAD
from cnki_downloader.downloaders import PDFDownloader


def cmd_search(args):
    """搜索论文命令"""
    try:
        # 1. 登录
        auth = CNKIAuth()
        session = auth.ip_login()

        if not auth.is_authenticated():
            print("❌ 登录失败")
            return 1

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

        # 4. 保存结果
        output_file = args.output or "papers.json"
        save_json(papers, output_file)

        return 0

    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        return 1


def cmd_download(args):
    """下载 PDF 命令"""
    try:
        from cnki_downloader.utils import load_json
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

    return 0


if __name__ == "__main__":
    sys.exit(main())
