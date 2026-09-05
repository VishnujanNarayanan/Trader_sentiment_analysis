-- The Limitations section says costs are excluded from closed PnL. This puts a
-- number on that: what share of the average trade's profit does its own fee
-- consume? An edge smaller than its costs is not an edge.
SELECT
    sentiment,
    COUNT(*)                                        AS trade_count,
    ROUND(AVG(closed_pnl), 2)                       AS avg_pnl,
    ROUND(AVG(fee), 4)                              AS avg_fee,
    ROUND(AVG(closed_pnl) - AVG(fee), 2)            AS avg_pnl_net_of_fee,
    CASE WHEN AVG(closed_pnl) > 0
         THEN ROUND(100.0 * AVG(fee) / AVG(closed_pnl), 2) END AS fee_pct_of_pnl
FROM trades
GROUP BY sentiment
ORDER BY fee_pct_of_pnl DESC;
