import yfinance as yf
import pandas as pd
from database import SessionLocal, engine
from models import Base, Company, Price

# --- MISE À JOUR DE LA BASE DE DONNÉES ---
print("Réinitialisation des tables PostgreSQL...")
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

TICKERS = [
    # --- CAC 40 (Composants principaux - Avril 2026) ---
    "AC.PA", "AI.PA", "AIR.PA", "MT.AS", "CS.PA", "BNP.PA", "EN.PA", "BVI.PA", 
    "CAP.PA", "CA.PA", "ACA.PA", "BN.PA", "DSY.PA", "EDF.PA", "ENGI.PA", "EL.PA", 
    "ERF.PA", "ENX.PA", "RMS.PA", "KER.PA", "OR.PA", "LR.PA", "MC.PA", "ML.PA", 
    "ORA.PA", "RI.PA", "PUB.PA", "RNO.PA", "SAF.PA", "SGO.PA", "SAN.PA", "SU.PA", 
    "GLE.PA", "STLAP.PA", "STMPA.PA", "HO.PA", "TTE.PA", "URW.PA", "VIE.PA", "DG.PA",

    # --- LES 7 FANTASTIQUES (USA) ---
    "AAPL",   # Apple
    "MSFT",   # Microsoft
    "GOOGL",  # Alphabet (Google)
    "AMZN",   # Amazon
    "META",   # Meta (Facebook)
    "NVDA",   # NVIDIA
    "TSLA",   # Tesla

    # --- INDICES PERTINENTS (Tickers Yahoo Finance) ---
    "^FCHI",  # CAC 40 Index
    "^GSPC",  # S&P 500
    "^IXIC",  # NASDAQ Composite
    "^DJI",   # Dow Jones Industrial Average
    "^STOXX50E", # Euro Stoxx 50
    "^N225",  # Nikkei 225
    "^VIX",   # Indice de la peur (Volatilité)
    "BTC-USD" # Bitcoin (souvent pertinent en corrélation)
]

