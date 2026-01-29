import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

ADMIN_IDS = {444694124, 7850041157}

USER_SHABELNIK = 63158924
USER_BOTH = 7850041157


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    keyboard = [
        [InlineKeyboardButton("Календарь", url="https://clck.ru/3MscXu")],
        [InlineKeyboardButton("Добавить мероприятие", url="https://clck.ru/3MrvFT")],
        [InlineKeyboardButton("Заявка на вход", url="https://forms.yandex.ru/cloud/697743ab068ff06061e8a02e")],
        [InlineKeyboardButton("Заявка", url="https://forms.yandex.ru/cloud/65cc7cb92530c22a292928c9/?page=1")],
        [InlineKeyboardButton("Телефонный справочник", url="https://sks-bot.ru/employee")]
    ]

    # кнопка для 63158924
    if user_id == USER_SHABELNIK:
        keyboard.append([
            InlineKeyboardButton("Мероприятия Шабельник В.В.", url="https://clck.ru/3Ms2mH")
        ])

    # кнопки для 7850041157
    if user_id == USER_BOTH:
        keyboard.append([
            InlineKeyboardButton("Мероприятия Шабельник В.В.", url="https://clck.ru/3Ms2mH")
        ])
        keyboard.append([
            InlineKeyboardButton("Мероприятия Солодилова Л.А.", url="https://clck.ru/3Ms33K")
        ])

    # админка для администраторов
    if user_id in ADMIN_IDS:
        keyboard.append([
            InlineKeyboardButton("⚙ Админ-панель", callback_data="admin_panel")
        ])

    await update.message.reply_text(
        "Добрый день!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.run_polling()
