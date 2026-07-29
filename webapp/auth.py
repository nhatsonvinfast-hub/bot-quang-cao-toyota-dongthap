from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from models import User, db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("posts.list_posts"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("posts.list_posts"))
        flash("Sai tên đăng nhập hoặc mật khẩu.", "error")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/users", methods=["GET", "POST"])
@login_required
def manage_users():
    if not current_user.is_admin:
        flash("Chỉ admin mới quản lý được người dùng.", "error")
        return redirect(url_for("posts.list_posts"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        display_name = request.form.get("display_name", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "composer")
        if User.query.filter_by(username=username).first():
            flash("Tên đăng nhập đã tồn tại.", "error")
        elif not username or not password:
            flash("Cần nhập tên đăng nhập và mật khẩu.", "error")
        else:
            u = User(username=username, display_name=display_name or username, role=role)
            u.set_password(password)
            db.session.add(u)
            db.session.commit()
            flash(f"Đã tạo tài khoản {username}.", "success")
        return redirect(url_for("auth.manage_users"))

    users = User.query.order_by(User.created_at).all()
    return render_template("users.html", users=users)
