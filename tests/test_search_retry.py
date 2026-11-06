"""空检索结果最多重试三次，失败时保留已获取的页面。"""
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cnki_downloader.core.search import CNKISearcher
from cnki_downloader.models import Paper


@pytest.fixture
def searcher(monkeypatch):
    monkeypatch.setattr('time.sleep', Mock())
    session = Mock()
    session.post.return_value = Mock(status_code=200, text='response')
    instance = CNKISearcher(session)
    instance.parser = Mock()
    return instance


def test_empty_result_recovers_on_third_retry(searcher):
    paper = Paper(1, '论文', '/paper')
    searcher.parser.parse_paper_list.side_effect = [([], '')] * 3 + [([paper], 'valid-token')]
    assert searcher.search_by_journal('管理世界', page=108) == [paper]
    assert searcher.session.post.call_count == 4
    assert searcher.turn_page == 'valid-token'
    assert all(call.kwargs['data']['pageNum'] == '108'
               for call in searcher.session.post.call_args_list)


@pytest.mark.parametrize('server_error', [False, True])
def test_three_retries_exhausted_returns_previous_pages(searcher, server_error, capsys):
    paper = Paper(1, '论文', '/paper')
    if server_error:
        searcher.session.post.return_value.text = '数据服务获取数据异常'
    searcher.parser.parse_paper_list.side_effect = [([paper], 'token')] + [([], '')] * 4
    assert searcher.search_by_journal_all_pages('管理世界', max_pages=151) == [paper]
    assert searcher.session.post.call_count == 5
    assert [call.kwargs['data']['pageNum'] for call in searcher.session.post.call_args_list] == ['1', '2', '2', '2', '2']
    assert '重试 3 次' in capsys.readouterr().out


def test_retry_budget_resets_for_next_page(searcher):
    first, second = Paper(1, '一', '/1'), Paper(2, '二', '/2')
    searcher.parser.parse_paper_list.side_effect = [([], '')] * 3 + [([first], 'one')] + [([], '')] * 3 + [([second], 'two')]
    assert searcher.search_by_journal_all_pages('管理世界', max_pages=2) == [first, second]
    assert searcher.session.post.call_count == 8


def test_warmup_stops_only_after_retries_exhausted(searcher):
    searcher.parser.parse_paper_list.return_value = ([], '')
    assert searcher.search_by_journal_all_pages('管理世界', start_page=10, max_pages=151) == []
    assert searcher.session.post.call_count == 4
    assert all(call.kwargs['data']['pageNum'] == '1'
               for call in searcher.session.post.call_args_list)


def test_nonempty_response_does_not_retry(searcher):
    paper = Paper(1, '论文', '/paper')
    searcher.parser.parse_paper_list.return_value = ([paper], 'token')
    assert searcher.search_by_title('论文') == [paper]
    assert searcher.session.post.call_count == 1
