# config.py

## Rôle
Centralise les constantes de configuration pour l'API Financial Modeling Prep (FMP) afin d'éviter leur redéfinition dispersée dans les modules.

## Dépendances
- **Internes** : aucune
- **Externes** : `os`

## Fonctionnement
Expose trois constantes lues à l'import :
- `FMP_API_KEY` : clé API FMP lue depuis l'environnement (chaîne vide si absente — ne lève pas d'erreur).
- `FMP_STABLE` : URL de base de l'API stable FMP (`https://financialmodelingprep.com/stable`).
- `FMP_V3` : URL de base de l'API v3 FMP (`https://financialmodelingprep.com/api/v3`).

## Utilisé par
- `routers/fundamentals.py` (import de `FMP_API_KEY` et `FMP_V3` pour le proxy FMP)
- `seeds/seed_live_prices.py` (import de `FMP_API_KEY` et `FMP_STABLE`)

## Points d'attention
- `FMP_API_KEY` vaut `""` si la variable d'environnement est absente — les modules consommateurs doivent vérifier qu'elle est non vide avant d'appeler FMP (ex. : `if not FMP_API_KEY: raise HTTP 503`).
- `FMP_STABLE` et `FMP_V3` sont deux bases d'URL différentes : les endpoints disponibles ne sont pas les mêmes selon le plan FMP. Le plan gratuit couvre `/stable/profile` et `/stable/quote` mais pas tous les endpoints `/api/v3`.
- Ne pas hardcoder la clé ici même en dev — toujours passer par `.env`.
