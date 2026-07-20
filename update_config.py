#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from datetime import datetime

from ib_insync import *


CONFIG_FILE = "config.json"


def main():

    print("=" * 50)
    print("IBKR CONFIG REFRESH")
    print("=" * 50)

    ib = IB()

    print("\nConnecting to IB Gateway...")

    # -------------------------------------------------
    # SAFE CONNECT
    # -------------------------------------------------

    try:

        ib.connect(
            "127.0.0.1",
            4002,
            clientId=77,
            timeout=10
        )

    except Exception as e:

        print("\nERROR:")
        print("Nepodarilo sa pripojit na IB Gateway.")
        print("")
        print("Skontroluj:")
        print("- je spusteny IB Gateway")
        print("- si prihlasena")
        print("- API je povolene")
        print("- port 4002 je spravny")
        print("")
        print("Ak nie si prihlasena:")
        print("-> priprav si user + heslo")
        print("-> prihlas sa do IB Gateway")
        print("-> potom spusti script znovu")
        print("")
        print(f"DETAIL: {e}")

        sys.exit(1)

    if not ib.isConnected():

        print("\nERROR:")
        print("IB Gateway nie je connected.")
        print("Prihlas sa a skus znova.")

        sys.exit(1)

    print("CONNECTED OK")

    # nechame Gateway zosynchronizovat data
    ib.sleep(2)

    # -------------------------------------------------
    # ACCOUNTS
    # -------------------------------------------------

    print("\nAccounts:")

    accounts = ib.managedAccounts()

    print(accounts)

    account_id = accounts[0]

    print(f"\nUsing account: {account_id}")

    # -------------------------------------------------
    # POSITIONS
    # -------------------------------------------------

    positions = ib.positions()

    spyy = None
    lqq = None

    for p in positions:

        if p.contract.symbol == "SPYY":
            spyy = p

        elif p.contract.symbol == "LQQ":
            lqq = p

    if not spyy or not lqq:

        raise Exception(
            "SPYY or LQQ were not found."
        )

    print("\nPOSITIONS:")

    print(
        f"SPYY: "
        f"{spyy.position} "
        f"@ {spyy.avgCost}"
    )

    print(
        f"LQQ: "
        f"{lqq.position} "
        f"@ {lqq.avgCost}"
    )

    # -------------------------------------------------
    # IBKR LIVE MARKET DATA
    # -------------------------------------------------

    print("\nFetching LIVE prices from IBKR...")

    spyy_price = None
    lqq_price = None

    try:

        # SPYY -> contract z positions()
        spyy_contract = spyy.contract

        # LQQ -> manual IBIS contract
        lqq_contract = Stock(
            symbol='LQQ',
            exchange='IBIS',
            currency='EUR'
        )

        ib.qualifyContracts(
            lqq_contract
        )

        ib.reqMarketDataType(1)

        spyy_ticker = ib.reqMktData(
            spyy_contract
        )

        lqq_ticker = ib.reqMktData(
            lqq_contract
        )

        print("Waiting for market data...")

        ib.sleep(5)

        spyy_price = spyy_ticker.marketPrice()
        lqq_price = lqq_ticker.marketPrice()

        # fallback last()

        if (
            spyy_price != spyy_price
            or spyy_price is None
        ):
            spyy_price = spyy_ticker.last

        if (
            lqq_price != lqq_price
            or lqq_price is None
        ):
            lqq_price = lqq_ticker.last

        print(f"SPYY LIVE price: {spyy_price}")
        print(f"LQQ LIVE price: {lqq_price}")

        # cleanup

        ib.cancelMktData(
            spyy_contract
        )

        ib.cancelMktData(
            lqq_contract
        )

    except Exception as e:

        print(f"\nLIVE market data failed: {e}")

    # -------------------------------------------------
    # FETCH LIMIT ORDERS
    # -------------------------------------------------

    print("\nFetching open orders from IBKR...")

    ib.reqAllOpenOrders()

    ib.sleep(1)

    ibkr_limits = []

    open_trades = ib.openTrades()

    for o in ib.openOrders():

        if (
            o.account == account_id
            and o.orderType == "LMT"
            and o.action == "BUY"
        ):

            for t in open_trades:

                if (
                    t.order.orderId == o.orderId
                    and t.contract.symbol in [
                        "LQQ",
                        "SPYY"
                    ]
                ):

                    ibkr_limits.append({

                        "price": round(
                            float(o.lmtPrice),
                            2
                        ),

                        "qty": int(
                            o.totalQuantity
                        )
                    })

    # remove duplicates

    unique_limits = []

    for item in ibkr_limits:

        if item not in unique_limits:
            unique_limits.append(item)

    ibkr_limits = sorted(
        unique_limits,
        key=lambda x: x["price"],
        reverse=True
    )

    print(
        f"Found limit orders in IBKR: "
        f"{ibkr_limits}"
    )

    # -------------------------------------------------
    # ACCOUNT SUMMARY
    # -------------------------------------------------

    cash = None

    print("\nFetching account summary...")

    summary = ib.accountSummary()

    for row in summary:

        if (
            row.tag in [
                "TotalCashBalance",
                "TotalCashValue"
            ]
            and row.currency in [
                "EUR",
                "BASE"
            ]
        ):

            try:

                value = float(row.value)

                if value > 0:
                    cash = value

            except:
                pass

    # fallback

    if cash is None:

        for v in ib.accountValues(account_id):

            if (
                v.tag == "TotalCashBalance"
                and v.currency == "EUR"
            ):

                try:

                    value = float(v.value)

                    if value > 0:
                        cash = value

                except:
                    pass

    print(f"Cash: {cash}")

    # -------------------------------------------------
    # LOAD CONFIG
    # -------------------------------------------------

    config_path = (
        Path(__file__).resolve().parent
        / CONFIG_FILE
    )

    print(f"\nSaving to: {config_path}")

    with open(
        config_path,
        encoding="utf-8"
    ) as f:

        cfg = json.load(f)

    pf = cfg["portfolio"]

    # -------------------------------------------------
    # UPDATE CONFIG
    # -------------------------------------------------

    pf["SPYY_SHARES"] = round(
        float(spyy.position),
        4
    )

    pf["SPYY_AVG_COST"] = round(
        float(spyy.avgCost),
        6
    )

    pf["LQQ_SHARES"] = round(
        float(lqq.position),
        4
    )

    pf["LQQ_AVG_COST"] = round(
        float(lqq.avgCost),
        6
    )

    # -------------------------------------------------
    # MARKET PRICES
    # -------------------------------------------------

    if spyy_price is not None:

        pf["SPYY_LAST_PRICE"] = round(
            float(spyy_price),
            2
        )

    if lqq_price is not None:

        pf["LQQ_LAST_PRICE"] = round(
            float(lqq_price),
            2
        )

    # -------------------------------------------------
    # CASH
    # -------------------------------------------------

    if cash is not None:

        pf["CASH"] = round(
            cash,
            2
        )

    # -------------------------------------------------
    # UPDATE LIMITS
    # -------------------------------------------------

    if ibkr_limits:

        cfg["limits"] = ibkr_limits

        print(
            " -> Sekcia 'limits' "
            "overwritten with IBKR data."
        )

    else:

        print(
            " -> Nothing was found in IBKR. "
            "Leaving the 'limits' section unchanged."
        )

    # -------------------------------------------------
    # RESTORE DEFAULT LIMITS
    # -------------------------------------------------

    if (
        "limits" not in cfg
        or not cfg["limits"]
    ):

        print(
            "\nLimits boli prazdne - "
            "obnovujem default limitky."
        )

        cfg["limits"] = [

            {
                "price": 11,
                "qty": 2
            },

            {
                "price": 10,
                "qty": 2
            },

            {
                "price": 9,
                "qty": 3
            },

            {
                "price": 8,
                "qty": 3
            },

            {
                "price": 7,
                "qty": 3
            }
        ]

    # -------------------------------------------------
    # NET LIQ CALCULATION
    # -------------------------------------------------

    current_spyy_price = (
        spyy_price
        if spyy_price is not None
        else pf["SPYY_LAST_PRICE"]
    )

    current_lqq_price = (
        lqq_price
        if lqq_price is not None
        else pf["LQQ_LAST_PRICE"]
    )

    calculated_netliq = (

        float(pf["CASH"])

        + (
            float(spyy.position)
            * current_spyy_price
        )

        + (
            float(lqq.position)
            * current_lqq_price
        )
    )

    pf["NET_LIQ_IB"] = round(
        calculated_netliq,
        2
    )

    print(
        f"Calculated NetLiq: "
        f"{pf['NET_LIQ_IB']}"
    )

    # -------------------------------------------------
    # TIMESTAMP
    # -------------------------------------------------

    pf["last_updated"] = (
        datetime.now()
        .strftime("%Y-%m-%d %H:%M")
    )

    # -------------------------------------------------
    # SAVE
    # -------------------------------------------------

    with open(
        config_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            cfg,
            f,
            indent=2,
            ensure_ascii=False
        )

    ib.disconnect()

    print("\nCONFIG UPDATED OK")


if __name__ == "__main__":
    main()