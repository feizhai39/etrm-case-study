# etl/normalize.py
import pandas as pd
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pandas")

def to_date_dayfirst(series):
    # Try day-first DD/MM/YY(YY); falls back safely
    return pd.to_datetime(series, dayfirst=True, errors="coerce").dt.date

def parse_delivery_yyyymm(code):
    # Handles '2504' -> '2025-04'
    if pd.isna(code): return None
    s = str(code).strip()
    if len(s) != 4 or not s.isdigit(): return None
    yy, mm = int(s[:2]), int(s[2:])
    return f"{2000+yy:04d}-{mm:02d}"

def _col(df, name):
    if name not in df.columns:
        raise KeyError(f"Missing column '{name}'. Available: {list(df.columns)}")
    return df[name]

def normalize_df(df, broker_code_default, mapping):
    df = df.copy()
    df.columns = df.columns.str.strip()
    for c in df.select_dtypes(include="object"):
        df[c] = df[c].str.strip()

    # numeric coercions (remove commas if any)
    for key in ["quantity","trade_price","market_price","variation_margin"]:
        src = mapping.get(key)
        if src in df.columns:
            df[src] = pd.to_numeric(df[src].astype(str).str.replace(",", ""), errors="coerce")

    out = pd.DataFrame()
    # broker code (prefer file, fallback)
    bsrc = mapping.get("broker_code")
    out["broker_code"] = (_col(df, bsrc).replace("", pd.NA).fillna(broker_code_default)
                          if bsrc in df.columns else broker_code_default)
    out["external_trade_id"] = df.index.astype(str)
    out["account_number"]    = _col(df, mapping["account_number"]).astype(str)
    out["product_name"]      = _col(df, mapping["product_name"]).astype(str)

    pc = mapping.get("product_code")
    out["product_code"] = (_col(df, pc).astype(str) if pc in df.columns else pd.NA)

    out["trade_date"]     = to_date_dayfirst(_col(df, mapping["trade_date"]))
    out["delivery_month"] = _col(df, mapping["delivery_date"]).map(parse_delivery_yyyymm)

    def norm_side(x):
        s = (str(x) or "").upper()
        return "BUY" if s.startswith("B") else ("SELL" if s.startswith("S") else pd.NA)
    out["side"] = _col(df, mapping["side"]).map(norm_side)

    out["quantity"] = pd.to_numeric(_col(df, mapping["quantity"]), errors="coerce")
    out.loc[out["side"].eq("SELL"), "quantity"] *= -1

    tp = mapping.get("trade_price")
    mp = mapping.get("market_price")
    vm = mapping.get("variation_margin")
    out["trade_price"]      = pd.to_numeric(df.get(tp), errors="coerce") if tp else pd.NA
    out["market_price"]     = pd.to_numeric(df.get(mp), errors="coerce") if mp else pd.NA
    out["variation_margin"] = pd.to_numeric(df.get(vm), errors="coerce") if vm else pd.NA

    out["currency_code"] = _col(df, mapping["currency"]).str.upper()
    out["as_of_date"]    = to_date_dayfirst(_col(df, mapping["as_of_date"]))

    return out