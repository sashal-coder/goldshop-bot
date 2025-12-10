import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice
)

# 🔑 Токен и ID администратора
import os
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = 7880197257

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Главное меню (ReplyKeyboard)
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Купить голду"), KeyboardButton(text="Помощь")]
    ],
    resize_keyboard=True
)

# Хэндлер команды /start
async def start_handler(message: types.Message):
    await message.answer(
        "Привет 👋 Добро пожаловать в GoldShop!\nВыберите действие:",
        reply_markup=main_menu
    )
    logger.info(f"Пользователь @{message.from_user.username} запустил бота.")

# Обработка кнопки "Купить голду"
async def buy_gold_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="50 голды (25⭐)", callback_data="buy_50")],
        [InlineKeyboardButton(text="100 голды (50⭐)", callback_data="buy_100")],
        [InlineKeyboardButton(text="250 голды (125⭐)", callback_data="buy_250")],
        [InlineKeyboardButton(text="500 голды (250⭐)", callback_data="buy_500")]
    ])
    await message.answer("Выберите количество голды:", reply_markup=keyboard)
    logger.info(f"Пользователь @{message.from_user.username} открыл меню покупки.")

# Раздел "Помощь"
async def help_handler(message: types.Message):
    help_text = (
        "ℹ️ Инструкция по покупке:\n\n"
        "1️⃣ Нажмите «Купить голду» и выберите нужный пакет.\n"
        "2️⃣ Оплатите через Telegram Stars (⭐).\n"
        "3️⃣ После оплаты бот попросит отправить скриншот выставленного скина.\n"
        "4️⃣ Скрин пересылается админу для проверки.\n"
        "5️⃣ После подтверждения вы получите свой товар ✅.\n\n"
        "Если возникнут вопросы — пишите сюда 👉 @Anonimys07"
    )
    await message.answer(help_text)
    logger.info(f"Пользователь @{message.from_user.username} открыл раздел помощи.")

# Выставление счёта (Stars)
async def process_buy(callback_query: types.CallbackQuery):
    try:
        amount = int(callback_query.data.split("_")[1])
        prices_map = {50: 25, 100: 50, 250: 125, 500: 250}

        if amount not in prices_map:
            await callback_query.answer("❌ Ошибка: неизвестный пакет.", show_alert=True)
            logger.warning(f"Неизвестный пакет: {callback_query.data}")
            return

        stars_price = prices_map[amount]

        await bot.send_invoice(
            chat_id=callback_query.from_user.id,
            title=f"Покупка {amount} голды",
            description=f"{amount} голды",
            payload=f"order_{amount}",
            provider_token="STARS",   # заменишь на настоящий provider_token
            currency="XTR",
            prices=[LabeledPrice(label=f"{amount} голды", amount=stars_price * 1)]
        )
        await callback_query.answer()
        logger.info(f"Выставлен счёт пользователю @{callback_query.from_user.username} на {amount} голды.")
    except Exception as e:
        await callback_query.answer("⚠️ Ошибка при выставлении счёта.", show_alert=True)
        logger.error(f"Ошибка при выставлении счёта: {e}")

# Подтверждение оплаты
async def checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
    logger.info(f"PreCheckoutQuery от пользователя {pre_checkout_query.from_user.id} подтверждён.")

async def got_payment(message: types.Message):
    try:
        payload = message.successful_payment.invoice_payload
        package = payload.replace("order_", "")
        stars_paid = message.successful_payment.total_amount // 100

        await message.answer("✅ Оплата прошла! Отправьте скриншот выставленного скина.")
        await bot.send_message(
            ADMIN_ID,
            f"Покупатель @{message.from_user.username or message.from_user.id} оплатил {package} голды за {stars_paid}⭐."
        )
        logger.info(f"Оплата успешна: @{message.from_user.username} купил {package} голды за {stars_paid}⭐.")
    except Exception as e:
        await message.answer("⚠️ Ошибка при обработке оплаты.")
        logger.error(f"Ошибка при обработке оплаты: {e}")

# Получение скриншота
async def handle_photo(message: types.Message):
    try:
        await bot.send_photo(
            ADMIN_ID,
            message.photo[-1].file_id,
            caption=f"Скрин от @{message.from_user.username or message.from_user.id}"
        )
        await message.answer("Скрин получен, ожидайте подтверждения ✅")
        logger.info(f"Скриншот от @{message.from_user.username} переслан админу.")
    except Exception as e:
        await message.answer("⚠️ Ошибка при отправке скрина.")
        logger.error(f"Ошибка при пересылке фото: {e}")

# Регистрация хэндлеров
def register_handlers():
    dp.message.register(start_handler, Command("start"))
    dp.message.register(buy_gold_handler, lambda m: m.text == "Купить голду")
    dp.message.register(help_handler, lambda m: m.text == "Помощь")
    dp.callback_query.register(process_buy, lambda c: c.data.startswith("buy_"))
    dp.pre_checkout_query.register(checkout)
    dp.message.register(got_payment, lambda m: m.content_type == "successful_payment")
    dp.message.register(handle_photo, lambda m: m.content_type == "photo")

async def main():
    register_handlers()
    logger.info("Бот запущен и готов к работе.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())