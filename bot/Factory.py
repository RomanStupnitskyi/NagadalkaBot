import asyncio
import logging

from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher
from pymongo import MongoClient

from .routers import routers, birthday_router
from .Config import ClientConfig, TelegramConfig, MongoConfig
from .middlewares.IsUser import IsUserMiddleware, BaseMiddleware


class Config:
	def __init__(self):
		self.client = ClientConfig()
		self.mongodb = MongoConfig()
		self.telegram = TelegramConfig()

class Factory:
	def __init__(self):
		self.config = Config()
		self.storage = MemoryStorage()
		self.database_client = MongoClient(self.config.mongodb.URL)

		self.dp = Dispatcher(storage=self.storage)
		self.bot = Bot(
			token=self.config.client.TOKEN,
			default=self.config.client.DEFAULT
		)

	def setup_logging(self) -> None:
		logging.basicConfig(level=self.config.client.LOGGING_LEVEL)

	def setup_middlewares(self) -> None:
		self.dp.message.middleware(IsUserMiddleware(database_client=self.database_client, telegram_config=self.config.telegram))
		self.dp.callback_query.middleware(BaseMiddleware(database_client=self.database_client, telegram_config=self.config.telegram))
	
	async def setup_routers(self) -> None:
		self.dp.include_routers(*routers)
		await birthday_router.emit_startup(self.bot, self.database_client, self.config.telegram.GROUP_ID)
	
	async def setup_aiogram(self) -> None:
		logging.info("Configuring aiogram...")

		self.setup_middlewares()
		await self.setup_routers()

		logging.info("Aiogram is configured")
	
	async def aiogram_on_startup_polling(self) -> None:
		await self.bot.delete_webhook(drop_pending_updates=self.config.client.DROP_PENDING_UPDATES)
		await self.setup_aiogram()

	def start(self) -> None:
		self.setup_logging()
		self.dp.startup.register(self.aiogram_on_startup_polling)

		asyncio.run(self.dp.start_polling(self.bot))
