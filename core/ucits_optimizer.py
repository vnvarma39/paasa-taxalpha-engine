"""
UCITS vs US-Domiciled ETF Tax Arbitrage & Estate Tax Shielding Engine.

Analyzes foreign and non-US resident alien (NRA) exposure to:
1. US Estate Tax (up to 40% on US-situs assets > $60,000).
2. Dividend Withholding Tax Leakage (30% statutory or 25% treaty vs 15% Ireland-US treaty).
3. Accumulating (Acc) Share Class Tax Deferral Alpha.
"""

from typing import List, Dict, Any

class UCITSOptimizer:
    # Comprehensive migration mapping from US-domiciled ETFs to equivalent Irish-domiciled UCITS ETFs
    UCITS_MAPPING = {
        "VOO": {
            "name": "Vanguard S&P 500 ETF (US)",
            "ucits_ticker": "CSPX",
            "ucits_alt": "VUAA",
            "ucits_name": "iShares Core S&P 500 UCITS ETF (Acc)",
            "exchange": "London Stock Exchange (LSE)",
            "currency": "USD",
            "is_accumulating": True,
            "us_withholding_rate": 0.25, # Treaty rate for India / 0.30 for non-treaty
            "ucits_withholding_rate": 0.15, # US-Ireland treaty rate at fund level
            "us_ter": 0.0003,
            "ucits_ter": 0.0007,
            "dividend_yield": 0.0145, # 1.45%
            "correlation": 0.999
        },
        "SPY": {
            "name": "SPDR S&P 500 ETF Trust (US)",
            "ucits_ticker": "CSPX",
            "ucits_alt": "SPY5",
            "ucits_name": "iShares Core S&P 500 UCITS ETF (Acc)",
            "exchange": "London Stock Exchange (LSE)",
            "currency": "USD",
            "is_accumulating": True,
            "us_withholding_rate": 0.25,
            "ucits_withholding_rate": 0.15,
            "us_ter": 0.0009,
            "ucits_ter": 0.0007,
            "dividend_yield": 0.0145,
            "correlation": 0.999
        },
        "IVV": {
            "name": "iShares Core S&P 500 ETF (US)",
            "ucits_ticker": "CSPX",
            "ucits_alt": "VUAA",
            "ucits_name": "iShares Core S&P 500 UCITS ETF (Acc)",
            "exchange": "London Stock Exchange (LSE)",
            "currency": "USD",
            "is_accumulating": True,
            "us_withholding_rate": 0.25,
            "ucits_withholding_rate": 0.15,
            "us_ter": 0.0003,
            "ucits_ter": 0.0007,
            "dividend_yield": 0.0145,
            "correlation": 0.999
        },
        "QQQ": {
            "name": "Invesco QQQ Trust (US)",
            "ucits_ticker": "CNDX",
            "ucits_alt": "EQQQ",
            "ucits_name": "iShares NASDAQ 100 UCITS ETF (Acc)",
            "exchange": "London Stock Exchange (LSE)",
            "currency": "USD",
            "is_accumulating": True,
            "us_withholding_rate": 0.25,
            "ucits_withholding_rate": 0.15,
            "us_ter": 0.0020,
            "ucits_ter": 0.0033,
            "dividend_yield": 0.0062, # 0.62%
            "correlation": 0.999
        },
        "VT": {
            "name": "Vanguard Total World Stock ETF (US)",
            "ucits_ticker": "VWRA",
            "ucits_alt": "SSAC",
            "ucits_name": "Vanguard FTSE All-World UCITS ETF (Acc)",
            "exchange": "London Stock Exchange (LSE)",
            "currency": "USD",
            "is_accumulating": True,
            "us_withholding_rate": 0.25,
            "ucits_withholding_rate": 0.15,
            "us_ter": 0.0007,
            "ucits_ter": 0.0022,
            "dividend_yield": 0.0210,
            "correlation": 0.998
        },
        "VTI": {
            "name": "Vanguard Total Stock Market ETF (US)",
            "ucits_ticker": "VUSA",
            "ucits_alt": "CSPX",
            "ucits_name": "Vanguard S&P 500 UCITS ETF",
            "exchange": "London Stock Exchange (LSE)",
            "currency": "USD",
            "is_accumulating": True,
            "us_withholding_rate": 0.25,
            "ucits_withholding_rate": 0.15,
            "us_ter": 0.0003,
            "ucits_ter": 0.0007,
            "dividend_yield": 0.0140,
            "correlation": 0.995
        }
    }

    US_ESTATE_TAX_EXEMPTION_USD = 60000.0  # Non-Resident Alien (NRA) exemption threshold
    US_ESTATE_TAX_TOP_RATE = 0.40          # 40% top marginal federal estate tax

    @classmethod
    def analyze_portfolio(cls, open_positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyzes portfolio holdings for US estate tax liability and dividend tax leakage,
        recommending UCITS migration opportunities.
        """
        total_us_situs_val_usd = 0.0
        us_etf_holdings = []
        annual_withholding_leakage_usd = 0.0
        projected_10yr_reinvestment_alpha_usd = 0.0

        # Aggregate total US-situs exposure
        for pos in open_positions:
            val_usd = pos.get("current_val_usd", 0.0)
            sym = pos.get("symbol", "").upper()
            total_us_situs_val_usd += val_usd

            if sym in cls.UCITS_MAPPING:
                meta = cls.UCITS_MAPPING[sym]
                div_yield = meta["dividend_yield"]
                annual_dividend_usd = val_usd * div_yield

                # Direct tax leakage: (US withholding - Ireland withholding)
                rate_diff = meta["us_withholding_rate"] - meta["ucits_withholding_rate"]
                annual_saved_tax_usd = annual_dividend_usd * rate_diff

                # Expense ratio difference drag
                ter_drag_usd = val_usd * (meta["ucits_ter"] - meta["us_ter"])
                net_annual_alpha_usd = annual_saved_tax_usd - ter_drag_usd

                # 10-year compounding calculation (assuming 8% annualized nominal return)
                compound_10yr = 0.0
                r = 0.08
                for yr in range(1, 11):
                    compound_10yr += net_annual_alpha_usd * ((1 + r) ** (10 - yr))

                annual_withholding_leakage_usd += max(0.0, net_annual_alpha_usd)
                projected_10yr_reinvestment_alpha_usd += max(0.0, compound_10yr)

                us_etf_holdings.append({
                    "symbol": sym,
                    "name": meta["name"],
                    "current_val_usd": round(val_usd, 2),
                    "ucits_replacement": meta["ucits_ticker"],
                    "ucits_alt": meta["ucits_alt"],
                    "ucits_name": meta["ucits_name"],
                    "exchange": meta["exchange"],
                    "currency": meta["currency"],
                    "structure": "Accumulating (Acc - Auto Reinvested)",
                    "annual_dividend_usd": round(annual_dividend_usd, 2),
                    "annual_tax_saved_usd": round(annual_saved_tax_usd, 2),
                    "net_annual_alpha_usd": round(net_annual_alpha_usd, 2),
                    "compound_10yr_alpha_usd": round(compound_10yr, 2),
                    "correlation": meta["correlation"]
                })

        # Calculate US Estate Tax Exposure
        estate_tax_exposed_amount_usd = max(0.0, total_us_situs_val_usd - cls.US_ESTATE_TAX_EXEMPTION_USD)
        estimated_estate_tax_liability_usd = estate_tax_exposed_amount_usd * cls.US_ESTATE_TAX_TOP_RATE

        return {
            "summary": {
                "total_us_situs_assets_usd": round(total_us_situs_val_usd, 2),
                "nra_exemption_limit_usd": cls.US_ESTATE_TAX_EXEMPTION_USD,
                "estate_tax_exposed_amount_usd": round(estate_tax_exposed_amount_usd, 2),
                "estimated_estate_tax_liability_usd": round(estimated_estate_tax_liability_usd, 2),
                "is_estate_tax_at_risk": estate_tax_exposed_amount_usd > 0,
                "total_annual_withholding_leakage_usd": round(annual_withholding_leakage_usd, 2),
                "projected_10yr_reinvestment_alpha_usd": round(projected_10yr_reinvestment_alpha_usd, 2)
            },
            "ucits_candidates": us_etf_holdings,
            "statutory_benefits": [
                {
                    "title": "US Estate Tax Shielding",
                    "badge": "40% Asset Protection",
                    "description": "Non-US residents (NRAs) investing in US-domiciled assets face up to 40% federal estate tax on assets over $60k upon death. Irish UCITS ETFs are non-US situs assets, completely eliminating US estate tax liability."
                },
                {
                    "title": "15% Dividend Withholding Cap",
                    "badge": "Tax Treaty Alpha",
                    "description": "Ireland's bilateral tax treaty with the US automatically cuts dividend withholding from 30% (standard NRA rate) to 15% at the fund level without manual tax filings."
                },
                {
                    "title": "Automatic NAV Reinvestment (Accumulating Share Class)",
                    "badge": "Zero Drag Compounding",
                    "description": "UCITS 'Acc' share classes reinvest dividends internally without triggering local distribution taxable events, eliminating annual dividend taxation and FX conversion frictions."
                }
            ]
        }
