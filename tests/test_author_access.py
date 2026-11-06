"""作者验证后刷新 URL 重试，重试失败时保存部分结果。"""
import json
import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cnki_downloader import main
from cnki_downloader.models import Paper, Author
from cnki_downloader.core import enrichment


def response(text, status=200):
    return Mock(text=text, status_code=status, encoding='utf-8')


@pytest.mark.parametrize('interrupt', [False, True])
def test_verification_stops_batch_and_saves_partial_codes(tmp_path, monkeypatch, interrupt):
    monkeypatch.setattr(enrichment.CNKISearcher, 'search_by_title', Mock(return_value=[]))
    path = tmp_path / 'papers.json'
    rows = [{'标题': '论文', '备注': '保留', '作者': [
        {'name': '一', 'profile_url': '/a'}, {'name': '二', 'profile_url': '/b'},
        {'name': '三', 'profile_url': '/c'}]}]
    path.write_text(json.dumps(rows), encoding='utf-8')
    session = Mock()
    session.get.side_effect = [response('<input id="au-code" value="001">'),
                               KeyboardInterrupt() if interrupt else
                               response('<title>安全验证</title><p>请拖动滑块完成验证</p>')]
    monkeypatch.setattr(main, 'CNKIAuth', Mock(return_value=Mock(anonymous_login=Mock(return_value=session))))
    assert main.cmd_author(Namespace(input=str(path), delay=0)) == 1
    saved = json.loads(path.read_text(encoding='utf-8'))
    assert saved[0]['作者'][0]['au_code'] == '001'
    assert not saved[0]['作者'][1].get('au_code')
    assert saved[0]['备注'] == '保留'
    assert session.get.call_count == 2
    session.close.assert_called_once()


@pytest.mark.parametrize('blocked', [response('<title>安全验证</title>'), response('', 403), response('', 429)])
def test_access_limit_is_not_swallowed_as_missing_code(blocked, monkeypatch):
    monkeypatch.setattr(enrichment.CNKISearcher, 'search_by_title', Mock(return_value=[]))
    from cnki_downloader.core.access import AccessBlocked
    session = Mock()
    session.get.return_value = blocked
    paper = Paper(1, '论文', '/paper', authors=[Author('作者', '/a'), Author('后续', '/b')])
    with pytest.raises(AccessBlocked):
        main.fetch_author_codes(session, paper, {}, delay=0)
    assert session.get.call_count == 1


def test_normal_page_without_code_still_continues_and_delays(monkeypatch):
    search = Mock()
    monkeypatch.setattr(enrichment.CNKISearcher, 'search_by_title', search)
    sleep = Mock()
    monkeypatch.setattr('time.sleep', sleep)
    session = Mock()
    session.get.side_effect = [response('<title>作者页面</title><script>安全验证</script>'),
                               response('<input id="au-code" value="002">')]
    paper = Paper(1, '论文', '/paper', authors=[Author('作者', '/a'), Author('其他', '/b')])
    main.fetch_author_codes(session, paper, {}, delay=5)
    assert paper.authors[0].au_code == ''
    assert paper.authors[1].au_code == '002'
    assert sleep.call_count == 2
    search.assert_not_called()


def test_existing_and_cached_codes_do_not_send_requests(monkeypatch):
    sleep = Mock()
    monkeypatch.setattr('time.sleep', sleep)
    session = Mock()
    paper = Paper(1, '论文', '/paper', authors=[Author('已有', '/known', au_code='001'),
                                              Author('缓存', '/cached')])
    main.fetch_author_codes(session, paper, {'https://kns.cnki.net/cached': '002'}, delay=3)
    assert paper.authors[1].au_code == '002'
    session.get.assert_not_called()
    sleep.assert_not_called()


@pytest.mark.parametrize('shared', [False, True])
def test_author_verification_refreshes_urls_and_retries(shared, monkeypatch):
    search = Mock(return_value=[Paper(1, '论文', '/fresh-detail', source='期刊', publish_date='2026-01-01')])
    monkeypatch.setattr(enrichment.CNKISearcher, 'search_by_title', search)
    paper = Paper(1, '论文', '/old-detail', source='期刊', publish_date='2026-01-01', authors=[
        Author('已有', '/known', au_code='001'), Author('作者', '/old'), Author('后续', '/next-old')])
    session = Mock()
    session.get.side_effect = [response('<title>安全验证</title>'), response(
        '<div class="wx-tit"><h3 class="author"><span><a href="/fresh">作者</a></span>'
        '<span><a href="/next-fresh">后续</a></span></h3></div>'),
        response('<input id="au-code" value="002">'), response('<input id="au-code" value="003">')]
    if shared:
        assert enrichment.fetch_codes(session, paper, {}, Mock()) == 0
    else:
        main.fetch_author_codes(session, paper, {}, delay=0)
    search.assert_called_once_with('论文')
    assert [c.args[0] for c in session.get.call_args_list] == [
        'https://kns.cnki.net/old', 'https://kns.cnki.net/fresh-detail',
        'https://kns.cnki.net/fresh', 'https://kns.cnki.net/next-fresh']
    assert [a.au_code for a in paper.authors] == ['001', '002', '003']


