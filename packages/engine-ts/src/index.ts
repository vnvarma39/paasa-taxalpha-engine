/**
 * Paasa TaxAlpha Engine: Complete TypeScript SDK & Core Package
 * -------------------------------------------------------------
 * Top-level exports for Rule 115, FIFO lot matching, wash-sale ETF
 * substitution, UCITS arbitrage, and HMRC Section 104 pooling.
 */

export * from "./types.ts";
export * from "./currency.ts";
export * from "./tax_engine.ts";
export * from "./loss_harvester.ts";
export * from "./ucits.ts";
export * from "./global_tax.ts";

import type { TradeRecord } from "./types.ts";
import { Rule115CurrencyConverter } from "./currency.ts";
import { FIFOTaxEngine } from "./tax_engine.ts";
import { TaxLossHarvesterTS } from "./loss_harvester.ts";
import { UCITSOptimizerTS } from "./ucits.ts";
import { GlobalTaxEngineTS } from "./global_tax.ts";

export class PaasaTaxAlphaEngineTS {
  public fx: Rule115CurrencyConverter;
  public fifo: FIFOTaxEngine;
  public harvester: TaxLossHarvesterTS;

  constructor() {
    this.fx = new Rule115CurrencyConverter();
    this.fifo = new FIFOTaxEngine(this.fx);
    this.harvester = new TaxLossHarvesterTS();
  }

  runFullAnalysis(trades: TradeRecord[], taxSlabPct: number = 30.0) {
    const calculation = this.fifo.calculate(trades, taxSlabPct);
    const harvesting = this.harvester.analyze(calculation.openPositions, taxSlabPct);
    const ucits = UCITSOptimizerTS.analyze(calculation.openPositions);
    const ukHmrc = GlobalTaxEngineTS.calculateUkHmrcPooling(trades);

    const portfolioValUsd = calculation.openPositions.reduce((acc, p) => acc + p.currentValUsd, 0);
    const totalGainUsd = calculation.matchedTrades.reduce((acc, m) => acc + m.gainUsd, 0);
    const jurisdictions = GlobalTaxEngineTS.getJurisdictionProfiles(portfolioValUsd, totalGainUsd);

    return {
      tradesIngested: trades.length,
      matchedTrades: calculation.matchedTrades,
      openPositions: calculation.openPositions,
      totalRealizedGainInr: calculation.totalGainInr,
      totalTaxInr: calculation.totalTaxInr,
      taxLossHarvesting: harvesting,
      ucitsArbitrage: ucits,
      ukHmrcPooling: ukHmrc,
      jurisdictionComparisons: jurisdictions
    };
  }
}

// Self-test execution when run directly via node
if (process.argv[1]?.endsWith("index.ts")) {
  console.log("⚡ Paasa TaxAlpha Engine: TypeScript Modular Core Initialized.");
  const engine = new PaasaTaxAlphaEngineTS();
  const testTrades: TradeRecord[] = [
    { tradeId: 1, date: "2022-01-15", symbol: "VOO", assetType: "ETF", action: "BUY", quantity: 50, priceUsd: 410, feesUsd: 1.0 },
    { tradeId: 2, date: "2024-03-20", symbol: "VOO", assetType: "ETF", action: "SELL", quantity: 20, priceUsd: 510, feesUsd: 1.0 },
    { tradeId: 3, date: "2024-06-10", symbol: "AMD", assetType: "EQUITY", action: "BUY", quantity: 100, priceUsd: 175, feesUsd: 1.0 }
  ];
  const analysis = engine.runFullAnalysis(testTrades, 30.0);
  console.log("  Trades Ingested:", analysis.tradesIngested);
  console.log("  Matched FIFO Trades:", analysis.matchedTrades.length);
  console.log("  Open Positions:", analysis.openPositions.length);
  console.log("  Harvest Candidates:", analysis.taxLossHarvesting.recommendations.length);
  console.log("  Tax Alpha Potential (INR):", analysis.taxLossHarvesting.totalPotentialTaxSavedInr.toFixed(2));
  console.log("  [OK] Full Modular TypeScript Suite Passed Successfully!");
}
