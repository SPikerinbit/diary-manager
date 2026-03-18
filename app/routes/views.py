# routes/views.py
import os
from flask import Response

from app.routes import views_bp
from app.config import BASE_DIR


@views_bp.route("/")
def index():
    """主页 - Apple风格仪表盘"""
    html_path = BASE_DIR / "templates" / "index.html"
    with open(html_path, "r", encoding="utf-8") as f:
        return Response(f.read(), mimetype="text/html")
