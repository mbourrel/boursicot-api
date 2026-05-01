"""
Moteur de scoring Boursicot — 6 scores (0-10) + Note Globale + Verdict.

Scores :
  - health     : Santé financière (Marge Nette, ROE, Dette/FP, Ratio Liquidité)
  - valuation  : Valorisation (PER vs secteur, PER vs Forward PE)
  - growth     : Croissance (Croissance CA, Croissance Bénéfices)
  - dividend   : Dividende (payout_ratio, dividend_yield vs secteur)
  - momentum   : Momentum technique (Prix vs MM50/MM200, Golden/Death cross)
  - efficiency : Efficacité (ROE + Marge Nette vs secteur + tendance historique)
  - complexity : Complexité perçue (Market Cap, Beta) — élevé = plus avancé
  - verdict    : "Profil Fort" | "Profil Solide" | "Profil Neutre" | "Profil Prudent" | "Profil Fragile"

Pondérations Note Globale :
  health 25%  |  valuation 20%  |  growth 20%  |  efficiency 15%
  dividend 10%  |  momentum 10%
"""


# ── Scorabilité ───────────────────────────────────────────────────────────────

def is_scorable(ticker: str) -> bool:
    """
    Retourne True si le scoring fondamental est applicable à ce ticker.
    Indices (^), cryptos (-USD) et matières premières (=F) ne disposent pas
    des données fondamentales nécessaires (bilans, ratios, secteur) et ne
    doivent pas être scorés.
    """
    if ticker.startswith('^'):  return False  # Indices boursiers
    if '-USD' in ticker:        return False  # Cryptomonnaies
    if ticker.endswith('=F'):   return False  # Matières premières
    return True


# ── Utilitaires ────────────────────────────────────────────────────────────────

def _get_val(metrics_list, name: str):
    """Extrait la valeur d'une métrique par son nom depuis une liste JSON [{name, val, unit}]."""
    if not metrics_list:
        return None
    for m in metrics_list:
        if m.get("name") == name:
            v = m.get("val")
            if v is not None and v != 0:
                return float(v)
    return None


def _sector_avg(companies, cat: str, metric_name: str):
    """Calcule la moyenne sectorielle pour une métrique donnée sur une liste de sociétés."""
    vals = []
    for c in companies:
        metrics = getattr(c, cat, None) or []
        v = _get_val(metrics, metric_name)
        if v is not None:
            vals.append(v)
    return sum(vals) / len(vals) if vals else None


def _clamp(v: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, v))


def _ratio_score(company_val, sector_val, invert: bool = False, neutral: float = 5.0) -> float:
    """
    Score 0-10 basé sur le ratio entreprise / secteur.
    ratio = 1.0  →  score 5  (dans la moyenne sectorielle)
    ratio = 2.0  →  score 10 (deux fois mieux)
    Si invert=True, un ratio plus bas est meilleur (ex. Dette/Fonds Propres).
    """
    if company_val is None or sector_val is None or sector_val == 0:
        return neutral
    ratio = company_val / sector_val
    if invert:
        ratio = 1.0 / ratio if ratio != 0 else 10.0
    return _clamp(ratio * 5.0)


# ── Scores individuels ─────────────────────────────────────────────────────────

def _score_health(company, sector_companies: list) -> float:
    """Santé financière : Marge Nette, ROE, Dette/FP, Ratio Liquidité."""
    marge_nette = _get_val(company.financial_health, "Marge Nette")
    roe         = _get_val(company.financial_health, "ROE")
    dette_fp    = _get_val(company.financial_health, "Dette/Fonds Propres")
    ratio_liq   = _get_val(company.balance_cash,     "Ratio Liquidité")

    sect_marge = _sector_avg(sector_companies, "financial_health", "Marge Nette")
    sect_roe   = _sector_avg(sector_companies, "financial_health", "ROE")
    sect_dette = _sector_avg(sector_companies, "financial_health", "Dette/Fonds Propres")
    sect_liq   = _sector_avg(sector_companies, "balance_cash",     "Ratio Liquidité")

    parts = []
    if marge_nette is not None:
        parts.append(_ratio_score(marge_nette, sect_marge))
    if roe is not None:
        parts.append(_ratio_score(roe, sect_roe))
    if dette_fp is not None:
        parts.append(_ratio_score(dette_fp, sect_dette, invert=True))
    if ratio_liq is not None:
        parts.append(_ratio_score(ratio_liq, sect_liq))

    return round(sum(parts) / len(parts), 2) if parts else 5.0


