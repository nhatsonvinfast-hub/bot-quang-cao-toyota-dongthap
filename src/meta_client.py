"""Thin wrapper around the Meta Graph API for Page content operations."""
from datetime import datetime
from typing import Optional

import requests

import config


class MetaAPIError(RuntimeError):
    pass


class MetaClient:
    def __init__(self, page_id: Optional[str] = None, page_access_token: Optional[str] = None):
        self.page_id = page_id or config.FB_PAGE_ID
        self.page_access_token = page_access_token or config.FB_PAGE_ACCESS_TOKEN
        if not self.page_access_token:
            raise MetaAPIError(
                "FB_PAGE_ACCESS_TOKEN chưa có trong .env. "
                "Chạy scripts/exchange_token.py trước."
            )
        self.base = config.GRAPH_API_BASE

    def _request(self, method: str, path: str, **kwargs):
        params = kwargs.pop("params", {}) or {}
        params.setdefault("access_token", self.page_access_token)
        resp = requests.request(method, f"{self.base}/{path}", params=params, timeout=30, **kwargs)
        if resp.status_code >= 400:
            raise MetaAPIError(f"Graph API error {resp.status_code}: {resp.text}")
        return resp.json()

    def post_text(self, message: str, link: Optional[str] = None) -> dict:
        params = {"message": message}
        if link:
            params["link"] = link
        return self._request("POST", f"{self.page_id}/feed", params=params)

    def post_photo(self, image_url: str, caption: str = "") -> dict:
        return self._request(
            "POST",
            f"{self.page_id}/photos",
            params={"url": image_url, "caption": caption},
        )

    def schedule_post(self, message: str, publish_time: datetime, link: Optional[str] = None) -> dict:
        """Schedules a post; publish_time must be 10 min–75 days in the future."""
        params = {
            "message": message,
            "published": "false",
            "scheduled_publish_time": int(publish_time.timestamp()),
        }
        if link:
            params["link"] = link
        return self._request("POST", f"{self.page_id}/feed", params=params)

    def list_recent_posts(self, limit: int = 10) -> list:
        data = self._request(
            "GET",
            f"{self.page_id}/posts",
            params={"fields": "id,message,created_time,permalink_url", "limit": limit},
        )
        return data.get("data", [])

    def delete_post(self, post_id: str) -> dict:
        return self._request("DELETE", post_id)

    def get_page_insights(self, metrics: list[str], period: str = "day") -> dict:
        return self._request(
            "GET",
            f"{self.page_id}/insights",
            params={"metric": ",".join(metrics), "period": period},
        )

    def get_post_insights(self, post_id: str, metrics: list[str]) -> dict:
        return self._request(
            "GET",
            f"{post_id}/insights",
            params={"metric": ",".join(metrics)},
        )