def importer_donnees():
    db = SessionLocal()
    print("Démarrage du téléchargement massif des données...")

    try:
        for ticker in TICKERS:
            print(f"-> Traitement de l'action {ticker}...")
            stock = yf.Ticker(ticker)
            info = stock.info

            name = info.get("shortName", ticker)
            sector = info.get("sector", "Inconnu")
            description = info.get("longBusinessSummary", "Description non disponible.")

            # --- ANCIENNES CATÉGORIES ---
            market_cap = info.get("marketCap", 0)
            pe_ratio = info.get("trailingPE", 0)
            div_yield = (info.get("dividendYield", 0) or 0) * 100
            
            profit_margin = (info.get("profitMargins", 0) or 0) * 100
            roe = (info.get("returnOnEquity", 0) or 0) * 100
            debt_to_equity = info.get("debtToEquity", 0) or 0

            market_analysis = [
                {"name": "Capitalisation", "val": market_cap, "unit": "$", "avg": 50000000000},
                {"name": "PER (Price/Earnings)", "val": round(pe_ratio, 2) if pe_ratio else 0, "unit": "x", "avg": 15},
                {"name": "Rendement Dividende", "val": round(div_yield, 2) if div_yield else 0, "unit": "%", "avg": 2.5}
            ]
            
            financial_health = [
                {"name": "Marge Nette", "val": round(profit_margin, 2) if profit_margin else 0, "unit": "%", "avg": 10},
                {"name": "ROE (Rentabilité)", "val": round(roe, 2) if roe else 0, "unit": "%", "avg": 15},
                {"name": "Dette / Capitaux Propres", "val": round(debt_to_equity, 2) if debt_to_equity else 0, "unit": "%", "avg": 50}
            ]

            # --- 1. VALORISATION AVANCÉE ---
            forward_pe = info.get("forwardPE", 0)
            pb_ratio = info.get("priceToBook", 0)
            ev_ebitda = info.get("enterpriseToEbitda", 0)
            peg_ratio = info.get("pegRatio", 0)

            advanced_valuation = [
                {"name": "Forward PE (Estimé)", "val": round(forward_pe, 2) if forward_pe else 0, "unit": "x", "avg": 15},
                {"name": "Price to Book (P/B)", "val": round(pb_ratio, 2) if pb_ratio else 0, "unit": "x", "avg": 2},
                {"name": "EV / EBITDA", "val": round(ev_ebitda, 2) if ev_ebitda else 0, "unit": "x", "avg": 10},
                {"name": "PEG Ratio", "val": round(peg_ratio, 2) if peg_ratio else 0, "unit": "x", "avg": 1}
            ]

            # --- 2. COMPTE DE RÉSULTAT & CROISSANCE ---
            total_revenue = info.get("totalRevenue", 0)
            ebitda = info.get("ebitda", 0)
            rev_growth = (info.get("revenueGrowth", 0) or 0) * 100
            earn_growth = (info.get("earningsGrowth", 0) or 0) * 100

            income_growth = [
                {"name": "Chiffre d'Affaires", "val": total_revenue, "unit": "$", "avg": 0},
                {"name": "EBITDA", "val": ebitda, "unit": "$", "avg": 0},
                {"name": "Croissance CA", "val": round(rev_growth, 2), "unit": "%", "avg": 5},
                {"name": "Croissance Bénéfices", "val": round(earn_growth, 2), "unit": "%", "avg": 5}
            ]

            # --- 3. BILAN & LIQUIDITÉ ---
            total_cash = info.get("totalCash", 0)
            fcf = info.get("freeCashflow", 0)
            current_ratio = info.get("currentRatio", 0)

            balance_cash = [
                {"name": "Trésorerie Totale", "val": total_cash, "unit": "$", "avg": 0},
                {"name": "Free Cash Flow", "val": fcf, "unit": "$", "avg": 0},
                {"name": "Ratio de Liquidité", "val": round(current_ratio, 2) if current_ratio else 0, "unit": "x", "avg": 1.5}
            ]

            # --- 4. RISQUE & MARCHÉ ---
            beta = info.get("beta", 0)
            high_52w = info.get("fiftyTwoWeekHigh", 0)
            low_52w = info.get("fiftyTwoWeekLow", 0)
            short_pct = (info.get("shortPercentOfFloat", 0) or 0) * 100

            risk_market = [
                {"name": "Beta (Volatilité)", "val": round(beta, 2) if beta else 0, "unit": "x", "avg": 1},
                {"name": "Plus Haut (52 sem)", "val": round(high_52w, 2) if high_52w else 0, "unit": "$", "avg": 0},
                {"name": "Plus Bas (52 sem)", "val": round(low_52w, 2) if low_52w else 0, "unit": "$", "avg": 0},
                {"name": "Actions Shortées", "val": round(short_pct, 2), "unit": "%", "avg": 2}
            ]

            # --- ENREGISTREMENT DE L'ENTREPRISE ---
            company = db.query(Company).filter(Company.ticker == ticker).first()
            if not company:
                company = Company(
                    ticker=ticker, 
                    name=name, 
                    sector=sector,
                    description=description,
                    market_analysis=market_analysis,
                    financial_health=financial_health,
                    advanced_valuation=advanced_valuation,
                    income_growth=income_growth,
                    balance_cash=balance_cash,
                    risk_market=risk_market
                )
                db.add(company)
            else:
                company.description = description
                company.market_analysis = market_analysis
                company.financial_health = financial_health
                company.advanced_valuation = advanced_valuation
                company.income_growth = income_growth
                company.balance_cash = balance_cash
                company.risk_market = risk_market
            
            db.commit()

            # --- HISTORIQUE DES PRIX (MULTI-TIMEFRAMES) ---
            print(f"    Récupération de l'historique des prix pour {ticker}...")
            
            # 1. Hebdomadaire (5 ans)
            df_1w = stock.history(period="5y", interval="1wk")
            if not df_1w.empty: df_1w['interval'] = '1W'

            # 2. Journalier (1 an)
            df_1d = stock.history(period="1y", interval="1d")
            if not df_1d.empty: df_1d['interval'] = '1D'

            # 3. Horaire (1 mois)
            df_1h = stock.history(period="1mo", interval="1h")
            if not df_1h.empty: df_1h['interval'] = '1h'

            # Concaténation des trois dataframes
            dfs = [df for df in [df_1w, df_1d, df_1h] if not df.empty]
            
            if dfs:
                df_final = pd.concat(dfs)
                
                # Nettoyage des données pour éviter les plantages API (NaN)
                df_final = df_final.dropna(subset=['Close', 'Open', 'High', 'Low'])
                df_final = df_final.fillna(0) 
                
                df_final.reset_index(inplace=True)
                
                # Selon l'intervalle, yfinance nomme la colonne 'Date' ou 'Datetime'
                date_col = 'Datetime' if 'Datetime' in df_final.columns else 'Date'
                
                # Suppression de la timezone pour éviter les erreurs de format avec SQLAlchemy/Postgres
                if df_final[date_col].dt.tz is not None:
                    df_final[date_col] = df_final[date_col].dt.tz_localize(None)

                # Insertion en base de données
                for index, row in df_final.iterrows():
                    date_val = row[date_col].to_pydatetime()
                    
                    # On vérifie avec la date ET l'intervalle
                    existing_price = db.query(Price).filter(
                        Price.ticker == ticker, 
                        Price.date == date_val,
                        Price.interval == row['interval']
                    ).first()
                    
                    if not existing_price:
                        new_price = Price(
                            ticker=ticker,
                            date=date_val,
                            interval=row['interval'],
                            open_price=float(row["Open"]),
                            high_price=float(row["High"]),
                            low_price=float(row["Low"]),
                            close_price=float(row["Close"]),
                            volume=int(row["Volume"])
                        )
                        db.add(new_price)
                
                db.commit()
            print(f"   ✅ Données de {name} enregistrées avec succès !")

        print("Opération terminée ! Ton terminal est prêt.")

    except Exception as e:
        print(f"Erreur lors du traitement : {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    importer_donnees()