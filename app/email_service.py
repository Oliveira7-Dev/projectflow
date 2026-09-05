import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr


def _as_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def send_email(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> None:
    host = (os.getenv("SMTP_HOST") or "").strip()
    port = int((os.getenv("SMTP_PORT") or "587").strip())
    username = (os.getenv("SMTP_USER") or "").strip()
    password = os.getenv("SMTP_PASSWORD") or ""
    from_email = (os.getenv("SMTP_FROM") or "").strip()
    from_name = (os.getenv("SMTP_FROM_NAME") or "ProjectFlow").strip()

    use_ssl = _as_bool("SMTP_USE_SSL", default=(port == 465))
    use_tls = _as_bool("SMTP_USE_TLS", default=not use_ssl)
    timeout = int((os.getenv("SMTP_TIMEOUT") or "20").strip())

    missing = []
    if not host:
        missing.append("SMTP_HOST")
    if not username:
        missing.append("SMTP_USER")
    if not password:
        missing.append("SMTP_PASSWORD")
    if not from_email:
        missing.append("SMTP_FROM")

    if missing:
        raise RuntimeError(
            "Configuração SMTP incompleta. Faltando: " + ", ".join(missing)
        )

    if use_ssl and use_tls:
        raise RuntimeError(
            "Use apenas um modo SMTP: SMTP_USE_SSL=true OU SMTP_USE_TLS=true."
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((from_name, from_email))
    msg["To"] = to_email
    msg.set_content(text_body)

    if html_body:
        msg.add_alternative(html_body, subtype="html")

    tls_context = ssl.create_default_context()

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(
                host,
                port,
                timeout=timeout,
                context=tls_context,
            ) as smtp:
                smtp.login(username, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                smtp.ehlo()
                if use_tls:
                    smtp.starttls(context=tls_context)
                    smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(msg)
    except smtplib.SMTPAuthenticationError as exc:
        raise RuntimeError(
            "Falha na autenticação SMTP. Confira SMTP_USER e SMTP_PASSWORD."
        ) from exc
    except smtplib.SMTPSenderRefused as exc:
        raise RuntimeError(
            "O remetente SMTP_FROM foi recusado. No Brevo, ele precisa estar "
            "cadastrado/verificado em Senders & IP."
        ) from exc
    except smtplib.SMTPRecipientsRefused as exc:
        raise RuntimeError("O servidor SMTP recusou o destinatário.") from exc
    except (smtplib.SMTPException, OSError) as exc:
        raise RuntimeError(f"Falha ao enviar e-mail via SMTP: {exc}") from exc
