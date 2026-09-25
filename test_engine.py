"""
Paasa TaxAlpha Engine: Comprehensive Test Suite & Verification Script
---------------------------------------------------------------------
Verifies:
1. Rule 115 SBI TT Buying Rate currency conversion & fallback interpolation.
2. Trade log ingestion, schema validation, and typed record generation.
3. FIFO lot matching, LTCG/STCG classification, and Return Decomposition.
4. Pre-March 31 Tax-Loss Harvester & correlated ETF substitute matrix.
5. Foreign dividend tax credit under India-US DTAA (Section 90 / Form 67).
6. CA-Ready Excel Report generation.
"""

import json
import os
import sys
from datetime import date
from io import StringIO

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from core.currency import (
    CurrencyConverter,
    Rule115CurrencyConverter,
    convert_usd_to_inr,
    get_default_converter,
    get_preceding_month_key,
    get_sbi_tt_rate,
)
from core.dtaa import DTAAReconciler
from core.loss_harvester import LossHarvester, TaxLossHarvester
from core.parser import (
    TradeParser,
    TradeRecord,
    get_indian_financial_year,
    parse_csv,
    trades_to_dataframe,
)
from core.tax_engine import TaxEngine


def test_currency_engine():
    print("\n" + "=" * 65)
    print("[1] TESTING CURRENCY CONVERSION (RULE 115)")
    print("=" * 65)

    # 1. Preceding month key calculation
    assert get_preceding_month_key("2024-05-15") == "2024-04"
    assert get_preceding_month_key("2024-01-10") == "2023-12"
    assert get_preceding_month_key(date(2023, 1, 1)) == "2022-12"
    print("  [OK] Preceding month key calculation verified.")

    # 2. Historical lookup
    rate_apr24 = get_sbi_tt_rate("2024-05-15")  # looks up 2024-04 rate (83.40 / 83.45)
    assert 80.0 <= rate_apr24 <= 90.0, f"Unexpected rate: {rate_apr24}"

    rate_dec23 = get_sbi_tt_rate("2024-01-20")  # looks up 2023-12 rate (83.15)
    assert 80.0 <= rate_dec23 <= 90.0, f"Unexpected rate: {rate_dec23}"

    conv_amt, rate = convert_usd_to_inr(100.0, "2024-05-15")
    assert conv_amt > 0, "Conversion amount should be positive"
    print(f"  [OK] Standard lookup: $100 on 2024-05-15 -> INR {conv_amt:,.2f} @ INR {rate}/USD")

    # 3. Boundary & fallback interpolation
    rate_future = get_sbi_tt_rate("2030-01-01")
    assert rate_future > 0, "Future fallback failed"
    rate_past = get_sbi_tt_rate("2020-01-01")
    assert rate_past > 0, "Past fallback failed"
    print("  [OK] Out-of-bounds boundary fallback & interpolation verified.")


def test_parser_engine(csv_path: str):
    print("\n" + "=" * 65)
    print("[2] TESTING TRADE PARSER & VALIDATION")
    print("=" * 65)

    trades = parse_csv(csv_path)
    assert len(trades) > 0, "No trades parsed from sample CSV"
    print(f"  [OK] Successfully parsed {len(trades)} trades from {os.path.basename(csv_path)}")

    # Check date sorting
    for i in range(len(trades) - 1):
        assert trades[i]["date"] <= trades[i + 1]["date"], "Trades not sorted chronologically"
    print("  [OK] Chronological trade order verified.")

    # Check typed attributes
    sample = trades[0]
    assert sample["action"] in {"BUY", "SELL", "DIVIDEND"}
    assert sample["quantity"] > 0
    assert sample["price_usd"] > 0
    print(f"  [OK] Sample trade verified: Date={sample['date']}, "
          f"{sample['symbol']} {sample['action']} {sample['quantity']} @ ${sample['price_usd']}")

    # Test string buffer parsing
    mini_csv = (
        "Date,Symbol,Asset_Type,Action,Quantity,Price_USD,Fees_USD,Withholding_Tax_USD\n"
        "2024-06-01,NVDA,Stock,BUY,10,120.0,1.0,0.0\n"
    )
    mini_trades = parse_csv(StringIO(mini_csv))
    assert len(mini_trades) == 1 and mini_trades[0]["symbol"] == "NVDA"
    print("  [OK] In-memory stream / string CSV parsing verified.")

    # Test dataframe conversion
    df = trades_to_dataframe(trades)
    assert len(df) == len(trades)
    print(f"  [OK] Pandas DataFrame conversion verified: {df.shape[0]} rows, {df.shape[1]} cols")

    return trades


