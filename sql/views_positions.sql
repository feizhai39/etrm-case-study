CREATE VIEW IF NOT EXISTS v_positions AS
SELECT
    a.account_number,
    p.product_name,
    t.delivery_month,
    t.currency_code,
    SUM(t.quantity) AS position_qty,
    AVG(NULLIF(t.trade_price,0)) AS avg_trade_price,
    AVG(NULLIF(t.market_price,0)) AS current_market_price,
    SUM(COALESCE(t.variation_margin, 0)) AS variation_margin_total
FROM trades t
JOIN accounts a   ON a.account_id = t.account_id
JOIN products p   ON p.product_id = t.product_id
GROUP BY a.account_number, p.product_name, t.delivery_month, t.currency_code;