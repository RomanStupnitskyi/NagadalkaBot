from abc import abstractmethod
from aiogram.types import TelegramObject
from typing import Any, Awaitable, Callable
from aiogram.dispatcher.middlewares.base import BaseMiddleware as AiogramMiddleware


class BaseMiddleware(AiogramMiddleware):
	def __init__(self, **kwargs):
		self._kwargs = kwargs

	async def __middleware__(self,
			handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
			event: TelegramObject,
			data: dict[str, Any]) -> Any:
		return await handler(event, data)
	
	async def __call__(self,
			handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
			event: TelegramObject,
			data: dict[str, Any]) -> Any:
		for key, value in self._kwargs.items():
			data[key] = value

		result = await self.__middleware__(handler, event, data)

		for key in self._kwargs.keys():
			del data[key]

		return result
