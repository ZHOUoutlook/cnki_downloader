"""翻页预热序列测试"""
import sys
from pathlib import Path

# 将 src 加入路径以便导入包内模块
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cnki_downloader.core.pagination import build_warmup_pages


def test_warmup_starts_from_page_1():
    """所有预热序列必须以第 1 页开头（获取初始 hidTurnPage 令牌）。"""
    for sp in [2, 5, 9, 10, 20, 100]:
        targets = build_warmup_pages(sp)
        assert targets[0] == 1, f"start_page={sp} 的预热序列应以第1页开头: {targets}"


def test_warmup_ends_at_start_page():
    """预热序列应以 start_page 结尾（使令牌对应 start_page 的下一页）。"""
    for sp in [2, 5, 9, 10, 13, 20, 100]:
        targets = build_warmup_pages(sp)
        assert targets[-1] == sp, f"start_page={sp} 的预热序列应以 {sp} 结尾: {targets}"


def test_warmup_sequence_logic():
    """验证完整预热序列。"""
    assert build_warmup_pages(1) == []
    assert build_warmup_pages(2) == [1, 2]
    assert build_warmup_pages(5) == [1, 5]
    assert build_warmup_pages(9) == [1, 9]
    assert build_warmup_pages(10) == [1, 9, 13, 10]
    assert build_warmup_pages(13) == [1, 9, 13]
    assert build_warmup_pages(20) == [1, 9, 13, 17, 21, 20]
    assert build_warmup_pages(100) == [1, 9, 13, 17, 21, 25, 29, 33, 37, 41,
                                       45, 49, 53, 57, 61, 65, 69, 73, 77,
                                       81, 85, 89, 93, 97, 101, 100]
