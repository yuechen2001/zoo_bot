import os
from dotenv import load_dotenv

load_dotenv()

BOT_ENV = os.getenv("BOT_ENV", "dev")
_token_key = "BOT_TOKEN_PROD" if BOT_ENV == "prod" else "BOT_TOKEN_DEV"
BOT_TOKEN = os.getenv(_token_key) or os.getenv("BOT_TOKEN", "")
DATABASE_PATH = os.getenv("DATABASE_PATH", "zoo_bot.db")
PROMPT_INTERVAL_MINUTES = int(os.getenv("PROMPT_INTERVAL_MINUTES", "30"))
JOB_INTERVAL_MINUTES = int(os.getenv("JOB_INTERVAL_MINUTES", "1"))
HUNGER_INTERVAL_MINUTES = int(os.getenv("HUNGER_INTERVAL_MINUTES", "30"))
CHECKIN_WINDOW_MINUTES = int(os.getenv("CHECKIN_WINDOW_MINUTES", "15"))
CATCH_EXPIRY_MINUTES = int(os.getenv("CATCH_EXPIRY_MINUTES", "5"))
TRADE_EXPIRY_MINUTES = int(os.getenv("TRADE_EXPIRY_MINUTES", "10"))
TIMEZONE = os.getenv("TIMEZONE", "Asia/Shanghai")
INVESTMENT_HOURS = int(os.getenv("INVESTMENT_HOURS", "24"))
INVESTMENT_RETURN_RATE = float(os.getenv("INVESTMENT_RETURN_RATE", "0.25"))
BREED_READY_REMINDER_MINUTES = int(os.getenv("BREED_READY_REMINDER_MINUTES", "30"))

# Comma-separated Telegram user IDs allowed to use /admin commands
# e.g. ADMIN_IDS=123456789,987654321
ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
