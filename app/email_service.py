import os
import smtplib
from email.message import EmailMessage


def send_email(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> None:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM") or username
    from_name = os.getenv("SMTP_FROM_NAME", "ProjectFlow")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    if not all([host, username, password, from_email]):
        raise RuntimeError("SMTP não configurado.")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email

    # Fallback para clientes de e-mail sem suporte a HTML.
    msg.set_content(text_body)

    if html_body:
        msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(host, port, timeout=15) as smtp:
        smtp.ehlo()
        if use_tls:
            smtp.starttls()
            smtp.ehlo()
        smtp.login(username, password)
        smtp.send_message(msg)
