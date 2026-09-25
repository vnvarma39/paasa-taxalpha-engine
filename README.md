# ⚡ Paasa TaxAlpha Engine
### *Local-First Dual-Calendar Tax-Loss Harvester & DTAA Schedule FA Generator for Global Indian Investors*

> **Built for:** Nitish Sahni (CEO & Co-founder) & Sparsh Sharma (Co-founder) — **Paasa (YC S24)**  
> **Author:** Nikhil Varma Vanapala (B.Tech AI/Data Science, Mahindra University)  
> **Tech Stack:** Python 3.10+ • Flask • Tailwind CSS (via CDN) • Chart.js • OpenPyXL • 100% Local In-Memory  
> **Deployment Status:** Production-Ready Local Command Center (`http://127.0.0.1:5000`)

<br/>

<div align="center">
  <img src="assets/terminal_overview.png" alt="Paasa TaxAlpha Terminal Dashboard" width="100%" style="border-radius: 8px; border: 1px solid #1F242D;" />
  <p><em>Figure 1: Bespoke Brutalist Financial Terminal displaying ₹79,927 in pre-March 31 tax alpha and live wash-sale replacement matrix.</em></p>
</div>

<br/>

---

## 1. Executive Summary & Problem Context

Paasa enables Indian HNIs, founders, and tech professionals to build generational global wealth by investing in US public equities and ETFs under the RBI's **Liberalised Remittance Scheme (LRS)**. However, cross-border investors encounter severe tax and regulatory friction every March:

### The 4 Core Bottlenecks Indian Global Investors Face
1. **The Dual-Calendar Fiscal Mismatch (US Jan–Dec vs India Apr–Mar):**  
   US custodian brokers (Interactive Brokers, DriveWealth, Charles Schwab) issue Form 1099-B on a **Jan 1 – Dec 31** basis. Indian income tax filings (**ITR-2**) operate on **April 1 – March 31**. An investor cannot hand a 1099-B to an Indian Chartered Accountant (CA) without painful, error-prone manual trade re-slicing.
2. **Mandatory Indian Rule 115 FX Normalization:**  
   Under **Rule 115 of the Indian Income Tax Rules, 1962**, capital gains in foreign currency must convert to INR using the **SBI Telegraphic Transfer (TT) Buying Rate** as of the *last day of the month immediately preceding the transaction month*. Standard brokers report in USD; converting each historical lot manually takes 12–15 hours.
3. **Lost Pre-March 31 Tax Alpha (The ₹80k+ Missed Opportunity):**  
   US brokers do not alert Indian investors in March. Under **Section 70 of the Indian Income Tax Act**, foreign capital losses can directly offset realized capital gains. In a typical \$45k portfolio, unharvested losses in dip positions (e.g. AMD, TSLA) leave **₹60,000 to ₹1,00,000+** in unnecessary tax liability on the table every March 31st.
4. **DTAA Foreign Dividend Tax Credit (Form 67 & Schedule FSI):**  
   US brokers withhold **25%** on dividends paid to Indian residents under Article 10 of the India-US DTAA. Claiming this credit under **Section 90** requires line-by-line reconciliation in Form 67 and Schedule FSI before ITR filing.
5. **Mandatory Schedule FA Foreign Asset Disclosure:**  
   Indian residents must disclose peak and closing values for foreign assets in Schedule FA. Non-disclosure carries harsh penalties (₹10 Lakh under the Black Money Act).

---

## 2. System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PAASA TAXALPHA WORKSPACE                        │
└────────────────────────────────────────────────────────────────────────┘
                                    │
       ┌────────────────────────────┴───────────────────────────┐
       ▼                                                        ▼
