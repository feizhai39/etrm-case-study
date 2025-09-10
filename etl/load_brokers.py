import pandas as pd
from sqlalchemy import create_engine
from normalize import normalize_df

# Broker A mapping
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

# Broker B mapping
MAP_B = {
  "account_number": "Ledger Code",                 # acts like account
  "product_name": "Instrument Long Name",
  "product_code": "Instrument Code",               # optional but useful
  "trade_date": "Trade Date",
  "delivery_date": "Delivery/Prompt date",         # we'll turn into YYYY-MM
  "side": None,                                    # not provided; inferred from Volume sign
  "quantity": "Volume",
  "trade_price": "Price",
  "market_price": "Market Rate",
  "variation_margin": "Variation Margin",
  "currency": "Currency Code",
  "as_of_date": "Open position date",              # snapshot date
  "broker_code": None                               # file has no broker code; we'll use 'BKB'
}

engine = create_engine("sqlite:///db/etrm.sqlite", future=True)

# Load Broker A
df_a = pd.read_csv("Broker A Open Positions.csv")
df_a = normalize_df(df_a, "BKA", MAP_A)
df_a.to_sql("trades", engine, if_exists="append", index=False)

# Load Broker B
df_b = pd.read_csv("Broker B Open Positions.csv")
df_b = normalize_df(df_b, "BKB", MAP_B)
df_b.to_sql("trades", engine, if_exists="append", index=False)

print("✅ Trades loaded successfully!")