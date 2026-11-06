"""详情直接使用现有链接更新作者 URL；重新检索仅用于作者验证恢复。"""
import json
import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cnki_downloader import main
from cnki_downloader.core import enrichment
from cnki_downloader.core.parser import PaperParser
from cnki_downloader.models import Paper, Author

HTML = '<div class="wx-tit"><h3 class="author"><span><a href="/author-new">作者</a></span></h3></div>'


def test_author_without_affiliation_block_is_parsed():
    info = PaperParser.parse_paper_detail(HTML)
    assert info['authors'][0].profile_url == '/author-new'


def test_cli_uses_existing_detail_and_saves_fresh_author_url(tmp_path, monkeypatch):
    path = tmp_path / 'papers.json'
    path.write_text(json.dumps([{'标题': '论文', '来源': '期刊', '发表时间': '2026-01-01',
        '详情链接': '/old-detail', '摘要': '摘要', '卷号': '2026', '期号': '1',
        '作者': [{'name': '作者', 'profile_url': '/author-old', 'au_code': ''}]}]), encoding='utf-8')
    search = Mock(return_value=[Paper(1, '论文', '/fresh-detail', source='期刊', publish_date='2026-01-01')])
    monkeypatch.setattr(enrichment.CNKISearcher, 'search_by_title', search)
    session = Mock()
    session.get.return_value = Mock(text=HTML, status_code=200, encoding='utf-8')
    monkeypatch.setattr(main, 'CNKIAuth', Mock(return_value=Mock(anonymous_login=Mock(return_value=session))))
    assert main.cmd_detail(Namespace(input=str(path))) == 0
    search.assert_not_called()
    assert session.get.call_args.args[0] == 'https://kns.cnki.net/old-detail'
    saved = json.loads(path.read_text(encoding='utf-8'))[0]
    assert saved['详情链接'] == '/old-detail'
    assert saved['作者'][0]['profile_url'] == '/author-new'
    assert saved['摘要'] == '摘要'


@pytest.mark.parametrize('candidates', [[], [Paper(1, '论文', '/wrong', source='其他')],
    [Paper(1, '论文', '/a', source='期刊'), Paper(2, '论文', '/b', source='期刊')]])
def test_no_unique_match_keeps_existing_links(candidates, monkeypatch):
    monkeypatch.setattr(enrichment.CNKISearcher, 'search_by_title', Mock(return_value=candidates))
    paper = Paper(1, '论文', '/old-detail', source='期刊', authors=[Author('作者', '/old-author')])
    session = Mock()
    with pytest.raises(ValueError, match='唯一匹配'):
        enrichment.refresh_detail_url(session, paper)
    assert paper.detail_url == '/old-detail'
    assert paper.authors[0].profile_url == '/old-author'
    session.get.assert_not_called()


def test_known_codes_do_not_trigger_search_and_survive_parsing(monkeypatch):
    search = Mock()
    monkeypatch.setattr(enrichment.CNKISearcher, 'search_by_title', search)
    paper = Paper(1, '论文', '/detail', authors=[Author('作者', '/old', au_code='001')])
    session = Mock()
    session.get.return_value = Mock(text=HTML, status_code=200, encoding='utf-8')
    enrichment.fetch_detail(session, paper)
    search.assert_not_called()
    assert paper.authors[0].au_code == '001'
    assert paper.authors[0].profile_url == '/author-new'


@pytest.mark.parametrize('authors', [[], [Author('作者', '/old')]])
def test_shared_detail_updates_author_url_without_search(authors, monkeypatch):
    search = Mock()
    monkeypatch.setattr(enrichment.CNKISearcher, 'search_by_title', search)
    paper = Paper(1, '论文', '/detail', authors=authors)
    session = Mock()
    session.get.return_value = Mock(text=HTML, status_code=200, encoding='utf-8')
    enrichment.fetch_detail(session, paper)
    search.assert_not_called()
    assert session.get.call_args.args[0] == 'https://kns.cnki.net/detail'
    assert paper.detail_url == '/detail'
    assert paper.authors[0].profile_url == '/author-new'