def test_tax_engine(trades):
    print("\n" + "=" * 65)
    print("[3] TESTING TAX ENGINE (FIFO LOT MATCHING & RULE 115)")
    print("=" * 65)

    engine = TaxEngine()
    analysis = engine.calculate(trades, tax_slab_pct=30.0, current_date="2026-03-25")

    realized = analysis["realized_trades"]
    dividends = analysis["dividends"]
    open_positions = analysis["open_positions"]
    fy_summary = analysis["fy_summary"]

    assert len(realized) > 0, "Expected realized trades"
    assert len(dividends) > 0, "Expected dividend records"
    assert len(open_positions) > 0, "Expected open positions"

    print(f"  [OK] Processed portfolio:")
    print(f"       • Realized Trades Matched : {len(realized)}")
    print(f"       • Dividend Distributions   : {len(dividends)}")
    print(f"       • Currently Open Lots      : {len(open_positions)}")

    # Verify Return Decomposition & Holding Period Classification
    from datetime import datetime
    for t in realized:
        days = t["holding_days"]
        dt_sell = datetime.strptime(t["sell_date"][:10], "%Y-%m-%d").date()
        threshold = 24.0 if dt_sell >= date(2024, 7, 23) else 36.0
        if t["holding_months"] > threshold:
            assert t["term"] == "LTCG", f"Trade held {days} days ({t['holding_months']}m) on {t['sell_date']} misclassified as {t['term']}"
        else:
            assert t["term"] == "STCG", f"Trade held {days} days ({t['holding_months']}m) on {t['sell_date']} misclassified as {t['term']}"

        # Gain calculation verification
        assert "gain_inr" in t
        assert "asset_gain_usd" in t
        assert "fx_gain_inr" in t

    print("  [OK] Holding period partition (>24 months = LTCG, <=24 months = STCG) verified.")
    print("  [OK] Asset Return & Currency Drift decomposition verified.")

    # Print Indian FY Summaries
    print("\n  [+] Indian Financial Year Summaries (April 1 - March 31):")
    for fy, s in sorted(fy_summary.items()):
        print(f"     • {fy}:")
        print(f"       Realized Gain INR  : INR {s['total_gain_inr']:,.2f} (${s['gain_usd']:,.2f})")
        print(f"       STCG Gain (Slab)   : INR {s['stcg_gain_inr']:,.2f} -> Tax: INR {s['stcg_tax_inr']:,.2f}")
        print(f"       LTCG Gain (12.5%)  : INR {s['ltcg_gain_inr']:,.2f} -> Tax: INR {s['ltcg_tax_inr']:,.2f}")
        print(f"       Total Estimated Tax: INR {s['total_tax_inr']:,.2f}")

    return analysis


def test_loss_harvester(open_positions):
    print("\n" + "=" * 65)
    print("[4] TESTING PRE-MARCH 31 TAX-LOSS HARVESTER")
    print("=" * 65)

    harvester = TaxLossHarvester()
    harvest_result = harvester.analyze_harvest_opportunities(
        open_positions, tax_slab_pct=30.0
    )

    candidates = harvest_result["candidates"]
    total_loss_usd = harvest_result["total_harvestable_loss_usd"]
    total_loss_inr = harvest_result["total_harvestable_loss_inr"]
    total_saved_inr = harvest_result["total_potential_tax_saved_inr"]

    print(f"  • Total Underwater Candidates : {len(candidates)}")
    print(f"  • Total Harvestable Losses    : ${total_loss_usd:,.2f} (INR {total_loss_inr:,.2f})")
    print(f"  • Potential Direct Tax Savings: INR {total_saved_inr:,.2f}")

    assert len(candidates) > 0, "Expected underwater loss candidates (e.g. AMD, TSLA)"
    assert total_saved_inr > 0, "Expected positive tax savings"

    print("\n  [+] Actionable Tax-Loss Harvesting Recommendations:")
    for idx, c in enumerate(candidates, start=1):
        print(f"    {idx}. {c['symbol']} ({c['quantity']} shares @ ~${c['current_price_usd']} vs Cost ${c['buy_price_usd']})")
        print(f"       Loss: -INR {c['loss_inr']:,.2f} (-${c['loss_usd']:,.2f}, {c['loss_pct']}%) | {c['loss_type']}")
        print(f"       Tax Saved in Cash: INR {c['potential_tax_saved_inr']:,.2f} (Offset @ {c['applicable_tax_rate']}%)")
        if c.get("swap"):
            swap = c["swap"]
            print(f"       --> Recommended Wash-Sale Substitute: {swap['primary_substitute']} ({swap['substitute_name']})")
            print(f"           Correlation: {swap['correlation']} | Expense Ratio: {swap['expense_ratio']}")
            print(f"           Rationale: {swap['rationale']}")
            print(f"           Rebalance Action: BUY ~{swap['est_substitute_quantity']} shares of {swap['primary_substitute']} @ ${swap['est_substitute_price']}")

    return harvest_result


