"""验证页应停止请求并保留部分取得的编码，不能误报成编码缺失。"""
import json
import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cnki_downloader import main
from cnki_downloader.models import Paper, Author


def response(text, status=200):
    return Mock(text=text, status_code=status, encoding='utf-8')


@pytest.mark.parametrize('interrupt', [False, True])
def test_verification_stops_batch_and_saves_partial_codes(tmp_path, monkeypatch, interrupt):
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
def test_access_limit_is_not_swallowed_as_missing_code(blocked):
    from cnki_downloader.core.access import AccessBlocked
    session = Mock()
    session.get.return_value = blocked
    paper = Paper(1, '论文', '/paper', authors=[Author('作者', '/a'), Author('后续', '/b')])
    with pytest.raises(AccessBlocked):
        main.fetch_author_codes(session, paper, {}, delay=0)
    assert session.get.call_count == 1


def test_normal_page_without_code_still_continues_and_delays(monkeypatch):
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
