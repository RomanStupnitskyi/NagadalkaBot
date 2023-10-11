from pymongo.collection import Collection
from pymongo import MongoClient
from datetime import datetime
from math import ceil
import asyncio
import logging

from aiogram.fsm.state import State, StatesGroup
from aiogram.filters.state import StateFilter
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types.message import Message
from aiogram.types.user import User
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Router, Bot

from .filters.DM import DM
from .filters.Group import Group


birthday_router = Router(name="birthday")


# =================================================================================
# ============================= /NEXT_TO_CONGRATULATE =============================
# =================================================================================

@birthday_router.message(Command("next_to_congratulate"))
async def next_to_congratulate_command(message: Message, db: MongoClient) -> None:
	"""
	The next person to congratulate on birthday
	"""
	next_to_congratulate = db.user.data.find_one()
	now = datetime.now()

	for user_data in db.user.data.find():
		prev_users_birthday: datetime | None = next_to_congratulate.get('birthday')
		if not prev_users_birthday:
			next_to_congratulate = user_data
			continue

		prev_coming_birthday = datetime(now.year, prev_users_birthday.month, prev_users_birthday.day)
		if now.timestamp() > prev_coming_birthday.timestamp():
			prev_coming_birthday = datetime(now.year+1, prev_users_birthday.month, prev_users_birthday.day)

		birthday: datetime | None = user_data.get('birthday')

		if not birthday:
			continue
		
		coming_birthday = datetime(now.year, birthday.month, birthday.day)
		if now.timestamp() > coming_birthday.timestamp():
			coming_birthday = datetime(now.year+1, birthday.month, birthday.day)
		print(coming_birthday.strftime("%d.%m.%Y"))

		if coming_birthday.timestamp() < prev_coming_birthday.timestamp():
			next_to_congratulate = user_data
			continue

	coming_birthday: datetime | None = next_to_congratulate.get('birthday')
	if coming_birthday:
		coming_birthday_date = datetime(now.year, coming_birthday.month, coming_birthday.day)
		if now.timestamp() > coming_birthday_date.timestamp():
			coming_birthday_date = datetime(now.year+1, coming_birthday.month, coming_birthday.day)

		age = coming_birthday_date.year - coming_birthday.year
		member = await message.bot.get_chat_member(db.telegram.config.find_one().get("group_id"), int(next_to_congratulate.get('id')))
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


# ==================================================================================
# ================================= /BIRTHDAY_LIST =================================
# ==================================================================================


@birthday_router.message(Command("birthday_list"))
async def birthday_list_command(message: Message, db: MongoClient) -> None:
	"""
	List of birthdays of all users
	"""
	users_data = [*filter(lambda user: user.get('birthday'), db.user.data.find())]
	users = []
	group_id = db.telegram.config.find_one().get('group_id')
	for user in users_data:
		if len(users) == 10:
			break

		member = await message.bot.get_chat_member(group_id, int(user.get('id')))
		users.append(
			'<code>{0}.</code> {1}: {2}'
				.format(
					users_data.index(user)+1,
					f'<b>{member.user.full_name}</b>' if message.chat.type != "private" else f'<a href="tg://user?id={user.get("id")}">{member.user.full_name}</a>',
					user['birthday'].strftime('%d.%m.%Y')
				)
			)

	previous_button = InlineKeyboardButton(text="Попередня", callback_data="previous_button")
	next_button = InlineKeyboardButton(text="Наступна", callback_data="next_button")
	markup = InlineKeyboardMarkup(inline_keyboard=[[previous_button, next_button]])

	await message.answer(
		'{0}\n\nСторінка 1/{1}'
			.format("\n".join(users), ceil(len(users_data)/10)),
			reply_markup=markup
		)


# =================================================================================
# =================================== /BIRTHDAY ===================================
# =================================================================================


class UserData(StatesGroup):
	birthday = State()


async def congratulate(bot: Bot, db: MongoClient, user: User, birthday: datetime) -> None:
	chat_id = db.telegram.config.find_one().get('group_id')
	age = datetime.now().year - birthday.year
	await bot.send_message(
		chat_id,
		'🎉 Вітаємо нашого однокурсника(-цю) <a href="tg://user?id={0}">{1}</a> з Днем Народження, з його(її) {2}-річчям!!!'
			.format(user.id, user.full_name, age)
		)


async def congratulate_async(bot: Bot, db: MongoClient, user: User, user_data):
	now = datetime(*map(lambda x: int(x), datetime.now().strftime("%Y.%m.%d").split(".")))
	birthday = user_data['birthday']
	current_birthday = datetime(now.year, birthday.month, birthday.day)

	if now.timestamp() >= (current_birthday.timestamp()):
		current_birthday = datetime(now.year+1, birthday.month, birthday.day)

	time_to_congratulate =  current_birthday.timestamp() - datetime.now().timestamp()
	
	await asyncio.sleep(time_to_congratulate)
	await congratulate(bot, db, user, birthday)

	asyncio.create_task(congratulate_async(bot, db, user, user_data))


@birthday_router.message(Command("birthday"), Group())
async def birthday_group_command(message: Message, db: MongoClient) -> None:
	"""
	Birthday command to use in group chat
	"""
	await message.reply("Will be soon")


@birthday_router.message(Command("birthday"), StateFilter(None), DM())
async def birthday_command(message: Message, db: MongoClient, state: FSMContext) -> None:
	"""
	Birthday command to use in direct messages
	"""
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
	"""
	Birthday handler to handle and save user's birthday
	"""
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
