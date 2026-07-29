from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from meta_client import MetaAPIError, MetaClient
from models import Page, db

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/settings/pages", methods=["GET", "POST"])
@login_required
def manage_pages():
    if not current_user.is_admin:
        abort(403)

    if request.method == "POST":
        fb_page_id = request.form.get("fb_page_id", "").strip()
        access_token = request.form.get("access_token", "").strip()

        if not fb_page_id or not access_token:
            flash("Cần nhập Page ID và Access Token.", "error")
            return redirect(url_for("pages.manage_pages"))

        try:
            info = MetaClient.verify_token(fb_page_id, access_token)
        except MetaAPIError as e:
            flash(f"Không xác thực được token: {e}", "error")
            return redirect(url_for("pages.manage_pages"))

        existing = Page.query.filter_by(fb_page_id=fb_page_id).first()
        if existing:
            existing.access_token = access_token
            existing.name = info.get("name", existing.name)
            existing.category = info.get("category", existing.category)
            flash(f"Đã cập nhật token cho Trang {existing.name}.", "success")
        else:
            page = Page(
                fb_page_id=fb_page_id,
                access_token=access_token,
                name=info.get("name", fb_page_id),
                category=info.get("category"),
            )
            db.session.add(page)
            flash(f"Đã thêm Trang {info.get('name')}.", "success")
        db.session.commit()
        return redirect(url_for("pages.manage_pages"))

    pages = Page.query.order_by(Page.created_at).all()
    return render_template("settings_pages.html", pages=pages)


@pages_bp.route("/settings/pages/<int:page_id>/toggle", methods=["POST"])
@login_required
def toggle_page(page_id):
    if not current_user.is_admin:
        abort(403)
    page = db.session.get(Page, page_id) or abort(404)
    page.is_active = not page.is_active
    db.session.commit()
    return redirect(url_for("pages.manage_pages"))