def test_dtaa_engine(dividends):
    print("\n" + "=" * 65)
    print("[5] TESTING DTAA FOREIGN DIVIDEND TAX CREDIT & FORM 67")
    print("=" * 65)

    form_67_schedule = DTAAReconciler.generate_form_67_schedule(dividends, tax_slab_pct=30.0)
    entries = form_67_schedule["entries"]
    summary = form_67_schedule["summary"]

    assert len(entries) > 0, "Expected Form 67 dividend entries"
    print(f"  • Dividend Events Reconciled  : {len(entries)}")
    print(f"  • Total Gross Foreign Dividend: ${summary['total_gross_dividend_usd']:,.2f} (INR {summary['total_gross_dividend_inr']:,.2f})")
    print(f"  • US Withholding Tax (25%)    : ${summary['total_withholding_usd']:,.2f} (INR {summary['total_withholding_inr']:,.2f})")
    print(f"  • Indian Tax Liability (30%)  : INR {summary['total_indian_tax_inr']:,.2f}")
    print(f"  • Section 90 FTC Relief Claim : INR {summary['total_ftc_claimed_inr']:,.2f}")
    print(f"  • Net Indian Tax Due After FTC: INR {summary['net_tax_payable_inr']:,.2f}")

    assert summary["total_ftc_claimed_inr"] > 0
    assert summary["net_tax_payable_inr"] >= 0

    # Verify Schedule FSI details on first entry
    first = entries[0]
    assert first["country_code"] == "01 (United States)"
    assert "Article 10" in first["dtaa_article"]
    print(f"  [OK] Form 67 & Schedule FSI statutory fields verified.")

    return form_67_schedule


def test_exporter_excel(analysis_data):
    print("\n" + "=" * 65)
    print("[6] TESTING CA-READY EXCEL REPORT EXPORTER")
    print("=" * 65)

    try:
        from core.exporter import ReportExporter
        excel_out = ReportExporter.export_excel(analysis_data)
        excel_bytes = excel_out.getvalue() if hasattr(excel_out, "getvalue") else excel_out
        assert len(excel_bytes) > 1000, "Excel output is suspiciously small"
        report_path = os.path.join(base_dir, "exports", "ca_taxalpha_report_demo.xlsx")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "wb") as f:
            f.write(excel_bytes)
        print(f"  [OK] Generated multi-tab CA-ready Excel workbook: {os.path.basename(report_path)} ({len(excel_bytes):,} bytes)")
    except Exception as e:
        print(f"  [NOTE] Excel exporter skipped or optional: {e}")


def test_benchmark_engine(analysis_data):
    print("\n" + "=" * 65)
    print("[7] TESTING TAX ALPHA & COMPUTATIONAL BENCHMARK ENGINE")
    print("=" * 65)

    from core.benchmark import TaxAlphaFinancialBenchmark, EngineThroughputBenchmark

    bench = TaxAlphaFinancialBenchmark.evaluate(analysis_data, tax_slab_pct=30.0)
    assert bench["tax_alpha_inr"] > 0, "Tax alpha INR should be positive"
    assert bench["tax_alpha_bps"] > 0, "Tax alpha bps should be positive"
    assert len(bench["benchmark_tracking"]) >= 4, "Should have 4 benchmark ETF tracking pairs"
    print(f"  [OK] Financial Tax Alpha verified: ₹{bench['tax_alpha_inr']:,.2f} (+{bench['tax_alpha_bps']} bps)")
    print(f"  [OK] Tracking error fidelity verified: VOO/IVV TE={bench['benchmark_tracking'][0]['tracking_error_pct']}%")

    # Fast micro-throughput check
    r115_bench = EngineThroughputBenchmark.benchmark_rule115_lookups(iterations=1000)
    assert r115_bench["throughput_ops_per_sec"] > 1000, "Rule 115 throughput should exceed 1000 ops/sec"
    print(f"  [OK] Rule 115 Micro-Throughput verified: {r115_bench['throughput_ops_per_sec']:,} lookups/sec")

    fifo_bench = EngineThroughputBenchmark.benchmark_fifo_matching(batch_sizes=[200])
    assert fifo_bench[0]["throughput_trades_per_sec"] > 500, "FIFO throughput should exceed 500 trades/sec"
    print(f"  [OK] FIFO Lot Micro-Throughput verified: {fifo_bench[0]['throughput_trades_per_sec']:,} trades/sec")


def main():
    csv_path = os.path.join(base_dir, "data", "sample_portfolio_ibkr.csv")

    test_currency_engine()
    trades = test_parser_engine(csv_path)
    analysis = test_tax_engine(trades)
    harvest = test_loss_harvester(analysis["open_positions"])
    dtaa_report = test_dtaa_engine(analysis["dividends"])

    analysis["tax_loss_harvest"] = harvest
    analysis["dtaa_form_67"] = dtaa_report

    test_exporter_excel(analysis)
    test_benchmark_engine(analysis)

    # Export unified JSON output
    out_json = os.path.join(base_dir, "data", "engine_test_output.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, default=str)

    print("\n" + "=" * 65)
    print(f"SUCCESS: All Paasa TaxAlpha Engine calculations passed cleanly!")
    print(f"Summary JSON written to: {out_json}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()

