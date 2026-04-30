# routers/exchange_rates.py

## Rôle
Router FastAPI exposant les taux de change courants (EURUSD, GBPUSD, JPYUSD, CHFUSD) stockés en base et mis à jour 1x/jour par le cron `seed_exchange_rates`.

## Dépendances
- **Internes** : `database.get_db`, `models`
- **Externes** : `fastapi`, `sqlalchemy`

## Fonctionnement

### `GET /api/exchange-rates`
1. Récupère toutes les lignes de la table `exchange_rates`.
2. Construit un dict `{pair: rate}` et détermine `updated_at` comme le max des timestamps.
3. Si la table est vide, retourne `{"rates": {}, "updated_at": null}` sans erreur.

Format de réponse :
```json
{
  "rates": {"EURUSD": 1.085, "GBPUSD": 1.27, "JPYUSD": 0.0065, "CHFUSD": 1.12},
  "updated_at": "2026-04-29T08:00:00"
}
```

## Utilisé par
- Frontend Boursicot : conversion de devises pour l'affichage des prix et des valorisations (actions européennes en EUR, US en USD).

## Points d'attention
- Les taux sont exprimés **en USD** (EURUSD = combien de USD pour 1 EUR). Toutes les paires ont l'USD comme monnaie de cotation.
- La fraîcheur dépend entièrement du cron `seed_exchange_rates` — en cas de panne du cron, les données peuvent être périmées sans indication côté API (pas de champ `stale`).
- `updated_at` est retourné en ISO 8601 sans timezone (UTC naïf) — le frontend doit en tenir compte pour l'affichage.
- Pas de cache en mémoire — chaque appel fait une requête SQL, ce qui est acceptable pour une table de 4 lignes.
