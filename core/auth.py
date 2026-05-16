"""CNKI 登录认证模块"""

import requests
from typing import Optional

from ..config import (
    IP_LOGIN_API,
    DEFAULT_HEADERS,
    LOGIN_TIMEOUT,
)


class CNKIAuth:
    """知网认证类，处理 IP 登录和会话管理"""

    def __init__(self, headers: Optional[dict] = None):
        """
        初始化认证器

        Args:
            headers: 自定义请求头，默认使用 DEFAULT_HEADERS
        """
        self.headers = headers or DEFAULT_HEADERS.copy()
        self._session: Optional[requests.Session] = None
        self._cookie_string: Optional[str] = None

    def anonymous_login(self) -> requests.Session:
        """
        匿名访问知网：通过 recsys GenerateClientID 获取 Ecp_ClientId，
        再初始化 KNS 匿名会话。
        """
        session = requests.Session()

        headers = dict(self.headers or {})
        headers.pop("Cookie", None)
        headers.pop("Host", None)
        headers.setdefault("User-Agent", "Mozilla/5.0")
        headers.setdefault("Accept", "application/json, text/javascript, */*; q=0.01")
        headers.setdefault("Referer", "https://kns.cnki.net/")
        headers.setdefault("Origin", "https://kns.cnki.net")

        try:
            # 1. 直接请求生产环境 GenerateClientID
            r = session.get(
                "https://recsys.cnki.net/RCDService/api/UtilityOpenApi/GenerateClientID",
                headers=headers,
                timeout=10,
            )

            r.raise_for_status()
            data = r.json()

            if not data.get("Success") or not data.get("Data"):
                raise RuntimeError(f"获取 Ecp_ClientId 失败：{data}")

            ecp_client_id = data["Data"]

            # 2. 写入 requests session cookie
            session.cookies.set(
                "Ecp_ClientId",
                ecp_client_id,
                domain=".cnki.net",
                path="/",
            )

            # 3. 访问 KNS，补充 SID_kns_new
            kns_headers = dict(headers)
            kns_headers.update({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://kns.cnki.net/",
                "Upgrade-Insecure-Requests": "1",
            })

            session.get(
                "https://kns.cnki.net/kns8s/defaultresult/index",
                headers=kns_headers,
                timeout=15,
            )

            # 4. 保存会话
            self._session = session
            self._cookie_string = "; ".join(
                f"{c.name}={c.value}" for c in session.cookies
            )

            print("\n✅ 【匿名会话创建成功】")
            return session

        except requests.RequestException as e:
            raise RuntimeError(f"匿名会话初始化失败：网络请求异常：{e}") from e

    def ip_login(self) -> requests.Session:
        """
        使用 IP 地址登录知网

        Returns:
            requests.Session: 已认证的会话对象

        Raises:
            ConnectionError: 登录失败时抛出
        """
        session = requests.Session()

        # 1. 先访问登录页，获取基础 Cookie
        session.get(
            "https://login.cnki.net/TopLogin/",
            headers=self.headers,
            timeout=LOGIN_TIMEOUT
        )

        # 2. 调用官方 IP 登录接口
        print("正在调用知网官方 IP 登录接口：IpLoginPo")
        resp = session.post(
            url=IP_LOGIN_API,
            json={},
            headers=self.headers,
            timeout=LOGIN_TIMEOUT
        )

        print(f"登录接口返回：{resp.status_code} | {resp.text}")

        # 3. 跳转到知网新平台补全所有业务 Cookie
        session.get(
            "https://kns.cnki.net/kns8s/brief/grid",
            headers=self.headers,
            timeout=LOGIN_TIMEOUT
        )

        # 4. 保存会话和 Cookie
        self._session = session
        self._cookie_string = "; ".join([f"{k}={v}" for k, v in session.cookies.items()])

        print("\n✅ 【完整登录 Cookie】")
        print(self._cookie_string)

        return session

    def get_session(self) -> Optional[requests.Session]:
        """
        获取当前会话

        Returns:
            已认证的会话对象，如果未登录则返回 None
        """
        return self._session

    def get_cookie_string(self) -> Optional[str]:
        """
        获取 Cookie 字符串

        Returns:
            Cookie 字符串，如果未登录则返回 None
        """
        return self._cookie_string

    def is_authenticated(self) -> bool:
        """
        检查是否已认证

        Returns:
            bool: 是否已登录
        """
        return self._session is not None and len(self._session.cookies) > 0
