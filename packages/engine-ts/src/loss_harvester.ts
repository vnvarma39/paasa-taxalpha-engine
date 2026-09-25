/**
 * Paasa TaxAlpha Engine: Algorithmic Loss Harvester (TypeScript)
 * --------------------------------------------------------------
 * Scans open lots for underwater positions, pairs them with correlated
 * substitutes from the Wash-Sale matrix, and calculates net tax savings.
 */

import type { OpenLotPosition, HarvestRecommendation, WashSaleSubstitute } from "./types.ts";

export const CORRELATED_ETF_SUBSTITUTE_MATRIX: Record<string, {
  name: string;
  substitutes: Array<{
    symbol: string;
    name: string;
    correlation: number;
    expenseRatio: string;
    rationale: string;
    estPriceUsd: number;
  }>;
}> = {
  "VOO": {
    name: "Vanguard S&P 500 ETF",
    substitutes: [
      { symbol: "IVV", name: "iShares Core S&P 500", correlation: 0.9992, expenseRatio: "0.03%", rationale: "Identical index tracking without triggering US wash-sale disallowance.", estPriceUsd: 516.80 },
      { symbol: "SPY", name: "SPDR S&P 500 ETF", correlation: 0.9990, expenseRatio: "0.09%", rationale: "High liquidity broad index replacement.", estPriceUsd: 514.90 }
    ]
  },
  "QQQ": {
    name: "Invesco QQQ Trust (Nasdaq 100)",
    substitutes: [
      { symbol: "QQQM", name: "Invesco NASDAQ 100 ETF", correlation: 0.9996, expenseRatio: "0.15%", rationale: "Same index holdings with 5 bps lower expense ratio.", estPriceUsd: 196.40 },
      { symbol: "VGT", name: "Vanguard Information Tech ETF", correlation: 0.9520, expenseRatio: "0.10%", rationale: "Tech-focused mega-cap replacement basket.", estPriceUsd: 545.00 }
    ]
  },
  "NVDA": {
    name: "NVIDIA Corporation",
    substitutes: [
      { symbol: "SMH", name: "VanEck Semiconductor ETF", correlation: 0.8840, expenseRatio: "0.35%", rationale: "Preserves semiconductor alpha with diversified basket.", estPriceUsd: 242.00 },
      { symbol: "SOXX", name: "iShares Semiconductor ETF", correlation: 0.8620, expenseRatio: "0.35%", rationale: "High correlation US semiconductor index.", estPriceUsd: 218.00 }
    ]
  },
  "AMD": {
    name: "Advanced Micro Devices",
    substitutes: [
      { symbol: "SMH", name: "VanEck Semiconductor ETF", correlation: 0.8420, expenseRatio: "0.35%", rationale: "High beta semiconductor exposure preservation.", estPriceUsd: 242.00 },
      { symbol: "NVDA", name: "NVIDIA Corporation", correlation: 0.8250, expenseRatio: "N/A", rationale: "Category leader direct single-stock replacement.", estPriceUsd: 128.40 }
    ]
  },
  "TSLA": {
    name: "Tesla Inc",
    substitutes: [
      { symbol: "ARKK", name: "ARK Innovation ETF", correlation: 0.7850, expenseRatio: "0.75%", rationale: "High TSLA portfolio weighting and disruptive beta.", estPriceUsd: 48.20 },
      { symbol: "CARZ", name: "First Trust NASDAQ Global Auto", correlation: 0.8120, expenseRatio: "0.70%", rationale: "Global EV and automotive industry basket.", estPriceUsd: 52.10 }
    ]
  }
};

export class TaxLossHarvesterTS {
  analyze(openPositions: OpenLotPosition[], taxSlabPct: number = 30.0): {
    recommendations: HarvestRecommendation[];
    totalHarvestableLossUsd: number;
    totalHarvestableLossInr: number;
    totalPotentialTaxSavedInr: number;
  } {
    const recommendations: HarvestRecommendation[] = [];
    let totalHarvestableLossUsd = 0;
    let totalHarvestableLossInr = 0;
    let totalPotentialTaxSavedInr = 0;

    for (const pos of openPositions) {
      if (pos.unrealizedPnlInr >= 0) continue;

      const lossUsd = Math.abs(pos.unrealizedPnlUsd);
      const lossInr = Math.abs(pos.unrealizedPnlInr);
      const taxRate = pos.term === "STCG" ? taxSlabPct : 12.5;
      const potentialSavedInr = Math.round(lossInr * (taxRate / 100.0) * 100) / 100;

      const subMatrix = CORRELATED_ETF_SUBSTITUTE_MATRIX[pos.symbol];
      const primarySub = subMatrix ? subMatrix.substitutes[0] : {
        symbol: "SPY",
        name: "SPDR S&P 500 ETF",
        correlation: 0.85,
        expenseRatio: "0.09%",
        rationale: "Broad market index replacement.",
        estPriceUsd: 514.90
      };

      const rebalanceQty = Math.round(((pos.quantity * pos.currentPriceUsd) / primarySub.estPriceUsd) * 100) / 100;

      const substitute: WashSaleSubstitute = {
        symbol: primarySub.symbol,
        name: primarySub.name,
        correlation: primarySub.correlation,
        expenseRatio: primarySub.expenseRatio,
        rationale: primarySub.rationale,
        substitutePriceUsd: primarySub.estPriceUsd,
        rebalanceQuantity: rebalanceQty
      };

      recommendations.push({
        lotId: pos.lotId,
        symbol: pos.symbol,
        assetType: pos.assetType,
        buyDate: pos.buyDate,
        quantity: pos.quantity,
        buyPriceUsd: pos.buyPriceUsd,
        currentPriceUsd: pos.currentPriceUsd,
        lossUsd,
        lossInr,
        lossPct: Math.abs(pos.unrealizedPnlPct),
        term: pos.term,
        applicableTaxRate: taxRate,
        potentialTaxSavedInr: potentialSavedInr,
        substitute,
        actionTicket: `SELL ${pos.quantity} ${pos.symbol} @ $${pos.currentPriceUsd} & SWAP INTO ~${rebalanceQty} ${substitute.symbol} @ $${substitute.substitutePriceUsd}`
      });

      totalHarvestableLossUsd += lossUsd;
      totalHarvestableLossInr += lossInr;
      totalPotentialTaxSavedInr += potentialSavedInr;
    }

    recommendations.sort((a, b) => b.potentialTaxSavedInr - a.potentialTaxSavedInr);

    return {
      recommendations,
      totalHarvestableLossUsd: Math.round(totalHarvestableLossUsd * 100) / 100,
      totalHarvestableLossInr: Math.round(totalHarvestableLossInr * 100) / 100,
      totalPotentialTaxSavedInr: Math.round(totalPotentialTaxSavedInr * 100) / 100
    };
  }
}
