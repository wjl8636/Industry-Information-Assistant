# Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
# 未经授权，禁止转售或仿制。

"""
Evidence Link - 证据链路工具

提供 URL 规范化，用于：来源去重、引用校验、Grounding 回源。
所有证据相关能力共用的基础工具。

设计理念：URL 规范化降低"同页不同参"导致的误判重复与失效引用。
"""

import re
from typing import Optional
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode, unquote


# 常见跟踪参数：命中即剔除
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "spm", "from", "from_source", "share", "timestamp", "_t", "spm_id_from",
    "mood", "fr", "refer_scene", "refer_share_scheme",
}

# 默认端口（规范化时可去除）
_DEFAULT_PORTS = {"http": 80, "https": 443}

# 短链白名单域名：不展开，避免依赖网络
_SHORTLINK_DOMAINS = {"t.cn", "dwz.cn", "bit.ly", "goo.gl", "tinyurl.com", "s.weibo.com", "c.m.163.com"}


def _clean_host(host: str) -> str:
    """host 小写、去 www. 前缀（保留二级域名语义）"""
    host = host.lower().strip()
    if host.startswith("www."):
        # 尽量保留主域：a.b.www 等除外
        host = host[4:]
    return host or "www.unknown"


def normalize_url(url: Optional[str]) -> str:
    """规范化 URL 为 canonical form。

    规则：
    - scheme/host 小写
    - 去默认端口
    - 去锚点 (#fragment)
    - 去跟踪参数（utm_* / spm / from 等）
    - 去结尾斜杠（除根路径）
    - 无 scheme 时补 https://
    - host 去 www.

    返回 canonical URL 字符串；无效输入返回原文（不抛错）。
    """
    if not url:
        return ""
    url = url.strip().strip("\"")
    if not url:
        return ""

    # 去掉包裹的括号/引号（markdown 引用常见）
    url = url.strip("<>")

    # 补默认协议
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        url = "https://" + url

    try:
        parsed = urlparse(url)
    except Exception:
        return url

    # 归一 host
    host = _clean_host(parsed.hostname or "")
    if not host:
        return url

    # scheme 小写
    scheme = parsed.scheme.lower()
    port = parsed.port
    if port and _DEFAULT_PORTS.get(scheme) == port:
        port = None

    # 去掉 tracking 参数，保留其它 query
    keep_query = []
    for k, v in parse_qsl(parsed.query, keep_blank_values=True):
        key_clean = k.lower()
        if key_clean in _TRACKING_PARAMS:
            continue
        keep_query.append((k, v))
    query = urlencode(keep_query) if keep_query else ""

    # 路径：保留大小写（区分敏感），去结尾斜杠
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    netloc = host
    if port:
        netloc = f"{host}:{port}"

    # 不加 fragment
    return urlunparse((scheme, netloc, path, "", query, ""))


def is_same_canonical_url(url_a: Optional[str], url_b: Optional[str]) -> bool:
    """判断两个 URL 规范化后是否同一页面（用于去重/引用校验）"""
    if not url_a or not url_b:
        return False
    return normalize_url(url_a) == normalize_url(url_b)


def extract_markdown_links(text: str) -> list:
    """从报告中提取 [title](url) 形式的所有引用链接。

    Returns:
        List[{"title": str, "url": str}]
    """
    pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    links = []
    for m in pattern.finditer(text):
        title = m.group(1).strip()
        url = m.group(2).strip()
        if title and url and url.lower().startswith(("http://", "https://")):
            links.append({"title": title, "url": url})
    return links