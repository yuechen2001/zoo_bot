-- up
INSERT OR IGNORE INTO user_enclosures (user_id, habitat, level)
SELECT u.user_id, h.habitat, 1
FROM users u
JOIN (
    SELECT 'woodland' AS habitat UNION ALL
    SELECT 'savanna'             UNION ALL
    SELECT 'tropical'            UNION ALL
    SELECT 'aquatic'             UNION ALL
    SELECT 'tundra'              UNION ALL
    SELECT 'mythic'
) h;

-- down
-- non-reversible data backfill
