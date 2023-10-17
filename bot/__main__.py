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
	"""
	Set up logging for the NagadalkaBot application.
	This function configures the logging module to output log messages at the DEBUG level.
	"""
	logging.basicConfig(level=logging.DEBUG)


def setup_database(url: str) -> MongoClient:
	"""
	Connects to a MongoDB database using the given URL and returns a MongoClient instance.

	Args:
		url (str): The URL of the MongoDB database to connect to.

	Returns:
		MongoClient: A MongoClient instance connected to the specified database.

	Raises:
		ConnectionError: If the connection to the database fails.
	"""
	db = MongoClient(url)
	config = db.telegram.config.find_one()

	if not config:
		db.telegram.config.insert_one(
				{'group_id': 0, 'owner_id': os.getenv('OWNER_ID')}
		)

	return db


def setup_middlewares(dp: Dispatcher, db: MongoClient) -> None:
	"""
	Adds middlewares to the given dispatcher object.

	Args:
		dp (telegram.ext.Dispatcher): The dispatcher object to add middlewares to.
		db (pymongo.MongoClient): The MongoDB client object to use for database middleware.

	Returns:
		None
	"""
	dp.message.middleware(DatabaseMiddleware(db))
	dp.message.outer_middleware(IsAuthMiddleware(db))
	birthday_router.callback_query.middleware(DatabaseMiddleware(db))


async def setup_routers(bot: Bot, dp: Dispatcher, db: MongoClient) -> None:
	"""
	Sets up the routers for the bot.

	Args:
		bot (Bot): The bot instance.
		dp (Dispatcher): The dispatcher instance.
		db (MongoClient): The MongoDB client instance.

	Returns:
		None
	"""
	dp.include_routers(general_router, development_router, birthday_router)
	await birthday_router.emit_startup(bot, db)


async def setup_aiogram(bot: Bot, dispatcher: Dispatcher) -> None:
	"""
	Configures the aiogram library for use with the given bot and dispatcher.

	Args:
		bot (Bot): The aiogram Bot instance to use.
		dispatcher (Dispatcher): The aiogram Dispatcher instance to use.

	Returns:
		None
	"""
	logging.debug("Configuring aiogram...")

	DB_URL = os.getenv("DB_URL")
	if not '--production' in sys.argv and not '--use-prod-db' in sys.argv:
		DB_URL = os.getenv("TEST_DB_URL")

	database = setup_database(DB_URL)
	setup_middlewares(dispatcher, database)
	await setup_routers(bot, dispatcher, database)

	logging.info("Configured aiogram")


async def aiogram_on_startup_polling(dispatcher: Dispatcher, bot: Bot) -> None:
	"""
	Delete the webhook and set up polling for the bot using aiogram.

	Args:
		dispatcher (aiogram.Dispatcher): The dispatcher instance.
		bot (aiogram.Bot): The bot instance.

	Returns:
		None
	"""
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
