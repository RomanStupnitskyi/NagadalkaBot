from pymongo.collection import Collection
from pymongo import MongoClient
from datetime import datetime
import asyncio
import logging

from aiogram.fsm.state import State, StatesGroup
from aiogram.filters.state import StateFilter
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types.message import Message
from aiogram.types.user import User
from aiogram import Router, Bot

from .filters.DM import DM
from .filters.Group import Group


birthday_router = Router(name="birthday")

class UserData(StatesGroup):
	birthday = State()


async def congratulate(bot: Bot, db: MongoClient, user: User, birthday: datetime) -> None:
	chat_id = db.telegram.config.find_one().get('group_id')
	age = datetime.now().year - birthday.year
	await bot.send_message(
		chat_id,
		'🎉 Вітаємо нашого співвітчизника(-цю) <a href="tg://user?id={0}">{1}</a> з Днем Народження, з його(її) {2}-річчям!!!'
			.format(user.id, user.full_name, age)
		)


async def congratulate_async(bot: Bot, db: MongoClient, user: User, user_data):
	now = datetime(*map(lambda x: int(x), datetime.now().strftime("%Y.%m.%d").split(".")))
	birthday = user_data['birthday']
	current_birthday = datetime(now.year, birthday.month, birthday.day)

	if now.timestamp() >= (current_birthday.timestamp()):
		current_birthday = datetime(now.year+1, birthday.month, birthday.day)

	time_to_congratulate =  current_birthday.timestamp() - datetime.now().timestamp() + 37500
	
	await asyncio.sleep(time_to_congratulate)
	await congratulate(bot, user, birthday)

	asyncio.create_task(congratulate_async(bot, db, user, user_data))


@birthday_router.message(Command("birthday"), Group())
async def birthday_group_command(message: Message, db: MongoClient) -> None:
	collection: Collection = db.user.data
	if message.reply_to_message and not message.reply_to_message.from_user.is_bot:
		user = message.reply_to_message.from_user
		user_data = collection.find_one({ 'id': user.id })

		if not user_data or not user_data.get('birthday'):
			await message.reply('<code>{0}</code> ще не народився(-лась)'.format(user.full_name))
			return None
		
		await message.reply(
			'🎁 День Народження <code>{0}</code> - {1}'
				.format(
					user.full_name,
					user_data.get('birthday').strftime("%d.%m.%Y")
				)
			)
		return None

	user = message.from_user
	user_data = collection.find_one({ "id": message.from_user.id })

	if not user_data.get('birthday'):
		await message.reply('❓ Ти ще не вказав дату свого народження. Напиши мені в особисті повідомлення /birthday, щоб вказату дату свого народження')
		return None
	
	await message.reply(
		"🎁 Твій день народження - <b>{0}</b>"
			.format(user_data['birthday'].strftime("%d.%m.%Y"))
		)


@birthday_router.message(Command("birthday"), StateFilter(None), DM())
async def birthday_command(message: Message, db: MongoClient, state: FSMContext) -> None:
	collection: Collection = db.user.data
	user_data = collection.find_one({ "id": message.from_user.id })

	if user_data.get("birthday"):
		await message.reply(
			"🎁 Твій день народження - <b>{0}</b>"
				.format(user_data['birthday'].strftime("%d.%m.%Y"))
			)
		return None
	
	await state.set_state(UserData.birthday)
	await message.answer("🎈 Напиши свій день народження в форматі <b>dd.mm.yyyy</b> (наприклад, 31.12.2006)")


@birthday_router.message(StateFilter(UserData.birthday), DM())
async def birthday_handler(message: Message, db: MongoClient, state: FSMContext) -> None:
	try:
		user = message.from_user
		date_format = "%d.%m.%Y"

		date = datetime.strptime(message.text, date_format)
		db.user.data.update_one({ "id": user.id }, { "$set": { "birthday": date } })

		await state.clear()
		await message.answer(f"✅ Твоє день народження ({date.strftime(date_format)}) записано")
	
		user_data = db.user.data.find_one({ 'id': user.id })
		asyncio.create_task(congratulate_async(message.bot, db, user, user_data))
		current_birthday = datetime(2023, date.month, date.day)

		if date.month >= 9 and datetime.now().timestamp() > current_birthday.timestamp():
			chat_id = db.telegram.config.find_one().get('group_id')
			age = datetime.now().year - date.year
			await message.bot.send_message(
				chat_id,
				'🎉 <b>{0}</b> <a href="tg://user?id={1}">{2}</a> виповнилося {3} роки!!! Вітаємо з минулим Днем Народження!!!'
					.format(date.strftime("%d.%m.%Y"), user.id, user.full_name, age)
				)

	except ValueError:
		await message.reply("🔄 Ви вказали неправильно дату, напишіть ще раз")
	except Exception as error:
		logging.error(error)
		await message.reply("Щось пішло не так під час обробки")


@birthday_router.startup()
async def startup_handler(bot: Bot, db: MongoClient = None) -> None:
	if not db:
		return None
	
	try:
		for user in db.user.data.find():
			if not user.get('birthday'):
				continue

			group_id = db.telegram.config.find_one().get('group_id');
			member = await bot.get_chat_member(group_id, user['id'])
			asyncio.create_task(congratulate_async(bot, db, member.user, user))
	except Exception as error:
		logging.error('Birthday system cencelled:')
		logging.error(error)
