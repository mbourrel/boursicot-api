"""
Compteur journalier des requêtes FMP avec alertes email et circuit breaker.
Stockage : table api_quotas sur Neon (PostgreSQL). Reset automatique à minuit.

Seuils :
  - 210 appels (85 %) -> alerte email d'avertissement
  - 245 appels (98 %) -> alerte email critique + circuit breaker activé
"""
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models import ApiQuota

THRESHOLD_ALERT   = 210
THRESHOLD_BLOCKED = 245
FMP_DAILY_LIMIT   = 250


def _get_or_create_today(db) -> ApiQuota:
    today = date.today()
    quota = db.query(ApiQuota).filter(ApiQuota.date == today).first()
    if not quota:
        quota = ApiQuota(date=today, call_count=0, alert_85_sent=False, alert_98_sent=False)
        db.add(quota)
        db.commit()
        db.refresh(quota)
    return quota


def get_count() -> int:
    """Retourne le nombre d'appels FMP effectués aujourd'hui."""
    db = SessionLocal()
    try:
        quota = db.query(ApiQuota).filter(ApiQuota.date == date.today()).first()
        return quota.call_count if quota else 0
    finally:
        db.close()


def check_and_increment() -> tuple[str, int]:
    """
    Doit être appelé avant chaque requête FMP.

    Retourne :
        ('ok',      count) — appel autorisé
        ('alert',   count) — appel autorisé, seuil d'alerte atteint (email envoyé)
        ('blocked', count) — appel bloqué, circuit breaker actif
    """
    db = SessionLocal()
    try:
        quota = _get_or_create_today(db)

        # ── Circuit Breaker ────────────────────────────────────────────────────
        if quota.call_count >= THRESHOLD_BLOCKED:
            count = quota.call_count
            print(
                f"  [FMP CIRCUIT BREAKER] Appel bloqué — "
                f"{count}/{FMP_DAILY_LIMIT} appels aujourd'hui. "
                f"Les prix en base restent inchangés."
            )
            return "blocked", count

        # ── Incrément ─────────────────────────────────────────────────────────
        quota.call_count += 1
        quota.updated_at  = datetime.utcnow()
        count             = quota.call_count

        # ── Seuils (flag saved BEFORE sending email to avoid double-send) ────
        status = "ok"

        if count >= THRESHOLD_BLOCKED and not quota.alert_98_sent:
            quota.alert_98_sent = True
            db.commit()
            _fire_alert_98(count)
            status = "alert"
        elif count >= THRESHOLD_ALERT and not quota.alert_85_sent:
            quota.alert_85_sent = True
            db.commit()
            _fire_alert_85(count)
            status = "alert"
        else:
            db.commit()

        return status, count
    finally:
        db.close()


# ── Templates email ────────────────────────────────────────────────────────────

def _fire_alert_85(count: int) -> None:
    from utils.mailer import send_monitoring_email

    pct     = round(count / FMP_DAILY_LIMIT * 100)
    subject = "[Boursicot Pro] Alerte Quota FMP : 85% consommé"
    html    = f"""
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:auto;padding:24px">
  <h2 style="color:#D97706;border-bottom:2px solid #F59E0B;padding-bottom:10px;margin-bottom:20px">
    ⚠️&nbsp; Alerte Quota FMP — 85% consommé
  </h2>
  <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
    <tr style="background:#FFFBEB">
      <td style="padding:12px 16px;border:1px solid #FCD34D;font-weight:bold;width:55%">
        Appels effectués aujourd'hui
      </td>
      <td style="padding:12px 16px;border:1px solid #FCD34D;font-size:1.5em;font-weight:bold;color:#D97706">
        {count}&thinsp;/&thinsp;{FMP_DAILY_LIMIT}
      </td>
    </tr>
    <tr>
      <td style="padding:10px 16px;border:1px solid #e5e7eb">Consommation</td>
      <td style="padding:10px 16px;border:1px solid #e5e7eb;font-weight:bold">{pct}%</td>
    </tr>
    <tr>
      <td style="padding:10px 16px;border:1px solid #e5e7eb">Seuil de blocage (circuit breaker)</td>
      <td style="padding:10px 16px;border:1px solid #e5e7eb">{THRESHOLD_BLOCKED} appels (98%)</td>
    </tr>
    <tr>
      <td style="padding:10px 16px;border:1px solid #e5e7eb">Appels restants avant blocage</td>
      <td style="padding:10px 16px;border:1px solid #e5e7eb;font-weight:bold;color:#D97706">
        {THRESHOLD_BLOCKED - count} appels
      </td>
    </tr>
  </table>
  <p style="color:#555;font-size:13px;line-height:1.6">
    Si le cron du soir est déclenché dans cet état, le circuit breaker s'activera avant la fin du run.
    Les prix en base resteront ceux du dernier run réussi.
  </p>
  <p style="color:#999;font-size:11px;border-top:1px solid #eee;padding-top:12px;margin-top:20px">
    Boursicot Pro — Monitoring automatique FMP · Reset à minuit UTC
  </p>
</body>
</html>"""
    send_monitoring_email(subject, html)


def _fire_alert_98(count: int) -> None:
    from utils.mailer import send_monitoring_email

    pct     = round(count / FMP_DAILY_LIMIT * 100)
    subject = "[Boursicot Pro] CRITIQUE — Circuit Breaker FMP activé (98% quota)"
    html    = f"""
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:auto;padding:24px">
  <h2 style="color:#DC2626;border-bottom:2px solid #EF4444;padding-bottom:10px;margin-bottom:20px">
    🚨&nbsp; Circuit Breaker FMP activé
  </h2>
  <div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:6px;padding:14px 18px;margin-bottom:20px">
    <strong>Tous les appels FMP sont désormais bloqués</strong> pour le reste de la journée.<br>
    L'application continue de fonctionner avec les derniers prix enregistrés en base de données.
  </div>
  <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
    <tr style="background:#FEE2E2">
      <td style="padding:12px 16px;border:1px solid #FECACA;font-weight:bold;width:55%">
        Appels effectués aujourd'hui
      </td>
      <td style="padding:12px 16px;border:1px solid #FECACA;font-size:1.5em;font-weight:bold;color:#DC2626">
        {count}&thinsp;/&thinsp;{FMP_DAILY_LIMIT}
      </td>
    </tr>
    <tr>
      <td style="padding:10px 16px;border:1px solid #e5e7eb">Consommation</td>
      <td style="padding:10px 16px;border:1px solid #e5e7eb;font-weight:bold">{pct}%</td>
    </tr>
    <tr>
      <td style="padding:10px 16px;border:1px solid #e5e7eb">Statut circuit breaker</td>
      <td style="padding:10px 16px;border:1px solid #e5e7eb;font-weight:bold;color:#DC2626">
        ACTIF — appels bloqués
      </td>
    </tr>
    <tr>
      <td style="padding:10px 16px;border:1px solid #e5e7eb">Réinitialisation automatique</td>
      <td style="padding:10px 16px;border:1px solid #e5e7eb">Minuit UTC</td>
    </tr>
  </table>
  <p style="color:#999;font-size:11px;border-top:1px solid #eee;padding-top:12px;margin-top:20px">
    Boursicot Pro — Monitoring automatique FMP · Reset à minuit UTC
  </p>
</body>
</html>"""
    send_monitoring_email(subject, html)
