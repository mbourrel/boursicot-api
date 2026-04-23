"""
Moteur de scoring Boursicot — Option A : Score de Lisibilité et Performance.

Calcule 4 scores (0-10) + un verdict textuel pour aider les investisseurs débutants
à interpréter les données fondamentales d'une entreprise.

Scores :
  - health     : Santé financière (Marge Nette, ROE, Dette/FP, Ratio Liquidité)
  - valuation  : Valorisation (PER vs secteur, PER vs Forward PE)
  - growth     : Croissance (Croissance CA, Croissance Bénéfices)
  - complexity : Complexité perçue (Market Cap, Beta) — élevé = plus avancé
  - verdict    : "Excellent" | "Bon" | "Correct" | "Risqué" | "À éviter"
"""


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
    ratio = 0.5  →  score 2.5

    Si invert=True, un ratio plus bas est meilleur (ex. Dette/Fonds Propres).
    """
    if company_val is None or sector_val is None or sector_val == 0:
        return neutral
    ratio = company_val / sector_val
    if invert:
        ratio = 1.0 / ratio if ratio != 0 else 10.0
    return _clamp(ratio * 5.0)


# ── Calcul principal ───────────────────────────────────────────────────────────

def compute_scores(company, sector_companies: list) -> dict:
    """
    Calcule les scores d'investissement pour une entreprise.

    Args:
        company         : instance models.Company
        sector_companies: liste de models.Company du même secteur (peut inclure l'entreprise elle-même)

    Returns:
        dict { "health", "valuation", "growth", "complexity", "verdict" }
    """

    # ── SANTÉ FINANCIÈRE (0-10) ──────────────────────────────────────────────
    # Indicateurs : Marge Nette (+), ROE (+), Dette/Fonds Propres (-), Ratio Liquidité (+)

    marge_nette = _get_val(company.financial_health, "Marge Nette")
    roe         = _get_val(company.financial_health, "ROE")
    dette_fp    = _get_val(company.financial_health, "Dette/Fonds Propres")
    ratio_liq   = _get_val(company.balance_cash,     "Ratio Liquidité")

    sect_marge  = _sector_avg(sector_companies, "financial_health", "Marge Nette")
    sect_roe    = _sector_avg(sector_companies, "financial_health", "ROE")
    sect_dette  = _sector_avg(sector_companies, "financial_health", "Dette/Fonds Propres")
    sect_liq    = _sector_avg(sector_companies, "balance_cash",     "Ratio Liquidité")

    health_parts = []
    if marge_nette is not None:
        health_parts.append(_ratio_score(marge_nette, sect_marge, invert=False))
    if roe is not None:
        health_parts.append(_ratio_score(roe, sect_roe, invert=False))
    if dette_fp is not None:
        health_parts.append(_ratio_score(dette_fp, sect_dette, invert=True))
    if ratio_liq is not None:
        health_parts.append(_ratio_score(ratio_liq, sect_liq, invert=False))

    health = round(sum(health_parts) / len(health_parts), 2) if health_parts else 5.0

    # ── VALORISATION (0-10) ─────────────────────────────────────────────────
    # Indicateurs : PER vs secteur (faible = bon), Forward PE vs PER actuel

    per        = _get_val(company.market_analysis,    "PER")
    forward_pe = _get_val(company.advanced_valuation, "Forward PE")
    sect_per   = _sector_avg(sector_companies, "market_analysis", "PER")

    val_parts = []

    if per is not None and per > 0:
        # PER faible par rapport au secteur = score élevé
        val_parts.append(_ratio_score(per, sect_per, invert=True))

        # Forward PE < PER actuel → les analystes anticipent une croissance des bénéfices
        if forward_pe is not None and forward_pe > 0:
            # Plus forward_pe est bas vs per, meilleur le signal
            fwd_bonus = _clamp(5.0 + (per - forward_pe) / max(per, 1.0) * 5.0)
            val_parts.append(fwd_bonus)

    elif per is not None and per < 0:
        # PER négatif = pertes en cours → signal défavorable
        val_parts.append(2.0)

    valuation = round(sum(val_parts) / len(val_parts), 2) if val_parts else 5.0

    # ── CROISSANCE (0-10) ────────────────────────────────────────────────────
    # Indicateurs : Croissance CA (%), Croissance Bénéfices (%)
    # Plages de normalisation calibrées sur le marché actions :
    #   CA        : [-20 %, +30 %]  →  0-10
    #   Bénéfices : [-30 %, +50 %]  →  0-10

    crois_ca    = _get_val(company.income_growth, "Croissance CA")
    crois_benef = _get_val(company.income_growth, "Croissance Bénéfices")

    growth_parts = []
    if crois_ca is not None:
        growth_parts.append(_clamp((crois_ca + 20.0) / 50.0 * 10.0))
    if crois_benef is not None:
        growth_parts.append(_clamp((crois_benef + 30.0) / 80.0 * 10.0))

    growth = round(sum(growth_parts) / len(growth_parts), 2) if growth_parts else 5.0

    # ── COMPLEXITÉ (0-10) ────────────────────────────────────────────────────
    # Score élevé = titre plus difficile à analyser pour un débutant.
    # Indicateurs : Capitalisation (petite = complexe/risqué), Beta (volatil = complexe)

    cap  = _get_val(company.market_analysis, "Capitalisation")
    beta = _get_val(company.risk_market,     "Beta")

    complexity_parts = []

    if cap is not None:
        if cap < 500e6:    cap_score = 9.0   # Micro/Small Cap
        elif cap < 2e9:    cap_score = 7.0   # Small/Mid Cap
        elif cap < 10e9:   cap_score = 5.0   # Mid Cap
        elif cap < 50e9:   cap_score = 3.0   # Large Cap
        else:              cap_score = 1.5   # Mega Cap
        complexity_parts.append(cap_score)

    if beta is not None:
        if beta > 2.0:     beta_score = 9.0
        elif beta > 1.5:   beta_score = 7.0
        elif beta > 1.0:   beta_score = 5.0
        elif beta > 0.5:   beta_score = 3.0
        else:              beta_score = 1.5
        complexity_parts.append(beta_score)

    complexity = round(sum(complexity_parts) / len(complexity_parts), 2) if complexity_parts else 5.0

    # ── VERDICT ─────────────────────────────────────────────────────────────
    overall = (health + valuation + growth) / 3.0
    if overall >= 7.5:   verdict = "Excellent"
    elif overall >= 6.0: verdict = "Bon"
    elif overall >= 4.5: verdict = "Correct"
    elif overall >= 3.0: verdict = "Risqué"
    else:                verdict = "À éviter"

    return {
        "health":     health,
        "valuation":  valuation,
        "growth":     growth,
        "complexity": complexity,
        "verdict":    verdict,
    }
