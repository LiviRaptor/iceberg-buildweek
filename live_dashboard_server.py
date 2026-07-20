#!/usr/bin/env python3
'''Experimental local live server for Livka dashboard.

It does not replace the static up flow. It serves the generated HTML and, when
IB Gateway live data is available, overlays selected values once per second.
'''
import json
import math
import mimetypes
import os
import threading
import urllib.error
import urllib.request
import webbrowser

from livka_dashboard_core import (
    enrich_limits,
    get_latest_price_with_source,
    get_lqq_Market_snapshot,
    Market_regime_for,
)
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
HTML_FILE = ROOT / 'livka_dashboard.html'
CONFIG_FILE = Path(os.environ.get('ICEBERG_CONFIG', 'config.json'))
if not CONFIG_FILE.is_absolute():
    CONFIG_FILE = ROOT / CONFIG_FILE
DEMO_MODE = CONFIG_FILE.name == 'config.demo.json'
HOST = '127.0.0.1'
PORT = 8765
MARKET_CONTEXT = None



def clean_price(value):
    try:
        price = float(value)
    except Exception:
        return None
    return price if math.isfinite(price) and price > 0 else None


def load_config():
    with open(CONFIG_FILE, encoding='utf-8') as f:
        return json.load(f)


def get_Market_context(lqq_price):
    global MARKET_CONTEXT
    if MARKET_CONTEXT is None:
        try:
            MARKET_CONTEXT = get_lqq_Market_snapshot(lqq_price)
        except Exception:
            sma50d = 1690.0 / 200.0
            sma100d = 1559.0 / 200.0
            sma200d = 1501.0 / 200.0
            sma50w = 1463.0 / 200.0
            MARKET_CONTEXT = {
                'sma50d': sma50d,
                'sma100d': sma100d,
                'sma200d': sma200d,
                'sma50w': sma50w,
                **Market_regime_for(lqq_price, sma50d, sma200d),
            }
    regime = Market_regime_for(lqq_price, MARKET_CONTEXT.get('sma50d'), MARKET_CONTEXT.get('sma200d'))
    return {**MARKET_CONTEXT, **regime}


def limit_action(dist_pct):
    if abs(dist_pct) < 5:
        return '<span class="lim-alert">⚠ Within reach!</span>'
    if abs(dist_pct) < 15:
        return '<span class="lim-watch">Watch</span>'
    return '<span class="lim-ok">GTC · auto</span>'


def calc_snapshot(spyy_price=None, lqq_price=None, live=False, status='config snapshot'):
    cfg = load_config()
    pf = cfg['portfolio']

    spyy_price = clean_price(spyy_price) or clean_price(pf.get('SPYY_LAST_PRICE'))
    lqq_price = clean_price(lqq_price) or clean_price(pf.get('LQQ_LAST_PRICE'))
    if not spyy_price:
        spyy_price, _source = get_latest_price_with_source('SPYY.DE', pf.get('SPYY_LAST_PRICE'))
    if not lqq_price:
        lqq_price, _source = get_latest_price_with_source('LQQ.PA', pf.get('LQQ_LAST_PRICE'))
    if not spyy_price or not lqq_price:
        raise RuntimeError('Missing usable SPYY/LQQ price')

    spyy_shares = float(pf['SPYY_SHARES'])
    lqq_shares = float(pf['LQQ_SHARES'])
    spyy_cost = spyy_shares * float(pf['SPYY_AVG_COST'])
    lqq_cost = lqq_shares * float(pf['LQQ_AVG_COST'])
    cash = float(pf['CASH'])

    spyy_value = spyy_shares * spyy_price
    lqq_value = lqq_shares * lqq_price
    invested = spyy_value + lqq_value
    net_liq = invested + cash
    spyy_pnl = spyy_value - spyy_cost
    lqq_pnl = lqq_value - lqq_cost
    total_pnl = spyy_pnl + lqq_pnl
    total_cost = spyy_cost + lqq_cost

    def pct(value, base):
        return value / base * 100 if base else 0.0

    Market = get_Market_context(lqq_price)
    limits = enrich_limits(
        [dict(limit) for limit in load_config().get('limits', [])],
        lqq_price,
        Market.get('sma50d'),
        Market.get('sma100d'),
        Market.get('sma200d'),
        Market.get('sma50w'),
    )
    live_limits = []
    for idx, limit in enumerate(limits):
        live_limits.append({
            'idx': idx,
            'price': limit['price'],
            'qty': limit['qty'],
            'volume': limit['volume'],
            'dist_pct': limit['dist_pct'],
            'bar_pct': limit['bar_pct'],
            'ma': limit['ma'],
            'color': '#edc676' if limit['dist_pct'] > -35 else '#df9270',
            'action': limit_action(limit['dist_pct']),
        })

    return {
        'ok': True,
        'live': bool(live),
        'status': status,
        'updated_at': datetime.now().strftime('%H:%M:%S'),
        'spyy_price': spyy_price,
        'lqq_price': lqq_price,
        'spyy_value': spyy_value,
        'lqq_value': lqq_value,
        'invested': invested,
        'net_liq': net_liq,
        'spyy_pnl': spyy_pnl,
        'spyy_pnl_pct': pct(spyy_pnl, spyy_cost),
        'lqq_pnl': lqq_pnl,
        'lqq_pnl_pct': pct(lqq_pnl, lqq_cost),
        'total_pnl': total_pnl,
        'total_pnl_pct': pct(total_pnl, total_cost),
        'spyy_pct': pct(spyy_value, invested),
        'lqq_pct': pct(lqq_value, invested),
        'cash': cash,
        'reserve': float(pf.get('RESERVE', 0)),
        'Market_regime': Market.get('Market_regime', 'UNKNOWN'),
        'regime_class': Market.get('regime_class', 'st-warn'),
        'limits': live_limits,
    }