def _score_valuation(company, sector_companies: list) -> float:
    """Valorisation : PER vs secteur, Forward PE vs PER."""
    per        = _get_val(company.market_analysis,    "PER")
    forward_pe = _get_val(company.advanced_valuation, "Forward PE")
    sect_per   = _sector_avg(sector_companies, "market_analysis", "PER")

    parts = []
    if per is not None and per > 0:
        parts.append(_ratio_score(per, sect_per, invert=True))
        if forward_pe is not None and forward_pe > 0:
            fwd_bonus = _clamp(5.0 + (per - forward_pe) / max(per, 1.0) * 5.0)
            parts.append(fwd_bonus)
    elif per is not None and per < 0:
        parts.append(2.0)

    return round(sum(parts) / len(parts), 2) if parts else 5.0


def _score_growth(company) -> float:
    """Croissance : Croissance CA et Bénéfices normalisées sur plages de marché."""
    crois_ca    = _get_val(company.income_growth, "Croissance CA")
    crois_benef = _get_val(company.income_growth, "Croissance Bénéfices")

    parts = []
    if crois_ca is not None:
        parts.append(_clamp((crois_ca + 20.0) / 50.0 * 10.0))
    if crois_benef is not None:
        parts.append(_clamp((crois_benef + 30.0) / 80.0 * 10.0))

    return round(sum(parts) / len(parts), 2) if parts else 5.0


def _score_dividend(company, sector_companies: list) -> float:
    """
    Dividende : payout_ratio (optimal 40-60%) + dividend_yield vs secteur.
    Les sociétés sans dividende reçoivent 5.0 (neutre) — ne pas pénaliser les growth stocks.
    """
    dd         = company.dividends_data or {}
    div_yield  = dd.get("dividend_yield")   # float %
    payout     = dd.get("payout_ratio")     # float %

    # Pas de dividende → score neutre
    no_yield   = div_yield is None or div_yield == 0
    no_payout  = payout is None or payout == 0
    if no_yield and no_payout:
        return 5.0

    parts = []

    # Score payout_ratio : optimal [40 %, 60 %]
    if payout is not None and payout > 0:
        if 40 <= payout <= 60:
            payout_score = 9.0
        elif payout < 40:
            # 0 % → 5.0, 40 % → 9.0
            payout_score = _clamp(5.0 + (payout / 40.0) * 4.0)
        elif payout <= 100:
            # 60 % → 9.0, 100 % → 2.0
            payout_score = _clamp(9.0 - ((payout - 60.0) / 40.0) * 7.0)
        else:
            # Payout > 100 % : non soutenable
            payout_score = 1.0
        parts.append(payout_score)

    # Score yield vs moyenne sectorielle
    sect_yields = []
    for c in sector_companies:
        cd = c.dividends_data or {}
        y  = cd.get("dividend_yield")
        if y is not None and y > 0:
            sect_yields.append(float(y))
    sect_yield = sum(sect_yields) / len(sect_yields) if sect_yields else None

    if div_yield is not None and div_yield > 0 and sect_yield:
        parts.append(_ratio_score(div_yield, sect_yield))

    return round(sum(parts) / len(parts), 2) if parts else 5.0


def _score_momentum(company) -> float:
    """
    Momentum technique : prix actuel vs MM50/MM200 + signal Golden/Death cross.
    Les champs MM50, MM200, Prix Actuel doivent être stockés dans risk_market.
    """
    price = _get_val(company.risk_market, "Prix Actuel")
    mm50  = _get_val(company.risk_market, "MM50")
    mm200 = _get_val(company.risk_market, "MM200")

    if price is None:
        return 5.0

    parts = []

    # Prix vs MM50 (tendance court terme)
    if mm50 is not None and mm50 > 0:
        ratio = price / mm50
        # ±5 % de déviation = ±1 point de score
        score = _clamp(5.0 + (ratio - 1.0) * 20.0)
        parts.append(score)

    # Prix vs MM200 (tendance long terme)
    if mm200 is not None and mm200 > 0:
        ratio = price / mm200
        score = _clamp(5.0 + (ratio - 1.0) * 15.0)
        parts.append(score)

    # Golden / Death cross : MM50 vs MM200
    if mm50 is not None and mm200 is not None and mm200 > 0:
        cross = mm50 / mm200
        if cross > 1.02:     # Golden cross → haussier
            parts.append(7.5)
        elif cross < 0.98:   # Death cross → baissier
            parts.append(2.5)
        else:                # Zone de transition
            parts.append(5.0)

    return round(sum(parts) / len(parts), 2) if parts else 5.0


