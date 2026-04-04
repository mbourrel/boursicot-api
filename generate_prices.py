import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def generate_stock_data(symbol, start_price, days=1500):
    dates = [datetime(2022, 1, 1) + timedelta(days=i) for i in range(days)]
    # Ignorer les week-ends pour simuler la bourse
    dates = [d for d in dates if d.weekday() < 5]
    
    data = []
    current_price = start_price
    
    for date in dates:
        volatility = current_price * 0.02
        open_price = current_price + np.random.normal(0, volatility * 0.5)
        close_price = open_price + np.random.normal(0, volatility)
        high_price = max(open_price, close_price) + abs(np.random.normal(0, volatility * 0.5))
        low_price = min(open_price, close_price) - abs(np.random.normal(0, volatility * 0.5))
        
        data.append({
            "symbol": symbol,
            "time": date.strftime("%Y-%m-%d"),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2)
        })
        current_price = close_price
        
    df = pd.DataFrame(data)
    
    # Calcul des moyennes mobiles
    df['ma10'] = df['close'].rolling(window=10).mean().round(2)
    df['ma100'] = df['close'].rolling(window=100).mean().round(2)
    df['ma365'] = df['close'].rolling(window=365).mean().round(2)
    
    # Remplacer les valeurs NaN par None pour que le JSON soit valide
    df = df.replace({np.nan: None})
    return df.to_dict('records')

# Générer les données pour les 3 entreprises
all_data = []
all_data.extend(generate_stock_data("AAPL", 150))
all_data.extend(generate_stock_data("MSFT", 250))
all_data.extend(generate_stock_data("TSLA", 200))

# Sauvegarder dans le fichier JSON
base_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(base_dir, "historical_prices.json"), "w") as f:
    json.dump(all_data, f, indent=2)

print("Fichier historical_prices.json généré avec les moyennes mobiles (MA10, MA100, MA365) !")