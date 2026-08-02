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

            # # 3. 作者 + 作者链接
            # authors = []
            # author_elems = row.select('.author a.KnowledgeNetLink')
            # for a in author_elems:
            #     author = Author(
            #         name=a.get_text(strip=True),
            #         profile_url=a.get('href', '')
            #     )
            #     authors.append(author)

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
                # authors=authors,
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
        解析论文详情页

        Args:
            html_content: HTML 内容

        Returns:
            dict: 论文详情信息，包含 doi, abstract, keywords, author , author_org, issn, cn, pages, fund, album, topic, cls_no
        """
        import re
        soup = BeautifulSoup(html_content, 'html.parser')
        result = {}

        try:
            # 1. 摘要
            abstract_elem = soup.select_one('#ChDivSummary, .abstract-text, .brief-text')
            if abstract_elem:
                result['abstract'] = abstract_elem.get_text(strip=True)

            # 2. 关键词
            keywords = []
            keyword_elems = soup.select('.keywords a')
            for a in keyword_elems:
                kw = a.get_text(strip=True).rstrip(';')
                if kw and kw not in keywords:
                    keywords.append(kw)
            if keywords:
                result['keywords'] = keywords

            # 3. DOI
            for li in soup.select('li.top-space'):
                label = li.select_one('.rowtit')
                if label and 'DOI' in label.get_text():
                    p = li.select_one('p')
                    if p:
                        result['doi'] = p.get_text(strip=True).strip()
                        break

            # 4. 专辑
            for li in soup.select('li.top-space'):
                label = li.select_one('.rowtit')
                if label and '专辑' in label.get_text():
                    p = li.select_one('p')
                    if p:
                        result['album'] = p.get_text(strip=True)
                        break

            # 5. 专题
            for li in soup.select('li.top-space'):
                label = li.select_one('.rowtit')
                if label and '专题' in label.get_text():
                    p = li.select_one('p')
                    if p:
                        result['topic'] = p.get_text(strip=True).replace(';', ';')
                        break

            # 6. 分类号
            for li in soup.select('li.top-space'):
                label = li.select_one('.rowtit')
                if label and '分类号' in label.get_text():
                    p = li.select_one('p')
                    if p:
                        result['cls_no'] = p.get_text(strip=True)
                        break

            # 7. 作者单位 及 作者
            # 结构：第一个 h3.author 包含作者名（带 superscript 索引），第二个 h3.author 包含单位信息
            author_div = soup.select_one('.wx-tit')
            if author_div:
                author_elements = author_div.select('h3.author')
                if len(author_elements) >= 2:
                    # 第一个 h3.author：解析作者名和superscript索引
                    authors = []
                    first_h3 = author_elements[0]
                    for span in first_h3.select('span'):
                        author_link = span.select_one('a')
                        if author_link:
                            # 情况1: 作者名在 <a> 标签内
                            href = author_link.get('href', '')
                            sup_elem = author_link.find('sup')
                            aff_indices = sup_elem.get_text(strip=True) if sup_elem else ''
                            author_name = author_link.get_text(strip=True)
                            if sup_elem:
                                sup_text = sup_elem.get_text(strip=True)
                                author_name = author_name.replace(sup_text, '')
                            author_name = author_name.strip()
                            if author_name:
                                authors.append(Author(
                                    name=author_name,
                                    profile_url=href,
                                    affiliation_indices=aff_indices
                                ))
                        else:
                            # 情况2: 作者名只是纯文本（在 span 内，没有 <a>）
                            author_name = span.get_text(strip=True)
                            if author_name:
                                authors.append(Author(
                                    name=author_name,
                                    profile_url='',
                                    affiliation_indices=''
                                ))
                    if authors:
                        result['authors'] = authors

                    # 第二个 h3.author：解析作者单位
                    org_list = []
                    second_h3 = author_elements[1]
                    for span in second_h3.select('span'):
                        org_link = span.select_one('a')
                        if org_link:
                            org_text = org_link.get_text(strip=True)
                        else:
                            org_text = span.get_text(strip=True)
                        # 去掉开头的序号，如 "1." "2." 等
                        org_text = re.sub(r'^\d+\.\s*', '', org_text)
                        if org_text:
                            org_list.append(org_text)
                    if org_list:
                        result['author_org'] = org_list

            # 8. 基金
            fund_elem = soup.select_one('.funds')
            if fund_elem:
                # 获取所有基金名称
                funds = []
                for a in fund_elem.select('a'):
                    fund_text = a.get_text(strip=True)
                    if fund_text:
                        funds.append(fund_text)
                if funds:
                    result['fund'] = '; '.join(funds)
                else:
                    # 直接文本
                    fund_text = fund_elem.get_text(strip=True)
                    if fund_text:
                        result['fund'] = fund_text

            # 9. 页数（总页数）
            page_count = soup.select_one('#page-count')
            if page_count:
                result['pages'] = page_count.get('value', '')

            # 10. 卷号、期号、页码范围 - 在 .top-tip 中，格式如 "2026,47(06)" 和 ": 1101-1130"
            top_tip = soup.select_one('.top-tip')
            if top_tip:
                top_tip_text = top_tip.get_text()
                # 匹配卷号期号：2026,47(06) - 处理换行和空白
                vol_issue_match = re.search(r'(\d{4})\s*,\s*(\d+)\s*\(\s*(\d+)\s*\)', top_tip_text)
                if vol_issue_match:
                    result['volume'] = vol_issue_match.group(1).strip()  # 2026
                    result['issue'] = vol_issue_match.group(3).strip()  # 06
                # 匹配页码范围：如 ": 1101-1130"
                page_range_match = re.search(r':\s*(\d+-\d+)', top_tip_text)
                if page_range_match:
                    result['page_range'] = page_range_match.group(1)  # 1101-1130

            # 11. ISSN / CN 号 - 在 ul.row > li.top-space 中
            for li in soup.select('li.top-space'):
                label = li.select_one('.rowtit')
                if not label:
                    continue
                label_text = label.get_text(strip=True)
                p = li.select_one('p')
                if not p:
                    continue
                val = p.get_text(strip=True)
                if 'ISSN' in label_text:
                    result['issn'] = val
                elif 'CN' in label_text and len(val) < 30:
                    result['cn'] = val

        except Exception as e:
            print(f"解析详情页失败: {e}")

        return result
