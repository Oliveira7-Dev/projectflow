import os
import re
import hashlib

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, current_user
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from . import db, limiter
from .models import User
from .email_service import send_email
from .email_templates import verification_email_html, password_reset_email_html

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
RESET_TOKEN_MAX_AGE = 30 * 60  # 30 minutos
EMAIL_VERIFY_MAX_AGE = 24 * 60 * 60  # 24 horas


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



def _email_serializer():
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"],
        salt="projectflow-email-verification-v1",
    )


def create_email_verification_token(user: User) -> str:
    return _email_serializer().dumps({
        "uid": user.id,
        "email": user.email,
    })


def verify_email_token(token: str):
    try:
        data = _email_serializer().loads(token, max_age=EMAIL_VERIFY_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None

    user = db.session.get(User, data.get("uid"))
    if not user:
        return None

    if user.email != data.get("email"):
        return None

    return user


def send_verification_email(user: User) -> None:
    token = create_email_verification_token(user)
    scheme = "https" if os.getenv("RENDER") else request.scheme
    verify_url = url_for(
        "auth.verify_email",
        token=token,
        _external=True,
        _scheme=scheme,
    )

    subject = "ProjectFlow - Confirme seu e-mail"
    body = f"""Olá, {user.name}.

Confirme seu endereço de e-mail para ativar sua conta no ProjectFlow:

{verify_url}

Este link expira em 24 horas.

Se você não criou esta conta, ignore esta mensagem.

ProjectFlow
"""
    html = verification_email_html(user.name, verify_url)
    send_email(user.email, subject, body, html)


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
            if not user.is_verified:
                flash(
                    "Seu e-mail ainda não foi confirmado. "
                    "Confirme o endereço antes de entrar.",
                    "warning",
                )
                return redirect(url_for("auth.resend_verification"))

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
            return render_template(
                "auth/register.html",
                form_name=name,
                form_email=email,
            )

        if not valid_password(password):
            flash("A senha precisa ter no mínimo 10 caracteres, com maiúscula, minúscula, número e caractere especial.", "warning")
            return render_template(
                "auth/register.html",
                form_name=name,
                form_email=email,
            )

        if User.query.filter_by(email=email).first():
            flash(
                "Este e-mail já está cadastrado. Use outro e-mail ou entre na sua conta.",
                "danger",
            )
            return render_template(
                "auth/register.html",
                email_error="Este e-mail já foi usado.",
                form_name=name,
                form_email=email,
            )

        user = User(name=name, email=email, is_verified=False)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        try:
            send_verification_email(user)
        except Exception:
            current_app.logger.exception("Falha ao enviar e-mail de verificação.")
            flash(
                "Conta criada, mas não foi possível enviar o e-mail agora. "
                "Use a opção de reenviar confirmação.",
                "warning",
            )
            return redirect(url_for("auth.resend_verification"))

        flash(
            "Conta criada. Enviamos um link de confirmação para seu e-mail. "
            "Confirme-o antes de entrar.",
            "success",
        )
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")



@auth_bp.route("/verify-email/<token>")
def verify_email(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    user = verify_email_token(token)
    if not user:
        flash("O link de confirmação é inválido ou expirou.", "danger")
        return redirect(url_for("auth.resend_verification"))

    if user.is_verified:
        flash("Este e-mail já foi confirmado. Você já pode entrar.", "success")
        return redirect(url_for("auth.login"))

    user.is_verified = True
    db.session.commit()

    flash("E-mail confirmado com sucesso. Sua conta está ativa.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/resend-verification", methods=["GET", "POST"])
@limiter.limit("3 per 15 minutes", methods=["POST"])
def resend_verification():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()[:180]

        # Resposta genérica para reduzir enumeração de contas.
        generic_message = (
            "Se existir uma conta pendente para esse e-mail, "
            "um novo link de confirmação será enviado."
        )

        if EMAIL_RE.match(email):
            user = User.query.filter_by(email=email).first()
            if user and not user.is_verified:
                try:
                    send_verification_email(user)
                except Exception:
                    current_app.logger.exception(
                        "Falha ao reenviar e-mail de verificação."
                    )

        flash(generic_message, "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/resend_verification.html")


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
                    html = password_reset_email_html(user.name, reset_url)
                    send_email(user.email, subject, body, html)
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
