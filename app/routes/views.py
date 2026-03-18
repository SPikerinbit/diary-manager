# routes/views.py
from flask import render_template

from app.routes import views_bp


@views_bp.route("/")
def index():
    """主页"""
    return render_template("index.html")


@views_bp.route("/statistics")
def statistics():
    """统计页面"""
    return render_template("statistics.html")


@views_bp.route("/weekly")
def weekly():
    """周报页面"""
    return render_template("weekly.html")


@views_bp.route("/files")
def files():
    """文件管理页面"""
    return render_template("files.html")


@views_bp.route("/settings")
def settings():
    """设置页面"""
    return render_template("settings.html")
