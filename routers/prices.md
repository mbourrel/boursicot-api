# routers/prices.py

## Rôle
Router FastAPI exposant l'historique des prix OHLCV depuis la table `prices`, formaté pour les graphiques Lightweight Charts.

## Dépendances
- **Internes** : `database.get_db`, `models`
- **Externes** : `fastapi`, `sqlalchemy`, `typing.Optional`

## Fonctionnement

### `GET /api/prices`
Paramètres :
- `ticker` (requis) : symbole yfinance (ex. `AAPL`, `AI.PA`, `^GSPC`).
- `interval` (défaut `1D`) : granularité souhaitée — `15m`, `1h`, `1D`, `1W`.
- `limit` (optionnel) : nombre de bougies à retourner.

Logique :
- Sans `limit` : retourne toutes les bougies triées par date ASC.
- Avec `limit` : sélectionne les N dernières bougies (DESC + limit), puis les réordonne ASC pour l'affichage.
- Lève HTTP 404 si aucune donnée n'est trouvée pour la combinaison ticker/interval.

Réponse : liste de `{time, open, high, low, close, volume, interval}`. `time` est une chaîne ISO 8601.

## Utilisé par
- Frontend Boursicot : composant graphique (Lightweight Charts) pour l'affichage des bougies.

## Points d'attention
- Pas de validation de la valeur `interval` : une valeur inconnue (ex. `2h`) ne lève pas d'erreur mais retourne simplement 0 résultat → 404.
- Le champ `time` est une chaîne ISO (`isoformat()`), non un timestamp Unix — vérifier la compatibilité avec la version de Lightweight Charts utilisée côté frontend.
- La table `prices` n'a pas d'index composite sur `(ticker, interval, date)` — les requêtes avec `limit` font un `ORDER BY date DESC LIMIT N` qui peut être lent sur une grande table si l'index manque.
- Les prix live (intraday temps réel) ne sont **pas** dans cette table — ils sont dans `companies.live_price`. Cette route couvre uniquement l'historique seedé par les crons.
