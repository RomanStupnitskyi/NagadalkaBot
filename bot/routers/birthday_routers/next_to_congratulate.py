from typing import Any
from datetime import datetime

from aiogram import Router
from aiogram.types.message import Message
from aiogram.filters.command import Command

from bot.extensions.sorted_users import get_sorted_users


next_to_congratulate_router = Router(name='next_to_congratulate')


@next_to_congratulate_router.message(Command('next_to_congratulate'))
async def next_to_congratulate_command(message: Message, database_client: dict[str, Any], telegram_config: dict[str, Any]) -> None:
	next_to_congratulate = get_sorted_users(database_client)[0]
	now = datetime.now()

	coming_birthday: datetime | None = next_to_congratulate["birthday"]
	if coming_birthday:
		coming_birthday_date = datetime(now.year, coming_birthday.month, coming_birthday.day)
		if now.timestamp() > coming_birthday_date.timestamp():
			coming_birthday_date = datetime(now.year+1, coming_birthday.month, coming_birthday.day)

		age = coming_birthday_date.year - coming_birthday.year
		member = await message.bot.get_chat_member(telegram_config.GROUP_ID, int(next_to_congratulate.get('id')))
		user = member.user

		await message.reply(
			'🎉 Найближчий День Народження у <a href="tg://user?id={0}">{1}</a>, <b>{2}</b> він(вона) святкуватиме своє {3}-річчя'
				.format(
					user.id,
					user.full_name,
					coming_birthday_date.strftime("%d.%m.%Y"),
					age,
				)
			)
