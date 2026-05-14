from telegram import Update
from telegram.ext import ContextTypes
import db


async def name_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id

    if not ctx.args or len(ctx.args) < 2 or not ctx.args[0].isdigit():
        await update.message.reply_text("Usage: /name <number> <nickname>\nExample: /name 1 Fluffy")
        return

    position = int(ctx.args[0])
    nickname = " ".join(ctx.args[1:])[:20]
    animal = db.get_animal_by_position(tg_id, position)

    if not animal:
        count = len(db.get_animals(tg_id))
        await update.message.reply_text(f"No animal at #{position}. You have {count} animal(s).")
        return

    with db.get_conn() as conn:
        conn.execute(
            "UPDATE animals SET nickname = ? WHERE animal_id = ?",
            (nickname, animal["animal_id"]),
        )

    await update.message.reply_text(
        f"{animal['emoji']} Animal #{position} is now called *{nickname}*!",
        parse_mode="Markdown",
    )
