import yfinance as yf
import pandas as pd
from collections import OrderedDict
from database import SessionLocal, engine
from models import Base, Company, Price
from sqlalchemy.dialects.postgresql import insert as pg_insert

# ── Mappings anglais → français pour les états financiers ─────────────────────

BALANCE_SHEET_MAP = OrderedDict([
    ("Total Assets",                            "Actif Total"),
    ("Total Liabilities Net Minority Interest", "Passif Total"),
    ("Stockholders Equity",                     "Capitaux Propres"),
    ("Total Debt",                              "Dette Totale"),
    ("Long Term Debt",                          "Dette Long Terme"),
    ("Current Assets",                          "Actif Courant"),
    ("Current Liabilities",                     "Passif Courant"),
    ("Cash And Cash Equivalents",               "Trésorerie & Équivalents"),
    ("Accounts Receivable",                     "Créances Clients"),
    ("Inventory",                               "Stocks"),
    ("Goodwill",                                "Goodwill"),
    ("Retained Earnings",                       "Bénéfices Non Distribués"),
    ("Net PPE",                                 "Immobilisations Nettes"),
    ("Working Capital",                         "Besoin en Fonds de Roulement"),
])

INCOME_STMT_MAP = OrderedDict([
    ("Total Revenue",                     "Chiffre d'Affaires"),
    ("Cost Of Revenue",                   "Coût des Ventes"),
    ("Gross Profit",                      "Bénéfice Brut"),
    ("Operating Income",                  "Résultat Opérationnel (EBIT)"),
    ("EBITDA",                            "EBITDA"),
    ("Net Income",                        "Résultat Net"),
    ("Basic EPS",                         "BPA Basique"),
    ("Diluted EPS",                       "BPA Dilué"),
    ("Interest Expense",                  "Charges Financières"),
    ("Tax Provision",                     "Impôt sur les Bénéfices"),
    ("Research And Development",          "Recherche & Développement (R&D)"),
    ("Selling General And Administration","Frais Généraux & Admin. (SG&A)"),
])

CASHFLOW_MAP = OrderedDict([
    ("Operating Cash Flow",          "Flux de Trésorerie Opérationnel"),
    ("Capital Expenditure",          "Dépenses d'Investissement (CapEx)"),
    ("Free Cash Flow",               "Free Cash Flow"),
    ("Investing Cash Flow",          "Flux d'Investissement Total"),
    ("Financing Cash Flow",          "Flux de Financement Total"),
    ("Dividends Paid",               "Dividendes Versés"),
    ("Repurchase Of Capital Stock",  "Rachats d'Actions"),
    ("Depreciation And Amortization","Amortissements (D&A)"),
    ("Net Income",                   "Résultat Net"),
    ("Change In Working Capital",    "Variation du BFR"),
])


def parse_financial_df(df, name_map):
    """
    Transforme un DataFrame yfinance (index = métriques, colonnes = dates)
    en structure JSON stockable : {"years": [...], "items": [{name, vals, unit}]}.
    Ne conserve que les métriques du name_map et ignore celles entièrement nulles.
    """
    if df is None or df.empty:
        return None

    # Colonnes triées du plus récent au plus ancien
    sorted_cols = sorted(df.columns, reverse=True)[:4]
    years = [str(col)[:10] for col in sorted_cols]

    items = []
    for en_name, fr_name in name_map.items():
        if en_name not in df.index:
            continue
        row = df.loc[en_name]
        vals = [None if pd.isna(row[col]) else float(row[col]) for col in sorted_cols]
        if all(v is None or v == 0 for v in vals):
            continue
        items.append({"name": fr_name, "vals": vals, "unit": "$"})

    return {"years": years, "items": items} if items else None

# --- MISE À JOUR DE LA BASE DE DONNÉES (sans suppression) ---
print("Vérification/création des tables PostgreSQL...")
Base.metadata.create_all(bind=engine)

TICKERS = [
    # --- CAC 40 ---
    "AC.PA", "AI.PA", "AIR.PA", "MT.AS", "CS.PA", "BNP.PA", "EN.PA", "BVI.PA", 
    "CAP.PA", "CA.PA", "ACA.PA", "BN.PA", "DSY.PA", "ENGI.PA", "EL.PA", 
    "ERF.PA", "ENX.PA", "RMS.PA", "KER.PA", "OR.PA", "LR.PA", "MC.PA", "ML.PA", 
    "ORA.PA", "RI.PA", "PUB.PA", "RNO.PA", "SAF.PA", "SGO.PA", "SAN.PA", "SU.PA", 
    "GLE.PA", "STLAP.PA", "STMPA.PA", "HO.PA", "TTE.PA", "URW.PA", "VIE.PA", "DG.PA", 
    #--- action bonus ---
    "ABVX.PA",

    # --- LES 7 FANTASTIQUES (USA) ---
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",

    # --- INDICES PERTINENTS ---
    "^FCHI", "^GSPC", "^IXIC", "^DJI", "^STOXX50E", "^N225", "^VIX", "BTC-USD",
    
    # --- MÉTAUX PRÉCIEUX ET INDUSTRIELS ---
    "GC=F",   # Or (Gold)
    "SI=F",   # Argent (Silver)

    # --- ÉNERGIE ---
    "CL=F",   # Pétrole Brut WTI (Crude Oil)
    "BZ=F",   # Pétrole Brent
    "NG=F",   # Gaz Naturel


    # --- MATIÈRES PREMIÈRES AGRICOLES ---
    "ZC=F",   # Maïs (Corn)
    "ZW=F",   # Blé (Wheat)
    "CT=F"    # Coton
]

