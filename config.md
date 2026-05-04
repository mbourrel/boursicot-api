# config.py

## Rôle
Centralise toutes les constantes de configuration de l'API : clés FMP, URLs de base, et identifiants du système d'alertes email.

## Dépendances
- **Internes** : aucune
- **Externes** : `os`

## Fonctionnement
Expose les constantes suivantes, toutes lues depuis les variables d'environnement à l'import :

### FMP (Financial Modeling Prep)
- `FMP_API_KEY` : clé API FMP (chaîne vide si absente — ne lève pas d'erreur).
- `FMP_STABLE` : URL de base de l'API stable FMP (`https://financialmodelingprep.com/stable`).
- `FMP_V3` : URL de base de l'API v3 FMP (`https://financialmodelingprep.com/api/v3`).

### Valorisation (ajout 2026-05-04)
- `EQUITY_RISK_PREMIUM` : prime de risque actions historique long terme, fixée à `0.055` (5,5 %). Utilisée dans le calcul du WACC par CAPM : `WACC = rf + β × EQUITY_RISK_PREMIUM`.

### Email — Monitoring FMP (ajout 2026-05-02)
- `ALERT_EMAILS` : adresses destinataires des alertes, séparées par des virgules. Défaut : `mateo.bourrel@orange.fr,b00821404@essec.edu`.
- `EMAIL_USER` : compte Gmail expéditeur (SMTP_USER). Doit correspondre à un compte Gmail avec App Password activé.
- `EMAIL_PASSWORD` : App Password Google 16 caractères (pas le mot de passe du compte).

## Utilisé par
- `routers/fundamentals.py` — `FMP_API_KEY` et `FMP_V3` (proxy FMP) ; `EQUITY_RISK_PREMIUM` (calcul WACC dans `_compute_valuation_defaults`)
- `seeds/seed_live_prices.py` — `FMP_API_KEY` et `FMP_STABLE`
- `utils/fmp_monitor.py` — `ALERT_EMAILS`, `EMAIL_USER`, `EMAIL_PASSWORD` (via import dans `_fire_alert_*`)
- `utils/mailer.py` — `ALERT_EMAILS`, `EMAIL_USER`, `EMAIL_PASSWORD`

## Variables d'environnement (.env)
```
FMP_API_KEY=...
EMAIL_USER=colocdulude@gmail.com
EMAIL_PASSWORD=xxxx xxxx xxxx xxxx   # App Password Gmail
ALERT_EMAILS=mateo.bourrel@orange.fr,b00821404@essec.edu
```

## Points d'attention
- `FMP_API_KEY` vaut `""` si la variable est absente — les modules consommateurs doivent vérifier qu'elle est non vide avant d'appeler FMP.
- `FMP_STABLE` et `FMP_V3` sont deux bases d'URL différentes : les endpoints disponibles ne sont pas les mêmes selon le plan FMP.
- `EMAIL_PASSWORD` est un App Password Google (16 caractères avec espaces) — différent du mot de passe du compte. Généré dans Compte Google → Sécurité → Mots de passe des applications.
- Ne jamais hardcoder ces valeurs ici, même en dev — toujours passer par `.env`.
- `EMAIL_USER` et `EMAIL_PASSWORD` ne sont jamais affichés dans les logs (voir `utils/mailer.py`).
