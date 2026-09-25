/**
 * Paasa TaxAlpha Engine: Domain Type Definitions (TypeScript)
 * -----------------------------------------------------------
 * Strongly-typed domain models for cross-border tax calculation,
 * Rule 115 FX normalization, FIFO lot matching, and UCITS arbitrage.
 */

export type AssetType = "EQUITY" | "ETF";
export type TradeAction = "BUY" | "SELL" | "DIVIDEND";
export type CapitalGainsTerm = "LTCG" | "STCG";

export interface TradeRecord {
  tradeId: number;
  date: string; // YYYY-MM-DD
  symbol: string;
  assetType: AssetType;
  action: TradeAction;
  quantity: number;
  priceUsd: number;
  feesUsd: number;
  withholdingTaxUsd?: number;
  notes?: string;
}

export interface MatchedFIFOTrade {
  buyTradeId: number;
  sellTradeId: number;
  symbol: string;
  assetType: AssetType;
  quantity: number;
  buyDate: string;
  sellDate: string;
  holdingDays: number;
  holdingMonths: number;
  term: CapitalGainsTerm;
  costBasisUsd: number;
  proceedsUsd: number;
  gainUsd: number;
  buyFxRate: number;
  sellFxRate: number;
  costBasisInr: number;
  proceedsInr: number;
  gainInr: number;
  assetGrowthUsd: number;
  currencyDriftInr: number;
  applicableTaxRatePct: number;
  estimatedTaxInr: number;
  indianFy: string;
}

export interface OpenLotPosition {
  lotId: number;
  symbol: string;
  assetType: AssetType;
  buyDate: string;
  quantity: number;
  buyPriceUsd: number;
  currentPriceUsd: number;
  buyFxRate: number;
  currentFxRate: number;
  costBasisUsd: number;
  currentValUsd: number;
  costBasisInr: number;
  currentValInr: number;
  unrealizedPnlUsd: number;
  unrealizedPnlInr: number;
  unrealizedPnlPct: number;
  holdingDays: number;
  holdingMonths: number;
  term: CapitalGainsTerm;
  isLoss: boolean;
}

export interface WashSaleSubstitute {
  symbol: string;
  name: string;
  correlation: number;
  expenseRatio: string;
  rationale: string;
  substitutePriceUsd: number;
  rebalanceQuantity: number;
}

export interface HarvestRecommendation {
  lotId: number;
  symbol: string;
  assetType: AssetType;
  buyDate: string;
  quantity: number;
  buyPriceUsd: number;
  currentPriceUsd: number;
  lossUsd: number;
  lossInr: number;
  lossPct: number;
  term: CapitalGainsTerm;
  applicableTaxRate: number;
  potentialTaxSavedInr: number;
  substitute: WashSaleSubstitute;
  actionTicket: string;
}

export interface DTAAReliefClaim {
  totalGrossDividendsUsd: number;
  totalGrossDividendsInr: number;
  usWithholdingTaxUsd: number;
  usWithholdingTaxInr: number;
  indianTaxLiabilityInr: number;
  section90CreditReliefInr: number;
  netIndianTaxPayableInr: number;
}

export interface UCITSArbitrageResult {
  holding: string;
  ucitsEquivalent: string;
  exchange: string;
  dividendWhtArbitrageBps: number;
  annualDividendSavedUsd: number;
  usEstateTaxExposureUsd: number;
  usEstateTaxShieldedUsd: number;
}

export interface JurisdictionTaxProfile {
  jurisdiction: string;
  countryCode: string;
  governingLaw: string;
  fiscalYear: string;
  capitalGainsTaxRate: string;
  lossCarryforwardYears: number;
  usEstateTaxShielded: boolean;
  estimatedTaxPayableUsd: number;
}
