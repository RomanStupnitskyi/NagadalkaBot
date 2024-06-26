import json
from math import ceil
from typing import Any
from pymongo import MongoClient

from aiogram import Router
from aiogram.types.message import Message
from aiogram.filters.command import Command
from aiogram.types.callback_query import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.filters.IsButton import IsButton
from bot.extensions.sorted_users import get_sorted_users


birthday_list_router = Router(name="birthday_list")


@birthday_list_router.message(Command("birthday_list"))
async def birthday_list_command(message: Message, database_client: MongoClient, telegram_config: dict[str, Any]) -> None:
	users_data = get_sorted_users(database_client)
	users = []
	for user in users_data:
		if len(users) == 10:
			break

		member = await message.bot.get_chat_member(telegram_config.GROUP_ID, int(user["id"]))
		users.append(
			'<code>{0}.</code> {1}: {2}'
				.format(
					users_data.index(user)+1,
					f'<b>{member.user.full_name}</b>' if message.chat.type != "private" else f'<a href="tg://user?id={user.get("id")}">{member.user.full_name}</a>',
					user['birthday'].strftime('%d.%m.%Y')
				)
			)

	builder = InlineKeyboardBuilder()
	builder.button(text="Попередня", callback_data=json.dumps({'name': 'previous_button', 'page': 1}))
	builder.button(text="Наступна", callback_data=json.dumps({'name': 'next_button', 'page': 1}))
	builder.adjust(2, False)

	await message.reply(
		'{0}\n\nСторінка 1/{1}'
			.format("\n".join(users), ceil(len(users_data)/10)),
			reply_markup=builder.as_markup()
		)


@birthday_list_router.callback_query(IsButton('next_button'))
async def next_button_handler(callback: CallbackQuery, database_client: MongoClient, telegram_config: dict[str, Any]) -> None:
	button = json.loads(callback.data)
	page = int(button["page"])
	users_data = get_sorted_users(database_client)

	if page+1 > ceil(len(users_data)/10):
		await callback.answer('Це остання сторінка', show_alert=True)
		return None
	
	users = []
	for user in users_data[page*10:page*10+10]:
		member = await callback.bot.get_chat_member(telegram_config.GROUP_ID, int(user.get('id')))
		users.append(
			'<code>{0}.</code> {1}: {2}'
				.format(
					users_data.index(user)+1,
					f'<b>{member.user.full_name}</b>' if callback.message.chat.type != "private" else f'<a href="tg://user?id={user.get("id")}">{member.user.full_name}</a>',
					user['birthday'].strftime('%d.%m.%Y')
				)
			)
	
	builder = InlineKeyboardBuilder()
	builder.button(text="Попередня", callback_data=json.dumps({'name': 'previous_button', 'page': page+1}).__str__())
	builder.button(text="Наступна", callback_data=json.dumps({'name': 'next_button', 'page': page+1}).__str__())
	builder.adjust(2, False)

	await callback.message.edit_text(
		'{0}\n\nСторінка {1}/{2}'
			.format("\n".join(users), page+1, ceil(len(users_data)/10)),
			reply_markup=builder.as_markup()
		)


@birthday_list_router.callback_query(IsButton('previous_button'))
async def previous_button_handler(callback: CallbackQuery, database_client: MongoClient, telegram_config: dict[str, Any]) -> None:
	button = json.loads(callback.data)
	page = int(button["page"])
	users_data = get_sorted_users(database_client)

	if page-1 < 1:
		await callback.answer('Це перша сторінка', show_alert=True)
		return None

	users = []
	for user in users_data[(page-2)*10:(page-2)*10+10]:
		member = await callback.bot.get_chat_member(telegram_config.GROUP_ID, int(user.get('id')))
		users.append(
			'<code>{0}.</code> {1}: {2}'
				.format(
					users_data.index(user)+1,
					f'<b>{member.user.full_name}</b>' if callback.message.chat.type != "private" else f'<a href="tg://user?id={user.get("id")}">{member.user.full_name}</a>',
					user['birthday'].strftime('%d.%m.%Y')
				)
			)

	builder = InlineKeyboardBuilder()
	builder.button(text="Попередня", callback_data=json.dumps({'name': 'previous_button', 'page': page-1}).__str__())
	builder.button(text="Наступна", callback_data=json.dumps({'name': 'next_button', 'page': page-1}).__str__())
	builder.adjust(2, False)
	
	await callback.message.edit_text(
		'{0}\n\nСторінка {1}/{2}'
			.format("\n".join(users), page-1, ceil(len(users_data)/10)),
			reply_markup=builder.as_markup()
		)
