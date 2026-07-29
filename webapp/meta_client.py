"""Thin wrapper around the Meta Graph API for Page content operations."""
from datetime import datetime
from typing import Optional

import requests

import config


class MetaAPIError(RuntimeError):
    pass


class MetaClient:
    def __init__(self, page_id: str, page_access_token: str):
        if not page_id or not page_access_token:
            raise MetaAPIError("Thiếu page_id hoặc page_access_token.")
        self.page_id = page_id
        self.page_access_token = page_access_token
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

    def schedule_post(self, message: str, publish_time: datetime, link: Optional[str] = None) -> dict:
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

    def get_page_insights(self, metrics: list[str], period: str = "day") -> dict:
        return self._request(
            "GET",
            f"{self.page_id}/insights",
            params={"metric": ",".join(metrics), "period": period},
        )

    @staticmethod
    def verify_token(page_id: str, page_access_token: str) -> dict:
        resp = requests.get(
            f"{config.GRAPH_API_BASE}/{page_id}",
            params={"fields": "id,name,category", "access_token": page_access_token},
            timeout=30,
        )
        if resp.status_code >= 400:
            raise MetaAPIError(f"Graph API error {resp.status_code}: {resp.text}")
        return resp.json()
