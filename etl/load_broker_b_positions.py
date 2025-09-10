import pandas as pd
from sqlalchemy import create_engine, text
from pathlib import Path
from normalize import normalize_df

# mapping from above
MAP_B = {
  "account_number": "Ledger Code",
  "product_name": "Instrument Long Name",
  "product_code": "Instrument Code",
  "trade_date": "Trade Date",
  "delivery_date": "Delivery/Prompt date",
  "side": None,
  "quantity": "Volume",
  "trade_price": "Price",
  "market_price": "Market Rate",
  "variation_margin": "Variation Margin",
  "currency": "Currency Code",
  "as_of_date": "Open position date",
  "broker_code": None
}

def normalize_broker_b(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Use the generic normalize_df but patch in:
    - day-first date parsing
    - delivery_month from a real date column (Delivery/Prompt date)
    - side inferred from Volume sign
    - fallback broker code 'BKB'
    """
    # We’ll borrow normalize_df’s structure by creating a compatible mapping
    # and then fix side & delivery_month specifics.
    df = df_raw.copy()
    df.columns = df.columns.str.strip()

    # Coerce numerics
    for col in ["Volume", "Price", "Market Rate", "Variation Margin"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")

    def parse_date_flexible(series):
        """Parse dates that may be in m/d/Y or d/m/Y; returns datetime.date."""
        s = pd.to_datetime(series, format="%m/%d/%Y", errors="coerce")
        mask = s.isna()
        if mask.any():
            s.loc[mask] = pd.to_datetime(series[mask], format="%d/%m/%Y", errors="coerce")
        return s.dt.date

    def yyyy_mm_from_date(series):
        """Return YYYY-MM from a date-like column that may be m/d/Y or d/m/Y."""
        s = pd.to_datetime(series, format="%m/%d/%Y", errors="coerce")
        mask = s.isna()
        if mask.any():
            s.loc[mask] = pd.to_datetime(series[mask], format="%d/%m/%Y", errors="coerce")
        return s.dt.strftime("%Y-%m")

    out = pd.DataFrame()
    out["broker_code"] = "BKB"  # file doesn’t include it
    out["external_trade_id"] = df.index.astype(str)

    out["account_number"] = df["Ledger Code"].astype(str).str.strip()
    out["product_code"]   = df["Instrument Code"].astype(str).str.strip()
    out["product_name"]   = df["Instrument Long Name"].astype(str).str.strip()

    out["trade_date"]     = parse_date_flexible(df["Trade Date"])
    out["delivery_month"] = yyyy_mm_from_date(df["Delivery/Prompt date"])

    # Quantity and side inference:
    # - If Volume < 0 => SELL; Volume > 0 => BUY; if all non-negative, we treat as BUY.
    qty = pd.to_numeric(df["Volume"], errors="coerce").fillna(0.0)
    side = qty.map(lambda x: "SELL" if x < 0 else "BUY")
    out["side"] = side
    # Store signed quantity (+BUY, -SELL)
    out["quantity"] = qty.abs()
    out.loc[out["side"].eq("SELL"), "quantity"] *= -1

    out["trade_price"]      = pd.to_numeric(df.get("Price"), errors="coerce")
    out["market_price"]     = pd.to_numeric(df.get("Market Rate"), errors="coerce")
    out["variation_margin"] = pd.to_numeric(df.get("Variation Margin"), errors="coerce")

    out["currency_code"] = df["Currency Code"].astype(str).str.upper().str.strip()
    out["as_of_date"]    = parse_date_flexible(df["Open position date"])

    return out

def upserts_and_insert(engine, df_norm):
    # normalize broker_code just in case
    df_norm = df_norm.copy()
    df_norm["broker_code"] = (
        df_norm["broker_code"].astype(str).str.strip().replace({"": "BKB"})
    )

    with engine.begin() as conn:
        # ensure all broker codes exist
        for b in df_norm["broker_code"].dropna().unique():
            conn.execute(
                text("INSERT OR IGNORE INTO brokers(broker_code, broker_name) VALUES (:c, :n)"),
                {"c": b, "n": "Broker B"},
            )

        # currencies
        for ccy in df_norm["currency_code"].dropna().unique():
            conn.execute(
                text("INSERT OR IGNORE INTO currencies(currency_code) VALUES (:ccy)"),
                {"ccy": ccy},
            )

        # accounts
        for acct in df_norm["account_number"].dropna().unique():
            conn.execute(
                text("INSERT OR IGNORE INTO accounts(account_number) VALUES (:a)"),
                {"a": acct},
            )

        # products
        for row in df_norm[["product_code", "product_name"]].drop_duplicates().itertuples(index=False):
            pc, pn = row
            if pc:
                conn.execute(
                    text("INSERT OR IGNORE INTO products(product_code, product_name) VALUES (:pc,:pn)"),
                    {"pc": pc, "pn": pn or pc},
                )
            else:
                conn.execute(
                    text("INSERT OR IGNORE INTO products(product_name) VALUES (:pn)"),
                    {"pn": pn or "UNKNOWN"},
                )

    # ---- resolve FKs (re-fetch after inserts) ----
    with engine.begin() as conn:
        res = conn.execute(text("SELECT broker_code, broker_id FROM brokers")).fetchall()
        brokers = {r[0]: r[1] for r in res}

        res = conn.execute(text("SELECT account_number, account_id FROM accounts")).fetchall()
        accounts = {r[0]: r[1] for r in res}

        prows = conn.execute(text("SELECT product_id, product_code, product_name FROM products")).fetchall()
        prod_by_code = {r[1]: r[0] for r in prows if r[1]}
        prod_by_name = {r[2]: r[0] for r in prows if r[2]}

    # backfill any missing brokers then re-map (belt & suspenders)
    missing_codes = set(df_norm["broker_code"].unique()) - set(brokers.keys())
    if missing_codes:
        with engine.begin() as conn:
            for b in missing_codes:
                conn.execute(
                    text("INSERT OR IGNORE INTO brokers(broker_code, broker_name) VALUES (:c,:n)"),
                    {"c": b, "n": "Broker B"},
                )
            # refresh mapping again
            res = conn.execute(text("SELECT broker_code, broker_id FROM brokers")).fetchall()
            brokers = {r[0]: r[1] for r in res}

    df = df_norm.copy()
    df["broker_id"]  = df["broker_code"].map(brokers)
    df["account_id"] = df["account_number"].map(accounts)
    df["product_id"] = df.apply(
        lambda r: prod_by_code.get(r["product_code"]) or prod_by_name.get(r["product_name"]),
        axis=1,
    )

    # quick sanity check to avoid NOT NULL failures
    if df["broker_id"].isna().any():
        missing = df.loc[df["broker_id"].isna(), "broker_code"].unique()
        raise RuntimeError(f"Missing broker_id for codes: {missing}. Check brokers table.")

    cols = [
        "broker_id","external_trade_id","account_id","product_id",
        "trade_date","delivery_month","side","quantity",
        "trade_price","market_price","variation_margin",
        "currency_code","as_of_date"
    ]
    df[cols].to_sql("trades", engine, if_exists="append", index=False)

def main():
    path = Path("Broker B Open Positions.csv")
    assert path.exists(), "File not found in project root."
    engine = create_engine("sqlite:///db/etrm.sqlite", future=True)

    df_raw = pd.read_csv(path, dtype=str)
    df_norm = normalize_broker_b(df_raw)
    df_norm["broker_code"] = "BKB"   # force broker code for Broker B
    upserts_and_insert(engine, df_norm)
    print("✅ Broker B loaded.")

if __name__ == "__main__":
    main()
