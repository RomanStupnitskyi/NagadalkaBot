from pymongo.collection import Collection
from pymongo import MongoClient
from datetime import datetime
from math import ceil
import asyncio
import logging
import json

from aiogram.fsm.state import State, StatesGroup
from aiogram.filters.state import StateFilter
from aiogram.filters.command import Command
from aiogram.types.callback_query import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types.message import Message
from aiogram.types.user import User
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Router, Bot

from .filters.DM import DM
from .filters.Group import Group
from .filters.IsButton import IsButton


birthday_router = Router(name="birthday")


# =================================================================================
#  /NEXT_TO_CONGRATULATE - Sends a message to the group chat with information about
# =================================================================================

@birthday_router.message(Command("next_to_congratulate"))
async def next_to_congratulate_command(message: Message, db: MongoClient) -> None:
	"""
	This function finds the user whose birthday is closest to the current date and sends a message to the group chat
	with information about their upcoming birthday.

	Args:
	- message (telegram.Message): The message object that triggered the command.
	- db (pymongo.MongoClient): The database client object.

	Returns:
	- None
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


# ======================================================================================
# /BIRTHDAY_LIST - Sends a list of users with their birthdays to the user who triggered
# ======================================================================================


@birthday_router.message(Command("birthday_list"))
async def birthday_list_command(message: Message, db: MongoClient) -> None:
	"""
	Sends a list of users with their birthdays to the user who triggered the command.
	The list is limited to 10 users per page, and pagination buttons are included to navigate between pages.

	Args:
	- message (telegram.Message): The message object that triggered the command.
	- db (pymongo.MongoClient): The MongoDB client object used to interact with the database.

	Returns:
	- None
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

	previous_button = InlineKeyboardButton(text="Попередня", callback_data=json.dumps({'name': 'previous_button', 'page': 1}))
	next_button = InlineKeyboardButton(text="Наступна", callback_data=json.dumps({'name': 'next_button', 'page': 1}))
	markup = InlineKeyboardMarkup(inline_keyboard=[[previous_button, next_button]])

	await message.reply(
		'{0}\n\nСторінка 1/{1}'
			.format("\n".join(users), ceil(len(users_data)/10)),
			reply_markup=markup
		)


@birthday_router.callback_query(IsButton('next_button'))
async def next_button_handler(callback: CallbackQuery, db: MongoClient) -> None:
	"""
	Handles the callback query for the "next" button in the birthday router.
	
	Args:
	- callback (CallbackQuery): The callback query object.
	- db (MongoClient): The MongoDB client object.
	
	Returns:
	- None
	"""
	if callback.from_user.id != callback.message.reply_to_message.from_user.id:
		await callback.answer('Це не ваше повідомлення', show_alert=True)
		return None

	button = json.loads(callback.data)
	page = int(button["page"])
	users_data = [*filter(lambda user: user.get('birthday'), db.user.data.find())]
	group_id = db.telegram.config.find_one().get('group_id')

	if page+1 > ceil(len(users_data)/10):
		await callback.answer('Це остання сторінка', show_alert=True)
		return None
	
	users = []
	for user in users_data[page*10:page*10+10]:
		member = await callback.bot.get_chat_member(group_id, int(user.get('id')))
		users.append(
			'<code>{0}.</code> {1}: {2}'
				.format(
					users_data.index(user)+1,
					f'<b>{member.user.full_name}</b>' if callback.message.chat.type != "private" else f'<a href="tg://user?id={user.get("id")}">{member.user.full_name}</a>',
					user['birthday'].strftime('%d.%m.%Y')
				)
			)
	
	previous_button = InlineKeyboardButton(text="Попередня", callback_data=json.dumps({ 'name': 'previous_button', 'page': page+1 }).__str__())
	next_button = InlineKeyboardButton(text="Наступна", callback_data=json.dumps({ 'name': 'next_button', 'page': page+1 }).__str__())
	markup = InlineKeyboardMarkup(inline_keyboard=[[previous_button, next_button]])

	await callback.message.edit_text(
		'{0}\n\nСторінка {1}/{2}'
			.format("\n".join(users), page+1, ceil(len(users_data)/10)),
			reply_markup=markup
		)


