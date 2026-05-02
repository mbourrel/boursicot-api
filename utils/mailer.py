"""
Envoi d'emails HTML via Gmail SMTP (smtp.gmail.com:587 + STARTTLS).
Utilise EMAIL_USER / EMAIL_PASSWORD définis dans .env.
"""
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ALERT_EMAILS, EMAIL_USER, EMAIL_PASSWORD

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 587


def send_monitoring_email(subject: str, html_body: str) -> bool:
    """
    Envoie un email HTML à tous les destinataires de ALERT_EMAILS.

    Retourne True si l'envoi a réussi, False sinon.
    Les credentials ne sont jamais affichés dans les logs.
    """
    recipients = [e.strip() for e in (ALERT_EMAILS or "").split(",") if e.strip()]
    if not recipients:
        print("  [MAILER] Aucun destinataire configuré dans ALERT_EMAILS.")
        return False
    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("  [MAILER] EMAIL_USER ou EMAIL_PASSWORD manquant dans .env.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"Boursicot Pro <{EMAIL_USER}>"
    msg["To"]      = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, recipients, msg.as_string())
        print(f"  [MAILER] Email envoyé -> {', '.join(recipients)}")
        return True
    except Exception as e:
        # On n'affiche pas le mot de passe, juste le type d'erreur
        print(f"  [MAILER] Echec envoi : {type(e).__name__}: {e}")
        return False
