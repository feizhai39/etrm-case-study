# etl/load_broker_a_positions.py
import pandas as pd
from sqlalchemy import create_engine, text
from pathlib import Path
from normalize import normalize_df

MAP_A = {
  "account_number": "Client Code",
  "product_name": "Commodity Name",
  "product_code": "Commodity Code",
  "trade_date": "Trade Date",
  "delivery_date": "Delivery Month/Year",
  "side": "Bought or Sold",
  "quantity": "Quantity",
  "trade_price": "Trade Price",
  "market_price": "Current Price",
  "variation_margin": "Variation Margin Amount",
  "currency": "Transaction Currency",
  "as_of_date": "Input Date",
  "broker_code": "Broker Code"
}

def upserts_and_insert(engine, df_norm):
    with engine.begin() as conn:
        # dims
        for b in df_norm["broker_code"].dropna().unique():
            conn.execute(text(
                "INSERT OR IGNORE INTO brokers(broker_code, broker_name) VALUES (:c, :n)"
            ), {"c": b, "n": "Broker A"})
        for ccy in df_norm["currency_code"].dropna().unique():
            conn.execute(text("INSERT OR IGNORE INTO currencies(currency_code) VALUES (:ccy)"),
                         {"ccy": ccy})
        for acct in df_norm["account_number"].dropna().unique():
            conn.execute(text("INSERT OR IGNORE INTO accounts(account_number) VALUES (:a)"),
                         {"a": acct})
        for row in df_norm[["product_code","product_name"]].drop_duplicates().itertuples(index=False):
            pc, pn = row
            if pc:
                conn.execute(text(
                    "INSERT OR IGNORE INTO products(product_code, product_name) VALUES (:pc,:pn)"
                ), {"pc": pc, "pn": pn or pc})
            else:
                conn.execute(text(
                    "INSERT OR IGNORE INTO products(product_name) VALUES (:pn)"
                ), {"pn": pn or "UNKNOWN"})

    # resolve FKs
    with engine.begin() as conn:
        # brokers
        res = conn.execute(text("SELECT broker_code, broker_id FROM brokers")).fetchall()
        brokers = {r[0]: r[1] for r in res}

        # accounts
        res = conn.execute(text("SELECT account_number, account_id FROM accounts")).fetchall()
        accounts = {r[0]: r[1] for r in res}

        # products
        prows = conn.execute(text("SELECT product_id, product_code, product_name FROM products")).fetchall()
        prod_by_code = {r[1]: r[0] for r in prows if r[1]}
        prod_by_name = {r[2]: r[0] for r in prows if r[2]}

    df = df_norm.copy()
    df["broker_id"]  = df["broker_code"].map(brokers)
    df["account_id"] = df["account_number"].map(accounts)
    df["product_id"] = df.apply(lambda r: prod_by_code.get(r["product_code"]) or prod_by_name.get(r["product_name"]), axis=1)

    cols = ["broker_id","external_trade_id","account_id","product_id",
            "trade_date","delivery_month","side","quantity",
            "trade_price","market_price","variation_margin",
            "currency_code","as_of_date"]

    df[cols].to_sql("trades", engine, if_exists="append", index=False)

def main():
    path = Path("Broker A Open Positions.csv")
    assert path.exists(), "File not found in project root."
    engine = create_engine("sqlite:///db/etrm.sqlite", future=True)
    df_raw = pd.read_csv(path, dtype=str)
    df_norm = normalize_df(df_raw, "BKA", MAP_A)
    upserts_and_insert(engine, df_norm)
    print("✅ Broker A loaded.")

if __name__ == "__main__":
    main()