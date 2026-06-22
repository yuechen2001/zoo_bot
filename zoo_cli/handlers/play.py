import hmac
import hashlib
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ContextTypes

from config import BOT_TOKEN, WEBAPP_URL
import db


async def play_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("Use /start first to join the zoo!")
        return
    if not WEBAPP_URL:
        await update.message.reply_text("The zoo web app isn't set up yet. Stay tuned!")
        return
    if update.message.chat.type == "private":
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🎮 Open Zoo", web_app=WebAppInfo(url=WEBAPP_URL))]]
        )
    else:
        payload = f"{user_id}:{int(time.time())}"
        sig = hmac.new(BOT_TOKEN.encode(), payload.encode(), hashlib.sha256).hexdigest()
        url = f"{WEBAPP_URL}?token={payload}:{sig}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Open Zoo", url=url)]])
    await update.message.reply_text("Tap below to open your zoo!", reply_markup=kb)
