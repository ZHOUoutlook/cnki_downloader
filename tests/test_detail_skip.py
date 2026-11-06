"""摘要以 <正> 开头的文献跳过 detail，不检索、不请求、不改记录。"""
import sys
from argparse import Namespace
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cnki_downloader import main
from cnki_downloader.core import enrichment
from cnki_downloader.models import Paper


@pytest.mark.parametrize('abstract', ['<正>通知', '  \n<正>通知'])
def test_shared_detail_skips_marked_abstract(abstract, monkeypatch):
    paper = Paper(1, '通知', '/old-detail', abstract=abstract)
    original = deepcopy(paper)
    search = Mock()
    monkeypatch.setattr(enrichment.CNKISearcher, 'search_by_title', search)
    session = Mock()
    assert not enrichment.needs_detail(paper)
    enrichment.fetch_detail(session, paper)
    search.assert_not_called()
    session.get.assert_not_called()
    assert paper == original


def test_cli_preserves_skipped_raw_record_without_requests(monkeypatch):
    rows = [{'标题': '通知', '详情链接': '/old-detail', '摘要': '<正>通知',
             '作者': [], '备注': '保留自定义字段', '下载状态': 'completed', '本地PDF路径': 'a.pdf'}]
    original = deepcopy(rows)
    monkeypatch.setattr(main, 'load_json', Mock(return_value=rows))
    save = Mock()
    monkeypatch.setattr(main, 'save_json', save)
    session = Mock()
    monkeypatch.setattr(main, 'CNKIAuth', Mock(return_value=Mock(anonymous_login=Mock(return_value=session))))
    search = Mock()
    monkeypatch.setattr(enrichment.CNKISearcher, 'search_by_title', search)
    assert main.cmd_detail(Namespace(input='papers.json')) == 0
    search.assert_not_called()
    session.get.assert_not_called()
    assert save.call_args.args[0] == original


@pytest.mark.parametrize('abstract', ['', '正常摘要', '正文中出现<正>'])
def test_other_abstracts_still_need_detail(abstract):
    assert enrichment.needs_detail(Paper(1, '论文', '/detail', abstract=abstract))


def test_newly_fetched_marked_abstract_is_saved_for_next_run(monkeypatch):
    rows = [{'标题': '通知', '详情链接': '/detail', '摘要': '',
             '作者': [{'name': '作者', 'au_code': '001'}]}]
    monkeypatch.setattr(main, 'load_json', Mock(return_value=rows))
    save = Mock()
    monkeypatch.setattr(main, 'save_json', save)
    session = Mock()
    session.get.return_value = Mock(status_code=200, encoding='utf-8',
        text='<span id="ChDivSummary">&lt;正&gt;通知</span>')
    monkeypatch.setattr(main, 'CNKIAuth', Mock(return_value=Mock(anonymous_login=Mock(return_value=session))))
    assert main.cmd_detail(Namespace(input='papers.json')) == 0
    saved = save.call_args.args[0]
    assert saved[0]['摘要'] == '<正>通知'
    session.get.assert_called_once()
    monkeypatch.setattr(main, 'load_json', Mock(return_value=saved))
    session.get.reset_mock()
    assert main.cmd_detail(Namespace(input='papers.json')) == 0
    session.get.assert_not_called()
