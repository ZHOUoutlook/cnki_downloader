"""GUI 的详情补全和工作文件保存不依赖 Qt 或真实网络。"""
import json
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cnki_downloader.models import Paper, Author
from cnki_downloader.core.enrichment import fetch_detail, needs_detail, fetch_codes
from cnki_downloader.gui.workspace import Workspace


def test_missing_code_refreshes_author_link_and_keeps_known_codes(monkeypatch):
    monkeypatch.setattr('cnki_downloader.core.enrichment.CNKISearcher.search_by_title',
                        Mock(return_value=[Paper(1, '论文', '/fresh-detail')]))
    paper = Paper(1, '论文', '/paper', abstract='摘要', volume='1', issue='2',
                  authors=[Author('张三', '/old'), Author('李四', '/known', au_code='002')])
    session = Mock()
    session.get.return_value.text = '''<div class="wx-tit"><h3 class="author">
      <span><a href="/fresh">张三</a></span><span><a href="/known-new">李四</a></span>
      </h3><h3 class="author"><span>大学</span></h3></div>'''
    session.get.return_value.encoding = 'utf-8'
    assert needs_detail(paper)
    fetch_detail(session, paper)
    assert paper.authors[0].profile_url == '/fresh'
    assert paper.authors[1].au_code == '002'
    paper.authors[0].au_code = '001'
    assert not needs_detail(paper)


def test_author_failure_continues_and_uses_fresh_link():
    session = Mock()
    resp = Mock(text='<input id="au-code" value="001">', encoding='utf-8')
    session.get.side_effect = [TimeoutError('超时'), resp]
    paper = Paper(1, '论文', '/paper', authors=[Author('失败', '/bad'), Author('成功', '/fresh')])
    logs = []
    fetch_codes(session, paper, {}, logs.append)
    assert paper.authors[0].au_code == ''
    assert paper.authors[1].au_code == '001'
    assert session.get.call_args.args[0] == 'https://kns.cnki.net/fresh'
    assert logs


def test_workspace_atomic_save_preserves_custom_fields(tmp_path):
    path = tmp_path / 'papers.json'
    path.write_text(json.dumps([{'标题': '论文', '备注': '保留', '作者': [
        {'name': '张三', 'profile_url': '/old', '备注': '作者备注'}]}]), encoding='utf-8')
    store = Workspace.load(path)
    store.papers[0].authors[0].profile_url = '/fresh'
    store.papers[0].authors[0].au_code = '001'
    store.save()
    saved = json.loads(path.read_text(encoding='utf-8'))
    assert saved[0]['备注'] == '保留'
    assert saved[0]['作者'][0]['备注'] == '作者备注'
    assert saved[0]['作者'][0]['profile_url'] == '/fresh'
    assert saved[0]['作者'][0]['au_code'] == '001'


@pytest.mark.parametrize('data', [{}, [1], [{'作者': ['张三']}], [{'作者': None}]])
def test_workspace_rejects_invalid_json_records(tmp_path, data):
    path = tmp_path / 'bad.json'
    path.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError):
        Workspace.load(path)


def test_workspace_failed_replace_preserves_original_file(tmp_path, monkeypatch):
    from cnki_downloader.gui import workspace
    path = tmp_path / 'original.json'
    original = '[{"标题": "旧论文"}]'
    path.write_text(original, encoding='utf-8')
    store = Workspace.load(path)
    store.papers[0].title = '新论文'
    monkeypatch.setattr(workspace.os, 'replace', Mock(side_effect=PermissionError('文件占用')))
    with pytest.raises(PermissionError):
        store.save()
    assert path.read_text(encoding='utf-8') == original
    assert list(tmp_path.glob('*.tmp')) == []


def test_workspace_search_merge_preserves_enrichment_and_raw_fields(tmp_path):
    path = tmp_path / 'merge.json'
    path.write_text(json.dumps([{'标题': '论文', '发表时间': '2026-01-01', '备注': '保留',
        '摘要': '摘要', '作者': [{'name': '作者', 'au_code': '001'}]}]), encoding='utf-8')
    store = Workspace.load(path)
    assert store.merge([Paper(1, '论文', '/fresh', publish_date='2026-01-01', citation_count=2)]) == 0
    store.save()
    assert store.papers[0].authors[0].au_code == '001'
    assert store.papers[0].abstract == '摘要'
    assert store.papers[0].detail_url == '/fresh'
    assert json.loads(path.read_text(encoding='utf-8'))[0]['备注'] == '保留'


def test_workspace_normalizes_nullable_fields_before_gui_reads(tmp_path):
    path = tmp_path / 'nullable.json'
    path.write_text(json.dumps([{
        '标题': None, '来源': None, '详情链接': None, '摘要': None,
        '关键词': None, '作者单位': None, '下载状态': None,
        '作者': [{'name': None, 'profile_url': None, 'au_code': None}],
        '备注': {'nullable': None},
    }]), encoding='utf-8')
    store = Workspace.load(path)
    paper = store.papers[0]
    assert paper.title == paper.source == paper.detail_url == paper.abstract == ''
    assert paper.keywords == []
    assert paper.author_org == ''
    assert paper.download_status == 'pending'
    assert paper.authors[0] == Author('', '', au_code='')
    store.save()
    saved = json.loads(path.read_text(encoding='utf-8'))[0]
    assert saved['备注'] == {'nullable': None}


@pytest.mark.parametrize('record', [
    {'标题': ['不是文本']},
    {'来源': 3},
    {'关键词': '不是列表'},
    {'关键词': [{}]},
    {'作者单位': [None]},
    {'作者': [{'name': ['作者']}]},
    {'作者': [{'profile_url': 3}]},
    {'作者': [{'au_code': 123}]},
    {'被引': []},
    {'序号': 1.5},
    {'本地PDF路径': {}},
])
def test_workspace_rejects_invalid_known_field_types(tmp_path, record):
    path = tmp_path / 'invalid-field.json'
    path.write_text(json.dumps([record]), encoding='utf-8')
    with pytest.raises(ValueError, match='第 1 条'):
        Workspace.load(path)
