import streamlit as st
import pandas as pd
import datetime as dt
from nsepy import get_history
import ta
import yfinance as yf

# --- V40 Stock Basket ---
v40_stocks = [
    "RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","HINDUNILVR","SBIN","BHARTIARTL",
    "AXISBANK","KOTAKBANK","ITC","LT","BAJFINANCE","ASIANPAINT","MARUTI","SUNPHARMA",
    "ULTRACEMCO","HCLTECH","WIPRO","TECHM","ONGC","POWERGRID","NTPC","ADANIPORTS",
    "COALINDIA","NESTLEIND","TITAN","BAJAJFINSV","HDFCLIFE","GRASIM","BRITANNIA",
    "DRREDDY","CIPLA","EICHERMOT","HEROMOTOCO","M&M","DIVISLAB","BPCL","SHREECEM","UPL"
]

st.title("📈 NSE V40 Stochastic Screener (Daily)")

# --- Date Range: last 6 months ---
start = dt.date.today() - dt.timedelta(days=180)
end = dt.date.today()

signals = []

for symbol in v40_stocks:
    try:
        # --- Try NSE first ---
        df = get_history(symbol=symbol, start=start, end=end)
        if df.empty:
            raise ValueError("NSE data empty")
        df = df[["High","Low","Close"]].copy()

    except Exception:
        # --- Fallback to Yahoo Finance ---
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            df = ticker.history(start=start, end=end, interval="1d")
            df = df[["High","Low","Close"]].copy()
        except Exception:
            signals.append([symbol, "NO DATA", None, None, None, None, None])
            continue

    # --- Compute Stochastic (4,3,3) ---
    stoch = ta.momentum.StochasticOscillator(
        high=df["High"], low=df["Low"], close=df["Close"],
        window=4, smooth_window=3
    )
    df["%K"] = stoch.stoch()
    df["%D"] = stoch.stoch_signal()

    # --- Apply Strategy Rules ---
    last_signal = "HOLD"
    buy_price, target_3, target_5, three_pct_hit, five_pct_hit = None, None, None, None, None

    for i in range(1, len(df)):
        k, d = df["%K"].iloc[i], df["%D"].iloc[i]
        prev_k, prev_d = df["%K"].iloc[i-1], df["%D"].iloc[i-1]
        close_price = df["Close"].iloc[i]

        # BUY when both cross below 20
        if k < 20 and d < 20 and (prev_k >= 20 or prev_d >= 20):
            last_signal = "BUY"
            buy_price = close_price
            target_3 = buy_price * 1.03
            target_5 = buy_price * 1.05
            three_pct_hit, five_pct_hit = None, None

        # SELL when both cross above 80
        elif k > 80 and d > 80 and (prev_k <= 80 or prev_d <= 80):
            last_signal = "SELL"
            # Reset everything on SELL
            buy_price, target_3, target_5, three_pct_hit, five_pct_hit = None, None, None, None, None

        # Check targets if in a trade
        if buy_price:
            if not three_pct_hit and close_price >= target_3:
                three_pct_hit = target_3
            if not five_pct_hit and close_price >= target_5:
                five_pct_hit = target_5
                last_signal = "SELL"
                # Reset everything on final SELL
                buy_price, target_3, target_5, three_pct_hit, five_pct_hit = None, None, None, None, None

    signals.append([symbol, last_signal, buy_price, target_3, target_5, three_pct_hit, five_pct_hit])

# --- Show Results ---
signals_df = pd.DataFrame(
    signals, 
    columns=["Stock","Signal","Buy Price","Target 3%","Target 5%","3% Hit","5% Hit"]
)
st.dataframe(signals_df)
