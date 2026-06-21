-- up
UPDATE users SET coins = ROUND(coins), pending_enclosure_coins = ROUND(pending_enclosure_coins);
