-- The project's claim, as one number per band: buy PnL minus sell PnL.
-- "Be greedy when others are fearful" predicts this is positive under fear and
-- negative under greed. Computed in SQL so the finding does not depend on the
-- pandas code being right.
WITH sides AS (
    SELECT
        sentiment,
        AVG(CASE WHEN side = 'BUY'  THEN closed_pnl END) AS buy_pnl,
        AVG(CASE WHEN side = 'SELL' THEN closed_pnl END) AS sell_pnl
    FROM trades
    GROUP BY sentiment
)
SELECT
    sentiment,
    ROUND(buy_pnl, 2)                AS buy_pnl,
    ROUND(sell_pnl, 2)               AS sell_pnl,
    ROUND(buy_pnl - sell_pnl, 2)     AS buy_minus_sell,
    CASE WHEN buy_pnl > sell_pnl THEN 'BUY' ELSE 'SELL' END AS favours
FROM sides
ORDER BY
    CASE sentiment
        WHEN 'Extreme Fear'  THEN 1
        WHEN 'Fear'          THEN 2
        WHEN 'Neutral'       THEN 3
        WHEN 'Greed'         THEN 4
        WHEN 'Extreme Greed' THEN 5
        ELSE 6
    END;
