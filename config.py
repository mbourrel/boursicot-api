"""
Centralise la configuration FMP (Financial Modeling Prep).
Importer depuis ici plutôt que de redéfinir les constantes dans chaque module.
"""
import os

FMP_API_KEY   = os.getenv("FMP_API_KEY", "")
FMP_STABLE    = "https://financialmodelingprep.com/stable"
FMP_V3        = "https://financialmodelingprep.com/api/v3"
