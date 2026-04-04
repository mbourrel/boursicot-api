import json
import random
from datetime import datetime, timedelta, timezone

def generate_stock_history(symbol, start_price, num_points=100):
    data = []
    current_close = start_price
    # On commence 100 minutes en arrière
    start_time = datetime.now(timezone.utc) - timedelta(minutes=num_points)
    
    for i in range(num_points):
        open_price = current_close
        
        # On simule une variation max de 1% pour la bougie
        change = open_price * random.uniform(-0.01, 0.01)
        close_price = open_price + change
        
        # Le High et Low doivent être au-delà de Open et Close
        high_price = max(open_price, close_price) + (open_price * random.uniform(0, 0.002))
        low_price = min(open_price, close_price) - (open_price * random.uniform(0, 0.002))
        
        timestamp = start_time + timedelta(minutes=i)
        
        data.append({
            "time": int(timestamp.timestamp()), # Timestamp Unix
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "symbol": symbol
        })
        current_close = close_price
        
    return data

all_history = []
all_history.extend(generate_stock_history("AAPL", 175.00))
all_history.extend(generate_stock_history("MSFT", 420.00))
all_history.extend(generate_stock_history("TSLA", 195.00))

with open("historical_prices.json", "w") as f:
    json.dump(all_history, f, indent=2)

print("✅ Fichier historical_prices.json généré avec des bougies (OHLC) !")