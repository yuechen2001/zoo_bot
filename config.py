import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DATABASE_PATH = os.getenv("DATABASE_PATH", "zoo_bot.db")
PROMPT_INTERVAL_MINUTES = int(os.getenv("PROMPT_INTERVAL_MINUTES", "30"))
CHECKIN_WINDOW_MINUTES = int(os.getenv("CHECKIN_WINDOW_MINUTES", "15"))
CATCH_EXPIRY_MINUTES   = int(os.getenv("CATCH_EXPIRY_MINUTES", "5"))
TIMEZONE = os.getenv("TIMEZONE", "Asia/Shanghai")

# Comma-separated Telegram user IDs allowed to use /admin commands
# e.g. ADMIN_IDS=123456789,987654321
ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}
