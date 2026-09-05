import os
from datetime import timedelta

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy import inspect, text

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "60 per hour"])
talisman = Talisman()

def create_app():
    app = Flask(__name__)

    database_url = os.getenv("DATABASE_URL", "sqlite:///projectflow.db")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    secret_key = os.getenv("SECRET_KEY")
    if not secret_key and os.getenv("RENDER"):
        raise RuntimeError("SECRET_KEY não configurada no ambiente de produção.")

    app.config.update(
        SECRET_KEY=secret_key or "dev-only-change-me",
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=bool(os.getenv("RENDER")),
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SAMESITE="Lax",
        REMEMBER_COOKIE_SECURE=bool(os.getenv("RENDER")),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    )

    # Render/proxies: respeita HTTPS original com segurança.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Security headers. CSP liberando apenas recursos usados pelo projeto.
    csp = {
        "default-src": ["'self'"],
        "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "img-src": ["'self'", "data:"],
        "script-src": ["'self'", "'unsafe-inline'"],
        "connect-src": ["'self'"],
        "object-src": ["'none'"],
        "frame-ancestors": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
    }

    talisman.init_app(
        app,
        content_security_policy=csp,
        force_https=bool(os.getenv("RENDER")),
        strict_transport_security=bool(os.getenv("RENDER")),
        strict_transport_security_max_age=31536000,
        strict_transport_security_include_subdomains=True,
        frame_options="DENY",
        referrer_policy="strict-origin-when-cross-origin",
    )

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Faça login para continuar."
    login_manager.login_message_category = "warning"

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    from .auth import auth_bp
    from .main import main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()

        # Migração leve para bancos já existentes.
        # Usuários antigos são considerados verificados para não perderem acesso.
        inspector = inspect(db.engine)
        if "user" in inspector.get_table_names():
            columns = {col["name"] for col in inspector.get_columns("user")}
            if "is_verified" not in columns:
                db.session.execute(
                    text('ALTER TABLE "user" ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT TRUE')
                )
                db.session.commit()

    return app
