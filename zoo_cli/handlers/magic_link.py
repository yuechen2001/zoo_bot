import hmac
import hashlib
import time

from telegram import Update
from telegram.ext import ContextTypes

from config import BOT_TOKEN, WEBAPP_URL
from game.constants import WEB_LINK_EXPIRY_HOURS
import db


async def weblink_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not db.get_user(user_id):
        await update.message.reply_text("Use /start first to join the zoo!")
        return
    if not WEBAPP_URL:
        await update.message.reply_text("Web app isn't configured yet.")
        return
    payload = f"{user_id}:{int(time.time())}"
    sig = hmac.new(BOT_TOKEN.encode(), payload.encode(), hashlib.sha256).hexdigest()
    token = f"{payload}:{sig}"
    url = f"{WEBAPP_URL}?token={token}"
    await update.message.reply_text(
        f"🔗 Open your zoo in any browser (valid {WEB_LINK_EXPIRY_HOURS}h):\n{url}\n\n"
        "⚠️ Don't share this link — it gives full access to your zoo."
    )
