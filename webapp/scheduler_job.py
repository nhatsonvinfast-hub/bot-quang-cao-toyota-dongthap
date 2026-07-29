"""Background job: reconciles our DB status with Facebook's native
scheduled publishing. Posts are handed to Facebook (scheduled_publish_time)
at approval time; this job just flips our local status to "posted" once
that time has passed and Facebook confirms the post is live.
"""
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from meta_client import MetaAPIError, MetaClient
from models import Post, db

_scheduler = None


def _check_due_posts(app):
    with app.app_context():
        due = Post.query.filter(
            Post.status == "scheduled",
            Post.scheduled_time <= datetime.now(timezone.utc),
        ).all()
        for post in due:
            try:
                client = MetaClient(post.page.fb_page_id, post.page.access_token)
                info = client._request(
                    "GET", post.fb_post_id, params={"fields": "is_published"}
                )
                if info.get("is_published", True):
                    post.status = "posted"
            except MetaAPIError:
                continue
        if due:
            db.session.commit()


def start_scheduler(app):
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(lambda: _check_due_posts(app), "interval", minutes=5, next_run_time=datetime.now())
    _scheduler.start()
    return _scheduler
