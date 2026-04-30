# seeds/migrate_db.py

## Role
Script de migration DDL idempotente pour la base PostgreSQL existante. A executer une seule fois apres un changement de schema qui ne peut pas etre applique par `create_all` (qui ne modifie pas les tables existantes).

## Dependances
- **Internes** : `config` (DATABASE_URL via SQLALCHEMY_DATABASE_URL)
- **Externes** : `sqlalchemy`, `python-dotenv`

## Migrations appliquees

| Migration | SQL | Statut |
|-----------|-----|--------|
| Index secteur | `CREATE INDEX IF NOT EXISTS ix_companies_sector ON companies(sector)` | Appliquee 2026-04-30 |
| MacroCache JSONB | `ALTER TABLE macro_cache ALTER COLUMN data_json TYPE JSONB USING data_json::jsonb` | Appliquee 2026-04-30 |

## Fonctionnement
- Chaque migration est executee dans une transaction separee avec rollback sur erreur.
- `IF NOT EXISTS` sur l'index rend la migration idempotente (safe a re-executer).
- En cas d'echec (ex: donnee non-JSON dans data_json), affiche `SKIP (message)` et continue — les donnees restent intactes.

## Usage
```bash
python seeds/migrate_db.py
```

Sortie attendue :
```
Migrations DDL Boursicot
  > ix_companies_sector... OK
  > macro_cache.data_json -> JSONB... OK
Termine
```

## Utilise par
- Execution manuelle unique par le developpeur apres chaque changement de schema.
- Ne fait pas partie des crons GitHub Actions.

## Points d'attention
- Necessite `SQLALCHEMY_DATABASE_URL` dans `.env` ou les variables d'environnement.
- La migration JSONB echoue si une ligne de `macro_cache` contient du TEXT non-JSON valide — inspecter manuellement avant si en doute.
- Pour ajouter une nouvelle migration : ajouter un tuple `(label, sql)` dans la liste `MIGRATIONS` du script.
