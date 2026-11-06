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


def test_workspace_serialization_does_not_copy_discarded_model_fields():
    class ObsoleteKeywords(list):
        def __deepcopy__(self, memo):
            raise AssertionError('Discarded model fields must not be copied')

    store = Workspace([Paper(1, '论文', '/p', keywords=['新关键词'],
                             authors=[Author('作者', '/fresh')])])
    store.raw = [{'关键词': ObsoleteKeywords(['旧关键词']), '备注': {'tags': ['保留']},
                  '作者': [{'name': '作者', '备注': {'tags': ['作者备注']}}]}]
    rows = store.to_rows()
    assert rows[0]['关键词'] == ['新关键词']
    assert rows[0]['作者'][0]['profile_url'] == '/fresh'
    rows[0]['备注']['tags'].append('修改')
    rows[0]['作者'][0]['备注']['tags'].append('修改')
    rows[0]['关键词'].append('修改')
    assert store.raw[0]['备注']['tags'] == ['保留']
    assert store.raw[0]['作者'][0]['备注']['tags'] == ['作者备注']
    assert store.papers[0].keywords == ['新关键词']


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
    replace = Mock(side_effect=PermissionError('文件占用'))
    monkeypatch.setattr(workspace.os, 'replace', replace)
    monkeypatch.setattr(workspace.time, 'sleep', Mock())
    with pytest.raises(PermissionError):
        store.save()
    assert replace.call_count == 5
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


def test_workspace_retries_transient_replace_denial(tmp_path, monkeypatch):
    from cnki_downloader.gui import workspace
    path = tmp_path / 'transient.json'
    original = '[{"标题": "旧论文"}]'
    path.write_text(original, encoding='utf-8')
    store = Workspace.load(path)
    store.papers[0].title = '新论文'
    replace = workspace.os.replace
    attempts = []
    def temporarily_busy(source, target):
        attempts.append(source)
        assert path.read_text(encoding='utf-8') == original
        if len(attempts) < 3:
            raise PermissionError(13, '文件暂时被占用')
        return replace(source, target)
    monkeypatch.setattr(workspace.os, 'replace', temporarily_busy)
    store.save()
    assert len(attempts) == 3 and len(set(attempts)) == 1
    assert json.loads(path.read_text(encoding='utf-8'))[0]['标题'] == '新论文'
    assert list(tmp_path.glob('*.tmp')) == []


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows 文件共享锁行为')
def test_workspace_recovers_when_windows_reader_releases_file(tmp_path):
    from threading import Timer
    path = tmp_path / 'windows-lock.json'
    path.write_text('[{"标题": "旧论文"}]', encoding='utf-8')
    store = Workspace.load(path)
    store.papers[0].title = '新论文'
    reader = path.open('rb')
    timer = Timer(0.2, reader.close)
    timer.start()
    try:
        store.save()
    finally:
        timer.join()
        reader.close()
    assert json.loads(path.read_text(encoding='utf-8'))[0]['标题'] == '新论文'


def test_workspace_does_not_retry_unrelated_io_errors(tmp_path, monkeypatch):
    from cnki_downloader.gui import workspace
    path = tmp_path / 'disk-error.json'
    path.write_text('[{"标题": "论文"}]', encoding='utf-8')
    store = Workspace.load(path)
    replace = Mock(side_effect=OSError(28, '磁盘空间不足'))
    monkeypatch.setattr(workspace.os, 'replace', replace)
    with pytest.raises(OSError):
        store.save()
    replace.assert_called_once()



def test_search_transaction_deduplicates_only_in_staging_file(tmp_path):
    from cnki_downloader.gui.workspace import SearchTransaction
    path = tmp_path / 'dedup.json'
    rows = [{'标题': '论文', '发表时间': '2026-01-01', '备注': '保留',
             '作者': [{'name': '作者', 'au_code': ''}]},
            {'标题': '论文', '发表时间': '2026-01-01',
             '作者': [{'name': '作者', 'au_code': '001'}], '摘要': '摘要'}]
    path.write_text(json.dumps(rows), encoding='utf-8')
    original = path.read_bytes()
    transaction = SearchTransaction(Workspace.load(path))
    transaction.begin()
    transaction.merge([Paper(1, '论文', '/fresh', publish_date='2026-01-01')])
    assert path.read_bytes() == original
    staged = json.loads(transaction.temporary.read_text(encoding='utf-8'))
    assert len(staged) == 1
    assert staged[0]['作者'][0]['au_code'] == '001'
    assert staged[0]['备注'] == '保留'
    assert staged[0]['摘要'] == '摘要'
    assert staged[0]['详情链接'] == '/fresh'
    transaction.commit()
    assert transaction.workspace.path == path
    assert not transaction.temporary.exists()
    assert json.loads(path.read_text(encoding='utf-8')) == staged


def test_search_transaction_keeps_staging_file_when_final_replace_fails(tmp_path, monkeypatch):
    from cnki_downloader.gui import workspace
    path = tmp_path / 'blocked.json'
    path.write_text('[{"标题": "旧论文"}]', encoding='utf-8')
    original = path.read_bytes()
    transaction = workspace.SearchTransaction(Workspace.load(path))
    transaction.begin()
    transaction.merge([Paper(1, '新论文', '/new')])
    monkeypatch.setattr(workspace.os, 'replace', Mock(side_effect=PermissionError('拒绝访问')))
    monkeypatch.setattr(workspace.time, 'sleep', Mock())
    with pytest.raises(PermissionError):
        transaction.commit()
    assert path.read_bytes() == original
    assert transaction.temporary.exists()
    assert len(json.loads(transaction.temporary.read_text(encoding='utf-8'))) == 2
