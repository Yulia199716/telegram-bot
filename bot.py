from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = "8219826850:AAEnU6GZBD8NNaaN_uO7znBsOVuRa3RKAJU"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
    [InlineKeyboardButton("Календарь", url="https://clck.ru/3MscXu")],
    [InlineKeyboardButton("Добавить мероприятие", url="https://clck.ru/3MrvFT")],
    [InlineKeyboardButton("Заявка на вход", url="https://forms.yandex.ru/cloud/697743ab068ff06061e8a02e")],
    [InlineKeyboardButton("Заявка на ВКС", url="https://forms.yandex.ru/cloud/65cc7cb92530c22a292928c9/?page=1")],
    [InlineKeyboardButton("Телефонный справочник", url="https://sks-bot.ru/employee")]
]


    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Добро пожаловать!",
        reply_markup=reply_markup
    )

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))

print("Бот запущен...")
app.run_polling()
