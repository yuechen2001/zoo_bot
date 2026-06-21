-- up
-- Randomize stat_speed, stat_rarity, stat_temperament for all existing animals
-- that still have the default value of 50 (i.e. pre-genetics animals).
-- ABS(RANDOM()) % 41 + 35 gives a uniform integer in [35, 75].
UPDATE animals
SET
    stat_speed       = ABS(RANDOM()) % 41 + 35,
    stat_rarity      = ABS(RANDOM()) % 41 + 35,
    stat_temperament = ABS(RANDOM()) % 41 + 35
WHERE stat_speed = 50 AND stat_rarity = 50 AND stat_temperament = 50;

-- down
-- No rollback — cannot recover the original random values.
