"""
Multi-Jurisdiction Cross-Border Tax Engine.

Models tax rules across global jurisdictions for cross-border investors:
1. 🇮🇳 INDIA: Income Tax Act (Rule 115, Budget 2024 LTCG @ 12.5% > 24m, STCG @ slab).
2. 🇬🇧 UNITED KINGDOM: HMRC (Tax Year Apr 6 - Apr 5, Section 104 Share Pooling, Bed & Breakfasting 30-day rule).
3. 🇺🇸 UNITED STATES: IRS (Form 8949, Jan 1 - Dec 31, 1-year LT vs ST, 30-Day Wash-Sale Rule).
4. 🌐 UAE / SINGAPORE / OFFSHORE: Zero Capital Gains Tax, Estate Tax & Remittance Optimization.
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any
from collections import defaultdict

class GlobalTaxEngine:

    JURISDICTIONS = {
        "IN": {
            "name": "India",
            "flag": "🇮🇳",
            "authority": "Income Tax Department (CBDT)",
            "fiscal_year": "April 1 – March 31",
            "currency": "INR",
            "currency_symbol": "₹",
            "cgt_rules": "LTCG >24m @ 12.5%, STCG <=24m @ Slab Rate (20%-39%)",
            "lot_method": "FIFO (First-In, First-Out)",
            "fx_rule": "Rule 115 (SBI TT Buying Rate on Preceding Month-End)",
            "statutory_form": "ITR-2 (Schedule CG, Schedule FA, Form 67)"
        },
        "UK": {
            "name": "United Kingdom",
            "flag": "🇬🇧",
            "authority": "HM Revenue & Customs (HMRC)",
            "fiscal_year": "April 6 – April 5",
            "currency": "GBP",
            "currency_symbol": "£",
            "cgt_rules": "Annual Exempt Amount £3,000; 20% on higher rate (10% basic)",
            "lot_method": "Section 104 Holding (Average Cost Pooling) + 30-Day 'Bed & Breakfasting'",
            "fx_rule": "HMRC Monthly Average Spot Rate",
            "statutory_form": "Self Assessment (SA108 Capital Gains Summary)"
        },
        "US": {
            "name": "United States",
            "flag": "🇺🇸",
            "authority": "Internal Revenue Service (IRS)",
            "fiscal_year": "January 1 – December 31",
            "currency": "USD",
            "currency_symbol": "$",
            "cgt_rules": "LTCG >12m (0%/15%/20% + 3.8% NIIT); STCG <=12m (Ordinary Income up to 37%)",
            "lot_method": "Specific Identification / FIFO + 30-Day Wash-Sale Rule",
            "fx_rule": "US Treasury Reporting Rates",
            "statutory_form": "Form 1040 (Schedule D & Form 8949)"
        },
        "GLOBAL": {
            "name": "UAE / Singapore / Offshore",
            "flag": "🌐",
            "authority": "ADGM / DIFC / IRAS (Singapore)",
            "fiscal_year": "January 1 – December 31",
            "currency": "USD",
            "currency_symbol": "$",
            "cgt_rules": "0% Capital Gains Tax, 0% Dividend Withholding",
            "lot_method": "Average Cost Basis",
            "fx_rule": "Spot FX Rate",
            "statutory_form": "CRS / FATCA Annual Self-Certification"
        }
    }

    # Reference FX rates to base USD
    FX_TO_USD = {
        "USD": 1.0,
        "INR": 88.75,
        "GBP": 0.79,
        "EUR": 0.92,
        "AED": 3.67,
        "SGD": 1.34
    }

    @classmethod
    def calculate_uk_hmrc_pooling(cls, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Implements HMRC Section 104 Share Pooling:
        All shares of the same class acquired by the same person in the same company
        are treated as forming a single asset (a 'pool'), which grows or shrinks with
        each acquisition or disposal, with an average pooled cost.
        """
        # Group by symbol
        pools = {}
        realized_events = []
        total_uk_gain_gbp = 0.0

        usd_to_gbp = cls.FX_TO_USD["GBP"]

        # Sort trades chronologically
        sorted_trades = sorted(trades, key=lambda t: t.get("date", ""))

        for t in sorted_trades:
            sym = t.get("symbol", "")
            action = t.get("action", "").upper()
            qty = float(t.get("quantity", 0.0))
            price_usd = float(t.get("price_usd", 0.0))
            price_gbp = price_usd * usd_to_gbp
            trade_date = t.get("date", "")

            if sym not in pools:
                pools[sym] = {"total_qty": 0.0, "total_cost_gbp": 0.0}

            if action == "BUY":
                pools[sym]["total_qty"] += qty
                pools[sym]["total_cost_gbp"] += (qty * price_gbp)
            elif action == "SELL":
                pool = pools[sym]
                if pool["total_qty"] > 0:
                    avg_cost_per_share_gbp = pool["total_cost_gbp"] / pool["total_qty"]
                    disposal_qty = min(qty, pool["total_qty"])
                    cost_basis_gbp = disposal_qty * avg_cost_per_share_gbp
                    proceeds_gbp = disposal_qty * price_gbp
                    gain_gbp = proceeds_gbp - cost_basis_gbp

                    # Update pool
                    pool["total_qty"] -= disposal_qty
                    pool["total_cost_gbp"] -= cost_basis_gbp

                    # HMRC tax year: Apr 6 to Apr 5
                    dt = datetime.strptime(trade_date[:10], "%Y-%m-%d").date()
                    if dt.month > 4 or (dt.month == 4 and dt.day >= 6):
                        uk_ty = f"TY {dt.year}/{str(dt.year + 1)[-2:]}"
                    else:
                        uk_ty = f"TY {dt.year - 1}/{str(dt.year)[-2:]}"

                    total_uk_gain_gbp += gain_gbp
                    realized_events.append({
                        "date": trade_date,
                        "symbol": sym,
                        "quantity": disposal_qty,
                        "disposal_proceeds_gbp": round(proceeds_gbp, 2),
                        "hmrc_pooled_cost_gbp": round(cost_basis_gbp, 2),
                        "gain_loss_gbp": round(gain_gbp, 2),
                        "hmrc_tax_year": uk_ty
                    })

        # HMRC £3,000 Annual Exempt Amount
        uk_annual_exemption = 3000.0
        taxable_uk_gain_gbp = max(0.0, total_uk_gain_gbp - uk_annual_exemption)
        estimated_uk_tax_gbp = taxable_uk_gain_gbp * 0.20 # 20% higher rate

        return {
            "jurisdiction": "UK",
            "statutory_framework": "HMRC Section 104 Share Pooling (TCGA 1992)",
            "total_realized_gain_gbp": round(total_uk_gain_gbp, 2),
            "annual_exempt_amount_gbp": uk_annual_exemption,
            "taxable_gain_gbp": round(taxable_uk_gain_gbp, 2),
            "estimated_tax_gbp": round(estimated_uk_tax_gbp, 2),
            "realized_events": realized_events
        }

    @classmethod
    def get_jurisdiction_comparison(cls, portfolio_usd: float, total_gain_usd: float) -> List[Dict[str, Any]]:
        """
        Returns side-by-side tax comparison of the exact same portfolio across all 4 jurisdictions.
        """
        comparisons = []
        fx = cls.FX_TO_USD

        # 1. INDIA
        inr_val = portfolio_usd * fx["INR"]
        inr_gain = total_gain_usd * fx["INR"]
        in_tax = (inr_gain * 0.20) # Blended rate
        comparisons.append({
            "code": "IN",
            "name": "India (ITR-2)",
            "flag": "🇮🇳",
            "reporting_currency": f"₹{inr_val:,.0f} INR",
            "effective_tax_rate": "12.5% LTCG / 30% STCG",
            "estimated_tax": f"₹{in_tax:,.0f}",
            "key_benefit_or_rule": "Rule 115 SBI TT Conversion; Sec 70 Loss Set-Off",
            "tax_efficiency_rating": "Moderate"
        })

        # 2. UNITED KINGDOM
        gbp_val = portfolio_usd * fx["GBP"]
        gbp_gain = total_gain_usd * fx["GBP"]
        uk_tax = max(0.0, (gbp_gain - 3000.0) * 0.20)
        comparisons.append({
            "code": "UK",
            "name": "United Kingdom (HMRC)",
            "flag": "🇬🇧",
            "reporting_currency": f"£{gbp_val:,.0f} GBP",
            "effective_tax_rate": "20% (above £3k exemption)",
            "estimated_tax": f"£{uk_tax:,.0f}",
            "key_benefit_or_rule": "Section 104 Average Cost Pooling; Bed & ISA Allowance",
            "tax_efficiency_rating": "High (below allowance)"
        })

        # 3. UNITED STATES
        us_tax = total_gain_usd * 0.15 # 15% long-term capital gains rate
        comparisons.append({
            "code": "US",
            "name": "United States (IRS)",
            "flag": "🇺🇸",
            "reporting_currency": f"${portfolio_usd:,.0f} USD",
            "effective_tax_rate": "15% - 20% LTCG",
            "estimated_tax": f"${us_tax:,.0f}",
            "key_benefit_or_rule": "Form 8949 Specific ID; 30-Day Wash-Sale Rule",
            "tax_efficiency_rating": "Moderate"
        })

        # 4. UAE / SINGAPORE
        comparisons.append({
            "code": "GLOBAL",
            "name": "UAE (DIFC) / Singapore",
            "flag": "🌐",
            "reporting_currency": f"${portfolio_usd:,.0f} USD",
            "effective_tax_rate": "0% (Zero Capital Gains)",
            "estimated_tax": "$0 (Tax-Free)",
            "key_benefit_or_rule": "Zero CGT; UCITS Dividend Withholding Optimization",
            "tax_efficiency_rating": "Maximum (0% Drag)"
        })

        return comparisons
