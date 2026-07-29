"""
One-off script: exchange the short-lived user token in .env for a long-lived
Page Access Token (does not expire as long as the Page's permissions don't
change), and write it back into .env as FB_PAGE_ACCESS_TOKEN.

Usage:
    python scripts/exchange_token.py
"""
import sys
from pathlib import Path

import requests
from dotenv import set_key

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import config  # noqa: E402


def exchange_long_lived_user_token(short_token: str) -> str:
    resp = requests.get(
        f"{config.GRAPH_API_BASE}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": config.FB_APP_ID,
            "client_secret": config.FB_APP_SECRET,
            "fb_exchange_token": short_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_page_access_token(long_lived_user_token: str, page_id: str) -> tuple[str, str]:
    resp = requests.get(
        f"{config.GRAPH_API_BASE}/{page_id}",
        params={"fields": "access_token,name", "access_token": long_lived_user_token},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["access_token"], data.get("name", "")


def main():
    if not config.FB_APP_SECRET:
        print("Thiếu FB_APP_SECRET trong .env. Dán App Secret vào .env rồi chạy lại.")
        sys.exit(1)
    if not config.FB_USER_ACCESS_TOKEN:
        print("Thiếu FB_USER_ACCESS_TOKEN trong .env.")
        sys.exit(1)
    if not config.FB_PAGE_ID:
        print("Thiếu FB_PAGE_ID trong .env.")
        sys.exit(1)

    print("1/2 Đổi sang long-lived user token...")
    long_user_token = exchange_long_lived_user_token(config.FB_USER_ACCESS_TOKEN)
    print("   OK.")

    print("2/2 Lấy long-lived Page Access Token...")
    page_token, page_name = get_page_access_token(long_user_token, config.FB_PAGE_ID)
    print(f"   OK. Page: {page_name}")

    set_key(str(config.ENV_PATH), "FB_PAGE_ACCESS_TOKEN", page_token)
    set_key(str(config.ENV_PATH), "FB_USER_ACCESS_TOKEN", long_user_token)
    print("\nĐã lưu FB_PAGE_ACCESS_TOKEN (long-lived) vào .env.")
    print("Token này về cơ bản không hết hạn trừ khi bạn đổi mật khẩu FB,")
    print("thu hồi quyền app, hoặc không đăng nhập > 60 ngày.")


if __name__ == "__main__":
    main()