┌──────────────────────────────┐        ┌──────────────────────────────┐
│       FLASK REST CORE        │        │   FINANCIAL TERMINAL SPA     │
│       (`paasa/server.py`)    │        │  (`paasa/static/index.html`) │
├──────────────────────────────┤        ├──────────────────────────────┤
│ • GET  /                     │ ◄────► │ • Editorial Brutalist UI     │
│ • GET  /api/health           │        │ • Newsreader Serif + Monospace│
│ • GET  /api/sample           │        │ • Electric Acid (#D4FF00)    │
│ • POST /api/analyze          │        │ • Real-time Live Tax Saved   │
│ • GET  /api/export (.xlsx)   │        │ • FX Drift vs Asset Alpha    │
└──────────────────────────────┘        └──────────────────────────────┘
               │
       ┌───────┴────────────────────────────────────────┐
       ▼                                                ▼
┌──────────────────────────────┐        ┌──────────────────────────────┐
│      CORE ENGINE SUITE       │        │     EMBEDDED LOCAL DATA      │
│      (`paasa/core/`)         │        │     (`paasa/data/`)          │
├──────────────────────────────┤        ├──────────────────────────────┤
│ • parser.py (IBKR/DW CSV)    │        │ • sbi_tt_historical.json     │
│ • currency.py (Rule 115 FX)  │        │   (Monthly SBI TT 2021–2026) │
│ • tax_engine.py (FIFO Lots)  │        │ • etf_substitutes.json       │
│ • loss_harvester.py (Swaps)  │        │   (Wash-Sale Correlation)    │
│ • dtaa_reconciler.py (Form 67)│       │ • sample_portfolio_ibkr.csv  │
│ • exporter.py (OpenPyXL CA)  │        │   (Realistic Multi-Year)     │
└──────────────────────────────┘        └──────────────────────────────┘
```

---

## 3. Core Engine Mechanics

### A. FIFO Lot Matching & Budget 2024 Classification
- Foreign equities and ETFs are categorized as **unlisted securities** under Section 2(42A).
- **Post-Budget 2024 Regime (Effective July 23, 2024):**
  - **LTCG:** Holding period > **24 months**, taxed at a flat **12.5%** (without indexation).
  - **STCG:** Holding period <= **24 months**, taxed at the investor's applicable slab rate (**20%**, **30%**, or **39%** with surcharge & cess).
- Every sell order consumes historical buy lots on a strict FIFO basis, computing holding days, holding months, and exact tranche costs.

### B. Rule 115 SBI TT Buying Rate Normalization
For any transaction date $T$:
1. Finds the preceding calendar month end: $T_{\text{preceding\_month}}$.
2. Looks up the exact SBI TT Buying Rate in `sbi_tt_historical.json`.
3. Converts cost basis and proceeds to INR offline with zero external network dependencies.
4. Decomposes total INR return into **Asset Alpha ($)** vs **Currency Drift (USD/INR Rupee Depreciation Tailwind)**.

### C. Wash-Sale Correlated ETF Substitution Matrix
Under US IRS rules (and prudent risk management), repurchasing a substantially identical security within 30 days triggers the wash-sale disallowance rule. To harvest Indian capital losses without violating wash-sale intent or losing market exposure:
- **VOO** (Vanguard S&P 500) $\rightarrow$ Swap into **IVV** ($\rho = 0.999$) or **SPY**
- **QQQ** (Invesco Nasdaq 100) $\rightarrow$ Swap into **QQQM** ($\rho = 0.999$) or **VGT** ($\rho = 0.952$)
- **NVDA** $\rightarrow$ Swap into **SMH** ($\rho = 0.884$) or **SOXX** ($\rho = 0.862$)
- **AMD** $\rightarrow$ Swap into **SMH** ($\rho = 0.842$) or **NVDA** ($\rho = 0.825$)
- **TSLA** $\rightarrow$ Swap into **ARKK** ($\rho = 0.785$) or **CARZ** ($\rho = 0.812$)

### D. Multi-Tab CA-Ready Excel Workbook Generation
Generates a formatted, publication-grade Excel workbook with 5 dedicated schedules:
1. `Summary_Dashboard`: High-level portfolio metrics, realized gains, net tax saved, and DTAA relief.
2. `Schedule_Capital_Gains`: Full FIFO audit trail with buy/sell dates, Rule 115 FX rates, STCG/LTCG, and estimated tax.
3. `Schedule_FSI_Dividends`: Foreign income, 25% US withholding, and Form 67 Section 90 credit.
4. `Schedule_FA_Holdings`: Foreign equity disclosure for ITR-2 Table A3/A4 with peak and closing balances.
5. `Tax_Alpha_Harvest_Plan`: Actionable trade tickets with recommended correlated substitutes and projected INR savings.

---

## 4. Quickstart Guide (Local Execution)

### Prerequisites
- Python 3.10+
- Flask and OpenPyXL (`pip install flask openpyxl`)

### Launching the Web Server
Navigate to the project root and run:
```bash
python server.py
```

Console Output:
```text
============================================================================
  🚀 PAASA TAXALPHA ENGINE — LOCAL-FIRST DUAL-CALENDAR TAX OPTIMIZER
  YC S24 Portfolio Project | Built for Nitish Sahni & Sparsh Sharma
============================================================================
  * Web Dashboard  : http://127.0.0.1:5000
  * API Health     : http://127.0.0.1:5000/api/health
  * Sample Analysis: http://127.0.0.1:5000/api/sample
  * CA Export      : http://127.0.0.1:5000/api/export?format=excel
  * Rule 115 Rates : Bundled SBI TT Historical DB (2021-2026)
  * Wash-Sale Rule : Active ETF Substitution Matrix Loaded
============================================================================
```

### CLI Flags
- `--no-browser`: Do not automatically launch the default web browser.
- `--port 8080`: Bind to a custom port (default: 5000).
- `--host 0.0.0.0`: Listen on all network interfaces.

<br/>

<div align="center">
  <img src="assets/terminal_full_page.png" alt="Paasa Full Terminal Matrix" width="100%" style="border-radius: 8px; border: 1px solid #1F242D;" />
  <p><em>Figure 2: Full interactive audit ledger displaying Rule 115 FIFO lots, asset return decomposition, and Schedule FA compliance matrices.</em></p>
</div>

<br/>

---

## 5. API Reference

| Endpoint | Method | Parameters | Description |
| :--- | :--- | :--- | :--- |
| `/` | `GET` | — | Serves the single-page terminal dashboard. |
| `/api/health` | `GET` | — | Health check and engine status telemetry. |
| `/api/sample` | `GET` | `tax_slab` (float), `fy` (str) | Computes full analysis on bundled sample portfolio (`sample_portfolio_ibkr.csv`). |
| `/api/analyze` | `POST` | `file` (multipart) OR `csv_text` (JSON) | Ingests custom trade CSV and returns parsed JSON analysis. |
| `/api/export` | `GET` | `format` (`excel`\|`csv`), `fy` (str), `tax_slab` (float) | Streams downloadable, CA-ready multi-tab Excel spreadsheet or CSV. |

---

## 6. Video Demo Script (2-Minute Loom Walkthrough)
### *Pitching to Nitish Sahni (CEO) & Sparsh Sharma (Co-founder), Paasa*

* **Target Duration:** 2 minutes (120 seconds)  
* **Format:** Loom screen share + camera bubble in the bottom corner  
* **Target Audience:** Nitish Sahni (`nitish@paasa.com`) & Sparsh Sharma (`sparsh@paasa.com`)

---

### [0:00 – 0:25] The Hook: The Hidden Pain of Indian LRS Tax Season
> *(Screen on: Blank Interactive Brokers 1099-B PDF side-by-side with an Indian ITR-2 Schedule FA form)*
> 
> "Hey Nitish and Sparsh! Huge congratulations on the YC S24 batch. I love Paasa’s mission of making global asset allocation effortless for Indian investors.
> 
> But right now, every Indian HNI investing in US stocks through Interactive Brokers or DriveWealth runs into a massive wall every March:
> 1. US brokers report on **Jan 1 to Dec 31 calendar years**, while Indian taxes require **April 1 to March 31 fiscal years**.
> 2. Rule 115 mandates converting gains using the **SBI TT Buying Rate on the last day of the preceding month**.
> 3. Worst of all: US brokers **never tell Indian investors to harvest losses before March 31st**, costing them ₹50,000 to ₹1,00,000 in unharvested tax alpha."

---

### [0:25 – 1:00] The Solution: Ingestion & Dual-Calendar Normalization
> *(Action: Switch tab to `http://127.0.0.1:5000`. Drag and drop `sample_portfolio_ibkr.csv` into the terminal ingestion zone).*
> 
> "I built the **Paasa TaxAlpha Engine** to turn this 14-hour CA headache into a 2-second automated workflow.
> 
> Watch this: I drop a raw Interactive Brokers trade confirmation CSV right into the terminal. In less than 200 milliseconds, the engine:
> - Normalizes every lot under **Indian Rule 115** using our bundled historical SBI TT rate engine.
> - Automatically applies **Budget 2024 foreign equity rules**: classifying holding periods over 24 months as LTCG at 12.5%, and short-term at the investor's slab.
> - Decomposes the portfolio returns into **Stock Alpha vs USD/INR Currency Drift**, showing the exact tailwind from rupee depreciation."

---

### [1:00 – 1:35] The "Magic Moment": Algorithmic Pre-March 31 Tax Alpha
> *(Action: Scroll down to the Pre-March 31 Algorithmic Tax-Loss Harvester. Point cursor at the live counter: ₹79,927. Toggle checkboxes on and off to show the live counter reacting).*
> 
> "Here is the magic moment for Paasa:
> Look at our **Pre-March 31 Algorithmic Tax-Loss Harvester**. The engine scanned the open positions and found ₹5.2 Lakhs in unrealized losses across high-entry lots in AMD and TSLA.
> 
> It provides exact, wash-sale-safe swap instructions:
> - *Sell AMD $\rightarrow$ Swap into SMH (VanEck Semiconductor ETF, correlation 0.84)*
> - *Sell VOO $\rightarrow$ Swap into IVV (iShares S&P 500, correlation 0.999)*
> 
> Look at the live counter: toggling these execution tickets immediately projects **₹79,927 saved in cash taxes** before March 31st. The investor maintains 100% market exposure while resetting their cost basis and capturing pure tax alpha."

---

### [1:35 – 1:50] The 1-Click CA Export
> *(Action: Click the "EXPORT CA WORKBOOK (.XLSX)" button in the top right. Open the downloaded Excel file to show the 5 formatted tabs: Summary, Schedule Capital Gains, Schedule FSI Dividends, Schedule FA).*
> 
> "And for their Chartered Accountant? One click generates a complete, audit-ready Excel workbook with Schedule Capital Gains FIFO matching, Schedule FSI dividend foreign tax credit under Section 90, and ITR-2 Schedule FA foreign asset disclosure."

---

### [1:50 – 2:05] The Close & Pitch
> *(Camera focus)*
> 
> "I built this prototype specifically for Paasa because I want to bring this level of engineering velocity and financial depth to your team as a software engineering intern.
> 
> I’ve documented the architecture and repo cleanly. I’d love 10 minutes this week to show you how we can integrate this directly into Paasa’s user dashboard.
> 
> Thanks Nitish and Sparsh, and talk soon!"

---

## 7. Project File Structure

```text
paasa/
├── server.py                          # Flask REST API server (port 5000)
├── README.md                          # Comprehensive documentation & pitch blueprint
├── PRD_Dual_Calendar_Tax_Engine.md    # Product Requirement Document
├── problem_breakdown_and_pitch.md     # Market breakdown & cold outreach templates
│
├── core/                              # Financial calculation engine package
│   ├── __init__.py                    # Exports core modules and helper functions
│   ├── parser.py                      # Robust CSV ingestion (IBKR, DW, Generic)
│   ├── currency.py                    # Rule 115 SBI TT Buying Rate converter
│   ├── tax_engine.py                  # FIFO lot matching, Budget 2024 LTCG/STCG
│   ├── loss_harvester.py              # Loss scanner & wash-sale ETF swap matrix
│   ├── dtaa_reconciler.py             # Form 67 & Schedule FSI foreign tax credits
│   └── exporter.py                    # Multi-tab publication-grade Excel exporter
│
├── data/                              # Bundled static reference data (offline-first)
│   ├── sbi_tt_historical.json         # Historical monthly SBI TT rates (2021–2026)
│   ├── etf_substitutes.json           # Correlated ETF swap pairs with rationale
│   └── sample_portfolio_ibkr.csv      # Ready-to-demo mock portfolio (RSUs + ETFs)
│
└── static/                            # Frontend Single-Page Application
    └── index.html                     # Brutalist editorial financial terminal SPA
```

---

## 8. License & Attribution
Developed with pride by **Nikhil Varma Vanapala** for **Paasa (YC S24)**.
All financial calculations conform to the Indian Income Tax Act, 1961, Rule 115 of the Income Tax Rules, 1962, and the Union Budget 2024 capital gains regime.
