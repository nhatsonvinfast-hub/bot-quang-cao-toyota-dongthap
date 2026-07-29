import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user

import config
from models import Page, User, db


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Vui lòng đăng nhập để tiếp tục."
    login_manager.login_message_category = "warning"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from auth import auth_bp
    from pages_bp import pages_bp
    from posts import posts_bp
    from stats_bp import stats_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(stats_bp)

    @app.route("/")
    def index():
        return redirect(url_for("posts.list_posts"))

    @app.context_processor
    def inject_sidebar_pages():
        if current_user.is_authenticated:
            return {"pages_sidebar": Page.query.order_by(Page.name).all()}
        return {"pages_sidebar": []}

    with app.app_context():
        db.create_all()
        from seed import ensure_seed_data

        ensure_seed_data()

    if not config.IS_SERVERLESS:
        # Vercel functions are short-lived per request; a background thread
        # here would not run reliably, so the auto-publish job only starts
        # when this app runs as a normal long-lived process.
        from scheduler_job import start_scheduler

        start_scheduler(app)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, use_reloader=False, port=5000)
