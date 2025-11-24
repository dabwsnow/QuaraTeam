import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

# Импортируем токен и роутеры
from config import BOT_TOKEN
from handlers import router as user_router

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GodBot")

async def main():
    """Главная функция для инициализации и запуска бота."""
    
    # Используем хранилище в оперативной памяти (подходит для FSM в небольших ботах)
    storage = MemoryStorage()

    # Настройки по умолчанию для бота
    default_properties = DefaultBotProperties(
        parse_mode=ParseMode.HTML, # Устанавливаем HTML-форматирование по умолчанию
    )

    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN, default=default_properties)
    dp = Dispatcher(storage=storage)

    # Включаем роутер с обработчиками (включая логику CAPTCHA)
    dp.include_router(user_router)

    # Удаление неактуального вебхука и ожидающих обновлений
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Бот запущен! Ожидание входящих обновлений...")
    
    # Запуск поллинга (ожидания входящих сообщений)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную.")
    except Exception as e:
        logger.error(f"Произошла ошибка при запуске бота: {e}", exc_info=True)