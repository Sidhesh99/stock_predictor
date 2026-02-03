import os
import warnings
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

from flask import Flask, render_template, request, jsonify
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

app = Flask(__name__)

# ── stock name → CSV file (no network needed) ──────────────────────
STOCKS = {
    "RELIANCE":  "RELIANCE.csv",
    "TCS":       "TCS.csv",
    "INFY":      "INFY.csv",
    "HDFCBANK":  "HDFCBANK.csv",
    "ICICIBANK": "ICICIBANK.csv",
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
LOOKBACK = 60
MIN_ROWS  = 70

# ── LSTM helper ─────────────────────────────────────────────────────
class StockPredictor:
    def __init__(self):
        self.scaler = MinMaxScaler(feature_range=(0, 1))

    def _build_model(self, input_shape):
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25, activation='relu'),
            Dense(1)
        ])
        model.compile(optimizer='adam', loss='mean_squared_error')
        return model

    def _make_sequences(self, scaled):
        X, y = [], []
        for i in range(LOOKBACK, len(scaled)):
            X.append(scaled[i - LOOKBACK:i, 0])
            y.append(scaled[i, 0])
        X = np.array(X).reshape(len(X), LOOKBACK, 1)
        return X, np.array(y)

    def predict(self, stock_name, start_date, end_date):
        csv_path = os.path.join(DATA_DIR, STOCKS[stock_name])
        df = pd.read_csv(csv_path, parse_dates=["Date"])
        df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)].sort_values("Date")

        if len(df) < MIN_ROWS:
            return None, "Not enough data. Please choose a wider date range (minimum ~3 months)."

        prices  = df["Close"].values.astype(np.float64)
        dates   = df["Date"].dt.strftime("%Y-%m-%d").tolist()

        scaled = self.scaler.fit_transform(prices.reshape(-1, 1))
        X, y   = self._make_sequences(scaled)

        if len(X) < 10:
            return None, "Not enough data after sequence creation. Widen the date range."

        model = self._build_model((LOOKBACK, 1))
        model.fit(X, y, epochs=10, batch_size=32, verbose=0)

        last_seq        = scaled[-LOOKBACK:].reshape(1, LOOKBACK, 1)
        pred_scaled     = model.predict(last_seq, verbose=0)
        predicted_price = float(self.scaler.inverse_transform(pred_scaled)[0][0])

        current_price   = float(prices[-1])
        change_pct      = ((predicted_price - current_price) / current_price) * 100

        if change_pct > 1.5:
            decision    = "BUY"
            confidence  = min(75 + abs(change_pct) * 2, 95)
        elif change_pct < -1.5:
            decision    = "SELL"
            confidence  = min(75 + abs(change_pct) * 2, 95)
        else:
            decision    = "HOLD"
            confidence  = max(50, 70 - abs(change_pct) * 3)

        return {
            "success":           True,
            "stock_name":        stock_name,
            "dates":             dates,
            "historical_prices": prices.tolist(),
            "current_price":     round(current_price, 2),
            "predicted_price":   round(predicted_price, 2),
            "price_change":      round(change_pct, 2),
            "decision":          decision,
            "confidence":        int(confidence),
        }, None


predictor = StockPredictor()

@app.route("/")
def index():
    return render_template("index.html", stocks=list(STOCKS.keys()))

@app.route("/predict", methods=["POST"])
def predict_route():
    try:
        body  = request.get_json()
        stock = body.get("stock", "RELIANCE")
        start = body.get("start_date", "2022-01-01")
        end   = body.get("end_date",   "2025-01-01")

        if stock not in STOCKS:
            return jsonify({"success": False, "error": "Invalid stock selected."})

        result, err = predictor.predict(stock, start, end)
        if err:
            return jsonify({"success": False, "error": err})
        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
