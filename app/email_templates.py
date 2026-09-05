from html import escape


def _base_email(title: str, intro: str, button_text: str, action_url: str,
                info_text: str, footer_text: str) -> str:
    title = escape(title)
    intro = escape(intro)
    button_text = escape(button_text)
    action_url = escape(action_url, quote=True)
    info_text = escape(info_text)
    footer_text = escape(footer_text)

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#0b1020;font-family:Arial,Helvetica,sans-serif;color:#eef2ff;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
         style="width:100%;background:#0b1020;margin:0;padding:0;">
    <tr>
      <td align="center" style="padding:36px 16px;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
               style="max-width:600px;background:#11182c;border:1px solid #26314f;border-radius:20px;overflow:hidden;">

          <tr>
            <td style="padding:28px 30px 18px;text-align:center;background:#0e1529;">
              <div style="font-size:26px;font-weight:800;color:#ffffff;letter-spacing:-0.5px;">
                ⚡ ProjectFlow
              </div>
              <div style="margin-top:7px;font-size:13px;color:#8f9ab0;">
                Gerencie seus projetos com segurança.
              </div>
            </td>
          </tr>

          <tr>
            <td style="padding:34px 30px 12px;text-align:center;">
              <div style="width:64px;height:64px;line-height:64px;margin:0 auto 18px;
                          border-radius:18px;background:#6d5dfc;font-size:30px;">
                ✓
              </div>
              <h1 style="margin:0 0 14px;font-size:28px;line-height:1.2;color:#ffffff;">
                {title}
              </h1>
              <p style="margin:0 auto;max-width:470px;font-size:16px;line-height:1.65;color:#a6b0c4;">
                {intro}
              </p>
            </td>
          </tr>

          <tr>
            <td align="center" style="padding:24px 30px;">
              <a href="{action_url}"
                 style="display:inline-block;background:#6d5dfc;color:#ffffff;text-decoration:none;
                        font-size:16px;font-weight:700;padding:15px 26px;border-radius:12px;
                        box-shadow:0 10px 30px rgba(109,93,252,.28);">
                {button_text}
              </a>
            </td>
          </tr>

          <tr>
            <td style="padding:0 30px 26px;">
              <div style="padding:15px 17px;border:1px solid #26314f;border-radius:12px;
                          background:#0d1427;color:#8f9ab0;font-size:13px;line-height:1.55;">
                🔒 {info_text}
              </div>
            </td>
          </tr>

          <tr>
            <td style="padding:0 30px 28px;">
              <p style="margin:0 0 10px;font-size:12px;line-height:1.55;color:#707d97;text-align:center;">
                Se o botão não funcionar, copie e cole este endereço no navegador:
              </p>
              <div style="word-break:break-all;font-size:11px;line-height:1.5;color:#8e82ff;
                          padding:12px;border-radius:10px;background:#0b1122;border:1px solid #202a46;">
                {action_url}
              </div>
            </td>
          </tr>

          <tr>
            <td style="padding:20px 30px 28px;border-top:1px solid #202a46;text-align:center;">
              <p style="margin:0;font-size:12px;line-height:1.6;color:#69758d;">
                {footer_text}
              </p>
              <p style="margin:10px 0 0;font-size:11px;color:#56627a;">
                © ProjectFlow
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def verification_email_html(user_name: str, verify_url: str) -> str:
    name = escape(user_name)
    return _base_email(
        title="Confirme seu e-mail",
        intro=f"Olá, {name}! Falta só um passo para ativar sua conta. "
              "Clique no botão abaixo para confirmar que este endereço de e-mail pertence a você.",
        button_text="Confirmar meu e-mail",
        action_url=verify_url,
        info_text="Este link expira em 24 horas. Após a confirmação, seu acesso ao ProjectFlow será liberado.",
        footer_text="Se você não criou uma conta no ProjectFlow, pode ignorar este e-mail com segurança.",
    )


def password_reset_email_html(user_name: str, reset_url: str) -> str:
    name = escape(user_name)
    return _base_email(
        title="Redefina sua senha",
        intro=f"Olá, {name}! Recebemos uma solicitação para alterar a senha da sua conta. "
              "Use o botão abaixo para criar uma nova senha.",
        button_text="Redefinir minha senha",
        action_url=reset_url,
        info_text="Este link expira em 30 minutos e deixa de funcionar assim que sua senha for alterada.",
        footer_text="Se você não solicitou uma nova senha, ignore este e-mail. Sua senha atual continuará funcionando.",
    )
