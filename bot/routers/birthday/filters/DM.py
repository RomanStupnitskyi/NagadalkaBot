from aiogram.filters import Filter
from aiogram.types.message import Message

class DM(Filter):
	async def __call__(self, message: Message) -> bool:
		return message.chat.type == 'private'