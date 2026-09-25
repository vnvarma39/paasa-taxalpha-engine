# 🏢 Startup Workspace: Paasa (YC S24)

> **Company:** Paasa (`https://paasa.com/`)  
> **Batch:** Y Combinator Summer 2024 (YC S24)  
> **Sector:** FinTech / WealthTech / Cross-Border Investing  
> **HQ:** Gurugram, Haryana  
> **Key Founders:** Nitish Sahni (Co-founder & CEO), Sparsh Sharma (Co-founder)  
> **Contact:** `founders@paasa.com` / `nitish@paasa.com` / `sparsh@paasa.com`  
> **Status:** Seed / Early Stage (~10–20 employees) — **High founder visibility**

---

## 1. What Paasa Does & Why It Matters

Paasa is building the premier wealth management and execution platform for Indian residents investing in global public markets (US, UK, Europe, HK). Acting as an intelligent layer on top of custodian brokers like Interactive Brokers, Paasa solves the massive regulatory, compliance, and tax friction that prevents Indian capital from diversifying abroad.

---

## 2. Core Technical Bottlenecks & Friction Points

1. **Dual Tax Regime Optimization (India vs US / Foreign):**
   * Indian tax years run **April 1 to March 31**, while foreign exchanges (like the US) calculate tax on **Jan 1 to Dec 31**.
   * Capital gains tax rules in India for foreign unlisted/listed securities differ radically from domestic equities (TCS at 20% on remittances above ₹7L, Section 90/91 DTAA relief, Form 67 filings).
   * **The Gap:** Standard Robo-advisors use generic US-centric tax-loss harvesting. Paasa needs an algorithmic engine calibrated specifically to Indian fiscal years and DTAA credits.

2. **LRS & FEMA Regulatory Document Automation:**
   * Sending funds overseas requires outward remittance under RBI's Liberalised Remittance Scheme (LRS).
   * Users face complex paperwork: Form A2, Form 15CA (self-declaration), Form 15CB (Chartered Accountant certification), and bank statement verification.
   * **The Gap:** Manual verification slows onboarding and increases operational burn. Intelligent document parsing (OCR + LLM validation) can automate compliance verification.

3. **Currency (INR vs USD) Volatility & Dynamic Rebalancing:**
   * Global returns for Indian investors are dual-variable: Asset Performance + FX Drift (USD/INR depreciation or appreciation).
   * **The Gap:** Need quantitative portfolio tracking that separates alpha from currency effects and triggers rebalancing when foreign exchange swings exceed user tolerance.

---

## 3. The Value Proposal: What You Can Build & Pitch

### Proposed Mini-Project / Value Prototype:
**"Algorithmic Tax-Loss Harvesting & Dual-Calendar Tax Alpha Simulator for Indian Global Investors"**

* **Core Stack:** Python, Pandas/Polars, FastAPI, Docker, Streamlit (or Next.js).
* **Architecture:**
  1. **Trade Ingestion:** Parse CSV/JSON trade history from Interactive Brokers / DriveWealth.
  2. **Indian Fiscal Year Partitioning:** Slice realized/unrealized gains across April–March boundaries.
  3. **Loss-Harvesting Optimizer:** Identify wash-sale avoidance candidates (re-allocating into correlated ETFs, e.g. VOO vs IVV) before March 31st to offset Indian domestic or foreign capital gains.
  4. **DTAA Tax Simulator:** Estimate Form 67 foreign tax credit offsets for US withholding dividends (25% rate under India-US DTAA).
  5. **Interactive Dashboard:** Visual metric showing "Estimated Tax Saved in ₹" vs "Standard Buy-and-Hold".

---

## 4. Tailored Cold Email to Founders (Nitish Sahni & Sparsh Sharma)

```text
Subject: Built a dual-calendar Tax-Loss Harvesting simulator for Paasa's investors

Hi Nitish and Sparsh,

Huge congrats on the YC S24 batch! Love how Paasa is untangling the friction around LRS remittances and global asset allocation for Indian investors—long overdue compared to clunky legacy banking routes.

One technical nuance that caught my attention is the dual-tax friction Indian HNIs face: US brokers report on Jan-Dec calendar years, but Indian tax filing requires April-March fiscal year alignment, TCS reconciliation, and Form 67 DTAA foreign tax credits.

Rather than just observing it, I spent the last few days building a lightweight prototype tailored for Indian global investors:

🔗 [Live Demo / Technical Teardown Link: DocSend / HuggingFace]
💻 [Clean GitHub Repo with Dockerized API]

What it does:
1. Ingests broker trade histories and automatically partitions gains across Indian fiscal years (Apr–Mar).
2. Simulates tax-loss harvesting opportunities before March 31 without violating wash-sale intent (switching to correlated ETFs).
3. Projects estimated tax alpha saved in INR after applying Indian tax slab offsets.

I am a 7th-semester B.Tech student (AI/ML & Data Science) at Mahindra University. I’m looking for an engineering/data science internship where I can ship high-impact features with zero ramp-up time.

Would you be open to a 10-minute chat this Thursday at 3 PM or Friday morning to see how this fits Paasa's roadmap?

Best regards,
Nikhil Varma
[Phone Number] | [LinkedIn Profile] | [GitHub Profile]
```

---

## 5. LinkedIn Connection Note to Nitish Sahni (CEO)

```text
Hi Nitish, congrats on YC S24! As a 7th-sem AI/Data Science student, I built a prototype tax-loss harvesting engine specifically calibrated for Indian fiscal year (Apr-Mar) global portfolios on Paasa. Would love to share the teardown and demo!
```
