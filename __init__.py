"""CNKI 论文助手

知网论文搜索和下载工具
"""

from .core import CNKIAuth, CNKISearcher, PaperParser
from .models import Paper, Author
from .downloaders import BaseDownloader, PDFDownloader
from .utils import save_json, load_json, print_paper_summary

__version__ = '0.1.0'
__all__ = [
    'CNKIAuth',
    'CNKISearcher',
    'PaperParser',
    'Paper',
    'Author',
    'BaseDownloader',
    'PDFDownloader',
    'save_json',
    'load_json',
    'print_paper_summary',
]
