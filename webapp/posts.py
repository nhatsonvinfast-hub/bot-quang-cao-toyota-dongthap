from datetime import datetime, timezone

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from meta_client import MetaAPIError, MetaClient
from models import Page, Post, db

posts_bp = Blueprint("posts", __name__)

TAB_FILTERS = {
    "all": None,
    "draft": ["draft", "rejected"],
    "pending": ["pending"],
    "scheduled": ["scheduled"],
    "posted": ["posted"],
}
TAB_LABELS = {
    "all": "Tất cả",
    "draft": "Bản nháp",
    "pending": "Chờ duyệt",
    "scheduled": "Đã lên lịch",
    "posted": "Đã đăng",
}


@posts_bp.route("/posts")
@login_required
def list_posts():
    tab = request.args.get("tab", "all")
    page_filter = request.args.get("page_id", type=int)

    query = Post.query
    if page_filter:
        query = query.filter(Post.page_id == page_filter)
    statuses = TAB_FILTERS.get(tab)
    if statuses:
        query = query.filter(Post.status.in_(statuses))
    posts = query.order_by(Post.updated_at.desc()).all()

    counts = {}
    base_query = Post.query
    if page_filter:
        base_query = base_query.filter(Post.page_id == page_filter)
    counts["all"] = base_query.count()
    for key, statuses in TAB_FILTERS.items():
        if statuses:
            counts[key] = base_query.filter(Post.status.in_(statuses)).count()

    pages = Page.query.filter_by(is_active=True).order_by(Page.name).all()

    return render_template(
        "posts_list.html",
        posts=posts,
        pages=pages,
        tab=tab,
        tab_labels=TAB_LABELS,
        counts=counts,
        active_page_id=page_filter,
    )


@posts_bp.route("/posts/new", methods=["GET", "POST"])
@login_required
def new_post():
    pages = Page.query.filter_by(is_active=True).order_by(Page.name).all()
    if not pages:
        flash("Chưa có Trang Facebook nào. Vào Cài đặt để thêm Trang trước.", "error")
        return redirect(url_for("pages.manage_pages"))

    if request.method == "POST":
        content = request.form.get("content", "").strip()
        page_id = request.form.get("page_id", type=int)
        link = request.form.get("link", "").strip() or None
        tag = request.form.get("tag", "").strip() or None
        action = request.form.get("action", "draft")

        if not content or not page_id:
            flash("Cần nhập nội dung và chọn Trang.", "error")
            return redirect(url_for("posts.new_post"))

        status = "pending" if action == "submit" else "draft"
        post = Post(
            page_id=page_id,
            author_id=current_user.id,
            content=content,
            link=link,
            tag=tag,
            status=status,
        )
        db.session.add(post)
        db.session.commit()
        flash("Đã lưu bài viết." if status == "draft" else "Đã gửi duyệt.", "success")
        return redirect(url_for("posts.list_posts"))

    return render_template("post_form.html", pages=pages, post=None)


@posts_bp.route("/posts/<int:post_id>")
@login_required
def view_post(post_id):
    post = db.session.get(Post, post_id) or abort(404)
    return render_template("post_detail.html", post=post)


