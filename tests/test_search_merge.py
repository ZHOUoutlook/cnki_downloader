"""搜索写入前清理历史重复，且不丢失已补全的信息。"""
import json
import sys
from argparse import Namespace
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cnki_downloader import main
from cnki_downloader.models import Paper


@pytest.mark.parametrize('reverse', [False, True])
def test_existing_duplicates_are_combined_before_adding(reverse):
    rows = [
        {'标题': '新时代·新征程·新起点', '发表时间': '2018-01-15', '下载': 784,
         '作者': [{'name': '李志軍', 'au_code': '', '备注': '保留'}],
         '摘要': '已有摘要', '下载状态': 'pending'},
        {'标题': '新时代·新征程·新起点', '发表时间': '2018-01-15', '下载': 791,
         '作者': [{'name': '李志軍', 'au_code': '000009718109'}],
         'DOI': '10.19744/j.cnki.11-1235/f.2018.01.001',
         '下载状态': 'completed', '本地PDF路径': 'output/pdfs/paper.pdf'},
    ]
    if reverse:
        rows.reverse()
    merged, stats = main.merge_search_results([Paper(1, '新论文', '/new', publish_date='2026-01-01')], rows)
    assert len(merged) == 2
    old = merged[1]
    assert old['下载'] == 791
    assert old['作者'][0]['au_code'] == '000009718109'
    assert old['作者'][0]['备注'] == '保留'
    assert old['摘要'] == '已有摘要'
    assert old['DOI'] == '10.19744/j.cnki.11-1235/f.2018.01.001'
    assert old['下载状态'] == 'completed'
    assert old['本地PDF路径'] == 'output/pdfs/paper.pdf'
    assert stats['deduplicated'] == 1
    assert stats['added'] == 1
    assert [r['序号'] for r in merged] == [1, 2]


def test_duplicates_are_cleaned_even_without_new_results():
    row = {'标题': '论文', '发表时间': '2026-01-01'}
    merged, stats = main.merge_search_results([], [row, deepcopy(row)])
    assert len(merged) == 1
    assert stats['deduplicated'] == 1


@pytest.mark.parametrize('existing_file', [False, True])
def test_search_saves_unique_results_on_first_and_later_runs(tmp_path, monkeypatch, existing_file):
    target = tmp_path / 'papers.json'
    row = {'标题': '论文', '发表时间': '2026-01-01', '来源': '管理世界'}
    if existing_file:
        target.write_text(json.dumps([row, row]), encoding='utf-8')
    searcher = Mock()
    searcher.search_by_journal.return_value = [
        Paper(1, '论文', '/first', source='管理世界', publish_date='2026-01-01'),
        Paper(2, '论文', '/fresh', source='管理世界', publish_date='2026-01-01'),
    ]
    monkeypatch.setattr(main, 'CNKIAuth', Mock())
    monkeypatch.setattr(main, 'CNKISearcher', Mock(return_value=searcher))
    args = Namespace(journal='管理世界', title=None, pages=1, page_size=20, start_page=1, output=str(target))
    assert main.cmd_search(args) == 0
    saved = json.loads(target.read_text(encoding='utf-8'))
    assert len(saved) == 1
    assert saved[0]['详情链接'] == '/fresh'


def test_distinct_dates_and_source_filter_keep_existing_behavior():
    rows = [{'标题': '论文', '发表时间': date, '来源': source}
            for date, source in [('2026-01-01', '管理世界'), ('2025-01-01', '管理世界'),
                                 ('2026-01-01', '其他期刊')]]
    merged, stats = main.merge_search_results([], rows, source='管理世界')
    assert len(merged) == 2
    assert stats['removed'] == 1
