"""
Centralise la configuration FMP (Financial Modeling Prep).
Importer depuis ici plutôt que de redéfinir les constantes dans chaque module.
"""
import os

FMP_API_KEY   = os.getenv("FMP_API_KEY", "")
FMP_STABLE    = "https://financialmodelingprep.com/stable"
FMP_V3        = "https://financialmodelingprep.com/api/v3"

# ── Circuit breaker FMP — alertes email ──────────────────────────────────────
EQUITY_RISK_PREMIUM = 0.055  # prime de risque actions historique long terme

ALERT_EMAILS   = os.getenv("ALERT_EMAILS",   "mateo.bourrel@orange.fr,b00821404@essec.edu")
EMAIL_USER     = os.getenv("EMAIL_USER",     "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
