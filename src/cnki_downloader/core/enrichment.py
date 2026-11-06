"""供桌面工作台复用的文献详情与作者编码操作。"""
from urllib.parse import urljoin

from ..config import DEFAULT_HEADERS, REQUEST_TIMEOUT
from .parser import PaperParser
from .search import CNKISearcher
from .access import AccessBlocked, check_access


def skip_detail(paper):
    """按用户规则跳过摘要以 <正> 开头的记录，忽略前导空白。"""
    return (paper.abstract or '').lstrip().startswith('<正>')


def needs_detail(paper):
    return not skip_detail(paper) and bool(paper.detail_url) and (
        not paper.abstract or not paper.volume or not paper.issue
        or not paper.authors or any(not a.au_code for a in paper.authors)
    )


def read_page(session, url, referer):
    response = session.get(url, headers={
        'User-Agent': DEFAULT_HEADERS['User-Agent'],
        'Accept': 'text/html,application/xhtml+xml', 'Referer': referer,
    }, timeout=REQUEST_TIMEOUT)
    if not response.encoding or response.encoding.lower() == 'iso-8859-1':
        response.encoding = response.apparent_encoding or 'utf-8'
    check_access(response)
    response.raise_for_status()
    return response.text


def refresh_detail_url(session, paper):
    """通过当前会话重新检索，只有唯一匹配的论文才可用于刷新。"""
    if not paper.title.strip():
        raise ValueError('论文标题为空，无法重新检索详情链接')
    candidates = CNKISearcher(session).search_by_title(paper.title)
    matches = [p for p in candidates
               if p.title.strip() == paper.title.strip() and p.detail_url
               and (not paper.source or p.source.strip() == paper.source.strip())
               and (not paper.publish_date or p.publish_date.strip() == paper.publish_date.strip())]
    urls = {urljoin('https://kns.cnki.net/', p.detail_url) for p in matches}
    if len(urls) != 1:
        raise ValueError('重新检索未找到唯一匹配的论文，保留原链接，不刷新作者')
    return urls.pop()


def fetch_detail(session, paper):
    if skip_detail(paper):
        return
    url = urljoin('https://kns.cnki.net/', paper.detail_url)
    info = PaperParser.parse_paper_detail(read_page(session, url, 'https://kns.cnki.net/'))
    if not info:
        raise ValueError('详情页面没有可解析的信息，链接可能已过期或需要验证')
    new_authors = info.get('authors', [])
    for author in new_authors:
        previous = [a for a in paper.authors if a.name == author.name]
        if len(previous) == 1 and sum(a.name == author.name for a in new_authors) == 1:
            author.au_code = previous[0].au_code
            author.profile_url = author.profile_url or previous[0].profile_url
    for name, value in info.items():
        if value and hasattr(paper, name):
            setattr(paper, name, value)


def refresh_author_links(session, paper, blocked_author, before_request):
    """作者页验证后重新检索并读取详情，仅更新可唯一对应的作者 URL。"""
    before_request()
    detail_url = refresh_detail_url(session, paper)
    before_request()
    info = PaperParser.parse_paper_detail(read_page(session, detail_url, 'https://kns.cnki.net/'))
    fresh_authors = info.get('authors', [])
    updates = []
    for author in paper.authors:
        matches = [a for a in fresh_authors if a.name == author.name and a.profile_url]
        if (len(matches) == 1
                and sum(a.name == author.name for a in fresh_authors) == 1
                and sum(a.name == author.name for a in paper.authors) == 1):
            updates.append((author, matches[0].profile_url))
    if not any(author is blocked_author for author, _ in updates):
        raise ValueError('新详情页没有该作者的唯一主页链接，保留原链接')
    paper.detail_url = detail_url
    for author, url in updates:
        author.profile_url = url


def fetch_codes(session, paper, cache, log, checkpoint=lambda: None, before_request=lambda: None):
    failures = 0
    refreshed = False
    for author in paper.authors:
        checkpoint()
        if author.au_code:
            continue
        if not author.profile_url:
            log(f'{author.name}：没有主页链接，请先补全详情')
            failures += 1
            continue
        while True:
            checkpoint()
            base = urljoin('https://kns.cnki.net/', paper.detail_url)
            url = urljoin(base, author.profile_url)
            try:
                code = cache.get(url)
                if not code:
                    before_request()
                    code = PaperParser.parse_author_code(read_page(session, url, base))
                if not code:
                    raise ValueError('页面没有 au-code，链接可能已过期')
                author.au_code = cache[url] = code
                log(f'{author.name}：{code}')
                break
            except AccessBlocked:
                if refreshed:
                    log(f'{author.name}：刷新链接后仍遇到验证或访问限制，停止请求')
                    raise
                refreshed = True
                log(f'{author.name}：遇到验证或访问限制，重新检索论文并刷新作者链接后重试一次')
                checkpoint()
                try:
                    refresh_author_links(session, paper, author, before_request)
                except AccessBlocked:
                    raise
                except Exception as exc:
                    raise AccessBlocked(f'验证后的作者链接刷新失败，已停止请求：{exc}') from exc
            except Exception as exc:
                failures += 1
                log(f'{author.name}：编码获取失败，{exc}')
                break
    return failures
