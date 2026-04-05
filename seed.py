import yfinance as yf
from database import SessionLocal, engine
from models import Base, Company, Price

# --- MISE À JOUR DE LA BASE DE DONNÉES ---
print("Réinitialisation des tables PostgreSQL...")
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

TICKERS = [
    "MC.PA", "TTE.PA", "OR.PA", "SAN.PA", "AI.PA", "BNP.PA", "CS.PA", 
    "AIR.PA", "SU.PA", "DG.PA", "ACA.PA", "RMS.PA", "EL.PA", "EN.PA", 
    "CAP.PA", "LR.PA", "GLE.PA", "VIV.PA", "SGO.PA", "CA.PA",
    "AAPL", "MSFT", "TSLA"
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

            # --- ENREGISTREMENT ---
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

            # Historique des prix
            hist = stock.history(period="1y")
            for index, row in hist.iterrows():
                date_val = index.date()
                existing_price = db.query(Price).filter(Price.ticker == ticker, Price.date == date_val).first()
                if not existing_price:
                    new_price = Price(
                        ticker=ticker,
                        date=date_val,
                        open_price=float(row["Open"]),
                        high_price=float(row["High"]),
                        low_price=float(row["Low"]),
                        close_price=float(row["Close"]),
                        volume=int(row["Volume"])
                    )
                    db.add(new_price)
            
            db.commit()
            print(f"   Données de {name} enregistrées avec succès !")

        print("Opération terminée ! Ton terminal est prêt.")

    except Exception as e:
        print(f"Erreur lors du traitement : {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    importer_donnees()