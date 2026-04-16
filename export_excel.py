import yfinance as yf
import pandas as pd

TICKERS = ["AAPL", "MSFT", "TTE.PA", "^FCHI"]

OUTPUT_FILE = "yahoo_fields_exploration.xlsx"


def explore_fields(tickers):
    all_keys = set()
    data_per_ticker = []

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info or {}

            keys = set(info.keys())
            all_keys.update(keys)

            row = {"ticker": ticker}
            row.update(info)

            data_per_ticker.append(row)

            print(f"✅ {ticker}: {len(keys)} champs trouvés")

        except Exception as e:
            print(f"❌ Erreur {ticker}: {e}")

    return all_keys, pd.DataFrame(data_per_ticker)


def export_fields():
    all_keys, df = explore_fields(TICKERS)

    # Liste des champs
    df_keys = pd.DataFrame(sorted(list(all_keys)), columns=["field_name"])

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        df_keys.to_excel(writer, sheet_name="ALL_FIELDS", index=False)
        df.to_excel(writer, sheet_name="DATA_SAMPLE", index=False)

    print(f"\n📁 Fichier généré : {OUTPUT_FILE}")
    print(f"📊 Nombre total de champs uniques : {len(all_keys)}")


if __name__ == "__main__":
    export_fields()