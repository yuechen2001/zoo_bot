-- up
INSERT OR IGNORE INTO user_enclosures (user_id, habitat, level)
SELECT user_id, 'desert', 1 FROM users;

-- down
DELETE FROM user_enclosures WHERE habitat = 'desert';