def _score_efficiency(company, sector_companies: list) -> float:
    """
    Efficacité opérationnelle :
      - ROE et Marge Nette vs secteur (niveau actuel)
      - Tendance de la marge nette sur 5 ans (amélioration vs historique)
    """
    roe   = _get_val(company.financial_health, "ROE")
    marge = _get_val(company.financial_health, "Marge Nette")

    sect_roe   = _sector_avg(sector_companies, "financial_health", "ROE")
    sect_marge = _sector_avg(sector_companies, "financial_health", "Marge Nette")

    parts = []

    if roe is not None:
        parts.append(_ratio_score(roe, sect_roe))
    if marge is not None:
        parts.append(_ratio_score(marge, sect_marge))

    # Tendance historique : évolution de la marge nette sur income_stmt_data
    stmt = company.income_stmt_data
    if stmt:
        items    = stmt.get("items", [])
        rev_item = next((i for i in items if i["name"] == "Chiffre d'Affaires"), None)
        ni_item  = next((i for i in items if i["name"] == "Résultat Net"), None)

        if rev_item and ni_item:
            rev_vals = rev_item.get("vals", [])
            ni_vals  = ni_item.get("vals", [])
            margins  = []
            for r, n in zip(rev_vals, ni_vals):
                if r and r != 0 and n is not None:
                    margins.append(n / r * 100)

            if len(margins) >= 2:
                recent    = margins[0]
                older_avg = sum(margins[1:]) / len(margins[1:])
                if older_avg != 0:
                    improvement = (recent - older_avg) / abs(older_avg)
                    # +20 % d'amélioration → +1 point
                    trend_score = _clamp(5.0 + improvement * 5.0)
                    parts.append(trend_score)

    return round(sum(parts) / len(parts), 2) if parts else 5.0


def _score_complexity(company) -> float:
    """Complexité perçue : Market Cap (petite = complexe) + Beta (élevé = complexe)."""
    cap  = _get_val(company.market_analysis, "Capitalisation")
    beta = _get_val(company.risk_market,     "Beta")

    parts = []

    if cap is not None:
        if cap < 500e6:   parts.append(9.0)   # Micro/Small Cap
        elif cap < 2e9:   parts.append(7.0)   # Small/Mid Cap
        elif cap < 10e9:  parts.append(5.0)   # Mid Cap
        elif cap < 50e9:  parts.append(3.0)   # Large Cap
        else:             parts.append(1.5)   # Mega Cap

    if beta is not None:
        if beta > 2.0:    parts.append(9.0)
        elif beta > 1.5:  parts.append(7.0)
        elif beta > 1.0:  parts.append(5.0)
        elif beta > 0.5:  parts.append(3.0)
        else:             parts.append(1.5)

    return round(sum(parts) / len(parts), 2) if parts else 5.0


# ── Pondérations Note Globale ──────────────────────────────────────────────────

SCORE_WEIGHTS = {
    "health":     0.25,
    "valuation":  0.20,
    "growth":     0.20,
    "efficiency": 0.15,
    "dividend":   0.10,
    "momentum":   0.10,
}


# ── Calcul principal ───────────────────────────────────────────────────────────

def compute_scores(company, sector_companies: list) -> dict:
    """
    Calcule les 6 scores d'investissement + Note Globale + Verdict.

    Args:
        company         : instance models.Company
        sector_companies: liste de models.Company du même secteur

    Returns:
        dict {
          health, valuation, growth, dividend, momentum, efficiency,
          complexity, global_score, verdict
        }
    """
    health     = _score_health(company, sector_companies)
    valuation  = _score_valuation(company, sector_companies)
    growth     = _score_growth(company)
    dividend   = _score_dividend(company, sector_companies)
    momentum   = _score_momentum(company)
    efficiency = _score_efficiency(company, sector_companies)
    complexity = _score_complexity(company)

    # Note Globale pondérée
    global_score = round(
        health     * SCORE_WEIGHTS["health"]     +
        valuation  * SCORE_WEIGHTS["valuation"]  +
        growth     * SCORE_WEIGHTS["growth"]     +
        efficiency * SCORE_WEIGHTS["efficiency"] +
        dividend   * SCORE_WEIGHTS["dividend"]   +
        momentum   * SCORE_WEIGHTS["momentum"],
        2
    )

    # Verdict basé sur la Note Globale
    if global_score >= 7.5:   verdict = "Profil Fort"
    elif global_score >= 6.0: verdict = "Profil Solide"
    elif global_score >= 4.5: verdict = "Profil Neutre"
    elif global_score >= 3.0: verdict = "Profil Prudent"
    else:                     verdict = "Profil Fragile"

    return {
        "health":       health,
        "valuation":    valuation,
        "growth":       growth,
        "dividend":     dividend,
        "momentum":     momentum,
        "efficiency":   efficiency,
        "complexity":   complexity,
        "global_score": global_score,
        "verdict":      verdict,
    }
