from typing import Any, Awaitable, Callable
from pymongo import MongoClient

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class DatabaseMiddleware(BaseMiddleware):
	def __init__(self, database: MongoClient) -> None:
		self.db = database

	
	async def __call__(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: dict[str, Any]
    ) -> Any:
		data["db"] = self.db
		result = await handler(event, data)
		del data["db"]
		return result