class LiveState:
    def __init__(self):
        self.lock = threading.Lock()
        self.snapshot = calc_snapshot()

    def start(self):
        thread = threading.Thread(target=self._run_ib, daemon=True)
        thread.start()

    def get(self):
        with self.lock:
            return dict(self.snapshot)

    def set_snapshot(self, **kwargs):
        with self.lock:
            self.snapshot = calc_snapshot(**kwargs)

    def _run_ib(self):
        if DEMO_MODE:
            while True:
                self.set_snapshot(live=True, status='IBKR LIVE · DEMO FEED')
                threading.Event().wait(1)

        try:
            import asyncio
            asyncio.set_event_loop(asyncio.new_event_loop())
            from ib_insync import IB, Stock
        except Exception as exc:
            self.set_snapshot(live=False, status=f'IB module unavailable: {exc}')
            return

        ib = IB()
        try:
            ib.connect('127.0.0.1', 4002, clientId=78, timeout=10)
            ib.sleep(2)

            spyy_contract = None
            for position in ib.positions():
                if position.contract.symbol == 'SPYY':
                    spyy_contract = position.contract
                    break
            if spyy_contract is None:
                raise RuntimeError('SPYY position contract not found')

            lqq_contract = Stock(symbol='LQQ', exchange='IBIS', currency='EUR')
            ib.qualifyContracts(lqq_contract)
            ib.reqMarketDataType(1)
            spyy_ticker = ib.reqMktData(spyy_contract)
            lqq_ticker = ib.reqMktData(lqq_contract)

            def fresh_tick(ticker, max_age_seconds=180):
                tick_time = getattr(ticker, 'time', None)
                if not tick_time:
                    return False
                try:
                    now = datetime.now(tick_time.tzinfo) if tick_time.tzinfo else datetime.now()
                    return abs((now - tick_time).total_seconds()) <= max_age_seconds
                except Exception:
                    return False

            def ticker_price(ticker):
                bid = clean_price(getattr(ticker, 'bid', None))
                ask = clean_price(getattr(ticker, 'ask', None))
                last = clean_price(getattr(ticker, 'last', None))
                close = clean_price(getattr(ticker, 'close', None))
                Market = clean_price(ticker.MarketPrice())
                fresh = fresh_tick(ticker)

                if fresh and bid and ask:
                    return (bid + ask) / 2, 'live', True
                if fresh and last:
                    return last, 'live', True
                if Market:
                    return Market, 'last/close', False
                if last:
                    return last, 'last', False
                if close:
                    return close, 'close', False
                return None, 'waiting for IB ticks', False

            while True:
                ib.sleep(1)
                spyy_price, spyy_source, spyy_live = ticker_price(spyy_ticker)
                lqq_price, lqq_source, lqq_live = ticker_price(lqq_ticker)

                if spyy_price and lqq_price:
                    both_live = spyy_live and lqq_live
                    status = f'SPYY: {spyy_source} · LQQ: {lqq_source}'
                    self.set_snapshot(spyy_price=spyy_price, lqq_price=lqq_price, live=both_live, status=status)
                else:
                    self.set_snapshot(live=False, status=f'SPYY: {spyy_source} · LQQ: {lqq_source}')
        except Exception as exc:
            self.set_snapshot(live=False, status=f'IB disconnected: {exc}')


