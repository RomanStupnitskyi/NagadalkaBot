import logging
import os

from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode


class ClientConfig:
	def __init__(self):
		self.TOKEN = os.getenv('CLIENT_TOKEN')
		self.DEFAULT = DefaultBotProperties(parse_mode=ParseMode.HTML)
		self.DROP_PENDING_UPDATES = True
		self.LOGGING_LEVEL = logging.INFO

class TelegramConfig:
	def __init__(self):
		self.OWNER_ID = int(os.getenv('OWNER_ID'))
		self.GROUP_ID = int(os.getenv('GROUP_ID'))

class MongoConfig:
	def __init__(self):
		self.URL = os.getenv('MONGODB_URL') or ""
