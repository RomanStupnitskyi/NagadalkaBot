from typing import Any, Awaitable, Callable
from pymongo import MongoClient
import logging

from aiogram.enums.chat_member_status import ChatMemberStatus
from aiogram.types.message import Message
from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject
from aiogram.types.user import User
from aiogram.types.chat import Chat

class IsAuthMiddleware(BaseMiddleware):
	def __init__(self, database: MongoClient) -> None:
		self.db = database

	async def __call__(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: dict[str, Any]
    ) -> Any:
		user: User = data['event_from_user']
		event_chat: Chat = data['event_chat']
		message: Message = data['event_update'].message
		bot: Bot = data['bot']

		if user.is_bot:
			return None

		config = self.db.telegram.config.find_one()
		group_id = config.get('group_id');
		owner_id = config.get('owner_id')
		
		try:
			member = await bot.get_chat_member(group_id, user.id)
			if member.status == ChatMemberStatus.LEFT:
				if self.db.user.data.find_one({ 'id': user.id }):
					self.db.user.data.delete_one({ 'id': user.id })
				
				await message.reply('Permission denied')
				return None

			collection = self.db.user.data
			userData = collection.find_one({ "id": user.id })

			if not userData:
				userData = collection.insert_one({ "id": user.id })

			result = await handler(event, data)
			return result
		
		except Exception as error:
			logging.error(error)

			if user.id == int(owner_id):
				collection = self.db.user.data
				userData = collection.find_one({ "id": user.id })

				if not userData:
					userData = collection.insert_one({ "id": user.id })

				result = await handler(event, data)
				return result
			else:
				await bot.send_message(event_chat.id, "Сталась неочікувана помилка :(")
