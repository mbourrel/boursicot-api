# seed_utils.py

## Rôle
Fournit les utilitaires et mappings partagés entre tous les scripts de seeding : tables de traduction EN→FR des lignes de bilans, et fonctions de transformation de DataFrames yfinance.

## Dépendances
- **Internes** : `assets_config.TICKERS` (ré-exporté)
- **Externes** : `pandas`, `collections.OrderedDict`

## Fonctionnement

### Mappings de colonnes (OrderedDict)
Trois dictionnaires ordonnés définissent la liste des lignes à extraire et leur traduction française :

- `BALANCE_SHEET_MAP` : 14 lignes du bilan (Actif Total, Passif Total, Capitaux Propres, etc.)
- `INCOME_STMT_MAP` : 12 lignes du compte de résultat (Chiffre d'Affaires, EBITDA, Résultat Net, BPA, etc.)
- `CASHFLOW_MAP` : 10 lignes du tableau de flux de trésorerie (FCF, CapEx, Dividendes Versés, etc.)

L'ordre des clés détermine l'ordre d'affichage dans le frontend.

### `parse_financial_df(df, name_map)`
Transforme un DataFrame yfinance (index = noms de lignes EN, colonnes = dates) en structure JSON stockable :
```json
{
  "years": ["2024-12-31", "2023-12-31", ...],
  "items": [{"name": "Chiffre d'Affaires", "vals": [12e9, 10e9, ...], "unit": "$"}]
}
```
- Trie les colonnes en ordre décroissant (année la plus récente en premier).
- Ignore les lignes absentes du DataFrame ou entièrement nulles/zéro.
- Retourne `None` si le DataFrame est vide.

### `clean_dataframe(df, interval_val)`
Standardise un DataFrame OHLCV yfinance avant concaténation dans les scripts de prix :
- Ajoute la colonne `interval`.
- Réinitialise l'index et renomme la colonne date en `Date` (gère `Datetime` et `index`).
- Supprime la timezone des dates (localize None) pour compatibilité PostgreSQL.

## Utilisé par
- `seeds/seed_fundamentals.py` : importe `TICKERS`, `BALANCE_SHEET_MAP`, `INCOME_STMT_MAP`, `CASHFLOW_MAP`, `parse_financial_df`.
- `seeds/seed_prices.py` et `seeds/seed_prices_init.py` : importent `TICKERS`, `clean_dataframe`.

## Points d'attention
- `TICKERS` est ré-exporté depuis `assets_config` via `noqa: F401` — les scripts de seed peuvent l'importer d'ici sans chercher `assets_config`.
- `parse_financial_df` ignore silencieusement les lignes entièrement à zéro — une métrique avec des vraies valeurs de zéro serait donc exclue. En pratique, les zéros yfinance indiquent des données manquantes.
- L'ordre des `OrderedDict` est significatif : modifier l'ordre change l'affichage frontend sans migration de données (les données sont stockées par nom, pas par position).
- `clean_dataframe` ne valide pas les valeurs OHLCV — les NaN sur Close/Open/High/Low sont filtrés dans les scripts appelants.
