import json
import asyncio
import logging
from typing import Any
from datetime import datetime
from pymongo import MongoClient
from pymongo.collection import Collection

from aiogram import Router, Bot
from aiogram.types.message import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters.command import Command
from aiogram.filters.state import StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.types.callback_query import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.filters.DM import MessageDM, CallbackDM
from bot.filters.Group import Group
from bot.filters.IsButton import IsButton
from bot.extensions.congratulate import congratulate_async, birthday_outcome_async
from .birthday_routers import routers


birthday_router = Router(name="birthday")
birthday_router.include_routers(*routers)


class UserData(StatesGroup):
	birthday = State()


@birthday_router.message(Command("birthday"), Group())
async def birthday_group_command(message: Message, database_client: MongoClient) -> None:
	collection: Collection = database_client.user.data
	if message.reply_to_message and not message.reply_to_message.from_user.is_bot:
		user = message.reply_to_message.from_user
		user_data = collection.find_one({ 'id': user.id })

		if not user_data:
			await message.reply('<code>{0}</code> ще не народився(-лась)'.format(user.full_name))
			return None
		
		await message.reply(
			'🎁 День Народження <code>{0}</code> - {1}'
				.format(
					user.full_name,
					user_data['birthday'].strftime("%d.%m.%Y")
				)
			)
		return None

	bot = await message.bot.get_me()
	user = message.from_user
	user_data = collection.find_one({ "id": message.from_user.id })

	if not user_data:
		button = InlineKeyboardButton(text="Додати свій День Народження", url="https://t.me/{0}".format(bot.username))
		markup = InlineKeyboardMarkup(inline_keyboard=[[button]])
		await message.reply('❓ Я не знаю коли в тебе день народження', reply_markup=markup)
		return None
	
	await message.reply(
		"🎁 Твій день народження - <b>{0}</b>"
			.format(user_data['birthday'].strftime("%d.%m.%Y"))
		)


@birthday_router.message(Command("birthday"), StateFilter(None), MessageDM())
async def birthday_command(message: Message, database_client: MongoClient, state: FSMContext) -> None:
	collection: Collection = database_client.user.data
	user_data = collection.find_one({ "id": message.from_user.id })

	if user_data:
		builder = InlineKeyboardBuilder()
		builder.button(text="✏️ Змінити дату", callback_data=json.dumps({ 'name': 'update_birthday_button' }))
		await message.reply(
			"🎁 Твій день народження - <b>{0}</b>"
				.format(user_data['birthday'].strftime("%d.%m.%Y")),
			reply_markup=builder.as_markup()
			)
		return None
	
	await state.set_state(UserData.birthday)
	await message.answer("🎈 Відправ дату в форматі <b>dd.mm.yyyy</b> (наприклад, 31.12.2006)")


@birthday_router.callback_query(IsButton("update_birthday_button"), CallbackDM())
async def update_birthday_button(callback: CallbackQuery, state: FSMContext) -> None:
	await state.set_state(UserData.birthday)
	await callback.message.edit_reply_markup()
	await callback.message.edit_text("🎈 Відправ дату в форматі <b>dd.mm.yyyy</b> (наприклад, 31.12.2006)", show_alert=True)


@birthday_router.message(StateFilter(UserData.birthday), MessageDM())
async def birthday_handler(message: Message, database_client: dict[str, Any], telegram_config: dict[str, Any], state: FSMContext) -> None:
	try:
		user = message.from_user
		user_data = { "id": user.id }
		collection = database_client.user.data
		date_format = "%d.%m.%Y"

		date = datetime.strptime(message.text, date_format)
		await state.clear()
		if collection.find_one(user_data):
			collection.update_one({ "id": user.id }, { "$set": { "birthday": date } })
			await message.answer(f"✅ Твоє день народження оновлено на {date.strftime(date_format)}")
		else:
			collection.insert_one({ **user_data, "birthday": date })
			await message.answer(f"✅ Твоє день народження записано, {date.strftime(date_format)}")

		task: asyncio.Task[Any] = next((task for task in asyncio.all_tasks() if task.get_name() == str(user.id)), None)
		if task:
			task.cancel()
			logging.info(f"Cancelling task '{user.id}'...")
	
		user_data = collection.find_one({ 'id': user.id })
		asyncio.create_task(congratulate_async(message.bot, telegram_config.GROUP_ID, user, database_client), name=user.id)

	except ValueError:
		await message.reply("🔄 Ви вказали неправильно дату, напишіть ще раз")
	except Exception as error:
		logging.error(error)
		await message.reply("Щось пішло не так під час виконання")


@birthday_router.startup()
async def startup_handler(bot: Bot, database_client: MongoClient = None, group_id: int = None) -> None:
	try:
		if not database_client or not group_id:
			return None

		for user in database_client.user.data.find():
			if not user.get('birthday'):
				continue

			member = await bot.get_chat_member(group_id, user['id'])
			asyncio.create_task(congratulate_async(bot, group_id, member.user, database_client), name=user['id'])
	
		for user_birthday in database_client.user.birthdays.find():
			now =  datetime.now()
			delay = datetime(now.year, now.month, now.day, 20, 48, 0).timestamp() - now.timestamp()
			member = await bot.get_chat_member(group_id, user['id'])

			# delay = datetime(now.year, now.month, now.day, 23, 59, 59) - now.timestamp()
			asyncio.create_task(birthday_outcome_async(delay, bot, database_client, member.user, group_id))
	except Exception as error:
		logging.error('Birthday system cencelled:')
		logging.error(error)