@posts_bp.route("/posts/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = db.session.get(Post, post_id) or abort(404)
    if post.status not in ("draft", "rejected") or post.author_id != current_user.id:
        if not current_user.is_admin:
            flash("Chỉ tác giả mới sửa được bài ở trạng thái nháp/bị từ chối.", "error")
            return redirect(url_for("posts.view_post", post_id=post.id))

    pages = Page.query.filter_by(is_active=True).order_by(Page.name).all()

    if request.method == "POST":
        post.content = request.form.get("content", "").strip()
        post.page_id = request.form.get("page_id", type=int)
        post.link = request.form.get("link", "").strip() or None
        post.tag = request.form.get("tag", "").strip() or None
        action = request.form.get("action", "draft")
        post.status = "pending" if action == "submit" else "draft"
        db.session.commit()
        flash("Đã cập nhật bài viết." if post.status == "draft" else "Đã gửi duyệt.", "success")
        return redirect(url_for("posts.list_posts"))

    return render_template("post_form.html", pages=pages, post=post)


@posts_bp.route("/posts/<int:post_id>/submit", methods=["POST"])
@login_required
def submit_post(post_id):
    post = db.session.get(Post, post_id) or abort(404)
    if post.status not in ("draft", "rejected"):
        flash("Bài viết không ở trạng thái có thể gửi duyệt.", "error")
        return redirect(url_for("posts.view_post", post_id=post.id))
    post.status = "pending"
    post.reject_reason = None
    db.session.commit()
    flash("Đã gửi duyệt.", "success")
    return redirect(url_for("posts.view_post", post_id=post.id))


@posts_bp.route("/posts/<int:post_id>/reject", methods=["POST"])
@login_required
def reject_post(post_id):
    if not current_user.can_approve:
        abort(403)
    post = db.session.get(Post, post_id) or abort(404)
    post.status = "rejected"
    post.reject_reason = request.form.get("reason", "").strip()
    db.session.commit()
    flash("Đã từ chối bài viết.", "success")
    return redirect(url_for("posts.list_posts"))


@posts_bp.route("/posts/<int:post_id>/approve", methods=["POST"])
@login_required
def approve_post(post_id):
    if not current_user.can_approve:
        abort(403)
    post = db.session.get(Post, post_id) or abort(404)
    if post.status != "pending":
        flash("Chỉ duyệt được bài đang chờ duyệt.", "error")
        return redirect(url_for("posts.view_post", post_id=post.id))

    publish_now = request.form.get("publish_now") == "1"
    scheduled_time_raw = request.form.get("scheduled_time", "").strip()

    client = MetaClient(post.page.fb_page_id, post.page.access_token)
    try:
        if publish_now:
            result = client.post_text(post.content, link=post.link)
            post.fb_post_id = result.get("id")
            post.status = "posted"
        else:
            if not scheduled_time_raw:
                flash("Cần chọn thời gian đăng, hoặc chọn 'Đăng ngay'.", "error")
                return redirect(url_for("posts.view_post", post_id=post.id))
            scheduled_dt = datetime.fromisoformat(scheduled_time_raw)
            result = client.schedule_post(post.content, scheduled_dt, link=post.link)
            post.fb_post_id = result.get("id")
            post.scheduled_time = scheduled_dt
            post.status = "scheduled"
        post.approved_by_id = current_user.id
        db.session.commit()
        flash("Đã duyệt bài viết.", "success")
    except MetaAPIError as e:
        flash(f"Lỗi khi gọi Facebook API: {e}", "error")

    return redirect(url_for("posts.list_posts"))


@posts_bp.route("/posts/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = db.session.get(Post, post_id) or abort(404)
    if post.author_id != current_user.id and not current_user.is_admin:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash("Đã xóa bài viết.", "success")
    return redirect(url_for("posts.list_posts"))


@posts_bp.route("/posts/sync-external", methods=["POST"])
@login_required
def sync_external():
    """Marks posts as scheduled/posted when they were published directly via
    the Graph API (bypassing the approve flow), so the dashboard reflects
    reality. Admin only. Body: [{post_id, fb_post_id, scheduled_time, status}]
    """
    if not current_user.is_admin:
        abort(403)
    entries = request.get_json(force=True)
    updated = 0
    for entry in entries:
        post = db.session.get(Post, entry["post_id"])
        if not post:
            continue
        post.fb_post_id = entry.get("fb_post_id")
        post.status = entry.get("status", "scheduled")
        if entry.get("scheduled_time"):
            post.scheduled_time = datetime.fromtimestamp(
                entry["scheduled_time"], tz=timezone.utc
            )
        post.approved_by_id = current_user.id
        updated += 1
    db.session.commit()
    return jsonify({"updated": updated})


@posts_bp.route("/calendar")
@login_required
def calendar_view():
    posts = (
        Post.query.filter(Post.status.in_(["scheduled", "posted"]))
        .order_by(Post.scheduled_time.asc())
        .all()
    )
    by_date = {}
    for p in posts:
        dt = p.scheduled_time or p.updated_at
        key = dt.strftime("%Y-%m-%d")
        by_date.setdefault(key, []).append(p)
    return render_template("calendar.html", by_date=sorted(by_date.items()))