def clean_dataframe(df, interval_val):
    """
    Standardise le dataframe (nom de la date, timezone) AVANT la concaténation.
    """
    if df is None or df.empty:
        return None
    
    df = df.copy()
    df['interval'] = interval_val
    df.reset_index(inplace=True)
    
    # Harmonisation : On renomme toujours la colonne temps en 'Date'
    if 'Datetime' in df.columns:
        df.rename(columns={'Datetime': 'Date'}, inplace=True)
    elif 'index' in df.columns:
        df.rename(columns={'index': 'Date'}, inplace=True)
        
    # Suppression de la timezone pour la compatibilité avec PostgreSQL
    if 'Date' in df.columns and df['Date'].dt.tz is not None:
        df['Date'] = df['Date'].dt.tz_localize(None)
        
    return df

def importer_donnees():
    db = SessionLocal()
    print("Démarrage du téléchargement massif des données...")

    for ticker in TICKERS:
        try:
            print(f"\n-> Traitement de l'action {ticker}...")
            stock = yf.Ticker(ticker)
            info = stock.info

            name = info.get("shortName", ticker)
            sector = info.get("sector", "Inconnu")
            description = info.get("longBusinessSummary", "Description non disponible.")

            # --- RÉCUPÉRATION DES FONDAMENTAUX ---
            market_analysis = [
                {"name": "Capitalisation", "val": info.get("marketCap", 0), "unit": "$"},
                {"name": "PER", "val": round(info.get("trailingPE", 0) or 0, 2), "unit": "x"},
                {"name": "Rendement Div", "val": round((info.get("dividendYield", 0) or 0) * 100, 2), "unit": "%"}
            ]
            
            financial_health = [
                {"name": "Marge Nette", "val": round((info.get("profitMargins", 0) or 0) * 100, 2), "unit": "%"},
                {"name": "ROE", "val": round((info.get("returnOnEquity", 0) or 0) * 100, 2), "unit": "%"},
                {"name": "Dette/Fonds Propres", "val": round(info.get("debtToEquity", 0) or 0, 2), "unit": "%"}
            ]

            advanced_valuation = [
                {"name": "Forward PE", "val": round(info.get("forwardPE", 0) or 0, 2), "unit": "x"},
                {"name": "Price to Book", "val": round(info.get("priceToBook", 0) or 0, 2), "unit": "x"},
                {"name": "EV / EBITDA", "val": round(info.get("enterpriseToEbitda", 0) or 0, 2), "unit": "x"},
                {"name": "PEG Ratio", "val": round(info.get("pegRatio", 0) or 0, 2), "unit": "x"}
            ]

            income_growth = [
                {"name": "Chiffre d'Affaires", "val": info.get("totalRevenue", 0), "unit": "$"},
                {"name": "EBITDA", "val": info.get("ebitda", 0), "unit": "$"},
                {"name": "Croissance CA", "val": round((info.get("revenueGrowth", 0) or 0) * 100, 2), "unit": "%"},
                {"name": "Croissance Bénéfices", "val": round((info.get("earningsGrowth", 0) or 0) * 100, 2), "unit": "%"}
            ]

            balance_cash = [
                {"name": "Trésorerie Totale", "val": info.get("totalCash", 0), "unit": "$"},
                {"name": "Free Cash Flow", "val": info.get("freeCashflow", 0), "unit": "$"},
                {"name": "Ratio Liquidité", "val": round(info.get("currentRatio", 0) or 0, 2), "unit": "x"}
            ]

            risk_market = [
                {"name": "Beta", "val": round(info.get("beta", 0) or 0, 2), "unit": "x"},
                {"name": "Plus Haut 52w", "val": round(info.get("fiftyTwoWeekHigh", 0) or 0, 2), "unit": "$"},
                {"name": "Plus Bas 52w", "val": round(info.get("fiftyTwoWeekLow", 0) or 0, 2), "unit": "$"},
                {"name": "Actions Shortées", "val": round((info.get("shortPercentOfFloat", 0) or 0) * 100, 2), "unit": "%"}
            ]

            # --- ÉTATS FINANCIERS HISTORIQUES ---
            try:
                balance_sheet_data = parse_financial_df(stock.balance_sheet, BALANCE_SHEET_MAP)
            except Exception:
                balance_sheet_data = None

            try:
                income_stmt_data = parse_financial_df(stock.income_stmt, INCOME_STMT_MAP)
            except Exception:
                income_stmt_data = None

            try:
                cashflow_data = parse_financial_df(stock.cashflow, CASHFLOW_MAP)
            except Exception:
                cashflow_data = None

            # --- UPSERT ENTREPRISE (crée ou écrase si le ticker existe déjà) ---
            company = db.query(Company).filter(Company.ticker == ticker).first()
            if company:
                company.name = name
                company.sector = sector
                company.description = description
                company.market_analysis = market_analysis
                company.financial_health = financial_health
                company.advanced_valuation = advanced_valuation
                company.income_growth = income_growth
                company.balance_cash = balance_cash
                company.risk_market = risk_market
                company.balance_sheet_data = balance_sheet_data
                company.income_stmt_data = income_stmt_data
                company.cashflow_data = cashflow_data
            else:
                company = Company(
                    ticker=ticker, name=name, sector=sector, description=description,
                    market_analysis=market_analysis, financial_health=financial_health,
                    advanced_valuation=advanced_valuation, income_growth=income_growth,
                    balance_cash=balance_cash, risk_market=risk_market,
                    balance_sheet_data=balance_sheet_data,
                    income_stmt_data=income_stmt_data,
                    cashflow_data=cashflow_data,
                )
                db.add(company)
            db.commit()

            # --- HISTORIQUE DES PRIX (MULTI-TIMEFRAMES OPTIMISÉS) ---
            print(f"    Récupération de l'historique des prix...")
            
            # Limites maximales fiables de Yahoo Finance
            df_1w_raw = stock.history(period="10y", interval="1wk")
            df_1d_raw = stock.history(period="10y", interval="1d")
            df_1h_raw = stock.history(period="730d", interval="1h") # Max ~2 ans
            df_15m_raw = stock.history(period="60d", interval="15m") # Max 60 jours

            cleaned_dfs = [
                clean_dataframe(df_1w_raw, '1W'),
                clean_dataframe(df_1d_raw, '1D'),
                clean_dataframe(df_1h_raw, '1h'),
                clean_dataframe(df_15m_raw, '15m')
            ]
            
            dfs = [df for df in cleaned_dfs if df is not None and not df.empty]
            
            if dfs:
                df_final = pd.concat(dfs, ignore_index=True)
                df_final = df_final.dropna(subset=['Close', 'Open', 'High', 'Low'])
                df_final = df_final.fillna(0) 

                # --- INSERTION RAPIDE EN MASSE (Bulk Insert) ---
                prices_to_insert = []
                # Utilisation d'un set pour s'assurer qu'il n'y a aucun doublon exact venant de Yahoo
                seen_records = set() 

                for _, row in df_final.iterrows():
                    if 'Date' not in row or pd.isna(row['Date']):
                        continue
                        
                    date_val = row['Date'].to_pydatetime()
                    interval_val = row['interval']
                    
                    # Clé unique pour éviter les doublons dans le même lot
                    record_key = (ticker, date_val, interval_val)
                    if record_key not in seen_records:
                        seen_records.add(record_key)
                        
                        prices_to_insert.append(Price(
                            ticker=ticker,
                            date=date_val,
                            interval=interval_val,
                            open_price=float(row["Open"]),
                            high_price=float(row["High"]),
                            low_price=float(row["Low"]),
                            close_price=float(row["Close"]),
                            volume=int(row["Volume"])
                        ))

                # Upsert en masse : INSERT ... ON CONFLICT DO UPDATE
                # Met à jour OHLCV si la bougie existe déjà, sinon insère.
                if prices_to_insert:
                    records = [
                        {
                            "ticker":      p.ticker,
                            "date":        p.date,
                            "interval":    p.interval,
                            "open_price":  p.open_price,
                            "high_price":  p.high_price,
                            "low_price":   p.low_price,
                            "close_price": p.close_price,
                            "volume":      p.volume,
                        }
                        for p in prices_to_insert
                    ]
                    stmt = pg_insert(Price).values(records)
                    stmt = stmt.on_conflict_do_update(
                        constraint="uix_ticker_date_interval",
                        set_={
                            "open_price":  stmt.excluded.open_price,
                            "high_price":  stmt.excluded.high_price,
                            "low_price":   stmt.excluded.low_price,
                            "close_price": stmt.excluded.close_price,
                            "volume":      stmt.excluded.volume,
                        }
                    )
                    db.execute(stmt)
                    db.commit()
                    print(f"    ✅ {len(prices_to_insert)} bougies insérées/mises à jour.")

        except Exception as e:
            print(f"    ❌ Erreur lors du traitement de {ticker} : {e}")
            db.rollback()
            continue

    print("\nOpération terminée ! Ton terminal est prêt.")
    db.close()

if __name__ == "__main__":
    importer_donnees()