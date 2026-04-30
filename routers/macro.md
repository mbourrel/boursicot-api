# routers/macro.py

## Rôle
Router FastAPI exposant les indicateurs macroéconomiques (cycle économique, liquidité M2/BTC, taux directeurs et rendements obligataires), avec cache PostgreSQL 24h/6h.

## Dépendances
- **Internes** : `database.get_db`, `services.macro_service` (4 fonctions), `schemas.macro` (4 modèles Pydantic)
- **Externes** : `fastapi`, `sqlalchemy`

## Fonctionnement
Router minimaliste de délégation — chaque endpoint délègue entièrement la logique métier à `macro_service.py` :

| Endpoint | Service | Cache TTL | Description |
|---|---|---|---|
| `GET /macro/cycle` | `get_cycle_data` | 24h | Phase du cycle économique (INDPRO + CPIAUCSL via FRED) |
| `GET /macro/liquidity` | `get_liquidity_data` | 24h | M2SL vs BTC-USD normalisés base 100 depuis jan 2020 |
| `GET /macro/cycle/history` | `get_cycle_history` | 24h | Historique mensuel du cycle depuis 1948 (~920 points) |
| `GET /macro/rates` | `get_rates_data` | 6h | Taux directeurs (Fed, BCE, BoE, BoJ) + rendements obligataires |

Chaque route utilise `response_model` Pydantic pour la validation et la documentation OpenAPI.

## Utilisé par
- Frontend Boursicot : composants macro (phase du cycle, graphique liquidité, courbe des taux).

## Points d'attention
- Le préfixe est `/macro` (sans `/api`) — différent des autres routers. À prendre en compte côté frontend pour les appels fetch.
- Les TTL de cache sont définis dans `macro_service.py`, pas ici — le router ne contrôle pas la fraîcheur des données.
- Si FRED est indisponible ET le cache est vide, le service lève HTTP 502. Le frontend doit gérer ce cas.
- `MacroRatesOut` a un TTL de seulement 6h (les taux bougent plus fréquemment) — un appel en fin de TTL peut prendre plusieurs secondes (appels FRED synchrones).
