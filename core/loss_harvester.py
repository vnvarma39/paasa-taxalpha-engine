import os
import json

class TaxLossHarvester:
    """
    Algorithmic Pre-March 31 Tax-Loss Harvester & Wash-Sale Avoidance Engine.
    Scans open positions for unrealized losses and pairs them with highly correlated
    ETF substitutes to keep portfolio exposure constant while capturing Indian tax alpha.
    """

    SUBSTITUTE_PRICES = {
        "IVV": 516.80,
        "SPY": 514.90,
        "SPLG": 62.40,
        "QQQM": 196.40,
        "VGT": 545.00,
        "XLK": 215.00,
        "SMH": 242.00,
        "SOXX": 218.00,
        "ARKK": 48.20,
        "CARZ": 52.10,
        "META": 585.00,
        "XLC": 88.50,
        "MSFT": 412.00,
        "NVDA": 126.50,
    }

    def __init__(self, substitutes_file=None):
        if substitutes_file is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            substitutes_file = os.path.join(base_dir, "data", "etf_substitutes.json")

        self.substitutes = self._load_substitutes(substitutes_file)

    def _load_substitutes(self, filepath):
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def analyze_harvest_opportunities(self, open_positions, realized_summary=None, tax_slab_pct=30.0):
        """
        Analyzes open positions to find loss-harvesting opportunities.
        """
        harvest_candidates = []
        total_harvestable_loss_usd = 0.0
        total_harvestable_loss_inr = 0.0
        total_potential_tax_saved_inr = 0.0

        for pos in open_positions:
            unrealized_inr = pos["unrealized_pnl_inr"]
            if unrealized_inr >= 0:
                continue  # Only losing positions

            loss_usd = abs(pos["unrealized_pnl_usd"])
            loss_inr = abs(unrealized_inr)
            symbol = pos["symbol"]
            term = pos["term"]  # STCG or LTCG (holding <= 24m is STCL, > 24m is LTCL)

            # Determine tax offset rate
            # Short-Term Capital Loss (STCL) can offset STCG (at slab rate 30%)
            # Long-Term Capital Loss (LTCL) offsets LTCG (at 12.5%)
            offset_tax_rate = tax_slab_pct if term == "STCG" else 12.5
            potential_tax_saved = round(loss_inr * (offset_tax_rate / 100.0), 2)

            # Get substitutes
            sub_info = self.substitutes.get(symbol, {})
            recommended_subs = sub_info.get("substitutes", [])
            primary_sub = recommended_subs[0] if recommended_subs else None

            # Calculate swap details
            swap_details = None
            if primary_sub:
                sub_sym = primary_sub["symbol"]
                sub_price = self.SUBSTITUTE_PRICES.get(sub_sym, 100.0)
                sub_qty = round((pos["quantity"] * pos["current_price_usd"]) / sub_price, 2)
                swap_details = {
                    "primary_substitute": sub_sym,
                    "substitute_name": primary_sub["name"],
                    "correlation": primary_sub["correlation"],
                    "expense_ratio": primary_sub.get("expense_ratio", "N/A"),
                    "rationale": primary_sub["rationale"],
                    "est_substitute_price": sub_price,
                    "est_substitute_quantity": sub_qty,
                    "all_substitutes": recommended_subs
                }
            else:
                # Default generic sector substitute
                swap_details = {
                    "primary_substitute": "SPY" if pos["asset_type"] == "ETF" else "SMH",
                    "substitute_name": "Broad Market ETF",
                    "correlation": 0.85,
                    "expense_ratio": "0.09%",
                    "rationale": "Maintains broad market exposure while resetting cost basis.",
                    "est_substitute_price": 514.90,
                    "est_substitute_quantity": round((pos["quantity"] * pos["current_price_usd"]) / 514.90, 2),
                    "all_substitutes": []
                }

            candidate = {
                "lot_id": pos["lot_id"],
                "symbol": symbol,
                "asset_type": pos["asset_type"],
                "buy_date": pos["buy_date"],
                "quantity": pos["quantity"],
                "buy_price_usd": pos["buy_price_usd"],
                "current_price_usd": pos["current_price_usd"],
                "loss_usd": round(loss_usd, 2),
                "loss_inr": round(loss_inr, 2),
                "loss_pct": abs(pos["unrealized_pnl_pct"]),
                "term": term,
                "loss_type": "Short-Term Capital Loss (STCL)" if term == "STCG" else "Long-Term Capital Loss (LTCL)",
                "applicable_tax_rate": offset_tax_rate,
                "potential_tax_saved_inr": potential_tax_saved,
                "swap": swap_details,
                "action_recommendation": f"SELL {pos['quantity']} {symbol} @ ~${pos['current_price_usd']} & SWAP -> {swap_details['primary_substitute']}",
                "selected_by_default": True
            }

            harvest_candidates.append(candidate)
            total_harvestable_loss_usd += loss_usd
            total_harvestable_loss_inr += loss_inr
            total_potential_tax_saved_inr += potential_tax_saved

        # Sort candidates by biggest tax saving descending
        harvest_candidates.sort(key=lambda x: x["potential_tax_saved_inr"], reverse=True)

        return {
            "candidates": harvest_candidates,
            "total_candidates": len(harvest_candidates),
            "total_harvestable_loss_usd": round(total_harvestable_loss_usd, 2),
            "total_harvestable_loss_inr": round(total_harvestable_loss_inr, 2),
            "total_potential_tax_saved_inr": round(total_potential_tax_saved_inr, 2),
            "deadline_date": "March 31, 2026",
            "statutory_reference": "Section 70 of Indian Income Tax Act (Inter-source Set Off of Losses)"
        }

LossHarvester = TaxLossHarvester

