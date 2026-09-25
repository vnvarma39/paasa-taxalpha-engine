import os
import sys
import json
import argparse
import webbrowser
import threading
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, send_file, Response

from core.parser import TradeParser
from core.currency import Rule115CurrencyConverter
from core.tax_engine import TaxEngine
from core.loss_harvester import TaxLossHarvester
from core.dtaa_reconciler import DTAAReconciler
from core.exporter import ReportExporter
from core.ucits_optimizer import UCITSOptimizer
from core.global_tax import GlobalTaxEngine
from core.benchmark import TaxAlphaFinancialBenchmark, EngineThroughputBenchmark

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DATA_DIR = os.path.join(BASE_DIR, "data")
SAMPLE_CSV_PATH = os.path.join(DATA_DIR, "sample_portfolio_ibkr.csv")

app = Flask(__name__, static_folder=STATIC_DIR)

# Shared in-memory cache of latest analysis result for 1-click export
latest_analysis_cache = {
    "data": None,
    "timestamp": None,
    "filename": "sample_portfolio_ibkr.csv"
}

def run_pipeline(csv_source, tax_slab_pct=30.0, selected_fy=None):
    """
    Executes the complete Paasa TaxAlpha calculation pipeline.
    """
    trades = TradeParser.parse_csv(csv_source)
    if not trades:
        raise ValueError("No valid trades found in the provided CSV statement.")

    engine = TaxEngine()
    analysis = engine.calculate(trades, tax_slab_pct=tax_slab_pct)

    harvester = TaxLossHarvester()
    harvest = harvester.analyze_harvest_opportunities(
        analysis["open_positions"],
        analysis["fy_summary"],
        tax_slab_pct=tax_slab_pct
    )

    dtaa = DTAAReconciler.generate_form_67_schedule(
        analysis["dividends"],
        tax_slab_pct=tax_slab_pct
    )

    # 1. UCITS ETF & Estate Tax Shielding Analysis
    ucits_data = UCITSOptimizer.analyze_portfolio(analysis["open_positions"])

    # 2. Multi-Jurisdiction Global Comparison
    total_gain_usd = sum(f.get("gain_usd", 0.0) for f in analysis["fy_summary"].values())
    portfolio_val_usd = analysis["portfolio_totals"].get("current_val_usd", 0.0)
    raw_trades = [{"date": t.date.isoformat(), "symbol": t.symbol, "action": t.action, "quantity": t.quantity, "price_usd": t.price_usd} for t in trades]
    uk_data = GlobalTaxEngine.calculate_uk_hmrc_pooling(raw_trades)
    jurisdiction_comps = GlobalTaxEngine.get_jurisdiction_comparison(portfolio_val_usd, total_gain_usd)

    analysis["tax_loss_harvest"] = harvest
    analysis["dtaa"] = dtaa
    analysis["ucits_optimization"] = ucits_data
    analysis["uk_hmrc"] = uk_data
    analysis["jurisdiction_comparisons"] = jurisdiction_comps
    analysis["global_jurisdictions"] = GlobalTaxEngine.JURISDICTIONS
    analysis["benchmark"] = TaxAlphaFinancialBenchmark.evaluate(analysis, tax_slab_pct=tax_slab_pct)
    analysis["tax_slab_pct"] = tax_slab_pct
    analysis["selected_fy"] = selected_fy or "ALL"
    analysis["total_trades_ingested"] = len(trades)

    return analysis

@app.route("/", methods=["GET"])
def index():
    """Serves the single-page application frontend."""
    return send_from_directory(STATIC_DIR, "index.html")

@app.route("/docs/", methods=["GET"])
@app.route("/docs/<path:filename>", methods=["GET"])
def docs_proxy(filename="index.html"):
    """Serves the standalone zero-install interactive showcase."""
    docs_dir = os.path.join(BASE_DIR, "docs")
    return send_from_directory(docs_dir, filename)

@app.route("/<path:path>", methods=["GET"])
def static_proxy(path):
    """Serves static assets if needed."""
    if os.path.exists(os.path.join(STATIC_DIR, path)):
        return send_from_directory(STATIC_DIR, path)
    return send_from_directory(STATIC_DIR, "index.html")

@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "Paasa TaxAlpha Engine",
        "version": "1.0.0",
        "environment": "local-first",
        "timestamp": datetime.now().isoformat()
    })

