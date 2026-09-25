/**
 * Paasa TaxAlpha Engine: Rule 115 Currency Converter (TypeScript)
 * ---------------------------------------------------------------
 * Implements Rule 115 of the Indian Income Tax Rules, 1962:
 * Foreign currency gains must convert to INR using the SBI TT Buying Rate
 * as on the last day of the calendar month immediately preceding the transaction.
 */

export const SBI_TT_HISTORICAL_DB: Record<string, number> = {
  "2021-01": 72.85, "2021-02": 73.10, "2021-03": 73.40, "2021-04": 74.20,
  "2021-05": 73.90, "2021-06": 74.30, "2021-07": 74.45, "2021-08": 73.80,
  "2021-09": 74.15, "2021-10": 74.90, "2021-11": 74.85, "2021-12": 74.50,
  "2022-01": 74.70, "2022-02": 75.10, "2022-03": 75.80, "2022-04": 76.40,
  "2022-05": 77.60, "2022-06": 78.30, "2022-07": 79.25, "2022-08": 79.80,
  "2022-09": 81.30, "2022-10": 82.20, "2022-11": 81.65, "2022-12": 82.70,
  "2023-01": 81.80, "2023-02": 82.60, "2023-03": 82.15, "2023-04": 81.90,
  "2023-05": 82.45, "2023-06": 82.05, "2023-07": 82.25, "2023-08": 82.70,
  "2023-09": 83.10, "2023-10": 83.25, "2023-11": 83.30, "2023-12": 83.15,
  "2024-01": 83.05, "2024-02": 82.90, "2024-03": 83.35, "2024-04": 83.40,
  "2024-05": 83.30, "2024-06": 83.45, "2024-07": 83.65, "2024-08": 83.85,
  "2024-09": 83.75, "2024-10": 84.05, "2024-11": 84.45, "2024-12": 84.85,
  "2025-01": 86.20, "2025-02": 86.60, "2025-03": 86.95, "2025-04": 87.10,
  "2025-05": 87.25, "2025-06": 87.40, "2025-07": 87.65, "2025-08": 87.90,
  "2025-09": 88.00, "2025-10": 88.10, "2025-11": 88.15, "2025-12": 88.20,
  "2026-01": 88.50, "2026-02": 88.75, "2026-03": 89.10
};

export class Rule115CurrencyConverter {
  private rates: Record<string, number>;

  constructor(customRates?: Record<string, number>) {
    this.rates = customRates || SBI_TT_HISTORICAL_DB;
  }

  getPrecedingMonthKey(dateInput: string | Date): string {
    const d = typeof dateInput === "string" ? new Date(dateInput.slice(0, 10)) : dateInput;
    let year = d.getUTCFullYear();
    let month = d.getUTCMonth(); // 0-indexed: 0 = Jan, so previous month is month - 1 + 1 = month

    if (month === 0) {
      month = 12;
      year -= 1;
    }
    return `${year.toString().padStart(4, "0")}-${month.toString().padStart(2, "0")}`;
  }

  getRule115Rate(dateInput: string | Date): number {
    const key = this.getPrecedingMonthKey(dateInput);
    if (this.rates[key]) return this.rates[key];

    const sortedKeys = Object.keys(this.rates).sort();
    if (key < sortedKeys[0]) return this.rates[sortedKeys[0]];
    if (key > sortedKeys[sortedKeys.length - 1]) return this.rates[sortedKeys[sortedKeys.length - 1]];

    for (let i = 0; i < sortedKeys.length - 1; i++) {
      if (key >= sortedKeys[i] && key <= sortedKeys[i + 1]) {
        return this.rates[sortedKeys[i + 1]];
      }
    }
    return 89.10;
  }

  decomposeReturn(
    costBasisUsd: number,
    proceedsUsd: number,
    buyDate: string,
    sellDate: string
  ): {
    totalReturnInr: number;
    assetGainUsd: number;
    assetGainInr: number;
    currencyGainInr: number;
    effectiveFxAppreciationPct: number;
  } {
    const buyFx = this.getRule115Rate(buyDate);
    const sellFx = this.getRule115Rate(sellDate);

    const costBasisInr = costBasisUsd * buyFx;
    const proceedsInr = proceedsUsd * sellFx;
    const totalReturnInr = proceedsInr - costBasisInr;

    const assetGainUsd = proceedsUsd - costBasisUsd;
    const assetGainInr = assetGainUsd * buyFx;
    const currencyGainInr = proceedsUsd * (sellFx - buyFx);

    const fxAppreciationPct = buyFx > 0 ? ((sellFx - buyFx) / buyFx) * 100 : 0;

    return {
      totalReturnInr: Math.round(totalReturnInr * 100) / 100,
      assetGainUsd: Math.round(assetGainUsd * 100) / 100,
      assetGainInr: Math.round(assetGainInr * 100) / 100,
      currencyGainInr: Math.round(currencyGainInr * 100) / 100,
      effectiveFxAppreciationPct: Math.round(fxAppreciationPct * 100) / 100
    };
  }
}
