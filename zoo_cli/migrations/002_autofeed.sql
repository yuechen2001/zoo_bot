-- up
ALTER TABLE users ADD COLUMN autofeed_threshold INTEGER DEFAULT NULL;
ALTER TABLE users ADD COLUMN autofeed_max_coins INTEGER DEFAULT NULL;

-- down
ALTER TABLE users DROP COLUMN autofeed_threshold;
ALTER TABLE users DROP COLUMN autofeed_max_coins;