@pytest.mark.parametrize('blocked_stage', ['retry', 'detail', 'no_match'])
def test_cli_saves_refreshed_links_and_partial_codes_on_recovery_failure(tmp_path, monkeypatch, blocked_stage):
    path = tmp_path / 'papers.json'
    path.write_text(json.dumps([{'标题': '论文', '详情链接': '/old-detail', '备注': '保留', '作者': [
        {'name': '一', 'profile_url': '/a', '额外': '保留'}, {'name': '二', 'profile_url': '/b'},
        {'name': '三', 'profile_url': '/c'}]}]), encoding='utf-8')
    search = Mock(return_value=[] if blocked_stage == 'no_match' else [Paper(1, '论文', '/fresh-detail')])
    monkeypatch.setattr(enrichment.CNKISearcher, 'search_by_title', search)
    session = Mock()
    session.get.side_effect = [response('<input id="au-code" value="001">'),
        response('<title>安全验证</title>'),
        response('<title>安全验证</title>') if blocked_stage == 'detail' else response(
            '<div class="wx-tit"><h3 class="author"><span><a href="/fresh-b">二</a></span></h3></div>'),
        response('<title>安全验证</title>')]
    monkeypatch.setattr(main, 'CNKIAuth', Mock(return_value=Mock(anonymous_login=Mock(return_value=session))))
    assert main.cmd_author(Namespace(input=str(path), delay=0)) == 1
    saved = json.loads(path.read_text(encoding='utf-8'))[0]
    assert saved['作者'][0]['au_code'] == '001'
    assert saved['作者'][0]['额外'] == '保留'
    assert saved['备注'] == '保留'
    assert saved['作者'][1]['profile_url'] == ('/fresh-b' if blocked_stage == 'retry' else '/b')
    assert saved['详情链接'] == ('https://kns.cnki.net/fresh-detail' if blocked_stage == 'retry' else '/old-detail')
    assert not saved['作者'][1].get('au_code')
    search.assert_called_once_with('论文')
    assert session.get.call_count == {'retry': 4, 'detail': 3, 'no_match': 2}[blocked_stage]


@pytest.mark.parametrize('html', [
    '<div class="wx-tit"><h3 class="author"><span><a href="/x">其他作者</a></span></h3></div>',
    '<div class="wx-tit"><h3 class="author"><span><a href="/x">作者</a></span>'
    '<span><a href="/y">作者</a></span></h3></div>',
])
def test_recovery_does_not_retry_stale_or_ambiguous_author_link(html, monkeypatch):
    from cnki_downloader.core.access import AccessBlocked
    monkeypatch.setattr(enrichment.CNKISearcher, 'search_by_title',
                        Mock(return_value=[Paper(1, '论文', '/fresh-detail')]))
    paper = Paper(1, '论文', '/old-detail', authors=[Author('作者', '/old')])
    session = Mock()
    session.get.side_effect = [response('<title>安全验证</title>'), response(html)]
    with pytest.raises(AccessBlocked):
        enrichment.fetch_codes(session, paper, {}, Mock())
    assert session.get.call_count == 2
    assert paper.detail_url == '/old-detail'
    assert paper.authors[0].profile_url == '/old'


def test_cli_saves_new_urls_and_code_after_successful_recovery(tmp_path, monkeypatch):
    path = tmp_path / 'papers.json'
    path.write_text(json.dumps([{'标题': '论文', '详情链接': '/old-detail', '备注': '保留',
        '作者': [{'name': '作者', 'profile_url': '/old', '额外': '保留'}]}]), encoding='utf-8')
    monkeypatch.setattr(enrichment.CNKISearcher, 'search_by_title',
                        Mock(return_value=[Paper(1, '论文', '/fresh-detail')]))
    session = Mock()
    session.get.side_effect = [response('<title>安全验证</title>'), response(
        '<div class="wx-tit"><h3 class="author"><span><a href="/fresh">作者</a></span></h3></div>'),
        response('<input id="au-code" value="001">')]
    monkeypatch.setattr(main, 'CNKIAuth', Mock(return_value=Mock(anonymous_login=Mock(return_value=session))))
    assert main.cmd_author(Namespace(input=str(path), delay=0)) == 0
    saved = json.loads(path.read_text(encoding='utf-8'))[0]
    assert saved['详情链接'] == 'https://kns.cnki.net/fresh-detail'
    assert saved['作者'][0] == {'name': '作者', 'profile_url': '/fresh', 'au_code': '001', '额外': '保留'}
    assert saved['备注'] == '保留'
    session.close.assert_called_once()
