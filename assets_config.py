"""
Source unique de vérité pour le catalogue d'actifs de Boursicot.
Utilisé par :
  - les scripts de seeding (seed_utils.py → TICKERS)
  - l'endpoint /api/assets (frontend fetch au démarrage)
"""

# Ordre : CAC 40, Magnificient 7, Indices, Crypto, Matières premières
ASSET_DICTIONARY: dict[str, str] = {
    # ── CAC 40 ──────────────────────────────────────────────────────────────
    "AC.PA":     "Accor",
    "AI.PA":     "Air Liquide",
    "AIR.PA":    "Airbus",
    "MT.AS":     "ArcelorMittal",
    "CS.PA":     "AXA",
    "BNP.PA":    "BNP Paribas",
    "EN.PA":     "Bouygues",
    "BVI.PA":    "Bureau Veritas",
    "CAP.PA":    "Capgemini",
    "CA.PA":     "Carrefour",
    "ACA.PA":    "Crédit Agricole",
    "BN.PA":     "Danone",
    "DSY.PA":    "Dassault Systèmes",
    "ENGI.PA":   "Engie",
    "EL.PA":     "EssilorLuxottica",
    "ERF.PA":    "Eurofins Scientific",
    "ENX.PA":    "Euronext",
    "RMS.PA":    "Hermès",
    "KER.PA":    "Kering",
    "OR.PA":     "L'Oréal",
    "LR.PA":     "Legrand",
    "MC.PA":     "LVMH",
    "ML.PA":     "Michelin",
    "ORA.PA":    "Orange",
    "RI.PA":     "Pernod Ricard",
    "PUB.PA":    "Publicis",
    "RNO.PA":    "Renault",
    "SAF.PA":    "Safran",
    "SGO.PA":    "Saint-Gobain",
    "SAN.PA":    "Sanofi",
    "SU.PA":     "Schneider Electric",
    "GLE.PA":    "Société Générale",
    "STLAP.PA":  "Stellantis",
    "STMPA.PA":  "STMicroelectronics",
    "HO.PA":     "Thales",
    "TTE.PA":    "TotalEnergies",
    "URW.PA":    "Unibail-Rodamco-Westfield",
    "VIE.PA":    "Veolia",
    "DG.PA":     "Vinci",
    # ── Actions bonus ───────────────────────────────────────────────────────
    "ABVX.PA":   "Abivax",
    "DIM.PA":    "Sartorius Stedim Biotech",
    # ── Les 7 Fantastiques (Magnificent 7) ──────────────────────────────────
    "AAPL":  "Apple",
    "MSFT":  "Microsoft",
    "GOOGL": "Alphabet",
    "AMZN":  "Amazon",
    "META":  "Meta",
    "NVDA":  "NVIDIA",
    "TSLA":  "Tesla",
    # ── Indices ──────────────────────────────────────────────────────────────
    "^STOXX":   "STOXX Europe 600",
    "^GSPC":    "S&P 500",
    "^IXIC":    "Nasdaq Composite",
    "^DJI":     "Dow Jones",
    "^STOXX50E":"Euro Stoxx 50",
    "^N225":    "Nikkei 225",
    "^VIX":     "VIX Volatility Index",
    # ── Crypto ───────────────────────────────────────────────────────────────
    "BTC-USD":  "Bitcoin",
    # ── Métaux précieux ───────────────────────────────────────────────────────
    "GC=F": "Or (Gold)",
    "SI=F": "Argent (Silver)",
    # ── Énergie ──────────────────────────────────────────────────────────────
    "CL=F": "Pétrole Brut WTI",
    "BZ=F": "Pétrole Brent",
    "NG=F": "Gaz Naturel",
    # ── Matières premières agricoles ─────────────────────────────────────────
    "ZC=F": "Maïs (Corn)",
    "ZW=F": "Blé (Wheat)",
    "CT=F": "Coton",
}

# Liste de tickers dérivée — utilisée par les scripts de seeding
TICKERS: list[str] = list(ASSET_DICTIONARY.keys())
