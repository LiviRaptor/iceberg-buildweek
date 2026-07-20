# Iceberg

Iceberg is a live portfolio guardrail dashboard for a long-term ETF investing plan. It turns a personal investment plan into a calm, visual cockpit: current portfolio value, cash buffer, LQQ exposure, limit-order readiness, market-regime status, and a Guardrail Review.

It is not an investment advisor and does not place trades. It is a personal decision-support dashboard that checks whether the current portfolio state is consistent with predefined risk rules.

## Why It Exists

Long-term investing is simple in theory and hard in practice. The difficult moments are not spreadsheet moments; they are panic moments. Iceberg is designed for those moments: it keeps the plan visible, highlights risk concentration, tracks cash and limit orders, and provides a concise guardrail review before emotional decisions take over.

## What Was Built During OpenAI Build Week

Iceberg started before Build Week as a private static HTML portfolio snapshot generated from one large script. It worked as a personal dashboard, but it was not modular, not public-demo ready, and not easy to evolve.

During Build Week, the project was refactored and productized with Codex as an iterative engineering partner:

- split one large script into core logic, templates, static assets, and a local live server
- transformed a static HTML portfolio snapshot into an IBKR-connected live dashboard with live-updating pricing, exposure monitoring, and guardrail checks
- added browser-side live metric updates
- added a public demo configuration with synthetic/sample portfolio values
- separated private configuration from the public submission
- translated the UI into English
- added a market-regime visual layer
- added the Guardrail Review panel
- cleaned the repository for public submission

A key part of the work was preserving the original visual identity while making the dashboard maintainable. Earlier AI-assisted refactoring attempts had repeatedly broken the layout; this Build Week iteration succeeded in separating the application structure without losing the design.

## Main Features

- IBKR-connected live dashboard served locally.
- Demo portfolio configuration via `config.demo.json`
- Optional private Interactive Brokers refresh flow via `update_config.py`
- Portfolio value with and without cash
- Position-level P&L for SPYY and LQQ
- LQQ hard-cap monitor
- Limit-order trigger monitor
- Retirement/time-horizon countdown
- Scenario checkpoints for future risk windows
- Market-regime indicator
- Guardrail Review in deterministic demo mode

## Guardrail Review

The Guardrail Review checks whether the current portfolio plan is internally consistent with predefined risk rules. It focuses on:

- LQQ exposure
- cash reserve visibility
- distance from the first limit order
- leverage drift
- known future risk windows

For the Build Week demo, the review runs in deterministic guardrail demo mode. This makes the demo safe and reliable without exposing API keys, brokerage credentials, or relying on external API quota. The component is designed to support a future GPT-based reasoning layer. It is not investment advice.

## How To Run

From the project directory:

```bash
./start_iceberg_live.sh
```

Then open:

```text
http://127.0.0.1:8765/
```

Optional market-regime preview:

```text
http://127.0.0.1:8765/?regimePreview=1
```

## Demo Data

The public submission uses `config.demo.json`. It contains sample values only and is intended for demonstration.

Private files are ignored by git:

- `config.json`
- `private_not_for_github/`
- generated `livka_dashboard.html`
- runtime caches

## Project Structure

```text
start_iceberg_live.sh            # starts the live demo
livka_dashboard_refactor_codex.py # dashboard generator
livka_dashboard_core.py           # shared calculations and data loading
live_dashboard_server.py          # local live server and JSON endpoints
update_config.py                  # optional private IBKR refresh helper
config.demo.json                  # public demo config
templates_codex/                  # HTML section templates
static_codex/                     # CSS and browser-side JS
assets/                           # visual assets
functional_files.txt              # detailed file inventory
```

## Privacy And Safety

Iceberg does not include private brokerage credentials or API keys. The repository is intended to be published with `config.demo.json` only.

The dashboard is not financial advice. It does not recommend buying, selling, or holding any security. It displays predefined personal risk rules and checks consistency against them.

## Image And Likeness Notice

The portraits shown in the dashboard are AI-generated or AI-transformed illustrative depictions of public figures and appear alongside attributed quotations. They are not official photographs, and no endorsement, sponsorship, or affiliation is implied.

Run the public-submission safety check with:

```bash
python3 submission_audit.py
```

## How Codex And GPT-5.6 Were Used

The product concept, investment rules, calculations, visual direction, and safety boundaries were defined by Livia. Codex was used as an iterative engineering partner during Build Week to modularize the original monolithic script, connect the live dashboard flow to IBKR data, preserve the existing visual design, separate public demo data from private configuration, and prepare the repository for submission.

GPT-5.6 in Codex was used for the final Build Week audit. That work included reviewing privacy and demo-mode separation, correcting Guardrail Review naming so the public demo does not imply a live model call, adding an automated submission-safety check, and tightening the README claims. The public Guardrail Review remains deterministic; GPT-5.6 was used in the development and audit process rather than being presented as an embedded investment advisor.

## Built With

- Python
- HTML/CSS/JavaScript
- Local Python HTTP server
- Optional yfinance / pandas support for history data
- Optional ib_insync support for private Interactive Brokers integration
- Codex-assisted refactoring and productization during OpenAI Build Week
- GPT-5.5 for the main Codex-assisted implementation work
- GPT-5.6 final privacy, safety, and submission audit

## Author

Livia Petrickova — Senior Data Engineer  
LinkedIn: https://sk.linkedin.com/in/liviapetrickova
