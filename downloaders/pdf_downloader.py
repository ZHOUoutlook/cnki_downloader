"""PDF 下载器"""

import re
import random
import time
from typing import List, Optional
from pathlib import Path
import requests
from bs4 import BeautifulSoup

from ..core.auth import CNKIAuth
from ..core.search import CNKISearcher

from .base import BaseDownloader
from ..models import Paper
from ..utils import sanitize_filename, get_unique_filepath, update_json_entry
from ..config import (
    DOWNLOAD_TIMEOUT,
    PDF_DOWNLOAD_BASE,
    REQUEST_TIMEOUT,
)


class PDFDownloader(BaseDownloader):
    """PDF 下载器"""

    def __init__(
        self,
        session: requests.Session,
        output_dir: str = "output/pdfs",
        json_file: Optional[str] = None,
        auth: Optional[CNKIAuth] = None ,
    ):
        """
        初始化 PDF 下载器

        Args:
            session: 已认证的 requests.Session 对象
            output_dir: PDF 输出目录
            json_file: JSON 文件路径，用于更新下载状态
            auth: CNKIAuth 对象，用于重新登录
        """
        super().__init__(output_dir)
        self.session = session
        self.json_file = json_file
        self.auth = auth
        self.searcher = CNKISearcher(session)

    def _relogin(self) -> bool:
        """
        重新登录知网

        Returns:
            bool: 是否登录成功
        """
        if not self.auth:
            print("   ⚠️ 未提供 auth 对象，无法重新登录")
            return False

        try:
            print("   🔄 正在重新登录...")
            new_session = self.auth.ip_login()
            if new_session:
                self.session = new_session
                print("   ✅ 重新登录成功")
                return True
            else:
                print("   ❌ 重新登录失败")
                return False
        except Exception as e:
            print(f"   ❌ 重新登录失败: {e}")
            return False

    def _refresh_detail_url(self, paper: 'Paper', retry_count: int = 0) -> Optional[str]:
        """
        通过重新搜索论文标题获取新的详情链接

        Args:
            paper: 论文对象
            retry_count: 当前重试次数

        Returns:
            Optional[str]: 新的详情链接，失败返回 None
        """
        max_retries = 2

        if not paper.title:
            print("   ⚠️ 论文标题为空，无法搜索")
            return None

        try:
            print(f"   🔄 正在通过标题重新搜索获取详情链接...")
            print(f"   📝 标题: {paper.title[:50]}{'...' if len(paper.title) > 50 else ''}")
            
            papers = self.searcher.search_by_title(
                title=paper.title,
                page=1,
                page_size=5
            )

            if not papers:
                print("   ⚠️ 未找到匹配的论文")
                return None

            # 查找标题完全匹配的论文
            for p in papers:
                if p.title == paper.title:
                    print(f"   ✅ 找到匹配的论文，获取到新的详情链接")
                    return p.detail_url

            # 如果没有完全匹配的论文，提示用户并返回 None
            if papers:
                print(f"   ⚠️ 未找到完全匹配，使用第一个搜索结果")
                print(f"   📝 搜索结果标题: {papers[0].title[:50]}{'...' if len(papers[0].title) > 50 else ''}")
                return None

            return None

        except Exception as e:
            print(f"   ❌ 重新搜索失败: {e}")

            # 重试
            if retry_count < max_retries:
                print(f"   🔄 重试获取详情链接 (第 {retry_count + 1} 次)...")
                time.sleep(2)
                return self._refresh_detail_url(paper, retry_count + 1)

            return None

    def _get_detail_page(self, url: str, retry_count: int = 0, paper: Optional['Paper'] = None) -> Optional[str]:
        """
        获取论文详情页内容

        Args:
            url: 详情页 URL
            retry_count: 当前重试次数
            paper: 论文对象，用于在 URL 过期时重新搜索获取新的详情链接

        Returns:
            Optional[str]: HTML 内容，失败返回 None
        """
        max_retries = 2  # 最大重试次数

        try:
            # 处理相对 URL
            if url.startswith('//'):
                url = 'https:' + url
            elif url.startswith('/'):
                url = 'https://kns.cnki.net' + url
            elif not url.startswith('http'):
                url = 'https://kns.cnki.net/' + url

            # 使用更完整的浏览器请求头，模拟真实浏览器访问
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.7,en;q=0.6",
                # "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-site",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
                "Referer": "https://kns.cnki.net/kns8s/defaultresult/index",
            }
            response = self.session.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True
            )
            # 检查是否被重定向到登录页面或验证页面
            if response.status_code == 302 or 'login' in response.url.lower():
                print(f"   ⚠️ 可能需要重新登录，状态码: {response.status_code}")

                # 尝试重新登录
                if retry_count < max_retries and self.auth:
                    print(f"   🔄 尝试重新登录 (第 {retry_count + 1} 次)...")
                    if self._relogin():
                        # 等待一段时间后重试
                        time.sleep(2)
                        return self._get_detail_page(url, retry_count + 1, paper)

                return None

            response.raise_for_status()
            response.encoding = 'utf-8'

            # 检查返回内容是否有效（不是验证页面）
            if '验证' in response.text[:500] or 'captcha' in response.text[:500].lower() or "�" in response.text[:500].lower():
                print(f"   ⚠️ 触发验证机制，详情链接可能已过期")

                # 优先尝试通过重新搜索获取新的详情链接
                if paper and paper.title:
                    new_url = self._refresh_detail_url(paper)
                    paper.detail_url = new_url  # 更新论文对象中的详情链接
                    if new_url:
                        print(f"   🔄 使用新的详情链接重试...")
                        time.sleep(2)
                        return self._get_detail_page(new_url, retry_count, paper)

                # 如果无法获取新链接，尝试重新登录后重试原链接
                if retry_count < max_retries and self.auth:
                    print(f"   🔄 尝试重新登录 (第 {retry_count + 1} 次)...")
                    if self._relogin():
                        time.sleep(3)
                        return self._get_detail_page(url, retry_count + 1, paper)

                return None

            return response.text

        except requests.exceptions.Timeout:
            print(f"   ⚠️ 请求超时")

            # 超时后重试
            if retry_count < max_retries:
                print(f"   🔄 重试获取详情页 (第 {retry_count + 1} 次)...")
                time.sleep(2)
                return self._get_detail_page(url, retry_count + 1, paper)

            return None

        except requests.exceptions.ConnectionError as e:
            print(f"   ⚠️ 连接错误: {e}")

            # 连接错误后重试
            if retry_count < max_retries:
                print(f"   🔄 重试获取详情页 (第 {retry_count + 1} 次)...")
                time.sleep(3)
                return self._get_detail_page(url, retry_count + 1, paper)

            return None

        except Exception as e:
            print(f"   获取详情页失败: {e}")
            return None

    def _extract_pdf_url(self, html: str) -> Optional[str]:
        """
        从详情页 HTML 中提取 PDF 下载链接

        Args:
            html: 详情页 HTML 内容

        Returns:
            Optional[str]: PDF 下载链接，失败返回 None
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # 方法1: 查找 PDF 下载按钮
            pdf_btn = soup.select_one('a#pdfDown, li.btn-dlpdf a')
            if pdf_btn:
                href = pdf_btn.get('href', '')
                if href and 'bar.cnki.net/bar/download' in href:
                    return href

            # 方法2: 查找包含 download/order 的链接
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'bar.cnki.net/bar/download/order' in href:
                    return href

            # 方法3: 查找 CAJ 下载链接作为备选
            caj_btn = soup.select_one('a#cajDown, li.btn-dlcaj a')
            if caj_btn:
                href = caj_btn.get('href', '')
                if href and 'bar.cnki.net/bar/download' in href:
                    print("  ⚠️ 未找到 PDF 链接，将下载 CAJ 格式")
                    return href

            return None

        except Exception as e:
            print(f"  解析 PDF 链接失败: {e}")
            return None

    def _download_file(self, url: str, filepath: Path) -> bool:
        """
        下载文件到指定路径

        Args:
            url: 下载链接
            filepath: 保存路径

        Returns:
            bool: 是否下载成功
        """
        try:
            # 使用更完整的浏览器请求头
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0",
                "Accept": "application/pdf,application/x-caj,application/octet-stream,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.7,en;q=0.6",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Referer": "https://kns.cnki.net/",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-site",
                "Sec-Fetch-User": "?1",
            }

            response = self.session.get(
                url,
                headers=headers,
                timeout=DOWNLOAD_TIMEOUT,
                stream=True,
                allow_redirects=True
            )

            # 检查是否被重定向到登录页面
            if response.status_code == 302 or 'login' in response.url.lower():
                print(f"   ⚠️ 下载时需要重新登录")
                return False

            response.raise_for_status()

            # 检查是否是有效的 PDF/CAJ 文件
            content_type = response.headers.get('Content-Type', '')
            content_disp = response.headers.get('Content-Disposition', '')

            # 确定文件扩展名
            ext = '.pdf'
            if 'caj' in content_type.lower() or '.caj' in content_disp.lower():
                ext = '.caj'
            elif '.pdf' not in str(filepath).lower():
                # 如果路径没有扩展名，添加
                if not str(filepath).lower().endswith(('.pdf', '.caj')):
                    filepath = Path(str(filepath) + ext)

            # 写入文件
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

            # 验证文件大小
            if filepath.exists() and filepath.stat().st_size > 0:
                return True
            else:
                filepath.unlink(missing_ok=True)
                return False

        except Exception as e:
            print(f"  下载文件失败: {e}")
            return False

    def download(self, paper: Paper, filename: Optional[str] = None) -> Optional[str]:
        """
        下载单个论文 PDF

        Args:
            paper: 论文对象
            filename: 自定义文件名（不含扩展名）

        Returns:
            Optional[str]: 下载后的文件路径，失败返回 None
        """
        # 检查是否有详情页链接
        if not paper.detail_url:
            print(f"❌ [{paper.seq}] {paper.title}")
            print(f"   没有详情页链接")
            return None

        # 确定文件名
        if filename:
            safe_name = sanitize_filename(filename)
        else:
            # 使用标题和日期作为文件名
            date_str = paper.publish_date.replace('-', '') if paper.publish_date else ''
            safe_name = sanitize_filename(f"{paper.title}_{date_str}")
            # safe_name = sanitize_filename(f"{paper.seq}_{paper.title}_{date_str}")

        # 检查是否已存在
        pdf_path = self.output_dir / f"{safe_name}.pdf"
        caj_path = self.output_dir / f"{safe_name}.caj"

        if pdf_path.exists():
            print(f"⏭️ [{paper.seq}] {paper.title}")
            print(f"   PDF 已存在: {pdf_path}")
            paper.download_status = "completed"
            paper.local_pdf_path = str(pdf_path)
            return str(pdf_path)

        if caj_path.exists():
            print(f"⏭️ [{paper.seq}] {paper.title}")
            print(f"   CAJ 已存在: {caj_path}")
            paper.download_status = "completed"
            paper.local_pdf_path = str(caj_path)
            return str(caj_path)

        print(f"📥 [{paper.seq}] {paper.title}")

        # 步骤1: 获取详情页
        print(f"   获取详情页...")
        html = self._get_detail_page(paper.detail_url, paper=paper)
        if not html:
            print(f"   ❌ 获取详情页失败")
            paper.download_status = "failed"
            return None
        
        # 步骤2: 提取 PDF 下载链接
        print(f"   解析下载链接...")
        download_url = self._extract_pdf_url(html)
        if not download_url:
            print(f"   ❌ 未找到下载链接")
            # 进入安全验证界面后，详情页会变成一个提示页面，无法获取下载链接，这时可以尝试重新登录
            paper.download_status = "failed"
            return None

        # 步骤3: 下载文件
        print(f"   下载文件...")
        # 先尝试 .pdf 扩展名
        temp_path = self.output_dir / f"{safe_name}.pdf"

        if self._download_file(download_url, temp_path):
            # 检查实际文件类型
            if temp_path.suffix == '.pdf':
                final_path = temp_path
            else:
                final_path = temp_path

            print(f"   ✅ 下载成功: {final_path.name}")
            paper.download_status = "completed"
            paper.local_pdf_path = str(final_path)
            return str(final_path)
        else:
            print(f"   ❌ 下载失败")
            paper.download_status = "failed"
            return None

    def download_batch(
        self,
        papers: List[Paper],
        max_workers: int = 1,
        skip_existing: bool = True,
        delay: float = 10.0,
        update_json: bool = True
    ) -> dict:
        """
        批量下载论文 PDF

        Args:
            papers: 论文列表
            max_workers: 最大并发数（暂不支持并发）
            skip_existing: 是否跳过已存在的文件
            delay: 每次下载之间的延迟（秒）
            update_json: 是否更新 JSON 文件

        Returns:
            dict: 下载结果统计
        """
        results = {
            'total': len(papers),
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'files': []
        }

        # 过滤有下载链接的论文，且文件缺失或未下载的论文。同时过滤掉已经完成的论文paper.download_status=completed
        # 使用标题和日期作为文件名
        # 检查是否已存在
        downloadable = [
            p for p in papers 
            if p.detail_url
            and (
                # 路径为空 → 需要下载
                not p.local_pdf_path
                # 路径存在但文件不存在 → 需要下载
                or (p.local_pdf_path and not Path(p.local_pdf_path).exists())
                # 还没完成的论文 → 需要下载
                or not Path(self.output_dir / f"{sanitize_filename(p.title)}_{p.publish_date.replace('-', '') if p.publish_date else ''}.pdf").exists()
            )
        ]
        print(f"\n📄 共 {len(papers)} 篇论文，{len(downloadable)} 篇有详情链接")

        if not downloadable:
            print("❌ 没有可需要下载的论文")
            return results

        for i, paper in enumerate(downloadable, 1):
            print(f"\n[{i}/{len(downloadable)}] ", end="")

            # 更新状态为下载中
            paper.download_status = "downloading"

            filepath = self.download(paper)

            if filepath:
                results['success'] += 1
                results['files'].append(filepath)
            else:
                results['failed'] += 1

            # 更新 JSON 文件
            if update_json and self.json_file and paper.seq > 0:
                # seq 从 1 开始，索引从 0 开始
                update_data = {
                    '下载状态': paper.download_status,
                    '本地PDF路径': paper.local_pdf_path or ''
                }
                # 如果 detail_url 被刷新了，也更新它
                if (paper._original_detail_url and
                    paper.detail_url and
                    paper.detail_url != paper._original_detail_url):
                    update_data['详情链接'] = paper.detail_url
                    print(f"   📝 详情链接已更新")

                update_json_entry(
                    self.json_file,
                    paper.seq - 1,
                    update_data
                )
            # 添加延迟，避免请求过快
            if i < len(downloadable) and delay > 0:
                random_delay = delay * (0.5 + 0.5 * random.random())  # 5-10秒随机延迟
                print(f"   ⏳ 等待 {random_delay:.1f} 秒...")
                time.sleep(random_delay)

            # 每下载 10 篇清除 session cookies 并重新登录
            if i % 10 == 0 and i < len(downloadable):
                print(f"\n   🧹 已下载 {i} 篇，清除 session cookies...")
                self.session.cookies.clear()

                # 重新登录
                if self.auth:
                    if not self._relogin():
                        print("   ⚠️ 重新登录失败，继续尝试下载...")

                # 等待一段时间
                if delay > 0:
                    random_delay = delay * (0.5 + 0.5 * random.random())
                    print(f"   ⏳ 等待 {random_delay:.1f} 秒...")
                    time.sleep(random_delay)

        print(f"\n{'='*50}")
        print(f"📊 下载统计:")
        print(f"   ✅ 成功: {results['success']}")
        print(f"   ❌ 失败: {results['failed']}")
        print(f"{'='*50}")

        return results

    def download_from_json(
        self,
        json_file: str,
        limit: Optional[int] = None,
        delay: float = 10.0,
        update_json: bool = True
    ) -> dict:
        """
        从 JSON 文件读取论文列表并下载

        Args:
            json_file: JSON 文件路径
            limit: 限制下载数量
            delay: 每次下载之间的延迟（秒）
            update_json: 是否更新 JSON 文件

        Returns:
            dict: 下载结果统计
        """
        from ..utils import load_json

        # 设置 JSON 文件路径
        self.json_file = json_file

        # 加载论文数据
        papers_data = load_json(json_file)
        papers = [Paper.from_dict(p) for p in papers_data]

        if limit:
            papers = papers[:limit]
            print(f"限制下载前 {limit} 篇")

        return self.download_batch(papers, delay=delay, update_json=update_json)
