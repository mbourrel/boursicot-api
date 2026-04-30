# routers/search.py

## Rôle
Router FastAPI fournissant une recherche textuelle simple sur les entreprises (ticker ou nom) dans la table `companies`.

## Dépendances
- **Internes** : `database.get_db`, `models`
- **Externes** : `fastapi`, `sqlalchemy`

## Fonctionnement

### `GET /api/search?q={query}`
- Filtre la table `companies` avec `ILIKE` (insensible à la casse) sur `ticker` et `name` (union OR).
- Limite les résultats à 10 entrées.
- Retourne les objets `Company` complets (tous les champs JSON inclus).

## Utilisé par
- Frontend Boursicot : barre de recherche permettant de naviguer vers la fiche d'une action.

## Points d'attention
- La recherche ne couvre que la table `companies` — les actifs non seedés (indices, crypto sans fiche fondamentale) ne sont pas retrouvables par cette route. Utiliser `/api/assets` pour le catalogue complet.
- `ILIKE` avec des wildcards des deux côtés (`%q%`) n'utilise pas d'index B-tree standard — acceptable sur ~64 lignes, mais à surveiller si la table grossit.
- La réponse inclut tous les champs JSON (`financial_health`, `income_stmt_data`, etc.) — verbeux pour un résultat de recherche. Envisager un schéma de réponse allégé si la bande passante devient un problème.
- Pas de gestion du cas `q` vide — une requête `?q=` retourne jusqu'à 10 entreprises aléatoires (tous les noms matchent `%%`).
