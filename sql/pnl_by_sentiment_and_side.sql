-- The headline table: on days the market felt a certain way, did the buyer or
-- the seller earn more? Ordered fear-to-greed so the gradient is readable.
SELECT
    sentiment,
    side,
    COUNT(*)                        AS trade_count,
    ROUND(AVG(closed_pnl), 2)       AS avg_pnl,
    ROUND(SUM(closed_pnl), 2)       AS total_pnl,
    ROUND(SUM(size_usd), 2)         AS traded_volume_usd
FROM trades
GROUP BY sentiment, side
ORDER BY
    CASE sentiment
        WHEN 'Extreme Fear'  THEN 1
        WHEN 'Fear'          THEN 2
        WHEN 'Neutral'       THEN 3
        WHEN 'Greed'         THEN 4
        WHEN 'Extreme Greed' THEN 5
        ELSE 6
    END,
    side;
