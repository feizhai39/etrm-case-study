PRAGMA foreign_keys = ON;

CREATE TABLE brokers (
  broker_id INTEGER PRIMARY KEY,
  broker_code TEXT UNIQUE NOT NULL,
  broker_name TEXT NOT NULL
);

CREATE TABLE accounts (
  account_id INTEGER PRIMARY KEY,
  account_number TEXT UNIQUE NOT NULL
);

CREATE TABLE products (
  product_id INTEGER PRIMARY KEY,
  product_code TEXT,
  product_name TEXT NOT NULL
);

CREATE TABLE currencies (
  currency_code TEXT PRIMARY KEY
);

CREATE TABLE trades (
  trade_id INTEGER PRIMARY KEY,
  broker_id INTEGER NOT NULL REFERENCES brokers(broker_id),
  external_trade_id TEXT,
  account_id INTEGER NOT NULL REFERENCES accounts(account_id),
  product_id INTEGER NOT NULL REFERENCES products(product_id),
  trade_date DATE NOT NULL,
  delivery_month TEXT NOT NULL,
  side TEXT CHECK (side IN ('BUY','SELL')),
  quantity REAL NOT NULL,
  trade_price REAL,
  market_price REAL,
  variation_margin REAL,
  currency_code TEXT NOT NULL REFERENCES currencies(currency_code),
  as_of_date DATE NOT NULL
);