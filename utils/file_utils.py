"""文件操作工具模块"""

import json
import re
from pathlib import Path
from typing import List, Any, Union

from ..config import OUTPUT_DIR


def ensure_dir(path: Union[str, Path]) -> Path:
    """
    确保目录存在，不存在则创建

    Args:
        path: 目录路径

    Returns:
        Path: 目录 Path 对象
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def save_json(
    data: List[Any],
    filename: str,
    indent: int = 2,
    ensure_ascii: bool = False
) -> str:
    """
    保存数据为 JSON 文件

    Args:
        data: 要保存的数据列表
        filename: 文件名
        indent: 缩进空格数
        ensure_ascii: 是否转义非 ASCII 字符

    Returns:
        str: 保存的文件路径
    """
    # 如果是相对路径，保存到输出目录
    filepath = Path(filename)
    if not filepath.is_absolute():
        ensure_dir(OUTPUT_DIR)
        filepath = Path(OUTPUT_DIR) / filepath

    # 转换数据
    if data and hasattr(data[0], 'to_dict'):
        data = [item.to_dict() for item in data]

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)

    print(f"✅ 数据已保存到: {filepath}")
    return str(filepath)


def load_json(filename: str) -> List[Any]:
    """
    加载 JSON 文件

    Args:
        filename: 文件名

    Returns:
        List[Any]: 加载的数据
    """
    filepath = Path(filename)
    # 只处理纯文件名（没有目录分隔符的情况）
    if not filepath.is_absolute() and len(filepath.parts) == 1:
        # 如果只是文件名，先检查当前目录，再检查 OUTPUT_DIR
        if not filepath.exists():
            output_path = Path(OUTPUT_DIR) / filepath
            if output_path.exists():
                filepath = output_path
    elif not filepath.is_absolute():
        # 如果是相对路径（包含目录），检查是否存在
        if not filepath.exists():
            output_path = Path(OUTPUT_DIR) / filepath
            if output_path.exists():
                filepath = output_path

    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def update_json_entry(
    filename: str,
    index: int,
    updates: dict,
    indent: int = 2,
    ensure_ascii: bool = False
) -> bool:
    """
    更新 JSON 文件中的指定条目

    Args:
        filename: JSON 文件名
        index: 条目索引
        updates: 要更新的字段
        indent: 缩进空格数
        ensure_ascii: 是否转义非 ASCII 字符

    Returns:
        bool: 是否更新成功
    """
    filepath = Path(filename)
    # 只处理纯文件名（没有目录分隔符的情况）
    if not filepath.is_absolute() and len(filepath.parts) == 1:
        # 如果只是文件名，先检查当前目录，再检查 OUTPUT_DIR
        if not filepath.exists():
            output_path = Path(OUTPUT_DIR) / filepath
            if output_path.exists():
                filepath = output_path
    elif not filepath.is_absolute():
        # 如果是相对路径（包含目录），检查是否存在
        if not filepath.exists():
            output_path = Path(OUTPUT_DIR) / filepath
            if output_path.exists():
                filepath = output_path

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if 0 <= index < len(data):
            data[index].update(updates)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
            return True
        return False
    except Exception as e:
        print(f"更新 JSON 文件失败: {e}")
        return False


def sanitize_filename(name: str, max_length: int = 200) -> str:
    """
    清理文件名，移除非法字符

    Args:
        name: 原始文件名
        max_length: 最大长度

    Returns:
        str: 清理后的文件名
    """
    # 移除 Windows 不允许的字符
    illegal_chars = r'[<>:"/\\|?*]'
    name = re.sub(illegal_chars, '_', name)

    # 移除首尾空格和点
    name = name.strip('. ')

    # 限制长度
    if len(name) > max_length:
        name = name[:max_length]

    return name or 'unnamed'


def get_unique_filepath(directory: Union[str, Path], filename: str) -> Path:
    """
    获取唯一的文件路径，避免覆盖

    Args:
        directory: 目录路径
        filename: 文件名

    Returns:
        Path: 唯一的文件路径
    """
    dir_path = ensure_dir(directory)
    filepath = dir_path / filename

    if not filepath.exists():
        return filepath

    # 如果文件存在，添加序号
    stem = filepath.stem
    suffix = filepath.suffix
    counter = 1

    while filepath.exists():
        new_name = f"{stem}_{counter}{suffix}"
        filepath = dir_path / new_name
        counter += 1

    return filepath


def print_paper_summary(papers: List[Any], show_detail: bool = False) -> None:
    """
    打印论文摘要信息

    Args:
        papers: 论文列表
        show_detail: 是否显示详细信息
    """
    print(f"\n共解析到 {len(papers)} 篇论文\n")
    for paper in papers:
        print(paper)
        if show_detail and hasattr(paper, 'detail_url'):
            print(f"   详情: {paper.detail_url}")
        print("-" * 80)

# 判断文件是否存在
def file_exists(filepath: Path) -> bool:
    """
    判断文件是否存在

    Args:
        filepath: 文件路径

    Returns:
        bool: 文件是否存在
    """
    path = Path(filepath)
    if path.exists():
        return True
    # 非绝对路径时，检查 OUTPUT_DIR 目录
    if not path.is_absolute():
        output_path = Path(OUTPUT_DIR) / filepath
        return output_path.exists()
    return False