@birthday_router.callback_query(IsButton('previous_button'))
async def previous_button_handler(callback: CallbackQuery, db: MongoClient) -> None:
	"""
	Handles the callback query when the user clicks the "previous" button on the birthday list.

	Parameters:
	- callback (CallbackQuery): The callback query object.
	- db (MongoClient): The MongoDB client object.

	Returns:
	- None
	"""
	if callback.from_user.id != callback.message.reply_to_message.from_user.id:
		await callback.answer('Це не ваше повідомлення', show_alert=True)
		return None
	
	button = json.loads(callback.data)
	page = int(button["page"])
	users_data = [*filter(lambda user: user.get('birthday'), db.user.data.find())]
	group_id = db.telegram.config.find_one().get('group_id')

	if page-1 < 1:
		await callback.answer('Це перша сторінка', show_alert=True)
		return None

	users = []
	for user in users_data[(page-2)*10:(page-2)*10+10]:
		member = await callback.bot.get_chat_member(group_id, int(user.get('id')))
		users.append(
			'<code>{0}.</code> {1}: {2}'
				.format(
					users_data.index(user)+1,
					f'<b>{member.user.full_name}</b>' if callback.message.chat.type != "private" else f'<a href="tg://user?id={user.get("id")}">{member.user.full_name}</a>',
					user['birthday'].strftime('%d.%m.%Y')
				)
			)

	previous_button = InlineKeyboardButton(text="Попередня", callback_data=json.dumps({ 'name': 'previous_button', 'page': page-1 }).__str__())
	next_button = InlineKeyboardButton(text="Наступна", callback_data=json.dumps({ 'name': 'next_button', 'page': page-1 }).__str__())
	markup = InlineKeyboardMarkup(inline_keyboard=[[previous_button, next_button]])
	
	await callback.message.edit_text(
		'{0}\n\nСторінка {1}/{2}'
			.format("\n".join(users), page-1, ceil(len(users_data)/10)),
			reply_markup=markup
		)


# =================================================================================
# /BIRTHDAY - Handles the /birthday command in a group chat and in a private chat.
# =================================================================================


class UserData(StatesGroup):
	birthday = State()


async def congratulate(bot: Bot, db: MongoClient, user: User, birthday: datetime) -> None:
	"""
	Sends a birthday message to the group chat.

	Args:
	- bot (Bot): The bot instance used to send the message.
	- db (MongoClient): The database client instance used to retrieve the group chat ID.
	- user (User): The user whose birthday is being celebrated.
	- birthday (datetime): The user's birthday.

	Returns:
	- None
	"""
	chat_id = db.telegram.config.find_one().get('group_id')
	age = datetime.now().year - birthday.year
	await bot.send_message(
		chat_id,
		'🎉 Вітаємо нашого однокурсника(-цю) <a href="tg://user?id={0}">{1}</a> з Днем Народження, з його(її) {2}-річчям!!!'
			.format(user.id, user.full_name, age)
		)


async def congratulate_async(bot: Bot, db: MongoClient, user: User, user_data):
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
	Handles the /birthday command in a group chat. If a user is mentioned in the command, 
	the bot will check if the user has a birthday stored in the database and reply with 
	their birthday if available. If no user is mentioned, the bot will check if the 
	sender has a birthday stored in the database and reply with their birthday if available. 
	If no birthday is found, the bot will prompt the user to add their birthday.
	
	Args:
	- message (telegram.Message): The message object that triggered the command.
	- db (pymongo.MongoClient): The MongoDB client object used to interact with the database.
	
	Returns:
	- None
	"""
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

	bot = await message.bot.get_me()
	user = message.from_user
	user_data = collection.find_one({ "id": message.from_user.id })

	if not user_data.get('birthday'):
		button = InlineKeyboardButton(text="Додати свій День Народження", url="https://t.me/{0}".format(bot.username))
		markup = InlineKeyboardMarkup(inline_keyboard=[[button]])
		await message.reply('❓ Я не знаю коли в тебе день народження', reply_markup=markup)
		return None
	
	await message.reply(
		"🎁 Твій день народження - <b>{0}</b>"
			.format(user_data['birthday'].strftime("%d.%m.%Y"))
		)


@birthday_router.message(Command("birthday"), StateFilter(None), DM())
async def birthday_command(message: Message, db: MongoClient, state: FSMContext) -> None:
	"""
	Handles the '/birthday' command, which retrieves the user's birthday from the database and sends it back to them.
	If the user has not set their birthday yet, the function prompts them to do so by setting the conversation state to
	'UserData.birthday' and sending a message with instructions.
	
	Args:
	- message (telegram.Message): The message object representing the user's command.
	- db (pymongo.MongoClient): The MongoDB client object used to interact with the database.
	- state (aiogram.dispatcher.fsm.FSMContext): The FSM context object used to manage the conversation state.

	Returns:
	- None
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
	Handles the user's birthday input by updating the user's birthday in the database and sending a congratulatory message
	if it's the user's birthday. If the user inputs an invalid date, an error message is sent.

	Args:
	- message (telegram.Message): The message object representing the user's input.
	- db (pymongo.MongoClient): The MongoDB client object used to interact with the database.
	- state (aiogram.dispatcher.storage.FSMContext): The FSMContext object used to manage the conversation state.

	Returns:
	- None
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
	"""
	Handles the startup of the BirthdayRouter by congratulating users with a birthday.

	Args:
	- bot (Bot): The bot instance.
	- db (MongoClient, optional): The MongoDB client instance. Defaults to None.

	Returns:
	- None
	"""
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
