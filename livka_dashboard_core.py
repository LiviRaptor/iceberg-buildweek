import json
import math
import os
import webbrowser
from datetime import datetime
from pathlib import Path

REQUIRED_PACKAGES = ("yfinance", "pandas")
CONFIG_FILE = "config.json"
DASHBOARD_FILE = "livka_dashboard.html"
GOAL_DEFAULT = 750000
RETIRE_YEAR = 2043
RETIRE_FLOAT = 2043 + 11 / 12
MONTHS_SK = ["Jan", "Feb", "Mar", "Apr", "maj", "jun", "jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

RATES = {
    "tlmeny": {"p1": 0.048, "p2": 0.050, "lbl": "SPYY ~5 % + LQQ ~4 % (Decay); po 10. roku ~5 %"},
    "konsenzus": {"p1": 0.085, "p2": 0.075, "lbl": "SPYY ~7 % + LQQ ~13 % blend; after year 10, leverage Declines -> ~7.5%"},
    "aiboom": {"p1": 0.1175, "p2": 0.090, "lbl": "SPYY ~9 % + LQQ ~20 %; po 10. roku ~9 %"},
}


def print_banner():
    print("=" * 52)
    print("  Livka Dashboard v62-refactor")
    print("=" * 52)


def ensure_dependencies():
    missing = []
    for package in REQUIRED_PACKAGES:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    if missing:
        print(
            "  Optional packages missing: "
            + ", ".join(missing)
            + " — history will use fallback data."
        )


def load_config(script_dir):
    config_name = os.environ.get("ICEBERG_CONFIG", CONFIG_FILE)
    config_path = Path(config_name)
    if not config_path.is_absolute():
        config_path = script_dir / config_path
    if not config_path.exists():
        raise FileNotFoundError(
            f"Missing {config_path}. Set ICEBERG_CONFIG or create config.json/config.demo.json."
        )
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def usable_price(value):
    try:
        price = float(value)
        return price if math.isfinite(price) and price > 0 else None
    except (TypeError, ValueError):
        return None


def get_latest_price_with_source(ticker, fallback_price=None):
    price = usable_price(fallback_price)
    if price is not None:
        print(f"  {ticker} IB live/config price: {price:.2f}")
        return price, "IB live"

    history = get_history(ticker, period="10d")
    if history is not None and not history.empty:
        price = usable_price(history.iloc[-1])
        if price is not None:
            print(f"  {ticker} Yahoo fallback last close: {price:.2f}")
            return price, "Yahoo fallback"

    raise ValueError(f"No usable price for {ticker}: config/IB and Yahoo failed")


def get_latest_price(ticker, fallback_price=None):
    price, _source = get_latest_price_with_source(ticker, fallback_price)
    return price


def get_history(ticker, period="3y"):
    try:
        import pandas as pd
        import yfinance as yf

        df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        close = df["Close"].dropna()
        if close.empty:
            raise ValueError("empty close history")
        return close
    except Exception as exc:
        print(f"  history {ticker}: {exc}")
        return None


def fallback_lqq_monthly():
    return [
        722.2, 759, 829, 765.2, 862.8, 932.8, 952.4, 764.6, 711.4, 793, 639.6, 562.6,
        477, 594.8, 555.8, 475, 478.2, 459.8, 387, 466.2, 478, 541.8, 535.6, 647.2, 712,
        755.4, 741.8, 687.2, 637.6, 753.8, 825.4, 883, 953.2, 983.8, 920.8, 966.6,
        1149.8, 1068.4, 1043.6, 1091.6, 1107.6, 1244, 1295.4, 1350.8, 1196.8, 971.8,
        927, 1121.6, 1211, 1324.8, 1292.6, 1410.2, 1578, 1495.6, 1478.8, 1485.2,
        1400.4, 1244, 1661.6, 2056, 2043.0,
    ]


LQQ_SPLIT_RATIO = 200
LQQ_SPLIT_DETECT_MULTIPLE = 20


def normalize_lqq_split_prices(values, lqq_price):
    # Yahoo can briefly mix pre/post split prices. Keep the dashboard on the current post-split scale.
    return values.where(values <= lqq_price * LQQ_SPLIT_DETECT_MULTIPLE, values / LQQ_SPLIT_RATIO)


def Market_regime_for(lqq_price, sma50d, sma200d):
    if sma200d and sma50d:
        if lqq_price > sma200d and sma50d > sma200d:
            return {
                "Market_regime": "BULL",
                "regime_color": "var(--teal)",
                "regime_text": "NASDAQ above SMA200 · positive momentum · LQQ-friendly environment",
                "regime_class": "st-ok",
                "regime_action": "hold LQQ",
            }
        if lqq_price < sma200d and sma50d < sma200d:
            return {
                "Market_regime": "BEAR",
                "regime_color": "var(--red)",
                "regime_text": "NASDAQ below SMA200 · negative momentum · leverage risk",
                "regime_class": "st-danger",
                "regime_action": "consider reducing LQQ",
            }
        return {
            "Market_regime": "NEUTRAL",
            "regime_color": "var(--gold)",
            "regime_text": "Market without clear direction · elevated volatility",
            "regime_class": "st-warn",
            "regime_action": "caution",
        }

    return {
        "Market_regime": "UNKNOWN",
        "regime_color": "var(--soft)",
        "regime_text": "Not enough data for the regime engine",
        "regime_class": "st-warn",
        "regime_action": "check data",
    }


def get_lqq_Market_snapshot(lqq_price):
    history = get_history("LQQ.PA")
    if history is None or len(history) < 50:
        return {
            "sma50d": 1690.0 / LQQ_SPLIT_RATIO,
            "sma100d": 1559.0 / LQQ_SPLIT_RATIO,
            "sma200d": 1501.0 / LQQ_SPLIT_RATIO,
            "sma50w": 1463.0 / LQQ_SPLIT_RATIO,
            "monthly_lqq": [round(x / LQQ_SPLIT_RATIO, 2) for x in fallback_lqq_monthly()],
            **Market_regime_for(lqq_price, 1690.0 / LQQ_SPLIT_RATIO, 1501.0 / LQQ_SPLIT_RATIO),
        }

    history = normalize_lqq_split_prices(history, lqq_price)

    sma50d = float(history.rolling(50).mean().iloc[-1])
    sma100d = float(history.rolling(100).mean().iloc[-1]) if len(history) >= 100 else None
    sma200d = float(history.rolling(200).mean().iloc[-1]) if len(history) >= 200 else None
    weekly = history.resample("W").last()
    sma50w = float(weekly.rolling(50).mean().iloc[-1]) if len(weekly) >= 50 else None
    monthly_lqq = [round(float(x), 2) for x in history.resample("ME").last().iloc[-61:]]
    s100 = f"{sma100d:.0f}" if sma100d else "?"
    s200 = f"{sma200d:.0f}" if sma200d else "?"
    print(f"  SMA 50d={sma50d:.0f} 100d={s100} 200d={s200}")
    return {
        "sma50d": sma50d,
        "sma100d": sma100d,
        "sma200d": sma200d,
        "sma50w": sma50w,
        "monthly_lqq": monthly_lqq,
        **Market_regime_for(lqq_price, sma50d, sma200d),
    }


def closest_ma(price, sma50d, sma100d, sma200d, sma50w):
    mas = {}
    if sma50d:
        mas[f"SMA 50d (~{sma50d:.0f})"] = abs(price - sma50d)
    if sma100d:
        mas[f"SMA 100d (~{sma100d:.0f})"] = abs(price - sma100d)
    if sma200d:
        mas[f"SMA 200d (~{sma200d:.0f})"] = abs(price - sma200d)
    if sma50w:
        mas[f"SMA 50W (~{sma50w:.0f})"] = abs(price - sma50w)
    return min(mas, key=mas.get) if mas else "--"


def enrich_limits(limits, lqq_price, sma50d, sma100d, sma200d, sma50w):
    for limit in limits:
        limit["dist_pct"] = round((limit["price"] - lqq_price) / lqq_price * 100, 1)
        limit["volume"] = limit["price"] * limit["qty"]
        limit["ma"] = closest_ma(limit["price"], sma50d, sma100d, sma200d, sma50w)
        limit["bar_pct"] = min(100, round(abs(limit["dist_pct"]) / 65 * 100))
    return limits


def project(start, monthly, inc_yr, inc_amt, lump_yr, lump_amt, pause_yr, scenario, chart_end, goal):
    rates = RATES[scenario]
    value, total_c, goal_yr = start, 0, None
    points = [{"x": 2026, "y": round(value)}]
    for year in range(2027, chart_end + 1):
        rate = rates["p1"] if (year - 2026) <= 10 else rates["p2"]
        if year > RETIRE_YEAR:
            contribution = 0
            lump = 0
        else:
            month_value = monthly + (inc_amt if inc_amt > 0 and year >= inc_yr else 0)
            contribution = 0 if year == pause_yr else month_value * 12
            lump = lump_amt if lump_amt > 0 and year == lump_yr else 0
        value = value * (1 + rate) + contribution + lump
        total_c += contribution + lump
        if goal_yr is None and value >= goal:
            goal_yr = year
        points.append({"x": year, "y": round(value)})
    return points, goal_yr, round(value)


def find_breakeven(points, scenario, goal):
    rates = RATES[scenario]
    for i in range(1, len(points)):
        year, value = points[i]["x"], points[i]["y"]
        if year > RETIRE_YEAR:
            break
        years_left = RETIRE_FLOAT - year
        if years_left <= 0:
            return "teraz!"
        p1 = min(years_left, max(0, 2036 - year))
        p2 = max(0, years_left - p1)
        if value * (1 + rates["p1"]) ** p1 * (1 + rates["p2"]) ** p2 >= goal:
            previous = points[i - 1]
            for month in range(13):
                years_left_2 = RETIRE_FLOAT - (previous["x"] + month / 12)
                if years_left_2 <= 0:
                    return f"{MONTHS_SK[0]} {previous['x']}"
                q1 = min(years_left_2, max(0, 2036 - previous["x"] - month / 12))
                q2 = max(0, years_left_2 - q1)
                if previous["y"] * (1 + rates["p1"]) ** q1 * (1 + rates["p2"]) ** q2 >= goal:
                    return f"{MONTHS_SK[month % 12]} {previous['x'] if month < 12 else year}"
            return f"early {year}"
    return "after 2043"


def sc(value):
    return "#83c89a" if value >= 0 else "#df9270"


def dashboard_output_path(script_dir):
    return script_dir / DASHBOARD_FILE


def write_dashboard(html, output_path, fallback_dir):
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
    except PermissionError:
        output_path = fallback_dir / DASHBOARD_FILE
        output_path.write_text(html, encoding="utf-8")
    print(f"\n  Saved: {output_path}")
    webbrowser.open(f"file://{output_path}")
