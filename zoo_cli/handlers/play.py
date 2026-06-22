from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ContextTypes

from config import WEBAPP_URL


async def play_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    import db

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
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Open Zoo", url=WEBAPP_URL)]])
    await update.message.reply_text("Tap below to open your zoo!", reply_markup=kb)
