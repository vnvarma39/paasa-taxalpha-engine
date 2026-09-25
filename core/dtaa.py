"""
Paasa Core DTAA & Foreign Tax Credit Engine: India-US Article 10 & Form 67
--------------------------------------------------------------------------
Reconciles US dividend withholding tax (25%) with Indian tax liability
under the India-US Double Tax Avoidance Agreement (DTAA Section 90 / Rule 128).
Prepares statutory schedule data for Form 67 and Schedule FSI (ITR-2/ITR-3).
"""

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

from .currency import CurrencyConverter, get_default_converter
from .parser import TradeRecord, get_indian_financial_year


@dataclass
class DividendReconciliationItem:
    trade_id: int
    date: date
    symbol: str
    quantity: float
    dividend_per_share_usd: float
    gross_dividend_usd: float
    withholding_tax_usd: float
    net_dividend_usd: float
    fx_rate: float
    gross_dividend_inr: float
    withholding_tax_inr: float
    net_dividend_inr: float
    indian_tax_rate: float
    indian_tax_payable_inr: float
    foreign_tax_credit_inr: float  # Section 90 FTC relief
    net_indian_tax_due_inr: float
    excess_us_tax_inr: float
    financial_year: str
    article_dtaa: str = "Article 10 (Dividends)"
    country_name: str = "United States of America"
    country_code: str = "01"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["date"] = self.date.isoformat()
        return d


@dataclass
class DTAASummaryFY:
    financial_year: str
    total_records: int
    total_gross_dividend_usd: float
    total_withholding_tax_usd: float
    total_net_dividend_usd: float
    total_gross_dividend_inr: float
    total_withholding_tax_inr: float
    total_indian_tax_payable_inr: float
    total_foreign_tax_credit_inr: float
    total_net_indian_tax_due_inr: float
    total_excess_foreign_tax_inr: float
    items: List[DividendReconciliationItem] = field(default_factory=list)
    schedule_fsi: Dict[str, Any] = field(default_factory=dict)
    form_67_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["items"] = [i.to_dict() for i in self.items]
        return d


