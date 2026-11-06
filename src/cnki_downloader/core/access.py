"""识别访问限制，交由调用方停止任务并保留进度。"""
from bs4 import BeautifulSoup


class AccessBlocked(RuntimeError):
    """需要人工处理验证或等待网站解除访问限制。"""


def check_access(response):
    if response.status_code in (403, 429):
        raise AccessBlocked(f'网站限制访问（HTTP {response.status_code}），已停止请求')
    soup = BeautifulSoup(response.text, 'html.parser')
    for node in soup(['script', 'style', 'noscript']):
        node.decompose()
    title = soup.title.get_text(' ', strip=True) if soup.title else ''
    text = soup.get_text(' ', strip=True)
    if (any(marker in title for marker in ('安全验证', '访问验证', '验证码', 'Security Verification'))
            or any(marker in text for marker in (
                '请完成安全验证', '请进行安全验证', '请拖动滑块', '请输入验证码',
                '人机验证', '访问过于频繁', '访问频繁', '访问异常',
            ))):
        raise AccessBlocked('页面要求安全验证或限制访问，已停止请求；请在浏览器中人工检查')
