import os
from telegram.ext import ApplicationBuilder, CommandHandler

TOKEN = os.getenv("TOKEN")

async def start(update, context):
    await update.message.reply_text("Я живой. Команда /start работает.")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.run_polling()
