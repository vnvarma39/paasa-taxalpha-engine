import copy
from datetime import datetime, date
from .currency import Rule115CurrencyConverter

class TaxEngine:
    """
    Dual-Calendar Realized Gain & FIFO Lot Engine for Indian Residents holding US Equities.
    - Post-Budget 2024 Rules (LTCG > 24 months @ 12.5%, STCG <= 24 months @ Slab).
    - Rule 115 SBI TT Buying Rate conversion.
    - Slices gains by Indian FY (Apr 1 - Mar 31) vs US CY (Jan 1 - Dec 31).
    """

    CURRENT_MARKET_PRICES = {
        "VOO": 515.20,
        "QQQ": 478.50,
        "QQQM": 196.40,
        "IVV": 516.80,
        "SPY": 514.90,
        "NVDA": 126.50,
        "AAPL": 228.40,
        "MSFT": 412.00,
        "AMD": 118.25,
        "TSLA": 210.50,
        "GOOGL": 182.10,
        "SMH": 242.00,
        "VGT": 545.00,
        "XLK": 215.00,
        "ARKK": 48.20,
    }

    def __init__(self, currency_converter=None):
        self.fx = currency_converter or Rule115CurrencyConverter()

    @staticmethod
    def get_indian_fy(date_str):
        """
        Returns Indian Financial Year string, e.g. 'FY 2024-25' for 2024-05-18.
        April 1 of Year N to March 31 of Year N+1.
        """
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        year = dt.year
        if dt.month >= 4:
            return f"FY {year}-{str(year + 1)[-2:]}"
        else:
            return f"FY {year - 1}-{str(year)[-2:]}"

    @staticmethod
    def get_us_cy(date_str):
        """
        Returns US Calendar Year string, e.g. 'CY 2024' for 2024-05-18.
        """
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        return f"CY {dt.year}"

    @staticmethod
    def is_post_budget_2024(date_str):
        """
        Budget 2024 changes took effect on July 23, 2024.
        """
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        return dt >= date(2024, 7, 23)

    def calculate(self, trades, tax_slab_pct=30.0, current_date="2026-03-25"):
        """
        Runs FIFO lot matching, calculates realized gains, dividends, open positions,
        and currency alpha decomposition.
        """
        # Separate trades
        buy_lots = {}  # symbol -> list of lots
        realized_trades = []
        dividends = []

        for trade in trades:
            action = trade["action"]
            symbol = trade["symbol"]

            if action == "BUY":
                if symbol not in buy_lots:
                    buy_lots[symbol] = []
                buy_fx = self.fx.get_rule_115_rate(trade["date"])
                buy_lots[symbol].append({
                    "trade_id": f"BUY-{trade['date']}-{symbol}-{len(buy_lots[symbol])+1}",
                    "date": trade["date"],
                    "symbol": symbol,
                    "asset_type": trade["asset_type"],
                    "total_quantity": trade["quantity"],
                    "remaining_quantity": trade["quantity"],
                    "price_usd": trade["price_usd"],
                    "fees_usd": trade["fees_usd"],
                    "buy_fx": buy_fx,
                    "cost_basis_usd": trade["quantity"] * trade["price_usd"] + trade["fees_usd"],
                    "cost_basis_inr": (trade["quantity"] * trade["price_usd"] + trade["fees_usd"]) * buy_fx,
                    "notes": trade.get("notes", "")
                })

            elif action == "SELL":
                sell_qty_needed = trade["quantity"]
                sell_price_usd = trade["price_usd"]
                sell_fees_usd = trade["fees_usd"]
                sell_date = trade["date"]
                sell_fx = self.fx.get_rule_115_rate(sell_date)

                if symbol not in buy_lots or not buy_lots[symbol]:
                    # Unmatched sell (or short/vested prior)
                    continue

                for lot in buy_lots[symbol]:
                    if sell_qty_needed <= 0:
                        break
                    if lot["remaining_quantity"] <= 0:
                        continue

                    matched_qty = min(lot["remaining_quantity"], sell_qty_needed)
                    lot["remaining_quantity"] -= matched_qty
                    sell_qty_needed -= matched_qty

                    # Fraction of fees
                    matched_buy_fees = (matched_qty / lot["total_quantity"]) * lot["fees_usd"] if lot["total_quantity"] > 0 else 0
                    matched_sell_fees = (matched_qty / trade["quantity"]) * sell_fees_usd if trade["quantity"] > 0 else 0

                    buy_cost_usd = (matched_qty * lot["price_usd"]) + matched_buy_fees
                    sell_proceeds_usd = (matched_qty * sell_price_usd) - matched_sell_fees

                    buy_cost_inr = buy_cost_usd * lot["buy_fx"]
                    sell_proceeds_inr = sell_proceeds_usd * sell_fx

                    realized_gain_usd = sell_proceeds_usd - buy_cost_usd
                    realized_gain_inr = sell_proceeds_inr - buy_cost_inr

                    # Holding period
                    dt_buy = datetime.strptime(lot["date"], "%Y-%m-%d").date()
                    dt_sell = datetime.strptime(sell_date, "%Y-%m-%d").date()
                    holding_days = (dt_sell - dt_buy).days
                    holding_months = round(holding_days / 30.4375, 1)

                    # LTCG vs STCG classification
                    post_budget = self.is_post_budget_2024(sell_date)
                    threshold_months = 24.0 if post_budget else 36.0
                    is_ltcg = holding_months > threshold_months

                    tax_rate_pct = 12.5 if is_ltcg else tax_slab_pct
                    estimated_tax_inr = max(0.0, realized_gain_inr * (tax_rate_pct / 100.0))

                    # Decompose return into Asset vs FX Drift
                    decomp = self.fx.decompose_return(
                        lot["price_usd"] * matched_qty,
                        sell_price_usd * matched_qty,
                        lot["date"],
                        sell_date
                    )

                    realized_trades.append({
                        "symbol": symbol,
                        "asset_type": trade["asset_type"],
                        "quantity": round(matched_qty, 4),
                        "buy_date": lot["date"],
                        "sell_date": sell_date,
                        "holding_days": holding_days,
                        "holding_months": holding_months,
                        "term": "LTCG" if is_ltcg else "STCG",
                        "buy_price_usd": lot["price_usd"],
                        "sell_price_usd": sell_price_usd,
                        "buy_fx_rate": lot["buy_fx"],
                        "sell_fx_rate": sell_fx,
                        "buy_cost_usd": round(buy_cost_usd, 2),
                        "sell_proceeds_usd": round(sell_proceeds_usd, 2),
                        "gain_usd": round(realized_gain_usd, 2),
                        "buy_cost_inr": round(buy_cost_inr, 2),
                        "sell_proceeds_inr": round(sell_proceeds_inr, 2),
                        "gain_inr": round(realized_gain_inr, 2),
                        "tax_rate_pct": tax_rate_pct,
                        "estimated_tax_inr": round(estimated_tax_inr, 2),
                        "indian_fy": self.get_indian_fy(sell_date),
                        "us_cy": self.get_us_cy(sell_date),
                        "asset_gain_usd": decomp["asset_gain_usd"],
                        "fx_gain_inr": decomp["fx_gain_inr"],
                        "notes": trade.get("notes", "")
                    })

            elif action == "DIVIDEND":
                div_fx = self.fx.get_rule_115_rate(trade["date"])
                gross_div_usd = trade["quantity"] * trade["price_usd"]
                withholding_usd = trade["withholding_tax_usd"]
                net_div_usd = gross_div_usd - withholding_usd

                gross_div_inr = round(gross_div_usd * div_fx, 2)
                withholding_inr = round(withholding_usd * div_fx, 2)
                net_div_inr = round(net_div_usd * div_fx, 2)

                # DTAA Sec 90 allows credit up to Indian tax or US WHT
                indian_tax_on_div = round(gross_div_inr * (tax_slab_pct / 100.0), 2)
                ftc_eligible_inr = min(withholding_inr, indian_tax_on_div)
                net_tax_payable_inr = max(0.0, indian_tax_on_div - ftc_eligible_inr)

                dividends.append({
                    "date": trade["date"],
                    "symbol": symbol,
                    "asset_type": trade["asset_type"],
                    "quantity": trade["quantity"],
                    "per_share_usd": trade["price_usd"],
                    "gross_div_usd": round(gross_div_usd, 2),
                    "withholding_usd": round(withholding_usd, 2),
                    "net_div_usd": round(net_div_usd, 2),
                    "fx_rate": div_fx,
                    "gross_div_inr": gross_div_inr,
                    "withholding_inr": withholding_inr,
                    "net_div_inr": net_div_inr,
                    "ftc_eligible_inr": ftc_eligible_inr,
                    "indian_tax_inr": indian_tax_on_div,
                    "net_tax_payable_inr": net_tax_payable_inr,
                    "indian_fy": self.get_indian_fy(trade["date"]),
                    "us_cy": self.get_us_cy(trade["date"]),
                })

        # Calculate Open Positions
        open_positions = []
        current_fx = self.fx.get_rule_115_rate(current_date)
        dt_current = datetime.strptime(current_date[:10], "%Y-%m-%d").date()

        for symbol, lots in buy_lots.items():
            for lot in lots:
                rem_qty = lot["remaining_quantity"]
                if rem_qty <= 0:
                    continue

                curr_price_usd = self.CURRENT_MARKET_PRICES.get(symbol, lot["price_usd"] * 1.05)
                mkt_val_usd = rem_qty * curr_price_usd
                mkt_val_inr = mkt_val_usd * current_fx

                cost_basis_usd = rem_qty * lot["price_usd"]
                cost_basis_inr = cost_basis_usd * lot["buy_fx"]

                unrealized_pnl_usd = mkt_val_usd - cost_basis_usd
                unrealized_pnl_inr = mkt_val_inr - cost_basis_inr
                unrealized_pnl_pct = ((curr_price_usd / lot["price_usd"]) - 1.0) * 100.0 if lot["price_usd"] > 0 else 0.0

                dt_buy = datetime.strptime(lot["date"], "%Y-%m-%d").date()
                holding_days = (dt_current - dt_buy).days
                holding_months = round(holding_days / 30.4375, 1)
                is_ltcg = holding_months > 24.0

                decomp = self.fx.decompose_return(cost_basis_usd, mkt_val_usd, lot["date"], current_date)

                open_positions.append({
                    "lot_id": lot["trade_id"],
                    "symbol": symbol,
                    "asset_type": lot["asset_type"],
                    "buy_date": lot["date"],
                    "quantity": round(rem_qty, 4),
                    "buy_price_usd": lot["price_usd"],
                    "current_price_usd": round(curr_price_usd, 2),
                    "buy_fx_rate": lot["buy_fx"],
                    "current_fx_rate": current_fx,
                    "cost_basis_usd": round(cost_basis_usd, 2),
                    "current_val_usd": round(mkt_val_usd, 2),
                    "cost_basis_inr": round(cost_basis_inr, 2),
                    "current_val_inr": round(mkt_val_inr, 2),
                    "unrealized_pnl_usd": round(unrealized_pnl_usd, 2),
                    "unrealized_pnl_inr": round(unrealized_pnl_inr, 2),
                    "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
                    "holding_days": holding_days,
                    "holding_months": holding_months,
                    "term": "LTCG" if is_ltcg else "STCG",
                    "asset_growth_usd": decomp["asset_gain_usd"],
                    "fx_drift_inr": decomp["fx_gain_inr"],
                    "is_loss": unrealized_pnl_inr < 0,
                    "notes": lot.get("notes", "")
                })

        # Summarize by Indian FY
        fy_summary = {}
        for r in realized_trades:
            fy = r["indian_fy"]
            if fy not in fy_summary:
                fy_summary[fy] = {
                    "stcg_gain_inr": 0.0,
                    "ltcg_gain_inr": 0.0,
                    "total_gain_inr": 0.0,
                    "stcg_tax_inr": 0.0,
                    "ltcg_tax_inr": 0.0,
                    "total_tax_inr": 0.0,
                    "gain_usd": 0.0,
                    "trades_count": 0
                }
            if r["term"] == "STCG":
                fy_summary[fy]["stcg_gain_inr"] += r["gain_inr"]
                fy_summary[fy]["stcg_tax_inr"] += r["estimated_tax_inr"]
            else:
                fy_summary[fy]["ltcg_gain_inr"] += r["gain_inr"]
                fy_summary[fy]["ltcg_tax_inr"] += r["estimated_tax_inr"]

            fy_summary[fy]["total_gain_inr"] += r["gain_inr"]
            fy_summary[fy]["total_tax_inr"] += r["estimated_tax_inr"]
            fy_summary[fy]["gain_usd"] += r["gain_usd"]
            fy_summary[fy]["trades_count"] += 1

        # Round FY summaries
        for fy in fy_summary:
            for k in fy_summary[fy]:
                if isinstance(fy_summary[fy][k], float):
                    fy_summary[fy][k] = round(fy_summary[fy][k], 2)

        # Totals across all open positions
        total_open_usd = sum(p["current_val_usd"] for p in open_positions)
        total_open_inr = sum(p["current_val_inr"] for p in open_positions)
        total_unrealized_pnl_usd = sum(p["unrealized_pnl_usd"] for p in open_positions)
        total_unrealized_pnl_inr = sum(p["unrealized_pnl_inr"] for p in open_positions)

        return {
            "realized_trades": realized_trades,
            "dividends": dividends,
            "open_positions": open_positions,
            "fy_summary": fy_summary,
            "portfolio_totals": {
                "current_val_usd": round(total_open_usd, 2),
                "current_val_inr": round(total_open_inr, 2),
                "unrealized_pnl_usd": round(total_unrealized_pnl_usd, 2),
                "unrealized_pnl_inr": round(total_unrealized_pnl_inr, 2),
                "open_lots_count": len(open_positions),
                "current_fx_rate": current_fx
            }
        }
