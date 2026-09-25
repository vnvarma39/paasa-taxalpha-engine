"""
Paasa Core Financial Engine Package
-----------------------------------
A dual-calendar financial calculation engine for Indian investors
allocating capital to global markets under RBI's LRS scheme.
"""

from .currency import (
    Rule115CurrencyConverter,
    CurrencyConverter,
    get_sbi_tt_rate,
    convert_usd_to_inr,
    get_preceding_month_key,
    get_default_converter,
)
from .parser import (
    TradeParser,
)
from .tax_engine import (
    TaxEngine,
)
from .loss_harvester import (
    TaxLossHarvester,
    LossHarvester,
)
from .dtaa_reconciler import (
    DTAAReconciler,
)
from .exporter import (
    ReportExporter,
)
from .ucits_optimizer import (
    UCITSOptimizer,
)
from .global_tax import (
    GlobalTaxEngine,
)

__all__ = [
    "Rule115CurrencyConverter",
    "CurrencyConverter",
    "get_sbi_tt_rate",
    "convert_usd_to_inr",
    "get_preceding_month_key",
    "get_default_converter",
    "TradeParser",
    "TaxEngine",
    "TaxLossHarvester",
    "LossHarvester",
    "DTAAReconciler",
    "ReportExporter",
    "UCITSOptimizer",
    "GlobalTaxEngine",
]
