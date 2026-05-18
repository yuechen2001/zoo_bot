-- up
ALTER TABLE users ADD COLUMN catch_message_id INTEGER;
ALTER TABLE users ADD COLUMN catch_chat_id INTEGER;

-- down
SELECT 1;
