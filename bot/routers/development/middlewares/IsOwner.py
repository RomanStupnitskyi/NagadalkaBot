from typing import Any, Awaitable, Callable
import os

from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject
from aiogram.types.user import User
from aiogram.types.chat import Chat


class IsOwnerMiddleware(BaseMiddleware):
	async def __call__(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: dict[str, Any]
    ) -> Any:
		user: User = data["event_from_user"]
		chat: Chat = data["event_chat"]
		bot: Bot = data["bot"]

		if str(user.id) != os.getenv("OWNER_ID"):
			await bot.send_message(chat.id, "Permission denied")
			return None

		result = await handler(event, data)
		return result