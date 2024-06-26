from pymongo import MongoClient
from datetime import datetime
import logging
import asyncio
import json

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types.user import User
from aiogram import Bot

from .random_greeting import greeting_service


async def send_birthday_outcome(bot: Bot, database_client: MongoClient, user: User, group_id: int) -> None:
	birthday_data = {
		'user_id': user.id,
		'group_id': group_id
	}
	user_birthday = database_client.user.birthdays.find_one(birthday_data)
	try:
		database_client.user.birthdays.delete_one(birthday_data)

		greeted_by_list = []
		for user_id in user_birthday["greeted_by"]:
			member = await bot.get_chat_member(group_id, user_id)
			greeted_by_list.append("<a href=\"tg://user?id={0}\">{1}</a>".format(user_id, member.user.full_name if member else "invalid_user"))
		
		greeted_by_text = ", ".join(greeted_by_list) or "<code>🌌 Всесвіт</code>"
		await bot.send_message(
			user.id,
			f"📊 Привіт! Надсилаю підсумки твого дня народження\n\n🗂 Кількість привітань: <code>{len(user_birthday['greeted_by'])}</code>\n👥 Хто привітав: {greeted_by_text}")
	except Exception as error:
		logging.error(error)


async def birthday_outcome_async(delay: int, bot: Bot, database_client: MongoClient, user: User, group_id: int) -> None:
	logging.info(f"Waiting for birthday outcome in {delay} seconds")
	await asyncio.sleep(delay)
	await send_birthday_outcome(bot, database_client, user, group_id)


async def congratulate(bot: Bot, database_client: MongoClient, user: User, group_id: int) -> None:
	builder = InlineKeyboardBuilder()
	builder.button(text="🎁 Привітати", callback_data=json.dumps({ 'name': 'greet_button' }))
	builder.button(text="👥 Хто привітав?", callback_data=json.dumps({ 'name': 'who_greeted_button' }))

	message = await bot.send_message(
		group_id,
		'<b>🎉 Сьогодні день народження у</b> <a href="tg://user?id={0}">{1}</a>,\n\n{2}\n\n<b>👥 Привітали:</b> <code>0</code>'
			.format(user.id, user.full_name, greeting_service.get_random_greeting),
		reply_markup=builder.as_markup()
		)
	database_client.user.birthdays.insert_one({
		'user_id': user.id,
		'group_id': group_id,
		'message_id': message.message_id,
		'greeted_by': []
	})


async def congratulate_async(bot: Bot, group_id: int, user: User, database_client: MongoClient):
	"""
	A coroutine function that calculates the time until the user's next birthday and sleeps until it's time to congratulate them.

	Args:
	- bot (Bot): The bot instance.
	- db (MongoClient): The MongoDB client instance.
	- user (User): The user to congratulate.
	- user_data (dict): The user's data, including their birthday.

	Returns:
	- None
	"""
	user_data = database_client.user.data.find_one({ "id": user.id })
	now = datetime(*map(lambda x: int(x), datetime.now().strftime("%Y.%m.%d.%H.%M.%S").split(".")))
	birthday = user_data['birthday']
	current_birthday = datetime(now.year, birthday.month, birthday.day)

	if now.timestamp() >= (current_birthday.timestamp()):
		current_birthday = datetime(now.year+1, birthday.month, birthday.day)

	time_to_congratulate = current_birthday.timestamp() - datetime.now().timestamp()
	logging.info(f"Celebrating {user.full_name}'s ({user.id}) birthday will be in {time_to_congratulate} seconds.")

	try:
		await asyncio.sleep(time_to_congratulate)

		await congratulate(bot, database_client, user, group_id)
		await birthday_outcome_async(86399, bot, database_client, user, group_id)

		asyncio.create_task(congratulate_async(bot, group_id, user, database_client), name=user.id)
	except asyncio.CancelledError:
		logging.info(f"{user.full_name}'s ({user.id}) task was cancelled")