LIVE = LiveState()


def build_guardrail_context(snapshot):
    limits = snapshot.get('limits') or []
    first_limit = limits[0] if limits else {}
    return {
        'market_regime': snapshot.get('Market_regime'),
        'lqq_exposure_pct': round(float(snapshot.get('lqq_pct', 0)), 1),
        'spyy_exposure_pct': round(float(snapshot.get('spyy_pct', 0)), 1),
        'cash_eur': round(float(snapshot.get('cash', 0)), 2),
        'reserve_eur': round(float(snapshot.get('reserve', 0)), 2),
        'net_liq_eur': round(float(snapshot.get('net_liq', 0)), 2),
        'first_limit_price': first_limit.get('price'),
        'first_limit_distance_pct': first_limit.get('dist_pct'),
        'scenario_checkpoints': ['2029 possible income shock', '2033 possible income shock'],
    }


def demo_guardrail_review(snapshot):
    ctx = build_guardrail_context(snapshot)
    dist = ctx.get('first_limit_distance_pct')
    dist_text = f"{dist:.1f}% from the first limit order" if isinstance(dist, (int, float)) else 'not near a limit trigger'
    return {
        'ok': True,
        'mode': 'Deterministic demo review',
        'review': (
            f"Plan consistent. LQQ exposure is {ctx['lqq_exposure_pct']:.1f}%, cash reserve is visible, and the portfolio is {dist_text}.\n"
            "Watch LQQ leverage drift and the 2029/2033 personal risk windows. Not investment advice."
        ),
    }


def guardrail_review(snapshot):
    # Build Week demo mode: keep the endpoint deterministic and API-key free for recordings.
    return demo_guardrail_review(snapshot)


