-- Realised PnL day by day, with the band that day carried. Feeds the time
-- series chart, and shows whether the effect is spread across the window or
-- comes from a few standout sessions.
SELECT
    trade_date,
    sentiment,
    COUNT(*)                    AS trade_count,
    ROUND(SUM(closed_pnl), 2)   AS total_pnl,
    ROUND(AVG(closed_pnl), 2)   AS avg_pnl
FROM trades
GROUP BY trade_date, sentiment
ORDER BY trade_date;