class DTAAReconciler:
    """
    Reconciles foreign dividend withholding taxes against Indian tax liabilities
    under Article 10 of India-US DTAA and Rule 128 of Indian Income Tax Rules.
    """

    def __init__(
        self,
        converter: Optional[CurrencyConverter] = None,
        investor_slab_rate: float = 0.30,  # 30% default slab rate
        cess_rate: float = 0.04,  # 4% Health & Education Cess
        include_cess: bool = True,
    ):
        self.converter = converter or get_default_converter()
        self.investor_slab_rate = investor_slab_rate
        self.cess_rate = cess_rate
        self.effective_tax_rate = (
            investor_slab_rate * (1 + cess_rate) if include_cess else investor_slab_rate
        )

    def process_dividends(self, dividend_trades: List[TradeRecord]) -> List[DividendReconciliationItem]:
        """
        Processes dividend TradeRecords into detailed DTAA reconciliation items.
        """
        items: List[DividendReconciliationItem] = []

        for trade in dividend_trades:
            if trade.action != "DIVIDEND":
                continue

            gross_usd = trade.total_usd
            wht_usd = trade.withholding_tax_usd
            # If withholding tax is 0 in input, check default 25% US treaty rate
            if wht_usd == 0.0 and gross_usd > 0.0:
                wht_usd = round(gross_usd * 0.25, 2)

            net_usd = round(gross_usd - wht_usd, 4)

            fx_rate = trade.fx_rate
            gross_inr = round(gross_usd * fx_rate, 2)
            wht_inr = round(wht_usd * fx_rate, 2)
            net_inr = round(gross_inr - wht_inr, 2)

            # Indian tax on gross dividend under "Income from Other Sources"
            indian_tax_inr = round(gross_inr * self.effective_tax_rate, 2)

            # Foreign Tax Credit (FTC) under Rule 128: lower of Indian tax or US tax paid
            ftc_inr = round(min(indian_tax_inr, wht_inr), 2)
            net_indian_tax_due = round(max(0.0, indian_tax_inr - ftc_inr), 2)
            excess_us_tax = round(max(0.0, wht_inr - indian_tax_inr), 2)

            item = DividendReconciliationItem(
                trade_id=trade.trade_id,
                date=trade.date,
                symbol=trade.symbol,
                quantity=trade.quantity,
                dividend_per_share_usd=trade.price_usd,
                gross_dividend_usd=gross_usd,
                withholding_tax_usd=wht_usd,
                net_dividend_usd=net_usd,
                fx_rate=fx_rate,
                gross_dividend_inr=gross_inr,
                withholding_tax_inr=wht_inr,
                net_dividend_inr=net_inr,
                indian_tax_rate=round(self.effective_tax_rate, 4),
                indian_tax_payable_inr=indian_tax_inr,
                foreign_tax_credit_inr=ftc_inr,
                net_indian_tax_due_inr=net_indian_tax_due,
                excess_us_tax_inr=excess_us_tax,
                financial_year=trade.financial_year,
            )
            items.append(item)

        return items

    def get_summary_by_fy(
        self, dividend_trades: List[TradeRecord], financial_year: Optional[str] = None
    ) -> Dict[str, DTAASummaryFY]:
        """
        Aggregates dividend reconciliation by Indian Financial Year and constructs
        statutory Schedule FSI and Form 67 fields.
        """
        items = self.process_dividends(dividend_trades)
        by_fy: Dict[str, List[DividendReconciliationItem]] = {}
        for item in items:
            fy = item.financial_year
            if fy not in by_fy:
                by_fy[fy] = []
            by_fy[fy].append(item)

        if financial_year and financial_year not in by_fy:
            by_fy[financial_year] = []

        summaries: Dict[str, DTAASummaryFY] = {}

        for fy, fy_items in sorted(by_fy.items()):
            if financial_year and fy != financial_year:
                continue

            tot_gross_usd = round(sum(i.gross_dividend_usd for i in fy_items), 2)
            tot_wht_usd = round(sum(i.withholding_tax_usd for i in fy_items), 2)
            tot_net_usd = round(sum(i.net_dividend_usd for i in fy_items), 2)

            tot_gross_inr = round(sum(i.gross_dividend_inr for i in fy_items), 2)
            tot_wht_inr = round(sum(i.withholding_tax_inr for i in fy_items), 2)
            tot_ind_tax_inr = round(sum(i.indian_tax_payable_inr for i in fy_items), 2)
            tot_ftc_inr = round(sum(i.foreign_tax_credit_inr for i in fy_items), 2)
            tot_net_ind_tax = round(sum(i.net_indian_tax_due_inr for i in fy_items), 2)
            tot_excess_tax = round(sum(i.excess_us_tax_inr for i in fy_items), 2)

            # Schedule FSI fields required for ITR-2
            schedule_fsi = {
                "country_code": "01",
                "country_name": "United States of America",
                "head_of_income": "Income from Other Sources (Foreign Dividends)",
                "gross_foreign_income_inr": tot_gross_inr,
                "tax_paid_outside_india_inr": tot_wht_inr,
                "tax_payable_in_india_inr": tot_ind_tax_inr,
                "relief_claimed_section_90_inr": tot_ftc_inr,
                "dtaa_article": "Article 10",
            }

            # Form 67 summary required before ITR filing
            form_67 = {
                "financial_year": fy,
                "source_country": "USA (01)",
                "nature_of_income": "Dividends",
                "income_amount_usd": tot_gross_usd,
                "income_amount_inr": tot_gross_inr,
                "us_withholding_tax_paid_usd": tot_wht_usd,
                "us_withholding_tax_paid_inr": tot_wht_inr,
                "relief_under_section_90_inr": tot_ftc_inr,
                "filing_requirement": "Mandatory prior to filing ITR-2 to claim Foreign Tax Credit",
            }

            summaries[fy] = DTAASummaryFY(
                financial_year=fy,
                total_records=len(fy_items),
                total_gross_dividend_usd=tot_gross_usd,
                total_withholding_tax_usd=tot_wht_usd,
                total_net_dividend_usd=tot_net_usd,
                total_gross_dividend_inr=tot_gross_inr,
                total_withholding_tax_inr=tot_wht_inr,
                total_indian_tax_payable_inr=tot_ind_tax_inr,
                total_foreign_tax_credit_inr=tot_ftc_inr,
                total_net_indian_tax_due_inr=tot_net_ind_tax,
                total_excess_foreign_tax_inr=tot_excess_tax,
                items=fy_items,
                schedule_fsi=schedule_fsi,
                form_67_summary=form_67,
            )

        return summaries

    @staticmethod
    def generate_form_67_schedule(dividends, tax_slab_pct=30.0):
        """
        Builds line-by-line Form 67 / Schedule FSI schedule from parsed dividend events.
        Compatible with raw dividend dictionaries.
        """
        schedule_entries = []
        total_gross_dividend_usd = 0.0
        total_withholding_usd = 0.0
        total_gross_dividend_inr = 0.0
        total_withholding_inr = 0.0
        total_ftc_claimed_inr = 0.0
        total_indian_tax_inr = 0.0

        for div in dividends:
            gross_usd = div.get("gross_div_usd", 0.0)
            wht_usd = div.get("withholding_usd", 0.0)
            gross_inr = div.get("gross_div_inr", 0.0)
            wht_inr = div.get("withholding_inr", 0.0)
            rate = div.get("fx_rate", 83.0)

            indian_tax = round(gross_inr * (tax_slab_pct / 100.0), 2)
            ftc_allowed = min(wht_inr, indian_tax)
            net_tax_due = max(0.0, indian_tax - ftc_allowed)

            entry = {
                "date": div.get("date", ""),
                "symbol": div.get("symbol", ""),
                "country_code": "01 (United States)",
                "dtaa_article": "Article 10 (Dividends - 25% Rate)",
                "gross_income_usd": gross_usd,
                "rule_115_fx_rate": rate,
                "gross_income_inr": gross_inr,
                "tax_paid_usd": wht_usd,
                "tax_paid_inr": wht_inr,
                "indian_tax_liability_inr": indian_tax,
                "tax_relief_sec_90_inr": ftc_allowed,
                "net_tax_payable_inr": net_tax_due,
                "indian_fy": div.get("indian_fy", ""),
                "form_67_status": "Eligible for Foreign Tax Credit",
            }
            schedule_entries.append(entry)

            total_gross_dividend_usd += gross_usd
            total_withholding_usd += wht_usd
            total_gross_dividend_inr += gross_inr
            total_withholding_inr += wht_inr
            total_ftc_claimed_inr += ftc_allowed
            total_indian_tax_inr += indian_tax

        return {
            "entries": schedule_entries,
            "summary": {
                "total_gross_dividend_usd": round(total_gross_dividend_usd, 2),
                "total_withholding_usd": round(total_withholding_usd, 2),
                "total_gross_dividend_inr": round(total_gross_dividend_inr, 2),
                "total_withholding_inr": round(total_withholding_inr, 2),
                "total_ftc_claimed_inr": round(total_ftc_claimed_inr, 2),
                "total_indian_tax_inr": round(total_indian_tax_inr, 2),
                "net_tax_payable_inr": round(max(0.0, total_indian_tax_inr - total_ftc_claimed_inr), 2),
            },
        }