LIVE_OVERLAY = r'''
<style>
.live-chip{display:inline-flex;align-items:center;gap:7px;Margin-top:8px;padding:5px 10px;border-radius:999px;background:rgba(95,204,167,.08);border:1px solid rgba(95,204,167,.16);color:var(--dim);font-size:12px;width:max-content;}
.live-dot{width:8px;height:8px;border-radius:50%;background:var(--dim);display:inline-block;}
.live-chip.is-live{color:#4ADE80;border-color:rgba(74,222,128,.28);}
.live-chip.is-live .live-dot{background:#4ADE80;box-shadow:0 0 0 0 rgba(74,222,128,.55);animation:livePulse 1s infinite;}
@keyframes livePulse{0%{box-shadow:0 0 0 0 rgba(74,222,128,.55)}70%{box-shadow:0 0 0 8px rgba(74,222,128,0)}100%{box-shadow:0 0 0 0 rgba(74,222,128,0)}}
</style>
<script>
(function(){
  const eur0 = v => Math.round(v).toLocaleString('sk-SK') + ' €';
  const eur1 = v => Number(v).toLocaleString('sk-SK', {minimumFractionDigits:1, maximumFractionDigits:1}) + ' €';
  const eur2 = v => Number(v).toLocaleString('sk-SK', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' €';
  const pct1 = v => (v >= 0 ? '+' : '') + Number(v).toFixed(1) + ' %';
  const signed0 = v => (v >= 0 ? '+' : '') + Math.round(v).toLocaleString('sk-SK') + ' €';
  const pnlColor = v => v >= 0 ? '#4ADE80' : '#df9270';
  const set = (id, value) => { const el = document.getElementById(id); if (el) el.textContent = value; };
  const color = (id, value) => { const el = document.getElementById(id); if (el) el.style.color = pnlColor(value); };

  const source = document.getElementById('live-price-source');
  if (source && !document.getElementById('live-chip')) {
    const chip = document.createElement('div');
    chip.id = 'live-chip';
    chip.className = 'live-chip';
    chip.innerHTML = '<span class="live-dot"></span><span id="live-chip-text">LIVE waiting for IB</span>';
    source.insertAdjacentElement('afterend', chip);
  }

  async function refreshLive(){
    try {
      const res = await fetch('/api/live-snapshot', {cache:'no-store'});
      const d = await res.json();
      set('live-spyy-price', eur1(d.spyy_price));
      set('live-lqq-price', eur1(d.lqq_price));
      set('live-spyy-price-detail', eur2(d.spyy_price));
      set('live-lqq-price-detail', eur2(d.lqq_price));
      set('live-net-liq', eur0(d.net_liq));
      set('live-invested', eur0(d.invested));
      set('live-total-pnl', signed0(d.total_pnl));
      set('live-total-pnl-pct', pct1(d.total_pnl_pct) + ' on invested capital');
      set('live-spyy-pnl', signed0(d.spyy_pnl));
      set('live-spyy-pnl-pct', pct1(d.spyy_pnl_pct));
      set('live-spyy-value', 'value ' + eur0(d.spyy_value));
      set('live-lqq-pnl', signed0(d.lqq_pnl));
      set('live-lqq-pnl-pct', pct1(d.lqq_pnl_pct));
      set('live-lqq-value', 'value ' + eur0(d.lqq_value));
      set('live-spyy-pct', Number(d.spyy_pct).toFixed(1) + ' %');
      set('live-lqq-pct', Number(d.lqq_pct).toFixed(1) + ' %');
      const spyyBar = document.getElementById('live-spyy-bar');
      const lqqBar = document.getElementById('live-lqq-bar');
      if (spyyBar) spyyBar.style.width = Number(d.spyy_pct).toFixed(1) + '%';
      if (lqqBar) lqqBar.style.width = Number(d.lqq_pct).toFixed(1) + '%';
      set('live-hardcap-pct', Number(d.lqq_pct).toFixed(1) + ' %');
      set('live-risk-hardcap-pct', Number(d.lqq_pct).toFixed(1) + ' %');
      const hardcapFill = document.getElementById('live-hardcap-fill');
      if (hardcapFill) hardcapFill.style.width = Math.min(100, Number(d.lqq_pct)).toFixed(1) + '%';
      const riskHardcapFill = document.getElementById('live-risk-hardcap-fill');
      if (riskHardcapFill) riskHardcapFill.style.width = Math.min(100, Number(d.lqq_pct)).toFixed(1) + '%';
      if (Array.isArray(d.limits)) {
        const firstLimit = d.limits[0];
        const alertBox = document.getElementById('live-limit-alert');
        if (firstLimit && alertBox) {
          alertBox.classList.remove('is-watch', 'is-hot');
          const absDist = Math.abs(Number(firstLimit.dist_pct));
          if (absDist < 5) {
            alertBox.classList.add('is-hot');
            set('live-limit-alert-main', 'TRIGGER ALERT · ' + eur2(firstLimit.price));
          } else if (absDist < 15) {
            alertBox.classList.add('is-watch');
            set('live-limit-alert-main', 'WATCH · ' + eur2(firstLimit.price));
          } else {
            set('live-limit-alert-main', '1st limit order ' + eur2(firstLimit.price));
          }
          set('live-limit-alert-sub', 'distance ' + (firstLimit.dist_pct >= 0 ? '+' : '') + Number(firstLimit.dist_pct).toFixed(1) + ' % from LQQ');
        }
        d.limits.forEach(lim => {
          set('live-limit-volume-' + lim.idx, eur0(lim.volume));
          const dist = document.getElementById('live-limit-dist-' + lim.idx);
          if (dist) {
            dist.style.color = lim.color;
            const barHtml = '<div class="dbar"><div id="live-limit-bar-' + lim.idx + '" class="dbar-f" style="width:' + Number(lim.bar_pct).toFixed(0) + '%"></div></div>';
            dist.innerHTML = (lim.dist_pct >= 0 ? '+' : '') + Number(lim.dist_pct).toFixed(1) + ' %' + barHtml;
          }
          set('live-limit-ma-' + lim.idx, lim.ma);
          const action = document.getElementById('live-limit-action-' + lim.idx);
          if (action) action.innerHTML = lim.action;
        });
      }
      const regimePreview = new URLSearchParams(window.location.search).has('regimePreview');
      const regimeBadge = document.getElementById('live-regime-badge');
      if (!regimePreview) {
        set('live-regime-text', d.Market_regime || 'UNKNOWN');
        if (regimeBadge) {
          regimeBadge.classList.remove('is-bull', 'is-bear', 'is-neutral');
          if (d.Market_regime === 'BULL') regimeBadge.classList.add('is-bull');
          else if (d.Market_regime === 'BEAR') regimeBadge.classList.add('is-bear');
          else if (d.Market_regime === 'NEUTRAL') regimeBadge.classList.add('is-neutral');
        }
      }
      ['live-total-pnl','live-total-pnl-pct'].forEach(id => color(id, d.total_pnl));
      ['live-spyy-pnl','live-spyy-pnl-pct'].forEach(id => color(id, d.spyy_pnl));
      ['live-lqq-pnl','live-lqq-pnl-pct'].forEach(id => color(id, d.lqq_pnl));

      const src = document.getElementById('live-price-source');
      if (src) {
        src.style.display = 'none';
      }
      const chip = document.getElementById('live-chip');
      const chipText = document.getElementById('live-chip-text');
      if (chip && chipText) {
        chip.classList.toggle('is-live', !!d.live);
        chipText.textContent = d.status + ' · ' + d.updated_at;
      }
    } catch (e) {
      const chip = document.getElementById('live-chip');
      const chipText = document.getElementById('live-chip-text');
      if (chip) chip.classList.remove('is-live');
      if (chipText) chipText.textContent = 'live server offline';
    }
  }
  refreshLive();
  setInterval(refreshLive, 1000);
})();
</script>
'''


