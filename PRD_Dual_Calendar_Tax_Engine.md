# 📄 Product Requirement Document (PRD)

# Project: Paasa TaxAlpha Engine
### *Local-First Dual-Calendar Tax-Loss Harvester & DTAA Schedule FA Generator for Global Indian Investors*

---

| **Document Version** | 1.0 |
| **Target Company** | **Paasa (YC S24)** (`paasa.com`) |
| **Audience** | Nitish Sahni (CEO) & Sparsh Sharma (Co-founder) |
| **Author** | Nikhil Varma Vanapala |
| **Execution Mode** | **100% Local Deployment** (Python + Streamlit + SQLite / Polars) |
| **Status** | Ready for Local Implementation |

---

## 1. Executive Summary & Problem Context

### Why Paasa Needs This
Paasa enables Indian HNIs and tech professionals to invest in US equities and ETFs under the RBI's **Liberalised Remittance Scheme (LRS)**. However, Indian investors face extreme tax and regulatory friction:
1. **Fiscal Year Mismatch:** US brokers (Interactive Brokers, DriveWealth, Charles Schwab) calculate tax years on **Jan 1 – Dec 31**. Indian income tax operates on **April 1 – March 31**. US 1099-B/1042-S statements are unusable for Indian ITR filings without manual re-calculation.
2. **Double Currency Fluctuations (USD + INR):** Gains must be computed in INR using the SBI Telegraphic Transfer (TT) Buying Rate on the last day of the month preceding transaction month (Rule 115 of Indian Income Tax Rules).
3. **Lost Tax Alpha:** In India, foreign equity capital losses can offset foreign capital gains (and long-term can offset long-term). Investors rarely harvest losses before **March 31st** because US broker platforms don't alert them to Indian financial year-end opportunities.
4. **DTAA Foreign Tax Credit Friction (Form 67):** The US withholds 25% on dividends paid to Indian residents. Claiming this foreign tax credit under Section 90 requires detailed reconciliation in Schedule FSI and Form 67.

### What This Local Project Does
A self-contained, offline-first Python web application that ingests US broker trade confirmations (CSV), calculates tax liability under Indian tax rules (Rule 115 FX conversion), recommends **March 31st Tax-Loss Harvesting trades** using a wash-sale avoidance ETF substitution matrix, and exports a CA-ready **Schedule FA & FSI tax breakdown**.

---

## 2. Target Personas & Core Use Case

### Primary User: "Rohan — Senior SDE / Tech Lead in Bengaluru"
* Holds $45,000 in US stocks (vested RSUs + LRS remittances).
* Uses Interactive Brokers or DriveWealth.
* **Pain Point:** In March, his Chartered Accountant (CA) asks for his foreign capital gains and Schedule FA details. Rohan spends 14 hours manually converting USD to INR using daily SBI rates and calculating whether to sell dipping stocks to save ₹60,000 on capital gains taxes.
* **The "Magic Moment":** Rohan drops his `trades.csv` into the local app. Within 2 seconds, it tells him:
  > *"You have ₹1,20,000 in taxable STCG for FY 2025–26. Sell 18 shares of your losing position in AMD before March 31st and swap into NVDA/SMH to save ₹36,000 in Indian taxes without losing semiconductor exposure."*

---

## 3. Scope & System Architecture (100% Local)

