#!/usr/bin/env python3
"""
Livka Investment Dashboard v62
Prices: yfinance/IBKR/config  |  Portfolio: demo config or optional private config.json
Spustenie: python3 livka_dashboard_claude_v62.py
"""
import json

from livka_dashboard_core import (
    GOAL_DEFAULT,
    RATES,
    dashboard_output_path,
    ensure_dependencies,
    enrich_limits,
    find_breakeven,
    get_latest_price_with_source,
    get_lqq_Market_snapshot,
    load_config,
    print_banner,
    project,
    sc,
    write_dashboard,
)
from datetime import datetime
from pathlib import Path


def load_template(path: Path, **values):
    text = path.read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def main():
    script_dir = Path(__file__).resolve().parent
    print_banner()
    ensure_dependencies()

    cfg = load_config(script_dir)
    portfolio = cfg["portfolio"]
    SPYY_SHARES = portfolio["SPYY_SHARES"]
    SPYY_AVG_COST = portfolio["SPYY_AVG_COST"]
    LQQ_SHARES = portfolio["LQQ_SHARES"]
    LQQ_AVG_COST = portfolio["LQQ_AVG_COST"]
    CASH = portfolio["CASH"]
    RESERVE = portfolio["RESERVE"]
    NET_LIQ_IB = portfolio["NET_LIQ_IB"]
    LIMITS = cfg["limits"]
    GOAL = cfg.get("goal", GOAL_DEFAULT)
    retirement = cfg.get("retirement", {})
    RETIRE_DISPLAY = retirement.get("display", "Nov 2043")
    CHART_END = retirement.get("chart_end_year", 2053)
    retire_year = int(retirement.get("year", 2043))
    retire_month = int(retirement.get("month", 11))
    today_for_retire = datetime.now()
    months_left = max(0, (retire_year - today_for_retire.year) * 12 + retire_month - today_for_retire.month)
    retire_years_left, retire_months_left = divmod(months_left, 12)
    retire_countdown = f"Retirement in <strong>{retire_years_left}</strong> years and <strong>{retire_months_left}</strong> months"

    print("\n[1/3] Fetching prices...")
    lqq_price, lqq_price_source = get_latest_price_with_source("LQQ.PA", portfolio.get("LQQ_LAST_PRICE"))
    spyy_price, spyy_price_source = get_latest_price_with_source("SPYY.DE", portfolio.get("SPYY_LAST_PRICE"))
    if lqq_price_source == spyy_price_source:
        price_source = lqq_price_source
    else:
        price_source = f"mix: LQQ {lqq_price_source}, SPYY {spyy_price_source}"
    price_source_color = "#4ADE80" if price_source == "IB live" else "var(--dim)"

    snapshot = get_lqq_Market_snapshot(lqq_price)
    sma50d = snapshot["sma50d"]
    sma100d = snapshot["sma100d"]
    sma200d = snapshot["sma200d"]
    sma50w = snapshot["sma50w"]
    monthly_lqq = snapshot["monthly_lqq"]
    Market_regime = snapshot["Market_regime"]
    regime_color = snapshot["regime_color"]
    regime_text = snapshot["regime_text"]
    regime_class = snapshot["regime_class"]
    regime_action = snapshot["regime_action"]

    print("\n[2/3] Calculating...")
    spyy_value = round(SPYY_SHARES * spyy_price, 2)
    spyy_cost = round(SPYY_SHARES * SPYY_AVG_COST, 2)
    spyy_pnl = round(spyy_value - spyy_cost, 2)
    spyy_pnl_pct = round(spyy_pnl / spyy_cost * 100, 1) if spyy_cost else 0
    lqq_value = round(LQQ_SHARES * lqq_price, 2)
    lqq_cost = round(LQQ_SHARES * LQQ_AVG_COST, 2)
    lqq_pnl = round(lqq_value - lqq_cost, 2)
    lqq_pnl_pct = round(lqq_pnl / lqq_cost * 100, 1) if lqq_cost else 0
    invested = round(spyy_value + lqq_value, 2)
    net_liq = round(invested + CASH, 2)
    dry_powder = round(CASH - RESERVE, 2)
    LIMITS = enrich_limits(LIMITS, lqq_price, sma50d, sma100d, sma200d, sma50w)
    limits_total = sum(limit["price"] * limit["qty"] for limit in LIMITS)
    cash_gap = round(dry_powder - limits_total, 2)
    total_pnl = round(spyy_pnl + lqq_pnl, 2)
    total_pnl_pct = round(total_pnl / (spyy_cost + lqq_cost) * 100, 1)

    pts_base, goal_yr, final_val = project(invested, 800, 2027, 0, 2027, 0, 0, "konsenzus", CHART_END, GOAL)
    be_base = find_breakeven(pts_base, "konsenzus", GOAL)
    today_str = datetime.now().strftime("%-d. %-m. %Y %H:%M")
    print(
        f"  Net Liq: {net_liq:,.2f} EUR  "
        f"SPYY: {spyy_pnl:+,.0f}({spyy_pnl_pct:+.1f}%)  "
        f"LQQ: {lqq_pnl:+,.0f}({lqq_pnl_pct:+.1f}%)"
    )
    print(f"  Break even: {be_base}  |  750k: {goal_yr}")

    # ── HTML ─────────────────────────────────────────────────────
    print("\n[3/3] Generating HTML...")
    munger_image_uri = "assets/munger.png"
    karpis_image = script_dir / "assets" / "karpis.png"
    if karpis_image.exists():
        karpis_media_html = (
            f'<img class="mentor-photo" width="320" height="320" '
            f'src="assets/karpis.png" alt="Juraj Karpis">'
        )
    else:
        karpis_media_html = '<div class="mentor-photo mentor-placeholder">assets/karpis.png</div>'


    lim_rows=''
    for idx, lim in enumerate(LIMITS):
        col='#edc676' if lim['dist_pct']>-35 else '#df9270'
        w=lim['bar_pct']
        # akcia: ak vzdialenost < 5% = pozor, inak automaticky
        if abs(lim['dist_pct'])<5:   action='<span class="lim-alert">\u26a0 Within reach!</span>'
        elif abs(lim['dist_pct'])<15: action='<span class="lim-watch">Sledova\u0165</span>'
        else:                         action='<span class="lim-ok">GTC \u00b7 auto</span>'
        lim_rows += (
            f'<tr data-limit-row="{idx}"><td style="font-weight:500">{lim["price"]:,} \u20ac</td>'
            f'<td class="r">{lim["qty"]}</td>'
            f'<td id="live-limit-volume-{idx}" class="r">{lim["volume"]:,} \u20ac</td>'
            f'<td id="live-limit-dist-{idx}" class="r" style="color:{col}">{lim["dist_pct"]:+.1f} %'
            f'<div class="dbar"><div id="live-limit-bar-{idx}" class="dbar-f" style="width:{w}%"></div></div></td>'
            f'<td id="live-limit-ma-{idx}">{lim["ma"]}</td>'
            f'<td id="live-limit-action-{idx}">{action}</td></tr>'
        )

    ring_offset  = round(214*(1-invested/GOAL),1)
    rates_js     = json.dumps(RATES)
    mc_js        = json.dumps(monthly_lqq)
    lim_prices   = ', '.join(str(l['price']) for l in LIMITS)
    sma100_str   = f'{sma100d:.0f}' if sma100d else '--'
    sma200_str   = f'{sma200d:.0f}' if sma200d else '--'
    sma50w_str   = f'{sma50w:.0f}'  if sma50w  else '--'
    lqq_pct_num = lqq_value / invested * 100 if invested else 0.0
    first_limit = LIMITS[0] if LIMITS else None
    if first_limit:
        first_dist = first_limit['dist_pct']
        if abs(first_dist) < 5:
            limit_alert_class = 'is-hot'
            limit_alert_main = f"TRIGGER ALERT · {first_limit['price']:.2f} €"
        elif abs(first_dist) < 15:
            limit_alert_class = 'is-watch'
            limit_alert_main = f"WATCH · {first_limit['price']:.2f} €"
        else:
            limit_alert_class = ''
            limit_alert_main = f"1st limit order {first_limit['price']:.2f} €"
        limit_alert_sub = f"distance {first_dist:+.1f} % from LQQ"
    else:
        limit_alert_class = ''
        limit_alert_main = 'bez limitiek'
        limit_alert_sub = 'no trigger'


    header_section = load_template(
        script_dir / "templates_codex" / "header_section.html",
        today_str=today_str,
        spyy_price=f"{spyy_price:,.1f}",
        lqq_price=f"{lqq_price:,.1f}",
        price_source=price_source,
        price_source_color=price_source_color,
        RETIRE_DISPLAY=RETIRE_DISPLAY,
        RETIRE_DISPLAY_EN=str(RETIRE_DISPLAY).replace("nov", "Nov"),
        retire_countdown=retire_countdown,
        goal_pct=f"{invested / GOAL * 100:.1f}",
        Market_regime=Market_regime,
        regime_badge_class={"BULL": "is-bull", "BEAR": "is-bear", "NEUTRAL": "is-neutral"}.get(Market_regime, ""),
        regime_icon={"BULL": "♉", "BEAR": "↓", "NEUTRAL": "•"}.get(Market_regime, "•"),
        lqq_pct=f"{lqq_pct_num:.1f}",
        limit_alert_class=limit_alert_class,
        limit_alert_main=limit_alert_main,
        limit_alert_sub=limit_alert_sub,
    )

    portfolio_section = load_template(
        script_dir / "templates_codex" / "portfolio_section.html",
        net_liq=f"{net_liq:,.0f}",
        invested=f"{invested:,.0f}",
        total_pnl_color=sc(total_pnl),
        total_pnl=f"{total_pnl:+,.0f}",
        total_pnl_pct=f"{total_pnl_pct:+.1f}",
        SPYY_SHARES=f"{SPYY_SHARES:.4f}",
        SPYY_AVG_COST=f"{SPYY_AVG_COST:.2f}",
        spyy_price=f"{spyy_price:.2f}",
        spyy_pnl_color=sc(spyy_pnl),
        spyy_pnl=f"{spyy_pnl:+,.0f}",
        spyy_pnl_pct=f"{spyy_pnl_pct:+.1f}",
        spyy_value=f"{spyy_value:,.0f}",
        LQQ_SHARES_INT=int(LQQ_SHARES),
        LQQ_AVG_COST=f"{LQQ_AVG_COST:.2f}",
        lqq_price=f"{lqq_price:.2f}",
        lqq_pnl_color=sc(lqq_pnl),
        lqq_pnl=f"{lqq_pnl:+,.0f}",
        lqq_pnl_pct=f"{lqq_pnl_pct:+.1f}",
        lqq_value=f"{lqq_value:,.0f}",
        CASH=f"{CASH:,.2f}",
        RESERVE=f"{RESERVE:,.0f}",
        dry_powder=f"{dry_powder:,.2f}",
        limits_total=f"{limits_total:,}",
        cash_gap_color="#edc676" if cash_gap >= -2000 else "#df9270",
        cash_gap=f"{cash_gap:+,.2f}",
        spyy_pct=f"{spyy_value / invested * 100:.1f}" if invested else "0.0",
        lqq_pct=f"{lqq_value / invested * 100:.1f}" if invested else "0.0",
    )

    risk_section = load_template(
        script_dir / "templates_codex" / "risk_section.html",
        lqq_share_pct=f"{lqq_value / (spyy_value + lqq_value) * 100:.1f}" if (spyy_value + lqq_value) else "0.0",
        lqq_value=f"{lqq_value:,.0f}",
        limits_total=f"{limits_total:,.0f}",
        lqq_max_exposure=f"{lqq_value + limits_total:,.0f}",
        regime_color=regime_color,
        Market_regime=Market_regime,
        regime_text=regime_text,
        regime_class=regime_class,
        regime_action=regime_action,
    )

    trajectory_section = load_template(
        script_dir / "templates_codex" / "trajectory_section.html",
        CHART_END=CHART_END,
        RETIRE_DISPLAY=RETIRE_DISPLAY,
        RETIRE_DISPLAY_EN=str(RETIRE_DISPLAY).replace("nov", "Nov"),
    )

    limits_section = load_template(
        script_dir / "templates_codex" / "limits_section.html",
        lim_rows=lim_rows,
        sma50d=f"{sma50d:.0f}",
        sma100_str=sma100_str,
        sma200_str=sma200_str,
        sma50w_str=sma50w_str,
    )

    munger_section = load_template(
        script_dir / "templates_codex" / "munger_section.html",
        munger_image_uri=munger_image_uri,
        karpis_media_html=karpis_media_html,
    )

    panic_section = load_template(
        script_dir / "templates_codex" / "panic_section.html"
    )

    dashboard_css = load_template(
        script_dir / "static_codex" / "dashboard.css",
        ring_offset=ring_offset,
    )

    dashboard_js = load_template(
        script_dir / "static_codex" / "dashboard.js",
        rates_js=rates_js,
        invested_start=f"{invested:.2f}",
        CHART_END=CHART_END,
        invested_spark=f"{invested:.0f}",
        mc_js=mc_js,
        lim_prices=lim_prices,
        lqq_price_1=f"{lqq_price:.1f}",
        lqq_price_0=f"{lqq_price:.0f}",
        spyy_value_raw=spyy_value,
        lqq_value_raw=lqq_value,
    )

    html = load_template(
        script_dir / "templates_codex" / "base.html",
        dashboard_css=dashboard_css,
        dashboard_js=dashboard_js,
        header_section=header_section,
        portfolio_section=portfolio_section,
        risk_section=risk_section,
        trajectory_section=trajectory_section,
        limits_section=limits_section,
        munger_section=munger_section,
        panic_section=panic_section,
        today_str=today_str,
    )



    write_dashboard(html, dashboard_output_path(script_dir), script_dir)
    print("\nDone!")


if __name__ == "__main__":
    main()
