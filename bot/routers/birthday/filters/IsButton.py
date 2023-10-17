from aiogram.filters.callback_data import CallbackQueryFilter
from aiogram.types.callback_query import CallbackQuery
import json


class IsButton(CallbackQueryFilter):
	def __init__(self, button_name: str) -> None:
		self.button_name = button_name

	async def __call__(self, callback: CallbackQuery) -> bool:
		try:
			data = json.loads(callback.data)
			return data["name"] == self.button_name
		except Exception as error:
			return self.button_name == callback.data