"""
Utilitaires partagés entre les scripts de seeding.
"""
import pandas as pd
from collections import OrderedDict

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

# Liste complète des tickers à traiter
TICKERS = [
    # --- CAC 40 ---
    "AC.PA", "AI.PA", "AIR.PA", "MT.AS", "CS.PA", "BNP.PA", "EN.PA", "BVI.PA",
    "CAP.PA", "CA.PA", "ACA.PA", "BN.PA", "DSY.PA", "ENGI.PA", "EL.PA",
    "ERF.PA", "ENX.PA", "RMS.PA", "KER.PA", "OR.PA", "LR.PA", "MC.PA", "ML.PA",
    "ORA.PA", "RI.PA", "PUB.PA", "RNO.PA", "SAF.PA", "SGO.PA", "SAN.PA", "SU.PA",
    "GLE.PA", "STLAP.PA", "STMPA.PA", "HO.PA", "TTE.PA", "URW.PA", "VIE.PA", "DG.PA",
    # --- action bonus ---
    "ABVX.PA",
    # --- LES 7 FANTASTIQUES (USA) ---
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
    # --- INDICES ---
    "^FCHI", "^GSPC", "^IXIC", "^DJI", "^STOXX50E", "^N225", "^VIX", "BTC-USD",
    # --- MÉTAUX PRÉCIEUX ---
    "GC=F", "SI=F",
    # --- ÉNERGIE ---
    "CL=F", "BZ=F", "NG=F",
    # --- MATIÈRES PREMIÈRES AGRICOLES ---
    "ZC=F", "ZW=F", "CT=F",
]


def parse_financial_df(df, name_map):
    """
    Transforme un DataFrame yfinance en structure JSON stockable.
    """
    if df is None or df.empty:
        return None
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


def clean_dataframe(df, interval_val):
    """Standardise le DataFrame (colonne date, timezone) avant concaténation."""
    if df is None or df.empty:
        return None
    df = df.copy()
    df['interval'] = interval_val
    df.reset_index(inplace=True)
    if 'Datetime' in df.columns:
        df.rename(columns={'Datetime': 'Date'}, inplace=True)
    elif 'index' in df.columns:
        df.rename(columns={'index': 'Date'}, inplace=True)
    if 'Date' in df.columns and df['Date'].dt.tz is not None:
        df['Date'] = df['Date'].dt.tz_localize(None)
    return df
