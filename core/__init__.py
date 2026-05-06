"""核心功能模块"""

from .auth import CNKIAuth
from .search import CNKISearcher
from .parser import PaperParser

__all__ = ['CNKIAuth', 'CNKISearcher', 'PaperParser']
