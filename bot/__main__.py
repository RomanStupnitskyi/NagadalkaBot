from pymongo import MongoClient
from dotenv import load_dotenv
import asyncio
import logging
import sys
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from middlewares import DatabaseMiddleware, IsAuthMiddleware
from routers import general_router, development_router, birthday_router


def setup_logging() -> None:
	logging.basicConfig(level=logging.DEBUG)


def setup_database() -> MongoClient:
	return MongoClient(os.getenv("DB_URL"))


def setup_middlewares(dp: Dispatcher, db: MongoClient) -> None:
	dp.message.middleware(DatabaseMiddleware(db))
	dp.message.outer_middleware(IsAuthMiddleware(db))


async def setup_routers(bot: Bot, dp: Dispatcher, db: MongoClient) -> None:
	dp.include_routers(general_router, development_router, birthday_router)
	await birthday_router.emit_startup(bot, db)


async def setup_aiogram(bot: Bot, dispatcher: Dispatcher) -> None:
	logging.debug("Configuring aiogram...")

	database = setup_database()
	setup_middlewares(dispatcher, database)
	await setup_routers(bot, dispatcher, database)

	logging.info("Configured aiogram")
	

async def aiogram_on_startup_polling(dispatcher: Dispatcher, bot: Bot) -> None:
	await bot.delete_webhook(drop_pending_updates=True)
	await setup_aiogram(bot, dispatcher)


def main() -> None:
	if not '--production' in sys.argv:
		load_dotenv()

	setup_logging()
	bot = Bot(os.getenv("BOT_TOKEN"), parse_mode="HTML")
	storage = MemoryStorage()

	dp = Dispatcher(storage=storage)
	dp.startup.register(aiogram_on_startup_polling)

	asyncio.run(dp.start_polling(bot))


if __name__ == "__main__":
	main()
