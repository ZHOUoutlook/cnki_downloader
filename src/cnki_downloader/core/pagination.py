"""翻页预热序列构建模块

提供 build_warmup_pages 函数，用于在 start_page > 1 时
构建正确的预热页码序列，确保 hidTurnPage 令牌链完整。
"""

from typing import List


def build_warmup_pages(start_page: int) -> List[int]:
    """构建翻页预热序列。

    策略：
        - 必须从第 1 页开始获取初始 hidTurnPage 令牌
        - 若 start_page > 9，先跳到第 9 页
        - 之后每 +4 页一跳（9→13→17→...），直到越过 start_page
        - 最后回落到 start_page，使令牌对应 start_page 的下一页

    Args:
        start_page: 目标起始页码

    Returns:
        List[int]: 预热页码序列，例如 start_page=10 → [1, 9, 13, 10]
                   start_page=20 → [1, 9, 13, 17, 21, 20]
                   start_page=2  → [1, 2]
    """
    if start_page <= 1:
        return []

    targets = [1]

    if start_page > 9:
        targets.append(9)
        p = 9
        while p < start_page:
            p += 4
            targets.append(p)

    if targets[-1] != start_page:
        targets.append(start_page)

    return targets
