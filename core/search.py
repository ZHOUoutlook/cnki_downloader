"""CNKI 论文搜索模块"""

import json
import requests
from typing import Optional, List

from ..config import (
    TARGET_API,
    SEARCH_HEADERS,
    JOURNAL_PAYLOAD,
    JOURNAL_QUERY,
    TITLE_PAYLOAD,
    TITLE_QUERY,
    REQUEST_TIMEOUT,
)
from ..models import Paper
from .parser import PaperParser


class CNKISearcher:
    """知网论文搜索类"""

    def __init__(self, session: requests.Session):
        """
        初始化搜索器

        Args:
            session: 已认证的 requests.Session 对象
        """
        self.session = session
        self.parser = PaperParser()
        self.turn_page  = ""

    def search(
        self,
        query: Optional[dict] = None,
    ) -> List[Paper]:
        """
        搜索论文

        Args:
            query: 查询参数，默认使用 JOURNAL_PAYLOAD
            page: 页码，从 1 开始
            page_size: 每页数量

        Returns:
            List[Paper]: 论文列表
        """
        payload = (query or JOURNAL_PAYLOAD).copy()
        response = self.session.post(
            TARGET_API,
            data=payload,
            headers=SEARCH_HEADERS,
            timeout=REQUEST_TIMEOUT
        )

        print(f"搜索请求状态码：{response.status_code}")
        paper_list , turn_page = self.parser.parse_paper_list(response.text)
        self.turn_page = turn_page
        if paper_list == []:
            print("搜索网页text:",response.text)
            
        return paper_list

    def search_by_journal(
        self,
        journal_name: str,
        page: int = 1,
        page_size: int = 20
    ) -> List[Paper]:
        """
        按期刊名称搜索论文

        Args:
            journal_name: 期刊名称
            page: 页码
            page_size: 每页数量

        Returns:
            List[Paper]: 论文列表
        """
        payload = JOURNAL_PAYLOAD.copy()
        query_json = JOURNAL_QUERY.copy()
        query_json["QNode"]["QGroup"][0]["Items"][0]["Value"] = journal_name
        # query_json["QNode"]["QGroup"][0]["ChildItems"][0]["Items"][0]["value"] = journal_name

        payload["pageNum"] = str(page)
        payload["pageSize"] = str(page_size)
        if page > 1:
            query_json["Products"] = "CJFQ,CAPJ,CJTL,CDFD,CMFD,CPFD,IPFD,CPVD,CCND,WBFD,SCSF,SCHF,SCSD,SNAD,CCJD,CJFN,CCVD"
            query_json["SearchFrom"] = 4
            payload["boolSearch"] = "false" # 关闭布尔搜索，使用默认查询条件 
            payload["sortField"] = "PT"
            payload["sortType"] = "desc"
            payload["turnpage"] = self.turn_page
            # payload["CurPage"] = str(page) 
        else:
            # 模糊
            # payload["aside"] = f"文献来源：{journal_name}"  
            # 精确
            payload["aside"] = f"（文献来源：{journal_name}(精确)）"
             
        payload["QueryJson"] = json.dumps(query_json, ensure_ascii=False)

        

        return self.search(query=payload)

    def search_by_journal_all_pages(
        self,
        journal_name: str,
        max_pages: Optional[int] = None,
        page_size: int = 20
    ) -> List[Paper]:
        """
        搜索所有页面的论文

        Args:
            journal_name: 期刊名称
            max_pages: 最大页数限制，None 表示不限制
            page_size: 每页数量

        Returns:
            List[Paper]: 所有论文列表
        """
        all_papers = []
        page = 1

        while True:
            print(f"\n正在获取第 {page} 页...")
            papers = self.search_by_journal(journal_name, page=page, page_size=page_size)

            if not papers:
                print("没有更多数据")
                break

            all_papers.extend(papers)
            print(f"本页获取 {len(papers)} 篇，累计 {len(all_papers)} 篇")

            if max_pages and page >= max_pages:
                print(f"已达到最大页数限制 ({max_pages} 页)")
                break

            page += 1

        return all_papers

    def search_by_title(
        self,
        title: str,
        page: int = 1,
        page_size: int = 20
    ) -> List[Paper]:
        """
        按论文标题搜索

        Args:
            title: 论文标题
            page: 页码
            page_size: 每页数量

        Returns:
            List[Paper]: 论文列表
        """
        payload = TITLE_PAYLOAD.copy()
        query_json = TITLE_QUERY.copy()
        query_json["QNode"]["QGroup"][0]["Items"][0]["Value"] = title
        payload["QueryJson"] = json.dumps(query_json, ensure_ascii=False)
        # 模糊
        # payload["aside"] = f"篇名：{title}"  
        # 精确
        payload["aside"] = f"（篇名：{title}(精确)）"
        # payload["turnpage"] = self.turn_page
        # print(payload["turnpage"])
        # print(f"   📝 搜索请求: {payload}")

        return self.search(query=payload)