"""Seeds an admin user and the default Page from .env / environment
variables. Idempotent — safe to call on every startup, including on
serverless cold starts where the DB resets each time.

CLI usage: python webapp/seed.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from models import Page, User, db


def ensure_seed_data():
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", display_name="Quản trị viên", role="admin")
        admin.set_password(config.DEFAULT_ADMIN_PASSWORD)
        db.session.add(admin)
        print(
            f"Đã tạo tài khoản admin / {config.DEFAULT_ADMIN_PASSWORD} "
            "— đổi mật khẩu sau khi đăng nhập lần đầu."
        )

    if config.DEFAULT_FB_PAGE_ID and config.DEFAULT_FB_PAGE_ACCESS_TOKEN:
        if not Page.query.filter_by(fb_page_id=config.DEFAULT_FB_PAGE_ID).first():
            page = Page(
                fb_page_id=config.DEFAULT_FB_PAGE_ID,
                name=config.DEFAULT_FB_PAGE_NAME or config.DEFAULT_FB_PAGE_ID,
                access_token=config.DEFAULT_FB_PAGE_ACCESS_TOKEN,
            )
            db.session.add(page)
            print(f"Đã import Trang {page.name} từ biến môi trường.")

    db.session.commit()


if __name__ == "__main__":
    from app import create_app

    app = create_app()
    with app.app_context():
        ensure_seed_data()
