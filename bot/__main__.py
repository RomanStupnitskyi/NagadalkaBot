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


def setup_database(url: str) -> MongoClient:
	db = MongoClient(url)
	config = db.telegram.config.find_one()

	if not config:
		db.telegram.config.insert_one({ 'group_id': 0, 'owner_id': os.getenv('OWNER_ID')  })

	return db


def setup_middlewares(dp: Dispatcher, db: MongoClient) -> None:
	dp.message.middleware(DatabaseMiddleware(db))
	dp.message.outer_middleware(IsAuthMiddleware(db))


async def setup_routers(bot: Bot, dp: Dispatcher, db: MongoClient) -> None:
	dp.include_routers(general_router, development_router, birthday_router)
	await birthday_router.emit_startup(bot, db)


async def setup_aiogram(bot: Bot, dispatcher: Dispatcher) -> None:
	logging.debug("Configuring aiogram...")

	DB_URL = os.getenv("DB_URL")
	if not '--production' in sys.argv and not '--use-prod-db' in sys.argv:
		DB_URL = os.getenv("TEST_DB_URL")

	database = setup_database(DB_URL)
	setup_middlewares(dispatcher, database)
	await setup_routers(bot, dispatcher, database)

	logging.info("Configured aiogram")
	

async def aiogram_on_startup_polling(dispatcher: Dispatcher, bot: Bot) -> None:
	await bot.delete_webhook(drop_pending_updates=True)
	await setup_aiogram(bot, dispatcher)


def main() -> None:
	if not '--hosting' in sys.argv:
		load_dotenv()
		
	BOT_TOKEN = os.getenv("BOT_TOKEN")

	if not '--production' in sys.argv:
		BOT_TOKEN = os.getenv("TEST_BOT_TOKEN")

	setup_logging()
	bot = Bot(BOT_TOKEN, parse_mode="HTML")
	storage = MemoryStorage()

	dp = Dispatcher(storage=storage)
	dp.startup.register(aiogram_on_startup_polling)

	asyncio.run(dp.start_polling(bot))


if __name__ == "__main__":
	main()
