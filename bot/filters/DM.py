from aiogram.filters import Filter
from aiogram.types.message import Message
from aiogram.types.callback_query import CallbackQuery


class MessageDM(Filter):
	async def __call__(self, message: Message) -> bool:
		return message.chat.type == 'private'

class CallbackDM(Filter):
	async def __call__(self, callback: CallbackQuery) -> bool:
		return callback.message.chat.type == 'private'