class Handler(BaseHTTPRequestHandler):
    def send_body(self, body, content_type='text/html; charset=utf-8', status=200):
        data = body.encode('utf-8') if isinstance(body, str) else body
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/live-snapshot':
            self.send_body(json.dumps(LIVE.get(), ensure_ascii=False), 'application/json; charset=utf-8')
            return
        if path.startswith('/assets/'):
            asset = (ROOT / path.lstrip('/')).resolve()
            try:
                asset.relative_to(ROOT / 'assets')
            except ValueError:
                self.send_body('Not found', 'text/plain; charset=utf-8', 404)
                return
            if asset.exists() and asset.is_file():
                content_type = mimetypes.guess_type(str(asset))[0] or 'application/octet-stream'
                self.send_body(asset.read_bytes(), content_type)
                return
            self.send_body('Not found', 'text/plain; charset=utf-8', 404)
            return
        if path in ('/', '/livka_dashboard.html'):
            html = HTML_FILE.read_text(encoding='utf-8')
            html = html.replace('</body>', LIVE_OVERLAY + '\\n</body>')
            self.send_body(html)
            return
        self.send_body('Not found', 'text/plain; charset=utf-8', 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == '/api/ai-review':
            review = guardrail_review(LIVE.get())
            self.send_body(json.dumps(review, ensure_ascii=False), 'application/json; charset=utf-8')
            return
        self.send_body('Not found', 'text/plain; charset=utf-8', 404)

    def log_message(self, fmt, *args):
        return


def main():
    if not HTML_FILE.exists():
        raise SystemExit(f'Missing {HTML_FILE}. Run livka_dashboard_refactor_codex.py first.')
    LIVE.start()
    url = f'http://{HOST}:{PORT}/'
    print('=' * 50)
    print('Livka Dashboard LIVE experiment')
    print('=' * 50)
    print(f'URL: {url}')
    print('Static up ostatusa nezmeneny. Ctrl+C zastatusi live server.')
    try:
        webbrowser.open(url)
    except Exception:
        pass
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == '__main__':
    main()
