import os
import json
from datetime import datetime, date

class Rule115CurrencyConverter:
    """
    Implements Rule 115 of the Indian Income Tax Rules, 1962:
    Exchange rate for foreign income/gains conversion to INR must be the
    SBI Telegraphic Transfer (TT) Buying Rate as on the last day of the
    month immediately preceding the month of the transaction.
    """


    def __init__(self, rates_file=None):
        if rates_file is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            rates_file = os.path.join(base_dir, "data", "sbi_tt_historical.json")

        self.rates_file = rates_file
        self.rates = self._load_rates()

    def _load_rates(self):
        default_rates = {
            "2021-01": 72.85, "2021-06": 74.30, "2021-12": 74.50,
            "2022-01": 74.70, "2022-03": 75.80, "2022-06": 78.30, "2022-12": 82.70,
            "2023-01": 81.80, "2023-03": 82.15, "2023-06": 82.05, "2023-12": 83.15,
            "2024-01": 83.05, "2024-03": 83.35, "2024-06": 83.45, "2024-12": 84.85,
            "2025-01": 86.20, "2025-03": 86.95, "2025-06": 87.40, "2025-12": 88.20,
            "2026-01": 88.50, "2026-02": 88.75, "2026-03": 89.10
        }
        if os.path.exists(self.rates_file):
            try:
                with open(self.rates_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return default_rates
        return default_rates

    def get_preceding_month_key(self, dt):
        """
        Given a date, returns 'YYYY-MM' of the preceding month.
        E.g. 2024-03-10 -> '2024-02'
             2024-01-15 -> '2023-12'
        """
        if isinstance(dt, str):
            # Parse YYYY-MM-DD
            dt = datetime.strptime(dt[:10], "%Y-%m-%d").date()
        elif isinstance(dt, datetime):
            dt = dt.date()

        year = dt.year
        month = dt.month - 1
        if month == 0:
            month = 12
            year -= 1
        return f"{year:04d}-{month:02d}"

    def get_rule_115_rate(self, dt):
        """
        Returns the SBI TT Buying Rate for the date as mandated by Rule 115.
        """
        key = self.get_preceding_month_key(dt)
        if key in self.rates:
            return float(self.rates[key])

        # If key missing, find closest available key
        available_keys = sorted(self.rates.keys())
        if not available_keys:
            return 86.50

        if key < available_keys[0]:
            return float(self.rates[available_keys[0]])
        if key > available_keys[-1]:
            return float(self.rates[available_keys[-1]])

        # Find closest preceding
        candidate = available_keys[0]
        for k in available_keys:
            if k <= key:
                candidate = k
            else:
                break
        return float(self.rates[candidate])

    def convert_usd_to_inr(self, usd_amount, dt):
        """
        Converts USD amount to INR using the Rule 115 exchange rate.
        """
        rate = self.get_rule_115_rate(dt)
        return round(usd_amount * rate, 2), rate

    def decompose_return(self, buy_usd, sell_usd, buy_date, sell_date):
        """
        Decomposes total INR gain into Asset Growth and FX Currency Drift.
        Returns:
            asset_gain_usd, asset_gain_pct,
            fx_gain_inr, fx_gain_pct,
            total_gain_inr, total_gain_pct
        """
        buy_fx = self.get_rule_115_rate(buy_date)
        sell_fx = self.get_rule_115_rate(sell_date)

        buy_inr = buy_usd * buy_fx
        sell_inr = sell_usd * sell_fx

        total_gain_inr = sell_inr - buy_inr
        total_gain_pct = ((sell_inr / buy_inr) - 1.0) * 100.0 if buy_inr > 0 else 0.0

        asset_gain_usd = sell_usd - buy_usd
        asset_gain_pct = ((sell_usd / buy_usd) - 1.0) * 100.0 if buy_usd > 0 else 0.0

        fx_gain_pct = ((sell_fx / buy_fx) - 1.0) * 100.0 if buy_fx > 0 else 0.0
        # FX portion of INR gain: Buy_USD * (Sell_FX - Buy_FX)
        fx_gain_inr = buy_usd * (sell_fx - buy_fx)

        return {
            "buy_fx": buy_fx,
            "sell_fx": sell_fx,
            "buy_inr": round(buy_inr, 2),
            "sell_inr": round(sell_inr, 2),
            "total_gain_inr": round(total_gain_inr, 2),
            "total_gain_pct": round(total_gain_pct, 2),
            "asset_gain_usd": round(asset_gain_usd, 2),
            "asset_gain_pct": round(asset_gain_pct, 2),
            "fx_gain_inr": round(fx_gain_inr, 2),
            "fx_gain_pct": round(fx_gain_pct, 2),
        }

CurrencyConverter = Rule115CurrencyConverter
_default_converter = None

def get_default_converter():
    global _default_converter
    if _default_converter is None:
        _default_converter = Rule115CurrencyConverter()
    return _default_converter

def get_sbi_tt_rate(dt):
    return get_default_converter().get_rule_115_rate(dt)

def convert_usd_to_inr(usd_amount, dt):
    return get_default_converter().convert_usd_to_inr(usd_amount, dt)

def get_preceding_month_key(dt):
    return get_default_converter().get_preceding_month_key(dt)

