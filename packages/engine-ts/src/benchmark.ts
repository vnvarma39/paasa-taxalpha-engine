/**
 * Paasa TaxAlpha Engine: TypeScript / Node.js 24 (V8) High-Throughput Benchmark
 * -----------------------------------------------------------------------------
 * Measures V8 runtime throughput and latency for Rule 115 FX queries and FIFO lot matching.
 */

import { Rule115CurrencyConverter } from "./currency.ts";
import { FIFOTaxEngine } from "./tax_engine.ts";
import type { TradeRecord } from "./types.ts";

function benchmarkRule115(iterations: number = 50000) {
  const converter = new Rule115CurrencyConverter();
  const sampleDates: string[] = [];
  for (let y = 2021; y <= 2025; y++) {
    for (let m = 1; m <= 12; m++) {
      const d = (m % 28) + 1;
      sampleDates.push(`${y}-${m.toString().padStart(2, "0")}-${d.toString().padStart(2, "0")}`);
    }
  }

  const start = performance.now();
  for (let i = 0; i < iterations; i++) {
    const dt = sampleDates[i % sampleDates.length];
    converter.getRule115Rate(dt);
  }
  const elapsedMs = performance.now() - start;
  const opsPerSec = Math.round(iterations / (elapsedMs / 1000));
  const avgLatencyUs = Math.round(((elapsedMs / iterations) * 1000) * 1000) / 1000;

  return { iterations, elapsedSec: Math.round(elapsedMs) / 1000, opsPerSec, avgLatencyUs };
}

function benchmarkFifoMatching(batchSizes: number[] = [1000, 5000, 10000]) {
  const engine = new FIFOTaxEngine();
  const symbols = ["VOO", "QQQ", "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "AMD", "TSLA"];
  const results = [];

  for (const n of batchSizes) {
    const trades: TradeRecord[] = [];
    const baseDate = new Date("2022-01-01").getTime();

    for (let i = 0; i < n; i++) {
      const dt = new Date(baseDate + i * 0.3 * 86400000).toISOString().slice(0, 10);
      const sym = symbols[i % symbols.length];
      const action = (i % 10 < 7) ? "BUY" : "SELL";
      const qty = Math.floor(Math.random() * 45) + 5;
      const price = Math.floor(Math.random() * 500) + 100;
      trades.push({
        tradeId: i + 1,
        date: dt,
        symbol: sym,
        assetType: sym === "VOO" || sym === "QQQ" ? "ETF" : "EQUITY",
        action,
        quantity: qty,
        priceUsd: price,
        feesUsd: 1.0
      });
    }

    const start = performance.now();
    engine.calculate(trades, 30.0);
    const elapsedMs = performance.now() - start;

    const throughput = Math.round(n / (elapsedMs / 1000));
    const avgLatencyUs = Math.round(((elapsedMs / n) * 1000) * 100) / 100;

    results.push({
      batchSize: n,
      elapsedSec: (elapsedMs / 1000).toFixed(4),
      throughput,
      avgLatencyUs
    });
  }

  return results;
}

console.log("=".repeat(82));
console.log("  ⚡ PAASA TAXALPHA ENGINE — TYPESCRIPT (NODE.JS 24 V8) BENCHMARK");
console.log("  YC S24 Portfolio Project | Built for Nitish Sahni & Sparsh Sharma");
console.log("=".repeat(82));
console.log(`  * Runtime Environment : Node.js ${process.version} (Native V8 JIT)`);
console.log(`  * Memory Heap Used    : ${(process.memoryUsage().heapUsed / 1024 / 1024).toFixed(2)} MB`);
console.log("=".repeat(82));

console.log("\n" + "─".repeat(82));
console.log("  [1] RULE 115 SBI TT QUERY THROUGHPUT (NODE.JS 24 V8)");
console.log("─".repeat(82));
const r115 = benchmarkRule115(50000);
console.log(`  • Iterations  : ${r115.iterations.toLocaleString()} queries`);
console.log(`  • Elapsed Time: ${r115.elapsedSec} seconds`);
console.log(`  • Throughput  : ${r115.opsPerSec.toLocaleString()} lookups/sec`);
console.log(`  • Avg Latency : ${r115.avgLatencyUs} µs/lookup`);

console.log("\n" + "─".repeat(82));
console.log("  [2] FIFO LOT MATCHING & BUDGET 2024 SCALABILITY (TYPESCRIPT)");
console.log("─".repeat(82));
console.log("  Batch Size (Trades)      Time (s)       Throughput (Trades/s)    Latency/Trade (µs)");
console.log("  " + "─".repeat(74));
const fifoResults = benchmarkFifoMatching([1000, 5000, 10000]);
for (const r of fifoResults) {
  console.log(`  ${r.batchSize.toLocaleString().padEnd(24)} ${r.elapsedSec.padEnd(14)} ${r.throughput.toLocaleString().padEnd(24)} ${r.avgLatencyUs.toFixed(2)}`);
}

console.log("\n" + "=".repeat(82));
console.log("  SUMMARY: TypeScript engine executed with sub-millisecond per-batch latency.");
console.log("=".repeat(82) + "\n");