@app.route("/api/sample", methods=["GET"])
def get_sample_analysis():
    """
    Runs the calculation engine against paasa/data/sample_portfolio_ibkr.csv.
    Accepts optional query params: tax_slab (float), fy (string).
    """
    try:
        tax_slab = float(request.args.get("tax_slab", 30.0))
        selected_fy = request.args.get("fy", "ALL")

        if not os.path.exists(SAMPLE_CSV_PATH):
            return jsonify({"success": False, "error": f"Sample file not found at {SAMPLE_CSV_PATH}"}), 404

        analysis = run_pipeline(SAMPLE_CSV_PATH, tax_slab_pct=tax_slab, selected_fy=selected_fy)

        latest_analysis_cache["data"] = analysis
        latest_analysis_cache["timestamp"] = datetime.now()
        latest_analysis_cache["filename"] = "sample_portfolio_ibkr.csv"

        return jsonify({
            "success": True,
            "source": "sample_portfolio_ibkr.csv",
            "data": analysis
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/benchmark", methods=["GET"])
def get_benchmark():
    """
    Returns the comprehensive financial alpha performance benchmark
    and engine throughput telemetry across Python and V8 runtimes.
    """
    try:
        tax_slab = float(request.args.get("tax_slab", 30.0))
        selected_fy = request.args.get("fy", "ALL")

        # Run pipeline on sample portfolio to extract financial benchmark
        analysis = run_pipeline(SAMPLE_CSV_PATH, tax_slab_pct=tax_slab, selected_fy=selected_fy)
        financial_bench = TaxAlphaFinancialBenchmark.evaluate(analysis, tax_slab_pct=tax_slab)

        # Run micro-throughput benchmark
        throughput = EngineThroughputBenchmark.run_all()

        return jsonify({
            "success": True,
            "financial_benchmark": financial_bench,
            "engine_throughput": throughput,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/analyze", methods=["POST"])
def analyze_portfolio():
    """
    Accepts an uploaded CSV file or raw CSV text, runs the core engine,
    and returns the comprehensive JSON analysis.
    """
    try:
        tax_slab = float(request.form.get("tax_slab") or request.args.get("tax_slab") or 30.0)
        selected_fy = request.form.get("fy") or request.args.get("fy") or "ALL"

        filename = "uploaded_trades.csv"
        csv_content = None

        if "file" in request.files:
            file = request.files["file"]
            filename = file.filename or "uploaded_trades.csv"
            csv_content = file.read().decode("utf-8-sig", errors="replace")
        elif "csv" in request.files:
            file = request.files["csv"]
            filename = file.filename or "uploaded_trades.csv"
            csv_content = file.read().decode("utf-8-sig", errors="replace")
        elif request.is_json:
            data = request.get_json()
            csv_content = data.get("csv_text") or data.get("csv")
            tax_slab = float(data.get("tax_slab", tax_slab))
            selected_fy = data.get("fy", selected_fy)
            filename = data.get("filename", "uploaded_trades.csv")
        elif request.data:
            csv_content = request.data.decode("utf-8-sig", errors="replace")

        if not csv_content or not csv_content.strip():
            return jsonify({"success": False, "error": "No CSV trade data received. Please provide a file or raw CSV text."}), 400

        analysis = run_pipeline(csv_content, tax_slab_pct=tax_slab, selected_fy=selected_fy)

        latest_analysis_cache["data"] = analysis
        latest_analysis_cache["timestamp"] = datetime.now()
        latest_analysis_cache["filename"] = filename

        return jsonify({
            "success": True,
            "source": filename,
            "data": analysis
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/export", methods=["GET"])
def export_report():
    """
    Generates and streams a downloadable CA-ready Excel workbook or CSV summary.
    Query params: format=excel|csv (default: excel), fy=ALL|FY 2024-25|FY 2025-26
    """
    try:
        fmt = request.args.get("format", "excel").lower()
        selected_fy = request.args.get("fy", "ALL")
        tax_slab = float(request.args.get("tax_slab", 30.0))

        # Use cached analysis or run fresh on sample data
        analysis = latest_analysis_cache.get("data")
        if not analysis:
            analysis = run_pipeline(SAMPLE_CSV_PATH, tax_slab_pct=tax_slab, selected_fy=selected_fy)
            latest_analysis_cache["data"] = analysis

        fy_suffix = selected_fy.replace(" ", "_") if selected_fy != "ALL" else "Consolidated"

        if fmt == "csv":
            csv_str = ReportExporter.export_csv(analysis, selected_fy=selected_fy)
            filename = f"Paasa_TaxAlpha_CA_Report_{fy_suffix}.csv"
            return Response(
                csv_str,
                mimetype="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            excel_stream = ReportExporter.export_excel(analysis, selected_fy=selected_fy)
            filename = f"Paasa_TaxAlpha_CA_Report_{fy_suffix}.xlsx"
            return send_file(
                excel_stream,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name=filename
            )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def open_browser_tab(url):
    webbrowser.open(url)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Paasa TaxAlpha Local Engine")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind server (default: 5000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser on launch")
    args = parser.parse_args()

    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    local_url = f"http://{args.host}:{args.port}"

    print("\n" + "=" * 76)
    print("  [+] PAASA TAXALPHA ENGINE - LOCAL-FIRST DUAL-CALENDAR TAX OPTIMIZER")
    print("  YC S24 Portfolio Project | Built for Nitish Sahni & Sparsh Sharma")
    print("=" * 76)
    print(f"  * Web Dashboard  : {local_url}")
    print(f"  * API Health     : {local_url}/api/health")
    print(f"  * Sample Analysis: {local_url}/api/sample")
    print(f"  * CA Export      : {local_url}/api/export?format=excel")
    print("  * Rule 115 Rates : Bundled SBI TT Historical DB (2021-2026)")
    print("  * Wash-Sale Rule : Active ETF Substitution Matrix Loaded")
    print("=" * 76 + "\n")

    if not args.no_browser:
        threading.Timer(1.2, open_browser_tab, args=[local_url]).start()

    app.run(host=args.host, port=args.port, debug=False)
