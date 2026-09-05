-- How much of the measured effect is a handful of traders?
--
-- The Limitations section flags survivorship and selection but never quantifies
-- them. If the top few accounts carry most of the PnL, the "traders make money
-- buying into fear" finding is really "these traders did", which is a much
-- weaker claim.
WITH per_account AS (
    SELECT account,
           COUNT(*)         AS trades,
           SUM(closed_pnl)  AS pnl
    FROM trades
    GROUP BY account
)
SELECT
    account,
    trades,
    ROUND(pnl, 2)                                              AS pnl,
    ROUND(100.0 * pnl / (SELECT SUM(closed_pnl) FROM trades), 2) AS pct_of_total_pnl
FROM per_account
ORDER BY pnl DESC
LIMIT 20;
