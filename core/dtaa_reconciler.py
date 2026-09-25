class DTAAReconciler:
    """
    DTAA Foreign Tax Credit (FTC) & Form 67 Reconciler under Section 90 of Indian IT Act.
    Reconciles 25% US dividend withholding tax for Schedule FSI and Form 67 filings.
    """

    @staticmethod
    def generate_form_67_schedule(dividends, tax_slab_pct=30.0):
        """
        Builds line-by-line Form 67 / Schedule FSI schedule from parsed dividend events.
        """
        schedule_entries = []
        total_gross_dividend_usd = 0.0
        total_withholding_usd = 0.0
        total_gross_dividend_inr = 0.0
        total_withholding_inr = 0.0
        total_ftc_claimed_inr = 0.0
        total_indian_tax_inr = 0.0

        for div in dividends:
            gross_usd = div["gross_div_usd"]
            wht_usd = div["withholding_usd"]
            gross_inr = div["gross_div_inr"]
            wht_inr = div["withholding_inr"]
            rate = div["fx_rate"]

            indian_tax = round(gross_inr * (tax_slab_pct / 100.0), 2)
            # Under Section 90, FTC is the lower of tax paid in US or tax payable in India
            ftc_allowed = min(wht_inr, indian_tax)
            net_tax_due = max(0.0, indian_tax - ftc_allowed)

            entry = {
                "date": div["date"],
                "symbol": div["symbol"],
                "country_code": "01 (United States)",
                "dtaa_article": "Article 10 (Dividends - 25% Rate)",
                "gross_income_usd": gross_usd,
                "rule_115_fx_rate": rate,
                "gross_income_inr": gross_inr,
                "tax_paid_usd": wht_usd,
                "tax_paid_inr": wht_inr,
                "indian_tax_liability_inr": indian_tax,
                "tax_relief_sec_90_inr": ftc_allowed,
                "net_tax_payable_inr": net_tax_due,
                "indian_fy": div["indian_fy"],
                "form_67_status": "Eligible for Foreign Tax Credit",
            }
            schedule_entries.append(entry)

            total_gross_dividend_usd += gross_usd
            total_withholding_usd += wht_usd
            total_gross_dividend_inr += gross_inr
            total_withholding_inr += wht_inr
            total_ftc_claimed_inr += ftc_allowed
            total_indian_tax_inr += indian_tax

        return {
            "entries": schedule_entries,
            "summary": {
                "total_gross_dividend_usd": round(total_gross_dividend_usd, 2),
                "total_withholding_usd": round(total_withholding_usd, 2),
                "total_gross_dividend_inr": round(total_gross_dividend_inr, 2),
                "total_withholding_inr": round(total_withholding_inr, 2),
                "total_indian_tax_inr": round(total_indian_tax_inr, 2),
                "total_ftc_claimed_inr": round(total_ftc_claimed_inr, 2),
                "net_tax_payable_inr": round(max(0.0, total_indian_tax_inr - total_ftc_claimed_inr), 2),
            },
            "filing_note": "Form 67 must be submitted online on the e-filing portal before filing ITR under Rule 128."
        }
