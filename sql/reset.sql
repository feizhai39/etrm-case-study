PRAGMA foreign_keys = OFF;

-- Drop existing tables & view if they exist
DROP VIEW IF EXISTS v_positions;
DROP TABLE IF EXISTS trades;
DROP TABLE IF EXISTS brokers;
DROP TABLE IF EXISTS accounts;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS currencies;

PRAGMA foreign_keys = ON;