/**
 * Paasa TaxAlpha Engine: FIFO Lot Matching & Budget 2024 Engine (TypeScript)
 * --------------------------------------------------------------------------
 * Matches sell orders against historical buy lots using strict FIFO.
 * Categorizes gains under Section 2(42A) Budget 2024:
 * - Holding > 24 months = LTCG @ 12.5% (flat)
 * - Holding <= 24 months = STCG @ applicable slab (20%, 30%, 39%)
 */

import type { TradeRecord, MatchedFIFOTrade, OpenLotPosition, CapitalGainsTerm } from "./types.ts";
import { Rule115CurrencyConverter } from "./currency.ts";

export class FIFOTaxEngine {
  private fx: Rule115CurrencyConverter;

  constructor(customFx?: Rule115CurrencyConverter) {
    this.fx = customFx || new Rule115CurrencyConverter();
  }

  getIndianFinancialYear(dateStr: string): string {
    const d = new Date(dateStr.slice(0, 10));
    const year = d.getUTCFullYear();
    const month = d.getUTCMonth() + 1; // 1-12
    if (month >= 4) {
      return `FY ${year}-${(year + 1).toString().slice(2)}`;
    } else {
      return `FY ${year - 1}-${year.toString().slice(2)}`;
    }
  }

  calculate(trades: TradeRecord[], taxSlabPct: number = 30.0, currentMarketPrices?: Record<string, number>): {
    matchedTrades: MatchedFIFOTrade[];
    openPositions: OpenLotPosition[];
    totalGainInr: number;
    totalTaxInr: number;
    fySummaries: Record<string, { totalGainInr: number; totalTaxInr: number; tradesCount: number }>;
  } {
    const sorted = [...trades].sort((a, b) => a.date.localeCompare(b.date));
    const buyQueues: Record<string, Array<{ trade: TradeRecord; remQty: number }>> = {};
    const matched: MatchedFIFOTrade[] = [];

    const defaultPrices: Record<string, number> = {
      "VOO": 515.20, "QQQ": 478.50, "NVDA": 128.40, "AMD": 118.25,
      "TSLA": 210.50, "AAPL": 224.30, "MSFT": 448.50, "AMZN": 186.40,
      ...currentMarketPrices
    };

    for (const t of sorted) {
      if (t.action === "BUY") {
        if (!buyQueues[t.symbol]) buyQueues[t.symbol] = [];
        buyQueues[t.symbol].push({ trade: t, remQty: t.quantity });
      } else if (t.action === "SELL") {
        let sellRem = t.quantity;
        const queue = buyQueues[t.symbol] || [];

        while (sellRem > 0.00001 && queue.length > 0) {
          const buyLot = queue[0];
          const matchedQty = Math.min(sellRem, buyLot.remQty);

          const buyDt = new Date(buyLot.trade.date);
          const sellDt = new Date(t.date);
          const holdingDays = Math.max(1, Math.round((sellDt.getTime() - buyDt.getTime()) / (1000 * 60 * 60 * 24)));
          const holdingMonths = Math.round((holdingDays / 30.4375) * 10) / 10;
          const isLtcg = holdingMonths > 24.0;
          const term: CapitalGainsTerm = isLtcg ? "LTCG" : "STCG";

          const buyFx = this.fx.getRule115Rate(buyLot.trade.date);
          const sellFx = this.fx.getRule115Rate(t.date);

          const costBasisUsd = matchedQty * buyLot.trade.priceUsd;
          const proceedsUsd = matchedQty * t.priceUsd;
          const gainUsd = proceedsUsd - costBasisUsd;

          const costBasisInr = costBasisUsd * buyFx;
          const proceedsInr = proceedsUsd * sellFx;
          const gainInr = proceedsInr - costBasisInr;

          const decomp = this.fx.decomposeReturn(costBasisUsd, proceedsUsd, buyLot.trade.date, t.date);

          const taxRate = isLtcg ? 12.5 : taxSlabPct;
          const estimatedTaxInr = gainInr > 0 ? (gainInr * taxRate) / 100.0 : 0.0;

          matched.push({
            buyTradeId: buyLot.trade.tradeId,
            sellTradeId: t.tradeId,
            symbol: t.symbol,
            assetType: t.assetType,
            quantity: Math.round(matchedQty * 10000) / 10000,
            buyDate: buyLot.trade.date,
            sellDate: t.date,
            holdingDays,
            holdingMonths,
            term,
            costBasisUsd: Math.round(costBasisUsd * 100) / 100,
            proceedsUsd: Math.round(proceedsUsd * 100) / 100,
            gainUsd: Math.round(gainUsd * 100) / 100,
            buyFxRate: buyFx,
            sellFxRate: sellFx,
            costBasisInr: Math.round(costBasisInr * 100) / 100,
            proceedsInr: Math.round(proceedsInr * 100) / 100,
            gainInr: Math.round(gainInr * 100) / 100,
            assetGrowthUsd: decomp.assetGainUsd,
            currencyDriftInr: decomp.currencyGainInr,
            applicableTaxRatePct: taxRate,
            estimatedTaxInr: Math.round(estimatedTaxInr * 100) / 100,
            indianFy: this.getIndianFinancialYear(t.date)
          });

          buyLot.remQty -= matchedQty;
          sellRem -= matchedQty;

          if (buyLot.remQty <= 0.00001) {
            queue.shift();
          }
        }
      }
    }

    // Open Positions
    const openPositions: OpenLotPosition[] = [];
    const currentDateStr = new Date().toISOString().slice(0, 10);
    const currentFx = this.fx.getRule115Rate(currentDateStr);

    for (const [sym, queue] of Object.entries(buyQueues)) {
      for (const item of queue) {
        if (item.remQty <= 0.00001) continue;
        const currPrice = defaultPrices[sym] || item.trade.priceUsd * 1.05;
        const buyFx = this.fx.getRule115Rate(item.trade.date);

        const costUsd = item.remQty * item.trade.priceUsd;
        const currValUsd = item.remQty * currPrice;
        const costInr = costUsd * buyFx;
        const currValInr = currValUsd * currentFx;

        const pnlUsd = currValUsd - costUsd;
        const pnlInr = currValInr - costInr;
        const pnlPct = item.trade.priceUsd > 0 ? ((currPrice - item.trade.priceUsd) / item.trade.priceUsd) * 100 : 0;

        const buyDt = new Date(item.trade.date);
        const nowDt = new Date(currentDateStr);
        const holdingDays = Math.max(1, Math.round((nowDt.getTime() - buyDt.getTime()) / (1000 * 60 * 60 * 24)));
        const holdingMonths = Math.round((holdingDays / 30.4375) * 10) / 10;
        const term: CapitalGainsTerm = holdingMonths > 24.0 ? "LTCG" : "STCG";

        openPositions.push({
          lotId: item.trade.tradeId,
          symbol: sym,
          assetType: item.trade.assetType,
          buyDate: item.trade.date,
          quantity: Math.round(item.remQty * 10000) / 10000,
          buyPriceUsd: item.trade.priceUsd,
          currentPriceUsd: currPrice,
          buyFxRate: buyFx,
          currentFxRate: currentFx,
          costBasisUsd: Math.round(costUsd * 100) / 100,
          currentValUsd: Math.round(currValUsd * 100) / 100,
          costBasisInr: Math.round(costInr * 100) / 100,
          currentValInr: Math.round(currValInr * 100) / 100,
          unrealizedPnlUsd: Math.round(pnlUsd * 100) / 100,
          unrealizedPnlInr: Math.round(pnlInr * 100) / 100,
          unrealizedPnlPct: Math.round(pnlPct * 100) / 100,
          holdingDays,
          holdingMonths,
          term,
          isLoss: pnlInr < 0
        });
      }
    }

    // Rollups
    let totalGainInr = 0;
    let totalTaxInr = 0;
    const fySummaries: Record<string, { totalGainInr: number; totalTaxInr: number; tradesCount: number }> = {};

    for (const m of matched) {
      totalGainInr += m.gainInr;
      totalTaxInr += m.estimatedTaxInr;

      if (!fySummaries[m.indianFy]) {
        fySummaries[m.indianFy] = { totalGainInr: 0, totalTaxInr: 0, tradesCount: 0 };
      }
      fySummaries[m.indianFy].totalGainInr += m.gainInr;
      fySummaries[m.indianFy].totalTaxInr += m.estimatedTaxInr;
      fySummaries[m.indianFy].tradesCount += 1;
    }

    return {
      matchedTrades: matched,
      openPositions,
      totalGainInr: Math.round(totalGainInr * 100) / 100,
      totalTaxInr: Math.round(totalTaxInr * 100) / 100,
      fySummaries
    };
  }
}
