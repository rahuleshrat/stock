import streamlit as st
import pandas as pd
import datetime as dt
from nsepy import get_history
import ta
import yfinance as yf
import matplotlib.pyplot as plt

# --- V40 Stock Basket ---
v40_stocks = [
    "RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","HINDUNILVR","SBIN","BHARTIARTL",
    "AXISBANK","KOTAKBANK","ITC","LT","BAJFINANCE","ASIANPAINT","MARUTI","SUNPHARMA",
    "ULTRACEMCO","HCLTECH","WIPRO","TECHM","ONGC","POWERGRID","NTPC","ADANIPORTS",
    "COALINDIA","NESTLEIND","TITAN","BAJAJFINSV","HDFCLIFE","GRASIM","BRITANNIA",
    "DRREDDY","CIPLA","EICHERMOT","HEROMOTOCO","M&M","DIVISLAB","BPCL","SHREECEM","UPL"
]

st.title("📈 NSE V40 Stochastic Screener (Daily – Current Only)")

# --- Date Range: last 6 months ---
start = dt.date.today() - dt.timedelta(days=180)
end = dt.date.today()

signals = []

def fetch_data(symbol):
    """Fetch stock data from NSE, fallback to Yahoo Finance"""
    try:
        df = get_history(symbol=symbol, start=start, end=end)
        if df.empty:
            raise ValueError("NSE data empty")
        df = df[["High","Low","Close"]].copy()
    except Exception:
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            df = ticker.history(start=start, end=end, interval="1d")
            df = df[["High","Low","Close"]].copy()
        except Exception:
            return None
    return df

# --- Loop through all V40 and compute CURRENT signal only ---
for symbol in v40_stocks:
    df = fetch_data(symbol)
    if df is None or df.empty:
        signals.append([symbol, "NO DATA", None, None, None, None, None])
        continue

    # Compute stochastic (4,3,3)
    stoch = ta.momentum.StochasticOscillator(
        high=df["High"], low=df["Low"], close=df["Close"],
        window=4, smooth_window=3
    )
    df["%K"] = stoch.stoch()
    df["%D"] = stoch.stoch_signal()

    # --- Get latest row values ---
    current_k = df["%K"].iloc[-1]
    current_d = df["%D"].iloc[-1]
    current_price = df["Close"].iloc[-1]

    # --- Signal based ONLY on today ---
    if current_k < 20 and current_d < 20:
        signal = "BUY"
        buy_price = round(current_price, 2)
        target_3 = round(buy_price * 1.03, 2)
        target_5 = round(buy_price * 1.05, 2)
        three_pct_hit = target_3 if current_price >= target_3 else None
        five_pct_hit = target_5 if current_price >= target_5 else None
    elif current_k > 80 and current_d > 80:
        signal = "SELL"
        buy_price, target_3, target_5, three_pct_hit, five_pct_hit = None, None, None, None, None
    else:
        signal = "HOLD"
        buy_price, target_3, target_5, three_pct_hit, five_pct_hit = None, None, None, None, None

    signals.append([symbol, signal, buy_price, target_3, target_5, three_pct_hit, five_pct_hit])

# --- Summary Table with Color Coding ---
signals_df = pd.DataFrame(
    signals,
    columns=["Stock","Signal","Buy Price","Target 3%","Target 5%","3% Hit","5% Hit"]
)

def highlight_rows(row):
    if row["Signal"] == "BUY":
        return ['background-color: lightgreen'] * len(row)
    elif row["Signal"] == "SELL":
        return ['background-color: salmon'] * len(row)
    elif row["Signal"] == "HOLD":
        return ['background-color: lightyellow'] * len(row)
    elif row["Signal"] == "NO DATA":
        return ['background-color: lightgrey'] * len(row)
    else:
        return [''] * len(row)

styled_df = signals_df.style.apply(highlight_rows, axis=1)

st.subheader("📊 Screener Summary (Today’s Signal Only)")
st.dataframe(styled_df, use_container_width=True)

# --- Plotting Section ---
st.subheader("📈 Stochastic & Price Charts with Signals")
selected_stock = st.selectbox("Choose a stock", v40_stocks)

df = fetch_data(selected_stock)
if df is not None and not df.empty:
    stoch = ta.momentum.StochasticOscillator(
        high=df["High"], low=df["Low"], close=df["Close"],
        window=4, smooth_window=3
    )
    df["%K"] = stoch.stoch()
    df["%D"] = stoch.stoch_signal()

    # --- Find buy/sell points in history ---
    buy_points, sell_points = [], []
    for i in range(1, len(df)):
        k, d = df["%K"].iloc[i], df["%D"].iloc[i]
        prev_k, prev_d = df["%K"].iloc[i-1], df["%D"].iloc[i-1]
        date = df.index[i]
        price = df["Close"].iloc[i]

        if k < 20 and d < 20 and (prev_k >= 20 or prev_d >= 20):
            buy_points.append((date, k, price))
        elif k > 80 and d > 80 and (prev_k <= 80 or prev_d <= 80):
            sell_points.append((date, k, price))

    # --- Plot Stochastic Oscillator ---
    fig, ax = plt.subplots(figsize=(10,5))
    ax.plot(df.index, df["%K"], label="%K (4)", color="blue")
    ax.plot(df.index, df["%D"], label="%D (3)", color="orange")
    ax.axhline(20, color="green", linestyle="--", alpha=0.7)
    ax.axhline(80, color="red", linestyle="--", alpha=0.7)

    for date, k_val, price in buy_points:
        ax.scatter(date, k_val, marker="^", color="green", s=100)
        ax.text(date, k_val+2, f"{price:.1f}", color="green", fontsize=8)

    for date, k_val, price in sell_points:
        ax.scatter(date, k_val, marker="v", color="red", s=100)
        ax.text(date, k_val-5, f"{price:.1f}", color="red", fontsize=8)

    ax.set_title(f"Stochastic Oscillator (4,3,3) - {selected_stock}")
    ax.legend()
    st.pyplot(fig)

    # --- Plot Price Chart ---
    fig2, ax2 = plt.subplots(figsize=(10,5))
    ax2.plot(df.index, df["Close"], label="Close Price", color="black")

    for date, _, price in buy_points:
        ax2.scatter(date, price, marker="^", color="green", s=100)
        ax2.text(date, price*1.01, f"{price:.1f}", color="green", fontsize=8)

    for date, _, price in sell_points:
        ax2.scatter(date, price, marker="v", color="red", s=100)
        ax2.text(date, price*0.99, f"{price:.1f}", color="red", fontsize=8)

    ax2.set_title(f"Price Chart with BUY/SELL signals - {selected_stock}")
    ax2.legend()
    st.pyplot(fig2)
