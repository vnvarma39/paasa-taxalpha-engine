/**
 * Paasa TaxAlpha Engine: Global Multi-Jurisdiction Engine (TypeScript)
 * --------------------------------------------------------------------
 * Implements UK HMRC Section 104 Share Pooling (TCGA 1992 s104) and
 * cross-border tax comparison across India, UK, US, and UAE/Singapore.
 */

import type { TradeRecord, JurisdictionTaxProfile } from "./types.ts";

export interface UKSharePoolItem {
  symbol: string;
  totalQuantity: number;
  totalAllowableCostGbp: number;
  averageCostPerShareGbp: number;
}

export class GlobalTaxEngineTS {
  /**
   * Models UK HMRC Section 104 Share Pooling.
   * Under UK law, shares of the same class form an ongoing pool with an average cost basis.
   */
  static calculateUkHmrcPooling(trades: TradeRecord[], usdGbpRate: number = 0.79): {
    pools: Record<string, UKSharePoolItem>;
    totalRealizedGainGbp: number;
    annualExemptAmountGbp: number;
    taxableGainGbp: number;
    estimatedCgtGbp: number;
  } {
    const pools: Record<string, UKSharePoolItem> = {};
    let totalRealizedGainGbp = 0;

    const sorted = [...trades].sort((a, b) => a.date.localeCompare(b.date));

    for (const t of sorted) {
      if (!pools[t.symbol]) {
        pools[t.symbol] = {
          symbol: t.symbol,
          totalQuantity: 0,
          totalAllowableCostGbp: 0,
          averageCostPerShareGbp: 0
        };
      }
      const pool = pools[t.symbol];

      if (t.action === "BUY") {
        const costGbp = t.quantity * t.priceUsd * usdGbpRate;
        pool.totalQuantity += t.quantity;
        pool.totalAllowableCostGbp += costGbp;
        pool.averageCostPerShareGbp = pool.totalQuantity > 0 ? pool.totalAllowableCostGbp / pool.totalQuantity : 0;
      } else if (t.action === "SELL") {
        if (pool.totalQuantity > 0) {
          const disposedQty = Math.min(t.quantity, pool.totalQuantity);
          const allowableCostDisposed = disposedQty * pool.averageCostPerShareGbp;
          const proceedsGbp = disposedQty * t.priceUsd * usdGbpRate;
          const gainGbp = proceedsGbp - allowableCostDisposed;

          totalRealizedGainGbp += gainGbp;

          pool.totalQuantity -= disposedQty;
          pool.totalAllowableCostGbp -= allowableCostDisposed;
          pool.averageCostPerShareGbp = pool.totalQuantity > 0 ? pool.totalAllowableCostGbp / pool.totalQuantity : 0;
        }
      }
    }

    const annualExemptAmountGbp = 3000.0; // Current HMRC Capital Gains Exemption
    const taxableGainGbp = Math.max(0, totalRealizedGainGbp - annualExemptAmountGbp);
    const estimatedCgtGbp = taxableGainGbp * 0.20; // 20% higher rate UK CGT

    return {
      pools,
      totalRealizedGainGbp: Math.round(totalRealizedGainGbp * 100) / 100,
      annualExemptAmountGbp,
      taxableGainGbp: Math.round(taxableGainGbp * 100) / 100,
      estimatedCgtGbp: Math.round(estimatedCgtGbp * 100) / 100
    };
  }

  static getJurisdictionProfiles(portfolioValUsd: number, totalGainUsd: number): JurisdictionTaxProfile[] {
    return [
      {
        jurisdiction: "India (ITR-2)",
        countryCode: "IN",
        governingLaw: "Income Tax Act, 1961 (Rule 115, Sec 70)",
        fiscalYear: "April 1 - March 31",
        capitalGainsTaxRate: "12.5% LTCG / Slab STCG",
        lossCarryforwardYears: 8,
        usEstateTaxShielded: false,
        estimatedTaxPayableUsd: Math.round(totalGainUsd * 0.125 * 100) / 100
      },
      {
        jurisdiction: "United Kingdom (HMRC)",
        countryCode: "GB",
        governingLaw: "Taxation of Chargeable Gains Act 1992 (s104 Pooling)",
        fiscalYear: "April 6 - April 5",
        capitalGainsTaxRate: "20% (over £3k exemption)",
        lossCarryforwardYears: 4,
        usEstateTaxShielded: false,
        estimatedTaxPayableUsd: Math.round(Math.max(0, totalGainUsd - 3800) * 0.20 * 100) / 100
      },
      {
        jurisdiction: "United States (IRS)",
        countryCode: "US",
        governingLaw: "Internal Revenue Code (IRC Sec 1091 Wash-Sale)",
        fiscalYear: "January 1 - December 31",
        capitalGainsTaxRate: "15-20% Long / 37% Short",
        lossCarryforwardYears: 99,
        usEstateTaxShielded: false,
        estimatedTaxPayableUsd: Math.round(totalGainUsd * 0.15 * 100) / 100
      },
      {
        jurisdiction: "UAE / Singapore",
        countryCode: "AE",
        governingLaw: "Territorial 0% CGT Regime",
        fiscalYear: "January 1 - December 31",
        capitalGainsTaxRate: "0% (Tax-Free)",
        lossCarryforwardYears: 0,
        usEstateTaxShielded: true,
        estimatedTaxPayableUsd: 0.0
      }
    ];
  }
}
