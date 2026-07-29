from flask import Blueprint, render_template, request
from flask_login import login_required

from meta_client import MetaAPIError, MetaClient
from models import Page

stats_bp = Blueprint("stats", __name__)

DEFAULT_METRICS = ["page_views_total", "page_post_engagements", "page_total_actions"]


@stats_bp.route("/stats")
@login_required
def stats_view():
    pages = Page.query.filter_by(is_active=True).order_by(Page.name).all()
    selected_id = request.args.get("page_id", type=int)
    selected = None
    if pages:
        selected = next((p for p in pages if p.id == selected_id), pages[0])

    insights = None
    error = None
    if selected:
        try:
            client = MetaClient(selected.fb_page_id, selected.access_token)
            data = client.get_page_insights(DEFAULT_METRICS, period="day")
            insights = data.get("data", [])
        except MetaAPIError as e:
            error = str(e)

    return render_template(
        "stats.html", pages=pages, selected=selected, insights=insights, error=error
    )