```
[ Local Trade CSV (IBKR / DriveWealth / Generic) ]
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   PAASA TAXALPHA CORE ENGINE                │
│                                                             │
│  1. Ingestion & Validation Engine (Pandas / Polars)          │
│  2. Historical FX Rule 115 Normalizer (Local SBI TT Rate DB)│
│  3. Dual-Calendar Partition Engine (Apr-Mar vs Jan-Dec)     │
│  4. Indian Tax Classifier (LTCG >24m @ 12.5% vs STCG @ Slab)│
│  5. Pre-March 31 Tax-Loss Harvesting & Substitution Matrix │
│  6. Dividend DTAA & Form 67 Foreign Tax Credit Estimator    │
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 INTERACTIVE LOCAL FRONTEND                  │
│                     (Streamlit / Altair)                    │
│                                                             │
│  • Visual P&L vs Currency Alpha Drift                       │
│  • One-Click Actionable Tax-Loss Harvest Recommendations    │
│  • Downloadable CA-Ready Tax Summary (Excel / Clean PDF)    │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Detailed Feature Specifications

### Feature 1: CSV Statement Ingestion & Auto-Detection
* **Input:** CSV upload of trade history.
* **Supported Formats:** Interactive Brokers Trade CSV, DriveWealth Transaction CSV, Paasa Standard Format.
* **Columns Required:** `Date`, `Symbol`, `Asset_Type`, `Action` (BUY/SELL/DIVIDEND), `Quantity`, `Price_USD`, `Fees_USD`, `Withholding_Tax_USD`.

### Feature 2: Indian Rule 115 FX Converter (Zero External API Dependency)
* **Rule 115 Mandate:** Foreign capital gains must convert to INR using the **SBI TT Buying Rate** as of the last day of the month preceding the transaction.
* **Implementation:** Ship bundled `sbi_tt_historical.json` containing monthly SBI TT rates (2022 to present) with fallback interpolation.
* **Output:** Every trade logs `Price_USD`, `FX_Rate_INR`, and `Total_Value_INR`.

### Feature 3: Dual-Calendar Realized Gain & Holding Period Engine
* **Partitioning:**
  * **Indian FY:** April 1 to March 31.
  * **US CY:** Jan 1 to Dec 31 (reconciles with US 1099-B).
* **Tax Rules Applied (Post-Budget 2024 Indian Regime):**
  * **LTCG:** Holding period > 24 months for unlisted/foreign equities, taxed at **12.5%** (without indexation).
  * **STCG:** Holding period <= 24 months, taxed at slab rate (configurable: 20%, 30%, 39%).
  * **FIFO (First-In, First-Out)** accounting for lot matching.

### Feature 4: Algorithmic Pre-March 31 Tax-Loss Harvester
* Scans all current unrealized positions with negative P&L.
* Determines whether harvesting the loss offsets realized STCG or LTCG for the current Indian financial year.
* **Wash-Sale ETF Substitution Engine:**
  * Suggests correlated substitutes to avoid US wash-sale rules while keeping market exposure neutral:
    * Sell `VOO` (Vanguard S&P 500) -> Buy `IVV` (iShares S&P 500) or `SPY`
    * Sell `QQQ` (Invesco Nasdaq) -> Buy `QQQM` or `VGT`
    * Sell `NVDA` -> Buy `SMH` (VanEck Semiconductor ETF)
* **Actionable Card:** Shows exact trade instructions with projected tax savings in INR.

### Feature 5: DTAA Dividend Tax Credit & Form 67 Reconciler
* US dividend withholding tax is 25% under India-US DTAA.
* Computes Gross Dividend, Tax Withheld in US, and relief under Section 90 for Form 67 / Schedule FSI.

### Feature 6: One-Click CA Report Export
* Export clean, CA-ready Excel workbook with tabs:
  1. `Summary_Dashboard`: Net Tax Saved, Total Tax Payable, Alpha Breakdown.
  2. `Schedule_Capital_Gains`: Sliced by Indian FY with FIFO lots.
  3. `Schedule_FSI_Dividends`: Foreign income and US tax withheld for Form 67.
  4. `Schedule_FA_Holdings`: Foreign Asset reporting required for Indian ITR-2.

---

## 5. Technical Stack (Local Execution Only)

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ | Fast data manipulation, rich financial libs. |
| **Data Processing** | `pandas` / `polars` | Fast FIFO matching and time-series date slicing. |
| **UI Framework** | `streamlit` | Runs 100% locally with zero deployment overhead (`streamlit run app.py`). |
| **Visualizations** | `plotly` / `altair` | Interactive charts (Asset Return vs FX Drift). |
| **Report Generation** | `openpyxl` | Creates multi-tab formatted Excel workbooks for CAs. |
| **Sample Datasets** | Embedded CSV files | Comes pre-loaded with mock portfolios for instant 1-click testing. |

---

## 6. Directory Structure for the Local Project

```
paasa/
├── README.md                          # Quickstart guide + architecture overview
├── app.py                             # Main Streamlit UI entry point
├── requirements.txt                   # pandas, streamlit, plotly, openpyxl
│
├── core/
│   ├── __init__.py
│   ├── parser.py                      # CSV parsers (IBKR, DriveWealth, Generic)
│   ├── currency.py                    # Rule 115 SBI TT rate normalizer
│   ├── tax_engine.py                  # FIFO matching, STCG/LTCG, Indian FY partition
│   ├── loss_harvester.py              # Loss harvesting & ETF substitution matrix
│   └── dtaa_reconciler.py             # Form 67 / foreign dividend tax credit calculator
│
├── data/
│   ├── sbi_tt_historical.json         # Static monthly SBI TT rates (2022-2026)
│   ├── etf_substitutes.json           # Correlated asset pairs (VOO->IVV, QQQ->VGT)
│   └── sample_portfolio_ibkr.csv      # Ready-to-demo mock portfolio
│
└── exports/
    └── ca_report_template.xlsx        # Pre-formatted exportable schedule
