-- up
-- Remove accidentally purchased special titles (title_expedition, title_eternal)
-- from user_purchases. These are quest/achievement rewards, not buyable items.
DELETE FROM user_purchases
WHERE item_key IN ('title_expedition', 'title_eternal');

-- Unequip the title for any user who had one of these active.
UPDATE users
SET active_title = NULL
WHERE active_title IN ('title_expedition', 'title_eternal');

-- down
-- No rollback — cannot restore deleted purchase records.
