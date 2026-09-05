import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user
from . import db, limiter
from .models import User

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

def valid_password(password: str) -> bool:
    return (
        len(password) >= 10
        and any(c.isupper() for c in password)
        and any(c.islower() for c in password)
        and any(c.isdigit() for c in password)
    )

@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()[:180]
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session.clear()
            login_user(user, remember=False, fresh=True)
            session.permanent = True
            return redirect(url_for("main.dashboard"))

        # Mensagem genérica evita revelar se o e-mail existe.
        flash("E-mail ou senha inválidos.", "danger")

    return render_template("auth/login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("3 per minute", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()[:120]
        email = request.form.get("email", "").strip().lower()[:180]
        password = request.form.get("password", "")

        if len(name) < 2 or not EMAIL_RE.match(email):
            flash("Nome ou e-mail inválido.", "warning")
            return render_template("auth/register.html")

        if not valid_password(password):
            flash("A senha precisa ter no mínimo 10 caracteres, com maiúscula, minúscula e número.", "warning")
            return render_template("auth/register.html")

        if User.query.filter_by(email=email).first():
            flash("Não foi possível concluir o cadastro com esses dados.", "warning")
            return render_template("auth/register.html")

        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        session.clear()
        login_user(user, remember=False, fresh=True)
        session.permanent = True
        return redirect(url_for("main.dashboard"))

    return render_template("auth/register.html")

@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("auth.login"))
