"""
文化DNA —— 联网图片搜索 Provider 抽象层

「混合搜索」策略：
- 默认 Provider：Bing 图片搜索（免密钥，cn.bing.com/images/search，HTML 内嵌 m="{...}" JSON 可直接解析）
- 预留扩展点：未来可接入 API 型 provider（图库 / 收藏 / 云图等），只需实现 ImageSearchProvider.search() 并注册到 _PROVIDERS

聚合逻辑：按注册顺序依次搜索，结果按 image_url 去重后合并。
"""
import re
import json
import html
import logging

import requests

logger = logging.getLogger(__name__)

# ── 搜索请求头（模拟浏览器，降低被反爬拦截概率）──────────────
SEARCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://cn.bing.com/",
}
_SEARCH_URL = "https://cn.bing.com/images/search"
_DEFAULT_TIMEOUT = 10


class ImageSearchProvider:
    """图片搜索 Provider 抽象基类"""

    name = "base"

    def search(self, query, limit=10):
        """
        搜索图片，返回候选列表。

        Returns:
            [{"title", "image_url", "thumb_url", "page_url", "mime"}, ...]
            失败返回空列表（不抛异常）。
        """
        raise NotImplementedError


class BingImageSearchProvider(ImageSearchProvider):
    """Bing 图片搜索 Provider（免密钥）"""

    name = "bing"

    def search(self, query, limit=10):
        try:
            params = {"q": query, "count": limit, "form": "HDRSC2"}
            resp = requests.get(_SEARCH_URL, params=params, headers=SEARCH_HEADERS, timeout=_DEFAULT_TIMEOUT)

            if resp.status_code != 200:
                logger.warning("Bing 图片搜索失败: HTTP %s", resp.status_code)
                return []
            if "text/html" not in (resp.headers.get("content-type") or ""):
                return []

            # Bing 图片结果以 m="{\"murl\":...,\"turl\":...}" 内嵌，先按属性值截取
            blobs = re.findall(r'm="(\{[^"]*)"\s*[a-z]*=', resp.text)
            if not blobs:
                blobs = re.findall(r'm="(\{.*?\})"', resp.text)

            results = []
            seen = set()
            for blob in blobs:
                try:
                    data = json.loads(html.unescape(blob))
                except (json.JSONDecodeError, ValueError):
                    continue

                image_url = data.get("murl") or data.get("turl") or ""
                if not image_url or not image_url.startswith("http"):
                    continue
                if image_url in seen:
                    continue
                seen.add(image_url)

                results.append({
                    "title": (data.get("t") or "").strip(),
                    "image_url": image_url,
                    "thumb_url": data.get("turl") or image_url,
                    "page_url": data.get("purl") or "",
                    "mime": data.get("mime") or "",
                })
                if len(results) >= limit:
                    break

            logger.info("Bing 图片搜索: query=%s 命中 %d 条", query, len(results))
            return results

        except Exception as e:
            logger.warning("Bing 图片搜索异常: %s", str(e))
            return []


# ── Provider 注册表（按优先级排列；新增 provider 在下方 append）──────────
_PROVIDERS = [
    BingImageSearchProvider(),
]


def get_providers():
    """返回已注册的搜索 provider 列表（按优先级）"""
    return _PROVIDERS


def search_images(query, limit=10):
    """
    聚合所有 provider 的搜索结果，按 image_url 去重后合并返回。

    Returns:
        [{..., "provider": "bing"}, ...]
    """
    seen = set()
    merged = []
    for provider in _PROVIDERS:
        try:
            for item in provider.search(query, limit):
                url = item.get("image_url")
                if not url or url in seen:
                    continue
                seen.add(url)
                item["provider"] = provider.name
                merged.append(item)
        except Exception as e:
            logger.warning("provider %s 搜索异常: %s", provider.name, str(e))
    return merged