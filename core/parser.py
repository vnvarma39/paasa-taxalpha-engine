import csv
import io
from datetime import datetime

class TradeParser:
    """
    Robust CSV Trade parser supporting Paasa Standard, Interactive Brokers,
    DriveWealth, and Generic CSV trade histories.
    """

    @staticmethod
    def parse_csv(csv_source):
        """
        Parses CSV from file path, StringIO, or raw string.
        Returns list of standardized trade dictionaries sorted chronologically.
        """
        if isinstance(csv_source, str):
            if "\n" in csv_source or "," in csv_source:
                reader = csv.DictReader(io.StringIO(csv_source.strip()))
            else:
                # File path
                with open(csv_source, "r", encoding="utf-8-sig") as f:
                    content = f.read()
                reader = csv.DictReader(io.StringIO(content.strip()))
        elif hasattr(csv_source, "read"):
            content = csv_source.read()
            if isinstance(content, bytes):
                content = content.decode("utf-8-sig", errors="replace")
            reader = csv.DictReader(io.StringIO(content.strip()))
        else:
            raise ValueError("Unsupported CSV source type")

        fieldnames = [f.strip().lower() if f else "" for f in (reader.fieldnames or [])]
        raw_rows = list(reader)

        standardized_records = []
        for raw in raw_rows:
            # Map keys case-insensitively
            row = {k.strip().lower(): v.strip() if isinstance(v, str) else v for k, v in raw.items() if k}
            record = TradeParser._normalize_row(row)
            if record:
                standardized_records.append(record)

        # Sort chronologically by date
        standardized_records.sort(key=lambda x: x["date"])
        return standardized_records

    @staticmethod
    def _normalize_row(row):
        """
        Normalizes a single row to standard schema:
        {
            "date": "YYYY-MM-DD",
            "symbol": "VOO",
            "asset_type": "ETF" | "EQUITY",
            "action": "BUY" | "SELL" | "DIVIDEND",
            "quantity": float,
            "price_usd": float,
            "fees_usd": float,
            "withholding_tax_usd": float,
            "notes": str
        }
        """
        # 1. Date resolution
        date_str = None
        for key in ["date", "tradedate", "date/time", "transaction_date", "settle_date", "timestamp"]:
            if key in row and row[key]:
                date_str = row[key]
                break

        if not date_str:
            return None

        clean_date = TradeParser._parse_date_string(date_str)
        if not clean_date:
            return None

        # 2. Symbol resolution
        symbol = None
        for key in ["symbol", "ticker", "asset", "code"]:
            if key in row and row[key]:
                symbol = row[key].upper().strip()
                break

        if not symbol:
            return None

        # 3. Action resolution
        raw_action = ""
        for key in ["action", "side", "type", "transaction_type", "activity"]:
            if key in row and row[key]:
                raw_action = str(row[key]).upper().strip()
                break

        action = "BUY"
        if "SELL" in raw_action or "SL" in raw_action:
            action = "SELL"
        elif "DIV" in raw_action:
            action = "DIVIDEND"
        elif "BUY" in raw_action or "BOT" in raw_action:
            action = "BUY"
        else:
            # Check quantity sign
            for q_key in ["quantity", "shares", "qty", "amount"]:
                if q_key in row and row[q_key]:
                    try:
                        q_val = float(str(row[q_key]).replace(",", ""))
                        if q_val < 0:
                            action = "SELL"
                    except ValueError:
                        pass

        # 4. Quantity resolution
        quantity = 0.0
        for key in ["quantity", "shares", "qty"]:
            if key in row and row[key]:
                try:
                    quantity = abs(float(str(row[key]).replace(",", "")))
                    break
                except ValueError:
                    pass

        # 5. Price resolution
        price_usd = 0.0
        for key in ["price_usd", "price", "t. price", "tradeprice", "unit_price", "nav"]:
            if key in row and row[key]:
                try:
                    price_usd = float(str(row[key]).replace("$", "").replace(",", ""))
                    break
                except ValueError:
                    pass

        # 6. Fees resolution
        fees_usd = 0.0
        for key in ["fees_usd", "fees", "fee", "commission", "comm/fee", "ibcommission"]:
            if key in row and row[key]:
                try:
                    fees_usd = abs(float(str(row[key]).replace("$", "").replace(",", "")))
                    break
                except ValueError:
                    pass

        # 7. Withholding tax
        withholding_tax_usd = 0.0
        for key in ["withholding_tax_usd", "withholding_tax", "withholding", "wht", "tax_withheld"]:
            if key in row and row[key]:
                try:
                    withholding_tax_usd = abs(float(str(row[key]).replace("$", "").replace(",", "")))
                    break
                except ValueError:
                    pass

        # If dividend and withholding tax not specified, standard US DTAA withholding is 25%
        if action == "DIVIDEND" and withholding_tax_usd == 0.0 and quantity > 0 and price_usd > 0:
            withholding_tax_usd = round(quantity * price_usd * 0.25, 2)

        # 8. Asset Type
        asset_type = "EQUITY"
        known_etfs = {"VOO", "QQQ", "QQQM", "IVV", "SPY", "VGT", "XLK", "SMH", "SOXX", "ARKK", "CARZ", "SPLG", "IWM", "VNQ", "IYR", "XLRE", "XLC"}
        if symbol in known_etfs:
            asset_type = "ETF"
        elif "asset_type" in row and row["asset_type"]:
            asset_type = row["asset_type"].upper()

        notes = row.get("notes", "") or row.get("description", "") or ""

        return {
            "date": clean_date,
            "symbol": symbol,
            "asset_type": asset_type,
            "action": action,
            "quantity": quantity,
            "price_usd": price_usd,
            "fees_usd": fees_usd,
            "withholding_tax_usd": withholding_tax_usd,
            "notes": str(notes).strip()
        }

    @staticmethod
    def _parse_date_string(date_str):
        date_str = str(date_str).strip()
        # Handle formats: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, YYYY/MM/DD, etc.
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%Y/%m/%d",
            "%d-%b-%Y",
            "%d-%B-%Y",
            "%b %d, %Y",
            "%B %d, %Y",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str[:19].strip(), fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass
        # Try splitting by space or T
        cleaned = date_str.split(" ")[0].split("T")[0]
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]:
            try:
                dt = datetime.strptime(cleaned, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass
        return None


def get_indian_financial_year(dt):
    """
    Returns Indian Financial Year string, e.g. 'FY 2024-25' for 2024-05-18.
    """
    if isinstance(dt, str):
        dt = datetime.strptime(dt[:10], "%Y-%m-%d").date()
    elif isinstance(dt, datetime):
        dt = dt.date()
    year = dt.year
    if dt.month >= 4:
        return f"FY {year}-{str(year + 1)[-2:]}"
    else:
        return f"FY {year - 1}-{str(year)[-2:]}"


from dataclasses import dataclass, asdict

@dataclass
class TradeRecord:
    date: str
    symbol: str
    asset_type: str
    action: str
    quantity: float
    price_usd: float
    fees_usd: float = 0.0
    withholding_tax_usd: float = 0.0
    notes: str = ""
    trade_id: int = 0
    fx_rate: float = 0.0
    total_usd: float = 0.0
    total_inr: float = 0.0
    financial_year: str = ""
    calendar_year: int = 0

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __contains__(self, key):
        return hasattr(self, key)

    def to_dict(self):
        return asdict(self)


def parse_csv(csv_source, typed=True):
    """
    Convenience function to parse CSV source. If typed=True, returns list of TradeRecord objects.
    """
    from .currency import get_sbi_tt_rate
    raw_records = TradeParser.parse_csv(csv_source)
    if not typed:
        return raw_records

    typed_records = []
    for idx, r in enumerate(raw_records, start=1):
        dt_str = r["date"]
        fx = get_sbi_tt_rate(dt_str)
        tot_usd = round(r["quantity"] * r["price_usd"], 2)
        tot_inr = round(tot_usd * fx, 2)
        fy = get_indian_financial_year(dt_str)
        cy = int(dt_str[:4])

        rec = TradeRecord(
            date=dt_str,
            symbol=r["symbol"],
            asset_type=r["asset_type"],
            action=r["action"],
            quantity=r["quantity"],
            price_usd=r["price_usd"],
            fees_usd=r["fees_usd"],
            withholding_tax_usd=r["withholding_tax_usd"],
            notes=r.get("notes", ""),
            trade_id=idx,
            fx_rate=fx,
            total_usd=tot_usd,
            total_inr=tot_inr,
            financial_year=fy,
            calendar_year=cy
        )
        typed_records.append(rec)
    return typed_records


def trades_to_dataframe(trades):
    """
    Converts trade records to pandas DataFrame.
    """
    import pandas as pd
    records = [t.to_dict() if hasattr(t, "to_dict") else t for t in trades]
    return pd.DataFrame(records)
