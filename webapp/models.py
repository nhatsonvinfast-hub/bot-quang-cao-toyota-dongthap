from datetime import datetime, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

POST_STATUSES = ["draft", "pending", "scheduled", "posted", "rejected"]
POST_STATUS_LABELS = {
    "draft": "Bản nháp",
    "pending": "Chờ duyệt",
    "scheduled": "Đã lên lịch",
    "posted": "Đã đăng",
    "rejected": "Bị từ chối",
}


def now_utc():
    return datetime.now(timezone.utc)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(120))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="composer")  # composer | approver | admin
    created_at = db.Column(db.DateTime, default=now_utc)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def can_approve(self) -> bool:
        return self.role in ("approver", "admin")

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class Page(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fb_page_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    access_token = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=now_utc)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    page_id = db.Column(db.Integer, db.ForeignKey("page.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    approved_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    content = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(500))
    tag = db.Column(db.String(80))

    status = db.Column(db.String(20), nullable=False, default="draft")
    scheduled_time = db.Column(db.DateTime)
    fb_post_id = db.Column(db.String(80))
    reject_reason = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=now_utc)
    updated_at = db.Column(db.DateTime, default=now_utc, onupdate=now_utc)

    page = db.relationship("Page", backref="posts")
    author = db.relationship("User", foreign_keys=[author_id])
    approved_by = db.relationship("User", foreign_keys=[approved_by_id])

    @property
    def status_label(self):
        return POST_STATUS_LABELS.get(self.status, self.status)
