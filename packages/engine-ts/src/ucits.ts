/**
 * Paasa TaxAlpha Engine: UCITS & US Estate Tax Optimizer (TypeScript)
 * -------------------------------------------------------------------
 * Analyzes US-domiciled vs Irish-domiciled UCITS ETFs:
 * 1. 15% vs 30% dividend withholding tax arbitrage (US-Ireland tax treaty).
 * 2. 40% US federal estate tax risk on non-resident aliens (assets > $60k).
 */

import type { OpenLotPosition, UCITSArbitrageResult } from "./types.ts";

export const UCITS_EQUIVALENCE_MAPPING: Record<string, {
  ucitsSymbol: string;
  name: string;
  exchange: string;
  currency: string;
  terPct: number;
  estYieldPct: number;
}> = {
  "VOO": { ucitsSymbol: "CSPX / VUAA", name: "iShares Core S&P 500 UCITS", exchange: "LSE (London)", currency: "USD", terPct: 0.07, estYieldPct: 1.35 },
  "SPY": { ucitsSymbol: "CSPX / SPY5", name: "iShares / SPDR S&P 500 UCITS", exchange: "LSE (London)", currency: "USD", terPct: 0.07, estYieldPct: 1.35 },
  "QQQ": { ucitsSymbol: "CNDX / EQQQ", name: "iShares / Invesco Nasdaq 100 UCITS", exchange: "LSE (London)", currency: "USD", terPct: 0.30, estYieldPct: 0.60 },
  "VT":  { ucitsSymbol: "VWRA / SSAC", name: "Vanguard FTSE All-World UCITS", exchange: "LSE (London)", currency: "USD", terPct: 0.22, estYieldPct: 1.80 }
};

export class UCITSOptimizerTS {
  static analyze(openPositions: OpenLotPosition[]): {
    results: UCITSArbitrageResult[];
    totalPortfolioValUsd: number;
    totalUsSitusExposedUsd: number;
    totalUsEstateTaxLiabilityUsd: number;
    totalAnnualDividendTaxSavedUsd: number;
  } {
    const results: UCITSArbitrageResult[] = [];
    let totalPortfolioValUsd = 0;
    let totalAnnualDividendTaxSavedUsd = 0;

    for (const pos of openPositions) {
      totalPortfolioValUsd += pos.currentValUsd;
      const mapping = UCITS_EQUIVALENCE_MAPPING[pos.symbol];
      if (mapping) {
        // Dividend WHT rate difference: 30% standard (or 25% DTAA) down to 15% Irish fund level = 10% to 15% saving
        const annualGrossDiv = pos.currentValUsd * (mapping.estYieldPct / 100.0);
        const whtSaved = annualGrossDiv * 0.15; // 15% saved on dividend yield

        // US Estate Tax exposure (if portfolio exceeds $60k threshold)
        const estateRisk = Math.max(0, pos.currentValUsd - 60000) * 0.40;

        results.push({
          holding: pos.symbol,
          ucitsEquivalent: mapping.ucitsSymbol,
          exchange: mapping.exchange,
          dividendWhtArbitrageBps: 150.0,
          annualDividendSavedUsd: Math.round(whtSaved * 100) / 100,
          usEstateTaxExposureUsd: Math.round(estateRisk * 100) / 100,
          usEstateTaxShieldedUsd: Math.round(estateRisk * 100) / 100
        });

        totalAnnualDividendTaxSavedUsd += whtSaved;
      }
    }

    const totalUsSitusExposedUsd = Math.max(0, totalPortfolioValUsd - 60000);
    const totalUsEstateTaxLiabilityUsd = totalUsSitusExposedUsd * 0.40;

    return {
      results,
      totalPortfolioValUsd: Math.round(totalPortfolioValUsd * 100) / 100,
      totalUsSitusExposedUsd: Math.round(totalUsSitusExposedUsd * 100) / 100,
      totalUsEstateTaxLiabilityUsd: Math.round(totalUsEstateTaxLiabilityUsd * 100) / 100,
      totalAnnualDividendTaxSavedUsd: Math.round(totalAnnualDividendTaxSavedUsd * 100) / 100
    };
  }
}