```

---

## 7. Implementation Sprint Plan (48-Hour Build)

| Phase | Duration | Tasks | Deliverables |
| :--- | :--- | :--- | :--- |
| **Phase 1: Core Engine** | 4–6 hrs | 1. Write `parser.py` with mock IBKR CSV.<br>2. Build FIFO lot matching in `tax_engine.py`.<br>3. Implement Rule 115 currency conversion in `currency.py`. | Terminal script calculating exact Indian FY capital gains. |
| **Phase 2: Tax-Loss & DTAA Logic** | 4–6 hrs | 1. Implement unrealized P&L scanner in `loss_harvester.py`.<br>2. Build `etf_substitutes.json` lookup.<br>3. Add dividend withholding tax reconciliation in `dtaa_reconciler.py`. | Tested tax-saving recommendation engine. |
| **Phase 3: Streamlit Interface** | 4–5 hrs | 1. Build CSV drag-and-drop uploader.<br>2. Render visual KPI cards (Tax Saved, LTCG/STCG, FX Drift).<br>3. Add interactive substitution tables and 1-click Excel export. | Clean, high-polish local web app running on `localhost:8501`. |
| **Phase 4: Packaging & Video Pitch** | 2–3 hrs | 1. Record 2-minute Loom walkthrough showing problem & solution.<br>2. Write clean README with architecture diagram.<br>3. Draft tailored pitch email to Nitish & Sparsh. | Ready-to-send pitch package. |

---

## 8. Pitch Strategy & Outreach Deliverable

1. **GitHub Repository:** Clean, well-documented repo titled `paasa-taxalpha-engine` with a GIF demo in the README.
2. **2-Minute Loom Video:**
   * *0:00–0:30:* The Problem — Why US 1099 statements cause Indian CAs headaches and how Indian investors lose ₹50k+ in unharvested tax losses before March 31st.
   * *0:30–1:30:* The Demo — Drop an Interactive Brokers CSV into the app, show Indian FY tax liability calculated under Rule 115, and highlight the ETF substitution trade saving ₹42,000 before March 31st.
   * *1:30–2:00:* The Ask — *"I built this for Paasa because I admire your YC S24 mission. I'd love to bring this kind of engineering rigor to your team as an intern."*
3. **Direct Email to Nitish Sahni (`nitish@paasa.com`) & Sparsh Sharma (`sparsh@paasa.com`)** linking the repo and Loom video.
