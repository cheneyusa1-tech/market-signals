"""
每日信号生成脚本 — 由 GitHub Actions 自动运行
输出 signals.json，供 index.html 读取展示
"""
import yfinance as yf, pandas as pd, numpy as np, json, warnings
from datetime import datetime, timezone
warnings.filterwarnings("ignore")

INDICES = {
    "SPY": "标普500 S&P 500",
    "QQQ": "纳斯达克 Nasdaq 100",
    "DIA": "道琼斯 Dow Jones",
}

def signal_engine(price, vix, ma_fast=20, ma_slow=50):
    df = pd.DataFrame({"price": price, "vix": vix}).dropna()
    for w in [ma_fast, ma_slow]:
        df[f"ma{w}"] = df["price"].rolling(w).mean()
    df["ret_5d"]     = df["price"].pct_change(5)
    df["ret_21d"]    = df["price"].pct_change(21)
    df["above_fast"] = df["price"] > df[f"ma{ma_fast}"]
    df["above_slow"] = df["price"] > df[f"ma{ma_slow}"]
    df["vix_peak"]   = df["vix"].rolling(10).max()
    df["vix_cool"]   = df["vix"] < df["vix_peak"] * 0.85
    df["vix_10d"]    = df["vix"].shift(10)
    df["vix_spike"]  = df["vix"] > df["vix_10d"] * 1.40

    def make_pos(entry_c, exit_c):
        pos, in_p, cd = [], False, 0
        for i in range(len(df)):
            if cd > 0: cd -= 1
            if in_p:
                if exit_c.iloc[i]: in_p = False; cd = 5
                pos.append(1)
            else:
                if entry_c.iloc[i] and cd == 0: in_p = True
                pos.append(1 if in_p else 0)
        return pos

    entry20 = df["above_fast"] & (df["ret_5d"] > 0) & (df["ret_21d"] > 0) & df["vix_cool"]
    exit20  = ~df["above_fast"] | (df["ret_21d"] < -0.03) | df["vix_spike"]
    df["pos_fast"] = make_pos(entry20, exit20)

    entry50 = df["above_slow"] & (df["ret_5d"] > 0) & (df["ret_21d"] > 0) & df["vix_cool"]
    exit50  = ~df["above_slow"] | (df["ret_21d"] < -0.03) | df["vix_spike"]
    df["pos_slow"] = make_pos(entry50, exit50)
    return df

def backtest_annual(df, pos_col):
    dr = df["price"].pct_change()
    sr = df[pos_col].shift(1) * dr
    sc = (1 + sr).cumprod()
    bc = (1 + dr).cumprod()
    annual = []
    for yr in sorted(dr.index.year.unique()):
        m = dr.index.year == yr
        s_yr = (1 + sr[m]).prod() - 1
        b_yr = (1 + dr[m]).prod() - 1
        annual.append({
            "year": int(yr),
            "strategy": round(s_yr * 100, 1),
            "benchmark": round(b_yr * 100, 1),
            "alpha": round((s_yr - b_yr) * 100, 1),
        })
    cum_alpha = round((sc.iloc[-1] / bc.iloc[-1] - 1) * 100, 1)
    n = max(len(dr.dropna()) / 252, 0.01)
    cagr_s = round((sc.iloc[-1] ** (1/n) - 1) * 100, 1)
    cagr_b = round((bc.iloc[-1] ** (1/n) - 1) * 100, 1)
    mdd_s  = round(((sc - sc.cummax()) / sc.cummax()).min() * 100, 1)
    mdd_b  = round(((bc - bc.cummax()) / bc.cummax()).min() * 100, 1)
    sharpe = round((sr.mean() / sr.std()) * np.sqrt(252), 2) if sr.std() > 0 else 0
    return {
        "annual": annual, "cum_alpha": cum_alpha,
        "cagr": cagr_s, "bench_cagr": cagr_b,
        "mdd": mdd_s, "bench_mdd": mdd_b, "sharpe": sharpe,
        "invested_pct": round(df[pos_col].mean() * 100, 1),
    }

print("下载数据...")
vix = yf.download("^VIX", start="2010-01-01", progress=False)["Close"].squeeze()
out = {"updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "indices": {}}

for sym, name in INDICES.items():
    price = yf.download(sym, start="2010-01-01", progress=False)["Close"].squeeze()
    df    = signal_engine(price, vix)
    last  = df.iloc[-1]

    out["indices"][sym] = {
        "name": name,
        "date": str(df.index[-1].date()),
        "price": round(float(last.price), 2),
        "ma20":  round(float(last.ma20), 2),
        "ma50":  round(float(last.ma50), 2),
        "vix":   round(float(last.vix), 1),
        "ret_5d":  round(float(last.ret_5d) * 100, 2),
        "ret_21d": round(float(last.ret_21d) * 100, 2),
        "signal_fast": int(last.pos_fast),
        "signal_slow": int(last.pos_slow),
        "conditions": {
            "above_ma20":  bool(last.above_fast),
            "above_ma50":  bool(last.above_slow),
            "mom5_pos":    bool(last.ret_5d > 0),
            "mom21_pos":   bool(last.ret_21d > 0),
            "vix_cooling": bool(last.vix_cool),
            "vix_spike":   bool(last.vix_spike),
        },
        "backtest_fast": backtest_annual(df, "pos_fast"),
        "backtest_slow": backtest_annual(df, "pos_slow"),
    }
    print(f"  {sym}: fast={'多' if last.pos_fast else '空'}, slow={'多' if last.pos_slow else '空'}")

with open("signals.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("signals.json 已生成 ✅")
