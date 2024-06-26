import logging
from typing import Any, Awaitable, Callable

from aiogram.types.user import User
from aiogram.types import TelegramObject, Message, Update

from bot.Config import TelegramConfig
from .BaseMiddleware import BaseMiddleware


class IsUserMiddleware(BaseMiddleware):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)

	async def __middleware__(self,
			handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
			event: TelegramObject,
			data: dict[str, Any]) -> Any:
		user: User = data["event_from_user"]
		update: Update = data["event_update"]
		telegram_config: TelegramConfig = data["telegram_config"]

		if not user.is_bot:
			try:
				if not await user.bot.get_chat_member(telegram_config.GROUP_ID, user.id):
					return await update.message.reply("Permission denied")
				return await handler(event, data)
			except Exception as error:
				logging.error("An error occour while handling message middleware:\n{0}".format(error))
