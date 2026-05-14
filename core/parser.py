"""CNKI HTML 解析模块"""

from bs4 import BeautifulSoup
from typing import List

from ..models import Paper, Author


class PaperParser:
    """论文 HTML 解析器"""

    @staticmethod
    def parse_paper_list(html_content: str) -> List[Paper]:
        """
        解析知网检索结果 HTML，返回结构化论文列表

        Args:
            html_content: HTML 内容

        Returns:
            List[Paper]: 论文对象列表
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        papers = []

        # 定位所有论文行
        # 精准提取 id="hidTurnPage" 的 value
        hid_turn_page = soup.find('input', id='hidTurnPage')
        paper_rows = soup.select('table.result-table-list tbody tr')
        
        for row in paper_rows:
            paper = PaperParser._parse_row(row)
            if paper:
                papers.append(paper)
        if hid_turn_page:
            value = hid_turn_page.get('value')
            # print("提取到的 hidTurnPage value：", value)
        else:
            value = ""
            print("未找到hidTurnPage标签")
        return papers,value

    @staticmethod
    def _parse_row(row) -> Paper:
        """
        解析单行论文数据

        Args:
            row: BeautifulSoup 元素

        Returns:
            Paper: 论文对象
        """
        try:
            # 1. 序号
            seq_elem = row.select_one('.seq')
            seq = int(seq_elem.get_text(strip=True)) if seq_elem else 0

            # 2. 论文标题 + 详情链接
            title_elem = row.select_one('.name a.fz14')
            title = title_elem.get_text(strip=True) if title_elem else ''
            detail_url = title_elem.get('href', '') if title_elem else ''

            # 3. 作者 + 作者链接
            authors = []
            author_elems = row.select('.author a.KnowledgeNetLink')
            for a in author_elems:
                author = Author(
                    name=a.get_text(strip=True),
                    profile_url=a.get('href', '')
                )
                authors.append(author)

            # 4. 来源（期刊/会议等）
            source_elem = row.select_one('.source a')
            source = source_elem.get_text(strip=True) if source_elem else ''

            # 5. 发表时间
            date_elem = row.select_one('.date')
            publish_date = date_elem.get_text(strip=True) if date_elem else ''

            # 6. 数据库类型（期刊/硕博等）
            db_elem = row.select_one('.data span')
            db_type = db_elem.get_text(strip=True) if db_elem else ''

            # 7. 被引次数
            quote_elem = row.select_one('.quote a.quoteCnt')
            citation_count = int(quote_elem.get_text(strip=True) or 0) if quote_elem else 0

            # 8. 下载次数
            download_elem = row.select_one('.download a.downloadCnt')
            download_count = int(download_elem.get_text(strip=True) or 0) if download_elem else 0

            # 9. 下载链接
            download_link = row.select_one('a.downloadlink')
            download_url = download_link.get('href', '') if download_link else ''

            # 10. HTML阅读链接
            html_link = row.select_one('a.icon-html')
            html_url = html_link.get('href', '') if html_link else ''

            # 11. AI阅读链接
            ai_link = row.select_one('a.icon-airead')
            ai_read_url = ai_link.get('href', '') if ai_link else ''

            return Paper(
                seq=seq,
                title=title,
                detail_url=detail_url,
                authors=authors,
                source=source,
                publish_date=publish_date,
                db_type=db_type,
                citation_count=citation_count,
                download_count=download_count,
                download_url=download_url,
                html_url=html_url,
                ai_read_url=ai_read_url
            )

        except Exception as e:
            print(f"解析行失败: {e}")
            return None

    @staticmethod
    def parse_paper_detail(html_content: str) -> dict:
        """
        解析论文详情页（预留接口）

        Args:
            html_content: HTML 内容

        Returns:
            dict: 论文详情信息
        """
        # TODO: 实现详情页解析
        return {}
