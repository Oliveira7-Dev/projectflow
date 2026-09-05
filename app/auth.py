import os
import re
import hashlib

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, current_user
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from . import db, limiter
from .models import User
from .email_service import send_email

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
RESET_TOKEN_MAX_AGE = 30 * 60  # 30 minutos


def valid_password(password: str) -> bool:
    return (
        len(password) >= 10
        and any(c.isupper() for c in password)
        and any(c.islower() for c in password)
        and any(c.isdigit() for c in password)
        and any(not c.isalnum() for c in password)
    )


def _serializer():
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"],
        salt="projectflow-password-reset-v1",
    )


def _password_fingerprint(user: User) -> str:
    # Vincula o token ao hash atual. Ao trocar a senha, tokens antigos deixam de valer.
    return hashlib.sha256(user.password_hash.encode("utf-8")).hexdigest()[:24]


def create_password_reset_token(user: User) -> str:
    return _serializer().dumps({
        "uid": user.id,
        "fp": _password_fingerprint(user),
    })


def verify_password_reset_token(token: str):
    try:
        data = _serializer().loads(token, max_age=RESET_TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None

    user = db.session.get(User, data.get("uid"))
    if not user:
        return None

    if data.get("fp") != _password_fingerprint(user):
        return None

    return user


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
            flash("A senha precisa ter no mínimo 10 caracteres, com maiúscula, minúscula, número e caractere especial.", "warning")
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


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("3 per 10 minutes", methods=["POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()[:180]

        # Resposta sempre igual para impedir enumeração de contas.
        generic_message = (
            "Se houver uma conta cadastrada com esse e-mail, "
            "você receberá um link para redefinir a senha."
        )

        if EMAIL_RE.match(email):
            user = User.query.filter_by(email=email).first()
            if user:
                token = create_password_reset_token(user)
                scheme = "https" if os.getenv("RENDER") else request.scheme
                reset_url = url_for(
                    "auth.reset_password",
                    token=token,
                    _external=True,
                    _scheme=scheme,
                )

                subject = "ProjectFlow - Redefinição de senha"
                body = f"""Olá, {user.name}.

Recebemos uma solicitação para redefinir sua senha do ProjectFlow.

Use o link abaixo:
{reset_url}

Este link expira em 30 minutos e deixa de funcionar após a senha ser alterada.

Se você não solicitou essa alteração, ignore este e-mail.

ProjectFlow
"""

                try:
                    send_email(user.email, subject, body)
                except Exception:
                    # Não expõe detalhes de SMTP ao usuário final.
                    current_app.logger.exception("Falha ao enviar e-mail de recuperação.")

        flash(generic_message, "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("5 per 10 minutes", methods=["POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    user = verify_password_reset_token(token)
    if not user:
        flash("Este link de recuperação é inválido ou expirou.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if password != confirm:
            flash("As senhas não coincidem.", "warning")
            return render_template("auth/reset_password.html", token=token)

        if not valid_password(password):
            flash(
                "A senha precisa ter no mínimo 10 caracteres, "
                "com maiúscula, minúscula, número e caractere especial.",
                "warning",
            )
            return render_template("auth/reset_password.html", token=token)

        user.set_password(password)
        db.session.commit()

        # O fingerprint muda junto com o hash, invalidando o token usado.
        session.clear()
        flash("Senha alterada com sucesso. Entre novamente.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", token=token)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("auth.login"))
